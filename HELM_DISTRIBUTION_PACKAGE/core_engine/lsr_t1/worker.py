"""LSR-T1 worker. One process, one single-use run. Needs the supervisor's permit.

Order: permit -> source hash check -> sockets blocked -> CODE tests (must pass, else no run) ->
BEHAVIOR tests (the brief's result-bearing tests; run and recorded, never block) -> all families x arms ->
RESULTS_T1.json + SUMMARY.json. Pattern: sdg_bridge_v2/worker.py and fair_data_experiment_v2_sdg/worker.py.
"""
import argparse
import hashlib
import io
import json
import os
from fractions import Fraction
from pathlib import Path
import socket
import sys
import time
import unittest

sys.set_int_max_str_digits(0)  # exact Fractions can exceed 4300 digits (run 1 crashed on this)

HERE = Path(__file__).resolve().parent
PATHS = [str(HERE.parent), r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1",
         r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011"]
HARD_WALL_SECONDS = 300
GUARD_SECONDS = 280
RUN_ID = "LSR_T1_MSI_RUN2"
SCOPE = "LSR_T1"
CODE_TESTS = ("test_halt_carries_gaps", "test_witnessed_ratio_exact", "test_clarification10_plus_never_times",
              "test_machine_reader_agrees")
BEHAVIOR_TESTS = ("test_clean_sdg_adds_zero_recipes", "test_best_of_two_solved_by_cap2_not_single",
                  "test_additive_halts_not_recipe_shaped_without_parallel_production",
                  "test_parallel_production_fits_additive")


def dec4(fr):
    x = abs(fr) * 10000
    q = (2 * x.numerator + x.denominator) // (2 * x.denominator)
    return "%s%d.%04d" % ("-" if fr < 0 else "", q // 10000, q % 10000)


def default(o):
    if isinstance(o, Fraction):
        return {"exact": "%d/%d" % (o.numerator, o.denominator), "decimal4": dec4(o)}
    if isinstance(o, (set, frozenset, tuple)):
        return list(o)
    return str(o)


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=1, allow_nan=False, ensure_ascii=False, default=default), "utf-8")


def expected_sign_line(manifest_sha256):
    return "APPROVE lsr_t1, source " + manifest_sha256[:8] + ", LOCAL_CPU_ONCE on MSI, 300 s cap, no spend."


def activate(path):
    p = json.loads(Path(path).read_text("utf-8-sig"))
    sha = p.get("source_manifest_sha256")
    if (p.get("authorized") is not True or p.get("scope") != SCOPE or p.get("run_id") != RUN_ID
            or p.get("environment") != "LOCAL_CPU_ONCE" or type(sha) is not str or len(sha) != 64
            or p.get("owner_sign_line") != expected_sign_line(sha) or p.get("network_allowed") is not False
            or p.get("max_wall_seconds") != HARD_WALL_SECONDS or p.get("new_spend") != 0
            or p.get("hostname") != "MSI" or socket.gethostname() != "MSI"
            or not 0 < p.get("deadline_epoch", 0) - time.time() <= HARD_WALL_SECONDS):
        raise PermissionError("explicit owner-evidenced one-time MSI permit required")
    expected = HERE / "runs" / RUN_ID / "AUTHORIZATION.json"
    if Path(path).resolve() != expected.resolve():
        raise PermissionError("authorization must be the single-use run artifact")
    with (expected.parent / "CONSUMED.json").open("x", encoding="utf-8") as handle:
        json.dump({"pid": os.getpid(), "utc_epoch": time.time(), "run_id": RUN_ID}, handle)
    return p


def block_network():
    class OfflineSocket(socket.socket):
        def __new__(cls, *args, **kwargs):
            raise PermissionError("lsr_t1 forbids sockets")

    def rejected(*args, **kwargs):
        raise PermissionError("lsr_t1 forbids network")
    socket.socket = OfflineSocket
    socket.create_connection = rejected


def verify_source(permission):
    raw = (HERE / "SOURCE_MANIFEST.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != permission["source_manifest_sha256"]:
        raise PermissionError("approved manifest mismatch")
    for row in json.loads(raw)["files"]:
        if hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise PermissionError("source/data drift: " + row["path"])


def run_tests(names):
    suite = unittest.TestSuite()
    for n in names:
        suite.addTest(unittest.TestLoader().loadTestsFromName("lsr_t1.test_lsr.TestLSR." + n))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    failed = sorted({t.id().split(".")[-1] for t, _ in result.failures + result.errors})
    return {"tests": result.testsRun, "passed": result.testsRun - len(failed), "failures": len(result.failures),
            "errors": len(result.errors), "failed": failed, "ok": result.wasSuccessful(),
            "details": [{"test": t.id().split(".")[-1], "error": e[-800:]} for t, e in result.failures + result.errors]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    start = time.time()
    permission = activate(args.authorization)
    out = Path(args.output)
    verify_source(permission)
    block_network()
    sys.path[:0] = PATHS
    deadline = min(start + GUARD_SECONDS, permission["deadline_epoch"] - 10)
    progress_path = out / "PROGRESS.jsonl"

    def progress(rec):
        rec["t"] = round(time.time() - start, 3)
        with progress_path.open("a", encoding="utf-8") as h:
            h.write(json.dumps(rec) + "\n")
    t0 = time.process_time()
    code = run_tests(CODE_TESTS)
    behavior = run_tests(BEHAVIOR_TESTS)
    tests = {"code_tests_must_pass": code, "behavior_tests_recorded": behavior,
             "cpu_seconds": round(time.process_time() - t0, 3)}
    write(out / "TEST_RESULTS.json", tests)
    progress({"stage": "tests", "code_ok": code["ok"], "behavior_passed": behavior["passed"]})
    if not code["ok"]:
        write(out / "SUMMARY.json", {"status": "CODE_TESTS_FAILED_NO_RUN", "tests": tests})
        sys.exit(3)
    from lsr_t1 import run_t1
    result = run_t1.run_all(deadline, progress)
    result["tests"] = tests
    result["wall_seconds_worker"] = round(time.time() - start, 3)
    result["cpu_seconds_worker"] = round(time.process_time(), 3)
    result["deadline_hit"] = time.time() > deadline
    write(out / "RESULTS_T1.json", result)
    write(out / "SUMMARY.json", {"status": "COMPLETED", "marks": result["marks"], "summary": result["summary"],
                                 "binder_today": result["binder_today"],
                                 "claim3_direct_check_b": {k: v for k, v in result["claim3_direct_check_b"].items()
                                                           if k != "per_omega"},
                                 "shape_library": result["shape_library"], "tests": tests,
                                 "wall_seconds_worker": result["wall_seconds_worker"],
                                 "cpu_seconds_worker": result["cpu_seconds_worker"],
                                 "deadline_hit": result["deadline_hit"]})
    progress({"stage": "done"})


if __name__ == "__main__":
    main()
