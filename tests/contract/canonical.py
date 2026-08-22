"""ONE canonical request per port, shared by the structural and behavioural contract suites.

Parity means the same request through every implementation, so the request needs a single home.
Retyping it per suite is how two "parity" tests end up asserting different things.

Each :class:`PortCase` answers three questions about one port:

* ``invoke``   : what a single canonical call to this port looks like;
* ``answered`` : what it means for the OFFLINE family to have actually answered (a port that
  returns ``None`` and records nothing has not answered, it has merely not raised);
* ``managed_refusal`` : what the MANAGED family must do when called with no cloud reachable.
  Never a silent success: either it refuses because it is unconfigured, or its lazy SDK import
  fails. Both are honest; returning as if the work happened is not.

Adding a port means adding a case here. ``test_port_parity.py`` fails the build if this table and
the port map ever disagree, so the touch list in ``CONTRIBUTING.md`` is enforced.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agent_eval_kit import EvalReport
from hex_service_kit.identity import IdentityError, Principal, RequestContext
from hex_service_kit.observability import TokenUsage

from conformity_pack.domain.kernel import (
    AuditEvent,
    Citation,
    Decision,
    Severity,
)
from conformity_pack.domain.models import (
    Applicability,
    ApplicabilityCell,
    ConformityResult,
    RiskTier,
)

from tests.fixtures import sample_cases

#: The audit record every audit-port implementation is handed. Already redacted, as the port
#: requires: a raw identifier must never reach a WORM record.
CANONICAL_EVENT = AuditEvent(
    action="conformity_assess",
    actor=sample_cases.ACTOR,
    decision=Decision.ESCALATED,
    severity=Severity.HIGH,
    redacted_summary="credit-decision-copilot: high-risk, 3 obligation(s) apply",
    citations=(Citation(source_id="hrz3:agent:credit-decision-copilot", title="Registry card"),),
)

#: The escalated result every review-router implementation is handed (rule R8's payload).
CANONICAL_RESULT = ConformityResult(
    subject=sample_cases.ESCALATING_SYSTEM,
    severity=Severity.HIGH,
    decision=Decision.ESCALATED,
    summary=f"{sample_cases.ESCALATING_SYSTEM}: high-risk, 3 obligation(s) apply",
    requires_human_review=True,
    citations=(Citation(source_id="hrz3:agent:credit-decision-copilot", title="Registry card"),),
    tier=RiskTier.HIGH,
)

#: A canonical matrix cell, for the matrix-store round trip.
CANONICAL_CELL = ApplicabilityCell(
    system=sample_cases.ESCALATING_SYSTEM,
    obligation_id="eu-art9",
    framework="eu-ai-act",
    applicability=Applicability.APPLIES,
    reasons=("framework eu-ai-act applies",),
)

#: The inbound transport context every identity implementation is handed.
CANONICAL_CONTEXT = RequestContext(headers={"x-dev-persona": "auditor"})


@dataclass(frozen=True, slots=True)
class PortCase:
    """One port's canonical call plus the two verdicts the parity suites need."""

    invoke: Callable[[Any], Any]
    answered: Callable[[Any, Any], bool]
    managed_refusal: tuple[type[BaseException], ...]
    detail: str


def _audit_invoke(adapter: Any) -> Any:
    return adapter.record(CANONICAL_EVENT)


def _audit_answered(adapter: Any, _result: Any) -> bool:
    stored = adapter.log.read_all()
    return bool(stored) and stored[-1]["actor"] == sample_cases.ACTOR and adapter.verify().ok


def _identity_invoke(adapter: Any) -> Any:
    return adapter.resolve(CANONICAL_CONTEXT)


def _identity_answered(_adapter: Any, result: Any) -> bool:
    return isinstance(result, Principal) and bool(result.actor)


def _review_invoke(adapter: Any) -> Any:
    return adapter.route(CANONICAL_RESULT, maker=sample_cases.ACTOR, tenant=sample_cases.TENANT)


def _review_answered(adapter: Any, result: Any) -> bool:
    return bool(result) and len(adapter.outbox.pending()) == 1


def _registry_invoke(adapter: Any) -> Any:
    return adapter.list()


def _registry_answered(_adapter: Any, result: Any) -> bool:
    return bool(result) and any(c.name == sample_cases.ESCALATING_SYSTEM for c in result)


def _obligations_invoke(adapter: Any) -> Any:
    return adapter.obligations()


def _obligations_answered(_adapter: Any, result: Any) -> bool:
    return bool(result) and all(o.framework for o in result)


def _evidence_invoke(adapter: Any) -> Any:
    return adapter.harvest(sample_cases.ESCALATING_SYSTEM)


def _evidence_answered(_adapter: Any, result: Any) -> bool:
    return bool(result)


