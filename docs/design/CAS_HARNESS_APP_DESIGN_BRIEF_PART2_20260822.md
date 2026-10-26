# CAS Harness — Design Brief, Part 2
Landing page · Dashboard · The Explainer · Capability surfaces
Read Part 1 first. All principles there still bind — especially: **the floor is the hero**, **honest states are first-class**, **numbers exact**.

---

## 9. The Explainer — the floating AI button

A persistent, movable assistant (Claude via API) that explains what a result means, in the user's own words, wherever they are in the app.

This is the difference between an instrument only a researcher can read and a product an executive can act on. It is also the single easiest place to destroy the product's credibility, so its constraints matter more than its looks.

### 9.1 Form

- **Resting state:** a `48px` circle. No label, no glow, no pulse, no "AI ✨". A single quiet mark. It should read as a tool, not a mascot.
- **Position:** free. The user drags it anywhere; it magnetises to the nearest edge and stays there. **Position persists per user across sessions and across screens** — if they park it bottom-left, it is bottom-left forever until moved.
- **Out of the way:** dragging it to a screen corner collapses it to a `12px` edge tab — present, nearly invisible, one tap to restore. It must be possible to make this thing effectively disappear without disabling it.
- **Opened:** expands into a panel anchored to its docked edge — a side sheet, not a modal. **The result stays visible while the panel is open.** The user must be able to look at the number and the explanation simultaneously. Never cover the data being discussed.
- **Never:** bounces, wiggles, emits notification dots, or speaks first. It waits.

### 9.2 Behaviour

- **Context-aware.** It always knows which screen, which model, and which result the user is looking at. Opening it on a Relation Profile pre-loads that run — no "what would you like to know?" cold start.
- **Opens with three suggested questions**, generated from the current screen, not a generic list:
  - *Why does this beat the baseline?*
  - *What could still be wrong with this?*
  - *What does this mean for my deployment?*

  The second one is mandatory on every screen. A product that will argue against its own result is a product people believe.
- **Continuity.** Walking from the Profile to a Relation detail carries the thread. It does not reset.
- **Selection-aware.** Highlight any number anywhere in the app → a small "explain" affordance appears near the selection, routed to the same panel.

### 9.3 Grounding rules — non-negotiable

The Explainer is **fed the actual result JSON, the claim state, and the method description for the current view.** It answers from that payload.

- It **may** restate, translate to plain language, compare to other runs in the workspace, and explain method.
- It **may not** invent numbers, estimate values not present, or speculate about models not tested.
- Any figure it states must appear in the payload. If asked something the data cannot answer, the correct response is *"this run doesn't measure that"* — and the UI should make that a normal, well-designed response, not a failure.
- **It must carry the claim state.** If a result is `BOUNDED`, the explanation says so unprompted. If `WITHDRAWN`, it leads with that.
- **Every explanation is stamped** with the model that produced it and a link to the underlying JSON. The explanation is commentary; the data is the record. Never blur them.

### 9.4 Failure states, designed

- No API key → the panel explains what it would do and where to add a key. It does not nag elsewhere.
- API down → the button greys out. **The app is fully usable without it.** The Explainer is never on the critical path to reading a result.
- Streaming → text streams in; the three suggestions stay pinned.

---

## 10. Landing page

One scroll. Five sections. No carousel, no logo wall, no testimonial slider, no chat bubble.

1. **The claim.** One sentence, large, alone on a near-empty ground:
   > See what a model actually represents — measured against a baseline that cannot be gamed.

   One button: *Connect a model*. Nothing else above the fold.

2. **The proof, not a description of the proof.** A live, static Floor component with real numbers from a real run. The two matched sentences underneath, differing words highlighted, everything else identical. **This is the whole pitch and it is visual, not prose.** A visitor should understand the method here without a paragraph.

3. **What it measures.** Six relation names, one line each. No icons. No cards with drop shadows.

4. **The finding worth the visit.** Speaker binding — models bind cause and time strongly, and who-is-speaking weakly, and instruction tuning does not close the gap. Two Floor components side by side. One sentence.

5. **What it does not claim.** An actual section on the landing page listing the limits. Nobody does this. It will be the most persuasive block on the page, and it costs nothing because the limits are already true.

**Footer:** method, reproduction, pricing. No newsletter capture.

---

## 11. Dashboard

The home surface after login. **Not a metrics wall.**

- **Row 1 — Models.** The shelf from Part 1 §5.2. Nothing added.
- **Row 2 — Recent runs.** Model, relation set, verdict, timestamp. One line each, monospace numbers.
- **Row 3 — Attention.** Only appears when something needs a person: a run refused by the pre-flight gate, a result auto-bounded by a later run, a drift alarm. **Empty by default and that is the good state.** Do not manufacture activity to fill it.

No sparkline strip. No "total probes run" vanity counters. No activity heat map.

---

## 12. Capability surfaces

Each capability gets a surface. **Each surface renders its true claim state** — the statuses below are current and must be shown in the UI, not softened. Designing an unproven capability as though it were proven is the one failure this product cannot survive.

