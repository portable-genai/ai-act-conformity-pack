"""The conformity assessment service: pure engines orchestrated, model narrates, R8 escalation.

This is the top-level assess call. The consequential work, the risk tier, the applicability matrix
and the evidence sufficiency, is done by the PURE engines (:mod:`.risk_tier`, :mod:`.applicability`,
:mod:`.sufficiency`); the model only PHRASES the result, behind the narrator port, schema-validated
and discarded on failure. Every result carries citations, PII is redacted BEFORE the audit write,
and a consequential result (a high-risk or prohibited classification, an undecided cell, or a named
evidence gap on a system asserting conformity) sets ``requires_human_review`` so the surface routes
it to human-review-console under rule R8. It never auto-executes.

Determinism is the invariant: with the narrator adapter stubbed the pack's figures are identical,
because the figures never came from the model. :meth:`assess` is replayable given the same
``as_of`` and the same port fixtures.
"""

from __future__ import annotations

from pii_kit import redact

from ..ports.audit import AuditSinkPort
from ..ports.evidence import EvidencePort
from ..ports.matrix_store import MatrixStorePort
from ..ports.narrator import NarratorPort
from ..ports.obligations import ObligationsPort
from ..ports.observability import ObservabilityTracerPort
from ..ports.registry import RegistryPort
from ..ports.retrieval import RetrievalPort
from . import applicability as applicability_engine
from . import risk_tier as risk_tier_engine
from . import sufficiency as sufficiency_engine
from .errors import ConformityError, EmptyRetrievalError, UngroundedNarrativeError
from .kernel import AuditEvent, Citation, Decision, utcnow
from .models import (
    AiSystemCard,
    AiSystemInput,
    Applicability,
    ApplicabilityCell,
    ConformityResult,
    RiskTier,
    Sufficiency,
    SufficiencyVerdict,
    TierVerdict,
    severity_for_tier,
)
from .packs import DEFAULT_PACK
from .pii import PII_PATTERNS
from .prompts import (
    NarrationContext,
    build_prompt,
    deterministic_narrative,
    validate_narration,
)

#: Tiers whose classification is consequential enough to force human review on its own.
_ESCALATING_TIERS = (RiskTier.HIGH, RiskTier.PROHIBITED)

#: One span per assessment. Structural attributes only: see :meth:`ConformityService.assess`.
_ASSESS_SPAN = "conformity.assess"


