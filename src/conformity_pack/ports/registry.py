"""RegistryPort: the read side of the agent-registry (the AI-system inventory source).

ai-act-conformity-pack owns no inventory of its own (the wave's inventory boundary): it READS the
deployed AI and agent systems from the built agent-registry and classifies what it finds. This port
names that read seam. It mirrors the read half of agent-registry's ``AgentRegistryPort`` (``get`` /
``list``), and the adapters parse the additive ``governance`` block (owner, lifecycle, scopes,
protocols) that ``agent-registry`` defines, because those declared fields drive the classification.

The domain stays pure: this port speaks the vertical's own :class:`AiSystemCard`, and the
adapters translate the registry's wire card into it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.models import AiSystemCard


@runtime_checkable
class RegistryPort(Protocol):
    def get(self, name: str) -> AiSystemCard | None:
        """Resolve one system's card by name, or ``None`` when it is not registered."""
        ...

    def list(self) -> tuple[AiSystemCard, ...]:
        """List every AI-system card currently in the registry (the fleet to be governed)."""
        ...
