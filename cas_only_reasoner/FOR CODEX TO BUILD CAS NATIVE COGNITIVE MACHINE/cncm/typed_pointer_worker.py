"""One pointer-study job: the machine reads ONE focus world as a small directed graph and answers by
POINTING at that graph's own nodes. CUDA worker only, Linux only, no CPU fallback.

Owner-approved 2026-09-19 ("Accept both, carry on"; "Approve the smoke job (Recommended)"; "Yes --
require the relational kinds"). Adapted from `typed_practice_worker` (pipeline review, MINIMAL BUILD
PLAN item 4). Differences, each deliberate:

- THE PHASE ORDER IS FIXED AND LOAD-BEARING, and it differs from the practice worker's:

      preflight -> packets -> checkpoint check PHASE A -> seed + double build -> passes with evaluations
      -> retention/interference -> reloads/replays -> checkpoint check PHASE B -> ablations
      -> source verification -> deliver

  **PHASE A FINISHES BEFORE THE POINTER MODEL IS SEEDED** (review M3). Restoring a practice checkpoint
  overwrites all three global RNG streams with no save and restore (`learner.py:358-362`), so a model
  built before phase A would start from irreproducible weights. Phase A restores this job's seed's
  practice checkpoints, extracts and seals the PUBLIC post-block vectors of every slot, and reads NO
  answer: it cannot, because `cas_meta2.typed_teaching.checker` is required NOT to be in `sys.modules`
  at that point (FP3, test P14).
  **THE ORDERING IS MEASURED IN THE ARTIFACT, NEVER ASSERTED** (review R1-2). `model_identity.json`
  carries `phase_a_finished_before_the_model_was_seeded` as a derivation over three runtime readings --
  no pointer model attached before the build, phase A's own return time earlier than the build time from
  the run's monotonic clock, and phase A's recorded `status` -- so a job whose phase A ran and FAILED
  records `false` there, beside `phase_a_status`, instead of the unconditional literal it used to carry.
  REPORT-ONLY IS UNCHANGED: phase A still cannot fail an otherwise complete job, and the reader that
  wants to fail closed on it does so from `phase_a_status`. The field
  `identical_start_with_and_without_the_checkpoint_check` is a KNOWN TAUTOLOGY and the artifact says so
  where it is written; `double_build_equal`, `seed_core_identities` and `seeds_pairwise_different` are
  the checks in that artifact that can vary.
  **PHASE B RUNS LAST** -- after every pointer evaluation, reload and replay -- because deriving targets
  before training would breach the registered custody rule (`practice_contract.py:11-12`,
  `typed_course_worker.py:149`).

- THE `^6` IDENTITY CHECK DIGESTS THE THREE `^6` TENSORS ONLY. `model_state_identity` digests the whole
  `module.state_dict()` (`learner.py:111`, `:306`), and this machine's `module` is ONE CONTAINER holding
  the learned heads plus the `^6` block, so a container can never equal a three-tensor digest (review
  DG4, sharpened; `measurements/framework_probe/FINDINGS.md`). `_three_key_state` therefore reduces the
  container to `left.weight` / `right.weight` / `merge.weight` and `state_identity` is taken over exactly
  that dict. For the PRACTICE module the two forms coincide (its module IS the three tensors) and phase A
  proves it in-job; that equality is what makes the cross-machine comparison legitimate, and
  `model_identity.json` records BOTH numbers separately because they are not the same number here.
  This check is an IN-JOB check on AWS only: a local build reproduces the practice weights to within
  7.450580596923828e-09 but not byte-exactly, and `state_identity` is a byte-exact hash.

- THE WINDOWS REFUSAL HAPPENS BEFORE ANY NUMERIC IMPORT. Nothing in this module imports torch, numpy or
  any numeric provider at module level; the first numeric import is the one inside
  `cas_meta2.teaching_cycle.gpu_adapter._cuda()`, which runs its platform guard first
  (`gpu_adapter.py:37-39`, `:42-49`). Test P8's ordering depends on it and this module preserves it.

- `expected_main_delta` IS CHECKED AS CANONICAL BYTES against the summed per-update deltas, and
  `base.counter_delta` requires the two snapshots' key sets to match EXACTLY. The learner's
  `COUNTER_KEYS` and the contract's `MAIN_COUNTERS` are the same eleven names and the contract's
  `PLANNED_WORK` relations are the shared source of truth, so no counter outside those eleven may be
  introduced here either.

- DG9 -- THIS JOB MEASURES ITS OWN COST. `phase_timings.json` records per-phase elapsed seconds, the
  measured seconds per update and per evaluation, and the projection of the registered ten-pass job.
  The practice figure is 5,465.811116456 s of worker clock and 6,064 s of instance time against a
  `WORKER_DEADLINE_SECONDS` of 12,300; the pointer machine's per-update cost is UNMEASURED, and this
  job's timing is what measures it. Nothing is rounded anywhere in this file.

- THE EVIDENCE PUBLISHER IS CREATE-ONLY. Every file this worker places under ``results/`` is complete
  before its final name exists: pass logs grow in ``<results parent>/pointer_staging`` (outside
  ``results/``) and are moved in whole, and every other file is written as ``<name>.partial`` and renamed
  (`practice_worker._publish_bytes`). The live publisher uploads each new name once; a file that grew
  after its first upload fails the final upload with `EVIDENCE_DIGEST_CONFLICT`.

- THE CHECKPOINT CHECK ALWAYS WRITES ITS ARTIFACT WITH A `status` FIELD INSIDE (review RK6). A missing
  artifact fails `EXPECTED_ARTIFACTS` and the lifecycle evidence contract; and a module imported inside
  a `try` that fails poisons `attestor.snapshot()` with `FAILED_IMPORTS` at `final_source_verification`,
  after the money is spent. So every module the check needs -- `recurrent_cjt.recurrence`,
  `pointer_inputs`, `pointer_learner`, `practice_learner`, `slots`, `encoder` -- is imported at MODULE
  IMPORT TIME, outside any `try` anywhere in this file (their resolved paths travel in
  `schedule_plan.json` and in the phase-A artifact as evidence; all six are pure at import, so this
  module still imports without torch). Each check artifact carries `status` in {`COMPLETE`, `FAILED`}
  (plus `SKIPPED` for a deliberately shrunken run, which `pre_design/AWS_SMOKE_S10_PLAN.md:110-111`
  requires to be recorded rather than silently missing). Phase A, phase B and the ablations are
  REPORT-ONLY: a failure inside them is recorded and the job continues, and `deliver` then drops exactly
  the names those checks could not produce from the set it requires, so a reported check can never fail
  an otherwise complete job.
  **BECAUSE REPORT-ONLY ALSO MEANS "A DEGRADED CHECK DOES NOT FAIL THE JOB", THE REPORT MUST SAY SO OUT
  LOUD** (review R2, MAJOR 2). `run()` publishes `report["degraded_checks"]`, the sorted names of every
  one of the three whose own `status` is not `COMPLETE`, together with `report["report_only_status"]`,
  which carries each check's own status and `None` for a check that never produced its artifact at all --
  so "the ablations ran and failed" and "the ablations never started" are different readings, and `None`
  is a MISSING status rather than a new status word. `run()` reads those statuses and does not restate
  them, exactly as it reads `pointer_contract.PASSES`. Both keys reach `worker_report.json` (the whole
  report) and `measurements.json` (the `summary` list in `deliver`). An EMPTY `degraded_checks` is the
  claim that all three ran to completion, and nothing else is.

- THE PASS COUNT COMES FROM `pointer_contract.PASSES`, read, never restated. `design["schedule"]` is the
  registered ten-pass schedule; a SHRUNKEN run for the smoke job is expressed by an explicit environment
  request (`REDUCED_SCHEDULE_ENV`) that changes no registered constant and is recorded in
  `schedule_plan.json`.

Reuse, by import, of the practice worker's helpers: `_publish_bytes`, `_publish`, `_move_in`,
`_seal_predictions`, `_train_logged`, `_stage_and_train`, `_split_score`. Reuse of the shared base:
`_ProgressWriter`, `_partial_checkpoint`, `_score_seal`, `_state`, `_check_state`, `counter_delta`,
`_representatives`. `_evaluate` is NOT reused: it stamps the PRACTICE study's boundary string into every
scoring artifact it publishes (`typed_practice_worker.py:154`), so this worker publishes its own scoring
evidence, with the pointer boundary, through the same seal-then-score order.
"""
from __future__ import annotations

import contextlib
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time

from cas_meta2.recurrent_cjt import recurrence as recurrence_module
from cas_meta2.typed_teaching import encoder as encoder_module
from cas_meta2.typed_teaching import pointer_contract as contract
from cas_meta2.typed_teaching import pointer_inputs as pointer_reader
from cas_meta2.typed_teaching import pointer_learner as pointer_module
from cas_meta2.typed_teaching import practice_learner as practice_learner_module
from cas_meta2.typed_teaching import slots as slot_module
from cas_meta2.typed_teaching.learner import PARAMETERS as CORE_PARAMETERS, state_identity as tensor_state_identity
from . import typed_course_worker as base
from . import typed_matched_worker as matched
from . import typed_practice_worker as practice_worker

CANDIDATE = contract.CANDIDATE
CONFIG_SCHEMA = contract.CONFIG_SCHEMA
RESULT_SCHEMA = "cncm.typed-pointer-worker-result/0.1"
FAILURE_SCHEMA = "cncm.typed-pointer-failure/0.1"
SUCCESS_STATUS = "COMPLETE_TYPED_POINTER_ARM"
FAILED_STATUS = "TYPED_POINTER_FAILED"
DELIVERED_STATUS = "TYPED_POINTER_DELIVERED"
BOUNDARY = contract.DESIGN["boundary"]
PASSES = contract.PASSES
CHECKPOINTS = contract.PASS_CHECKPOINTS
FULL = contract.FULL_COURSE_CHECKPOINTS
HELD_ONLY = tuple(n for n in CHECKPOINTS if n not in FULL)
CHECKPOINT_NAMES = ("initial", "pass_01", "prelast", "final", "retained")
# The practice checkpoints phase A restores. `prelast` and `retained` stay unshipped on purpose so the
# check costs what the owner was told (review M2, hand-off 5.1).
PHASE_A_CHECKPOINTS = ("initial", "pass_01", "final")
# The pointer checkpoints phase B probes the machine's own node states at.
PHASE_B_POINTER_CHECKPOINTS = ("initial", "pass_01", "final")
EVALUATION_DEPTH = 8
CHECKPOINT_CHECK_STATUSES = ("COMPLETE", "FAILED", "SKIPPED")
# DG8. One component at a time, reset to its `initial.pt` weights on a restored copy of `final`.
#
# These four rows say WHICH component a container key belongs to -- a semantic decision no key set can
# supply. They are NOT the coverage check. `_ablation_components` derives every component's names from the
# container's own live `state_dict()` and refuses if any key is matched by NO row or by more than one, so a
# rename in `pointer_learner` can never silently shrink the ablated set (review R2, BLOCKER 3).
#
# The old `round_mix` row listed seven names from an abandoned design, SIX of which matched nothing at all
# (`round_state_norm`, `round_parent_norm`, `round_child_norm`, `self_mix`, `parent_mix`, `child_mix`):
# the three mix scalars had become ONE 3-element `Parameter` (`pointer_learner.py:670-674`). The old check
# was a count of names matching the ROWS, so the surviving `round_rate` satisfied it, `node_encode.weight`
# and `round_mix` were left unablated, the coverage `require` fired BEFORE the baseline evaluation, and all
# ten ablation artifacts were then dropped from the required set while the job still reported success.
ABLATION_COMPONENTS = (
    ("core_block", ("left.weight", "right.weight", "merge.weight")),
    # The shared round: the per-half node encoder belongs with the round mixing, exactly as the row above
    # groups the three `^6` tensors. All three names EXIST in the live container.
    ("round_mix", ("node_encode.weight", "round_mix", "round_rate")),
    ("heads", ("node_head.", "edge_head.", "role_head.", "role_embedding", "pointer_key.",
               "reach_option_head.", "mode_option_head.", "world_head.")),
    ("query_and_readout", ("query_projection.", "query_norm.", "attention_key.", "world_projection.",
                           "declaration_table", "declaration_projection.", "directed_pair_embedding")),
)
ABLATION_PHASES = ("ablation_baseline",) + tuple("ablation_" + name for name, _ in ABLATION_COMPONENTS)
# The shrunken-schedule request, read once at the start of `run()`. An environment request and not a
# config key on purpose: `pointer_contract.validate_config` rebuilds the whole config from the live tree
# and requires canonical identity (`pointer_contract.py:800-807`), so a schedule override can never travel
# inside the config without changing a registered constant.
REDUCED_SCHEDULE_ENV = "CNCM_POINTER_REDUCED_SCHEDULE"
REDUCED_SCHEDULE_KEYS = frozenset({"passes", "updates", "evaluations", "phase_a", "reloads", "phase_b",
                                   "ablations", "retention", "interference", "replays"})
OWNER_PROJECTION_THRESHOLD_SECONDS = 11000
# DG9. The MEASURED non-worker overhead of one AWS pointer job: the instance seconds that are not the
# worker's own clock -- boot, package install and delivery. `pre_design/AWS_SMOKE_S10_PLAN.md:29` measures it
# as 6,064 s of instance time minus the practice worker's own 5,465.811116456 s of `elapsed_seconds`, which
# is 598.188883544 s; that plan writes the same measurement rounded as "598.2 s". Nothing is rounded here.
# The owner's threshold is a number about INSTANCE time, so this term is what makes the comparison honest
# (review R2, MAJOR 1).
PRACTICE_INSTANCE_SECONDS = 6064
PRACTICE_WORKER_CLOCK_SECONDS = 5465.811116456
MEASURED_NON_WORKER_OVERHEAD_SECONDS = PRACTICE_INSTANCE_SECONDS - PRACTICE_WORKER_CLOCK_SECONDS
# The three REPORT-ONLY checks, in phase order, each with the `ctx` key its own artifact report lives under.
# `run()` publishes which of them did NOT reach `COMPLETE` (review R2, MAJOR 2).
REPORT_ONLY_CHECKS = (("checkpoint_check_phase_a", "phase_a"),
                      ("checkpoint_check_phase_b", "phase_b"),
                      ("ablations", "ablations"))
