"""Local EvidencePort: the fixture Hrz4/Hrz5 evidence, harvested per system (SDK-free offline).

Serves the synthetic harvested evidence from :mod:`.fleet_fixtures`. Deliberately incomplete for
some systems so the sufficiency engine surfaces the same named gaps the managed adapter would
when a platform evidence file is genuinely absent.
"""

from __future__ import annotations

from ...config import Settings
from ...domain.models import EvidenceItem
from . import fleet_fixtures


class LocalEvidenceAdapter:
    """Serve fixture evidence for the ``local`` profile."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def harvest(self, system: str) -> tuple[EvidenceItem, ...]:
        return fleet_fixtures.evidence_for(system)
