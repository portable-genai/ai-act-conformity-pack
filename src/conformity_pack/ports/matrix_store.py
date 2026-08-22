"""MatrixStorePort: persist the computed applicability matrix for lineage reporting.

The applicability matrix is computed deterministically and then PERSISTED, keyed by ``tenant``
and ``as_of``, so a later run can report lineage (what applied, to whom, when, and why). The
managed adapter is BigQuery (honouring the row's BigQuery stack entry); the local adapter is an
in-memory store; the onprem placeholder fails fast. The store speaks the vertical's own
:class:`ApplicabilityCell`; the adapter serialises it.

**The tenant is half the key, and it was missing.** The port used to declare ``put(as_of, cells)``
and ``get(as_of)``, so two tenants computing a matrix for the same replay date overwrote each
other in the local store and either read back the other's cells, while the BigQuery table had no
tenant column at all and the persisted lineage record could not be filtered even after the fact.
A lineage record is what a regulator is shown; "whose matrix is this" is not a reporting nicety.

Two rules every implementation obeys:

* the tenant comes from the VERIFIED principal (``Principal.tenant``), never from a client
  field, and never from a deployment-wide setting standing in for one;
* an EMPTY tenant is REFUSED, by :func:`require_tenant`, rather than stored under ``""``. See
  :class:`~..domain.errors.TenantScopeError` for why the empty string is the defect, not a
  default.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.errors import TenantScopeError
from ..domain.models import ApplicabilityCell


def require_tenant(tenant: str) -> str:
    """The partition key, or a refusal. Never a fallback, and never the empty string.

    Written once here, beside the contract it enforces, and called by every implementation, so
    the fail-closed half of the contract cannot hold in one adapter family and quietly not in
    another. Whitespace is stripped first: a tenant of ``"   "`` is an absent tenant that got
    past a truthiness check, which is exactly the shape a configuration mistake takes.
    """
    partition = tenant.strip()
    if not partition:
        raise TenantScopeError(
            "a tenant-partitioned matrix read or write needs the verified principal's tenant; "
            "refusing rather than falling back to the empty partition, which every unscoped "
            "caller would share"
        )
    return partition


@runtime_checkable
class MatrixStorePort(Protocol):
    def put(self, tenant: str, as_of: str, cells: tuple[ApplicabilityCell, ...]) -> str:
        """Persist ``tenant``'s matrix for ``as_of``; return a reference to the stored matrix."""
        ...

    def get(self, tenant: str, as_of: str) -> tuple[ApplicabilityCell, ...]:
        """Read back ``tenant``'s matrix for ``as_of`` (empty when THAT tenant stored none).

        The tenant filter is the STORE's, not the caller's: a read must never be able to span
        tenants, so an implementation filters on the partition rather than returning everything
        and trusting whoever called it to discard the rest.
        """
        ...
