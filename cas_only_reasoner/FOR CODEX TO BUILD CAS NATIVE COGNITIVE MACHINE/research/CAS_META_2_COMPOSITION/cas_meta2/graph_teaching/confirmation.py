"""GRAPH6_CONFIRMATION_001 — repeat the successful learning and test fresh transfer.

Owner-directed (2026-09-09). ONE combined job, no chain of separately funded
diagnostics. Everything that made competence run 005 succeed stays frozen:

* the SAME practice records, teaching order, optimizer settings and 64 updates
  per candidate;
* the SAME encoder, tokenizer and ^6 module architecture — the encoder's random
  projection is built ONCE with the frozen encoder seed and shared by every
  candidate, so only the LEARNER initialization varies;
* the SAME registered fit comparison: mean after-loss < mean before-loss − 0.02.

What is new is the measurement, not the learner:

* three independently initialized candidate learners, each with its own
  optimizer state, each trained for 64 updates (192 updates total);
* a pre-registered FRESH panel of 30 graph families with one question per
  operation (90 cases) that excludes the teaching records and the previously
  examined dataset, including trivially renamed duplicates (``fresh_panel.py``);
* every candidate is measured on the SAME fresh panel BEFORE and AFTER training,
  and the paired change is reported with a family-clustered bootstrap interval
  and an exact McNemar test — the crucial comparison is trained vs untrained on
  the same new questions, not "did the machinery run";
* every scheduled candidate is reported; none is dropped for looking bad.

The preserved run-005 checkpoint is a special case: its weights were never
persisted (the run saved only the parameter digest
``cb008721b92144b4e0ef52e86c2c449415935110747aca18ff23229c05240e50``), and the
module bank was constructed without any seed, so those exact weights are not
reproducible. This module therefore reports the baseline row as UNAVAILABLE with
that reason, and optionally (owner's choice) runs a declared BASELINE
REPRODUCTION candidate whose digest is checked against the preserved one.
"""
from __future__ import annotations

import math
import random
from hashlib import sha256

from .graph import canonical, digest, require

SCHEMA = "cas-graph-training-graph6-confirmation-result/1"
CANDIDATE_SCHEMA = "cas-graph-training-graph6-confirmation-candidate/1"
VERDICT_SCHEMA = "cas-graph-training-graph6-confirmation-verdict/1"

# Frozen candidate (competence run 005 configuration).
FROZEN_ENCODER_SEED = 20260909
FROZEN_LEARNING_RATE = 0.003
FROZEN_MAX_OPTIMIZER_STEPS = 64
FROZEN_MAX_WALL_SECONDS = 600.0
FROZEN_ARM = "cas"
HISTORY_EVERY = 8

# Pre-declared learner initialization seeds: three INDEPENDENT learners, not
# three rounds of continued training on one checkpoint. The encoder seed above
# stays fixed, so these vary only the module/optimizer initialization.
LEARNER_SEEDS = (20260913, 20260914, 20260915)
CANDIDATE_COUNT = len(LEARNER_SEEDS)
TOTAL_OPTIMIZER_STEPS = CANDIDATE_COUNT * FROZEN_MAX_OPTIMIZER_STEPS   # 192

# Registered fit comparison (unchanged from run 005).
FIT_MARGIN = 0.02

# Pre-registered fresh-transfer criterion (declared BEFORE execution; the old
# 6/12 pilot threshold belonged to that 12-case panel and is NOT reused).
TRANSFER_MARGIN = 0.10        # +9 of 90 cases, paired, on the same fresh panel
TRANSFER_LEVEL = 0.50         # 45/90 absolute, above the 1/3 chance level
PER_OP_MARGIN = 0.10          # each operation must not regress; two must gain
PER_OP_REQUIRED_GAINS = 2
CONFIRM_MIN_CANDIDATES = 2    # at least 2 of 3 candidates must pass

# Uncertainty: 95% family-clustered bootstrap (3 cases per family) + exact
# McNemar on the discordant case pairs. Both are deterministic.
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20260921
CONFIDENCE = 0.95

# The preserved run-005 weights were never saved; only this digest survives.
PRESERVED_BASELINE_DIGEST = ("cb008721b92144b4e0ef52e86c2c449415935110747aca18ff"
                             "23229c05240e50")
