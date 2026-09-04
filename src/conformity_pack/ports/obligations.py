"""ObligationsPort: the read seam onto the obligations-control-mapping graph (the
obligations-control-mapping seam).

ai-act-conformity-pack evaluates applicability OVER the shared obligations graph
(``rgc-obligations-control-
mapping``); it does not own the obligations. This port names that read. The adapters pin
``obligation-register-kit`` by tag for the record shapes and translate a kit ``Obligation`` into
the vertical's :class:`ObligationRef` (framework, minimum tier, jurisdiction, required evidence
kinds), so the pure applicability engine never depends on the kit.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.models import ObligationRef


@runtime_checkable
class ObligationsPort(Protocol):
    def obligations(self) -> tuple[ObligationRef, ...]:
        """Every obligation in the obligations-control-mapping graph, as vertical
        :class:`ObligationRef` records.
        """
        ...
