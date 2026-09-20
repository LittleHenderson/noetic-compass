"""The pointer machine's learner: ONE container, a node-level readout, and its own gradient gate.

WHAT THIS MODULE IS. `PointerCourseLearner` is the typed_pointer_001 study's learner. It is NOT a subclass
of `learner.TypedCourseLearner`: the shared class freezes every parameter outside the `^6` allowlist
(`graph_teaching/trainer.py:86-87`), demands a finite gradient on EVERY parameter of `self.module`
(`learner.py:271`) while zeroing with `set_to_none=True` (`learner.py:185`), and restricts AdamW to the
three `^6` tensors (`learner.py:107`). Three independent refusals, each fatal to a multi-head container
(review RK1, RK2; `INTERFACE_SPEC_SHARED.md` GOTCHAS 1 and 15). It mirrors the shared PUBLIC contract
instead, so `cncm/typed_pointer_worker.py`'s helpers keep working unchanged: `__init__`, `predict`,
`stage_batch`, `train_sealed_batch`, `export_checkpoint`, `restore_checkpoint`, `profile`, and the
attributes `torch`, `module`, `optimizer`, `encoder`, `counters`, `cursor`, `model_revision`, `failed`,
`run_identity_digest` (plus `limits`, `device`, `framework`, `_pending`, `_started`, `_elapsed_before`,
which `restore_checkpoint` and `_budget` read -- `INTERFACE_SPEC_SHARED.md` C.4). The joint correspondence
loss is NOT re-implemented: `TypedCourseLearner._tensor_loss(self, ...)` is CALLED, which is sound because
that method reads only `self.torch` (`INTERFACE_SPEC_SHARED.md` C.2).

Importing this module performs no numeric work: `torch` is imported only inside functions that are called,
exactly as the `reader` and `contract` modules in this package already do it.

ONE CONTAINER. `self.module` is a single `nn.Module` holding every learned weight, the registered `^6`
block included, and `graph_teaching.scope_parameters` is NEVER called on it. The three `^6` tensors keep the
exact names `left.weight` (64x64), `right.weight` (64x64) and `merge.weight` (64x128) that
`learner.PARAMETER_SHAPES` registers, because they are installed by `register_parameter` rather than as a
child module. `restore_checkpoint` compares the MODULE-LEVEL `profile()` over a transitive list of 22 files
(`learner.py:336`, `learner.py:30-38`, `slots.profile()`, `course.profile()`), so this module ships its own
`profile()` and its own file list and must never be expected to reproduce `learner.profile()`'s values
(`INTERFACE_SPEC_SHARED.md` GOTCHA 2).

=========================================================================================================
THE READOUT -- the reason this file exists (REVIEW_SYNTHESIS.md section 5.5)
=========================================================================================================

MEASURED, and quoted exactly as reported. With node features drawn randomly per node and mean pooling to the
world vector `g_w`:
    inter-shape distance 0.831003   intra-shape distance 1.213181   ratio 0.68
Two worlds with DIFFERENT shapes sit 0.831003 apart while two draws of the SAME shape sit 1.213181 apart, so
different shapes are closer together than same-shape samples. Nearest-centroid over 123 samples recovers 8 to
13, against a chance level of 20.5. The graph content of the pooled vector is 3-8 % of its norm, rising only
to 13-16 % with the real flag dimensions. The node states, by contrast, DO carry the wiring: the mean cosine
gap between EDGE pairs and NON-edge pairs is 0.388418 at 4 rounds (0.585565 against 0.197146) and 0.340409 at
8 rounds (0.835563 against 0.495154).

WHAT THIS MODULE DOES ABOUT IT, in two parts.

1. STRUCTURAL ANSWERS ARE SCORED AT THE NODE LEVEL, never after pooling. The `correspondence`
   `mapping_target` head and the `reach` `VIA_<node>` head take their logits from node states through a
   learned pointer key, and no pooled vector reaches either of them. The `parts` / `context` membership heads
   and the `edge_account` head also read node states, so every answer that is a claim about the focus world's
   own structure is read where the structure is.

2. THE WORLD-LEVEL HEADS ARE CONDITIONED ON THE POOLED MEAN **PLUS EXPLICIT DEGREE FEATURES** AND A LEARNED
   ATTENTION POOL. That is a deliberate choice among the candidates the review listed (degree features,
   rank-sorted concatenation, attention pooling). Justification, in one sentence: because
   `REVIEW_SYNTHESIS.md` section 4.5 records that the sorted (in-degree, out-degree) multiset is a COMPLETE
   isomorphism invariant on this corpus -- 0 of 2016 non-isomorphic pairs are indistinguishable under any of
   the four colourings tested (`DESIGN_REVIEW_LEARNABILITY_LENS.md` [LB3], [LB7]) -- the exact degree SUMS
   (not degree means) carry everything mean pooling destroys at a ratio of 0.68 (0.831003 against 1.213181),
   so the world head is handed the invariant itself instead of being asked to recover it from a
   feature-dominated blur. The world vector is mean ++ max ++ four degree/flag features ++ a learned
   attention pool, projected to WIDTH. An `analogy` answer is isomorphic AND different domain in 17 of 17
   held records, so each candidate world's four declaration fields are embedded separately and concatenated
   into that candidate's score: the world scorer sees BOTH the domain text and the shape.

`UNCERTAIN:` that this readout separates two DIFFERENT shapes by more than two draws of the SAME shape is NOT
asserted here; it is a measurement this file does not run. `REVIEW_SYNTHESIS.md` section 5.5 point 4 registers
that smoke test as the guard against this class of failure returning, and it is the worker's.

=========================================================================================================
NORMALISATION PLACEMENT (REVIEW_SYNTHESIS.md section 5.6)
=========================================================================================================

RMS normalisation is applied AT THE INPUTS OF EACH ROUND, before the registered `^6` block, NOT after the
update. The measured spectral norm of d(sum of final node states)/d(initial node states) over 8 shared rounds
is **127.0-140.2** with the norm after the update -- the draft's implied reading, and an exploding gradient --
against **8.240-14.83** with the norm at the inputs. THE DRAFT'S IMPLIED PLACEMENT IS THE DANGEROUS ONE, and
it is the placement this module does not use. Concretely each round RMS-normalises (a) the residual stream
`h`, (b) the parent aggregate and (c) the child aggregate before they enter `^6`, and then also holds the
residual stream itself at unit row RMS after the update.

`UNCERTAIN:` the 8.240-14.83 figure was measured for the input placement in the form the learnability lens
simulated; whether ALSO holding the residual at unit RMS after the update moves that spectral norm was not
measured by either review, and this module does not claim it does not. The hold is kept because without it an
unnormalised residual stream over K = 8 rounds is exactly the accumulation the 127.0-140.2 row measures.
Section 5.6 decision 4 makes the same point about the saturation figure: the worker's assertion must measure
the combination actually built. `pass0_saturation` below is that instrument.

=========================================================================================================
INITIALISATION (REVIEW_SYNTHESIS.md section 5.6)
=========================================================================================================

The `^6` block is `W2 * tanh(W1 x)`, so where `|z| > 2` its derivative is below 0.071 and the block is
effectively a constant. Measured fraction of pre-activations with `|z| > 2`: He-normal / over-large with no
norm **75.30-98.03 %**; any initialisation with the output norm **48.02-91.83 %**; He-normal with the output
norm -- the natural choice for a two-layer tanh net without biases -- **48.02-57.21 %**, the WORST case;
torch-default with the output norm **7.65-13.42 %**, the only moderate figure. So the initialisation is
PINNED to the torch-default scheme: the `^6` block is built by
`cncm.typed_matched_worker._framework(torch, device, seed)`, which constructs `_DecomposeTransform` from
`nn.Linear(..., bias=False)` and therefore draws from `torch.nn.init.kaiming_uniform_` (a = sqrt(5)). The block
is installed as a leaf parameter WITHOUT further initialisation, `module.initial_block()` returns the three
tensors exactly as `_framework` built them, `pass0_saturation` digests them so the pass-0 assertion can be tied
to the registered start, and `run_identity["initialization"]` records the pin. Every OTHER parameter this file
creates uses `nn.Linear`'s default scheme too; the only tensor initialised by hand is the declaration table,
whose last row is reserved and zeroed as the padding row.

`UNCERTAIN:` the saturation fraction for torch-default WITH THE INPUT PLACEMENT was never printed -- the lens
printed torch-default with the OUTPUT placement (7.65-13.42 %). The worker must measure the combination
actually built rather than assume that number carries over (section 5.6 decision 4).

=========================================================================================================
K = 8, AND `depth` IS NOT AN INPUT (review LK18, DG1)
=========================================================================================================

K = 8 shared message-passing rounds, whatever the batch's `depth` is. Training batches used depths 1 / 2 / 4 /
8 while EVERY evaluation uses 8, so a learner that conditioned on `depth` could gain from p0 to p10 by
extrapolating depth, and that gain would be indistinguishable from learning in the label. `DESIGN` does not
say so plainly; review LK18 does, and the mechanism here is structural rather than a convention: the forward
pass takes NO depth argument at all (`_forward(self, packet)`, `graph_forward(self, reading, ...)`), `stage_batch`
validates the batch's depth only as a schedule coordinate and never passes it on, and every prediction records
`depth = PREDICTION_DEPTH` = `contract.DESIGN["prediction_depth"]` = 8.
`UNCERTAIN:` K = 8 is an UNCONVERGED phase of the recurrence (per-round update magnitude for a 4-node world at
torch-default runs 0.279, 0.288, 0.309, 0.325, 0.333, 0.338, 0.341, 0.343 and is still growing), so a depth
ablation over K = 1, 2, 4, 8 compares FUNCTIONS, not compute budgets. Recorded as a property of the study, not
treated here as a knob.

=========================================================================================================
KNOWN, REPORTED, NOT HIDDEN: `correspondence` CANNOT EXPRESS A BIJECTION
=========================================================================================================

The `correspondence` `mapping_target` head here reads node states and never a pooled vector, as the review
requires -- but the learnability lens measured that A PER-NODE ADDITIVE HEAD CANNOT EXPRESS A BIJECTION AT ALL:
every permutation in the source world's automorphism group receives an identical total score, the declared tie
rule picks the first syntactic bijection, and that is correct in **0 of 20** held records; in **81 of 88**
records no admissible mapping lies in the source world's automorphism group, so no additive per-node score over
these inputs can be made to prefer a correct answer (LB12, LB13, LB15). The contract has already removed all
five `correspondence` questions from the gate population under the ARCHITECTURAL class `inexpressible` -- not as
a shortcut (`pointer_contract.py:478-503`). `correspondence` is still run, scored and sealed here; this note is
the disclosure that its failure is a known head limit, so the study does not read it as evidence about the
machine.

ONE RECORDED RELAXATION. `edge_account`'s head receives the single raw `(a -> b)` adjacency bit as one extra
input dimension, which is exactly the relaxation the learnability lens asked for in its own `edge_account`
section. The bit is a constant, not a gradient path; it is not a hashed alias and it is world-independent, and
it hands over neither `children`, nor reachability, nor isomorphism. It is recorded in
`profile()["edge_head_relaxation"]` and in `run_identity["head_set"]`.

WHAT THIS FILE DOES NOT DO. Importing, defining or measuring anything here runs no training. The real numerical
acceptance is the AWS smoke and the paid job; no GPU work happens on the local machine.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
import io
import math
import os
from pathlib import Path
import random
import re
import threading
import time

from . import pointer_contract as contract, pointer_inputs, source
from .learner import BATCH_SCHEMA, PARAMETER_SHAPES, PARAMETERS, TypedCourseLearner, _cpu, state_identity

# `require` is the shared pair, so every failure raises `ValueError("TYPED_MATCHED:" + code)`.
require, digest, canonical = source.require, source.digest, source.canonical

CHECKPOINT_SCHEMA = "cncm.typed-pointer-checkpoint/0.1"
UPDATE_SCHEMA = "cncm.typed-pointer-update/0.1"
PREDICTION_SCHEMA = "cas.typed-teaching-prediction/0.1"

# The twelve fields `loss_plan.validate_prediction` requires EXACTLY (`loss_plan.py:37-39`). A prediction
# missing one, or carrying a thirteenth, is refused with `TYPED_LOSS_PREDICTION_FIELDS`.
PREDICTION_FIELDS = ("schema", "prediction_id", "record_id", "packet_digest", "slot_plan_digest",
                     "depth", "model_revision", "run_context_digest", "encoder_identity_digest",
                     "scores", "decisions", "answer")
PREDICTION_FIELD_SET = frozenset(PREDICTION_FIELDS)
require(len(PREDICTION_FIELDS) == 12 and len(PREDICTION_FIELD_SET) == 12, "POINTER_PREDICTION_FIELDS")

RUN_IDENTITY_FIELDS = ("context", "learner_profile", "encoder_identity", "initial_model_identity",
                       "scope", "optimizer_config", "limits", "initialization", "core_rounds",
                       "readout", "head_set", "counters", "counter_units", "depth_is_not_an_input",
                       "prediction_depth", "normalisation_placement", "round_parameters_shared",
                       "dense_and_one_hot_only", "scored_fields", "measured_pooling", "measured_stability")
METADATA_FIELDS = ("run_identity", "run_identity_digest", "model_revision", "cursor", "counters",
                   "elapsed_seconds", "training_mode", "model_state_identity",
                   "optimizer_state_identity", "encoder_state_identity", "rng_state_identity",
                   "init_args", "learnable_names")
INIT_ARGS_FIELDS = ("optimizer_config", "run_context", "limits", "device", "python_seed", "root")

# -------------------------------------------------------------------------------------------------------
# THE SHAPE AND GEOMETRY OF THE MACHINE. Every width is a module constant, so the container is a pure
# function of this file plus the three `^6` tensors: `restore_checkpoint` rebuilds it and loads the saved
# state dict with `strict=True`, and a shape that moved without this file moving is then a state-dict
# mismatch rather than a silent re-initialisation. WIDTH is 64 because the registered `^6` block is 64-wide
# (`learner.PARAMETER_SHAPES`; `_DecomposeTransform` at
# `research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py:104-126`).
# -------------------------------------------------------------------------------------------------------
WIDTH = 64
CORE_ROUNDS = contract.PLANNED_WORK_ROUNDS                  # 8, shared weights, never the batch's depth
NODE_FEATURE_COUNT = 8                                      # the rank branch is off in the contract today
NODE_FEATURE_COUNT_WITH_RANK = 9
QUERY_INPUT_WIDTH = 21                                      # 8 kind + 9 rule + 4 scalars
CLAUSE_COUNT = 6                                            # the six independent role classes
DECLARATION_FIELDS = pointer_inputs.DECLARATION_FIELDS      # ("domain", "function", "kind", "setting")
DECLARATION_ROWS = len(DECLARATION_FIELDS)
DECL_MAX_TOKENS = 256                                       # rows reserved per declaration field
DECL_VECTOR_WIDTH = 32
# THE DEGREE FEATURES. A one-hot projection of the in-degree and the out-degree, each spanning
# {0, 1, 2, 3, 4 or more}: the COMPLETE isomorphism invariant on this corpus ([LB3], [LB7]) inside the head's
# own input, with NO division by the node count. Every bank world has at most 4 nodes and at most 3 children
# per node, so the truncation loses nothing here.
DEGREE_STEPS = 5
# WHERE THE TWO DEGREE COLUMNS ARE, AND WHY THEY ARE DERIVED. `_degree_features` appends `2 * DEGREE_STEPS`
# columns to every node feature row, in this order: the IN-degree one-hot's `DEGREE_STEPS` columns FIRST, then
# the OUT-degree one-hot's. These two constants name the FIRST column of each block, so the two blocks are
# `DEGREE_STEPS` apart and the second ends at the row's own width. Summed over a world's rows, that column is
# the world's count of nodes sitting at the block's first degree value -- scaled by the per-row RMS
# `_rms_unit` applies to the row, which is what `_pooled_worlds` and `_reach_options` then read.
#
# `OUT_DEGREE_SUM_COLUMN` previously read `NODE_FEATURE_COUNT + 1` = 9, which is the IN-degree block's SECOND
# column. Every world-level and reach-level degree feature therefore carried a second IN-degree statistic, no
# out-degree reading reached any head at all, and NOTHING RAISED, because index 9 exists inside an 18-wide row.
# That is the same family as the four width defects above -- a declaration drifting from the thing it
# describes -- and it is silent in exactly the way a wrong width is not, which is why the two constants are now
# DERIVED from the block they name AND validated against the world's own adjacency in `_graph_blocks`.
IN_DEGREE_SUM_COLUMN = NODE_FEATURE_COUNT
OUT_DEGREE_SUM_COLUMN = NODE_FEATURE_COUNT + DEGREE_STEPS
# The per-row LENGTH of the node feature matrix: the raw flag columns plus the one-hot degree columns.
NODE_ROW_WIDTH = NODE_FEATURE_COUNT + 2 * DEGREE_STEPS
# The `a -> b` adjacency bit's own embed width, so the edge head's MLP can be run as ONE batched matrix
# product over the `n x n` ordered pairs the `edge_account` slots enumerate.
DIRECTED_PAIR_WIDTH = 8
# mean ++ max ++ 4 degree/flag features ++ the learned attention pool: three full-width vectors and four
# scalars, so the mean is present AND the wiring the review measured it losing is present beside it.
WORLD_VECTOR_WIDTH = 3 * WIDTH + 4
# The per-candidate width of the world-choice scorer. CORRECTED: the query key and the query value are each a
# DOT PRODUCT with the candidate -- `key @ candidate` and `value @ candidate`, one scalar each, exactly as
# `_world_scores`' own docstring says -- so the two terms contribute 2 columns, not 2 * WIDTH. Plus 4 for the
# is_focus / is_target flags, plus the candidate's declaration embedding: the shape AND the domain text, which is
# what an `analogy` answer needs together (17 of 17 held).
#
# This constant previously read `2 * WIDTH + 4 + DECL_VECTOR_WIDTH`, written for a form the code does not
# implement, and `_world_scores` therefore refused on every prediction with POINTER_WORLD_CANDIDATE_WIDTH. It
# stayed hidden through the whole build and phase A because nothing scores a world until the first evaluation,
# and it cost a third AWS run to find. This is the same class as the node-head width: a declared width drifting
# from the thing it describes.
WORLD_CANDIDATE_WIDTH = 2 + 4 + DECL_VECTOR_WIDTH
SLOT_DECLARATION_FIELD = {"kind_ref": "kind", "function_ref": "function", "setting_ref": "setting",
                          "world_id": "domain"}
REACH_OPTION_COUNT = 2                                      # ABSENT, DIRECT
MODE_OPTION_COUNT = 2                                       # NO_MATCH, MAPPING
PER_ROUND_UPDATE_CAP = 0.01                                 # a collapse guard, not an authority choice
RMS_EPSILON = 1e-6
ROLE_IDS = 6                                                # the six independent role classes
# The internal, dot-free names each registered `^6` tensor is held under. `register_parameter` refuses a dot,
# so the container keeps the registered dotted names in its state dict and translates them here.
BLOCK_NAMES = {name: "_block_" + name.replace(".", "_") for name in PARAMETERS}
require(set(BLOCK_NAMES) == set(PARAMETERS) and len(set(BLOCK_NAMES.values())) == len(PARAMETERS)
        and all("." not in name for name in BLOCK_NAMES.values()), "POINTER_BLOCK_NAMES")
# The self-check must assert what the CONSTANT now is, and it must agree with `_world_scores`' own construction:
# two dot products, four flags, one declaration embedding. Re-deriving the old `2 * WIDTH` form here is what let
# the constant and the code disagree while both looked self-consistent.
require(WORLD_CANDIDATE_WIDTH == 2 + 4 + DECL_VECTOR_WIDTH
        and WORLD_VECTOR_WIDTH == 3 * WIDTH + 4, "POINTER_WIDTH_ARITHMETIC")

# EXACTLY as REVIEW_SYNTHESIS.md sections 5.5 and 5.6 printed them. Never rounded.
MEASURED_POOLING = {
    "inter_shape_distance": 0.831003,
    "intra_shape_distance": 1.213181,
    "ratio": 0.68,
    "nearest_centroid_recovered": "8-13 of 123 against a chance level of 20.5 of 123",
    "graph_content_share_of_norm": "3-8 percent, 13-16 percent with the real flag dimensions",
    "node_state_edge_gap_k1": 0.039000,
    "node_state_edge_gap_k2": 0.184217,
    "node_state_edge_gap_k4": 0.388418,
    "node_state_edge_gap_k8": 0.340409,
}
MEASURED_STABILITY = {
    "jacobian_after_update": "127.0-140.2",
    "jacobian_inputs": "8.240-14.83",
    "jacobian_none": "6.790-11.19",
    "saturation_he_normal_no_norm": "75.30-98.03 percent",
    "saturation_output_norm": "48.02-91.83 percent",
    "saturation_he_normal_output_norm": "48.02-57.21 percent",
    "saturation_torch_default_output_norm": "7.65-13.42 percent",
}
SATURATION_ABS_Z = 2.0
MAX_ABS_SCORE = 1000000.0                                   # `slots.MAX_ABS_SCORE`, `slots.py:25`

# -------------------------------------------------------------------------------------------------------
# THE COUNTER KEY SET, and the one shared source of truth `pointer_contract.expected_main_delta` must be
# updated from. `cncm/typed_course_worker.counter_delta` requires the two snapshots' key sets to match
# EXACTLY, and `typed_practice_worker.py:361` compares the canonical bytes of the summed per-update deltas
# against the registered expectation, so ONE extra or missing key fails MAIN_TRAINING_COUNTERS after the spend.
# The contract's `MAIN_COUNTERS` is None today and `expected_main_delta` fails closed with `MAIN_COUNTERS_OPEN`
# because the key set was never fixed (`pointer_contract.py:450-464`). This tuple IS that key set, and
# `EXPECTED_MAIN_COUNTERS` is the exact tuple `MAIN_COUNTERS` must be set to.
#
# The units are the POINTER machine's own: packet forwards, rounds times packets, and updates -- not the old
# machine's per-slot core passes. A packet forward is one presentation; each forward runs CORE_ROUNDS rounds of
# message passing, so the core-call ledger is rounds x packets.
# -------------------------------------------------------------------------------------------------------
COUNTER_KEYS = ("core_forward_attempts", "core_forward_calls", "sample_core_passes",
                "packet_forward_calls", "prediction_calls", "staged_batches", "backward_attempts",
                "backward_calls", "optimizer_step_attempts", "optimizer_updates",
                "private_loss_plan_calls")
PACKET_FORWARD_KEYS = ("packet_forward_calls", "prediction_calls", "private_loss_plan_calls")
ROUND_KEYS = ("core_forward_attempts", "core_forward_calls", "sample_core_passes")
UPDATE_KEYS = ("staged_batches", "backward_attempts", "backward_calls", "optimizer_step_attempts",
               "optimizer_updates")
COUNTER_UNITS = {key: ("PACKET_FORWARD" if key in PACKET_FORWARD_KEYS
                       else "ROUNDS_TIMES_PACKETS" if key in ROUND_KEYS else "UPDATE")
                 for key in COUNTER_KEYS}

# (counter key, schedule statistic, multiplier, unit). `result = schedule_stat x multiplier`.
# Derived THROUGH `contract.PLANNED_WORK["relations"]`, which is the one shared source of truth the interface
# spec asks for (`INTERFACE_SPEC_POINTER.md:49`): for every counter the contract's own table names, the
# statistic and the multiplier are taken FROM THE CONTRACT, and this module only adds the counters the
# contract's table does not name. One rule fixes both sides.
#
#   * PACKET_FORWARD: one record forward per presentation. `packet_forward_calls` is the forward itself,
#     `prediction_calls` the public prediction assembled from it, `private_loss_plan_calls` its checked loss
#     plan (one per record per update; training only, so it is only read on the main training phase).
#   * ROUNDS_TIMES_PACKETS: CORE_ROUNDS core invocations per forward, each taking an attempt, a call, and one
#     charged sample pass.
#   * UPDATE: one per batch.
#
# The pointer machine's units are its own -- packet forwards, rounds times packets, and updates, not the old
# machine's per-slot core passes. A packet forward is one presentation; each forward runs CORE_ROUNDS rounds of
# message passing, so the core ledger is rounds x packets. On the frozen stratified schedule that is
# 1176 presentations per pass x 8 = 9408 core calls per pass, i.e. 94080 over ten passes against the
# registered 600000 `MAX_CORE_CALLS`; the same multiplicative reconciliation `pointer_contract.py:105-114`
# asks the smoke job to make.
CONTRACTED = {name: (statistic, multiplier)
              for name, statistic, multiplier in contract.PLANNED_WORK["relations"]}
COUNTER_PLAN = (
    ("packet_forward_calls", "presentations", 1, "PACKET_FORWARD"),
    ("prediction_calls", "presentations", 1, "PACKET_FORWARD"),
    ("private_loss_plan_calls", "presentations", 1, "PACKET_FORWARD"),
    ("core_forward_attempts", "presentations", CORE_ROUNDS, "ROUNDS_TIMES_PACKETS"),
    ("core_forward_calls", "presentations", CORE_ROUNDS, "ROUNDS_TIMES_PACKETS"),
    ("sample_core_passes", "presentations", CORE_ROUNDS, "ROUNDS_TIMES_PACKETS"),
    ("staged_batches", "main_updates", 1, "UPDATE"),
    ("backward_attempts", "main_updates", 1, "UPDATE"),
    ("backward_calls", "main_updates", 1, "UPDATE"),
    ("optimizer_step_attempts", "main_updates", 1, "UPDATE"),
    ("optimizer_updates", "main_updates", 1, "UPDATE"),
)
PLANNED_WORK_RELATIONS = tuple(
    (name, CONTRACTED[name][0], CONTRACTED[name][1], unit) if name in CONTRACTED
    else (name, statistic, multiplier, unit)
    for name, statistic, multiplier, unit in COUNTER_PLAN)
EXPECTED_MAIN_COUNTERS = tuple(name for name, _, _, _ in PLANNED_WORK_RELATIONS)
require(len(COUNTER_KEYS) == 11 and len(set(COUNTER_KEYS)) == 11, "POINTER_COUNTER_KEYS")
require(tuple(sorted(name for name, _, _, _ in PLANNED_WORK_RELATIONS)) == tuple(sorted(COUNTER_KEYS))
        and len(PLANNED_WORK_RELATIONS) == len(COUNTER_KEYS)
        and tuple(sorted(COUNTER_UNITS)) == tuple(sorted(COUNTER_KEYS)), "POINTER_COUNTER_RELATIONS")
require(len(COUNTER_KEYS) == len(PACKET_FORWARD_KEYS) + len(ROUND_KEYS) + len(UPDATE_KEYS)
        and set(COUNTER_KEYS) == {*PACKET_FORWARD_KEYS, *ROUND_KEYS, *UPDATE_KEYS},
        "POINTER_COUNTER_ROLLUP")
require(all(row[1] in ("presentations", "main_updates") and type(row[2]) is int and row[2] >= 1
            for row in PLANNED_WORK_RELATIONS), "POINTER_COUNTER_RELATION_STATS")
require(all(CONTRACTED[name][1] == CORE_ROUNDS for name in ROUND_KEYS)
        and set(CONTRACTED) <= set(EXPECTED_MAIN_COUNTERS), "POINTER_COUNTER_CONTRACT_AGREEMENT")

# The study's own ceilings, read live from the contract rather than re-derived.
MAX_CORE_CALLS = contract.MAX_CORE_CALLS
MAX_UPDATES_CEILING = contract.LEARNER_MAX_UPDATES_CEILING
MAX_WALL_SECONDS = contract.MAX_WALL_SECONDS
PREDICTION_DEPTH = contract.DESIGN["prediction_depth"]
CONDITIONS = ("ALT_COMPONENT_WHOLE", "MIXED_SAME_ITEMS", "ORDINARY_DEPENDENCY_GRAPH")
SOURCE_SEEDS = (101, 202, 303)
require(type(PREDICTION_DEPTH) is int and PREDICTION_DEPTH in (1, 2, 4, 8), "POINTER_PREDICTION_DEPTH")
require(PREDICTION_DEPTH == contract.DESIGN["depths"][-1], "POINTER_PREDICTION_DEPTH")
require(type(contract.DESIGN["node_rank_feature"]) is bool, "POINTER_RANK_FEATURE")
require(CORE_ROUNDS == 8 and contract.DESIGN["core_rounds"] == CORE_ROUNDS, "POINTER_CORE_ROUNDS")
NODE_FEATURE_COUNT = (NODE_FEATURE_COUNT_WITH_RANK if contract.DESIGN["node_rank_feature"]
                      else NODE_FEATURE_COUNT)
# Derived AFTER the rank branch is resolved, so the two widths cannot disagree: `NODE_ROW_WIDTH` is the
# per-node row of the feature block, and `BLOCK_INPUT_WIDTH` is the three concatenated halves of one round --
# the normalised state, the normalised parent aggregate and the normalised child aggregate -- which a learned
# matrix projects to the registered `^6` block's own width. A world is read as a directed graph, and the
# block is the registered `^6` operation applied per node.
NODE_ROW_WIDTH = NODE_FEATURE_COUNT + 2 * DEGREE_STEPS
BLOCK_INPUT_WIDTH = 3 * NODE_ROW_WIDTH
require(NODE_ROW_WIDTH == (18 if not contract.DESIGN["node_rank_feature"] else 19)
        and BLOCK_INPUT_WIDTH == 3 * NODE_ROW_WIDTH, "POINTER_BLOCK_INPUT_WIDTH")
# The two degree blocks tile the degree half of the row EXACTLY: the in-degree block occupies
# `[IN_DEGREE_SUM_COLUMN, OUT_DEGREE_SUM_COLUMN)`, the out-degree block occupies the rest, and each is
# `DEGREE_STEPS` wide. This is arithmetic, so it cannot see a wrong number -- the check that can, and that
# reads the graph itself, is in `_graph_blocks`.
require(IN_DEGREE_SUM_COLUMN == NODE_FEATURE_COUNT
        and OUT_DEGREE_SUM_COLUMN == IN_DEGREE_SUM_COLUMN + DEGREE_STEPS
        and OUT_DEGREE_SUM_COLUMN + DEGREE_STEPS == NODE_ROW_WIDTH, "POINTER_DEGREE_COLUMNS")

# The reading's `kind` id space and the slot `field` space this module scores. Both are pinned here rather than
# imported, so a course change that reordered kinds or added a slot field fails closed.
KIND_NAMES = tuple(pointer_inputs.KIND_IDS)
KIND_COUNT = len(KIND_NAMES)
RULE_COUNT = len(pointer_inputs.RULE_IDS)
require(KIND_NAMES == contract.KINDS and KIND_COUNT == 8 and RULE_COUNT == 9, "POINTER_KIND_NAMES")
NODE_POINTER_FIELDS = frozenset(("whole", "mapping_target"))
WORLD_CHOICE_FIELDS = frozenset(("kind_ref", "function_ref", "setting_ref", "world_id"))
SCORED_FIELDS = frozenset(("node", "participant", "edge", "role", "whole", "reach", "mapping_target",
                           "mode", "world_id", "kind_ref", "function_ref", "setting_ref"))

# The six independent role classes of the published focal grammar. The 7 clause prefixes map onto 6 role
# classes because `parts` -> 5 and `account` -> [5, 6] TOUCH ROLE 5, and `role_set`'s symbols are the six role
# ids (`focal.grammar_profile()["candidate_menu"]` = ALL_SIX_ROLES_INDEPENDENT_OF_TARGET). The literals below
# are a FALLBACK: the canonical values are read from `focal` inside `RoleTagger`, which is the same module the
# private checker derives the role answer with, so this table cannot drift from it.
FOCAL_PREFIX_FALLBACK = {"definition": "Declared whole: ", "context": "Declared surroundings: ",
                         "analogy": "Different domains, same containment pattern: ",
                         "correspondence": "Exact node correspondence: ",
                         "parts": "Direct constituent inventory: ",
                         "account": "Complete static containment account: ",
                         "reference": "Source reference: "}
FOCAL_ROLES_FALLBACK = {"definition": [1], "context": [2], "analogy": [3], "correspondence": [4],
                        "parts": [5], "account": [5, 6], "reference": []}
CLAUSE_NAMES = tuple(sorted(FOCAL_PREFIX_FALLBACK))


# -------------------------------------------------------------------------------------------------------
# PROFILE AND IDENTITY HELPERS. `restore_checkpoint` compares the MODULE-LEVEL `profile()` over the transitive
# file list, so this module owns its own list and its own body.
# -------------------------------------------------------------------------------------------------------
def slots_profile():
    """`slots.profile()`, imported inside the function so this module still imports without it."""
    from . import slots
    return slots.profile()


def profile():
    """On-disk identity of the pointer learner: 10 own files plus the transitive `slots.profile()` chain.

    The practice checkpoints' `learner_profile` is `learner.profile()`, whose list is `learner.py:30-34` plus
    `slots.profile()` plus `course.profile()`'s 15 files. The pointer study's is THIS one, so a pointer
    checkpoint can never be restored as a practice one and vice versa: the digest differs by construction,
    before any value is compared.
    """
    own = Path(__file__).resolve()
    package = own.parent
    meta = own.parents[1]
    research = own.parents[2]
    paths = [own,
             package / "pointer_contract.py",
             package / "pointer_inputs.py",
             package / "learner.py",
             package / "loss_plan.py",
             package / "slots.py",
             meta / "recurrent_cjt" / "recurrence.py",
             meta / "graph_teaching" / "trainer.py",
             meta / "graph_teaching" / "real_framework.py",
             meta / "teaching_cycle" / "gpu_adapter.py"]
    require(all(path.is_file() for path in paths), "POINTER_PROFILE_FILES")
    body = {
        "schema": "cncm.typed-pointer-learner-profile/0.1",
        "files": [{"path": path.relative_to(research).as_posix(),
                   "sha256": sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
                  for path in paths],
        "slots_profile": slots_profile(),
        "width": WIDTH, "core_rounds": CORE_ROUNDS, "shared_round_parameters": True,
        "prediction_depth": PREDICTION_DEPTH, "depth_is_not_an_input": True,
        "counters": list(COUNTER_KEYS), "counter_units": dict(COUNTER_UNITS),
        "planned_work_relations": [list(row) for row in PLANNED_WORK_RELATIONS],
        "expected_main_counters": list(EXPECTED_MAIN_COUNTERS),
        "readout": ("NODE_LEVEL_FOR_STRUCTURAL_HEADS; WORLD_VECTOR_IS_MEAN_AND_MAX_AND_EXACT_DEGREE_SUMS_AND_"
                    "FOCUS_TARGET_FLAGS_AND_A_LEARNED_ATTENTION_POOL; WORLD_CHOICE_HEADS_ALSO_SEE_EACH_"
                    "CANDIDATE_WORLD_DECLARATION_TEXT"),
        "normalisation_placement": "INPUTS_OF_EACH_ROUND_BEFORE_THE_REGISTERED_CORE",
        "initialization": "BUILT_BY_cncm.typed_matched_worker._framework_TORCH_DEFAULT_SCHEME",
        "head_set": sorted(SCORED_FIELDS),
        "edge_head_relaxation": "THE_RAW_A_TO_B_ADJACENCY_BIT_AS_ONE_INPUT_DIMENSION_OF_THE_EDGE_MLP",
        "correspondence_disclosure": "KNOWN_INEXPRESSIBLE_PER_NODE_HEAD_LB12_LB13_LB15_REPORTED_NOT_HIDDEN",
        "measured_pooling": deepcopy(MEASURED_POOLING),
        "measured_stability": deepcopy(MEASURED_STABILITY),
        "gradient_gate": "FINITENESS_ONLY_WHERE_GRAD_IS_NOT_NONE_AT_LEAST_ONE_REQUIRED",
        "training_loss": ("TypedCourseLearner._tensor_loss CALLED UNCHANGED: field mean, task mean, batch "
                          "mean; raw task loss for training"),
        "identity_boundary": "ON_DISK_BYTES; LOADED_SOURCE_WHEEL_AND_PROVIDER_ATTESTATION_REQUIRED_FROM_WORKER",
        "status": "WORKER_IMPLEMENTATION_NUMERIC_ACCEPTANCE_PENDING_AWS_SMOKE",
    }
    return {**body, "profile_digest": digest(body)}


def _fingerprint(torch, value):
    """`name:dtype:shape` over a state dict in sorted-key order: names and shapes only, no values.

    An empty fingerprint means the object owns no tensors at all, which is how `restore_checkpoint` tells a
    pointer checkpoint (whose `model_state` carries this container's names) from a practice one (whose
    `model_state` is exactly the three `^6` keys) WITHOUT re-initialising anything.

    ANY MAPPING, NOT ONLY `dict`. This gate previously read `type(value) is dict`, and `nn.Module.state_dict()`
    returns a `collections.OrderedDict`, so the LIVE side of `restore_checkpoint`'s layout guard fingerprinted
    as the empty tuple while the SAVED side -- a genuine `dict`, because `export_checkpoint` saves
    `dict(self.module.state_dict())` -- fingerprinted as 46 rows. `()` never equals a 46-row tuple, so the guard
    failed on a container that matched the checkpoint EXACTLY, on every reload, after a full 1470-update
    training run had already been paid for. Nothing raised on the way in: the empty tuple was indistinguishable
    from the documented "owns no tensors" answer, which is why a wrong-type argument to this helper is a silent
    layout lie rather than an error. The gate is now `isinstance(value, Mapping)`, which is what both callers
    actually pass, and the empty answer is checked SEPARATELY from the comparison at the call site so the two
    meanings can never again share one expression.
    """
    rows = []
    if isinstance(value, Mapping):
        for key in sorted(value, key=lambda item: str(item)):
            item = value[key]
            if torch.is_tensor(item):
                rows.append("%s:%s:%s" % (key, item.dtype, tuple(int(v) for v in item.shape)))
    return tuple(rows)


def _tensor_flat_bytes(torch, value):
    """Exact tensor bytes, concatenated in sorted-key order, for the mapping a fingerprint was taken over."""
    require(isinstance(value, Mapping) and value, "POINTER_TENSOR_BYTES")
    chunks = []
    for key in sorted(value, key=lambda item: str(item)):
        item = value[key]
        require(torch.is_tensor(item) and not item.is_sparse, "POINTER_TENSOR_BYTES")
        chunks.append(bytes(item.detach().contiguous().reshape(-1).view(torch.uint8).cpu().tolist()))
    return b"".join(chunks)


# -------------------------------------------------------------------------------------------------------
# SLOT COORDINATE AND SYMBOL DECODERS. Pure string and index arithmetic over the plan, reading the canonical
# alias tables instead of recomputing them.
# -------------------------------------------------------------------------------------------------------
def _node_rank_of_ref(ref):
    """The rank a schema node ref carries: its own `/n<i>` index, which IS its sorted position.

    The same recovery `pointer_inputs.slot_readings` performs (`pointer_inputs.py:165-171`), so the mapping from
    a slot's coordinate refs onto the reading's node-list positions is one rule in one place.
    """
    require(type(ref) is str, "POINTER_SLOT_REF")
    head, separator, tail = ref.rpartition("/n")
    require(bool(head) and separator == "/n" and tail.isdigit() and str(int(tail)) == tail,
            "POINTER_SLOT_REF")
    return int(tail)


def _node_rank_of_alias(symbol):
    """`N7` -> 7. The alias table's N-prefix carries the rank and nothing else."""
    require(type(symbol) is str and re.fullmatch(r"N[0-9]+", symbol) is not None, "POINTER_NODE_ALIAS")
    return int(symbol[1:])