BASELINE_UNAVAILABLE_REASON = (
    "run 005 persisted only the parameter digest "
    + PRESERVED_BASELINE_DIGEST
    + "; the weights themselves were never written to evidence, and "
      "RegisteredOperationBank is constructed without a seed, so the exact "
      "trained weights are not reproducible")
BASELINE_MODES = ("none", "reproduce")


def mean(values):
    return sum(values) / max(1, len(values))


def _loss_total(value):
    return value if isinstance(value, (int, float)) else value["total"]


def fit_criterion(before_loss, after_loss):
    margin = (mean([_loss_total(value) for value in before_loss.values()])
              - mean([_loss_total(value) for value in after_loss.values()]))
    return {"met": margin > FIT_MARGIN, "margin": margin, "threshold": FIT_MARGIN,
            "rule": "mean(after) < mean(before) - 0.02"}


def encoder_identity(torch, encoder):
    """Digest of the frozen projection actually in use (control: identical for
    every candidate)."""
    digest_value = sha256()
    for token_id in range(encoder["vocabulary_size"]):
        vector = encoder["embed"](token_id)
        digest_value.update(vector.detach().cpu().numpy().tobytes())
    return digest_value.hexdigest()


ANSWER_FIELDS = ("correct", "encoded_correct_index", "reference")


def sealed_input(task):
    """Answer-free view of a task for the sealed prediction pass.

    Stronger than the training-time helper: it removes the private target AND
    the private correct index AND the checker derivation, so a prediction cannot
    read the answer even by accident.
    """
    return {key: value for key, value in task.items() if key not in ANSWER_FIELDS}


def evaluate_panel(learner, cases, *, arm=FROZEN_ARM):
    """Predict the fresh panel with the answers SEALED.

    Pass 1 records every prediction using an answer-free task view; only pass 2
    compares those recorded predictions with the answers. The learner never
    sees an answer field, and no evaluation feedback reaches it.
    """
    from . import adapter
    tasks = []
    for family_id, record in cases:
        task = adapter.public_records(record, arm)
        require(not (set(sealed_input(task)) & set(ANSWER_FIELDS)),
                "FRESH_PANEL_ANSWER_EXPOSED")
        tasks.append((family_id, task))
    sealed = [{"family_id": family_id, "record_id": task["record_id"],
               "op": task["op"],
               "predicted": learner.predict(sealed_input(task))}
              for family_id, task in tasks]
    results = []
    for (family_id, task), prediction in zip(tasks, sealed):
        results.append({**prediction,
                        "correct": prediction["predicted"] == task["correct"]})
    return {"sealed_predictions": sealed, "results": results,
            "attempted": len(results),
            "correct": sum(1 for row in results if row["correct"]),
            "accuracy": (sum(1 for row in results if row["correct"]) / len(results)
                         if results else 0.0),
            "per_op": {op: {"attempted": sum(1 for row in results if row["op"] == op),
                            "correct": sum(1 for row in results if row["op"] == op
                                           and row["correct"])}
                       for op in sorted({row["op"] for row in results})},
            "sealed_before_answers": True,
            "panel_digest": digest(canonical([row["record_id"] for row in results]))}


def practice_accuracy(learner, tasks):
    """Familiar-example accuracy. The prediction uses the same answer-free view
    as the sealed fresh panel (the real learner ignores answer fields either
    way, so this matches competence run 005's familiar measurement while never
    handing the answer to the model)."""
    attempted = correct = 0
    rows = []
    for task in tasks:
        predicted = learner.predict(sealed_input(task))
        expected = task["encoded_options"][task["encoded_correct_index"]]
        attempted += 1
        correct += int(predicted == expected)
        rows.append({"record_id": task["record_id"], "op": task["op"],
                     "correct": predicted == expected})
    return {"attempted": attempted, "correct": correct,
            "accuracy": (correct / attempted if attempted else 0.0),
            "per_op": {op: {"attempted": sum(1 for row in rows if row["op"] == op),
                            "correct": sum(1 for row in rows if row["op"] == op
                                           and row["correct"])}
                       for op in sorted({row["op"] for row in rows})},
            "predictions": rows}


def _binomial_tail(k, n):
    """P(X >= k) for X ~ Binomial(n, 0.5), exact."""
    require(0 <= k <= n, "BINOMIAL_RANGE")
    return sum(math.comb(n, index) for index in range(k, n + 1)) / (2 ** n)