canonical, require = contract.canonical, contract.require
# RK6. EVERY module the checkpoint check needs is imported HERE, at module import time -- outside any
# `try` anywhere in this file -- so a missing module fails the job before the first phase instead of
# poisoning `attestor.snapshot()` with `FAILED_IMPORTS` at `final_source_verification`, after the spend.
# All six are pure at import time: this module still imports without torch (test P8 / the numeric-import
# guard). Their resolved paths travel in `schedule_plan.json` and in the phase-A artifact as evidence.
CHECKPOINT_CHECK_IMPORTS = {
    "recurrence": str(Path(recurrence_module.__file__).resolve()),
    "pointer_inputs": str(Path(pointer_reader.__file__).resolve()),
    "pointer_learner": str(Path(pointer_module.__file__).resolve()),
    "practice_learner": str(Path(practice_learner_module.__file__).resolve()),
    "slots": str(Path(slot_module.__file__).resolve()),
    "encoder": str(Path(encoder_module.__file__).resolve()),
    "imported_outside_any_try": True}


# ======================================================================================================
# 1. THE SCHEDULE PLAN -- the registered plan, or an explicitly requested shrunken one.
# ======================================================================================================
def _evaluation_phases(evaluations, retention):
    """`course_pNN` for the full-course points, `heldback_pNN` for the held-only ones, then development."""
    names = [("course_p%02d" % number) if number in FULL else ("heldback_p%02d" % number)
             for number in evaluations]
    names += ["development_p%02d" % number for number in evaluations]
    if retention:
        names += ["retention_before", "retention_after"]
    return tuple(names)


def _plan(passes, updates, evaluations, phase_a, reload, phase_b, ablations, retention, interference, replays):
    """One validated plan dict. Everything downstream reads the plan, never the module constants."""
    require(type(passes) is int and 1 <= passes <= PASSES, "POINTER_PLAN_PASSES")
    require(updates is None or (type(updates) is int and updates >= 1), "POINTER_PLAN_UPDATES")
    require(type(evaluations) is list and evaluations
            and all(type(number) is int and number in CHECKPOINTS for number in evaluations)
            and len(set(evaluations)) == len(evaluations), "POINTER_PLAN_EVALUATIONS")
    require(type(phase_a) is list and phase_a and all(name in PHASE_A_CHECKPOINTS for name in phase_a)
            and len(set(phase_a)) == len(phase_a), "POINTER_PLAN_PHASE_A")
    for value in (phase_b, ablations, retention, interference, replays, reload):
        require(type(value) is bool, "POINTER_PLAN_FLAGS")
    if retention and not interference:
        require(False, "POINTER_PLAN_RETENTION_REQUIRES_INTERFERENCE")
    if reload:
        # A reload compares a restored checkpoint's predictions with the predictions of a named phase.
        require(0 in evaluations and passes in evaluations, "POINTER_PLAN_RELOAD_EVALUATIONS")
    if replays:
        require(passes in evaluations, "POINTER_PLAN_REPLAY_EVALUATIONS")
    prelast = updates is None or updates >= 2
    if replays:
        require(prelast, "POINTER_PLAN_REPLAY_UPDATES")
    checkpoints = ["initial", "pass_01"]
    if prelast:
        checkpoints.append("prelast")
    checkpoints.append("final")
    if retention:
        checkpoints.append("retained")
    return {
        "passes": passes,
        "updates": updates,
        "prelast": prelast,
        "evaluations": [int(number) for number in sorted(evaluations)],
        "evaluation_phases": _evaluation_phases(sorted(evaluations), retention),
        "phase_a": [name for name in PHASE_A_CHECKPOINTS if name in phase_a],
        "phase_b": phase_b,
        "ablations": ablations,
        "retention": retention,
        "interference": interference,
        "replays": replays,
        "reload": reload,
        "reloads": (["initial", "final"] + (["retained"] if retention else [])) if reload else [],
        "checkpoints": tuple(checkpoints),
        "ablation_phases": ABLATION_PHASES if ablations else (),
    }


FULL_PLAN = _plan(PASSES, None, list(CHECKPOINTS), list(PHASE_A_CHECKPOINTS), True, True, True, True, True, True)


def expected_artifact_names(plan):
    """Every name this run must place under ``results/artifacts/``, derived from the plan alone."""
    names = []
    for number in range(1, plan["passes"] + 1):
        names += ["pass_%02d_batches.jsonl" % number, "pass_%02d_updates.jsonl" % number]
    if plan["interference"]:
        names += ["interference_batches.jsonl", "interference_updates.jsonl"]
    for phase in plan["evaluation_phases"]:
        names += [phase + "_predictions.json", phase + "_scoring.json"]
    for name in plan["checkpoints"]:
        names += [name + ".pt", name + "_checkpoint.json"]
    for name in plan["reloads"]:
        names += [name + "_reload_predictions.json"]
    if plan["replays"]:
        for number in (1, 2):
            names += ["replay_%d_%s" % (number, suffix)
                      for suffix in ("batch.json", "update.json", "predictions.json")]
    names.append("checkpoint_check_phase_a.json")
    for name in plan["phase_a"]:
        names.append("checkpoint_check_vectors_%s.json" % name)
    if plan["phase_b"]:
        names.append("checkpoint_check_phase_b.json")
    if plan["ablations"]:
        for phase in plan["ablation_phases"]:
            names += [phase + "_predictions.json", phase + "_scoring.json"]
        names.append("ablations.json")
    names += ["model_identity.json", "phase_timings.json", "schedule_plan.json"]
    names += ["replay_report.json", "encoding_checks.json", "installed_sources.json", "loaded_sources.json",
              "protocol_material.json", "worker_report.json", "measurements.json"]
    require(len(names) == len(set(names)), "POINTER_ARTIFACT_NAMES_UNIQUE")
    require(len(names) < 500, "POINTER_ARTIFACT_NAMES_BOUND")
    require(all(Path(name).name == name for name in names), "POINTER_ARTIFACT_BASENAME")
    return tuple(names)


EXPECTED_ARTIFACTS = expected_artifact_names(FULL_PLAN)
EVIDENCE_REQUIRED_COUNT = len(EXPECTED_ARTIFACTS) + 3
require(set(FULL_PLAN["evaluation_phases"]) == set(
    tuple("course_p%02d" % number for number in FULL)
    + tuple("heldback_p%02d" % number for number in HELD_ONLY)
    + tuple("development_p%02d" % number for number in CHECKPOINTS)
    + ("retention_before", "retention_after")), "POINTER_REGISTERED_EVALUATIONS")


def reduced_request(source=None):
    """The parsed shrunken-schedule request, or ``None``. Never changes a registered constant."""
    raw = os.environ.get(REDUCED_SCHEDULE_ENV) if source is None else source
    if raw is None or raw == "":
        return None
    request = json.loads(raw)
    require(type(request) is dict and set(request) <= REDUCED_SCHEDULE_KEYS, "POINTER_REDUCED_SCHEDULE_KEYS")
    require(bool(request), "POINTER_REDUCED_SCHEDULE_EMPTY")
    return request


def schedule_plan(source=None):
    """`(plan, claim_bearing)` for this run. The registered plan unless a reduced request is present."""
    request = reduced_request(source)
    if request is None:
        return deepcopy(FULL_PLAN), True
    body = deepcopy(FULL_PLAN)
    for key in ("passes", "updates", "evaluations", "phase_a"):
        if key in request:
            body[key] = request[key]
    for key in ("reload", "phase_b", "ablations", "retention", "interference", "replays"):
        if key in request:
            body[key] = request[key]
    if "reloads" in request:
        body["reload"] = request["reloads"]
    plan = _plan(body["passes"], body["updates"], sorted(body["evaluations"]), body["phase_a"], body["reload"],
                 body["phase_b"], body["ablations"], body["retention"], body["interference"], body["replays"])
    claim_bearing = (plan["passes"] == PASSES and plan["updates"] is None
                     and plan["evaluations"] == sorted(CHECKPOINTS)
                     and plan["phase_a"] == list(PHASE_A_CHECKPOINTS) and plan["phase_b"] and plan["ablations"]
                     and plan["retention"] and plan["interference"] and plan["replays"] and plan["reload"])
    return plan, claim_bearing


def _schedule(frozen, plan):
    """`(batches, stats)` for the plan, from the contract's own schedule builder."""
    batches, stats = contract.pointer_schedule(frozen, passes=plan["passes"])
    if plan["updates"] is None or plan["updates"] == stats["main_updates"]:
        require(plan["passes"] == stats["passes"], "POINTER_SCHEDULE_PASSES")
        require(stats["main_updates"] == len(batches), "POINTER_SCHEDULE_UPDATES")
        return batches, stats
    require(plan["updates"] < stats["main_updates"], "POINTER_REDUCED_UPDATES")
    batches = batches[:plan["updates"]]
    counts = matched._slot_counts(frozen)
    stats = {**deepcopy(stats),
             "registered_main_updates": stats["main_updates"], "reduced_updates": True,
             "passes": max(batch["pass"] for batch in batches), "main_updates": len(batches),
             "presentations": sum(len(batch["record_ids"]) for batch in batches),
             "presentation_slots": sum(counts[key] for batch in batches for key in batch["record_ids"]),
             "planned_slot_core_passes": sum(counts[key] * batch["depth"] for batch in batches
                                             for key in batch["record_ids"]),
             "batches_digest": contract.digest(batches)}
    require(stats["main_updates"] == plan["updates"], "POINTER_REDUCED_UPDATES")
    return batches, stats


# ======================================================================================================
# 2. SMALL HELPERS.
# ======================================================================================================
def _deadline(started):
    """This study's own deadline. Shared helpers handed the matched deadline get a FRESH clock instead."""
    require(time.monotonic() - started < contract.WORKER_DEADLINE_SECONDS, "POINTER_DEADLINE_EXCEEDED")


@contextlib.contextmanager
def _timed(timings, phase, **values):
    """Record one phase's exact elapsed seconds. Never rounded."""
    began = time.monotonic()
    try:
        yield
    finally:
        timings.append({"phase": phase, "seconds": time.monotonic() - began, **values})


_publish_bytes = practice_worker._publish_bytes
_publish = practice_worker._publish
_move_in = practice_worker._move_in
_seal_predictions = practice_worker._seal_predictions
_train_logged = practice_worker._train_logged
_stage_and_train = practice_worker._stage_and_train
_split_score = practice_worker._split_score
_sampled = base._representatives
_partial_checkpoint = base._partial_checkpoint
_score_seal = base._score_seal
_counter_delta = base.counter_delta


def _three_key_state(module):
    """The `^6` block ALONE out of a container's whole state dict: exactly `left/right/merge.weight`.

    This is the only form comparable across the two machines (review DG4 sharpened): the practice
    module's `state_dict()` IS these three tensors, while the pointer container's carries many more.
    """
    state = dict(module.state_dict())
    present = {name for name in state if name in CORE_PARAMETERS}
    require(present == set(CORE_PARAMETERS) and len(CORE_PARAMETERS) == 3, "POINTER_CORE_PARAMETERS")
    return {name: state[name] for name in CORE_PARAMETERS}


def _core_identity(torch, module):
    """`state_identity` over EXACTLY the three `^6` tensors -- the in-job DG4(a) comparison."""
    return tensor_state_identity(torch, _three_key_state(module))


def _container_identity(torch, module):
    """`state_identity` over the WHOLE container. A DIFFERENT number from `_core_identity` by design."""
    return tensor_state_identity(torch, dict(module.state_dict()))


def _evaluate(learner, packets, phase_name, artifacts, *, started, progress, work):
    """One evaluation: predict, seal durably, read back, THEN score. This study's boundary and codes."""
    _deadline(started)
    state = base._state(learner.torch, learner)
    counters = deepcopy(learner.counters)
    began = time.monotonic()
    progress(phase_name + "_predictions", completed_packets=0, total_packets=len(packets))
    rows = []
    for packet in packets.values():
        _deadline(started)
        rows.append(learner.predict(packet, EVALUATION_DEPTH))
        if len(rows) % 50 == 0 or len(rows) == len(packets):
            progress(phase_name + "_predictions", completed_packets=len(rows), total_packets=len(packets))
    path = artifacts / (phase_name + "_predictions.json")
    pin = _seal_predictions(path, rows, phase=phase_name, expected_ids=list(packets))
    # Durable public bytes precede every evaluation target. The shared scorer's own deadline is the matched
    # study's, so it is handed a fresh clock and this worker's deadline is re-checked immediately after.
    scored = _score_seal(path, pin, packets, started=time.monotonic(), progress=progress)
    _deadline(started)
    scored["boundary"] = BOUNDARY
    _publish(artifacts / (phase_name + "_scoring.json"), scored)
    require(state == base._state(learner.torch, learner), "EVALUATION_CHANGED_LEARNED_STATE")
    delta = _counter_delta(learner.counters, counters)
    require(delta["optimizer_updates"] == delta["backward_calls"] == 0, "EVALUATION_UPDATED_MODEL")
    work.append({"phase": phase_name, "delta": delta, "elapsed_seconds": time.monotonic() - began})
    return {row["record_id"]: row for row in rows}, scored


def _numeric_leaves(value):
    """Every scalar leaf of a reading, so a non-integer leaf can be refused explicitly."""
    if type(value) is dict:
        leaves = []
        for key in value:
            leaves += _numeric_leaves(value[key])
        return leaves
    if type(value) is list:
        leaves = []
        for item in value:
            leaves += _numeric_leaves(item)
        return leaves
    return [value]


