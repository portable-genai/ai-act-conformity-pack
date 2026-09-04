"""Managed HorizonPort: read the compliance-advisory AI-reg horizon change feed over HTTP.

Reads compliance-advisory's ``CorpusChange`` feed and translates each record into the vertical's
:class:`RegChange`. The base URL is ``horizon_url`` in ``config/settings.yaml``; an empty value
fails closed. No cloud SDK import.
"""

from __future__ import annotations

from typing import Any

from ...config import Settings
from ...domain.kernel import Citation
from ...domain.models import RegChange


def _change_from_wire(body: dict[str, Any]) -> RegChange:
    return RegChange(
        id=str(body.get("id", "")),
        title=str(body.get("title", "")),
        frameworks=tuple(str(f) for f in (body.get("frameworks") or ())),
        scopes=tuple(str(s) for s in (body.get("scopes") or ())),
        detail=str(body.get("detail", "")),
        citation=Citation(
            source_id=f"rsk1:change:{body.get('id', '')}", title=str(body.get("title", ""))
        ),
    )


class CloudHorizonAdapter:
    """Read corpus changes from the live compliance-advisory horizon feed."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def changes(self, since: str = "") -> tuple[RegChange, ...]:
        url = self._settings.horizon_url.strip()
        if not url:
            raise RuntimeError(
                "horizon_url is not configured; set it (config/settings.yaml horizon_url) "
                "to the compliance-advisory horizon feed base URL."
            )
        return self._fetch(url.rstrip("/"), since)

    def _fetch(
        self, base: str, since: str
    ) -> tuple[RegChange, ...]:  # pragma: no cover - live only
        import httpx

        response = httpx.get(f"{base}/v1/changes", params={"since": since}, timeout=10.0)
        response.raise_for_status()
        return tuple(_change_from_wire(item) for item in (response.json() or ()))
