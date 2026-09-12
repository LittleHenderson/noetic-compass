"""CAS_RDCJT_001: the recurrent CJT as a candidate computation profile.

Built from the owner-supplied directive "Recurrent Neural CJT v0.1" (the handoff
zip, plan .md and profile .json were delivered as sandbox links, not local files, so
the pasted plan text is the binding source and that provenance is recorded here).

The capability: process the problem, retain the internal state, process that state
again **while the original encoded problem is still supplied**, and answer after a
bounded number of passes through the SAME transformation.

    s_0   = 0
    s_1   = F_theta(e)
    s_k+1 = F_theta(e + B(s_k, e))

    B(s, e) = lambda * RMS(e) * s / sqrt(RMS(e)^2 + RMS(s)^2 + epsilon^2)

with lambda = 0.5 and epsilon = 1e-6 as proposed settings, and the final state going
through the **existing scoring function unchanged**.

Four boundaries this module enforces in code rather than in prose, because each is
easy to violate by accident:

* **No new trainable matrices.** The only transformation is the one passed in as
  ``core``; this module adds arithmetic and a loop, nothing with parameters. So
  additional capacity cannot be what distinguishes the two learners.
* **Thinking longer is not learning.** Nothing here updates weights. The accounting
  object counts computation, and it distinguishes batched transformation calls from
  sample-level passes, because equal teaching exposure is not equal training compute.
* **Depth eight is the answer at depth eight.** ``select_best_depth`` exists only to
  raise: choosing the best intermediate answer with a checker is the failure this
  candidate must not commit.
* **Fresh state per question.** ``per_question_state`` allocates a separate state per
  item, so an answer-bearing state cannot be carried from a guided exercise into an
  unassisted test.

Numerical convergence is telemetry, not a truth certificate: a state can settle while
the answer is wrong, and can keep moving while the answer is right.
"""
from __future__ import annotations

import json
from hashlib import sha256

SCHEMA = "cas.recurrent-cjt/0.1"

#: The declared training depths and the primary evaluation allowance.
DEPTHS = (1, 2, 4, 8)
PRIMARY_DEPTH = 8

#: Proposed feedback settings. Deliberately not CAS-Ohm quantities and not supplied
#: by the referenced paper: a declared numerical design choice.
LAMBDA = 0.5
EPSILON = 1e-6

#: Sixteen rounds, each assigned one depth, every depth four times. CFC rounds are a
#: different kind of repetition from recurrent passes and both stay visible.
ROUND_DEPTH_SCHEDULE = (1, 2, 4, 8,
                        2, 4, 8, 1,
                        4, 8, 1, 2,
                        8, 1, 2, 4)

#: The four phases of one CFC round, with their decisions and updates, from the
#: constructor plan. The same course is used for both experimental conditions.
ROUND_PHASES = (("WITHIN_CUBE", 28, 4), ("ACROSS_FACE", 12, 2),
                ("RETURN_TO_CUBE", 8, 1), ("OLD_SKILL_MAINTENANCE", 8, 1))
DECISIONS_PER_ROUND = sum(phase[1] for phase in ROUND_PHASES)
UPDATES_PER_ROUND = sum(phase[2] for phase in ROUND_PHASES)

#: Evaluation depths, including the mechanism control, and their meanings.
EVALUATION_DEPTHS = ("R1", "R2", "R4", "R8", "RESET_8")

#: Declared planning counts for the whole course, for both conditions.
DECLARED_COURSE = {"rounds": len(ROUND_DEPTH_SCHEDULE),
                   "teaching_decisions": DECISIONS_PER_ROUND * len(ROUND_DEPTH_SCHEDULE),
                   "optimizer_updates": UPDATES_PER_ROUND * len(ROUND_DEPTH_SCHEDULE)}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return sha256(canonical(value)).hexdigest()


# --------------------------------------------------------------------------
# the arithmetic
# --------------------------------------------------------------------------

def rms(values):
    """Root mean square of a plain sequence: the reference implementation."""
    require(len(values) > 0, "RMS_EMPTY_VECTOR")
    total = 0.0
    for value in values:
        total += float(value) * float(value)
    return (total / len(values)) ** 0.5


