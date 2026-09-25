"""API request/response schemas (Pydantic) mapped to/from the pure-domain models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..domain.models import ApplicabilityCell, ConformityResult, SufficiencyVerdict


class AssessRequest(BaseModel):
    """Assess one deployed AI system, resolved by name from the registry."""

    system: str
    #: Optional replay date stamped on the persisted matrix. The domain never reads a clock.
    as_of: str = ""


class CitationModel(BaseModel):
    source_id: str
    title: str
    snippet: str = ""


class ApplicabilityModel(BaseModel):
    obligation_id: str
    framework: str
    applicability: str
    reasons: list[str] = []

    @classmethod
    def from_domain(cls, cell: ApplicabilityCell) -> ApplicabilityModel:
        return cls(
            obligation_id=cell.obligation_id,
            framework=cell.framework,
            applicability=cell.applicability.value,
            reasons=list(cell.reasons),
        )


class SufficiencyModel(BaseModel):
    obligation_id: str
    sufficiency: str
    present_kinds: list[str] = []
    missing_kinds: list[str] = []

    @classmethod
    def from_domain(cls, verdict: SufficiencyVerdict) -> SufficiencyModel:
        return cls(
            obligation_id=verdict.obligation_id,
            sufficiency=verdict.sufficiency.value,
            present_kinds=list(verdict.present_kinds),
            missing_kinds=list(verdict.missing_kinds),
        )


class AssessResponse(BaseModel):
    """The conformity verdict for one system: the deterministic tier and matrix, plus routing."""

    subject: str
    tier: str
    severity: str
    decision: str
    summary: str
    narrative: str
    requires_human_review: bool
    #: Where the escalation WENT (rule R8): the human-review-console review id, or the local queue
    #: reference. Empty exactly when ``review_routing`` is not ``routed``.
    review_ref: str = ""
    #: What happened to the hand-off: routed, failed, off or not_required. ``failed`` means the
    #: result is NOT queued for review, and the console says so.
    review_routing: Literal["routed", "failed", "off", "not_required"] = "not_required"
    applicability: list[ApplicabilityModel] = []
    sufficiency: list[SufficiencyModel] = []
    gaps: list[str] = []
    citations: list[CitationModel] = []

    @classmethod
    def from_domain(
        cls,
        result: ConformityResult,
        *,
        review_ref: str = "",
        review_routing: str = "not_required",
    ) -> AssessResponse:
        return cls(
            subject=result.subject,
            tier=result.tier.value,
            severity=result.severity.value,
            decision=result.decision.value,
            summary=result.summary,
            narrative=result.narrative,
            requires_human_review=result.requires_human_review,
            review_ref=review_ref,
            review_routing=review_routing,  # type: ignore[arg-type]
            applicability=[ApplicabilityModel.from_domain(c) for c in result.applicability],
            sufficiency=[SufficiencyModel.from_domain(s) for s in result.sufficiency],
            gaps=list(result.gaps),
            citations=[
                CitationModel(source_id=c.source_id, title=c.title, snippet=c.snippet)
                for c in result.citations
            ],
        )


class HealthResponse(BaseModel):
    status: str
    profile: str
    region: str
    #: What the UI's model pill states before any answer (then it shows ``X-Answered-By``):
    #: where the runtime sits and which model the bound generator calls. Both are read off the
    #: service because the browser cannot know either.
    runtime: str = "local"  # "gcp" | "local"
    generator_model: str = "deterministic-offline-stub"
