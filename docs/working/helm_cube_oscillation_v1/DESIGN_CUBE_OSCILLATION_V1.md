# HELM cube oscillation v1 — taught facts become cubes at their Atlas node only after the CTT and the brain side agree; whole memories fade step by step into CAS at that same node (design, 2026-10-21 PDT)

Status: **DESIGN ONLY. NOTHING BUILT, NOTHING TRAINED, NOTHING RUN, NOTHING LICENSED. 0 USD.**
Every part named here keeps the claim status it has on the spec sheet today. Everything new is `PROPOSED`. Claude is
not the research governor: this packet proposes; the owner decides; a status word can come only from a frozen program.

## 0. The owner's words this design answers (verbatim, 2026-10-21, typed into the TEACH-1 builder session)

1. "DO YOU THINK THE CUBE NODE SYSTEM CAN ASSIST IN AMELIORATING HELM'S LEARNING?"
2. "YEAH BRO BECAUSE THE CUBE SYSTEM RUNS DIRECTLY INTO RPA ATLAS SYSTEM RIGHT??? USE THE OSCILLATION BETWEEN CTT AND RECIPE BRAIN TO DETERMINE WHAT TO KEEP REGARDING MAYBE THE EYE CAN CONTROL THE ROUNDS OF OSCILLATION" — quoting the builder's own warning: "If it reads a sentence wrong, it stores a wrong fact. A stored wrong fact is worse than a quoted sentence, because a quote at least shows the person's real words. That reading step is the "ears" in the talk design (§7.110), and it has no passing result yet."
3. "“design the cube oscillation follow-up” AND REMEMBER THAT MEMORY SHOULD BE USED AT THIS RPA ENDPOINT WHERE TO SAVE SPACE LITERAL PLAIN ENGLISH WHOLE MEMORIES PERIODICALLY INCREMENTALLY FADE INTO CAS EXPRESSIONS AND ALL ELSE THAT COMES ALONG WITH WHAT WE ALREADY ESTABLISHED IN MEMORY YOU GET ME"

Read as five requirements (the owner may correct any one with a word):

| # | Requirement | Where in this design |
|---|---|---|
| O1 | taught facts become **cubes**, filed in the **Atlas** (the RPA) | §3 |
| O2 | a fact is kept only when the **CTT and the brain side agree** after rounds of back-and-forth ("oscillation") | §2 |
| O3 | the **Eye** watches, and later may control, the rounds | §2.4 |
| O4 | memory lives **at the Atlas endpoint** (the node where the fact landed) | §3, §4 |
| O5 | **to save space**, whole plain-English memories **fade periodically and incrementally** into CAS expressions, keeping everything already established (capsules, clues, breadcrumb, receipt, fetch-first refresh, fit check, strengthening, the honesty rule) | §4 |

## 1. What TEACH-1 taught us (spec §7.121; facts, not claims)

- Recall was keyword matching over whole sentences. A CAS capsule and a plain-text note with the same clues tied
  (R2 = 0), because both hold only words.
- The 7 answers that failed U1 were HELM quoting a whole correction ("eight; I said seventeen before") instead of
  saying the current value.
- The taught facts never became cubes: the chat files a plain-conversation line with no cube, so every capsule bound
  none, and the fit check's contradiction test and the cube half of strengthening never ran.
- Every honesty gate held (HG-H8 4,029 labels right; 0 invented). Those gates are kept word for word.

## 2. The oscillation: two different readers must agree before a fact is kept (O2, O3)

### 2.1 The two sides

