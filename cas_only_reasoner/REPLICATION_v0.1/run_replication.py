"""The one-command external replication runner (the path to E6).

An EXTERNAL evaluator - outside the developing party's session and
provenance - runs:

    python run_replication.py            # all deterministic suites
    python run_replication.py --cortex   # adds the live-cortex smoke

It re-runs every board's test suite, re-derives the qualification,
verifies the deterministic digests, and writes replication_report.json
next to this file. The evaluator then completes the attestation form
in REPLICATION.md, claim by claim. E6 unlocks ONLY for the exact
claims independently reproduced.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)

EXPECTED_PATH = os.path.join(HERE, "expected_results.json")


def utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def run_suite(board: str) -> dict:
    """Counts come from junit XML - uniform regardless of each
    board's own pytest quiet settings (self-test finding: nine boards
    suppress the 'N passed' summary line)."""
    import tempfile
    import xml.etree.ElementTree as ET
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = os.path.join(tmp, "results.xml")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no",
             f"--junitxml={xml_path}"],
            cwd=os.path.join(LANE, board),
            capture_output=True, text=True, timeout=1200)
        tests = failures = errors = 0
        if os.path.exists(xml_path):
            root = ET.parse(xml_path).getroot()
            suite = root if root.tag == "testsuite" \
                else root.find("testsuite")
            if suite is not None:
                tests = int(suite.get("tests", 0))
                failures = int(suite.get("failures", 0))
                errors = int(suite.get("errors", 0))
    return {"board": board,
            "passed": tests - failures - errors,
            "failed": failures + errors,
            "exit_code": proc.returncode}


def qualification() -> str:
    proc = subprocess.run(
        [sys.executable, "run_demo.py"],
        cwd=os.path.join(LANE, "CRQS_v0.1"),
        capture_output=True, text=True, timeout=600)
    # the demo qualifies three Minds; the CNCM is the LAST block
    # (self-test finding: the first match was the cas-rr prototype)
    matches = re.findall(r"Qualified level:\s*\n\s*(CAS-\S+ / E\d / A\d)",
                         proc.stdout or "")
    return matches[-1] if matches else "NOT FOUND"


def deterministic_digests() -> dict:
    """Re-derive the digests that must reproduce bit-for-bit on any
    machine (no wall-clock content)."""
    digests = {}
    code = (
        "import sys, json\n"
        f"sys.path.insert(0, {os.path.join(LANE, 'CCB_M1_v0.1')!r})\n"
        "from cas_math.discovery import discover\n"
        "print(discover()['discovery_digest'])\n"
    )
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=600)
    digests["discovery_digest"] = (proc.stdout or "").strip().splitlines()[-1] \
        if proc.returncode == 0 else f"ERROR: {proc.stderr[-200:]}"

    code = (
        "import sys, json, tempfile, os\n"
        f"sys.path.insert(0, {os.path.join(LANE, 'CNCM_G10_v0.1')!r})\n"
        "from integration import episodes\n"
        "with tempfile.TemporaryDirectory() as tmp:\n"
        "    episodes.episode1(tmp)\n"
        "    episodes.episode2(tmp)\n"
        "    result = episodes.episode3(tmp)\n"
        "print(result['store_digest'])\n"
    )
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=900)
    digests["g10_final_store_digest"] = \
        (proc.stdout or "").strip().splitlines()[-1] \
        if proc.returncode == 0 else f"ERROR: {proc.stderr[-200:]}"
    return digests


def cortex_smoke() -> dict:
    """Optional live leg: model identity receipt + one grounded parse
    + one fabrication catch. Requires the local model snapshot."""
    code = (
        "import sys, json\n"
        f"sys.path.insert(0, {os.path.join(LANE, 'CAS_CORTEX_v0.1')!r})\n"
        "from cortex.adapter import CortexAdapter\n"
        "from cortex.router import HybridRouter\n"
        "adapter = CortexAdapter()\n"
        "router = HybridRouter(mode='HYBRID_COMMIT', cortex=adapter)\n"
        "a = router.turn('would you say the cat is gray?')\n"
        "b = router.turn('the zorble is gray.')\n"
        "print(json.dumps({'weights_digest': "
        "adapter.receipt['weights_digest'], "
        "'equivalence_answer': a['answer'].get('text'), "
        "'fabrication_catch': b['answer'].get('status')}))\n"
    )
    proc = subprocess.run([sys.executable, "-c", code],
                          capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        return {"status": "FAILED", "stderr": proc.stderr[-300:]}
    return json.loads((proc.stdout or "").strip().splitlines()[-1])


def main():
    utf8()
    parser = argparse.ArgumentParser()
    parser.add_argument("--cortex", action="store_true",
                        help="include the live-cortex smoke leg")
    args = parser.parse_args()

    expected = json.load(open(EXPECTED_PATH, encoding="utf-8"))

    environment = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
    }
    print("environment:", json.dumps(environment))

    suites = []
    for board, expected_count in expected["suite_counts"].items():
        result = run_suite(board)
        result["expected"] = expected_count
        result["match"] = (result["passed"] == expected_count
                           and result["failed"] == 0
                           and result["exit_code"] == 0)
        suites.append(result)
        flag = "OK " if result["match"] else "MISMATCH"
        print(f"  [{flag}] {board}: {result['passed']} passed "
              f"(expected {expected_count})")

    qualified = qualification()
    qual_match = qualified == expected["qualified_level"]
    print(f"qualification: {qualified!r} "
          f"(expected {expected['qualified_level']!r}) "
          f"{'OK' if qual_match else 'MISMATCH'}")

    digests = deterministic_digests()
    digest_matches = {
        name: {"observed": value,
               "expected": expected["deterministic_digests"].get(name),
               "match": value == expected[
                   "deterministic_digests"].get(name)}
        for name, value in digests.items()}
    for name, row in digest_matches.items():
        print(f"  digest {name}: {row['observed']} "
              f"{'OK' if row['match'] else 'MISMATCH'}")

    report = {
        "environment": environment,
        "suites": suites,
        "all_suites_match": all(s["match"] for s in suites),
        "qualification": {"observed": qualified,
                          "expected": expected["qualified_level"],
                          "match": qual_match},
        "deterministic_digests": digest_matches,
        "known_caveats": expected["known_caveats"],
    }
    if args.cortex:
        report["cortex_smoke"] = cortex_smoke()
        report["cortex_smoke"]["expected_weights_digest"] = \
            expected["cortex"]["weights_digest"]
        print("cortex smoke:", json.dumps(report["cortex_smoke"]))

    payload = json.dumps(report, sort_keys=True, default=str)
    report["report_digest"] = hashlib.sha256(
        payload.encode("utf-8")).hexdigest()[:16]
    out = os.path.join(HERE, "replication_report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    print(f"\nreport written: {out} (digest {report['report_digest']})")
    print("next: complete the attestation form in REPLICATION.md, "
          "claim by claim.")


if __name__ == "__main__":
    main()
