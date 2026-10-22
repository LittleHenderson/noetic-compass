"""LM-T1 worker. One process, one single-use run, needs the supervisor's permit.

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
RUN_ID = "LM_T1_MSI_ONCE"
SCOPE = "LM_T1"


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False, default=str), "utf-8")


def expected_sign_line(sha):
    return "APPROVE lm_t1, source " + sha[:8] + ", LOCAL_CPU_ONCE on MSI, 300 s cap, no spend."


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
            raise PermissionError("lm_t1 forbids sockets")

    def rejected(*args, **kwargs):
        raise PermissionError("lm_t1 forbids network")
    socket.socket = OfflineSocket
    socket.create_connection = rejected


def verify_source(permission):
    raw = (HERE / "SOURCE_MANIFEST.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != permission["source_manifest_sha256"]:
        raise PermissionError("approved manifest mismatch")
    for row in json.loads(raw)["files"]:
        if hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest() != row["sha256"]:
            raise PermissionError("source/data drift: " + row["path"])


def run_tests():
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestLoader().loadTestsFromName("test_lm_t1"))
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

    import cce
    import coverage
    import scoring
    frozen = json.loads((HERE / "FROZEN.json").read_text("utf-8"))
    hs_freeze = json.loads((HERE / "handset" / "HAND_SET_FREEZE.json").read_text("utf-8"))
    hs_raw = (HERE / "handset" / "HAND_SET_v0_1.json").read_bytes()
    if hashlib.sha256(hs_raw).hexdigest() != hs_freeze["sha256"]:
        write(out / "ERROR.json", {"status": "ABORTED_HAND_SET_DRIFT"})
        return 3
    items = json.loads(hs_raw.decode("utf-8"))["items"]

    t = time.perf_counter()
    recipes = scoring.load_recipes()
    r1 = scoring.m1(recipes)
    timings["m1"] = time.perf_counter() - t
    write(out / "M1_ROUND_TRIP_576.json", r1)
    t = time.perf_counter()
    r2 = scoring.m2(recipes)
    timings["m2"] = time.perf_counter() - t
    write(out / "M2_WORDING_DRAWS.json", r2)

    t = time.perf_counter()
    r6, _ = coverage.run_main()
    side = coverage.side_universes()
    timings["m6"] = time.perf_counter() - t
    rows6 = r6["rows"]
    m6_pass = (r6["n_eligible"] == 2600 and sum(r6["state_counts"].values()) == 2600
               and not any(r["covered_without_charge"] for r in rows6)
               and all(r["receipt_id"] for r in rows6 if r["state"] == "COVERED"))
    write(out / "M6_COVERAGE_LEDGER.json", {"main": r6, "side": side, "pass": m6_pass,
                                            "covered_without_charge": sum(r["covered_without_charge"] for r in rows6)})

    t = time.perf_counter()
    back = []
    for r in recipes:
        try:
            back.append(cce.parse(cce.render(r["content"])))
        except Exception:
            back.append(None)
    terms = []
    probe_contents = []
    for f, n in coverage.pairs():
        for d in cce.DOMAINS:
            for rv in coverage.REG_VALUES:
                pc = coverage.probe_content(f, n, d, rv)
                probe_contents.append(pc)
                terms += scoring.walk_terms(pc)
    gold_contents = []
    for it in items:
        if "content" in it["expect"]:
            try:
                cce.canonical(it["expect"]["content"])
                gold_contents.append(it["expect"]["content"])
                terms += scoring.walk_terms(it["expect"]["content"])
            except Exception:
                pass
    r7 = scoring.m7(recipes, back, terms)
    timings["m7"] = time.perf_counter() - t
    write(out / "M7_COMPILER_CROSSCHECK.json", r7)

    t = time.perf_counter()
    lookup = scoring.Lookup([r["content"] for r in recipes] + gold_contents + probe_contents)
    lk_m1 = 0
    for r in recipes:
        try:
            lk_m1 += lookup.parse(cce.render(r["content"])) == cce.normalize(r["content"])
        except cce.Refusal:
            pass
    r3 = scoring.m3(items, lookup)
    r3["lookup_m1_576"] = lk_m1
    timings["m3"] = time.perf_counter() - t
    write(out / "M3_HAND_SET.json", r3)

    t = time.perf_counter()
    excluded = set(frozen["headline_rows"]["excluded_42_seed_ids"])
    eng_rows, total_rows = scoring.load_english(excluded)
    r4 = scoring.m4(eng_rows, lookup)
    r4["rows_in_files"] = total_rows
    r4["recipe_rows"] = len(eng_rows)
    r5 = scoring.m5(eng_rows)
    r5b = scoring.m5b(eng_rows)
    timings["m4_m5"] = time.perf_counter() - t
    rows4 = r4.pop("rows")
    with (out / "M4_SDG_ROWS.jsonl").open("w", encoding="utf-8") as h:
        for row in rows4:
            h.write(json.dumps(row, ensure_ascii=False) + "\n")
    write(out / "M4_SDG_ENGLISH.json", r4)
    write(out / "M5_CONTROLS.json", {"M5": r5, "M5b_shuffled": r5b})

    hard = {"M1": r1["pass"], "M2": r2["pass"], "M3": r3["pass"], "M5_00459": r5["positive_control_00459_mismatch"],
            "M5b": r5b["pass"], "M6": m6_pass, "M7": r7["pass"]}
    reading = {"hard_marks": hard, "LM_T1_core": "PASS" if all(hard.values()) else "FAILURE",
               "failed_hard_marks": [k for k, v in hard.items() if not v],
               "M4_SDG_mark": "SDG mark met" if r4["mark_met"] else "SDG mark not met",
               "M4_numbers": {"alias_wide_match": r4["alias_wide_match"], "of": r4["headline_rows"], "mark": 176,
                              "bridge_v2_match_same_rows": r4["bridge_v2_on_same_rows"].get("MATCH", 0)},
               "claim_ceiling": "ENGINEERED-NOT-VALIDATED (translator); FORM only; no meaning claim",
               "reading_rule": frozen["reading_rule"]}
    write(out / "READING.json", reading)
    timings["worker_wall_total"] = time.perf_counter() - t0
    timings["worker_cpu_total"] = time.process_time() - c0
    summary = {"run_id": RUN_ID, "timings_seconds": timings, "reading": reading,
               "tests": {k: tests[k] for k in ("tests", "failures", "errors", "ok")},
               "M1": {k: r1[k] for k in ("recipes", "round_trip_ok", "pass")},
               "M2": {k: v for k, v in r2.items()},
               "M3": {k: v for k, v in r3.items() if k != "rows"},
               "M4": r4, "M5": r5, "M5b": r5b,
               "M6": {"state_counts": r6["state_counts"], "pass": m6_pass,
                      "side": {k: v["state_counts"] for k, v in side.items()},
                      "side_gaps": {k: v["gap_set"] for k, v in side.items()}},
               "M7": {k: v for k, v in r7.items() if k != "rows_disagree"}}
    write(out / "SUMMARY.json", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
