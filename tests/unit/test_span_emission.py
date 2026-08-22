"""Assessing a system opens ONE span, and that span carries no content.

A trace backend is not the WORM audit trail. It has no redaction stage, no retention policy
written against a regulator's requirement, and a far wider read audience than the audit store.
So the value of tracing the assessment path depends entirely on the span carrying structural
attributes only: which action, whose, which pack. A system name, a card description, a tier
reason or a narrative fragment reaching a span has left the boundary the service's ``redact``
call exists to hold, and it has left it silently.

The content case drives the system whose registry card description carries a planted NRIC, so
the check runs against input that would actually leak if any attribute were content-shaped.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from conformity_pack.config import build_container
from conformity_pack.domain.conformity_service import ConformityService
from conformity_pack.domain.models import AiSystemInput, ConformityResult

from tests.conftest import local_settings
from tests.fixtures import sample_cases

#: Every attribute key the assess span is allowed to carry. A verdict that started explaining
#: itself on the span (a tier reason, a gap, the system name) would widen this set, which is
#: the point of asserting on the set rather than on the individual keys.
_ASSESS_KEYS = {"action", "actor", "pack"}


class _RecordingTracer:
    """Captures every span name and attribute so the test can inspect what was emitted."""

    def __init__(self) -> None:
        self.spans: list[tuple[str, dict[str, str]]] = []

    @contextmanager
    def span(self, name: str, **attributes: str) -> Iterator[None]:
        self.spans.append((name, dict(attributes)))
        yield

    def record_token_usage(self, usage: object, model: str) -> None:
        return None


def _assess(case: AiSystemInput) -> tuple[_RecordingTracer, ConformityResult]:
    """The REAL local adapters, exactly as ``tests.conftest.build_conformity_service`` wires."""
    container = build_container(local_settings())
    tracer = _RecordingTracer()
    service = ConformityService(
        audit=container.audit,
        registry=container.registry,
        obligations=container.obligations,
        evidence=container.evidence,
        retrieval=container.retrieval,
        narrator=container.narrator,
        tracer=tracer,  # type: ignore[arg-type]
        matrix_store=container.matrix_store,
    )
    result = service.assess(case, actor=sample_cases.ACTOR, tenant=sample_cases.TENANT)
    return tracer, result


def _emitted(tracer: _RecordingTracer) -> str:
    """Every attribute VALUE that was emitted, and every KEY, as one searchable blob."""
    parts: list[str] = []
    for name, attributes in tracer.spans:
        parts.append(name)
        parts.extend(attributes)
        parts.extend(attributes.values())
    return " ".join(parts)


def test_assessing_a_system_opens_exactly_one_named_span() -> None:
    tracer, _ = _assess(sample_cases.ROUTINE_CASE)
    assert [name for name, _ in tracer.spans] == ["conformity.assess"]


def test_the_span_carries_the_structural_attributes_an_operator_needs() -> None:
    """Enough to answer "whose assessment is slow, on which pack", and nothing more."""
    tracer, _ = _assess(sample_cases.ROUTINE_CASE)
    _, attributes = tracer.spans[0]
    assert attributes["action"] == "assess"
    assert attributes["actor"] == sample_cases.ACTOR
    assert attributes["pack"] == "eu-ai-act"


@pytest.mark.parametrize(
    "case",
    [sample_cases.ROUTINE_CASE, sample_cases.ESCALATING_CASE, sample_cases.PII_CASE],
    ids=["routine", "escalating", "pii"],
)
def test_the_attribute_set_is_a_fixed_allowlist_whatever_the_tier(case: AiSystemInput) -> None:
    """A high-risk verdict must not start attaching its reasons, or the system, to the span."""
    tracer, _ = _assess(case)
    for _, attributes in tracer.spans:
        assert set(attributes) == _ASSESS_KEYS


def test_no_span_attribute_carries_card_content_or_the_planted_identifier() -> None:
    """The system used here has an NRIC planted in its card description, so a leak would show."""
    tracer, result = _assess(sample_cases.PII_CASE)
    emitted = _emitted(tracer)

    forbidden = [
        sample_cases.PLANTED_NRIC,
        sample_cases.PII_SYSTEM,
        "Gamma LLP",
        result.subject,
        result.summary,
        result.narrative,
        *result.tier_reasons,
        *result.gaps,
    ]
    for literal in forbidden:
        assert literal, "an empty needle would pass this test for the wrong reason"
        assert literal not in emitted, f"a span attribute carried {literal!r}"
        assert literal.lower() not in emitted.lower(), f"a span attribute carried {literal!r}"


def test_every_emitted_attribute_value_is_a_string_the_port_declares() -> None:
    """``span(name, **attributes: str)``: a non-string would serialise however the SDK felt."""
    tracer, _ = _assess(sample_cases.ESCALATING_CASE)
    values: list[Any] = [v for _, attributes in tracer.spans for v in attributes.values()]
    assert values
    assert all(isinstance(value, str) for value in values)
