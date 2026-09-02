# Adoption FAQ

For an engineering lead forking this repo as their institution's conformity base. The
step-by-step is [`../ADOPTING.md`](../ADOPTING.md); this answers the "will it hurt later?"
questions.

### How do I rebrand it for my organisation?

`scripts/rename_fork.py` rewrites the package name (`conformity_pack`, which is also the console
script), the `CFP_` env prefix (including the bare token that
`infra/terraform/render.tf.json` carries, so Terraform sets the same variable names on the
service), the Terraform `name_prefix` resource stem (`rgc14-svc`) and the distribution / git id
in one pass. Preview with `--dry-run`, apply with `--yes`, then recreate the venv,
`make install`, and run `make gate`. The catalog id `Rgc14` is left alone unless you pass
`--catalog-id`, so a fork stays traceable to the entry it descends from. The script does the
mechanical rename; the human decisions (rule packs, region, IdP, obligation source, eval golden
set) are the checklist in `ADOPTING.md`.

### If several institutions fork this, how does each take upstream fixes?

Track upstream via **git tags**. The repo declares a core-vs-adopter-owned boundary
(`ADOPTING.md` section 2): upstream owns `domain/kernel.py`, `ports/`, `tests/contract/`, the
eval harness mechanics, CI and the Terraform stack; you own `config/settings.yaml` values, the
rule packs in `domain/packs.py`, the fixtures and golden set, `adapters/onprem/*`, UI theming and
`terraform.tfvars`. Rebase your adopter-owned changes onto each release rather than merging
`main` continuously, so conflicts stay in files you were told to expect.

### What do we have to supply that is not in this repo?

Four things, and none of them is code here:

1. **The rule packs.** `domain/packs.py` ships the reference `"eu-ai-act"` pack. Its scope
   vocabulary is illustrative, not a legal enumeration; your compliance function owns the real
   one.
2. **The obligation register.** The applicability engine reads it over `ObligationsPort`. Point
   it at Rgc7 (`RGC7_OBLIGATIONS_URL`) with your obligations loaded, or at your own register.
   Do not build a second one here.
3. **The evidence feed.** `EvidencePort` harvests the artefacts sufficiency is measured against
   (Hrz4 eval reports, Hrz5 audit trails). Offline it serves fixtures.
4. **The review console.** An Hrz7 deployment reachable at `HUMAN_REVIEW_URL`. The managed
   router REFUSES to swallow an escalation when this is empty, so a fork cannot ship rule R8
   unwired and green.

### How do I add a new outbound dependency (a new port)?

There is a fixed touch list and a contract test that enforces it. A port must be registered in
FIVE places or it runs with no enforcement at all: `ports/__init__.py` (`PORT_PROTOCOLS`),
`config.DEFAULT_BINDINGS`, a `Container` accessor, `config/settings.yaml`, and a `PortCase` in
`tests/contract/canonical.py`. Then bind it in all three families.
`tests/contract/test_port_parity.py` asserts set equality across the five. See
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md).

### Can I retune the classification policy without touching engine code?

Partly today, and this is stated honestly. The rule packs are already **data**
(`RISK_TIER_PACKS` in `domain/packs.py`: frozen mappings of `frozenset`s, looked up by name), so
adding or retuning a pack is not an engine edit. But there is **not yet** a `policy:` block in
`config/settings.yaml` that a deployment could carry its own pack in without a code change, and
the eval thresholds and the PII jurisdiction list are module constants. That is the open B4 item
in [`../practices-audit.md`](../practices-audit.md). If your compliance function must own these
as configuration, plan that small addition as part of adoption.

### Does the gate run for my fork out of the box?

Yes. `make gate` is offline, credential-free and network-free (ruff, ruff format, mypy strict,
the whole suite except integration, and the eval), and the CI workflow references no `secrets.`,
so a fork's build is green immediately. You add secrets only when you wire the `gcp` profile.
Note the eval measures the REFERENCE rule packs and golden cases until you rebuild them for your
own framework; that is an explicit adoption step, not a silent pass.

### Will the demo rot after I diverge?

It is guarded, and the guard is inside the gate. A demo step lives in `demo.STEPS` and in
`walkthrough.CHECKS`, and `tests/unit/test_demo_surface.py` holds the two equal, so a claim the
demo makes but nobody verifies cannot exist. `make demo-selftest` runs the whole arc headless
over the real loopback server and exits non-zero when a claim stops being true; the hosted
check runs it and `make portability` on every pull request and every push to main. If
you diverge, keep the step keys and the `facts` dict the checks read.

### The eval reports 1.000. Should we believe it?

Only because each metric is proved able to report something else.
`tests/unit/test_not_falsely_green.py` hands the safety metric a planted mutant and fails the
build if it still passes. A metric that cannot go red is not a metric. The scores are also
measured against the REFERENCE golden set, which is synthetic: rebuilding it for your framework
is adoption step 7.

### What is still open?

[`../practices-audit.md`](../practices-audit.md) carries the per-check verdict and the work list.
The two that matter most before production: binding the Hrz1 guardrail gateway (needed before
untrusted free text reaches the narrator), and registering this repo's metric bundle with Hrz4 so
`eval/run_eval.py --mode gate` has an authority to ask. The Terraform stack is written, validated
and tested against a mocked provider; it has never been applied.
