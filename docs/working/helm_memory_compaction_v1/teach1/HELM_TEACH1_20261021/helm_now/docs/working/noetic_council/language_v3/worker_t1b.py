"""LM-T1b worker (copied from worker.py). One process, one single-use run, needs the supervisor's permit.

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
RUN_ID = "LM_T1B_MSI_ONCE"
SCOPE = "LM_T1B"


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False, default=str), "utf-8")


def expected_sign_line(sha):
    return "APPROVE lm_t1b, source " + sha[:8] + ", LOCAL_CPU_ONCE on MSI, 300 s cap, no spend."


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
            raise PermissionError("lm_t1b forbids sockets")

    def rejected(*args, **kwargs):
        raise PermissionError("lm_t1b forbids network")
    socket.socket = OfflineSocket
    socket.create_connection = rejected


def verify_source(permission):
    raw = (HERE / "SOURCE_MANIFEST_T1B.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != permission["source_manifest_sha256"]:
        raise PermissionError("approved manifest mismatch")
    for row in json.loads(raw)["files"]:
        if hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise PermissionError("source/data drift: " + row["path"])


def run_tests():
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestLoader().loadTestsFromNames(["test_lm_t1b", "test_lm_t1"]))
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
    timings = {}
    t = time.perf_counter()
    tests = run_tests()
    timings["tests"] = time.perf_counter() - t
    write(out / "TEST_RESULTS.json", tests)
    if not tests["ok"]:
        write(out / "ERROR.json", {"status": "ABORTED_TEST_GATE"})
        return 2
    import scoring
    import t1b
    import cas_ast
    import cce_v01b as b
    fz = json.loads((HERE / "handset" / "HAND_SET_v0_1b_ADD16_FREEZE.json").read_text("utf-8"))
    raw = (HERE / "handset" / "HAND_SET_v0_1b_ADD16.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != fz["sha256"]:
        write(out / "ERROR.json", {"status": "ABORTED_HAND_SET_DRIFT"})
        return 3
    add16 = json.loads(raw.decode("utf-8"))["items"]
    hand64 = json.loads((HERE / "handset" / "HAND_SET_v0_1.json").read_text("utf-8"))["items"]
    comp_path = Path(cas_ast.COMPILER_ROOT, "api", "notation", "compiler.py")
    if hashlib.sha256(comp_path.read_bytes()).hexdigest() != cas_ast.COMPILER_SHA256:
        write(out / "ERROR.json", {"status": "ABORTED_COMPILER_DRIFT"})
        return 4
    t = time.perf_counter()
    r1, c1 = t1b.b1()
    r2, c2 = t1b.b2()
    r3 = t1b.b3(add16)
    timings["b1_b2_b3"] = time.perf_counter() - t
    t = time.perf_counter()
    recipes = scoring.load_recipes()
    r5 = t1b.b5([r["content"] for r in recipes], hand64)
    r7 = t1b.b7(recipes)
    r6 = t1b.b6(t1b.load_examples())
    book_contents = [b.parse(row["sentence"]) for row in r6["rows"] if row.get("sentence") and row.get("cce_round_trip")]
    hand_contents = [b.parse(it["text"]) for row, it in zip(r3["rows"], add16) if row["ok"] and "content" in it["expect"]]
    r4 = t1b.b4(c1 + c2 + hand_contents + book_contents)
    timings["b4_b5_b6_b7"] = time.perf_counter() - t
    for name, val in (("B1_NEST.json", r1), ("B2_META.json", r2), ("B3_HAND_ADD16.json", r3), ("B4_COMPILER.json", r4),
                      ("B5_NO_DAMAGE.json", r5), ("B6_BOOK_EXAMPLES.json", r6), ("B7_RECIPE_GRAMMAR.json", r7)):
        write(out / name, val)
    hard = {"B1": r1["pass"], "B2": r2["pass"], "B3": r3["pass"], "B4": r4["pass"], "B5": r5["pass"]}
    reading = {"hard_marks": hard, "LM_T1b_core": "PASS" if all(hard.values()) else "FAILURE",
               "failed_hard_marks": [k for k, v in hard.items() if not v],
               "B6_book_examples_exact_of_accepted": "%d of %d" % (r6["exact_of_accepted"], r6["accepted_cases"]),
               "B7_recipe_grammar_disagreements": r7["disagreements"],
               "compiler_used": {"path": str(comp_path), "sha256": cas_ast.COMPILER_SHA256},
               "claim_ceiling": "ENGINEERED-NOT-VALIDATED; FORM only; nesting meaning (N1-N13) not settled"}
    write(out / "READING.json", reading)
    timings["worker_wall_total"] = time.perf_counter() - t0
    timings["worker_cpu_total"] = time.process_time() - c0
    summary = {"run_id": RUN_ID, "timings_seconds": timings, "reading": reading,
               "tests": {k: tests[k] for k in ("tests", "failures", "errors", "ok")},
               "B1": r1, "B2": r2, "B3": {k: v for k, v in r3.items() if k != "rows"}, "B4": r4, "B5": r5,
               "B6": {k: v for k, v in r6.items() if k != "rows"}, "B7": {k: v for k, v in r7.items() if k != "rows"}}
    write(out / "SUMMARY.json", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
