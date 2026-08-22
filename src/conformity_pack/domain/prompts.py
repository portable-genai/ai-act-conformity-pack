"""The narration surface: prompt templates, a schema validator, and the grounded fallback.

The model's job here is deliberately small and deliberately non-consequential: it PHRASES a
conformity narrative for a verdict the engines have ALREADY produced. It never classifies, never
scores sufficiency, and never introduces a figure the engines did not compute. Everything in this
module is pure stdlib and I/O-free; the model call itself happens behind the narrator PORT.

Three pieces:

* :func:`build_prompt` : the instruction text handed to the model, carrying the engine facts and
  the grounding snippets it may restate, and nothing else.
* :func:`validate_narration` : parse the model's JSON reply and REJECT it unless every figure it
  cites is one the engine produced and every source it cites was retrieved or is an engine row.
  A reply that fails validation is discarded (the service falls back to the deterministic text),
  so a hallucinated figure can never reach a pack.
* :func:`deterministic_narrative` : the fallback, built purely from the engine facts, so it is
  grounded by construction. This is also what makes the numbers identical when the narrator
  adapter is stubbed: the consequential fields never depended on the model in the first place.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .errors import UngroundedNarrativeError
from .models import ConformityResult


@dataclass(frozen=True, slots=True)
class NarrationContext:
    """The engine facts the narrative may restate, and the closed sets it is validated against."""

    system: str
    tier: str
    conditional: bool
    applies_count: int
    conditional_count: int
    gaps: tuple[str, ...]
    allowed_figures: frozenset[str]
    allowed_sources: frozenset[str]

    @classmethod
    def from_result(
        cls, result: ConformityResult, grounding_sources: frozenset[str]
    ) -> NarrationContext:
        """Derive the closed validation sets from a computed result plus the retrieved sources."""
        figures = {
            result.tier.value,
            str(result.applies_count),
            str(result.conditional_count),
            str(len(result.gaps)),
        }
        engine_sources = {c.source_id for c in result.citations}
        return cls(
            system=result.subject,
            tier=result.tier.value,
            conditional=result.conditional,
            applies_count=result.applies_count,
            conditional_count=result.conditional_count,
            gaps=result.gaps,
            allowed_figures=frozenset(figures),
            allowed_sources=frozenset(engine_sources | grounding_sources),
        )


_PROMPT_HEADER = (
    "You are drafting the conformity-pack narrative for one deployed AI system. Restate ONLY the "
    "facts given below. Do not compute, infer or introduce any figure, tier or count that is not "
    "in the FACTS block. Cite only sources listed in GROUNDING. Reply as a single JSON object: "
    '{"narrative": str, "figures": [str], "sources": [str]}.'
)


def build_prompt(context: NarrationContext, grounding: tuple[str, ...]) -> str:
    """The instruction text for the narrator, assembled from engine facts and grounding.

    Pure string construction: no model, no I/O. The prompt hands the model the closed set of
    figures and sources it is allowed to use, which is exactly what :func:`validate_narration`
    then enforces on the reply.
    """
    facts = {
        "system": context.system,
        "tier": context.tier,
        "conditional": context.conditional,
        "applies_count": context.applies_count,
        "conditional_count": context.conditional_count,
        "gaps": list(context.gaps),
        "allowed_figures": sorted(context.allowed_figures),
    }
    lines = [
        _PROMPT_HEADER,
        "FACTS:",
        json.dumps(facts, sort_keys=True),
        "GROUNDING:",
        *(f"- {snippet}" for snippet in grounding),
    ]
    return "\n".join(lines)


def validate_narration(reply: str, context: NarrationContext) -> str:
    """Parse the model reply and return its narrative, or reject it as ungrounded.

    The reply must be a JSON object whose ``figures`` are all in the allowed set and whose
    ``sources`` are all in the allowed set. Anything else, malformed JSON, an unlisted figure, a
    fabricated source, raises :class:`UngroundedNarrativeError`, and the caller discards the
    reply. Validation is against the engine's closed sets, never against the model's own claims.
    """
    try:
        parsed = json.loads(reply)
    except (json.JSONDecodeError, TypeError) as exc:
        raise UngroundedNarrativeError("narration reply was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise UngroundedNarrativeError("narration reply was not a JSON object")

    narrative = parsed.get("narrative")
    if not isinstance(narrative, str) or not narrative.strip():
        raise UngroundedNarrativeError("narration reply carried no narrative text")

    figures = parsed.get("figures", [])
    sources = parsed.get("sources", [])
    if not isinstance(figures, list) or not isinstance(sources, list):
        raise UngroundedNarrativeError("narration figures/sources were not lists")

    stray_figures = {str(f) for f in figures} - context.allowed_figures
    if stray_figures:
        raise UngroundedNarrativeError(
            f"narration cited figures the engine never produced: {sorted(stray_figures)}"
        )
    stray_sources = {str(s) for s in sources} - context.allowed_sources
    if stray_sources:
        raise UngroundedNarrativeError(
            f"narration cited sources that were not retrieved: {sorted(stray_sources)}"
        )
    return narrative.strip()


def deterministic_narrative(result: ConformityResult) -> str:
    """The grounded fallback narrative, built purely from the engine verdict.

    Used when no narrator is bound, when the model reply fails validation, and by the offline
    gate, so a conformity pack is always producible without a model and the consequential figures
    never depend on one.
    """
    tier_clause = (
        f"{result.subject} is classified {result.tier.value}-risk under the EU AI Act"
        + (
            " (CONDITIONAL: use scopes are undeclared and must be confirmed)"
            if result.conditional
            else ""
        )
        + "."
    )
    obligations_clause = (
        f"{result.applies_count} obligation(s) apply; {result.conditional_count} could not be "
        "decided without a human confirming a declared attribute."
    )
    gap_clause = (
        "Evidence gaps: " + "; ".join(result.gaps) + "."
        if result.gaps
        else "No evidence gaps were found for the applicable obligations."
    )
    return " ".join((tier_clause, obligations_clause, gap_clause))
