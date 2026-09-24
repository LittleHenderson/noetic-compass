"""Q4-SDG-1 A-versus-B 0.2: the ONE program that reads the results and emits the frozen verdicts. No torch.

It reads only the result files the runner (q4_ab_train.py) wrote under one results folder:
  job_result.json, STOP.json, stage0.json, prep.json,
  runs/<arm>_<seed>/{run_manifest.json, checkpoint_<NNNNN>.json, run_result.json, reload_check.json}
It never reads smoke/ (the smoke runs gate and time the job; they are never evidence), any data folder, any model
file, or any file whose name contains sealed or ends in _eval.jsonl.

Every rule comes from q4_ab_rules.py (spec Q4_SDG_AB_SPEC_v0_2.md, frozen before launch). It refuses results written
under different rules, and a prep.json whose panels, targets, edits, edit kinds or null rates differ from the frozen
ones. It RECOMPUTES what it decides on (exact trees from the free tokens and the pinned targets; teacher-forced counts
from the per-position bits; edit counts from the raw probabilities, edit by edit in the frozen order) and marks a run
invalid when the runner's own totals disagree. No judgement: the output labels are exactly those listed in LABELS.

  python -B read_q4_ab_results.py --results <folder> [--out verdict.json]
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import q4_ab_rules as rules  # noqa: E402

VERDICT_SCHEMA = "helm-cas-expression-lab.q4-sdg-ab-verdict/0.2"
_FORBIDDEN = re.compile(r"(_eval\.jsonl$|sealed)", re.IGNORECASE)
FIELDS = ("noetic", "domain", "drive", "register")
LABELS = {
    "job": ("JOB_COMPLETE", "JOB_STOPPED_<STOP_CODE>", "JOB_FAILED", "JOB_RESULT_MISSING"),
    "stage0": ("STAGE0_REPRODUCED", "STAGE0_NOT_REPRODUCED", "STAGE0_MISSING"),
    "no_verdict": ("NO_VERDICT_STAGE0", "NO_VERDICT_PREP_MISSING", "NO_VERDICT_FROZEN_RULES_DIFFER",
                   "NO_VERDICT_PREP_NOT_FROZEN"),
    "run": ("RUN_VALID", "RUN_INCOMPLETE", "RUN_INVALID_<REASON>"),
    "checkpoint": tuple("INPUT_USE_" + level for level in rules.LEVELS),
    "calibration": ("INPUT_USE_RULE_SILENT_AT_INITIALISATION", "INPUT_USE_RULE_FIRES_AT_INITIALISATION"),
    "arm": ("ARM_<A|B>_SHOWS_INPUT_USE", "ARM_<A|B>_SHOWS_NO_INPUT_USE", "ARM_<A|B>_INPUT_USE_UNDETERMINED"),
    "architecture": ("ARCHITECTURE_CHANGE_JUSTIFIED", "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE",
                     "ARCHITECTURE_DECISION_INCOMPLETE", "ARCHITECTURE_NOT_EVALUATED"),
    "architecture_reason": tuple("ARCHITECTURE_INCOMPLETE_BECAUSE_" + r for r in rules.ARCHITECTURE_REASONS),
    "pair": ("B_BEATS_A_<PANEL>_PAIR<i>", "A_BEATS_B_<PANEL>_PAIR<i>", "NO_PAIRED_DIFFERENCE_<PANEL>_PAIR<i>",
             "PAIR_INCOMPLETE_<PANEL>_PAIR<i>"),
    "lessons": tuple("LESSONS_%s_<PANEL>" % outcome for outcome in rules.LESSON_OUTCOMES),
    "lessons_overall": tuple("LESSONS_OVERALL_" + outcome for outcome in rules.OVERALL_LESSON_OUTCOMES),
}


class ReadError(ValueError):
    pass


def load(path):
    """Strict JSON of one result file; None when absent. Refuses eval/sealed names, duplicate keys, NaN/Infinity."""
    path = Path(path)
    if _FORBIDDEN.search(path.name):
        raise ReadError("CUSTODY_REFUSED: %s" % path.name)
    if not path.is_file():
        return None

    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):
            raise ReadError("DUPLICATE_JSON_KEYS in %s" % path.name)
        return dict(items)

    def constant(name):
        raise ReadError("NONFINITE_NUMBER in %s" % path.name)
    return json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)


def _fraction_text(value):
    return "%d/%d" % (value.numerator, value.denominator)


def _count(values):
    out = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items()))


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def _lf_sha256(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# ------------------------------------------------------------------------------------------------------------
# One checkpoint: the input-use tests (T1, T2V, T2P, T3) and the level, recomputed from raw per-row and per-edit values
# ------------------------------------------------------------------------------------------------------------
def _panel_rows(checkpoint, name, prep_rows):
    panel = checkpoint.get("panels", {}).get(name)
    if panel is None:
        raise ReadError("PANEL_MISSING: %s" % name)
    rows = panel["rows"]
    if [r["id"] for r in rows] != [r["id"] for r in prep_rows]:
        raise ReadError("PANEL_ROWS_DIFFER_FROM_PREP: %s" % name)
    return panel, rows


def exact_flags(checkpoint, name, prep_rows):
    """Recomputed: GENERATED and the free tokens equal the target tokens. The runner's flag must agree."""
    panel, rows = _panel_rows(checkpoint, name, prep_rows)
    flags = {}
    for row, spec in zip(rows, prep_rows):
        exact = row["outcome"] == "GENERATED" and row["free"] == spec["target_tokens"]
        if bool(row["exact"]) != exact:
            raise ReadError("EXACT_FLAG_DISAGREES: %s" % row["id"])
        flags[row["id"]] = exact
    if panel["exact"] != sum(flags.values()):
        raise ReadError("EXACT_TOTAL_DISAGREES: %s" % name)
    return flags


