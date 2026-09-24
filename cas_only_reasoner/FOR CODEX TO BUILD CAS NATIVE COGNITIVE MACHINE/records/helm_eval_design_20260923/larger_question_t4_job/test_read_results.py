"""Small pure-Python tests for read_results.py (Codex review codex-0007, defect 5). Label CLAUDE_BUILT_CLAUDE_CHECKED.

Synthetic job folders in a temporary directory; the real results/ folder is never touched.
Every identity binding has a mismatch-negative case. Run: python -B test_read_results.py (also collectable by pytest)
"""
import atexit
import copy
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import read_results as rr  # noqa: E402

WHL = "research/dist/cas_neural_cjt-0.2.0-py3-none-any.whl"
EVAL = {"t4_larger_question_checks.py": "1" * 64, "__init__.py": "2" * 64}
IDENTITY = {"schema": "claude.larger-question-t4-bundle-identity/0.1", "source_commit": "e" * 40,
            "script": rr.PREFIX + "t4_larger_question_checks.py",
            "eval_paths_lf_sha256": {rr.PREFIX + k: v for k, v in EVAL.items()},
            "required_inputs_sha256": {WHL: "6" * 64, "records/x.json": "7" * 64}}
RECORD = {"instance_id": "i-job", "launched_utc": "2026-09-24T05:53:38Z", "bundle": {"sha256": "b" * 64},
          "identity": IDENTITY}
WATCH = {"schema": rr.WATCH_SCHEMA, "instance_id": "i-job", "launched_utc": "2026-09-24T05:53:38Z",
         "outcome": "RESULTS_RECEIVED", "job_status": "done", "final_state": "terminated", "terminated_confirmed": True,
         "volumes_of_this_job_remaining": [], "cost_upper_bound_usd": 0.4489, "dollar_ceiling": 3.0}
ROWS = b'{"row": 1}\n{"row": 2}\n'


