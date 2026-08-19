# PREREG — "NEXT BOARD" PREDICTION TEST, v1

**Revision:** **Rev 0.4** (post-adversarial-review; supersedes Rev 0.3 in full)
**Gate:** Gate 4 (output-lens, sequential)
**Status at time of writing:** PREREGISTERED — NOT YET RUN. **No data has been collected under
this revision.** One Rev 0.3 smoke run exists and is quarantined in `rev03_stale/` marked
`DO_NOT_REUSE` — it was generated under the without-replacement follow-up scheme that Rev 0.4
rejects as true-by-construction (§13, FATAL-1). It must not be relabelled or analysed.
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
**within-conversation** permutation null, the scripted user move, turn position, and — the primary
kill — the **strongest of three surface models** (char n-gram, word unigram, length) reading the *raw
text* of turn N. If a surface model predicts turn N+1's board as well as the board label of turn N
does, the board abstraction is adding nothing and the hypothesis is rejected at v1. A **matched
6-class discourse taxonomy**, read by the same panel on the same corpus, runs *inside v1* so that a
positive result says something about the *board* taxonomy specifically and not merely about "an LLM
ensemble beats TF-IDF".

**Note on the baseline you should have in mind.** The console prints a 1/6 = 0.167 label chance. That
is **not** the relevant baseline. Gate 0 permits the "none dominates" class up to 0.40 of consensus
labels, so an always-predict-the-mode rule can legitimately score up to **≈ 0.40 — about 2.4× the
1/6 figure**. GATE 2 compares against the LOCO-measured marginal, not against 1/6, precisely so that a
dominant class cannot buy a pass.

---

## 1. HYPOTHESIS

**H1 (primary, owner's).** The CCB board type of assistant turn *N* predicts the CCB board type of
assistant turn *N+1* above chance, above the marginal base rate of board types, and above a surface
model of turn *N*'s raw text.

**H0 (null).** Board type of turn *N* carries no information about turn *N+1* beyond (a) the marginal
frequency of board types, (b) the composition of the conversation it sits in, and (c) whatever a
surface text model already extracts from turn *N*.

Directional prediction if H1 holds: the transition matrix P(b_{N+1} | b_N) is non-uniform in a way
that survives leave-one-conversation-out cross-validation **and** a within-conversation permutation.

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

Carried verbatim into the reader prompt. They exist because the source material makes three specific
confusions likely.

1. **COUNT THE INPUTS.** B1 also weighs a pull-toward against a push-away — but on **one** request.
   B3 needs **two separate things** being compared. The words "difference", "differential",
   "on the one hand / on the other" do **not** by themselves make it B3.
2. **A SAFETY TOPIC DOES NOT MAKE IT B1.** A turn can compare a request against a known-safe baseline;
   that is two inputs and cancellation of what they share → **B3**, however safety-flavoured it reads.
3. **B2 vs B5.** Both use energy/rhythm words. B2 = *how often* and *how locked* a repeating behaviour
   is. B5 = *is there enough*, *what order*, *when to stop*.
4. **REPETITION ALONE IS NOT B2.** B2 needs rate-plus-cycle-plus-rigidity together.
5. **PICK THE DOMINANT ONE.** Real turns mix. If none dominates, choose **B0** — B0 is a legitimate
   answer, not a failure.

### 4.2 A known epistemic mismatch, disclosed

Every board chapter in the book carries an honesty note that all parameters (β, Q, f0, CMRR, rail
voltages, tolerances) are **design values chosen by the author, never measurements from a running
model**. Our rubric therefore contains **no** item asking readers to judge whether a turn "measured"
or "benchmarked" anything. Readers judge observable textual behaviour only.

### 4.3 The matched-taxonomy arm (CONTROL 8) — inside v1

A second, independently constructed **6-class discourse taxonomy of equal granularity** (5 named
classes + "none dominates"), built from ordinary speech-act categories with zero CCB content, is
labelled by the **same panel on the same corpus** and put through the **same prediction test**:

| code | reader-facing description |
|---|---|
| **D1** | Tells the reader what to **do** — instructions, steps, a plan, a recommendation to act. |
| **D2** | **Explains** how or why something is the way it is — mechanism, definitions, background, causes. |
| **D3** | **Argues** for a position — advances and supports a claim, or weighs claims and comes down somewhere. |
| **D4** | Attends to the reader's **feelings** and situation — acknowledges, validates, reassures, softens. |
| **D5** | Talks about **itself** — its own knowledge, limits, uncertainty, process, self-correction. |
| **D0** | None of the five above dominates. |

Rev 0.3 deferred this to v2. That was wrong: without it, a GATE 1 pass licenses only *"a 3-model LLM
consensus reading of turn N beats a TF-IDF logistic regression on turn N"* — which **any** competently
written 6-class discourse taxonomy would likely also achieve — so v1's positive result would be close
to uninformative **about boards specifically**. The arm costs one extra labelling pass on the *same*
corpus (~128 calls) and converts a GREY into an actual finding, versus spending twice on two corpora.

---

## 5. CORPUS DESIGN

### 5.1 Shape

| parameter | full run | `--smoke` |
|---|---|---|
| conversations | **36** (the entire seed bank) | 4 |
| assistant turns per conversation | **7** | 3 |
| total assistant turns | **252** | 12 |
| possible (turn N → turn N+1) pairs | **216** | 8 |
| readers per turn | 3 (of a 4-model panel) | 3 |
| taxonomy arms | 2 (`board`, `alt`) | 2 |

`--n-convos` is **hard-capped at 36** and the runner exits with an error above it. Rev 0.3 defaulted to
30 and would have silently shrunk any larger request to the 36-prompt bank size, quietly invalidating
the Gate 0 pair arithmetic.

### 5.2 Seed prompts

All 36 seed prompts come from the **existing** bank in
`docs/working/gate2_closure/independent_bank/gen_real_outputs.py` (`PROMPTS`), ordered by
`random.Random(20260819).sample(PROMPTS, 36)`. Reusing that bank keeps this corpus comparable to
every `l1_real` / `l2_*` number already on record. The bank is deliberately diverse: decision
dilemmas, factual explanation, grief, ethics, creative writing, code, interpersonal conflict,
self-doubt, science explanation, habit change. **No seed prompt is reused across conversations** —
two conversations from one prompt would be topically correlated and would break LOCO independence.

### 5.3 User follow-up turns — sampled i.i.d. WITH REPLACEMENT

Turns 2–7 of each conversation are driven by a fixed bank of **five board-agnostic follow-up moves**:

- `U1` "Say more about that."
- `U2` "What's the strongest case against what you just said?"
- `U3` "I don't think that's right. Convince me, or change your mind."
- `U4` "Okay — what should I actually do first?"
- `U5` "How would you know if you were wrong here?"

**Each turn's follow-up is an INDEPENDENT draw with replacement** (`random.Random(770000 + conv_id)`,
one `choice()` per turn). A move may appear twice in a conversation or not at all.

