# AUDIT_ROUNDS_32_33_RESULT — independent audit of rounds 32 and 33, and a ranking bug in the constraint layer

**Written 2026-09-18 by an auditing agent (Claude Opus 5), at the owner's request. $0.00. Pure Python on
recorded scores. No torch, no GPU, no model, no training, no new run.**

Scripts and raw outputs: `audit_rounds_32_33/`. Every number below was re-measured by independent
code. Where only one agent measured a number, this record says so.

---

## 0. What the owner ruled, 2026-09-18

Asked whether a decoder may read graph edges or the focus world out of the input, the owner answered,
verbatim: **"IT MUST BE LEARNING LEARNING AT THE NEURON LEVEL THE ARCHITECTURE SHOULD BE SERVING THIS
PURPOSE. EVERYTHING SHOULD BE SERVING THIS PURPOSE."**

Applied in this record: a gain produced by a hand-written rule over saved scores is **not** progress
of the machine. Such gains are reported separately from learned gains and are never added to them.

## 1. Round 32 — `EDGE_DIRECTION_CORRECTION.md`

**The bug and the fix are real.** `checker._edges` keeps `(source, target)` ordered; `probe_edge_reachability.py`,
re-run, prints `4 of 16`, `2 of 9` and `True` twice. No sorted edge pair remains in `records/`.

What went too far:

| claim | finding |
|---|---|
| "the correction makes the machine look better" | The fitted readout's `77.8426%` per slot is **below** always-ABSENT, `79.7862%`, on the same 1,029 slots. It finds **47 of 208** true edges (`22.5962%`); balanced accuracy `57.2177%`. The rise came from a lopsided answer key, not a better reader. `audit_rounds_32_33/r32_edge_confusion_output.txt` |
| "below chance in four of six runs" | **Six of six** (`62.7794%`–`67.3469%` against `67.7444%`). Fixed later in round 34, commit `2b16ae04`. |
| "there is no composition defect left to explain" | NOT LICENSED. 13 of 70 questions have 9 slots, so the independence prediction is `3.4289%`, not `1.82%`; and the measured rate is **1 of 70** (95% range `0.04%`–`7.70%`). |
| "`setting_ref` is worth exactly +0.0000" | True only for the analyst's fitted readout. The trained machine's own `setting_ref` accuracy is `0.0000%` (STATUS Limit 8). |
| "the fitted readout" | It is a ridge fit on the **frozen** encoder, not the trained machine. `definition 48.5714%` (fit) against `0%` (machine) compares two different things. |

## 2. Round 33 — `ALL_DECLARED_CONSTRAINTS_RESULT.md`

**Every headline number reproduces** (four independent scripts): `parts` 236/318 = `74.2138%`,
`definition` 43/420 = `10.2381%`, `edge_account` 0/420; run totals 193, 192, 200, 203, 196, 189 of 564;
`+31.00` per run; 226.5/564 = `40.1596%`. The script's decoder equals the recorded decisions `808/808`.
`r33_rerun_all_declared_constraints.txt` matches the committed output.

What the numbers mean:

1. **"Truth-free" does not mean "answer-free".** `k` equals the true answer's size in `53/53` `parts` and
   `70/70` `edge_account` questions, computed from the list the checker builds the answer from. The
   learner-visible text (`input_frames.py`, `_build`) carries every world's `contains`, `declared_whole`
   and `declarations`. A plain reader of the input scores `100.0000%` on `parts`, `edge_account`,
   `definition` and `context`. The record disclosed where `k` comes from (§1); the fault is presenting the
   result as progress on the objective.
2. **`parts` carries a real ranking signal — on practised questions only.** Within-question AUC `0.867662`.
   On equal information: count + "the whole is never its own part" + random pick = `203/318 = 63.8365%`;
   the same rules + the machine's margin ranking = `277/318 = 87.1069%`. **The machine adds +23.2704
   points.** The whole is a candidate in `318/318` questions and a true part in `0/318`.
   `r33_whole_baseline.txt`, `verify-signal-1/`.
3. **Round 32's `context` result is no better than random.** With the same count rule, the machine gets
   `137/420 = 32.6190%`; a random choice of three gets `163.5/420 = 38.9286%` (every subset enumerated).
   AUC `0.466862`, below 0.5 in all six runs. 78 of the 137 correct answers are forced by the count alone.
   No significance test; 57 unique questions per run. **FLAG_FOR_HUMAN_REVIEW.** `verify-signal-0/`.