def job(edit=None):
    """A complete, clean synthetic job folder; edit(files) may change any file before it is written."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="rr_test_"))
    atexit.register(shutil.rmtree, tmp, True)
    files = {
        "launch_record.json": copy.deepcopy(RECORD),
        "watch_record.json": copy.deepcopy(WATCH),
        "results/identity.json": copy.deepcopy(IDENTITY),
        "results/STATUS": "done\n",
        "results/CHECKS_EXIT_CODE": "0\n",
        "results/stage0_smoke.json": {"pass": True, "torch": rr.TORCH, "device_name": "Tesla T4", "problems": []},
        "results/larger_path_result.json": {
            "verdict": "INTEGRATION_CHECKS_PASS", "reason": None, "complete": True, "requested": ["d", "c", "b", "a"],
            "torch": rr.TORCH, "device_name": "Tesla T4", "rows_file_sha256": hashlib.sha256(ROWS).hexdigest(),
            "inputs": {"eval_paths_lf_sha256": dict(EVAL)},
            "checks": {n: {"name": n.upper(), "verdict": "PASS"} for n in ("d", "c", "b", "a")}},
        "results/larger_path_result.json.rows.jsonl": ROWS,
        "results/env.txt": "Python 3.14.7\nbundle_sha256=%s\n%s  pkg/%s\nnumpy==2.5.2\n" % ("b" * 64, "6" * 64, WHL),
        "results/job.log": "JOB START\nbundle.tar.gz: OK\nJOB FINISH\n",
    }
    if edit:
        edit(files)
    (tmp / "results").mkdir()
    for name, body in files.items():
        if body is None:
            continue
        raw = body if isinstance(body, bytes) else body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
        (tmp / name).write_bytes(raw)
    return tmp


def reading(edit=None):
    return rr.read(job(edit))


def integrity_failed(edit, key):
    out, code = reading(edit)
    assert out["job_verdict"] == "RESULT_INTEGRITY_FAILED", out["job_verdict"]
    assert key in out["problems"], (key, out["problems"])
    assert out["script_verdict"] == "INTEGRATION_CHECKS_PASS"          # the script's own verdict is preserved
    assert out["route_acceptance"]["verdict"] == "ROUTE_NOT_ACCEPTED" and code == 1, (out["route_acceptance"], code)


def route_refused(edit, needle):
    out, code = reading(edit)
    assert out["job_verdict"] == "INTEGRATION_CHECKS_PASS", out["job_verdict"]   # the job itself still passes
    assert out["route_acceptance"]["verdict"] == "ROUTE_NOT_ACCEPTED", out["route_acceptance"]
    assert any(needle in r for r in out["route_acceptance"]["reasons"]), (needle, out["route_acceptance"])
    assert code == 3, code                                                     # strict exit: not 0


def test_clean_job_is_route_accepted_exit_0():
    out, code = reading()
    assert out["problems"] == {} and out["job_verdict"] == "INTEGRATION_CHECKS_PASS", out["problems"]
    assert out["route_acceptance"] == {"verdict": "ROUTE_ACCEPTED", "reasons": []} and code == 0
    assert out["cleanup_evidence"]["bound_to_instance"] == "i-job"


# ------------------------------------------------------------------- machine identity.json vs launch record
def test_machine_identity_source_commit_mismatch():
    integrity_failed(lambda f: f["results/identity.json"].update(source_commit="f" * 40), "machine_identity_mismatch")


def test_machine_identity_eval_paths_mismatch():
    def edit(f):
        f["results/identity.json"]["eval_paths_lf_sha256"][rr.PREFIX + "__init__.py"] = "9" * 64
    integrity_failed(edit, "machine_identity_mismatch")


def test_machine_identity_required_input_mismatch():
    def edit(f):
        f["results/identity.json"]["required_inputs_sha256"]["records/x.json"] = "8" * 64
    integrity_failed(edit, "machine_identity_mismatch")


def test_machine_identity_missing():
    integrity_failed(lambda f: f.update({"results/identity.json": None}), "machine_identity_missing")


# ------------------------------------------------------------------------------ bundle sha256 and wheels
def test_machine_bundle_sha256_mismatch():
    integrity_failed(lambda f: f.update({"results/env.txt": f["results/env.txt"].replace("b" * 64, "c" * 64)}),
                     "machine_bundle_sha256")


def test_machine_bundle_sha256_line_missing_or_repeated():
    integrity_failed(lambda f: f.update({"results/env.txt": "\n".join(
        l for l in f["results/env.txt"].splitlines() if not l.startswith("bundle_sha256="))}), "machine_bundle_sha256")
    integrity_failed(lambda f: f.update({"results/env.txt": f["results/env.txt"] + "bundle_sha256=%s\n" % ("c" * 64)}),
                     "machine_bundle_sha256")


def test_machine_env_missing():
    integrity_failed(lambda f: f.update({"results/env.txt": None}), "machine_env_missing")


def test_machine_wheel_hash_mismatch():
    integrity_failed(lambda f: f.update({"results/env.txt": f["results/env.txt"].replace("6" * 64, "5" * 64)}),
                     "machine_wheel_sha256")


def test_machine_bundle_check_line_missing():
    integrity_failed(lambda f: f.update({"results/job.log": "JOB START\nJOB FINISH\n"}), "machine_bundle_check_line_missing")


def test_launch_record_bundle_differs_from_machine():
    integrity_failed(lambda f: f["launch_record.json"]["bundle"].update(sha256="d" * 64), "machine_bundle_sha256")


def test_launch_record_source_commit_differs_from_machine():
    integrity_failed(lambda f: f["launch_record.json"]["identity"].update(source_commit="0" * 40),
                     "machine_identity_mismatch")


def test_code_under_test_mismatch_still_caught():
    integrity_failed(lambda f: f["results/larger_path_result.json"]["inputs"]["eval_paths_lf_sha256"].update(
        {"__init__.py": "3" * 64}), "code_under_test")


# ---------------------------------------------------------------------------- cleanup bound to the launch
def test_cleanup_from_an_unrelated_instance_is_refused():
    route_refused(lambda f: f["watch_record.json"].update(instance_id="i-other"), "WATCH_INSTANCE_NOT_LAUNCHED_INSTANCE")


def test_cleanup_with_a_different_launch_time_is_refused():
    route_refused(lambda f: f["watch_record.json"].update(launched_utc="2026-09-23T01:00:00Z"),
                  "WATCH_LAUNCH_TIME_NOT_LAUNCH_RECORD")


def test_cleanup_schema_volumes_termination_missing():
    route_refused(lambda f: f["watch_record.json"].update(schema="other/0.1"), "WATCH_SCHEMA")
    route_refused(lambda f: f["watch_record.json"].update(volumes_of_this_job_remaining="unknown:ClientError"),
                  "VOLUMES_LEFT_OR_UNKNOWN")
    route_refused(lambda f: f["watch_record.json"].update(terminated_confirmed=False), "NOT_CONFIRMED_TERMINATED")
    route_refused(lambda f: f.update({"watch_record.json": None}), "WATCH_RECORD_MISSING")


def test_launch_record_without_instance_id_refuses_route():
    def edit(f):
        del f["launch_record.json"]["instance_id"]
    route_refused(edit, "LAUNCH_PINS_MISSING")


# ------------------------------------------------------------------------------- script verdict preserved
def test_script_fail_is_preserved_and_exit_1():
    def edit(f):
        f["results/larger_path_result.json"]["verdict"] = "INTEGRATION_CHECKS_FAIL"
        f["results/larger_path_result.json"]["checks"]["b"]["verdict"] = "FAIL"
    out, code = reading(edit)
    assert out["script_verdict"] == out["job_verdict"] == "INTEGRATION_CHECKS_FAIL" and code == 1
    assert out["script"]["verdict"] == "INTEGRATION_CHECKS_FAIL" and out["checks"]["b"]["verdict"] == "FAIL"


def test_route_requirements_unchanged():
    route_refused(lambda f: f["results/larger_path_result.json"].update(requested=["d", "c"]), "REQUESTED_NOT_DCBA")
    route_refused(lambda f: f["results/larger_path_result.json"].update(complete=False), "SUMMARY_NOT_COMPLETE")


def test_main_strict_exit_codes_and_no_write():
    folder = job(lambda f: f["watch_record.json"].update(instance_id="i-other"))
    assert rr.main(["--dir", str(folder), "--no-write"]) == 3
    assert not (folder / "RESULTS_READING.json").exists()
    assert rr.main(["--dir", str(job()), "--no-write"]) == 0


def run_all():
    import contextlib
    import io
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                fn()
            print("PASS", name)
        except Exception as error:
            failed += 1
            print("FAIL", name, type(error).__name__, str(error)[:600])
    print("%d passed, %d failed" % (len(tests) - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_all())
