"use client";

import { useEffect, useState } from "react";

// Every request goes to THIS origin. The browser never learns the service's address and never
// holds its credential; the route handler under /api/agent forwards, having discarded whatever
// identity the client tried to assert.
const API = "/api/agent";

// Mirrors the service's seeded local personas. The picker is a DEV convenience: the server
// validates the selection against its own list, so a hand-crafted value cannot invent a persona.
const PERSONAS = ["analyst", "approver", "auditor", "other-tenant"];

// What happened to the human-review hand-off, in the words the user needs. A result that
// escalated but is not queued must say so rather than read as reviewed.
const REVIEW_ROUTING_TEXT: Record<string, string> = {
  routed: "Sent to the review console.",
  failed: "Could not reach the review console; this assessment is not queued for review.",
  off: "Review routing is off in this deployment; this assessment is not queued for review.",
};

function reviewRoutingOf(body: string): string | undefined {
  try {
    const parsed = JSON.parse(body) as { review_routing?: unknown };
    return typeof parsed.review_routing === "string" ? parsed.review_routing : undefined;
  } catch {
    return undefined;
  }
}

// The AI systems the local profile's fixture registry holds (`adapters/local/fleet_fixtures.py`),
// offered as suggestions because the API serves no list of them. The field stays free text: under
// a managed profile the registry is the live agent-registry, and the service answers 404 for a
// name it does not hold. The two cards planted for the redaction proofs are left out on purpose.
const KNOWN_SYSTEMS = [
  "credit-decision-copilot",
  "hr-cv-screener",
  "social-scoring-pilot",
  "market-insights-chatbot",
  "internal-reporting-helper",
  "undeclared-analytics",
  "model-risk-validation",
];

interface CardSummary {
  name?: string;
  description?: string;
  skills?: { id: string; name: string }[];
}

export default function Home() {
  const [persona, setPersona] = useState(PERSONAS[0]);
  const [system, setSystem] = useState(KNOWN_SYSTEMS[0]);
  const [asOf, setAsOf] = useState("");
  const [result, setResult] = useState("");
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [card, setCard] = useState<CardSummary | null>(null);

  // The service names itself, so this UI carries no hardcoded product name to go stale.
  useEffect(() => {
    let live = true;
    fetch(API + "/.well-known/agent-card.json", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        if (live) setCard(body as CardSummary | null);
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFailed(false);
    try {
      // `AssessRequest` is the whole request: the system is resolved by name from the registry,
      // and the actor and tenant come from the verified principal, never from this body.
      const response = await fetch(API + "/v1/assess", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Dev-Persona": persona },
        body: JSON.stringify({ system: system.trim(), as_of: asOf }),
      });
      const body = await response.text();
      setFailed(!response.ok);
      setResult(body);
    } catch (error) {
      setFailed(true);
      setResult(String(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>{card?.name ?? "Agent console"}</h1>
      <p className="sub">
        {card?.description ??
          "Assess an AI system. The tier and obligations are deterministic, cited, and routed to a human reviewer when they escalate."}
      </p>

      <form onSubmit={submit}>
        <fieldset>
          <legend>Who you are</legend>
          <label>
            Seeded dev persona (local profile only; the server resolves identity, not this field)
            <select value={persona} onChange={(event) => setPersona(event.target.value)}>
              {PERSONAS.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        </fieldset>

        <fieldset>
          <legend>The AI system</legend>
          <label>
            System name, as registered (suggestions are the local fixture fleet)
            <input
              value={system}
              list="known-systems"
              onChange={(event) => setSystem(event.target.value)}
            />
            <datalist id="known-systems">
              {KNOWN_SYSTEMS.map((name) => (
                <option key={name} value={name} />
              ))}
            </datalist>
          </label>
          <label>
            As of (optional; stamps the persisted obligation matrix with this date)
            <input type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} />
          </label>
          <button type="submit" disabled={busy || !system.trim()}>
            {busy ? "Working" : "Assess this system"}
          </button>
        </fieldset>
      </form>

      {result && REVIEW_ROUTING_TEXT[reviewRoutingOf(result) ?? ""] ? (
        <p className="sub" data-review-routing={reviewRoutingOf(result)}>
          {REVIEW_ROUTING_TEXT[reviewRoutingOf(result) ?? ""]}
        </p>
      ) : null}
      {result ? <pre className={failed ? "result error" : "result"}>{result}</pre> : null}

      <footer>
        Synthetic, obviously fictional data only. Identity is resolved server-side and the
        client-asserted actor is discarded; see ui/README.md for the embedding contract.
      </footer>
    </main>
  );
}