> **Rev 0.3 defect, corrected.** Rev 0.3 drew a **permutation** — all five used exactly once. That makes
> f_t and f_{t+1} **dependent**: P(f_{t+1}=u | f_t=u) = 0 against an unconditional 1/5. Turn *t* is
> generated in response to f_t and turn *t+1* in response to f_{t+1}, so b_N carried information about
> which follow-up had been **consumed**, which constrained which follow-up drove b_{N+1} — **a
> b_N → b_{N+1} dependence manufactured entirely by the sampling scheme, with zero board content.**
> Rev 0.3 §5.3 asserted "a randomised stimulus cannot create a spurious correlation between b_N and
> b_{N+1}". **That claim was false for that design and is deleted.** With i.i.d. draws it is true, and
> the user-move control below is a hard kill rather than a downgrade.

Second protection: **CONTROL 5 / GATE 6** predicts b_{N+1} from the follow-up template id alone. In
Rev 0.4 failing it **REJECTS the run** (Rev 0.3 merely downgraded to "SUPPORTED (weak)", which would
have let a fully design-induced signal be reported as support).

### 5.4 Generator / labeller separation (mandatory requirement 4)

Panel (frozen, all four already blindness-probed at 0.033–0.110 against a 0.3 threshold):
`gemini-2.5-flash`, `deepseek-v4-pro`, `qwen3.8-max`, `glm-4.6`.

Conversation *i* is generated by `ORDER[i % 4]`. Its turns are labelled by **the other three models
only**. No model ever labels a turn it wrote. This is enforced at three points: at label time
(`collect_marks` refuses the write), at analyze time (GATE 4 **computes** the violation set), and in
the report (the violating uids are listed). Rev 0.3 hardcoded `g4 = True` and wrote
`{"enforced": true, "assertion_passed": true}` unconditionally, with the real check as a bare `assert`
that crashed the run instead of producing a REJECTED verdict; that report field was not evidence of
anything. Reader count per turn is a constant 3 — required for Fleiss κ.

### 5.5 What a reader sees

A reader sees **one assistant turn, in isolation**: no conversation id, no turn index, no user turn, no
neighbouring turns, no other reader's label. Turn text is truncated to 1000 characters (same as every
`l2_*` run).

