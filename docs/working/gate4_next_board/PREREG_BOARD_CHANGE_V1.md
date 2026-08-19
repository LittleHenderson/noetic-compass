# PREREG — BOARD **CHANGE** TEST, v1

**Gate:** Gate 4 (output lens, sequential)
**Status:** PREREGISTERED — **NOT YET BUILT, NOT YET RUN.** No corpus, no labels, no numbers exist
under this design.
**Author:** Claude (agent), for owner review.
**Date written:** 2026-08-19
**Directory:** `docs/working/gate4_next_board/`
**Runner (to be written):** `board_change_test.py` — a **new** file. `next_board_test.py` is not
edited by this design and stays on disk as the record of the retired test.
**Replaces:** `PREREG_NEXT_BOARD_V1.md` (Rev 0.4 / v2 / v2.1). That document is **not edited**. It is
retired, and §17 below records exactly what this design inherits from it and what it drops.
**Descends from:** `docs/working/gate2_closure/PREREG_LENS_NONARBITRARINESS_20260817.md` and
`docs/working/gate2_closure/CAS_LENS_REPAIR_ROADMAP_20260818.md`. Every ceiling stated there binds
here.

---

## 0. ONE-PARAGRAPH SUMMARY

The old test asked what board comes next. It failed, because in real conversation the board almost
never changes, so "what comes next" is nearly always "the same thing". This test asks the opposite
question. It looks at the moments when the board **does** change. Two claims are made, and they are
kept apart on purpose. **Claim 1** is retrospective: when the board changes between turn N and turn
N+1, does the lens see the change? **Claim 2** is prospective and is the one worth money: is there a
signal in turn N that a change is coming at N+1, before N+1 exists? Claim 2 is gated much harder than
Claim 1, and Claim 2 is reported **only** on changes the user did not ask for. Everything is measured
in output space. No weights claim. The primary metric is **F1 on the change class**, with precision,
recall, the base rate and the confusion matrix beside it, and with Matthews correlation coefficient as
a co-requirement. **Accuracy is forbidden as a headline number.**

---

## 1. WHY WE PIVOTED — AND WHY THE STICKINESS IS A FINDING, NOT A BUG

The next-board test was rejected on its own smoke run. The numbers, from
`next_board_report_smoke.json` at commit `aebe179f`:

| quantity | value |
|---|---|
| `board_acc` (LOCO first-order Markov) | **0.5079** |
| `persistence_acc` (just predict the same board as turn N) | **0.5238** |
| `board_acc − persistence_acc` | **−0.0162** (bootstrap p5 **−0.0484**) |
| within-conversation permutation null, mean / p95 | **0.4761** / **0.5881** |
| empirical `p` on that null | **0.4279** |
| GATE 3 (permutation null) | **FALSE** |
| GATE 5 (beats persistence) | **FALSE** |
| VERDICT | **REJECTED** |

Read plainly: **natural conversation is sticky.** In that corpus the board stayed the same across
**33 of 63** transitions (0.5238). Predicting "no change" beat the transition model. Shuffling labels
inside a conversation did not destroy the apparent signal, because the signal was autocorrelation, not
prediction. There was almost nothing to predict.

**That stickiness is a finding.** It says the steady state is not where the information is. It
reframes the question. The valuable event is the **change**. Changes are rare, and rare events are
where the commercial value sits: seeing a shift in a model's reasoning before it arrives is an
early-warning capability. A tool that says "this model is about to stop answering and start refusing"
is worth something. A tool that says "this model is doing the same thing it was doing last turn" is
not.

So this design throws away the steady state and spends its whole budget on the transitions.

**One number from the retired run is carried forward as an anchor and nothing more.** The observed
change rate there was `1 − 0.5238 = 0.4762` over 63 pairs. It is not used as the planning base rate
(§8.1 says why).

---

## 2. THE TWO CLAIMS

They are separate. The second is much stronger than the first. A pass on the first does **not**
license the second.

### CLAIM 1 — DETECTION (retrospective)

> When the kind of response changes between assistant turn N and assistant turn N+1, does the board
> lens see it — better than a surface model reading the same two texts?

The lens reads each turn **in isolation**. It never sees the pair. The change signal it produces is
the simple indicator `b_N ≠ b_{N+1}`. The thing that signal is checked against is an **independent**
panel judgement made on the **pair**, by readers who are never shown the board taxonomy (§6.2).

This is a real claim, but a modest one. It is retrospective. You need turn N+1 to have happened.

### CLAIM 2 — EARLY WARNING (prospective)

> Is there a signal **in turn N alone** that a change is coming at N+1 — before N+1 exists?

The predictor may use only what exists at turn N: the board label of turn N, and how much the three
readers disagreed about turn N. Nothing from turn N+1 may touch it.

This is the commercially meaningful claim. It is gated much harder (§10.3), and it is reported
**only** on the model-initiated subset defined in §3.

---

## 3. THE DESIGN POINT THAT DECIDES THE WHOLE STUDY

**A board change has two possible causes. They are not the same finding.**

**(a) USER-INDUCED.** The user's message between turn N and turn N+1 asks for something different.
"Ok but what should I actually do?" flips ANSWER-shaped output to PLAN-shaped output. The board
changed because **the user changed it**.

> **This is trivial.** It is instruction-following, not the model's reasoning shifting. It carries
> **no early-warning value**, because you already know what you asked for. Nobody needs a lens to tell
> them their own request changed.

**(b) MODEL-INITIATED.** The user's message does **not** call for a different kind of response, and
the board changes anyway. The model turned from explaining to refusing, or from answering to
planning, or from analysing to hedging, without being pushed there.

> **This is the interesting case, and it is the only one that supports Claim 2.**

### 3.1 How the two are separated — preregistered, blind, measured not assumed

Two mechanisms, and both are used.

**Mechanism 1 — corpus construction.** The corpus holds the user turn constant in the stratum that
matters. In **Stratum N** the user's follow-ups are pure continuers that request no particular kind of
response (§5.3). A change in Stratum N is a candidate model-initiated change **by construction**.

**Mechanism 2 — blind classification, which is what actually decides it.** Construction is not
trusted on its own. Every observed transition is classified by a blind panel:

- **What the reader sees:** the user message that preceded assistant turn N, and the user message that
  preceded assistant turn N+1. **Nothing else.** Never the model's replies. Never a board name. Never
  a turn index or conversation id.
- **The question:** *"Does the second message ask for a different KIND of response than the first?"*
- **The answer:** `DIFFERENT-KIND` or `SAME-KIND`. Three readers. Majority of ≥2 agreeing among ≥2
  present.

| panel verdict | classification of the transition |
|---|---|
| `DIFFERENT-KIND` | **USER-INDUCED** |
| `SAME-KIND` | **MODEL-INITIATED** |
| no consensus | **UNCLASSIFIED** — excluded from both subsets, counted and reported |

**Claim 2 is computed on the MODEL-INITIATED subset only.** The negatives for Claim 2 come from the
same subset — that is, the Claim 2 analysis set is *every* pair whose user turn did not request a
different kind, changed or not.

**Claim 2 on the user-induced subset is also computed, reported, and licenses nothing.** It is
included so the contrast is visible, and it is labelled `NOT LICENSED` in the report on that line
itself.

### 3.2 The instrument check on this panel — a positive control

If the user panel never says `DIFFERENT-KIND` anywhere, the split has not been *measured*, only
assumed, and Claim 2's whole separation is unverified.

**Stratum S** exists for this reason. Its user turns are drawn from the retired design's follow-up
bank, which contains `U4` — *"Okay — what should I actually do first?"* — an explicit request for a
different kind of response.

> **Preregistered floor `USER_PANEL_POSITIVE_CONTROL_MIN = 0.50`.** Of the Stratum S transitions where
> a `U4` draw follows a non-`U4` draw, the panel must return `DIFFERENT-KIND` on at least **0.50**. If
> it does not, the panel cannot detect a different-kind request even where one was deliberately
> inserted, the (a)/(b) split is unmeasured, and **Claim 2 is VACUOUS**.

