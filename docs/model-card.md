# Model card: AI Act Conformity Pack (Rgc14)

This is a STARTER model card. It records the model boundary as built and the controls that must
be completed before a managed deployment. The deterministic engines are the system of record; the
model is a bounded, replaceable component.

## What the model does, and does not do

- **Does**: phrase a conformity narrative for a verdict the engines have ALREADY produced. It
  receives a prompt built by `domain/prompts.build_prompt` from engine facts plus the grounding
  snippets it may restate, and returns a JSON object with a narrative, the figures it used and
  the sources it cites.
- **Does NOT**: produce any tier, matrix cell, sufficiency verdict, gap or escalation. The risk
  tier (`domain/risk_tier.py`), obligation applicability (`domain/applicability.py`), evidence
  sufficiency (`domain/sufficiency.py`) and the horizon re-check (`domain/horizon_recheck.py`)
  are pure stdlib over declared facts. With the local stub narrator bound, every consequential
  field of a pack is identical, so a model change cannot move a figure.

## Boundary and validation

- The model is reachable through exactly one port, `ports/narrator.py`, whose whole surface is
  `narrate(prompt: str) -> str`. There is no second model seam.
- The reply is parsed by `domain/prompts.validate_narration` and REJECTED unless every figure it
  cites is one the engine produced and every source it cites was retrieved or is an engine row. A
  rejected reply is discarded, never repaired, and the service falls back to
  `deterministic_narrative`, which is grounded by construction.
- Personal data is masked before the audit write, before a review payload leaves the process, and
  before a tool result can enter a model's context (`domain/pii.py`, `agent/tools.py`,
  `adapters/_review_payload.py`).
- Every consequential result sets `requires_human_review` and is routed to Hrz7 (rule R8) in the
  same call; nothing auto-executes.

## Adapters and profiles

| Profile | Narrator adapter | Behaviour |
|---|---|---|
| `local` | `adapters/local/narrator.py` | Deterministic stub: echoes the FACTS block back as a narrative with exactly the allowed figures and sources. SDK-free, no model. |
| `gcp` | `adapters/gcp/narrator.py` | Gemini via the Google GenAI SDK, imported lazily inside the method. The model id comes from `narrator_model` in `config/settings.yaml` (`CFP_NARRATOR_MODEL`, default `gemini-2.5-flash`). |
| `onprem` | `adapters/onprem/narrator.py` | Fail-fast placeholder: raises, naming the client-hosted model gateway to bind. |

The stub deliberately does not invent prose beyond the facts. A stub that wrote freely would be a
second, kinder narrator that the managed path does not share, and the offline gate would stop
exercising the validation the managed path depends on.

## Remaining controls (TODO, repo owner)

- **Model id, version and region** (P-07): `gemini-2.5-flash` is a default, not a pin. Confirm the
  id is served in your deployment region, pin the exact model and version, and record it here.
  Gemini model ids are regional and an unavailable one fails at call time rather than at boot.
- **Budget, rate limit and a kill switch** (P-10, P-11): there is no per-tenant token budget, no
  request rate limit, and no switch that forces deterministic-only operation. The fallback path
  exists (a rejected reply already yields the deterministic narrative), but nothing yet lets an
  operator disable the model deliberately.
- **Evaluation of the live model**: the offline eval scores the deterministic pipeline with the
  stub narrator against the golden cases. Add a managed-profile run, registered with the Hrz4
  promotion gate (P-08, rule R5), that scores narrative groundedness against the same golden
  cases with the real model bound.
- **Prompt-injection screening** (rule R1): the Hrz1 guardrail gateway is not bound. Screen any
  untrusted free text (a supplier-written system description, an uploaded evidence summary)
  before it reaches `build_prompt`, and fail closed to deterministic-only when the screen is
  unavailable.
- **Reasoning trace**: `COMPLIANCE.md` P-07 records that a model's reasoning trace should be
  audited alongside its output. Today the audit record carries the validated narrative and its
  citations, not the prompt and reply pair.

Until these are complete the system is safe to run offline (deterministic engines plus the stub
narrator) and the managed model path is not production-cleared.
