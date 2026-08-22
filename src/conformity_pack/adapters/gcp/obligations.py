"""Managed ObligationsPort: read the Rgc7 obligations graph over HTTP.

Reads the Rgc7 (``obligations-control-mapping``) feed, parses each row into an
``obligation-register-kit`` ``Obligation`` (the shared wire shape), and translates it into the
vertical's :class:`ObligationRef` through the same :func:`obligation_to_ref` the local fixture
adapter uses, so both families produce identical vertical records. The base URL is
``obligations_url`` in ``config/settings.yaml``; an empty value fails closed. No cloud SDK import;
the network call runs only against a live Rgc7 service.
"""

from __future__ import annotations

from typing import Any

from obligation_register import Citation as KitCitation
from obligation_register import Obligation as KitObligation

from ...config import Settings
from ...domain.models import ObligationRef
from .._obligation_records import obligation_to_ref


def _kit_from_wire(body: dict[str, Any]) -> KitObligation:
    attributes = tuple((str(k), str(v)) for k, v in (body.get("attributes") or {}).items())
    oid = str(body.get("id", ""))
    title = str(body.get("title", ""))
    return KitObligation(
        id=oid,
        title=title,
        text=str(body.get("text", "")) or title,
        citation=KitCitation(source_id=f"rgc7:obligation:{oid}", title=title),
        attributes=attributes,
    )


class CloudObligationsAdapter:
    """Read obligations from the live Rgc7 service."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def obligations(self) -> tuple[ObligationRef, ...]:
        url = self._settings.obligations_url.strip()
        if not url:
            raise RuntimeError(
                "obligations_url is not configured; set it (config/settings.yaml "
                "obligations_url) to the Rgc7 obligations service base URL."
            )
        return self._fetch(url.rstrip("/"))

    def _fetch(self, base: str) -> tuple[ObligationRef, ...]:  # pragma: no cover - live only
        import httpx

        response = httpx.get(f"{base}/v1/obligations", timeout=10.0)
        response.raise_for_status()
        return tuple(obligation_to_ref(_kit_from_wire(item)) for item in (response.json() or ()))
