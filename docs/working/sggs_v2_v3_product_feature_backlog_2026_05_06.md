# SGGS — Spatial Gesture Graph Specification (v2/v3 product backlog)

**Status:** BACKLOG. Do NOT dispatch engineering until v0 ships. Captured 2026-05-06 to preserve technical specifics so this doesn't have to be re-researched when implementation time arrives.

**Sequencing this sits behind:**
- v0: K=9 classifier + native NL gen head + 50K Tier 3 dialogue corpus → working conversational model
- v1: Path C — Simplex Δ°₃₉ rebuild (cognitive substrate as continuous probability simplex with Fisher-Rao metric)
- v1.5: Meta-logic proof layer over RPM (inspectable "why did the gate pass/fail")
- **v2/v3: SGGS — this document.**

Engineering estimate: 16-24 weeks total (8-12 baseline visualization + 8-12 live witnessing with rewind + gesture integration). This is product engineering, not research. Not a v0 blocker.

---

## What SGGS is

A 3D, gesturally-manipulable, structurally-meaningful viewer for CAS-Native generation. Three composable layers:

1. **Baseline 3D visualization** — interactive 3D rendering of CAS diagrams and Idea Atlas with omnidirectional rotation, zoom, and node manipulation.
2. **Live generation witnessing** — visualization updates in real-time as the model produces structured output. Structural assembly is observable as a temporal process, not just as a finished result.
3. **Rewind + slow-motion playback** — timeline scrubber with playback controls (play, pause, slow-motion at 0.25x/0.5x/0.75x, frame-step, fast-forward, scrub, bookmark). Like a video editor for cognition.

These compose. Phase 1 is baseline 3D. Phase 2 adds live + rewind. They're sequenced extensions, not parallel features.

---

## Why this is real product value (not feature creep)

Three reasons SGGS is more than visual polish:

### 1. Interpretability at the temporal level
Most AI interfaces show finished output with maybe a streaming-token effect. SGGS shows **structural assembly** — noetic axis appearing first, then domain locking in, then foundation reference attaching, then cluster containers forming. That reveals the order of cognitive operations. It's interpretability at the temporal level, complementing Mode 7 mechanistic interpretability at the layer level.

### 2. Audit-grade observability
Real-time-only viewing is demo-grade. Rewind makes it audit-grade: stakeholders can replay the moment a domain assignment locked in, slow it down, examine what context was present when the model committed. That's what regulators, compliance reviewers, and skeptical stakeholders actually need.

### 3. Connects symbolic + neural interpretability stacks
Rewind to the moment Domain Descent Attention layer fired. Slow-motion through activation propagation. Watch which input tokens were load-bearing for that specific structural commitment. SGGS makes the two-level interpretability story (symbolic CAS structure + neural mechanistic trace) **temporally inspectable**, not just statically queryable.

### 4. Bonus: new product category
No current AI product shows live structured-thought formation. Streaming text yes. Streaming structure no. SGGS would define what "watching AI think structurally" looks like as a UX paradigm. Strong differentiation for stakeholder demos, conference talks, partnership conversations.

---

## Technical building blocks (all mature, low adoption risk)

### Gesture recognition: MediaPipe Hands
- Google-maintained production library
- Hand-keypoint tracking via webcam at acceptable browser framerates
- Stable JavaScript API, well-documented gesture vocabulary
- **Privacy property**: runs locally in browser. No data leaves the machine. Critical for regulated-domain deployment (medical, legal, financial). Server-side gesture recognition would disqualify SGGS from those domains.
- Three core gestures already documented: fist-spin (rotation), pinch (node drag), two-hand pinch-spread (zoom)

### 3D rendering: Three.js
- De-facto standard for web 3D
- Force-directed graph implementations exist as libraries
- Handles thousands of nodes well; tens of thousands needs optimization
- Massive ecosystem; little risk of abandonment

### Reference implementation
- Telecladius / Bles Software gesture demo: working integration of MediaPipe + Three.js, shows the pattern works end-to-end. Use as reference, not as dependency.

