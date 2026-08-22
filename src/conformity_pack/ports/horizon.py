"""HorizonPort: the Rsk1 AI-reg horizon change feed (which corpus movements to re-check).

Rsk1 (incl. the ex-Rgc6 horizon scanner) emits regulatory-corpus changes. Rgc14 consumes that
feed and, for each change, deterministically re-runs classification and applicability for the
affected systems (:mod:`..domain.horizon_recheck`). This port names the feed read. The adapters
translate Rsk1's ``CorpusChange`` records into the vertical's :class:`RegChange`; the domain does
the re-check purely.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.models import RegChange


@runtime_checkable
class HorizonPort(Protocol):
    def changes(self, since: str = "") -> tuple[RegChange, ...]:
        """Corpus changes at or after ``since`` (an ISO date, or empty for the whole feed)."""
        ...
