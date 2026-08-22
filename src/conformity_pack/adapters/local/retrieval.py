"""Local RetrievalPort: the fixture rule knowledge base (SDK-free offline).

Serves rule-text snippets from :mod:`.fleet_fixtures` as citations. It answers a query only when
a KB token appears in it, so an off-topic query returns EMPTY and the grounding rule (P-05, the
service raises on an empty retrieval where grounding is required) can actually be exercised.
"""

from __future__ import annotations

from ...config import Settings
from ...domain.kernel import Citation
from . import fleet_fixtures


class LocalRetrievalAdapter:
    """Serve the fixture knowledge base for the ``local`` profile."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def search(self, query: str) -> tuple[Citation, ...]:
        return fleet_fixtures.knowledge_base(query)
