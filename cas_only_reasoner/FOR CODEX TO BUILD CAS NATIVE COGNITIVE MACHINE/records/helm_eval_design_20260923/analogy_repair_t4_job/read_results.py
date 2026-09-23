"""Emit the HELM-ANALOGY-REPAIR-1 item-1 verdict from the downloaded results, by the rules of prereg amendment A4.3.

Reads files only (results/, launch_record.json, and the retained T4 reference in ../aws_probe_job/results/). Checks,
in order, and the first that applies wins:
  1 INCOMPLETE  2 SWITCH_TESTS_FAILED / SWITCH_NOT_READ_ONLY  3 REFERENCE_NOT_REPRODUCIBLE_ON_T4
  4 OFF_NOT_PRESERVED  5 OFF_STRUCTURE_CHANGED  6 OFF_PROBE_NOT_ABSENT  7 OFF_PRESERVED_ON_T4 (pass)
The fresh-ON reading is reported as FRESH_ON_REPORT_ONLY and never enters the verdict. Every outcome carries the
label CLAUDE_BUILT_CLAUDE_CHECKED. Writes RESULTS_READING.json and prints it.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "results"
REF = HERE.parent / "aws_probe_job" / "results"
SEEDS = ("20260917", "20260918", "20260919")
PARAMS_OFF = 174303
ABSENT = "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT"


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def rows(prefix):
    out, complete = {}, True
    for s in SEEDS:
        d = load(RES / (prefix % s))
        if d is None or not d.get("complete"):
            complete = False
        for r in (d or {}).get("results", []):
            out[r["label"]] = r
    return out, complete


def main():
    record = load(HERE / "launch_record.json") or {}
    status = (RES / "STATUS").read_text().strip() if (RES / "STATUS").is_file() else None
    out = {"schema": "claude.analogy-repair-t4-reading/0.1", "label": "CLAUDE_BUILT_CLAUDE_CHECKED", "status": status,
           "repaired_commit": record.get("identity", {}).get("repaired_commit"), "problems": {}}
    # stage 0
    junit = RES / "stage0_junit.xml"
    if junit.is_file():
        suite = ET.parse(junit).getroot()
        suites = [suite] if suite.tag == "testsuite" else list(suite)
        out["stage0_pytest"] = {k: sum(int(x.get(k, 0)) for x in suites) for k in ("tests", "failures", "errors", "skipped")}
    ro = load(RES / "stage0_read_only_check.json")
    out["stage0_read_only_check"] = None if ro is None else {"pass": ro["pass"], "results": ro["results"]}
    control, c_ok = rows("preservation_control_20208c92_T4_seed%s.json")
    off, o_ok = rows("preservation_OFF_T4_seed%s.json")
    reference, _ = rows_ref = ({}, True)
    for s in SEEDS:
        d = load(REF / ("preservation_reference_20208c92_T4_seed%s.json" % s))
        for r in (d or {}).get("results", []):
            reference[r["label"]] = r
    probes = {}
    p_ok = True
    for s in SEEDS:
        d = load(RES / ("probe_OFF_T4_seed%s.json" % s))
        if d is None or not d.get("complete"):
            p_ok = False
        for r in (d or {}).get("results", []):
            probes[r["label"]] = r
    labels = sorted(reference)
    out["models"] = labels
    table = {}
    for m in labels:
        c, o, ref, pr = control.get(m), off.get(m), reference[m], probes.get(m)
        table[m] = {"reference_digest": ref["overall_digest"],
                    "control_digest": c and c["overall_digest"], "off_digest": o and o["overall_digest"],
                    "control_equals_reference": bool(c) and c["overall_digest"] == ref["overall_digest"],
                    "off_equals_control": bool(c and o) and o["overall_digest"] == c["overall_digest"],
                    "off_parameter_count": o and o["parameter_count"],
                    "off_keys_shapes_equal_control": bool(c and o) and o["state_keys_shapes_digest"] == c["state_keys_shapes_digest"],
                    "checkpoint_sha256_ok": (o is not None and (o["checkpoint_sha256"] is None and ref["checkpoint_sha256"] is None
                                                                or o["checkpoint_sha256"] == ref["checkpoint_sha256"])),
                    "off_probe_verdict": pr and pr["verdict"], "off_probe_switch": pr and pr.get("switch")}
    out["per_model"] = table
    complete = (status is not None and c_ok and o_ok and p_ok and len(labels) == 9
                and all(control.get(m) and off.get(m) and probes.get(m) for m in labels))
    stage0 = out.get("stage0_pytest")
    if status in ("SWITCH_TESTS_FAILED",) or (stage0 and (stage0["failures"] or stage0["errors"])):
        verdict = "SWITCH_TESTS_FAILED"
    elif status == "SWITCH_NOT_READ_ONLY" or (ro is not None and not ro["pass"]):
        verdict = "SWITCH_NOT_READ_ONLY"
    elif not complete or stage0 is None or ro is None:
        verdict = "INCOMPLETE"
    elif not all(t["control_equals_reference"] for t in table.values()):
        verdict = "REFERENCE_NOT_REPRODUCIBLE_ON_T4"
        out["problems"]["control_differs_from_reference"] = [m for m, t in table.items() if not t["control_equals_reference"]]
    elif not all(t["off_equals_control"] for t in table.values()):
        verdict = "OFF_NOT_PRESERVED"
        out["problems"]["off_differs_from_control"] = [m for m, t in table.items() if not t["off_equals_control"]]
    elif not all(t["off_parameter_count"] == PARAMS_OFF and t["off_keys_shapes_equal_control"] and t["checkpoint_sha256_ok"] for t in table.values()):
        verdict = "OFF_STRUCTURE_CHANGED"
    elif not all(t["off_probe_verdict"] == ABSENT for t in table.values()):
        verdict = "OFF_PROBE_NOT_ABSENT"
    else:
        verdict = "OFF_PRESERVED_ON_T4"
    # INCOMPLETE takes precedence over everything except a stage-0 stop, which ends the job by design (A4.1)
    out["item1_verdict"] = verdict
    fresh = load(RES / "probe_ON_fresh_T4.json")
    out["fresh_on"] = {"label": "FRESH_ON_REPORT_ONLY", "complete": fresh and fresh.get("complete"),
                       "readings": [{"label": r["label"], "verdict": r["verdict"], "switch": r.get("switch"), "summary": r.get("summary")}
                                    for r in (fresh or {}).get("results", [])],
                       "note": "no pass rule; never satisfies item 2 (trained ON); item 3's REACHABILITY label does not apply (A4.4)"}
    out["item2_trained_on"] = "OPEN: no trained switch-ON checkpoint exists; needs a separate owner-approved training job"
    w = load(HERE / "watch_record.json")
    if w:
        out["watch"] = {k: w.get(k) for k in ("outcome", "job_status", "final_state", "terminated_confirmed",
                                               "volumes_of_this_job_remaining", "minutes_from_launch_to_watch_end", "cost_upper_bound_usd")}
    (HERE / "RESULTS_READING.json").write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1, sort_keys=True)[:8000])


if __name__ == "__main__":
    main()
