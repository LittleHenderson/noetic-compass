"""Q4-SDG-1 error panel: where does the ORIGINAL Q4 checkpoint go wrong? NEURAL -- AWS T4 only, never this laptop.

Answers directive section 3, questions 3, 4, 5 (refined) and 6, on the original checkpoint
records/q4_authorized_20260922/run_001 (weights sha256 d54f5715...). Forward and backward passes only.
It creates NO optimizer and takes NO step. The weights on disk are never written.

  Stage 0  verify the checkpoint and reproduce the 16 saved dev predictions of run_001. Every decoding step keeps
           its chosen token, runner-up and logit margin (same grammar mask and tie-break as free decoding), so a
           near-tie flip can be told from a real fault. Any difference writes DEVICE_OR_SOURCE_MISMATCH.json with
           the rows, their traces and the first differing step, and STOPS.
  Q3       next-token accuracy with the correct previous tokens (gold prefix), per slot kind, plain argmax and
           grammar-masked argmax (lowest token id breaks ties, as in free decoding), next to free generation;
           includes the choice at each row's first wrong decision and after it.
  Q4       compiler-derived one-field edits (noetic, domain, drive, register) of every leaf of every input:
           the change in the encoder summary and in the probability of the correct field token, gold prefix fixed.
  Q5       summary swap with a partner of the same bare shape (so the same token length), plus a same-example
           re-encode control, at the gold prefix.
  Q6       gradient norms per module group from one backward pass of the original loss (no step), plus separate
           backward passes of the decision-position and field-position losses; weight change = final checkpoint
           minus a re-initialised model (seed 20260921, the same call order as q4_smoke_job.py), with a check of
           the re-initialisation against update 1 of updates.jsonl (loss, total and per-group gradient norms).
           If that check fails, every final-minus-initial number is WITHHELD (null) under status
           REINIT_NOT_REPRODUCED_ON_THIS_DEVICE; only the final weights' own norms are written.

PANELS. old_dev16: the first 16 visible Q3 G dev rows (the smoke's dev panel; development diagnostic only).
teaching16: the first 16 training rows the run actually consumed. public64: 2 unconsumed train rows per G-train
shape (32) plus 32 dev rows after the first 16, spread round-robin over the 9 dev shapes; seed PANEL_SEED; the
selection digest is recorded. None of these rows is a family-D trigger source.

CUSTODY. Targets are recompiled from the VISIBLE text with the pinned compiler; no sealed file is read. The job
refuses to start if its Q3 data folder holds any *_eval.jsonl or sealed* file. Fails closed without CUDA
(GPU_REQUIRED), with a busy GPU, or with a torch/Python runtime other than the pinned one. One process, one try.

Run (AWS):  python -B q4_error_panel.py run --run-dir <run_001> --data-dir data/q3_v0_7 --out <new dir>
Check (no torch, fine locally):  python -B q4_error_panel.py select --run-dir <run_001> --data-dir data/q3_v0_7
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import sys
import time

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import q3_behaviour_records as q3  # noqa: E402
import q4_sdg_curriculum as sdg  # noqa: E402
from learner_q4_decoder import TOKENS, allowed_next, ast_to_tokens, free_decode  # noqa: E402

SCHEMA = "helm-cas-expression-lab.q4-sdg-error-panel/0.1"
EXPERIMENT = "Q4-SDG-1"
LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"
PLAN_SHA = "9dacc83627422d704c9db58f5ddbac82936e7d52211ec061247419fbad78095c"
WEIGHTS_SHA = "d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477"
INIT_SEED = 20260921            # the original run's seed: re-initialisation and the consumed-row order
PANEL_SEED = 20260971           # new: selection of the public panel
OLD_DEV_ROWS = 16
TEACHING_ROWS = 16
PUBLIC_TRAIN_PER_SHAPE = 2
PUBLIC_DEV_ROWS = 32
MODULE_GROUPS = ("input_embedding", "encoder", "output_embedding", "decoder", "output_head")
FIELD_SLOTS = ("noetic", "domain", "drive", "register")
EXPECTED_TORCH = "2.11.0+cu128"
EXPECTED_PYTHON = (3, 14)
REINIT_RELATIVE_TOLERANCE = 1e-4
DEFAULT_MAX_WALL_SECONDS = 2400     # 40 minutes; the machine timer is 45 minutes
_FORBIDDEN_NAME = re.compile(r"(_eval\.jsonl$|sealed)", re.IGNORECASE)
RESULT_LIMITS = (
    "Diagnostic of ONE saved checkpoint; not a capability claim",
    "This panel inspects 48 Q3 G-dev rows in total, not 16: old_dev16 (dev rows 0-15, inspected many times) plus "
    "the 32 G-dev rows in public64. All 48 are now inspected development rows; any later G-dev panel must flag "
    "them and report results with and without them",
    "No row of this panel may be used as a family-D trigger",
)


class PanelError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(body):
    return hashlib.sha256(body).hexdigest()


def guarded_read(path):
    """Every file this module opens itself goes through here. Eval and sealed names are refused."""
    path = Path(path)
    if _FORBIDDEN_NAME.search(path.name):
        raise PanelError("CUSTODY_REFUSED: %s" % path.name)
    return path.read_bytes()


def read_json(path):
    from q3_load import strict_loads
    return strict_loads(guarded_read(path).decode("utf-8"), Path(path).name)


def read_jsonl(path):
    from q3_load import strict_loads
    return [strict_loads(line, Path(path).name) for line in guarded_read(path).decode("utf-8").splitlines() if line.strip()]


def write_once(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def check_data_custody(data_dir):
    """The job's Q3 folder may hold the manifest and visible files; never an eval or sealed file (names only)."""
    present = sorted(p.name for p in Path(data_dir).iterdir() if _FORBIDDEN_NAME.search(p.name))
    if present:
        raise PanelError("CUSTODY_REFUSED: eval or sealed files present in the job's data folder: %s" % present)


