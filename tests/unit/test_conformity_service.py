"""The conformity service end to end: determinism, R8 flag, narration, grounding, redaction."""

from __future__ import annotations

import pytest

from conformity_pack.config import build_container
from conformity_pack.domain.conformity_service import ConformityService
from conformity_pack.domain.errors import (
    ConformityError,
    EmptyRetrievalError,
    UngroundedNarrativeError,
)
from conformity_pack.domain.kernel import Citation, Decision
from conformity_pack.domain.models import AiSystemInput, RiskTier
from conformity_pack.domain.prompts import NarrationContext, validate_narration

from tests.conftest import build_conformity_service, local_settings
from tests.fixtures import sample_cases


def _service() -> ConformityService:
    return build_conformity_service(build_container(local_settings()))


def test_a_high_risk_system_escalates_and_is_cited() -> None:
    result = _service().assess(
        sample_cases.ESCALATING_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )
    assert result.tier is RiskTier.HIGH
    assert result.requires_human_review is True
    assert result.decision is Decision.ESCALATED
    assert result.citations, "a consequential result must carry provenance"
    assert result.applies_count >= 1


def test_a_minimal_system_does_not_escalate() -> None:
    result = _service().assess(
        sample_cases.ROUTINE_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )
    assert result.tier is RiskTier.MINIMAL
    assert result.requires_human_review is False
    assert result.gaps == ()


def test_an_undeclared_system_is_conditional_and_escalates() -> None:
    result = _service().assess(
        AiSystemInput(system="undeclared-analytics"),
        actor=sample_cases.ACTOR,
        tenant=sample_cases.TENANT,
    )
    assert result.conditional is True
    assert result.requires_human_review is True


def test_an_unknown_system_raises() -> None:
    with pytest.raises(ConformityError):
        _service().assess(
            AiSystemInput(system="no-such-system"),
            actor=sample_cases.ACTOR,
            tenant=sample_cases.TENANT,
        )


def test_the_assessment_is_replayable_and_deterministic() -> None:
    first = _service().assess(
        sample_cases.ESCALATING_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )
    second = _service().assess(
        sample_cases.ESCALATING_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )
    assert (first.tier, first.applies_count, first.gaps) == (
        second.tier,
        second.applies_count,
        second.gaps,
    )


class _AdversarialNarrator:
    """A narrator that tries to smuggle a fabricated figure past the schema validator."""

    def narrate(self, prompt: str) -> str:
        return '{"narrative": "tier is minimal", "figures": ["minimal"], "sources": []}'


def test_a_hallucinated_figure_never_changes_a_consequential_field() -> None:
    """With a lying narrator, the tier and matrix are IDENTICAL: the model never produced them."""
    container = build_container(local_settings())
    honest = build_conformity_service(container)
    lying = ConformityService(
        audit=container.audit,
        registry=container.registry,
        obligations=container.obligations,
        evidence=container.evidence,
        retrieval=container.retrieval,
        narrator=_AdversarialNarrator(),
        tracer=container.tracer,
    )
    a = honest.assess(
        sample_cases.ESCALATING_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )
    b = lying.assess(
        sample_cases.ESCALATING_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
    )
    assert (a.tier, a.applies_count, a.conditional_count, a.gaps) == (
        b.tier,
        b.applies_count,
        b.conditional_count,
        b.gaps,
    )


def test_validate_narration_rejects_a_figure_the_engine_never_produced() -> None:
    context = NarrationContext(
        system="s",
        tier="high",
        conditional=False,
        applies_count=3,
        conditional_count=0,
        gaps=(),
        allowed_figures=frozenset({"high", "3", "0"}),
        allowed_sources=frozenset(),
    )
    with pytest.raises(UngroundedNarrativeError):
        validate_narration('{"narrative": "x", "figures": ["99"], "sources": []}', context)


class _EmptyRetrieval:
    def search(self, query: str) -> tuple[Citation, ...]:
        return ()


def test_an_empty_retrieval_is_a_hard_error_not_an_invented_narrative() -> None:
    """P-05: a grounded narrative cannot be drafted over nothing."""
    container = build_container(local_settings())
    service = ConformityService(
        audit=container.audit,
        registry=container.registry,
        obligations=container.obligations,
        evidence=container.evidence,
        retrieval=_EmptyRetrieval(),
        narrator=container.narrator,
        tracer=container.tracer,
    )
    with pytest.raises(EmptyRetrievalError):
        service.assess(
            sample_cases.ESCALATING_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT
        )


def test_the_audit_summary_is_redacted_before_it_is_written() -> None:
    container = build_container(local_settings())
    service = build_conformity_service(container)
    service.assess(sample_cases.PII_CASE, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT)
    records = container.audit.log.read_all()
    joined = " ".join(str(r.get("redacted_summary", "")) for r in records)
    assert sample_cases.PLANTED_NRIC not in joined
