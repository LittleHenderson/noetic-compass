"""Read the downloaded HELM-LARGER-QUESTION-PATH-1 T4 results and emit the job reading. Label CLAUDE_BUILT_CLAUDE_CHECKED.

Reads files only: `results/`, `launch_record.json` and `watch_record.json`. It does not re-decide any check. The check
verdicts and the overall verdict are the ones `t4_larger_question_checks.py` wrote; this program only checks that the
files are whole and belong to the launched bundle, then restates them. The first rule that applies wins:
  1 SMOKE_FAILED                the job stopped at stage 0 (its own STATUS says which part failed)
  2 INCOMPLETE                  no summary file, or the summary says it is not complete and names no refusal
  3 RESULT_INTEGRITY_FAILED     the rows file's sha256 differs from the summary's, or the code under test, the
                                torch build or the GPU differ from the launched bundle and the T4 reference
  4 the script's own verdict    INTEGRATION_CHECKS_PASS / _FAIL / _INCOMPLETE, or its refusal (SETUP_REFUSED,
                                GPU_REQUIRED, WALL_LIMIT_REACHED, PREFLIGHT_OVER_WALL_LIMIT)
Nothing here measures Helm's accuracy; any accuracy statement is NOT LICENSED by this job. Writes RESULTS_READING.json.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "results"
SUMMARY = RES / "larger_path_result.json"
ROWS = RES / "larger_path_result.json.rows.jsonl"
TORCH, GPU = "2.11.0+cu128", "T4"


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def main():
    record = load(HERE / "launch_record.json") or {}
    identity = record.get("identity", {})
    status = (RES / "STATUS").read_text(encoding="utf-8").strip() if (RES / "STATUS").is_file() else None
    smoke = load(RES / "stage0_smoke.json")
    summary = load(SUMMARY)
    out = {"schema": "claude.larger-question-t4-reading/0.1", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
           "job_status": status, "source_commit": identity.get("source_commit"),
           "bundle_sha256": record.get("bundle", {}).get("sha256"), "stage0_smoke": smoke, "problems": {},
           "accuracy": "NOT LICENSED: plumbing checks on public fixtures; nothing here measures Helm's accuracy"}
    if summary is not None:
        out["script"] = {key: summary.get(key) for key in ("verdict", "reason", "complete", "requested", "torch",
                                                           "device_name", "wall_seconds", "rows_by_check",
                                                           "course_digest", "fixture_set_digest")}
        out["checks"] = {name: {k: v for k, v in (row or {}).items() if k in ("name", "verdict", "reason", "crash")}
                         for name, row in (summary.get("checks") or {}).items()}
        out["preflight"] = summary.get("preflight")
    # integrity
    if summary is not None:
        if ROWS.is_file():
            observed = hashlib.sha256(ROWS.read_bytes()).hexdigest()
            if observed != summary.get("rows_file_sha256"):
                out["problems"]["rows_file_sha256"] = {"observed": observed, "summary": summary.get("rows_file_sha256")}
        else:
            out["problems"]["rows_file"] = "missing"
        launched = identity.get("eval_paths_lf_sha256", {})
        ran = (summary.get("inputs") or {}).get("eval_paths_lf_sha256", {})
        prefix = "research/CAS_META_2_COMPOSITION/eval_paths/"
        if ran and {prefix + name: digest for name, digest in ran.items()} != launched:
            out["problems"]["code_under_test"] = {"ran": ran, "launched": launched}
        if summary.get("torch") is not None and summary.get("torch") != TORCH:
            out["problems"]["torch"] = summary.get("torch")
        if summary.get("device_name") is not None and GPU not in summary.get("device_name"):
            out["problems"]["device_name"] = summary.get("device_name")
    script_verdict = (summary or {}).get("verdict")
    # Review fb6bc4dd MINOR (coordinator fix): a PASS must be fail-closed on identity. It needs the code hashes, the
    # torch build and the GPU to be PRESENT and equal to the launched values, the job's own STATUS "done", and the
    # check program's own exit code 0. A missing field is a problem, never a silent pass.
    if summary is not None and script_verdict == "INTEGRATION_CHECKS_PASS":
        ran_hashes = (summary.get("inputs") or {}).get("eval_paths_lf_sha256")
        if not ran_hashes or not identity.get("eval_paths_lf_sha256"):
            out["problems"]["code_under_test_missing"] = {"ran": ran_hashes, "launched": identity.get("eval_paths_lf_sha256")}
        if summary.get("torch") != TORCH:
            out["problems"]["torch_missing_or_wrong"] = summary.get("torch")
        if not summary.get("device_name") or GPU not in summary.get("device_name"):
            out["problems"]["device_missing_or_wrong"] = summary.get("device_name")
        if status != "done":
            out["problems"]["job_status_not_done"] = status
        exit_file = RES / "CHECKS_EXIT_CODE"
        exit_code = exit_file.read_text(encoding="utf-8").strip() if exit_file.is_file() else None
        if exit_code != "0":
            out["problems"]["checks_exit_code"] = exit_code
    if status in ("SMOKE_FAILED", "SMOKE_LIST_INPUTS_FAILED") or (smoke is not None and not smoke.get("pass")):
        verdict = "SMOKE_FAILED"
    elif summary is None or script_verdict is None:
        verdict = "INCOMPLETE"
    elif out["problems"]:
        verdict = "RESULT_INTEGRITY_FAILED"
    else:
        verdict = script_verdict
    out["job_verdict"] = verdict
    w = load(HERE / "watch_record.json")
    if w:
        out["watch"] = {k: w.get(k) for k in ("outcome", "job_status", "final_state", "terminated_confirmed",
                                               "volumes_of_this_job_remaining", "minutes_from_launch_to_watch_end",
                                               "cost_upper_bound_usd", "dollar_ceiling")}
    # Route acceptance (Codex bus request codex-0005): a separate, stricter verdict. PASS from the job alone is not
    # enough. It needs complete=true; requested exactly d, c, b, a; each of those checks present with verdict PASS;
    # a passing stage-0 receipt; the launch record's bundle and source pins; the identity checks above clean; and,
    # SEPARATELY, termination and volume-cleanup evidence from the watcher.
    reasons = []
    if verdict != "INTEGRATION_CHECKS_PASS":
        reasons.append("JOB_VERDICT_NOT_PASS:%s" % verdict)
    if summary is None or summary.get("complete") is not True:
        reasons.append("SUMMARY_NOT_COMPLETE")
    if summary is not None and summary.get("requested") != ["d", "c", "b", "a"]:
        reasons.append("REQUESTED_NOT_DCBA:%s" % (summary or {}).get("requested"))
    for name in ("d", "c", "b", "a"):
        row = ((summary or {}).get("checks") or {}).get(name)
        if not row or row.get("verdict") != "PASS":
            reasons.append("CHECK_%s_NOT_PASS:%s" % (name, (row or {}).get("verdict")))
    if smoke is None or smoke.get("pass") is not True:
        reasons.append("STAGE0_RECEIPT_MISSING_OR_NOT_PASS")
    if not record.get("bundle", {}).get("sha256") or not identity.get("source_commit"):
        reasons.append("LAUNCH_PINS_MISSING")
    if out["problems"]:
        reasons.append("IDENTITY_PROBLEMS:%s" % sorted(out["problems"]))
    cleanup_ok = bool(w) and w.get("terminated_confirmed") is True and w.get("volumes_of_this_job_remaining") == []
    out["cleanup_evidence"] = {"accepted": cleanup_ok, "terminated_confirmed": (w or {}).get("terminated_confirmed"),
                               "volumes_of_this_job_remaining": (w or {}).get("volumes_of_this_job_remaining")}
    if not cleanup_ok:
        reasons.append("CLEANUP_EVIDENCE_MISSING_OR_INCOMPLETE")
    out["route_acceptance"] = {"verdict": "ROUTE_ACCEPTED" if not reasons else "ROUTE_NOT_ACCEPTED", "reasons": reasons}
    (HERE / "RESULTS_READING.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                                newline="\n")
    print(json.dumps(out, indent=1, sort_keys=True)[:8000])
    return 0 if verdict == "INTEGRATION_CHECKS_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