def source_hashes():
    from q4_checkpoint import runtime_source_pins
    extra = ("q4_error_panel.py", "q4_sdg_curriculum.py", "q4_panel_evaluation.py", "historical_compiler.py",
             "pinned_sources/compiler_pre_ohm_61ed5a45.py", "Q3_DATA_PINS.json", "q4_smoke_job.py")
    return {"runtime_source_pins": runtime_source_pins(),
            "other_lf_sha256": {name: sdg.lf_sha256(HERE / name) for name in extra}}


# ------------------------------------------------------------------------------------------------------------
# Records of the original run (no torch)
# ------------------------------------------------------------------------------------------------------------
def read_run(run_dir):
    run = Path(run_dir)
    plan = read_json(run / "plan.json")
    if sha(canonical(plan)) != PLAN_SHA:
        raise PanelError("HISTORICAL_PLAN_MISMATCH")
    result = read_json(run / "result.json")
    updates = read_jsonl(run / "updates.jsonl")
    predictions = read_jsonl(run / "dev_predictions.jsonl")
    if (result.get("checkpoint_weights_sha256") != WEIGHTS_SHA or result.get("actual_updates") != 128
            or [u.get("update") for u in updates] != list(range(1, 129)) or len(predictions) != OLD_DEV_ROWS
            or plan["seed"] != INIT_SEED or plan["width"] != 64 or plan["train_examples"] != 2048):
        raise PanelError("HISTORICAL_RUN_RECORDS_INCONSISTENT")
    weights = guarded_read(run / "checkpoint" / "model_state.pt")
    if sha(weights) != WEIGHTS_SHA:
        raise PanelError("CHECKPOINT_WEIGHTS_MISMATCH")
    identity = {"source_pins": plan["source_pins"], "data_version": plan["data_version"],
                "manifest_sha256": plan["manifest_sha256"], "contract_digest": plan["contract_digest"],
                "environment": plan["environment"], "plan_sha256": PLAN_SHA, "authorization": result["authorization"]}
    return {"dir": run, "plan": plan, "result": result, "updates": updates, "predictions": predictions,
            "identity": identity}


def visible_rows(data_dir, plan):
    """Visible Q3 v0.7 G train and dev rows: pinned manifest, hashed visible files. Nothing else is opened."""
    import q3_load
    check_data_custody(data_dir)
    q3_load.check_pins(data_dir)
    if q3_load.manifest_sha(data_dir) != plan["manifest_sha256"]:
        raise PanelError("DATA_IDENTITY_MISMATCH")
    return q3_load.load_visible(data_dir, "G", "train"), q3_load.load_visible(data_dir, "G", "dev")


def consumed_positions(count):
    """The run's single-example order: random.Random(seed).shuffle(range(2048)); 128 updates consumed order[:128]."""
    from q4_panel_evaluation import consumed_indices
    return consumed_indices(count, INIT_SEED, 128)


def compiled_row(visible, compiler, panel, origin):
    """Target recompiled from the VISIBLE text with the pinned compiler (the Q3 G oracle); the sealed file is unread."""
    artifact = compiler.compile_expression(visible["observation"]).to_dict()
    if not artifact["valid"] or artifact["ast"] is None:
        raise PanelError("VISIBLE_ROW_DOES_NOT_COMPILE: %s" % visible["record_id"])
    target = q3.to_lab_spelling(artifact["ast"])
    tokens = ast_to_tokens(target)
    slots = sdg.token_slots(tokens)
    info = sdg.describe(target)
    return {"panel": panel, "record_id": visible["record_id"], "observation": visible["observation"],
            "origin": origin, "target_ast": target, "target_tokens": list(tokens),
            "slot_kinds": [s["slot"] for s in slots], "slot_paths": [s["path"] for s in slots],
            "target_source": "RECOMPILED_FROM_VISIBLE_TEXT_PINNED_COMPILER_SEALED_FILE_NOT_READ",
            **{k: info[k] for k in ("content_sha256", "q3_tree_shape_key", "ordered_operator_shape_sha256",
                                    "depth", "leaf_count", "shape_text")}}


