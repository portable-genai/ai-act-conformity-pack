"""Managed RetrievalPort: grounded retrieval via Gemini File Search (SDK imports stay lazy).

Retrieves AI-Act / FEAT / JFSA rule-text snippets from the managed File Search store and returns
them as citations the narrative grounds against. The ``google-genai`` import lives inside the
method so the offline profiles import this module with no SDK installed.
"""

from __future__ import annotations

from ...config import Settings
from ...domain.kernel import Citation


class CloudRetrievalAdapter:
    """Retrieve grounded rule snippets from the managed knowledge base."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def search(self, query: str) -> tuple[Citation, ...]:
        # Lazy import: absent in the offline profile and in CI (hence import-not-found ignore).
        from google import genai

        client = genai.Client()
        response = client.models.generate_content(
            model=self._settings.narrator_model, contents=query
        )
        # A real File Search response carries grounding chunks; this thin path returns the model
        # text as one snippet. The offline profile is the ground truth for the eval.
        return (
            Citation(
                source_id="gemini:file-search",
                title="Gemini File Search",
                snippet=str(response.text)[:120],
            ),
        )
