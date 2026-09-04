"""The deterministic EU AI Act risk-tier engine (pure stdlib, replayable).

This is the reason the classification can be put in front of a regulator: the tier is PURE CODE over
a system's DECLARED card attributes, using set-membership rule packs (:mod:`.packs`), in the
mechanism of compliance-advisory's ``HorizonPolicy.assess_applicability`` (a verdict plus explicit
reasons). The LLM never classifies; it only narrates a decision this module has already made.

Two invariants this module encodes:

* **CONDITIONAL, never silently minimal.** A system that declares no use scopes cannot be ruled
  out of the high-risk regime, so it is tiered CONDITIONAL for a human to confirm, not assumed
  MINIMAL. An adversarial under-declared card therefore cannot slip out of scope by omission.
* **Fail closed toward the higher tier.** :meth:`RiskTierPack.tier_for` evaluates strongest
  first, so a scope that could read two ways takes the stronger tier.

The framework dimensions (FEAT / HKMA / APRA / JFSA) are computed the same way: set membership of
the declared scopes against each framework's scope set, gated on the declared deployment
jurisdiction where the framework is jurisdiction-anchored.
"""

from __future__ import annotations

from .models import (
    AiSystemCard,
    DimensionVerdict,
    TierVerdict,
)
from .packs import DEFAULT_PACK, RiskTierPack, risk_tier_pack

#: The card attribute naming where a system is deployed (a ``;``-separated set of ISO codes, or
#: ``GLOBAL``). Read for the jurisdiction-anchored framework dimensions.
_JURISDICTION_ATTR = "jurisdictions"


def _declared_jurisdictions(card: AiSystemCard) -> frozenset[str]:
    raw = card.attr(_JURISDICTION_ATTR)
    if raw is None:
        return frozenset()
    return frozenset(part.strip().upper() for part in raw.split(";") if part.strip())


def _dimension(
    framework: str,
    scopes: frozenset[str],
    declared_jurisdictions: frozenset[str],
    pack: RiskTierPack,
) -> DimensionVerdict:
    """Compute one framework dimension: does this framework's regime reach the system?"""
    framework_scopes = pack.framework_scopes.get(framework, frozenset())
    matched = scopes & framework_scopes
    anchor = pack.framework_jurisdictions.get(framework, "")
    if not matched:
        return DimensionVerdict(framework, False, "no in-scope use for this framework")
    if anchor and anchor not in declared_jurisdictions:
        # The use is in scope but the system is not declared as deployed in this jurisdiction, so
        # this framework's obligations do not bind here.
        return DimensionVerdict(
            framework,
            False,
            f"in-scope use ({', '.join(sorted(matched))}) but not deployed in {anchor}",
        )
    return DimensionVerdict(
        framework, True, f"in-scope use in {anchor or 'all markets'}: {', '.join(sorted(matched))}"
    )


def classify(card: AiSystemCard, *, pack_name: str = DEFAULT_PACK) -> TierVerdict:
    """Classify one system's card into a risk tier plus the framework dimensions.

    Deterministic and replayable: the same card and pack always produce the same verdict. The
    reasons record every matched rule so a reviewer can trace the tier back to the declared
    scopes it rested on.
    """
    pack = risk_tier_pack(pack_name)
    scopes = frozenset(s.strip() for s in card.scopes if s.strip())
    reasons: list[str] = []

    conditional = not scopes
    if conditional:
        reasons.append(
            "no use scopes are declared on the registry card, so the system cannot be ruled out "
            "of the high-risk regime; a human must confirm the scope before a tier is relied on"
        )

    tier, matched = pack.tier_for(scopes)
    if matched:
        reasons.append(f"tier {tier.value}: matched scope(s) {', '.join(matched)}")
    elif scopes:
        reasons.append(
            "tier minimal: no declared scope matches a prohibited, high-risk or "
            "transparency-obligated use"
        )

    declared_jurisdictions = _declared_jurisdictions(card)
    dimensions = tuple(
        _dimension(framework, scopes, declared_jurisdictions, pack)
        for framework in sorted(pack.framework_scopes)
    )

    return TierVerdict(
        system=card.name,
        tier=tier,
        conditional=conditional,
        reasons=tuple(reasons),
        dimensions=dimensions,
        citations=(card.citation(),),
    )