def _input_checks(root, tokenizer, packets, representatives, artifacts, *, started, all_packets, progress,
                  phase):
    """The V1 replacement for `base._encoding_checks`, on the POINTER input reader.

    Per packet it proves: the reading is deterministic (two reads are byte-identical); it carries no float
    at all, so there is nothing that could be non-finite; it holds no forbidden field, no node ref and no
    node label; its node key set matches the registered rank branch; and it yields exactly one entry per
    slot of the EXISTING slot plan. Once per call it proves: the label/declaration cache is PINNED and
    built exactly ONCE, per resolved root, and the cached token ids of a representative's declaration text
    equal the ids the SAME reusable lookup produces directly.
    """
    from cas_meta2.typed_teaching import pointer_inputs as reader
    _deadline(started)
    before = reader._CACHE_STATE["builds"]
    first = reader.label_cache(root)
    builds = reader._CACHE_STATE["builds"]
    second = reader.label_cache(root)
    require(canonical(first) == canonical(second), "POINTER_INPUT_CACHE_EQUAL")
    require(reader._CACHE_STATE["builds"] == builds, "POINTER_INPUT_CACHE_REBUILT")
    require(builds >= before and reader.LABEL_CACHE_DIGEST_PIN is not None, "POINTER_INPUT_CACHE_BUILDS")
    require(first["cache_digest"] == reader.LABEL_CACHE_DIGEST_PIN, "POINTER_INPUT_CACHE_PIN")
    require(first["declaration_count"] > 0 and first["excerpt_count"] > 0, "POINTER_INPUT_CACHE_EMPTY")
    lookup = reader._unit_lookup(tokenizer.vocabulary)
    forbidden = (b"supports", b"cue", b"instruction", b"role_catalog", b"answer", b"admissible", b"correct")
    use_rank = contract.DESIGN["node_rank_feature"]
    expected_node_keys = ({"rank", "is_declared_whole", "is_participant", "is_whole_argument", "is_part_argument"}
                          if use_rank else
                          {"is_declared_whole", "is_participant", "is_whole_argument", "is_part_argument"})
    keys = list(packets) if all_packets else list(representatives.values())
    representative_ids = set(representatives.values())
    if progress is not None:
        progress(phase, completed_packets=0, total_packets=len(keys))
    digests, cache_rows, slot_total = {}, [], 0
    for at, key in enumerate(keys):
        _deadline(started)
        packet = packets[key]
        reading = reader.read_packet(packet)
        require(canonical(reader.read_packet(packet)) == canonical(reading), "POINTER_INPUT_READ_NOT_DETERMINISTIC")
        digest = reader.input_digest(reading)
        raw = canonical(reading)
        for needle in forbidden:
            require(needle not in raw, "POINTER_INPUT_FORBIDDEN_FIELD:" + needle.decode("ascii"))
        require(b'"/n' not in raw and b'"ref"' not in raw and b'"label"' not in raw, "POINTER_INPUT_NODE_ALIAS")
        require(reading["node_rank_feature"] == (1 if use_rank else 0), "POINTER_INPUT_RANK_BRANCH")
        leaves = _numeric_leaves(reading)
        require(all(type(leaf) in (int, str, type(None)) for leaf in leaves), "POINTER_INPUT_LEAF_TYPES")
        require(all(set(node) == expected_node_keys for world in reading["worlds"].values()
                    for node in world["nodes"]), "POINTER_INPUT_NODE_KEYS")
        plan = slot_module.compile_slots(packet)
        slot_rows = reader.slot_readings(reading, plan)
        require(len(slot_rows) == len(plan["slots"]) and bool(slot_rows), "POINTER_INPUT_SLOT_COUNT")
        slot_total += len(slot_rows)
        digests[key] = digest
        if progress is not None and ((at + 1) % 50 == 0 or at + 1 == len(keys)):
            progress(phase, completed_packets=at + 1, total_packets=len(keys))
        if key in representative_ids:
            world = None
            for candidate in packet["source"]["worlds"]:
                if candidate["world_id"] == reading["focus_world_id"]:
                    world = candidate
            require(world is not None, "POINTER_INPUT_FOCUS_WORLD")
            fields = {}
            for field in reader.DECLARATION_FIELDS:
                text = world["declarations"][field]
                fields[field] = (reader._encode_text(text, lookup, tokenizer.max_tokens)
                                 == reading["focus_world"]["declaration_ids"][field])
            excerpt = None
            if reading["query"]["kind_name"] == reader.ROLE_SET:
                text = packet["record"]["query"]["arguments"]["focal_excerpt"]
                excerpt = (sorted(reader._encode_text(text, lookup, tokenizer.max_tokens))
                           == reading["excerpt"])
            cache_rows.append({"record_id": key, "kind": reading["query"]["kind_name"],
                               "declaration_ids_equal_direct": all(fields.values()), "fields": fields,
                               "excerpt_equal_direct": excerpt, "reading_digest": digest})
    require(bool(cache_rows), "POINTER_INPUT_REPRESENTATIVES")
    require(all(row["declaration_ids_equal_direct"] for row in cache_rows), "POINTER_INPUT_CACHE_DIRECT")
    require(all(row["excerpt_equal_direct"] is not False for row in cache_rows), "POINTER_INPUT_EXCERPT_DIRECT")
    return {"schema": "cncm.typed-pointer-input-checks/0.1", "phase": phase, "records_checked": len(keys),
            "slots_checked": slot_total, "label_cache_digest": first["cache_digest"],
            "label_cache_builds": builds, "label_cache_roots": list(reader._CACHE_STATE["roots"]),
            "declaration_count": first["declaration_count"], "excerpt_count": first["excerpt_count"],
            "declaration_ids_equal_direct": True, "node_rank_feature": bool(use_rank),
            "numeric_leaf_types": ["int", "str", "none"], "float_leaves": 0,
            "forbidden_fields_absent": [needle.decode("ascii") for needle in forbidden],
            "node_alias_absent": True, "all_packets": bool(all_packets),
            "slot_readings_per_record_match_the_slot_plan": True, "representatives": cache_rows,
            "reading_digests": digests, "boundary": BOUNDARY}


# ======================================================================================================
# 3. PHASE: preflight.
# ======================================================================================================
def _preflight(root, attestor, report):
    """The GPU guard FIRST, then the attestor and the package check, then the runtime pin and determinism.

    The order is the practice worker's and is load-bearing twice over. `os.environ` is set before torch is
    imported; `_cuda()` runs its platform guard before its own `import torch`, so on Windows this raises
    `ValueError("TEACHING_GPU:LINUX_WORKER_REQUIRED")` with NO numeric import performed and BEFORE the
    attestor is demanded -- which is exactly what test P8 asserts (`INTERFACE_SPEC_PIPELINE.md:395-399`).
    """
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    from cas_meta2.teaching_cycle.gpu_adapter import _cuda
    torch, device = _cuda()
    torch.cuda.reset_peak_memory_stats(device)
    require(attestor is not None and callable(getattr(attestor, "snapshot", None)), "SOURCE_ATTESTOR_REQUIRED")
    loaded_before = attestor.snapshot()
    from .rpa_learning_worker import verify_worker_packages
    packages_before = verify_worker_packages(root)
    report["runtime"] = {"device": str(device), "torch_version": str(torch.__version__),
                         "cuda_version": torch.version.cuda, "gpu_name": torch.cuda.get_device_name(device)}
    require(report["runtime"]["torch_version"] == "2.11.0+cu128" and report["runtime"]["cuda_version"] == "12.8"
            and "RTX PRO 4500" in report["runtime"]["gpu_name"], "RUNTIME_MISMATCH")
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    require(contract.DESIGN["depths"][-1] == EVALUATION_DEPTH, "POINTER_EVALUATION_DEPTH")
    require(contract.DESIGN["prediction_depth"] == EVALUATION_DEPTH, "POINTER_PREDICTION_DEPTH")
    return torch, device, loaded_before, packages_before


# ======================================================================================================
# 4. PHASE: packets.
# ======================================================================================================
def _public_packet_preparation(ctx):
    """The frozen course read as public packets, the schedule, and the protocol artifact."""
    frozen, design = ctx["frozen"], ctx["design"]
    plan = ctx["plan"]
    artifacts = ctx["artifacts"]
    packets = dict(contract.public_packets(frozen))
    held, trained, excluded = contract.split(frozen)
    require(held == design["held_back_record_ids"] and excluded == design["excluded_record_ids"],
            "HOLDOUT_IDENTITY")
    ctx["held_set"], ctx["trained_set"], ctx["excluded_set"] = set(held), set(trained), set(excluded)
    ctx["held_worlds"] = set(contract.held_worlds(frozen))
    ctx["held_packets"] = {key: packets[key] for key in packets if key in ctx["held_set"]}
    ctx["development_packets"] = contract.development_packets(ctx["development"])
    ctx["retention_packets"] = dict(contract.retention_packets(frozen))
    ctx["retention_held"] = {key for key, packet in ctx["retention_packets"].items()
                             if packet["record"]["source_world_id"] in ctx["held_worlds"]}
    batches, stats = _schedule(frozen, plan)
    if plan["updates"] is None and plan["passes"] == PASSES:
        require(canonical(stats) == canonical(design["schedule"]), "POINTER_SCHEDULE_IDENTITY")
    else:
        # A shrunken schedule changes NOTHING registered: the per-pass update count is still the design's,
        # and the update total is exactly what the plan asked for -- the pass count times that, or the cap.
        require(stats["updates_per_pass"] == design["schedule"]["updates_per_pass"],
                "POINTER_REDUCED_SCHEDULE_PER_PASS")
        require(stats["main_updates"] == (plan["updates"] if plan["updates"] is not None
                                          else plan["passes"] * stats["updates_per_pass"]),
                "POINTER_REDUCED_SCHEDULE")
    require(all(key in ctx["trained_set"] for batch in batches for key in batch["record_ids"]),
            "UNTRAINABLE_IN_TRAINING")
    if contract.STRATIFIED:
        require(all(len(batch["record_ids"]) == len(contract.KINDS) for batch in batches),
                "POINTER_STRATIFY_COVERAGE")
    interference = contract.interference_batches(frozen) if plan["interference"] else []
    require(all(key in ctx["trained_set"] for batch in interference for key in batch["record_ids"]),
            "UNTRAINABLE_IN_INTERFERENCE")
    ctx["packets"], ctx["batches"], ctx["stats"], ctx["interference"] = packets, batches, stats, interference
    ctx["representatives"] = _sampled(packets)
    _publish(artifacts / "protocol_material.json",
             {"schema": "cncm.typed-pointer-protocol-material/0.1",
              "schedule": {"batches": batches, "stats": stats},
              "registered_passes": PASSES, "planned_passes": plan["passes"],
              "claim_bearing_run": ctx["claim_bearing"],
              "held_worlds": sorted(ctx["held_worlds"]), "held_back_record_ids": held,
              "trained_record_ids": trained, "excluded_record_ids": excluded,
              "interference_batches": interference, "development": ctx["development"],
              "retention_record_ids": list(ctx["retention_packets"]),
              "retention_held_world_record_ids": sorted(ctx["retention_held"]),
              "representatives": ctx["representatives"],
              "gate_population": ("COMPUTED_BY_THE_POINTER_GATE_READER_records/typed_pointer_001/"
                                  "evaluate_gates.py_NEVER_BY_THE_WORKER"),
              "relational_tier": list(contract.RELATIONAL), "direct_read_tier": list(contract.DIRECT_READ),
              "retention_packet_digests": {key: sha256(canonical(value)).hexdigest()
                                           for key, value in ctx["retention_packets"].items()},
              "boundary": BOUNDARY})
    ctx["phase"]("input_checks_initial")
    ctx["encoding"] = {"initial": _input_checks(ctx["root"], ctx["tokenizer"], packets,
                                                ctx["representatives"], artifacts, started=ctx["started"],
                                                all_packets=True, progress=ctx["phase"],
                                                phase="initial_input_checks")}
    _deadline(ctx["started"])


# ======================================================================================================
# 5. PHASE: checkpoint check PHASE A -- BEFORE the pointer model is seeded. Public vectors only.
# ======================================================================================================
def _practice_checkpoint(root, seed, name):
    """One shipped practice checkpoint and its sidecar, re-checked against the contract's pins."""
    relative = "records/typed_practice_001/receipt_%d/checkpoints/%s" % (seed, name)
    pin = contract.CHECKPOINT_PINS.get(relative + ".pt")
    sidecar_pin = contract.CHECKPOINT_PINS.get(relative + "_checkpoint.json")
    require(pin is not None and sidecar_pin is not None, "POINTER_PRACTICE_CHECKPOINT_PIN:" + relative)
    path = Path(root) / (relative + ".pt")
    require(path.is_file() and not path.is_symlink(), "POINTER_PRACTICE_CHECKPOINT_PATH:" + relative)
    raw = path.read_bytes()
    require(len(raw) == pin["bytes"] and sha256(raw).hexdigest() == pin["sha256"],
            "POINTER_PRACTICE_CHECKPOINT_BYTES:" + relative)
    sidecar_path = Path(root) / (relative + "_checkpoint.json")
    require(sidecar_path.is_file() and not sidecar_path.is_symlink(),
            "POINTER_PRACTICE_SIDECAR_PATH:" + relative)
    sidecar_raw = sidecar_path.read_bytes()
    require(len(sidecar_raw) == sidecar_pin["bytes"]
            and sha256(sidecar_raw).hexdigest() == sidecar_pin["sha256"],
            "POINTER_PRACTICE_SIDECAR_BYTES:" + relative)
    sidecar = json.loads(sidecar_raw)
    require(type(sidecar) is dict
            and set(sidecar) == {"path", "sha256", "bytes", "run_identity_digest", "metadata"},
            "POINTER_PRACTICE_SIDECAR_FIELDS")
    require(sidecar["sha256"] == pin["sha256"] and sidecar["bytes"] == pin["bytes"],
            "POINTER_PRACTICE_SIDECAR_PIN:" + relative)
    require(type(sidecar["run_identity_digest"]) is str and len(sidecar["run_identity_digest"]) == 64,
            "POINTER_PRACTICE_RUN_IDENTITY:" + relative)
    return path, pin, sidecar