def _via_rank(symbol):
    """`VIA_N7` -> 7.

    `symbol[5:]`, NOT `symbol[4:]`. The prefix `VIA_N` is five characters; slicing from index 4 leaves the leading
    `N`, so `int()` raised `invalid literal for int() with base 10: 'N0'` on the first `VIA_N` symbol a real run
    ever scored -- after the model built, after phase A completed, and after five other wiring defects had been
    cleared. `_node_rank` directly above is the correct shape of this function: its prefix `N` is one character and
    it slices from index 1. The `require` below already pins the pattern, so everything from index 5 is digits.
    """
    require(type(symbol) is str and re.fullmatch(r"VIA_N[0-9]+", symbol) is not None,
            "POINTER_VIA_ALIAS")
    return int(symbol[5:])


def _world_alias_table(plan):
    """`{alias: world_id}` in the alias table's own order, checked for uniqueness."""
    rows = plan["aliases"]["worlds"]
    require(type(rows) is list and rows, "POINTER_ALIAS_TABLE")
    table = {row["alias"]: row["world_id"] for row in rows}
    require(len(table) == len(rows), "POINTER_WORLD_ALIAS")
    return table


def _sorted_world_ids(reading):
    """The reading's world ids in canonical order. `pointer_inputs` builds the dict index-sorted."""
    ids = list(reading["worlds"])
    require(ids == sorted(ids) and len(set(ids)) == len(ids), "POINTER_READING_ORDER")
    return ids