class ConformityService:
    """Assess one AI system for conformity, end to end, deterministically."""

    def __init__(
        self,
        *,
        audit: AuditSinkPort,
        registry: RegistryPort,
        obligations: ObligationsPort,
        evidence: EvidencePort,
        retrieval: RetrievalPort,
        narrator: NarratorPort,
        tracer: ObservabilityTracerPort,
        matrix_store: MatrixStorePort | None = None,
        pack_name: str = DEFAULT_PACK,
    ) -> None:
        self._audit = audit
        self._registry = registry
        self._obligations = obligations
        self._evidence = evidence
        self._retrieval = retrieval
        self._narrator = narrator
        self._tracer = tracer
        self._matrix_store = matrix_store
        self._pack_name = pack_name

    def assess(
        self, request: AiSystemInput, *, actor: str, tenant: str, as_of: str = ""
    ) -> ConformityResult:
        """Classify, map obligations, score evidence, narrate, and set the R8 flag.

        ``actor`` and ``tenant`` are both the VERIFIED principal's, never a client-supplied
        field: the request schema carries neither. ``tenant`` is keyword-only and has no default
        on purpose. A default would be the empty string, and the empty string is the shared
        partition every unscoped caller collides in, so a new surface that forgot the tenant
        would compile, run, and quietly store its lineage where another tenant reads it.

        The whole path runs inside one span. Its attributes are STRUCTURAL only, never the
        system name, a card description, a tier reason or any narrative text: a trace backend
        is not the WORM audit trail. It has no redaction stage, a wider read audience and no
        retention rule written against a regulator's requirement, so anything content-shaped
        that reaches a span has left the boundary the ``redact`` call exists to hold, silently.
        """
        with self._tracer.span(
            _ASSESS_SPAN,
            action="assess",
            actor=actor,
            pack=self._pack_name,
        ):
            card = self._registry.get(request.system)
            if card is None:
                raise ConformityError(
                    f"system {request.system!r} is not in the registry; nothing to assess"
                )

            verdict = risk_tier_engine.classify(card, pack_name=self._pack_name)
            obligations = self._obligations.obligations()
            obligations_by_id = {o.id: o for o in obligations}
            jurisdictions = _declared_jurisdictions(card)
            cells = applicability_engine.build_matrix(
                verdict, obligations, system_jurisdictions=jurisdictions
            )
            evidence = self._evidence.harvest(card.name)
            sufficiency = sufficiency_engine.assess_sufficiency(cells, obligations_by_id, evidence)
            gaps = _named_gaps(cells, sufficiency)

            requires_review = (
                verdict.tier in _ESCALATING_TIERS
                or verdict.conditional
                or any(c.applicability is Applicability.CONDITIONAL for c in cells)
                or bool(gaps)
            )

            citations = _collect_citations(verdict, cells, sufficiency)
            grounding = self._ground(verdict)
            narrative = self._narrate(verdict, cells, gaps, citations, grounding)

            summary = (
                f"{card.name}: {verdict.tier.value}-risk, "
                f"{_applies_count(cells)} obligation(s) apply, {len(gaps)} evidence gap(s)"
            )
            decision = Decision.ESCALATED if requires_review else Decision.ALLOWED

            # Redact BEFORE the audit write. The masking below is belt to the kernel's braces:
            # `AuditEvent.__post_init__` masks the summary AND every citation field, so the WORM
            # boundary holds for every caller rather than for the ones that remembered. This call
            # stays because redaction is idempotent and the intent is worth reading at the write.
            self._audit.record(
                AuditEvent(
                    action="conformity_assess",
                    actor=actor,
                    decision=decision,
                    severity=severity_for_tier(verdict.tier),
                    redacted_summary=redact(f"{summary} :: {narrative}", PII_PATTERNS),
                    citations=citations,
                    timestamp=utcnow(),
                )
            )

            # The persisted matrix is TENANT-partitioned lineage, so the tenant goes to the store
            # rather than being implied by whoever happens to read it back. An empty tenant is
            # refused inside the adapter (`ports/matrix_store.require_tenant`), not defaulted:
            # see TenantScopeError.
            if self._matrix_store is not None and as_of:
                self._matrix_store.put(tenant, as_of, cells)

            return ConformityResult(
                subject=card.name,
                severity=severity_for_tier(verdict.tier),
                decision=decision,
                summary=summary,
                requires_human_review=requires_review,
                citations=citations,
                tier=verdict.tier,
                conditional=verdict.conditional,
                tier_reasons=verdict.reasons,
                dimensions=verdict.dimensions,
                applicability=cells,
                sufficiency=sufficiency,
                gaps=gaps,
                narrative=narrative,
            )

    # ------------------------------------------------------------------ grounding + narration
    def _ground(self, verdict: TierVerdict) -> tuple[Citation, ...]:
        """Retrieve the rule text the narrative may cite; empty retrieval is a hard error (P-05).

        The query always carries the tier token, and the fixture / File Search KB always answers
        a tier token, so a genuinely empty result means the KB is misconfigured, not that the
        system is out of scope, and inventing a narrative over nothing is exactly what P-05
        forbids.
        """
        query = " ".join((verdict.tier.value, *verdict.applicable_frameworks))
        grounding = self._retrieval.search(query)
        if not grounding:
            raise EmptyRetrievalError(
                f"the knowledge base returned nothing for {query!r}; a grounded narrative cannot "
                "be drafted over an empty retrieval (P-05)"
            )
        return grounding

    def _narrate(
        self,
        verdict: TierVerdict,
        cells: tuple[ApplicabilityCell, ...],
        gaps: tuple[str, ...],
        citations: tuple[Citation, ...],
        grounding: tuple[Citation, ...],
    ) -> str:
        """Phrase the narrative via the model, validated; fall back to the grounded template.

        The model output is validated against the engine's closed sets and DISCARDED on failure,
        so a hallucinated figure never survives. The fallback is built purely from engine facts,
        which is also why swapping the narrator cannot change a consequential number.
        """
        interim = ConformityResult(
            subject=verdict.system,
            severity=severity_for_tier(verdict.tier),
            decision=Decision.ALLOWED,
            summary="",
            requires_human_review=False,
            citations=citations,
            tier=verdict.tier,
            conditional=verdict.conditional,
            applicability=cells,
            gaps=gaps,
        )
        grounding_sources = frozenset(c.source_id for c in grounding)
        context = NarrationContext.from_result(interim, grounding_sources)
        prompt = build_prompt(context, tuple(c.snippet for c in grounding if c.snippet))
        try:
            reply = self._narrator.narrate(prompt)
            return validate_narration(reply, context)
        except (UngroundedNarrativeError, NotImplementedError, RuntimeError, ValueError):
            # A failed, unreachable or unimplemented narrator never blocks a pack: the grounded
            # deterministic narrative stands in, and it carries only engine figures.
            return deterministic_narrative(interim)


# --------------------------------------------------------------------------- helpers (pure)
def _declared_jurisdictions(card: AiSystemCard) -> frozenset[str]:
    raw = card.attr("jurisdictions")
    if raw is None:
        return frozenset()
    return frozenset(part.strip().upper() for part in raw.split(";") if part.strip())


def _applies_count(cells: tuple[ApplicabilityCell, ...]) -> int:
    return sum(1 for c in cells if c.applicability is Applicability.APPLIES)


def _named_gaps(
    cells: tuple[ApplicabilityCell, ...],
    sufficiency: tuple[SufficiencyVerdict, ...],
) -> tuple[str, ...]:
    """Every named gap: an unmet evidence requirement, or an undecided applicability cell."""
    gaps: list[str] = []
    for verdict in sufficiency:
        if verdict.sufficiency is not Sufficiency.SUFFICIENT:
            missing = ", ".join(verdict.missing_kinds) or "all required evidence"
            gaps.append(f"{verdict.obligation_id}: {verdict.sufficiency.value} (missing {missing})")
    for cell in cells:
        if cell.applicability is Applicability.CONDITIONAL:
            gaps.append(f"{cell.obligation_id}: applicability CONDITIONAL, awaiting confirmation")
    return tuple(gaps)


def _collect_citations(
    verdict: TierVerdict,
    cells: tuple[ApplicabilityCell, ...],
    sufficiency: tuple[SufficiencyVerdict, ...],
) -> tuple[Citation, ...]:
    """Every provenance behind the result, deduplicated by source id, deterministically ordered."""
    seen: dict[str, Citation] = {}
    for citation in verdict.citations:
        seen.setdefault(citation.source_id, citation)
    for cell in cells:
        if cell.applicability is Applicability.APPLIES:
            for citation in cell.citations:
                seen.setdefault(citation.source_id, citation)
    for verdict_s in sufficiency:
        for citation in verdict_s.citations:
            seen.setdefault(citation.source_id, citation)
    return tuple(seen[key] for key in sorted(seen))