**Excerpt ids are per-batch, per-reader ALIASES** drawn from `random.Random(91000 + …).sample(range(1000,10000), k)`.
Rev 0.3 printed the internal `uid`, which equals `turns_per_conv × conv_position + turn_index` and
therefore deterministically encoded **both conversation and turn position** — a direct contradiction of
this section's own blindness guarantee. The uid↔alias map lives only on the analysis side.

Turns are shuffled across labelling batches with a per-reader seed (`4242 + reader_index`), then a
deterministic repair pass swaps any batch-mates from the same conversation. **No batch may contain two
turns from the same conversation.** If any residual collision survives the repair, the run **aborts at
label time** and the residual count is also a hard Gate 0 check. (Rev 0.3 counted residual collisions
and reported them but gated nothing — yet a residual collision is exactly the contamination that lets a
reader smooth its own labels and manufacture the dependence under test.)

### 5.6 Label acceptance — strict, and why

A labelling call is accepted **only if all four hold**:

1. `finish_reason == "stop"`;
2. a **JSON array** is parseable out of the **answer** (`message.content`);
3. every id is an **alias actually shown in that batch** (a fabricated id is dropped, and can never
   overwrite a genuine label from another batch);
4. **exactly** the batch's ids appear, once each.

Anything else yields **zero labels** and routes the batch into the repair pass.

> Rev 0.3 concatenated `content` with `reasoning_content` and scanned the result for the first
> `\b(B[0-5])\b` after `"id":`. A reasoning model that hit `finish_reason="length"` before emitting the
> array, or wrote "not B1, so B3" in its trace, would still yield confident-looking labels harvested from
> chain-of-thought; `finish_reason` was printed but never enforced. It also stored **any** uid the model
> emitted, without checking it belonged to that batch, into a plain dict in `as_completed` order — so a
> hallucinated id could nondeterministically overwrite a real label. Both are closed.

**Reasoning-only responses are refused by default.** `--allow-reasoning-only` exists but is a
**preregistration deviation** and must be recorded in §14 if used. The cost of strictness is paid by
the repair pass, not by coverage.

### 5.7 Repair pass and checkpointing

**Repair pass.** After the main pass, each reader is re-asked *only* for the uids it failed to return, in
batches of 3, for up to 2 rounds (`--repair-rounds`). Coverage on this panel is lost to parse/drop, not
to call failure, so this is cheap — and it is what makes the Gate 0 coverage floors reachable at all.

**Checkpointing.** Both API stages append to JSONL as each unit lands and skip completed units on
restart: conversations to `conversations.jsonl`, individual labelling calls to `label_calls.jsonl`
(keyed by a sha256 of reader+arm+uid-set). Rev 0.3 buffered everything in memory and wrote only after
the executor fully drained, so a KeyboardInterrupt, console-encoding crash, expired key or OOM lost the
**entire** stage — 252 generation calls, or an hour-plus of serialized GLM labelling.

**Partial conversations are kept.** A short/empty or failed turn now **truncates** the conversation at
the last good turn (kept if it reached `--min-turns`, default 3). Rev 0.3 raised and discarded the whole
conversation including its good turns, shrinking the binding constraint (n) and skewing the generator mix.

---

## 6. THE STATISTIC

Per turn, the **consensus label** is the majority among the readers who returned a label, requiring
**≥ 2 present and ≥ 2 agreeing**. A pair (b_N, b_{N+1}) is usable only if **both** turns have a
consensus label.

**The two Gate-0 metrics are deliberately decoupled** (Rev 0.4): *agreement* (Fleiss κ, raw pairwise) is
computed on **complete cases only** — all 3 readers present — so it is never inflated by non-random
dropout on hard items; *consensus* may form from 2 present labels, so one missing reader does not
destroy a usable turn. Rev 0.3 required 3-of-3 **and** a majority for every usable pair, which is what
made its pair floor unreachable.

**Primary statistic: `board_acc`.** Leave-one-conversation-out (LOCO) cross-validated accuracy of a
first-order Markov predictor:

- On the training folds, count transitions `C[b_N][b_{N+1}]`.
- Predict `argmax_{b'} C[b_N][b']`.
- If `b_N` is unseen in training, back off to the training mode of `b_{N+1}`.
- Groups = conversations, so a conversation is never in both train and test.

**Tie-break rule, disclosed.** Ties resolve first on the **training-fold overall frequency** of the tied
classes, then on sorted class name. Rev 0.3 broke ties on name alone; because `"B0"` sorts before
`B1..B5`, *every* tie in the transition table and every backoff tie resolved to the "none dominates"
class — deterministic, but a systematic tilt. The frequency tie-break removes it; the residual
alphabetical tie-break (used only when frequencies are also tied) is disclosed here and is the only
remaining arbitrary element.

