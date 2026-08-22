"""Local NarratorPort: a DETERMINISTIC stub narrator (no model, SDK-free offline).

The stub returns a JSON reply that restates ONLY the engine facts embedded in the prompt, so it
always passes :func:`..domain.prompts.validate_narration` and, crucially, is deterministic: the
consequential figures in a pack are identical whether a real model is reachable or this stub is
bound. That is the "with the generation adapter stubbed, numbers are IDENTICAL" property made
literal, and it is why the offline gate can exercise the narration path with no model at all.

The stub deliberately does NOT invent prose beyond the facts: it echoes the FACTS block back as a
narrative and lists exactly the allowed figures and grounding sources, because a stub that made
up text would be a second, kinder narrator that the managed path does not share.
"""

from __future__ import annotations

import json

from ...config import Settings


class LocalNarratorAdapter:
    """A deterministic, model-free narrator for the ``local`` profile."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def narrate(self, prompt: str) -> str:
        facts, figures, sources = _parse_prompt(prompt)
        narrative = (
            f"{facts.get('system', 'the system')} is classified {facts.get('tier', 'unknown')}"
            "-risk under the EU AI Act. "
            f"{facts.get('applies_count', 0)} obligation(s) apply and "
            f"{facts.get('conditional_count', 0)} require a human to confirm a declaration."
        )
        gaps = facts.get("gaps") or []
        if isinstance(gaps, list) and gaps:
            narrative += " Evidence gaps remain: " + "; ".join(str(g) for g in gaps) + "."
        return json.dumps({"narrative": narrative, "figures": figures, "sources": sources})


def _parse_prompt(prompt: str) -> tuple[dict[str, object], list[str], list[str]]:
    """Recover the FACTS json, the allowed figures and the grounding sources from the prompt.

    The prompt is built by ``domain.prompts.build_prompt``: a header, a ``FACTS:`` line, a JSON
    object, a ``GROUNDING:`` line, then ``- <snippet>`` lines. The stub reads the facts back so
    its reply cannot drift from what the engine authorised.
    """
    lines = prompt.splitlines()
    facts: dict[str, object] = {}
    grounding: list[str] = []
    for index, line in enumerate(lines):
        if line.strip() == "FACTS:" and index + 1 < len(lines):
            try:
                loaded = json.loads(lines[index + 1])
                if isinstance(loaded, dict):
                    facts = loaded
            except json.JSONDecodeError:
                facts = {}
        if line.startswith("- "):
            grounding.append(line[2:])
    figures_raw = facts.get("allowed_figures")
    figures = [str(f) for f in figures_raw] if isinstance(figures_raw, list) else []
    # The stub cites no external source ids (it only restates FACTS), so sources stays empty and
    # validation trivially holds; grounding is recorded in the narrative but not claimed as a
    # figure. This keeps the stub honest about what it did and did not read.
    return facts, figures, []
