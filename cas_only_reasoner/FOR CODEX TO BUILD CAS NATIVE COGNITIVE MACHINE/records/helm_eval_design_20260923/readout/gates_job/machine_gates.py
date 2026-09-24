"""The gates job's own program. It runs ON the AWS machine, never on the laptop (the frozen grader loads the frozen
course, which ran the laptop out of memory). Standard library only: no torch, no network. CLAUDE_BUILT_CLAUDE_CHECKED.

    python -B machine_gates.py anchors --root DIR
        every bundled file against anchors.json (raw sha256); an unlisted or missing file fails.
    python -B machine_gates.py gates --mode 1|2 --tree DIR --study REL --out DIR
        1. a Linux-path copy of the study: ONLY each job's receipt_dir changes, to <tree>/records/typed_pointer_001/<the
           recorded folder name> (the frozen grader reads receipt_dir literally; the study holds Windows paths);
        2. the frozen grader, unchanged: python -B records/typed_pointer_001/evaluate_gates.py <copy>;
        3. its printed reading, re-serialised canonically (sorted keys, no spaces, one newline: the committed form),
           to gate_reading_fresh.json, and a summary to GATES_READING_SUMMARY.json.
        Mode 1 verdict: GATES_REPRODUCED only if the canonical sha256, the label and H1 per seed all equal the committed
        Helm 2.0 reading; otherwise GATES_NOT_REPRODUCED. Mode 2 verdict: GATES_READ_ON_REPAIRED_ARM when the grader
        printed a non-VOID reading; its label is a historical-rule reading of the ON arm, diagnostic only (prereg A5.3).
    python -B machine_gates.py decide --mode 1|2 --out DIR
        reads EXIT_CODES and the output files and writes GATES_JOB_RESULT.json. Exit 0 only for ALL_PASS.

A failed expectation is a FAILURE with its name; nothing here upgrades it.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = "records/typed_pointer_001/"
SEEDS = ("20260917", "20260918", "20260919")
MODE1_EXPECT = {
    "reading_sha256": "52877c1670132c70dfd82e5e133e4e6ef90d8595a4b49387a6b0bace9f9d10d6",
    "label": "NO_TRANSFER_TO_NEW_WORLDS",
    "h1": {"20260917": [11, 1], "20260918": [12, 0], "20260919": [7, 1]},
}
EXPECTED_EXIT = {
    1: {"gates": "0", "hist_check": "4", "hist_reading": "4", "anchor": "0", "rescore": "0",
        "test_trusted_rescore": "0", "test_historical_compatibility": "0", "test_historical_rescore_rule": "0"},
    2: {"gates": "0", "anchor": "0", "rescore": "0"},
}
MODE1_OUTPUTS = {  # file in out/ -> (field, required value)
    "historical_check_helm2_experimental_r1.json": ("verdict", "HISTORICAL_COMPATIBILITY_OK"),
    "historical_compat_reading_helm2_experimental_0_4r1.json": ("verdict", "HISTORICAL_COMPATIBILITY_OK"),
    "trusted_rescore_reading_helm2_experimental_0_4r1.json": ("verdict", "RESCORE_OK"),
}
MODE2_READING = "trusted_rescore_reading_analogy_on_seeds_0_4r1.json"
CUSTODY = "EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT"


def canonical_bytes(value):
    """The committed form of a gate reading: sorted keys, no spaces, ASCII escapes, one trailing newline."""
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# ---- anchors --------------------------------------------------------------------------------------------------------
def check_anchors(root):
    root = pathlib.Path(root)
    anchors = json.loads((root / "anchors.json").read_bytes())["files"]
    bad = [n for n, row in anchors.items() if not (root / n).is_file() or sha256((root / n).read_bytes()) != row["sha256"]]
    present = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
    extra = [p for p in present if p != "anchors.json" and p not in anchors]
    print("bundled files checked: %d; bad or missing: %d; unlisted: %d" % (len(anchors), len(bad), len(extra)))
    for name in (bad + extra)[:10]:
        print("  %s" % name)
    return 0 if not bad and not extra else 1


# ---- gates ----------------------------------------------------------------------------------------------------------
def map_study(study_bytes, tree):
    """(mapped study, mapping record). Only each job's receipt_dir changes; the folder must exist in the tree."""
    original = json.loads(study_bytes)
    mapped = json.loads(study_bytes)
    rows = []
    for job in mapped["jobs"]:
        recorded = str(job["receipt_dir"])
        name = re.split(r"[\\/]", recorded.rstrip("\\/"))[-1]
        target = (pathlib.Path(tree) / R / name).resolve()
        if not re.fullmatch(r"receipt_[A-Za-z0-9_]+", name) or not target.is_dir():
            raise SystemExit("STUDY_MAPPING_FAILED: seed %s receipt %r not found at %s" % (job.get("model_seed"), name, target))
        job["receipt_dir"] = str(target)
        rows.append({"seed": str(job["model_seed"]), "recorded": recorded, "mapped": str(target)})
    strip = lambda s: {**s, "jobs": [{k: v for k, v in j.items() if k != "receipt_dir"} for j in s["jobs"]]}
    if strip(original) != strip(mapped):
        raise SystemExit("STUDY_MAPPING_FAILED: something other than receipt_dir changed")
    record = {"original_sha256": sha256(study_bytes), "mapped_sha256": sha256(canonical_bytes(mapped)),
              "only_receipt_dir_changed": True, "jobs": rows}
    return mapped, record


