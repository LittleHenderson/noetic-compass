# Analogy wiring probe v0.3: rules fixed before any trained-checkpoint reading

- **Status:** `PROPOSED`
- **Written by:** Claude, as builder of readout item "probe-v03", on 2026-09-24. Labels:
  `CLAUDE_BUILT_CLAUDE_CHECKED`; `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT`.
- **Written when:** while repaired seed 20260917 (R17) trains. No version of the probe has read any trained
  switch-ON checkpoint. No repaired-arm analogy number has been opened. The unit controls in section 8 use only
  synthetic, pure-Python scorers.
- **What it replaces, for the 18 mechanism checks only:**
  `../../analogy_wiring_probe/PREREG_ANALOGY_WIRING_PROBE_v0_2.md`. Its amendments A5.1 to A5.3 name "probe v0.2".
  Section 10 proposes the one-line change. v0.2 and all its receipts stay unchanged, as historical diagnostics.
  They are **not** counted toward the corrected gate (design v0.4 amendment A2.6).
- **Why it exists:** Codex's design v0.4 amendment A2.6 (`../../EVALUATION_DESIGN_v0_4.md`, commit `c3a128ee`)
  and `../../../helm_controlled_prelaunch_20260924/ROUTE_AND_CHECKPOINT_PROTOCOL.md`. Both say that probe v0.2
  cannot close the repaired mechanism gate. The metric below is Claude's default Q-E, sent to Codex as bus message
  `claude-0024` (2026-09-24T13:40:35Z). Codex has not answered it yet.
- **What makes it binding:** nothing yet. It becomes the rule for the 18 checks only after an acceptance record
  (section 9) binds the hashes of this file, the metric and the harness. Until then, `item2_reader.py` prints
  `MECHANISM_GATE_OPEN` with the reason `PREREG_V0_3_NOT_ACCEPTED`, whatever the probe reads.

## 1. The claim being checked (unchanged from v0.2)

"Changing the arrangement Helm is asked to compare can now affect the relevant answer scores."

- **Relevant** means that the change can alter **which candidate world wins**, or **whether any world beats
  NO_MATCH**.
- A shift that adds the same amount to every candidate's score is **not** relevant.
- Correct answers are a later, separate test. This probe reads no gold answer.

## 2. The two defects of v0.2

1. **Normalization.** v0.2 turned scores into z-scores (distance from the group average, in units of the group's
   spread). It recomputed the average and spread after every change. In the bystander test, the changed world
   stayed inside the group. So when that world's own score moved, the average and spread moved, and every other
   candidate's z-score moved with them, even when their raw scores did not change at all.
   - Public evidence (`../../aws_probe_job/results/before_reading_v0_2_T4_seed20260917.json`, commit
     `dfe15fa6`). Unchanged Helm 2.0, seed 20260917, T4. Changing the focus moved nothing (`max_M3z` 0.0). Yet
     the bystander leak L read 0.0112065225747362 to 0.04736953181640158 on the fresh and initial models, and
     0.02427044721255378 to 0.14733683224369587 on the trained final. Helm computes each world's vector from that
     world alone (`_rounds` in `pointer_learner.py`), so those numbers are the normalization, not a coupling.
   - The same defect can hide a real coupling. If changing one world rescales **every** candidate's score the same
     way, re-standardising removes it. v0.2 then reads no leak (section 8, control 5b).
2. **Direction.** v0.2 scored its set contrasts by their absolute size. Movement **away** from the worlds that
   now match passed as easily as movement toward them (section 8, control 4).

## 3. Definitions (v0.3)

Per analogy record r: frozen course `272c26e1...`, 70 records, 24 distinct focus worlds, as in v0.2.

- **Scores.** `s_c` is the logit of candidate world c in the record's single `world_id` slot, read in float64.
  `NO_MATCH` is pinned at 0 by the model. `s0` is the score in the **unchanged** packet.
- **X:** the cross-domain non-focus candidates. **X_all:** every non-focus candidate.
- **Counterfactuals (unchanged from v0.2, with its amendment A1):**
  - graph: the focus is rewired to each alternative shape of its node count, except its own shape;
  - bystander: the first (sorted) world in X with the focus's node count, rewired to each alternative except its
    own shape;
  - domain: the focus's `domain` declaration is replaced by each other bank domain.

  Each counterfactual packet is read by the learner's own `pointer_inputs.read_packet`. The slot plan comes from
  the unmodified packet. Every focus copy in a focus-changed reading is asserted consistent.