def feedback(state, encoded, *, lambda_=LAMBDA, epsilon=EPSILON, rms_fn=rms,
             cast=float):
    """B(s, e): the previous state carried back, scaled against the input's RMS.

    In exact arithmetic the result's RMS cannot exceed ``lambda_ * rms(e)``: the
    denominator is at least ``rms(s)``, which cancels it. That bounds THIS term; it
    proves nothing about the whole process converging or reasoning correctly.

    ``cast`` is the one hook the numerical path needs. The default ``float`` coerces
    a plain sequence; a tensor path passes an identity instead, because ``float()``
    on a tensor DETACHES it from the autograd graph. With the default, this function
    would train the first pass and quietly freeze the rest.
    """
    require(len(state) == len(encoded), "FEEDBACK_SHAPE_MISMATCH")
    input_rms = rms_fn(encoded)
    state_rms = rms_fn(state)
    denominator = (input_rms ** 2 + state_rms ** 2 + epsilon ** 2) ** 0.5
    scale = lambda_ * input_rms / denominator
    return [scale * cast(value) for value in state]


def reinjected(encoded, state, *, lambda_=LAMBDA, epsilon=EPSILON, rms_fn=rms,
               cast=float):
    """e + B(s, e): what the transformation receives on the next pass."""
    carried = feedback(state, encoded, lambda_=lambda_, epsilon=epsilon,
                       rms_fn=rms_fn, cast=cast)
    return [cast(base) + extra for base, extra in zip(encoded, carried)]


class Accounting:
    """Explicit per-pass charging. One update per batch, whatever the depth.

    ``batched_calls`` counts passes through the transformation for a whole batch;
    ``sample_passes`` counts passes per question. Eight internal passes are eight
    sample passes and ONE optimizer update, never eight updates.
    """

    def __init__(self):
        self.batched_calls = 0
        self.sample_passes = 0
        self.optimizer_updates = 0
        self.depths = []

    def charge(self, *, depth, samples):
        require(depth in DEPTHS, "ACCOUNTING_DEPTH:" + str(depth))
        require(int(samples) >= 0, "ACCOUNTING_SAMPLES")
        self.batched_calls += depth
        self.sample_passes += depth * int(samples)
        self.depths.append(depth)
        return self

    def update(self):
        self.optimizer_updates += 1
        return self

    def report(self):
        depths = self.depths or [0]
        return {"schema": SCHEMA, "batched_core_forward_calls": self.batched_calls,
                "sample_level_core_passes": self.sample_passes,
                "optimizer_updates": self.optimizer_updates,
                "mean_depth": round(sum(depths) / len(depths), 4),
                "trainable_parameter_count": "unchanged: no new trainable matrices",
                "note": ("derived planning counts, not measured GPU work; equal "
                         "teaching exposure is not equal training compute")}


def per_question_state(count, *, width, zeros=None):
    """A fresh, separate working state per question.

    Carrying an answer-bearing state between questions is what this prevents, so the
    allocation is per item rather than per batch or per cube.
    """
    require(int(count) > 0 and int(width) > 0, "STATE_SHAPE")
    allocate = zeros or (lambda: [0.0] * int(width))
    return [allocate() for _ in range(int(count))]


def run_passes(encoded, core, *, depth, state=None, accounting=None,
               lambda_=LAMBDA, epsilon=EPSILON, rms_fn=rms, cast=float,
               zeros=None, reset_each_pass=False):
    """Carry the state through ``depth`` passes of the same transformation.

    ``reset_each_pass`` implements RESET_8: eight computations with the working state
    discarded between them. Under a deterministic transformation it must reproduce
    the one-pass result, which is what makes it a mechanism check rather than a
    competing architecture.

    ``rms_fn``, ``cast`` and ``zeros`` are the whole numerical seam. Both paths run
    THIS loop, so the reference arithmetic and the training path cannot drift apart.
    ``zeros`` exists because an initial state has to be built in the caller's backend:
    zero floats cannot be stacked into a tensor.
    """
    require(depth in DEPTHS, "DEPTH_NOT_DECLARED:" + str(depth))
    width = len(encoded)
    allocate = zeros or (lambda count: [0.0] * count)
    # The shortcut is an identity, not a semantic change: with a zero state, B is the
    # zero vector and e + 0 is e bitwise, so the one-pass path could go through
    # ``reinjected`` and land on the same value. It is kept because depth one is the
    # matched condition and should be the existing computation literally.
    shortcut = depth == 1 and state is None
    current = list(allocate(width)) if state is None else list(state)
    require(len(current) == width, "STATE_WIDTH_MISMATCH")
    for _ in range(depth):
        incoming = (list(encoded) if (reset_each_pass or shortcut)
                    else reinjected(encoded, current, lambda_=lambda_,
                                    epsilon=epsilon, rms_fn=rms_fn, cast=cast))
        current = list(core(incoming))
        require(len(current) == width, "CORE_WIDTH_CHANGED")
    if accounting is not None:
        accounting.charge(depth=depth, samples=1)
    return current