**Reported alongside — descriptive, not gating:** the full transition matrix, per-class marginals, and
NMI(b_N ; b_{N+1}) **with its own within-conversation permutation null and empirical p** (NMI is
upward-biased at small n and is clearly non-zero under independence, so quoting it without a null
invites over-reading).

> **MULTIPLICITY CLAUSE (binding).** `board_acc` is the single preregistered primary statistic, named in
> advance, singular, computed one way. **No individual transition cell may be reported as a result.**
> "B1→B3 runs at 3× chance" is forbidden — that is the forking path this clause closes. The 36-cell
> matrix may be shown in full as description, never mined for a claim.

---

## 7. CONTROLS

All controls use the **identical LOCO fold split**, including CONTROL 6 (which has no fitted parameters
but is nonetheless computed over the same test indices, so this sentence is literally true — in Rev 0.3
it was not).

**CONTROL 1 — SURFACE (mandatory req. 1; PRIMARY KILL).** Three baselines on **turn N's raw text**
(the same 1000-char truncation the readers saw), predicting b_{N+1} under the same LOCO folds, with the
vectoriser **refit inside every training fold**:

| baseline | recipe (identical to `acceptance_gate.gate_surface_separability`) |
|---|---|
| char | `TfidfVectorizer(analyzer="char", ngram_range=(3,5), max_features=5000)` |
| **word unigram** | `CountVectorizer(max_features=3000, stop_words="english", binary=True)` |
| length | raw character count |

each → `LogisticRegression(max_iter=500, random_state=42)`, **with `C` tuned on grouped inner splits of
the training fold only** (grid 0.25 / 1 / 4 / 16).
**`surface_acc = max(char_acc, word_acc, length_acc)`.**

> **Rev 0.3 handicapped this control twice.** (a) Only the char baseline ran on the predictive task —
> yet **word unigram (topic) is the single most likely surface route** from turn N's text to turn N+1's
> board, and it was never run. (b) `LogisticRegression` at default `C` on ~145 training rows against 5000
> sparse char features regularises toward the majority class, so `char_acc` lands near `marginal_acc` and
> GATE 1 collapses into GATE 2 — leaving the "PRIMARY KILL" with almost no independent teeth. The
> information given to the control was correctly matched (same text, same folds, refit per fold); the
> model class was not allowed to be competitive. It is now.

> If `surface_acc >= board_acc`, **the board abstraction adds nothing** and the test fails.

*Diagnostic companion (not gating):* same-turn surface separability — can a surface model recover a
turn's **own** label? Reported two ways: a **LOCO-grouped** version (this is the one that flags) and a
direct call to `acceptance_gate.gate_surface_separability` for comparability only. The latter uses
`StratifiedKFold` with **no conversation grouping**, so same-conversation text leaks across folds and
inflates it, and it silently returns `{"error": …}` whenever any class has fewer than 5 members — which
is likely here. **Note also that its `chance` parameter is accepted but never referenced in its body:
passing `chance=1/6` configures nothing.** Our preregistered flag is `same_turn_surface_acc > 0.667`
(4× chance) on the **grouped** numbers → labels are largely a surface artifact, which *downgrades* a
positive result to "surface-driven" but does not by itself kill the sequential claim.

**CONTROL 2 — MARGINAL BASE RATE (mandatory req. 2).** Always predict the training-fold mode of
b_{N+1}. Statistic: `marginal_acc`. With the B0 cap at 0.40 this can legitimately reach ≈ 0.40; the
board predictor must beat *this*, not 1/6.

**CONTROL 3 — SHUFFLE NULL (mandatory req. 3), WITHIN-CONVERSATION.** Hold `b_N` and the grouping fixed;
permute `b_{N+1}` **inside each conversation** (block permutation), 1000 trials, `random.Random(0)`.
Report null mean, 95th percentile, and empirical `p = (#{trials ≥ real} + 1)/1001`.

> **Rev 0.3's null was mis-specified and did not test what it claimed.** It permuted `b_{N+1}` across
> **all** pairs globally, which also destroys **conversation-level clustering**. Each conversation is one
> seed prompt on one topic generated by one model, so its turns are label-homogeneous for reasons that
> have nothing to do with transitions; under a global null that homogeneity **alone** drives `board_acc`
> far above the null and GATE 3 passes with **no transition structure whatsoever**. Rev 0.3's claim that
> the shuffle "preserves both marginals and destroys only the temporal link" was false. A
> within-conversation permutation preserves each conversation's label composition and isolates exactly
> the temporal link. **This is the significance test of the whole study; as written in Rev 0.3 its
> p-value was not interpretable.**
>
> **Consequence, stated in advance:** this null is *strong*. A purely **persistent** (sticky) label
> sequence will **not** clear it, because within-conversation permutation of a run-structured sequence
> still leaves many adjacent identical pairs. That is intended: persistence is CONTROL 6's business, and
> GATE 3 is meant to find transition structure, not stickiness.

