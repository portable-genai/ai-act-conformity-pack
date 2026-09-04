"""The synthetic AI fleet the offline profile governs: cards, obligations, evidence, KB, feed.

One home for the fixture data every ``local`` adapter serves, so the registry, obligations,
evidence, retrieval and horizon adapters all agree on one fleet. Obviously fictional: every system,
owner and party is invented and every domain is ``.example``. This is the self-governing demo fleet,
so model-risk-validation's own registered card is included (the wave's second repo governs the
first).

The data is deliberately shaped so the deterministic engines produce a spread of outcomes: a
prohibited practice, high-risk credit and HR systems, a limited-risk chatbot, a minimal internal
tool, and an adversarial under-declared card that must classify CONDITIONAL rather than minimal.
"""

from __future__ import annotations

from obligation_register import Citation as KitCitation
from obligation_register import Obligation as KitObligation

from ...domain.kernel import Citation
from ...domain.models import (
    AiSystemCard,
    EvidenceItem,
    ObligationRef,
    RegChange,
    RiskTier,
)
from .._obligation_records import obligation_to_ref


def _card(
    name: str,
    scopes: tuple[str, ...],
    jurisdictions: str,
    *,
    lifecycle: str = "production",
    owner: str = "ai-platform@bank.example",
    description: str = "",
) -> AiSystemCard:
    attributes: tuple[tuple[str, str], ...] = (
        (("jurisdictions", jurisdictions),) if jurisdictions else ()
    )
    return AiSystemCard(
        name=name,
        description=description or f"{name} (FICTIONAL synthetic system)",
        owner=owner,
        lifecycle=lifecycle,
        scopes=scopes,
        protocols=("a2a", "mcp"),
        attributes=attributes,
    )


#: The deployed fleet, keyed by name. An UNDECLARED jurisdiction is modelled by passing "".
FLEET: tuple[AiSystemCard, ...] = (
    _card(
        "credit-decision-copilot",
        ("credit-scoring", "customer-facing-assistant"),
        "SG;HK",
        description="Assists a credit officer with a creditworthiness recommendation.",
    ),
    _card(
        "hr-cv-screener",
        ("employment-screening",),
        "AU",
        description="Ranks job applications for a recruiter.",
    ),
    _card(
        "social-scoring-pilot",
        ("social-scoring",),
        "SG",
        lifecycle="draft",
        description="A pilot scoring citizens by behaviour (a prohibited practice).",
    ),
    _card(
        "market-insights-chatbot",
        ("chatbot",),
        "SG",
        description="Answers staff questions about market data.",
    ),
    _card(
        "internal-reporting-helper",
        ("internal-reporting",),
        "SG",
        description="Formats internal management reports.",
    ),
    _card(
        "undeclared-analytics",
        (),
        "SG",
        lifecycle="draft",
        description="An analytics system whose use scopes were never declared on the card.",
    ),
    # model-risk-validation's own registered card, so this pack governs the wave's first repo (slice
    # 8).
    _card(
        "model-risk-validation",
        ("creditworthiness-assessment", "aml-transaction-monitoring"),
        "SG",
        owner="model-risk@bank.example",
        description="model-risk-validation: quantitative model-risk validation copilot.",
    ),
    # A card whose free-text description carries a planted identifier, for the redaction proofs.
    # The description flows into the card's citation snippet, so redact-before-audit must mask it.
    _card(
        "gamma-analytics-copilot",
        ("credit-scoring",),
        "SG",
        description="Credit analytics for Gamma LLP; contact NRIC S1234567D (FICTIONAL).",
    ),
    # A card whose NAME carries a planted identifier, for the LOCATOR half of the same proof.
    # `AiSystemCard.citation()` builds source_id=f"hrz3:agent:{name}" and title=f"Registry card:
    # {name}", so a registry that names a system after the case it was built for puts the
    # identifier in two fields that look structural and are not. Naming a system this way is a
    # mistake an upstream registry makes, not a shape this pack may assume away: the fields are
    # free text with a key-shaped name.
    _card(
        "delta-analytics-copilot-nric-S1234567D",
        ("credit-scoring",),
        "SG",
        description="Credit analytics for Delta Pte Ltd (FICTIONAL).",
    ),
)


