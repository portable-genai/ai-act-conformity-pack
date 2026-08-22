"""Managed MatrixStorePort: persist the applicability matrix to BigQuery (SDK imports stay lazy).

Persists a computed matrix into a BigQuery table for lineage reporting (honouring the row's
BigQuery stack entry). The ``google-cloud-bigquery`` import lives inside the method so the offline
profiles import this module with no SDK installed and the offline gate stays SDK-free.

Every row carries a ``tenant`` column. Carrying only ``as_of`` lands every tenant's lineage in one
undifferentiated table: not merely unfiltered on read, but unfilterABLE, because the column that
says whose matrix a row is never gets written. A retention-bound lineage table cannot be
repartitioned after the fact, so no later correction can repair the rows already written.
"""

from __future__ import annotations

from typing import Any

from hex_service_kit.serialization import dataclass_from_jsonable, to_jsonable

from ...config import Settings
from ...domain.models import ApplicabilityCell
from ...ports.matrix_store import require_tenant

#: The lineage table, unqualified. One table, partitioned by the ``tenant`` column below.
_TABLE = "applicability_matrix"


def matrix_rows(
    tenant: str, as_of: str, cells: tuple[ApplicabilityCell, ...]
) -> list[dict[str, Any]]:
    """The rows one ``put`` inserts. Pure, so the tenant column is provable with no live GCP.

    Split out of :meth:`CloudMatrixStore.put` deliberately: the method itself cannot run in the
    offline gate (it needs a client), and a tenant column nobody can assert offline is a tenant
    column that goes missing again in the next refactor.
    """
    partition = require_tenant(tenant)
    return [{"tenant": partition, "as_of": as_of, **to_jsonable(cell)} for cell in cells]


def _cell_from_row(row: dict[str, Any]) -> ApplicabilityCell:
    """Rehydrate one cell from a stored row, dropping the two partition columns.

    ``tenant`` and ``as_of`` are the KEY, not part of the cell: feeding them back into the
    dataclass would either be ignored or, worse, silently shadow a field of the same name added
    later. Pure, and tested beside :func:`matrix_rows` for the same reason.
    """
    payload = {k: v for k, v in row.items() if k not in ("tenant", "as_of")}
    cell = dataclass_from_jsonable(ApplicabilityCell, payload)
    assert isinstance(cell, ApplicabilityCell)
    return cell


class CloudMatrixStore:
    """Persist and read applicability matrices in BigQuery, partitioned by tenant."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _dataset(self) -> str:
        dataset = self._settings.matrix_dataset.strip()
        if not dataset:
            raise RuntimeError(
                "matrix_dataset is not configured; set it (config/settings.yaml matrix_dataset) "
                "to the BigQuery 'project.dataset' the lineage table lives in."
            )
        return dataset

    def put(
        self, tenant: str, as_of: str, cells: tuple[ApplicabilityCell, ...]
    ) -> str:  # pragma: no cover - needs live GCP
        partition = require_tenant(tenant)
        rows = matrix_rows(partition, as_of, cells)
        from google.cloud import (
            bigquery,
        )

        client = bigquery.Client()
        table = f"{self._dataset()}.{_TABLE}"
        client.insert_rows_json(table, rows)
        return f"bq:{table}:{partition}:{as_of}"

    def get(
        self, tenant: str, as_of: str
    ) -> tuple[ApplicabilityCell, ...]:  # pragma: no cover - needs live GCP
        partition = require_tenant(tenant)
        from google.cloud import (
            bigquery,
        )

        client = bigquery.Client()
        # The tenant filter is the STORE's, and it is a query PARAMETER: a filter the caller
        # applied after the fact is not isolation, and one interpolated into the text is a
        # cross-tenant read a single quoting mistake away. Only the table identifier is
        # interpolated, and it comes from configuration rather than from any request.
        job = client.query(
            f"SELECT * FROM `{self._dataset()}.{_TABLE}` "  # noqa: S608 - identifier, not a value
            "WHERE tenant = @tenant AND as_of = @as_of ORDER BY obligation_id",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("tenant", "STRING", partition),
                    bigquery.ScalarQueryParameter("as_of", "STRING", as_of),
                ]
            ),
        )
        return tuple(_cell_from_row(dict(row)) for row in job.result())
