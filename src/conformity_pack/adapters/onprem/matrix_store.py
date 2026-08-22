"""On-prem MatrixStorePort: fail-fast portability placeholder (the sovereign-exit proof, P-12)."""

from __future__ import annotations

from ...config import Settings
from ...domain.models import ApplicabilityCell


class OnPremMatrixStore:
    """Satisfies MatrixStorePort but refuses at call time: the client wires its own store."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def put(self, tenant: str, as_of: str, cells: tuple[ApplicabilityCell, ...]) -> str:
        raise NotImplementedError(
            "on-prem matrix store is a portability placeholder: bind the client's own lineage "
            "store (see docs/onprem-migration.md)"
        )

    def get(self, tenant: str, as_of: str) -> tuple[ApplicabilityCell, ...]:
        raise NotImplementedError(
            "on-prem matrix store is a portability placeholder: bind the client's own lineage "
            "store (see docs/onprem-migration.md)"
        )
