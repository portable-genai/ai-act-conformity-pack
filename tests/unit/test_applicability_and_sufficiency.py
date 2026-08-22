"""The applicability and sufficiency engines: APPLIES/NOT/CONDITIONAL, named gaps, fail-closed."""

from __future__ import annotations

from conformity_pack.domain.applicability import assess_cell, build_matrix
from conformity_pack.domain.models import (
    Applicability,
    DimensionVerdict,
    ObligationRef,
    RiskTier,
    Sufficiency,
    TierVerdict,
)
from conformity_pack.domain.sufficiency import assess_obligation, assess_sufficiency


def _verdict(
    tier: RiskTier = RiskTier.HIGH,
    *,
    conditional: bool = False,
    frameworks: tuple[str, ...] = (),
) -> TierVerdict:
    dims = tuple(DimensionVerdict(f, True, "in scope") for f in frameworks)
    return TierVerdict("s", tier, conditional, (), dims)


def _obl(
    framework: str = "eu-ai-act",
    min_tier: RiskTier = RiskTier.HIGH,
    jurisdiction: str = "",
    required: tuple[str, ...] = (),
) -> ObligationRef:
    return ObligationRef("o1", "t", framework, min_tier, jurisdiction, required)


def test_a_matching_high_obligation_applies() -> None:
    cell = assess_cell(_verdict(), _obl(), system_jurisdictions=frozenset({"SG"}))
    assert cell.applicability is Applicability.APPLIES


def test_a_framework_the_system_is_not_subject_to_does_not_apply() -> None:
    cell = assess_cell(_verdict(), _obl(framework="feat"), system_jurisdictions=frozenset({"SG"}))
    assert cell.applicability is Applicability.NOT_APPLICABLE


def test_an_undeclared_tier_makes_every_relevant_obligation_conditional() -> None:
    cell = assess_cell(_verdict(conditional=True), _obl(), system_jurisdictions=frozenset({"SG"}))
    assert cell.applicability is Applicability.CONDITIONAL


def test_an_undeclared_jurisdiction_on_an_anchored_obligation_is_conditional() -> None:
    """Fail closed: an anchored obligation with no declared jurisdiction is undecided."""
    cell = assess_cell(
        _verdict(frameworks=("feat",)),
        _obl(framework="feat", jurisdiction="SG"),
        system_jurisdictions=frozenset(),
    )
    assert cell.applicability is Applicability.CONDITIONAL


def test_a_weaker_system_tier_than_the_obligation_does_not_apply() -> None:
    cell = assess_cell(
        _verdict(RiskTier.LIMITED), _obl(min_tier=RiskTier.HIGH), system_jurisdictions=frozenset()
    )
    assert cell.applicability is Applicability.NOT_APPLICABLE


def test_the_matrix_has_one_cell_per_obligation() -> None:
    obligations = (_obl(), _obl(framework="feat"))
    cells = build_matrix(_verdict(), obligations, system_jurisdictions=frozenset({"SG"}))
    assert len(cells) == 2


# ------------------------------------------------------------------- sufficiency
def _ev(kind: str, obligation_ids: tuple[str, ...]):
    from conformity_pack.domain.models import EvidenceItem

    return EvidenceItem(id=f"e-{kind}", kind=kind, obligation_ids=obligation_ids)


def test_all_required_evidence_present_is_sufficient() -> None:
    obl = _obl(required=("eval-report", "audit-trail"))
    evidence = (_ev("eval-report", ("o1",)), _ev("audit-trail", ("o1",)))
    assert assess_obligation(obl, evidence).sufficiency is Sufficiency.SUFFICIENT


def test_some_required_evidence_present_is_partial_and_names_the_gap() -> None:
    obl = _obl(required=("eval-report", "audit-trail"))
    verdict = assess_obligation(obl, (_ev("eval-report", ("o1",)),))
    assert verdict.sufficiency is Sufficiency.PARTIAL
    assert verdict.missing_kinds == ("audit-trail",)


def test_no_required_evidence_present_is_insufficient() -> None:
    obl = _obl(required=("eval-report",))
    assert assess_obligation(obl, ()).sufficiency is Sufficiency.INSUFFICIENT


def test_sufficiency_scores_only_applies_cells() -> None:
    """A CONDITIONAL or NOT_APPLICABLE obligation is not scored: no verdict is manufactured."""
    from conformity_pack.domain.models import ApplicabilityCell

    cells = (
        ApplicabilityCell("s", "o1", "eu-ai-act", Applicability.APPLIES, ()),
        ApplicabilityCell("s", "o2", "eu-ai-act", Applicability.CONDITIONAL, ()),
    )
    obligations_by_id = {"o1": _obl(required=("eval-report",)), "o2": _obl(required=("x",))}
    verdicts = assess_sufficiency(cells, obligations_by_id, ())
    assert [v.obligation_id for v in verdicts] == ["o1"]
