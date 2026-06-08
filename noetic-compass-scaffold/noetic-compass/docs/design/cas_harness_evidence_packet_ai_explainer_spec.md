# SPEC — CAS Harness: Evidence Packet AI Explainer ("Explain this packet")

- **Status:** Draft / design-locked — Jun 7, 2026. Build is post-launch (after the security-spine
  tenant-iso merge; see Dependencies).
- **One-line:** an AI button on an Evidence Packet that gives a novice developer a plain-English,
  *cited* interpretation of their packet — pointing them at **what** and **why** further
  investigation may be needed — without exposing CAS internals and without overstating the verdict.
- **Surfaces through:** the existing floating **Guide** (`GuideChatWidget`, Gemini-backed), opened in
  a new "packet context" mode. Backend extends `api/services/explainer.py`.

---

## 1. Purpose & scope

CAS Harness produces **Evidence Packets (EPs)**: an honest verdict
(`ACCEPT` / `FLAG_FOR_HUMAN_REVIEW` / `SUPPRESS`), proof chips, blind-spot findings, and a
WORM-anchor status. EPs are dense and unfriendly to a novice developer skimming a result.

This feature adds an **"Explain this packet (plain English)"** action that produces an interpretation
optimized for one job: **tell the developer what the packet says and where to look next** — an
*investigative pointer*, not a verdict-restater and not a substitute for reading the EP.

It is explicitly **NOT**:
- a re-scoring or second opinion (it never computes or alters a verdict),
- a window into CAS scoring math, probe construction, or hidden prompts,
- authoritative — the **original EP is authoritative**; this is a reading aid.

## 2. Non-negotiable guardrails

**G1 — Verdict fidelity (honesty).** The interpretation states the verdict **exactly as the packet
records it**. It MUST NOT: upgrade `FLAG_FOR_HUMAN_REVIEW` or `SUPPRESS` toward "pass"; call a
**scoped-validation** ACCEPT a **customer-production** ACCEPT; invent a confidence/score the packet
does not contain; imply certification the packet does not assert. When the packet carries the
scoped-vs-production distinction, the interpretation must carry it too.

**G2 — IP containment.** The model receives the packet's **customer-facing fields only** (§4
allow-list). It MUST NOT receive or reveal: scoring formulas/weights, probe-generation logic, the
"why this probe" methodology, internal prompts, other tenants' data, or raw model/provider secrets.

**G3 — Tenant ownership.** The endpoint resolves the EP **only if the caller's tenant owns the
trace** (reuses the evidence-ownership ledger). No cross-tenant explanation, ever.

**G4 — User responsibility (disclaimer).** Before first use (and persistently in the panel footer):
> *"This is an AI-generated reading aid. The original Evidence Packet is the authoritative record —
> you are responsible for reading it yourself. Do not rely on this summary alone for any
> go/no-go decision."*
First-use requires an explicit acknowledgement (stored per account); footer line is always visible.

## 3. The "just enough" principle (input minimalism)

Feed the model the **minimum** projection needed to be *insightful about what to investigate* — no
more. More context ≠ better here; it raises IP risk and hallucination surface. The projection is a
curated, redacted view (§4), plus the matching public-guide sections (the same KB the Guide already
uses). If a field isn't on the allow-list, it isn't sent.

## 4. Redaction allow-list / deny-list

**MAY be sent (the projection):**
- `verdict` (literal: ACCEPT / FLAG_FOR_HUMAN_REVIEW / SUPPRESS) + any scope qualifier
  (e.g. `validation_scope`, `is_customer_production`).
- `proof_chips[]`: each chip's `id`, customer-facing `label`, and literal `status`
  (verified / present / missing / failed / unavailable) — **status words verbatim, never "pass".**
- `blind_spots[]` / inversion findings in **customer-facing terms**: which axis flagged, severity
  band, and the **customer's own flagged prompt/input + the observed behavior** (see §5).
