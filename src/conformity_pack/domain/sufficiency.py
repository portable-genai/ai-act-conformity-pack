"""The deterministic evidence-sufficiency engine (pure stdlib, replayable).

Given the obligations that APPLY to a system and the evidence harvested for it (model-quality-gate
eval reports, agent-observability trails), this maps evidence to obligations and decides, per
obligation, whether the required evidence kinds are present. Missing evidence is a NAMED gap, never
papered over; the LLM is never asked to assert conformity the evidence does not support.

Deterministic: the same obligations and the same evidence set always produce the same verdicts.
"""

from __future__ import annotations

from .kernel import Citation
from .models import (
    Applicability,
    ApplicabilityCell,
    EvidenceItem,
    ObligationRef,
    Sufficiency,
    SufficiencyVerdict,
)


def _evidence_kinds_for(obligation_id: str, evidence: tuple[EvidenceItem, ...]) -> set[str]:
    """The distinct evidence kinds harvested that reference this obligation."""
    return {item.kind for item in evidence if obligation_id in item.obligation_ids}


def _citations_for(obligation_id: str, evidence: tuple[EvidenceItem, ...]) -> tuple[Citation, ...]:
    return tuple(
        item.citation
        for item in evidence
        if obligation_id in item.obligation_ids and item.citation is not None
    )


def assess_obligation(
    obligation: ObligationRef,
    evidence: tuple[EvidenceItem, ...],
) -> SufficiencyVerdict:
    """Decide whether the harvested evidence answers one applicable obligation."""
    required = set(obligation.required_evidence)
    present = _evidence_kinds_for(obligation.id, evidence) & required if required else set()
    missing = required - present

    if not required:
        # An obligation that names no required evidence is satisfied by declaration alone; there
        # is nothing to be insufficient about, so it is trivially sufficient.
        sufficiency = Sufficiency.SUFFICIENT
    elif not present:
        sufficiency = Sufficiency.INSUFFICIENT
    elif missing:
        sufficiency = Sufficiency.PARTIAL
    else:
        sufficiency = Sufficiency.SUFFICIENT

    return SufficiencyVerdict(
        obligation_id=obligation.id,
        sufficiency=sufficiency,
        present_kinds=tuple(sorted(present)),
        missing_kinds=tuple(sorted(missing)),
        citations=_citations_for(obligation.id, evidence),
    )


def assess_sufficiency(
    cells: tuple[ApplicabilityCell, ...],
    obligations_by_id: dict[str, ObligationRef],
    evidence: tuple[EvidenceItem, ...],
) -> tuple[SufficiencyVerdict, ...]:
    """Sufficiency for every obligation that APPLIES to the system, in obligation-id order.

    Only APPLIES cells are scored: a NOT_APPLICABLE obligation needs no evidence, and a
    CONDITIONAL one cannot be scored until a human resolves it, so scoring it would manufacture a
    verdict the engine has not earned.
    """
    applies = sorted({c.obligation_id for c in cells if c.applicability is Applicability.APPLIES})
    return tuple(
        assess_obligation(obligations_by_id[oid], evidence)
        for oid in applies
        if oid in obligations_by_id
    )
