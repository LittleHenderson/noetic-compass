"""generate_rc02_receipt.py -- the COMMITTED, reproducible RC-0.2 receipt generator.

OWNER DIRECTIVE RC-0.2 section 10: the status is never hand-written into JSON. This
program regenerates the scenario matrix, runs the raw test suites (stdout captured to
committed report files), executes the FAULT-INJECTION BATTERY (each attack from the
owner's section-12 list must be DETECTED/REFUSED by the system), and emits the status
deterministically from the raw results:

    DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS
        iff all suites pass AND all scenarios pass AND all 8 injections are detected
        AND fresh-process replay is identical AND a mutated input changes the digest
    GATE0_REFUTED
        iff any injection goes UNDETECTED (a live authority hole)
    GATE0_INCONCLUSIVE
        otherwise (e.g. an environment/test failure that is not a detected-hole proof)

Self-reference law: this receipt records the PARENT commit SHA and the code-tree digest.
It cannot contain its own commit SHA; a follow-up attestation commit binds that SHA.

Usage:
    python generate_rc02_receipt.py              # write receipt + matrix + raw reports
    python generate_rc02_receipt.py --check-only # run everything, print STATUS, write nothing
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "sim"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------ fault-injection battery
def run_injections():
    """Each attack must be DETECTED/REFUSED. Returns list of {attack, detected, detail}."""
    import rc01_scenarios as SC
    import rc01_engine as E
    import rc01_types as T
    import rc0_types as T0
    from rc01_coordinator import (HardenedCoordinator, PublicationCoordinator,
                                  PublicationRefused, RejectedBatch)
    out = []

    def record(name, detected, detail):
        out.append({"attack": name, "detected": bool(detected), "detail": str(detail)[:200]})

    PAY = "alpha beta gamma delta"

    # 1. unauthorized publication (uncommitted verdict)
    r = SC.engine([SC.cause("i1", ("structure_cue",), PAY)],
                  SC.Reg().add("i1", "^6_decompose", "intended", PAY),
                  commit_verdicts=False).run()
    record("unauthorized_publication", r["metrics"]["published"] == 0,
           f"published={r['metrics']['published']}")

    # 2. corrupted Effect payload (correct expert id)
    r = SC.engine([SC.cause("i2", ("structure_cue",), PAY)],
                  SC.Reg().add("i2", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"theta": ("K_coarse",)}})).run()
    record("corrupted_effect_payload",
           r["metrics"]["published"] == 0 and r["metrics"]["off_axis_effects"] == 1,
           f"published={r['metrics']['published']}, off_axis={r['metrics']['off_axis_effects']}")

    # 3. new_value digest collision
    c = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    kw = dict(episode_id="ep0", tick=0, producer_id="kernel", expert_id="^6_decompose",
              fld="memory", base_state_version=0,
              base_state_digest=c.get_digest("^6_decompose"))
    a = T.VersionedIntent(new_value=("A",), **kw)
    b = T.VersionedIntent(new_value=("B",), **kw)
    record("new_value_digest_collision", a.intent_digest != b.intent_digest,
           "digests differ" if a.intent_digest != b.intent_digest else "COLLISION")

    # 4. incomplete final-state seal (same metadata, different committed value)
    ca = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    cb = HardenedCoordinator({"^6_decompose": SC.bias()}, "ep0")
    ca.commit([T.VersionedIntent(new_value=("A",), **kw)], 0)
    cb.commit([T.VersionedIntent(new_value=("B",), **kw)], 0)
    record("incomplete_final_state_seal", ca.seal() != cb.seal(),
           "seals differ" if ca.seal() != cb.seal() else "SEAL BLIND TO VALUE")

    # 5. fake CAP (single live saturated route)
    r = SC.engine([SC.cause("i5", ("structure_cue",), PAY)],
                  SC.Reg().add("i5", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"region": "saturation"}})).run()
    record("fake_cap_single_route",
           r["metrics"]["cap_events"] == 0 and r["metrics"]["deferred_causes"] == 1,
           f"cap_events={r['metrics']['cap_events']}, deferred={r['metrics']['deferred_causes']}")

    # 6. missing split return
    sc = next(s for s in SC.SCENARIOS() if s["id"] == "split_resume_combine")
    r = sc["build"]().run()
    combined = [p for p in r["publications"]
                if p["cause"] == "sp0" and p["status"] == "PUBLISHED"]
    record("missing_split_return",
           r["metrics"]["split_frames_resumed"] == 1 and len(combined) == 1,
           f"resumed={r['metrics']['split_frames_resumed']}, combined_pub={len(combined)}")

    # 7. multi-prerequisite stranding
    r = SC.engine([SC.cause("i7", ("structure_cue",), PAY)],
                  SC.Reg().add("i7", "^6_decompose", "intended", PAY),
                  states=SC.states(**{"^6_decompose": {"wisdom": 0.0, "power": 0.0}})).run()
    record("multi_prerequisite_stranding",
           r["metrics"]["published"] == 1 and r["metrics"]["repairs_completed"] == 2,
           f"published={r['metrics']['published']}, repairs={r['metrics']['repairs_completed']}")

    # 8. negative budget spend
    bgt = T.ComputeBudget.make(3)
    try:
        bgt.spend(-1)
        record("negative_budget_spend", False, "spend(-1) accepted")
    except (TypeError, ValueError):
        record("negative_budget_spend", bgt.left == 3, f"left={bgt.left}")
    return out


def main():
    check_only = "--check-only" in sys.argv
    t_start = time.time()
    start_iso = time.strftime("%Y-%m-%dT%H:%M:%S")

    # ---- raw test suites (stdout captured) ----
    suites = {}
    raw_reports = {}
    import os
    child_env = dict(os.environ, RC02_IN_GENERATOR="1")
    for name in ("test_rc0", "test_rc01", "test_rc02", "test_rc03"):
        proc = subprocess.run([sys.executable, f"tests/{name}.py"],
                              capture_output=True, text=True, cwd=str(HERE),
                              env=child_env)
        last = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "NO OUTPUT"
        suites[name] = {"result": last, "exit": proc.returncode}
        raw_reports[name] = proc.stdout + ("\n--- STDERR ---\n" + proc.stderr
                                           if proc.stderr else "")

    # ---- scenario matrix ----
    import rc01_scenarios as SC
    rows, counts = SC.run_matrix()
    all_scenarios_pass = all(r["passed"] for r in rows)

    # ---- fresh-process replay + mutation sensitivity ----
    entry = str(HERE / "sim" / "rc01_replay_entry.py")

    def rp(args):
        return subprocess.run([sys.executable, entry] + args, capture_output=True,
                              text=True, cwd=str(HERE)).stdout.strip()
    d1, d2, d3 = rp(["normal_intended"]), rp(["normal_intended"]), \
        rp(["normal_intended", "--mutate"])

    # ---- fault-injection battery (adversarial input fixtures) ----
    injections = run_injections()
    all_detected = all(i["detected"] for i in injections)

    # ---- REAL mutation audit (RC-0.3): deliberate implementation breaks must be
    # caught by named tests; a surviving mutation is a live authority hole ----
    mut_proc = subprocess.run([sys.executable, "run_mutation_audit.py"],
                              capture_output=True, text=True, cwd=str(HERE))
    mut_path = HERE / "rc03_mutation_report.json"
    mutation_report = json.loads(mut_path.read_text(encoding="utf-8"))         if mut_path.exists() else None
    mutations_ok = bool(mutation_report and mutation_report.get("all_caught")
                        and mutation_report.get("pristine_unchanged"))

    # ---- deterministic status emission (never hand-written) ----
    suites_ok = all(s["exit"] == 0 for s in suites.values())
    replay_ok = (d1 == d2) and (d1 != d3)
    if not all_detected or (mutation_report is not None and not mutations_ok):
        status = "GATE0_REFUTED"          # an undetected attack or a surviving mutation
    elif mutation_report is None:
        status = "GATE0_INCONCLUSIVE"     # mutation audit missing: cannot claim the pass
    elif suites_ok and all_scenarios_pass and replay_ok and mutations_ok:
        status = "DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS"
    else:
        status = "GATE0_INCONCLUSIVE"

    print(f"suites: {[s['result'] for s in suites.values()]}")
    print(f"scenarios: {sum(1 for r in rows if r['passed'])}/{len(rows)}")
    print(f"injections detected: {sum(1 for i in injections if i['detected'])}/{len(injections)}")
    if mutation_report:
        print(f"mutations caught: {sum(1 for m in mutation_report['mutations'] if m['caught'])}"
              f"/{len(mutation_report['mutations'])}")
    print(f"replay identical: {d1 == d2} | mutation changes digest: {d1 != d3}")
    print(f"STATUS: {status}")
    if check_only:
        return 0

    # ---- git context + environment ----
    def git(*a):
        return subprocess.run(["git"] + list(a), capture_output=True, text=True,
                              cwd=str(HERE)).stdout.strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    parent = git("rev-parse", "HEAD")
    dirty = subprocess.run(["git", "diff", "--quiet"], cwd=str(HERE)).returncode != 0

    # ---- write raw reports ----
    reports_dir = HERE / "rc02_raw_reports"
    reports_dir.mkdir(exist_ok=True)
    raw_paths = {}
    for name, text in raw_reports.items():
        p = reports_dir / f"{name}.stdout.txt"
        p.write_text(text, encoding="utf-8")
        raw_paths[name] = str(p.relative_to(HERE)).replace("\\", "/")

    # ---- scenario matrix artifact ----
    matrix = {"matrix_id": "RC01_SCENARIO_MATRIX", "phase": "RC-0.2",
              "scenarios": rows, "counts": counts}
    (HERE / "RC01_SCENARIO_MATRIX.json").write_text(
        json.dumps(matrix, indent=2, default=str) + "\n", encoding="utf-8")

    # ---- artifact digests over the tree (excluding the receipt itself) ----
    tree = {}
    for p in sorted(HERE.rglob("*")):
        if (p.is_file() and "__pycache__" not in str(p) and ".pytest_cache" not in str(p)
                and p.name not in ("RC01_FEEDBACK_CLOSURE_RECEIPT.json",)):
            tree[str(p.relative_to(HERE)).replace("\\", "/")] = sha(p)
    code_tree_digest = hashlib.sha256(
        json.dumps(tree, sort_keys=True).encode()).hexdigest()

    deps = {"python": sys.version, "platform": platform.platform(),
            "modules": {"json": "stdlib", "hashlib": "stdlib", "dataclasses": "stdlib"}}

    receipt = {
        "receipt_id": "RC01_FEEDBACK_CLOSURE_RECEIPT",
        "phase": "RC-0.2 (effect authority, semantic verification, complete state seal)",
        "status": status,
        "status_emitted_by": "generate_rc02_receipt.py (deterministic; never hand-written)",
        "claim_bearing": False,
        "neural_network": "NONE (deterministic CPU simulation only)",
        "environment": {"python": sys.version.split()[0], "os": platform.platform(),
                        "branch": branch, "parent_commit_sha": parent,
                        "working_tree_dirty_at_generation": dirty,
                        "dependencies": deps},
        "self_reference_law": "This receipt records the PARENT commit and the code-tree "
                              "digest; the commit SHA that contains this receipt can only "
                              "be bound by a follow-up commit. Any such binding record is "
                              "an UNSIGNED Git-history binding, not a signed or "
                              "independently verified attestation, until the owner signs "
                              "with a real key.",
        "commands": ["python generate_rc02_receipt.py",
                     "python tests/test_rc0.py", "python tests/test_rc01.py",
                     "python tests/test_rc02.py", "python sim/rc01_scenarios.py",
                     "python sim/rc01_replay_entry.py normal_intended [--mutate]"],
        "started": start_iso,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "duration_seconds": round(time.time() - t_start, 2),
        "tests": suites,
        "raw_report_paths": raw_paths,
        "scenario_matrix": {"total": len(rows),
                            "passed": sum(1 for r in rows if r["passed"]),
                            "all_passed": all_scenarios_pass, "counts": counts,
                            "per_scenario": [{"id": r["id"], "passed": r["passed"]}
                                             for r in rows],
                            "matrix_digest": sha(HERE / "RC01_SCENARIO_MATRIX.json")},
        "fault_injections": injections,
        "mutation_audit": mutation_report,
        "digest_domain": "all artifact digests are SHA-256 over RAW FILE BYTES exactly as "
                         "stored on disk (no newline normalization, no encoding transform); "
                         "trace/seal digests are SHA-256 over canonical JSON "
                         "(sorted keys, ensure_ascii, compact separators)",
        "fresh_process_replay": {"digest_run1": d1, "digest_run2": d2,
                                 "identical": d1 == d2, "mutated_digest": d3,
                                 "mutation_changes_digest": d1 != d3},
        "artifact_digests": tree,
        "test_file_digests": {f"tests/{n}.py": sha(HERE / "tests" / f"{n}.py")
                              for n in ("test_rc0", "test_rc01", "test_rc02")},
        "code_tree_digest": code_tree_digest,
        "claims_permitted": ["the deterministic reference controller enforces its typed "
                             "authority, verification, and seal semantics across every "
                             "registered path, and detects all eight injected attacks"],
        "claims_prohibited": ["neural capability", "learning improvement",
                              "CAS-specific value", "CAS-Ohm predictive validity",
                              "reasoning-machine capability", "efficiency advantage"],
    }
    (HERE / "RC01_FEEDBACK_CLOSURE_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("receipt written: RC01_FEEDBACK_CLOSURE_RECEIPT.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
