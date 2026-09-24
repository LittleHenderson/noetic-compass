"""Read the downloaded HELM-LARGER-QUESTION-PATH-1 T4 results and emit the job reading. Label CLAUDE_BUILT_CLAUDE_CHECKED.

Reads files only: `results/`, `launch_record.json`, `watch_record.json` and `dry_run_record.json`. It does not re-decide
any check. The check verdicts and the overall verdict are the ones `t4_larger_question_checks.py` wrote (kept unchanged
under "script" and "script_verdict"); this program only checks that the files are whole, belong to the launched bundle
and came from THIS launch, then restates them. The first rule that applies wins:
  1 SMOKE_FAILED                the job stopped at stage 0 (its own STATUS says which part failed)
  2 INCOMPLETE                  no summary file, or the summary says it is not complete and names no refusal
  3 RESULT_INTEGRITY_FAILED     the rows file's sha256 differs from the summary's; the code under test, the torch build
                                or the GPU differ from the launched bundle and the T4 reference; the MACHINE's own
                                records do not bind to the launch record (codex-0007 defect 5): results/identity.json
                                must equal the launch record's identity exactly; results/env.txt must carry exactly the
                                launched bundle sha256 and wheel hashes; job.log must show the machine's own
                                "bundle.tar.gz: OK"; or a JSON file is not a JSON object
  4 the script's own verdict    INTEGRATION_CHECKS_PASS / _FAIL / _INCOMPLETE, or its refusal (SETUP_REFUSED,
                                GPU_REQUIRED, WALL_LIMIT_REACHED, PREFLIGHT_OVER_WALL_LIMIT)

Route acceptance is a separate, stricter verdict (codex-0005, codex-0007, and the builder review of bb942461). It also
requires, besides the job verdict INTEGRATION_CHECKS_PASS and the four checks d/c/b/a PASS:
  * REVIEWED PINS: the launch record's bundle sha256 and source commit equal the reviewed pair (default: the pair the
    reviewed dry run fixed, 2410f269... / e05889ee...; --expect-bundle / --expect-source), and dry_run_record.json, when
    present, agrees;
  * THIS LAUNCH PRODUCED THESE FILES: the watch record's outcome is RESULTS_RECEIVED, it downloaded > 0 files, its
    job_status equals results/STATUS, and the machine's one "JOB START <utc>" line in job.log lies between the launch
    record's launched_utc and the watch record's watch_ended_utc. If env.txt carries "instance_id=<id>" (IMDSv2) it
    must equal the launched instance. With no such line the route is refused, except for the ONE finished job: its
    template (dc05f4af..., which predates the line) AND its instance i-09e14d4afd0e0ebfa, both together (round 2
    MINOR-C: the current job.sh.template still has that sha256, so the template alone would exempt every later launch);
  * CLEANUP of this launch: the watch record's instance id and launch time equal the launch record's; terminated
    confirmed; no volume left.

Exit code (strict): 0 only when the route verdict is ROUTE_ACCEPTED; 3 when the job verdict is PASS but the route is not
accepted; 1 for any other job verdict. Nothing here measures Helm's accuracy; any accuracy statement is NOT LICENSED by
this job. Writes RESULTS_READING.json.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
TORCH, GPU = "2.11.0+cu128", "T4"
WATCH_SCHEMA = "claude.larger-question-t4-watch/0.1"
PREFIX = "research/CAS_META_2_COMPOSITION/eval_paths/"
WHEEL_LINE = re.compile(r"^([0-9a-f]{64})  pkg/(\S+\.whl)$")
JOB_START = re.compile(r"^JOB START (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$")
# The reviewed pair: dry_run_record.json at job commit 3f19c914, admitted by review fb6bc4dd.
REVIEWED_BUNDLE_SHA256 = "2410f269a46d0a8024c7709976557aa1734b7e577cc6cfdb9e9909c53393bd36"
REVIEWED_SOURCE_COMMIT = "e05889eec0f800a9a17b0c39a8d8d37f544b43bf"
# The ONE finished job whose machine script wrote no instance id (round 2 MINOR-C): the exemption is keyed to BOTH its
# template sha256 (launch_record.json machine_script_template_sha256) AND its instance id. The template alone is not
# enough: this folder's CURRENT job.sh.template still has that sha256, so a template-only key would exempt every later
# launch. Any other instance whose env.txt has no instance_id= line is refused. The next launch from this folder needs
# a template that writes instance_id=<IMDSv2 instance-id> (a job-code change with its own review; not made here).
EXEMPT_WITHOUT_INSTANCE_LINE = (("dc05f4afd885d13559e1352e4496cf043e7bd5ed203c62031220c804016fd01e", "i-09e14d4afd0e0ebfa"),)


def load(path, errors):
    """A JSON object, or None. A file that exists but is not a JSON object is named in `errors` (review NOTE c)."""
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        doc = None
    if not isinstance(doc, dict):
        errors.append(path.name)
        return None
    return doc


def text(path):
    return path.read_text(encoding="utf-8") if path.is_file() else None


def utc(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def machine_bindings(res, record, identity, problems, errors):
    """Compare what the MACHINE wrote with the launch record (codex-0007 defect 5)."""
    machine_identity = load(res / "identity.json", errors)
    if machine_identity is None:
        problems["machine_identity_missing_or_not_an_object"] = True
    elif machine_identity != identity:
        keys = sorted(k for k in set(machine_identity) | set(identity) if machine_identity.get(k) != identity.get(k))
        problems["machine_identity_mismatch"] = {k: {"machine": machine_identity.get(k), "launched": identity.get(k)}
                                                 for k in keys}
    launched_bundle = (record.get("bundle") or {}).get("sha256")
    env = text(res / "env.txt")
    if env is None:
        problems["machine_env_missing"] = True
    else:
        lines = [line.split("=", 1)[1].strip() for line in env.splitlines() if line.startswith("bundle_sha256=")]
        if lines != [launched_bundle]:
            problems["machine_bundle_sha256"] = {"machine": lines, "launched": launched_bundle}
        wheels = {m.group(2): m.group(1) for m in map(WHEEL_LINE.match, env.splitlines()) if m}
        launched_wheels = {p: d for p, d in (identity.get("required_inputs_sha256") or {}).items() if p.endswith(".whl")}
        if not launched_wheels or wheels != launched_wheels:
            problems["machine_wheel_sha256"] = {"machine": wheels, "launched": launched_wheels}
    log = text(res / "job.log")
    if log is None or "bundle.tar.gz: OK" not in log.splitlines():
        problems["machine_bundle_check_line_missing"] = True


def provenance(res, record, w, status):
    """Did THIS launch produce the files in results/? (builder review of bb942461, MAJOR 5)."""
    problems, out = [], {}
    if not w:
        return ["WATCH_RECORD_MISSING"], out
    if w.get("outcome") != "RESULTS_RECEIVED":
        problems.append("WATCH_OUTCOME_NOT_RESULTS_RECEIVED:%s" % w.get("outcome"))
    downloaded = w.get("files_downloaded")
    if isinstance(downloaded, bool) or not isinstance(downloaded, int) or downloaded <= 0:
        problems.append("WATCH_FILES_DOWNLOADED_NOT_POSITIVE:%r" % (downloaded,))
    if w.get("job_status") is None or w.get("job_status") != status:
        problems.append("WATCH_JOB_STATUS_NOT_RESULTS_STATUS:%r vs %r" % (w.get("job_status"), status))
    start, end = utc(record.get("launched_utc")), utc(w.get("watch_ended_utc"))
    log = text(res / "job.log") or ""
    starts = [m.group(1) for m in map(JOB_START.match, log.splitlines()) if m]
    out["job_start_utc"], out["window"] = starts, [record.get("launched_utc"), w.get("watch_ended_utc")]
    if len(starts) != 1:
        problems.append("JOB_START_LINE_MISSING_OR_REPEATED:%d" % len(starts))
    elif start is None or end is None or utc(starts[0]) is None or not start <= utc(starts[0]) <= end:
        problems.append("JOB_START_OUTSIDE_THIS_LAUNCH:%s not in [%s, %s]" % (
            starts[0], record.get("launched_utc"), w.get("watch_ended_utc")))
    env = text(res / "env.txt") or ""
    ids = [line.split("=", 1)[1].strip() for line in env.splitlines() if line.startswith("instance_id=")]
    if ids:
        out["machine_instance_id"] = ids
        if ids != [record.get("instance_id")] or not record.get("instance_id"):
            problems.append("MACHINE_INSTANCE_ID_NOT_LAUNCHED_INSTANCE:%s" % ids)
    elif (record.get("machine_script_template_sha256"), record.get("instance_id")) in EXEMPT_WITHOUT_INSTANCE_LINE:
        out["machine_instance_id"] = ("NOT_WRITTEN: template %s predates the IMDSv2 line; this binding rests on the "
                                      "time window and the watch record" % record["machine_script_template_sha256"][:8])
    else:
        problems.append("MACHINE_INSTANCE_ID_MISSING (template %s must write instance_id=)" % (
            str(record.get("machine_script_template_sha256"))[:8]))
    return problems, out


def read(here, expect_bundle=REVIEWED_BUNDLE_SHA256, expect_source=REVIEWED_SOURCE_COMMIT):
    here = pathlib.Path(here)
    res, errors, record_errors = here / "results", [], []          # result files / the folder's own records
    record = load(here / "launch_record.json", record_errors) or {}
    identity = record.get("identity") if isinstance(record.get("identity"), dict) else {}
    status = text(res / "STATUS").strip() if (res / "STATUS").is_file() else None
    smoke = load(res / "stage0_smoke.json", errors)
    summary = load(res / "larger_path_result.json", errors)
    rows = res / "larger_path_result.json.rows.jsonl"
    out = {"schema": "claude.larger-question-t4-reading/0.3", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
           "job_status": status, "source_commit": identity.get("source_commit"), "instance_id": record.get("instance_id"),
           "bundle_sha256": (record.get("bundle") or {}).get("sha256"), "stage0_smoke": smoke, "problems": {},
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
        if rows.is_file():
            observed = hashlib.sha256(rows.read_bytes()).hexdigest()
            if observed != summary.get("rows_file_sha256"):
                out["problems"]["rows_file_sha256"] = {"observed": observed, "summary": summary.get("rows_file_sha256")}
        else:
            out["problems"]["rows_file"] = "missing"
        launched = identity.get("eval_paths_lf_sha256", {})
        ran = (summary.get("inputs") or {}).get("eval_paths_lf_sha256", {})
        if ran and {PREFIX + name: digest for name, digest in ran.items()} != launched:
            out["problems"]["code_under_test"] = {"ran": ran, "launched": launched}
        if summary.get("torch") is not None and summary.get("torch") != TORCH:
            out["problems"]["torch"] = summary.get("torch")
        if summary.get("device_name") is not None and GPU not in summary.get("device_name"):
            out["problems"]["device_name"] = summary.get("device_name")
        machine_bindings(res, record, identity, out["problems"], errors)
    script_verdict = (summary or {}).get("verdict")
    # Review fb6bc4dd MINOR: a PASS must be fail-closed on identity (present AND equal; a missing field is a problem).
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
        exit_code = text(res / "CHECKS_EXIT_CODE")
        if (exit_code or "").strip() != "0":
            out["problems"]["checks_exit_code"] = exit_code
    w = load(here / "watch_record.json", record_errors)
    dry = load(here / "dry_run_record.json", record_errors)
    if errors:
        out["problems"]["json_files_not_objects"] = sorted(set(errors))
    if status in ("SMOKE_FAILED", "SMOKE_LIST_INPUTS_FAILED") or (smoke is not None and not smoke.get("pass")):
        verdict = "SMOKE_FAILED"
    elif summary is None or script_verdict is None:
        verdict = "INCOMPLETE"
    elif out["problems"]:
        verdict = "RESULT_INTEGRITY_FAILED"
    else:
        verdict = script_verdict
    out["script_verdict"] = script_verdict          # the script's own verdict, never rewritten
    out["job_verdict"] = verdict
    if w:
        out["watch"] = {k: w.get(k) for k in ("instance_id", "launched_utc", "watch_ended_utc", "outcome", "job_status",
                                               "files_downloaded", "final_state", "terminated_confirmed",
                                               "volumes_of_this_job_remaining", "minutes_from_launch_to_watch_end",
                                               "cost_upper_bound_usd", "dollar_ceiling")}
    # Route acceptance (codex-0005, bindings codex-0007, builder review of bb942461).
    reasons = []
    if verdict != "INTEGRATION_CHECKS_PASS":
        reasons.append("JOB_VERDICT_NOT_PASS:%s" % verdict)
    if summary is None or summary.get("complete") is not True:
        reasons.append("SUMMARY_NOT_COMPLETE")
    if summary is not None and summary.get("requested") != ["d", "c", "b", "a"]:
        reasons.append("REQUESTED_NOT_DCBA:%s" % summary.get("requested"))
    for name in ("d", "c", "b", "a"):
        row = ((summary or {}).get("checks") or {}).get(name)
        if not row or row.get("verdict") != "PASS":
            reasons.append("CHECK_%s_NOT_PASS:%s" % (name, (row or {}).get("verdict")))
    if smoke is None or smoke.get("pass") is not True:
        reasons.append("STAGE0_RECEIPT_MISSING_OR_NOT_PASS")
    if not (record.get("bundle") or {}).get("sha256") or not identity.get("source_commit") or not record.get("instance_id"):
        reasons.append("LAUNCH_PINS_MISSING")
    if out["problems"]:
        reasons.append("IDENTITY_PROBLEMS:%s" % sorted(out["problems"]))
    if record_errors:
        reasons.append("RECORD_NOT_A_JSON_OBJECT:%s" % ",".join(sorted(set(record_errors))))
    pins = []
    if (record.get("bundle") or {}).get("sha256") != expect_bundle:
        pins.append("LAUNCH_BUNDLE_NOT_REVIEWED:%s" % (record.get("bundle") or {}).get("sha256"))
    if identity.get("source_commit") != expect_source:
        pins.append("LAUNCH_SOURCE_NOT_REVIEWED:%s" % identity.get("source_commit"))
    if dry is not None and ((dry.get("bundle") or {}).get("sha256") != expect_bundle
                            or (dry.get("identity") or {}).get("source_commit") != expect_source):
        pins.append("DRY_RUN_RECORD_DISAGREES_WITH_THE_REVIEWED_PINS")
    out["reviewed_pins"] = {"expected_bundle_sha256": expect_bundle, "expected_source_commit": expect_source,
                            "dry_run_record": "present" if dry is not None else "absent", "problems": pins}
    reasons.extend(pins)
    origin, detail = provenance(res, record, w, status)
    out["provenance"] = dict(detail, accepted=not origin, problems=origin)
    if origin:
        reasons.append("RESULTS_NOT_BOUND_TO_THIS_LAUNCH:%s" % ",".join(origin))
    cleanup = []
    if not w:
        cleanup.append("WATCH_RECORD_MISSING")
    else:
        if w.get("schema") != WATCH_SCHEMA:
            cleanup.append("WATCH_SCHEMA:%s" % w.get("schema"))
        if not record.get("instance_id") or w.get("instance_id") != record.get("instance_id"):
            cleanup.append("WATCH_INSTANCE_NOT_LAUNCHED_INSTANCE:%s" % w.get("instance_id"))
        if not record.get("launched_utc") or w.get("launched_utc") != record.get("launched_utc"):
            cleanup.append("WATCH_LAUNCH_TIME_NOT_LAUNCH_RECORD:%s" % w.get("launched_utc"))
        if w.get("terminated_confirmed") is not True or w.get("final_state") not in ("terminated", "gone"):
            cleanup.append("NOT_CONFIRMED_TERMINATED")
        if w.get("volumes_of_this_job_remaining") != []:
            cleanup.append("VOLUMES_LEFT_OR_UNKNOWN")
    out["cleanup_evidence"] = {"accepted": not cleanup, "problems": cleanup,
                               "bound_to_instance": (w or {}).get("instance_id"),
                               "terminated_confirmed": (w or {}).get("terminated_confirmed"),
                               "volumes_of_this_job_remaining": (w or {}).get("volumes_of_this_job_remaining")}
    if cleanup:
        reasons.append("CLEANUP_EVIDENCE_NOT_ACCEPTED:%s" % ",".join(cleanup))
    out["route_acceptance"] = {"verdict": "ROUTE_ACCEPTED" if not reasons else "ROUTE_NOT_ACCEPTED", "reasons": reasons}
    code = 1 if verdict != "INTEGRATION_CHECKS_PASS" else (0 if not reasons else 3)
    out["exit_code"] = {"value": code, "rule": "0 only for ROUTE_ACCEPTED; 3 job PASS but route not accepted; "
                                               "1 any other job verdict"}
    return out, code


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read the T4 larger-question results (strict exit).")
    parser.add_argument("--dir", default=str(HERE), help="job folder (default: this folder)")
    parser.add_argument("--expect-bundle", default=REVIEWED_BUNDLE_SHA256, help="the reviewed bundle sha256")
    parser.add_argument("--expect-source", default=REVIEWED_SOURCE_COMMIT, help="the reviewed source commit")
    parser.add_argument("--no-write", action="store_true", help="do not write RESULTS_READING.json")
    args = parser.parse_args(argv)
    out, code = read(args.dir, expect_bundle=args.expect_bundle, expect_source=args.expect_source)
    if not args.no_write:
        (pathlib.Path(args.dir) / "RESULTS_READING.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n",
                                                                     encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1, sort_keys=True)[:8000])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