def _role_prefixes():
    """The published clause prefixes and their role lists, read from `focal` where it is importable."""
    try:
        from . import focal
        prefixes = dict(focal.PREFIXES)
        roles = {name: list(value) for name, value in focal._ROLES.items()}
    except Exception:
        prefixes, roles = dict(FOCAL_PREFIX_FALLBACK), deepcopy(FOCAL_ROLES_FALLBACK)
    require(set(prefixes) == set(roles) == set(FOCAL_PREFIX_FALLBACK), "POINTER_ROLE_PREFIXES")
    require(all(prefixes[name] == FOCAL_PREFIX_FALLBACK[name] for name in FOCAL_PREFIX_FALLBACK),
            "POINTER_ROLE_PREFIX_TEXT")
    require(all(sorted(set(roles[name])) == sorted(set(FOCAL_ROLES_FALLBACK[name]))
                for name in FOCAL_ROLES_FALLBACK)
            and all(1 <= role <= CLAUSE_COUNT for value in roles.values() for role in value),
            "POINTER_ROLE_PREFIX_ROLES")
    return prefixes, roles


class RoleTagger:
    """The `role_set` clause matcher: which clause prefix each line of a focal excerpt starts with.

    `role_set` is the TEXT tier and is reported, never labelled on. Its answer is the union of the roles of the
    clause prefixes present in the focal excerpt (`focal.derive_roles`, `focal.py:246-273`), and the excerpt
    reaches the reading as a POSITION-FREE sorted bag of token ids (`pointer_inputs.py:391-396`), so the clause
    structure is not recoverable from the reading alone. This tagger reads the excerpt TEXT from the packet's
    public query and returns, per line, which clause prefix it starts with -- a pure function of public syntax
    that performs no numeric work. It is not a second answer channel: it is the same public convention `focal`
    publishes in `grammar_profile()["clauses"]`.
    """

    def __init__(self, *, root):
        self.root = Path(root).resolve()
        self.prefixes, self.roles = _role_prefixes()
        self.cache = pointer_inputs.label_cache(self.root)
        self.cache_digest = self.cache["cache_digest"]
        require(type(self.cache_digest) is str and re.fullmatch("[0-9a-f]{64}", self.cache_digest)
                is not None, "POINTER_TAGGER_CACHE")

    def segments(self, packet):
        """`[[clause name, payload]]` for one packet's focal excerpt, in line order."""
        require(type(packet) is dict and type(packet.get("record")) is dict, "POINTER_TAGGER_PACKET")
        query = packet["record"].get("query")
        require(type(query) is dict and type(query.get("arguments")) is dict, "POINTER_TAGGER_PACKET")
        text = query["arguments"].get("focal_excerpt")
        require(type(text) is str and bool(text), "POINTER_TAGGER_EXCERPT")
        rows = []
        for line in text.split("\n"):
            names = [name for name in CLAUSE_NAMES if line.startswith(self.prefixes[name])]
            require(len(names) == 1, "POINTER_TAGGER_CLAUSE")
            rows.append([names[0], line[len(self.prefixes[names[0]]):]])
        require(rows, "POINTER_TAGGER_EXCERPT")
        return rows

    def roles_present(self, packet):
        """The sorted role ids the excerpt declares. The union, exactly as `focal.derive_roles` takes it."""
        present = set()
        for name, _payload in self.segments(packet):
            present.update(self.roles[name])
        require(all(1 <= role <= CLAUSE_COUNT for role in present), "POINTER_TAGGER_ROLE")
        return sorted(present)

    def indicators(self, packet):
        """The `CLAUSE_COUNT`-long role indicator of one packet, as a list of 0/1 ints."""
        present = set(self.roles_present(packet))
        return [1 if role in present else 0 for role in range(1, CLAUSE_COUNT + 1)]


_TAGGER_LOCK = threading.RLock()
_TAGGERS = {}
ROOTS = {}


def role_tagger(root):
    """One `RoleTagger` per resolved root, cached: building it reads the frozen course ONCE."""
    key = str(Path(root).resolve())
    with _TAGGER_LOCK:
        if key not in _TAGGERS:
            _TAGGERS[key] = RoleTagger(root=key)
        if key not in ROOTS:
            ROOTS[key] = {"root": key, "tagger_cache_digest": _TAGGERS[key].cache_digest, "built": True}
        return _TAGGERS[key]


def root_record(root):
    """The registered record for one CNCM root, so `restore_checkpoint` can rebuild the same tagger."""
    key = str(Path(root).resolve())
    with _TAGGER_LOCK:
        require(key in ROOTS, "POINTER_ROOT_NOT_BUILT")
        return deepcopy(ROOTS[key])