def gate_summary(reading):
    """What the readout prints: the label, integrity, and per seed H1 and H2 with b, c, exact p, kinds and worlds."""
    def test(seed, key):
        row = ((reading.get("seeds") or {}).get(seed) or {}).get(key) or {}
        return {"b_wrong_to_right": row.get("wrong_to_right"), "c_right_to_wrong": row.get("right_to_wrong"),
                "p_one_sided": row.get("p_one_sided"), "passed": row.get("passed"), "pairs": row.get("pairs"),
                "improved_kinds": row.get("improved_kinds"), "improved_worlds": len(row.get("improved_worlds") or [])}
    gates = reading.get("gates") or {}
    floor = ((reading.get("population") or {}).get("zero_learning_floor") or {})
    return {
        "label": reading.get("label"), "label_rule": reading.get("label_rule"),
        "integrity_pass": (gates.get("integrity") or {}).get("pass"),
        "void_paths_taken": reading.get("void_paths_taken"),
        "H1_G_LEARN_population": {"pass": (gates.get("G_LEARN_population") or {}).get("pass"),
                                  "per_seed": {s: test(s, "G_LEARN_population") for s in SEEDS}},
        "H2_G_LEARN_all_kinds": {"pass": (gates.get("G_LEARN_all_kinds") or {}).get("pass"),
                                 "per_seed": {s: test(s, "G_LEARN_all_kinds") for s in SEEDS}},
        "report_only": {
            "zero_learning_floor_union_of_population": [floor.get("union_total"), floor.get("population_total")],
            "analogy_questions_correct_by_checkpoint": {
                s: (((reading.get("seeds") or {}).get(s) or {}).get("kind_questions_correct") or {}).get("analogy") for s in SEEDS},
        },
    }


def mode1_verdict(fresh_sha, summary, expect=MODE1_EXPECT):
    reasons = []
    if fresh_sha != expect["reading_sha256"]:
        reasons.append("READING_SHA256_DIFFERS:%s" % fresh_sha)
    if summary["label"] != expect["label"]:
        reasons.append("LABEL_DIFFERS:%s" % summary["label"])
    for seed, (b, c) in expect["h1"].items():
        row = summary["H1_G_LEARN_population"]["per_seed"][seed]
        if [row["b_wrong_to_right"], row["c_right_to_wrong"]] != [b, c]:
            reasons.append("H1_DIFFERS:%s:%s/%s" % (seed, row["b_wrong_to_right"], row["c_right_to_wrong"]))
    return ("GATES_REPRODUCED" if not reasons else "GATES_NOT_REPRODUCED"), reasons


def mode2_verdict(code, summary):
    reasons = []
    if code != 0:
        reasons.append("GRADER_EXIT:%s" % code)
    if summary["label"] in (None, "VOID") or summary["void_paths_taken"]:
        reasons.append("READING_VOID:%s" % summary["void_paths_taken"])
    return ("GATES_READ_ON_REPAIRED_ARM" if not reasons else "GATES_READING_FAILED"), reasons


def run_gates(mode, tree, study_rel, out):
    tree, out = pathlib.Path(tree).resolve(), pathlib.Path(out)
    mapped, mapping = map_study((tree / study_rel).read_bytes(), tree)
    mapped_path = out / "study_mapped_linux.json"
    mapped_path.write_bytes(canonical_bytes(mapped))
    (out / "study_mapping.json").write_text(json.dumps(mapping, indent=1, sort_keys=True), encoding="utf-8")
    proc = subprocess.run([sys.executable, "-B", str(tree / R / "evaluate_gates.py"), str(mapped_path)], cwd=str(tree),
                          capture_output=True, timeout=45 * 60)
    (out / "gate_reading_fresh_raw.json").write_bytes(proc.stdout)
    (out / "evaluate_gates_stderr.txt").write_bytes(proc.stderr)
    try:
        reading = json.loads(proc.stdout)
    except ValueError:
        reading = {}
    fresh = canonical_bytes(reading)
    (out / "gate_reading_fresh.json").write_bytes(fresh)
    summary = gate_summary(reading)
    if mode == 1:
        verdict, reasons = mode1_verdict(sha256(fresh), summary)
        if proc.returncode != 0:
            verdict, reasons = "GATES_NOT_REPRODUCED", reasons + ["GRADER_EXIT:%s" % proc.returncode]
    else:
        verdict, reasons = mode2_verdict(proc.returncode, summary)
    result = {"schema": "claude.gates-job-reading-summary/0.1", "mode": mode, "verdict": verdict, "reasons": reasons,
              "grader_exit": proc.returncode, "fresh_reading_sha256": sha256(fresh), "study_mapping": mapping,
              "summary": summary, "custody": CUSTODY,
              "status_note": ("mode 1: the Helm 2.0 control column, re-derived" if mode == 1 else
                              "mode 2: a historical-rule reading of the ON arm, diagnostic only (A5.3); it licenses no "
                              "structural-analogy transfer and no version promotion; nothing here is compared with Helm 2.0")}
    if mode == 1:
        result["expected"] = MODE1_EXPECT
    (out / "GATES_READING_SUMMARY.json").write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("verdict", "reasons", "grader_exit", "fresh_reading_sha256")}, indent=1))
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0 if verdict in ("GATES_REPRODUCED", "GATES_READ_ON_REPAIRED_ARM") else 1


