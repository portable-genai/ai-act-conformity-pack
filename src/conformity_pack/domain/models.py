"""Vertical artifact models: the AI-Act / FEAT conformity vertical's own types.

The artifacts THIS vertical reasons over, as opposed to the vertical-neutral machinery in
``kernel.py`` (``Severity``, ``Decision``, ``Citation``, ``AuditEvent``). A fork building a
different vertical rewrites this module and leaves ``kernel.py`` untouched.

Everything here is a frozen, slotted, pure-stdlib value object. The consequential DECISIONS
(the risk tier, the obligation-applicability verdict, the evidence-sufficiency verdict) are
computed by the pure engines in :mod:`.risk_tier`, :mod:`.applicability` and
:mod:`.sufficiency`; this module only holds the shapes those engines produce and consume.

``AiSystemInput`` and ``ConformityResult`` are the request and result of the top-level assess
call (:mod:`.conformity_service`). ``ConformityResult`` carries the four fields the R8 review
payload needs (``subject``, ``summary``, ``severity``, ``requires_human_review``, ``citations``)
alongside the rich per-slice detail, so the escalation path the template ships is reused
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hex_service_kit.enums import LenientStrEnum

from .kernel import Citation, Decision, Severity


class RiskTier(LenientStrEnum):
    """The EU AI Act risk tier of a deployed AI system. Ordered weakest to strongest below."""

    MINIMAL = "minimal"  # no specific AI-Act obligations beyond voluntary codes
    LIMITED = "limited"  # transparency obligations only (Art. 50): disclose AI interaction
    HIGH = "high"  # Annex III high-risk use: the full conformity regime (Art. 8-27)
    PROHIBITED = "prohibited"  # Art. 5 banned practice: may not be placed on the market


#: Weakest to strongest. Comparisons use the index, never the string, so a stricter tier always
#: wins a worst-of composition.
RISK_TIER_ORDER: tuple[RiskTier, ...] = (
    RiskTier.MINIMAL,
    RiskTier.LIMITED,
    RiskTier.HIGH,
    RiskTier.PROHIBITED,
)

#: How a risk tier maps onto the vertical-neutral severity band the audit record and the review
#: payload speak. A prohibited practice and a high-risk system are both consequential enough to
#: force human review; the mapping is deliberate and lives in one place.
_TIER_SEVERITY: dict[RiskTier, Severity] = {
    RiskTier.PROHIBITED: Severity.CRITICAL,
    RiskTier.HIGH: Severity.HIGH,
    RiskTier.LIMITED: Severity.MEDIUM,
    RiskTier.MINIMAL: Severity.LOW,
}


def severity_for_tier(tier: RiskTier) -> Severity:
    """The severity band a risk tier maps to (single source of the tier -> band mapping)."""
    return _TIER_SEVERITY[tier]


class Applicability(LenientStrEnum):
    """Whether an obligation applies to a system, over the obligations-control-mapping graph."""

    APPLIES = "applies"  # the framework, jurisdiction and tier all match: the obligation binds
    NOT_APPLICABLE = "not_applicable"  # a declared attribute rules it out
    CONDITIONAL = "conditional"  # an attribute needed to decide is undeclared: a human confirms


class Sufficiency(LenientStrEnum):
    """Whether the harvested evidence answers an applicable obligation."""

    SUFFICIENT = "sufficient"  # every required evidence kind is present
    PARTIAL = "partial"  # some required kinds present, at least one missing
    INSUFFICIENT = "insufficient"  # no required evidence kind present: a named gap


@dataclass(frozen=True, slots=True)
class AiSystemCard:
    """A deployed AI/agent system as read from the agent-registry's ``governance`` block.

    ``scopes`` are the declared use scopes that drive AI-Act classification; ``attributes`` is a
    sorted key/value tuple carrying the additional declared facts the engines read (jurisdiction,
    materiality, oversight, and so on). Undeclared is distinct from empty: a key that is absent
    yields a CONDITIONAL verdict rather than a silent MINIMAL.
    """

    name: str
    description: str = ""
    owner: str = ""
    lifecycle: str = "draft"
    scopes: tuple[str, ...] = ()
    protocols: tuple[str, ...] = ()
    attributes: tuple[tuple[str, str], ...] = ()

    def attr(self, key: str) -> str | None:
        """The declared value for ``key``, or ``None`` when the key is UNDECLARED.

        An empty declared value is returned as ``""`` (declared, but blank); only a missing key
        returns ``None``, so the engines can fail closed on "not declared" without conflating it
        with "declared as nothing".
        """
        for name, value in self.attributes:
            if name == key:
                return value
        return None

    def citation(self) -> Citation:
        """Provenance for a claim derived from this card: the registry row it came from."""
        return Citation(
            source_id=f"hrz3:agent:{self.name}",
            title=f"Registry card: {self.name}",
            snippet=self.description[:80],
        )


@dataclass(frozen=True, slots=True)
class DimensionVerdict:
    """One non-EU framework dimension's read on a system (FEAT, HKMA, APRA, JFSA)."""

    framework: str
    applies: bool
    reason: str


