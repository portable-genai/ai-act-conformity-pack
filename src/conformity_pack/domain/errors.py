"""Domain error types (pure stdlib). One base, so a caller can catch the vertical's faults.

These are DOMAIN faults (an unknown pack, an ungrounded narrative, an empty knowledge base),
distinct from the adapter-layer faults an ``onprem`` placeholder raises (``NotImplementedError``)
or a managed adapter raises when a cloud is unreachable. Nothing here imports a framework, a
cloud SDK or a port.
"""

from __future__ import annotations


class ConformityError(Exception):
    """Base class for every fault raised by the conformity-pack domain."""


class UnknownPackError(ConformityError):
    """A named classification pack does not exist. Raised rather than binding a default."""


class UngroundedNarrativeError(ConformityError):
    """A narrative asserted a figure or a claim the deterministic engine never produced."""


class EmptyRetrievalError(ConformityError):
    """A grounded narrative was requested but the knowledge base returned nothing (P-05)."""


class TenantScopeError(ConformityError):
    """A tenant-partitioned read or write was attempted with no tenant to partition it by.

    Refused rather than defaulted. An empty tenant is not a neutral key: it is ONE partition that
    every unscoped caller shares, so storing under it recreates the cross-tenant collision the
    partition exists to prevent, and does it silently. The tenant comes from the VERIFIED
    principal and from nowhere else, so the honest answer when there is none is a refusal.
    """
