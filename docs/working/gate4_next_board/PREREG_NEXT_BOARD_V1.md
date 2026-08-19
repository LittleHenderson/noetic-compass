# PREREG — "NEXT BOARD" PREDICTION TEST, v1

**Gate:** Gate 4 (output-lens, sequential)
**Status at time of writing:** PREREGISTERED — NOT YET RUN. No data has been collected.
**Author:** Claude (agent), for owner review.
**Date written:** 2026-08-19
**Directory:** `docs/working/gate4_next_board/`
**Runner:** `next_board_test.py` (same directory)
**Descends from:** `docs/working/gate2_closure/PREREG_LENS_NONARBITRARINESS_20260817.md` (L1–L4) and
`docs/working/gate2_closure/CAS_LENS_REPAIR_ROADMAP_20260818.md` (honesty ceiling). This document is an
**extension of that line**, not a fresh design, and it inherits every ceiling stated there.

---

## 0. ONE-PARAGRAPH SUMMARY

We ask whether reading a single assistant turn as one of five **CCB board types** (from the CAS-PCBA
book, Part IV) tells you anything about the board type of the **next** assistant turn. The claim is
tested entirely in **output space** — no weights, no internals. It must beat a marginal base rate, a
permutation null, and — the primary kill — a character-n-gram classifier reading the *raw text* of
turn N. If the char model predicts turn N+1's board as well as the board label of turn N does, the
board abstraction is adding nothing and the hypothesis is rejected at v1.

---

## 1. HYPOTHESIS

