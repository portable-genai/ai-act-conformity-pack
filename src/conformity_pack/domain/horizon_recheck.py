"""The AI-reg horizon re-check (pure stdlib): which systems a corpus change reopens.

compliance-advisory's horizon feed emits ``CorpusChange`` records when the regulatory corpus moves.
This module answers the deterministic question those records raise for the conformity fleet: WHICH
systems' classification and applicability a given change reopens, and only those. A change that
touches a framework a system is not subject to, and touches no scope the system declares, does not
affect it, so recomputing it would be noise.

The re-check is intentionally a pure predicate over declared facts: a replayed change flips
exactly the affected systems and no others, which is the property the eval proves.
"""

from __future__ import annotations

from .models import (
    AiSystemCard,
    RegChange,
    TierVerdict,
)


def change_affects(change: RegChange, card: AiSystemCard, verdict: TierVerdict) -> bool:
    """True when ``change`` reopens ``card``'s verdict: shared framework AND shared scope.

    Both must hold. A change is scoped to the frameworks it amends and the use scopes it renames
    or reclassifies; a system is affected only when it is subject to one of those frameworks and
    declares one of those scopes. Requiring both keeps a broad framework-wide change from
    reopening every system while a scope it never mentions is unaffected.
    """
    frameworks = frozenset(change.frameworks)
    if not frameworks & frozenset(verdict.applicable_frameworks):
        return False
    if not change.scopes:
        # A framework-wide change with no named scopes touches every system subject to it.
        return True
    return bool(frozenset(change.scopes) & frozenset(card.scopes))


def affected_systems(
    change: RegChange,
    cards: tuple[AiSystemCard, ...],
    verdicts: dict[str, TierVerdict],
) -> tuple[str, ...]:
    """Every system name ``change`` reopens, sorted, deduplicated, deterministic."""
    return tuple(
        sorted(
            card.name
            for card in cards
            if card.name in verdicts and change_affects(change, card, verdicts[card.name])
        )
    )