### 3.3 If there are too few model-initiated changes, that is a preregistered VACUOUS outcome

> **Binding.** If the model-initiated subset yields fewer than **40** changes or fewer than **150**
> analysable pairs, **Claim 2 is VACUOUS**. Nothing about Claim 2 is licensed. **This is not a repair
> opportunity.** Re-running with a corpus tuned until enough model-initiated changes appear is
> selecting on the outcome, and it is forbidden. Any revival is a different construct, argued from
> scratch, in a new preregistration.

### 3.4 Why the prescribed-turn-type "hybrid" is NOT used here

`HYBRID_DESIGN_NOTE.md` proposed: SDG plans the path, a real model writes the turns, and the
prescribed turn type is the ground truth. `compliance_check.py` tested the assumption that a real
model can hit a prescribed turn type, and returned
**`FLOOR_ESTABLISHED__NOT_VALIDATED`** — recovery **0.7619** against a 7-way chance of **0.1429**, 42
items, Fleiss κ **0.9213**, with uneven per-type compliance (`ACK` recall **0.0000**, `ANSWER` recall
**0.3333**, 4 of 6 prescribed `ANSWER` turns read as `PLAN`) and a per-generator spread of **0.2636**
(qwen **0.9000** vs deepseek **0.6364**).

That floor is real. It is also **the wrong tool for Claim 2**, and this is the load-bearing reason:

> **A prescribed change is an instructed change.** Telling a model "now write a PLAN turn" makes the
> change case (a) — externally induced — by construction. It can support a detection claim. It can
> **never** support an early-warning claim, because there was nothing to warn about; the experimenter
> caused it.

So the hybrid is out of v1. The compliance numbers are recorded here as the reason, and stay available
for a future Claim-1-only detection study if one is ever wanted.

---

## 4. HYPOTHESES

**H1 (Claim 1).** The board lens, applied to each assistant turn in isolation, produces a change
indicator (`b_N ≠ b_{N+1}`) that reproduces an independent pair-level judgement of "did the kind of
response change" with change-class F1 above every trivial baseline and above the strongest surface
model reading the same two texts.

**H0(1).** The change indicator carries nothing beyond what a surface model already extracts from the
two texts — most obviously, "the two turns just look different from each other".

**H2 (Claim 2).** Among transitions where the user did **not** request a different kind of response,
information available at turn N alone predicts whether a change occurs at N+1, with change-class F1
above every trivial baseline, above the surface model of turn N's text, and above a
within-conversation permutation null.

**H0(2).** Nothing at turn N carries information about whether the next turn will differ in kind. The
change, when it happens, is unforecastable from the output lens.

---

## 5. CORPUS

### 5.1 Real model outputs only

> **Binding.** No templates. No synthetic text. No rendered strings.

This is not a preference. The retired design's SDG arm was withdrawn because its corpus was **38
distinct strings**, exact-string lookup was a bijection onto the label, and **raw character count
alone** predicted the label at **1.0000**. A surface-determined corpus makes the primary kill
unsatisfiable and the study unfalsifiable. Any corpus for this test must be written by real models,
turn by turn, with growing conversation context.

### 5.2 Shape

| parameter | full run | pilot |
|---|---|---|
| conversations, **Stratum N** (neutral user turns) | **60** (resizable to 120, §8.3) | 16 |
| conversations, **Stratum S** (shifting user turns) | **20** | 0 |
| conversations total | **80** | 16 |
| assistant turns per conversation | **10** | 10 |
| assistant turns total | **800** | 160 |
| transitions (possible pairs) per conversation | **9** | 9 |
| transitions total | **720** (540 in N, 180 in S) | 144 |
| readers per item, every task | **3** (from the 4-model bank) | 3 |
| reader tasks | **3** (§6) | 3 |

Ten assistant turns, not seven. Model-initiated drift needs room to happen. A longer conversation on
one topic is where a self-initiated shift lives.

### 5.3 The two user-turn banks

**Stratum N — pure continuers.** Each follow-up is an **independent draw with replacement**
(`random.Random(SEED_FOLLOWUP_N_BASE + conv_id)`, one `choice()` per turn). A move may appear twice or
not at all. These request no particular kind of response:

- `C1` "Go on."
- `C2` "Say more about that."
- `C3` "Keep going."
- `C4` "Mm-hm."
- `C5` "And?"

**Stratum S — shifting.** The retired design's bank, unchanged, drawn the same way
(`SEED_FOLLOWUP_S_BASE + conv_id`):

- `U1` "Say more about that."
- `U2` "What's the strongest case against what you just said?"
- `U3` "I don't think that's right. Convince me, or change your mind."
- `U4` "Okay — what should I actually do first?"
- `U5` "How would you know if you were wrong here?"

**i.i.d. with replacement is mandatory, and the reason is inherited.** Drawing a permutation
(each move used exactly once) makes `f_t` and `f_{t+1}` dependent — `P(f_{t+1}=u | f_t=u) = 0` against
an unconditional 1/5 — which manufactures a turn-to-turn dependence with zero board content. That
defect was found and fixed in the retired design and it is not reintroduced here.

### 5.4 Seeds — designed to CONTAIN changes, never to script them

80 distinct seed prompts. **No seed is reused across conversations** — two conversations from one
prompt would be topically correlated and would break leave-one-conversation-out independence.

- **36** come from the existing bank in
  `docs/working/gate2_closure/independent_bank/gen_real_outputs.py` (`PROMPTS`), ordered by
  `random.Random(SEED_PROMPT_ORDER).sample(PROMPTS, 36)`. Reusing that bank keeps this corpus
  comparable to every `l1_real` / `l2_*` number already on record.
- **44** are new, authored under the same blind-author discipline: the author never sees the board
  taxonomy, the board rubric, or any board name.

Seed families, and the count of each:

| family | shape | count | why |
|---|---|---|---|
| F1 factual → personal | a question about a statistic or a procedure that turns out to be about the asker's own situation | 12 | invites a shift from explaining to attending |
| F2 request → boundary | a benign request that drifts toward something a model should decline | 12 | invites a shift from answering to refusing |
| F3 open → action | an open question where a model may decide on its own to start prescribing steps | 12 | invites a shift from discussing to planning |
| F4 explain → edge of knowledge | a question that runs past what a model can support | 12 | invites a shift from asserting to hedging |
| F5 **steady** | a technical explanation with no natural turn in it | **12** | **the honest negatives** — seeds expected NOT to shift |
| F6 mixed / bank | the 36 existing bank prompts, unclassified | 20 used in N, 16 in S | comparability with prior runs |

*(Family counts sum to 80 across both strata; the exact per-stratum allocation is frozen in the runner
before generation and printed in the report.)*

> **DISCLOSURE, BINDING.** Choosing seeds likely to *contain* a change is **enrichment** — sampling for
> a rare event. It is legitimate, and it is how rare-event studies are run. But the base rate this
> corpus produces is an **ENRICHED** base rate. It is **never** an estimate of how often models change
> board in the wild, and no report may present it as one. The F5 steady family exists so the corpus is
> not wholly composed of invitations.

### 5.5 Generation protocol, and the two mechanical defects it must fix

Turns are generated sequentially inside a conversation and in parallel across conversations.
`max_tokens=800`, `temperature=0.7`. Conversation `i` is generated by `ORDER[i % 4]` over the frozen
panel: `gemini-2.5-flash`, `deepseek-v4-pro`, `qwen3.8-max`, `glm-4.6`.

The retired design's smoke exposed two mechanical defects. Both are fixed here, in advance:

**DEFECT 1 — a 25× generator length gap.** gemini produced ~140-character turns while
deepseek/qwen/glm produced ~3300–4000. That confounds generator identity with the label **and** hands
the length-based surface control a free ride.