# -------------------------------------------------------------------------------------------------------
# THE ONE CONTAINER. Every learned weight of the pointer machine lives here, the three `^6` tensors included,
# and nothing else is a parameter. `graph_teaching.scope_parameters` is NEVER called on it:
# `real_framework.resolve_plasticity_groups` returns every parameter name of a real framework's module, so
# calling it would set `requires_grad_(False)` on every head (`trainer.py:86-87`, review RK2).
# -------------------------------------------------------------------------------------------------------
def _build_container(torch, framework, device):
    """Build the pointer container, installing the registered `^6` tensors under their exact names.

    The `^6` block comes from the framework built FIRST by `cncm.typed_matched_worker._framework` (`:43-48`), and
    its weights are installed as TOP-LEVEL parameters so their state-dict names stay `left.weight`,
    `right.weight`, `merge.weight` -- the names `learner.PARAMETER_SHAPES` registers and the names a practice
    checkpoint's `model_state` carries; a child module would prefix them. `core_block` reproduces that block's
    registered arithmetic exactly (`torch.cat((tanh(left(x)), tanh(right(x))), -1)` then `merge`;
    `cas_cjt/neural.py:124-126`), and the block weights are installed as leaf parameters with no further
    initialisation, which is the initialisation pin.
    """
    registered = dict(framework.module.state_dict())
    require(set(registered) == set(PARAMETERS), "POINTER_FRAMEWORK_STATE_KEYS")
    require(all(tuple(registered[name].shape) == PARAMETER_SHAPES[name] for name in PARAMETERS),
            "POINTER_FRAMEWORK_STATE_SHAPE")
    start = {name: registered[name].detach().to(device=device, dtype=torch.float32).contiguous().clone()
             for name in PARAMETERS}
    layout = {name: tuple(int(v) for v in start[name].shape) for name in PARAMETERS}

    class _PointerContainer(torch.nn.Module):
        """ONE container: the `^6` weights, the shared round, the readouts and the per-kind heads."""

        initial_block_layout = layout

        def __init__(self):
            super().__init__()
            # ---- the registered ^6 block, under its exact registered NAMES, installed FIRST ----
            # `nn.Module.register_parameter` refuses a name containing a dot, so each `^6` tensor is held
            # under an underscore name and the dot-free names are restored in `state_dict` / `load_state_dict`
            # below. Nothing downstream ever sees the underscore form: `named_parameters`,
            # `module.state_dict()`, the optimizer's groups and every checkpoint carry `left.weight`,
            # `right.weight`, `merge.weight`.
            for name in PARAMETERS:
                value = start[name].detach().clone()
                require(tuple(value.shape) == PARAMETER_SHAPES[name], "POINTER_FRAMEWORK_STATE_SHAPE")
                self.register_parameter(BLOCK_NAMES[name],
                                        torch.nn.Parameter(value, requires_grad=True))
            # ---- the shared round: the per-half encoder, the three-way blend, and the round rate ----
            # The node's raw feature row and its two aggregate rows are encoded SEPARATELY by one shared matrix
            # and then blended, so the registered `^6` block is called on ONE width-WIDTH vector per node per
            # round, exactly as `_DecomposeTransform` requires.
            self.node_encode = torch.nn.Linear(NODE_ROW_WIDTH, WIDTH, bias=False).to(device)
            # A softmax over three logits: how much of the node's OWN signal, of its parents' aggregate and of
            # its children's aggregate enters the registered `^6` block this round. Shared by all K rounds.
            self.round_mix = torch.nn.Parameter(
                torch.tensor([0.5, 0.25, 0.25], device=device, dtype=torch.float32))
            # `tanh(round_rate)` bounds the per-round step, so the residual stream cannot be driven off its
            # unit-RMS scale by a single round.
            self.round_rate = torch.nn.Parameter(torch.zeros(1, device=device, dtype=torch.float32))
            # ---- phase one: the query, the readouts, and the one-hot tables ----
            self.query_projection = torch.nn.Linear(QUERY_INPUT_WIDTH, WIDTH, bias=False).to(device)
            self.query_norm = torch.nn.LayerNorm(WIDTH).to(device)
            self.attention_key = torch.nn.Linear(WIDTH, 1, bias=False).to(device)
            self.world_projection = torch.nn.Linear(WORLD_VECTOR_WIDTH, WIDTH, bias=False).to(device)
            self.declaration_table = torch.nn.Parameter(
                torch.empty(DECLARATION_ROWS * DECL_MAX_TOKENS, WIDTH, device=device,
                            dtype=torch.float32))
            torch.nn.init.normal_(self.declaration_table, mean=0.0, std=1.0)
            # The LAST row of every field's block is that field's padding row, held at zero so a short
            # declaration pads with zeros rather than with a learned token.
            padding = torch.tensor([field * DECL_MAX_TOKENS + DECL_MAX_TOKENS - 1
                                    for field in range(DECLARATION_ROWS)], device=device)
            torch.nn.init.zeros_(self.declaration_table[padding, :])
            self.declaration_projection = torch.nn.Linear(WIDTH, DECL_VECTOR_WIDTH, bias=False).to(device)
            self.directed_pair_embedding = torch.nn.Parameter(
                torch.zeros(2, DIRECTED_PAIR_WIDTH, device=device, dtype=torch.float32))
            torch.nn.init.normal_(self.directed_pair_embedding, mean=0.0, std=1.0)
            # ---- phase three: the heads. Small, and none of them sees raw adjacency but the edge head. ----
            # `2 * WIDTH`, NOT `NODE_FEATURE_COUNT + WIDTH`. `GraphForward.__init__` builds the node head's input
            # as `cat((self.hidden, self.query_value))` -- the node's hidden state followed by the encoded query --
            # which is WIDTH + WIDTH columns. Declaring `NODE_FEATURE_COUNT + WIDTH` (8 + 64 = 72) left the head
            # unable to accept what the forward pass feeds it, and it stayed hidden until the first real training
            # step on AWS: `runtimeError: mat1 and mat2 shapes cannot be multiplied (244x128 and 72x64)` inside
            # `node_head`, after preflight, after phase A, after the model build. The sibling heads were always
            # right -- `edge_head` uses `2 * WIDTH + DIRECTED_PAIR_WIDTH` and `role_head` uses three WIDTHs -- which
            # is what marks this line as the outlier rather than the forward pass.
            self.node_head = torch.nn.Sequential(
                torch.nn.Linear(2 * WIDTH, WIDTH, bias=False), torch.nn.GELU(),
                torch.nn.LayerNorm(WIDTH), torch.nn.Linear(WIDTH, 2, bias=True)).to(device)
            self.edge_head = torch.nn.Sequential(
                torch.nn.Linear(2 * WIDTH + DIRECTED_PAIR_WIDTH, WIDTH, bias=False), torch.nn.GELU(),
                torch.nn.LayerNorm(WIDTH), torch.nn.Linear(WIDTH, 2, bias=True)).to(device)
            self.role_head = torch.nn.Sequential(
                torch.nn.Linear(WIDTH + WIDTH + WIDTH + CLAUSE_COUNT, WIDTH, bias=False), torch.nn.GELU(),
                torch.nn.LayerNorm(WIDTH), torch.nn.Linear(WIDTH, 2, bias=True)).to(device)
            self.role_embedding = torch.nn.Parameter(
                torch.empty(ROLE_IDS, WIDTH, device=device, dtype=torch.float32))
            torch.nn.init.normal_(self.role_embedding, mean=0.0, std=1.0)
            self.pointer_key = torch.nn.Linear(WIDTH, WIDTH, bias=False).to(device)
            self.reach_option_head = torch.nn.Sequential(
                torch.nn.Linear(2 * WIDTH + 4, WIDTH, bias=False), torch.nn.GELU(),
                torch.nn.LayerNorm(WIDTH), torch.nn.Linear(WIDTH, REACH_OPTION_COUNT, bias=True)).to(device)
            # `3 * WIDTH`, and the whole point is that BOTH this head and the reshape in `_mode_options` used to
            # say `2 * WIDTH + 2 * WIDTH` -- they agreed with each other and disagreed with the tensor, which is
            # `cat((query_value, focus_world, target_world))` = three WIDTH-wide vectors. `_mode_options`'
            # docstring always described it correctly: "scored against `q`, the focus world vector and the target
            # world vector". Two places restating the same wrong number is why the guard pattern in this module
            # never caught anything: a check that recomputes the constant cannot detect the constant being wrong.
            # `_mode_options` now derives its width and checks it against this head, so the two cannot part again.
            self.mode_option_head = torch.nn.Sequential(
                torch.nn.Linear(3 * WIDTH, WIDTH, bias=False), torch.nn.GELU(),
                torch.nn.LayerNorm(WIDTH), torch.nn.Linear(WIDTH, MODE_OPTION_COUNT, bias=True)).to(device)
            self.world_head = torch.nn.Sequential(
                torch.nn.Linear(WORLD_CANDIDATE_WIDTH, WIDTH, bias=False), torch.nn.GELU(),
                torch.nn.LayerNorm(WIDTH), torch.nn.Linear(WIDTH, 1, bias=True)).to(device)
            require(len(list(self.named_parameters())) > len(PARAMETERS), "POINTER_CONTAINER_EMPTY")

        def core_block(self, value):
            """The registered `^6` arithmetic, as `_DecomposeTransform.forward` performs it."""
            left = getattr(self, BLOCK_NAMES["left.weight"])
            right = getattr(self, BLOCK_NAMES["right.weight"])
            merge = getattr(self, BLOCK_NAMES["merge.weight"])
            parts = torch.cat((torch.tanh(torch.nn.functional.linear(value, left)),
                               torch.tanh(torch.nn.functional.linear(value, right))), dim=-1)
            return torch.nn.functional.linear(parts, merge)

        def state_dict(self, *args, **kwargs):
            """The registered `^6` names, never the internal dot-free holders."""
            value = super().state_dict(*args, **kwargs)
            for name in PARAMETERS:
                holder = BLOCK_NAMES[name]
                if holder in value:
                    value[name] = value.pop(holder)
            require(all(name in value for name in PARAMETERS), "POINTER_STATE_BLOCK_NAMES")
            return value

        def load_state_dict(self, state_dict, strict=True, **kwargs):
            """Accept the registered `^6` names and translate them onto the internal holders."""
            body = dict(state_dict)
            for name in PARAMETERS:
                require(name in body, "POINTER_STATE_BLOCK_NAMES:" + name)
                body[BLOCK_NAMES[name]] = body.pop(name)
            return super().load_state_dict(body, strict=strict, **kwargs)

        def initial_block(self):
            """The three `^6` tensors exactly as `_framework` built them: the initialisation check."""
            return {name: start[name].detach().clone() for name in PARAMETERS}

        def preactivations(self, value):
            """The block's two pre-activation tensors for a 2-D input: `[W1 x, W2 tanh(W1 x)]`."""
            left = getattr(self, BLOCK_NAMES["left.weight"])
            right = getattr(self, BLOCK_NAMES["right.weight"])
            merge = getattr(self, BLOCK_NAMES["merge.weight"])
            first = torch.cat((torch.nn.functional.linear(value, left),
                               torch.nn.functional.linear(value, right)), dim=-1)
            second = torch.nn.functional.linear(torch.tanh(first), merge)
            return first, second

    return _PointerContainer()


# -------------------------------------------------------------------------------------------------------
# THE MESSAGE-PASSING CORE AND THE READOUTS THE HEADS READ. Every function here is a pure function of a
# reading (`pointer_inputs.read_packet`'s return value) plus tensors: no private packet data reaches it, and
# none of it conditions on a batch's `depth`.
# -------------------------------------------------------------------------------------------------------
def _row_rms(torch, value):
    """One RMS scalar per row over ALL of that row's features, clamped away from zero.

    The reading's own flags are small non-negative counts, so a PER-ROW scale keeps their relative sizes and
    brings the tensor to O(1) before the first linear map. Normalising per COLUMN would instead hand the block a
    z-score where a 1-flag is O(1) and a 0-flag is a large negative number, which is the wrong pre-activation
    regime for `tanh` (review section 5.6's saturation table).
    """
    require(value.dim() == 2, "POINTER_ROW_RMS")
    return torch.clamp(torch.sqrt(torch.mean(value * value, dim=1, keepdim=True)), min=RMS_EPSILON)


def _rms_unit(torch, value):
    """Per-node RMS normalisation: the placement review section 5.6 pins."""
    require(value.dim() == 2, "POINTER_RMS_UNIT")
    return value / _row_rms(torch, value)


def _block_width(model):
    """The registered `^6` block's INPUT width, read from the block's own weight, never from `WIDTH`.

    `WIDTH` is a module constant restating the second dimension of the registered `left.weight`; the
    registered tensors are the authority (`learner.PARAMETER_SHAPES`, `_DecomposeTransform.forward`), so every
    check that a tensor is the width the block consumes reads THIS and not the constant. The two are equal
    today and the point is that a check cannot detect the constant being wrong.
    """
    return int(getattr(model, BLOCK_NAMES["left.weight"]).shape[1])


def _degree_features(torch, adjacency):
    """`(one_hot, in_degree, out_degree)`: `[in-degree, out-degree]` one-hot, truncated at `DEGREE_STEPS - 1`.

    Not divided by the node count: the sorted (in-degree, out-degree) multiset is a complete isomorphism
    invariant on this corpus, and a mean would put the invariant back behind a division. Every bank world has at
    most 4 nodes and at most 3 children per node, so the truncation loses nothing here. The in-degree block
    comes FIRST, which is the order `IN_DEGREE_SUM_COLUMN` / `OUT_DEGREE_SUM_COLUMN` name.

    The two degree tensors are RETURNED as well as one-hot encoded, because `_graph_blocks` checks the two
    column offsets against them: a wrong offset is silent (it addresses a column that exists), so the check has
    to be against the degrees themselves -- and this function is the only place they are computed.
    """
    require(adjacency.dim() == 2 and adjacency.shape[0] == adjacency.shape[1], "POINTER_ADJACENCY_SHAPE")
    in_degree = torch.clamp(adjacency.sum(dim=0).to(torch.int64), max=DEGREE_STEPS - 1)
    out_degree = torch.clamp(adjacency.sum(dim=1).to(torch.int64), max=DEGREE_STEPS - 1)
    one_hot = torch.cat(
        (torch.nn.functional.one_hot(in_degree, num_classes=DEGREE_STEPS).to(adjacency.dtype),
         torch.nn.functional.one_hot(out_degree, num_classes=DEGREE_STEPS).to(adjacency.dtype)), dim=1)
    require(tuple(one_hot.shape) == (adjacency.shape[0], 2 * DEGREE_STEPS), "POINTER_DEGREE_FEATURES")
    return one_hot, in_degree, out_degree


def _graph_blocks(torch, reading, device):
    """`[[world_id, node_count, features, adjacency]]` for every world the reading carries, in sorted order.

    The feature row is, in this order and this width (`NODE_FEATURE_COUNT`): `is_declared_whole`,
    `is_participant` (its raw rank 1..3), `is_primary_label` (1..3; omitted when the rank branch is on),
    `is_whole_argument`, `is_part_argument` (query marks, which exist in the FOCUS world only), `is_focus`,
    `is_target`, then the two degree features. The row is RMS-normalised ONCE PER ROW. Nothing is derived from a
    node's ref beyond its list position, and the query marks are applied by LIST POSITION, which is the
    reading's own node order.
    """
    focus_world_id = reading["focus_world_id"]
    require(type(focus_world_id) is str, "POINTER_FOCUS_WORLD")
    whole_argument, part_argument = reading["query"]["whole"], reading["query"]["part"]
    blocks = []
    for world_id in _sorted_world_ids(reading):
        graph = reading["worlds"][world_id]
        node_count = graph["node_count"]
        require(node_count == len(graph["nodes"]) and node_count >= 1, "POINTER_NODE_COUNT")
        adjacency = torch.zeros(node_count, node_count, dtype=torch.float32, device=device)
        for source, target in graph["contains"]:
            require(0 <= source < node_count and 0 <= target < node_count, "POINTER_ADJACENCY_INDEX")
            adjacency[source, target] = 1.0
        rows = []
        for rank, node in enumerate(graph["nodes"]):
            is_focus = world_id == focus_world_id
            # EIGHT columns, written as ONE literal so the width is countable at the point of construction and
            # cannot drift by an appended element. The two query marks exist in the FOCUS world only, and are
            # applied by LIST POSITION, which is the reading's own node order and this block's row order.
            values = [
                float(node.get("is_declared_whole", 0)),
                float(node.get("is_participant", 0)),
                float(node["rank"]) if contract.DESIGN["node_rank_feature"]
                else float(node.get("is_primary_label", 0)),
                1.0 if (is_focus and whole_argument == rank) else 0.0,
                1.0 if (is_focus and part_argument == rank) else 0.0,
                float(graph["is_focus"]),
                float(graph["is_target"]),
                1.0,                                   # a constant bias column, never a reading fact
            ][:NODE_FEATURE_COUNT]
            if len(values) != NODE_FEATURE_COUNT:
                raise ValueError("TYPED_MATCHED:POINTER_NODE_FEATURE_WIDTH:%d" % len(values))
            rows.append(values)
        features = torch.tensor(rows, dtype=torch.float32, device=device).reshape(node_count,
                                                                                 NODE_FEATURE_COUNT)
        degree_one_hot, in_degree, out_degree = _degree_features(torch, adjacency)
        features = torch.cat((features, degree_one_hot), dim=1)
        require(features.shape[1] == NODE_ROW_WIDTH, "POINTER_NODE_FEATURE_WIDTH")
        # THE GUARD THAT ENDS THIS FAMILY FOR THE TWO DEGREE COLUMNS. Both constants are INDEXES into this row,
        # and a wrong index is SILENT: it addresses a column that exists and belongs to the other degree block,
        # so no width check can see it and the world head simply never receives an out-degree reading. So the
        # check is against the GRAPH and not against a restatement of the constants: each named block must be
        # the one-hot of the degree it is named for, computed one line above from this same `adjacency`.
        in_block = features[:, IN_DEGREE_SUM_COLUMN:IN_DEGREE_SUM_COLUMN + DEGREE_STEPS]
        out_block = features[:, OUT_DEGREE_SUM_COLUMN:OUT_DEGREE_SUM_COLUMN + DEGREE_STEPS]
        require(tuple(in_block.shape) == (node_count, DEGREE_STEPS)
                and tuple(out_block.shape) == (node_count, DEGREE_STEPS)
                and bool((in_block.sum(dim=1) == 1).all().item())
                and bool((out_block.sum(dim=1) == 1).all().item())
                and bool((in_block.argmax(dim=1) == in_degree).all().item())
                and bool((out_block.argmax(dim=1) == out_degree).all().item()),
                "POINTER_DEGREE_COLUMNS:" + world_id)
        blocks.append([world_id, node_count, _rms_unit(torch, features), adjacency])
    require(focus_world_id in [row[0] for row in blocks], "POINTER_FOCUS_WORLD")
    return blocks