**CONTROL 4 — GENERATOR/LABELLER SEPARATION (mandatory req. 4).** Structural; computed, not asserted (§5.4).

**CONTROL 5 — USER-MOVE.** Predict b_{N+1} from the follow-up template id alone. Statistic:
`usermove_acc`. **Gated as a HARD KILL** (GATE 6).

**CONTROL 6 — PERSISTENCE / STICKINESS.** Predict `b_{N+1} = b_N`. Statistic: `persistence_acc`.

**CONTROL 7 — TURN POSITION.** Predict b_{N+1} from the turn index alone. Statistic: `turnpos_acc`.
**Now gated** (GATE 7). Rev 0.3 computed it and gated nothing, so a b_N that was largely a function of
turn position (very plausible — turn 1 is a fresh answer, later turns are defences and action lists)
would let the Markov table merely re-encode the position→label map while every gate still passed.

**CONTROL 8 — MATCHED DISCOURSE TAXONOMY (§4.3).** Same panel, same corpus, same prediction test, on
the D1–D5/D0 taxonomy. Compared **on the pairs usable in both arms**, so the margin is paired.
Statistic: `alt_acc`. Gated as GATE 8.

---

## 8. DECISION RULE

Gates are evaluated **in order**. Gate 0 is read **before** any prediction number — and this is now
**enforceable**, not aspirational: `--stage gate0` prints agreement and coverage **only**, computes no
prediction statistic, and writes its own report.

### GATE 0 — AGREEMENT AND VIABILITY FLOOR (mandatory req. 5). Preregistered VACUOUS escape.

| check | threshold | rationale |
|---|---|---|
| Fleiss κ, 3 readers, 6 classes, **complete cases only** | **≥ 0.35** | below this, readers are not assigning a shared thing. Reachable on prior evidence: 0.4479 on a 40-way task, 0.5489 on a 12-way task |
| complete cases available for κ | **≥ 60** | κ on fewer is not interpretable |
| raw pairwise agreement, complete cases only | **≥ max(0.50, P_e + 0.35·(1 − P_e))** | see note below |
| complete-case coverage | **≥ 0.60** of turns | honest κ denominator; measured comparators are l1_real 0.556 (4 readers) and l2_wiring 0.694 |
| consensus coverage (≥2 agreeing of ≥2 present) | **≥ 0.70** of turns | a majority rule must not stand on thin coverage — `l3_minimal_pairs` fired a majority rule that could never trigger |
| B0 share of consensus labels | **≤ 0.40** | if the taxonomy does not fit the corpus, nothing downstream means anything |
| residual same-conversation batch collisions | **= 0** | hard; §5.5 |
| usable pairs after all filtering | **≥ 90** (full run) | see arithmetic below |

**The raw-agreement floor is DERIVED, not asserted.** With 6 classes and the permitted concentration,
chance agreement `P_e = Σ p_k²` is roughly 0.25, so a flat raw floor of 0.50 implies κ ≈ 0.33 — *below*
the 0.35 κ floor. Rev 0.3 stated both as independent hurdles without ever computing their joint
difficulty. Rev 0.4 computes `P_e` from the **observed** marginals and sets the binding raw floor to
`P_e + 0.35·(1 − P_e)`, so the two are one hurdle expressed twice, with an absolute 0.50 kept as a
second, explicit floor. The report prints `P_e`, both floors, and which one bound.

**Pair-count arithmetic, shown so the thresholds are jointly satisfiable** (this is the Rev 0.3
auto-doom, corrected):

> 36 conversations × 7 turns = **252 turns**, and 36 × 6 = **216 possible pairs**. A pair needs a
> consensus label at both ends, so `usable_pairs ≈ 216 · c²` where `c` is consensus coverage:
> **c = 0.70 → 106 pairs** (floor 90, ✓ with margin) · c = 0.65 → 91 · c = 0.60 → 78 (fails, but the
> 0.70 coverage floor fails first — the ordering is consistent).
> Rev 0.3 set a **100-pair floor on 30 × 6 = 150 possible pairs**, which silently demanded **c ≥ 0.82**
> while stating **0.70** two rows above it in the same table. At this panel's measured coverage
> (0.556–0.694) that bought a **near-certain VACUOUS** for the entire spend. The three changes that fix
> it are the repair pass (§5.7), the decoupled metrics (§6), and this larger, arithmetically consistent
> corpus.

**If ANY Gate 0 check fails → VERDICT = VACUOUS.** The prediction statistics are still computed and
written (so the run is not wasted), but they are **not evidence** and may not be cited. The report says
so in those words.

