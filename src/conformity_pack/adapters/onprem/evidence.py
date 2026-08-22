"""On-prem EvidencePort: fail-fast portability placeholder (the sovereign-exit proof, P-12)."""

from __future__ import annotations

from ...config import Settings
from ...domain.models import EvidenceItem


class OnPremEvidenceAdapter:
    """Satisfies EvidencePort but refuses at call time: the client wires its own evidence stores."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def harvest(self, system: str) -> tuple[EvidenceItem, ...]:
        raise NotImplementedError(
            "on-prem evidence harvest is a portability placeholder: bind the client's own "
            "eval-evidence and audit stores (see docs/onprem-migration.md)"
        )