def field_counts(checkpoint, name, prep_rows):
    """Teacher-forced grammar-masked correct / total per slot kind, from the per-position bits."""
    panel, rows = _panel_rows(checkpoint, name, prep_rows)
    counts = {}
    for row, spec in zip(rows, prep_rows):
        if len(row["tf"]) != len(spec["slot_kinds"]) or set(row["tf"]) - {"0", "1"}:
            raise ReadError("TEACHER_FORCED_BITS_MALFORMED: %s" % row["id"])
        for kind, bit in zip(spec["slot_kinds"], row["tf"]):
            cell = counts.setdefault(kind, [0, 0])
            cell[0] += bit == "1"
            cell[1] += 1
    if {k: list(v) for k, v in panel["tf_by_slot"].items()} != counts:
        raise ReadError("TEACHER_FORCED_TOTALS_DISAGREE: %s" % name)
    return counts


def measurable_edits(prep):
    return [e for e in prep["edits"] if e["to"] is not None]


def edit_move_test(deltas):
    """T2 on one list of moves: u rises >= delta, d falls <= -delta; pass iff u >= min_share x n and the sign test."""
    up = sum(1 for d in deltas if d >= rules.T2_DELTA)
    down = sum(1 for d in deltas if d <= -rules.T2_DELTA)
    sign_p = rules.sign_test_upper(up, down) if up + down else Fraction(1)
    return {"edits": len(deltas), "up": up, "down": down, "p_value": float(sign_p),
            "share_up": _fraction_text(Fraction(up, len(deltas))) if deltas else None,
            "passes": bool(deltas) and Fraction(up) >= rules.T2_MIN_SHARE * len(deltas) and sign_p <= rules.T2_ALPHA,
            "max_abs_delta": max((abs(d) for d in deltas), default=None)}


