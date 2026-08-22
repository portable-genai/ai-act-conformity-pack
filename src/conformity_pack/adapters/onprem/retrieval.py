"""On-prem RetrievalPort: fail-fast portability placeholder (the sovereign-exit proof, P-12)."""

from __future__ import annotations

from ...config import Settings
from ...domain.kernel import Citation


class OnPremRetrievalAdapter:
    """Satisfies RetrievalPort but refuses at call time: the client wires its own rule KB."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def search(self, query: str) -> tuple[Citation, ...]:
        raise NotImplementedError(
            "on-prem retrieval is a portability placeholder: bind the client's own rule-text "
            "knowledge base (see docs/onprem-migration.md)"
        )
