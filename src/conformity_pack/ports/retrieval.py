"""RetrievalPort: grounded retrieval over the AI-reg / FEAT rule knowledge base (P-05).

The narrative is GROUNDED: it may restate only rule text that was retrieved, and an empty
retrieval for a required query is a hard error, not a licence to invent (P-05). This port names
the retrieval. The managed adapter is Gemini File Search over the AI-Act / FEAT / JFSA rule
corpus; the local adapter is a fixture knowledge base. Snippets are returned as
:class:`Citation`s so the narrative's grounding sources are the retrieval's own, checkable set.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.kernel import Citation


@runtime_checkable
class RetrievalPort(Protocol):
    def search(self, query: str) -> tuple[Citation, ...]:
        """Retrieve rule-text snippets for ``query`` as citations; may be empty (caller decides)."""
        ...