def _post_block_vectors(torch, restored, packets, *, started, progress, phase):
    """The practice machine's post-block vector of EVERY slot, by the forward's own arithmetic (review M4).

    `TypedCourseLearner._forward` (`learner.py:145-156`) encodes the slot, runs `recurrence.run_passes` at
    depth 8 with the registered core, and stacks the final state. This function reproduces exactly that
    path -- `encode_slot`, the same `rms`, the same identity `cast` -- and returns the stacked post-block
    vector itself. Nothing is charged to the restored learner's counters and no target is touched, so the
    extracted vectors are PUBLIC and the restored checkpoint's counters are left exactly as restored.
    """
    recurrence = recurrence_module
    counters_before = deepcopy(restored.counters)
    rows = []
    was_training = restored.module.training
    restored.module.eval()
    keys = list(packets)
    core_calls = 0
    with torch.no_grad():
        for at, key in enumerate(keys):
            _deadline(started)
            packet = packets[key]
            plan = slot_module.compile_slots(packet)
            slots_out = []

            def rms(values):
                require(all(torch.is_tensor(value) for value in values), "POINTER_PHASE_A_DETACHED")
                vector = torch.stack(list(values))
                return torch.sqrt(torch.mean(vector * vector))

            def core(incoming):
                nonlocal core_calls
                restored._budget()
                result = restored.module(torch.stack(list(incoming)).unsqueeze(0))[0]
                core_calls += 1
                require(tuple(result.shape) == (64,) and bool(torch.isfinite(result).all().item()),
                        "POINTER_PHASE_A_CORE_OUTPUT")
                return result

            for slot in plan["slots"]:
                encoded = restored.encoder.encode_slot(packet, plan, slot)
                require(tuple(encoded.shape) == (64,) and not encoded.requires_grad
                        and bool(torch.isfinite(encoded).all().item()), "POINTER_PHASE_A_ENCODED_SLOT")
                final = recurrence.run_passes(encoded, core, depth=EVALUATION_DEPTH, state=None, rms_fn=rms,
                                              cast=lambda value: value,
                                              zeros=lambda count: torch.zeros(count, dtype=encoded.dtype,
                                                                              device=encoded.device))
                vector = torch.stack(list(final))
                require(tuple(vector.shape) == (64,) and bool(torch.isfinite(vector).all().item()),
                        "POINTER_PHASE_A_VECTOR")
                slots_out.append({"slot_id": slot["slot_id"], "symbols": list(slot["symbols"]),
                                  "indexes": [restored.encoder.symbol_to_index[symbol]
                                              for symbol in slot["symbols"]],
                                  "vector": [float(value) for value in vector.detach().cpu()]})
            rows.append({"record_id": key, "focus_world_id": packet["source"]["focus_world_id"],
                         "slots": slots_out})
            if progress is not None and ((at + 1) % 50 == 0 or at + 1 == len(keys)):
                progress(phase, completed_packets=at + 1, total_packets=len(keys))
    restored.module.train(was_training)
    require(restored.counters == counters_before, "POINTER_PHASE_A_CHARGED_COUNTERS")
    return rows, core_calls


def _verify_vectors_against_predictions(torch, restored, packets, representatives, rows, *, started):
    """Rebuild logits from the extracted vector and compare them with `restored.predict` BIT FOR BIT."""
    by_record = {row["record_id"]: row for row in rows}
    verified = []
    for key in representatives.values():
        _deadline(started)
        packet = packets[key]
        plan = slot_module.compile_slots(packet)
        prediction = restored.predict(packet, EVALUATION_DEPTH)
        require(prediction["depth"] == EVALUATION_DEPTH, "POINTER_PHASE_A_PREDICTION_DEPTH")
        for slot, stored in zip(plan["slots"], by_record[key]["slots"]):
            require(stored["slot_id"] == slot["slot_id"], "POINTER_PHASE_A_SLOT_ORDER")
            vector = torch.tensor(stored["vector"], dtype=torch.float32, device=restored.device)
            logits = restored.encoder.readout_rows[stored["indexes"]] @ vector
            rebuilt = [float(logits[at].detach().cpu().item()) for at in range(len(stored["symbols"]))]
            published = [prediction["scores"][slot["slot_id"]][symbol] for symbol in stored["symbols"]]
            require(rebuilt == published, "POINTER_PHASE_A_LOGIT_MISMATCH")
            verified.append({"record_id": key, "slot_id": slot["slot_id"], "symbols": stored["symbols"],
                             "exact": True, "logits": rebuilt})
    return verified


def _checkpoint_check_phase_a(ctx):
    """Restore this seed's practice checkpoints, seal their PUBLIC vectors, read NO answer. NEVER raises."""
    report = {"schema": "cncm.typed-pointer-checkpoint-check-phase-a/0.1", "phase": "A", "status": "FAILED",
              "status_vocabulary": list(CHECKPOINT_CHECK_STATUSES),
              "seed": ctx["design"]["model_seed"], "restored": list(ctx["plan"]["phase_a"]),
              "checkpoints": {}, "logit_verification": [], "depth": EVALUATION_DEPTH, "width": 64,
              "custody": ("PUBLIC POST-BLOCK VECTORS ONLY: no answer, target or private sidecar is read, and "
                          "`cas_meta2.typed_teaching.checker` is required NOT to be imported yet"),
              "checker_imported_before_phase_a": "cas_meta2.typed_teaching.checker" in sys.modules,
              "startup_imports": deepcopy(ctx.get("startup_imports", {})),
              "answers_read": False, "report_only": True, "boundary": BOUNDARY}
    try:
        require(not report["checker_imported_before_phase_a"], "POINTER_PHASE_A_CUSTODY")
        torch, device = ctx["torch"], ctx["device"]
        root, artifacts = ctx["root"], ctx["artifacts"]
        seed = ctx["design"]["model_seed"]
        practice_module = practice_learner_module
        for name in ctx["plan"]["phase_a"]:
            _deadline(ctx["started"])
            ctx["phase"]("checkpoint_check_phase_a_" + name, checkpoint=name)
            began = time.monotonic()
            path, pin, sidecar = _practice_checkpoint(root, seed, name)
            restored = practice_module.PracticeCourseLearner.restore_checkpoint(
                torch, matched._framework(torch, device, seed), path=path, expected_sha256=pin["sha256"],
                expected_run_identity_digest=sidecar["run_identity_digest"], device=device)
            require(set(restored.module.state_dict()) == set(CORE_PARAMETERS),
                    "POINTER_PHASE_A_PRACTICE_MODULE")
            core_identity = _core_identity(torch, restored.module)
            recorded = sidecar["metadata"]["model_state_identity"]
            rows, core_calls = _post_block_vectors(torch, restored, ctx["packets"], started=ctx["started"],
                                                   progress=ctx["phase"],
                                                   phase="checkpoint_check_phase_a_" + name)
            verified = _verify_vectors_against_predictions(torch, restored, ctx["packets"],
                                                          ctx["representatives"], rows,
                                                          started=ctx["started"])
            pin_artifact = _publish(artifacts / ("checkpoint_check_vectors_%s.json" % name),
                                    {"schema": "cncm.typed-pointer-post-block-vectors/0.1", "seed": seed,
                                     "checkpoint": name, "checkpoint_sha256": pin["sha256"],
                                     "run_identity_digest": sidecar["run_identity_digest"],
                                     "depth": EVALUATION_DEPTH, "width": 64, "records": len(rows),
                                     "slots": sum(len(row["slots"]) for row in rows),
                                     "vectors_digest": contract.digest(rows), "rows": rows,
                                     "boundary": BOUNDARY})
            report["checkpoints"][name] = {
                "checkpoint_sha256": pin["sha256"], "checkpoint_bytes": pin["bytes"],
                "run_identity_digest": sidecar["run_identity_digest"],
                "cursor": sidecar["metadata"]["cursor"], "records": len(rows),
                "slots": sum(len(row["slots"]) for row in rows), "core_calls": core_calls,
                "core_identity_over_three_keys": core_identity,
                "practice_recorded_model_state_identity": recorded,
                "three_key_form_equals_the_practices_own_identity": core_identity == recorded,
                "vectors_artifact": pin_artifact, "vectors_digest": contract.digest(rows),
                "elapsed_seconds": time.monotonic() - began}
            report["logit_verification"] += verified
            del restored
        require(all(row["three_key_form_equals_the_practices_own_identity"]
                    for row in report["checkpoints"].values()), "POINTER_PHASE_A_IDENTITY_FORM")
        require(all(row["exact"] for row in report["logit_verification"]), "POINTER_PHASE_A_LOGIT_EXACT")
        require(len(report["checkpoints"]) == len(ctx["plan"]["phase_a"]), "POINTER_PHASE_A_INCOMPLETE")
        report["status"] = "COMPLETE"
    except Exception as error:                                   # noqa: BLE001 - reported, never fatal
        report["failure"] = {"schema": FAILURE_SCHEMA, "type": type(error).__name__,
                             "detail": str(error)[:1000]}
    _publish(ctx["artifacts"] / "checkpoint_check_phase_a.json", report)
    return report


# ======================================================================================================
# 6. PHASE: seed + double build (the DG4 in-job checks).
# ======================================================================================================
def _seed_and_double_build(ctx):
    """Build the pointer model AFTER phase A, twice and independently, and record every DG4 identity."""
    torch, device, root = ctx["torch"], ctx["device"], ctx["root"]
    design, artifacts = ctx["design"], ctx["artifacts"]
    seed = design["model_seed"]
    build_frozen_typed_encoder = encoder_module.build_frozen_typed_encoder
    PointerCourseLearner, role_tagger = pointer_module.PointerCourseLearner, pointer_module.role_tagger
    encoder = build_frozen_typed_encoder(torch, ctx["tokenizer"], seed=design["encoder_seed"], d_model=64,
                                         device=device)
    limits = {"max_updates": ctx["stats"]["main_updates"]
              + (contract.INTERFERENCE_UPDATES if ctx["plan"]["interference"] else 0),
              "max_core_calls": contract.MAX_CORE_CALLS,
              "max_wall_seconds": contract.WORKER_DEADLINE_SECONDS}
    run_context = {"run_id": ctx["config"]["job"],
                   "course_sha256": contract.MATERIAL[ctx["course_path"]]["sha256"],
                   "condition": design["condition"], "source_seed": design["source_seed"]}
    tagger = role_tagger(str(root))

    def build(model_seed):
        return PointerCourseLearner(torch, matched._framework(torch, device, model_seed), encoder,
                                    optimizer_config=design["optimizer_config"], run_context=run_context,
                                    limits=limits, device=device, tagger=tagger, python_seed=model_seed,
                                    root=str(root))

    # R1-2. THE ORDERING IS MEASURED HERE, at the instant before the container is built, from two runtime
    # facts and nothing else: whether any pointer model was already attached to this run, and the run's own
    # monotonic reading of when phase A returned (`run()` records it). Nothing about this pair is written as
    # a literal, because a literal cannot vary and therefore is not evidence.
    model_seeded_at = time.monotonic()
    model_already_present = ctx.get("main") is not None
    main = build(seed)
    # (b) a SECOND, independent build of the WHOLE model: the container identity must be equal.
    second = build(seed)
    whole_first = _container_identity(torch, main.module)
    whole_second = _container_identity(torch, second.module)
    del second
    require(whole_first == whole_second, "POINTER_DOUBLE_BUILD_MISMATCH")
    core_identity = _core_identity(torch, main.module)
    # (c) the three seeds' `^6` starts must be pairwise different.
    seed_identities = {}
    for model_seed in contract.MODEL_SEEDS:
        probe = build(model_seed)
        seed_identities[str(model_seed)] = _core_identity(torch, probe.module)
        del probe
    require(len(set(seed_identities.values())) == len(seed_identities), "POINTER_SEED_IDENTITIES_NOT_DISTINCT")
    require(seed_identities[str(seed)] == core_identity, "POINTER_SEED_IDENTITY_STABLE")
    # (a) the three `^6` tensors must match THIS seed's recorded practice start. The practice value was
    # recorded by the practice study's own process, which ran no pointer checkpoint check and had a wholly
    # different RNG history, and `_framework` re-seeds all three streams, so the build is a pure function of
    # the seed -- which is exactly the "identical start with and without the checkpoint check" comparison
    # (M3 / DG4d). The model that trains is THIS one, built after phase A RETURNED. `run()` only calls this
    # function after `_checkpoint_check_phase_a` has returned, and the artifact MEASURES that ordering rather
    # than asserting it (R1-2); when phase A returned with anything other than `COMPLETE`, the reference
    # identity below comes from the practice sidecar directly and the ordering claim is recorded as false.
    phase_a = ctx["phase_a"]
    if "initial" in phase_a["checkpoints"]:
        recorded = phase_a["checkpoints"]["initial"]["practice_recorded_model_state_identity"]
    else:
        _, _, sidecar = _practice_checkpoint(root, seed, "initial")
        recorded = sidecar["metadata"]["model_state_identity"]
    # R1-2. The two halves of the ordering, each MEASURED, then the claim they support. `phase_a_status`
    # below is phase A's own recorded status, read and never restated.
    phase_a_returned_at = ctx.get("phase_a_returned_at")
    phase_a_status = phase_a["status"]
    returned_first = type(phase_a_returned_at) in (int, float) and phase_a_returned_at < model_seeded_at
    ordering_holds = bool(returned_first and not model_already_present and phase_a_status == "COMPLETE")
    identity = {"schema": "cncm.typed-pointer-model-identity/0.1", "model_seed": seed,
                "identity_form": "THREE_^6_TENSORS_ONLY",
                "core_identity": core_identity,
                "whole_container_identity": whole_first,
                "whole_container_form_is_a_different_number": whole_first != core_identity,
                "practice_recorded_model_state_identity": recorded,
                "core_identity_equals_the_practice_start": core_identity == recorded,
                "second_independent_whole_build_identity": whole_second,
                "double_build_equal": whole_first == whole_second,
                "seed_core_identities": seed_identities,
                "seeds_pairwise_different": len(set(seed_identities.values())) == len(seed_identities),
                "identical_start_with_and_without_the_checkpoint_check": core_identity == recorded,
                "identical_start_with_and_without_the_checkpoint_check_evidence_status": {
                    "status": "KNOWN_TAUTOLOGY",
                    "reason": ("R1-2. This flag is DEFINITIONALLY the same comparison as "
                               "`core_identity_equals_the_practice_start` above -- the same two values, the "
                               "same operator -- so it can never vary independently of it and is NOT separate "
                               "evidence. It is kept, and kept honest, because the gate reader "
                               "(`records/typed_pointer_001/evaluate_gates.py`, `DG4_FLAGS` and "
                               "`I3:<seed>:DG4_CHECK_INDEPENDENT_START`) looks for it by name."),
                    "on_arm": ("this job's container, built after phase A returned, whose `^6` start "
                               "`core_identity` records"),
                    "off_arm": ("the practice study's recorded identity, obtained by a process that ran NO "
                                "checkpoint check and had a wholly different RNG history -- which is why "
                                "this comparison IS the with-versus-without comparison"),
                    "why_there_is_no_independent_measurement_in_this_job": (
                        "a second arm cannot be built. An arm built BEFORE phase A would start from the RNG "
                        "state phase A overwrites (`learner.py:358-362`), which is the defect the phase "
                        "order exists to avoid, and the phase order is load-bearing "
                        "(`pre_design/AWS_SMOKE_S10_PLAN.md:155`, review M3). Perturbing this job's own RNG "
                        "to build a third arm would change the numerics of the model that trains, on a "
                        "spend path, for a field that is already covered."),
                    "checks_in_this_artifact_that_CAN_vary": ["double_build_equal", "seed_core_identities",
                                                              "seeds_pairwise_different"]},
                "comparison_method": ("the practice value was recorded by the practice study's own process, "
                                      "with no checkpoint check and a different RNG history; `_framework` "
                                      "re-seeds all three streams, so this build is a pure function of the "
                                      "seed and this equality IS the comparison"),
                "phase_a_finished_before_the_model_was_seeded": ordering_holds,
                "phase_a_finished_before_the_model_was_seeded_definition": (
                    "MEASURED, not asserted (R1-2). True only when all three measured readings agree: no "
                    "pointer model was attached to this run before this build, phase A had already returned "
                    "at an earlier reading of the run's own monotonic clock, and phase A's own recorded "
                    "status is COMPLETE. A phase A that ran and FAILED leaves this false, because the "
                    "reference identity was then read from the practice sidecar directly and it is not "
                    "phase A's evidence that the start was compared against."),
                "phase_a_returned_at_monotonic": phase_a_returned_at,
                "model_seeded_at_monotonic": model_seeded_at,
                "phase_a_returned_before_the_model_was_seeded": returned_first,
                "no_pointer_model_existed_when_this_one_was_built": not model_already_present,
                "phase_a_status": phase_a_status,
                "limits": deepcopy(limits), "python_seed": seed,
                "local_note": ("a LOCAL build reproduces the practice weights to within 7.450580596923828e-09 "
                               "but not byte-exactly, so this equality is an IN-JOB AWS check only"),
                "boundary": BOUNDARY}
    require(identity["core_identity_equals_the_practice_start"], "POINTER_CORE_IDENTITY_MISMATCH")
    _publish(artifacts / "model_identity.json", identity)
    main.module.train(True)
    ctx["main"], ctx["encoder"], ctx["identity"] = main, encoder, identity
    ctx["report"]["initial_model_identity"] = core_identity
    ctx["report"]["whole_container_identity"] = whole_first
    ctx["report"]["model_identity"] = {"schema": "cncm.typed-pointer-model-identity/0.1",
                                       "identity_form": identity["identity_form"],
                                       "core_identity_equals_the_practice_start":
                                           identity["core_identity_equals_the_practice_start"],
                                       "double_build_equal": identity["double_build_equal"],
                                       "seeds_pairwise_different": identity["seeds_pairwise_different"],
                                       # R1-2. The measured ordering travels with the summary too, so a reader
                                       # of `worker_report.json` alone sees it rather than having to open the
                                       # artifact. Read from `identity`, never restated.
                                       "phase_a_finished_before_the_model_was_seeded":
                                           identity["phase_a_finished_before_the_model_was_seeded"],
                                       "phase_a_status": identity["phase_a_status"]}


