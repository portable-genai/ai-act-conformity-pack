"""Local ObligationsPort: the fixture obligations-control-mapping graph (SDK-free offline).

Serves the synthetic obligations graph from :mod:`.fleet_fixtures` as vertical
:class:`ObligationRef` records, the same shape the managed adapter produces by translating an
``obligation-register-kit`` record. The offline applicability engine runs against these.
"""

from __future__ import annotations

from ...config import Settings
from ...domain.models import ObligationRef
from . import fleet_fixtures


class LocalObligationsAdapter:
    """Serve the fixture obligations graph for the ``local`` profile."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def obligations(self) -> tuple[ObligationRef, ...]:
        return fleet_fixtures.OBLIGATIONS
