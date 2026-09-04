"""Freeze the obligations-control-mapping seam: the ``obligation-register-kit`` record shape this
repo consumes.

ai-act-conformity-pack does not own obligations; it reads them from obligations-control-mapping,
typed by the shared kit. This suite freezes the ONE translation from a kit ``Obligation`` into the
vertical ``ObligationRef`` so a kit release that changed a field name or an attribute key fails here
rather than silently mis-classifying applicability. It is a contract fixture test, exactly as the
build rules require for a consumed-but-unbuilt dependency's shape.
"""

from __future__ import annotations

from obligation_register import Citation as KitCitation
from obligation_register import Obligation as KitObligation

from conformity_pack.adapters._obligation_records import obligation_to_ref
from conformity_pack.adapters.local import fleet_fixtures
from conformity_pack.domain.models import RiskTier


def test_a_kit_record_translates_to_the_expected_vertical_ref() -> None:
    record = KitObligation(
        id="eu-art9",
        title="EU AI Act Art. 9",
        text="risk management system",
        citation=KitCitation(source_id="rgc7:obligation:eu-art9", title="EU AI Act Art. 9"),
        attributes=(
            ("framework", "eu-ai-act"),
            ("min_tier", "high"),
            ("jurisdiction", ""),
            ("required_evidence", "risk-assessment;eval-report"),
        ),
    )
    ref = obligation_to_ref(record)
    assert ref.id == "eu-art9"
    assert ref.framework == "eu-ai-act"
    assert ref.min_tier is RiskTier.HIGH
    assert ref.jurisdiction == ""
    assert ref.required_evidence == ("risk-assessment", "eval-report")
    assert ref.citation is not None and ref.citation.source_id == "rgc7:obligation:eu-art9"


def test_a_record_with_no_min_tier_fails_closed_to_high_not_minimal() -> None:
    record = KitObligation(
        id="x",
        title="t",
        text="t",
        citation=KitCitation(source_id="rgc7:obligation:x"),
        attributes=(("framework", "feat"),),
    )
    assert obligation_to_ref(record).min_tier is RiskTier.HIGH


def test_the_fixture_graph_is_built_from_kit_records() -> None:
    """The local fixture obligations are genuinely kit records, translated at import."""
    assert fleet_fixtures.KIT_OBLIGATIONS
    assert all(isinstance(o, KitObligation) for o in fleet_fixtures.KIT_OBLIGATIONS)
    assert len(fleet_fixtures.OBLIGATIONS) == len(fleet_fixtures.KIT_OBLIGATIONS)
    # Every kit record's id survives the translation, so no obligation is dropped.
    assert {o.id for o in fleet_fixtures.KIT_OBLIGATIONS} == {
        r.id for r in fleet_fixtures.OBLIGATIONS
    }
