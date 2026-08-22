"""On-prem RegistryPort: fail-fast portability placeholder (the sovereign-exit proof, P-12)."""

from __future__ import annotations

from ...config import Settings
from ...domain.models import AiSystemCard


class OnPremRegistryAdapter:
    """Satisfies RegistryPort but refuses at call time: the client wires its own registry."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get(self, name: str) -> AiSystemCard | None:
        raise NotImplementedError(
            "on-prem registry is a portability placeholder: bind the client's own AI-system "
            "inventory (see docs/onprem-migration.md)"
        )

    def list(self) -> tuple[AiSystemCard, ...]:
        raise NotImplementedError(
            "on-prem registry is a portability placeholder: bind the client's own AI-system "
            "inventory (see docs/onprem-migration.md)"
        )
