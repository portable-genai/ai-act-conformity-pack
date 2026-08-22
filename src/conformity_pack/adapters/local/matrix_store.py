"""Local MatrixStorePort: an in-memory matrix store (SDK-free offline).

Persists a computed applicability matrix keyed by the ``(tenant, as_of)`` PAIR in a process-local
dict, so the offline gate, the tests and the demo can round-trip a matrix without BigQuery. Not a
no-op: a ``put`` followed by a ``get`` returns the same cells, which is what the parity suite
asserts the offline family actually answers.

The pair is the fix, not a refinement. Keyed on ``as_of`` alone, two tenants assessing on the
same replay date wrote into one slot: the second write destroyed the first, and both tenants then
read the survivor. One shared process serving two tenants is the ordinary case, not an exotic
one, so this store is where the isolation has to hold offline.
"""

from __future__ import annotations

from ...config import Settings
from ...domain.models import ApplicabilityCell
from ...ports.matrix_store import require_tenant


class LocalMatrixStore:
    """Record computed matrices in memory for the ``local`` profile, partitioned by tenant."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._store: dict[tuple[str, str], tuple[ApplicabilityCell, ...]] = {}

    def put(self, tenant: str, as_of: str, cells: tuple[ApplicabilityCell, ...]) -> str:
        partition = require_tenant(tenant)
        self._store[(partition, as_of)] = cells
        return f"local-matrix:{partition}:{as_of}:{len(cells)}"

    def get(self, tenant: str, as_of: str) -> tuple[ApplicabilityCell, ...]:
        partition = require_tenant(tenant)
        return self._store.get((partition, as_of), ())