# ======================================================================================================
# 7. PHASE: passes with evaluations (main training).
# ======================================================================================================
def _main_training(ctx):
    """The plan's passes: one sealed-then-trained update at a time, evaluated at the plan's checkpoints."""
    main, artifacts, plan = ctx["main"], ctx["artifacts"], ctx["plan"]
    staging, stats, packets = ctx["staging"], ctx["stats"], ctx["packets"]
    report, work = ctx["report"], ctx["work"]

    def checkpoint(name):
        phase(name + "_checkpoint", completed_updates=main.cursor)
        pin = main.export_checkpoint(staging / (name + ".pt"))
        _move_in(staging / (name + ".pt"), artifacts / (name + ".pt"))
        ctx["checkpoint_pins"][name] = {**pin, "path": str(artifacts / (name + ".pt"))}
        _publish(artifacts / (name + "_checkpoint.json"), ctx["checkpoint_pins"][name])

    def evaluate_at(number):
        if number in FULL:
            name = "course_p%02d" % number
            ctx["predictions"][name], scored = _evaluate(main, packets, name, artifacts, started=ctx["started"],
                                                         progress=phase, work=work)
            report["scores"][name] = {"correct": scored["correct"], "total": scored["total"],
                                      **_split_score(scored, ctx["sides"])}
        else:
            name = "heldback_p%02d" % number
            _, scored = _evaluate(main, ctx["held_packets"], name, artifacts, started=ctx["started"],
                                  progress=phase, work=work)
            report["scores"][name] = {"correct": scored["correct"], "total": scored["total"],
                                      "held_back": {"correct": scored["correct"], "total": scored["total"]}}
        name = "development_p%02d" % number
        _, scored = _evaluate(main, ctx["development_packets"], name, artifacts, started=ctx["started"],
                              progress=phase, work=work)
        report["development_scores"].append({"pass": number, "cursor": main.cursor,
                                             "correct": scored["correct"], "total": scored["total"]})

    phase = ctx["phase"]
    checkpoint("initial")
    ctx["main_deltas"] = []
    if 0 in plan["evaluations"]:
        evaluate_at(0)
    last_seal, pass_summaries, training_seconds, update_count = None, [], 0.0, 0
    for number in range(1, plan["passes"] + 1):
        _deadline(ctx["started"])
        names = ("pass_%02d_batches.jsonl" % number, "pass_%02d_updates.jsonl" % number)
        batches_log, updates_log = staging / names[0], staging / names[1]
        batches_log.touch(exist_ok=False)
        updates_log.touch(exist_ok=False)
        losses, gradients = [], []
        began = time.monotonic()
        for batch in (item for item in ctx["batches"] if item["pass"] == number):
            if batch["cursor"] == stats["main_updates"] - 1:
                checkpoint("prelast")
            before = deepcopy(main.counters)
            last_seal, update = _train_logged(main, batch, packets, staging, batches_log, updates_log,
                                              started=ctx["started"])
            ctx["main_deltas"].append(_counter_delta(main.counters, before))
            losses.append(update["raw_batch_loss"])
            gradients.append(update["gradient_squared_norm"])
            update_count += 1
            report["completed_main_updates"] = main.cursor
            if main.cursor % 10 == 0:
                phase("main_training", completed_main_updates=main.cursor,
                      total_main_updates=stats["main_updates"], current_pass=number)
        training_seconds += time.monotonic() - began
        _move_in(batches_log, artifacts / names[0])
        _move_in(updates_log, artifacts / names[1])
        require(bool(losses), "POINTER_EMPTY_PASS")
        pass_summaries.append({"pass": number, "updates": len(losses), "cursor_end": main.cursor,
                               "mean_raw_batch_loss": sum(losses) / len(losses),
                               "first_raw_batch_loss": losses[0], "last_raw_batch_loss": losses[-1],
                               "mean_gradient_squared_norm": sum(gradients) / len(gradients),
                               "seconds": time.monotonic() - began})
        if number < plan["passes"]:
            _partial_checkpoint(main, ctx["results"], main.cursor)
        if number == 1:
            checkpoint("pass_01")
        if number == plan["passes"]:
            checkpoint("final")
        if number in plan["evaluations"]:
            evaluate_at(number)
    require(main.cursor == stats["main_updates"] and not any(staging.iterdir()), "POINTER_MAIN_INCOMPLETE")
    require(update_count == stats["main_updates"], "POINTER_INCOMPLETE_UPDATES")
    report["pass_summaries"] = pass_summaries
    report["training_seconds"] = training_seconds
    report["main_training_delta"] = matched._sum_deltas(ctx["main_deltas"])
    require(canonical(report["main_training_delta"]) == canonical(contract.expected_main_delta(stats)),
            "MAIN_TRAINING_COUNTERS")
    work.append({"phase": "main_training", "delta": report["main_training_delta"],
                 "elapsed_seconds": training_seconds})
    require(ctx["checkpoint_pins"]["initial"]["metadata"]["model_state_identity"]
            != ctx["checkpoint_pins"]["final"]["metadata"]["model_state_identity"], "TRAINABLE_CORE_UNCHANGED")
    ctx["last_seal"] = last_seal


# ======================================================================================================
# 8. PHASE: retention / interference.
# ======================================================================================================
def _retention_and_interference(ctx):
    """The retention panel before and after the trained-record-only interference interval."""
    main, artifacts, plan = ctx["main"], ctx["artifacts"], ctx["plan"]
    staging, stats, packets = ctx["staging"], ctx["stats"], ctx["packets"]
    report, work = ctx["report"], ctx["work"]
    if plan["retention"]:
        ctx["retention_sides"] = {"held_world": ctx["retention_held"],
                                  "trained_world": set(ctx["retention_packets"]) - ctx["retention_held"]}
        _, before_score = _evaluate(main, ctx["retention_packets"], "retention_before", artifacts,
                                    started=ctx["started"], progress=ctx["phase"], work=work)
    else:
        before_score = None
    deltas = []
    if plan["interference"]:
        names = ("interference_batches.jsonl", "interference_updates.jsonl")
        batches_log, updates_log = staging / names[0], staging / names[1]
        batches_log.touch(exist_ok=False)
        updates_log.touch(exist_ok=False)
        for batch in ctx["interference"]:
            before = deepcopy(main.counters)
            _train_logged(main, batch, packets, staging, batches_log, updates_log, started=ctx["started"])
            deltas.append(_counter_delta(main.counters, before))
            ctx["phase"]("interference_training", completed_updates=main.cursor,
                         total_updates=stats["main_updates"] + contract.INTERFERENCE_UPDATES)
        _move_in(batches_log, artifacts / names[0])
        _move_in(updates_log, artifacts / names[1])
    report["interference_delta"] = matched._sum_deltas(deltas) if deltas else None
    if plan["interference"]:
        require(report["interference_delta"]["optimizer_updates"] == contract.INTERFERENCE_UPDATES
                and report["interference_delta"]["prediction_calls"]
                == contract.INTERFERENCE_UPDATES * contract.INTERFERENCE_BATCH, "INTERFERENCE_COUNTS")
        work.append({"phase": "interference_training", "delta": report["interference_delta"]})
    if plan["retention"]:
        ctx["phase"]("retained_checkpoint", completed_updates=main.cursor)
        pin = main.export_checkpoint(staging / "retained.pt")
        _move_in(staging / "retained.pt", artifacts / "retained.pt")
        ctx["checkpoint_pins"]["retained"] = {**pin, "path": str(artifacts / "retained.pt")}
        _publish(artifacts / "retained_checkpoint.json", ctx["checkpoint_pins"]["retained"])
        ctx["retained_predictions"], after_score = _evaluate(main, ctx["retention_packets"], "retention_after",
                                                            artifacts, started=ctx["started"],
                                                            progress=ctx["phase"], work=work)
        report["retention_scores"] = {"before": {key: before_score[key] for key in ("correct", "total")},
                                      "after": {key: after_score[key] for key in ("correct", "total")},
                                      "before_by_side": _split_score(before_score, ctx["retention_sides"]),
                                      "after_by_side": _split_score(after_score, ctx["retention_sides"]),
                                      "starting_competence_met":
                                          2 * before_score["correct"] >= before_score["total"],
                                      "interference_updates": contract.INTERFERENCE_UPDATES
                                      if plan["interference"] else 0}
    ctx["encoding"]["final"] = _input_checks(ctx["root"], ctx["tokenizer"], ctx["packets"],
                                             ctx["representatives"], artifacts, started=ctx["started"],
                                             all_packets=False, progress=ctx["phase"],
                                             phase="final_input_checks")
    _deadline(ctx["started"])
    _publish(artifacts / "encoding_checks.json", ctx["encoding"])


# ======================================================================================================
# 9. PHASE: reloads / replays.
# ======================================================================================================
def _restore_pointer(ctx, *, path, pin, encoder):
    """Restore ONE pointer checkpoint into a freshly built framework, and require the exact state back."""
    restored = pointer_module.PointerCourseLearner.restore_checkpoint(
        ctx["torch"], matched._framework(ctx["torch"], ctx["device"], ctx["design"]["model_seed"]), encoder,
        path=path, expected_sha256=pin["sha256"],
        expected_run_identity_digest=ctx["main"].run_identity_digest, device=ctx["device"])
    base._check_state(ctx["torch"], restored, pin)
    return restored


