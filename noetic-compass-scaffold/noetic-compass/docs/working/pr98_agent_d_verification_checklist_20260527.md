# PR #98 Agent D Verification Checklist

Date: 2026-05-27
Owner: Agent D, verification/test-only lane

## Executable Regressions Added

- `tests/test_evidence_routes.py::test_evidence_get_preserves_s7_f28_20b_packet_claims`
  - Mocks an on-disk GPT-NeoX-20B S7-F28 trace.
  - Verifies Evidence Packet assembly preserves balanced-logistic bridge claim rows and the "verifier merge pending" caveat unchanged.
  - Verifies packet assembly does not promote the S7-F28 bridge tier into a completed CAS Harness verifier verdict.
- `live-trace-worker/tests/test_schemas.py::test_method_runtime_statuses_do_not_enable_non_runtime_methods`
  - Verifies payload-only and unsupported methods are reported as such and remain disabled.
- `live-trace-worker/tests/test_sessions.py::test_dump_session_emits_full_event_sequence`
  - Verifies the dump stream emits a `method_runtime_status` event and marks `evidence_packet` as `payload_only` and `drive_local_eraser` as `unsupported`.
- `atlas-viewer/src/lib/liveWorkerRequest.test.ts`
  - Verifies selected payload-only and unsupported methods are serialized with `enabled: false`.
- `atlas-viewer/src/components/audit/EnterpriseScalePlanCard.test.tsx`
  - Verifies the 20B card is presented as an open-weight execution plan, not a loaded or verified audit packet.

## Checklist-Only Until Agent B/C Implementation Lands

### Audit Console "Load 20B Packet"

Current blocker: the audit components in this branch expose scale-plan and fleet-executor panels, but there is no implemented Audit Console packet-loader action/state that fetches a 20B packet ID and renders its Evidence Packet rows.

Add tests when the loader exists:

- Mock `GET /evidence/gpt-neox-20b-s7-f28-balanced-logistic`.
- Click "Load 20B packet" or the final implemented control name.
- Assert the console renders model `EleutherAI/gpt-neox-20b`, trace ID, packet schema version, claim rows, confidence/support fields, and the "verifier merge pending" caveat.
- Assert the loaded packet is not displayed as `ACCEPT` until a verifier decision layer is present.
- Assert 404/malformed packet states render `FLAG` or explicit error, not a completed audit.

### 40E/F28 Balanced-Logistic Method Guardrails

Current blocker: no production runtime method or API contract in this branch exposes a `balanced_logistic` readout pipeline for 40-Element or Foundation-28 closure claims. Existing code only has generic `foundation_probe` runtime knobs and documentation of the methodology.

Add tests when the pipeline exists:

- Accept only `taxonomy in {"40E", "F28"}` or the final canonical enum names.
- Require source-derived balanced scenario sets with every class populated before closure claims.
- Require `StandardScaler` plus balanced logistic readout; reject nearest-centroid readout for closure-tier claims.
- Require majority/chance and shuffled-label controls in the Evidence Packet.
- Require raw-symbol controls to remain non-supporting for eta-to-epsilon claims.
- Require missing or below-threshold metrics to produce `FLAG` or refusal, never `ACCEPT`.
- Require packet provenance to include model ID, layer, readout method, class counts, heldout split, and metric thresholds.

### Anti-Fabrication Behavior Still To Cover In UI

Already covered at worker/request-builder level: payload-only and unsupported LIVE methods cannot be enabled as live runtime work.

Add UI-level tests when Agent B/C screens are wired:

- Selecting Evidence Packet or Spatial Evidence in LIVE mode must show payload-only/export semantics, not "running live".
- Scale plans must not render as completed audits.
- Fleet merge without every worker receipt and packet fragment must remain blocked.
- Demo/replay packets must be visibly labeled as demo/replay.
- Any packet without a verifier decision layer must show pending/FLAG wording rather than `ACCEPT`.
