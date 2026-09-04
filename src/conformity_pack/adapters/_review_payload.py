"""Shared conversion from an escalated result to an ``review-kit`` Review payload.

Lives in the adapter layer, not the pure domain, because it depends on the kit. EVERY content field
is redacted BEFORE it leaves the process (the same redact-before-anything rule the audit write
obeys), using the shared ``pii-kit``, so no raw identifier reaches human-review-console over the
wire; human-review-console redacts again before its own audit write (defence in depth).

"Every content field" is the load-bearing word, and it is written here because twice it was not
true: the citation LOCATOR and TITLE were passed through while the snippet beside them was scrubbed,
and ``case_ref`` and ``source_key`` were derived from the RAW subject while the subject itself was
masked. Both times the field's structural-looking name is what hid it. The rule is that a field
crossing this boundary is content unless it is ATTRIBUTION: ``maker`` and ``tenant`` are asserted
here and trusted by human-review-console because the caller is an authenticated S2S service (per-hop
on-behalf-of token exchange is the deferred next layer), and they are the only two fields a leak
scan over this payload skips.
"""

from __future__ import annotations

import re

from pii_kit import NATIONAL_ID_PATTERNS, UNIVERSAL_PATTERNS, national_patterns_for
from pii_kit import redact as pii_redact
from review_kit import Citation as KitCitation
from review_kit import Review

from ..domain.kernel import Severity
from ..domain.models import ConformityResult

#: Cap the citations carried on the wire: enough for a reviewer to trace the decision without
#: copying the whole evidence set into the console.
_MAX_CITATIONS = 8

#: The console is a SHARED sink: a case filed in one market may still quote another market's
#: national id, so the payload is scrubbed against every jurisdiction's rows plus the universal
#: email/phone rows, whatever this deployment's own ``domain.pii.JURISDICTIONS`` selects.
_ALL_PATTERNS = (
    *national_patterns_for(tuple(NATIONAL_ID_PATTERNS.keys())),
    *UNIVERSAL_PATTERNS,
)

#: Bands that demand dual control (two approvals) rather than a single checker.
_DUAL_CONTROL = (Severity.CRITICAL,)


def _redact(text: str) -> str:
    """Mask every jurisdiction's identifiers plus email/phone, and normalise whitespace."""
    return re.sub(r"\s+", " ", pii_redact(text, _ALL_PATTERNS)).strip()


def _kit_citations(result: ConformityResult) -> tuple[KitCitation, ...]:
    """Every field of every citation is masked, not only the snippet.

    A locator is routinely built from upstream free text (``hrz3:agent:<the card name>``, with
    the same name repeated in the title), so masking only the snippet let the identifier cross to
    the shared console in the two fields named like keys. De-duplication keys off the REDACTED
    locator, so two systems that differ only in a masked identifier collapse to one citation
    rather than both crossing the wire.
    """
    seen: set[str] = set()
    out: list[KitCitation] = []
    for citation in result.citations:
        source_id = _redact(citation.source_id)
        if source_id in seen:
            continue
        seen.add(source_id)
        out.append(
            KitCitation(
                source_id=source_id,
                title=_redact(citation.title),
                snippet=_redact(citation.snippet),
            )
        )
        if len(out) >= _MAX_CITATIONS:
            break
    return tuple(out)


def result_to_review(result: ConformityResult, *, maker: str, tenant: str = "") -> Review:
    """Build the review a producer submits to human-review-console when a result escalates.

    The subject is redacted ONCE and reused for the case reference and the idempotency key, so no
    raw identifier reaches the wire through a DERIVED field. Masking it in ``subject``
    and passed raw into ``case_ref`` and ``source_key`` on the lines below, which put the
    identifier on the shared console in the two fields whose structural names made them look like
    keys rather than content. A registry system name should never carry personal data; the
    redaction has to hold whether or not it does.

    The cost is named rather than hidden: two systems whose names differ ONLY in a masked
    identifier now share a source key and collapse to one review at the console. That is the
    right trade against publishing the identifier, and a system distinguished solely by a
    national id is not a system anyone should be keying on. The key stays STABLE across retries,
    which is the property the console's idempotency actually needs: ``pii_kit.redact``
    substitutes a fixed token per pattern rather than anything per-call, measured over 50 calls
    by ``tests/unit/test_audit_redaction.py`` rather than assumed.
    """
    subject = _redact(result.subject)
    return Review(
        action="conformity_pack:triage",
        subject=subject,
        maker=maker,
        tenant=tenant,
        summary=_redact(result.summary),
        severity=result.severity.value,
        required_approvals=2 if result.severity in _DUAL_CONTROL else 1,
        sod_group="conformity_pack-maker-checker",
        case_ref=subject,
        # Producer-owned, tenant-scoped key so a retried delivery is idempotent at the console.
        source_key=f"ai-act-conformity-pack:{subject}:{result.severity.value}",
        citations=_kit_citations(result),
    )
