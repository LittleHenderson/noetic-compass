"""generate_rc02_receipt.py -- the COMMITTED, reproducible RC-0.4 receipt generator.

The status is never hand-written into JSON. This program regenerates the scenario
matrix, runs the raw test suites (stdout captured to committed report files), executes
the FAULT-INJECTION BATTERY, runs the REAL mutation audit under the RC-0.4 status law,
and emits the status deterministically from the raw results:

    DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT
        (the STRONGEST internally emittable status, RC-0.4A section 6) iff all suites
        pass AND all scenarios pass AND all injections are detected AND fresh-process
        replay is identical AND a mutated input changes the digest AND the mutation
        audit satisfies the freshness law AND the fresh report matches the FROZEN
        mutation manifest exactly. Full Gate 0 freezes only after an independent
        auditor reruns the exact committed evidence.
    GATE0_REFUTED
        iff any injection goes UNDETECTED, any applied mutation SURVIVES or fails
        only via a non-semantic crash, or the fresh report does not match the frozen
        mutation manifest (missing/extra/renamed/re-targeted mutations)
    GATE0_INCONCLUSIVE
        otherwise (environment/test failure, or a mutation audit that cannot be
        trusted: crashed, stale, or generated from a different tree)

RC-0.4 MUTATION-STATUS LAW (owner audit major 1 of 846f323f): before the audit runs,
any previous mutation report is DELETED; afterwards the status accepts ONLY a freshly
created report whose source-tree and test-tree digests equal the CURRENT tree, whose
subprocess exited 0, and in which every mutation was applied AND caught by a SEMANTIC
AssertionError. A crash can never fall back to a previously committed passing report.

Self-reference law: this receipt records the PARENT commit SHA and the code-tree digest.
It cannot contain its own commit SHA; a follow-up binding record (UNSIGNED Git-history
binding, not an attestation) binds that SHA.

Usage:
    python generate_rc02_receipt.py              # write receipt + matrix + raw reports
    python generate_rc02_receipt.py --check-only # run everything, print STATUS,
                                                 # write NOTHING (the mutation audit
                                                 # reports via stdout in this mode)
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

SUITES = ("test_rc0", "test_rc01", "test_rc02", "test_rc03", "test_rc04",
          "test_rc04a", "test_rc04b")

# RC-0.4A section 4: the FROZEN mutation inventory. The manifest file's
# canonical-content digest is pinned HERE so neither the file nor this constant can
# change without the other showing in the diff. Newline-normalization-proof: the
# digest is over json.dumps(parsed content, sort_keys, compact), not raw bytes.
MANIFEST_PATH_NAME = "RC04_REQUIRED_MUTATIONS_v1.json"
REQUIRED_MUTATION_MANIFEST_DIGEST = \
    "877ff938a680e40830d4111f34d9fb17d510ad68d8b546dfb842f8c8ee76c852"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_required_manifest(path=None):
    """Load + integrity-check the frozen mutation manifest. Returns (manifest, reason)."""
    p = Path(path) if path else (HERE / MANIFEST_PATH_NAME)
    if not p.exists():
        return None, "MUTATION_MANIFEST_FILE_MISSING"
    data = json.loads(p.read_text(encoding="utf-8"))
    canon = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canon).hexdigest() != REQUIRED_MUTATION_MANIFEST_DIGEST:
        return None, "MUTATION_MANIFEST_TAMPERED"
    return data, "OK"


def mutation_manifest_law(fresh_report, manifest):
    """RC-0.4A section 4: the fresh report must contain EXACTLY the frozen mutation
    set -- same names, same count, same file/test pairs. Proves 'every REQUIRED
    mutation was present and caught', not merely 'every present mutation was caught'.
    Returns (ok, reason); any failure REFUTES the status."""
    if manifest is None:
        return False, "MUTATION_MANIFEST_UNAVAILABLE"
    req = {m["name"]: m for m in manifest.get("mutations", [])}
    report_muts = (fresh_report or {}).get("mutations", [])
    # RC-0.4B (internal audit MINOR): validate the report entries BEFORE set math --
    # a malformed name would crash join()/sorted(), and a duplicate name would collapse
    # in a dict comprehension and defeat the count check.
    names = [m.get("name") for m in report_muts]
    if any((not isinstance(n, str)) or not n for n in names):
        return False, "MUTATION_MANIFEST_MALFORMED_ENTRY"
    if len(names) != len(set(names)):
        return False, "MUTATION_MANIFEST_DUPLICATE_ENTRY"
    got = {m["name"]: m for m in report_muts}
    missing = sorted(set(req) - set(got))
    if missing:
        return False, "MUTATION_MANIFEST_MISSING_REQUIRED:" + ",".join(missing)
    extra = sorted(set(got) - set(req))
    if extra:
        return False, "MUTATION_MANIFEST_EXTRA_UNREGISTERED:" + ",".join(extra)
    if len(names) != manifest.get("required_count"):
        return False, "MUTATION_MANIFEST_COUNT_MISMATCH"
    for name, r in req.items():
        g = got[name]
        if g.get("file") != r["file"] or g.get("expected_test") != r["expected_test"]:
            return False, f"MUTATION_MANIFEST_PAIR_MISMATCH:{name}"
    return True, "OK"


def emit_status(all_detected, mutation_survived, report_exists, manifest_ok,
                mutations_ok, suites_ok, scenarios_ok, replay_ok):
    """The deterministic status law, as one pure testable function (RC-0.4A).
    Strongest emittable status is PASS_PENDING_INDEPENDENT_AUDIT -- full Gate 0
    freezes only after an independent auditor reruns the exact committed evidence."""
    if not all_detected or mutation_survived:
        return "GATE0_REFUTED"           # undetected attack or surviving mutation
    if report_exists and not manifest_ok:
        return "GATE0_REFUTED"           # wrong INVENTORY: a required law is unproven
    if not mutations_ok:
        return "GATE0_INCONCLUSIVE"      # audit crashed/stale/wrong-tree: no pass claim
    # RC-0.4B (internal audit MINOR): the PASS path consults manifest_ok UNCONDITIONALLY
    # so this pure function is independently sound -- it never relies on a caller
    # invariant coupling report_exists to mutations_ok.
    if manifest_ok and suites_ok and scenarios_ok and replay_ok:
        return "DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT"
    return "GATE0_INCONCLUSIVE"


# ------------------------------------------------------------ RC-0.4 mutation-status law
def run_fresh_mutation_audit(here: Path, check_only: bool, runner=subprocess.run):
    """Run the mutation audit and return (returncode, fresh_report_or_None).

    Write mode: any PRIOR report file is deleted FIRST, so the only readable report is
    one this run created. Check-only mode: the audit writes nothing and reports over
    stdout (MUTATION_REPORT_JSON: line). Either way, a crash yields report=None --
    stale evidence is unreachable by construction."""
    report_path = here / "rc03_mutation_report.json"
    if check_only:
        proc = runner([sys.executable, "run_mutation_audit.py", "--emit-stdout"],
                      capture_output=True, text=True, cwd=str(here))
        report = None
        for line in (getattr(proc, "stdout", "") or "").splitlines():
            if line.startswith("MUTATION_REPORT_JSON:"):
                report = json.loads(line[len("MUTATION_REPORT_JSON:"):])
        return proc.returncode, report
    if report_path.exists():
        report_path.unlink()      # stale evidence deleted BEFORE the audit launches
    proc = runner([sys.executable, "run_mutation_audit.py"],
                  capture_output=True, text=True, cwd=str(here))
    if not report_path.exists():
        return proc.returncode, None   # crash: no fresh report, no fallback
    return proc.returncode, json.loads(report_path.read_text(encoding="utf-8"))


def mutation_status_law(returncode, fresh_report, current_src_digest, current_test_digest):
    """Deterministic acceptance law for the mutation audit (RC-0.4 section 6).
    `fresh_report` must be a report produced by THIS run (never a pre-existing file).
    Returns (ok, reason)."""
    if fresh_report is None:
        return False, "MUTATION_AUDIT_MISSING_FRESH_REPORT"
    if fresh_report.get("source_tree_digest") != current_src_digest:
        return False, "MUTATION_REPORT_SOURCE_TREE_MISMATCH"
    if fresh_report.get("test_tree_digest") != current_test_digest:
        return False, "MUTATION_REPORT_TEST_TREE_MISMATCH"
    muts = fresh_report.get("mutations", [])
    if not muts or not all(m.get("applied") for m in muts):
        return False, "MUTATION_NOT_APPLIED"
    if not all(m.get("caught") and m.get("semantic_failure") for m in muts):
        return False, "MUTATION_SURVIVED_OR_NONSEMANTIC"
    if not fresh_report.get("pristine_unchanged"):
        return False, "PRISTINE_TREE_MODIFIED"
    if returncode != 0:
        return False, "MUTATION_AUDIT_NONZERO_EXIT"
    return True, "OK"


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
    for name in SUITES:
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

    # ---- REAL mutation audit under the RC-0.4 status law: stale evidence deleted
    # first; only a FRESH report from the CURRENT tree, exit 0, every mutation applied
    # and caught SEMANTICALLY, is accepted ----
    import run_mutation_audit as MA
    mut_rc, mutation_report = run_fresh_mutation_audit(HERE, check_only)
    cur_src = MA.tree_digest(HERE / "sim")
    cur_tst = MA.tree_digest(HERE / "tests")
    mutations_ok, mutation_law_reason = mutation_status_law(
        mut_rc, mutation_report, cur_src, cur_tst)
    # a SURVIVING (or crash-only-detected) applied mutation is a proven authority hole
    mutation_survived = bool(mutation_report) and any(
        m.get("applied") and not (m.get("caught") and m.get("semantic_failure"))
        for m in mutation_report.get("mutations", []))

    # ---- RC-0.4A: the FROZEN mutation inventory must match exactly ----
    manifest, manifest_load_reason = load_required_manifest()
    manifest_ok, manifest_reason = mutation_manifest_law(mutation_report, manifest)
    if manifest is None:
        manifest_reason = manifest_load_reason

    # ---- deterministic status emission (never hand-written) ----
    suites_ok = all(s["exit"] == 0 for s in suites.values())
    replay_ok = (d1 == d2) and (d1 != d3)
    status = emit_status(all_detected, mutation_survived,
                         mutation_report is not None, manifest_ok,
                         mutations_ok, suites_ok, all_scenarios_pass, replay_ok)

    print(f"suites: {[s['result'] for s in suites.values()]}")
    print(f"scenarios: {sum(1 for r in rows if r['passed'])}/{len(rows)}")
    print(f"injections detected: {sum(1 for i in injections if i['detected'])}/{len(injections)}")
    if mutation_report:
        print(f"mutations caught (semantic): "
              f"{sum(1 for m in mutation_report['mutations'] if m['caught'])}"
              f"/{len(mutation_report['mutations'])}")
    print(f"mutation status law: {mutation_law_reason}")
    print(f"mutation manifest law: {manifest_reason}")
    print(f"replay identical: {d1 == d2} | mutation changes digest: {d1 != d3}")
    print(f"STATUS: {status}")
    if check_only:
        # --check-only writes NOTHING (RC-0.4 section 7)
        return (0 if status ==
                "DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT"
                else 1)

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
    matrix = {"matrix_id": "RC01_SCENARIO_MATRIX", "phase": "RC-0.4",
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
        "phase": "RC-0.4B (finalization GOVERNS the write paths via a shared seal gate; "
                 "self-verifying result(); storable==sealable non-finite rejection; "
                 "exact typed runtime snapshot; sealed fault paths; frozen mutation "
                 "inventory) -- RC-0.4A directive plus its internal pre-commit "
                 "adversarial-audit closures",
        "status": status,
        "status_emitted_by": "generate_rc02_receipt.py (deterministic; never hand-written)",
        "independent_confirmation": "PENDING BY CONSTRUCTION -- the strongest "
                                    "emittable status name itself says "
                                    "PENDING_INDEPENDENT_AUDIT (RC-0.4A section 6); "
                                    "full Gate 0 freezes only after an independent "
                                    "auditor checks out the exact commit, reruns all "
                                    "suites/scenarios/the frozen mutation inventory, "
                                    "and reproduces the repaired attacks",
        "claim_bearing": False,
        "neural_network": "NONE (deterministic CPU simulation only)",
        "trust_boundary": "the verifier issuance registry and all private registries "
                          "are SAME-PROCESS API CAPABILITY DISCIPLINE: ordinary API "
                          "callers cannot manufacture an accepted receipt without the "
                          "verifier issuance path. This is NOT cryptographic isolation "
                          "and NOT hostile-code isolation -- introspection inside the "
                          "same Python process is out of scope by design (RC-0.4 "
                          "section 7).",
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
                     "python generate_rc02_receipt.py --check-only",
                     "python run_mutation_audit.py"]
                    + [f"python tests/{n}.py" for n in SUITES]
                    + ["python sim/rc01_scenarios.py",
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
        "mutation_status_law": {
            "accepted": mutations_ok, "reason": mutation_law_reason,
            "subprocess_returncode": mut_rc,
            "current_source_tree_digest": cur_src,
            "current_test_tree_digest": cur_tst,
            "law": "stale report deleted before launch; only a fresh report from the "
                   "current tree with exit 0 and every mutation applied AND caught by "
                   "a semantic AssertionError is accepted; a crash never falls back to "
                   "prior evidence"},
        "mutation_manifest_law": {
            "accepted": manifest_ok, "reason": manifest_reason,
            "manifest_file": MANIFEST_PATH_NAME,
            "pinned_manifest_digest": REQUIRED_MUTATION_MANIFEST_DIGEST,
            "law": "the fresh report must contain EXACTLY the frozen mutation set "
                   "(names, count, file/test pairs); a missing, extra, renamed, or "
                   "re-targeted mutation REFUTES the status (RC-0.4A section 4)"},
        "digest_domain": "all artifact digests are SHA-256 over RAW FILE BYTES exactly as "
                         "stored on disk (no newline normalization, no encoding transform); "
                         "trace/seal digests are SHA-256 over canonical JSON "
                         "(sorted keys, ensure_ascii, compact separators)",
        "fresh_process_replay": {"digest_run1": d1, "digest_run2": d2,
                                 "identical": d1 == d2, "mutated_digest": d3,
                                 "mutation_changes_digest": d1 != d3},
        "artifact_digests": tree,
        "test_file_digests": {**{f"tests/{n}.py": sha(HERE / "tests" / f"{n}.py")
                                 for n in SUITES},
                              "run_mutation_audit.py": sha(HERE / "run_mutation_audit.py")},
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