def input_use(checkpoint, arm, prep):
    sp1 = prep["panels"]["SP1"]
    counts = field_counts(checkpoint, "SP1", sp1)
    fields = {}
    for field in FIELDS:
        k, n = counts.get(field, [0, 0])
        p_teach = rules.most_frequent_rate(prep["pools"][arm]["field_counts"][field])
        p_panel = rules.most_frequent_rate(prep["sp1_field_counts"][field])
        p0 = max(p_teach, p_panel)
        tail = rules.binomial_upper_tail(k, n, p0) if n else Fraction(1)
        fields[field] = {"correct": k, "n": n, "p_teach": _fraction_text(p_teach), "p_panel": _fraction_text(p_panel),
                         "null_rate": _fraction_text(p0), "p_value": float(tail),
                         "passes_alpha": n > 0 and tail <= rules.T1_ALPHA}
    t1 = fields[rules.T1_FIELD]
    values = checkpoint.get("edits", {}).get("values")
    items = measurable_edits(prep)
    if not isinstance(values, list):
        raise ReadError("EDITS_MISSING")
    if len(values) != rules.EDIT_COUNT or len(items) != rules.EDIT_COUNT:
        raise ReadError("EDIT_COUNT_DIFFERS: %d values, %d edits, frozen %d" % (len(values), len(items), rules.EDIT_COUNT))
    moves = {"value": [], "presence": []}
    by_field = {field: [] for field in FIELDS}
    changed_choice = 0
    for value, item in zip(values, items):
        if (not isinstance(value, list) or len(value) != len(rules.EDIT_VALUE_COLUMNS)
                or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in value[:4])):
            raise ReadError("EDIT_VALUE_MALFORMED")
        if value[7] != item["row"] or value[8] != item["position"]:
            raise ReadError("EDIT_ORDER_DIFFERS: %s at %s" % (item["row"], item["position"]))
        delta = value[1] - value[0]
        kind = rules.edit_kind(item["field"], item["from"], item["to"])
        moves[kind].append(delta)
        if kind == "value":
            by_field[item["field"]].append(delta)
        changed_choice += value[4] != value[5]
    t2v, t2p = edit_move_test(moves["value"]), edit_move_test(moves["presence"])
    if t2v["edits"] != rules.VALUE_EDIT_COUNT or t2p["edits"] != rules.PRESENCE_EDIT_COUNT:
        raise ReadError("EDIT_KIND_COUNTS_DIFFER")
    _, rows = _panel_rows(checkpoint, "SP1", sp1)
    distinct = len({tuple(r["free"]) for r in rows})
    if distinct != checkpoint["panels"]["SP1"]["distinct_free_outputs"]:
        raise ReadError("DISTINCT_TOTAL_DISAGREES")
    t3 = {"distinct_free_outputs": distinct, "rows": len(rows), "passes": distinct >= rules.T3_MIN_DISTINCT,
          "meaning": "free generation has not collapsed; not evidence of field-value reading by itself"}
    level = rules.input_use_level(t1["passes_alpha"], t2v["passes"], t2p["passes"], t3["passes"])
    return {"level": level, "label": "INPUT_USE_" + level,
            "T1": dict(t1, field=rules.T1_FIELD, passes=t1["passes_alpha"]), "T2V": t2v, "T2P": t2p, "T3": t3,
            "T2_ALL_EDITS_REPORTED_NOT_DECISIVE": edit_move_test(moves["value"] + moves["presence"]),
            "T2V_BY_FIELD_REPORTED_NOT_DECISIVE": {f: edit_move_test(d) for f, d in by_field.items()},
            "masked_choice_changed_by_edit_reported_not_decisive": changed_choice,
            "secondary_field_tests_reported_not_decisive": {f: v for f, v in fields.items() if f != rules.T1_FIELD},
            "summary_similarity": checkpoint.get("summary_similarity")}