def select_panels(train, dev, compiler):
    """Declared, seeded selection. Returns (rows, selection record)."""
    consumed = consumed_positions(len(train))
    consumed_set = set(consumed)
    rows = [compiled_row(dev[i], compiler, "old_dev16", {"split": "dev", "index": i}) for i in range(OLD_DEV_ROWS)]
    rows += [compiled_row(train[i], compiler, "teaching16", {"split": "train", "index": i, "update": k + 1})
             for k, i in enumerate(consumed[:TEACHING_ROWS])]

    def key_of(row):
        artifact = compiler.compile_expression(row["observation"]).to_dict()
        return sdg.bare_key16(q3.tree_shape(q3.to_lab_spelling(artifact["ast"])))
    train_keys = [key_of(r) for r in train]
    dev_keys = [key_of(r) for r in dev]
    if set(train_keys) != set(sdg.G_TRAIN_SHAPES) or set(dev_keys) != set(sdg.G_DEV_SHAPES):
        raise PanelError("SHAPE_KEYS_DIFFER_FROM_THE_FROZEN_16_AND_9")
    rng = random.Random(PANEL_SEED)
    public = []
    for key in sorted(sdg.G_TRAIN_SHAPES):
        pool = [i for i, k in enumerate(train_keys) if k == key and i not in consumed_set]
        rng.shuffle(pool)
        public += [("train", i) for i in pool[:PUBLIC_TRAIN_PER_SHAPE]]
    strata = {}
    for key in sorted(sdg.G_DEV_SHAPES):
        pool = [i for i, k in enumerate(dev_keys) if k == key and i >= OLD_DEV_ROWS]
        rng.shuffle(pool)
        strata[key] = pool
    taken = 0
    while taken < PUBLIC_DEV_ROWS and any(strata.values()):
        for key in sorted(strata):
            if strata[key] and taken < PUBLIC_DEV_ROWS:
                public.append(("dev", strata[key].pop(0)))
                taken += 1
    for split, i in public:
        source = train if split == "train" else dev
        rows.append(compiled_row(source[i], compiler, "public64", {"split": split, "index": i,
                                                                    "consumed_in_training": i in consumed_set if split == "train" else False}))
    ids = [r["record_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise PanelError("PANEL_ROWS_OVERLAP")
    selection = {"panel_seed": PANEL_SEED, "init_seed": INIT_SEED, "consumed_positions_first_16": consumed[:TEACHING_ROWS],
                 "rule": "old_dev16 = visible G dev rows 0-15; teaching16 = the first 16 consumed training rows in "
                         "update order; public64 = per G-train shape (sorted key) 2 unconsumed train rows, seeded "
                         "shuffle; then dev rows 16+ round-robin over the 9 dev shapes (sorted key) up to 32",
                 "counts": dict(sorted(collections.Counter(r["panel"] for r in rows).items())),
                 "digest": sha(canonical([[r["panel"], r["record_id"], r["content_sha256"]] for r in rows]))}
    return rows, selection


# ------------------------------------------------------------------------------------------------------------
# Compiler-derived one-field edits and matched partners (no torch)
# ------------------------------------------------------------------------------------------------------------
def one_field_edits(row, compiler):
    """For every leaf and field: the next value (cyclic) that compiles to exactly the edited tree."""
    target = row["target_ast"]
    if sdg.render_ast(target) != row["observation"]:
        return [], "SURFACE_NOT_CANONICAL"
    edits = []
    for path in sdg.leaf_paths(target):
        leaf = sdg.get_at(target, path)
        cell = sdg.leaf_cell(leaf)
        for index, field in enumerate(FIELD_SLOTS):
            values = sdg.VALUES[field]
            start, refused = values.index(cell[index]), []
            for step in range(1, len(values)):
                value = values[(start + step) % len(values)]
                edited = sdg.replace_at(target, path, sdg._with_field(leaf, field, value))
                try:
                    checked = sdg.compile_intended(edited, compiler)
                except sdg.Refusal as refusal:
                    refused.append([str(value), refusal.code])
                    continue
                diff = sdg.differing_positions(row["target_tokens"], checked["target_tokens"])
                if diff is None or len(diff) != 1 or row["slot_kinds"][diff[0]] != field:
                    raise PanelError("EDIT_NOT_ONE_FIELD: %s" % checked["observation"])
                edits.append({"path": path, "field": field, "from": str(cell[index]), "to": str(value),
                              "position": diff[0], "observation": checked["observation"],
                              "old_token": TOKENS[row["target_tokens"][diff[0]]],
                              "new_token": TOKENS[checked["target_tokens"][diff[0]]], "refused_before": refused})
                break
            else:
                edits.append({"path": path, "field": field, "from": str(cell[index]), "to": None,
                              "refused_before": refused, "status": "NO_COMPILABLE_EDIT"})
    return edits, None


def matched_partners(rows):
    """Partner = the next row (cyclic, by panel then record id) with the same bare shape and different content.

Same bare shape means the same number of leaves, so the same target token length (7 x leaves - 1).
"""
    by_shape = collections.defaultdict(list)
    for row in sorted(rows, key=lambda r: (r["panel"], r["record_id"])):
        by_shape[row["q3_tree_shape_key"]].append(row)
    partners = {}
    for members in by_shape.values():
        for index, row in enumerate(members):
            for step in range(1, len(members)):
                other = members[(index + step) % len(members)]
                if other["content_sha256"] != row["content_sha256"]:
                    if len(other["target_tokens"]) != len(row["target_tokens"]):
                        raise PanelError("PARTNER_LENGTH_MISMATCH")
                    partners[row["record_id"]] = other["record_id"]
                    break
    return partners


# ------------------------------------------------------------------------------------------------------------
# Small numeric helpers (Python floats; float64)
# ------------------------------------------------------------------------------------------------------------
def softmax(logits, allowed=None):
    ids = range(len(logits)) if allowed is None else allowed
    peak = max(logits[i] for i in ids)
    weights = {i: math.exp(logits[i] - peak) for i in ids}
    total = sum(weights.values())
    return {i: w / total for i, w in weights.items()}


def choose(logits, allowed=None):
    """Highest logit; the LOWEST token id breaks ties -- exactly free_decode's rule."""
    ids = range(len(logits)) if allowed is None else allowed
    return min(ids, key=lambda token: (-logits[token], token))


def summary_change(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return {"l2": math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))), "max_abs": max(abs(x - y) for x, y in zip(a, b)),
            "cosine": dot / (na * nb) if na and nb else None}


