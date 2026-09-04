"""EvidencePort: harvest conformity evidence for a system (model-quality-gate eval reports,
agent-observability trails).

The sufficiency engine needs the evidence a system already has: model-quality-gate's eval evidence
(the ``MrmEvidence`` / ``EvalReport`` shapes behind model-quality-gate's model-card store) and
agent-observability's audit trails. This port names that harvest. The adapters read those platform
surfaces; the domain reasons over the vertical's own :class:`EvidenceItem`, each tagging which
obligation ids it attests.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.models import EvidenceItem


@runtime_checkable
class EvidencePort(Protocol):
    def harvest(self, system: str) -> tuple[EvidenceItem, ...]:
        """Every evidence artefact harvested for ``system``, tagged by the obligations it meets."""
        ...