# ------------------------------------------------------------------------------------------------------------
# Runs
# ------------------------------------------------------------------------------------------------------------
def read_run(root, arm, seed, prep, frozen_sha):
    folder = Path(root) / "runs" / ("%s_%d" % (arm, seed))
    manifest, result = load(folder / "run_manifest.json"), load(folder / "run_result.json")
    reload_record = load(folder / "reload_check.json")
    checkpoints = {k: load(folder / ("checkpoint_%05d.json" % k)) for k in rules.CHECKPOINTS}
    info = {"arm": arm, "seed": seed, "readings": {}, "exact": {}, "validity": None}
    problems = []
    if manifest is None:
        info["validity"] = "RUN_INCOMPLETE"
        return info, {}
    if manifest.get("frozen_sha256") != frozen_sha:
        problems.append("FROZEN_SHA_DIFFERS")
    info["init_state_sha256"] = manifest.get("init_state_sha256")
    teach = manifest.get("teach_fit", [])
    per_checkpoint = {}
    for point, record in checkpoints.items():
        if record is None:
            continue
        try:
            if record.get("frozen_sha256") != frozen_sha or record.get("checkpoint") != point:
                raise ReadError("CHECKPOINT_IDENTITY_DIFFERS")
            reading = input_use(record, arm, prep)
            flags = {name: exact_flags(record, name, prep["panels"][name]) for name in ("SP1", "SP2")}
            if "B_DEV" in prep["panels"]:
                flags["B_DEV"] = exact_flags(record, "B_DEV", prep["panels"]["B_DEV"])
            flags["TEACH_FIT"] = exact_flags(record, "TEACH_FIT", teach)
        except (ReadError, KeyError, TypeError, IndexError) as error:
            problems.append("RESULT_INCONSISTENT_AT_%d (%s)" % (point, str(error)[:80]))
            continue
        info["readings"][str(point)] = reading
        per_checkpoint[point] = {"record": record, "flags": flags}
        inspected = {r["id"] for r in prep["panels"]["SP2"] if r.get("inspected")}
        info["exact"][str(point)] = {
            "SP1": [sum(flags["SP1"].values()), len(flags["SP1"])],
            "SP2U": [sum(v for k, v in flags["SP2"].items() if k not in inspected),
                     sum(1 for k in flags["SP2"] if k not in inspected)],
            "SP2ALL": [sum(flags["SP2"].values()), len(flags["SP2"])],
            "B_DEV_B_INTERNAL_REPORT_ONLY": ([sum(flags["B_DEV"].values()), len(flags["B_DEV"])]
                                             if "B_DEV" in flags else None),
            "TEACH_FIT_PER_ARM_NOT_COMPARED": [sum(flags["TEACH_FIT"].values()), len(flags["TEACH_FIT"])]}
        info.setdefault("report_not_decisive", {})[str(point)] = {
            name: {"first_wrong_decision_kinds": _count(r.get("fwd") or "EXACT" for r in panel["rows"]),
                   "mean_free_length": _mean(len(r["free"]) for r in panel["rows"]),
                   "outcomes": _count(r["outcome"] for r in panel["rows"]),
                   "distinct_free_outputs": panel["distinct_free_outputs"],
                   "teacher_forced_by_slot": panel["tf_by_slot"]}
            for name, panel in record["panels"].items()}
        info["report_not_decisive"][str(point)]["summary_similarity"] = record.get("summary_similarity")
    if problems:
        info["validity"] = "RUN_INVALID_" + problems[0].split(" ")[0]
        info["problems"] = problems
    elif result is None or rules.FINAL not in per_checkpoint or any(checkpoints[k] is None for k in rules.CHECKPOINTS):
        info["validity"] = "RUN_INCOMPLETE"
    elif (result.get("status") != "COMPLETE" or result.get("updates") != rules.UPDATES
          or result.get("frozen_sha256") != frozen_sha):
        info["validity"] = "RUN_INVALID_RESULT_RECORD"
    elif reload_record is None:
        info["validity"] = "RUN_INVALID_RELOAD_MISSING"
    elif reload_record.get("status") != "RELOAD_REPRODUCED":
        info["validity"] = "RUN_INVALID_RELOAD_MISMATCH"
    else:
        info["validity"] = "RUN_VALID"
    if result is not None:
        info["practice"] = {k: result.get(k) for k in ("updates", "presentations", "distinct_rows_seen", "pool_rows",
                                                       "target_tokens", "source_bytes", "train_seconds",
                                                       "eval_seconds", "wall_seconds", "final_weights_sha256")}
    return info, per_checkpoint


def valid_final_levels(runs):
    """arm -> the FINAL input-use level of every VALID run of that arm, in seed order."""
    return {arm: [runs[(arm, seed)]["readings"][str(rules.FINAL)]["level"] for seed in rules.SEEDS
                  if runs[(arm, seed)]["validity"] == "RUN_VALID"] for arm in rules.ARMS}


def pair_start_equal(a, b):
    """Same starting tensors: equal init hashes, and identical checkpoint-0 outputs on the shared panels."""
    if a["info"].get("init_state_sha256") is None or a["info"]["init_state_sha256"] != b["info"].get("init_state_sha256"):
        return False
    ca, cb = a["checkpoints"].get(0), b["checkpoints"].get(0)
    if ca is None or cb is None:
        return False
    for name in ("SP1", "SP2"):
        ra, rb = ca["record"]["panels"][name]["rows"], cb["record"]["panels"][name]["rows"]
        if [(r["id"], r["free"], r["tf"]) for r in ra] != [(r["id"], r["free"], r["tf"]) for r in rb]:
            return False
    return True


