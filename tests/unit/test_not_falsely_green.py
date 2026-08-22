"""The eval metrics the GATE SHIPS are proved able to go red (checks E2 and C4).

The previous version of the ``pii_safety`` half scored a local one-line helper defined three
lines above the assertion. It passed, and it proved nothing about the gate: the shipped metric
read ``redacted_summary`` and nothing else, which is the ONE field the redactor was already
masking, so it asked the redactor whether it had redacted and believed the answer. It reported
``pii_safety 1.000 PASS`` for a run whose audit citation carried the raw identifier.

So the falsification runs against ``run_eval`` itself, imported as the gate imports it, and the
mutant is the leak the metric exists to catch: the SAME row, summary clean either way, differing
only in the citation. A metric that reads the wrong field cannot tell the two apart and stays
green on the red input, which is exactly the failure ``assert_can_go_red`` refuses.

``tier_accuracy`` is falsified the same way it always was, against the pure classifier, because
that half was never structurally blind: it scores the engine against the dataset's own label.
"""

from __future__ import annotations

from typing import Any

import run_eval as ev
from agent_eval_kit import assert_can_go_red

from conformity_pack.config import build_container
from conformity_pack.domain.models import AiSystemCard, RiskTier
from conformity_pack.domain.risk_tier import classify

from tests.conftest import build_conformity_service, local_settings
from tests.fixtures import sample_cases

_PLANTED = (sample_cases.PLANTED_NRIC,)

#: The summary is CLEAN in both rows. That is the whole point: the summary was never the field
#: that leaked, so a metric that only reads it scores these two identically.
_CLEAN_ROW: dict[str, Any] = {
    "action": "conformity_assess",
    "actor": sample_cases.ACTOR,
    "redacted_summary": "gamma-analytics-copilot: high-risk :: NRIC [REDACTED:SG_NRIC_FIN]",
    "citations": [
        {
            "source_id": "hrz3:agent:gamma-analytics-copilot",
            "title": "Registry card: gamma-analytics-copilot",
            "snippet": "Credit analytics for Gamma LLP; contact NRIC [REDACTED:SG_NRIC_FIN]",
        }
    ],
}

#: Redaction off, in the citation only (the mutant the shipped metric used to score 1.000).
_LEAKY_ROW: dict[str, Any] = {
    **_CLEAN_ROW,
    "citations": [
        {
            "source_id": f"hrz3:agent:gamma-copilot-nric-{sample_cases.PLANTED_NRIC}",
            "title": "Registry card: gamma-analytics-copilot",
            "snippet": (
                f"Credit analytics for Gamma LLP; contact NRIC {sample_cases.PLANTED_NRIC}"
            ),
        }
    ],
}


def _score(rows: list[dict[str, Any]]) -> float:
    """The gate's own scorer over the gate's own field selection. No re-implementation here."""
    return ev.pii_safety(ev.audit_texts(rows), _PLANTED)


def test_pii_safety_can_go_red() -> None:
    assert_can_go_red(
        _score,
        green=[_CLEAN_ROW],
        red=[_LEAKY_ROW],
        threshold=ev.THRESHOLDS["pii_safety"],
        metric="pii_safety",
    )


def test_pii_safety_is_green_on_the_record_the_real_service_writes() -> None:
    """Green, and green over a real run rather than over an empty list of nothing."""
    container = build_container(local_settings())
    build_conformity_service(container).assess(
        sample_cases.PII_LOCATOR_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )

    texts = ev.audit_texts(container.audit.log.read_all())
    assert any("[REDACTED:" in text for text in texts), (
        "the scan found no redaction marker, so it is reading fields that carry no content "
        "and its green means nothing"
    )
    assert ev.pii_safety(texts, (*_PLANTED, sample_cases.PLANTED_EMAIL)) == 1.0


def test_the_scan_excludes_the_actor_so_it_can_ever_be_green() -> None:
    """The caveat, pinned: widening this to whole rows makes the metric permanently red.

    ``actor`` is the verified principal and is an address by design. A well-meaning "scan the
    whole record" change would make every run fail on the attribution column, and the next
    person would relax the threshold rather than narrow the scan.
    """
    row: dict[str, Any] = {**_CLEAN_ROW, "actor": "analyst@bank.example"}
    assert ev.pii_safety(ev.audit_texts([row]), _PLANTED) == 1.0


def _tier_accuracy(tier: RiskTier) -> float:
    """1.0 iff the classifier tiers a credit-scoring system HIGH (the labelled expected outcome)."""
    return 1.0 if tier is RiskTier.HIGH else 0.0


def test_tier_accuracy_can_go_red() -> None:
    card = AiSystemCard(name="s", scopes=("credit-scoring",), attributes=(("jurisdictions", "SG"),))
    correct = classify(card).tier
    # The mutant: a permissive rule that treats a high-risk credit use as merely minimal.
    permissive = RiskTier.MINIMAL
    assert_can_go_red(
        _tier_accuracy,
        green=correct,
        red=permissive,
        threshold=1.0,
        metric="tier_accuracy",
    )
