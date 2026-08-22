"""Canonical synthetic systems, shared by the unit and contract suites.

Every system is a card in the offline fixture fleet (``adapters/local/fleet_fixtures``), so a
test that asks the registry for one of these names always resolves it. One escalating system
(high-risk, routes under R8), one routine system (minimal, nothing applies, no escalation) and
one system whose registry description carries a planted identifier are enough: parity means the
SAME request through every implementation, so the request has one home rather than being retyped.
"""

from __future__ import annotations

from conformity_pack.domain.models import AiSystemInput

#: The verified principal the tests attribute work to (never a client-asserted actor).
ACTOR = "analyst@bank.example"

#: A tenant partition, so the outbound-review assertions are not all on the empty string.
TENANT = "demo-bank"

#: A HIGH-risk system that MUST escalate: credit-scoring is an Annex III use, so rule R8 applies.
ESCALATING_SYSTEM = "credit-decision-copilot"
ESCALATING_CASE = AiSystemInput(system=ESCALATING_SYSTEM)

#: A MINIMAL-risk system that must NOT escalate: nothing applies and there is no gap, so a router
#: that manufactured a review here would be lying.
ROUTINE_SYSTEM = "internal-reporting-helper"
ROUTINE_CASE = AiSystemInput(system=ROUTINE_SYSTEM)

#: A planted identifier, so a redaction assertion has an independent literal to look for rather
#: than trusting the pattern pack to agree with itself. NRIC values must be checksum-valid.
PLANTED_NRIC = "S1234567D"

#: A planted address, so the universal rows have an independent literal of their own rather than
#: sharing the national-ID row's.
PLANTED_EMAIL = "kai.tan@delta.example"

#: A HIGH-risk system whose registry card description carries the planted identifier, for the
#: redact-before-anything proofs (the description flows into the card's citation snippet).
PII_SYSTEM = "gamma-analytics-copilot"
PII_CASE = AiSystemInput(system=PII_SYSTEM)

#: The LOCATOR half of the same proof: a system whose NAME carries the identifier, so it lands in
#: the citation's ``source_id`` and ``title`` rather than in its snippet. A sink that masks only
#: the snippet writes the identifier back out of the two fields beside it.
PII_LOCATOR_SYSTEM = "delta-analytics-copilot-nric-S1234567D"
PII_LOCATOR_CASE = AiSystemInput(system=PII_LOCATOR_SYSTEM)
