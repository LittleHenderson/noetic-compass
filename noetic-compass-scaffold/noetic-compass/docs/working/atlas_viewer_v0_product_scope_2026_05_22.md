# CAS Harness Atlas Viewer — v0 Product Scope

**Status:** Draft for user sign-off
**Date:** 2026-05-22
**Anchor branch:** experiment/cas-probe-pythia
**Companion doc:** `atlas_viewer_neuralnet_scene_design_2026_05_22.md`

---

## 1. Product framing

Atlas Viewer is a standalone, licensed beta product on a separate domain from `noeticcompass.com`. It is a developer-facing dashboard that lets users plug in their own AI model (HuggingFace model ID), run the CAS Harness's validated testing battery against it, and watch the resulting reasoning trace as an explorable 3D + 2D evidence map. Every visual element ties back to a 15-field Evidence Packet — model coordinate (Layer N, Neuron M), CAS interpretation, validated Stage artifact, sample-level proof.

**North-star claim (single sentence):**

> Atlas Viewer lets users watch an AI model's reasoning trace as an explorable 3D/2D evidence map, with every visual claim tied back to a verification artifact.

**Audiences:**

- **R&D teams** (academic + corporate) — interpretability research, model auditing
- **Alpha partners** (enterprise) — pre-deployment safety review of in-house models
- **Individual developers** (hobbyist + indie) — exploration tier, community access

**What it is NOT:**

- Not a marketing demo. It's a paid, licensed product.
- Not a CAS-Native AI demo. It's the harness applied TO a user's model.
- Not a universal "any AI" tool. Users supply HuggingFace-hostable models from a supported architecture family; unknown families are gracefully refused with a "request adapter" form.

**Data flywheel framing:** users on untested architectures generate exploratory runs that, aggregated anonymously and at sufficient independent-run count, graduate that architecture from Exploratory to Validated. Users get early access; we get the validation expansion. ToS opt-in is the legal posture.

---

## 2. Phased scope — what ships when

### v0.0 — Demo cockpit (4–6 weeks)

**Goal:** Alpha-partner demo. One model, no user intake yet.

- Pythia-160M only (smallest validated arch; Stage 27O/27P/27F artifacts already point at it)
- Replay-only: traces are pre-recorded fixtures, not live runs
- Module picker (read-only) — shows the 7 testing methods with cards
- 3D NeuralNetScene with Pythia-160M architecture hardcoded
- Mode 7 Timeline + 2D Notation Panel + Evidence Drawer + Control Bar
- Gated waitlist signup (no auth yet — Calendly link or Typeform)

**Deliverable:** 5-minute demo path. Alpha partner sees the model's reasoning replay end-to-end on a curated trace.

### v0.1 — Paid beta (additional 6–10 weeks; cumulative 10–16 wks)

**Goal:** Real users pay real money to run real harness jobs.

- Standalone Vite app at atlas-viewer/ subdomain (e.g. `atlas.noeticcompass.com`)
- Auth: existing JWT middleware + new license-key second-factor
- License tiers (Community / Professional / Enterprise) — see §4
- Stripe billing integration
- User-supplied HF model ID → async job queue → email-on-completion
- Per-tenant quota tied to existing rate limiter
- Pythia-160M still the only supported arch; users run on validated arch only at this phase

**Deliverable:** Paid product. First $1 of revenue.

### v0.2 — Multi-arch + flywheel (additional 4–8 weeks; cumulative 14–24 wks)

**Goal:** Users plug in their own untested model, contribute to validation graduation.

- Auto-scaling NeuralNetScene (per companion doc)
- Multi-arch capture adapter framework (Llama, Mistral, Gemma, Phi, Qwen, OLMo, Pythia, GPT-NeoX)
- "Exploratory" result banding for runs on untested archs
- Validation-graduation queue surface — public dashboard showing arch graduation status
- ToS opt-in for anonymized run aggregation

**Deliverable:** Data flywheel turns on. Architectures graduate from "exploratory" to "validated" as independent run counts accrue.

### v0.3 — Live + hosted + collaborative + full SGGS (additional 30–46 wks serialized; 16–24 wks with parallel workstreams, SGGS-bound; cumulative 44–70 wks or 30–48 wks)

**Goal:** Atlas Viewer becomes a hosted, live-streaming, multi-user product with full SGGS gesture-graph integration. The flagship demo. SGGS is the parallelization long-pole at this phase.