def _reloads_and_replays(ctx):
    """Same-process reconstruction: the plan's reloads and the two prelast replays."""
    artifacts, plan = ctx["artifacts"], ctx["plan"]
    staging, stats, packets = ctx["staging"], ctx["stats"], ctx["packets"]
    work = ctx["work"]
    reloads, replays = [], []
    for name in plan["reloads"]:
        _deadline(ctx["started"])
        ctx["phase"](name + "_reconstruction")
        pin = ctx["checkpoint_pins"][name]
        restored = _restore_pointer(ctx, path=artifacts / (name + ".pt"), pin=pin, encoder=ctx["encoder"])
        before = deepcopy(restored.counters)
        if name == "retained":
            selected = list(ctx["retention_packets"])[:8]
            source_packets = ctx["retention_packets"]
            expected = ctx["retained_predictions"]
        else:
            selected = list(ctx["representatives"].values())
            source_packets = packets
            expected = ctx["predictions"]["course_p%02d" % (0 if name == "initial" else plan["passes"])]
        rows = [restored.predict(source_packets[key], EVALUATION_DEPTH) for key in selected]
        require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows),
                "RELOAD_PREDICTION_MISMATCH")
        _seal_predictions(artifacts / (name + "_reload_predictions.json"), rows, phase=name + "_reload",
                          expected_ids=selected)
        delta = _counter_delta(restored.counters, before)
        require(delta["optimizer_updates"] == delta["backward_calls"] == 0, "RELOAD_UPDATED_MODEL")
        work.append({"phase": name + "_reload", "delta": delta})
        reloads.append({"phase": name, "checkpoint_sha256": pin["sha256"], "prediction_ids": selected,
                        "delta": delta})
        del restored
    if plan["replays"]:
        for branch in (1, 2):
            _deadline(ctx["started"])
            ctx["phase"]("replay_%d" % branch)
            pin = ctx["checkpoint_pins"]["prelast"]
            restored = _restore_pointer(ctx, path=artifacts / "prelast.pt", pin=pin, encoder=ctx["encoder"])
            before = deepcopy(restored.counters)
            staged_seal = staging / ("replay_%d_batch.json" % branch)
            raw, update = _stage_and_train(restored, ctx["batches"][-1], packets, staged_seal,
                                           started=ctx["started"])
            require(raw == ctx["last_seal"], "REPLAY_PREUPDATE_MISMATCH")
            _move_in(staged_seal, artifacts / ("replay_%d_batch.json" % branch))
            _publish(artifacts / ("replay_%d_update.json" % branch), update)
            base._check_state(ctx["torch"], restored, ctx["checkpoint_pins"]["final"])
            expected = ctx["predictions"]["course_p%02d" % plan["passes"]]
            rows = [restored.predict(packets[key], EVALUATION_DEPTH)
                    for key in ctx["representatives"].values()]
            require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows),
                    "REPLAY_FINAL_MISMATCH")
            _seal_predictions(artifacts / ("replay_%d_predictions.json" % branch), rows,
                              phase="replay_%d" % branch, expected_ids=list(ctx["representatives"].values()))
            delta = _counter_delta(restored.counters, before)
            require(delta["optimizer_updates"] == delta["backward_calls"] == 1, "REPLAY_COUNTS")
            work.append({"phase": "replay_%d" % branch, "delta": delta})
            replays.append({"branch": branch, "restored_cursor": stats["main_updates"] - 1,
                            "committed_cursor": restored.cursor, "delta": delta})
            del restored
    _publish(artifacts / "replay_report.json",
             {"schema": "cncm.typed-pointer-reload/0.1", "reloads": reloads, "replays": replays,
              "passes": plan["passes"], "reload_selected": plan["reload"], "replays_selected": plan["replays"],
              "boundary": "Same-process same-worker reconstruction only."})


# ======================================================================================================
# 10. PHASE: checkpoint check PHASE B -- last. Answers derived here and nowhere earlier.
# ======================================================================================================
def _ridge_probe(torch, features, targets, train_keys, test_keys, *, penalty=1.0):
    """One closed-form ridge probe: fit on the trained keys, score the held keys. Never a gradient step."""
    labels = sorted({targets[key] for key in set(train_keys) | set(test_keys)})
    if len(labels) < 2 or not train_keys or not test_keys:
        return {"skipped": "SINGLE_CLASS_OR_EMPTY_POPULATION", "classes": len(labels),
                "train": len(train_keys), "test": len(test_keys)}
    index = {label: at for at, label in enumerate(labels)}
    ordered_train, ordered_test = sorted(train_keys), sorted(test_keys)
    xt = torch.tensor([features[key] for key in ordered_train], dtype=torch.float64)
    xe = torch.tensor([features[key] for key in ordered_test], dtype=torch.float64)
    yt = torch.zeros(len(ordered_train), len(labels), dtype=torch.float64)
    for row, key in enumerate(ordered_train):
        yt[row, index[targets[key]]] = 1.0
    truth = torch.tensor([index[targets[key]] for key in ordered_test], dtype=torch.int64)
    gram = xt.transpose(0, 1).matmul(xt) + penalty * torch.eye(xt.shape[1], dtype=torch.float64)
    weights = torch.linalg.solve(gram, xt.transpose(0, 1).matmul(yt))
    predicted = xe.matmul(weights).argmax(dim=1)
    correct = int((predicted == truth).sum().item())
    counts = [0] * len(labels)
    for key in ordered_train:
        counts[index[targets[key]]] += 1
    return {"classes": len(labels), "train": len(ordered_train), "test": len(ordered_test),
            "correct": correct, "total": len(ordered_test), "accuracy": correct / len(ordered_test),
            "majority_reference": max(counts) / len(ordered_test), "penalty": penalty,
            "solver": "torch.linalg.solve_normal_equations_cpu_float64", "feature_width": len(features[ordered_train[0]])}


def _probe_rows(torch, features, targets, kind_of, worlds, trained_worlds, *, label):
    """Per kind, the trained-world -> held-world probe. Report only; no gate reads this."""
    rows = {}
    for kind in sorted(set(kind_of.values())):
        keys = [key for key in features if kind_of[key] == kind]
        train_keys = [key for key in keys if worlds[key] in trained_worlds]
        test_keys = [key for key in keys if worlds[key] not in trained_worlds]
        rows[kind] = {**_ridge_probe(torch, features, targets, train_keys, test_keys), "probe": label,
                      "kind": kind, "train_worlds": sorted({worlds[key] for key in train_keys}),
                      "held_worlds": sorted({worlds[key] for key in test_keys})}
    return rows


def _pointer_node_features(ctx, checkpoints, packets):
    """The pointer machine's own node states at named checkpoints: the focus world, mean-pooled per record."""
    build_frozen_typed_encoder = encoder_module.build_frozen_typed_encoder
    PointerCourseLearner = pointer_module.PointerCourseLearner
    torch, device, design = ctx["torch"], ctx["device"], ctx["design"]
    features, counts = {}, {}
    for name in checkpoints:
        _deadline(ctx["started"])
        ctx["phase"]("checkpoint_check_phase_b_" + name, checkpoint=name)
        pin = ctx["checkpoint_pins"][name]
        encoder = build_frozen_typed_encoder(torch, ctx["tokenizer"], seed=design["encoder_seed"], d_model=64,
                                             device=device)
        restored = PointerCourseLearner.restore_checkpoint(
            torch, matched._framework(torch, device, design["model_seed"]), encoder,
            path=ctx["artifacts"] / (name + ".pt"), expected_sha256=pin["sha256"],
            expected_run_identity_digest=ctx["main"].run_identity_digest, device=device)
        base._check_state(torch, restored, pin)
        restored.module.eval()
        rows, nodes = {}, 0
        with torch.no_grad():
            for at, key in enumerate(sorted(packets)):
                _deadline(ctx["started"])
                forward = restored._graph(packets[key])["forward"]
                offset = forward.focus_offset
                count = forward.blocks[forward.focus_position][1]
                vector = forward.hidden[offset:offset + count].mean(dim=0)
                require(tuple(vector.shape) == (64,) and bool(torch.isfinite(vector).all().item()),
                        "POINTER_PHASE_B_NODE_STATE")
                rows[key] = [float(value) for value in vector.detach().cpu()]
                nodes += count
                if (at + 1) % 50 == 0 or at + 1 == len(packets):
                    ctx["phase"]("checkpoint_check_phase_b_" + name, checkpoint=name,
                                 completed_packets=at + 1, total_packets=len(packets))
        features[name], counts[name] = rows, nodes
        del restored
    return features, counts


def _checkpoint_check_phase_b(ctx):
    """Derive answers and fit the trained-world -> held-world ridge probe. LAST. Report only. NEVER raises."""
    plan, artifacts = ctx["plan"], ctx["artifacts"]
    report = {"schema": "cncm.typed-pointer-checkpoint-check-phase-b/0.1", "phase": "B", "status": "FAILED",
              "status_vocabulary": list(CHECKPOINT_CHECK_STATUSES),
              "custody": ("RUNS LAST: every pointer evaluation, reload and replay has completed before the "
                          "private checker is imported and any target is derived"),
              "answers_read": True, "report_only": True, "probes": {}, "pointer_probes": {},
              "boundary": BOUNDARY}
    if not plan["phase_b"]:
        report.update(status="SKIPPED", answers_read=False, reason="PHASE_B_NOT_SELECTED_BY_THE_RUN_PLAN")
        _publish(artifacts / "checkpoint_check_phase_b.json", report)
        return report
    try:
        # The ordering is proved, not assumed: phase B refuses to derive anything until every pointer
        # evaluation, reload and replay this plan asked for has already completed (FP3, test P14).
        done = {row["phase"] for row in ctx["work"]}
        require(all(name + "_reload" in done for name in plan["reloads"])
                and all(not plan["replays"] or "replay_%d" % branch in done for branch in (1, 2))
                and all("course_p%02d" % number in done or "heldback_p%02d" % number in done
                        for number in plan["evaluations"]),
                "POINTER_PHASE_B_ORDER")
        from cas_meta2.typed_teaching import checker
        packets = ctx["packets"]
        kind_of = {key: packet["record"]["query"]["kind"] for key, packet in packets.items()}
        worlds = {key: packet["record"]["source_world_id"] for key, packet in packets.items()}
        targets = {}
        for key, packet in packets.items():
            target = checker.derive_target(packet["source"], packet["record"]["query"])
            targets[key] = canonical(target["admissible_answers"][0]).decode("utf-8")
        for name, pin in ctx["phase_a"]["checkpoints"].items():
            _deadline(ctx["started"])
            artifact = artifacts / pin["vectors_artifact"]["name"]
            raw = artifact.read_bytes()
            require(len(raw) == pin["vectors_artifact"]["bytes"]
                    and sha256(raw).hexdigest() == pin["vectors_artifact"]["sha256"],
                    "POINTER_PHASE_B_VECTORS_CHANGED")
            rows = json.loads(raw)["rows"]
            require(contract.digest(rows) == pin["vectors_digest"], "POINTER_PHASE_B_VECTORS_DIGEST")
            features = {}
            for row in rows:
                slots = row["slots"]
                width = len(slots[0]["vector"])
                features[row["record_id"]] = [sum(slot["vector"][at] for slot in slots) / len(slots)
                                              for at in range(width)]
            report["probes"][name] = _probe_rows(ctx["torch"], features, targets, kind_of, worlds,
                                                 ctx["trained_set"], label="PRACTICE_POST_BLOCK_VECTOR")
        if not ctx["phase_a"]["checkpoints"]:
            report["practice_probes_skipped"] = "PHASE_A_PRODUCED_NO_VECTOR_ARTIFACTS"
        checkpoints = [name for name in PHASE_B_POINTER_CHECKPOINTS if name in ctx["checkpoint_pins"]]
        pointer_features, node_counts = _pointer_node_features(ctx, checkpoints, packets)
        for name, features in pointer_features.items():
            report["pointer_probes"][name] = {
                **_probe_rows(ctx["torch"], features, targets, kind_of, worlds, ctx["trained_set"],
                              label="POINTER_FOCUS_WORLD_NODE_STATE"),
                "nodes_read": node_counts[name], "records": len(features)}
        report["status"] = "COMPLETE"
    except Exception as error:                                   # noqa: BLE001 - reported, never fatal
        report["failure"] = {"schema": FAILURE_SCHEMA, "type": type(error).__name__,
                             "detail": str(error)[:1000]}
    _publish(artifacts / "checkpoint_check_phase_b.json", report)
    return report


# ======================================================================================================
# 11. PHASE: ablations (review DG8).
# ======================================================================================================
def _ablation_components(state_keys):
    """`({component: (names)}, coverage reading)` derived from the container's own keys, or a refusal.

    CONSTRUCTIVE, not a count against a hand-maintained list (review R2, BLOCKER 3). `ABLATION_COMPONENTS`
    still decides WHICH component a key belongs to, because that is a semantic choice no key set can supply;
    what is derived here -- from the container's actual `state_dict()` keys -- is which keys each component
    actually owns. Two conditions are refused, and only these two:

      * a key matched by NO component -> `POINTER_ABLATION_COVERAGE:<key>` (the key would never be ablated,
        which is the defect this replaces: the evidence would be silently partial);
      * a key matched by MORE THAN ONE component -> `POINTER_ABLATION_AMBIGUOUS:<key>:<components>` (the
        evidence would be double-counted and the "other components are byte-unchanged" proof would be void);
      * a component that owns no key at all -> `POINTER_ABLATION_COMPONENT_EMPTY:<component>` (refused here
        rather than after the baseline evaluation, so nothing is spent on a component that cannot be reset).

    Each refusal carries the counts in its OWN code, so the published `failure.detail` of a refused job still
    says how many of how many keys were covered. A row whose prefixes match nothing is NOT refused on that
    ground alone: if every key is still owned by exactly one component the ablated set is complete and the
    evidence is real, so refusing would block a legitimate job over cruft. Dead prefixes are recorded as
    EVIDENCE instead, in `dead_prefixes`.
    """
    require(bool(state_keys) and all(type(name) is str for name in state_keys),
            "POINTER_ABLATION_STATE_EMPTY")
    components = {component: tuple(sorted(name for name in state_keys
                                          if any(name == prefix or name.startswith(prefix)
                                                 for prefix in prefixes)))
                  for component, prefixes in ABLATION_COMPONENTS}
    reading = {"state_dict_keys": len(state_keys),
               "per_component_counts": {component: len(names) for component, names in components.items()},
               "per_component_state_keys": {component: list(names) for component, names in components.items()},
               "dead_prefixes": sorted(component + ":" + prefix
                                       for component, prefixes in ABLATION_COMPONENTS for prefix in prefixes
                                       if not any(name == prefix or name.startswith(prefix)
                                                  for name in state_keys))}
    reading["covered_keys"] = len({name for names in components.values() for name in names})
    reading["uncovered_keys"] = sorted(set(state_keys) - {name for names in components.values() for name in names})
    counts = ":covered=" + str(reading["covered_keys"]) + ":of=" + str(len(state_keys))
    for component, names in components.items():
        require(bool(names), "POINTER_ABLATION_COMPONENT_EMPTY:" + component + counts)
    for name in sorted(state_keys):
        owners = sorted(component for component, names in components.items() if name in names)
        require(bool(owners), "POINTER_ABLATION_COVERAGE:" + name + counts)
        require(len(owners) == 1, "POINTER_ABLATION_AMBIGUOUS:" + name + ":" + ",".join(owners) + counts)
    reading["every_key_covered_by_exactly_one_component"] = (
        reading["covered_keys"] == len(state_keys) and len(reading["uncovered_keys"]) == 0)
    require(reading["every_key_covered_by_exactly_one_component"],
            "POINTER_ABLATION_COVERAGE" + counts)
    return components, reading


