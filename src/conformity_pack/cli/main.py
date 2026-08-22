"""Minimal stdlib CLI: assess a system, or verify the audit chain (argparse, no extra deps)."""

from __future__ import annotations

import argparse
import sys

from hex_service_kit.logging import configure_logging

from ..config import Container, build_container
from ..domain.conformity_service import ConformityService
from ..domain.errors import ConformityError
from ..domain.models import AiSystemInput


def _service(container: Container) -> ConformityService:
    return ConformityService(
        audit=container.audit,
        registry=container.registry,
        obligations=container.obligations,
        evidence=container.evidence,
        retrieval=container.retrieval,
        narrator=container.narrator,
        tracer=container.tracer,
        matrix_store=container.matrix_store,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="conformity_pack")
    sub = parser.add_subparsers(dest="command", required=True)

    assess_cmd = sub.add_parser("assess", help="Assess one AI system for conformity.")
    assess_cmd.add_argument("system", help="The registered system name to assess.")
    assess_cmd.add_argument("--actor", default="cli-user@bank.example")
    # Also the partition the persisted matrix is stored under, so `--as-of` without `--tenant`
    # is refused rather than writing lineage into the partition every unscoped run shares.
    assess_cmd.add_argument(
        "--tenant", default="", help="Tenant partition: asserted to Hrz7, and the matrix key."
    )
    assess_cmd.add_argument("--as-of", default="", help="Replay date stamped on the matrix.")

    args = parser.parse_args(argv)
    container = build_container()
    # Idempotent: a process that is both an API app and a CLI configures once.
    configure_logging(container.settings.profile, service="ai-act-conformity-pack")

    if args.command == "assess":
        try:
            result = _service(container).assess(
                AiSystemInput(system=args.system),
                actor=args.actor,
                tenant=args.tenant,
                as_of=args.as_of,
            )
        except ConformityError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"{result.subject}: {result.tier.value}-risk ({result.decision.value})")
        print(f"  obligations applying: {result.applies_count}")
        print(f"  evidence gaps: {len(result.gaps)}")
        print(f"  requires_human_review: {result.requires_human_review}")
        if result.requires_human_review:
            # Rule R8 on the CLI path too: the same escalation, the same router.
            ref = container.review_router.route(result, maker=args.actor, tenant=args.tenant)
            print(f"  routed to human review: {ref}")
        return 0

    return 2  # pragma: no cover - argparse requires a subcommand


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