### GATE 1 — SURFACE (primary kill)
`board_acc − surface_acc ≥ 0.05` **and** the 5th percentile of the paired cluster-bootstrap margin > 0.

### GATE 2 — MARGINAL
`board_acc − marginal_acc ≥ 0.05` **and** bootstrap p5 > 0.

### GATE 3 — WITHIN-CONVERSATION PERMUTATION NULL
`p_perm < 0.05` **and** `board_acc > null_p95`.

### GATE 4 — SEPARATION
Computed violation set is empty. A violation → **REJECTED**, not a crash.

### GATE 5 (downgrades — does not kill)
`board_acc − persistence_acc ≥ 0.05` (+ bootstrap p5 > 0). If it fails, the licensed wording drops to
*"board labels are temporally persistent"* and may **not** say *"transition structure predicts the next
board."*

### GATE 6 — USER MOVE (**HARD KILL** in Rev 0.4)
`board_acc − usermove_acc ≥ 0.05` (+ bootstrap p5 > 0). Failure → **REJECTED**. A signal produced by the
scripted stimulus is a design artifact and must not be reportable as support.

### GATE 7 (downgrades — does not kill)
`board_acc − turnpos_acc ≥ 0.05` (+ bootstrap p5 > 0).

### GATE 8 — MATCHED TAXONOMY (downgrades; governs the CAS-specificity wording)
`board_acc − alt_acc ≥ 0.05` on shared pairs (+ bootstrap p5 > 0).
- **Pass** → the finding is *board-taxonomy-specific beyond one matched 6-class discourse taxonomy on
  the same corpus and panel*. It is still **not** "CAS-specific" in any deeper sense — one matched
  control is not the space of possible taxonomies.
- **Fail** → CAS-specificity **stays GREY**, the verdict is downgraded to SUPPORTED (weak), and any
  sequential signal must be reported as **generic conversational structure**.
- **Not run** → GREY by default.

### 8.1 UNCERTAINTY AND POWER — how the 0.05 margins are to be read

Every 0.05 margin is a **preregistered threshold on a paired cluster bootstrap over conversations**
(2000 resamples, seed 7): the point margin must clear 0.05 **and** the 5th percentile must exceed 0. A
confidence interval on every gating margin is written to the report.

This is stated because the naked margins were not defensible. At ~106 pairs over 36 conversations
filling a 6×6 = 36-cell table there are ~3 observations per cell, so the LOCO Markov table backs off to
the training mode for many rows and `board_acc` converges mechanically toward `marginal_acc`;
observations also cluster (up to 6 pairs per conversation), so effective n is well below the pair count.
At p ≈ 0.4 and n ≈ 106 the SE of an accuracy is ≈ 0.05, so a 0.05 point margin is about **1 SE**.
**A failed GATE 2 at this n may reflect power, not truth**, and the report says so.

### VERDICTS

- **VACUOUS** — Gate 0 failed. Nothing is licensed. Repair the lens or the corpus, then re-run.
- **REJECTED** — Gate 0 passed, any of Gates 1, 2, 3, 4, **6** failed.
- **SUPPORTED (weak)** — Gates 0–4 and 6 passed, one or more of Gates 5, 7, 8 failed. Wording is
  downgraded as specified above.
- **SUPPORTED** — Gates 0–8 all passed.

No verdict is amendable after the run. No gate may be moved after seeing a number. The analyze stage
writes a **sha256 of this document and of `next_board_test.py`** into the report; compare it against the
hash recorded when the first labelling call ran. A mismatch means the preregistration or the runner was
edited after data collection began, and the run is not preregistered.

---

## 9. KILL STATEMENT

> **The idea is KILLED if `surface_acc >= board_acc`**, where `surface_acc = max(char, word-unigram,
> length)` on turn N's raw text.

That means: a surface classifier reading the raw text of turn N predicts turn N+1's board as well as, or
better than, the board *label* of turn N does. In that case the board abstraction is a lossy re-encoding
of surface text and contributes nothing of its own. This is **not repairable** by relabelling, by adding
readers, by adding board classes, or by a better prompt — the information was never in the abstraction.
A v2 would need a different corpus and a different construct, argued from scratch.

Three further kills:

- **Design-artifact kill (GATE 6):** if the scripted follow-up predicts b_{N+1} as well as the board
  label does, the "prediction" is the stimulus, not the board. REJECTED.
- **Taxonomy kill:** if Fleiss κ < 0.20, blind readers cannot assign board types to single turns at all.
  That kills the *board taxonomy as an output lens*, not merely the sequential claim, and blocks any
  downstream board work until repaired.
