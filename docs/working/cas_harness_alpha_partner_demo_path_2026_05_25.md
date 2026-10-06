# CAS Harness Alpha Partner Demo Path

Date: 2026-05-25
Owner: Agent D
Scope: 5-minute alpha partner workflow for CAS Harness Audit Console plus Atlas deep inspection
Status: Demo script and honesty checklist, not a production-readiness claim

## Bottom Line

Use the Audit Console as the product front door and Atlas as the inspection microscope.

The clean story is:

> Connect a model. Run a CAS audit. Return a verdict with evidence.

The current alpha story is narrower:

> The Audit Console shows the licensed audit workflow and can create an M1 session lifecycle without inventing a verdict. Atlas can show the verified Pythia-160M live inspection path when realmode passes. Full external-model verdicts and signed Evidence Packet export are later gates.

Do not let the demo imply arbitrary model support, signed compliance evidence, or final audit verdicts before those are wired.

## Demo URLs

Primary product path:

```text
https://atlas-viewer-app.onrender.com/audit-console
```

Deep inspection path:

```text
https://atlas-viewer-app.onrender.com/cockpit
```

Live-model proof path:

```text
https://noetic-compass-api.onrender.com/atlas/live/health/realmode
```

## Pre-Demo Honesty Checklist

Run this 5-10 minutes before an alpha partner call.

1. Open `/audit-console`.
   - Confirm the page loads.
   - Confirm the headline reads: "Connect a model. Run a CAS audit. Return a verdict with evidence."
   - Confirm the page says no final verdict is shown until a real audit runner computes it.

2. Press the Audit Console reference flow.
   - Click `Prepare M1 reference session` or `Connect model`.
   - Click `Run audit`.
   - Confirm the session stops honestly at the M1 boundary.
   - Expected honest state: no final verdict, no confidence, no Evidence Packet ID.

3. Confirm Atlas LIVE realmode before calling anything live.
   - Open `/atlas/live/health/realmode`.
   - Required fields:

```json
{
  "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
  "is_real_model": true,
  "fake_runtime_env": false,
  "model_loaded": true,
  "load_error": null,
  "manifest_is_real_model": true,
  "model_id": "EleutherAI/pythia-160m"
}
```

   - If any field fails, do not say "live actual weights." Say "Replay path only right now."

4. Confirm no placeholder verdicts.
   - If the Audit Console says `NO VERDICT YET`, say that out loud.
   - Do not call per-token Atlas verification a whole-run CAS Harness verdict.
   - Do not show a confidence number unless it comes from a real response or calibrated artifact.

5. Confirm Evidence Packet state.
   - Audit Console M1 sessions do not yet export signed Evidence Packets.
   - Atlas Evidence Drawer can show packet data only when a real `trace_id` resolves.
   - If the drawer shows local metadata or fallback copy, read that label out loud.

6. Confirm no unsupported model claims.
   - The verified live alpha model is `EleutherAI/pythia-160m`.
   - OLMo and Qwen are validated in research artifacts, but live Atlas adapters are not the current alpha path.
   - Outside customer models need adapter validation before being called supported.

## The 5-Minute Clickable Path

### 0:00-0:30 - Open With The Product

Open:

```text
/audit-console
```

Say:

> This is the CAS Harness Audit Console. This is the product layer. A licensed user connects a model, runs an audit, and gets an operational decision: ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW. Each decision needs confidence and provenance. Atlas is the microscope we open when someone wants to inspect why the audit said what it said.

Point at the headline and the workflow cards.

Do not say:

> This already audits any model.

Say instead:

> This alpha shows the workflow and the M1 session lifecycle. The verified live model path today is Pythia-160M; arbitrary outside models need adapters and validation before we claim support.

### 0:30-1:20 - Connect The Reference Model And Run The M1 Session

Click:

```text
Prepare M1 reference session
Run audit
```

Say:

> I am going to run the reference session. Notice the important part: the console refuses to invent a verdict. It creates a session lifecycle, validates the request shape, and stops before ACCEPT, SUPPRESS, or REVIEW because the full audit runner is not wired into this page yet.

When the UI shows no verdict/confidence, say:

> This is correct alpha behavior. A fake green verdict would be worse than no verdict. CAS Harness only earns the verdict when the runner has real model proof, CAS readout, causal proof, control proof, output proof, and packet proof.

### 1:20-2:20 - Explain The Six Proof Chips

Point to the provenance section.

Say:

> These chips are the proof checklist. They are not decoration.

Use this exact plain-English mapping:

| Chip | What it means |
|---|---|
| Model proof | We know what model ran, and whether real weights were loaded. |
| CAS readout | CAS could read the relevant internal signal from hidden states. |
| Causal proof | When the CAS-linked internal part was changed, the measured signal or behavior changed. |
| Control proof | Random or wrong-target changes did not explain the same effect. |
| Output proof | The evidence connects to the actual model output, not just an internal chart. |
| Packet proof | The result can be packaged with traceable evidence instead of just screenshots. |

