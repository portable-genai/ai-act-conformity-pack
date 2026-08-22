"""Nothing redaction removed survives anywhere else in the WORM record (check C3).

``ConformityService.assess`` masked ``redacted_summary`` and then handed the SAME event its
citations untouched, so the identifier the summary no longer carried was persisted verbatim one
field away, in a record that is by design immutable and long-retained. The summary is not the
record.

Two rules this suite holds, and they pull in opposite directions, which is why both are written
down:

* every CONTENT field is scanned: the summary, and each citation's locator, title and snippet.
  The snippet is ``AiSystemCard.description[:80]`` and the locator and title are both built from
  the card NAME, so all three are upstream free text wearing a structural-looking name.
* the ATTRIBUTION field is not. ``actor`` is the verified principal and is an address by design,
  so a blanket scan over a whole audit row could never go green, and a scan that "fixed" that by
  masking the actor would erase the only column that says who acted.

Scored two ways, as the eval metric is: the shared pack's own rows, plus the planted literals,
which still fire if a pattern row is broken.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest
from pii_kit import pack_leak

from conformity_pack.adapters._review_payload import result_to_review
from conformity_pack.config import build_container
from conformity_pack.domain.models import AiSystemInput
from conformity_pack.domain.pii import PII_PATTERNS

from tests.conftest import build_conformity_service, local_settings
from tests.fixtures import sample_cases

_PLANTED = (sample_cases.PLANTED_NRIC, sample_cases.PLANTED_EMAIL)


def _content(row: Mapping[str, Any]) -> str:
    """Every content-bearing field of one audit row, as one scannable blob.

    ``actor`` and the structural columns are excluded deliberately: see the module docstring.
    """
    return " ".join(
        (
            str(row.get("redacted_summary", "")),
            json.dumps(row.get("citations", []), sort_keys=True),
        )
    )


@pytest.mark.parametrize(
    "case",
    [sample_cases.PII_CASE, sample_cases.PII_LOCATOR_CASE],
    ids=["identifier-in-the-description", "identifier-in-the-system-name"],
)
def test_no_identifier_reaches_the_audit_record(case: AiSystemInput) -> None:
    container = build_container(local_settings())
    build_conformity_service(container).assess(
        case, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )

    rows = list(container.audit.log.read_all())
    assert rows, "the assess path wrote no audit record, so this proves nothing"

    for row in rows:
        blob = _content(row)
        assert not pack_leak(blob, PII_PATTERNS), f"pack row matched in the WORM record: {blob}"
        for token in _PLANTED:
            assert token not in blob, f"planted {token!r} survived into the WORM record: {blob}"


def test_the_actor_is_kept_verbatim_because_it_is_attribution() -> None:
    """The caveat, pinned: the principal is an address and must NOT be masked away."""
    container = build_container(local_settings())
    build_conformity_service(container).assess(
        sample_cases.PII_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )

    actors = [str(row.get("actor", "")) for row in container.audit.log.read_all()]
    assert actors == [sample_cases.ACTOR]


#: The review payload's ATTRIBUTION keys, dropped before the scan for the same reason the audit
#: row's ``actor`` is: ``maker`` is the verified principal and is an address by design, and
#: ``tenant`` is a partition name the deployment chose. Scanning them would make this test
#: permanently red and the next person would narrow it to a field list instead.
_ATTRIBUTION_KEYS = ("maker", "tenant")


def test_the_whole_review_payload_is_redacted_not_only_its_narrative_fields() -> None:
    """Every CONTENT field that crosses to the console, including the structurally-named ones.

    The console is a shared sink. ``subject`` and ``summary`` were masked while ``case_ref`` and
    ``source_key`` were derived from the SAME subject and passed raw on the lines below, so the
    identifier the payload had just removed from two fields crossed the wire in the two beside
    them; a citation LOCATOR is the same trap one level down. The scan therefore runs over the
    SERIALISED payload minus the attribution keys, so a field added to the Review later is
    covered by default rather than by somebody remembering to add it here.
    """
    container = build_container(local_settings())
    result = build_conformity_service(container).assess(
        sample_cases.PII_LOCATOR_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )
    review = result_to_review(result, maker=sample_cases.ACTOR, tenant=sample_cases.TENANT)

    payload = {
        key: value for key, value in review.to_payload().items() if key not in _ATTRIBUTION_KEYS
    }
    blob = json.dumps(payload, sort_keys=True)
    assert not pack_leak(blob, PII_PATTERNS), f"pack row matched in the review payload: {blob}"
    for token in _PLANTED:
        assert token not in blob, f"planted {token!r} crossed to the console: {blob}"


def test_the_review_source_key_is_stable_across_retries() -> None:
    """The cost of redacting the key, pinned: it must still be idempotent at the console.

    Two cases whose subjects differ ONLY in a masked identifier now collapse to one review, which
    is the right trade against publishing the identifier. What would NOT be acceptable is a key
    that varied per call, because a retried delivery would then duplicate the review rather than
    dedupe. ``pii_kit.redact`` substitutes a fixed token per pattern, so it does not; measured
    here rather than assumed.
    """
    container = build_container(local_settings())
    result = build_conformity_service(container).assess(
        sample_cases.PII_LOCATOR_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )
    keys = {
        result_to_review(result, maker=sample_cases.ACTOR, tenant=sample_cases.TENANT).source_key
        for _ in range(50)
    }
    assert len(keys) == 1, f"the idempotency key is not stable across retries: {keys}"
