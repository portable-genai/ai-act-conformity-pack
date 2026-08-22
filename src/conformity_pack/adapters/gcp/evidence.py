"""Managed EvidencePort: harvest Hrz4 eval evidence and Hrz5 audit trails over HTTP.

Reads the platform evidence surface (Hrz4's model-card store and Hrz5's audit trails) and tags
each artefact with the obligations it attests. The base URL is ``evidence_url`` in
``config/settings.yaml``; an empty value fails closed. No cloud SDK import.
"""

from __future__ import annotations

from typing import Any

from ...config import Settings
from ...domain.kernel import Citation
from ...domain.models import EvidenceItem


def _evidence_from_wire(body: dict[str, Any]) -> EvidenceItem:
    return EvidenceItem(
        id=str(body.get("id", "")),
        kind=str(body.get("kind", "")),
        obligation_ids=tuple(str(o) for o in (body.get("obligation_ids") or ())),
        detail=str(body.get("detail", "")),
        citation=Citation(
            source_id=f"hrz:evidence:{body.get('id', '')}", title=str(body.get("kind", ""))
        ),
    )


class CloudEvidenceAdapter:
    """Harvest evidence from the live platform evidence surface."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def harvest(self, system: str) -> tuple[EvidenceItem, ...]:
        url = self._settings.evidence_url.strip()
        if not url:
            raise RuntimeError(
                "evidence_url is not configured; set it (config/settings.yaml evidence_url) "
                "to the platform evidence surface base URL."
            )
        return self._fetch(url.rstrip("/"), system)

    def _fetch(
        self, base: str, system: str
    ) -> tuple[EvidenceItem, ...]:  # pragma: no cover - live only
        import httpx

        response = httpx.get(f"{base}/v1/evidence", params={"system": system}, timeout=10.0)
        response.raise_for_status()
        return tuple(_evidence_from_wire(item) for item in (response.json() or ()))
