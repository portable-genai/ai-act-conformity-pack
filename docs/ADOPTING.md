# Adopting this repo as your base

This repository (Rgc14, the AI Act Conformity Pack) is a **common base** that a bank or other
regulated institution forks to build its own **AI-system conformity engine**: a service that
classifies a registered AI system into a risk tier from its declared card, decides which
obligations bind it cell by cell, checks whether the harvested evidence is sufficient, and emits
a narrated conformity pack that a second line can read. It ships a reusable hexagonal core (a
pure-stdlib domain, typed ports, three swappable adapter profiles, a green offline gate) plus a
fully worked EU AI Act / FEAT / HKMA / APRA / JFSA vertical you can keep, retune, or replace with
your own framework set.

This guide is the step-by-step for making it yours. It has two halves: a **mechanical rebrand**
(one script) and the **human decisions** the script cannot make for you.

> Related reading: [`ARCHITECTURE.md`](../ARCHITECTURE.md) (the port table and topology),
> [`CONTRIBUTING.md`](../CONTRIBUTING.md) (adding an adapter, adding a port), the
> [`faq/`](faq/) directory, [`model-card.md`](model-card.md) (the model boundary),
> [`practices-audit.md`](practices-audit.md) (the per-check verdict).

---

## 1. What you keep vs what you rewrite

The core is hexagonal, and the boundary between reusable machinery and the conformity vertical is
a physical module split with an enforced dependency direction (practices-audit check A7).
`domain/kernel.py` owns the vertical-neutral contracts and imports nothing from the vertical, so
you can import it without loading a line of AI Act logic; `domain/models.py` holds only the Rgc14
artifacts and re-exports every kernel name.

| Layer | Where | For a new framework set |
|---|---|---|
| **Vertical-neutral machinery** | `domain/kernel.py` (`Citation`, `AuditEvent`, `Severity`, `Decision`, `utcnow`), `domain/errors.py`, every Protocol in `ports/`, the container wiring in `config.py` | keep untouched |
| **Policy (your numbers and sets)** | the rule packs in `domain/packs.py` (`RISK_TIER_PACKS`, the framework scope sets), the jurisdiction list in `domain/pii.py`, the metric thresholds in `eval/run_eval.py` | change deliberately (see section 4) |
| **Vertical (the artifacts themselves)** | the Rgc14 models in `domain/models.py` (`AiSystemCard`, `TierVerdict`, `ApplicabilityCell`, `SufficiencyVerdict`, `ConformityResult`), the four engines (`risk_tier.py`, `applicability.py`, `sufficiency.py`, `horizon_recheck.py`), `domain/prompts.py`, the local fixtures and the eval golden set | rewrite for your framework |

If your product is another *classification plus obligation-mapping* gate, most of the hexagon,
the three profiles, the deterministic-verdict pattern, the eval gate and the Hrz7 review routing
transfer directly; you replace the rule packs and the obligation source, and retune the policy
sets and the taxonomy.

## 2. Core-vs-adopter-owned files (so upstream merges stay mechanical)

Upstream keeps evolving these; avoid diverging from them so you can pull fixes cleanly:

- **Upstream-owned** (take our changes): the vertical-neutral machinery listed above, `ports/`,
  `tests/contract/`, the eval harness mechanics (`eval/run_eval.py`), the CI workflows, the
  hexagon wiring (`config.py` `Container`) and the deploy stack in `infra/terraform/`.
- **Adopter-owned** (yours; expect to edit): `config/settings.yaml` *values*, the rule packs in
  `domain/packs.py`, the local fixtures and the golden eval dataset, `adapters/onprem/*`, UI
  theming and branding, `infra/terraform/terraform.tfvars`, and the regulator crosswalk section
  of `COMPLIANCE.md`.

Track upstream via git tags; rebase your adopter-owned changes onto each release rather than
merging `main` continuously.

## 3. The mechanical rebrand (one script)

`scripts/rename_fork.py` rewrites the package name (`conformity_pack`, which is also the console
script), the `CFP_` env prefix (including the bare `CFP` that
`infra/terraform/render.tf.json` carries so Terraform sets the same variable names on the
service), the cloud resource stem (`rgc14-svc`, the Terraform `name_prefix`) and the distribution
/ git id in one pass. Preview first, then apply:

```bash
# Preview (writes nothing):
python scripts/rename_fork.py --package acme_ai_act_gate --env-prefix ACME \
    --resource acme-aiact --dry-run

# Apply:
python scripts/rename_fork.py --package acme_ai_act_gate --env-prefix ACME \
    --resource acme-aiact --yes

# Then recreate the environment (the distribution name changed) and prove it is green:
python3.12 -m venv .venv && source .venv/bin/activate
make install
make gate
```

`--dist` defaults to the `--resource` value; pass it explicitly when your git id differs from
your resource stem. `--resource` is validated against the same regex the Terraform
`name_prefix` variable enforces, so a stem the stack would refuse fails here instead of at plan
time. Add `--include-docs` to sweep Markdown prose too. The catalog id `Rgc14` is left alone
unless you pass `--catalog-id`, so a fork stays traceable to the entry it descends from. The
script deliberately does NOT touch the human decisions below.

## 4. The human decisions (the script can't make these)

1. **Region / residency.** The build defaults to `asia-southeast1` (MAS / Singapore), chosen once
   and shared: `config/settings.yaml:region`, `infra/terraform/render.tf.json:render_region` and
   the Terraform `region` / `allowed_regions` pair. Set all of them to your in-country region,
   and re-run the residency tests in `infra/terraform/production_edge.tftest.hcl`, which refuse a
   region outside the allowlist at plan time. See [`runbook.md`](runbook.md).
