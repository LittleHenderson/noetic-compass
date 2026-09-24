"""ITEM2 reader for the corrected wiring probe v0.3. JSON in, JSON out; standard library plus the frozen metric; no torch.

Rules: PREREG_ANALOGY_WIRING_PROBE_v0_3.md section 7 (status PROPOSED), which restates A5.2 of
PREREG_ANALOGY_WIRING_PROBE_v0_2.md for probe v0.3. Label: CLAUDE_BUILT_CLAUDE_CHECKED;
EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.

Every verdict is RE-DERIVED here from the raw score tables with the frozen metric. A verdict that the harness wrote
is never read. The 18 registered checkpoints (3 repaired seeds x pass_01.pt, evidence/main_checkpoint_0294/0588/
0882/1176.pt, final.pt) are fixed in this file; a missing one is a failure, never a skip.

  python -B item2_reader.py --inputs ITEM2_INPUTS.json [--out FILE]      (FILE is created; never replaced)

ITEM2_INPUTS.json (paths relative to that file):
  {"schema": "claude.item2-inputs/0.3",
   "entries": [{"model_seed": 20260917, "checkpoint_relative_path": "pass_01.pt", "main_updates": 147,
                "checkpoint_sha256": "<from the receipt inventory>", "receipt_root": "...",
                "score_table": "<path>", "score_table_sha256": "<sha256 of that file>"}, ... 18 ...],
   "validation_summary": "<path to validation_summary.json>", "validation_summary_sha256": "<sha256>",
   "acceptance_record": "<path>" or null}

Outcome: ITEM2_PASS | ITEM2_FAIL:<seed>/<checkpoint>=<reason>,... | ITEM2_INVALID | ITEM2_NOT_READ_PROBE_NOT_VALIDATED.
Mechanism gate: CLEARED only when ITEM2_PASS, VALIDATION_PASS, frozen rules, matching provenance on every table, and an
acceptance record that binds this prereg, metric and harness all hold. Otherwise MECHANISM_GATE_OPEN, with every
reason. This reader does NOT cover the A5.5 matched-start check, which is a separate program.
Exit: 0 when a reading was produced (whatever it says); 1 TOOL_STOP (malformed or unregistered input; nothing read).
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import probe_v0_3_metric as metric  # noqa: E402

SCHEMA_INPUTS = "claude.item2-inputs/0.3"
SCHEMA_READING = "claude.item2-reading/0.3"
SCHEMA_ACCEPTANCE = "claude.probe-v0.3-acceptance/0.1"
REGISTERED_SEEDS = (20260917, 20260918, 20260919)
REGISTERED_CHECKPOINTS = (("pass_01.pt", 147), ("evidence/main_checkpoint_0294.pt", 294),
                          ("evidence/main_checkpoint_0588.pt", 588), ("evidence/main_checkpoint_0882.pt", 882),
                          ("evidence/main_checkpoint_1176.pt", 1176), ("final.pt", 1470))
REGISTERED_18 = tuple((s, p, u) for s in REGISTERED_SEEDS for p, u in REGISTERED_CHECKPOINTS)
PROVENANCE_FIELDS = ("prereg_sha256_lf", "metric_sha256_lf", "harness_sha256_lf")
LABELS = ["CLAUDE_BUILT_CLAUDE_CHECKED", "EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT"]
Q_J = ("REPAIR_IMPROVES_ANALOGY_6 reads MECHANISM_GATE_OPEN; only the non-analogy H1/H2 view (13 and 40 questions) "
       "may be reported, labelled exploratory (default Q-J, bus message claude-0024)")


class ToolStop(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def provenance_ok(table, frozen):
    prov = table.get("provenance") if type(table) is dict else None
    return type(prov) is dict and all(prov.get(k) == frozen[k] for k in PROVENANCE_FIELDS)


def acceptance_ok(record, frozen):
    return (type(record) is dict and record.get("schema") == SCHEMA_ACCEPTANCE
            and record.get("accepted_by") in ("codex", "owner")
            and all(record.get(k) == frozen[k] for k in PROVENANCE_FIELDS))


def prereg_status():
    text = (HERE / metric.PREREG_NAME).read_text(encoding="utf-8")
    found = re.search(r"\*\*Status:\*\*\s*`([A-Z_]+)`", text)
    return found.group(1) if found else "STATUS_LINE_NOT_FOUND"


def item2(entries, load_table, validation_tables, validation_source, acceptance, *, rules=None, frozen=None):
    """The ITEM2 reading. `load_table(entry) -> (table_or_None, [problems])` is called once per entry, in order."""
    rules = metric.RULES if rules is None else rules
    frozen = metric.frozen_hashes() if frozen is None else frozen
    if type(entries) is not list:
        raise ToolStop("ITEM2_INPUT_ENTRIES")
    registered = {(s, p): u for s, p, u in REGISTERED_18}
    by_key = {}
    for e in entries:
        if type(e) is not dict:
            raise ToolStop("ITEM2_INPUT_ENTRY")
        key = (e.get("model_seed"), e.get("checkpoint_relative_path"))
        if key not in registered:
            raise ToolStop("ITEM2_ENTRY_NOT_REGISTERED:%s/%s" % key)
        if key in by_key:
            raise ToolStop("ITEM2_DUPLICATE_ENTRY:%s/%s" % key)
        by_key[key] = e

    before, after = validation_source
    validation = metric.evaluate_validation(validation_tables, before, after, rules=rules)
    provenance_bad = sorted(case for case, t in validation_tables.items() if not provenance_ok(t, frozen))
    validated = validation["validation"] == "VALIDATION_PASS" and not provenance_bad

    rows, seen_sha = [], {}
    for seed, path, updates in REGISTERED_18:
        row = {"model_seed": seed, "checkpoint_relative_path": path, "main_updates_registered": updates,
               "problems": [], "verdict": None}
        e = by_key.get((seed, path))
        if e is None:
            row["problems"].append("MISSING")
            rows.append(row)
            continue
        row.update(receipt_root=e.get("receipt_root"), checkpoint_sha256=e.get("checkpoint_sha256"),
                   main_updates=e.get("main_updates"))
        if e.get("main_updates") != updates:
            row["problems"].append("UPDATE_COUNT_MISMATCH")
        sha = e.get("checkpoint_sha256")
        if not (type(sha) is str and re.fullmatch(r"[0-9a-f]{64}", sha)):
            row["problems"].append("CHECKPOINT_SHA256_NOT_BOUND")
        elif sha in seen_sha:
            row["problems"].append("CHECKPOINT_SHA256_REUSED:" + seen_sha[sha])
        else:
            seen_sha[sha] = "%d/%s" % (seed, path)
        table, load_problems = load_table(e)
        row["problems"].extend(load_problems)
        if table is not None:
            model = table.get("model") if type(table) is dict else None
            if type(model) is not dict or model.get("checkpoint_sha256") != sha:
                row["problems"].append("CHECKPOINT_SHA256_MISMATCH")
            if type(model) is not dict or model.get("switch") is not True:
                row["problems"].append("SWITCH_NOT_TRUE")
            if not provenance_ok(table, frozen):
                row["problems"].append("PROVENANCE_MISMATCH")
            try:
                result = metric.evaluate(table, rules)
                row["verdict"] = result["verdict"]
                row["summary"] = result["summary"]
                row["M0_delta0_z"] = result["M0_delta0_z"]
            except metric.TableRefused as err:
                row["problems"].append("TABLE_REFUSED:" + err.code)
        elif not load_problems:
            row["problems"].append("SCORE_TABLE_MISSING")
        rows.append(row)

    def passed(r):
        return not r["problems"] and r["verdict"] == metric.PRESENT_BOTH

    if not validated:
        outcome = "ITEM2_NOT_READ_PROBE_NOT_VALIDATED"
    elif any(r["verdict"] == "INVALID_NONDETERMINISTIC" for r in rows):
        outcome = "ITEM2_INVALID"
    elif all(passed(r) for r in rows):
        outcome = "ITEM2_PASS"
    else:
        outcome = "ITEM2_FAIL:" + ",".join(
            "%d/%s=%s" % (r["model_seed"], r["checkpoint_relative_path"], "+".join(r["problems"]) or r["verdict"])
            for r in rows if not passed(r))

    reasons = []
    if outcome != "ITEM2_PASS":
        reasons.append(outcome.split(":")[0])
    if validation["validation"] != "VALIDATION_PASS":
        reasons.append("PROBE_V0_3_VALIDATION_FAILED:" + ",".join(validation["failed"]))
    if provenance_bad:
        reasons.append("VALIDATION_TABLE_PROVENANCE_MISMATCH:" + ",".join(provenance_bad))
    if rules != metric.RULES:
        reasons.append("RULES_NOT_FROZEN")
    accepted = acceptance_ok(acceptance, frozen)
    if not accepted:
        reasons.append("PREREG_V0_3_NOT_ACCEPTED")
    gate = "CLEARED" if not reasons else "MECHANISM_GATE_OPEN"
    for r in rows:
        if not passed(r):
            r["analogy_numbers"] = "ANALOGY_NOT_READ_WIRING_ABSENT"
        else:
            r["analogy_numbers"] = "ANALOGY_MAY_BE_READ" if gate == "CLEARED" else "ANALOGY_NOT_READ_GATE_OPEN"
        r["non_analogy_numbers"] = "READ_AS_REGRESSIONS"
    return {"schema": SCHEMA_READING, "outcome": outcome, "mechanism_gate": gate, "gate_open_reasons": reasons,
            "historical_gate_on_repaired_arm": ("MAY_RUN_FROZEN_EVALUATE_GATES" if gate == "CLEARED"
                                                else "G_LEARN_ON_NOT_READ"),
            "confirmatory_claim": ("MECHANISM_CONDITION_MET_OTHER_CONDITIONS_STILL_REQUIRED" if gate == "CLEARED"
                                   else Q_J),
            "entries": rows, "validation": validation, "validation_table_provenance_mismatch": provenance_bad,
            "acceptance_record_ok": accepted, "prereg_status": prereg_status(), "rules": rules,
            "rules_are_frozen": rules == metric.RULES, "frozen_hashes": frozen,
            "not_covered": ["A5.5 matched start (separate program)", "any analogy accuracy number"],
            "labels": LABELS}


def _load_json(path, code):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ToolStop(code)


def read_from_files(inputs_path):
    inputs_path = pathlib.Path(inputs_path).resolve()
    root = inputs_path.parent
    inputs = _load_json(inputs_path, "ITEM2_INPUTS_UNREADABLE")
    if type(inputs) is not dict or inputs.get("schema") != SCHEMA_INPUTS:
        raise ToolStop("ITEM2_INPUTS_SCHEMA")
    rel = inputs.get("validation_summary")
    if type(rel) is not str:
        raise ToolStop("ITEM2_VALIDATION_SUMMARY_NOT_NAMED")
    summary_path = root / rel
    try:
        summary_raw = summary_path.read_bytes()
    except OSError:
        raise ToolStop("ITEM2_VALIDATION_SUMMARY_UNREADABLE")
    if sha256_bytes(summary_raw) != inputs.get("validation_summary_sha256"):
        raise ToolStop("ITEM2_VALIDATION_SUMMARY_SHA256_MISMATCH")
    summary = json.loads(summary_raw.decode("utf-8"))
    if type(summary) is not dict or type(summary.get("tables")) is not dict or not all(
            type(spec) is dict and type(spec.get("file")) is str for spec in summary["tables"].values()):
        raise ToolStop("ITEM2_VALIDATION_SUMMARY_MALFORMED")
    tables = {}
    for case, spec in sorted(summary["tables"].items()):
        p = summary_path.parent / spec["file"]
        if not p.is_file():
            continue  # read as MISSING by the validation table
        raw = p.read_bytes()
        if sha256_bytes(raw) != spec.get("sha256"):
            raise ToolStop("ITEM2_VALIDATION_TABLE_SHA256_MISMATCH:" + case)
        tables[case] = json.loads(raw.decode("utf-8"))
    source = summary.get("pointer_learner_sha256_lf_before_after") or [None, None]
    acceptance = None
    if inputs.get("acceptance_record"):
        p = root / inputs["acceptance_record"]
        acceptance = _load_json(p, "ITEM2_ACCEPTANCE_RECORD_UNREADABLE") if p.is_file() else None

    def load_table(entry):
        rel_table = entry.get("score_table")
        if type(rel_table) is not str or not (root / rel_table).is_file():
            return None, ["SCORE_TABLE_MISSING"]
        raw = (root / rel_table).read_bytes()
        if sha256_bytes(raw) != entry.get("score_table_sha256"):
            return None, ["SCORE_TABLE_SHA256_MISMATCH"]
        return json.loads(raw.decode("utf-8")), []

    return item2(inputs.get("entries"), load_table, tables, source, acceptance)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    try:
        reading = read_from_files(args.inputs)
    except ToolStop as stop:
        print(json.dumps({"TOOL_STOP": stop.code}))
        return 1
    if args.out:
        out = pathlib.Path(args.out)
        if out.exists():
            print(json.dumps({"TOOL_STOP": "OUTPUT_EXISTS"}))
            return 1
        with open(out, "x", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(reading, indent=1, sort_keys=True))
    print(json.dumps({"outcome": reading["outcome"], "mechanism_gate": reading["mechanism_gate"],
                      "gate_open_reasons": reading["gate_open_reasons"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
