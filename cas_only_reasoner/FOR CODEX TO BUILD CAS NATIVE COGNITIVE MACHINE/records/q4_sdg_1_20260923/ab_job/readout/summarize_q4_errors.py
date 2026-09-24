"""Q4-SDG-1 saved-error summary. Read-only, $0, laptop, standard library only: no torch, no model, no rerun.

It reads ONLY the saved public records of the completed A-versus-B job:
  ../results/ab/prep.json                         panel rows: ids, target tokens, slot kinds, shape, inspected flag
  ../results/ab/runs/<run>/checkpoint_32768.json  per row: first wrong decision (fwd), assisted token bits (tf),
                                                  generated tokens (free), outcome, exact; per panel tf_by_slot
  ../results/ab/runs/<run>/run_result.json        run status and update count (identity check only)
  ../VERDICT_LAPTOP_REREAD.json                   the program-emitted verdict labels (quoted unchanged)
and, for the per-run CONTEXT section only (reported, not decisive):
  ../results/ab/runs/<run>/checkpoint_<earlier>.json   SP1 assisted bits at the earlier saved checkpoints
  ../results/ab/runs/<run>/run_manifest.json           the run's 64 teaching-fit rows (targets, slot kinds)
  ../results/ab/runs/<run>/updates.json                the saved training-loss windows
plus the pinned vocabulary / grammar mask (learner_q4_decoder.py) and the frozen constants (q4_ab_rules.py) from
research/helm_cas_expression_lab/.

It never opens *.pt, *_eval*, sealed*, salt* or anything under D:/tksCAS-archive (the open helper refuses them).

Panels (q4_ab_rules.PANELS): SP1 = 256 familiar-structure rows; SP2U = the 208 SP2 rows never inspected;
SP2ALL = all 256 SP2 rows. Final checkpoint only (32768 updates). Everything here is DESCRIPTIVE: it changes no
label and decides nothing.

  python -B summarize_q4_errors.py [--out <new json path>]      (create-only: refuses an existing output)
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
AB_JOB = HERE.parent
AB = AB_JOB / "results" / "ab"
LAB = HERE.parents[3] / "research" / "helm_cas_expression_lab"
if str(LAB) not in sys.path:
    sys.path.insert(0, str(LAB))

from learner_q4_decoder import TOKENS, allowed_next  # noqa: E402  -- pure Python, no torch
import q4_ab_rules as rules  # noqa: E402  -- frozen constants only (edit kinds, T2 delta, checkpoints); stdlib only

SCHEMA = "helm-cas-expression-lab.q4-sdg-error-summary/0.1"
LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"
FINAL = 32768
RUNS = ("A_20260931", "A_20260932", "A_20260933", "B_20260931", "B_20260932", "B_20260933")
ARMS = ("A", "B")
PANELS = ("SP1", "SP2U", "SP2ALL")
EXPECTED_N = {"SP1": 256, "SP2U": 208, "SP2ALL": 256}
SOURCE_PANEL = {"SP1": "SP1", "SP2U": "SP2", "SP2ALL": "SP2"}
EXPECTED_VERDICT = {"lessons_overall": "LESSONS_OVERALL_EFFECT_NOT_SHOWN",
                    "architecture": "ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE"}
FIELDS = ("noetic", "domain", "drive", "register")
FIELD_MISTAKE = {f: "WRONG_" + f.upper() for f in FIELDS}
MISTAKE_GROUP = {"EXACT": "EXACT",
                 "WRONG_NOETIC": "FIELD", "WRONG_DOMAIN": "FIELD", "WRONG_DRIVE": "FIELD", "WRONG_REGISTER": "FIELD",
                 "LOST_BRANCH": "STRUCTURE_BRANCH", "INVENTED_BRANCH": "STRUCTURE_BRANCH",
                 "PLUS_FOR_TIMES": "OPERATOR", "TIMES_FOR_PLUS": "OPERATOR",
                 "PREDICTION_ENDED": "OTHER", "GRAMMAR_VIOLATION": "OTHER"}
MISTAKE_ORDER = tuple(MISTAKE_GROUP)
GROUP_ORDER = ("EXACT", "FIELD", "STRUCTURE_BRANCH", "OPERATOR", "OTHER")
SLOT_ORDER = ("expr", "op", "noetic", "domain", "drive", "register", "eos")
SHAPE_CLASSES = ("SHAPE_MATCH", "FEWER_LEAVES", "MORE_LEAVES", "SAME_LEAF_COUNT_OTHER_SHAPE", "NOT_A_COMPLETE_TREE")
LEAF_BINS = ("leaf1", "leaf2", "leaf3", "leaf4+")          # which leaf of the TARGET tree (prefix order) a slot is in
FORBIDDEN_PARTS = ("_eval", "sealed", "salt")
READ = {}


class SummaryError(RuntimeError):
    pass


def open_json(path):
    """The only file-open path. Refuses model weights, eval, sealed and salt files, and the archive."""
    path = Path(path)
    low = str(path).replace("\\", "/").lower()
    if path.suffix.lower() == ".pt" or any(part in path.name.lower() for part in FORBIDDEN_PARTS) \
            or "tkscas-archive" in low:
        raise SummaryError("REFUSED_FORBIDDEN_FILE: %s" % path.name)
    data = path.read_bytes()
    READ[path.relative_to(AB_JOB.parent).as_posix() if AB_JOB.parent in path.parents else str(path)] = \
        hashlib.sha256(data).hexdigest()
    return json.loads(data.decode("utf-8"))


def lf_sha256(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# ---- tree helpers (the codec's prefix order: STATE noetic domain drive register | BINARY op left right) --------
def slot_info(target):
    """Per target position: (slot kind, tree path, leaves completed before this position)."""
    pending, out, leaves = [("expr", "")], [], 0
    for token in target:
        name = TOKENS[token]
        if not pending:
            out.append(("eos", "", leaves))
            continue
        kind, path = pending.pop()
        out.append((kind, path, leaves))
        if kind == "expr" and name == "STATE":
            pending.extend((k, path) for k in ("register", "drive", "domain", "noetic"))
        elif kind == "expr" and name == "BINARY":
            pending.extend((("expr", path + "R"), ("expr", path + "L"), ("op", path)))
        elif kind == "register":
            leaves += 1
    return out


def parse(tokens):
    """(tree, shape, depth, leaves) for one complete tree followed by EOS; None otherwise."""
    names = [TOKENS[t] if type(t) is int and 0 <= t < len(TOKENS) else None for t in tokens]
    pos = 0

    def node():
        nonlocal pos
        if pos >= len(names):
            raise SummaryError("INCOMPLETE")
        name = names[pos]
        pos += 1
        if name == "BINARY":
            if pos >= len(names):
                raise SummaryError("INCOMPLETE")
            op = names[pos]
            pos += 1
            left, right = node(), node()
            return ("B", op, left, right)
        if name == "STATE":
            fields = tuple(names[pos:pos + 4])
            if len(fields) < 4:
                raise SummaryError("INCOMPLETE")
            pos += 4
            return ("S", fields)
        raise SummaryError("NOT_A_NODE")

    try:
        tree = node()
    except SummaryError:
        return None
    if pos != len(names) - 1 or names[pos] != "EOS":
        return None
    return tree, shape_of(tree), depth_of(tree), leaves_of(tree)


def shape_of(tree):
    return "L" if tree[0] == "S" else "(%s %s)" % (shape_of(tree[2]), shape_of(tree[3]))


def depth_of(tree):
    return 0 if tree[0] == "S" else 1 + max(depth_of(tree[2]), depth_of(tree[3]))


def leaves_of(tree):
    return [tree[1]] if tree[0] == "S" else leaves_of(tree[2]) + leaves_of(tree[3])


def ops_of(tree):
    return [] if tree[0] == "S" else [tree[1]] + ops_of(tree[2]) + ops_of(tree[3])


def first_wrong(pred, target, slots):
    """The same rule as q4_sdg_curriculum.first_wrong_decision, re-derived here to check the saved fwd label."""
    for index, gold in enumerate(target):
        if index >= len(pred):
            return index, "PREDICTION_ENDED"
        if pred[index] == gold:
            continue
        if pred[index] not in allowed_next(tuple(target[:index])):
            return index, "GRAMMAR_VIOLATION"
        kind = slots[index][0]
        if kind == "expr":
            return index, "LOST_BRANCH" if TOKENS[gold] == "BINARY" else "INVENTED_BRANCH"
        if kind == "op":
            return index, "PLUS_FOR_TIMES" if TOKENS[pred[index]] == "PLUS" else "TIMES_FOR_PLUS"
        return index, FIELD_MISTAKE[kind]
    if len(pred) > len(target):
        return len(target), "GRAMMAR_VIOLATION"
    return None, None


# ---- one panel of one run ---------------------------------------------------------------------------------------
def fraction(a, b):
    return "%d/%d" % (a, b)


def summarize_panel(rows, targets, checks, where):
    n = len(rows)
    mistakes = collections.Counter()
    fwd_slot = collections.Counter()
    fwd_leaves_before = collections.Counter()
    fwd_index_sum = 0
    fwd_rows = 0
    shape_classes = collections.Counter()
    missing_leaves_total = 0
    extra_leaves_total = 0
    depth_pairs = collections.Counter()
    length = {"free_tokens_total": 0, "target_tokens_total": 0, "shorter": 0, "equal": 0, "longer": 0}
    tf_slot = {k: [0, 0] for k in SLOT_ORDER}
    tf_field_leaf = {f: {b: [0, 0] for b in LEAF_BINS} for f in FIELDS}
    tf_perfect_rows = 0
    matched_field = {f: [0, 0] for f in FIELDS}
    matched_op = [0, 0]
    outcomes = collections.Counter()
    exact = 0
    fwd_label_agree = 0
    for row in rows:
        target_row = targets[row["id"]]
        target = target_row["target_tokens"]
        slots = slot_info(target)
        if [s[0] for s in slots] != list(target_row["slot_kinds"]):
            raise SummaryError("SLOT_KINDS_DISAGREE %s %s" % (where, row["id"]))
        free = list(row["free"])
        outcomes[row["outcome"]] += 1
        exact += row["exact"]
        saved = row["fwd"] or "EXACT"
        index, mine = first_wrong(free, target, slots)
        mine = mine or "EXACT"
        fwd_label_agree += mine == saved
        mistakes[saved] += 1
        if index is not None:
            fwd_rows += 1
            fwd_index_sum += index
            kind = slots[index][0] if index < len(slots) else "eos"
            fwd_slot[kind] += 1
            leaves_before = slots[index][2] if index < len(slots) else target_row["leaf_count"]
            fwd_leaves_before[str(leaves_before) if leaves_before < 4 else "4+"] += 1
        # structure of the generated answer against the target
        tgt = parse(target)
        if tgt is None or tgt[1] != target_row["shape"] or tgt[2] != target_row["depth"] \
                or len(tgt[3]) != target_row["leaf_count"]:
            raise SummaryError("TARGET_TREE_DISAGREES_WITH_PREP %s %s" % (where, row["id"]))
        got = parse(free) if row["outcome"] == "GENERATED" else None
        if got is None:
            shape_classes["NOT_A_COMPLETE_TREE"] += 1
        else:
            depth_pairs["%d->%d" % (tgt[2], got[2])] += 1
            if got[1] == tgt[1]:
                shape_classes["SHAPE_MATCH"] += 1
                for leaf_t, leaf_g in zip(tgt[3], got[3]):
                    for f, a, b in zip(FIELDS, leaf_t, leaf_g):
                        matched_field[f][0] += a == b
                        matched_field[f][1] += 1
                for a, b in zip(ops_of(tgt[0]), ops_of(got[0])):
                    matched_op[0] += a == b
                    matched_op[1] += 1
            elif len(got[3]) < len(tgt[3]):
                shape_classes["FEWER_LEAVES"] += 1
                missing_leaves_total += len(tgt[3]) - len(got[3])
            elif len(got[3]) > len(tgt[3]):
                shape_classes["MORE_LEAVES"] += 1
                extra_leaves_total += len(got[3]) - len(tgt[3])
            else:
                shape_classes["SAME_LEAF_COUNT_OTHER_SHAPE"] += 1
        # length (EOS counted on both sides)
        length["free_tokens_total"] += len(free)
        length["target_tokens_total"] += len(target)
        length["shorter" if len(free) < len(target) else "equal" if len(free) == len(target) else "longer"] += 1
        # assisted (teacher-forced) token bits
        bits = row["tf"]
        if len(bits) != len(target):
            raise SummaryError("TF_BITS_LENGTH %s %s" % (where, row["id"]))
        for (kind, _, leaves_done), bit in zip(slots, bits):
            tf_slot[kind][0] += bit == "1"
            tf_slot[kind][1] += 1
            if kind in FIELDS:
                cell = tf_field_leaf[kind][LEAF_BINS[min(leaves_done, 3)]]
                cell[0] += bit == "1"
                cell[1] += 1
        tf_perfect_rows += set(bits) == {"1"}
    groups = collections.Counter()
    for mistake, count in mistakes.items():
        if mistake not in MISTAKE_GROUP:
            raise SummaryError("UNKNOWN_MISTAKE %s %s" % (where, mistake))
        groups[MISTAKE_GROUP[mistake]] += count
    checks.append({"check": "%s: first-wrong labels re-derived from generated vs target tokens agree" % where,
                   "value": fraction(fwd_label_agree, n), "pass": fwd_label_agree == n})
    checks.append({"check": "%s: first-wrong kinds add up to the panel size" % where,
                   "value": "%d of %d" % (sum(mistakes.values()), n), "pass": sum(mistakes.values()) == n})
    checks.append({"check": "%s: structure classes add up to the panel size" % where,
                   "value": "%d of %d" % (sum(shape_classes.values()), n), "pass": sum(shape_classes.values()) == n})
    checks.append({"check": "%s: length classes add up to the panel size" % where,
                   "value": "%d of %d" % (length["shorter"] + length["equal"] + length["longer"], n),
                   "pass": length["shorter"] + length["equal"] + length["longer"] == n})
    checks.append({"check": "%s: exact rows == EXACT first-wrong rows" % where,
                   "value": "%d vs %d" % (exact, mistakes["EXACT"]), "pass": exact == mistakes["EXACT"]})
    return {
        "n": n,
        "exact": exact,
        "outcomes": dict(sorted(outcomes.items())),
        "first_wrong_decision": {
            "by_kind": {k: mistakes.get(k, 0) for k in MISTAKE_ORDER},
            "by_group": {g: groups.get(g, 0) for g in GROUP_ORDER},
            "by_slot_kind": {k: fwd_slot.get(k, 0) for k in SLOT_ORDER},
            "whole_leaves_right_before_it": dict(sorted(fwd_leaves_before.items())),
            "index_sum": fwd_index_sum, "rows_with_a_wrong_decision": fwd_rows},
        "structure": {
            "by_class": {c: shape_classes.get(c, 0) for c in SHAPE_CLASSES},
            "missing_leaves_total": missing_leaves_total, "extra_leaves_total": extra_leaves_total,
            "target_depth_to_generated_depth": dict(sorted(depth_pairs.items()))},
        "length": length,
        "assisted_accuracy_by_slot": {k: v for k, v in tf_slot.items() if v[1]},
        "assisted_accuracy_by_field_and_leaf": tf_field_leaf,
        "assisted_rows_all_tokens_right": tf_perfect_rows,
        "free_field_accuracy_on_shape_matched_rows": {"fields": matched_field, "op": matched_op},
    }


def first_or_later(leaves_done):
    return "leaf1" if leaves_done == 0 else "later_leaves"


def run_context(run, prep, targets, verdict, final_record, checks):
    """Context for the one proposal, per run, REPORTED NOT DECISIVE and never an arm comparison:
    (1) SP1 assisted noetic accuracy on the first leaf vs later leaves at every saved checkpoint;
    (2) the same split on the run's own 64 teaching-fit rows at the final checkpoint;
    (3) the saved one-field VALUE edits at the final checkpoint, split first leaf vs later leaves;
    (4) the saved training loss, averaged over blocks of 4,096 updates."""
    out = {"note": "context for the proposal only; reported, not decisive; TEACH_FIT is per run and never compared"}
    by_checkpoint = {}
    for point in rules.CHECKPOINTS:
        record = final_record if point == FINAL else open_json(AB / "runs" / run / ("checkpoint_%05d.json" % point))
        if record["checkpoint"] != point or record["frozen_sha256"] != prep["frozen_sha256"]:
            raise SummaryError("CHECKPOINT_IDENTITY %s %d" % (run, point))
        cells = {"leaf1": [0, 0], "later_leaves": [0, 0]}
        for row in record["panels"]["SP1"]["rows"]:
            for (kind, _, done), bit in zip(slot_info(targets[row["id"]]["target_tokens"]), row["tf"]):
                if kind == "noetic":
                    cells[first_or_later(done)][0] += bit == "1"
                    cells[first_or_later(done)][1] += 1
        by_checkpoint[str(point)] = cells
    out["sp1_assisted_noetic_first_vs_later_leaf_by_checkpoint"] = by_checkpoint
    t1 = verdict["runs"][run]["readings"][str(FINAL)]["T1"]
    final_cells = by_checkpoint[str(FINAL)]
    checks.append({"check": "%s assisted noetic (first + later leaves) equals the program's T1 count at 32768" % run,
                   "value": "%d+%d vs %d/%d" % (final_cells["leaf1"][0], final_cells["later_leaves"][0],
                                                t1["correct"], t1["n"]),
                   "pass": [final_cells["leaf1"][0] + final_cells["later_leaves"][0],
                            final_cells["leaf1"][1] + final_cells["later_leaves"][1]] == [t1["correct"], t1["n"]]})
    manifest = open_json(AB / "runs" / run / "run_manifest.json")
    teach = {r["id"]: r for r in manifest["teach_fit"]}
    teach_cells = {f: {"leaf1": [0, 0], "later_leaves": [0, 0]} for f in FIELDS}
    for row in final_record["panels"]["TEACH_FIT"]["rows"]:
        spec = teach[row["id"]]
        slots = slot_info(spec["target_tokens"])
        if [s[0] for s in slots] != list(spec["slot_kinds"]) or len(row["tf"]) != len(slots):
            raise SummaryError("TEACH_FIT_SLOTS %s %s" % (run, row["id"]))
        for (kind, _, done), bit in zip(slots, row["tf"]):
            if kind in FIELDS:
                teach_cells[kind][first_or_later(done)][0] += bit == "1"
                teach_cells[kind][first_or_later(done)][1] += 1
    out["teach_fit_final_assisted_by_field_first_vs_later_leaf"] = teach_cells
    out["teach_fit_final_exact"] = [final_record["panels"]["TEACH_FIT"]["exact"], final_record["panels"]["TEACH_FIT"]["n"]]
    items = [e for e in prep["edits"] if e["to"] is not None]
    values = final_record["edits"]["values"]
    if len(items) != len(values):
        raise SummaryError("EDIT_COUNT %s" % run)
    moves = {f: {"leaf1": [0, 0, 0], "later_leaves": [0, 0, 0]} for f in FIELDS}      # [edits, up, down]
    for value, item in zip(values, items):
        if value[7] != item["row"] or value[8] != item["position"]:
            raise SummaryError("EDIT_ORDER %s" % run)
        if rules.edit_kind(item["field"], item["from"], item["to"]) != "value":
            continue
        done = slot_info(targets[item["row"]]["target_tokens"])[item["position"]][2]
        cell = moves[item["field"]][first_or_later(done)]
        delta = value[1] - value[0]
        cell[0] += 1
        cell[1] += delta >= rules.T2_DELTA
        cell[2] += delta <= -rules.T2_DELTA
    out["final_value_edits_first_vs_later_leaf"] = {
        "columns": ["edits", "up", "down"],
        "meaning": "an edit changes one field value in the input; 'up' = the model's probability of the NEW value "
                   "rose by at least %s at that field's position (the frozen T2 step); 'down' = fell by at least it"
                   % rules.T2_DELTA,
        "fields": moves}
    windows = open_json(AB / "runs" / run / "updates.json")["windows"]
    blocks = {}
    for start in range(0, len(windows), 64):
        block = windows[start:start + 64]
        blocks[str(block[-1]["last_update"])] = sum(w["loss_mean"] * w["n"] for w in block) / sum(w["n"] for w in block)
    out["training_loss_mean_per_4096_updates"] = blocks
    return out


def add(total, part):
    """Sum two panel summaries (same keys); used for the per-arm totals over three seeds."""
    if isinstance(part, dict):
        for key, value in part.items():
            if isinstance(value, (dict, list)):
                total.setdefault(key, {} if isinstance(value, dict) else [0] * len(value))
                if isinstance(value, list):
                    total[key] = [a + b for a, b in zip(total[key], value)]
                else:
                    add(total[key], value)
            else:
                total[key] = total.get(key, 0) + value
    return total


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(HERE / "Q4_ERROR_SUMMARY_20260924.json"))
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        raise SystemExit("REFUSED: output exists (create-only): %s" % out)
    checks = []
    prep = open_json(AB / "prep.json")
    verdict = open_json(AB_JOB / "VERDICT_LAPTOP_REREAD.json")
    for key, want in EXPECTED_VERDICT.items():
        checks.append({"check": "verdict label %s quoted unchanged" % key, "value": verdict[key],
                       "pass": verdict[key] == want})
    inspected = {r["id"] for r in prep["panels"]["SP2"] if r.get("inspected")}
    panel_ids = {"SP1": [r["id"] for r in prep["panels"]["SP1"]],
                 "SP2U": [r["id"] for r in prep["panels"]["SP2"] if r["id"] not in inspected],
                 "SP2ALL": [r["id"] for r in prep["panels"]["SP2"]]}
    targets = {r["id"]: r for name in ("SP1", "SP2") for r in prep["panels"][name]}
    for panel, ids in panel_ids.items():
        checks.append({"check": "prep panel %s size" % panel, "value": len(ids), "pass": len(ids) == EXPECTED_N[panel]})
    runs = {}
    for run in RUNS:
        result = open_json(AB / "runs" / run / "run_result.json")
        record = open_json(AB / "runs" / run / ("checkpoint_%05d.json" % FINAL))
        ok = (result["status"] == "COMPLETE" and result["updates"] == FINAL and record["checkpoint"] == FINAL
              and record["frozen_sha256"] == prep["frozen_sha256"] == result["frozen_sha256"]
              and record["arm"] == run[0] and "%s_%d" % (record["arm"], record["seed"]) == run)
        checks.append({"check": "%s identity (COMPLETE, 32768 updates, frozen sha, arm, seed)" % run,
                       "value": result["status"], "pass": ok})
        runs[run] = {"arm": run[0], "seed": record["seed"], "panels": {}}
        for panel in PANELS:
            source = record["panels"][SOURCE_PANEL[panel]]
            by_id = {r["id"]: r for r in source["rows"]}
            source_ids = panel_ids["SP1"] if SOURCE_PANEL[panel] == "SP1" else panel_ids["SP2ALL"]
            if len(by_id) != len(source["rows"]) or set(by_id) != set(source_ids):
                raise SummaryError("PANEL_IDS_DIFFER %s %s" % (run, panel))
            rows = [by_id[i] for i in panel_ids[panel]]
            summary = summarize_panel(rows, targets, checks, "%s %s" % (run, panel))
            runs[run]["panels"][panel] = summary
            reread = verdict["runs"][run]["exact"][str(FINAL)][panel]
            checks.append({"check": "%s %s exact equals the verdict re-read" % (run, panel),
                           "value": "%d/%d vs %d/%d" % (summary["exact"], summary["n"], reread[0], reread[1]),
                           "pass": [summary["exact"], summary["n"]] == reread})
            if panel != "SP2U":
                saved = {k: list(v) for k, v in source["tf_by_slot"].items()}
                checks.append({"check": "%s %s assisted accuracy re-derived from tf bits equals saved tf_by_slot"
                                        % (run, panel),
                               "value": "equal" if saved == summary["assisted_accuracy_by_slot"] else "differs",
                               "pass": saved == summary["assisted_accuracy_by_slot"]})
                checks.append({"check": "%s %s exact equals the saved panel exact" % (run, panel),
                               "value": "%d vs %d" % (summary["exact"], source["exact"]),
                               "pass": summary["exact"] == source["exact"]})
        runs[run]["context_reported_not_decisive"] = run_context(run, prep, targets, verdict, record, checks)
    arms = {arm: {panel: add({}, {}) for panel in PANELS} for arm in ARMS}
    for run, data in runs.items():
        for panel in PANELS:
            add(arms[data["arm"]][panel], json.loads(json.dumps(data["panels"][panel])))
    failed = [c for c in checks if not c["pass"]]
    report = {
        "schema": SCHEMA, "label": LABEL, "experiment": "Q4-SDG-1", "checkpoint": FINAL,
        "frozen_sha256": prep["frozen_sha256"],
        "status": "CHECKS_PASS" if not failed else "CHECKS_FAIL",
        "what_this_is": "descriptive error summary of the saved public A-versus-B records; decides nothing; "
                        "changes no label; no model loaded, no rerun, no torch",
        "verdict_labels_quoted_unchanged": {"lessons_overall": verdict["lessons_overall"],
                                            "architecture": verdict["architecture"],
                                            "lessons": verdict["lessons"]},
        "panels": {"SP1": "256 familiar-structure rows (shared, decisive)",
                   "SP2U": "208 new-structure rows never inspected (shared, decisive)",
                   "SP2ALL": "all 256 new-structure rows (reported)"},
        "mistake_groups": {g: [k for k in MISTAKE_ORDER if MISTAKE_GROUP[k] == g] for g in GROUP_ORDER},
        "runs": runs,
        "arm_totals_over_three_seeds": arms,
        "checks": checks,
        "checks_failed": len(failed),
        "inputs_sha256_raw_bytes": dict(sorted(READ.items())),
        "program": {"file": "summarize_q4_errors.py", "lf_sha256": lf_sha256(__file__),
                    "imports_lf_sha256": {"learner_q4_decoder.py": lf_sha256(LAB / "learner_q4_decoder.py"),
                                          "q4_ab_rules.py": lf_sha256(LAB / "q4_ab_rules.py")}},
    }
    partial = out.with_name(out.name + ".partial")
    with open(partial, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=1, sort_keys=True)
        handle.write("\n")
    os.replace(partial, out)
    print("%s: %d checks, %d failed -> %s" % (report["status"], len(checks), len(failed), out))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
