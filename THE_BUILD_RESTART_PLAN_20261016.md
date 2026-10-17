# THE BUILD — restart plan, 2026-10-16

**Read this, then `COUNCIL_STANDING_KNOWLEDGE.md`, then `OWNER_ORDERS_AND_DECISIONS_20261016.md`.
Do not start coding before all three.**

This is the plan for joining the pieces into one running loop. It is written from canon and from
measured results, not from memory.

---

## 0. The one sentence

> **"CJT proposes under Bias. RPM repairs prerequisites."**

Everything below is that sentence made executable.

---

## 1. The architecture, with each job separated

| part | what it IS | what it must NEVER do |
|---|---|---|
| **RPA = Recursive Possibility Atlas** | the map. Nodes hold the goal, the unfinished answer, the facts carried, the open branches. Facts, guesses, possibilities and contexts stay **distinct**. | be rebuilt. **Reuse `rpa_model.py` / `canonical.py`** from branch `codex/helm-rpa-recorded-run-20260922`, commit `eb9985566bd11a89f485d627186ef0efa7177f02`. The vision forbids a parallel build. |
| **Bias** | the CJT's **working memory**. Attention writes relevant information into it; the next CJT reads it. A Bias snapshot is the `^5`. | be written by more than one coordinator. |
| **ASOM** | the **gauge** on the Bias. Four labels. **BUILT** — `continuity_build_v2\asom.py`. | **gate anything.** It is a display. |
| **RPM** | the **gate**. Decides whether the next step may proceed, and repairs what is missing. | be replaced by any other check. |
| **CJT** | the **crossing** — the act of a thought moving from one Atlas node to another along an edge. Not a node. **BUILT** — `continuity_build_v2\crossings.py`. | be confused with a node or an edge. `is_cjt()` enforces this. |

---

## 2. The recursion engine — Definition 27.2, the three resolution functors

When a node in the **D/W/P** chain blocks, the system runs a **Formal Recursive Evaluation**. **Which
node blocked decides HOW it recurses.** Three different mechanisms, not one:

| blocked | spawns | mechanism | the Noetics |
|---|---|---|---|
| **Power** | **ONE** child chain | rational, structured — solves a resource gap | `Φ_P: P_blocked → (CO-8 ∘ CO-9) ⇒ RPM(P)` |
| **Wisdom** | **PARALLEL** children — a coproduct | **the only case where parallelism is allowed** | `Φ_W: W_blocked → (CO-5 ∨ CO-6)` |
| **Desire** | **NO child** — it loops | iterative, cycles the current state | `Φ_D: D_blocked → (CO-1 ∘ CO-4 ∘ CO-7)^N` |

**The three functors are the three Noetic pairs.** The recursion mechanism IS the Noetic algebra. Do not
implement it generically — which pair fires is determined by which node blocked.

### The depth rule

- **Maximum depth is 5.** The book calls it *"a stability horizon, not an arbitrary cap."* Every level
  adds load Γ.
- **A depth-5 chain meeting a new block is Structural Deadlock.** The fix is to **flatten into
  horizontal decomposition** — go sideways, never raise the number.
- **The Desire loop does NOT count toward depth.** It never descends.
- **The number is not agreed across sources** — 5 (book, Rust engine), 4 (rc0, CNCM), 3 (Gate A,
  governance rails, Atlas expansion default), `log₂(resources)+3` (Builder's Manual), none (older
  monad). **The council's reading: 5 is the horizon; the lower numbers are rails that sit INSIDE it
  and may be stricter; nothing may exceed 5.** This is a reading, awaiting the owner's word.
- **Edition warning:** `Thinking_in_Cognitive_Architecture_FINAL.docx` contains **none** of Def 27.2,
  Theorem 27.3, depth 5 or Structural Deadlock. Only the **v1 DOCX, the KDP PDF and the EPUBs** have
  them.

### The return rule

**Theorem 27.3:** `ε⁽ⁿ⁾ ∘ η⁽ⁿ⁾ = id⁽ⁿ⁾` must hold **independently at every depth**. A **dirty child
invalidates the whole parent chain** — *"if a child chain uses a 'dirty' resolution (e.g. a Power
bypass), the retraction morphism fails and the block propagates back up."*

**The way back is an address, not a memory.** Bind each open thread to an exact Atlas address and an
explicit return chain. **No root shortcut.** A returned thread must carry a **strictly newer** Bias; a
stale or duplicate finish may not wake an unrelated caller.

---

## 3. Continuity of thought — what is BUILT

