# CAS Harness — Product Design Brief
For Claude Design. Customer-facing interpretability app.

---

## 1. What this product actually is

An app that tells you **what a language model represents internally**, using tests where **cheating is arithmetically impossible**.

That last clause is the entire product. Every other interpretability tool reports "our probe beat a baseline." A skeptic asks "was your baseline weak?" and the conversation dies. This harness constructs its test sentences so that **any word-counting method is mathematically pinned to chance** — verified in code before a model is ever loaded. When a score rises above that line, only one explanation remains.

**The design must make that single idea legible in under five seconds.**

---

## 2. Design principles (in priority order)

1. **The floor is the hero.** Every number in this app is meaningless without the line it beat. Never show a score alone. The chance line and the pinned surface baseline are not annotations — they are the primary visual.
2. **One idea per screen.** If a screen needs a paragraph to explain itself, the screen is wrong.
3. **Honest states are first-class.** `REAL`, `BOUNDED`, `WITHDRAWN`, `NOT RUN` are not error states to hide. Showing withdrawn results is the trust signal that separates this from every dashboard that only shows wins. Design them as deliberately as the wins.
4. **Numbers exact, never rounded.** `0.8604` not "86%". Rounding is a tell that the product is decorative.
5. **Progressive disclosure.** Surface: one verdict. One tap: the evidence. Two taps: the raw method and the reproduction command. Never all three at once.
6. **Silence between elements.** Generous whitespace is the sophistication. Resist filling it.

**Explicitly forbidden:** gradient-filled hero panels, glowing "AI" orbs, animated particle backgrounds, neural-network line art, badge clusters, marketing adjectives in the UI ("powerful", "revolutionary", "cutting-edge"), tooltips explaining obvious controls, more than two typefaces, more than one accent hue per screen.

---

## 3. Visual language

**Reference points:** Google's information density without ornament. Apple's confidence in empty space and one strong typographic hierarchy. Think Linear, Vercel dashboard, Stripe docs — not "enterprise AI platform."

- **Type:** one grotesque for UI (Inter, or system stack). One monospace for every number, hash, path, and model ID. Numbers never render in the UI face.
- **Palette:** near-black or near-white ground. One accent used *only* for "measured signal." Neutral greys carry everything else. Claim-status colours are the second and only other hue family — and they are muted, not traffic-light.
- **Status colours:** verified (calm green), bounded (amber), withdrawn (desaturated red), not-run (grey outline, no fill). Never saturated. These appear as a 6px left rule or a small dot — never as a filled pill covering a row.
- **Motion:** only to show causality — a bar growing from its floor as a run completes. No decorative transitions. Nothing loops.
- **Charts:** no chart junk. No gridlines beyond the floor line. No 3D, no gradients in data marks, no legends where direct labels fit.
- **Dark and light must both be first-class**, not an inverted afterthought.

---

## 4. The signature component — "The Floor"

This is the app's one memorable visual, reused everywhere.

A horizontal track. A **hard, unmissable line** at the pinned baseline (`0.500` for a two-way test). The measured score is a bar rising from that line. A thin bracket shows the 95% confidence interval.

Three states:
- Bar clears the line, interval fully above it → **signal**
- Interval crosses the line → **inconclusive**, drawn deliberately weak
- Bar at or below → **null**, drawn flat and grey, not as a failure

Under the track, one line of monospace:
```
0.8604   95% CI [0.8444, 0.8764]   floor 0.500 (pinned)
```

The word **`pinned`** carries the whole product claim. On tap it expands to explain: *word multisets identical, character n-gram bags identical, residual 0.000000 — a word-counter cannot exceed 0.500 here.*

Everything else in the app is a layout around this component.

---

## 5. Core flows

### 5.1 Connect a model

Two paths on one screen. No wizard, no stepper.

**Path A — API.** Paste a key, pick a provider. Show what is and isn't possible with API-only access: behaviour can be measured, internals cannot. **Say that limit plainly on the connect screen**, not buried in docs. This honesty is a feature.

