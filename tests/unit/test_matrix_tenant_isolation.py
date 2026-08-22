"""The persisted applicability matrix is partitioned by tenant (check C2).

The store had no tenant column at all. ``put(as_of, cells)`` keyed a shared dict on the replay
date alone, so two tenants assessing on the same ``as_of`` overwrote each other and either read
the other's cells; the BigQuery table had no tenant column either, so the persisted lineage
record could not even be filtered after the fact. A lineage record is what a regulator is shown,
so "whose matrix is this" is not a reporting nicety.

Three things are pinned here, and the third is the one that gets relaxed later if nobody writes
it down:

* the partition HOLDS: one tenant's write never becomes another's read, on the same ``as_of``;
* the partition is derived from the VERIFIED principal, never from the request body, so the
  proof runs through the real API route with two seeded personas in two tenants;
* an EMPTY tenant is REFUSED. Storing under ``""`` is not a neutral default, it is one partition
  that every unscoped caller shares, which is the defect wearing a different name.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from hex_service_kit.identity import Principal

from conformity_pack.adapters.gcp.matrix_store import matrix_rows
from conformity_pack.adapters.local.matrix_store import LocalMatrixStore
from conformity_pack.api.schemas import AssessRequest
from conformity_pack.config import build_container
from conformity_pack.domain.errors import TenantScopeError
from conformity_pack.domain.models import Applicability, ApplicabilityCell

from tests.conftest import build_conformity_service, local_settings
from tests.fixtures import sample_cases

_AS_OF = "2026-08-21"
_TENANT_A = "alpha-bank"
_TENANT_B = "beta-bank"

_CELL = ApplicabilityCell(
    system=sample_cases.ESCALATING_SYSTEM,
    obligation_id="eu-art9",
    framework="eu-ai-act",
    applicability=Applicability.APPLIES,
    reasons=("framework eu-ai-act applies",),
)


def test_one_tenants_matrix_is_never_another_tenants_read() -> None:
    """The whole defect in one test: same as_of, two tenants, one store."""
    container = build_container(local_settings())
    store = container.matrix_store
    service = build_conformity_service(container)

    service.assess(
        sample_cases.ESCALATING_CASE, actor=sample_cases.ACTOR, tenant=_TENANT_A, as_of=_AS_OF
    )
    alpha = store.get(_TENANT_A, _AS_OF)
    assert alpha, "tenant A stored nothing, so this proves nothing"

    service.assess(
        sample_cases.ROUTINE_CASE, actor="analyst@beta.example", tenant=_TENANT_B, as_of=_AS_OF
    )

    assert store.get(_TENANT_A, _AS_OF) == alpha, (
        "tenant B's write on the same as_of overwrote tenant A's matrix"
    )
    assert store.get(_TENANT_B, _AS_OF) != alpha, (
        "tenant B read back tenant A's cells: the store is keyed on the as_of alone"
    )


def test_a_tenant_reads_nothing_for_an_as_of_it_never_wrote() -> None:
    """No silent fallback to a neighbour's partition when this tenant has no row."""
    store = LocalMatrixStore(local_settings())
    store.put(_TENANT_A, _AS_OF, (_CELL,))
    assert store.get(_TENANT_B, _AS_OF) == ()


@pytest.mark.parametrize("tenant", ["", "   "], ids=["empty", "whitespace"])
def test_an_unscoped_write_is_refused_rather_than_stored_under_the_empty_string(
    tenant: str,
) -> None:
    store = LocalMatrixStore(local_settings())
    with pytest.raises(TenantScopeError):
        store.put(tenant, _AS_OF, (_CELL,))
    with pytest.raises(TenantScopeError):
        store.get(tenant, _AS_OF)


def test_the_service_refuses_to_persist_a_matrix_it_cannot_attribute() -> None:
    """The refusal reaches the caller instead of the write silently landing in a shared bucket."""
    container = build_container(local_settings())
    service = build_conformity_service(container)
    with pytest.raises(TenantScopeError):
        service.assess(
            sample_cases.ESCALATING_CASE, actor=sample_cases.ACTOR, tenant="", as_of=_AS_OF
        )


def test_the_persisted_bigquery_row_carries_the_tenant_column() -> None:
    """A lineage record with no tenant column cannot be filtered even after the fact."""
    rows = matrix_rows(_TENANT_A, _AS_OF, (_CELL,))
    assert rows and all(row["tenant"] == _TENANT_A for row in rows)
    assert all(row["as_of"] == _AS_OF for row in rows)


def test_the_api_partitions_by_the_verified_principal_not_by_the_body(
    api_client: TestClient,
) -> None:
    """Two seeded personas, two tenants, one as_of, driven through the REAL route."""
    from conformity_pack.api.app import _container

    store = _container().matrix_store

    first = api_client.post(
        "/v1/assess",
        json={"system": sample_cases.ESCALATING_SYSTEM, "as_of": _AS_OF},
        headers={"X-Dev-Persona": "analyst"},
    )
    assert first.status_code == 200
    demo_bank = store.get("demo-bank", _AS_OF)
    assert demo_bank, "the analyst persona's tenant partition holds no matrix"

    second = api_client.post(
        "/v1/assess",
        json={"system": sample_cases.ROUTINE_SYSTEM, "as_of": _AS_OF},
        headers={"X-Dev-Persona": "other-tenant"},
    )
    assert second.status_code == 200

    assert store.get("demo-bank", _AS_OF) == demo_bank
    assert store.get("other-bank", _AS_OF) != demo_bank


def test_a_verified_principal_with_no_tenant_is_refused_with_403_not_404_or_500(
    api_client: TestClient,
) -> None:
    """The refusal is REACHABLE, so it has to answer honestly rather than by accident.

    ``adapters/gcp/identity.py`` sets ``tenant`` from the assertion's ``hd`` claim, and an IAP
    assertion for an account outside a Workspace domain carries none, so a verified principal
    with an empty tenant is an ordinary case and not a hypothetical. It must not become a 404
    (the system exists), a 500 (nothing broke) or a silent write into the shared partition.
    """
    from conformity_pack.api.app import app, get_principal

    app.dependency_overrides[get_principal] = lambda: Principal(
        subject="user@gmail.example", tenant="", source="test:no-tenant"
    )
    try:
        resp = api_client.post(
            "/v1/assess",
            json={"system": sample_cases.ESCALATING_SYSTEM, "as_of": _AS_OF},
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
    assert "tenant" in resp.json()["detail"]


def test_the_request_schema_advertises_no_tenant_field() -> None:
    """Check C1's half of this: a field the API accepts is a field a client can assert."""
    assert "tenant" not in AssessRequest.model_fields
    assert "actor" not in AssessRequest.model_fields
