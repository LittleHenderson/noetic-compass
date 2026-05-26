# CAS Harness Beta v0 Acceptance Matrix

**Status:** Draft for beta acceptance review
**Date:** 2026-05-26
**Owner:** Agent E - acceptance matrix lane

## Product Goal

Licensed/API users can attach a model, run a CAS audit, and receive a defensible result set:

- Verdict: `ACCEPT`, `SUPPRESS`, or `FLAG`
- Confidence attached to each verdict
- Proof chips that explain why the verdict was reached
- Evidence Packet export that preserves the audit trail

This matrix treats beta v0 as a paid/API-facing product workflow, not a marketing-only replay. A demo fixture may be used for the narrated demo, but the acceptance gate is the complete workflow contract.

## Scope Boundary

**In scope for beta v0 acceptance**

- License/API access gate
- Model attachment and validation status
- CAS audit setup and execution state
- Verdict table with confidence and proof chips
- Evidence Packet viewer/export
- Error, refusal, and low-confidence handling
- Reviewer/demo readiness gates

**Out of scope for this acceptance matrix**

- Final pricing and billing provider choice
- Multi-user collaboration
- SGGS gesture controls
- Public benchmark expansion
- Architecture Mapper research UX beyond a refusal/request-adapter path

## Verdict Contract

| Verdict | User meaning | Required beta behavior |
|---|---|---|
| `ACCEPT` | The audited output, token, claim, or step is supported by the configured CAS evidence stack. | Only shown when required module evidence exists, confidence clears the configured threshold, and all mandatory provenance links resolve. |
| `SUPPRESS` | The output, token, claim, or step should be blocked, withheld, or deprioritized because the audit found a validated failure condition. | Must identify the suppressing evidence class and expose at least one proof chip tied to packet evidence. |
| `FLAG` | The result is inconclusive, unsupported, low-confidence, exploratory, or needs human review. | Must be the default fallback for missing evidence, unsupported architecture, stale artifacts, threshold ambiguity, or confidence below the beta floor. |

**Release blocker:** no unsupported, stale, or low-confidence result may be rendered as `ACCEPT`.

## Acceptance Matrix