- **`MIN_TURN_CHARS = 200`.** A turn under 200 characters is regenerated, up to `MAX_REGEN = 2`
  attempts. If it is still short, the conversation is **truncated** at the last good turn and kept if
  it reached `MIN_TURNS = 6`. It is not discarded — discarding whole conversations shrinks the binding
  *n* and skews the generator mix.
- **Per-generator length is reported.** If `median_len(longest generator) / median_len(shortest) > 3.0`
  the report carries `GENERATOR_LENGTH_IMBALANCE_FLAG = true` and the finding is downgraded to
  "possibly generator-confounded".
- **CONTROL 9 (§9) predicts the change label from generator identity alone**, and is gated.

**DEFECT 2 — GLM as reader returned "0 labels, finish=length" on 2 calls**, because the reasoning
trace consumed the whole 16000-token budget before any JSON was emitted. Result: readers-per-turn was
`{2: 9, 3: 3}`, so only 3 of 12 turns got the full panel.

- The reader prompt requires **the JSON array first**, before any explanation.
- `finish_reason == "stop"` is enforced (§6.4). A truncated call yields **zero** labels and routes to
  the repair pass.
- Reader `max_tokens` is raised for glm-4.6 specifically, and the per-reader call-status histogram
  (`ok` / `finish_length` / `parse_fail` / `id_mismatch`) is mandatory report output.

### 5.6 Checkpointing

Both API stages append to JSONL as each unit lands and skip completed units on restart: conversations
to `conversations_change.jsonl`, individual labelling calls to `label_calls_change.jsonl` keyed by a
sha256 of reader + task + item-id-set. A run of this size cannot be allowed to lose a stage to an
interrupt, an encoding crash, or an expired key.

---

## 6. THE THREE READER TASKS

Three tasks, three separate item views, three separate calls. The same 4-model bank serves all three.

### 6.1 T-BOARD — one assistant turn, in isolation

Unchanged from the retired design and reused verbatim: the same six codes `B1 B2 B3 B4 B5 B0`, the
same reader-facing behaviour descriptions, the same five mandatory disambiguators. Readers never see
the words *CAS*, *TKS*, *Noetic*, *board*, *CCB*, or any board name. A reader sees **one** assistant
turn, truncated to `READER_TRUNC_CHARS = 1000` — no conversation id, no turn index, no user turn, no
neighbouring turn, no other reader's label.

Consensus: majority among readers who returned a label, requiring **≥ 2 present and ≥ 2 agreeing**.

Output: `b_N` for every turn. The change indicator is `b_N ≠ b_{N+1}`.

### 6.2 T-CHANGE — a pair of consecutive assistant turns. **This is the ground truth.**

- **What the reader sees:** two assistant turns, in order, labelled `FIRST` and `SECOND`, each
  truncated to 1000 characters. **No user text. No board taxonomy. No board rubric. No board names. No
  conversation id, no turn index.**
- **The question:** *"Did the KIND of response change between FIRST and SECOND?"*
- **The answer:** `CHANGE` or `SAME`. Nothing else. Strict JSON array, one enum field per item.
- Three readers. Consensus: ≥ 2 agreeing among ≥ 2 present.

> **WHY THIS IS NOT CIRCULAR, AND WHY THE POINT MATTERS.** The retired design's SDG arm was withdrawn
> because its answer key had been authored by reading the same strings through the same rubric the
> readers were given. The key and the instrument shared an origin, so the statistic had no informative
> range. That defect is structurally excluded here. The board panel sees **one turn** and uses the
> **board rubric**. The change panel sees **the pair** and is **never given the board rubric**. Neither
> panel can derive the other's answer. The two views do not overlap and the two vocabularies do not
> overlap.

> **AND THE HONEST LIMIT OF IT.** The T-CHANGE ground truth is still a **reader judgement**, not a fact
> about the model. It is an observed rating, never a voltmeter reading. If the change panel is itself
> reading surface difference — two turns that look stylistically different get called `CHANGE` — then
> the whole study is measuring text distance. **That is exactly what surface arm S4 (§9, CONTROL 1) is
> built to expose, and if S4 wins, the study is killed.**

### 6.3 T-USER — a pair of consecutive user messages

Defined in §3.1. Readers see only the two user messages, never a model reply, and answer
`DIFFERENT-KIND` or `SAME-KIND`.

### 6.4 Rules that bind all three tasks

**Generator ≠ labeller (mandatory).** No model ever labels a turn it wrote, or a pair either of whose
turns it wrote. Both turns of a pair come from the same conversation and therefore the same generator,
so exclusion is well defined. Enforced at three points: at label time (`collect_marks` refuses the
write), at analyse time (the violation set is **computed**, not asserted), and in the report (violating
ids listed). A violation is a **REJECTED** verdict, not a crash. Reader count per item is a constant 3,
which Fleiss κ requires. For T-USER, whose items are our own bank strings and not model output, a
deterministic `excluded_reader = ORDER[conv_id % 4]` keeps the panel exactly 3 wide, and the report
states in those words that this is a **structure-preserving holdout, not a separation control**.

**Per-batch, per-reader alias ids (mandatory).** Item ids shown to readers are aliases drawn from
`random.Random(SEED_ALIAS_BASE + …).sample(range(1000, 10000), k)`. A reader never sees an internal
uid, a turn index, or a conversation id. The internal uid encodes position; printing it would
contradict the blindness guarantee outright. The alias↔uid map lives only on the analysis side.

**No batch may contain two items from the same conversation.** Items are shuffled with a per-reader
seed, then a deterministic repair pass swaps same-conversation batch-mates. Residual collisions abort
the run at label time, and the residual count is a hard Gate 0 check. A same-conversation collision is
exactly the contamination that would let a reader smooth its own labels and manufacture the dependence
under test.

**Strict label acceptance (mandatory).** A call is accepted only if all four hold:

1. `finish_reason == "stop"`;
2. a JSON array is parseable out of the **answer** (`message.content`), never out of a reasoning trace;
3. every id is an alias **actually shown in that batch** — a fabricated id is dropped and can never
   overwrite a genuine label from another batch;
4. **exactly** the batch's ids appear, once each.

Anything else yields **zero** labels and routes the batch to repair. Reasoning-only responses are
refused by default; `--allow-reasoning-only` exists, is a **preregistration deviation**, and must be
logged in §18.

**Repair pass.** Each reader is re-asked only for the ids it failed to return, in batches of 3, for up
to `REPAIR_ROUNDS = 2`. Coverage on this panel is lost to parse and drop, not to call failure, so
repair is cheap and it is what makes the coverage floors reachable at all.

**A known limitation, disclosed in advance.** The board panel and the change panel are drawn from the
**same four models**. With four models and three readers per item, disjoint panels are impossible. The
separation here is by **task and by call** — the calls are stateless and the item views do not overlap
— **not** by model identity. This is a real limitation and it is named in the claim ceiling (§12.6).

---

## 7. METRICS

### 7.1 Accuracy is forbidden as a headline

> **BINDING.** No verdict, headline, console line, or report key may present **accuracy** as the
> primary result of this study. The classes are severely imbalanced. If changes are 15% of
> transitions, "always predict no-change" scores **85%** and means nothing at all. Accuracy is
> computed and written to the report as a diagnostic only, and every place it appears it is
> accompanied by the base rate.

### 7.2 Primary metric

> **PRIMARY: F1 on the CHANGE class**, co-required with **MCC > 0**.

Reported with it, all mandatory, on every result line:

- **precision on the change class**;
- **recall on the change class**;
- **the base rate, stated beside every figure** — the share of analysed pairs whose ground truth is
  `CHANGE`;
- **the full 2×2 confusion matrix** (TP, FP, TN, FN), never summarised away;
- **Matthews correlation coefficient (MCC)**;
- accuracy, marked `diagnostic — not the result`.

### 7.3 The base rate is the thing to beat, and here is the arithmetic

Let `p` be the change base rate. Three degenerate strategies are computed and the **highest** of them
is the bar:

| degenerate strategy | precision | recall | change-class F1 | MCC |
|---|---|---|---|---|
| always predict `CHANGE` | `p` | `1` | **`2p / (1 + p)`** | **0** |
| always predict `SAME` | undefined → 0 | 0 | **0** | **0** |
| random at the base rate `p` | `p` | `p` | **`p`** | **≈ 0** |

Since `2p/(1+p) > p` for every `p < 1`, the binding F1 bar is always
**`trivial_f1_bar = 2p / (1 + p)`** — the always-predict-`CHANGE` strategy. Worked values:

| `p` | `trivial_f1_bar` |
|---|---|
| 0.15 | **0.2609** |
| 0.20 | **0.3333** |
| 0.25 | **0.4000** |
| 0.30 | **0.4615** |
| 0.40 | **0.5714** |

> **This is why MCC is a CO-REQUIREMENT and not a nice-to-have.** Every one of the three degenerate
> strategies scores **MCC = 0**. A predictor that clears the F1 bar *and* has an MCC bootstrap lower
> bound above 0 cannot be any of them. F1 alone can be gamed by predicting the rare class always; F1
> plus MCC cannot.

`trivial_f1_bar` is computed on the **training folds** of each LOCO split, exactly like every other
control, so it is never an in-sample number compared against a cross-validated one.

### 7.4 Multiplicity clause (binding, inherited)

`change_f1` is the single preregistered primary statistic for each claim, named in advance, singular,
computed one way. **No individual confusion-matrix cell may be reported as a result.** "B1→B3 changes
are caught at 3× chance" is forbidden. Per-board breakdowns may be shown in full as description and
may never be mined for a claim.

---

## 8. SIZING — THE BASE RATE ASSUMED, AND THE CORPUS THAT FOLLOWS

### 8.1 The assumed change base rate

| source | value | why it is or is not used |
|---|---|---|
| retired smoke, measured | **0.4762** (30 of 63) | **upper anchor only.** 63 pairs; its own report records `conv_file: synthetic`; and its user bank contained `U4`, which requests a different kind, so part of that rate is user-induced |
| **preregistered planning value, Stratum N** | **0.25** | deliberately set **below** the only measurement. Continuers remove the user push, which should lower the rate; shift-inviting seeds should raise it |
| design floor the study must survive | **0.15** | if the true rate is this low, the study still runs, but it may go VACUOUS on Claim 2 |
| stop-the-spend rate | **< 0.10** | measured at the pilot → stop before the full spend (§8.3) |

> **Headline: the assumed change base rate is `0.25` in the neutral stratum.**

### 8.2 Corpus size that follows, and joint satisfiability of the floors

Per conversation: 10 assistant turns → **9 transitions**.
80 conversations → **800 turns**, **720 transitions** (540 in Stratum N, 180 in Stratum S).

A transition is **analysable for Claim 1** if it has board consensus at **both** ends and T-CHANGE
consensus on the pair. Let `c` = board consensus coverage and `c_p` = pair consensus coverage:

```
analysable_pairs  ≈  720 · c² · c_p
```

| scenario | `c` | `c_p` | analysable pairs |
|---|---|---|---|
| measured on the retired smoke | 0.7833 | — | — |
| planning values | **0.75** | **0.85** | **344** |
| **exactly at the Gate 0 floors** | **0.70** | **0.75** | **264** |

**Gate 0's floors are jointly satisfiable, and here is the check.** This is the arithmetic the retired
design got wrong once: Rev 0.3 set a 100-pair floor on 150 possible pairs, which silently demanded
consensus coverage ≥ 0.82 while the same table stated 0.70 two rows above — a guaranteed VACUOUS after
the full spend. That must not recur.

```
G0_MIN_ANALYSABLE_PAIRS = 240

at the exact floors:  720 × 0.70² × 0.75 = 720 × 0.49 × 0.75 = 264.6  →  264  ≥ 240   ✓ (margin 24)
at c = 0.66 (below floor):                720 × 0.4356 × 0.75 = 235.2  →  235  <  240
```

At `c = 0.66` the pair floor would fail — but the **coverage floor of 0.70 has already failed**, so the
coverage check fires first and the ordering is consistent. The two floors are one hurdle expressed
twice, not two independent hurdles that can contradict each other.

### 8.3 The Claim 2 sample floor is NOT guaranteed, and it is protected by a pilot spend gate

Model-initiated analysable pairs per Stratum N conversation, **at the floor coverages**:

```
9 transitions × c²(0.49) × c_p(0.75) × P(T-USER = SAME-KIND | Stratum N)(0.90) = 2.98 pairs
```

Model-initiated **changes** per Stratum N conversation = `2.98 × r`, where `r` is the neutral-stratum
change rate.

| `r` | changes at 60 convos | meets the 40 floor? |
|---|---|---|
| 0.25 (planning) | **44.7** | ✓ (thin) |
| 0.20 | 35.8 | ✗ |
| 0.15 (design floor) | 26.8 | ✗ |

So at the pessimistic end the study goes VACUOUS on Claim 2. That risk is real and it is not hidden.
Two preregistered protections, both written down before any spend:

**PROTECTION 1 — PILOT SPEND GATE.** Run 16 Stratum N conversations (160 turns) through generation,
T-BOARD, T-CHANGE and T-USER first. Cost ≈ 409 calls (§15). Measure `r̂` = the observed
model-initiated change rate on the pilot's analysable pairs.

**PROTECTION 2 — PREREGISTERED RESIZE RULE.** Written now, so applying it later is not a deviation:

```
K_neutral = clamp( ceil( 40 / (2.98 · r̂) ), 60, 120 )

r̂ = 0.25  →  54  → clamped up to  60
r̂ = 0.20  →  68
r̂ = 0.15  →  90
r̂ = 0.12  →  112
r̂ < 0.10  →  over the 120 cap  →  STOP. Declare Claim 2 VACUOUS. Do not spend the remainder.
```

Stratum S stays at 20 conversations regardless.

**Pilot conversations are retained in the final corpus.** They are generated by the same code, under
the same protocol, with the same seeds discipline. Only the change base rate — not any gate statistic
— is read from them to size the study. This is a mild winner's-curse risk and it is disclosed: the
final report must **also** print Claim 1 and Claim 2 metrics computed on the **non-pilot conversations
alone**, as a preregistered sensitivity. If the two disagree in direction, the finding is downgraded to
`PARTIAL`.

### 8.4 Uncertainty and power

Every margin is a **preregistered threshold on a paired cluster bootstrap over conversations**
(`BOOT_N = 2000`, `BOOT_SEED = 7`): the point margin must clear its threshold **and** the 5th
percentile (`BOOT_LOWER_Q = 5`) must exceed 0. A confidence interval on every gating margin is written
to the report.

At 60 model-initiated changes the standard error on a recall of 0.60 is `sqrt(.6·.4/60) = 0.063`, so a
95% interval is roughly ±0.12. Observations cluster (up to 9 pairs per conversation), so the effective
n is well below the pair count and the clusters, not the pairs, set the resolution. **A failed Claim 2
gate at this n may reflect power, not truth, and the report must say so on that line.**

---

## 9. CONTROLS — ALL MANDATORY, ALL INHERITED

Every control uses the **identical leave-one-conversation-out (LOCO) fold split**, grouped by
conversation, so a conversation is never in both train and test. Vectorisers are refit **inside every
training fold**. `C` is tuned on grouped inner splits of the **training fold only** (grid 0.25 / 1 / 4
/ 16). All controls are computed over the same test indices, including the ones with no fitted
parameters.

**CONTROL 1 — SURFACE. PRIMARY KILL. Char AND word n-gram are both mandatory.**

The word-unigram (topic) arm was missing once in the retired design and was flagged as a fatal
handicap: it is the single most likely surface route from text to label. It is mandatory here on
**every** surface battery, without exception.

For **Claim 1** the surface battery reads the raw text of **both** turns and predicts the T-CHANGE
ground truth, on the same task and the same folds as the board indicator:

| arm | recipe |
|---|---|
| **S1 char** | `TfidfVectorizer(analyzer="char", ngram_range=(3,5), max_features=5000)` on `text_N + "\n\n" + text_{N+1}` |
| **S2 word unigram** | `CountVectorizer(max_features=3000, stop_words="english", binary=True)` on the same concatenation |
| **S3 length** | `[len(text_N), len(text_{N+1}), abs(len_{N+1} − len_N)]` |
| **S4 pair distance** | **cosine distance between the two turns' own vectors**, char and word, thresholded — "just measure how different the two texts are" |

each → `LogisticRegression(max_iter=500, random_state=42)`.
`surface_change_f1 = max(S1, S2, S3, S4)` on change-class F1.

> **S4 is the arm most likely to kill this study, and it is included for exactly that reason.** The
> obvious cheap detector for "did the response change" is "are these two texts far apart". If it wins,
> the board abstraction is a lossy re-encoding of text distance.

For **Claim 2** the surface battery reads **turn N's raw text alone** — the same 1000-character
truncation the readers saw — and predicts whether a change occurs at N+1, on the same folds: char,
word unigram, length. `surface_early_f1 = max(char, word, length)`.

> **PRIMARY KILL, both claims.** If the surface battery matches or beats the board-based predictor on
> change-class F1, **the abstraction adds nothing** and the claim fails. Not repairable by relabelling,
> by adding readers, by adding board classes, or by a better prompt.

*Diagnostic companion, not gating:* same-pair surface separability of the T-CHANGE ground truth — can a
surface model recover the ground truth at all? Reported LOCO-grouped. Flag at
`ground_truth_surface_f1 > 0.667`, which means the ground truth is largely a surface artefact and
downgrades every positive result to "surface-driven".

**CONTROL 2 — BASE RATE.** The three degenerate strategies of §7.3, computed on training folds.
`trivial_f1_bar = 2p/(1+p)`. This is the number named as the thing to beat, printed beside every result.

**CONTROL 3 — WITHIN-CONVERSATION PERMUTATION NULL.** Hold the predictor and the grouping fixed;
permute the change outcome **inside each conversation** (block permutation). `PERM_TRIALS = 1000`,
`PERM_SEED = 0`. Report null mean, 95th percentile, and empirical `p = (#{trials ≥ real} + 1)/1001`.

> **Never a global shuffle.** A global permutation also destroys conversation-level clustering. Each
> conversation is one seed prompt on one topic written by one model, so its turns are label-homogeneous
> for reasons that have nothing to do with transitions; under a global null that homogeneity alone
> beats the null and the gate passes with no structure whatsoever. This was a named FATAL in the
> retired design. Block permutation preserves each conversation's composition and isolates exactly the
> temporal link.

**CONTROL 4 — GENERATOR ≠ LABELLER.** Structural, and **computed, not asserted** (§6.4). Hardcoding
this check to `true` was a named defect in the retired design; the violating ids are listed in the
report.

**CONTROL 5 — USER MOVE.** Predict the change outcome from the follow-up template id alone.
`usermove_change_f1`. **Gated as a HARD KILL** on both claims: a signal produced by the scripted
stimulus is a design artefact and must never be reportable as support.

**CONTROL 6 — TURN POSITION.** Predict the change outcome from the turn index alone.
`turnpos_change_f1`. Gated as a downgrade. Turn 1 is a fresh answer and later turns are defences and
action lists, so position alone could carry much of this.

**CONTROL 7 — PERSISTENCE / THE OLD RESULT, KEPT AS A DIAGNOSTIC.** The realised no-change rate, its
per-conversation distribution, and run-length statistics. Descriptive. It is the quantity that killed
the retired design and it is reported so the pivot stays auditable.

**CONTROL 8 — READER DISPERSION AT TURN N.** For Claim 2 only, and named in advance as the **one**
extra feature permitted: whether the three T-BOARD readers were unanimous on turn N, plus the count of
distinct labels they gave it. Used only in the secondary predictor P2 (§10.3). **No other feature may
be added to either predictor.**

**CONTROL 9 — GENERATOR IDENTITY.** Predict the change outcome from the generating model's identity
alone. `generator_change_f1`. Gated as a downgrade. This is the control that catches DEFECT 1 (§5.5)
if the length fix does not fully close it.

**Fail-closed rule, binding, both claims.** If a control **cannot be computed**, its gate is **`null`**
— never `true` — and the verdict is **VACUOUS**. A kill gate must fail closed. In the retired design a
surface array initialised to `0.0` let the primary kill evaluate `(acc − 0.0) ≥ 0.05` and **silently
pass with no control computed at all.** That must never happen again. The report states this under
`gates.gates_are_null_when_uncomputable`.

---

## 10. DECISION RULE

Gates are evaluated **in order**. Gate 0 is read **before** any prediction number, and this is
enforceable, not aspirational: `--stage gate0` prints agreement and coverage only, computes no
prediction statistic, and writes its own report.

### 10.1 GATE 0 — AGREEMENT AND VIABILITY. Preregistered VACUOUS escape.

| check | threshold | constant |
|---|---|---|
| Fleiss κ, T-BOARD, 3 readers, 6 classes, **complete cases only** | ≥ **0.35** | `G0_KAPPA_MIN_BOARD` |
| Fleiss κ, T-CHANGE, 3 readers, 2 classes, complete cases only | ≥ **0.35** | `G0_KAPPA_MIN_CHANGE` |
| Fleiss κ, T-USER, 3 readers, 2 classes, complete cases only | ≥ **0.30** | `G0_KAPPA_MIN_USER` |
| complete cases available for each κ | ≥ **60** | `G0_COMPLETE_N_MIN` |
| raw pairwise agreement, complete cases, each task | ≥ `max(0.50, P_e + 0.35·(1 − P_e))` | derived |
| complete-case coverage, each task | ≥ **0.60** | `G0_COMPLETE_CASE_COVERAGE_MIN` |
| board consensus coverage | ≥ **0.70** | `G0_BOARD_CONSENSUS_COVERAGE_MIN` |
| pair (T-CHANGE) consensus coverage | ≥ **0.75** | `G0_PAIR_CONSENSUS_COVERAGE_MIN` |
| user (T-USER) consensus coverage | ≥ **0.75** | `G0_USER_CONSENSUS_COVERAGE_MIN` |
| B0 share of consensus board labels | ≤ **0.40** | `G0_B0_SHARE_MAX` |
| residual same-conversation batch collisions | = **0** | `G0_COLLISIONS_MAX` |
| analysable pairs after all filtering | ≥ **240** | `G0_MIN_ANALYSABLE_PAIRS` |
| T-USER positive control on Stratum S | ≥ **0.50** | `USER_PANEL_POSITIVE_CONTROL_MIN` |

**The raw-agreement floor is DERIVED, not asserted.** `P_e = Σ p_k²` is computed from the **observed**
marginals of each task and the binding floor is `P_e + 0.35·(1 − P_e)`, with an absolute 0.50 kept as
a second explicit floor. The report prints `P_e`, both floors, and which one bound. Stating a flat κ
floor and a flat raw floor as independent hurdles, without ever computing their joint difficulty, was
a named defect in the retired design.

> **κ IS NOT THE SAME HURDLE ACROSS THE THREE TASKS, AND THE REPORT SAYS SO.** T-BOARD is a 6-class
> task; T-CHANGE and T-USER are binary, where chance agreement is far higher and κ is a harder,
> differently-scaled statistic. A κ of 0.35 on a binary task is **not** the same achievement as 0.35 on
> a 6-class task. The report carries `KAPPA_NOT_COMPARABLE_ACROSS_TASKS` and no write-up may present
> them as one number.

**If ANY Gate 0 check fails → VERDICT = VACUOUS.** The prediction statistics are still computed and
written, so the run is not wasted, but they are **not evidence** and may not be cited. The report says
so in those words.

### 10.2 CLAIM 1 GATES — detection