def _obl(
    oid: str,
    title: str,
    framework: str,
    min_tier: RiskTier,
    jurisdiction: str,
    required: tuple[str, ...],
) -> KitObligation:
    """One fixture obligation as an ``obligation-register-kit`` record (the
    obligations-control-mapping wire shape).

    The classifying facts the applicability engine reads travel in the kit record's
    ``attributes`` tuple, exactly as a real obligations-control-mapping feed carries them; the local
    adapter translates
    the kit record into a vertical :class:`ObligationRef` through the shared
    :func:`obligation_to_ref`, so the domain never depends on the kit.
    """
    return KitObligation(
        id=oid,
        title=title,
        text=title,
        citation=KitCitation(source_id=f"rgc7:obligation:{oid}", title=title),
        attributes=(
            ("framework", framework),
            ("min_tier", min_tier.value),
            ("jurisdiction", jurisdiction),
            ("required_evidence", ";".join(required)),
        ),
    )


#: The obligations-control-mapping graph fixture, as kit records spanning frameworks and tiers.
KIT_OBLIGATIONS: tuple[KitObligation, ...] = (
    _obl(
        "eu-art9",
        "EU AI Act Art. 9 risk-management system",
        "eu-ai-act",
        RiskTier.HIGH,
        "",
        ("risk-assessment", "eval-report"),
    ),
    _obl(
        "eu-art11",
        "EU AI Act Art. 11 technical documentation",
        "eu-ai-act",
        RiskTier.HIGH,
        "",
        ("technical-documentation",),
    ),
    _obl(
        "eu-art14",
        "EU AI Act Art. 14 human oversight",
        "eu-ai-act",
        RiskTier.HIGH,
        "",
        ("oversight-procedure", "audit-trail"),
    ),
    _obl(
        "eu-art50",
        "EU AI Act Art. 50 transparency to natural persons",
        "eu-ai-act",
        RiskTier.LIMITED,
        "",
        ("transparency-notice",),
    ),
    _obl(
        "eu-art5",
        "EU AI Act Art. 5 prohibited practice",
        "eu-ai-act",
        RiskTier.PROHIBITED,
        "",
        (),
    ),
    _obl(
        "feat-fairness",
        "MAS FEAT fairness assessment",
        "feat",
        RiskTier.HIGH,
        "SG",
        ("fairness-assessment",),
    ),
    _obl(
        "hkma-consumer",
        "HKMA consumer-protection controls",
        "hkma",
        RiskTier.HIGH,
        "HK",
        ("audit-trail",),
    ),
    _obl(
        "apra-cps230",
        "APRA CPS 230 operational-resilience attestation",
        "apra",
        RiskTier.HIGH,
        "AU",
        ("operational-resilience-attestation",),
    ),
)

#: The vertical view, derived by translating each kit record. The translation happens once, at
#: import, which is what makes the kit a genuinely consumed dependency of the offline gate.
OBLIGATIONS: tuple[ObligationRef, ...] = tuple(obligation_to_ref(o) for o in KIT_OBLIGATIONS)

OBLIGATIONS_BY_ID: dict[str, ObligationRef] = {o.id: o for o in OBLIGATIONS}


def _evidence(
    eid: str,
    kind: str,
    obligation_ids: tuple[str, ...],
    detail: str,
) -> EvidenceItem:
    return EvidenceItem(
        id=eid,
        kind=kind,
        obligation_ids=obligation_ids,
        detail=detail,
        citation=Citation(source_id=f"hrz:evidence:{eid}", title=f"{kind}: {eid}"),
    )


