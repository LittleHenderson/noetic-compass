# CAS Harness Audit Console Existing-Capability Audit - 2026-05-25

Owner: Agent F

Scope: verification/audit mapping only. This report maps the proposed Audit Console surface to what the existing Atlas LIVE worker/API and Evidence Packet API can truthfully support today.

## Bottom Line

The code can truthfully support a narrow live claim:

```text
For EleutherAI/pythia-160m, when /atlas/live/health/realmode returns
REAL_PYTHIA_WEIGHTS_LOADED and the first stream manifest has
is_real_model=true, the cockpit is receiving a live SSE stream from the
worker running real Pythia weights, with per-token probe summaries and
method knob echo.
```

The code cannot yet support a broad Audit Console claim:

```text
Connect any approved/open-weight model, run a CAS audit, produce an
ACCEPT/SUPPRESS/FLAG verdict, and export a signed or complete Evidence
Packet for that live session.
```

The current `AuditConsolePage` is explicitly a placeholder/product-flow page. Its `Run CAS audit` button has no audit API integration, and its `EVIDENCE_PACKET` rows are static copy, not runtime data.

Primary code anchors:

- `api/routes/atlas_live.py:37` defines the live session request shape.
- `api/routes/atlas_live.py:212` proxies `/atlas/live/health/realmode`.
- `api/routes/atlas_live.py:218` creates sessions and returns a stream token.
- `live-trace-worker/app/routes/health.py:35` defines the realmode proof body.
- `live-trace-worker/app/runtime/event_stream.py:231` streams real Pythia traces when loaded.
- `live-trace-worker/app/runtime/event_stream.py:276` dispatches real vs demo.
- `live-trace-worker/app/runtime/pythia_runner.py:38` generates one token at a time from Pythia.
- `api/routes/evidence.py:689` builds Evidence Packets from disk artifacts, not live sessions.
- `atlas-viewer/src/pages/AuditConsolePage.tsx:57` contains static placeholder packet rows.

## Atlas LIVE API: What It Actually Does

Supported:

- `POST /atlas/live/session` accepts `prompt`, `model_id`, `max_new_tokens`, `temperature`, optional `seed`, selected probes, and `method_config` knobs. It requires `X-Atlas-Invite-Code`, rate-limits by IP and invite code, forwards the request to the private worker, and returns `session_id`, `stream_url`, and `stream_token`.
- `GET /atlas/live/session/{session_id}/events` validates the short-lived JWT stream token and proxies the worker's SSE bytes.
- `GET /atlas/live/health` and `/atlas/live/health/realmode` proxy worker health. The realmode response is the proof surface the UI uses before claiming actual weights.

Realmode proof fields supported today:

- `verdict`: `REAL_PYTHIA_WEIGHTS_LOADED` or `NOT_REAL_PYTHIA_WEIGHTS`.
- `is_real_model`
- `fake_runtime_env`
- `model_loaded`
- `load_error`
- `manifest_is_real_model`
- `model_id`
- `worker_version`

Important boundary:

- The API route does not itself require realmode before creating a session. The cockpit currently creates the session, then calls `fetchLiveRealModeProof`, and refuses to accept the stream unless both the proof and stream manifest pass. That UI guard is real, but the backend session route alone is not a realmode enforcement gate.

## LIVE Worker Stream Schema: What Is Available

Supported event envelopes:

- `manifest`: emitted first; includes model id, tokenizer id, architecture, supported hooks, worker version, and `is_real_model`.
- `knob_resolution`: echoes the worker-resolved method knobs.
- `neuron_covers`: emits calibrated cover members when `blindspot_covers` is requested.
- `token`: one per emitted token.
- `word_spans`: emitted once at end of stream, mapping visible words back to token indices.
- `complete`: successful terminal event.
- `error`: failure terminal event.

Per-token fields available today:

- `token_index`
- `token`
- `top_activated_neurons`: top-K MLP hook coordinates when `active_trace` is requested.
- `mode7_attribution`: attention-derived edges when `mode7_attribution` is requested.
- `confidence`: normalized softmax margin when `confidence_margin` is requested.
- `inversion_risk`: scalar proxy from activation magnitude plus confidence pressure when inversion scan is active.
- `verification_mode`
- `verification_verdict`: `ACCEPT`, `FLAG`, or `SUPPRESS`.
- `verification_threshold`
- `verification_score`
- `verification_score_source`: `confidence`, `proxy_confidence`, or `unavailable`.
- `verification_invalid_mode`

What the verdict/confidence/provenance fields mean:

- `confidence` is not a calibrated probability of correctness. It is a top-1 minus top-2 logit margin normalized into `[0, 1]` in `probe_runner._softmax_margin`.
- `verification_verdict` is thresholding over that score according to `BALANCED`, `HIGH_PRECISION`, or `MAX_COVERAGE_TRIAGE` in `verification_mode.py:43` and `verification_mode.py:77`.
- `top_activated_neurons` and `mode7_attribution` are evidence surfaces. They are not a proof of semantic correctness or policy compliance.
- `neuron_covers` confidence is cover-level Stage 27F calibration (`targeted_drop / clean_margin`) projected onto cover members, not independent monosemantic confidence for each neuron.

## Evidence Packet API: What It Actually Does

Supported:

- `GET /evidence/{trace_id}` returns `evidence_packet.v1` for:
  - the dev fixture `dev_example_001`, or
  - a trace JSON file found in conventional on-disk locations.
