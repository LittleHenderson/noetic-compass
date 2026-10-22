"""LM-T1c worker (copied from worker_t1b.py). One process, one single-use run, needs the supervisor's permit.

Order: permit -> source hash check -> sockets blocked -> unit-test gate -> hand-set freeze check -> M1, M2, M7 on
the 576 SDG recipe seeds -> M6 coverage ledger (+ side universes) -> M3 hand set (+ LOOKUP) -> M4, M5, M5b on the
SDG English (streamed) -> READING.json (deterministic reading of the frozen marks) -> SUMMARY.json.
Permit and network block follow sdg_bridge_v2/worker.py.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
BRIDGE_ROOT = Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011")
LACUNA_ROOT = Path(r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1")
HARD_WALL_SECONDS = 300
RUN_ID = "LM_T1C_MSI_ONCE"
SCOPE = "LM_T1C"


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False, default=str), "utf-8")


def expected_sign_line(sha):
    return "APPROVE lm_t1c, source " + sha[:8] + ", LOCAL_CPU_ONCE on MSI, 300 s cap, no spend."


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
            raise PermissionError("lm_t1c forbids sockets")

    def rejected(*args, **kwargs):
        raise PermissionError("lm_t1c forbids network")
    socket.socket = OfflineSocket
    socket.create_connection = rejected


def verify_source(permission):
    raw = (HERE / "SOURCE_MANIFEST_T1C.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != permission["source_manifest_sha256"]:
        raise PermissionError("approved manifest mismatch")
    for row in json.loads(raw)["files"]:
        if hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise PermissionError("source/data drift: " + row["path"])


def run_tests():
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestLoader().loadTestsFromNames(["test_lm_t1c", "test_lm_t1b", "test_lm_t1"]))
    return {"tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "ok": result.wasSuccessful(), "details": [str(t) for t, _ in result.failures + result.errors]}


def main():
    t0, c0 = time.perf_counter(), time.process_time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--authorization", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    for p in (HERE, LACUNA_ROOT, BRIDGE_ROOT):
        sys.path.insert(0, str(p))
    permission = activate(args.authorization)
    out = Path(args.output).resolve()
    if out != (HERE / "runs" / RUN_ID).resolve():
        raise PermissionError("isolated run output required")
    verify_source(permission)
    block_network()
    tests = run_tests()
    write(out / "TEST_RESULTS.json", tests)
    if not tests["ok"]:
        write(out / "ERROR.json", {"status": "ABORTED_TEST_GATE"})
        return 2
    import scoring
    import t1c
    fz = json.loads((HERE / "handset" / "HAND_SET_v0_1c_R_DOTTED4_FREEZE.json").read_text("utf-8"))
    raw = (HERE / "handset" / "HAND_SET_v0_1c_R_DOTTED4.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != fz["sha256"]:
        write(out / "ERROR.json", {"status": "ABORTED_HAND_SET_DRIFT"})
        return 3
    r4 = json.loads(raw.decode("utf-8"))["items"]
    h64 = json.loads((HERE / "handset" / "HAND_SET_v0_1.json").read_text("utf-8"))["items"]
    h16 = json.loads((HERE / "handset" / "HAND_SET_v0_1b_ADD16.json").read_text("utf-8"))["items"]
    c1, c3 = t1c.c1_c3()
    c2 = t1c.c2(r4)
    c4 = t1c.c4()
    c5 = t1c.c5([r["content"] for r in scoring.load_recipes()], h64, h16)
    for name, val in (("C1_DOTTED_LEDGER.json", c1), ("C2_HAND_R4.json", c2), ("C3_SAME_NESTING.json", c3),
                      ("C4_REFUSALS.json", c4), ("C5_NO_DAMAGE.json", c5)):
        write(out / name, val)
    hard = {"C1": c1["pass"], "C2": c2["pass"], "C3": c3["pass"], "C4": c4["pass"], "C5": c5["pass"]}
    reading = {"hard_marks": hard, "LM_T1c_core": "PASS" if all(hard.values()) else "FAILURE",
               "failed_hard_marks": [k for k, v in hard.items() if not v],
               "ruling": "CAS Φ / Definition 26.1 (outer last) both . and : (OWNER_RULING_N1_NESTING_DIRECTION_20261014.md)",
               "claim_ceiling": "ENGINEERED-NOT-VALIDATED; FORM only"}
    write(out / "READING.json", reading)
    summary = {"run_id": RUN_ID, "reading": reading, "tests": {k: tests[k] for k in ("tests", "failures", "errors", "ok")},
               "C1": c1, "C2": {k: v for k, v in c2.items() if k != "rows"}, "C3": c3, "C4": c4, "C5": c5,
               "timings_seconds": {"worker_wall_total": time.perf_counter() - t0, "worker_cpu_total": time.process_time() - c0}}
    write(out / "SUMMARY.json", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