def _reset_component(torch, pointer_module, learner, initial_state, names):
    """Reset ONE component's `names` to their `initial.pt` values, and prove the rest is byte-untouched.

    `names` is the DERIVED member list of one row of `ABLATION_COMPONENTS` (`_ablation_components`), not the
    row's prefixes: the reset then acts on exactly the keys the coverage check proved are owned, with no
    second, independent prefix interpretation that could disagree with it.
    """
    state = dict(learner.module.state_dict())
    names = sorted(names)
    require(bool(names), "POINTER_ABLATION_COMPONENT_EMPTY")
    require(all(name in state for name in names), "POINTER_ABLATION_COMPONENT_NAME")
    registered_to_internal = {registered: internal
                              for internal, registered in pointer_module._registered_names(learner.module).items()}
    parameters = dict(learner.module.named_parameters())
    with torch.no_grad():
        for name in names:
            require(name in initial_state, "POINTER_ABLATION_INITIAL_NAME:" + name)
            require(name in registered_to_internal, "POINTER_ABLATION_HOLDER:" + name)
            source = initial_state[name]
            require(tuple(source.shape) == tuple(state[name].shape), "POINTER_ABLATION_SHAPE:" + name)
            holder = registered_to_internal[name]
            parameters[holder].copy_(source.to(parameters[holder].device))
    after = dict(learner.module.state_dict())
    require(all(bool(torch.equal(after[name].cpu(), initial_state[name].cpu())) for name in names),
            "POINTER_ABLATION_RESET")
    untouched = sorted(set(after) - set(names))
    require(all(bool(torch.equal(after[name].cpu(), state[name].cpu())) for name in untouched),
            "POINTER_ABLATION_TOUCHED_OTHER_COMPONENTS")
    return {"component_parameters": names, "component_count": len(names), "untouched_count": len(untouched),
            "component_identity": tensor_state_identity(torch, {name: initial_state[name] for name in names})}


def _ablations(ctx):
    """Restored copies of `final`, one component reset to `initial` at a time, all of it timed and sealed."""
    torch, artifacts, plan = ctx["torch"], ctx["artifacts"], ctx["plan"]
    report = {"schema": "cncm.typed-pointer-ablations/0.1", "status": "FAILED",
              "plan_ablations": plan["ablations"], "report_only": True,
              "components": {name: list(prefixes) for name, prefixes in ABLATION_COMPONENTS},
              "protocol": ("restore `final`, evaluate the held-back panel, then for EACH component restore "
                           "`final` again, reset exactly that component to its `initial.pt` weights, prove "
                           "the other components are byte-unchanged, and re-evaluate"),
              "boundary": ("Post-run component reset on a restored copy. Not a learning result and not a gate "
                           "input.")}
    if not plan["ablations"]:
        report.update(status="SKIPPED", reason="ABLATIONS_NOT_SELECTED_BY_THE_RUN_PLAN")
        _publish(artifacts / "ablations.json", report)
        return report
    try:
        initial = torch.load(artifacts / "initial.pt", map_location="cpu", weights_only=True)
        require(type(initial) is dict and "model_state" in initial, "POINTER_ABLATION_INITIAL")
        initial_state = dict(initial["model_state"])
        require(set(initial_state) == set(ctx["main"].module.state_dict()), "POINTER_ABLATION_INITIAL_KEYS")
        # CONSTRUCTIVE coverage (review R2, BLOCKER 3): every key of the LIVE container must be owned by
        # exactly one component, derived from the keys themselves. This runs BEFORE the baseline evaluation
        # on purpose, so an unowned key refuses the ablations family up front instead of after the spend.
        components, report["coverage"] = _ablation_components(sorted(ctx["main"].module.state_dict()))
        require(all(name in initial_state for names in components.values() for name in names),
                "POINTER_ABLATION_INITIAL_NAME")
        restore_pin = ctx["checkpoint_pins"]["final"]
        restored = _restore_pointer(ctx, path=artifacts / "final.pt", pin=restore_pin, encoder=ctx["encoder"])
        _, baseline = _evaluate(restored, ctx["held_packets"], "ablation_baseline", artifacts,
                                started=ctx["started"], progress=ctx["phase"], work=ctx["work"])
        baseline_accuracy = baseline["correct"] / baseline["total"]
        report["baseline"] = {"correct": baseline["correct"], "total": baseline["total"],
                              "accuracy": baseline_accuracy,
                              "kind_splits": _split_score(baseline, {"held_back": ctx["held_set"]})}
        del restored
        rows = {}
        for name, _prefixes in ABLATION_COMPONENTS:
            _deadline(ctx["started"])
            ctx["phase"]("ablation_" + name)
            began = time.monotonic()
            restored = _restore_pointer(ctx, path=artifacts / "final.pt", pin=restore_pin,
                                        encoder=ctx["encoder"])
            reset = _reset_component(torch, pointer_module, restored, initial_state, components[name])
            _, scored = _evaluate(restored, ctx["held_packets"], "ablation_" + name, artifacts,
                                  started=ctx["started"], progress=ctx["phase"], work=ctx["work"])
            accuracy = scored["correct"] / scored["total"]
            rows[name] = {**reset, "correct": scored["correct"], "total": scored["total"],
                          "accuracy": accuracy, "baseline_accuracy": baseline_accuracy,
                          "accuracy_drop": baseline_accuracy - accuracy,
                          "elapsed_seconds": time.monotonic() - began}
            del restored
        report["ablations"] = rows
        report["status"] = "COMPLETE"
    except Exception as error:                                   # noqa: BLE001 - reported, never fatal
        report["failure"] = {"schema": FAILURE_SCHEMA, "type": type(error).__name__,
                             "detail": str(error)[:1000]}
    _publish(artifacts / "ablations.json", report)
    return report


# ======================================================================================================
# 12. PHASE: source verification, timing, delivery.
# ======================================================================================================
def _final_source_verification(ctx):
    """The live tree, the wheels and the loaded-source attestation, all unchanged since preflight."""
    from .rpa_learning_worker import verify_worker_packages
    artifacts = ctx["artifacts"]
    require(canonical(contract.input_inventory(ctx["root"])) == canonical(ctx["config"]["inputs"]),
            "SOURCES_CHANGED")
    packages_after = verify_worker_packages(ctx["root"])
    require(ctx["packages_before"]["source_files"] == packages_after["source_files"], "WHEEL_SOURCES_CHANGED")
    _publish(artifacts / "installed_sources.json",
             {"before": ctx["packages_before"], "after": packages_after})
    _publish(artifacts / "loaded_sources.json",
             {"before": ctx["loaded_before"], "after": ctx["attestor"].snapshot()})


def _effective_required(ctx):
    """The names a COMPLETE run must actually have produced, after the report-only checks reported."""
    names = tuple(ctx["required_artifacts"])
    dropped = set()
    produced = ctx["phase_a"].get("checkpoints", {})
    for name in ctx["plan"]["phase_a"]:
        if name not in produced:
            dropped.add("checkpoint_check_vectors_%s.json" % name)
    if ctx["ablations"].get("status") != "COMPLETE":
        for phase_name in ctx["plan"]["ablation_phases"]:
            dropped.add(phase_name + "_predictions.json")
            dropped.add(phase_name + "_scoring.json")
    return tuple(name for name in names if name not in dropped), sorted(dropped)


def _report_only_status(ctx):
    """Each report-only check's OWN `status`, and `None` when it never produced its artifact at all.

    `None` is a MISSING status, never a new status word: it is what makes "the check ran, and failed"
    distinguishable from "the check never started", which a job that reports only `SUCCESS_STATUS` cannot
    otherwise tell (review R2, MAJOR 2). `run()` reads these, it never restates them.
    """
    return {name: (ctx.get(key) or {}).get("status") for name, key in REPORT_ONLY_CHECKS}


def _degraded_checks(ctx):
    """The report-only checks that did NOT reach `COMPLETE`, sorted. EMPTY means all three ran to completion.

    Report-only is kept: a degraded check is RECORDED here and the job still succeeds. This list is the only
    thing that separates a job that ran its ablations from one that never started them.
    """
    statuses = _report_only_status(ctx)
    return sorted(name for name, status in statuses.items() if status != "COMPLETE")


def _phase_timings(ctx):
    """DG9: this job measures its own cost, exactly, and projects the registered one.

    `projected_worker_seconds` is the WORKER CLOCK and keeps that meaning: the registered training,
    evaluation and phase-A seconds plus this job's measured worker-side glue. It is NOT the number the owner
    pays for. The owner pays INSTANCE seconds, so two terms the old projection omitted are now explicit
    (review R2, MAJOR 1):

      * the MEASURED non-worker overhead -- boot, package install and delivery, 598.188883544 s
        (`MEASURED_NON_WORKER_OVERHEAD_SECONDS`; the float64 result of that subtraction is
        598.1888835440004, and the last four digits are the binary-representation tail, not a round),
        which is instance time that never reaches this clock; and
      * any registered phase this job did not run. Its seconds sit inside `unmeasured` only when it actually
        ran, and this file never estimates an unmeasured phase, so those phases are named in
        `unmeasured_instance_terms` instead of being estimated, and the instance projection is then a LOWER
        BOUND by exactly those terms.

    `projected_instance_seconds` is the new quantity, and `within_owner_threshold` is decided against IT,
    not against the worker projection -- `OWNER_PROJECTION_THRESHOLD_SECONDS` is a spend boundary, and
    crossing it requires a NEW owner approval, so a true reading must be true of the quantity being paid
    for. A lower bound that is under the threshold does not authorize the spend: `within_owner_threshold` is
    therefore also false whenever `unmeasured_instance_terms` is non-empty, and the raw comparison on the
    measured terms alone stays available, named, in
    `within_owner_threshold_on_the_measured_instance_terms_only`.
    """
    report = ctx["report"]
    stats, plan = ctx["stats"], ctx["plan"]
    pass_summaries = report.get("pass_summaries", [])
    measured_updates = sum(row["updates"] for row in pass_summaries)
    training = report.get("training_seconds") or 0.0
    seconds_per_update = training / measured_updates if measured_updates else None
    evaluation_seconds = [row["elapsed_seconds"] for row in ctx["work"]
                          if row["phase"].startswith(("course_", "heldback_", "development_", "retention_",
                                                      "ablation_"))]
    measured_evaluations = len(evaluation_seconds)
    seconds_per_evaluation = (sum(evaluation_seconds) / measured_evaluations) if measured_evaluations else None
    phase_a = ctx["phase_a"] or {}
    phase_a_seconds = sum(row["elapsed_seconds"] for row in phase_a.get("checkpoints", {}).values())
    phase_a_count = len(phase_a.get("checkpoints", {}))
    registered_updates = PASSES * stats["updates_per_pass"]
    elapsed = report.get("elapsed_seconds", time.monotonic() - ctx["started"])
    # The registered phases this plan did NOT run. Their cost is in this job's `unmeasured` only if they ran.
    unmeasured_terms = sorted((["checkpoint_check_phase_b"] if not plan["phase_b"] else [])
                              + (["ablations"] if not plan["ablations"] else []))
    projection = None
    if seconds_per_update is not None and phase_a_count:
        unmeasured = elapsed - training - sum(evaluation_seconds) - phase_a_seconds
        projected_seconds = (unmeasured + registered_updates * seconds_per_update
                             + (seconds_per_evaluation or 0.0) * len(FULL_PLAN["evaluation_phases"])
                             + phase_a_seconds / phase_a_count * len(PHASE_A_CHECKPOINTS))
        projected_instance_seconds = projected_seconds + MEASURED_NON_WORKER_OVERHEAD_SECONDS
        within_on_the_measured_terms_only = projected_instance_seconds <= OWNER_PROJECTION_THRESHOLD_SECONDS
        projection = {"registered_passes": PASSES, "registered_main_updates": registered_updates,
                      "registered_evaluations": len(FULL_PLAN["evaluation_phases"]),
                      "measured_updates": measured_updates, "seconds_per_update": seconds_per_update,
                      "projected_main_training_seconds": registered_updates * seconds_per_update,
                      "measured_evaluations": measured_evaluations,
                      "seconds_per_evaluation": seconds_per_evaluation,
                      "projected_phase_a_seconds": phase_a_seconds / phase_a_count * len(PHASE_A_CHECKPOINTS),
                      "projected_phase_b_seconds": None,
                      "measured_other_seconds": unmeasured,
                      "projected_worker_seconds": projected_seconds,
                      "non_worker_overhead_seconds": MEASURED_NON_WORKER_OVERHEAD_SECONDS,
                      "non_worker_overhead_source": (
                          "measured, not estimated: 6,064 s of practice instance time minus 5,465.811116456 s "
                          "of practice worker clock (records/typed_practice_001/receipt_20260917/"
                          "checkpoints/worker_report.json); pre_design/AWS_SMOKE_S10_PLAN.md:29 writes the "
                          "same measurement rounded as \"598.2 s\""),
                      "projected_instance_seconds": projected_instance_seconds,
                      "instance_seconds_max": contract.INSTANCE_SECONDS_MAX,
                      "worker_deadline_seconds": contract.WORKER_DEADLINE_SECONDS,
                      "headroom_seconds": contract.WORKER_DEADLINE_SECONDS - projected_seconds,
                      "within_deadline": projected_seconds < contract.WORKER_DEADLINE_SECONDS,
                      "within_instance_seconds_max":
                          projected_instance_seconds < contract.INSTANCE_SECONDS_MAX,
                      "owner_threshold_seconds": OWNER_PROJECTION_THRESHOLD_SECONDS,
                      "owner_threshold_applies_to": "projected_instance_seconds",
                      "unmeasured_instance_terms": unmeasured_terms,
                      "projected_instance_seconds_is_a_lower_bound": bool(unmeasured_terms),
                      "within_owner_threshold_on_the_measured_instance_terms_only":
                          within_on_the_measured_terms_only,
                      "within_owner_threshold": (within_on_the_measured_terms_only and not unmeasured_terms),
                      "projection_complete": bool(plan["phase_b"]),
                      "projection_incomplete_because": (None if plan["phase_b"] else
                                                        "PHASE B DID NOT RUN IN THIS JOB; an unmeasured phase "
                                                        "is reported as None and never estimated")}
    body = {"schema": "cncm.typed-pointer-phase-timings/0.1", "phases": ctx["timings"],
            "worker_clock_seconds": elapsed, "worker_deadline_seconds": contract.WORKER_DEADLINE_SECONDS,
            "instance_seconds_max": contract.INSTANCE_SECONDS_MAX, "max_wall_seconds": contract.MAX_WALL_SECONDS,
            "non_worker_overhead_seconds": MEASURED_NON_WORKER_OVERHEAD_SECONDS,
            "practice_reference": {"worker_clock_seconds": PRACTICE_WORKER_CLOCK_SECONDS,
                                   "instance_seconds": PRACTICE_INSTANCE_SECONDS,
                                   "worker_deadline_seconds": contract.WORKER_DEADLINE_SECONDS,
                                   "source": "records/typed_practice_001/receipt_20260917/checkpoints/"
                                             "worker_report.json elapsed_seconds"},
            "measured": {"updates": measured_updates, "training_seconds": training,
                         "seconds_per_update": seconds_per_update, "evaluations": measured_evaluations,
                         "seconds_per_evaluation": seconds_per_evaluation,
                         "phase_a_seconds": phase_a_seconds, "phase_a_checkpoints": phase_a_count,
                         "ablations_seconds": (ctx["ablations"].get("ablations") and sum(
                             row["elapsed_seconds"] for row in ctx["ablations"]["ablations"].values())) or None},
            "projection": projection, "delivery_included": False, "boundary": BOUNDARY}
    _publish(ctx["artifacts"] / "phase_timings.json", body)
    report["phase_timings"] = {"worker_clock_seconds": body["worker_clock_seconds"],
                               "phases": body["phases"], "measured": body["measured"],
                               "projection": projection}