@dataclass(frozen=True, slots=True)
class TierVerdict:
    """The deterministic risk-tier decision plus the reasons and the framework dimensions."""

    system: str
    tier: RiskTier
    conditional: bool
    reasons: tuple[str, ...]
    dimensions: tuple[DimensionVerdict, ...]
    citations: tuple[Citation, ...] = ()

    @property
    def applicable_frameworks(self) -> tuple[str, ...]:
        """Every framework whose obligations can apply to this system (EU always included)."""
        extra = tuple(d.framework for d in self.dimensions if d.applies)
        return ("eu-ai-act", *extra)


@dataclass(frozen=True, slots=True)
class ObligationRef:
    """A thin reference to one obligation over the obligations-control-mapping graph, with its
    classifying attributes.

    The attributes the applicability engine reads: ``framework`` (which regime), ``min_tier``
    (the weakest system tier the obligation binds at), ``jurisdiction`` (or ``""`` for global),
    and ``required_evidence`` (a ``;``-separated list of evidence kinds the sufficiency engine
    checks for). Sourced from the ``obligation-register-kit`` record's ``attributes`` tuple.
    """

    id: str
    title: str
    framework: str
    min_tier: RiskTier
    jurisdiction: str = ""
    required_evidence: tuple[str, ...] = ()
    citation: Citation | None = None


@dataclass(frozen=True, slots=True)
class ApplicabilityCell:
    """One (system, obligation) cell of the applicability matrix."""

    system: str
    obligation_id: str
    framework: str
    applicability: Applicability
    reasons: tuple[str, ...]
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """One harvested evidence artefact (an model-quality-gate eval report, an agent-observability
    trail, and so on).
    """

    id: str
    kind: str
    obligation_ids: tuple[str, ...]
    detail: str = ""
    citation: Citation | None = None


@dataclass(frozen=True, slots=True)
class SufficiencyVerdict:
    """Whether the harvested evidence answers one applicable obligation, with the gap named."""

    obligation_id: str
    sufficiency: Sufficiency
    present_kinds: tuple[str, ...]
    missing_kinds: tuple[str, ...]
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True, slots=True)
class RegChange:
    """One regulatory-corpus movement from the compliance-advisory horizon feed that may reopen a
    verdict.

    A deliberately small mirror of compliance-advisory's ``CorpusChange``: the fields this system
    re-runs
    classification and applicability on. ``frameworks`` and ``scopes`` name what the change
    touches, so only the affected systems and cells are recomputed.
    """

    id: str
    title: str
    frameworks: tuple[str, ...]
    scopes: tuple[str, ...] = ()
    detail: str = ""
    citation: Citation | None = None


@dataclass(frozen=True, slots=True)
class AiSystemInput:
    """The request to assess one AI system for conformity: the system name to resolve.

    The card is resolved from the registry port at assess time rather than carried inline, so
    the caller cannot smuggle a different declaration past the registry the classification is
    supposed to be grounded in.
    """

    system: str


@dataclass(frozen=True, slots=True)
class ConformityResult:
    """The conformity verdict for one AI system: tier, matrix, sufficiency, narrative, routing.

    The first block is the R8 payload contract shared with the template's review path;
    everything after it is the vertical detail. The consequential fields (``tier``,
    ``applicability``, ``sufficiency``, ``requires_human_review``) come from the pure engines;
    ``narrative`` is the model's non-consequential phrasing and never carries a figure the
    engines did not compute.
    """

    subject: str
    severity: Severity
    decision: Decision
    summary: str
    requires_human_review: bool
    citations: tuple[Citation, ...] = ()
    tier: RiskTier = RiskTier.MINIMAL
    conditional: bool = False
    tier_reasons: tuple[str, ...] = ()
    dimensions: tuple[DimensionVerdict, ...] = ()
    applicability: tuple[ApplicabilityCell, ...] = ()
    sufficiency: tuple[SufficiencyVerdict, ...] = ()
    gaps: tuple[str, ...] = ()
    narrative: str = ""

    @property
    def applies_count(self) -> int:
        """How many obligations bind on this system (APPLIES cells)."""
        return sum(1 for c in self.applicability if c.applicability is Applicability.APPLIES)

    @property
    def conditional_count(self) -> int:
        """How many cells could not be decided without a human confirming a declaration."""
        return sum(1 for c in self.applicability if c.applicability is Applicability.CONDITIONAL)


@dataclass(frozen=True, slots=True)
class ConformityPack:
    """A conformity pack for the whole fleet: one result per system plus the fleet-level roll-up.

    Assembled by :mod:`.conformity_service`; rendered by the demo surface and the UI. ``as_of``
    is supplied by the caller (the domain never reads a clock), so a pack is replayable.
    """

    as_of: str
    results: tuple[ConformityResult, ...] = field(default_factory=tuple)

    @property
    def high_risk_systems(self) -> tuple[str, ...]:
        """Every system the engine tiered at HIGH or PROHIBITED (the conformity-regime set)."""
        strong = (RiskTier.HIGH, RiskTier.PROHIBITED)
        return tuple(r.subject for r in self.results if r.tier in strong)

    @property
    def systems_needing_review(self) -> tuple[str, ...]:
        """Every system whose result routed to a human reviewer under rule R8."""
        return tuple(r.subject for r in self.results if r.requires_human_review)