- **Live model attachment** (~4–6 wks)
  Replay path extended with live forward-pass streaming. Mode 7 SSE infrastructure extended to stream per-token activations + per-layer state. Client-side throttling/smoothing (delta-encoded frames, per-layer LOD). Pause freezes the stream; scrub re-plays buffered history (default buffer: last 256 tokens). NeuralNetScene gets a new `LiveStreamProvider` props branch.

- **Hosted model inference** (~6–10 wks)
  We host the user's chosen validated model on managed GPUs (Modal / RunPod / cloud). User picks model from a curated catalog; we run forward passes + all modules in one job. Removes the "user supplies GPU" friction at the cost of operational lift (per-tenant isolation, model lifecycle, cost passthrough or markup). Likely tier-gated (Pro / Enterprise only at launch).

- **Multi-user collaboration** (~4–6 wks)
  Multiple users view the same trace with shared cursor, comments, annotations, presence indicators. Realtime sync via WebSocket (Liveblocks recommended; Yjs as self-hosted alternative). Permission model: owner / editor / viewer / commenter. v0.3.0 ships view-only collab (read presence + comments); editor-level collab folds in at v0.3.1.

- **Full SGGS integration** (~16–24 wks — **CONFIRMED full scope per user 2026-05-22**; parallelization long-pole)
  Full SGGS product per `sggs_v2_v3_product_feature_backlog_2026_05_06.md`. Four sub-systems land in v0.3, each demoable on its own gate:
  - **Gesture vocabulary** (wks 1–6): MediaPipe Hands → 10-gesture cockpit map (pinch/zoom, swipe/scrub, point+hold/select, fist/pause, palm-raise/reset, two-hand-spread/fit, two-hand-rotate/orbit, index-finger-trace/annotate, thumbs-up/bookmark, cup-hands-gather/evidence-packet).
  - **Canonical graph identity** (wks 7–12): the model's neuron graph becomes the canonical graph object with stable IDs that persist across sessions, users, replay vs live. Annotations / bookmarks / comments / witness records anchor to canonical neuron IDs. Backend: `api/routes/sggs_graph.py`.
  - **Live-witnessing protocol** (wks 13–18): multi-user co-presence as gesture overlays on the scene (not just cursors). Witness records persist on canonical graph and surface in Evidence Packets. Extends collab `peerCursors` → `peerGestures`.
  - **Rewind / slow-motion** (wks 19–24): gestures interact with replay timeline (pinch-out = slow time 0.25×, pinch-in = reverse, palm-down = freeze). The headline "show me the moment the model picked this answer" demo behavior.

**Deliverable:** Fully hosted, collaborative, gesture-driven beta with canonical graph identity, live witnessing, and slow-motion replay. The "wow" demo flagship.

### v0.4+ (out of scope for this doc)

- Mobile / tablet client
- VR/AR client
- Open-source release path
- Marketplace for community-contributed module knobs
- Public API for headless module execution

---

## 3. Architecture — reuse map + new build

### What gets reused (no new build)

| Component | Path | Reuse fit |
|---|---|---|
| JWT auth middleware | `api/middleware/auth.py` | Add license-key validation as 2nd factor |
| Tiered rate limiter | existing | Map new license tiers to existing community/professional/enterprise slots |
| Evidence Packet API | `api/routes/harness_evidence.py` | Serves `GET /api/harness/evidence/{trace_id}` unchanged |
| Mode 7 SSE streaming | `api/routes/mode7.py` + `dashboard/src/Mode7LiveShell.tsx` | Reused inside `Mode7Timeline` |
| DB models | `api/models/` | `Idea` and `Assessment` tables already keyed by `api_key`/`user_id` |
| CAS color palette | `dashboard/src/lib/casColorPalette.ts` | Copy into `atlas-viewer/src/lib/atlasPalette.ts` with extensions |
| Notation 2D map | `dashboard/src/lib/notation2DMap.ts` + `Notation2DView.tsx` | Wrapped as `Notation2DPanel` |
| Evidence Packet Drawer | `dashboard/src/EvidencePacketDrawer.tsx` | Wrapped as `EvidenceDrawer` |
| Stage 27F neuron-cover data | `research/cas_probe/.tmp/stage27f_smoke.json` | Loaded directly via new `neuronCover.ts` types |