- **Fit kill:** if B0 share > 0.60, the five-board taxonomy does not describe ordinary assistant turns.
  Report it and stop; do not re-run with a "better" rubric on the same corpus.

**Recorded dead ends that must not be re-attempted as repairs:** adding more classes to lower the
random-overlap floor (the 20-part run: lift +0.231 vs +0.210, coverage 92%→58%, 7 classes unused);
and raising `--workers` to speed GLM up (it produces 429 storms, not throughput — and the semaphore
caps GLM concurrency at 1 regardless).

---

## 10. CLAIM CEILING

Binding. Inherited from `CAS_LENS_REPAIR_ROADMAP_20260818.md` and extended.

1. **Output space only.** Nothing here is a measurement from inside a model. No weights claim, no
   activation claim, no localisation claim. The Component Atlas already returned NULL/GREY on that
   question and this test does not revisit it.
2. **What a GATE 1 pass actually licenses is narrow.** `b_N` is a 3-model **LLM consensus reading**;
   the control is a TF-IDF/count logistic regression. Beating it licenses *"an LLM ensemble reading of
   turn N beats surface models of turn N"* — **not** "the board abstraction carries information". Only
   **GATE 8** speaks to whether the *board* taxonomy specifically matters, and one matched control is
   not the space of taxonomies. CAS-specificity is **GREY unless GATE 8 passes**, and even then the
   licensed phrase is "board-taxonomy-specific beyond one matched discourse taxonomy" — never
   "CAS-specific" (mandatory req. 6).
3. **The sequencing claim is ours, not the book's** (§3). The book describes intra-board stage
   sequencing richly and inter-board sequencing not at all.
4. **Design values, not measurements.** Every board parameter in the source is an author's design
   choice. The rubric judges observable text behaviour and claims nothing about β, Q, f0 or CMRR.
5. **Rating rubric, not physics.** A pass licenses exactly: *"the CCB board lens is a reliable,
   non-arbitrary annotation of assistant turns whose value at turn N carries information about turn N+1
   beyond surface text, marginals, a within-conversation permutation null, the scripted user move and
   turn position, within one 36-conversation corpus of four models."* It licenses no product-ACCEPT, no
   human-cognition claim, no cross-model-universality claim, and no generalisation past the seven-turn,
   follow-up-scripted setting.
6. **One corpus, one panel.** A single run with four related commercial models is not replication.
7. **No individual transition cell is a result** (§6 multiplicity clause).

---

## 11. COST ESTIMATE

| stage | calls | notes |
|---|---|---|
| generate (full) | **252** | 36 convos × 7 turns, sequential *within* a conversation, parallel across; `max_tokens=800`, `temperature=0.7`; context grows to ~5k by turn 7 |
| label, board arm | **128** | each reader labels the 3/4 of turns it did **not** generate: 189 turns ÷ 6 per batch = 32 batches × 4 readers |
| label, alt arm (CONTROL 8) | **128** | same corpus, same panel, D-taxonomy |
| repair pass | **~40–70** | batches of 3, ≤2 rounds, only the uids a reader failed to return |
| analyze | 0 | local; sklearn + numpy only |
| **full total** | **~550–580 calls** | |
| **`--smoke` total** | **~30 calls** | 12 gen + 8 label calls per arm × 2 arms + repair |

> Rev 0.3's arithmetic was wrong: it wrote "180 turns ÷ 6 = 30 batches × 3 readers = 90". Labelling is
> **4 readers × ⌈(3/4 · turns)/6⌉**, because every reader labels three-quarters of the corpus — not
> 3 readers labelling all of it.

**Tokens and money.** Rev 0.3 claimed ~0.32M output while simultaneously arguing that `max_tokens=16000`
is non-negotiable *because* readers spend most of it on trace — internally inconsistent (296 label calls
× 16k is a **4.7M ceiling**). Realistic: **~1.4M input, ~0.9–2.0M output**. At this panel's blended rates
that is roughly **$8–$25** for the full two-arm run; smoke is well under **$1**.

**Wall clock.** Dominated by GLM, pinned to `Semaphore(1)` plus a 7.0 s proactive interval:
GLM *labelling* is ~64 serialized calls (32 per arm) ≈ **45–60 min**; GLM *generation* is ~63 serialized
calls ≈ **20–35 min**. Rev 0.3 omitted the generation leg entirely. Budget **2–3.5 hours** for the full
run. Worker pools are sized to the **sum of the per-provider semaphores (9)** so a thread blocked on GLM
never starves gemini/deepseek/qwen; raising `--workers` does not raise GLM throughput.

**Spend discipline.**
1. `--stage generate --smoke`, then **eyeball three turns**. (A Rev 0.3 smoke run produced ~143-char
   gemini turns on one seed against ~4000-char deepseek turns — read the sample line the stage prints.)