| gate | requirement |
|---|---|
| **G1-1 SURFACE (PRIMARY KILL)** | `board_change_f1 − surface_change_f1 ≥ 0.05` **and** bootstrap p5 > 0 |
| **G1-2 TRIVIAL BASELINE** | `board_change_f1 − trivial_f1_bar ≥ 0.05` **and** bootstrap p5 > 0 |
| **G1-3 MCC** | `board_change_mcc > 0` **and** bootstrap p5 > 0 |
| **G1-4 PERMUTATION NULL** | `p_perm < 0.05` **and** `board_change_f1 > null_p95` |
| **G1-5 SEPARATION** | computed violation set is empty → otherwise REJECTED |
| **G1-6 USER MOVE (HARD KILL)** | `board_change_f1 − usermove_change_f1 ≥ 0.05` + p5 > 0 |
| **G1-7 TURN POSITION** (downgrade) | `board_change_f1 − turnpos_change_f1 ≥ 0.05` + p5 > 0 |
| **G1-8 GENERATOR IDENTITY** (downgrade) | `board_change_f1 − generator_change_f1 ≥ 0.05` + p5 > 0 |

### 10.3 CLAIM 2 GATES — early warning. **Gated much harder.**

Computed on the **MODEL-INITIATED subset only** (§3.1).

**Predictors, both named in advance, and no others may be added:**
- **P1 (primary):** `b_N` alone → LOCO predictor of `CHANGE` at N+1.
- **P2 (secondary, reported, not gating):** `b_N` plus reader dispersion at turn N (CONTROL 8).

| gate | requirement | vs Claim 1 |
|---|---|---|
| **G2-0 SAMPLE FLOOR** | ≥ **40** model-initiated changes **and** ≥ **150** model-initiated analysable pairs | new |
| **G2-1 SURFACE (PRIMARY KILL)** | `early_f1 − surface_early_f1 ≥ **0.10**` + p5 > 0 | **2× the margin** |
| **G2-2 TRIVIAL BASELINE** | `early_f1 − trivial_f1_bar ≥ **0.10**` + p5 > 0 | **2× the margin** |
| **G2-3 MCC** | `early_mcc > 0` **and** bootstrap p5 > 0 | same |
| **G2-4 PERMUTATION NULL** | `p_perm < **0.01**` **and** `early_f1 > null_p99` | **5× stricter, p99 not p95** |
| **G2-5 USER MOVE (HARD KILL)** | `early_f1 − usermove_change_f1 ≥ 0.10` + p5 > 0 | 2× the margin |
| **G2-6 TURN POSITION (HARD KILL here)** | `early_f1 − turnpos_change_f1 ≥ 0.10` + p5 > 0 | **promoted from downgrade to kill** |
| **G2-7 GENERATOR IDENTITY (HARD KILL here)** | `early_f1 − generator_change_f1 ≥ 0.10` + p5 > 0 | **promoted from downgrade to kill** |
| **G2-8 SENSITIVITY** | the non-pilot-only recomputation (§8.3) agrees in direction | new |

> **A CLAIM 1 PASS DOES NOT LICENSE CLAIM 2.** They are evaluated independently and reported on
> separate lines with separate verdicts. Detection is retrospective; early warning is prospective.
> Nothing about the first implies the second.

> **CLAIM 2 ON THE USER-INDUCED SUBSET LICENSES NOTHING.** It is computed, reported for contrast, and
> carries the literal label `NOT LICENSED — USER-INDUCED CHANGE IS INSTRUCTION-FOLLOWING` on its own
> line in the report.

### 10.4 VERDICTS

Per claim, using the spec-sheet vocabulary exactly (`docs/CAS_HARNESS_SPEC_SHEET.md` §3):

- **`VACUOUS`** — a precondition failed. Gate 0 failed, or a control could not be computed, or the
  Claim 2 sample floor was not reached. **The claim was never tested, rather than tested and
  rejected.** Nothing is licensed. Do not average a VACUOUS into a pass rate.
- **`REJECTED`** — Gate 0 passed and a kill gate failed.
- **`PARTIAL`** — the kill gates passed and one or more downgrade gates failed, or the non-pilot
  sensitivity disagreed. Name which part is reached and which is not. **A `PARTIAL` never licenses the
  full sentence.**
- **`HOLDS`** — all gates for that claim passed. This is the ceiling word for the output-lens group.
  It states the effect is **PRESENT** on this fixture against these nulls. **It never states the effect
  is CAS-specific**, and it may **never** be promoted to `VALIDATED` without a matched-taxonomy control,
  which is not in v1.
- **`NULL`** — a gate ran, was evaluable, and found nothing. An honest empty hand. Nulls are results
  and are kept.

No verdict is amendable after the run. No gate may be moved after seeing a number. The analyse stage
writes a **sha256 of this document and of `board_change_test.py`** into the report; it is compared
against the hash recorded when the first labelling call ran. A mismatch means this preregistration or
the runner was edited after data collection began, and **the run is not preregistered.**

**Provenance is decided by the data, not by a CLI flag.** Whether a label payload is Stratum N or
Stratum S, pilot or full, is derived from the payload itself. A disagreement with any flag **aborts the
run**. In the retired design a CLI flag decided provenance and an omitted flag wrote a false provenance
statement into a report.

---

## 11. LICENSED WORDING

If Claim 1 reaches `HOLDS`, the licensed sentence is exactly this and nothing wider:

> *"On one 80-conversation corpus written by four commercial models, a blind three-reader board lens
> applied to single assistant turns in isolation flagged a change in the kind of response at
> change-class F1 of X (base rate p, precision Y, recall Z, MCC M), above the strongest of four surface
> models reading the same two texts, above the always-predict-change trivial bar, above a
> within-conversation permutation null, above the scripted user move, above turn position, and above
> generator identity. The ground truth is an independent blind panel's judgement on the pair, not a
> fact about the model."*

If Claim 2 reaches `HOLDS`, the licensed sentence is exactly this and nothing wider:

> *"Among transitions where a blind panel reading only the user's messages judged that the user did NOT
> request a different kind of response, the board label of turn N alone predicted that the next turn
> would change kind, at change-class F1 of X (base rate p, precision Y, recall Z, MCC M, on N
> model-initiated changes), above the surface model of turn N's text by at least 0.10, above the
> trivial bar by at least 0.10, and above a within-conversation permutation null at p < 0.01, within
> one corpus of four commercial models."*

Anything beyond those sentences is outside this preregistration. Widening the sentence voids the
licence.

---

## 12. CLAIM CEILING — BINDING

1. **Output space only.** Nothing here is a measurement from inside a model. **No weights claim, no
   activation claim, no localisation claim.** The Component Atlas already returned `NULL` at 1b and
   `GREY` at 2.8b and 20B on that question, and **this test does not revisit it.**
2. **CAS-specificity stays `GREY`.** Board types may be ordinary discourse structure with a CAS name on
   them. Settling that needs a **matched-taxonomy control** — an independently constructed taxonomy of
   equal granularity, read by the same panel on the same corpus — and **that control is NOT in v1**. No
   result from this study may be described as "CAS-specific", in any wording, under any verdict.
3. **A Claim 1 pass does NOT license Claim 2**, and **Claim 2 on user-induced changes licenses
   nothing.**
4. **The ground truth is a reader judgement, not physics.** Every number here is an observed rating,
   never a voltmeter reading from a model. This is the permanent honesty ceiling and it is not
   negotiable.
5. **The base rate is ENRICHED by seed selection** (§5.4). It is not an estimate of how often models
   change board in the wild.
6. **The board panel and the change panel share the same four models.** Separation is by task and by
   call, not by model identity. A shared-model artefact cannot be excluded by this design.
7. **The board-to-board sequencing question is ours, not the framework's.** The CAS-PCBA book describes
   intra-board stage sequencing richly and inter-board sequencing not at all — Appendix D has no
   inter-board topology, the CCDL grammar has no board-composition production, and full-text search
   returns zero hits for *backplane, board-to-board, inter-board, multi-board, "the next board"*. A
   positive result may **never** be written up as "the CAS-PCBA framework predicts board changes".