- **Changed world w:** the focus for graph and domain counterfactuals; the bystander b for bystander
  counterfactuals.
- **Reference set R:** the candidate set with w removed. For graph changes R = X. For bystander changes
  R = X without b. For domain changes R = X_all.
- **Reference spread:** `sigma0(R)` = population standard deviation of `s0` over R. It comes from the **unchanged**
  packet, is computed once, and is never recomputed from a counterfactual.
- **Shared shift:** `shift = median over R of (s_c - s0_c)`. w is never in R. So w's own movement can never enter
  another candidate's value. One moved candidate cannot move the median of 3 or more.
- **Residual:** `res_c = (s_c - s0_c) - shift`, read in units of `sigma0(R)`.
- **Permitted transformation:** `s -> a*s + b`, with `a > 0` fixed for one model and `b` free for every packet.
  `b` may depend on the focus and on the counterfactual. Every scored quantity below is unchanged by it.

| Id | What | Unit |
|---|---|---|
| M0 | **Noise gate.** Each record's base forward runs twice. `delta0_z` = max over records of `max_c |s - s'|` divided by that record's `sigma0(X)`. The raw logit value is reported too | z |
| M1z | The witness pair (A7), as v0.2: each record standardised over the shared cross-domain set of its own unchanged packet; max `|z_A - z_B|`; Kendall discordant fraction reported | z |
| M2z | As v0.2: records grouped by focus domain; for each (group, candidate), the spread of its within-record z; the maximum | z |
| M3z(f) | max over graph alternatives of `max_{c in X} |res_c| / sigma0(X)` | z |
| K(f) | max over graph alternatives of the Kendall discordant-pair fraction on X, on **raw** scores (the same numbers as v0.2's) | fraction |
| RC(f) | **Signed.** Mean over the graph alternatives whose old and new accepted sets are both non-empty of `(mean_{A'} (s - s0) - mean_{A} (s - s0)) / sigma0(X)`. A = X worlds isomorphic to the old focus shape (they stop matching); A' = X worlds isomorphic to the new shape (they start matching). A correct comparison makes it positive | z |
| L(f) | **Bystander.** max over bystander alternatives of `max_{c in X \ {b}} |res_c| / sigma0(X \ {b})` | z |
| M5 | Change in `max_{c in X} s_c` per graph alternative, in logits and in `sigma0(X)` units; reported, not scored | logits, z |
| RC_dom(f) | **Signed.** Mean over the domain alternatives of `(mean_{start} (s - s0) - mean_{stop} (s - s0)) / sigma0(X_all)`. start = focus-shape isomorphs in the OLD focus domain (they start being answers); stop = focus-shape isomorphs in the NEW focus domain (they stop). A correct comparison makes it positive | z |

**Reported, not scored:** top-1 changes under the slot's decision (the argmax, NO_MATCH pinned at 0, a tie with
NO_MATCH counted as NO_MATCH); per-alternative values; the shared shifts; timings; GPU telemetry.

## 4. Frozen numbers

These are in `probe_v0_3_metric.RULES`. A reading made with any other values prints `rules_are_frozen: false`,
and the ITEM2 gate stays open.

- `tau` = 1e-5 (z).
- noise limit = 1e-6, in z units of each record's own `sigma0(X)`.
- `effect_floor` = max(1e-3, 100 * `delta0_z`) (z).
- `rc_min` = +1e-2 (z), **signed**.
- share = 22 of the 24 distinct foci; 70 records and 24 foci are required, or the table is refused.
- bystander limit: `L(f) <= 0.1 * M3z(f)`.
- |X| >= 4 for every focus, so that |X without b| >= 3 and the median shift is exact. The real bank has |X| = 48.
- Graph alternatives: v0.2's frozen list, unchanged:
  - 4 nodes: `((0,1),(0,2),(0,3))`, `((0,1),(0,2),(1,3),(2,3))`, `((0,1),(1,2),(2,3))`, `((0,1),(0,2),(3,1))`,
    `((0,1),(0,2),(1,3))`;
  - 3 nodes: `((0,1),(1,2))`, `((0,1),(0,2))`, `((0,2),(1,2))`, `((0,1),(0,2),(1,2))`.
- Witness pair: v0.2's, unchanged: `typed-input-092dc3b8...` and `typed-input-0df25be3...` (full ids in `RULES`).

## 5. Verdicts, per model

Read by `probe_v0_3_metric.evaluate`. The first row that applies wins.

| Verdict | Condition |
|---|---|
| `INVALID_NONDETERMINISTIC` | `delta0_z` > 1e-6 |
| `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` | M1z <= tau AND M2z <= tau AND every M3z(f) <= tau AND every K(f) = 0 |
| `PRESENT_GRAPH_AND_DOMAIN` | K(f) > 0 on >= 22 foci AND M3z(f) >= effect_floor on >= 22 foci AND median RC >= +1e-2 AND L(f) <= 0.1 * M3z(f) on >= 22 foci AND RC_dom(f) >= +1e-2 on >= 22 foci |
| `PRESENT_GRAPH` | the same, except the RC_dom condition fails |
| `COUPLED_NOT_COMPARISON` | the K, M3z and signed RC conditions hold; the bystander condition fails |
| `MOVES_AWAY_FROM_FAVOURED_SET` | the K and M3z conditions hold and median RC <= -1e-2 (new in v0.3) |
| `MIXED` | anything else |

- A quantity that cannot be computed (for example a zero reference spread) is recorded as undefined, with its
  reason, and counts as not meeting any condition.
- A table that is incomplete, has extra or missing counterfactuals, the wrong candidates, a non-finite score or the
  wrong witness pair is **refused** (`TableRefused`). A refusal is not a verdict on the model.

## 6. Validation on the real harness, before any of the 18 reads (E1a, T4)

- **Container:** one fresh container of the repaired package, seed 20260917, switch OFF
  (`{"analogy_focus_comparison": false}`, `--switch-expect false`). The switch-OFF container reproduced Helm
  2.0's preservation digests bit for bit on a T4 (`OFF_PRESERVED_ON_T4`, amendment A4), so it stands in for
  unchanged Helm 2.0.
- **Command:** `probe_v0_3_harness.py validate`. The five raw cases wrap `GraphForward._world_scores` **in memory**.
  The `pointer_learner.py` hash is taken before and after, and it must not change.

| Case | What is added to candidate c's logit (float64) | Pass condition |
|---|---|---|
| V1 `CONTROL_UNWRAPPED` | nothing | `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT`, and every L(f) <= tau |
| V2 `POSITIVE_COMPARISON` | `-2 * L1(degree histogram(focus), degree histogram(c)) - 2 * [same domain as focus]` | `PRESENT_GRAPH_AND_DOMAIN`, every L(f) <= tau, median RC >= +1e-2 |
| V3 `ANTI_COMPARISON` | the V2 terms with the sign flipped | `MOVES_AWAY_FROM_FAVOURED_SET`, median RC <= -1e-2, RC_dom(f) <= -1e-2 on >= 22 foci |
| V4 `NEGATIVE_UNIFORM` | `3 * (focus edges + focus nodes)`, the same for every candidate | `FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT` |
| V5 `NEGATIVE_COUPLED` | `0.5 * <mean degree histogram over ALL worlds, histogram(c)>` | NOT `PRESENT_GRAPH` and NOT `PRESENT_GRAPH_AND_DOMAIN` |
| V6 `INJECTED_INTERACTION` | derived from V1 in pure Python: +0.5 on one fixed other candidate (the first of X without b) in every bystander run | for every focus, `|L(f) - 0.5 / sigma0(X \ {b})| <= tau`; no other scored quantity moves |
| V7 `AFFINE_INVARIANCE` | derived from V2 in pure Python: `s -> 3.0*s + b(packet)`, b in [-4, 4] and different for every packet | the same verdict as V2; every scored quantity within relative 1e-9 |

- **Pass:** every row passes, and the source hash is unchanged. The program is
  `probe_v0_3_metric.evaluate_validation`, which `item2_reader.py` re-runs on the raw tables.
- **Failure:** the probe is not fit. The 18 reads do not start. The mechanism gate reads `MECHANISM_GATE_OPEN`.
  The failure is reported, not re-read.
- V1 is expected to read exactly 0 for every L, because each world's vector is computed from that world alone. The
  pass limit is tau, not 0, so that last-bit GPU arithmetic cannot fail it. The exact values are recorded.

## 7. ITEM2 (A5.2, restated for v0.3)

- **The 18 registered checkpoints:** seeds 20260917, 20260918 and 20260919, each with `pass_01.pt` (147 main
  updates), `evidence/main_checkpoint_0294.pt` (294), `_0588` (588), `_0882` (882), `_1176` (1176) and `final.pt`
  (1,470). This is the list in `EXECUTION_MANIFEST.json` `mechanism_checkpoint_checks` (commit `c3a128ee`).
- **Each entry binds** the receipt root, the checkpoint sha256 from the receipt inventory, the update count, and the
  score table's file sha256. The table's own `model.checkpoint_sha256` must equal the bound sha256. The switch must
  read `true`. The table must carry the hashes of this prereg, the metric and the harness.
- **Outcome, read by `item2_reader.py` from the raw tables:**
  - `ITEM2_NOT_READ_PROBE_NOT_VALIDATED` if the section 6 validation did not pass;
  - `ITEM2_INVALID` if any reading is `INVALID_NONDETERMINISTIC`;
  - `ITEM2_PASS` iff all 18 read `PRESENT_GRAPH_AND_DOMAIN`, with no binding problem;
  - `ITEM2_FAIL:<seed>/<checkpoint>=<reason>,...` otherwise. A missing entry, a hash mismatch, a refused table or
    any other verdict is a failure. Every failure is listed and kept.
- **A checkpoint that does not pass:** its analogy numbers are withheld as `ANALOGY_NOT_READ_WIRING_ABSENT`. Its
  non-analogy numbers are still read, as regressions.
- **Mechanism gate:** `CLEARED` only when all of these hold: `ITEM2_PASS`; `VALIDATION_PASS`; frozen rules;
  matching provenance on every table; a valid acceptance record (section 9). Otherwise `MECHANISM_GATE_OPEN`,
  with every reason printed.
- **When the gate is open:** the confirmatory claim `REPAIR_IMPROVES_ANALOGY_6` reads `MECHANISM_GATE_OPEN`. Only
  the non-analogy H1/H2 view (13 and 40 questions) may be reported, labelled exploratory (default Q-J,
  `claude-0024`). The historical gate on the repaired arm reads `G_LEARN_ON_NOT_READ` (A5.3).
- **Not covered here:** the A5.5 matched-start check. It is a separate program, and it is still required before any
  repaired number is compared with Helm 2.0.

## 8. Pure-Python unit controls (no torch; run once on the laptop)

`test_probe_v0_3.py`, on the synthetic bank in `toy_bank.py`. The bank has 64 worlds, |X| = 48, 24 foci and 70
records. Its scores are exact binary fractions. Every table goes through the real
`probe_v0_3_harness.build_score_table`, and every scorer reads each world's shape and domain from the packet it is
handed. The five acceptance controls:

1. A scorer in which each candidate depends only on itself (and on the focus) gives a bystander interaction of
   **exactly 0**. The same table read by v0.2's own functions gives a non-zero leak.
2. An interaction of size k injected between the bystander and one other candidate reads **exactly
   |k| / sigma0(X \ {b})**, for k = 0.5, -0.25 and 3.0. Nothing else moves.
3. `s -> a*s + b(packet)`, with a = 3.0 and a = 0.125, leaves **every verdict** unchanged, and every scored
   quantity within relative 1e-9.
4. The signed test: a real comparison reads median RC > 0 and `PRESENT_GRAPH_AND_DOMAIN`. The sign-flipped scorer
   reads median RC < 0 and `MOVES_AWAY_FROM_FAVOURED_SET`. v0.2 reads **that same sign-flipped scorer** as
   `PRESENT_GRAPH_AND_DOMAIN`. A right-graph, wrong-domain scorer reads `PRESENT_GRAPH` under v0.3; v0.2 reads it
   as `PRESENT_GRAPH_AND_DOMAIN` too.
5. v0.2's normalization confound no longer passes:
   - (a) a real comparison in which a candidate's own score jumps when its own graph takes a shape the bank never
     shows (in the bank, as in the real one, that happens only to three-node bystanders). v0.2 reads it as
     `COUPLED_NOT_COMPARISON`, although no other candidate's raw score moves. v0.3 reads `PRESENT_GRAPH_AND_DOMAIN`
     with L exactly 0;
   - (b) a coupling that rescales every candidate when a bystander changes. v0.2 reads no leak and passes it as
     `PRESENT_GRAPH_AND_DOMAIN`. v0.3 reads `COUPLED_NOT_COMPARISON`.

The same file also tests: the no-dependency and coupled controls; the noise gate; table refusals; that the harness's
counterfactual packets carry the intended change and leave the originals untouched; the validation reader on the
synthetic controls; and every ITEM2 outcome. The single run's output is kept in `unit_controls_run.log`.

## 9. The acceptance record (what makes v0.3 binding)

A JSON file with this content:

```
{"schema": "claude.probe-v0.3-acceptance/0.1", "accepted_by": "codex" | "owner",
 "prereg_sha256_lf": ..., "metric_sha256_lf": ..., "harness_sha256_lf": ...}
```

- The hashes are the LF-normalised sha256 of this file, `probe_v0_3_metric.py` and `probe_v0_3_harness.py`.
- Claude does not write this record. `item2_reader.py` checks the hashes. It cannot check who wrote the file, so
  the record must be committed by its author.

## 10. Proposed amendment to v0.2's A5.1 to A5.3 (`PROPOSED`)

"In A5.1, A5.2 and A5.3 of `PREREG_ANALOGY_WIRING_PROBE_v0_2.md`, read 'probe v0.3
(`readout/probe-v03/PREREG_ANALOGY_WIRING_PROBE_v0_3.md`)' where they say 'probe v0.2'. A5.2's outcome words are
kept, and section 7 of v0.3 adds `ITEM2_NOT_READ_PROBE_NOT_VALIDATED`. A5.4 to A5.6 are unchanged. The v0.2 fresh-ON
and switch-OFF readings stay as recorded, as historical diagnostics."

- It is proposed here and not written into the v0.2 file, which stays unchanged.
- It takes effect with the acceptance record in section 9.

## 11. Where it runs, limits, custody

- **Device:** an AWS GPU. A T4 (`g4dn.2xlarge`) is acceptable. It runs inside E1a, after U17 frees the GPU quota.
  Every invocation exits `GPU_REQUIRED` without CUDA. There is no CPU fallback. It is never run on the laptop.
- **Work:** forward passes only, under `no_grad`. No optimizer, no update, no checkpoint written.
- **Limits per invocation (v0.2's):** at most 3 models; a 3,600 s wall; admission at or below 75 C with at least
  2,048 MiB free; a stop at 80 C, checked every 10 forward groups; no automatic retries.
- **Side files:** the launcher must bundle `probe_v0_3_metric.py` and this file beside `probe_v0_3_harness.py`.
  The harness checks both before it imports torch.
- **Inputs:** only the public typed course: 70 analogy records and 24 focus worlds. No HSET-2 material, no eval
  split, no gold answer, no sealed file.
- **Counterfactual worlds:** only the 3- and 4-node shapes listed in section 4. They should be listed in the design
  v0.4 section 8 custody manifest before any TEST reading.
- **Reading order (A5.1 / A5.3):** no analogy number from a repaired checkpoint is opened before its v0.3 reading.
  The probe itself reads analogy-slot logits, not answers and not correctness.

## 12. Changes from v0.2, listed

- **Changed:**
  - the fixed reference spread, with the changed world left out;
  - the median shared shift;
  - signed RC and RC_dom;
  - the new verdict `MOVES_AWAY_FROM_FAVOURED_SET`;
  - the noise gate is now in z units. v0.2 compared a logit-unit `delta0` with z-unit floors;
  - K is computed on raw scores. It gives the same values as v0.2;
  - the metric is a pure function, separate from the torch harness;
  - table refusals; undefined quantities recorded with a reason;
  - top-1 ties are broken in sorted order (report only).
- **Unchanged:** the claim; the graph alternatives and their relabelling; the bystander rule; the domain
  alternatives; the witness pair; M1z; M2z; tau; `rc_min` as a size; the share of 22; the 0.1 leak ratio; the
  effect-floor minimum; the slot plan and reader route; the device limits.

## 13. Known limits, disclosed

- The median shift attributes a single moved candidate exactly. An interaction that moves more than half of R by the
  same amount is partly absorbed. It is still detected unless it is a uniform shift, which section 1 excludes.
- A rescaling that depends on the packet (a temperature that changes with the focus or the changed world) is not a
  permitted transformation. It reads as movement. Only a scale fixed for the whole model is permitted.
- V6 and V7 are arithmetic on real tables, not separate forward passes.
- One bystander per focus (v0.2's rule), not every same-size world.
- The validation container is fresh and untrained.
- A pass says that the scores respond to the focus in the registered direction, and that no bystander coupling was
  detected. It is not an accuracy result. It does not show that the model compares graphs the way the checker does.