### What's new — 10 work items

**A. Standalone app (items 1–2)**

1. **Vite scaffold** — `atlas-viewer/` new directory, separate build, shares API backend
2. **Auth + license layer** — API-key generation flow, license-key validation, license management UI

**B. Model + method config (items 3–4)**

3. **Model configuration** — HF model ID input, architecture detection, validation banner ("validated" / "exploratory")
4. **Testing method module system** — registry with card data, toggles, info panels, cost estimates

**C. 3D + cockpit (items 5–8)**

5. **Data layer** — Stage 27F neuron-cover types with model-native coordinates, colloquialism map, replay pipeline
6. **NeuralNetScene** — 3D Three.js viewer (see companion doc)
7. **AtlasViewerShell** — unified cockpit stitching 3D + Mode 7 + 2D + Evidence + ControlBar
8. **ReplayController** — timeline-driven animation hook

**D. Polish (items 9–10)**

9. **Integration** — auth-gated router, smoke tests, evidence drawer cross-linking
10. **Onboarding + docs** — first-run tour, knob explanation tooltips, plain-English module descriptions

### New file structure

```
noetic-compass-scaffold/noetic-compass/
├── atlas-viewer/              ← NEW standalone Vite app
│   ├── src/
│   │   ├── App.tsx            ← auth-gated router
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── LicensePage.tsx
│   │   │   ├── ModelConfigPage.tsx
│   │   │   └── CockpitPage.tsx
│   │   ├── components/
│   │   │   ├── cockpit/
│   │   │   │   ├── NeuralNetScene.tsx
│   │   │   │   ├── AtlasViewerShell.tsx
│   │   │   │   ├── Mode7Timeline.tsx
│   │   │   │   ├── Notation2DPanel.tsx
│   │   │   │   ├── EvidenceDrawer.tsx
│   │   │   │   ├── ControlBar.tsx
│   │   │   │   ├── MethodKnobsPanel.tsx
│   │   │   │   ├── LiveStreamProvider.tsx   ← v0.3
│   │   │   │   ├── CollabPresence.tsx       ← v0.3
│   │   │   │   ├── CommentLayer.tsx         ← v0.3
│   │   │   │   └── GestureLayer.tsx         ← v0.3
│   │   │   └── auth/
│   │   │       ├── ApiKeyManager.tsx
│   │   │       └── LicenseGate.tsx
│   │   ├── lib/
│   │   │   ├── neuronCover.ts
│   │   │   ├── colloquialismMap.ts
│   │   │   ├── atlasPalette.ts
│   │   │   ├── replayController.ts
│   │   │   ├── modelArchitecture.ts
│   │   │   ├── testingMethods.ts
│   │   │   ├── liveStream.ts                ← v0.3
│   │   │   ├── collabSync.ts                ← v0.3
│   │   │   └── gestureControls.ts           ← v0.3
│   │   └── hooks/
│   │       ├── useAuth.ts
│   │       ├── useLicense.ts
│   │       ├── useReplayController.ts
│   │       ├── useLiveStream.ts             ← v0.3
│   │       ├── useCollab.ts                 ← v0.3
│   │       └── useGestures.ts               ← v0.3
│   ├── package.json
│   └── vite.config.ts
├── api/
│   ├── routes/
│   │   ├── license.py
│   │   ├── model_config.py
│   │   ├── testing_methods.py
│   │   ├── live_stream.py                   ← v0.3
│   │   ├── hosted_inference.py              ← v0.3
│   │   └── collab.py                        ← v0.3
│   └── middleware/
│       └── license.py
└── dashboard/                 ← existing, unchanged
```

---

## 4. License tier model

Tiers map directly to existing rate-limiter slots.

| Tier | Req/min | Req/month | Arch access | Model slots | License term | Price |
|---|---|---|---|---|---|---|
| Community | 10 | 50 | Pythia-160M only | 1 | 7-day trial | Free |
| Professional | 30 | 500 | Any validated arch up to 1B params | 3 | 30-day license | TBD ($X/mo) |
| Enterprise | 120 | Unlimited | Any arch (incl. exploratory) | Unlimited | Annual license | TBD ($Y/yr) |

License keys are time-limited bearer tokens issued at checkout. Validated server-side per request alongside the JWT. Revocation = drop from license-key allow-list.

Exploratory-arch access is gated to Enterprise tier at v0.2 (per legal posture — see §7).