- `POST /evidence/{trace_id}/verify` re-hashes packet-referenced on-disk artifacts under allowed roots and compares them with recorded hashes.
- Claim levels are represented as `cas_hard_trace`, `source_copy_evidence`, `derived_trace`, and `neural_attribution_estimate`.
- The route has a dev fallback packet if deployment-local artifacts are missing.

Gaps against live session export:

- The live worker does not write a per-session trace artifact to any of the Evidence Packet discovery locations in `api/routes/evidence.py:257`.
- Live token events do not carry a generated `trace_id`.
- `buildLiveSessionEvidence` in `atlas-viewer/src/lib/liveSessionEvidence.ts:104` creates a redacted live-session summary object with schema `atlas_live_session_evidence_v0`; it is not `evidence_packet.v1`.
- There is no current code path from a completed live SSE session to `GET /evidence/{trace_id}`.
- There is no signing layer for packet export in the inspected route.

## Six Provenance Chips: Current Support Map

Assumed six chips from the current Audit Console placeholder wording:

```text
Confidence, Model flow, Prompt, Layer trace, Policy target, Run ID
```

| Chip | Backed today? | Truthful wording |
| --- | --- | --- |
| Confidence | Partially | "Per-token confidence margin / verification score available when requested." Do not show one global audit confidence like `0.87` unless a real audit response computes it. |
| Model flow | Partially | "Pythia-160M live worker realmode proof and stream manifest verified." Do not say generic open-weight/validated attachment unless a model-adapter registry is wired. |
| Prompt | Partially | The prompt is accepted by `LiveSessionRequest` and sent to the worker, but the live stream/evidence summary does not currently export it as a durable packet field. |
| Layer trace | Yes, bounded | `top_activated_neurons` provides per-token live hook summaries; `mode7_attribution` provides attention-derived edges. Do not call this a full persistent layer trace unless exported. |
| Policy target | No | No policy-target field exists in the live API request, worker schema, token events, or Evidence Packet builder inspected here. |
| Run ID | Partially | `session_id` exists for live worker sessions; `trace_id` is nullable and not generated for live sessions. Do not call it an audit run id unless persisted and linked to packet export. |

## What Audit Console Can Truthfully Claim Today

Safe copy:

- "Audit Console shell: verdict workflow placeholder."
- "LIVE real-weight proof is available for Pythia-160M."
- "Live sessions stream token events, activations, attention-derived Mode 7 edges, confidence margins, verification threshold verdicts, cover-library blindspot coordinates, and word spans."
- "Method controls are echoed back by the worker as resolved knobs."
- "Evidence Packet v1 exists for disk-backed trace artifacts and dev fixtures."
- "Live-session evidence summary can show realmode proof, manifest facts, token counts, consumed knobs, and redacted runtime facts."

Unsafe copy:

- "Run CAS audit" as an implemented backend action.
- "Accept/Suppress/Flag verdict" as an audit-level result. Per-token verification verdicts exist; a whole-run audit verdict does not.
- "Policy target was evaluated."
- "Evidence Packet export for this live session."
- "Signed Evidence Packet."
- "All open-weight models supported."
- "Multi-probe verification ensemble" for the current live worker. The inspected live path thresholds a confidence/proxy score.
- "RPM prerequisite chain proof" for live tokens. The live path uses attention-derived Mode 7 edges filtered by threshold.
- "Axis-by-axis inversion scan" for live tokens. The live path emits one scalar proxy.

## Risks That Would Look Foolish To Technical Stakeholders

1. Claiming generic model support while `get_manifest` accepts only `EleutherAI/pythia-160m`.
2. Showing `ACCEPT`, `SUPPRESS`, or `FLAG FOR HUMAN REVIEW` as a real audit verdict when the Audit Console page has no audit request or response integration.
3. Presenting the static `0.87` confidence row as live data. Current live confidence is per-token softmax-margin telemetry, and cover confidence is a cover-ablation ratio.
4. Calling the live verification stack a multi-probe ensemble. The worker's live verdict is threshold logic over confidence/proxy confidence.
5. Claiming live Evidence Packet export. The Evidence Packet API only assembles from dev fixture or on-disk trace artifacts; live sessions are not persisted into that format.
6. Claiming policy-target review. No policy target is present in the live API or worker event schema.
7. Treating blindspot cover members as individually proven monosemantic neurons. The code explicitly says confidence is cover-level calibration projected onto members.
8. Treating Mode 7 attention edges as causal proof. They are attention-derived attribution estimates.
9. Claiming real weights from a session id alone. The actual realmode claim requires both `/health/realmode` and the first stream manifest.
10. Leaking stream tokens or invite material in evidence artifacts. The live-session evidence helper has redaction logic, but any new Audit Console export must preserve that discipline.

## Minimal Honest Integration Contract

For the current push, Audit Console should consume existing live facts only as an evidence summary, not as an audit verdict:

```text
Real model proof: passed/failed/unverified
Model: EleutherAI/pythia-160m
Worker: m2-real-pythia
Session: live session_id
Tokens observed: token events + complete total
Methods consumed: resolved worker knobs
Per-token evidence: confidence margin, verification verdict, top activations,
Mode 7 edges, inversion-risk proxy
Evidence Packet: unavailable for live session unless a trace_id-backed packet
exists on disk
```

Recommended visible boundary:

```text
This is a live-session evidence summary, not a CAS Harness audit verdict.
Evidence Packet export is available only for trace_id-backed packet artifacts.
```