def mcnemar(before_flags, after_flags):
    """Exact McNemar test on the discordant pairs of the SAME cases."""
    require(len(before_flags) == len(after_flags), "MCNEMAR_LENGTH")
    after_only = sum(1 for before, after in zip(before_flags, after_flags)
                     if not before and after)
    before_only = sum(1 for before, after in zip(before_flags, after_flags)
                      if before and not after)
    n = after_only + before_only
    if n == 0:
        p_value = 1.0
    else:
        p_value = min(1.0, 2 * _binomial_tail(max(after_only, before_only), n))
    return {"improved_only": after_only, "regressed_only": before_only,
            "discordant": n, "p_value": p_value, "rule": "exact binomial, two-sided"}


def _percentile(sorted_values, fraction):
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1,
                max(0, int(round(fraction * (len(sorted_values) - 1)))))
    return sorted_values[index]


def clustered_bootstrap(before_flags, after_flags, family_ids,
                        resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED,
                        confidence=CONFIDENCE):
    """95% interval for the paired accuracy change, resampling FAMILIES.

    The 90 cases are not independent: three questions share one family. The
    interval therefore resamples the 30 families with replacement (carrying all
    of a family's cases) and reports the percentile interval of the accuracy
    delta. Deterministic: fixed seed, fixed resample count.
    """
    require(len(before_flags) == len(after_flags) == len(family_ids),
            "BOOTSTRAP_LENGTH")
    grouped = {}
    for before, after, family_id in zip(before_flags, after_flags, family_ids):
        grouped.setdefault(family_id, []).append((before, after))
    families = sorted(grouped)
    rng = random.Random(seed)
    deltas = []
    for _ in range(resamples):
        before_hits = after_hits = total = 0
        for _ in range(len(families)):
            picked = families[rng.randrange(len(families))]
            for before, after in grouped[picked]:
                before_hits += int(before)
                after_hits += int(after)
                total += 1
        if total:
            deltas.append((after_hits - before_hits) / total)
    deltas.sort()
    tail = (1.0 - confidence) / 2.0
    return {"method": "family-clustered percentile bootstrap",
            "resamples": resamples, "seed": seed, "confidence": confidence,
            "clusters": len(families), "cases_per_cluster": sorted(
                {len(rows) for rows in grouped.values()}),
            "low": _percentile(deltas, tail), "high": _percentile(deltas, 1 - tail),
            "median": _percentile(deltas, 0.5)}


def paired_analysis(before, after):
    """Paired fresh-panel analysis for one candidate (or the baseline row)."""
    before_rows = before["results"]
    after_rows = after["results"]
    require([row["record_id"] for row in before_rows]
            == [row["record_id"] for row in after_rows], "PAIRED_PANEL_MISMATCH")
    before_flags = [row["correct"] for row in before_rows]
    after_flags = [row["correct"] for row in after_rows]
    family_ids = [row["family_id"] for row in before_rows]
    delta_cases = sum(after_flags) - sum(before_flags)
    attempted = len(before_flags)
    per_op = {}
    for op in sorted({row["op"] for row in before_rows}):
        indices = [index for index, row in enumerate(before_rows) if row["op"] == op]
        op_before = sum(1 for index in indices if before_flags[index])
        op_after = sum(1 for index in indices if after_flags[index])
        per_op[op] = {"attempted": len(indices),
                      "before_correct": op_before, "after_correct": op_after,
                      "delta_cases": op_after - op_before,
                      "delta_accuracy": (op_after - op_before) / len(indices)
                      if indices else 0.0}
    return {"attempted": attempted,
            "before_correct": sum(before_flags), "after_correct": sum(after_flags),
            "before_accuracy": before["accuracy"], "after_accuracy": after["accuracy"],
            "delta_cases": delta_cases,
            "delta_accuracy": delta_cases / attempted if attempted else 0.0,
            "per_op": per_op,
            "uncertainty": clustered_bootstrap(before_flags, after_flags, family_ids),
            "mcnemar": mcnemar(before_flags, after_flags)}