Say:

> An ACCEPT verdict should not be customer-safe unless those proof categories are present or explicitly marked as available. Missing proof should route to review, suppression, or pending state.

### 2:20-3:20 - Explain Why CAS Is Different

Use the CAS-vs-baseline evidence panel in Atlas if visible, or keep this as the spoken proof block.

Say:

> The reason CAS matters is not the vocabulary. The reason CAS matters is measurement. CAS has to beat comparison opponents. In the validated tests, it does.

Use only these supported numbers:

- Internal readout: Pythia-160M Foundation probe 78.6%; Pythia-160M 40-element probe 89.8%; OLMo-1B 90.6%; Qwen2.5-1.5B 82.0%.
- Text baseline gap: text-only baseline was lower by 28.9 percentage points on Foundation and 39.7 points on the 40-element readout.
- Causal removal: Foundation readout dropped from 78.6% to 3.57% after CAS subspace ablation. 3.57% is exact 1-in-28 chance.
- Matched random ablations: mean disruption 0.000 and max 0.000.
- Output likelihood shifts: Pythia-160M +0.283, Pythia-1B +0.554, OLMo-1B +0.604, Qwen2.5-1.5B +0.796.
- Raw-CAS-symbol control on Qwen: near null at -0.0002.
- Accept/suppress verification: OLMo accepted accuracy 98.16% at 71.73% coverage; Qwen accepted accuracy 99.49% at 74.57% coverage.
- Inversion proxy coverage: 4,704 of 4,704 OLMo/Qwen rows measured in Stage 22.6/22.7; proxy rate 1.000.

Plain-English close:

> If CAS was just a naming scheme, it would not beat text-only guessing, it would not collapse to chance when the CAS direction is removed, random removals would cause the same effect, and output likelihood would not move in the predicted direction.

Boundary:

> These are validated benchmark claims. They are not a claim that CAS controls every model, every token, or every semantic failure mode.

### 3:20-4:20 - Open Atlas For Deep Inspection

Click:

```text
Inspect in Atlas
```

Or open:

```text
/cockpit
```

Before pressing LIVE, show:

```text
/atlas/live/health/realmode
```

Say:

> This endpoint is the live proof. It must show real Pythia weights loaded, fake mode off, no load error, and a real-model manifest. The badge in the UI is not the proof by itself; the endpoint plus the stream manifest are the proof.

If realmode passes, press LIVE.

Say:

> Atlas is now the inspection cockpit. It shows tokens, layers, active neuron coordinates, attention-derived Mode 7 edges, and evidence references. It is not the whole CAS Harness product. It is the microscope for a run.

Click a word/token/neuron if available.

Say:

> This is where a reviewer can inspect the evidence path. If a stored Evidence Packet exists for the trace ID, the drawer should show it. If not, the drawer must say local metadata or packet unavailable. That honesty is part of the product.

### 4:20-5:00 - Close With The Alpha Ask

Say:

> The current alpha proves the shape: a simple audit console, a verified live Pythia inspection path, and benchmark evidence that CAS beats baselines on specific jobs. The next alpha work is to wire the full audit runner into the console, export Evidence Packets from sessions, enforce license/API access, and add validated adapters for more model families.

Then ask for one concrete partner action:

> The ask is: give us a small set of outputs or scenarios you care about, and help us test whether CAS routes them to accept, suppress, or human review with evidence you can inspect.

## Stakeholder Talk Track By Question

### What is CAS Harness doing?

Say:

> CAS Harness reads structured signals from model internals, compares those signals against controls, and uses the evidence to route model outputs: accept, suppress, or human review.

Technical mapping:

```text
Plain English: reads structured signals
Technical: hidden-state CAS probes / readouts

Plain English: compares against controls
Technical: text baselines, random same-rank ablations, raw-symbol controls, matched controls

Plain English: routes outputs
Technical: verification stack / audit verdict layer

Plain English: shows receipts
Technical: Evidence Packet schema, trace references, provenance chips
```

### What does baseline mean?

Say:

> Baseline means the comparison opponent. It is what CAS has to beat before we can say CAS adds value.

Examples:

- Text-only baseline: can a normal text classifier guess the label just from words?
- Random ablation baseline: does removing random internal directions cause the same collapse?
- Raw-symbol control: does the model react only because it saw CAS-looking symbols?
- Accept-everything control: what happens if we never suppress or review anything?

### What is a verdict?

Say:

> ACCEPT means the output can proceed under the chosen audit profile. SUPPRESS means block or withhold it. FLAG FOR HUMAN REVIEW means CAS does not have enough clean evidence, or the policy requires a person.