def compare_pair(flags_a, flags_b, ids):
    b = sum(1 for i in ids if flags_b[i] and not flags_a[i])
    c = sum(1 for i in ids if flags_a[i] and not flags_b[i])
    p_b, p_a = rules.sign_test_upper(b, c), rules.sign_test_upper(c, b)
    if b > c and p_b <= rules.PAIR_ALPHA:
        outcome = "B_BEATS_A"
    elif c > b and p_a <= rules.PAIR_ALPHA:
        outcome = "A_BEATS_B"
    else:
        outcome = "NO_PAIRED_DIFFERENCE"
    return {"b_B_exact_A_not": b, "c_A_exact_B_not": c, "p_B_beats_A": float(p_b), "p_A_beats_B": float(p_a),
            "rows": len(ids), "outcome": outcome}


# ------------------------------------------------------------------------------------------------------------
def verdict(root):
    root = Path(root)
    frozen_sha = rules.frozen_sha256()
    out = {"schema": VERDICT_SCHEMA, "label": rules.LABEL, "experiment": rules.EXPERIMENT,
           "status": "PROGRAM_READING_NOT_CERTIFIED", "frozen_sha256": frozen_sha, "labels": [],
           "reader": "read_q4_ab_results.py", "labels_possible": LABELS,
           "reader_lf_sha256": {"read_q4_ab_results.py": _lf_sha256(__file__),
                                "q4_ab_rules.py": _lf_sha256(rules.__file__)}}
    job = load(root / "job_result.json")
    stop = load(root / "STOP.json")
    if job is None:
        out["job"] = "JOB_RESULT_MISSING"
    elif job.get("status") == "COMPLETE":
        out["job"] = "JOB_COMPLETE"
    elif job.get("stop_code") in rules.STOP_CODES:
        out["job"] = "JOB_STOPPED_%s" % job["stop_code"]
    else:
        out["job"] = "JOB_FAILED"
    out["stop"] = stop
    stage0 = load(root / "stage0.json")
    if stage0 is None:
        out["stage0"] = "STAGE0_MISSING"
    elif stage0.get("status") == "REPRODUCED_16_OF_16" and stage0.get("reinit_update_1", {}).get("reproduced") is True:
        out["stage0"] = "STAGE0_REPRODUCED"
    else:
        out["stage0"] = "STAGE0_NOT_REPRODUCED"
    out["labels"] += [out["job"], out["stage0"]]
    prep = load(root / "prep.json")
    no_verdict = None
    if out["stage0"] != "STAGE0_REPRODUCED":
        no_verdict = "NO_VERDICT_STAGE0"
    elif prep is None:
        no_verdict = "NO_VERDICT_PREP_MISSING"
    elif prep.get("frozen") != rules.frozen_record() or prep.get("frozen_sha256") != frozen_sha:
        no_verdict = "NO_VERDICT_FROZEN_RULES_DIFFER"
    else:
        problems = prep_problems(prep)
        if problems:
            no_verdict = "NO_VERDICT_PREP_NOT_FROZEN"
            out["prep_problems"] = problems
    if no_verdict:
        out["no_verdict"] = no_verdict
        out["architecture"] = "ARCHITECTURE_NOT_EVALUATED"
        out["lessons"] = {p: "LESSONS_NOT_EVALUATED_%s" % p for p in rules.COMPARISON_PANELS}
        out["lessons_overall"] = "LESSONS_OVERALL_NOT_EVALUATED"
        out["labels"] += ([no_verdict, out["architecture"]] + list(out["lessons"].values())
                          + [out["lessons_overall"]])
        return out
    runs, detail = {}, {}
    for arm, seed in rules.RUN_ORDER:
        info, checkpoints = read_run(root, arm, seed, prep, frozen_sha)
        runs[(arm, seed)] = info
        detail[(arm, seed)] = {"info": info, "checkpoints": checkpoints}
    out["runs"] = {"%s_%d" % key: info for key, info in runs.items()}
    levels_at_zero = {"%s_%d" % key: info["readings"]["0"]["level"] for key, info in runs.items()
                      if "0" in info["readings"]}
    fires_at_zero = any(level != "NONE" for level in levels_at_zero.values())
    out["calibration"] = ("INPUT_USE_RULE_FIRES_AT_INITIALISATION" if fires_at_zero
                          else "INPUT_USE_RULE_SILENT_AT_INITIALISATION")
    out["calibration_levels_at_checkpoint_0"] = levels_at_zero
    levels = valid_final_levels(runs)
    out["arms"] = {arm: {"label": rules.arm_label(arm, levels[arm]), "final_levels_of_valid_runs": levels[arm],
                         "valid_runs": len(levels[arm]), "full_runs": levels[arm].count("FULL"),
                         "runs_not_valid": len(rules.SEEDS) - len(levels[arm])} for arm in rules.ARMS}
    arm_labels = [out["arms"][arm]["label"] for arm in rules.ARMS]
    out["architecture"], out["architecture_reasons"] = rules.architecture_decision(levels, fires_at_zero)
    inspected = {r["id"] for r in prep["panels"]["SP2"] if r.get("inspected")}
    panel_ids = {"SP1": [r["id"] for r in prep["panels"]["SP1"]],
                 "SP2U": [r["id"] for r in prep["panels"]["SP2"] if r["id"] not in inspected],
                 "SP2ALL": [r["id"] for r in prep["panels"]["SP2"]]}
    source = {"SP1": "SP1", "SP2U": "SP2", "SP2ALL": "SP2"}
    twins = {r["id"]: r.get("near_twin_distance") or {} for name in ("SP1", "SP2") for r in prep["panels"][name]}
    out["near_twin_disclosure"] = {
        name: {arm: sum(1 for r in prep["panels"][name]
                        if (r.get("near_twin_distance") or {}).get(arm) is not None and r["near_twin_distance"][arm] <= 1)
               for arm in rules.ARMS} for name in ("SP1", "SP2")}
    out["pairs"], out["lessons"], outcome_by_panel = {}, {}, {}
    for panel in rules.COMPARISON_PANELS:
        outcomes = []
        for i, seed in enumerate(rules.SEEDS, 1):
            a, b = detail[("A", seed)], detail[("B", seed)]
            name = "%s_PAIR%d" % (panel, i)
            if (a["info"]["validity"] != "RUN_VALID" or b["info"]["validity"] != "RUN_VALID"
                    or not pair_start_equal(a, b)):
                out["pairs"][name] = {"outcome": "PAIR_INCOMPLETE"}
                outcomes.append("PAIR_INCOMPLETE")
            else:
                flags_a = a["checkpoints"][rules.FINAL]["flags"][source[panel]]
                flags_b = b["checkpoints"][rules.FINAL]["flags"][source[panel]]
                result = compare_pair(flags_a, flags_b, panel_ids[panel])
                far = [i for i in panel_ids[panel] if all((twins.get(i) or {}).get(arm) is None
                                                          or twins[i][arm] >= 2 for arm in rules.ARMS)]
                result["report_not_decisive_without_near_twins"] = dict(
                    compare_pair(flags_a, flags_b, far), note="rows at token distance 0 or 1 from either arm's "
                                                            "teaching pool removed (review A2 disclosure)")
                out["pairs"][name] = result
                outcomes.append(result["outcome"])
            out["labels"].append("%s_%s" % (out["pairs"][name]["outcome"], name))
        if "PAIR_INCOMPLETE" in outcomes:
            outcome_by_panel[panel] = "COMPARISON_INCOMPLETE"
        elif all(x == "B_BEATS_A" for x in outcomes):
            outcome_by_panel[panel] = "HELP"
        elif all(x == "A_BEATS_B" for x in outcomes):
            outcome_by_panel[panel] = "HURT"
        else:
            outcome_by_panel[panel] = "EFFECT_NOT_SHOWN"
        out["lessons"][panel] = "LESSONS_%s_%s" % (outcome_by_panel[panel], panel)
    out["lessons_overall"] = "LESSONS_OVERALL_" + rules.overall_lessons(outcome_by_panel)
    out["lessons_overall_panels"] = list(rules.PRIMARY_PANELS)
    out["labels"] += ["%s_%d:%s" % (k[0], k[1], v["validity"]) for k, v in runs.items()]
    out["labels"] += ["%s_%d@%s:%s" % (k[0], k[1], rules.FINAL, v["readings"][str(rules.FINAL)]["label"])
                      for k, v in runs.items() if str(rules.FINAL) in v["readings"]]
    out["labels"] += ([out["calibration"]] + arm_labels + [out["architecture"]]
                      + ["ARCHITECTURE_INCOMPLETE_BECAUSE_" + r for r in out["architecture_reasons"]]
                      + list(out["lessons"].values()) + [out["lessons_overall"]])
    return out