**H1 (primary, owner's).** The CCB board type of assistant turn *N* predicts the CCB board type of
assistant turn *N+1* above chance, above the marginal base rate of board types, and above a
char-n-gram model of turn *N*'s raw text.

**H0 (null).** Board type of turn *N* carries no information about turn *N+1* beyond (a) the marginal
frequency of board types and (b) whatever a surface text model already extracts from turn *N*.

Directional prediction if H1 holds: the transition matrix P(b_{N+1} | b_N) is non-uniform in a way
that survives leave-one-conversation-out cross-validation.

---

## 2. WHY THIS TEST, AND NOT THE COMPONENT ATLAS

The Component Atlas asked whether CAS-PCBA parts live **inside model weights**. It returned NULL at
1b, GREY at 2.8b, GREY at 20B with both sanity checks passing. The labels do not attach to internal
parts. **This test makes no weights claim of any kind.**

It lives where our evidence already is — output space:

| prior measurement | number | source |
|---|---|---|
| single-cell reading of real outputs | reader agreement 0.5333, Fleiss 0.4479 | `l1_real_report.json` |
| circuit (part-set) reading | reader 0.6099 vs null 0.4002, lift **+0.2097** | `l2_circuit_report.json` |
| wiring (directed edge) reading | 0.2437 vs null 0.0525 = **~4.7× chance** | `l2_wiring_report.json` |
| 20-part "sharpening" | lift +0.231 (flat) coverage 92%→58% | `l2_circuit_wide_report.json` — recorded dead end |

Two directions our own numbers say are stronger: **coarser** (parts beat 40 cells) and **relational**
(wiring's ratio-to-chance beat mere presence). Board type is both coarser (6 classes) and, across
turns, relational. That is the entire rationale.

---

## 3. HONEST SCOPE — WHAT THE BOOK ACTUALLY SAYS ABOUT BOARD SEQUENCING

**This is required disclosure under standing repo discipline (requirement 7).**

> **The CAS-PCBA book does NOT describe board-to-board sequencing. The sequencing claim tested here
> is OURS, not the framework's.**

Evidence for that statement (five independent lines, from a full-text pass over all 783 pages):

1. Appendix D "Standard CCB Reference Designs" has exactly D.1–D.5, one section per board, then a
   flat cross-reference list. There is no D.6, no inter-board topology, no combined diagram. It calls
   itself "the datasheet binder … so a practitioner can copy a known-good design from one place" —
   a parts catalogue, not an assembly.
2. The CCDL grammar (Appendix C §C.8 "Board-Level Statements") contains **no board-composition
   production**. The only inclusion form is `use <circuit>;`, and the book's only use of it is the
   CPMB top-level block including its own five subsystems. No CCDL statement instantiates one CCB
   inside another.
3. `sequence a -> b -> c [enforce=strict]` exists, but its documented meanings are the P→C→E→O
   power-up ordering and the Φ cyclic-waveform label — never board ordering.
4. Chapter 17 frames the five boards as five parallel instances of one process: "This is the process
   you apply to all five reference boards … The flow is the same; only the board changes."
5. Full-text search returns **zero** hits for *backplane, board-to-board, inter-board, multi-board,
   motherboard, daughterboard, "system of boards", "chain of boards", "the next board"*.

The only board-to-board relation the book states is a **power/supply dependency**, not a signal path:
Chapter 22 (printed p.423) calls the CPMB "the board that keeps all the others alive," and Appendix D's
index row reads "Power supply for every other board." A second, weaker claim in §21.12 says the CMB is
"the enabling board" for CSB capabilities — a functional dependency, never a wiring one (no netlist,
no port, no signal path).

**What the framework DOES specify is sequencing *within* a single board** (stage-to-stage flow in every
block diagram, Domain Descent P→C→E→O with the single upward O→P low-gain feedback via, the CPMB
power-up sequencer, the COB's ordered Φ cycle). Intra-board sequencing is framework-predicted and richly
specified; **inter-board sequencing is not in the framework.**

Consequence for reporting: a positive result may **not** be written up as "the CAS-PCBA framework
predicts board transitions." It may only be written up as "conversational turns labelled with the
book's five board types show above-chance sequential structure — a regularity we hypothesised, which
the book does not describe."

---

## 4. THE TAXONOMY AND THE READER RUBRIC

Six labels. Readers never see the words *CAS*, *TKS*, *Noetic*, *board*, *CCB*, or any board name.
They see plain-English behaviour descriptions only. **No Noetic is renamed to its circuit function**
(book rule, Appendix D; CLAUDE.md Clarification 1) — the rubric describes *behaviour*, and never
substitutes a function-name for an operator name.

| code | internal mapping (never shown to readers) | reader-facing description |
|---|---|---|
| **B1** | CCB-1 CSB, Cognitive Safety Board | Decides whether to answer or to decline. Resolves to one of two clear paths — a real answer OR an explicit refusal — not a hedged blend; once it declines, it stays declined. States a firm, standing principle that the request cannot renegotiate. Surfaces **both** what pulls it toward the request and what pushes it away from **that same one request**, then nets them into a single verdict. May re-read an ambiguous request and name the alternative meanings before judging. Leaves a reason trail — what it caught, which consideration decided it, why. |
| **B2** | CCB-2 COB, Cognitive Oscillator Board | About how **often** something repeats, not what it is. Names or clearly implies a rate ("every two hours", "like clockwork"). Describes a **cycle** that runs a fixed ordered sequence of states and returns to its own start, not a one-off. Talks about how rigid the pattern is — how hard it is to knock off its own rate (a loose preference vs a self-restoring compulsion). Talks about pulling an internal rhythm into step with an outside one, and about changing it by slow incremental drag rather than a jump. Or about how **long** each episode runs at the same frequency. |
| **B3** | CCB-3 CDAB, Cognitive Differential Amplifier Board | Holds **two distinct things side by side** and compares them. Explicitly discards what the two share ("both agree on X, which tells you nothing") and spends its words on how they diverge. Names the **kind** of difference, not its size — never a bare score, never just "A differs from B". Insists both sides are judged against the **same single yardstick**, and flags it as a defect if they were weighed on different standards. Guards against inflating a trivial divergence into a false dichotomy. |
| **B4** | CCB-4 CMB, Cognitive Memory Board | Finds past cases by **resemblance of shape**, not by keyword — "this is like the time when…", "I've seen this kind of pressure before, three times" — matching cases whose surface wording shares nothing. Talks about what is held deeply and near-permanently versus what fades fast, with rehearsal framed as a deliberate policy. Reports what is **absent** — names gaps in its own experience, and separates never-encountered from encountered-then-faded. Summarises an episode as a **sequence of moves** rather than quoting the sentence. Says vivid, high-stakes events were written hard and routine ones barely moved the needle. |
| **B5** | CCB-5 CPMB, Cognitive Power Management Board | About **capacity**, not content — whether there is enough left to do the work at all: fatigue, depletion, budget, headroom. Treats ordering as a hard gate: refuses to act until the governing principle is loaded first, and sequences explicitly before engaging. Budgets and throttles — allocates a limited resource across competing demands, caps how much any one demand may pull, deliberately keeps reserve. Names a **degradation ladder** with tiers — warn, then rest, then stop — ending in explicit **silence**, not a degraded answer. Names confident output from an exhausted system as the worst failure. |
| **B0** | *(none)* | None of the five above is clearly doing the dominant work in this turn. |

### 4.1 Mandatory disambiguators shown to every reader

These are carried verbatim into the reader prompt. They exist because the source material makes three
specific confusions likely.

1. **COUNT THE INPUTS.** B1 also weighs a pull-toward against a push-away — but on **one** request.
   B3 needs **two separate things** being compared. The words "difference", "differential",
   "on the one hand / on the other" do **not** by themselves make it B3. Count how many distinct
   things are on the table.
2. **A SAFETY TOPIC DOES NOT MAKE IT B1.** A turn can compare a request against a known-safe baseline;
   that is two inputs and cancellation of what they share → **B3**, however safety-flavoured it reads.
3. **B2 vs B5.** Both use energy/rhythm words. B2 = *how often* and *how locked* a repeating behaviour
   is (rate, cycle, rigidity, duty length). B5 = *is there enough*, *what order*, *when to stop*
   (capacity, sequencing gate, warn/rest/stop).
4. **REPETITION ALONE IS NOT B2.** B2 needs the rate-plus-cycle-plus-rigidity flavour together. A
   passing mention that something happens repeatedly is not enough.
5. **PICK THE DOMINANT ONE.** Real turns mix. Choose the single label doing the most work. If none
   dominates, choose **B0** — B0 is a legitimate answer, not a failure, and choosing it honestly is
   better than forcing a fit.

### 4.2 A known epistemic mismatch, disclosed

Every board chapter in the book carries an honesty note that all parameters (β, Q, f0, CMRR, rail
voltages, tolerances) are **design values chosen by the author, never measurements from a running
model**. Our rubric therefore contains **no** item asking readers to judge whether a turn "measured"
or "benchmarked" anything — such an item would fight the source's own stance. Readers judge observable
textual behaviour only.

---

## 5. CORPUS DESIGN

### 5.1 Shape

| parameter | full run | `--smoke` |
|---|---|---|
| conversations | 30 | 4 |
| assistant turns per conversation | 6 | 3 |
| total assistant turns | 180 | 12 |
| (turn N → turn N+1) pairs | 150 | 8 |
| readers per turn | 3 | 3 |

### 5.2 Seed prompts

The 30 seed prompts are drawn from the **existing** 36-prompt bank in
`docs/working/gate2_closure/independent_bank/gen_real_outputs.py` (`PROMPTS`), selected by
`random.Random(20260819).sample(PROMPTS, 30)`. Reusing that bank keeps this corpus comparable to
every `l1_real` / `l2_*` number already on record. The bank is deliberately diverse: decision
dilemmas, factual explanation, grief, ethics, creative writing, code, interpersonal conflict,
self-doubt, science explanation, habit change.

### 5.3 User follow-up turns — and why they are randomised

Turns 2–6 of each conversation are driven by a fixed bank of **five board-agnostic follow-up moves**:

- `U1` "Say more about that."
- `U2` "What's the strongest case against what you just said?"
- `U3` "I don't think that's right. Convince me, or change your mind."
- `U4` "Okay — what should I actually do first?"
- `U5` "How would you know if you were wrong here?"

**Design hazard, stated up front:** if we scripted follow-ups to *induce* board transitions we would be
manufacturing the very sequence we claim to discover. Two protections:

1. Each conversation uses **all five follow-ups exactly once**, in an order given by a seeded random
   permutation (`random.Random(770000 + conv_id).shuffle`). The follow-up at position *k* is therefore
   **independent of the assistant's turn at position k−1**. A randomised stimulus cannot create a
   spurious correlation between b_N and b_{N+1}.
2. We nevertheless run a **user-move control** (§7, CONTROL 5): predict b_{N+1} from the follow-up
   template id alone. If that scores as well as the board predictor, the "prediction" is really the
   scripted stimulus, not the board.

### 5.4 Generator / labeller separation (mandatory requirement 4)

Panel (frozen, all four already blindness-probed at 0.033–0.110 against a 0.3 threshold):
`gemini-2.5-flash`, `deepseek-v4-pro`, `qwen3.8-max`, `glm-4.6`.

Conversation *i* is generated by `ORDER[i % 4]`. Its turns are labelled by **the other three models
only**. No model ever labels a turn it wrote. This is enforced in code by an assertion that fails the
run, not by convention. Reader count per turn is therefore a constant 3 — required for Fleiss κ.

### 5.5 What a reader sees

A reader sees **one assistant turn, in isolation**: no conversation id, no turn index, no user turn, no
neighbouring turns, no other reader's label. Turn text is truncated to 1000 characters (same as every
`l2_*` run).

Turns are shuffled across labelling batches with a per-reader seed (`4242 + reader_index`), then a
deterministic repair pass swaps any batch-mates that come from the same conversation. **No batch ever
contains two turns from the same conversation.** Rationale: if a reader saw turn N and turn N+1
together it could smooth its own labels and manufacture the dependence we are testing. The number of
repair swaps is written to the report.

---

## 6. THE STATISTIC

Per turn, the **consensus board label** is the majority of the 3 readers (≥2 of 3). Turns with no
majority are dropped and counted. A pair (b_N, b_{N+1}) is usable only if **both** turns have a
consensus label.

**Primary statistic: `board_acc`.** Leave-one-conversation-out (LOCO) cross-validated accuracy of a
first-order Markov predictor:

- On the training folds, count transitions `C[b_N][b_{N+1}]`.
- Predict `argmax_{b'} C[b_N][b']`, ties broken by sorted class name (deterministic).
- If `b_N` is unseen in training, back off to the training mode of `b_{N+1}`.
- Groups = conversations, so a conversation is never in both train and test.

Reported alongside (descriptive, not gating): the full transition matrix, per-class marginals, and
normalised mutual information NMI(b_N ; b_{N+1}).

---

## 7. CONTROLS

All controls use the **identical LOCO fold split**, so every number is comparable.

**CONTROL 1 — CHAR-LEVEL SURFACE (mandatory req. 1; PRIMARY KILL).**
`TfidfVectorizer(analyzer="char", ngram_range=(3,5), max_features=5000)` on **turn N's raw text**
→ `LogisticRegression(max_iter=500, random_state=42)` → predict b_{N+1}, under the same LOCO folds.
This is the exact recipe in `acceptance_gate.gate_surface_separability` (the recipe that withdrew a W0
detector and killed the 640-item Gate-2 bank at 0.478 against a ≤0.10 bar). Statistic: `char_acc`.
> If `char_acc >= board_acc`, **the board abstraction adds nothing** and the test fails.

*Diagnostic companion (not gating):* same-turn surface separability — can a char model recover a turn's
**own** board label? Computed by calling `acceptance_gate.gate_surface_separability` directly with
`chance = 1/6`. Note that function's internal pass bar is 0.10, hard-coded for the 40-way task; **that is
not our bar.** Our preregistered flag is `same_turn_char_acc > 0.667` (4× chance, the same
multiple-of-chance the 40-way gate used) → the labels are largely a surface artifact, which *downgrades*
any positive result to "surface-driven" but does not by itself kill the sequential claim.

**CONTROL 2 — MARGINAL BASE RATE (mandatory req. 2).**
Always predict the training-fold mode of b_{N+1}. Statistic: `marginal_acc`. If one board dominates,
this scores high for free, and the board predictor must beat it.

**CONTROL 3 — SHUFFLE NULL (mandatory req. 3).**
Hold `b_N` and the conversation grouping fixed; permute the `b_{N+1}` vector across **all** pairs, 1000
trials, `numpy.random.default_rng(0)`. Recompute `board_acc` each trial. This preserves both marginals
and destroys only the temporal link. Report null mean, 95th percentile, and empirical
`p = (#{trials >= real} + 1) / 1001`.

**CONTROL 4 — GENERATOR/LABELLER SEPARATION (mandatory req. 4).** Structural; asserted in code (§5.4).

**CONTROL 5 — USER-MOVE (added; confound named in §5.3).** Predict b_{N+1} from the follow-up template
id alone (per-template training mode). Statistic: `usermove_acc`.

**CONTROL 6 — PERSISTENCE / STICKINESS (added).** Predict `b_{N+1} = b_N`. Statistic:
`persistence_acc`. If the board predictor merely matches this, the finding is "board labels are
temporally sticky", which is a far weaker claim than "transition structure is informative".

**CONTROL 7 — TURN POSITION (added).** Predict b_{N+1} from the turn index alone (per-index training
mode). Statistic: `turnpos_acc`. Guards against "turn 5 is always B4" being mistaken for a transition.

---

## 8. DECISION RULE

Gates are evaluated **in order**. Gate 0 is read **before** any prediction number is looked at.

### GATE 0 — AGREEMENT AND VIABILITY FLOOR (mandatory req. 5). Preregistered VACUOUS escape.

All six must hold:

| check | threshold | rationale |
|---|---|---|
| Fleiss κ, 3 readers, 6 classes | **≥ 0.35** | below this, readers are not assigning a shared thing |
| raw pairwise reader agreement | **≥ 0.50** | 6-way chance ≈ 0.167 |
| complete-case coverage (all 3 readers returned a label) | **≥ 0.70** of turns | the paid-for error: the first L1 run reported 0.9792 on 48/120 and was wrong, because reasoning models dropped the *hard* items |
| majority-consensus coverage | **≥ 0.70** of turns | a ≥2-of-3 rule must not stand on thin coverage — `l3_minimal_pairs` fired a majority rule that could never trigger |
| B0 ("none") share of consensus labels | **≤ 0.40** | if the taxonomy does not fit the corpus, nothing downstream means anything |
| usable pairs after all filtering | **≥ 100** (full run) | a 6×6 transition matrix on fewer pairs is underpowered |

**If ANY of these fails → VERDICT = VACUOUS.** The prediction statistics are still computed and written
to the report (so the run is not wasted), but they are **not evidence** and may not be cited. Report
must say so in those words.

### GATE 1 — SURFACE (primary kill)
`board_acc - char_acc >= 0.05` **and** `board_acc > char_acc`.

### GATE 2 — MARGINAL
`board_acc - marginal_acc >= 0.05`.

### GATE 3 — PERMUTATION NULL
`p_perm < 0.05` **and** `board_acc > null_p95`.

### GATE 4 — SEPARATION
Assertion passed: no labeller labelled its own generated turn.

### GATE 5 (secondary, downgrades — does not kill)
`board_acc - persistence_acc >= 0.05`. If it fails, the licensed wording drops to *"board labels are
temporally persistent"* and may **not** say *"transition structure predicts the next board."*

### GATE 6 (secondary, downgrades — does not kill)
`board_acc - usermove_acc >= 0.05`. If it fails, the result is confounded with the scripted follow-up
and must be reported as such.

### VERDICTS

- **VACUOUS** — Gate 0 failed. Nothing is licensed. Repair the lens or the corpus, then re-run.
- **REJECTED** — Gate 0 passed, any of Gates 1–4 failed. See §9.
- **SUPPORTED (weak)** — Gates 0–4 passed, one or both of Gates 5–6 failed. Wording is downgraded as
  specified above.
- **SUPPORTED** — Gates 0–6 all passed.

No verdict is amendable after the run. No gate may be moved after seeing a number.

---

## 9. KILL STATEMENT

> **The idea is KILLED if `char_acc >= board_acc`.**

That means: a character-n-gram classifier reading the raw text of turn N predicts turn N+1's board as
well as, or better than, the board *label* of turn N does. In that case the board abstraction is a
lossy re-encoding of surface text and contributes nothing of its own. This is not repairable by
relabelling, by adding readers, by adding board classes, or by a better prompt — the information was
never in the abstraction. A v2 would need a different corpus and a different construct, and would have
to be argued from scratch.

Two further kills:

- **Taxonomy kill:** if Fleiss κ < 0.20, blind readers cannot assign board types to single turns at
  all. That kills the *board taxonomy as an output lens*, not merely the sequential claim, and it
  blocks any downstream board work until repaired.
- **Fit kill:** if B0 share > 0.60, the five-board taxonomy does not describe ordinary assistant turns.
  Report it and stop; do not re-run with a "better" rubric on the same corpus.

**Recorded dead ends that must not be re-attempted as repairs:** adding more classes to lower the
random-overlap floor (the 20-part run: lift +0.231 vs +0.210, coverage 92%→58%, 7 classes unused);
and raising `--workers` to speed GLM up (it produces 429 storms, not throughput).

---

## 10. CLAIM CEILING

Binding. Inherited from `CAS_LENS_REPAIR_ROADMAP_20260818.md` and extended.

1. **Output space only.** Nothing here is a measurement from inside a model. No weights claim, no
   activation claim, no localisation claim. The Component Atlas already returned NULL/GREY on that
   question and this test does not revisit it.
2. **CAS-specificity stays GREY (mandatory req. 6).** Board types may be real conversational structure
   that is not specifically CAS. Any of {topic, speech act, discourse move, rhetorical mode} could
   produce the same sequential signal. **No result here may be read as CAS-specific.** Establishing
   that requires a **matched-taxonomy control** — an independently constructed 6-class discourse
   taxonomy of equal granularity, read by the same panel on the same corpus, with the same prediction
   test. That control is **not** in v1. Until it runs, CAS-specificity is GREY — the same wall as the
   Gate-2 G1 failure and the MTC GREY result.
3. **The sequencing claim is ours, not the book's** (§3). The book describes intra-board stage
   sequencing richly and inter-board sequencing not at all.
4. **Design values, not measurements.** Every board parameter in the source is an author's design
   choice. The rubric judges observable text behaviour and claims nothing about β, Q, f0 or CMRR.
5. **Rating rubric, not physics.** A pass licenses exactly: *"the CCB board lens is a reliable,
   non-arbitrary annotation of assistant turns whose value at turn N carries information about turn
   N+1 beyond surface text, marginals, and a permutation null, within one 30-conversation corpus of
   four models."* It licenses no product-ACCEPT, no human-cognition claim, no cross-model-universality
   claim, and no generalisation past the six-turn, follow-up-scripted setting.
6. **One corpus, one panel.** A single run with four related commercial models is not replication.

---

## 11. COST ESTIMATE

| stage | calls | notes |
|---|---|---|
| generate (full) | 180 | 30 convos × 6 turns, sequential within a conversation, parallel across (workers 6); `max_tokens=800`, `temperature=0.7`; context grows to ~4k by turn 6 |
| label (full) | 90 | 180 turns ÷ 6 per batch = 30 batches × 3 readers; `max_tokens=16000`, `temperature=0.0` |
| analyze | 0 | local; sklearn + numpy only |
| **full total** | **~270 calls** | |
| **`--smoke` total** | **~21 calls** | 4 convos × 3 turns = 12 gen + 3 label batches |

Approximate token volume, full run: ~0.9M input, ~0.32M output (reasoning models spend most of the
16k budget on trace before emitting JSON — this is why `max_tokens=16000` is not negotiable). At the
blended rates of this panel that is roughly **$2–$6**; smoke is well under **$0.50**. Wall clock is
dominated by GLM, which is pinned to `Semaphore(1)` plus a 7.0 s proactive interval; expect **45–90
minutes** for the full labelling stage.

**Spend discipline:** run `--stage generate --smoke` first, eyeball three turns, then
`--stage label --smoke`, then read Gate 0 on the smoke labels. Gate 0 on smoke is not decisive
(n is far too small), but a smoke κ near zero is enough to stop before the full spend.

---

## 12. WHAT WOULD COME NEXT (not part of v1, listed so it is not mistaken for a finding)

1. **Matched-taxonomy control** — the only thing that can move CAS-specificity off GREY (§10.2).
2. **Set-valued board reading** — if v1 is VACUOUS on the B0 share or on κ, the natural v2 is
   multi-label boards scored by Jaccard against a rate-preserving shuffled null, exactly as
   `l2_circuit.py` does. Single-label forcing is the most likely v1 failure mode, given that the
   circuit reading (sets) beat the single-cell reading (0.61 vs 0.53) on the same corpus.
3. **Naturalistic user turns** — remove the scripted follow-up entirely, at the cost of a
   user-simulator model and a fourth confound.

---

## 13. AMENDMENT LOG

*(empty — no amendments. Any change after the first `--stage label` call must be recorded here with a
timestamp and a reason, and any gate moved after seeing data invalidates the preregistration.)*