def transfer_verdict(paired):
    """The pre-registered per-candidate fresh-transfer rule."""
    ci = paired["uncertainty"]
    gains = sum(1 for stats in paired["per_op"].values()
                if stats["delta_accuracy"] >= PER_OP_MARGIN)
    no_regression = all(stats["delta_cases"] >= 0 for stats in paired["per_op"].values())
    conditions = {
        "paired_margin": {"required": TRANSFER_MARGIN,
                          "observed": paired["delta_accuracy"],
                          "met": paired["delta_accuracy"] >= TRANSFER_MARGIN},
        "interval_above_zero": {"low": ci["low"], "high": ci["high"],
                                "met": ci["low"] is not None and ci["low"] > 0.0},
        "absolute_level": {"required": TRANSFER_LEVEL,
                           "observed": paired["after_accuracy"],
                           "met": paired["after_accuracy"] >= TRANSFER_LEVEL},
        "per_operation": {"required_gains": PER_OP_REQUIRED_GAINS,
                          "gains": gains, "no_regression": no_regression,
                          "met": no_regression and gains >= PER_OP_REQUIRED_GAINS},
    }
    return {"schema": "cas-graph-training-graph6-transfer-verdict/1",
            "conditions": conditions,
            "passed": all(condition["met"] for condition in conditions.values())}


def confirmation_verdict(candidates):
    passed = [candidate for candidate in candidates
              if candidate["transfer"]["passed"]]
    return {"schema": VERDICT_SCHEMA,
            "candidates": len(candidates),
            "passed": len(passed),
            "required": CONFIRM_MIN_CANDIDATES,
            "passed_seeds": [candidate["learner_seed"] for candidate in passed],
            "outcome": ("FRESH_TRANSFER_CONFIRMED"
                        if len(passed) >= CONFIRM_MIN_CANDIDATES
                        else "FRESH_TRANSFER_NOT_CONFIRMED"),
            "rule": ("at least %d of %d independently initialized candidates "
                     "meet the pre-registered fresh-transfer rule"
                     % (CONFIRM_MIN_CANDIDATES, len(candidates)))}


def run_candidate(*, run_id, learner_seed, framework, torch, device, tasks, cases,
                  learner_factory, learning_rate=FROZEN_LEARNING_RATE,
                  max_optimizer_steps=FROZEN_MAX_OPTIMIZER_STEPS,
                  max_wall_seconds=FROZEN_MAX_WALL_SECONDS,
                  history_every=HISTORY_EVERY, encoder_identity_value=None,
                  trainer_module=None):
    """One independently initialized candidate: measure, train, measure.

    The caller builds the framework AFTER seeding the module initialization, so
    the three candidates start from different weights while sharing the frozen
    encoder.
    """
    from . import trainer as trainer_module_default
    trainer_module = trainer_module or trainer_module_default
    learner = learner_factory(framework.module, arm=FROZEN_ARM,
                              learning_rate=learning_rate)
    initial_identity = learner.checkpoint_identity()
    practice_before = practice_accuracy(learner, tasks)
    fresh_before = evaluate_panel(learner, cases)

    def scoped_learner_factory(model, arm=FROZEN_ARM, learning_rate=learning_rate):
        return learner_factory(model, arm=arm, learning_rate=learning_rate)

    training = trainer_module.launch(
        run_id=run_id + ".train", arm=FROZEN_ARM, seed=learner_seed,
        framework=framework, model=framework.module,
        learner_factory=scoped_learner_factory, learning_rate=learning_rate,
        max_optimizer_steps=max_optimizer_steps,
        max_wall_seconds=max_wall_seconds, history_every=history_every)
    # The trainer trains its own learner object over the SAME module; rebuild the
    # prediction learner over the trained module so the measured checkpoint and
    # the measured predictions cannot drift apart.
    trained = learner_factory(framework.module, arm=FROZEN_ARM,
                              learning_rate=learning_rate)
    practice_after = practice_accuracy(trained, tasks)
    fresh_after = evaluate_panel(trained, cases)
    paired = paired_analysis(fresh_before, fresh_after)
    return {"schema": CANDIDATE_SCHEMA, "run_id": run_id,
            "learner_seed": learner_seed, "arm": FROZEN_ARM,
            "encoder_seed": FROZEN_ENCODER_SEED,
            "encoder_identity": encoder_identity_value,
            "initial_checkpoint_identity": initial_identity,
            "trained_checkpoint_identity": trained.checkpoint_identity(),
            "practice": {"before": practice_before, "after": practice_after,
                         "delta_cases": (practice_after["correct"]
                                         - practice_before["correct"])},
            "fresh": {"before": fresh_before, "after": fresh_after},
            "paired": paired,
            "fit_criterion": fit_criterion(training["training"]["before_loss"],
                                           training["training"]["after_loss"]),
            "training": training,
            "transfer": transfer_verdict(paired),
            "containment": training["containment"],
            "completed_updates": training["training"]["completed_updates"]}


