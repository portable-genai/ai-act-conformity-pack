"""The deterministic obligation-applicability engine (pure stdlib, replayable).

For each (system, obligation) pair over the Rgc7 obligations graph, this decides APPLIES,
NOT_APPLICABLE or CONDITIONAL with explicit reasons, fail-closed on unknowns, worst-wins across
jurisdictions. The mechanism is the same set-membership reasoning as :mod:`.risk_tier`: an
obligation binds when its framework is one the system is subject to, the system's tier is at or
above the obligation's minimum tier, and the jurisdiction matches; a missing fact needed to
decide yields CONDITIONAL rather than a silent NOT_APPLICABLE.

The LLM plays no part. The matrix is the engine's, cell by cell, and the narrative later restates
it without altering a verdict.
"""

from __future__ import annotations

from .models import (
    RISK_TIER_ORDER as _TIER_ORDER,
)
from .models import (
    Applicability,
    ApplicabilityCell,
    ObligationRef,
    RiskTier,
    TierVerdict,
)

#: The card attribute naming where a system is deployed. Shared with :mod:`.risk_tier`.
_JURISDICTION_ATTR = "jurisdictions"


def _tier_at_or_above(system_tier: RiskTier, min_tier: RiskTier) -> bool:
    """True when ``system_tier`` is at least as strong as ``min_tier`` (index comparison)."""
    return _TIER_ORDER.index(system_tier) >= _TIER_ORDER.index(min_tier)


def assess_cell(
    verdict: TierVerdict,
    obligation: ObligationRef,
    *,
    system_jurisdictions: frozenset[str],
) -> ApplicabilityCell:
    """Decide whether one obligation applies to one system, with reasons.

    Order matters: framework membership first (an obligation from a framework the system is not
    subject to never binds), then the CONDITIONAL cases that a human must resolve, then the tier
    and jurisdiction tests. Worst-wins is expressed by the CONDITIONAL-before-decision ordering:
    an undeclared jurisdiction on a framework-relevant obligation is surfaced, not assumed away.
    """
    reasons: list[str] = []
    citations = (*verdict.citations, *((obligation.citation,) if obligation.citation else ()))

    if obligation.framework not in verdict.applicable_frameworks:
        reasons.append(
            f"framework {obligation.framework} is not one the system is subject to "
            f"(subject to: {', '.join(verdict.applicable_frameworks)})"
        )
        return ApplicabilityCell(
            verdict.system,
            obligation.id,
            obligation.framework,
            Applicability.NOT_APPLICABLE,
            tuple(reasons),
            citations,
        )

    # The system's tier could not be pinned down, so any obligation whose framework reaches it is
    # conditional: we cannot assert it binds, and we must not assert it does not.
    if verdict.conditional:
        reasons.append(
            "the system's risk tier is CONDITIONAL (scopes undeclared), so this obligation's "
            "applicability cannot be decided until the tier is confirmed"
        )
        return ApplicabilityCell(
            verdict.system,
            obligation.id,
            obligation.framework,
            Applicability.CONDITIONAL,
            tuple(reasons),
            citations,
        )

    # A jurisdiction-anchored obligation on a system that declares no jurisdictions at all cannot
    # be decided: fail closed to CONDITIONAL rather than guessing in or out.
    if obligation.jurisdiction and not system_jurisdictions:
        reasons.append(
            f"obligation is anchored to {obligation.jurisdiction} but the system declares no "
            "deployment jurisdictions; a human must confirm where it runs"
        )
        return ApplicabilityCell(
            verdict.system,
            obligation.id,
            obligation.framework,
            Applicability.CONDITIONAL,
            tuple(reasons),
            citations,
        )

    if obligation.jurisdiction and obligation.jurisdiction.upper() not in system_jurisdictions:
        reasons.append(
            f"obligation is anchored to {obligation.jurisdiction}, where the system is not "
            "declared as deployed"
        )
        return ApplicabilityCell(
            verdict.system,
            obligation.id,
            obligation.framework,
            Applicability.NOT_APPLICABLE,
            tuple(reasons),
            citations,
        )

    if not _tier_at_or_above(verdict.tier, obligation.min_tier):
        reasons.append(
            f"obligation binds at tier {obligation.min_tier.value} and above; the system is "
            f"tiered {verdict.tier.value}"
        )
        return ApplicabilityCell(
            verdict.system,
            obligation.id,
            obligation.framework,
            Applicability.NOT_APPLICABLE,
            tuple(reasons),
            citations,
        )

    reasons.append(
        f"framework {obligation.framework} applies, system tier {verdict.tier.value} >= "
        f"{obligation.min_tier.value}"
        + (f", jurisdiction {obligation.jurisdiction} matches" if obligation.jurisdiction else "")
    )
    return ApplicabilityCell(
        verdict.system,
        obligation.id,
        obligation.framework,
        Applicability.APPLIES,
        tuple(reasons),
        citations,
    )


def build_matrix(
    verdict: TierVerdict,
    obligations: tuple[ObligationRef, ...],
    *,
    system_jurisdictions: frozenset[str],
) -> tuple[ApplicabilityCell, ...]:
    """The full applicability row for one system: one cell per obligation, deterministically."""
    return tuple(
        assess_cell(verdict, obligation, system_jurisdictions=system_jurisdictions)
        for obligation in obligations
    )