def _query_vector(torch, reading, device):
    """`[kind one-hot, rule one-hot, whole, part, is_target, world_count]`: the 21-long query input."""
    query = reading["query"]
    kind, rule = query["kind"], query["rule"]
    require(type(kind) is int and 0 <= kind < KIND_COUNT, "POINTER_QUERY_KIND")
    require(type(rule) is int and 0 <= rule < RULE_COUNT, "POINTER_QUERY_RULE")
    values = [0.0] * KIND_COUNT + [0.0] * RULE_COUNT
    values[kind] = 1.0
    values[KIND_COUNT + rule] = 1.0
    world_count = query["world_count"]
    require(type(world_count) is int and world_count >= 1, "POINTER_QUERY_WORLD_COUNT")
    values.append(float(query["whole"]) if query["whole"] is not None else -1.0)
    values.append(float(query["part"]) if query["part"] is not None else -1.0)
    values.append(1.0 if query["target_world_id"] is not None else 0.0)
    values.append(min(world_count, 64) / 64.0)
    require(len(values) == QUERY_INPUT_WIDTH, "POINTER_QUERY_WIDTH")
    return torch.tensor(values, dtype=torch.float32, device=device).reshape(1, QUERY_INPUT_WIDTH)


def _block_input(torch, model, raw):
    """One round's `^6` input: a length-`WIDTH` vector per node.

    The three per-node halves of a round -- the normalised feature row, the normalised parent aggregate and the
    normalised child aggregate -- are each ENCODED by one shared learned matrix, then blended by a softmax over
    three round-shared scalars. So the registered `_DecomposeTransform` is called exactly as it is registered:
    once per node per round, on ONE `WIDTH`-long vector. The blend is the only place the round can decide how
    much of the node's own signal, of its parents' aggregate and of its children's aggregate to carry.

    The row width is `node_encode`'s OWN `in_features` and the split is `-1` where it can be, so the three
    restatements of `NODE_ROW_WIDTH` this function used to carry are gone: `model.node_encode(halves.reshape(-1,
    NODE_ROW_WIDTH))` would have failed on a row encoder built for a different width, but it would have failed
    with a reshape size, not with the layer that owns the width.
    """
    require(raw.dim() == 2, "POINTER_BLOCK_INPUT_WIDTH")
    row_width = int(model.node_encode.in_features)
    require(row_width == NODE_ROW_WIDTH and raw.shape[1] == 3 * row_width, "POINTER_BLOCK_INPUT_WIDTH")
    halves = raw.reshape(raw.shape[0], 3, -1)
    encoded = model.node_encode(halves.reshape(-1, row_width)).reshape(raw.shape[0], 3, -1)
    weights = torch.softmax(model.round_mix, dim=0)
    value = torch.einsum("nhw,h->nw", encoded, weights)
    require(value.shape == (raw.shape[0], _block_width(model)), "POINTER_BLOCK_INPUT_WIDTH")
    return value


def _rounds(torch, model, blocks, *, charge=None, observe=None):
    """K = CORE_ROUNDS shared rounds. `charge` is called once per round, for the counters.

    The round is `h <- h + cap * tanh(rate) * ^6([norm(h), norm(sum parents), norm(sum children)])`, with the
    three aggregates RMS-normalised AT THE INPUTS before the registered block. `depth` is not a parameter of
    this function and cannot reach the block through any argument.

    `observe(round_index, block_input)` is called once per round with the exact 2-D `^6` input as the block
    receives it (already projected to the block's width), which is how `pass0_saturation` measures the block's
    own pre-activations on the real geometry without a second copy of this loop.
    """
    counts = [row[1] for row in blocks]
    raw = torch.cat([row[2] for row in blocks], dim=0)
    block_width = _block_width(model)
    # The row encoder's OWN `in_features` is the check, and it has to be HERE: this is the first call that
    # consumes a raw feature row, so a row encoder built for a different row width would otherwise fail inside
    # torch's matmul -- `mat1 and mat2 shapes cannot be multiplied (244x18 and 19x64)` -- with a message that
    # names no layer, which is exactly how the node-head defect stayed hidden for a whole paid run.
    require(int(model.node_encode.in_features) == int(raw.shape[1]),
            "POINTER_NODE_ENCODE_WIDTH:%d!=%d" % (int(model.node_encode.in_features),
                                                  int(raw.shape[1])))
    hidden = _rms_unit(torch, model.node_encode(raw))
    require(hidden.shape == (sum(counts), block_width), "POINTER_ROUND_INITIAL_WIDTH")
    offsets, limit = [], 0
    for count in counts:
        offsets.append((limit, limit + count))
        limit += count
    require(limit == hidden.shape[0], "POINTER_ROUND_BLOCK")
    for round_index in range(CORE_ROUNDS):
        if charge is not None:
            charge(round_index)
        require(bool(torch.isfinite(hidden).all().item()), "POINTER_STATE_NONFINITE")
        inputs, parents, children = [], [], []
        for position, (start, stop) in enumerate(offsets):
            block = hidden[start:stop, :]
            raw = blocks[position][2]
            adjacency = blocks[position][3]
            # The three halves are NODE FEATURE rows, each RMS-normalised, then projected by one shared matrix.
            inputs.append(_rms_unit(torch, raw))
            parents.append(_rms_unit(torch, adjacency.matmul(raw)))
            children.append(_rms_unit(torch, adjacency.transpose(0, 1).matmul(raw)))
        # Worlds hold DIFFERENT node counts, so the per-node input and the two per-node messages are
        # concatenated row-by-row in world order rather than stacked square: row i of the result is
        # [norm(x_i), norm(sum parents_i), norm(sum children_i)] of one node of one world.
        heights = [row.shape[0] for row in inputs]
        block_input = torch.cat([torch.cat((inputs[index], parents[index], children[index]), dim=1)
                                 for index in range(len(inputs))], dim=0)
        require(block_input.shape == (sum(heights), BLOCK_INPUT_WIDTH), "POINTER_BLOCK_INPUT_WIDTH")
        # `_block_input` encodes and blends the three halves; the result is ONE width-WIDTH vector per node.
        hidden_input = _block_input(torch, model, block_input)
        require(hidden_input.shape == (block_input.shape[0], block_width), "POINTER_ROUND_MIX_WIDTH")
        if observe is not None:
            observe(round_index, hidden_input)
        update = model.core_block(hidden_input)
        hidden = _rms_unit(torch, hidden + PER_ROUND_UPDATE_CAP * torch.tanh(model.round_rate) * update)
    require(bool(torch.isfinite(hidden).all().item()), "POINTER_STATE_NONFINITE")
    return hidden


def _pair_rows(torch, blocks, device):
    """`(index_a, index_b, bit)` over every world's `n x n` ordered pairs, in block order.

    The pairs are enumerated exactly as `answer_space`'s `edge_pairs` does it, `[[a, b] for a in nodes for b in
    nodes]` (`checker.py:190-195` / `slots.py:104-105`), so one batched MLP over this tensor serves every
    `edge_account` slot in the packet and the plan's slot order IS this tensor's row order. The third return
    value is the `a -> b` adjacency BIT as a `long` index into the two-row pair embedding -- the empty edge is
    row 0 and the present edge is row 1, so the head is handed the bit as one extra input dimension and the
    bit still carries no gradient of its own.
    """
    left, right, bits = [], [], []
    limit = 0
    for block in blocks:
        count, adjacency = block[1], block[3]
        for index in range(count):
            for other in range(count):
                left.append(limit + index)
                right.append(limit + other)
                bits.append(1 if float(adjacency[index, other]) > 0.5 else 0)
        limit += count
    require(len(left) == sum(block[1] ** 2 for block in blocks)
            and all(bit in (0, 1) for bit in bits), "POINTER_PAIR_ROWS")
    index_a = torch.tensor(left, dtype=torch.int64, device=device)
    index_b = torch.tensor(right, dtype=torch.int64, device=device)
    bit = torch.tensor(bits, dtype=torch.int64, device=device)
    return index_a, index_b, bit


def _declaration_embeddings(torch, model, reading, world_ids, device):
    """`(names, embed)`: each world's four declarations embedded into `DECL_VECTOR_WIDTH`.

    A world's declaration field is a token-id list, so a value is `embed(one_hot(indices) @ table)`; no
    embedding lookup is performed. The LAST table row is reserved as the padding row and initialised to zero, so
    a short declaration pads with zeros rather than with a learned token.
    """
    names = list(DECLARATION_FIELDS)
    # ONE row block of `DECL_MAX_TOKENS` rows PER FIELD, shared by every world in the reading. A declaration
    # token is mapped to a row by a SORTED POSITION among the tokens that field names, so the table is a
    # function of the reading alone and two readings of the same packets agree. The LAST row of each block is
    # the padding row, held at zero.
    tokens = {field: [] for field in names}
    for world_id in world_ids:
        for field in names:
            ids = reading["worlds"][world_id]["declaration_ids"][field]
            require(type(ids) is list and ids, "POINTER_DECLARATION_TOKENS")
            require(all(type(value) is int and not isinstance(value, bool) and value >= 0 for value in ids),
                    "POINTER_DECLARATION_TOKEN")
            tokens[field].extend(ids)
    columns = {}
    for field in names:
        vocabulary = sorted(set(tokens[field]))
        require(0 < len(vocabulary) <= DECL_MAX_TOKENS - 1, "POINTER_DECLARATION_VOCABULARY:" + field)
        columns[field] = {token: position for position, token in enumerate(vocabulary)}
    shortened = []
    for world_id in world_ids:
        for field in names:
            ids = reading["worlds"][world_id]["declaration_ids"][field]
            seen = sorted({columns[field][token] for token in ids})
            shortened.append([position for position in seen[:DECL_MAX_TOKENS - 1]]
                             + [DECL_MAX_TOKENS - 1] * max(0, DECL_MAX_TOKENS - len(seen)))
    require(len(shortened) == len(world_ids) * DECLARATION_ROWS, "POINTER_DECLARATION_ROWS")
    require(all(len(row) == DECL_MAX_TOKENS for row in shortened), "POINTER_DECLARATION_ROWS")
    index = torch.tensor(shortened, dtype=torch.int64, device=device).reshape(
        len(world_ids), DECLARATION_ROWS, DECL_MAX_TOKENS)
    # A token id reaches 4000, so the index is a POSITION inside a per-field block, never a vocabulary id:
    # indexing a table by the raw token id would be an out-of-bounds read.
    require(int(index.min().item()) >= 0 and int(index.max().item()) < DECL_MAX_TOKENS,
            "POINTER_DECLARATION_INDEX")
    fields = torch.arange(DECLARATION_ROWS, dtype=torch.int64, device=device).reshape(1, DECLARATION_ROWS, 1)
    table = model.declaration_table.reshape(DECLARATION_ROWS, DECL_MAX_TOKENS, -1)
    # The table's row width is the width of the layer that consumes it, read from that layer.
    require(int(table.shape[-1]) == int(model.declaration_projection.in_features),
            "POINTER_DECLARATION_TABLE_WIDTH:%d!=%d" % (int(table.shape[-1]),
                                                        int(model.declaration_projection.in_features)))
    rows = table[fields.expand_as(index), index]
    require(rows.shape == (len(world_ids), DECLARATION_ROWS, DECL_MAX_TOKENS, table.shape[-1]),
            "POINTER_DECLARATION_ROWS")
    return names, model.declaration_projection(rows.sum(dim=2))


