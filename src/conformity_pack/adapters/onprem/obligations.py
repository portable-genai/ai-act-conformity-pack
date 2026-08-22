"""On-prem ObligationsPort: fail-fast portability placeholder (the sovereign-exit proof, P-12)."""

from __future__ import annotations

from ...config import Settings
from ...domain.models import ObligationRef


class OnPremObligationsAdapter:
    """Satisfies ObligationsPort but refuses at call time: the client wires its own Rgc7 feed."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def obligations(self) -> tuple[ObligationRef, ...]:
        raise NotImplementedError(
            "on-prem obligations feed is a portability placeholder: bind the client's own "
            "obligations register (see docs/onprem-migration.md)"
        )
