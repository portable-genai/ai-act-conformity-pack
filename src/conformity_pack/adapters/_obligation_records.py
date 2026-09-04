"""Translate an ``obligation-register-kit`` record into the vertical's :class:`ObligationRef`.

The obligations-control-mapping seam: both the local fixture graph and the managed
obligations-control-mapping adapter speak the shared kit's ``Obligation`` shape, and this is the ONE
place that shape is turned into the vertical type the pure applicability engine reads. Lives in the
adapter layer, not the domain, because it depends on the kit; the domain never imports it. Freezing
this translation is what ``tests/contract/test_obligation_kit_contract.py`` does.
"""

from __future__ import annotations

from obligation_register import Obligation as KitObligation

from ..domain.kernel import Citation
from ..domain.models import ObligationRef, RiskTier


def _attrs(obligation: KitObligation) -> dict[str, str]:
    return {key: value for key, value in obligation.attributes}


def obligation_to_ref(obligation: KitObligation) -> ObligationRef:
    """Read the classifying attributes off a kit record into a vertical :class:`ObligationRef`.

    The framework, minimum tier, jurisdiction and required-evidence kinds travel in the kit
    record's ``attributes`` tuple. A missing ``min_tier`` fails closed to HIGH (the strictest tier
    an obligation is likely to bind at), never to MINIMAL: an obligation whose tier is unstated
    should over-apply and be reviewed, not silently drop out of scope.
    """
    attrs = _attrs(obligation)
    min_tier = RiskTier(attrs["min_tier"]) if attrs.get("min_tier") else RiskTier.HIGH
    required = tuple(part for part in attrs.get("required_evidence", "").split(";") if part)
    citation = obligation.citation
    return ObligationRef(
        id=obligation.id,
        title=obligation.title,
        framework=attrs.get("framework", "eu-ai-act"),
        min_tier=min_tier,
        jurisdiction=attrs.get("jurisdiction", ""),
        required_evidence=required,
        citation=Citation(
            source_id=citation.source_id,
            title=citation.title or obligation.title,
            snippet=citation.snippet,
        ),
    )