#: Harvested evidence per system. Deliberately incomplete for some systems so the sufficiency
#: engine surfaces named gaps (a missing technical-documentation, a missing oversight procedure).
EVIDENCE: dict[str, tuple[EvidenceItem, ...]] = {
    "credit-decision-copilot": (
        _evidence(
            "cdc-eval",
            "eval-report",
            ("eu-art9",),
            "model-quality-gate eval run: passed the bundle.",
        ),
        _evidence(
            "cdc-audit", "audit-trail", ("eu-art14", "hkma-consumer"), "agent-observability trail."
        ),
        _evidence(
            "cdc-fair", "fairness-assessment", ("feat-fairness",), "MAS FEAT fairness review."
        ),
        # No risk-assessment (art9 PARTIAL), no technical-documentation (art11 INSUFFICIENT),
        # no oversight-procedure (art14 PARTIAL).
    ),
    "hr-cv-screener": (
        _evidence("hr-doc", "technical-documentation", ("eu-art11",), "Model card and datasheet."),
        # art9 and art14 have no evidence at all: INSUFFICIENT.
    ),
    "model-risk-validation": (
        _evidence("mrm-eval", "eval-report", ("eu-art9",), "model-quality-gate eval evidence."),
        _evidence("mrm-risk", "risk-assessment", ("eu-art9",), "Validation risk assessment."),
        _evidence("mrm-audit", "audit-trail", ("eu-art14",), "agent-observability trail."),
        _evidence("mrm-ovr", "oversight-procedure", ("eu-art14",), "Human oversight SOP."),
        _evidence("mrm-doc", "technical-documentation", ("eu-art11",), "Technical documentation."),
        _evidence("mrm-fair", "fairness-assessment", ("feat-fairness",), "FEAT fairness review."),
    ),
}


def evidence_for(system: str) -> tuple[EvidenceItem, ...]:
    """Harvested evidence for one system (empty when none has been recorded)."""
    return EVIDENCE.get(system, ())


#: The AI-Act / FEAT rule knowledge base the narrative grounds against, keyed by query token.
_KB: tuple[tuple[str, Citation], ...] = (
    (
        "high",
        Citation(
            source_id="kb:eu-ai-act:annex-iii",
            title="EU AI Act Annex III (high-risk uses)",
            snippet="Systems used for creditworthiness and employment are high-risk.",
        ),
    ),
    (
        "prohibited",
        Citation(
            source_id="kb:eu-ai-act:art5",
            title="EU AI Act Art. 5 (prohibited practices)",
            snippet="Social scoring by public authorities is prohibited.",
        ),
    ),
    (
        "limited",
        Citation(
            source_id="kb:eu-ai-act:art50",
            title="EU AI Act Art. 50 (transparency)",
            snippet="Users must be informed they are interacting with an AI system.",
        ),
    ),
    (
        "feat",
        Citation(
            source_id="kb:mas:feat",
            title="MAS FEAT principles",
            snippet="Fairness, ethics, accountability and transparency for AIDA in finance.",
        ),
    ),
    (
        "minimal",
        Citation(
            source_id="kb:eu-ai-act:recital",
            title="EU AI Act (minimal-risk systems)",
            snippet="Minimal-risk systems carry voluntary codes of conduct only.",
        ),
    ),
)


def knowledge_base(query: str) -> tuple[Citation, ...]:
    """Return every KB snippet whose token appears in ``query`` (case-insensitive)."""
    lowered = query.lower()
    return tuple(citation for token, citation in _KB if token in lowered)


#: The compliance-advisory horizon change feed fixture (formerly the regulatory change manager
#: corpus movements).
CHANGES: tuple[RegChange, ...] = (
    RegChange(
        id="chg-2026-eu-credit",
        title="EU AI Act guidance clarifies creditworthiness as high-risk",
        frameworks=("eu-ai-act",),
        scopes=("credit-scoring", "creditworthiness-assessment"),
        detail="Reclassification guidance affecting credit systems.",
        citation=Citation(source_id="rsk1:change:chg-2026-eu-credit", title="EU credit guidance"),
    ),
    RegChange(
        id="chg-2026-feat-refresh",
        title="MAS refreshes FEAT fairness expectations",
        frameworks=("feat",),
        scopes=("credit-scoring", "customer-facing-assistant"),
        detail="Updated FEAT fairness assessment expectations.",
        citation=Citation(source_id="rsk1:change:chg-2026-feat-refresh", title="FEAT refresh"),
    ),
)