# ---- decide ---------------------------------------------------------------------------------------------------------
def read_exit_codes(text):
    codes = {}
    for line in text.splitlines():
        key, sep, value = line.strip().partition("=")
        if sep:
            codes[key] = value
    return codes


def _json(path):
    try:
        return json.loads(pathlib.Path(path).read_bytes())
    except (OSError, ValueError):
        return None


def decide(mode, out):
    out = pathlib.Path(out)
    codes = read_exit_codes((out / "EXIT_CODES").read_text(encoding="utf-8") if (out / "EXIT_CODES").is_file() else "")
    failures = ["EXIT:%s=%s (expected %s)" % (k, codes.get(k, "missing"), v) for k, v in EXPECTED_EXIT[mode].items()
                if codes.get(k) != v]
    gates = _json(out / "GATES_READING_SUMMARY.json") or {}
    good_gates = "GATES_REPRODUCED" if mode == 1 else "GATES_READ_ON_REPAIRED_ARM"
    if gates.get("verdict") != good_gates:
        failures.append("GATES:%s %s" % (gates.get("verdict"), gates.get("reasons")))
    rescorer = []
    if mode == 1:
        for name, (field, want) in MODE1_OUTPUTS.items():
            got = (_json(out / name) or {}).get(field)
            if got != want:
                rescorer.append("OUTPUT:%s:%s=%r (expected %s)" % (name, field, got, want))
        label = (_json(out / "trusted_rescore_reading_helm2_experimental_0_4r1.json") or {}).get("label_rederived")
        if label != MODE1_EXPECT["label"]:
            rescorer.append("RESCORE_LABEL:%r" % label)
    else:
        reading = _json(out / MODE2_READING) or {}
        if reading.get("verdict") != "RESCORE_OK":
            rescorer.append("OUTPUT:%s:verdict=%r" % (MODE2_READING, reading.get("verdict")))
        if reading.get("label_rederived") != (gates.get("summary") or {}).get("label"):
            rescorer.append("RESCORE_LABEL_DIFFERS_FROM_GRADER:%r" % reading.get("label_rederived"))
    failures += rescorer
    rescorer_keys = [k for k in EXPECTED_EXIT[mode] if k != "gates"]
    rescorer_ok = not rescorer and all(codes.get(k) == EXPECTED_EXIT[mode][k] for k in rescorer_keys)
    result = {"schema": "claude.gates-job-result/0.1", "mode": mode, "label": "CLAUDE_BUILT_CLAUDE_CHECKED", "custody": CUSTODY,
              "gates_verdict": gates.get("verdict"),
              "rescorer_verdict": ("RESCORER_0_4_AWS_ACCEPTED" if rescorer_ok else "RESCORER_0_4_NOT_ACCEPTED") if mode == 1
              else ("RESCORE_OK_AGREES_WITH_GRADER" if rescorer_ok else "RESCORE_NOT_OK"),
              "overall": "ALL_PASS" if not failures else "FAILED", "failures": failures,
              "exit_codes": codes, "expected_exit_codes": EXPECTED_EXIT[mode], "gates_summary": gates.get("summary")}
    (out / "GATES_JOB_RESULT.json").write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("overall", "gates_verdict", "rescorer_verdict", "failures")}, indent=1))
    return 0 if not failures else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("anchors")
    a.add_argument("--root", required=True)
    g = sub.add_parser("gates")
    g.add_argument("--mode", type=int, choices=(1, 2), required=True)
    g.add_argument("--tree", required=True)
    g.add_argument("--study", required=True)
    g.add_argument("--out", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--mode", type=int, choices=(1, 2), required=True)
    d.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "anchors":
        return check_anchors(args.root)
    if args.command == "gates":
        return run_gates(args.mode, args.tree, args.study, args.out)
    return decide(args.mode, args.out)


if __name__ == "__main__":
    sys.exit(main())