def _narrator_invoke(adapter: Any) -> Any:
    prompt = (
        "FACTS:\n"
        + '{"system": "s", "tier": "high", "allowed_figures": ["high"]}'
        + "\nGROUNDING:\n- rule"
    )
    return adapter.narrate(prompt)


def _narrator_answered(_adapter: Any, result: Any) -> bool:
    return isinstance(result, str) and "narrative" in result


def _retrieval_invoke(adapter: Any) -> Any:
    return adapter.search("high eu-ai-act feat")


def _retrieval_answered(_adapter: Any, result: Any) -> bool:
    return bool(result) and all(isinstance(c, Citation) for c in result)


def _horizon_invoke(adapter: Any) -> Any:
    return adapter.changes()


def _horizon_answered(_adapter: Any, result: Any) -> bool:
    return bool(result) and all(c.frameworks for c in result)


def _matrix_invoke(adapter: Any) -> Any:
    ref = adapter.put(sample_cases.TENANT, "2026-08-08", (CANONICAL_CELL,))
    return ref


def _matrix_answered(adapter: Any, result: Any) -> bool:
    return bool(result) and adapter.get(sample_cases.TENANT, "2026-08-08") == (CANONICAL_CELL,)


def _tracer_invoke(adapter: Any) -> Any:
    with adapter.span("canonical.unit", action="canonical"):
        adapter.record_token_usage(TokenUsage(input_tokens=7, output_tokens=2), "canonical-model")
    return True


def _tracer_answered(adapter: Any, result: Any) -> bool:
    return bool(result)


def _evaluation_invoke(adapter: Any) -> Any:
    return adapter.evaluate("eval/datasets/canonical.jsonl")


def _evaluation_answered(adapter: Any, result: Any) -> bool:
    return isinstance(result, EvalReport) and result.dataset.endswith("canonical.jsonl")


CANONICAL_CALLS: dict[str, PortCase] = {
    "audit": PortCase(
        invoke=_audit_invoke,
        answered=_audit_answered,
        managed_refusal=(ImportError,),
        detail="write one already-redacted WORM record",
    ),
    "identity": PortCase(
        invoke=_identity_invoke,
        answered=_identity_answered,
        managed_refusal=(IdentityError,),
        detail="resolve a verified principal from transport context",
    ),
    "review_router": PortCase(
        invoke=_review_invoke,
        answered=_review_answered,
        managed_refusal=(RuntimeError,),
        detail="route one escalated result to human review",
    ),
    "registry": PortCase(
        invoke=_registry_invoke,
        answered=_registry_answered,
        managed_refusal=(RuntimeError,),
        detail="list the deployed AI fleet from the registry",
    ),
    "obligations": PortCase(
        invoke=_obligations_invoke,
        answered=_obligations_answered,
        managed_refusal=(RuntimeError,),
        detail="read the Rgc7 obligations graph",
    ),
    "evidence": PortCase(
        invoke=_evidence_invoke,
        answered=_evidence_answered,
        managed_refusal=(RuntimeError,),
        detail="harvest conformity evidence for a system",
    ),
    "narrator": PortCase(
        invoke=_narrator_invoke,
        answered=_narrator_answered,
        # The lazy `google.genai` import is the first thing the managed narrator does.
        managed_refusal=(ImportError,),
        detail="phrase a narrative from a grounded prompt",
    ),
    "retrieval": PortCase(
        invoke=_retrieval_invoke,
        answered=_retrieval_answered,
        managed_refusal=(ImportError,),
        detail="retrieve grounded rule snippets",
    ),
    "horizon": PortCase(
        invoke=_horizon_invoke,
        answered=_horizon_answered,
        managed_refusal=(RuntimeError,),
        detail="read the AI-reg horizon change feed",
    ),
    "matrix_store": PortCase(
        invoke=_matrix_invoke,
        answered=_matrix_answered,
        # The lazy `google.cloud.bigquery` import is the first thing the managed store does that
        # can fail here. The tenant guard runs ahead of it and passes: the canonical call carries
        # a real partition, because a parity suite that stored under "" would be asserting the
        # very collision `require_tenant` exists to refuse.
        managed_refusal=(ImportError,),
        detail="persist and read back a computed matrix",
    ),
    "tracer": PortCase(
        invoke=_tracer_invoke,
        answered=_tracer_answered,
        # NOTHING. Tracing is not essential to correctness, so the managed adapter must not refuse
        # offline either: with no SDK it degrades to a no-op and the traced body still runs. An
        # adapter that raised here would take a request down over a diagnostic.
        managed_refusal=(),
        detail="open one span and report the cost of a model call",
    ),
    "evaluation": PortCase(
        invoke=_evaluation_invoke,
        answered=_evaluation_answered,
        # The managed gate reaches Hrz4 over HTTP, which is unreachable offline.
        managed_refusal=(Exception,),
        detail="score one golden dataset through the promotion authority",
    ),
}