2. `--stage label --taxonomy board --smoke`.
3. `--stage gate0 --smoke` — this prints agreement/coverage and **no** prediction number.
4. **Smoke can never PASS Gate 0.** Its relaxed pair floor of 8 is exactly the number of pairs the smoke
   corpus can produce (4 convos × 2), so passing would require 100% consensus coverage. **Smoke is a
   RED-LIGHT-ONLY check:** a smoke κ near zero is enough to stop before the full spend; a smoke VACUOUS
   is not a stop signal and must not be read as one.

---

## 12. WHAT WOULD COME NEXT (not part of v1, listed so it is not mistaken for a finding)

1. **A second matched taxonomy, and a second corpus.** GATE 8 passing against one matched taxonomy is a
   real finding but not a general one.
2. **Set-valued board reading** — if v1 is VACUOUS on the B0 share or on κ, the natural v2 is multi-label
   boards scored by Jaccard against a rate-preserving shuffled null, exactly as `l2_circuit.py` does.
   Single-label forcing is the most likely v1 failure mode, given that the circuit reading (sets) beat
   the single-cell reading (0.61 vs 0.53) on the same corpus.
3. **Naturalistic user turns** — remove the scripted follow-up entirely, at the cost of a user-simulator
   model and a fourth confound.
4. **Higher-order structure** — a second-order Markov or a duration model, but only with the n to
   support it; at 216 possible pairs a 6×6 table is already thin (§8.1).

---

## 13. REVISION LOG — Rev 0.3 → Rev 0.4

Every change below is a correction made **before any Rev 0.4 data was collected**. Rev 0.3's smoke data
is quarantined and unusable.

**FATAL**
1. **True-by-construction follow-ups.** Permutation (without replacement) → **i.i.d. with replacement**;
   GATE 6 promoted from downgrade to **hard kill**; the false claim in §5.3 deleted.
2. **Permutation null mis-specified.** Global shuffle → **within-conversation block permutation**, which
   preserves conversation composition and isolates the temporal link.
3. **Gate 0 arithmetically and empirically unreachable.** Added a repair pass; decoupled agreement
   (complete cases) from consensus (≥2 of ≥2 present); grew the corpus to 36 × 7 = 216 possible pairs;
   restated the floors as jointly satisfiable and **showed the arithmetic**.

**MAJOR**
4. **Position index leaked to readers** — `uid` in the prompt → per-batch, per-reader **alias ids**.
5. **CONTROL 7 gated nothing** → **GATE 7** added.
6. **Labels could be harvested from a reasoning trace** → strict acceptance (finish_reason, JSON array
   from the answer, exact id set, reasoning-only refused by default).
7. **Hallucinated ids accepted and could overwrite real labels** → batch-alias intersection, first-write-wins.
8. **Residual same-conversation batch collisions reported but not gated** → **hard abort + Gate 0 check**.
9. **No checkpointing or resume** → JSONL append + skip-on-restart in both API stages.
10. **Surface control handicapped** → word-unigram and length added to the predictive task; `C` tuned
    inside the training fold; kill on `max(char, word, length)`.
11. **No uncertainty or power analysis** → paired cluster bootstrap over conversations on every gating
    margin; explicit power note.
12. **Gate 0's two agreement floors mutually inconsistent** → raw floor **derived** from observed marginals.
13. **Gate 1 licensed less than the framing implied** → **matched-taxonomy arm folded into v1** as
    CONTROL 8 / GATE 8.

**MINOR** — corrected call arithmetic (§11); corrected token/cost figures; disclosed that
`gate_surface_separability`'s `chance` argument is unused; same-turn diagnostic moved to LOCO-grouped
folds; CONTROL 6 computed over the LOCO folds so §7's claim is literally true; `_mode` tie-break changed
to frequency-then-name and disclosed; NMI given its own null; `--stage gate0` added; smoke declared
red-light-only; partial conversations kept instead of discarded; GATE 4 computed rather than hardcoded;
worker pool sized to the provider semaphores; multiplicity clause added; sha256 immutability record added.

**UNCHANGED because it was already correct** — the claim ceiling (§10) and the honest-scope disclosure
(§3) survive the review intact, as does the base-rate handling (GATE 2 compares against the LOCO-measured
marginal, never 1/6); §0 now states the absolute always-predict-mode ceiling implied by the B0 ≤ 0.40 cap.

---

## 14. AMENDMENT LOG

*(empty — no amendments since Rev 0.4 was frozen. Any change after the first `--stage label` call must be
recorded here with a timestamp and a reason, and any gate moved after seeing data invalidates the
preregistration. Using `--allow-reasoning-only` is a deviation and must be logged here.)*
