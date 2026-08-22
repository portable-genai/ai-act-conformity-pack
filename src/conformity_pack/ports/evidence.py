"""EvidencePort: harvest conformity evidence for a system (Hrz4 eval reports, Hrz5 audit trails).

The sufficiency engine needs the evidence a system already has: Hrz4's eval evidence (the
``MrmEvidence`` / ``EvalReport`` shapes behind Hrz4's model-card store) and Hrz5's audit trails.
This port names that harvest. The adapters read those platform surfaces; the domain reasons over
the vertical's own :class:`EvidenceItem`, each tagging which obligation ids it attests.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.models import EvidenceItem


@runtime_checkable
class EvidencePort(Protocol):
    def harvest(self, system: str) -> tuple[EvidenceItem, ...]:
        """Every evidence artefact harvested for ``system``, tagged by the obligations it meets."""
        ...