---

## 5. Testing method module catalog

Each module is one validated Stage protocol exposed as a knob with a card. Cards include:

- **Name** (user-facing)
- **What it does** (plain English, 1–2 sentences)
- **What it reveals** (the data story)
- **Stage anchor** (which validated artifact backs this)
- **Knob** (parameter the user controls)
- **Output shape** (what they get)
- **Compute cost** (estimated GPU minutes at default budget)
- **Prerequisites** (model artifacts required: activations / weights / etc.)

### Module 1: Foundation Probe

- **What:** Reads the 7-drive Foundation signal from model hidden states using linear probes
- **Reveals:** Per-layer activation map showing which drives the model is engaging
- **Stage:** 26 (linear probe readout, validated three families)
- **Knob:** Which axis (Noetic / Domain / Drive / Register) + layer range
- **Output:** Per-layer accuracy table + heatmap visualization
- **Cost:** ~5 GPU minutes for full sweep on Pythia-160M
- **Prereq:** Forward-pass hidden state capture

### Module 2: RPM Gate Check

- **What:** Tests whether prerequisite chains are complete along the model's reasoning path
- **Reveals:** Pass/fail status per pathway node (A0 → Dn → Wn → Pn → Outcome)
- **Stage:** RPM monad implementation (Correction 2: section-retraction, one-directional)
- **Knob:** Which pathway nodes to check; strictness threshold
- **Output:** Pathway diagram with gate verdicts
- **Cost:** ~2 GPU minutes
- **Prereq:** Trace artifact with token-position alignment

### Module 3: Inversion Scan

- **What:** Scans for structural drift across 7 inversion axes (N / W / F / E / S / A / P)
- **Reveals:** Severity ranking of detected inversions
- **Stage:** 7-axis inversion scanner from `cas-engine`
- **Knob:** Scan all 7 axes vs filtered subset; severity threshold
- **Output:** Inversion report with axis-by-axis breakdown
- **Cost:** ~3 GPU minutes
- **Prereq:** Forward-pass hidden states + RPM trace

### Module 4: Sparse Neuron-Cover Discovery

- **What:** Finds the smallest neuron set causally responsible for a target class
- **Reveals:** Model-native neuron coordinates (e.g. `L5N2648`) per class
- **Stage:** 27F/27G (sparse MLP-neuron-cover causal localization)
- **Knob:** Target class + sparsity budget (default: greedy until `clean_margin < threshold`)
- **Output:** `neuron_cover` list with `clean_margin` + `targeted_drop` scores
- **Cost:** ~15 GPU minutes (greedy search dominant)
- **Prereq:** Stage 26-style probe + ablation harness

### Module 5: Drive-Local Eraser Steering

- **What:** Suppresses a specific Foundation drive at the model's output side via a calibrated cover
- **Reveals:** Whether the drive is causally controllable (vs merely readable)
- **Stage:** 27O / 27P (validated cross-arch on Pythia + Qwen; asymmetric closure flagged for OLMo)
- **Knob:** Which of 7 Foundation drives + gain (default: calibrated cover, gain=1.0)
- **Output:** Pre/post output-distribution shift + matched-control p-value
- **Cost:** ~10 GPU minutes per drive
- **Prereq:** Module 4 output (neuron cover) for the target drive

### Module 6: Blindspot Detection

- **What:** Reports per-drive eraser-channel cover positions across selected layers
- **Reveals:** Where the model's representation is suppressing each drive (the "blind spots")
- **Stage:** 27P-derived (cover positions are by-product of Modules 4 + 5)
- **Knob:** Scope (one drive vs all 7); layer range
- **Output:** Per-drive blindspot overlay on NeuralNetScene + cover position table
- **Cost:** Free if Modules 4 + 5 already run; otherwise their cost
- **Prereq:** Modules 4 + 5

### Module 7: Verification Stack

- **What:** Multi-probe ensemble that decides whether to ACCEPT or SUPPRESS each generated token
- **Reveals:** Per-token verdict with confidence margin
- **Stage:** Verification Stack (assembled from Modules 1, 3, 6)
- **Knob:** Mode (BALANCED / HIGH_PRECISION / MAX_COVERAGE_TRIAGE)
- **Output:** Per-token ACCEPT / SUPPRESS / FLAG table
- **Cost:** ~1 GPU minute amortized across modules already run
- **Prereq:** Modules 1, 3, 6 outputs