| Area | Acceptance Criteria | Negative Cases That Must Pass | Beta Exit Blocker |
|---|---|---|---|
| License gate | A signed-in user sees license status, tier, expiry, quota, and API-key state before starting a run. The product prevents audit launch when entitlement is invalid. | Expired license, revoked key, missing API key, tier below endpoint requirement, quota exceeded, API-only request without license binding. | User can launch or fetch paid audit output without a valid license/API entitlement. |
| API user path | API users can submit the same required inputs as UI users and receive the same verdict/confidence/evidence schema. API responses include stable run IDs and packet IDs. | Missing auth header, license belongs to another user, replaying stale token, malformed model ID, malformed module config. | API and UI disagree on verdict semantics or evidence fields for the same run. |
| Model attachment | User can attach a supported model by model ID, see architecture family, validation band, parameter/size class, credential status, and readiness to run. | Invalid model ID, private/gated model without token, unsupported family, model too large for beta limit, tokenizer/config fetch failure, adapter unavailable. | The UI implies "any model" support or lets unknown architecture proceed as validated. |
| Architecture status | Every attached model is labeled `Validated`, `Exploratory`, or `Refused` before execution. Exploratory results cannot be presented with validated certainty. | Unknown family, partial config, adapter confidence below floor, architecture mismatch between metadata and runtime trace. | Architecture status is absent, hidden, or contradicted by the result page. |
| Audit setup | User can choose the audit scenario/module set, see default mode, expected cost/time, required artifacts, and whether prerequisites are satisfied. | Required module output missing, incompatible module combination, unsupported mode for tier, empty scenario, duplicate run submission. | Audit starts without the evidence prerequisites needed to produce the promised verdict table. |
| Run execution | A run has visible states: queued, running, completing, completed, canceled, failed. Each state has a run ID and timestamp. | Queue timeout, worker failure, user cancel, network retry, partial artifact write, backend returns 5xx, browser refresh mid-run. | User cannot distinguish in-progress, failed, partial, and completed audits. |
| Verdict result table | Completed audit shows per-token, per-claim, or per-step rows with `ACCEPT`, `SUPPRESS`, or `FLAG`, confidence, proof chips, and packet row link. | Mixed row statuses, empty result set, missing confidence, duplicate row IDs, result computed from partial artifacts. | Any verdict row lacks confidence or lacks an evidence link. |
| Confidence display | Confidence is numeric or banded consistently across UI, API, and Evidence Packet. Low confidence maps to `FLAG` unless a documented suppress rule applies. | Confidence unavailable, `NaN`, out of range, rounded to misleading certainty, confidence below threshold shown as `ACCEPT`. | Confidence is decorative and not tied to release/verdict behavior. |
| Proof chips | Proof chips are short, human-readable evidence summaries. Each chip opens or anchors to its supporting Evidence Packet row. | Chip without packet row, chip text contradicts verdict, chip references hidden internal-only artifact, chip generated for failed module. | Proof chips are static labels with no traceability. |
| Evidence Packet viewer | User can open an Evidence Packet from the result screen and verify model, run config, verdict rows, module outputs, provenance, confidence, and packet timestamp. | Packet missing row, packet belongs to another run, packet generated before run completion, packet schema version missing, packet cannot be opened after refresh. | Evidence Packet cannot reconstruct how a displayed verdict was produced. |
| Evidence Packet export | User can export/download the packet in beta-supported formats with signed manifest or integrity metadata. API users can fetch by packet ID if entitled. | Tampered packet, missing manifest/hash, unauthorized packet fetch, expired run link, export generated from stale UI state. | Export is a screenshot/report only and lacks machine-readable audit evidence. |
| Provenance and integrity | Every result records user/license, model ID, architecture band, module config, scenario/prompt reference, run ID, artifact IDs, schema version, and generation time. | Cross-user artifact leakage, prompt/model mismatch, stale cache collision, packet/version mismatch, changed model config after run. | Reviewer cannot identify what model/config produced the result. |
| Error and refusal UX | Refusals are explicit and useful: why it failed, whether retry is possible, what the user can change, and whether to request an adapter. | Silent failure, generic "something went wrong", refusal copy hidden in logs, unsupported model shown as failed audit instead of refused intake. | User mistakes a system failure or unsupported model for a CAS audit result. |
| Privacy and isolation | UI and packet make clear what was tested and do not expose other users' prompts, model credentials, license keys, or raw secrets. | Shared packet URL leaks data, credential appears in packet/export/log, run list crosses tenants, API returns another user's artifact. | Any cross-tenant data exposure or secret exposure. |
| Claim discipline | Visible copy states that CAS Harness audits the attached model under supported protocols. It does not promise universal truth, safety certification, or full "any AI" coverage. | Marketing copy says "any model", unsupported families appear validated, FAQ caveat contradicts headline claim. | Product overclaims beyond validated beta scope. |
| Demo fixture honesty | If a demo uses fixtures/replay, the UI labels the run as demo/replay and does not imply it is a live customer model audit. | Fixture shown as live, canned result lacks packet links, demo bypasses license/model steps without disclosure. | Demo script depends on a misleading workflow. |

## Negative Case Checklist

The beta should be rejected if any of these fail:

- Expired or revoked license cannot start a run.
- API key without matching license cannot fetch results or packets.
- Unknown architecture is refused or labeled exploratory; it is never silently validated.
- Private/gated model without credentials fails before audit execution.
- Missing module prerequisite produces `FLAG` or refusal, not `ACCEPT`.
- Low confidence produces `FLAG` unless an explicit suppress rule applies.
- Partial run artifacts cannot generate a completed Evidence Packet.
- Proof chips never appear without backing packet rows.
- Evidence Packet export cannot be fetched across tenant boundaries.
- Browser refresh does not lose completed run identity or packet linkage.
- Failed/canceled run cannot be mistaken for a completed audit.
- Replay/demo data is visibly labeled as replay/demo data.

## Demo Script Gates

The beta demo is acceptable only if the narrator can complete these gates without developer console access.

