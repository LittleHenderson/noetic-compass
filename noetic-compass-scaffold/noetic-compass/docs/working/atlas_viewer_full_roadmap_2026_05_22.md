# Atlas Viewer / CAS Harness — Full Product Roadmap

**Status:** Locked 2026-05-22 by user.
**Companion docs:** `atlas_viewer_v0_product_scope_2026_05_22.md` (v0.0 → v0.3 phasing), `atlas_viewer_neuralnet_scene_design_2026_05_22.md` (3D scene design).

This document captures the 15-item product composition. It extends — does not replace — the v0 scope doc. Six items below are net-new versus the prior scope doc and are marked **NEW**.

---

## Product framing

> CAS Compass measures model **behavior**. CAS Harness Atlas explains the **evidence path** behind that behavior. The strongest claim — and the strongest product story — is when the two agree on a model's failure pattern. The most valuable signal is when they disagree.

The cockpit is the front door. The product is the full workflow around attaching a model, running CAS tests, watching the evidence story, and exporting defensible results.

---

## Sequencing

```
Viewer (live, 9287f63 + dashboard-managed service)
   ↓
Scenarios (200+ Compass catalog → Atlas Library)
   ↓
Compass↔Atlas Concordance (same model, behavior vs evidence)
   ↓
Method Modules (live execution, not just registry cards)
   ↓
External Model Intake (user-supplied model IDs + adapters)
   ↓
Licensing / Billing
   ↓
Legal / IP review
   ↓
Production Infrastructure (worker service for heavy GPU jobs)
```

Wave-5 UI polish (item 15) runs in parallel with Scenarios + Concordance — different files, no conflict.

---

## The 15 items

### 1. Hosted Atlas Viewer alpha — **LIVE**

- 3D neural net cockpit ✓ (Pythia-160M, 12 × 3072 InstancedMesh neurons)
- Mode 7 trace timeline ✓
- 2D/spatial evidence panel ✓ (Spatial Evidence Layer wave 1.5)
- Evidence drawer ✓ (placeholder, fixture-backed)
- Playback / scrub / zoom controls ✓ (zoom Z0-Z5 with camera tween)

Live at `https://atlas-viewer-app.onrender.com`. Shared backend at `https://noetic-compass-api.onrender.com`. Service is Render-dashboard-managed (Blueprint validator rejected the static-site YAML block; bypassed via REST API). Custom domain `atlas.noeticcompass.com` pending DNS attachment.

### 2. Scenario Library — **NEW**

- Import the existing 200+ Noetic Compass scenarios into atlas-viewer as `scenario_pack_noetic_compass_v0.jsonl`
- Curated golden subset (20–30 scenarios) for the alpha demo URL
- Per-scenario schema: `scenario_id`, `title`, `source`, `prompt`, `domain`, `expected_cas_axes`, `expected_failure_modes`, `compass_baseline_score`, `atlas_expected_outputs`
- Left-panel scenario picker in the cockpit
- Each scenario loads a pre-computed Pythia-160M baseline trace; user compares "what the reference model did on healthcare-04" against any other model
- 400 augmented-library scenarios ship later as a downloadable pack (`scenario_pack_v0.1`)

### 3. Compass ↔ Atlas Concordance — **NEW**

- Run the same model + scenario set through both Compass and Atlas
- Per-scenario comparison fields:
  - Compass score
  - Atlas Verification Stack verdict (ACCEPT / CONSTRAIN / SUPPRESS)
  - Blindspot severity
  - Inversion proxy score
  - RPM gate status
  - Evidence packet confidence
  - Mode 7 trace pattern
- Concordance report: agreement by category, not exact numbers
- **Mismatches are the gold.** Two cases that drive research/product value:
  - Compass says answer was good but Atlas shows high blindspot → fragile internal path
  - Compass says answer was bad but Atlas shows stable trace → scoring rubric or output parser needs work
- Output: `compass_atlas_concordance_report_<model>_<scenario_pack>.md`

### 4. Testing Method Modules

Registry already exists in `atlas-viewer/src/lib/testingMethods.ts` (9 modules); next step is **live execution** against actual models, not just the card UI.

- Foundation Probe (Stage 26 anchor)
- RPM Gate Check
- Inversion Scan (7-axis)
- Sparse Neuron-Cover Discovery (Stage 27F/G)
- Drive-Local Eraser Steering (Stage 27O/P)
- Blindspot Detection
- Verification Stack (Mode selector: BALANCED / HIGH_PRECISION / MAX_COVERAGE_TRIAGE)
- Evidence Packet export
- Spatial Evidence Layer ✓ (already wired, wave 1.5)

### 5. User / Developer Onboarding

- Login flow (real, not placeholder — currently in `LoginPage.tsx`)
- API key manager UI
- License key manager UI
- Model config page (HF model ID input)
- Trial mode
- Guided first-run walkthrough

### 6. External Model Attachment

- User supplies API/model credentials
- Architecture discovery from HF `config.json`
- Supported-architecture adapters (Pythia / OLMo / Qwen / Llama / Mistral / Gemma / Phi / GPT-NeoX)
- "Unknown model" intake workflow with "request adapter" form
- Validation-status labels (Validated / Exploratory / Refused)

### 7. Architecture Mapper — **NEW**

- Pointer / draw / recreate unfamiliar model architectures
- Auto-generated layer map
- Neuron / feature map
- Traceable component graph
- Confidence labels for inferred architecture
- For models where Atlas doesn't have a pre-built adapter but the user wants to push through anyway

### 8. Live Harness Runs