2. **Identity / IdP.** This repo owns no login flow: the `gcp` profile verifies the IAP-injected
   assertion at the edge, `local` uses seeded dev personas, and `onprem` is a client IdP
   placeholder. Wire your issuer on the deployed service (auth is configured ON the service, not
   in this code) and set `CFP_IAP_AUDIENCE`. An unset or emptied
   audience refuses every caller rather than verifying without one.
3. **The rule packs (your classification policy).** `domain/packs.py` holds the packs as DATA:
   the scope sets that map a declared system to an EU AI Act tier, and the framework scope sets
   that drive the FEAT / HKMA / APRA / JFSA dimensions. The default pack `"eu-ai-act"` is a
   REFERENCE, not your legal position. Replace the scope vocabulary with your own taxonomy and
   keep the two invariants the engine encodes: an under-declared card tiers CONDITIONAL rather
   than MINIMAL, and an ambiguous scope takes the stronger tier.
4. **The obligation source.** The applicability engine reads the obligation graph over
   `ObligationsPort`. Offline it serves fixtures; under `gcp` it reads Rgc7 at
   `RGC7_OBLIGATIONS_URL`. Point it at your own obligation register, or keep Rgc7 and load your
   obligations into it, but do not build a second register here.
5. **Policy numbers your compliance function owns.** The jurisdiction list in `domain/pii.py`
   (which national PII rows are scanned, and in what order), the `required_evidence` kinds each
   obligation record declares (which is what `domain/sufficiency.py` measures a system against,
   so it is set in your obligation register rather than here), and the eval thresholds in
   `eval/run_eval.py` (`tier_accuracy`, `conditional_accuracy`, `pii_safety`). The in-repo ones
   are module-level today rather than a `policy:` settings section (practices-audit check B4);
   change them deliberately and add a test that pins your values.
6. **Reference data is fictional.** Every fixture (`tests/fixtures/sample_cases.py`,
   `eval/datasets/golden_cases.jsonl`) and the local obligation corpus use obviously fake system
   names and `.example` domains. Replace them with your own synthetic data. **Do not run against
   a real AI-system inventory without your own security and model-risk sign-off.**
7. **Eval golden set.** Rebuild `eval/datasets/golden_cases.jsonl` for your framework: a fork
   inherits a green gate that measures the WRONG ruleset until you do. The gate structure and the
   strict `pii_safety >= 0.99` metric are generic; the golden cases are yours.
8. **Deployment posture.** Review the Dockerfile (digest-pinned base, non-root uid 10001),
   `infra/terraform/` (Org Policy, CMEK, a dry-run-first VPC-SC perimeter, the locked WORM log
   bucket) and the loopback-by-default binding before you expose anything. The WORM lock is
   irreversible: confirm `retention_days` before the first apply.

## 5. Do not duplicate the platform

This repo is one system in a catalog of composable GRC systems. Several concerns it *touches* are
owned by sibling platform services, and you should integrate rather than rebuild them (see
[`faq/features-faq.md`](faq/features-faq.md) for the full map). The `gcp` profile's adapters are
already thin HTTP clients to them:

- **Rgc7** obligations and control mapping: the obligation graph the applicability engine reads,
  via `ObligationsPort` (`RGC7_OBLIGATIONS_URL`). This repo decides applicability; it does not
  own the register.
- **Rsk1** compliance assistant: the regulatory corpus and the horizon feed, via `RetrievalPort`
  and `HorizonPort` (`RSK1_HORIZON_URL`). A corpus change arrives as a `RegChange` and
  `domain/horizon_recheck.py` decides which systems it reopens.
- **Hrz3** agent registry: this agent publishes its A2A card at
  `/.well-known/agent-card.json`; register it rather than inventing a discovery mechanism.
- **Hrz4** AI-quality / model-risk gate: owns promotion. `eval/run_eval.py --mode gate` is the
  client half and refuses to run off the managed profile; the offline smoke mode mirrors the
  thresholds.
- **Hrz5** observability plus immutable WORM audit: audit events and trace spans go to it via
  `AuditSinkPort` and `ObservabilityTracerPort`.
- **Hrz7** human-review / maker-checker console: every `requires_human_review` escalation is
  routed to it over the shared `review-kit` (rule R8); you wire your endpoint
  (`HRZ_HUMAN_REVIEW_URL`), you do not re-implement the console.

The guardrail gateway (Hrz1) is **not** integrated today. It becomes mandatory the moment
untrusted free text (a supplier-written system description, say) reaches the narrator: see rule
R1 in [`../COMPLIANCE.md`](../COMPLIANCE.md).

## 6. Adoption checklist

- [ ] Ran `scripts/rename_fork.py`, recreated the venv, `make gate` green.
- [ ] Set the region in all three places (settings, `render.tf.json`, tfvars) and re-ran the
      Terraform residency tests.
- [ ] Wired your IdP audience on the deployed service (this repo owns no login flow).
- [ ] Replaced the rule packs in `domain/packs.py` with your framework, keeping the
      CONDITIONAL-not-MINIMAL and stronger-tier-wins invariants.
- [ ] Pointed `ObligationsPort` at your obligation register (or loaded yours into Rgc7).
- [ ] Owned the policy numbers (PII jurisdictions, required evidence kinds, eval thresholds) with
      your compliance function.
- [ ] Replaced every synthetic fixture and the local obligation corpus.
- [ ] Rebuilt the eval golden set for your framework.
- [ ] Reviewed the deploy posture (Dockerfile, Terraform, `retention_days`, bind address).
- [ ] Wired your Hrz7 review endpoint and decided which sibling services you integrate vs stub.
- [ ] Read [`model-card.md`](model-card.md) and closed its remaining controls before enabling the
      managed narrator.
- [ ] Recorded your baseline upstream tag so you can take future fixes.
