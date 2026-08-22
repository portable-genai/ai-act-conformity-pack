"""Managed NarratorPort: phrase the conformity narrative with Gemini (SDK imports stay lazy).

Calls the configured Gemini model to phrase a narrative for a verdict the engines already
produced; the reply is schema-validated and discarded on failure by the caller, so a
hallucination never reaches a pack. The ``google-genai`` import lives inside the method, so the
offline profiles import this module with no SDK installed and the offline gate stays SDK-free.
"""

from __future__ import annotations

from ...config import Settings


class CloudNarratorAdapter:
    """Phrase narratives via the managed generation model."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def narrate(self, prompt: str) -> str:
        # Lazy import: absent in the offline profile and in CI (hence import-not-found ignore).
        from google import genai

        client = genai.Client()
        response = client.models.generate_content(
            model=self._settings.narrator_model, contents=prompt
        )
        return str(response.text)