### Existing infrastructure SGGS builds on
- **Structured prediction heads** (12 heads landing one at a time during inference): drives the live structural-assembly updates. Already produced by training architecture.
- **Mode 3 per-utterance trace** (user_text → parsed_intent → pre_state → operators → post_state → output_CAS → compiler check → rendered_text): conceptually the same data, viewed live instead of after-the-fact.
- **Mode 7 mechanistic attribution** (live activation hooks + per-head attribution): feeds the deeper "what neural components fired" view during rewind.
- **Canonical graph identity** scheme: each piece of structure that appears has stable identity. Identity propagation works correctly because it's the same scheme used elsewhere.
- **CAS color palette v1.0**: structural type colors carry through to 3D rendering automatically.
- **IntentIR layer** (NL front door): user queries can render as parsed-intent nodes alongside model output, not just text labels.

None of these need to be built for SGGS. They exist or are committed to.

---

## Phase 1 — baseline 3D visualization (8-12 weeks)

Goal: interactive 3D viewer for CAS diagrams + Idea Atlas with static-snapshot data (completed turns, historical sessions, finished CAS structures).

Work breakdown:
- Three.js force-directed graph with CAS-aware rendering (color palette, structural types, canonical graph identity): 2-3 weeks
- MediaPipe Hands integration with three core gestures (fist-spin / pinch / two-hand zoom): 1-2 weeks
- Idea Atlas as 3D viewer mode: 1 week
- CAS diagram view (notation + graph + cluster containers): 2-3 weeks
- Polish, accessibility alternatives (keyboard/mouse parity, no webcam): 2-3 weeks
- Tests + browser-perf benchmarks at scale: 1 week

**MVP scope** (rough-edges-acceptable): 4-6 weeks if we accept basic gesture vocab + smaller node count + minimal accessibility.

---

## Phase 2 — live generation witnessing + rewind/slow-motion (8-12 weeks)

Builds on Phase 1.

Work breakdown:
- Inference-server streaming protocol (WebSocket or SSE — push structural commits as the model produces them): 1-2 weeks
- Frontend streaming consumption + state management: 1 week
- Animation timing/sequencing for readable structural assembly (smooth physics-based motion vs discrete steps; probably both modes): 1-2 weeks
- User query as IntentIR node integration (depends on NL front door being live): 1-2 weeks
- Timeline scrubber UI: 1 week
- Playback state interpolation (smooth scrubbing through arbitrary moments): 1-2 weeks
- Bookmark system (optional): 1 week
- Performance optimization for multi-turn live updates + history accumulation: 1-2 weeks

**Streaming granularity**: target head-level (12 updates per turn) not token-level (hundreds per turn). Token-level gets jittery; head-level is readable.

**Branching note**: under current architecture, the model produces one structured prediction (no live alternative consideration). True branching visualization requires either Mode 6 counterfactual exposure (top-k alternatives shown actively during generation) or beam search visualization. Be explicit which kind of "branching" the visualization is showing — alternative consideration vs structural growth — they're different features.

---

## Phase 3 — optional extensions (months later)

- Counterfactual exploration during rewind (Mode 6 alternatives surfaced as ghost nodes when scrubbing)
- Live next-token preview (top-k for the upcoming structural commitment)
- Persistent multi-session storage (Idea Atlas accumulates across sessions)
- Mobile/tablet touch + stylus interaction modes
- VR/AR viewer (Three.js → WebXR is straightforward)

Defer Phase 3 until Phase 1+2 ship and get stakeholder validation.

---

## What SGGS does NOT replace

**SVG static rendering stays.** Two distinct rendering paths coexist, not duplication:

- **SVG**: papers, benchmark figures, documentation, version-controlled reproducible static output. Works everywhere, prints cleanly.
- **Three.js**: interactive exploration, dashboards, debug tooling, audit interfaces, demo surfaces.

The benchmark paper still needs static figures regardless of whether the interactive viewer exists. Both paths serve different purposes.

---

## Risks and considerations to think through at implementation time

### Browser performance at scale
Three.js handles hundreds-to-thousands of nodes well. Tens of thousands needs optimization (instancing, LOD, culling). Idea Atlas at small scale fits comfortably; power users with 10K+ captured ideas need careful engineering. **Establish the performance ceiling before committing the architecture.**

