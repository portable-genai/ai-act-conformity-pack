"""The horizon re-check: a replayed change reopens exactly the affected systems, no others."""

from __future__ import annotations

from conformity_pack.adapters.local import fleet_fixtures
from conformity_pack.domain.horizon_recheck import affected_systems, change_affects
from conformity_pack.domain.models import RegChange
from conformity_pack.domain.risk_tier import classify


def _verdicts() -> dict[str, object]:
    return {card.name: classify(card) for card in fleet_fixtures.FLEET}


def test_a_credit_change_reopens_only_the_credit_systems() -> None:
    verdicts = _verdicts()
    change = RegChange(id="c", title="t", frameworks=("eu-ai-act",), scopes=("credit-scoring",))
    affected = affected_systems(change, fleet_fixtures.FLEET, verdicts)  # type: ignore[arg-type]
    assert "credit-decision-copilot" in affected
    assert "market-insights-chatbot" not in affected
    assert "internal-reporting-helper" not in affected


def test_a_change_in_an_unsubscribed_framework_reopens_nothing_for_that_system() -> None:
    verdicts = _verdicts()
    # A chatbot is not subject to FEAT, so a FEAT change does not reopen it.
    card = fleet_fixtures.FLEET[3]
    assert card.name == "market-insights-chatbot"
    change = RegChange(id="c", title="t", frameworks=("feat",), scopes=("chatbot",))
    assert change_affects(change, card, verdicts[card.name]) is False  # type: ignore[index]


def test_a_framework_wide_change_with_no_scopes_reopens_every_subscribed_system() -> None:
    verdicts = _verdicts()
    change = RegChange(id="c", title="t", frameworks=("eu-ai-act",), scopes=())
    affected = affected_systems(change, fleet_fixtures.FLEET, verdicts)  # type: ignore[arg-type]
    # Every system is subject to eu-ai-act, so all are reopened.
    assert set(affected) == {card.name for card in fleet_fixtures.FLEET}
