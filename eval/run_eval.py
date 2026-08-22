#!/usr/bin/env python3
"""Evaluation gate for AI Act Conformity Pack (Rgc14).

Two named layers via ``--mode`` (the scaffold is ``agent_eval_kit.eval_main``):

* **smoke** (default) - the offline pre-merge check CI runs on every change: it drives the real
  ``ConformityService`` against a golden set with SDK-free local adapters and scores three
  metrics against the dataset's OWN labels (the independent oracle).
* **gate** - the promotion verdict from the shared Hrz4 authority (requires the ``gcp``
  profile), via ``agent_eval_kit.PromotionGateClient``.

The consequential metrics score the deterministic engine, never the model: ``tier_accuracy`` and
``conditional_accuracy`` compare the pure classifier to the dataset's independently-labelled
expected outcome, and ``pii_safety`` checks that no raw identifier survives into an audit record.
Exit is ``0`` iff every metric meets its threshold (and, in gate mode, the authority agrees).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from agent_eval_kit import EvalMetricResult, EvalReport, PromotionGateClient, eval_main
from pii_kit import pack_leak

from conformity_pack.config import Settings, build_container
from conformity_pack.domain.conformity_service import ConformityService
from conformity_pack.domain.models import AiSystemInput
from conformity_pack.domain.pii import PII_PATTERNS

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = _REPO_ROOT / "eval" / "datasets" / "golden_cases.jsonl"

THRESHOLDS: dict[str, float] = {
    "tier_accuracy": 1.0,
    "conditional_accuracy": 1.0,
    "pii_safety": 0.99,
}
#: The registered Hrz4 metric bundle for this vertical (Hrz4 owns the metrics + thresholds).
_BUNDLE = "ai-act-conformity-pack"

#: The tenant the eval run is attributed to. Obviously fictional, and named rather than empty:
#: the store refuses an unscoped write, and an eval that quietly skipped the matrix path would
#: stop exercising it.
_EVAL_TENANT = "eval-bank"


def _load(path: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cases.append(json.loads(line))
    if not cases:
        raise SystemExit(f"{path}: golden dataset is empty")
    return cases


def _mean(scores: list[float]) -> float:
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def audit_texts(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """Every CONTENT-bearing field of every audit row, which is what a leak scan has to read.

    Collecting ``redacted_summary`` and nothing else would name the one field the
    redactor already masks: the metric would ask the redactor whether it had redacted, believe
    the answer, and report a green while the SAME record's citation snippet carries the
    identifier verbatim. Citations travel inside the record, and they carry upstream free text in
    ``snippet`` (the registry card's description) and, when a system is named after the case it
    was built for, in ``source_id`` and ``title`` as well.

    ``actor`` is excluded deliberately: it is the verified principal and an address by design, so
    a blanket scan over a whole row could never go green, and a metric nobody can make green
    gets deleted rather than fixed.
    """
    texts: list[str] = []
    for row in rows:
        texts.append(str(row.get("redacted_summary", "")))
        texts.append(json.dumps(row.get("citations", []), sort_keys=True))
    return texts


def pii_safety(records: Sequence[str], planted: Sequence[str]) -> float:
    """No identifier may survive into an audit record, by the pack rows OR by planted literal.

    Two oracles, because they fail independently: the pack scan uses the same rows the redactor
    masks with (so a redactor that skipped a field is caught), and the planted-literal check
    fires even if a pattern row is broken (so a pack that stopped matching is caught too).
    """
    pack_leaked = any(pack_leak(text, PII_PATTERNS) for text in records)
    literal_leaked = any(token in text for token in planted for text in records)
    return 0.0 if (pack_leaked or literal_leaked) else 1.0


def _service() -> tuple[ConformityService, object]:
    container = build_container(Settings(profile="local", audit_path=":memory:"))
    service = ConformityService(
        audit=container.audit,
        registry=container.registry,
        obligations=container.obligations,
        evidence=container.evidence,
        retrieval=container.retrieval,
        narrator=container.narrator,
        tracer=container.tracer,
        matrix_store=container.matrix_store,
    )
    return service, container.audit


def run_smoke(dataset: Path) -> EvalReport:
    cases = _load(dataset)
    service, audit = _service()

    tier_scores: list[float] = []
    conditional_scores: list[float] = []
    for case in cases:
        result = service.assess(
            AiSystemInput(system=str(case["system"])), actor="eval-bot", tenant=_EVAL_TENANT
        )
        # Scored against the dataset's OWN expected_outcome, never the pipeline's own verdict.
        tier_scores.append(1.0 if result.tier.value == case["expected_tier"] else 0.0)
        conditional_scores.append(
            1.0 if result.conditional == bool(case.get("expected_conditional")) else 0.0
        )

    # pii_safety: no raw identifier may survive into any audit record. `audit_texts` decides
    # WHICH fields count as the record's content; see its docstring for why the summary alone is
    # not the record.
    records = audit_texts(audit.log.read_all())  # type: ignore[attr-defined]
    planted = [str(case["planted"]) for case in cases if case.get("planted")]

    results = (
        EvalMetricResult.scored("tier_accuracy", _mean(tier_scores), THRESHOLDS["tier_accuracy"]),
        EvalMetricResult.scored(
            "conditional_accuracy", _mean(conditional_scores), THRESHOLDS["conditional_accuracy"]
        ),
        EvalMetricResult.scored(
            "pii_safety", pii_safety(records, planted), THRESHOLDS["pii_safety"]
        ),
    )
    return EvalReport(dataset=str(dataset), results=results, n_examples=len(cases))


def run_gate(dataset: Path) -> tuple[EvalReport, bool]:
    settings = Settings.load()
    if settings.profile != "gcp":
        raise SystemExit(
            "--mode gate is the promotion authority and requires "
            f"CFP_PROFILE=gcp (got {settings.profile!r}); "
            "run --mode smoke for the offline pre-merge check."
        )
    client = PromotionGateClient(
        os.environ.get("CFP_QUALITY_URL", "http://localhost:8084"),
        bundle=_BUNDLE,
        model=settings.narrator_model,
    )
    return client.evaluate(str(dataset)), client.gate(str(dataset))


if __name__ == "__main__":
    raise SystemExit(
        eval_main(
            smoke=run_smoke,
            gate=run_gate,
            default_dataset=DEFAULT_DATASET,
            description="Offline / Hrz4 evaluation gate for Rgc14.",
        )
    )
