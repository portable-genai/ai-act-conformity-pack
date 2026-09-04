"""Local RegistryPort: the fixture AI fleet, served with no live agent-registry (SDK-free offline).

Serves the synthetic self-governing fleet from :mod:`.fleet_fixtures`, so the offline gate, the
tests and the demo classify a real fleet without a running registry. Not a no-op: it returns the
same :class:`AiSystemCard`s the managed adapter would parse from agent-registry's ``governance``
block.
"""

from __future__ import annotations

from ...config import Settings
from ...domain.models import AiSystemCard
from . import fleet_fixtures


class LocalRegistryAdapter:
    """Serve the fixture fleet for the ``local`` profile."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get(self, name: str) -> AiSystemCard | None:
        for card in fleet_fixtures.FLEET:
            if card.name == name:
                return card
        return None

    def list(self) -> tuple[AiSystemCard, ...]:
        return fleet_fixtures.FLEET