8. **One corpus, one panel, four related commercial models.** That is not replication.
9. **No individual confusion-matrix cell is a result** (§7.4).
10. **Nothing here revives Claim A.** `CLAIM A — "the weights are natively CAS"` is **DEAD**, formally
    retired by the owner on 2026-08-18, and must not be revived in any external document. This study
    sits entirely inside **`CLAIM B — "CAS is a measurement and correction language"`**, which is
    **LIVE**, and it speaks to bar part 1 (reliable, non-arbitrary reading) only. It says nothing about
    bar part 2 (the algebra).

---

## 13. KILL STATEMENT

> **This line of work is KILLED if `surface_change_f1 ≥ board_change_f1` on Claim 1**, where
> `surface_change_f1 = max(S1 char, S2 word unigram, S3 length, S4 pair cosine distance)`.

That means a model reading the raw text of the two turns detects the change as well as, or better
than, the board labels do. In that case the board abstraction is a lossy re-encoding of text distance
and contributes nothing of its own. **This is not repairable** — not by relabelling, not by adding
readers, not by adding board classes, not by a better prompt. The information was never in the
abstraction. A v2 would need a different corpus and a different construct, argued from scratch.

Four further kills:

- **Instrument kill.** If T-CHANGE Fleiss κ < **0.20**, blind readers cannot agree that a change
  happened at all. There is no event to detect. This kills the change construct as an output lens, not
  merely this study, and it blocks downstream change work until repaired.
- **Ground-truth-is-surface kill.** If `ground_truth_surface_f1 > 0.667` **and** the surface battery
  also wins G1-1, the study is measuring text distance under two names. Report it and stop.
- **Design-artefact kill.** If the scripted follow-up predicts the change as well as the board label
  does (G1-6 or G2-5), the prediction is the stimulus, not the board. `REJECTED`.
- **Claim 2 specific kill.** With ≥ 40 model-initiated changes in hand, if `early_f1` does not clear
  the trivial bar and the surface bar by 0.10 with both bootstrap lower bounds above 0 and MCC above 0,
  **there is no early warning in the output lens** and the commercial claim is dead as constructed.

**Recorded dead ends that must NOT be re-attempted as repairs to this design:**
template-rendered corpora (38 strings, surface accuracy 1.0000, arm withdrawn); answer keys derived
from the same rubric the readers are given (mapping circularity, no informative range); adding more
classes to lower the random-overlap floor (the 20-part run: lift +0.231 vs +0.210, coverage 92%→58%,
7 classes unused); raising `--workers` to speed GLM up (it produces 429 storms, not throughput — the
semaphore caps GLM concurrency at 1 regardless).

---

## 14. VACUOUS ESCAPES — PREREGISTERED

Each of these means the claim **was never tested**, not that it was tested and rejected. None of them
is a failure of the hypothesis and none of them may be averaged into a pass rate.

1. **Gate 0 fails** on any agreement, coverage, B0-share, collision or pair-count check (§10.1) →
   **both claims VACUOUS**.
2. **T-USER positive control below 0.50** on Stratum S (§3.2) → the user-induced / model-initiated
   split is unmeasured → **Claim 2 VACUOUS**.
3. **Fewer than 40 model-initiated changes or fewer than 150 model-initiated pairs** (§3.3, G2-0) →
   **Claim 2 VACUOUS**. Not a repair opportunity.
4. **Pilot rate `r̂ < 0.10`** (§8.3) → stop before the full spend → **Claim 2 VACUOUS**, declared
   for the cost of the pilot.
5. **Any control uncomputable** → its gate is `null`, never `true` → **VACUOUS** (§9, fail-closed).
6. **T-CHANGE κ between 0.20 and 0.35** → VACUOUS (below 0.20 it is a kill, §13, not a vacuum).

---

## 15. COST ESTIMATE

**Call counts.**

| stage | calls, pilot (16 convos) | calls, full (80 convos) | calls at the 120-neutral ceiling (140 convos) |
|---|---|---|---|
| generation (10 turns per conversation) | 160 | **800** | 1,400 |
| T-BOARD labelling — 4 readers × ⌈(3/4 · turns)/6 per batch⌉ | 80 | **400** | 700 |
| T-CHANGE labelling — 4 readers × ⌈(3/4 · pairs)/4 per batch⌉ | 108 | **540** | 948 |
| T-USER labelling — 4 readers × ⌈(3/4 · pairs)/12 per batch⌉ | 36 | **180** | 316 |
| repair rounds (~12% of label batches, ≤ 2 rounds) | 25 | **135** | 235 |
| analyse | 0 | 0 | 0 |
| **total** | **≈ 409** | **≈ 2,055** | **≈ 3,599** |

The labelling arithmetic is `4 readers × ⌈(3/4 · items) / batch_size⌉`, because every reader labels
three-quarters of the corpus — not 3 readers labelling all of it. The retired design got this wrong
once and it is stated explicitly here.

**Money.** Scaled from the retired design's realised figures ($8–$25 for ~565 calls, i.e. $0.014–$0.044
per call across this panel's blended rates):

| run | estimate |
|---|---|
| pilot | **$6 – $18** |
| full (80 conversations) | **$29 – $90** |
| ceiling (140 conversations) | **$50 – $158** |

Token order of magnitude for the full run: **~6.5M input, ~2.2M output**. These are estimates scaled
from a prior run, not measurements, and are labelled as such in the report.

**Wall clock.** Dominated by glm-4.6, pinned to `Semaphore(1)` with a 7.0 s proactive interval. GLM
carries roughly one quarter of every stage: ~514 serialized calls on the full run at ~45–55 s each →
**6.5–8 hours**. Budget **7–10 hours**, run overnight, and treat the JSONL checkpointing as
non-optional. Worker pools are sized to the **sum of the per-provider semaphores** so a thread blocked
on GLM never starves gemini / deepseek / qwen. **Raising `--workers` does not raise GLM throughput.**

**This is roughly 3.5× the retired design's spend.** The pilot spend gate is what makes that
defensible: the single most likely way this study dies — too few model-initiated changes — is
detectable for **$6–$18** before the remaining ~$25–$75 is committed.

**Spend discipline, in order:**

1. `--stage generate --pilot`, then **eyeball three turns from each of the four generators** and check
   the per-generator median length ratio against the 3.0 flag. The retired design's smoke produced
   ~140-character gemini turns against ~3300–4000-character deepseek turns; that is visible in the
   sample line the stage prints.
2. `--stage label --task change --pilot`, then `--stage label --task user --pilot`, then
   `--stage label --task board --pilot`.
3. `--stage gate0 --pilot` — prints agreement and coverage and **no** prediction number.
4. `--stage pilot-size` — prints `r̂` and the resize rule's output. **If it prints
   `STOP — CLAIM 2 VACUOUS`, stop here.** This is the cheapest kill in the design.
5. Only then run the remainder.

**A pilot cannot PASS Gate 0**, and the reason is arithmetic, not judgement: 16 conversations yield 144
possible pairs, so at the floor coverages `144 × 0.49 × 0.75 = 52.9` analysable pairs against a floor
of 240. **The pilot is a RED-LIGHT-ONLY check.** A pilot κ near zero is enough to stop before the full
spend. A pilot `VACUOUS` is not a stop signal and must not be read as one.

---

## 16. WHAT IS NOT IN v1 — listed so it is never mistaken for a finding

1. **The matched-taxonomy control.** Without it, CAS-specificity is `GREY` and stays `GREY` (§12.2). It
   would cost one additional labelling pass on the same corpus and it is the single most valuable
   addition to a v2.
2. **A second corpus and a second panel.** One corpus with four related commercial models is not
   replication.
3. **Any weights, activation, or localisation work.** Closed by the Component Atlas arc.
4. **Set-valued board reading.** If Gate 0 fails on the B0 share or on κ, the natural next design is
   multi-label boards scored by Jaccard against a rate-preserving shuffled null, as `l2_circuit.py`
   does. The circuit reading (sets, 0.6099) beat the single-cell reading (0.5333) on the same corpus,
   so single-label forcing is a plausible failure mode.