| Side | What it is today | Its job here |
|---|---|---|
| **CTT** (the ears; §7.82, 9,585,566 parameters, three copies) | `ENGINEERED-NOT-VALIDATED`; §7.90 `EARS_NO_GAIN` / `EARS_HARMED`; §7.95 `INCONCLUSIVE` with Part K `EARS_EARNED_KEEP` reported only; trained on kitchen English only | **proposes** a structured reading of a line: thing, slot, value, and whether it replaces an earlier value; three copies must agree (the ACCEPT-2 rule of §7.95) |
| **Brain side** (the recipe brain's machinery: the hand-written reader `helm_english_in` / wide reader, exact `Fraction` values, the cube store's rules, the compiler) | the wide brain is `VALIDATED` for its own sentences (§7.89, §7.96); its reader is hand-written | **checks** the proposal (the thing and slot fit the world's shape, a replaced value exists, the cube would compile) and **says it back** in plain English through the voice |

The brain side is called the "recipe brain" in the owner's words because its exact-value writer, its supersession rule
and its consistency checks are the recipe brain's. The facts in this test are not recipes; the brain's coefficients
are never touched (HG-COEF kept).

### 2.2 One round

1. **Propose.** The CTT's three copies read the person's line. If they do not all give the same reading, the round
   ends with "no agreement".
2. **Check.** The brain side checks the reading against what it already holds (the world's things, the earlier
   value, the cube rules). A failed check ends the round with "no agreement".
3. **Say back.** The brain side writes the reading back in plain English ("Oxley line, September, 8 buses; this
   replaces 17").
4. **Re-read.** The CTT reads the say-back line. If it gives the same reading as step 1, the round **agrees**.

### 2.3 The keep rule (frozen proposal)

- **Keep as a cube** only after **2 agreeing rounds** within **at most 3 rounds** (the second round re-reads the
  person's words with the say-back as context).
- **No agreement within 3 rounds → no cube.** The line stays a whole verbatim memory (today's behaviour), and when it
  is next needed HELM asks ("Did you mean eight for September?"). The honest fallback is TEACH-1's quote-and-ask.
- **The person's own words always stay** beside the cube (in working memory or the cold copy, by fading stage). A cube
  never replaces the words; it adds a checked reading next to them.
- A **correction** becomes a **new revision** of the same cube (the store refuses a revision that does not increase:
  `store.py` `write_cube`). The old value stays in the history, marked replaced.

### 2.4 The Eye and the rounds (O3)

- The Eye's acting is `NOT LICENSED` (§7.38, §7.40; EYE-ACT-1 §7.122 sealed, not scored). So in the first exam the
  **round cap is a fixed number (3)**, and the Eye runs **REPORT-ONLY** beside it: it logs, per line, whether it would
  have stopped earlier, gone on, or asked. Its log is compared with what the cap did. Hard gate: 0 Eye writes.
- A later test (its own owner word, its own freeze) may let the Eye **control** the rounds in `HOLD` mode, the mode
  EYE-ACT-1 built: the Eye may stop the rounds early and make HELM ask, never add a round past the cap, never write a
  cube. That is OPEN_QUESTIONS Q3.

### 2.5 What can still go wrong, and how the exam catches it

- **Both readers wrong the same way.** The exam plants **trap lines** (OPEN_QUESTIONS Q6): sentences built so that a
  careless reading gives a plausible wrong value (two numbers in one line; a month named for a different fact; a
  "not" in an odd place). Hard gate **HG-WRONG-CUBE**: 0 cubes whose current value differs from the key.
- **The CTT has never seen these subjects.** It was trained on kitchen English. Without new training it would almost
  never propose a reading, so the oscillation would never agree and the arm would equal TEACH-1. Training on SDG
  sentences of the two subject templates is therefore part of the build (§6, owner line `CUBE TRAIN at 3 USD`).

## 3. Cubes at the Atlas endpoint (O1, O4)

- **The endpoint.** Each thing the person talks about (a yard, a bus line) gets one Atlas `CONTEXT` node: the place
  where everything about it lands. A kept fact becomes one cube (`kind` instance, faces: the slot, the value, the
  unit) and one Atlas node under that thing's node: kind `POSSIBILITY` when first kept, a new `FACT` node beside it
  once the person confirms it (the Atlas never changes a node's kind: `atlas.py`).
- **Binding.** The capsule of the line (§4) points at that cube by id (the binding TEACH-1 never exercised). The
  cube's provenance is `USER_SAID`; after a confirmed refresh it becomes `CHECKED` (`cube.py` sources).
- **Answering.** A question first looks up the thing's node (anchor first, then the searchlight R ∈ {1, 2, 4, 8},
  cap 15, as v1), then the slot. A cube answers with the **current value** in plain words, labelled `EXACT` only while
  the person's own digest-checked words for that fact are fetchable; else `RECONSTRUCTED`, said as such. No cube →
  TEACH-1's quote path.
- **Contradiction becomes checkable.** The fit check's F3 can now compare a rebuilt memory with the cube's current
  revision, which a plain-text note cannot do. This is the place the honest forecast says the CAS form might earn its
  keep (§7.115 pre-code §11).

## 4. Fading at the endpoint, step by step, to save space (O5)

TEACH-1 compacted in one step when the 12-turn budget was crossed. The owner asks for **periodic, incremental**
fading. The ladder (each step an append, each with a receipt; M1's mass rule, exact fractions, `FADING_RULES.md`):

| Stage | What the Atlas node holds | Space (counted in UTF-8 bytes) | Moves down when |
|---|---|---|---|
| **S0 WHOLE** | the person's whole line, verbatim; and its cube if kept | the line's bytes | its mass falls below θ₁, or working memory is over its byte budget |
| **S1 CAPSULE** | the CAS capsule (CCE sentence that round-trips, `^n^C` notation that compiles, ≤ 8 verbatim clues, number words never clues), the cube pointer, the breadcrumb (cold copy + sha256), the receipt; the whole line now in the cold copy | the capsule's bytes | mass below θ₂ |
| **S2 CAS** | only the CAS notation, the clue set, the cube pointer and the breadcrumb; the capsule's sentence goes to the cold copy beside the line | a few dozen bytes | never further: the cube and the breadcrumb are never dropped |

- **Mass** = importance × everyday use × recency, M1's formula with exact fractions: `m = s · f(n) · r(age)`,
  `f(n) = 1 + ⌊log2(1 + n)⌋`, `r = (19/20)^age`. One tick = one turn in the exam (M1 used one day; replay stays exact).
- **Periodic:** a fading sweep every **K = 4** turns (frozen proposal) moves every item whose mass crossed a line down
  one stage; never two stages at once.
- **Never faded:** cubes, recipe coefficients, the person's corrections while their cube is unconfirmed, numbers,
  names, owner words (the v1 never-compact list), and the current thread's last 2 turns.
- **Back up the ladder:** fetch-first recall brings S1 / S2 back to S0 when the cold copy checks (a verified use
  raises the mass); a confirmed refresh strengthens (mass up, clues grow from the person's words, cube to `CHECKED`,
  Atlas `FACT` node); content never changes.
- **The honesty rule is unchanged:** `EXACT` only on the person's digest-checked words; a rebuild from S1 / S2 is
  `RECONSTRUCTED`; nothing fetchable and no cube is `UNKNOWN`.
- **Space is measured, not assumed:** the exam counts the bytes held in working memory at every quiz (a new reported
  row and mark SPACE, prereg §8).

## 5. The cheap rivals the design must beat (the house rule: a mechanism-free baseline)

| Rival | What it is | Why |
|---|---|---|
| QUOTE_ONLY | TEACH-1's COMPACT_ON exactly (one-step compaction, no cubes) | today's best memory |
| TABLE | a plain lookup table `(thing, slot) → value`, written when the hand-written reader alone reads a line; no cube, no Atlas, no CAS, no fading ladder (FIFO on the text) | if a dictionary does as well, cubes are not what helps |
| ONE_READER | cubes at the Atlas, but written by the hand-written reader alone, no CTT, no rounds | does the oscillation matter? |
| CTT_ONLY | cubes written by the CTT's unanimous vote alone, no brain-side check or say-back | does the brain side matter? |
| ONE_STEP_FADE | the cube arm with TEACH-1's one-step compaction instead of the ladder | does incremental fading matter? |

## 6. Build, train, run: order and price

| Step | What | Where | Cost | Needs |
|---|---|---|---|---|
| 0 | this packet | laptop | **0 USD** | — |
| 1 | the owner's rulings on OPEN_QUESTIONS (incl. how a quoted correction is scored, Q1) | — | 0 | the owner |
| 2 | build v2 behind a new switch `HELM_CUBE_OSC` (default OFF): the cube writer at the Atlas node, the round loop, the fading ladder, the TABLE / ONE_READER / CTT_ONLY variants; tests FIX FIRST | laptop | 0 USD | Q1–Q5 |
| 3 | SDG training rows for the CTT: the two subject templates' statements, corrections, unknowns and traps → structured readings, plus an `LLM_WRITTEN` stratum, never an exam template (0 eight-word overlap) | laptop | 0 USD | Q7 |
| 4 | **CTT retraining** on (old c45 rows + the new rows), three copies, g5.xlarge us-west-2 | AWS GPU | proposed line **`CUBE TRAIN at 3 USD`** (c45 = 1.40 USD for 227,497 rows; expected about 2 USD) | step 3 |
| 5 | TEACH-2 sealed exam (custodian, AI-written turns, 3 families) and run | one CPU host (the CTT cannot run on the laptop, §7.82) | proposed line **`CUBE EXAM at 1 USD`** (expected under 0.20 USD) | steps 2–4 |

Total proposed: at most 4 USD, as two separate owner lines. Nothing is spent by this packet.

## 7. What this design does not claim

- That cubes help. That is what TEACH-2 asks; the forecast is in the pre-code §11.
- That the CTT reads well: its record is mixed; this design fences it behind agreement and asks by default.
- That the Eye may act: `NOT LICENSED`, unchanged.
- That language crosses an RPA: `NOT LICENSED` (§7.35, §7.100, §7.102). The Atlas here is a filing place and a lookup
  order, as in v1.
- Anything beyond `SYNTHETIC_ONLY` + `LLM_WRITTEN_ONLY`.

## 8. Sources read

Spec §7.43 (M1), §7.82, §7.90, §7.95 (CTT), §7.110 (talk packet), §7.115 and §7.121 (memory compaction, TEACH-1),
§7.122 (EYE-ACT-1), §7.69 (wave 3: `ATLAS×CUBE_STORE` additive); `docs/working/noetic_council/cube_store/store.py`,
`cube.py`; `docs/working/noetic_council/continuity_build_v2/atlas.py`; `helm_memory_compact.py` at the thread head;
`Documents\Codex\2026-10-15\helm_m1_memory_fading_design_v1\FADING_RULES.md`, `LAYERS.md`.