def table_row(label, candidate, note=None):
    """One row of the owner's compact results table."""
    paired = candidate["paired"]
    per_op = " ".join("%s %d/%d→%d/%d" % (op, stats["before_correct"],
                                          stats["attempted"], stats["after_correct"],
                                          stats["attempted"])
                      for op, stats in sorted(paired["per_op"].items()))
    return {"candidate": label,
            "learner_seed": candidate["learner_seed"],
            "practice_before": candidate["practice"]["before"]["accuracy"],
            "practice_after": candidate["practice"]["after"]["accuracy"],
            "practice_before_correct": candidate["practice"]["before"]["correct"],
            "practice_after_correct": candidate["practice"]["after"]["correct"],
            "fresh_before_accuracy": paired["before_accuracy"],
            "fresh_after_accuracy": paired["after_accuracy"],
            "fresh_before_correct": paired["before_correct"],
            "fresh_after_correct": paired["after_correct"],
            "fresh_delta_accuracy": paired["delta_accuracy"],
            "fresh_ci_low": paired["uncertainty"]["low"],
            "fresh_ci_high": paired["uncertainty"]["high"],
            "mcnemar_p": paired["mcnemar"]["p_value"],
            "fit_met": candidate["fit_criterion"]["met"],
            "fit_margin": candidate["fit_criterion"]["margin"],
            "transfer_passed": candidate["transfer"]["passed"],
            "per_operation": per_op,
            "note": note}


def baseline_row(mode):
    """The preserved-checkpoint row: either unavailable (with the reason) or a
    declared reproduction attempt."""
    if mode == "none":
        return {"candidate": "preserved run-005 checkpoint",
                "status": "UNAVAILABLE", "reason": BASELINE_UNAVAILABLE_REASON,
                "preserved_digest": PRESERVED_BASELINE_DIGEST}
    require(mode in BASELINE_MODES, "BASELINE_MODE_UNKNOWN")
    return {"candidate": "run-005 reproduction attempt",
            "status": "PENDING_REPRODUCTION",
            "preserved_digest": PRESERVED_BASELINE_DIGEST,
            "note": ("declared reproduction candidate: same frozen configuration "
                     "with a recorded initialization seed; reported as "
                     "BASELINE_REPRODUCED only if the trained checkpoint digest "
                     "equals the preserved digest, otherwise BASELINE_NOT_REPRODUCED")}