def _recount(rows, field):
    """Nonzero counts of each target token at the `field` positions, from the (pinned) targets, sorted."""
    counts = {}
    for row in rows:
        if len(row["target_tokens"]) != len(row["slot_kinds"]):
            raise ValueError("TARGET_AND_SLOT_LENGTHS_DIFFER")
        for token, kind in zip(row["target_tokens"], row["slot_kinds"]):
            if kind == field:
                counts[token] = counts.get(token, 0) + 1
    return sorted(counts.values())


def _counts_ok(counts):
    return (isinstance(counts, dict) and counts and all(type(v) is int and v >= 0 for v in counts.values())
            and sum(counts.values()) > 0)


def prep_problems(prep):
    """Every check that prep.json fails against the frozen record ([] = it is the frozen prep). Recomputed here:
    panel digests, the pinned targets, the edits and their kinds, the SP1 field counts and both frozen null rates."""
    try:
        sp1, sp2 = prep["panels"]["SP1"], prep["panels"]["SP2"]
        checks = {
            "SP1_DIGEST": rules.sha(rules.canonical([[r["id"], r["content_sha256"]] for r in sp1])) == rules.SP1_DIGEST,
            "SP2_DIGEST": rules.sha(rules.canonical([[r["id"], r["content_sha256"]] for r in sp2])) == rules.SP2_DIGEST,
            "PANEL_TARGETS_DIGEST": rules.panel_targets_digest(
                [(r["id"], r["target_tokens"], r["slot_kinds"]) for r in sp1 + sp2]) == rules.PANEL_TARGETS_DIGEST,
            "INSPECTED_DEV_DIGEST": rules.sha(rules.canonical(sorted(prep["inspected_dev_ids"])))
                                    == rules.INSPECTED_DEV_DIGEST,
            "A_POOL_DIGEST": rules.sha(rules.canonical(prep["pools"]["A"]["ids"])) == rules.A_POOL_DIGEST,
            "A_POOL_ROWS": len(prep["pools"]["A"]["ids"]) == rules.A_POOL_ROWS,
            "EDIT_PANEL_DIGEST": rules.sha(rules.canonical([[e["row"], e["path"], e["field"], e["to"], e["observation"]]
                                                            for e in prep["edits"]])) == rules.EDIT_PANEL_DIGEST,
            "EDIT_KINDS_DIGEST": rules.edit_kinds_digest(
                [(e["row"], e["position"], rules.edit_kind(e["field"], e["from"], e["to"]))
                 for e in measurable_edits(prep)]) == rules.EDIT_KINDS_DIGEST,
            "EDIT_COUNT": len(measurable_edits(prep)) == rules.EDIT_COUNT,
            "SP2_INSPECTED_FLAGS": {r["id"] for r in sp2 if r.get("inspected")} == set(prep["inspected_dev_ids"]),
            "PANEL_SIZES": len(sp2) == 256 and len(sp1) == rules.SP1_SIZE,
            "B_POOL_PRESENT": "B" in prep["pools"],
            "SP1_FIELD_COUNTS_RECOMPUTE": all(
                sorted(v for v in prep["sp1_field_counts"][f].values() if v) == _recount(sp1, f) for f in FIELDS),
            "SP1_NOETIC_NULL": rules.most_frequent_rate(prep["sp1_field_counts"]["noetic"]) == rules.SP1_NOETIC_NULL,
            "A_POOL_NOETIC_NULL": rules.most_frequent_rate(prep["pools"]["A"]["field_counts"]["noetic"])
                                  == rules.A_POOL_NOETIC_NULL,
            "POOL_COUNTS_WELL_FORMED": all(
                _counts_ok(prep["pools"][arm]["field_counts"][f]) for arm in prep["pools"] for f in FIELDS)
                and all(prep["pools"][arm]["noetic_counts"] == prep["pools"][arm]["field_counts"]["noetic"]
                        for arm in prep["pools"]),
        }
    except (KeyError, TypeError, ValueError, ZeroDivisionError, AttributeError) as error:
        return ["PREP_UNREADABLE (%s)" % type(error).__name__]
    return [name for name, ok in checks.items() if not ok]


def prep_is_frozen(prep):
    return not prep_problems(prep)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--results", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = verdict(args.results)
    body = (json.dumps(result, indent=1, sort_keys=True) + "\n").encode("utf-8")
    if args.out:
        with Path(args.out).open("xb") as stream:
            stream.write(body)
    for label in result["labels"]:
        print(label)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReadError as error:
        print("Q4_AB_READER_REFUSED: %s" % error, file=sys.stderr)
        sys.exit(1)