- Job queue
- Run selected testing modules
- Progress display
- Stream trace events to the cockpit live (extends Mode 7 SSE infra)
- Pause / stop / replay
- Save run artifacts (linked to Evidence Packets)

### 9. Evidence Packet System

- Signed JSON packet (15-field schema; partially exists)
- Human-readable report (markdown)
- Provenance hashes
- Row-level evidence links
- Downloadable audit bundle (.zip with packet.json + packet.md + signed manifest)

### 10. Atlas Reviewer Workflow — **NEW**

- Reviewer notes (annotations on the cockpit + on Evidence Packet rows)
- Claim ↔ evidence mapping (which packet rows support which audit claim)
- Accept / constrain / suppress decisions per claim
- Comparison across runs (longitudinal view)
- Export for NDA auditors / partners
- This is the "what does an NDA auditor actually do here" layer

### 11. Licensing / Billing

Per `atlas_viewer_v0_product_scope` §4:

- Community / Professional / Enterprise tiers
- Time-limited license keys
- Model slot limits
- Usage caps (req/min, req/month)
- Stripe (or Paddle / LemonSqueezy for international tax) integration
- Manual Enterprise billing flow

### 12. Security / Legal / IP

- ToS (alpha → public)
- Privacy policy
- Customer data policy
- No-training / data flywheel terms (anonymized run aggregation opt-in)
- IP attorney packet (USPTO #64/037,173 scope confirmation)
- NDA-gated partner language

### 13. Deployment / Infrastructure

- Hosted preview ✓ (live)
- Production app
- Shared API ✓ (live, Render)
- Atlas worker service (separate from main API) — for heavy GPU jobs, queues, uploads, cost control
- GPU job runner
- Artifact storage
- Monitoring / logging

### 14. Scenario + Benchmark Expansion — **NEW**

- Compass scenario pack (item 2 ships v0)
- CAS Harness benchmark pack (atlas-native scenarios beyond Compass)
- Open-weight model comparison reports
- Customer-submitted evals (gated, NDA where required)
- Longitudinal model reports (same model across version bumps; concordance shifts over time)

### 15. Polish / Demo / Sales Surface — **NEW**

- Wave-5 UI redesign — liquid-glass aesthetic (per user direction 2026-05-22):
  - Floating panels with `backdrop-filter: blur()` + semi-transparent fills
  - Spring physics animations (framer-motion)
  - Mouse-position parallax (substituting for device tilt on desktop)
  - Inter font + dark-only theme at v0
  - Cockpit panels float over Three.js scene; scene gets ambient tint integration
- Alpha walkthrough doc (5-minute partner demo path)
- Demo script (narrator-led)
- Onboarding copy (every visible TODO / placeholder string scrubbed or labeled honestly)
- Investor-safe screenshots
- Partner-facing deck
- Public launch page (post-alpha)

---

## What ships in wave 5 (alpha-demo readiness)

Three parallel workstreams against the live cockpit:

1. **Scenario library** (item 2) — data work, JSON loader extension, left-panel UI
2. **Concordance report** (item 3) — Compass + Atlas comparison harness, run pipeline, markdown report
3. **UI polish** (item 15) — liquid-glass redesign of cockpit panels

After wave 5: items 4 (live methods), 6 (external intake), 8 (live runs) are the heavy v0.1 → v0.2 work that requires backend orchestration + GPU.

---

## What's deferred to a separate workstream (not blocking alpha demo)

- Full SGGS product integration (per `sggs_v2_v3_backlog`)
- Architecture Mapper (item 7 — needs novel research)
- Atlas Reviewer Workflow (item 10 — needs auditor UX research)
- Multi-tenant licensing (item 11 — needs Stripe + auth infra)
- Live GPU worker service (item 13 — needs ops decisions)

---

## Status of each item against current branch

| # | Item | Status | Anchor |
|---|---|---|---|
| 1 | Hosted Atlas Viewer alpha | **LIVE** | `https://atlas-viewer-app.onrender.com` |
| 2 | Scenario Library | TODO | Wave 5 |
| 3 | Compass↔Atlas Concordance | TODO | Wave 5 |
| 4 | Method Modules (registry) | ✓ partial | `testingMethods.ts` exists; live execution TODO |
| 5 | User/Developer Onboarding | placeholder | `LoginPage.tsx` stub |
| 6 | External Model Attachment | TODO | v0.2 (per v0 scope doc) |
| 7 | Architecture Mapper | **NEW** TODO | post-v0.2 |
| 8 | Live Harness Runs | TODO | v0.2 / v0.3 |
| 9 | Evidence Packet System | ✓ partial | drawer + fixture-backed schema |
| 10 | Atlas Reviewer Workflow | **NEW** TODO | post-v0.2 |
| 11 | Licensing / Billing | TODO | v0.1 (per v0 scope doc) |
| 12 | Security / Legal / IP | TODO | v0.2 pre-requisite |
| 13 | Deployment Infrastructure | ✓ partial | Render live; worker service deferred |
| 14 | Scenario Expansion | **NEW** TODO | wave 5+ |
| 15 | Polish / Demo / Sales Surface | **NEW** TODO | Wave 5 (UI redesign starts now) |

---

## Open questions (carry over from prior scope docs)

Unchanged from `atlas_viewer_v0_product_scope_2026_05_22.md` §9 (Q1–Q13).

Two new wave-5-specific:

- **Q14** (wave 5 UI) — Inter / Geist / SF Pro web font? *Defaulted to Inter pending redirect.*
- **Q15** (wave 5 UI) — Dark-only / light-dark toggle / system-following? *Defaulted to dark-only pending redirect.*
