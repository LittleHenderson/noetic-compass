# Retained-evidence review + retrospective endpoint containment — recommendation 001

Status: **READ-ONLY WORK COMPLETE.** No training, no reservation, no neural
execution was performed for this record. `VARIED_CURRICULUM_NOT_ESTABLISHED` and
all 18 checkpoint files are preserved unchanged.

## 1. Retrospective endpoint containment (recovers part of the missing gate)

Tool: `tools/graph6_checkpoint_containment.py` — pure Python standard library (no
torch, no GPU). A `torch.save` file is a ZIP archive: `data.pkl` plus raw storage
buffers. The object graph is unpickled with stand-ins for the torch classes, so
each stored tensor keeps its parameter name, shape and storage offset, and its
bytes are hashed from the raw buffer.

Evidence: `RETROSPECTIVE_CONTAINMENT_001.json` (sha256
`989ec28253108ad6011ba88c6403d64122595476c2357be2ea58079fb8f27199`), 18/18
checkpoints read, 6/6 learners compared.

| Finding | Value |
| --- | --- |
| Components stored in every checkpoint | `model.left.weight`, `model.right.weight`, `model.merge.weight`, `encoder.projection` |
| Components that changed by 256 updates | **only those three model matrices** |
| Encoder projection | **byte-identical in all 18 checkpoints** — sha256 `116f3677d343db7cd9becbb0b293c4419d5f455b9e1044e33dbd6738ed1468cb`, which is exactly the `encoder_identity` the run reported (an independent cross-check of the run's own record) |
| Tokenizer vocabulary | identical across all 18 checkpoints |
| Optimizer state entries | 0 at step 0; 3 at steps 64 and 256 (one per matrix) |

**This is the retrospective endpoint comparison the owner asked for, and it is
evidence rather than an argument.** Its limits, stated in the file itself:

* it cannot show *when* between endpoints a change happened (no intermediate state
  was saved);
* it cannot speak to any component that was never written to a checkpoint — for
  example the other operation modules a `RegisteredOperationBank` constructs
  alongside decompose. Those were never saved, so they are **unverifiable from the
  retained files**, not "unchanged";
* it is **not** the registered digest-level containment report, and attempt 004
  must not be described as satisfying every registered evidence requirement.

## 2. Read-only review of the retained predictions

Tool: `tools/graph6_retained_evidence_review.py`; evidence
`RETAINED_EVIDENCE_REVIEW_001.json` (sha256 `823dff222ea2a4283268aa96ca6092a2526fa9512f9731a1075e56241cfdb65e`).

**What the retained per-case fields actually contain**

| Pass | Fields stored |
| --- | --- |
| fresh (90 cases) | `correct`, `family_id`, `op`, `predicted`, `record_id` |
| practice / own-curriculum (30 records) | `correct`, `op`, `record_id` — **no predicted option** |

**Own-curriculum accuracy by the variation each lesson was built with** (pooled
over the six learners; `none` = the control's unvaried lessons):

| Variation | Correct |
| --- | --- |
| consistent renaming | **9/9 (100 %)** |
| harmless reordering | **42/45 (93.3 %)** |
| answer-changing rewiring | **30/36 (83.3 %)** |
| control lessons (no variation) | 69/90 (76.7 %) |

So the varied learners did follow the relationship on their own practised cases,
including the cases where a connection had been moved (83.3 %). Each varied record
is nevertheless a *different graph*, so this is record-level evidence, not the
controlled contrast the owner specified.

**Fresh panel (unseen arrangements), pooled over six learners — the sharpest
finding in the whole investigation**

| Operation | Correct | Chance |
| --- | --- | --- |
| `LIST_PARTS` | **23/180 (12.8 %)** | 33.3 % |
| `FIND_SHARED_PART` | 71/180 (39.4 %) | 33.3 % |
| `REACHED_VIA` | 62/180 (34.4 %) | 33.3 % |

By condition, and at both endpoints:

| Condition | `LIST_PARTS` @64 | `LIST_PARTS` @256 | `FIND_SHARED_PART` @256 | `REACHED_VIA` @256 |
| --- | --- | --- | --- | --- |
| control | 13/90 (14.4 %) | **5/90 (5.6 %)** | 42/90 (46.7 %) | 27/90 (30.0 %) |
| varied | 21/90 (23.3 %) | **18/90 (20.0 %)** | 29/90 (32.2 %) | 35/90 (38.9 %) |

`REACHED_VIA` by label (pooled): direct 32/60 (53.3 %), absent 17/60 (28.3 %),
via 13/60 (21.7 %).

## 3. Missing measurements (explicitly unavailable)

1. **Predicted option strings for practice and own-curriculum passes** were not
   stored, so the rename / reorder / rewire contrasts on correctly answered
   practice cases cannot be recovered from the delivered result.
2. The **trained-learner contrasts themselves** (a practice case vs its renamed,
   reordered and rewired variants) were never run.
3. Per-option scores or logits: only the argmax was stored.
4. The intermediate training history between steps 0, 64 and 256.
5. Any component never written to a checkpoint (see §1).
6. The tokenizer artifact itself: only its vocabulary list is inside the
   checkpoints.

## 4. The bounded unit that would close the gap (prepared, NOT authorized)

`cas_meta2/graph_teaching/contrast_probe.py` + `tests/test_graph_training_contrast_probe.py`
(9 tests, pure Python). For each practice case a retained learner answered
correctly it builds four contrasts from the stored graph with the deterministic
checker — `original`, consistently `renamed` (graph, question, options and answer
renamed together, with a validation that the answer is the renamed original),
`reordered`, and `rewired` (one connection moved, answer recomputed) — and records
which option the frozen learner selects. **Zero optimizer steps.** It also records
an option-length reading for list questions, because the numbers in §2 make an
option-length bias a live hypothesis.

This is one bounded measurement unit over the 18 retained checkpoints, **not** a
series of diagnostics and **not** a retraining run. No launch or reservation is
requested in this record.

## 5. One evidence-based recommendation

**Measured defect (evidence, not hypothesis):** on unseen arrangements,
complete-part-list selection is **far below chance** — control 5/90 (5.6 %) and
varied 18/90 (20.0 %) against a 33.3 % chance level — while the same learners
answer their own list lessons at roughly 90 %. The control's score *falls* from
14.4 % at 64 updates to 5.6 % at 256. Below-chance performance on a three-option
choice means the learner is **systematically selecting the wrong kind of option**,
not failing at random. `FIND_SHARED_PART` (46.7 % for the control) shows the
system can do better than chance on the same panel, so this is specific to the list
task rather than general incapacity.

**Hypothesis (explicitly not measured):** the bias lives in the **option readout**
rather than in the problem encoding — the option vectors are sum-pooled token
embeddings, so a longer option (and one sharing more tokens with the graph) grows
in norm and can dominate the dot-product score. `LIST_PARTS` options are the only
ones that are *lists*, which is exactly where the collapse appears.

**Smallest next change I recommend:** do **not** raise the allowance and do not
redesign the curriculum again. First run the bounded zero-update contrast unit
above (one job, no training) to measure whether the list failure follows
renaming, follows rewiring, or follows option length. If — and only if — it
reproduces as an option-length/readout effect, the smallest fix is a
**length-normalized or per-slot readout**, which is a scoring change to the frozen
candidate, not a curriculum change. If instead the failure follows rewiring, the
readout hypothesis is dead and the problem is upstream in the module or the
encoding. Either outcome constrains the next design choice far better than another
blind increase in updates.

**Not recommended now:** increasing the teaching allowance, another curriculum
redesign, or promoting this specialist into child-call integration — none of which
is supported by the delivered evidence.