### What is the Evidence Packet?

Say:

> The Evidence Packet is the audit receipt. It should show what model was tested, what scenario was used, which methods ran, what the verdict was, what evidence existed, what was missing, and what limitations apply.

Boundary:

> In the current Audit Console M1 path, signed Evidence Packet export is not done yet. Do not call it compliance-grade until packet export, hashing, signing, access control, and legal review are complete.

### What is Atlas doing?

Say:

> Atlas is the inspection microscope. It lets a reviewer open the model run and see token activity, layer activity, attention paths, neuron cover overlap, and evidence references.

Boundary:

> The 3D scene alone does not prove the science. The benchmark claims come from probes, ablations, controls, output prediction, and replication.

## What Is Not Yet Production

Say this plainly when asked:

- The Audit Console is not yet a full arbitrary-model production auditor.
- The M1 session lifecycle does not yet compute final audit verdicts.
- The current verified live Atlas model is Pythia-160M.
- External models need adapters, capture paths, validation, and support labels.
- Audit Console Evidence Packet export is not yet signed/compliance-grade.
- Atlas per-token verification is not the same as a whole-run CAS Harness verdict.
- Blindspot confidence is cover-level evidence when calibrated, not single-neuron certainty.
- Inversion coverage is proxy-level attribution, not a full semantic inversion theorem.

## Must-Fix UX Gaps Before A High-Stakes Alpha Demo

1. Audit Console needs a visible live-model proof status when it is tied to Atlas LIVE. Right now the realmode proof lives in Atlas/API, not in the Audit Console header.
2. Audit Console should show a stronger disabled/pending Evidence Packet state: "No packet for this M1 session yet."
3. `Inspect in Atlas` currently opens the cockpit generically unless a trace reference exists. For a real audit row, it must deep-link to that row's trace/evidence.
4. Scenario selection is not yet visible in the Audit Console. The 25-scenario alpha set exists, but the console demo path does not yet let the user pick from it.
5. License/API gating is not production-enforced for Audit Console sessions. Do not demo it as metered commercial access yet.
6. The full audit runner is not wired into Audit Console. Until it is, the correct demo state is "session lifecycle created, verdict pending."
7. Audit Console should surface CAS-vs-baseline evidence directly, not only in Atlas, so users immediately see why CAS is different before opening the cockpit.
8. The UI should distinguish per-token Atlas telemetry from whole-run audit verdicts to avoid confusing technical reviewers.

## Files Inspected

Primary Audit Console and M1 worktree files inspected:

- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\docs\working\cas_harness_audit_console_plan_2026_05_25.md`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\docs\working\cas_harness_m1_evidence_packet_bridge_2026_05_25.md`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\docs\working\cas_harness_m1_risk_audit_2026_05_25.md`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\docs\working\cas_harness_audit_console_existing_capability_audit_2026_05_25.md`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\atlas-viewer\src\pages\AuditConsolePage.tsx`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\atlas-viewer\src\components\audit\AuditVerdictCard.tsx`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\atlas-viewer\src\components\audit\ProvenanceChips.tsx`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\atlas-viewer\src\components\audit\ModelConnectionCard.tsx`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\atlas-viewer\src\lib\casHarnessAudit.ts`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\atlas-viewer\src\lib\casHarnessAuditApi.ts`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\api\routes\cas_harness_audit.py`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\api\services\cas_harness_audit_sessions.py`

Atlas alpha, scenario, and live-verification files inspected:

- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\docs\working\atlas_alpha_demo_script_2026_05_24.md`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\docs\working\atlas_alpha_demo_live_verified_walkthrough_2026_05_25.md`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\docs\working\atlas_alpha_scenario_set_2026_05_24.md`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\scenarios\atlas_alpha_set_v0.json`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\scripts\verify_atlas_live.py`
- `C:\tmp\atlas-live-cockpit-integration\noetic-compass-scaffold\noetic-compass\atlas-viewer\src\lib\casBenchmarkEvidence.ts`

Marketing/spec/evidence files inspected from the main checkout:

- `C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\research\cas_probe\CAS_HARNESS_SPEC_SHEET_20260517.md`
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass\research\cas_probe\graphify-out\converted\CAS_HARNESS_SPEC_SHEET_v1_5_20260519_409e9efe.md`

Note: the exact direct markdown paths for `CAS_HARNESS_ROLLOUT_PLAN_v1_5_INTERNAL_20260521.md` and `CAS_HARNESS_SPEC_SHEET_v1_5_INVESTOR_EXTERNAL_NDA_20260521.md` were not present in this checkout during this pass. I used the current Audit Console worktree docs plus the converted v1.5 spec sheet available in the repo.