4. **`definition` enforces half its own rule.** `FOCUS_WORLD_DECLARATION_IDENTITY` applied in full scores
   `420/420`. The arm drops "focus" and picks among 64 worlds: `43/420` against a random `1.5971%`.
   Single-agent finding (critic): alone the machine gets `function_ref` right in `0/420`; most of the
   lift is overwriting that field. `critic2/definition_fields_output.txt`.
5. **`edge_account` "no signal at all" is overstated.** AUC `0.563352`; slot position alone `0.564953`.
   Random pick with the right count: `0.6419%`. Round 34 withdrew "a constraint cannot create evidence";
   this record still said it until the banner added today.
6. **"The ingredients exist" is unsupported** (fitted readout below always-ABSENT; see §1).
7. **It conflicts with the decoder's own contract.** `slots.py` line 1: "Pure fixed-slot typed decoding,
   with no semantic teacher or learned head"; `"semantic_repair": False`; `answers.py:136`: "excludes no
   answer because of graph correctness". Counting `contains` edges is graph reading.

## 3. A bug in `cncm/answer_constraints.py`, found and fixed today

`_apply_cardinality`'s docstring says it chooses "the k best by PRESENT minus ABSENT". The committed
code (round 37, HEAD `239f1b8b`) ranked by the `PRESENT` score alone. Measured by the critic and
matching the recorded figures exactly:

| kind | PRESENT alone (recorded in round 37) | margin (correct) |
|---|---|---|
| `parts` | 257/318 = `80.8176%` | 277/318 = `87.1069%` |
| `edge_account` | 0/420 = `0.0000%` | 18/420 = `4.2857%` |

Fixed as `_margin_rank`, with a regression test (`test_cardinality_ranks_by_the_margin_not_by_present_alone`)
that fails on the old code. The whole layer re-measured with the fix: `constraint_layer_corrected.txt`
(§5). Round 37's re-assertion that a constraint "cannot create evidence" for `edge_account` rested on
this bug.

## 4. Limits of this audit

- **In-sample.** Every number is on the 564 practised questions. The new-question panel is `0/59` and
  constrained scoring there cannot be measured from these receipts.
- **About three repeats, not six.** The six runs are three model seeds × two teaching orders from the
  same start. This weakens "six for six" in the record and in this audit equally.
- 5 of 14 audit agents died on a usage limit. Their ground was covered by other agents and by the lead
  auditor, except the `definition` field breakdown and the PRESENT-alone figures, which only the critic
  measured (both match recorded numbers exactly).

## 5. The constraint layer, re-measured with the fix

`measure_constraint_layer.py` re-run with the fix, all six runs, recorded scores
(`constraint_layer_corrected.txt`; the buggy output stays in `constraint_layer.txt`):

| kind | q | unconstrained | constrained, bug (round 37) | **constrained, fixed** |
|---|---:|---:|---:|---:|
| `parts` | 318 | 29.2453% | 80.8176% | **87.1069%** (277/318) |
| `edge_account` | 420 | 0.0000% | 0.0000% | **4.2857%** (18/420) |
| `definition` | 420 | 0.0000% | 10.2381% | 10.2381% |
| `context` | 420 | 0.0000% | 4.0476% | 4.0476% |
| one-decision kinds | 1590 | 66.5409% | 66.5409% | 66.5409% |
| **many-decision** | 1794 | 6.4103% | 18.8963% | **21.0145%** |
| **all** | 3384 | 34.6631% | 41.2825% | **42.4054%** |

Per run, all: 193→231, 192→229, 200→255, 203→250, 196→236, 189→234 of 564.

**By the owner's ruling (§0) this is a rule-layer gain on saved scores, not progress of the machine.**
It is reported here only so the record of the layer is correct. It is never to be added to a learned
gain.

## 6. Claim status

- **REAL:** all headline numbers of rounds 32 and 33; `parts` ranking signal (+23.2704 points on equal
  information, practised questions); the ranking bug and its cost.
- **NOT LICENSED:** `+31` per run; "the mean moves to 40.16%"; "useful as rankings" as a general rule;
  "no signal at all"; "the ingredients exist"; "no composition defect left".
- **FLAG_FOR_HUMAN_REVIEW:** round 32's `context` result (`32.6190%` against a random `38.9286%`).
- **WITHDRAWN** (by this audit, of its own sub-claim): "`OPEN` is not a status word" — the spec-sheet
  legend §3 lists `OPEN`.