- `anchor`: `status` (anchored / not-anchored), retention-mode disclosure, `trace_id`.
- `model_target` (the customer's own declared model/endpoint label), `audit_mode`, timestamps.
- `counts` (e.g. "4 of 6 proof chips ready").

**MUST NOT be sent (deny-list):**
- scoring math, NCCS weights, operator/drive/register internals, dial values;
- probe-generation logic, prompt templates, "why this probe was selected";
- any other tenant's data; raw API keys/secrets; internal trace plumbing beyond `trace_id`;
- the private CAS reasoning behind a score (the *result* is shareable; the *method* is not).

A single `build_packet_projection(ep) -> dict` function is the **only** path to the model input. It is
allow-list-driven (unknown fields dropped by default) and unit-tested field-by-field.

## 5. Highlighted prompts & blind spots — DECISION

**Question raised:** should users see highlighted prompts alongside the verdict explanation,
especially for blind spots?

**Recommendation — YES, with a sharp line:**
- **SHOW** the customer's **own flagged prompt/input verbatim** and the **observed behavior** that
  tripped the finding, plus *which* blind-spot/inversion axis flagged it and the severity band. This
  is the customer's own evidence and is exactly the "where to look" a novice needs. The AI may quote
  it and explain, in plain terms, *what* the concern is and *why* it warrants investigation.
- **DO NOT SHOW / DO NOT SEND** the proprietary **probe construction** behind that prompt — how CAS
  derived/selected/mutated it, the scoring math, or the internal reasoning. The interpretation
  explains the **finding and the next step**, not the **methodology**.

Net: highlighted prompts are an *evidence-and-investigation* surface (allowed), not a *methodology*
surface (forbidden). This satisfies "give the AI just enough to be insightful about what & why to
investigate" while honoring G2.

## 6. Citation / reference-point format

Every substantive claim in the interpretation is **anchored to the exact EP field it came from** —
the "reference points of the original EP." This is the traceability principle applied to the
explanation layer.

- The model returns **structured anchors**, not free-text citations: each explanation segment carries
  `{ text, refs: [ "verdict", "proof_chips.causal_proof.status", "anchor.status", ... ] }`.
- The widget renders each `ref` as a **clickable chip** that scrolls/links to that field in the real
  EP view. (Same pattern as the Guide's `Source:` chips, but pointing at the packet's own fields.)
- Rendering rule: an interpretation segment with **zero refs is not shown** (no uncited claims).

**Illustrative output (rendered):**
> Your audit returned **`FLAG_FOR_HUMAN_REVIEW`** — not a pass; a person must review.
> `[verdict]`
> The **Causal check** came back **`failed`** — the audit couldn't confirm the model's stated reason
> drove its behavior. `[proof_chips.causal_proof.status]`
> A blind spot was flagged on this input: *"<the customer's flagged prompt>"* — the model
> <observed behavior>. Worth reproducing and investigating. `[blind_spots.0]`
> The packet **is** sealed in the tamper-evident ledger. `[anchor.status]`

## 7. Output contract

```
ExplainPacketResponse {
  trace_id: string
  verdict_echo: string            // the literal verdict, echoed for the UI to assert ==  EP verdict
  segments: [ { text: string, refs: string[] } ]   // refs MUST be non-empty per segment
  investigate_next: [ { text: string, refs: string[] } ]  // the "what & why to look" list
  used_gemini: bool
  model: string
  safety_mode: "packet_projection_only"
  disclaimer: string              // G4 text
}
```
The UI **asserts `verdict_echo === EP.verdict`**; mismatch → discard the AI output and show the raw EP
verdict only (fail closed, never the inflated reading).

## 8. Backend design

- New endpoint `POST /explainer/evidence/{trace_id}` (JWT-protected, like `/explainer/chat`).
- Flow: resolve EP for `trace_id` **scoped to caller's tenant** (G3) → `build_packet_projection`
  (§4) → assemble Gemini prompt = projection + matched public-guide sections + a strict system prompt
  encoding G1/G2/G5 → call Gemini → validate output (verdict_echo match, every segment has refs, no
  deny-list tokens leaked) → return `ExplainPacketResponse`.
- System prompt encodes: "You are a reading aid. Preserve the verdict EXACTLY. Cite every claim to a
  provided field key. Explain what & why to investigate. You do NOT know and must NOT speculate about
  CAS scoring internals or how probes are built. If you cannot ground a statement in the provided
  fields, omit it."
- Reuses `GoogleConnector` + `gemini_explainer_model`; key stays server-side.

## 9. Frontend

- **AI button** on the Evidence Packet / verdict view: "Explain this packet (plain English)".
- Opens **`GuideChatWidget` in packet mode** (pre-loaded with `trace_id`), distinct from the
  free-chat Guide. Renders `segments` + `investigate_next` with clickable ref-chips (§6).
- **First-use disclaimer modal** (G4) requiring acknowledgement; persistent footer disclaimer.
- Verdict-echo mismatch → render raw EP verdict + "AI summary unavailable for this packet."

## 10. Honesty test cases (must pass before ship)

1. **No upgrade:** given a `FLAG_FOR_HUMAN_REVIEW` packet, the output's `verdict_echo` is
   `FLAG_FOR_HUMAN_REVIEW` and no segment text contains pass/accept/approved language.
2. **No suppress-softening:** a `SUPPRESS` packet is never described as acceptable/minor.
3. **Scope carried:** a scoped-validation ACCEPT is never described as a customer-production ACCEPT;
   the scope qualifier appears in the output.
4. **Every segment cited:** no segment ships with empty `refs`.
5. **Deny-list never leaks:** projection + output scanned for scoring-internal / probe-method tokens;
   zero matches.
6. **Ownership:** a `trace_id` the caller's tenant does not own → 404, no projection built.
7. **Verdict-echo guard:** a deliberately corrupted model output whose `verdict_echo` ≠ EP verdict is
   discarded by the API (fail-closed), surfaced as "unavailable", never rendered.
8. **Projection allow-list:** `build_packet_projection` drops any field not on the allow-list
   (table-driven test over every EP field).
9. **Dark default:** with the explainer disabled / no key, the button degrades to "unavailable", the
   EP renders normally.

## 11. Reuse & dependencies

- Reuses: `GuideChatWidget`, `api/services/explainer.py` (+ `GoogleConnector`), the Evidence Packet
  schema/view, the **evidence-ownership ledger** (G3), the public-guide KB.
- Depends on: the tenant-iso **evidence-ownership** path being live (security spine) so G3 is real,
  not best-effort. Build after that merges.

## 12. Sequencing

Design-locked now. Build sequence: (1) `build_packet_projection` + allow-list tests, (2) the endpoint
+ ownership scoping + verdict-echo guard, (3) the system prompt + honesty tests, (4) widget packet
mode + ref-chips + disclaimer modal. Not started during the cascompass.ai launch window.