def select_best_depth(*_args, **_kwargs):
    """Deliberately unsupported.

    Picking the depth whose answer the checker prefers would report a selected
    answer as the model's answer. The answer at depth N is the answer at depth N,
    even when it spoiled an answer that was correct at a lower depth.
    """
    raise ValueError("DEPTH_SELECTION_BY_CHECKER_IS_NOT_A_SUPPORTED_PATH")


def two_way_tally(per_depth_correct):
    """What the depth sweep must report: gains AND losses, per depth.

    ``per_depth_correct`` maps depth to a per-question mapping of correctness, so
    the comparison is paired on the question rather than on the aggregate.
    """
    require(1 in per_depth_correct, "TALLY_REQUIRES_THE_ONE_PASS_BASELINE")
    baseline = per_depth_correct[1]
    report = {}
    for depth in sorted(per_depth_correct):
        if depth == 1:
            continue
        rows = per_depth_correct[depth]
        gained = sorted(key for key, value in rows.items()
                        if value and not baseline.get(key))
        lost = sorted(key for key, value in rows.items()
                      if not value and baseline.get(key))
        report["R%d" % depth] = {"gained": gained, "lost": lost,
                                 "gained_count": len(gained),
                                 "lost_count": len(lost),
                                 "net": len(gained) - len(lost),
                                 "compared_questions": len(rows)}
    return report


def depth_for_round(round_index):
    require(0 <= int(round_index) < len(ROUND_DEPTH_SCHEDULE),
            "ROUND_OUTSIDE_THE_DECLARED_COURSE:" + str(round_index))
    return ROUND_DEPTH_SCHEDULE[int(round_index)]


def depth_coverage():
    """Every declared depth receives four complete rounds, including maintenance."""
    counts = {}
    for depth in ROUND_DEPTH_SCHEDULE:
        counts[depth] = counts.get(depth, 0) + 1
    return counts


def phase_batches(phase):
    """The declared batch sizes for one course phase.

    Taken from the constructor's implementation profile rather than restated here: a
    second derivation of the same allowance would drift away from the first. The
    phases flush at their boundaries, so within-cube updates can affect the
    across-face work that follows.
    """
    from ..rpm_cfc_constructor.diagnosis import phase_batches as declared
    return declared(phase)


def phase_update_counts():
    """Updates per phase per round, DERIVED from the declared batch structure.

    This is what makes 8 updates per round a derivation and not a copied number:
    ceil-per-phase of [8,8,8,4] / [8,4] / [8] / [8] is 4 + 2 + 1 + 1.
    """
    counts = {}
    for phase, decisions, declared_updates in ROUND_PHASES:
        batches = phase_batches(phase)
        require(sum(batches) == decisions,
                "COURSE_PHASE_DECISIONS:%s:%d!=%d"
                % (phase, sum(batches), decisions))
        require(len(batches) == declared_updates,
                "COURSE_PHASE_UPDATES:%s:%d!=%d"
                % (phase, len(batches), declared_updates))
        counts[phase] = {"decisions": decisions, "batches": batches,
                         "updates": len(batches)}
    return counts


def implementation_calls(*, depths=ROUND_DEPTH_SCHEDULE, module_calls_per_decision=1):
    """What the loader that exists today actually issues, per condition.

    ``GraphLearner.forward`` takes ONE position, so a batch of eight is eight
    transformation calls, not one. The declared table counts a batched call as a
    single pass over a whole batch, which is what a genuinely batched loader would
    issue. Sample-level passes are the same number under either convention;
    transformation calls are not. The ratio between the two learners is 3.75 either
    way, and both figures are reported so neither can stand in for the other.
    """
    one_pass = recurrent = 0
    for depth in depths:
        for _phase, decisions, _updates in ROUND_PHASES:
            one_pass += decisions * module_calls_per_decision
            recurrent += decisions * module_calls_per_decision * depth
    return {"one_pass_transformation_calls": one_pass,
            "recurrent_transformation_calls": recurrent,
            "ratio": round(recurrent / one_pass, 4),
            "convention": ("one transformation call per question, which is what "
                           "GraphLearner.forward issues today; a genuinely batched "
                           "loader would issue the declared 128 / 480"),
            "declared_sample_passes_one_pass": sum(
                decisions for _p, decisions, _u in ROUND_PHASES) * len(depths)}


