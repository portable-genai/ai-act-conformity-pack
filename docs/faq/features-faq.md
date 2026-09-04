# Features FAQ

For a product owner, a risk lead or a delivery manager deciding what this system does, what it
refuses to do, and where its responsibility ends.

### What does it actually do?

Given a registered AI system's declared card, it produces a conformity pack in four deterministic
steps and one narrated one:

1. **Risk tier** (`domain/risk_tier.py`): set-membership of the declared use scopes against a
   named rule pack yields an EU AI Act tier plus per-framework dimensions (FEAT, HKMA, APRA,
   JFSA), each with explicit reasons.
2. **Applicability** (`domain/applicability.py`): for every (system, obligation) pair over the
   `obligations-control-mapping` obligation graph, APPLIES, NOT_APPLICABLE or CONDITIONAL, worst-wins across
   jurisdictions.
3. **Sufficiency** (`domain/sufficiency.py`): for each applying obligation, whether the harvested
   evidence covers the kinds that obligation requires. Missing evidence becomes a NAMED gap.
4. **Horizon re-check** (`domain/horizon_recheck.py`): when the regulatory corpus moves, which
   systems that change reopens, and only those.
5. **Narration** (`domain/prompts.py` plus `NarratorPort`): prose that restates the verdicts above
   for a reader. It computes nothing.

### What is deterministic, and what does the model write?

Everything consequential is deterministic. The tier, every matrix cell, every sufficiency verdict
and the escalation decision are pure stdlib over declared facts, so the same card and the same
evidence always produce the same pack. The model only phrases the narrative, and its reply is
schema-validated against the engine's own figures and sources before it is accepted; a reply that
cites a figure the engine did not compute is discarded and the deterministic narrative is used
instead. With the local stub narrator bound, the pack's figures are byte-identical. See
[`../model-card.md`](../model-card.md).

### What will it refuse to do?

- **It will not rule a system out of scope by omission.** A card that declares no use scopes is
  tiered CONDITIONAL for a human to confirm, never MINIMAL. An under-declared card cannot slip
  out of the high-risk regime by saying less.
- **It will not resolve an ambiguous scope downward.** The tier evaluation runs strongest first,
  so a scope that reads two ways takes the stronger tier.
- **It will not auto-execute a consequential result.** A consequential pack sets
  `requires_human_review` and is ROUTED to the `human-review-console` in the same call that produced it
  (rule R8), on every surface.
- **It will not answer without provenance.** Every claim carries a `Citation`.

### Which surfaces expose it?

Five, and they behave the same because they share one domain service rather than reimplementing
it: the FastAPI app (`POST /v1/assess`), the argparse CLI (`conformity_pack assess <system>`),
the agent tools (`assess_system`, `verify_audit_trail`, advertised on the A2A card at
`/.well-known/agent-card.json`), the embeddable `ui/` micro-frontend, and the eval harness. Each
routes escalations in the same call, so rule R8 does not hold on four surfaces out of five.

### What does this repo own, and what does it integrate?

| Concern | Owner | How this repo touches it |
|---|---|---|
| The obligation, policy and control graph | `obligations-control-mapping` and control mapping | read over `ObligationsPort` (`RGC7_OBLIGATIONS_URL`). This repo decides applicability; it does not keep a register. |
| The regulatory corpus and the change horizon | `compliance-advisory` | read over `RetrievalPort` and `HorizonPort` (`RSK1_HORIZON_URL`); a `RegChange` drives the re-check. |
| Agent discovery and entitlements | `agent-registry` | this agent publishes a card; the registry owns discovery. |
| Model and agent promotion | `model-quality-gate` AI quality and model risk | `eval/run_eval.py --mode gate` asks `model-quality-gate`; the offline smoke mode never promotes. |
| Traces and the immutable audit sink | `agent-observability` agent observability | `AuditSinkPort` and `ObservabilityTracerPort`. |
| Human review and maker-checker | `human-review-console` human review console | `ReviewRouterPort` over the shared `review-kit`. This repo produces escalations; it does not render a queue. |
| Prompt-injection defence and output filtering | `agent-guardrail-gateway` agent guardrail gateway | **not wired today.** It becomes mandatory the moment untrusted free text reaches the narrator (rule R1). |
| Grounded retrieval over an enterprise corpus | `enterprise-knowledge-base` | not wired today; `RetrievalPort` serves the local corpus offline. |

### Can I demo it without a cloud project?

Yes, and the demo is code rather than a deck. `make demo` runs a presenter-paced walkthrough over
eight steps (opened, routine, escalation, redaction, review queue, audit, tamper, portability) on
its own loopback server; `make demo-selftest` runs the same arc headless and asserts every
narrated claim, so a claim that stops being true fails a build rather than a meeting;
`make demo-static` renders the same audit-first panels to static HTML for screenshots.

### What is not built yet?

The honest list is [`../practices-audit.md`](../practices-audit.md) and the `TODO (repo owner)`
rows in [`../../COMPLIANCE.md`](../../COMPLIANCE.md). The two that matter most for a production
decision: the `agent-guardrail-gateway` binding (needed before untrusted text reaches the narrator), and
registering this repo's metric bundle with `model-quality-gate` so `--mode gate` has an authority to ask.