def deliver(results, artifacts, report, *, failed):
    """The pointer result envelope: this study's schemas, this study's statuses, create-only throughout."""
    results, artifacts = Path(results), Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    required = tuple(report.get("required_artifacts", EXPECTED_ARTIFACTS))
    if not failed:
        require(set(required) - {"worker_report.json", "measurements.json"}
                <= {path.name for path in artifacts.iterdir()}, "POINTER_REQUIRED_ARTIFACTS")
    _publish(artifacts / "worker_report.json", report)
    summary = {key: report.get(key) for key in ("job", "source_sha", "status", "runtime", "elapsed_seconds",
        "condition", "model_seed", "failure", "main_training_delta", "interference_delta", "global_actual_work",
        "checkpoint_reload_verified", "scores", "development_scores", "retention_scores", "pass_summaries",
        "initial_model_identity", "whole_container_identity", "model_identity", "phase_timings",
        "schedule_plan_mode", "claimed_bearing_run", "claim_bearing", "checkpoint_check_phase_a_status",
        "checkpoint_check_phase_b_status", "ablation_status", "artifacts_dropped_from_the_required_set",
        "degraded_checks", "degraded_checks_absent_means", "report_only_status")}
    summary.update(learning_on_held_back_established=False, boundary=BOUNDARY)
    _publish(artifacts / "measurements.json", summary)
    entries = []
    for path in sorted(artifacts.iterdir()):
        if path.name.endswith(".partial"):
            continue
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 64 * 1024 ** 2,
                "ARTIFACT_BOUND")
        raw = path.read_bytes()
        entries.append({"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    require(len(entries) <= 500, "ARTIFACT_COUNT")
    _publish(artifacts / "manifest.json", {"artifacts": entries})
    result = {"schema": RESULT_SCHEMA, "job": report["job"], "artifacts": entries,
              "status": FAILED_STATUS if failed else DELIVERED_STATUS, "summary": summary,
              "failure": report.get("failure"), "boundary": BOUNDARY}
    pin = _publish(results / "result.json", result)
    _publish_bytes(results / "result.json.sha256", (pin["sha256"] + "\n").encode("ascii"))
    return result


# ======================================================================================================
# 13. THE RUN.
# ======================================================================================================
def run(config, root, results, artifacts, attestor=None):
    started = time.monotonic()
    root, results, artifacts = Path(root).resolve(), Path(results).resolve(), Path(artifacts).resolve()
    config = contract.validate_config(config, root)
    frozen, tokenizer, development = contract.load_material(root)
    design = config["design"]
    plan, claim_bearing = schedule_plan()
    required_artifacts = expected_artifact_names(plan)
    require(not artifacts.exists() and artifacts.parent == results and not (results / "result.json").exists(),
            "FRESH_RESULT_DIRECTORY")
    results.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir()
    staging = results.parent / "pointer_staging"
    require(not staging.exists(), "FRESH_STAGING_DIRECTORY")
    staging.mkdir()
    from cas_meta2.typed_teaching import practice_contract as practice_source  # noqa: F401 - COURSE_PATH only
    ctx = {"config": config, "root": root, "results": results, "artifacts": artifacts, "staging": staging,
           "started": started, "design": design, "frozen": frozen, "tokenizer": tokenizer,
           "development": development, "plan": plan, "claim_bearing": claim_bearing,
           "required_artifacts": required_artifacts, "course_path": practice_source.COURSE_PATH,
           "work": [], "timings": [], "checkpoint_pins": {}, "predictions": {}, "encoding": {},
           "main": None, "progress": None, "phase_a": {}, "phase_b": {}, "ablations": {}, "last_seal": None,
           "retained_predictions": {}}
    report = {"schema": "cncm.typed-pointer-worker-report/0.1", "candidate": CANDIDATE, "job": config["job"],
              "source_sha": config["source_sha"], "inputs": config["inputs"], "design": design,
              "condition": design["condition"], "model_seed": design["model_seed"], "boundary": BOUNDARY,
              "learning_on_held_back_established": False, "phase": "admitted",
              "claimed_bearing_run": claim_bearing, "claim_bearing": claim_bearing,
              "schedule_plan_mode": "REGISTERED" if claim_bearing else "REDUCED",
              "required_artifacts": list(required_artifacts), "registered_artifacts": list(EXPECTED_ARTIFACTS),
              "worker_deadline_seconds": contract.WORKER_DEADLINE_SECONDS,
              "passes": plan["passes"], "registered_passes": PASSES}
    ctx["report"] = report
    try:
        ctx["progress"] = base._ProgressWriter(results, started)

        def phase(name, **values):
            report["phase"] = name
            return ctx["progress"].emit(name, **values)

        ctx["phase"] = phase
        phase("preflight")
        ctx["startup_imports"] = deepcopy(CHECKPOINT_CHECK_IMPORTS)
        ctx["torch"], ctx["device"], ctx["loaded_before"], ctx["packages_before"] = _preflight(
            root, attestor, report)
        ctx["attestor"] = attestor
        _publish(artifacts / "schedule_plan.json",
                 {"schema": "cncm.typed-pointer-schedule-plan/0.1", "plan": plan, "registered_plan": FULL_PLAN,
                  "claim_bearing": claim_bearing, "mode": "REGISTERED" if claim_bearing else "REDUCED",
                  "reduced_schedule_env": REDUCED_SCHEDULE_ENV,
                  "reduced_schedule_requested": reduced_request() is not None,
                  "registered_passes": PASSES, "registered_constants_changed": False,
                  "required_artifacts": list(required_artifacts),
                  "artifacts_differ_from_the_registered_contract":
                      list(required_artifacts) != list(EXPECTED_ARTIFACTS),
                  "registered_required_artifacts": list(EXPECTED_ARTIFACTS),
                  "checkpoint_check_startup_imports": ctx["startup_imports"], "boundary": BOUNDARY})

        with _timed(ctx["timings"], "public_packet_preparation"):
            phase("public_packet_preparation")
            _public_packet_preparation(ctx)

        with _timed(ctx["timings"], "checkpoint_check_phase_a"):
            phase("checkpoint_check_phase_a")
            ctx["phase_a"] = _checkpoint_check_phase_a(ctx)
            report["checkpoint_check_phase_a_status"] = ctx["phase_a"]["status"]
            # R1-2. The run's OWN reading of when phase A returned. `_seed_and_double_build` compares this
            # against the reading it takes immediately before it builds the container, so the ordering the
            # model-identity artifact claims is a MEASUREMENT and not a literal. Recorded whether phase A
            # completed or failed, because "phase A returned before the model was seeded" and "phase A
            # completed" are two different facts and the artifact reports both separately.
            ctx["phase_a_returned_at"] = time.monotonic()
            _deadline(started)

        with _timed(ctx["timings"], "fresh_initialization"):
            phase("fresh_initialization")
            _seed_and_double_build(ctx)
            _deadline(started)

        report["scores"], report["development_scores"] = {}, []
        ctx["sides"] = {"held_back": ctx["held_set"], "trained": ctx["trained_set"],
                        "excluded": ctx["excluded_set"]}
        with _timed(ctx["timings"], "main_training"):
            _main_training(ctx)

        with _timed(ctx["timings"], "retention_and_interference"):
            phase("retention_and_interference")
            _retention_and_interference(ctx)

        with _timed(ctx["timings"], "reloads_and_replays"):
            _reloads_and_replays(ctx)
        totals = matched._sum_deltas([row["delta"] for row in ctx["work"]])
        expected_updates = (ctx["stats"]["main_updates"]
                            + (contract.INTERFERENCE_UPDATES if plan["interference"] else 0)
                            + (contract.REPLAY_UPDATES if plan["replays"] else 0))
        require(totals["optimizer_updates"] == totals["backward_calls"] == expected_updates,
                "GLOBAL_UPDATE_COUNTS")
        report["global_actual_work"] = {"phases": ctx["work"], "totals": totals,
            "historical_restored_counters_counted_again": False,
            "main_presentations": ctx["stats"]["presentations"],
            "interference_presentations": (contract.INTERFERENCE_UPDATES * contract.INTERFERENCE_BATCH
                                           if plan["interference"] else 0),
            "encoder_main_counters": ctx["main"].encoder.work_counters(),
            "expected_updates": expected_updates}

        with _timed(ctx["timings"], "checkpoint_check_phase_b"):
            phase("checkpoint_check_phase_b")
            ctx["phase_b"] = _checkpoint_check_phase_b(ctx)
            report["checkpoint_check_phase_b_status"] = ctx["phase_b"]["status"]

        with _timed(ctx["timings"], "ablations"):
            phase("ablations")
            ctx["ablations"] = _ablations(ctx)
            report["ablation_status"] = ctx["ablations"]["status"]

        # Review R2, MAJOR 2. The three report-only checks record their own failure INSIDE their artifact by
        # design, so the job's own status cannot carry it. These two fields do: which of them did not reach
        # `COMPLETE`, and each one's own status with `None` for a check that never started. Report-only is
        # preserved -- a degraded check is recorded and the job still succeeds.
        report["report_only_status"] = _report_only_status(ctx)
        report["degraded_checks"] = _degraded_checks(ctx)
        report["degraded_checks_absent_means"] = "EVERY_REPORT_ONLY_CHECK_REACHED_COMPLETE"

        with _timed(ctx["timings"], "final_source_verification"):
            phase("final_source_verification")
            _final_source_verification(ctx)
        _deadline(started)
        report.update(status=SUCCESS_STATUS, checkpoint_reload_verified=True,
                      peak_cuda_allocated_bytes=int(ctx["torch"].cuda.max_memory_allocated(ctx["device"])),
                      peak_cuda_reserved_bytes=int(ctx["torch"].cuda.max_memory_reserved(ctx["device"])),
                      elapsed_seconds=time.monotonic() - started, passes=plan["passes"],
                      main_updates=ctx["stats"]["main_updates"], global_updates=expected_updates)
        effective, dropped = _effective_required(ctx)
        report["required_artifacts"] = list(effective)
        report["artifacts_dropped_from_the_required_set"] = dropped
        with _timed(ctx["timings"], "timing_and_delivery"):
            _phase_timings(ctx)
            phase("delivery", main_updates=ctx["stats"]["main_updates"], global_updates=expected_updates)
            return deliver(results, artifacts, report, failed=False)
    except Exception as error:
        salvaged = []
        try:
            if staging.exists():
                for leftover in sorted(staging.iterdir()):
                    if leftover.is_file() and leftover.stat().st_size > 0:
                        _move_in(leftover, artifacts / ("failed_" + leftover.name))
                        salvaged.append(leftover.name)
        except Exception as salvage_error:                        # noqa: BLE001 - never mask the failure
            report["staging_salvage_failure"] = type(salvage_error).__name__
        report["staging_salvaged"] = salvaged
        # The same two readings on the FAILED envelope: a check that never started reports `None`, and it is
        # named in `degraded_checks` rather than left absent (review R2, MAJOR 2).
        report["report_only_status"] = _report_only_status(ctx)
        report["degraded_checks"] = _degraded_checks(ctx)
        report["degraded_checks_absent_means"] = "EVERY_REPORT_ONLY_CHECK_REACHED_COMPLETE"
        report.update(status=FAILED_STATUS, elapsed_seconds=time.monotonic() - started,
                      failure={"schema": FAILURE_SCHEMA, "type": type(error).__name__,
                               "detail": str(error)[:1000]},
                      completed_work_phases=ctx["work"])
        if ctx["main"] is not None:
            report["partial_main"] = {"cursor": ctx["main"].cursor,
                                      "model_revision": ctx["main"].model_revision,
                                      "counters": deepcopy(ctx["main"].counters),
                                      "learner_failed": ctx["main"].failed}
        if ctx["progress"] is not None:
            try:
                ctx["progress"].emit("failed/" + report["phase"],
                                     completed_updates=0 if ctx["main"] is None else ctx["main"].cursor)
            except Exception as progress_error:                   # noqa: BLE001 - recorded, never raised
                report["progress_write_failure"] = type(progress_error).__name__
        deliver(results, artifacts, report, failed=True)
        raise