Folder `continuity_build_v2\`, **46 test cases passing**:

- `stations.py` — the path S0 → S6, nesting inside S5, thresholds **undecided**
- `seams.py` — a seam needs **BOTH** the head to change **AND** the step ≥ threshold; never
  interpolate across a seam
- `continuity.py` — anchor, displacement, atlas path, counts
- `provenance.py` — **FOLLOWED** (pointer existed before the tick) / **CREATED** (written this tick,
  later admitted) / **ATTEMPTED** (written, refused or open). Shuffled control must produce **0**
  CREATED.
- `disengage.py` — the owner's ladder
- `atlas.py` — a **stand-in** atlas: four kinds, directed edges, sub-atlases, kind-pollution report
- `crossings.py` — the CJT as a crossing
- `asom.py` — the four-label gauge

## 4. The disengage ladder — the owner's words

**not declared → "I'm confused, I have no idea" → ask for clarity, naming the exact gap → disengage
WITH A REASON.**

Never guess at any step. The ask names the actual missing thing. Disengage is terminal for that turn.
Every step goes in the receipt, so a later reader sees it asked before it gave up.

---

## 5. The language layer — the owner most wants to see this talk

**CCE = Controlled Core English.** `parse(sentence) → CAS`, `render(CAS) → sentence`. **Both are
deterministic programs, not models. 0 learned parameters.** The only acceptance test is the round trip:
**ε∘η = id**, and **η∘ε ≠ id** — wording may change, content may not.

**Measured:** recipes **576/576**; English **233 of 439** against a **118** baseline.

**Q13 is decided: admit a `p/q` number form.** `CCE compares exact Decimals; RB uses exact Fractions`,
so a non-terminating coefficient had no form and the skin read `SKIN_FORM_BROKEN` in the wave-1 run —
while still recording **0 invented facts**. The grammar is still DESIGN ONLY, so `p/q` goes into v0.1
before it freezes.

---

## 6. THE BUILD ORDER

**Do these in order. Each one ends with a test that can fail.**

1. **Reuse the real Atlas.** Fetch `codex/helm-rpa-recorded-run-20260922`, read `rpa_model.py` and
   `canonical.py`, and make S0 bind to **it**. The stand-in becomes a thin adapter with a test proving
   it talks to the real model. **512 node / 8 MiB bounds are already measured.**
2. **The recursion engine.** Power → one child. Wisdom → parallel children. Desire → a loop that never
   touches the depth counter. Depth stop at 5 with a sideways flatten at the horizon. Prove with a
   test that a depth-6 descent cannot happen and that a dirty child invalidates its parents.
3. **Wire the return address.** Every open thread bound to an exact Atlas address; no root shortcut; a
   stale return refused.
4. **Wire ASOM into the loop as a readout only.** It reports; it never gates. Test that removing it
   changes no decision.
5. **Join continuity to the Atlas** so a thought's anchor is an Atlas position and its path is a list
   of crossings.
6. **Then, and only then, the language.** `p/q` form first, then TAP a station, then INJECT speech, then
   the round trip. **This is the piece the owner is most excited about.**

---

## 7. The rules that keep being broken

1. **Open the artefact before asserting anything** — including about your own record. Four false
   self-accusations in one session came from not doing this.
2. **Reuse, do not rebuild.** The vision says so: *"Do not create a parallel memory framework, RPA
   build or roadmap because a schema needs a compatible extension."* The council built a parallel
   atlas and had to be corrected.
3. **A name is not a reading.** `TEST_PLAN_HELM_R1.md` and `INTEGRATION_MANIFEST.md` were once
   discarded as "mere mentions" without being opened. They were the plan.
4. **A test that cannot fail proves nothing.** Prove it by breaking the rule in a copy and watching the
   suite catch it.
5. **Never invent a number, a threshold or an acronym.** Mark it undecided and say so.
6. **Never delete a negative.**
7. **A failed gate is a FAILURE**, never "pass with caveats".

---

## 8. What is already settled — do not re-open

- **Wave 1 ran and won.** `PASS`, `R1_BEATS_GB3`. Recipe **32**, transformer **9**, widened **8.5**,
  bar **4**. Reading sha256 `9b1dfdd88568012cabbcfa6d00e97c15dee07d445dfa5daff8be185975f4cf3a`.
  **Do not launch it again.**
- **The continuity machinery is built** — 46 cases pass.
- **The ASOM gauge is built** — 10 cases pass, four labels, gates nothing.
- **The memory test package is built** — 768 rows, nothing scored.
- **The 13 memory-policy open points are decided**, awaiting the council's reading.