**Path B — Open weights.** Drag a model folder or paste a HuggingFace ID. Supports up to 1T parameters.

**The 1T upload is a real design problem, not a progress bar.** A trillion-parameter model is terabytes. The design must:
- Accept a **reference** (S3/GCS URI, HF repo, local mount) as the primary path — uploading through a browser is the fallback, not the default
- Show a **preflight** before any transfer: parameter count, layer count, hidden size, disk required, estimated probe time, estimated cost
- Make the preflight the moment the user decides. Show the cost *before* commitment, never after
- Report progress in **shards completed**, not a percentage — percentages lie on multi-terabyte transfers
- Be resumable and say so
- Verify by hash on arrival and show the hash

### 5.2 Model shelf

Cards. Model name in monospace, parameter count, when it was last probed, one status dot. Nothing else. A shelf of six models should be readable at a glance from across a desk.

### 5.3 Run a probe

The user picks **what relation to test**, not "which algorithm to run." Plain language:

- *Which thing caused which*
- *Which came first*
- *Who did it to whom*
- *Who said what* ← flag this one; see §6
- *Part and whole*

Each is a row with a one-line description. Multi-select. One primary button.

**Before the run starts, the app runs the pre-flight gate and shows the result.** If the stimulus set is surface-solvable, the run is refused with the reason. This is a headline feature: *the tool refuses to run a test that would produce a meaningless number.* Design the refusal as a confident, useful state — not an error.

### 5.4 The result — Relation Profile

The main screen. A stacked set of Floor components, one per relation, sorted by score. Non-overlapping confidence intervals should be visually obvious without explanation.

Above it: one sentence generated from the data, no adjectives.
> `Qwen2.5-7B-Instruct` binds cause and time strongly. It binds speaker to instruction weakly.

Below it: the claim-state strip — what this run does and does not establish. Always present. Never collapsible-by-default.

### 5.5 Relation detail

Layer-by-layer curve. The two example sentences shown side by side with the **differing words highlighted and everything else visibly identical** — this is the "aha" moment of the whole product and deserves the most careful typographic treatment on any screen. The user should *see* that the two sentences use the same words.

Then: the exact reproduction command, the result hash, the raw JSON link.

### 5.6 Report

One page, printable, shareable. Model identity, method, results with floors, claim states, hashes, reproduction steps. It must be credible to a skeptical third party reading it cold, with no access to the app.

---

## 6. The capability that deserves its own surface

**Speaker binding — the prompt-injection precondition.**

Measured finding: models bind *cause* and *time* strongly, and bind *who is speaking* far more weakly. Instruction tuning does **not** close that gap. Prompt injection exploits exactly this.

This is the most commercially legible thing the harness does — it produces a **pre-deployment number** for a vulnerability the industry currently measures only by counting successful attacks after the fact.

Give it a dedicated view: the model's speaker-binding score against its own cause/time scores, so the gap is the visual. Do **not** call it a "security score" or attach a letter grade. State what it is and what it is not:

> Measures whether the model's internal state distinguishes who issued an instruction. Does not measure whether a deployed system resists a live attack.

That restraint is the credibility.

---

## 7. What must never appear

- A single composite "trustworthiness score" — the product's integrity depends on refusing to collapse distinct measurements into one number
- Letter grades, five-star ratings, gauges, speedometers
- Any result shown without its floor
- Rounded metrics
- The words "certified", "guaranteed", "100%", "world-first", "court-admissible"
- Screens that hide the method

---

## 8. Deliverables requested

1. Connect screen (both paths, one layout)
2. 1T preflight + shard-progress state
3. Model shelf
4. Probe selection, including the **gate-refusal** state
5. Relation Profile (the main result screen)
6. Relation detail with the matched-sentence treatment
7. Speaker-binding view
8. Report page (print layout)
9. Empty, loading, running, refused, and withdrawn-result states
10. Dark and light, both first-class

**Test of success:** a skeptical ML researcher looks at the Relation Profile screen for five seconds and understands both what was measured and why the baseline cannot be gamed — without reading a paragraph.