class GraphForward:
    """Everything one packet's forward produces, computed ONCE and shared by every head.

    `head_logits(plan)` returns `{slot_id: tensor}` with one logit per declared symbol in `slot["symbols"]`
    order, which is the shape `slots._check_scores` and `TypedCourseLearner._tensor_loss` both require. The
    structural heads read `hidden` -- the node states -- and the world heads read the degree-conditioned
    `worlds` vectors. The class holds tensors with a gradient path to the container, so the loss closes.
    """

    def __init__(self, torch, model, reading, device, *, charge=None):
        self.torch, self.model, self.reading, self.device = torch, model, reading, device
        self.blocks = _graph_blocks(torch, reading, device)
        self.world_ids = [row[0] for row in self.blocks]
        self.world_position = {world_id: index for index, world_id in enumerate(self.world_ids)}
        self.focus_world_id = reading["focus_world_id"]
        self.focus_position = self.world_position[self.focus_world_id]
        self.focus_offset = sum(row[1] for row in self.blocks[:self.focus_position])
        self.hidden = _rounds(torch, model, self.blocks, charge=charge)
        self.query = _query_vector(torch, reading, device)
        # Every head below is checked against the width THE LAYER OWNS, once, at the point the tensor is built.
        require(int(model.query_projection.in_features) == int(self.query.shape[1]),
                "POINTER_QUERY_HEAD_WIDTH:%d!=%d" % (int(model.query_projection.in_features),
                                                     int(self.query.shape[1])))
        self.query_value = self._encode_query()
        require(int(model.pointer_key.in_features) == int(self.query_value.shape[-1]),
                "POINTER_POINTER_KEY_WIDTH:%d!=%d" % (int(model.pointer_key.in_features),
                                                      int(self.query_value.shape[-1])))
        self.pointer_query = model.pointer_key(self.query_value)
        self.worlds = self._pooled_worlds()
        # The world vector is consumed by `matmul` against the query value and the pointer key, and by the
        # reach / mode / role / world-score concatenations, so its width has to BE the block width.
        require(int(model.world_projection.out_features) == _block_width(model)
                == int(self.query_value.shape[-1]),
                "POINTER_WORLD_VECTOR_WIDTH")
        self.declaration_names, self.declaration_embed = _declaration_embeddings(
            torch, model, reading, self.world_ids, device)
        index_a, index_b, adjacency_bit = _pair_rows(torch, self.blocks, device)
        self.pair_index = (index_a, index_b)
        pairs = self.hidden.index_select(0, index_a)
        others = self.hidden.index_select(0, index_b)
        edge_input = torch.cat((pairs, others, model.directed_pair_embedding[adjacency_bit]), dim=1)
        # The scalar was `int(value.shape[1]) == 2 * WIDTH + DIRECTED_PAIR_WIDTH`: it restated the head's own
        # construction, so it held while the head was right and could not have detected it being wrong. The
        # head's `in_features` is the number the forward pass actually has to satisfy.
        require(int(model.edge_head[0].in_features) == int(edge_input.shape[1]),
                "POINTER_EDGE_HEAD_WIDTH:%d!=%d" % (int(model.edge_head[0].in_features),
                                                    int(edge_input.shape[1])))
        self.edge_rows = model.edge_head(edge_input)
        node_input = torch.cat((self.hidden, self.query_value.reshape(1, -1).expand(
            self.hidden.shape[0], self.query_value.shape[-1])), dim=1)
        # THE GUARD THAT WOULD HAVE CAUGHT IT -- and the reason the first version did not. This line used to
        # assert only that `node_input` was `WIDTH + WIDTH` wide. That invariant HELD while the head was built for
        # `NODE_FEATURE_COUNT + WIDTH` and could not accept it, so the guard passed and the failure simply moved
        # one line down onto `model.node_head(node_input)` -- where it stayed hidden until the first real training
        # step on AWS (`mat1 and mat2 shapes cannot be multiplied (244x128 and 72x64)`). A guard that restates the
        # shape it was handed is not a check on the wiring. Comparing against the MODULE'S OWN `in_features` is.
        require(int(self.hidden.shape[1]) == int(self.query_value.shape[-1]),
                "POINTER_NODE_HEAD_INPUT")
        require(int(model.node_head[0].in_features) == int(node_input.shape[1]),
                "POINTER_NODE_HEAD_WIDTH:%d!=%d" % (int(model.node_head[0].in_features),
                                                    int(node_input.shape[1])))
        self.node_rows = model.node_head(node_input)

    def _encode_query(self):
        """The encoded query value, with the two focal argument marks' own node states spliced in.

        The whole argument is always a node of the FOCUS world, so its canonical rank indexes the focus world's
        slice directly. The marks' states are added IN ADDITION to the raw rank scalars in the 21-long vector,
        so a head that must relate two nodes is not asked to reconstruct a node state from an index.
        """
        torch, model = self.torch, self.model
        base = model.query_norm(model.query_projection(self.query)).reshape(-1)
        require(base.shape == (_block_width(model),), "POINTER_QUERY_STATE")
        value = base
        for argument in (self.reading["query"]["whole"], self.reading["query"]["part"]):
            if argument is None:
                continue
            require(type(argument) is int and 0 <= argument < self.blocks[self.focus_position][1],
                    "POINTER_QUERY_ARGUMENT")
            value = value + self.hidden[self.focus_offset + argument, :]
        require(bool(torch.isfinite(value).all().item()), "POINTER_QUERY_STATE")
        return value

    def _pooled_worlds(self):
        """`[mean, max, four degree/flag features, learned attention pool]` per world, projected to WIDTH.

        The raw width is `2 * WIDTH + 4` plus the attention pool, because the mean, the max AND the pool are
        each a full-width vector. All of them are kept and then projected together, so the head can use the
        mean and still reach the wiring through the max, the degree features and the pool.

        The four degree terms are the world's rows summed at the FIRST column of each degree block
        (`IN_DEGREE_SUM_COLUMN`, `OUT_DEGREE_SUM_COLUMN`) -- the in-degree and the out-degree count of nodes at
        that block's first value -- plus the same two divided by the node count. They are read from the columns
        `_graph_blocks` validates against the world's own adjacency.
        """
        torch, model = self.torch, self.model
        rows = []
        for position, block in enumerate(self.blocks):
            start = sum(row[1] for row in self.blocks[:position])
            state = self.hidden[start:start + block[1], :]
            features = block[2]
            require(int(model.attention_key.in_features) == int(state.shape[1]),
                    "POINTER_ATTENTION_KEY_WIDTH:%d!=%d" % (int(model.attention_key.in_features),
                                                            int(state.shape[1])))
            attention = torch.softmax(model.attention_key(state).reshape(-1), dim=0)
            pooled = (attention.reshape(-1, 1) * state).sum(dim=0)
            degrees = torch.stack([features[:, IN_DEGREE_SUM_COLUMN].sum(),
                                   features[:, OUT_DEGREE_SUM_COLUMN].sum(),
                                   features[:, IN_DEGREE_SUM_COLUMN].sum() / block[1],
                                   features[:, OUT_DEGREE_SUM_COLUMN].sum() / block[1]])
            rows.append(torch.cat((state.mean(dim=0), state.max(dim=0).values, degrees, pooled)))
        vector = torch.stack(rows)
        require(vector.shape[1] == WORLD_VECTOR_WIDTH, "POINTER_WORLD_VECTOR_WIDTH")
        # The projection's OWN input width is the authority: `WORLD_VECTOR_WIDTH` is the same number written
        # twice, so it cannot detect itself being wrong.
        require(int(model.world_projection.in_features) == int(vector.shape[1]),
                "POINTER_WORLD_VECTOR_WIDTH:%d!=%d" % (int(model.world_projection.in_features),
                                                       int(vector.shape[1])))
        return model.world_projection(vector)
    # ---- node-level heads: the structural answers ----
    def _node_options(self, position, ranks):
        """`logit = <pointer key, h_v>` for the named node ranks of ONE world, in the given order."""
        torch = self.torch
        require(type(ranks) is list and len(set(ranks)) == len(ranks), "POINTER_NODE_RANKS")
        start = sum(row[1] for row in self.blocks[:position])
        count = self.blocks[position][1]
        require(all(0 <= rank < count for rank in ranks), "POINTER_NODE_RANKS")
        if not ranks:
            return self.hidden.new_zeros(0)
        states = self.hidden.index_select(
            0, torch.tensor([start + rank for rank in ranks], dtype=torch.int64, device=self.device))
        return states.matmul(self.pointer_query)

    def _reach_options(self, position):
        """The always-available `reach` options: `ABSENT`, `DIRECT`, then one pointer per candidate node."""
        torch, model = self.torch, self.model
        features = self.blocks[position][2]
        count = self.blocks[position][1]
        degrees = torch.stack([features[:, IN_DEGREE_SUM_COLUMN].sum(),
                               features[:, OUT_DEGREE_SUM_COLUMN].sum(),
                               features[:, IN_DEGREE_SUM_COLUMN].sum() / count,
                               features[:, OUT_DEGREE_SUM_COLUMN].sum() / count])
        value = torch.cat((self.query_value, self.worlds[position], degrees)).reshape(1, -1)
        # DERIVED, NEVER RESTATED. This reshape used to say `2 * WIDTH + 4`, i.e. the same number the head was
        # built from -- a check that cannot detect that number being wrong, which is the whole lesson of the
        # width defects in this module. `-1` plus the head's own `in_features` has no second number to drift.
        require(int(model.reach_option_head[0].in_features) == int(value.shape[1]),
                "POINTER_REACH_OPTION_HEAD_WIDTH:%d!=%d"
                % (int(model.reach_option_head[0].in_features), int(value.shape[1])))
        return model.reach_option_head(value).reshape(-1)

    def _mode_options(self, position):
        """`NO_MATCH` and `MAPPING` scored against `q`, the focus world vector and the target world vector."""
        torch, model = self.torch, self.model
        value = torch.cat((self.query_value, self.worlds[self.focus_position],
                           self.worlds[position])).reshape(1, -1)
        # DERIVED, NEVER RESTATED. This line used to reshape to `2 * WIDTH + 2 * WIDTH` = 256 while concatenating
        # THREE WIDTH-wide tensors = 192, so the first mode-option scoring on a real run raised
        # `shape '[1, 256]' is invalid for input of size 192`. `-1` plus a check against the head's own
        # `in_features` has no second number to drift from -- which is the whole lesson of the four other width
        # defects in this module. The sibling `_reach_options` directly above was always right (`2 * WIDTH + 4`
        # for two vectors and the four degree terms), which is what marks this one as the outlier.
        require(int(value.shape[1]) == int(model.mode_option_head[0].in_features),
                "POINTER_MODE_OPTION_HEAD_WIDTH:%d!=%d" % (int(value.shape[1]),
                                                           int(model.mode_option_head[0].in_features)))
        return model.mode_option_head(value).reshape(-1)

    def _world_scores(self, field, symbols):
        """Every symbol that names a whole world, scored on `(query, source, candidate, declaration)`.

        The candidate term is `[query key @ candidate, query value @ candidate, four flags, declaration]`, so the
        scorer sees the candidate's degree-conditioned world vector AND the declaration text of the field the
        slot asks about -- the shape and the domain together, which is what `analogy` needs (17 of 17 held).
        """
        torch = self.torch
        column = self.declaration_names.index(SLOT_DECLARATION_FIELD.get(field, "domain"))
        key = self.worlds.matmul(self.pointer_query)
        value = self.worlds.matmul(self.query_value)
        flags = torch.zeros(self.worlds.shape[0], 4, dtype=torch.float32, device=self.device)
        for position, world_id in enumerate(self.world_ids):
            flags[position, 0] = 1.0 if world_id == self.focus_world_id else 0.0
            flags[position, 1] = float(self.reading["worlds"][world_id]["is_target"])
        candidate = torch.cat((key.reshape(-1, 1), value.reshape(-1, 1), flags,
                               self.declaration_embed[:, column, :]), dim=1)
        require(candidate.shape[1] == WORLD_CANDIDATE_WIDTH, "POINTER_WORLD_CANDIDATE_WIDTH")
        # And the head's own input width, which is the check that can fail: `WORLD_CANDIDATE_WIDTH` is the same
        # number the head was built from, so agreeing with it is not evidence. This was defect 2 of the six.
        require(int(self.model.world_head[0].in_features) == int(candidate.shape[1]),
                "POINTER_WORLD_HEAD_WIDTH:%d!=%d" % (int(self.model.world_head[0].in_features),
                                                     int(candidate.shape[1])))
        flat = self.model.world_head(candidate).reshape(-1)
        rows = []
        for symbol in symbols:
            if symbol == "NO_MATCH":
                rows.append(flat.new_zeros(()))
            else:
                world_id = _world_alias_table_for(self.reading, symbol)
                require(world_id in self.world_position, "POINTER_WORLD_NOT_IN_READING")
                rows.append(flat[self.world_position[world_id]])
        return torch.stack(rows)

    # ---- the branch table ----
    def head_logits(self, plan, indicators=None):
        """`{slot_id: tensor}`, one logit per declared symbol in `slot["symbols"]` order."""
        torch = self.torch
        require(type(indicators) is list and len(indicators) == CLAUSE_COUNT, "POINTER_ROLE_INDICATORS")
        indicator = torch.tensor(indicators, dtype=torch.float32, device=self.device)
        rows = {}
        for slot in plan["slots"]:
            field, symbols = slot["field"], list(slot["symbols"])
            coordinates = slot["coordinates"]
            if field in ("node", "participant"):
                require(len(coordinates) == 1, "POINTER_SLOT_COORDINATES")
                logits = self.node_rows[self.focus_offset + _node_rank_of_ref(coordinates[0])]
            elif field == "role":
                # The role is a FIXED world-independent category, so the slot's own coordinate IS the role id
                # and the head is `MLP[q, g_focus, E_role[r], role indicator]`: a 2-way yes/no over one role.
                require(len(coordinates) == 1 and type(coordinates[0]) is int
                        and not isinstance(coordinates[0], bool) and 0 < coordinates[0] <= ROLE_IDS,
                        "POINTER_SLOT_COORDINATES")
                value = torch.cat((indicator, self.query_value, self.worlds[self.focus_position],
                                   self.model.role_embedding[coordinates[0] - 1])).reshape(1, -1)
                # DERIVED, NEVER RESTATED. The reshape used to say `3 * WIDTH + CLAUSE_COUNT`, which is the
                # number `role_head` was itself built from: two restatements of one hand-written width agree with
                # each other and disagree with the tensor, which is exactly how defect 4 reached a paid run.
                require(int(self.model.role_head[0].in_features) == int(value.shape[1]),
                        "POINTER_ROLE_HEAD_WIDTH:%d!=%d" % (int(self.model.role_head[0].in_features),
                                                            int(value.shape[1])))
                logits = self.model.role_head(value).reshape(-1)
            elif field == "whole":
                logits = self._node_options(self.focus_position,
                                            [_node_rank_of_alias(symbol) for symbol in symbols])
            elif field == "mapping_target":
                logits = self._node_options(self._target_position(),
                                            [_node_rank_of_alias(symbol) for symbol in symbols])
            elif field == "reach":
                nodes = [_via_rank(symbol) for symbol in symbols if symbol.startswith("VIA_N")]
                require(symbols[:REACH_OPTION_COUNT] == ["ABSENT", "DIRECT"]
                        and symbols[REACH_OPTION_COUNT:] == ["VIA_N%d" % rank for rank in nodes],
                        "POINTER_REACH_SYMBOLS")
                logits = torch.cat((self._reach_options(self.focus_position),
                                    self._node_options(self.focus_position, nodes)))
            elif field == "edge":
                require(len(coordinates) == 2, "POINTER_SLOT_COORDINATES")
                logits = self.edge_rows[self._edge_pair_index(plan, coordinates)]
            elif field == "mode":
                logits = self._mode_options(self._target_position())
            elif field in WORLD_CHOICE_FIELDS:
                logits = self._world_scores(field, symbols)
            else:
                raise ValueError("TYPED_MATCHED:POINTER_SLOT_FIELD_UNSUPPORTED:" + str(field))
            require(tuple(logits.shape) == (len(symbols),), "POINTER_SLOT_LOGITS:" + str(slot["slot_id"]))
            require(bool(torch.isfinite(logits).all().item()), "POINTER_LOGITS_NONFINITE")
            rows[slot["slot_id"]] = logits
        require(len(rows) == len(plan["slots"]), "POINTER_SLOT_COVERAGE")
        return rows

    def _target_position(self):
        """The reading position of the correspondence target world, which must be in the reading."""
        target = self.reading["query"]["target_world_id"]
        require(type(target) is str and target in self.world_position, "POINTER_TARGET_WORLD")
        return self.world_position[target]

    def _edge_pair_index(self, plan, coordinates):
        """The `edge_rows` ROW of one `[a, b]` pair. `edge_rows` is global; the plan's pair list is not.

        `_pair_rows` builds `edge_rows` over EVERY world's `n x n` ordered pairs in block order, so the row a
        pair actually occupies is `offset(focus) + a * n_focus + b`. This method used to return the pair's
        position inside the plan's own `edge` slot list, which is `a * n_focus + b` alone -- an index into a
        DIFFERENT tensor's numbering. It is correct today only because every `edge_account` reading happens to
        carry exactly the focus world, so `offset(focus)` is 0 and the focus world is block 0 (measured over all
        564 registry packets). Nothing raised and nothing could: the wrong index addresses a row that exists.

        The row is therefore recovered from `pair_index` -- the tensor's OWN enumeration, the very tensors the
        head consumed -- and not from a second restatement of the plan's order. `focus_offset + rank` is the
        same node-row convention `head_logits` uses for the `node` and `participant` heads.
        """
        pairs = [[slot["coordinates"][0], slot["coordinates"][1]] for slot in plan["slots"]
                 if slot["field"] == "edge"]
        require(pairs == sorted(pairs), "POINTER_EDGE_PAIR_ORDER")
        target = list(coordinates)
        require(target in pairs, "POINTER_EDGE_PAIR")
        ranks = [_node_rank_of_ref(ref) for ref in target]
        require(all(0 <= rank < self.blocks[self.focus_position][1] for rank in ranks),
                "POINTER_EDGE_PAIR")
        index_a, index_b = self.pair_index
        wanted = (self.focus_offset + ranks[0], self.focus_offset + ranks[1])
        matches = [position for position in range(len(index_a))
                   if int(index_a[position]) == wanted[0] and int(index_b[position]) == wanted[1]]
        require(len(matches) == 1, "POINTER_EDGE_PAIR_ROW:%s" % (wanted,))
        return matches[0]


def _world_alias_table_for(reading, symbol):
    """`W7` -> that slot's world id, via the reading's own sorted alias order.

    `slots.alias_table` emits `W0..W63` by sorted exact world_id and every world-choice symbol list is built
    from that same sorted table (`slots.py:88-95`, `:107`), so the reading's sorted world order IS the alias
    order. The map is rebuilt from the reading rather than from a plan because `head_logits` is also reachable
    without the plan; a symbol that is not an alias fails closed.
    """
    require(type(symbol) is str and re.fullmatch(r"W[0-9]+", symbol) is not None, "POINTER_WORLD_ALIAS")
    index = int(symbol[1:])
    ids = sorted(reading["worlds"])
    require(0 <= index < len(ids), "POINTER_WORLD_ALIAS")
    return ids[index]


def _scalar_scores(torch, rows):
    """`{slot_id: {symbol: float}}` from the tensor bundle, refused outside the registered score bound."""
    scores = {}
    for slot_id, logits in rows.items():
        require(bool(torch.isfinite(logits).all().item()), "POINTER_LOGITS_NONFINITE")
        values = [float(value) for value in logits.detach().cpu().tolist()]
        require(all(abs(value) <= MAX_ABS_SCORE for value in values), "POINTER_SCORE_BOUND:" + str(slot_id))
        scores[slot_id] = values
    return scores


def _logit_rows(torch, plan, rows):
    """`{slot_id: {symbol: float}}` in the plan's declared symbol order.

    The signature used to carry a fourth, unused `symbols` parameter -- nothing in the body ever read it; the
    symbol names come from `slot["symbols"]` and the values from `rows[slot["slot_id"]]`. Every caller passes
    three arguments, so the stale parameter made the FIRST PREDICTION fail outright with
    `TypeError: _logit_rows() missing 1 required positional argument: 'rows'`, after the model had built, after
    phase A had completed, and after training had begun -- it cost a fourth AWS run to find. Removed rather than
    satisfied at the call site: the four other width bugs in this module all came from a declaration drifting
    away from what the code actually does, and inventing a value for a parameter nobody reads would be the same
    mistake in a new place.
    """
    result = {}
    for slot in plan["slots"]:
        values = rows[slot["slot_id"]]
        require(len(values) == len(slot["symbols"]), "POINTER_SLOT_SYMBOL_COVERAGE")
        result[slot["slot_id"]] = {symbol: values[index]
                                   for index, symbol in enumerate(slot["symbols"])}
    return result


def _validate_init_args(value, device):
    """Refuse any recorded `init_args` that is not exactly the recorded, typed set."""
    require(type(value) is dict and set(value) == set(INIT_ARGS_FIELDS), "POINTER_INIT_ARGS_FIELDS")
    require(type(value["python_seed"]) is int and 0 <= value["python_seed"] < 2 ** 63,
            "POINTER_INIT_ARGS_SEED")
    require(type(value["device"]) is str and value["device"] == device, "POINTER_INIT_ARGS_DEVICE")
    require(type(value["root"]) is str and Path(value["root"]).is_dir(), "POINTER_INIT_ARGS_ROOT")
    require(type(value["run_context"]) is dict and type(value["limits"]) is dict,
            "POINTER_INIT_ARGS_TYPES")
    return deepcopy(value)