### Module 8 (output): Evidence Packet

- **What:** 15-field signed audit artifact bundling all module outputs for a run
- **Reveals:** Full provenance — what was tested, with what knobs, on what model, under what license
- **Stage:** `evidence_packet_v1` schema (already deployed in `dashboard/src/lib/evidencePacket.ts`)
- **Knob:** Include / exclude per-token detail (default: include); export format (JSON / markdown)
- **Output:** Downloadable `.json` + `.md` + signed manifest
- **Cost:** Free (it's the report)
- **Prereq:** Any module output

---

## 6. Auth & license flow

```
User signs up
    ↓
JWT issued (existing flow)
    ↓
User purchases license key (Stripe checkout)
    ↓
License key issued, bound to user_id, expiry recorded
    ↓
On each API request:
    1. JWT validated (existing middleware)
    2. License key validated (new middleware): not expired, not revoked, tier matches endpoint
    3. Rate limit checked (existing middleware): per-tier quota
    4. Request proceeds
```

License keys are NOT short-lived. They are tier-and-expiry tokens. Revocation drops them from the allow-list immediately.

---

## 7. Multi-arch intake & data flywheel

### Architecture support matrix (v0.2)

| Family | v0.0 | v0.1 | v0.2 |
|---|---|---|---|
| Pythia | 160M | 160M | 160M / 1B / 2.8B |
| OLMo | — | — | 1B (validated readout; steering exploratory pending Stage 27P-OLMo) |
| Qwen | — | — | 2.5-1.5B |
| Llama | — | — | Exploratory |
| Mistral | — | — | Exploratory |
| Gemma | — | — | Exploratory |
| Phi | — | — | Exploratory |
| GPT-NeoX | — | — | Exploratory |
| Unknown family | — | — | Refused with "request adapter" form |

### Result banding

Every result ships with one of three bands:

- **Validated** — green badge. Arch is in the validated set. Cite Stage artifact.
- **Exploratory** — yellow badge. Arch is plausibly supported but pending sufficient independent runs to graduate. Confidence bands widened. Disclaimer: "These results are exploratory and contribute to validation graduation."
- **Refused** — red banner. Unknown architecture; module did not run. Request-adapter form.

### Graduation queue

Architectures graduate from Exploratory → Validated when:

- At least N independent successful runs from distinct users (default N = 20)
- Run-level diagnostics pass pre-registered NULL/GREY/PASS thresholds for that arch
- An internal reviewer signs off

Graduation status surfaced publicly on a "validated architectures" page.

### ToS / DPA posture

- ToS opt-in (default: opt-in required for Enterprise; opt-out available for Community/Pro at v0.2)
- Anonymized: only protocol-level metrics aggregate. User-supplied weights and prompts NEVER aggregate.
- Privacy policy + Data Processing Addendum drafted with legal review
- **Flag for IP attorney:** this is the validated-protocol layer, distinct from the validated-primitives layer (USPTO #64/037,173). Confirm scope before v0.2 ToS lock-in.

---

## 8. Risk register

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | Overclaim — user-facing copy says "any AI" before v0.2 | High | Hard-wire result banding into every result page; legal copy review |
| R2 | Adapter coverage gap — user uploads model from unknown family | Medium | "Refused" banner with "request adapter" form; coverage matrix on landing page |
| R3 | License-key leak — keys are bearer tokens | Medium | Server-side validation per request; one-click revocation in user UI |
| R4 | NeuralNetScene performance on large archs | High | Level-of-detail rendering (companion doc); refuse archs >70B params at v0.2 |
| R5 | IP attorney has not signed off on data-flywheel scope | High | Schedule attorney call before v0.2 ToS lock-in |
| R6 | User-supplied model is gated on HuggingFace | Medium | User supplies HF token in license-protected secrets vault; per-tenant key isolation |
| R7 | Stripe / payment provider downtime locks users out | Low | Cache license validity 24h; degrade gracefully on payment-provider outage |
| R8 | Hosted-GPU operational lift exceeds capacity at v0.3 launch | High | Start on managed providers (Modal / RunPod); in-house GPU pool only at enterprise scale; aggressive idle-model unload policy |
| R9 | Live-stream bandwidth saturates client connection on large archs | Medium | Per-layer LOD delta-encoding; throttle to client frame rate; degrade to replay if buffer underruns 3× consecutively |
| R10 | Multi-user state-sync conflicts (concurrent annotations / cursor races) | Medium | v0.3.0 ships view-only collab (read presence + comments only); editor-level collab gated behind Liveblocks CRDT or Yjs at v0.3.1 |
| R11 | Full SGGS workstream is the v0.3 parallelization long-pole — slip drags v0.3 | High | 4 × 4–6 wk sub-deliverable gates per `sggs_v2_v3_product_feature_backlog_2026_05_06.md` (gesture vocab → canonical graph → live-witnessing → rewind/slow-mo); each sub-deliverable demoable on its own; cockpit remains interactive after wk 6 even if later sub-systems slip |
| R12 | Hosted-inference cost-passthrough billing gets miscalibrated | High | Per-job cost cap; require user pre-authorization for jobs > $5 estimated cost; daily/monthly spend caps per tier |

---

## 9. Open questions for user sign-off

- **Q1.** Domain — `atlas.noeticcompass.com` subdomain, or separate domain entirely?
- **Q2.** Pricing — Community free, Professional $X/mo, Enterprise $Y/yr — fill in X and Y, or wait until v0.1 launch?
- **Q3.** Payment provider — Stripe is default; alternatives (Paddle, LemonSqueezy) worth considering for international tax handling?
- **Q4.** Enterprise sales motion — self-serve at v0.1 or sales-assisted (Calendly intake)?
- **Q5.** Validation graduation threshold — N = 20 runs is a guess. What's the right number?
- **Q6.** Adapter-request backlog SLA — how fast do we commit to building new adapters from user requests?
- **Q7.** Open-source vs proprietary — any part of `atlas-viewer/` open-sourced (the React shell) vs fully proprietary?
- **Q8.** Branding — name lock: "CAS Harness Atlas Viewer" or shorter ("Atlas Viewer", "Noetic Atlas")?
- **Q9.** ~~SGGS depth~~ — **RESOLVED 2026-05-22:** full SGGS scope confirmed by user. v0.3 includes the complete product per `sggs_v2_v3_product_feature_backlog_2026_05_06.md` (gesture vocabulary + canonical graph identity + live-witnessing protocol + rewind/slow-motion design). 16–24 wks, parallelization long-pole for v0.3.
- **Q10.** Hosted-GPU provider — Modal (fast iteration, managed) vs RunPod (cheaper, more raw) vs cloud (AWS / GCP A100s, max control). Recommendation: Modal at v0.3 launch, switch to cheaper provider once volume justifies.
- **Q11.** Collab realtime backend — Liveblocks (SaaS, batteries-included, monthly cost per MAU) vs Yjs (self-hosted CRDT, more work, no per-user cost). Recommendation: Liveblocks at v0.3.0; revisit at scale.
- **Q12.** Live-mode default — opt-in (default: replay; user toggles live) or default-on for hosted models (auto-stream from inference jobs). Recommendation: opt-in at v0.3.0; default-on at v0.3.1 once UX is proven.
- **Q13.** Hosted-inference catalog curation — which models, in what order? Validated set first (Pythia-160M / 1B / 2.8B, OLMo-1B, Qwen2.5-1.5B), then exploratory archs by user request, or open the gate to any HF-hosted model day-one?

---

## 10. Sign-off

Sign-off required before any v0.0 code lands:

- [ ] Domain (Q1)
- [ ] North-star claim wording final (§1)
- [ ] Phased scope acceptance (§2)
- [ ] License tier structure (§4) — TBD prices acceptable for v0.0 scope
- [ ] Module catalog (§5) — list complete and correct
- [ ] Risk register (§8) — additions / corrections
- [ ] IP attorney scope confirmation (R5) before v0.2 work begins

Subsequent gates:

- v0.0 → v0.1: license + auth shipped, first paid user; revisit pricing (Q2)
- v0.1 → v0.2: multi-arch adapter framework ready, attorney sign-off, ToS published
- v0.2 → v0.3: hosted-GPU provider chosen (Q10), collab backend chosen (Q11), SGGS sub-deliverable plan locked against `sggs_v2_v3_product_feature_backlog_2026_05_06.md` (Q9 RESOLVED full scope), cost-passthrough billing model validated against test runs (R12), live-stream LOD validated on largest validated arch (R9)