| Gate | Narrated action | Pass condition |
|---|---|---|
| 1. Access | Sign in or show API/license entitlement. | License/API status is visible and valid. |
| 2. Attach model | Enter or select a model. | Model ID, architecture, validation band, and readiness state appear. |
| 3. Configure audit | Choose scenario/module defaults. | UI shows what will run, expected cost/time, and prerequisites. |
| 4. Run audit | Start the CAS audit. | Run state progresses with run ID and no ambiguous loading dead end. |
| 5. Review verdicts | Open completed results. | Rows show `ACCEPT`, `SUPPRESS`, or `FLAG` with confidence. |
| 6. Inspect proof | Click at least one proof chip per verdict class shown. | Each chip opens/anchors to supporting evidence. |
| 7. Open packet | Open Evidence Packet from the result. | Packet contains run metadata, verdict rows, confidence, provenance, and schema/version. |
| 8. Export packet | Export or fetch packet. | Export preserves packet ID and integrity/provenance metadata. |
| 9. Show refusal | Attempt an unsupported or invalid model. | Product refuses safely with reason and next action. |
| 10. Close claim | Summarize what the audit says and does not say. | UI copy supports the claim without overpromising. |

## Technical Reviewer Red Flags

These are grounds for blocking beta acceptance or forcing a narrower release label:

- Verdict is computed client-side from display labels rather than from signed or server-owned audit artifacts.
- Confidence has no documented threshold behavior or can be overridden by UI state.
- `ACCEPT` can appear when architecture status is `Exploratory`, `Refused`, unknown, or missing.
- Proof chips are manually curated copy and not generated from packet-backed evidence rows.
- Evidence Packet omits model ID, architecture band, module config, run ID, schema version, or artifact hashes.
- Evidence Packet can be regenerated after the fact with different contents under the same packet ID.
- API and UI have separate result semantics or different confidence rounding rules.
- Retry logic can duplicate runs and merge artifacts under one run ID.
- Demo path bypasses licensing, model attachment, or packet generation in a way not labeled as fixture/replay.
- Logs, packet exports, screenshots, or browser state expose API keys, HF tokens, license keys, or customer secrets.
- Error states collapse unsupported model, failed run, canceled run, and low-confidence audit into the same UI message.
- User-facing copy claims safety certification, universal model support, or production readiness beyond beta validation.

## UI Visibility Rules

### Must Be Visible In Primary UI

- Current user/license/API entitlement state: valid, expired, revoked, quota-limited, or trial.
- Attached model ID and architecture status: `Validated`, `Exploratory`, or `Refused`.
- Audit run state, run ID, started/completed timestamps, and failure/cancel status.
- Selected audit mode/modules and unmet prerequisites.
- Result verdicts: `ACCEPT`, `SUPPRESS`, `FLAG`.
- Confidence beside every verdict, not hidden behind a tooltip.
- Proof chips beside each verdict row.
- Evidence Packet open/export action.
- Clear refusal reason for unsupported or invalid models.
- Demo/replay label when results are fixture-backed.
- Plain-language caveat that results apply to this model, this run, and this configured CAS audit.

### May Live In Hover, Drawer, Or Secondary Detail

- Formal CAS method names and Stage anchors.
- Exact threshold definitions and confidence calibration notes.
- Full module cost/time assumptions.
- Detailed provenance hashes and artifact IDs, as long as the Evidence Packet exposes them.
- Architecture adapter implementation notes.
- Glossary definitions for drive, inversion, RPM gate, blindspot, proof chip, and Evidence Packet field names.
- Reviewer-oriented packet schema details.

### Should Live In FAQ Or Documentation

- Pricing and tier comparison details.
- Data flywheel and validation-graduation explanation.
- Legal/IP posture and non-certification disclaimers.
- Supported architecture roadmap.
- API integration examples.
- How to request a new adapter.
- Difference between replay/demo, live audit, validated architecture, and exploratory architecture.

### Must Not Be Hidden Only In FAQ/Hover

- License invalid/expired state.
- Unsupported/refused architecture state.
- Low-confidence or inconclusive result state.
- Whether a result is replay/demo data.
- Whether the Evidence Packet failed integrity validation.
- Any warning that changes whether the user should trust, export, or act on the result.

## Beta Acceptance Sign-Off

Beta v0 is acceptable when all of the following are true:

- A licensed/API user can complete the attach-model to Evidence Packet workflow.
- Every displayed verdict has confidence and packet-backed proof.
- Negative cases fail closed into refusal, `FLAG`, or explicit error state.
- Demo script gates can be completed without console access or private operator knowledge.
- Technical reviewer red flags are resolved or documented as release-blocking exclusions.
- UI surfaces trust-critical states directly, while FAQ/hover content is limited to explanation and detail.