def describe_values(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return {"n": 0}
    mid = len(values) // 2
    median = values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2
    return {"n": len(values), "mean": sum(values) / len(values), "median": median, "min": values[0], "max": values[-1]}


# ------------------------------------------------------------------------------------------------------------
# Neural stages (called only inside run(), after the CUDA and custody gates)
# ------------------------------------------------------------------------------------------------------------
def decision_margins(calls, tokens):
    """Per free-decoding step: chosen token, runner-up and margin (top minus second logit).

`calls` are the (prefix, logits) pairs free_decode requested, in order; `tokens` are the tokens it chose. The
ranking uses the same grammar mask (allowed_next) and tie-break (highest logit, then lowest id) as free_decode.
A step with one allowed token has no runner-up (margin None). A small margin marks a decode that a tiny numeric
difference between GPUs could flip.
"""
    trace = []
    for i, ((prefix, logits), token) in enumerate(zip(calls, tokens)):
        allowed = allowed_next(tuple(prefix))
        finite = all(math.isfinite(x) for x in logits)
        ranked = sorted(allowed, key=lambda t: (-logits[t], t)) if finite else list(allowed)
        runner = ranked[1] if finite and len(ranked) > 1 else None
        trace.append({"i": i, "slot": sdg.slot_kind(tuple(prefix)), "chosen": TOKENS[token],
                      "chosen_is_top_ranked": finite and ranked[0] == token,
                      "runner_up": None if runner is None else TOKENS[runner],
                      "margin": None if runner is None else logits[ranked[0]] - logits[runner],
                      "allowed_count": len(allowed), "logits_finite": finite})
    return trace


def traced_generate(model, observation):
    """model.generate's exact path -- free_decode(model.encode(x), model.next_logits) -- with every logit call kept."""
    calls = []

    def recording(bottleneck, prefix):
        logits = model.next_logits(bottleneck, prefix)
        calls.append((tuple(prefix), logits))
        return logits
    result = free_decode(model.encode(observation), recording)
    return result, decision_margins(calls, result.tokens)


def _margin_summary(trace):
    margins = [(step["margin"], step["i"]) for step in trace if step["margin"] is not None]
    if not margins:
        return {"min_margin": None, "min_margin_position": None}
    low = min(margins)
    return {"min_margin": low[0], "min_margin_position": low[1]}


def first_token_difference(saved_ast, now_tokens, trace):
    """Where a saved decode and a replayed decode first differ, and the replay's margin at that step."""
    if saved_ast is None:
        return {"index": None, "note": "the saved decode has no tree"}
    saved_tokens = ast_to_tokens(saved_ast)
    for i, (a, b) in enumerate(zip(saved_tokens, now_tokens)):
        if a != b:
            step = trace[i] if i < len(trace) else {}
            return {"index": i, "saved_token": TOKENS[a], "now_token": TOKENS[b], "slot": step.get("slot"),
                    "now_runner_up": step.get("runner_up"), "now_margin_at_index": step.get("margin")}
    if len(saved_tokens) != len(now_tokens):
        return {"index": min(len(saved_tokens), len(now_tokens)), "note": "one decode is a prefix of the other"}
    return {"index": None, "note": "same tokens; the difference is outside the token stream (outcome or steps)"}


def stage0(model, run, dev):
    """Replay the 16 saved dev decodes. Compare the four saved keys; keep the full decision trace either way."""
    from learner_q4_representation import from_visible_record
    mismatches, reproduced = [], []
    for saved, visible in zip(run["predictions"], dev[:OLD_DEV_ROWS]):
        generated, trace = traced_generate(model, from_visible_record(visible))
        now = {"record_id": visible["record_id"], "outcome": generated.outcome, "ast": generated.ast,
               "steps": generated.steps}
        reproduced.append(dict(now, decision_trace=trace, **_margin_summary(trace)))
        if canonical(now) != canonical(saved):
            mismatches.append({"saved": saved, "now": now, "decision_trace": trace, **_margin_summary(trace),
                               "first_difference": first_token_difference(saved.get("ast"), generated.tokens, trace)})
    return reproduced, mismatches


def teacher_logits(model, row):
    """The full-sequence teacher-forced pass (the training path), without gradients, as Python floats."""
    import torch
    from learner_q4_representation import encode_observation
    with torch.no_grad():
        teacher = model.teacher_forced_logits(encode_observation(row["observation"]), tuple(row["target_tokens"][:-1]))
        values = [[float(x) for x in position] for position in teacher.detach().cpu().tolist()]
    model.eval()
    return values


def q3_trace(model, row, bottleneck, check_deadline):
    target = row["target_tokens"]
    steps, stepwise = [], []
    for i in range(len(target)):
        check_deadline()
        prefix = tuple(target[:i])
        logits = model.next_logits(bottleneck, prefix)
        stepwise.append(logits)
        allowed = allowed_next(prefix)
        probs, masked = softmax(logits), softmax(logits, allowed)
        gold = target[i]
        steps.append({"i": i, "slot": row["slot_kinds"][i], "path": row["slot_paths"][i], "gold": TOKENS[gold],
                      "plain": TOKENS[choose(logits)], "masked": TOKENS[choose(logits, allowed)],
                      "p_gold": probs[gold], "p_gold_masked": masked[gold],
                      "masked_rank_of_gold": sorted(allowed, key=lambda t: (-logits[t], t)).index(gold) + 1})
    teacher = teacher_logits(model, row)
    if len(teacher) != len(stepwise):
        raise PanelError("TEACHER_FORCED_LENGTH_MISMATCH")
    gap = max(abs(a - b) for s, t in zip(stepwise, teacher) for a, b in zip(s, t))
    agree = sum(choose(s, allowed_next(tuple(target[:i]))) == choose(t, allowed_next(tuple(target[:i])))
                for i, (s, t) in enumerate(zip(stepwise, teacher)))
    return steps, stepwise, {"max_abs_logit_gap_stepwise_vs_full_sequence": gap,
                             "masked_choice_agreement": agree, "positions": len(target)}


def run_q3(model, rows, bottlenecks, check_deadline):
    per_row, stepwise_logits = [], {}
    for row in rows:
        bottleneck = bottlenecks[row["record_id"]]
        free = free_decode(bottleneck, model.next_logits)
        wrong = sdg.first_wrong_decision(free.tokens, row["target_tokens"])
        steps, stepwise, crosscheck = q3_trace(model, row, bottleneck, check_deadline)
        stepwise_logits[row["record_id"]] = stepwise
        at = wrong["index"] if wrong else None
        per_row.append({"panel": row["panel"], "record_id": row["record_id"], "shape": row["shape_text"],
                        "free_outcome": free.outcome, "free_exact": free.ast == row["target_ast"],
                        "free_tokens": [TOKENS[t] for t in free.tokens], "first_wrong_decision": wrong,
                        "gold_prefix_masked_choice_correct_at_first_wrong_decision":
                            None if at is None or at >= len(steps) else steps[at]["masked"] == steps[at]["gold"],
                        "gold_prefix_steps": steps, "crosscheck": crosscheck})
    summary = {}
    for panel in sorted({r["panel"] for r in per_row}) + ["all"]:
        chosen = [r for r in per_row if panel == "all" or r["panel"] == panel]
        by_slot = collections.defaultdict(lambda: {"n": 0, "plain_correct": 0, "masked_correct": 0,
                                                   "masked_correct_before_first_wrong": 0, "n_before": 0,
                                                   "masked_correct_after_first_wrong": 0, "n_after": 0})
        for r in chosen:
            first = r["first_wrong_decision"]["index"] if r["first_wrong_decision"] else None
            for s in r["gold_prefix_steps"]:
                cell = by_slot[s["slot"]]
                cell["n"] += 1
                cell["plain_correct"] += s["plain"] == s["gold"]
                cell["masked_correct"] += s["masked"] == s["gold"]
                if first is None or s["i"] < first:
                    cell["n_before"] += 1
                    cell["masked_correct_before_first_wrong"] += s["masked"] == s["gold"]
                elif s["i"] > first:
                    cell["n_after"] += 1
                    cell["masked_correct_after_first_wrong"] += s["masked"] == s["gold"]
        at_first = [r["gold_prefix_masked_choice_correct_at_first_wrong_decision"] for r in chosen
                    if r["gold_prefix_masked_choice_correct_at_first_wrong_decision"] is not None]
        summary[panel] = {"rows": len(chosen), "free_exact": sum(r["free_exact"] for r in chosen),
                          "free_generated": sum(r["free_outcome"] == "GENERATED" for r in chosen),
                          "distinct_free_outputs": len({json.dumps(r["free_tokens"]) for r in chosen}),
                          "first_wrong_decision_kinds": dict(sorted(collections.Counter(
                              r["first_wrong_decision"]["mistake"] if r["first_wrong_decision"] else "EXACT"
                              for r in chosen).items())),
                          "gold_prefix_accuracy_by_slot": {k: dict(v) for k, v in sorted(by_slot.items())},
                          "gold_prefix_masked_correct_at_first_wrong_decision": [sum(at_first), len(at_first)],
                          "note_at_first_wrong_decision": "free decoding and the gold prefix share the prefix up to "
                                                          "the first wrong decision, so this count is a consistency "
                                                          "check (expected 0 correct unless the two numeric paths differ)"}
    return {"per_row": per_row, "summary": summary}, stepwise_logits


def run_q4(model, rows, bottlenecks, compiler, check_deadline):
    from learner_q4_representation import encode_observation
    records, skipped = [], []
    for row in rows:
        edits, why = one_field_edits(row, compiler)
        if why:
            skipped.append({"record_id": row["record_id"], "reason": why})
            continue
        b0 = bottlenecks[row["record_id"]]
        for edit in edits:
            check_deadline()
            if edit.get("to") is None:
                records.append(dict(edit, panel=row["panel"], record_id=row["record_id"]))
                continue
            b1 = model.encode(encode_observation(edit["observation"]))
            prefix = tuple(row["target_tokens"][:edit["position"]])
            allowed = allowed_next(prefix)
            l0, l1 = model.next_logits(b0, prefix), model.next_logits(b1, prefix)
            p0, p1 = softmax(l0), softmax(l1)
            old, new = row["target_tokens"][edit["position"]], TOKENS.index(edit["new_token"])
            c0, c1 = choose(l0, allowed), choose(l1, allowed)
            records.append(dict(edit, panel=row["panel"], record_id=row["record_id"],
                                summary_change=summary_change(b0.values, b1.values),
                                p_old_token={"original_input": p0[old], "edited_input": p1[old]},
                                p_new_token={"original_input": p0[new], "edited_input": p1[new]},
                                masked_choice={"original_input": TOKENS[c0], "edited_input": TOKENS[c1]},
                                choice_follows_input=(c0 == old and c1 == new)))
    summary = {}
    for panel in sorted({r["panel"] for r in records}) + ["all"]:
        for field in FIELD_SLOTS:
            chosen = [r for r in records if (panel == "all" or r["panel"] == panel) and r["field"] == field
                      and r.get("to") is not None]
            summary["%s/%s" % (panel, field)] = {
                "edits": len(chosen),
                "no_compilable_edit": sum(1 for r in records if (panel == "all" or r["panel"] == panel)
                                          and r["field"] == field and r.get("to") is None),
                "summary_l2": describe_values([r["summary_change"]["l2"] for r in chosen]),
                "summary_cosine": describe_values([r["summary_change"]["cosine"] for r in chosen]),
                "delta_p_new_token": describe_values([r["p_new_token"]["edited_input"] - r["p_new_token"]["original_input"]
                                                      for r in chosen]),
                "delta_p_old_token": describe_values([r["p_old_token"]["edited_input"] - r["p_old_token"]["original_input"]
                                                      for r in chosen]),
                "masked_choice_changed": sum(r["masked_choice"]["original_input"] != r["masked_choice"]["edited_input"]
                                             for r in chosen),
                "masked_choice_follows_input": sum(r["choice_follows_input"] for r in chosen)}
    return {"edits": records, "skipped_rows": skipped, "summary": summary}


def run_q5(model, rows, bottlenecks, stepwise_logits, check_deadline):
    from learner_q4_representation import encode_observation
    partners = matched_partners(rows)
    by_id = {r["record_id"]: r for r in rows}
    per_row = []
    for row in rows:
        if row["record_id"] not in partners:
            per_row.append({"record_id": row["record_id"], "panel": row["panel"], "status": "NO_MATCHED_PARTNER"})
            continue
        partner = by_id[partners[row["record_id"]]]
        own, other = bottlenecks[row["record_id"]], bottlenecks[partner["record_id"]]
        again = model.encode(encode_observation(row["observation"]))       # same-example control
        target = row["target_tokens"]
        swap_abs, control_abs, own_logp, swap_logp, changed, by_slot = [], [], [], [], 0, collections.defaultdict(list)
        for i in range(len(target)):
            check_deadline()
            prefix = tuple(target[:i])
            allowed = allowed_next(prefix)
            l_own = stepwise_logits[row["record_id"]][i]
            l_swap, l_again = model.next_logits(other, prefix), model.next_logits(again, prefix)
            p_own, p_swap, p_again = softmax(l_own)[target[i]], softmax(l_swap)[target[i]], softmax(l_again)[target[i]]
            swap_abs.append(abs(p_own - p_swap))
            control_abs.append(abs(p_own - p_again))
            own_logp.append(math.log(max(p_own, 1e-300)))
            swap_logp.append(math.log(max(p_swap, 1e-300)))
            changed += choose(l_own, allowed) != choose(l_swap, allowed)
            by_slot[row["slot_kinds"][i]].append(abs(p_own - p_swap))
        per_row.append({"record_id": row["record_id"], "panel": row["panel"], "partner": partner["record_id"],
                        "partner_panel": partner["panel"], "shape": row["shape_text"],
                        "summary_distance_to_partner": summary_change(own.values, other.values),
                        "same_example_reencode_distance": summary_change(own.values, again.values),
                        "max_abs_delta_p_gold_swap": max(swap_abs), "max_abs_delta_p_gold_control": max(control_abs),
                        "mean_log_p_gold_own": sum(own_logp) / len(own_logp),
                        "mean_log_p_gold_swapped": sum(swap_logp) / len(swap_logp),
                        "masked_choices_changed_by_swap": changed, "positions": len(target),
                        "mean_abs_delta_p_gold_by_slot": {k: sum(v) / len(v) for k, v in sorted(by_slot.items())}})
    measured = [r for r in per_row if "partner" in r]
    summary = {"rows_with_partner": len(measured), "rows_without_partner": len(per_row) - len(measured),
               "max_abs_delta_p_gold_swap": describe_values([r["max_abs_delta_p_gold_swap"] for r in measured]),
               "max_abs_delta_p_gold_control": describe_values([r["max_abs_delta_p_gold_control"] for r in measured]),
               "masked_choices_changed_by_swap_total": sum(r["masked_choices_changed_by_swap"] for r in measured),
               "positions_total": sum(r["positions"] for r in measured),
               "summary_cosine_to_partner": describe_values([r["summary_distance_to_partner"]["cosine"] for r in measured])}
    return {"per_row": per_row, "summary": summary}


def _group_norms(model):
    squares = {group: 0.0 for group in MODULE_GROUPS}
    for name, parameter in model.named_parameters():
        group = name.split(".")[0]
        if group not in squares:
            raise PanelError("UNKNOWN_MODULE_GROUP: %s" % name)
        if parameter.grad is not None:
            squares[group] += float(parameter.grad.detach().double().pow(2).sum().item())
    norms = {group: math.sqrt(value) for group, value in squares.items()}
    norms["total"] = math.sqrt(sum(squares.values()))
    return norms


def _token_losses(model, row, device):
    import torch
    from learner_q4_representation import encode_observation
    target = row["target_tokens"]
    logits = model.teacher_forced_logits(encode_observation(row["observation"]), tuple(target[:-1]))
    gold = torch.tensor(target, dtype=torch.long, device=device)
    per_token = torch.nn.functional.cross_entropy(logits, gold, reduction="none")
    original = torch.nn.functional.cross_entropy(logits, gold)
    return per_token, original


def backward_norms(model, row, device, positions):
    """One fresh forward, one backward of the mean loss over `positions` (None = the original loss). No step."""
    import torch
    model.zero_grad(set_to_none=True)
    per_token, original = _token_losses(model, row, device)
    if positions is None:
        loss = original
        extra = {"equal_weight_mean_minus_original": float((per_token.mean() - original).item())}
    else:
        if not positions:
            return None
        # A 0/1 mask (elementwise multiply + sum) keeps the backward deterministic under
        # torch.use_deterministic_algorithms; index_select's CUDA backward may lack a deterministic kernel.
        chosen = set(positions)
        mask = torch.tensor([1.0 if i in chosen else 0.0 for i in range(per_token.shape[0])],
                            dtype=per_token.dtype, device=device)     # built from a Python list: no CUDA indexing op
        loss = (per_token * mask).sum() / mask.sum()
        extra = {"positions": len(positions)}
    loss.backward()
    norms = _group_norms(model)
    model.zero_grad(set_to_none=True)
    return dict(extra, loss=float(loss.item()), grad_norms=norms)


def run_q6(model, rows, train, device, run, compiler, check_deadline):
    import torch
    from learner_q4_neural import NeuralConfig, build_model
    per_row = []
    for row in rows:
        check_deadline()
        decision = [i for i, k in enumerate(row["slot_kinds"]) if k == "expr"]
        field = [i for i, k in enumerate(row["slot_kinds"]) if k in FIELD_SLOTS]
        op = [i for i, k in enumerate(row["slot_kinds"]) if k == "op"]
        per_row.append({"record_id": row["record_id"], "panel": row["panel"],
                        "original_loss": backward_norms(model, row, device, None),
                        "decision_positions_loss": backward_norms(model, row, device, decision),
                        "field_positions_loss": backward_norms(model, row, device, field),
                        "op_positions_loss": backward_norms(model, row, device, op)})
    summary = {}
    for panel in sorted({r["panel"] for r in per_row}) + ["all"]:
        chosen = [r for r in per_row if panel == "all" or r["panel"] == panel]
        for loss_name in ("original_loss", "decision_positions_loss", "field_positions_loss", "op_positions_loss"):
            summary["%s/%s" % (panel, loss_name)] = {
                group: describe_values([r[loss_name]["grad_norms"][group] for r in chosen if r[loss_name]])
                for group in MODULE_GROUPS + ("total",)}
    # Re-initialise exactly as q4_smoke_job._worker did: seed, then build_model (all tensors made on CUDA).
    torch.manual_seed(INIT_SEED)
    torch.cuda.manual_seed_all(INIT_SEED)
    initial = build_model(NeuralConfig(64), device=device)
    first = train[consumed_positions(len(train))[0]]
    first_row = compiled_row(first, compiler, "update_1", {"split": "train", "update": 1})
    check = update_1_check(backward_norms(initial, first_row, device, None), run["updates"][0], first["record_id"])
    final_state, init_state = model.state_dict(), initial.state_dict()
    if set(final_state) != set(init_state):
        raise PanelError("STATE_KEYS_DIFFER")
    sums = {}
    for name in sorted(final_state):
        final_t, init_t = final_state[name].detach().double(), init_state[name].detach().double()
        delta = final_t - init_t
        sums[name] = {"delta": float(delta.pow(2).sum().item()), "init": float(init_t.pow(2).sum().item()),
                      "final": float(final_t.pow(2).sum().item()), "max_abs_delta": float(delta.abs().max().item())}
    del initial
    return {"per_row": per_row, "summary": summary, "weight_change": weight_change_record(check, sums)}


def update_1_check(at_init, saved, record_id):
    """Compare the re-initialised model's update-1 loss and gradient with updates.jsonl line 1.

Update 1 is the one gradient the original run is known to have applied from the initial weights; its norm per
module group is written as well as the total.
"""
    loss_gap = abs(at_init["loss"] - saved["loss"])
    norm_gap = abs(at_init["grad_norms"]["total"] - saved["pre_clip_gradient_norm"])
    reproduced = (loss_gap <= REINIT_RELATIVE_TOLERANCE * max(1.0, abs(saved["loss"]))
                  and norm_gap <= REINIT_RELATIVE_TOLERANCE * max(1.0, abs(saved["pre_clip_gradient_norm"])))
    return {"reproduced": reproduced, "record_id": record_id, "tolerance_relative": REINIT_RELATIVE_TOLERANCE,
            "saved_loss": saved["loss"], "reinit_loss": at_init["loss"],
            "saved_pre_clip_gradient_norm": saved["pre_clip_gradient_norm"],
            "reinit_gradient_norm": at_init["grad_norms"]["total"],
            "reinit_gradient_norms_by_module_group": {g: at_init["grad_norms"][g] for g in MODULE_GROUPS + ("total",)},
            "equal_weight_mean_minus_original": at_init.get("equal_weight_mean_minus_original")}


def weight_change_record(check, sums):
    """Weight change = final minus initial, per tensor and per module group -- ONLY if the re-initialisation passed.

Chosen rule (review P2): when update 1 is NOT reproduced, the rebuilt model is not the run's starting point, so every
difference and every initial-weight number is WITHHELD (null). Only the final weights' own norms are written, under
a key that names them as final-only. The status says which case applies.
"""
    finals = {name: math.sqrt(v["final"]) for name, v in sums.items()}
    final_by_group = {g: math.sqrt(sum(v["final"] for n, v in sums.items() if n.split(".")[0] == g)) for g in MODULE_GROUPS}
    record = {"why_it_can_differ": "CUDA random initialisation can depend on the GPU model's kernel launch layout; "
                                   "the original ran on an RTX 4070 Laptop GPU",
              "update_1_check": check,
              "final_weight_l2_only": {"by_module_group": final_by_group, "by_tensor": finals}}
    if not check["reproduced"]:
        record.update(status="REINIT_NOT_REPRODUCED_ON_THIS_DEVICE", by_module_group=None, by_tensor=None,
                      withheld="final-minus-initial numbers are withheld: the rebuilt start does not match update 1")
        return record
    squares = {g: {"delta": 0.0, "init": 0.0, "final": 0.0, "max_abs_delta": 0.0} for g in MODULE_GROUPS}
    by_tensor = {}
    for name, v in sums.items():
        by_tensor[name] = {"l2_delta": math.sqrt(v["delta"]), "l2_init": math.sqrt(v["init"]),
                           "l2_final": math.sqrt(v["final"]), "max_abs_delta": v["max_abs_delta"]}
        group = squares[name.split(".")[0]]
        for key in ("delta", "init", "final"):
            group[key] += v[key]
        group["max_abs_delta"] = max(group["max_abs_delta"], v["max_abs_delta"])
    by_group = {g: {"l2_delta": math.sqrt(v["delta"]), "l2_init": math.sqrt(v["init"]), "l2_final": math.sqrt(v["final"]),
                    "relative_change": math.sqrt(v["delta"]) / math.sqrt(v["init"]) if v["init"] else None,
                    "max_abs_delta": v["max_abs_delta"]} for g, v in squares.items()}
    record.update(status="REINIT_REPRODUCES_UPDATE_1", by_module_group=by_group, by_tensor=by_tensor, withheld=None)
    return record


# ------------------------------------------------------------------------------------------------------------
def require_device_string(device):
    if type(device) is not str or re.fullmatch(r"cuda:[0-9]+", device) is None:
        raise PanelError("GPU_REQUIRED: an explicit cuda:N device is required; there is no CPU path")


def run(run_dir, data_dir, out, *, device="cuda:0", max_wall_seconds=DEFAULT_MAX_WALL_SECONDS):
    require_device_string(device)                     # before any torch import, file write or data read
    if type(max_wall_seconds) is not int or not 60 <= max_wall_seconds <= 2700:
        raise PanelError("INVALID_WALL_LIMIT: 60..2700 seconds")
    started = time.monotonic()
    deadline = started + max_wall_seconds

    def check_deadline():
        if time.monotonic() >= deadline:
            raise PanelError("BUDGET_EXHAUSTED: wall limit reached")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)            # a used output directory is never reused
    status = "FAILED"
    try:
        records = read_run(run_dir)
        train, dev = visible_rows(data_dir, records["plan"])
        compiler = sdg.Compiler()
        rows, selection = select_panels(train, dev, compiler)
        write_once(out / "panel_manifest.json", {"schema": SCHEMA, "selection": selection, "rows": rows,
                                                 "compiler": compiler.receipt, "sources": source_hashes()})
        from q4_smoke_job import _check_device_idle
        _check_device_idle(device)                     # nvidia-smi must report no compute users
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        if os.environ["CUBLAS_WORKSPACE_CONFIG"] != ":4096:8":
            raise PanelError("CUBLAS_WORKSPACE_CONFIG_DIFFERS")
        import torch
        if not torch.cuda.is_available():
            raise PanelError("GPU_REQUIRED: CUDA is unavailable; no CPU fallback")
        if torch.__version__ != EXPECTED_TORCH or sys.version_info[:2] != EXPECTED_PYTHON:
            raise PanelError("RUNTIME_VERSION_MISMATCH: torch %s, python %s" % (torch.__version__, platform.python_version()))
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        from q4_checkpoint import load_checkpoint
        model = load_checkpoint(records["dir"] / "checkpoint", expected_identity=records["identity"],
                                expected_weights_sha256=WEIGHTS_SHA, width=64, device=device)
        reproduced, mismatches = stage0(model, records, dev)
        if mismatches:
            write_once(out / "DEVICE_OR_SOURCE_MISMATCH.json", {"rows": mismatches, "reproduced": reproduced,
                                                                "device": torch.cuda.get_device_name(device)})
            status = "DEVICE_OR_SOURCE_MISMATCH"
            raise PanelError("DEVICE_OR_SOURCE_MISMATCH: %d of 16 saved dev predictions differ" % len(mismatches))
        write_once(out / "stage0_reproduction.json", {"status": "REPRODUCED_16_OF_16", "rows": reproduced})
        from learner_q4_representation import encode_observation
        bottlenecks = {row["record_id"]: model.encode(encode_observation(row["observation"])) for row in rows}
        q3_result, stepwise = run_q3(model, rows, bottlenecks, check_deadline)
        write_once(out / "q3_teacher_forced_vs_free.json", q3_result)
        write_once(out / "q4_one_field_edits.json", run_q4(model, rows, bottlenecks, compiler, check_deadline))
        write_once(out / "q5_summary_swap.json", run_q5(model, rows, bottlenecks, stepwise, check_deadline))
        write_once(out / "q6_gradients_and_weight_change.json",
                   run_q6(model, rows, train, device, records, compiler, check_deadline))
        if sha(guarded_read(records["dir"] / "checkpoint" / "model_state.pt")) != WEIGHTS_SHA:
            raise PanelError("CHECKPOINT_CHANGED_DURING_THE_JOB")
        status = "COMPLETE"
        write_once(out / "result.json", {
            "schema": SCHEMA, "experiment": EXPERIMENT, "label": LABEL, "status": "DIAGNOSTIC_MEASURED_NOT_CERTIFIED",
            "actual_updates": 0, "optimizer": "NONE_CREATED", "weights_sha256": WEIGHTS_SHA, "plan_sha256": PLAN_SHA,
            "panel_selection_digest": selection["digest"], "sources": source_hashes(),
            "runtime": {"torch": torch.__version__, "cuda": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
                        "python": platform.python_version(), "platform": platform.platform(),
                        "device_name": torch.cuda.get_device_name(device),
                        "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
                        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                        "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(device)},
            "compiler": compiler.receipt, "elapsed_seconds": time.monotonic() - started,
            "custody": "targets recompiled from visible text; no sealed or eval file opened; data folder checked",
            "limits": list(RESULT_LIMITS)})
    except BaseException as error:
        try:
            write_once(out / "failure.json", {"status": status, "type": type(error).__name__, "message": str(error),
                                              "elapsed_seconds": time.monotonic() - started})
        except OSError:
            pass
        raise
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("run", "select"):
        command = sub.add_parser(mode)
        command.add_argument("--run-dir", required=True)
        command.add_argument("--data-dir", required=True)
        if mode == "run":
            command.add_argument("--out", required=True)
            command.add_argument("--device", default="cuda:0")
            command.add_argument("--max-wall-seconds", type=int, default=DEFAULT_MAX_WALL_SECONDS)
    args = parser.parse_args(argv)
    if args.mode == "select":
        records = read_run(args.run_dir)
        train, dev = visible_rows(args.data_dir, records["plan"])
        rows, selection = select_panels(train, dev, sdg.Compiler())
        print(json.dumps(selection, indent=1, sort_keys=True))
        return 0
    print(run(args.run_dir, args.data_dir, args.out, device=args.device, max_wall_seconds=args.max_wall_seconds))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as error:          # PanelError, JobError, CheckpointError, LessonError, Q3LoadError
        print("Q4_ERROR_PANEL_FAILED: %s" % error, file=sys.stderr)
        sys.exit(1)