def launch(*, run_id, torch, device, encoder, records, panel, learner_seeds=LEARNER_SEEDS,
           baseline_mode="none", learning_rate=FROZEN_LEARNING_RATE,
           max_optimizer_steps=FROZEN_MAX_OPTIMIZER_STEPS,
           max_wall_seconds=FROZEN_MAX_WALL_SECONDS, history_every=HISTORY_EVERY,
           framework_factory=None, learner_factory=None, trainer_module=None,
           encoder_identity_fn=None):
    """Run the whole pre-registered confirmation in ONE call."""
    from . import adapter
    from .real_framework import GraphLearner, build_graph_training_framework
    require(baseline_mode in BASELINE_MODES, "BASELINE_MODE_UNKNOWN")
    require(list(learner_seeds) == list(LEARNER_SEEDS),
            "LEARNER_SEEDS_FROZEN")
    require(panel["schema"] == "cas-graph-training-fresh-panel/1",
            "FRESH_PANEL_REQUIRED")
    identity_fn = encoder_identity_fn or encoder_identity
    encoder_identity_value = identity_fn(torch, encoder)
    framework_factory = framework_factory or (
        lambda seed: build_graph_training_framework(torch, device,
                                                    seed=FROZEN_ENCODER_SEED,
                                                    encoder=encoder))
    tasks = [adapter.public_records(record, FROZEN_ARM) for record in records]
    cases = [(case["family_id"], case["record"]) for case in panel["cases"]]

    def real_learner_factory(framework):
        return lambda model, arm=FROZEN_ARM, learning_rate=learning_rate: GraphLearner(
            torch, framework, tasks, device, learning_rate)

    candidates = []
    for learner_seed in learner_seeds:
        # The frozen encoder projection is built ONCE above and shared; seeding
        # the global RNG here changes ONLY the module/optimizer initialization
        # of this candidate (RegisteredOperationBank draws its Linear layers
        # from the ambient RNG and takes no seed).
        torch.manual_seed(learner_seed)
        framework = framework_factory(learner_seed)
        factory = learner_factory or real_learner_factory(framework)
        candidates.append(run_candidate(
            run_id="%s.seed%d" % (run_id, learner_seed), learner_seed=learner_seed,
            framework=framework, torch=torch, device=device, tasks=tasks,
            cases=cases, learner_factory=factory, learning_rate=learning_rate,
            max_optimizer_steps=max_optimizer_steps,
            max_wall_seconds=max_wall_seconds, history_every=history_every,
            encoder_identity_value=encoder_identity_value,
            trainer_module=trainer_module))

    baseline = baseline_row(baseline_mode)
    if baseline_mode == "reproduce":
        reproduction_seed = FROZEN_ENCODER_SEED
        torch.manual_seed(reproduction_seed)
        framework = framework_factory(reproduction_seed)
        factory = learner_factory or real_learner_factory(framework)
        reproduction = run_candidate(
            run_id="%s.reproduction" % run_id, learner_seed=reproduction_seed,
            framework=framework, torch=torch, device=device, tasks=tasks,
            cases=cases, learner_factory=factory, learning_rate=learning_rate,
            max_optimizer_steps=max_optimizer_steps,
            max_wall_seconds=max_wall_seconds, history_every=history_every,
            encoder_identity_value=encoder_identity_value,
            trainer_module=trainer_module)
        reproduced = (reproduction["trained_checkpoint_identity"]
                      == PRESERVED_BASELINE_DIGEST)
        baseline = {**baseline,
                    "status": "BASELINE_REPRODUCED" if reproduced
                              else "BASELINE_NOT_REPRODUCED",
                    "reproduction_seed": reproduction_seed,
                    "trained_checkpoint_identity":
                        reproduction["trained_checkpoint_identity"],
                    "table": table_row("run-005 reproduction attempt", reproduction)}

    identities = {candidate["encoder_identity"] for candidate in candidates}
    initial = [candidate["initial_checkpoint_identity"] for candidate in candidates]
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "panel": {"schema": panel["schema"], "panel_seed": panel["panel_seed"],
                  "family_count": panel["family_count"],
                  "case_count": panel["case_count"],
                  "cases_per_op": panel["cases_per_op"],
                  "reach_label_counts": panel["reach_label_counts"],
                  "distinct_family_patterns": panel["distinct_family_patterns"],
                  "distinct_case_patterns": panel["distinct_case_patterns"],
                  "excluded_case_ids": panel["excluded_case_ids"],
                  "excluded_signatures": panel["excluded_signatures"]},
        "budget": {"candidates": len(candidates),
                   "optimizer_steps_per_candidate": max_optimizer_steps,
                   "total_optimizer_steps": sum(
                       candidate["completed_updates"] for candidate in candidates),
                   "declared_total_optimizer_steps": TOTAL_OPTIMIZER_STEPS,
                   "max_wall_seconds_per_candidate": max_wall_seconds,
                   "declared_total_wall_seconds": max_wall_seconds * CANDIDATE_COUNT,
                   "learning_rate": learning_rate,
                   "arm": FROZEN_ARM},
        "controls": {"encoder_identity_shared": len(identities) == 1,
                     "encoder_identity": sorted(identities)[0] if identities else None,
                     "initial_checkpoints_distinct": len(set(initial)) == len(initial),
                     "initial_checkpoint_identities": initial},
        "candidates": candidates,
        "table": [table_row("seed %d" % candidate["learner_seed"], candidate)
                  for candidate in candidates],
        "baseline": baseline,
        "verdict": confirmation_verdict(candidates),
        "criterion": {"fit": {"margin": FIT_MARGIN,
                              "rule": "mean(after) < mean(before) - 0.02"},
                      "transfer": {"paired_margin": TRANSFER_MARGIN,
                                   "absolute_level": TRANSFER_LEVEL,
                                   "per_op_margin": PER_OP_MARGIN,
                                   "per_op_required_gains": PER_OP_REQUIRED_GAINS,
                                   "interval": "family-clustered 95% bootstrap",
                                   "test": "exact McNemar on discordant cases",
                                   "min_candidates": CONFIRM_MIN_CANDIDATES}},
        "claims": {"specialist_claimed": False, "composition_claimed": False,
                   "two_arm_comparison_claimed": False,
                   "sealed_splits_read": False,
                   "answers_sealed_before_predictions": True},
    }
