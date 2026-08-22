"""On-prem HorizonPort: fail-fast portability placeholder (the sovereign-exit proof, P-12)."""

from __future__ import annotations

from ...config import Settings
from ...domain.models import RegChange


class OnPremHorizonAdapter:
    """Satisfies HorizonPort but refuses at call time: the client wires its own horizon feed."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def changes(self, since: str = "") -> tuple[RegChange, ...]:
        raise NotImplementedError(
            "on-prem horizon feed is a portability placeholder: bind the client's own AI-reg "
            "change feed (see docs/onprem-migration.md)"
        )
