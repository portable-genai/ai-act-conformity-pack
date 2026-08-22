"""The deterministic risk-tier engine: correct tiers, CONDITIONAL over silent-minimal, replay."""

from __future__ import annotations

from conformity_pack.domain.models import AiSystemCard, RiskTier
from conformity_pack.domain.risk_tier import classify


def _card(scopes: tuple[str, ...], jurisdictions: str = "SG") -> AiSystemCard:
    attrs = (("jurisdictions", jurisdictions),) if jurisdictions else ()
    return AiSystemCard(name="s", scopes=scopes, attributes=attrs)


def test_a_prohibited_scope_takes_the_prohibited_tier() -> None:
    verdict = classify(_card(("social-scoring",)))
    assert verdict.tier is RiskTier.PROHIBITED
    assert verdict.conditional is False


def test_a_high_risk_use_is_high() -> None:
    assert classify(_card(("credit-scoring",))).tier is RiskTier.HIGH


def test_a_transparency_use_is_limited() -> None:
    assert classify(_card(("chatbot",))).tier is RiskTier.LIMITED


def test_an_unlisted_use_is_minimal() -> None:
    assert classify(_card(("internal-reporting",))).tier is RiskTier.MINIMAL


def test_no_declared_scope_is_CONDITIONAL_not_silently_minimal() -> None:
    """The adversarial under-declared card must not slip out of scope by omission."""
    verdict = classify(_card(()))
    assert verdict.conditional is True
    assert any("no use scopes are declared" in reason for reason in verdict.reasons)


def test_classification_fails_closed_to_the_higher_tier() -> None:
    """A system declaring both a prohibited and a high-risk use is prohibited, the stronger tier."""
    verdict = classify(_card(("credit-scoring", "social-scoring")))
    assert verdict.tier is RiskTier.PROHIBITED


def test_feat_applies_only_when_deployed_in_singapore() -> None:
    in_sg = classify(_card(("credit-scoring",), jurisdictions="SG"))
    not_sg = classify(_card(("credit-scoring",), jurisdictions="AU"))
    assert any(d.framework == "feat" and d.applies for d in in_sg.dimensions)
    assert any(d.framework == "feat" and not d.applies for d in not_sg.dimensions)


def test_classification_is_replayable() -> None:
    card = _card(("credit-scoring", "customer-facing-assistant"), "SG;HK")
    assert classify(card) == classify(card)