5. **Naturalistic user turns.** Removing the scripted follow-up entirely would need a user-simulator
   model, which adds a confound and would weaken the (a)/(b) split this design is built on.
6. **Change magnitude or direction.** This study asks only whether a change occurred, never which
   board it went to. Direction is a 36-cell question at ~240 pairs and the multiplicity clause
   forbids mining it.
7. **The prescribed-turn-type hybrid** (§3.4). Available for a future Claim-1-only detection study.
   Never for Claim 2.

---

## 17. INHERITANCE FROM THE RETIRED DESIGN

`PREREG_NEXT_BOARD_V1.md`, `next_board_test.py` and `compliance_check.py` are **not modified**. They
are read for context and reuse.

**Carried forward unchanged (these were added in response to three FATAL findings and must not be
lost):**

| carried | where |
|---|---|
| surface control, **char AND word n-gram**, same task and same folds, `C` tuned inside the training fold | §9 CONTROL 1 |
| base-rate control | §9 CONTROL 2, §7.3 |
| **within-conversation** block permutation null, never global | §9 CONTROL 3 |
| generator ≠ labeller, **computed not asserted** | §6.4, §9 CONTROL 4 |
| per-batch, per-reader **alias ids** — no turn index, no conversation id ever reaches a reader | §6.4 |
| `finish_reason == "stop"`, batch-id intersection, exact-id-set completeness, repair rounds, JSONL checkpointing | §5.6, §6.4 |
| leave-one-**CONVERSATION**-out folds | §9 |
| reader-agreement floor as a VACUOUS escape, with joint arithmetic shown | §8.2, §10.1, §14 |
| paired cluster bootstrap over conversations on every gating margin | §8.4 |
| multiplicity clause | §7.4 |
| fail-closed kill gates (uncomputable → `null`, never `true`) | §9 |
| provenance derived from the data, not from a CLI flag | §10.4 |
| sha256 immutability record of prereg + runner | §10.4 |
| the six-code board rubric and its five disambiguators, verbatim | §6.1 |
| the seed-prompt bank and the "no seed reused" rule | §5.4 |

**Dropped, with the reason:**

| dropped | why |
|---|---|
| `board_acc` (LOCO Markov next-board prediction) | the claim it served is retired. Stickiness makes it uninformative |
| GATE 5 persistence comparison as a gate | persistence is now the diagnostic (CONTROL 7), not a competitor |
| the matched-taxonomy arm (CONTROL 8 / GATE 8) | out of v1 scope; CAS-specificity stays `GREY` by construction (§12.2) |
| the entire `--generator sdg` template arm | withdrawn on two named kills; template text is forbidden here (§5.1) |
| `rubric_adherence_acc`, GATE RA-1, GATE RA-2, `KILL_MAPPING_CIRCULARITY` | that arm does not exist in this design |
| accuracy as a headline | forbidden (§7.1) |

**Constants.** All constants in this design are **new names** in a **new file**. No constant, seed,
threshold or verdict of `next_board_test.py` is edited, reused by name, or overwritten. The retired
design's frozen-constants banner and sha256 record stay meaningful.

---

## 18. AMENDMENT LOG

**2026-08-19 — v1. First version of the board-CHANGE design.**
Recorded **before** any generation or labelling call under this design. **No data exists.** No corpus
has been built, no runner has been written.

Reason for the new design: the next-board test was `REJECTED` on its own smoke. Persistence (predict
the same board as the previous turn) scored **0.5238** against the Markov predictor's **0.5079**, and
the within-conversation permutation null gave **p = 0.4279**. Natural conversation is sticky, so "what
comes next" is nearly always "the same thing" and there was almost nothing to predict. That stickiness
is treated here as a finding, not a bug: it says the valuable event is the **change**, and that changes
are rare, and that rare events are where the commercial value sits.

What this version establishes, all of it before any spend:

1. **Two claims, kept apart.** Detection (retrospective) and early warning (prospective), with the
   second gated at 2× the margin, 5× the permutation strictness, `p99` instead of `p95`, and two
   downgrade gates promoted to hard kills.
2. **The user-induced / model-initiated split**, decided by a blind panel that sees only the user's
   messages, with a positive control on a deliberately-shifting stratum so the split is measured rather
   than assumed. Claim 2 is reported on the model-initiated subset only.
3. **Precision, recall and F1 on the change class as the primary metric**, with the base rate stated
   beside every figure, the confusion matrix mandatory, MCC as a co-requirement that no degenerate
   strategy can pass, and **accuracy forbidden as a headline**.
4. **A pilot spend gate and a preregistered resize rule**, so the most likely death of this study — too
   few model-initiated changes — costs $6–$18 to discover instead of $29–$90.
5. **Joint satisfiability of the Gate 0 floors shown arithmetically**
   (`720 × 0.70² × 0.75 = 264 ≥ 240`), because a prior version of the retired design set floors that
   were mutually impossible and would have produced a guaranteed `VACUOUS` after the full spend.

No gate was moved after seeing a number, because no number exists. This document and
`board_change_test.py` must be committed together so the sha256 immutability comparison stays
meaningful.

*(Any change after the first `--stage label` call must be recorded here with a timestamp and a reason.
Any gate moved after seeing data invalidates this preregistration. Using `--allow-reasoning-only`, or
any override that relaxes a floor, is a deviation and must be logged here.)*

---

## AMENDMENT A1 — 2026-08-19 — generation token budget 800 -> 4000

**Logged BEFORE the pilot run, as required. Owner-approved.**

**What changes:** `BC_MAXTOK_GEN` 800 -> **4000**. Generation only. No reader budget, no metric,
no gate, no threshold, no control and no panel design changes.

**Why.** The frozen 800 was set on a MISDIAGNOSIS carried in from the retired next-board run.
The symptom recorded as "DEFECT 1 -- a 25x generator length gap ... gemini produced ~140-character
turns" was read as a GENERATOR STYLE confound and remedied with `MIN_TURN_CHARS=200` plus
regeneration. That remedy cannot work: the true cause is that reasoning/thinking tokens are
billed against `max_tokens` but never returned, so 800 is a DETERMINISTIC ceiling and every
regeneration attempt hits the identical wall.

Measured before this amendment (~$1 of diagnostic calls, no pilot labelling):

| generator | at `max_tokens=800` | given room |
|---|---|---|
| `gemini-2.5-flash` | `finish='length'`, answer **121-131 chars**, `completion_tokens=30` | 4000 -> `stop`, **3392 chars** |
| `glm-4.6` | `finish='length'`, answer **0 chars**, reasoning 3252 chars, `completion_tokens=800` | 2000 -> `stop`, **3675 chars** |
| `deepseek-v4-pro` | passes at turn 0, fails as context grows | fine |
| `qwen3.8-max` | passes | fine |

End-to-end confirmation: an 8-conversation smoke at 800 produced **2 surviving conversations,
both `qwen`**. The other three generators produced zero.

**Why it invalidated the pilot rather than merely degrading it.** The pilot's only output is
`r̂`, which sizes the full run via `K_neutral = clamp(ceil(40/(2.98·r̂)), 60, 120)`. At 800 the
corpus collapses to a SINGLE generator, so `r̂` would not be the quantity that formula is
defined on; CONTROL 9 (generator identity) would collapse to one level; and the
generator != labeller rotation the three-panel design rests on would break.

**Direction of risk, stated in advance.** Longer turns are *a priori* easier for readers to
label and may raise agreement and coverage. That helps Gate 0 and could flatter the study.
Mitigation: Gate 0 floors are UNCHANGED by this amendment, and the realised turn-length
distribution per generator is reported so a reader can see whether length is doing work. This
amendment does not touch any gate.

**Also unchanged:** the prereg's own honest expectation that `VACUOUS` on Claim 2 remains the
single likeliest outcome, for want of model-initiated changes.
