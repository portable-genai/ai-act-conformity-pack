# Portability FAQ

For architecture, cloud governance and exit planning. The question underneath all of these is
"how do we leave, and how do we know the answer is true today rather than on the day it was
written?"

### What is the lock-in surface?

Every outbound dependency is a `@runtime_checkable` Protocol in `ports/` (audit, evidence,
horizon, identity, matrix store, narrator, obligations, observability, evaluation, registry,
retrieval, review router), bound per profile from `config/settings.yaml`. There is no cloud SDK
import anywhere in `domain/`, and the managed adapters import their SDK LAZILY inside the method,
so the other two families import with no SDK installed at all.

### What are the three profiles?

| Profile | What it is | Who it is for |
|---|---|---|
| `local` | SDK-free offline stack: seeded dev personas, a hash-chained SQLite WORM audit log, a fixture obligation corpus, a deterministic stub narrator | dev, test, CI, and the offline demo |
| `gcp` | the managed stack: IAP identity, Cloud Logging WORM, Gemini narration, HTTP clients to the sibling services | a managed deployment |
| `onprem` | fail-fast `NotImplementedError` placeholders | the sovereign exit: a client binds its own in-country implementations here |

`CFP_PROFILE` selects the family. Unset means the offline adapters
bind but nobody chose them, which withdraws every relaxation rather than granting one.

### Is the portability claim tested, or just documented?

Tested, three ways, all in the offline gate or one command:

- `tests/contract/test_port_parity.py` asserts set equality across all five homes of a port (the
  `PORT_PROTOCOLS` map, `config.DEFAULT_BINDINGS`, the `Container` accessor, `settings.yaml` and
  the canonical-call table), so a port cannot be added in four places and run unenforced.
- `tests/contract/test_behavioral_parity.py` proves the offline family ANSWERS, the on-premises
  family RAISES and the managed family REFUSES rather than silently succeeding. A placeholder
  that quietly returned a default would make the exit claim false while looking green.
- `make portability` is the executable claim: named checks with a pass or fail each, ending with
  the no-cloud-SDK probe that BLOCKS the `google` import in a fresh interpreter rather than
  hoping the machine has none installed. It prints what it does NOT prove and exits non-zero on
  any failure.

### How do we actually exit?

[`../onprem-migration.md`](../onprem-migration.md) is the path. The short version: the audit trail
exports to and restores from JSON Lines, so the trail itself is a file copy; the domain is pure
stdlib and moves unchanged; what you implement is one adapter per port under `adapters/onprem/`,
each of which currently raises with a message naming what to bind. Nothing in `domain/` has to
change, which is the point of the split.

### What has to be replaced on the way out, specifically?

The narrator (bind your in-country model gateway, or run with the deterministic narrative and no
model at all, which changes no figure), the identity adapter (your IdP rather than IAP), the
audit sink (your WORM store), the obligations and horizon clients (your register and corpus), and
the review router (your maker-checker queue). The evaluation port is the one that deliberately
REFUSES to promote off the managed profile: a promotion certified by a laptop with no quality
service is certified by nothing.

### Can it run with no model at all?

Yes, and that is the load-bearing property rather than a convenience. Every consequential figure
is produced by the deterministic engines, so with the stub narrator bound the pack's tier, matrix
cells, sufficiency verdicts and escalation are identical. The model changes the prose and nothing
else. See [`../model-card.md`](../model-card.md).

### Is the data residency claim portable too?

The region is chosen once and shared by the runtime and Terraform: `config/settings.yaml:region`,
`infra/terraform/render.tf.json:render_region`, and the Terraform `region` / `allowed_regions`
pair, which refuses an unapproved region at plan time. Changing jurisdiction is a configuration
change in those three places plus a re-run of
`infra/terraform/production_edge.tftest.hcl`, not a code change.