### Accessibility
Gesture-only excludes users without webcam, with motor disabilities, or unfamiliar with the gesture vocabulary. **Keyboard + mouse alternatives required for parity.** Not a deal-breaker but real engineering work to maintain across input modalities.

### Mobile/tablet
Webcam gestures aren't natural on touchscreens. Mobile probably wants touch gestures (already standard). Tablet probably wants stylus. **Desktop webcam-gesture is one input modality among several to support eventually.**

### Latency vs richness tradeoff
Real-time streaming requires either WebSocket or SSE. If latency too high, "real-time" property breaks. If updates too granular, viz gets jittery. **Sweet spot is probably head-level granularity (12 updates per turn).**

### Continuity vs comprehensibility
Smooth animated transitions look good but can be hard to follow when much is happening fast. Discrete visible steps with brief pauses between major commits might be more readable for stakeholders learning to interpret CAS diagrams. **Prototype both modes.**

### User query representation
Show user queries as Idea Atlas nodes alongside model output: clean idea. But raw text node vs parsed CAS structure (IntentIR)? Parsed is much richer (front-door parsing visible live too). Requires IntentIR layer to be working and exposed at that point.

---

## Demo scenario (target end-state)

> Stakeholder speaks: "Help me think through whether to take this job offer." Query parses, structure assembles in ~8 seconds — noetic ^4, domain E, foundation reference, cluster forming. Stakeholder pauses, rewinds to the noetic resolution moment, watches at 0.25x, notices the Mode 7 activation pattern, asks "why ^4 and not ^7?" — rewinds further, watches Mode 6 alternative considerations, sees confidence delta. Stakeholder bookmarks the moment for later review.

This is fundamentally different from any current AI product UX. Two-level interpretability + temporal control + spatial manipulation + privacy-preserving local processing.

---

## Strategic framing

### Strengthens benchmark paper supplementary materials
Static figures are abstract. Supplementary materials with a video where reviewers can rewind to specific structural commitments and watch them happen frame-by-frame is substantially more compelling. Reviewers who interactively explore claims engage differently than reviewers limited to static figures.

### Patent landscape
Phase 2 (live witnessing + rewind/slow-motion structural cognition) is patentable on its own. Combined with Phase 1 spatial gesture surface, produces a multi-component patent portfolio. **Worth raising in deferred IP attorney conversation.**

### Adoption-vs-admiration boundary
Current Idea Atlas is functional but feels like a research demo. Gestural 3D would feel like a product. That's the difference between a tool that gets adopted vs admired-then-forgotten.

---

## When to revisit

**Revisit this document when:**
1. v0 conversational model has shipped (B-3 → B-4 done, working REPL with two-stage inference)
2. At least one paper has landed
3. Stakeholder demos have moved past static slides and started asking for interactive exploration
4. Inference server architecture decisions have been made (the streaming protocol details depend on it)

**Do NOT revisit before all four are true.** The pattern of "good ideas surface during hold patterns and try to fork attention" is real. The discipline is: capture, defer, ship the critical path.

---

## What this document preserves so it doesn't have to be re-researched

If a future session opens this file at implementation time:

- MediaPipe Hands is the gesture-recognition library (Google, mature, in-browser)
- Three.js is the 3D rendering library (de-facto standard, mature ecosystem)
- Telecladius / Bles Software demo is the reference implementation pattern
- Three core gestures: fist-spin (rotation), pinch (node drag), two-hand pinch-spread (zoom)
- Privacy property: webcam runs locally in browser, no data leaves the machine
- Streaming granularity target: head-level (12 updates per turn)
- The visualization composes with existing infrastructure: structured prediction heads, Mode 3 trace, Mode 7 mechanistic attribution, canonical graph identity, color palette v1.0, IntentIR
- SVG static rendering coexists with Three.js interactive — they serve different purposes
- Phase 1 → Phase 2 → Phase 3 sequencing is real, not arbitrary
- Engineering scope is product work, not research

If you find this file and the v0 conversational model has not shipped: **do not implement.** Capture is preserved; that's enough.
