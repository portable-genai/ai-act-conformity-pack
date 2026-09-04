"""Packs-as-data: the classification rule packs, looked up by name (the model-quality-gate bundle
mechanism).

This mirrors model-quality-gate's ``METRIC_BUNDLES`` shape (per-bundle bars looked up by name in
``model_quality_gate/domain/thresholds.py``): the rules are DATA, not code, so a bank can
carry its own pack in ``config/settings.yaml`` without a code edit, and the engine is the same
for every pack.

Two families live here:

* :data:`RISK_TIER_PACKS` : per named pack, the set-membership rules that classify a system's
  declared use scopes into an EU AI Act tier, plus the framework-dimension scope sets that drive
  FEAT / HKMA / APRA / JFSA applicability.
* The default pack ``"eu-ai-act"`` IS the reference policy. Its numbers and sets are the
  client's to override (practices check B4: bank-owned policy in config, never in code).

Everything here is a frozen mapping of ``frozenset``s: pure stdlib, no I/O, deterministic.
Synthetic taxonomies only; the scope vocabulary is illustrative, not a legal enumeration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .errors import UnknownPackError
from .models import RiskTier


@dataclass(frozen=True, slots=True)
class RiskTierPack:
    """One named classification pack: the scope sets for each tier and each framework dimension.

    Evaluated strongest-first (prohibited, then high, then limited), so a scope that appears in
    two sets takes the stronger tier: classification fails closed toward the higher tier.
    """

    prohibited_scopes: frozenset[str]
    high_risk_scopes: frozenset[str]
    limited_scopes: frozenset[str]
    #: framework key -> the scope set whose presence makes that framework's obligations apply.
    framework_scopes: dict[str, frozenset[str]] = field(default_factory=dict)
    #: framework key -> the jurisdiction code that framework is anchored to (or "" for global).
    framework_jurisdictions: dict[str, str] = field(default_factory=dict)

    def tier_for(self, scopes: frozenset[str]) -> tuple[RiskTier, tuple[str, ...]]:
        """Classify a scope set strongest-first, returning the tier and the matched reasons."""
        hits_prohibited = scopes & self.prohibited_scopes
        if hits_prohibited:
            return RiskTier.PROHIBITED, tuple(sorted(hits_prohibited))
        hits_high = scopes & self.high_risk_scopes
        if hits_high:
            return RiskTier.HIGH, tuple(sorted(hits_high))
        hits_limited = scopes & self.limited_scopes
        if hits_limited:
            return RiskTier.LIMITED, tuple(sorted(hits_limited))
        return RiskTier.MINIMAL, ()


#: The reference EU AI Act pack plus the APAC framework dimensions. Synthetic scope vocabulary.
_EU_PACK = RiskTierPack(
    prohibited_scopes=frozenset(
        {
            "social-scoring",
            "subliminal-manipulation",
            "biometric-categorisation-sensitive",
            "emotion-recognition-workplace",
            "predictive-policing-profiling",
            "untargeted-face-scraping",
        }
    ),
    high_risk_scopes=frozenset(
        {
            "credit-scoring",
            "creditworthiness-assessment",
            "insurance-risk-pricing",
            "biometric-identification",
            "employment-screening",
            "essential-private-services",
            "essential-public-services",
            "critical-infrastructure-safety",
            "aml-transaction-monitoring",
        }
    ),
    limited_scopes=frozenset(
        {
            "chatbot",
            "content-generation",
            "deepfake-generation",
            "emotion-recognition",
            "customer-facing-assistant",
        }
    ),
    framework_scopes={
        # MAS FEAT / Veritas: customer-facing or credit/insurance decisioning in Singapore.
        "feat": frozenset(
            {
                "credit-scoring",
                "creditworthiness-assessment",
                "insurance-risk-pricing",
                "customer-facing-assistant",
                "aml-transaction-monitoring",
            }
        ),
        # HKMA AI guidance: consumer-impacting analytics in Hong Kong.
        "hkma": frozenset(
            {
                "credit-scoring",
                "creditworthiness-assessment",
                "customer-facing-assistant",
                "aml-transaction-monitoring",
            }
        ),
        # APRA CPS 230/234: material operational or security-relevant systems in Australia.
        "apra": frozenset(
            {
                "critical-infrastructure-safety",
                "essential-private-services",
                "aml-transaction-monitoring",
                "biometric-identification",
            }
        ),
        # JFSA / Japan AI framework: customer-facing or credit decisioning in Japan.
        "jfsa": frozenset(
            {
                "credit-scoring",
                "creditworthiness-assessment",
                "customer-facing-assistant",
            }
        ),
    },
    framework_jurisdictions={"feat": "SG", "hkma": "HK", "apra": "AU", "jfsa": "JP"},
)


#: Named packs, looked up by name exactly like model-quality-gate's ``METRIC_BUNDLES``. A deployment
#: selects a
#: pack by name in ``config/settings.yaml``; an unknown name is a configuration error, not a
#: silent fallback (:func:`risk_tier_pack`).
RISK_TIER_PACKS: dict[str, RiskTierPack] = {
    "eu-ai-act": _EU_PACK,
}

#: The pack the engine uses when a deployment names none.
DEFAULT_PACK = "eu-ai-act"


def risk_tier_pack(name: str = DEFAULT_PACK) -> RiskTierPack:
    """The named classification pack, or a hard error naming what is available.

    A missing pack fails closed with :class:`UnknownPackError` rather than silently binding the
    default: a deployment that named a pack meant it, and running on a different one is exactly
    the silent-downgrade the three-state config discipline exists to prevent.
    """
    try:
        return RISK_TIER_PACKS[name]
    except KeyError as exc:
        raise UnknownPackError(
            f"risk-tier pack {name!r} is not defined; available packs: "
            f"{', '.join(sorted(RISK_TIER_PACKS))}"
        ) from exc