def evaluation_depth_plan():
    """The declared evaluation depths, and what each one is for."""
    return {
        "R1": {"depth": 1, "reset_each_pass": False,
               "meaning": "the matched one-pass condition; identical to the "
                          "existing learner's computation"},
        "R2": {"depth": 2, "reset_each_pass": False,
               "meaning": "two passes, state carried"},
        "R4": {"depth": 4, "reset_each_pass": False,
               "meaning": "four passes, state carried"},
        "R8": {"depth": 8, "reset_each_pass": False,
               "meaning": "eight passes, state carried: the primary allowance"},
        "RESET_8": {"depth": 8, "reset_each_pass": True,
                    "meaning": "eight computations with the state discarded between "
                               "them: a mechanism check, not a second architecture"},
    }


def course_cost(*, depths=ROUND_DEPTH_SCHEDULE):
    """The declared per-learner cost, derived rather than asserted.

    One-pass: one batched transformation call and one sample pass per decision.
    Recurrent: ``depth`` of each, and still ONE optimizer update per batch.
    """
    require(tuple(depths) == ROUND_DEPTH_SCHEDULE or len(depths) == len(
        ROUND_DEPTH_SCHEDULE), "COST_SCHEDULE_LENGTH")
    one_pass = {"batched_core_forward_calls": 0, "sample_level_core_passes": 0,
                "optimizer_updates": 0}
    recurrent = {"batched_core_forward_calls": 0, "sample_level_core_passes": 0,
                 "optimizer_updates": 0}
    for depth in depths:
        for _phase, decisions, updates in ROUND_PHASES:
            one_pass["batched_core_forward_calls"] += updates
            one_pass["sample_level_core_passes"] += decisions
            one_pass["optimizer_updates"] += updates
            recurrent["batched_core_forward_calls"] += updates * depth
            recurrent["sample_level_core_passes"] += decisions * depth
            recurrent["optimizer_updates"] += updates
    recurrent["ratio_of_sample_passes"] = round(
        recurrent["sample_level_core_passes"]
        / one_pass["sample_level_core_passes"], 4)
    recurrent["trainable_parameters"] = "same as the one-pass learner"
    return {"one_pass": one_pass, "recurrent": recurrent,
            "declared": dict(DECLARED_COURSE),
            "phases": phase_update_counts(),
            "evaluation_depths": evaluation_depth_plan(),
            "implemented_calls": implementation_calls(depths=depths),
            "boundary": ("derived planning counts, not measured GPU work; encoding, "
                         "backward computation, readout, checkpointing and "
                         "evaluation add their own cost")}


def profile_document():
    """The frozen identity of this candidate, for the request and the receipt."""
    return {"schema": SCHEMA, "candidate": "CAS_RDCJT_001",
            "depths": list(DEPTHS), "primary_depth": PRIMARY_DEPTH,
            "round_depths": list(ROUND_DEPTH_SCHEDULE),
            "depth_coverage": depth_coverage(),
            "evaluation_depths": list(EVALUATION_DEPTHS),
            "lambda": LAMBDA, "epsilon": EPSILON,
            "new_trainable_matrices": 0,
            "reuses_one_transformation": True,
            "reinjects_the_original_input": True,
            "answering_scoring_unchanged": True,
            "optimizer_updates_per_batch": 1,
            "backpropagation": ("full through at most eight passes; no detach "
                                "between passes; no per-pass loss"),
            "depth_selection_by_checker": False,
            "state_scope": "one working state per question, never carried between",
            "source_provenance": ("owner-supplied directive 'Recurrent Neural CJT "
                                 "v0.1'; the handoff zip, plan and profile were "
                                 "sandbox links, so the pasted plan text is the "
                                 "binding source"),
            "profile_sha256": digest({"depths": list(DEPTHS),
                                      "round_depths": list(ROUND_DEPTH_SCHEDULE),
                                      "lambda": LAMBDA, "epsilon": EPSILON})}
