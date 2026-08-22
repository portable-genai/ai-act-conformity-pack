"""On-prem NarratorPort: fail-fast portability placeholder (the sovereign-exit proof, P-12)."""

from __future__ import annotations

from ...config import Settings


class OnPremNarratorAdapter:
    """Satisfies NarratorPort but refuses at call time: the client wires its own model gateway."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def narrate(self, prompt: str) -> str:
        raise NotImplementedError(
            "on-prem narrator is a portability placeholder: bind the client's own in-country "
            "model gateway (see docs/onprem-migration.md)"
        )
