"""Local HorizonPort: the fixture Rsk1 horizon change feed (SDK-free offline).

Serves the synthetic corpus-change feed from :mod:`.fleet_fixtures`. The ``since`` filter is a
plain ISO-date string compare on the change id's embedded year segment; for the fixture feed it
returns the whole feed, which is enough to exercise the deterministic re-check.
"""

from __future__ import annotations

from ...config import Settings
from ...domain.models import RegChange
from . import fleet_fixtures


class LocalHorizonAdapter:
    """Serve the fixture change feed for the ``local`` profile."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def changes(self, since: str = "") -> tuple[RegChange, ...]:
        return fleet_fixtures.CHANGES