def _require_cuda_device(torch, device):
    """The run's device demand, in ONE place: a `cuda` device string on a machine with a live CUDA runtime.

    This is the two identical copies that stood in `PointerCourseLearner.__init__` and `restore_checkpoint`,
    extracted unchanged: same pattern, same `TYPED_LEARNER_CUDA_REQUIRED` code, same order after
    `execution_guard()`. No CPU fallback is added and none is admitted -- the demand is unchanged and still
    fails closed. What the extraction buys is a NAMED seam, so the CPU round-trip test can bypass the hardware
    demand exactly the way the harness already bypasses `execution_guard()`, instead of editing this file or
    relying on a real `torch.device("cuda:0")` on a box with no CUDA runtime (which cannot carry a tensor).
    """
    require(re.fullmatch(r"cuda(?::[0-9]+)?", str(device)) is not None and torch.cuda.is_available(),
            "TYPED_LEARNER_CUDA_REQUIRED")


# -------------------------------------------------------------------------------------------------------
# THE LEARNER.
# -------------------------------------------------------------------------------------------------------
class PointerCourseLearner:
    """The pointer study's learner. Mirrors `TypedCourseLearner`'s public contract, subclasses nothing.

    `framework` is the object `cncm.typed_matched_worker._framework(torch, device, seed)` returned; it is built
    FIRST by the caller. `encoder` is the frozen typed encoder, kept alive on `self.encoder` even though this
    learner never encodes a packet, because `typed_course_worker._state`, `_check_state` and
    `export_state` read it (`INTERFACE_SPEC_SHARED.md` C.4). `tagger` is optional on the first construction and
    is restored by `restore_checkpoint` from the recorded root; when it is `None`, a `role_set` record fails
    closed with `POINTER_ROLE_TAGGER_REQUIRED` rather than being scored without its clause indicator.
    """

    def __init__(self, torch, framework, encoder, *, optimizer_config, run_context, limits, device,
                 tagger, python_seed, root):
        from ..teaching_cycle.gpu_adapter import execution_guard
        execution_guard()
        _require_cuda_device(torch, device)
        self.torch = torch
        self.framework = framework
        self.device = (torch.device("cuda", torch.cuda.current_device())
                       if str(device) == "cuda" else torch.device(device))
        require(type(python_seed) is int and 0 <= python_seed < 2 ** 63, "POINTER_PYTHON_SEED")
        require(type(root) is str and Path(root).is_dir(), "POINTER_ROOT")
        self.root = str(Path(root).resolve())
        self.python_seed = python_seed
        self.tagger = tagger
        # ONE container. `scope_parameters` is never called on it (review RK2).
        self.module = _build_container(torch, framework, self.device)
        # The scope record is the container's own parameter list under the REGISTERED names, and it records
        # that the shared freeze was deliberately not applied.
        registered = _registered_names(self.module)
        parameters = dict(self.module.named_parameters())
        self.scope = {
            "allowed": sorted(registered[name] for name, parameter in parameters.items()
                              if parameter.requires_grad),
            "frozen": sorted(registered[name] for name, parameter in parameters.items()
                             if not parameter.requires_grad),
            "contract_id": "cas.cjt.operation.^6.decompose/0.2", "role": "operation:^6",
            "call": "NOT_CALLED_ON_THE_POINTER_CONTAINER",
        }
        require(set(self.scope["allowed"]) == set(self.module.state_dict())
                and not self.scope["frozen"], "POINTER_CONTAINER_SCOPE")
        require(set(PARAMETERS) <= set(self.scope["allowed"]), "POINTER_CONTAINER_BLOCK_SCOPE")
        self.encoder = encoder
        encoder.verify_frozen()
        parameters = dict(self.module.named_parameters())
        require(all(parameter.device == self.device and parameter.dtype == torch.float32
                    and parameter.requires_grad for parameter in parameters.values()),
                "POINTER_PARAMETER_DEVICE")
        require(all(tuple(parameters[BLOCK_NAMES[name]].shape) == PARAMETER_SHAPES[name]
                    for name in PARAMETERS)
                and tuple(encoder.readout_rows.shape) == (90, 64)
                and not encoder.readout_rows.requires_grad, "POINTER_PARAMETER_SHAPE")
        require(type(optimizer_config) is dict
                and set(optimizer_config) == {"learning_rate", "weight_decay", "betas", "eps"},
                "TYPED_OPTIMIZER_FIELDS")
        require(type(optimizer_config["betas"]) is list and len(optimizer_config["betas"]) == 2,
                "TYPED_OPTIMIZER_BETAS")
        values = [optimizer_config["learning_rate"], optimizer_config["weight_decay"],
                  optimizer_config["eps"], *optimizer_config["betas"]]
        require(all(type(value) in (int, float) and math.isfinite(value) for value in values)
                and 0 < values[0] <= 1 and 0 <= values[1] <= 1 and 0 < values[2] <= 1
                and all(0 <= value < 1 for value in values[3:]), "TYPED_OPTIMIZER_RANGE")
        require(type(limits) is dict and set(limits) == {"max_updates", "max_core_calls", "max_wall_seconds"}
                and type(limits["max_updates"]) is int and 0 < limits["max_updates"] <= MAX_UPDATES_CEILING
                and type(limits["max_core_calls"]) is int and 0 < limits["max_core_calls"] <= 1000000
                and type(limits["max_wall_seconds"]) in (int, float)
                and 0 < limits["max_wall_seconds"] <= 86400, "TYPED_LEARNER_LIMITS")
        require(type(run_context) is dict
                and set(run_context) == {"run_id", "course_sha256", "condition", "source_seed"}
                and type(run_context["run_id"]) is str
                and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_context["run_id"])
                and type(run_context["course_sha256"]) is str
                and re.fullmatch("[0-9a-f]{64}", run_context["course_sha256"])
                and run_context["condition"] in CONDITIONS
                and type(run_context["source_seed"]) is int
                and run_context["source_seed"] in SOURCE_SEEDS, "TYPED_LEARNER_RUN_CONTEXT")
        self.optimizer_config, self.limits = deepcopy(optimizer_config), deepcopy(limits)
        self.optimizer = torch.optim.AdamW(list(self.module.parameters()),
                                           lr=optimizer_config["learning_rate"],
                                           weight_decay=optimizer_config["weight_decay"],
                                           betas=tuple(optimizer_config["betas"]),
                                           eps=optimizer_config["eps"], foreach=False, fused=False,
                                           capturable=False)
        self.run_identity = {
            "context": deepcopy(run_context), "learner_profile": profile(),
            "encoder_identity": deepcopy(encoder.identity),
            "initial_model_identity": state_identity(torch, dict(self.module.state_dict())),
            "scope": deepcopy(self.scope), "optimizer_config": deepcopy(optimizer_config),
            "limits": deepcopy(limits),
            "initialization": "BUILT_BY_cncm.typed_matched_worker._framework_TORCH_DEFAULT_SCHEME",
            "core_rounds": CORE_ROUNDS, "readout": profile()["readout"],
            "head_set": sorted(SCORED_FIELDS), "counters": list(COUNTER_KEYS),
            "counter_units": dict(COUNTER_UNITS), "depth_is_not_an_input": True,
            "prediction_depth": PREDICTION_DEPTH,
            "normalisation_placement": profile()["normalisation_placement"],
            "round_parameters_shared": True, "dense_and_one_hot_only": True,
            "scored_fields": sorted(SCORED_FIELDS), "measured_pooling": deepcopy(MEASURED_POOLING),
            "measured_stability": deepcopy(MEASURED_STABILITY),
        }
        require(set(self.run_identity) == set(RUN_IDENTITY_FIELDS), "POINTER_RUN_IDENTITY_FIELDS")
        self.run_identity_digest = digest(self.run_identity)
        self.cursor = self.model_revision = 0
        self.counters = {key: 0 for key in COUNTER_KEYS}
        self._pending, self.failed = None, False
        self._started, self._elapsed_before = time.monotonic(), 0.0

    # ---- bookkeeping ----
    def _elapsed(self):
        return self._elapsed_before + time.monotonic() - self._started

    def _budget(self):
        require(not self.failed and self._elapsed() <= self.limits["max_wall_seconds"],
                "TYPED_LEARNER_FAILED_OR_WALL_BUDGET")

    def _charge_round(self, _round_index):
        """One core invocation: an attempt, a call, and one charged sample pass."""
        self.counters["core_forward_attempts"] += 1
        self.counters["core_forward_calls"] += 1
        self.counters["sample_core_passes"] += 1

    def _check_core_budget(self, planned):
        require(self.counters["core_forward_attempts"] + planned <= self.limits["max_core_calls"],
                "TYPED_LEARNER_FORWARD_BUDGET")

    def _tag(self, packet):
        """The `role_set` clause indicator of one packet. Fails closed when the tagger was not restored."""
        require(self.tagger is not None, "POINTER_ROLE_TAGGER_REQUIRED")
        return self.tagger.indicators(packet)

    def _graph(self, packet):
        """One packet's forward. `torch` is imported HERE, so importing this module does no numeric work."""
        import torch
        self._budget()
        self.encoder.verify_frozen()
        require(type(packet) is dict and type(packet.get("source")) is dict
                and type(packet.get("record")) is dict, "POINTER_PACKET")
        from . import slots
        plan = slots.compile_slots(packet)
        reading = pointer_inputs.read_packet(packet)
        reading["_device"] = self.device
        require(reading["record_id"] == plan["record_id"], "POINTER_READING_RECORD")
        self._check_core_budget(CORE_ROUNDS)
        self.counters["packet_forward_calls"] += 1
        forward = GraphForward(torch, self.module, reading, self.device, charge=self._charge_round)
        indicators = (self._tag(packet) if reading["query"]["kind_name"] == "role_set"
                      else [0] * CLAUSE_COUNT)
        rows = forward.head_logits(plan, indicators)
        values = _scalar_scores(torch, rows)
        scores = _logit_rows(torch, plan, values)
        require(set(scores) == {slot["slot_id"] for slot in plan["slots"]}, "POINTER_SLOT_COVERAGE")
        decisions = slots.score_decisions(packet, scores)
        answer = slots.assemble_answer(packet, decisions)
        body = {"schema": PREDICTION_SCHEMA, "record_id": plan["record_id"],
                "packet_digest": plan["packet_digest"], "slot_plan_digest": plan["plan_digest"],
                "depth": PREDICTION_DEPTH, "model_revision": self.model_revision,
                "run_context_digest": self.run_identity_digest,
                "encoder_identity_digest": digest(self.encoder.identity), "scores": scores,
                "decisions": decisions, "answer": answer}
        prediction = {**body, "prediction_id": "typed-prediction-" + digest(body)}
        require(set(prediction) == PREDICTION_FIELD_SET, "POINTER_PREDICTION_FIELDS")
        self.counters["prediction_calls"] += 1
        return {"packet": packet, "prediction": prediction, "plan": plan, "rows": rows,
                "forward": forward}

    # ---- the public contract ----
    def predict(self, packet, depth):
        """Public-only inference, one fixed depth. `depth` is checked, recorded as a coordinate, unused."""
        require(self._pending is None, "TYPED_LEARNER_PENDING_BATCH")
        require(type(depth) is int and depth in (1, 2, 4, 8), "TYPED_LEARNER_DEPTH")
        require(depth == PREDICTION_DEPTH, "POINTER_PREDICTION_DEPTH")
        self.module.eval()
        with self.torch.no_grad():
            result = self._graph(packet)
        return result["prediction"]

    def stage_batch(self, packets, depth, *, cursor, occurrence_ids):
        """Retain autograd, return public bytes for the caller to durably seal BEFORE any target is derived.

        `depth` is a schedule coordinate and nothing else: it is validated, and never passed to the forward,
        which is how `depth` is structurally unable to reach a head (review LK18).
        """
        self._budget()
        require(self._pending is None and type(cursor) is int and cursor == self.cursor
                and self.counters["optimizer_updates"] < self.limits["max_updates"],
                "TYPED_LEARNER_BATCH_CURSOR_OR_BUDGET")
        require(type(depth) is int and depth in (1, 2, 4, 8), "TYPED_LEARNER_DEPTH")
        require(type(packets) is list and 0 < len(packets) <= 8 and type(occurrence_ids) is list
                and len(occurrence_ids) == len(packets)
                and len(set(occurrence_ids)) == len(occurrence_ids)
                and all(type(value) is str and re.fullmatch(r"typed-occurrence-[0-9a-f]{64}", value)
                        for value in occurrence_ids), "TYPED_LEARNER_BATCH_SHAPE")
        self.encoder.verify_frozen()
        self.module.train()
        self.optimizer.zero_grad(set_to_none=True)
        results = [self._graph(packet) for packet in packets]
        body = {"schema": BATCH_SCHEMA, "cursor": cursor, "model_revision": self.model_revision,
                "run_identity_digest": self.run_identity_digest,
                "occurrence_ids": deepcopy(occurrence_ids),
                "predictions": [result["prediction"] for result in results]}
        public = {**body, "batch_id": "typed-batch-" + digest(body)}
        raw = (canonical(public) + "\n").encode()
        self._pending = {"results": results, "public": public, "raw": raw,
                         "model_identity": state_identity(self.torch, dict(self.module.state_dict()))}
        self.counters["staged_batches"] += 1
        return {"public": deepcopy(public), "bytes": raw, "sha256": sha256(raw).hexdigest()}

    def _tensor_loss(self, plan, loss, tensors):
        """`TypedCourseLearner._tensor_loss`, CALLED so the joint correspondence loss is unchanged."""
        return TypedCourseLearner._tensor_loss(self, plan, loss, tensors)

    def train_sealed_batch(self, path, *, expected_sha256, target_receipts):
        """Read the exact durable public seal BEFORE accessing private targets, then update.

        The gradient gate is the RK1 replacement: finiteness is required only on the parameters that actually
        received a gradient, at least ONE parameter must have received one, and the parameter names that did
        are recorded per update. `optimizer.zero_grad(set_to_none=True)` leaves `p.grad is None` for a head no
        field of the batch touched, and AdamW with a `None` gradient applies NEITHER an update NOR a weight-decay
        term to that parameter for that step -- so a kind that was absent from a batch is simply not trained by
        it, which is the whole point of the replacement.
        """
        self._budget()
        require(self._pending is not None, "TYPED_LEARNER_NO_PENDING_BATCH")
        seal = Path(path)
        require(seal.is_file() and not seal.is_symlink() and seal.stat().st_size <= 16 * 1024 * 1024,
                "TYPED_LEARNER_SEAL_PATH")
        raw = seal.read_bytes()
        require(type(expected_sha256) is str and sha256(raw).hexdigest() == expected_sha256
                and raw == self._pending["raw"], "TYPED_LEARNER_SEAL_MISMATCH")
        require(state_identity(self.torch, dict(self.module.state_dict()))
                == self._pending["model_identity"], "TYPED_LEARNER_MODEL_CHANGED_AFTER_PREDICTION")
        self.encoder.verify_frozen()
        # No target object has been iterated or validated before this point.
        from . import loss_plan
        require(type(target_receipts) is list and len(target_receipts) == len(self._pending["results"]),
                "TYPED_LEARNER_TARGET_COUNT")
        tasks, reports, loss_ids = [], [], []
        try:
            for result, target in zip(self._pending["results"], target_receipts):
                packet, plan, rows = result["packet"], result["plan"], result["rows"]
                prediction_raw = (canonical(result["prediction"]) + "\n").encode()
                self.counters["private_loss_plan_calls"] += 1
                loss = loss_plan.compile_loss_plan(
                    packet, target, sealed_prediction_bytes=prediction_raw,
                    expected_prediction_sha256=sha256(prediction_raw).hexdigest())
                task, report = self._tensor_loss(plan, loss, rows)
                scalar = loss_plan.scalar_report(packet, loss, result["prediction"]["scores"])
                require(math.isclose(report["raw_task_loss"], scalar["raw_task_loss"], rel_tol=2e-5,
                                     abs_tol=2e-5), "TYPED_LEARNER_SCALAR_TENSOR_LOSS_MISMATCH")
                report.update({"record_id": plan["record_id"], "loss_plan_digest": loss["loss_plan_digest"],
                               "admissible_answer_count": loss["admissible_answer_count"]})
                tasks.append(task)
                reports.append(report)
                loss_ids.append(loss["loss_plan_digest"])
            self._budget()
            total = self.torch.stack(tasks).mean()
            self.counters["backward_attempts"] += 1
            total.backward()
            self.counters["backward_calls"] += 1
            parameters = dict(self.module.named_parameters())
            trained = sorted(name for name, parameter in parameters.items()
                             if parameter.grad is not None)
            require(trained, "POINTER_GRADIENTS_ABSENT")
            require(all(bool(self.torch.isfinite(parameters[name].grad).all().item())
                        for name in trained), "TYPED_LEARNER_GRADIENTS")
            gradient_squared = sum(float((parameters[name].grad.detach()
                                         * parameters[name].grad.detach()).sum().cpu().item())
                                   for name in trained)
            require(math.isfinite(gradient_squared), "TYPED_LEARNER_GRADIENT_NORM_NONFINITE")
            self._budget()
            self.counters["optimizer_step_attempts"] += 1
            self.optimizer.step()
            self.counters["optimizer_updates"] += 1
            require(all(bool(self.torch.isfinite(parameter).all().item())
                        for parameter in parameters.values()), "TYPED_LEARNER_PARAMETERS_NONFINITE")
            self.encoder.verify_frozen()
            self.cursor += 1
            self.model_revision += 1
            result = {"schema": UPDATE_SCHEMA,
                      "batch_id": self._pending["public"]["batch_id"],
                      "public_seal_sha256": expected_sha256, "cursor_committed": self.cursor,
                      "model_revision": self.model_revision, "tasks": reports,
                      "raw_batch_loss": sum(row["raw_task_loss"] for row in reports) / len(reports),
                      "normalized_batch_loss": sum(row["normalized_task_loss"] for row in reports)
                      / len(reports),
                      "training_uses": "raw_batch_loss", "gradient_squared_norm": gradient_squared,
                      "loss_plan_digests": loss_ids, "counters": deepcopy(self.counters),
                      "gradient_parameter_names": trained,
                      "gradient_parameter_count": len(trained),
                      "gradient_parameter_total": len(parameters),
                      "none_gradient_parameters_update_and_decay_skipped":
                          sorted(set(parameters) - set(trained))}
            self._pending = None
            return result
        except Exception:
            self.failed = True
            self._pending = None
            raise

    # ---- checkpoints ----
    def export_checkpoint(self, path):
        """Write ONE container's whole state, its optimizer, the encoder state and all three RNG streams."""
        require(self._pending is None and not self.failed, "TYPED_CHECKPOINT_UNCOMMITTED_OR_FAILED")
        self.encoder.verify_frozen()
        torch = self.torch
        model = _cpu(torch, dict(self.module.state_dict()))
        optimizer = _cpu(torch, self.optimizer.state_dict())
        encoder = self.encoder.export_state()
        rng = {"torch_cpu": torch.get_rng_state().clone(),
               "torch_cuda": [value.clone() for value in torch.cuda.get_rng_state_all()],
               "python": random.getstate()}
        metadata = {"run_identity": deepcopy(self.run_identity),
                    "run_identity_digest": self.run_identity_digest,
                    "model_revision": self.model_revision, "cursor": self.cursor,
                    "counters": deepcopy(self.counters), "elapsed_seconds": self._elapsed(),
                    "training_mode": self.module.training,
                    "model_state_identity": state_identity(torch, model),
                    "optimizer_state_identity": state_identity(torch, optimizer),
                    "encoder_state_identity": state_identity(torch, encoder),
                    "rng_state_identity": state_identity(torch, rng),
                    "init_args": {"optimizer_config": deepcopy(self.optimizer_config),
                                  "run_context": deepcopy(self.run_identity["context"]),
                                  "limits": deepcopy(self.limits), "device": str(self.device),
                                  "python_seed": self.python_seed, "root": self.root},
                    "learnable_names": sorted(self.module.state_dict())}
        require(set(metadata) == set(METADATA_FIELDS), "POINTER_CHECKPOINT_METADATA_FIELDS")
        payload = {"schema": CHECKPOINT_SCHEMA, "metadata": metadata, "model_state": model,
                   "optimizer_state": optimizer, "encoder_state": encoder, "rng_state": rng}
        destination = Path(path)
        require(destination.parent.is_dir(), "TYPED_CHECKPOINT_PARENT")
        with destination.open("xb") as stream:
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        raw_bytes = destination.read_bytes()
        return {"path": str(destination.resolve()), "sha256": sha256(raw_bytes).hexdigest(),
                "bytes": len(raw_bytes), "run_identity_digest": self.run_identity_digest,
                "metadata": metadata}

    @classmethod
    def restore_checkpoint(cls, torch, framework, encoder, *, path, expected_sha256,
                           expected_run_identity_digest, device, expected_learnable_names=None):
        """Restore a POINTER checkpoint. A practice checkpoint is refused, not silently half-loaded.

        `framework` must be the freshly built pointer framework for this run's seed and must NOT have had the
        saved state loaded into it: the container is the thing that owns the state, so loading it into
        `framework.module` first (which is what `TypedCourseLearner.restore_checkpoint` does at
        `learner.py:341`) would put the container's names into the three-key `^6` module and raise
        `POINTER_CHECKPOINT_BLOCK_MISMATCH`. Pass `expected_learnable_names` to assert which parameters a run
        is willing to restore; the recorded name set is checked against it either way.
        """
        from ..teaching_cycle.gpu_adapter import execution_guard
        execution_guard()
        _require_cuda_device(torch, device)
        target = Path(path)
        require(target.is_file() and not target.is_symlink()
                and 0 < target.stat().st_size <= 256 * 1024 * 1024, "TYPED_CHECKPOINT_FILE_BOUND")
        raw = target.read_bytes()
        require(type(expected_sha256) is str and sha256(raw).hexdigest() == expected_sha256,
                "TYPED_CHECKPOINT_SHA")
        payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
        require(type(payload) is dict
                and set(payload) == {"schema", "metadata", "model_state", "optimizer_state",
                                     "encoder_state", "rng_state"}, "TYPED_CHECKPOINT_FIELDS")
        require(payload["schema"] == CHECKPOINT_SCHEMA, "POINTER_CHECKPOINT_SCHEMA")
        metadata = payload["metadata"]
        require(type(metadata) is dict and set(metadata) == set(METADATA_FIELDS),
                "TYPED_CHECKPOINT_METADATA")
        identity = metadata["run_identity"]
        require(digest(identity) == metadata["run_identity_digest"] == expected_run_identity_digest
                and canonical(identity["learner_profile"]) == canonical(profile()),
                "TYPED_CHECKPOINT_RUN_IDENTITY")
        for field in ("model", "optimizer", "encoder", "rng"):
            require(state_identity(torch, payload[field + "_state"])
                    == metadata[field + "_state_identity"], "TYPED_CHECKPOINT_STATE_DIGEST:" + field)
        pointer_names = _fingerprint(torch, payload["model_state"])
        require(pointer_names, "POINTER_CHECKPOINT_CONTAINER_EMPTY")
        require(set(PARAMETERS) <= {row.split(":", 1)[0] for row in pointer_names}
                and len(pointer_names) > len(PARAMETERS), "POINTER_CHECKPOINT_BLOCK_MISMATCH")
        require(list(metadata["learnable_names"]) == sorted(row.split(":", 1)[0] for row in pointer_names),
                "POINTER_CHECKPOINT_LEARNABLE_NAMES")
        if expected_learnable_names is not None:
            require(sorted(expected_learnable_names) == list(metadata["learnable_names"]),
                    "POINTER_CHECKPOINT_EXPECTED_NAMES")
        init_args = _validate_init_args(metadata["init_args"], str(device))
        container = _build_container(torch, framework, device)
        # The two questions are asked SEPARATELY. "Did the container produce any layout at all" is not the same
        # question as "does it equal the saved layout", and while they shared one `require` the empty answer
        # passed for a comparison -- the exact failure that cost the seventh run its reload. A container built by
        # `_build_container` always has more parameters than `PARAMETERS`, so an empty live fingerprint is a
        # defect in the fingerprinting, not a layout mismatch, and it now says so.
        container_names = _fingerprint(torch, container.state_dict())
        require(container_names, "POINTER_CHECKPOINT_CONTAINER_EMPTY")
        require(container_names == pointer_names, "POINTER_CHECKPOINT_LAYOUT")
        restored = cls(torch, framework, encoder,
                       optimizer_config=init_args["optimizer_config"],
                       run_context=init_args["run_context"], limits=init_args["limits"],
                       device=device, tagger=role_tagger(init_args["root"]),
                       python_seed=init_args["python_seed"], root=init_args["root"])
        restored.module.load_state_dict(payload["model_state"], strict=True)
        restored.optimizer.load_state_dict(payload["optimizer_state"])
        require(state_identity(torch, dict(restored.module.state_dict()))
                == metadata["model_state_identity"]
                and state_identity(torch, restored.optimizer.state_dict())
                == metadata["optimizer_state_identity"], "TYPED_CHECKPOINT_RESTORED_VALUES")
        require(type(metadata["cursor"]) is int and type(metadata["model_revision"]) is int
                and 0 <= metadata["cursor"] == metadata["model_revision"]
                <= restored.limits["max_updates"], "TYPED_CHECKPOINT_CURSOR")
        require(type(metadata["counters"]) is dict and set(metadata["counters"]) == set(restored.counters)
                and all(type(value) is int and value >= 0 for value in metadata["counters"].values())
                and metadata["counters"]["optimizer_updates"] == metadata["cursor"],
                "TYPED_CHECKPOINT_COUNTERS")
        require(type(metadata["elapsed_seconds"]) in (int, float)
                and math.isfinite(metadata["elapsed_seconds"])
                and 0 <= metadata["elapsed_seconds"] <= restored.limits["max_wall_seconds"]
                and type(metadata["training_mode"]) is bool, "TYPED_CHECKPOINT_RUNTIME_METADATA")
        restored.run_identity = deepcopy(identity)
        restored.run_identity_digest = expected_run_identity_digest
        restored.cursor = metadata["cursor"]
        restored.model_revision = metadata["model_revision"]
        restored.counters = deepcopy(metadata["counters"])
        restored._elapsed_before, restored._started = metadata["elapsed_seconds"], time.monotonic()
        restored.module.train(metadata["training_mode"])
        rng = payload["rng_state"]
        require(type(rng) is dict and set(rng) == {"torch_cpu", "torch_cuda", "python"},
                "TYPED_CHECKPOINT_RNG_FIELDS")
        torch.set_rng_state(rng["torch_cpu"])
        torch.cuda.set_rng_state_all(rng["torch_cuda"])
        random.setstate(rng["python"])
        current = {"torch_cpu": torch.get_rng_state(),
                   "torch_cuda": torch.cuda.get_rng_state_all(), "python": random.getstate()}
        require(state_identity(torch, current) == metadata["rng_state_identity"],
                "TYPED_CHECKPOINT_RNG_VALUES")
        restored.encoder.verify_frozen()
        return restored

    # ---- the pass-0 instrument the review requires the worker to assert with ----
    def pass0_saturation(self, packets, *, limit=None, threshold=SATURATION_ABS_Z):
        """Measure the `^6` block's pre-activation saturation on the pass-0 combination ACTUALLY BUILT.

        `REVIEW_SYNTHESIS.md` section 5.6 decision 4: the saturation fraction for torch-default WITH THE INPUT
        PLACEMENT was never printed, so the worker must measure this combination rather than assume the
        printed output-placement figure (7.65-13.42 %) carries over. This method is that measurement.

        It runs the REAL rounds over `packets` -- the frozen course read from the public packets, so the node
        feature geometry is the geometry training will use -- and reports, for the block's FIRST pre-activation
        tensor (W1 x, the layer the review's `|z| > 2` table is about) and separately for its SECOND (`W2
        tanh(W1 x)`, so the statistic is never misread):
          * `saturation_fraction`, the count of entries with `|z| > threshold` over all entries;
          * the same fraction over the first round alone, i.e. pass 0 proper;
          * the entry count and the absolute threshold, so no consumer has to restate either.

        `initial_fingerprint` and `initial_sha256` are the names/shapes and the exact bytes of the three `^6`
        tensors AS `_framework` BUILT THEM, computed in the same call and scoped to this method, so the pass-0
        assertion can be tied to the registered start without leaving any unrecorded tensor in the module or in
        a checkpoint. Nothing is written and no state is mutated.
        """
        import torch
        require(not self.failed and self._pending is None, "POINTER_SATURATION_STATE")
        require(threshold == SATURATION_ABS_Z, "POINTER_SATURATION_THRESHOLD")
        selected = list(packets.values()) if type(packets) is dict else list(packets)
        require(selected, "POINTER_SATURATION_PACKETS")
        if limit is not None:
            require(type(limit) is int and limit > 0, "POINTER_SATURATION_LIMIT")
            selected = selected[:limit]
        first_entries, second_entries, first_hits, second_hits = 0, 0, 0, 0
        round_zero = [0, 0]
        counts = 0
        was_training = self.module.training
        self.module.eval()

        def observe(round_index, block_input):
            """The one hook that turns the REAL round into the review's `|z| > 2` statistic."""
            first, second = self.module.preactivations(block_input)
            hits_first = int((first.abs() > threshold).sum().item())
            hits_second = int((second.abs() > threshold).sum().item())
            row = {"first": hits_first, "first_total": int(first.numel()),
                   "second": hits_second, "second_total": int(second.numel())}
            totals["first"] += row["first"]
            totals["first_total"] += row["first_total"]
            totals["second"] += row["second"]
            totals["second_total"] += row["second_total"]
            if round_index == 0:
                totals["round_zero"] = [row["first"], row["first_total"]]

        totals = {"first": 0, "first_total": 0, "second": 0, "second_total": 0, "round_zero": [0, 0]}
        with torch.no_grad():
            for packet in selected:
                self.encoder.verify_frozen()
                reading = pointer_inputs.read_packet(packet)
                reading["_device"] = self.device
                blocks = _graph_blocks(torch, reading, self.device)
                counts += sum(row[1] for row in blocks)
                _rounds(torch, self.module, blocks, charge=self._charge_round, observe=observe)
        self.module.train(was_training)
        first_entries, second_entries = totals["first_total"], totals["second_total"]
        first_hits, second_hits = totals["first"], totals["second"]
        round_zero = totals["round_zero"]
        start = self.module.initial_block()
        require(set(start) == set(PARAMETERS), "POINTER_INITIAL_BLOCK")
        return {
            "schema": "cncm.typed-pointer-pass0-saturation/0.1",
            "packets_measured": len(selected),
            "nodes_measured": counts,
            "core_rounds": CORE_ROUNDS,
            "normalisation_placement": "INPUTS_OF_EACH_ROUND_BEFORE_THE_REGISTERED_CORE",
            "initialization": "BUILT_BY_cncm.typed_matched_worker._framework_TORCH_DEFAULT_SCHEME",
            "threshold_abs_z": threshold,
            "first_layer": {"entries": first_entries, "saturated_entries": first_hits,
                            "saturation_fraction": first_hits / first_entries},
            "second_layer": {"entries": second_entries, "saturated_entries": second_hits,
                             "saturation_fraction": second_hits / second_entries},
            "round_zero_first_layer": {"entries": round_zero[1], "saturated_entries": round_zero[0],
                                       "saturation_fraction": round_zero[0] / round_zero[1]},
            "initial_fingerprint": list(_fingerprint(torch, start)),
            "initial_sha256": sha256(_tensor_flat_bytes(torch, start)).hexdigest(),
        }


def _registered_names(module):
    """`{internal parameter name: registered name}`: the `^6` holders map back to their dotted names."""
    names = {name: name for name, _parameter in module.named_parameters()}
    for name in PARAMETERS:
        require(BLOCK_NAMES[name] in names, "POINTER_STATE_BLOCK_NAMES:" + name)
        names[BLOCK_NAMES[name]] = name
    require(set(names.values()) == set(module.state_dict()), "POINTER_REGISTERED_NAMES")
    return names


def _packet_by_record(packets):
    """`{record_id: packet}` for a packet mapping or an iterable, used only by helper measurements."""
    rows = packets.values() if type(packets) is dict else packets
    return {packet["record"]["record_id"]: packet for packet in rows}