### 12.1 Cognitive structure detection — `REAL`
The pinned-pair engine. This is the flagship and Part 1 already specifies it (Relation Profile, Relation detail). Everything else on this list is secondary to it.

### 12.2 Prompt-injection detection — split surface, and be blunt
Two different things share this name and the UI must not merge them.

- **Speaker-binding measurement — `REAL`.** The representational precondition. Part 1 §6.
- **Text-surface injection filter (C11) — `NOT LICENSED for production`.** It is a deterministic text filter. It **provably cannot** separate a legitimate system instruction from an injected user instruction carrying the same words — those inputs are the same word multiset and the same n-gram bag.

**Design requirement:** show the two side by side with a demonstration — the same pair of sentences, the filter returning identical output for both, the binding measurement separating them. Turning a known weakness into an explicit comparison is stronger than hiding it.

### 12.3 η→ε bridge (probe → prefix → likelihood) — `REAL`
Read a state from activations, express it as an English prefix, measure the shift in what the model says next. Validated across **6 model points, 3 families, 160M → 20B**; the largest effect **`+1.412`** at 20B on the 40-Element axis.

**The control is the story:** a raw-CAS-symbol prefix is null at every scale (**`−0.020` to `+0.003`**). Meaning is doing the work, not the notation. Design it as a three-panel flow — *read → phrase → measure* — with the null control shown as a flat companion bar. Never show the effect without the null beside it.

### 12.4 Lacunarity — `VALIDATED` as diagnostic · `NULL` as injection detector
A gappiness measure over a state profile. Empirical range **`0.793` → `0.0016`**. Used as a preflight: a lumpy axis (Noetic-alone **`0.793`**) predicts steering will fail; a clean axis (Foundation **`0.021`**, 38× cleaner) predicts it will work.

**It failed as an injection detector** and the UI must say so: covert-vs-benign `p = 0.37`, overt in the *opposite* direction (`p = 1.3e-5`), AUC `0.33`.

Design as a **go/no-go gauge before steering**, never as a threat indicator.

### 12.5 Steering — `VALIDATED` (drive-local) · `FALSIFIED` (global)
Drive-local eraser steering works across architectures. **Global steering is falsified** — that is a recorded negative and must remain visible in the UI, not quietly dropped.

Surface: pick a direction, set strength, see the output shift **against a norm-matched random direction** — always. The random control is not optional; a big effect that a random direction also produces is worth nothing. Show both bars, always, side by side.

### 12.6 probe → ablate → steer loop
The end-to-end arc: find a direction, remove it, watch behaviour move, put it back.

**Honest limit for the UI:** the attested engine has **no runtime projection/ablation mode** — it adds, it does not project out. So the app measures **sufficiency** (inject → it moves), not **necessity** (remove → it stops). Label the loop stages accordingly and grey the stage that is not implemented rather than faking it. **Restoration is the receipt** — when ablation does land, re-adding the direction and recovering behaviour is the proof step, and it should be the visual climax of this surface.

### 12.7 Multi-layer trace + blind-spot detection — `PARTIAL`, controls missing
Classification across layers reaches **`95.4%`** on a 10-way task at Pythia-160M. **Chance is `10.0%`, and that is the only reference point this result has** — no text baseline, no shuffled-label null, no matched control.

**Design requirement:** this surface must render the missing controls as visible empty slots, not omit them. A user seeing `95.4%` must also see that three control rows are unfilled. Beating chance is not evidence of anything CAS-specific — a topic classifier beats 10% too.

### 12.8 Fractal classifier — `n = 1`, not a licensed capability
Classifies an axis as `Stabilizing` / `Oscillatory` / `Amplifying`, which predicts whether steering will succeed. Confirmed instance: Pythia-160M Noetic axis classed `Oscillatory` → Noetic steering subsequently failed, as predicted.

**One confirmed prediction is not a prediction record.** Show it as a labelled hypothesis with its evidence count visible (`n = 1`). If the count rises, the UI reflects it. Do not present it as a working oracle.

### 12.9 Layer indexing — `RESOLVED`, infrastructure
`L0` is the **output of block 0**, not the embeddings — which is why a layer-0 result is real signal and not a lookup-table artifact. Not a feature screen. It belongs as a one-line clarification wherever layer indices appear, because the first thing a sharp reviewer will ask about an L0 result is exactly this.

---

## 13. Additional deliverables

11. Landing page, full scroll
12. Dashboard, populated and empty
13. Explainer: resting, docked-to-edge, collapsed tab, open panel, no-key, offline, streaming
14. Explainer drag-and-dock interaction spec
15. Each capability surface in §12, **rendering its true claim state**
16. The injection split-surface comparison (§12.2)
17. A capability whose status is `NULL` or `FALSIFIED`, designed as carefully as a win — this is the house style test

**Test of success for Part 2:** a visitor who reads only the landing page understands the method; a customer who never opens the Explainer can still use the product; and a reviewer who opens the weakest capability surface finds its weakness stated before they can discover it themselves.
