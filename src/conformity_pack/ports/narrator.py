"""NarratorPort: the model seam that PHRASES a conformity narrative (never computes one).

Every consequential number and verdict is produced by the pure engines; the narrator only
restates them in prose. This port is the one place a generation model is called, and it is
deliberately narrow: it takes a fully-formed prompt (built by :mod:`..domain.prompts` from engine
facts) and returns the model's raw reply, which the service then SCHEMA-VALIDATES and discards on
failure. With the local stub bound, the reply is deterministic, so the pack's figures are
identical whether or not a real model is reachable.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class NarratorPort(Protocol):
    def narrate(self, prompt: str) -> str:
        """Return the model's raw reply to ``prompt`` (a JSON object the caller then validates)."""
        ...
