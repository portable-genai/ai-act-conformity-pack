"""Managed RegistryPort: read the AI fleet from the Hrz3 agent registry over HTTP.

Mirrors the read half of Hrz3's ``AgentRegistryPort`` against ``/v1/agents`` (GET one, GET all)
and parses the additive ``governance`` block into the vertical's :class:`AiSystemCard`. The base
URL is ``registry_url`` in ``config/settings.yaml``; an empty value fails closed rather than
guessing an endpoint. No cloud SDK is imported (the registry is a sibling HTTP service), so this
module imports cleanly offline; the network call is exercised only against a live registry.
"""

from __future__ import annotations

from typing import Any

from ...config import Settings
from ...domain.models import AiSystemCard


def _card_from_wire(body: dict[str, Any]) -> AiSystemCard:
    gov = body.get("governance") or {}
    owner_raw = gov.get("owner") or {}
    attributes: tuple[tuple[str, str], ...] = tuple(
        sorted((str(k), str(v)) for k, v in (gov.get("attributes") or {}).items())
    )
    return AiSystemCard(
        name=str(body.get("name", "")),
        description=str(body.get("description", "")),
        owner=str(owner_raw.get("team", "")),
        lifecycle=str(gov.get("lifecycle", "draft")),
        scopes=tuple(str(s) for s in (gov.get("scopes") or ())),
        protocols=tuple(str(p) for p in (gov.get("protocols") or ())),
        attributes=attributes,
    )


class CloudRegistryAdapter:
    """Resolve AI-system cards from the live Hrz3 registry."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _base_url(self) -> str:
        url = self._settings.registry_url.strip()
        if not url:
            raise RuntimeError(
                "registry_url is not configured; set AGENT_REGISTRY_URL "
                "(config/settings.yaml registry_url) to the Hrz3 registry base URL."
            )
        return url.rstrip("/")

    def get(self, name: str) -> AiSystemCard | None:  # pragma: no cover - needs live registry
        import httpx

        response = httpx.get(f"{self._base_url()}/v1/agents/{name}", timeout=10.0)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return _card_from_wire(response.json())

    def list(self) -> tuple[AiSystemCard, ...]:
        base = self._base_url()  # RuntimeError here is the offline managed refusal (unconfigured)
        return self._fetch_all(base)

    def _fetch_all(self, base: str) -> tuple[AiSystemCard, ...]:  # pragma: no cover - live only
        import httpx

        response = httpx.get(f"{base}/v1/agents", timeout=10.0)
        response.raise_for_status()
        return tuple(_card_from_wire(item) for item in (response.json() or ()))
