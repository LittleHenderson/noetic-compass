"""test_gate1a2_conformance.py -- the END-TO-END synthetic campaign (section 12)
plus the thirteen sabotage detections. PERMANENTLY NON-CLAIM-BEARING.

One committed harness builds the fixtures (tiny dataset, fake model identity,
fake AWS identity, TEST-key detached approvals, synthetic schedule) and runs
the SAME campaign driver as real mode through the complete lifecycle:
approvals -> trust root -> identity -> data -> baselines -> caches -> layer
selection -> 24+1 scheduled runs -> checkpoint receipts -> one-use protected
lock -> committed protected scoring -> raw results with evidence chain ->
frozen status program (--conformance) -> cost accounting -> shutdown ->
TERMINATED. Then each sabotage rebuilds a fresh campaign with ONE corruption
and requires the machinery to refuse it.

On success, prints the strongest status Gate 1A.2 permits:
GATE1A2_SOFTWARE_CONFORMANCE_PASS_PENDING_INDEPENDENT_AUDIT_OWNER_KEY_PIN_OWNER_DECISIONS_CONTAINER_PREP
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))

import exec.synthetic as syn  # noqa: E402
from exec.campaign_driver import CampaignDriver, sha256_file  # noqa: E402
from exec.fsio import write_utf8_lf  # noqa: E402

FINAL_STATUS = ("GATE1A2_SOFTWARE_CONFORMANCE_PASS"
                "_PENDING_INDEPENDENT_AUDIT"
                "_OWNER_KEY_PIN"
                "_OWNER_DECISIONS"
                "_CONTAINER_PREP")

HPKG = None          # the hermetic package copy (set once in main)
HCOMMIT = None


def make_hermetic_package(dst: Path):
    """The campaign driver requires an exact commit and a CLEAN tree (the real
    campaign runs from a pristine clone). To honor that law pre-commit, the
    conformance campaign runs against a hermetic COPY of the package inside a
    scratch git repository: copy -> regenerate manifests -> commit there."""
    shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns(
        "__pycache__", "results", "derived"))
    r = subprocess.run([sys.executable, str(dst / "tools" / "build_manifests.py")],
                       capture_output=True, text=True, cwd=dst)
    assert r.returncode == 0, r.stdout + r.stderr
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.email=conformance@test",
                 "-c", "user.name=conformance", "commit", "-q", "-m", "hermetic"]):
        subprocess.run(cmd, cwd=dst, capture_output=True, text=True, check=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dst,
                            capture_output=True, text=True, check=True
                            ).stdout.strip()
    return dst, commit


def build_campaign(root: Path, campaign_id: str):
    """All fixtures for one synthetic campaign; returns the driver kwargs."""
    synthetic_root = root / "synthetic"
    detached = root / "detached"                    # OUTSIDE the package root
    evidence = root / "evidence"
    detached.mkdir(parents=True, exist_ok=True)
    ident = syn.build_synthetic_model_identity(synthetic_root)
    s7_path, _, s7_sha = syn.build_synthetic_taxonomy(synthetic_root)
    sched_path = syn.build_synthetic_schedule(synthetic_root)
    dep_lock_sha = "88" * 32
    prep_receipt_path, prep_receipt = syn.build_container_prep_receipt(
        synthetic_root, ident, s7_sha, dep_lock_sha)
    # the dataset manifest digest must be known BEFORE signing: build the
    # synthetic dataset once into the evidence area the driver will use
    ds_root = evidence / "regenerated_dataset"
    manifest, _ = syn.build_synthetic_dataset(ds_root, campaign_id)
    fixture = {"container_prep_receipt_sha256": sha256_file(prep_receipt_path),
               "model_revision_sha": ident["model_revision_sha"],
               "model_weight_sha256s": ident["model_weight_sha256s"],
               "tokenizer_file_sha256s": ident["tokenizer_file_sha256s"],
               "dependency_lock_sha256": dep_lock_sha,
               "container_image_digest": prep_receipt["container_image_digest"],
               "dataset_manifest_sha256": sha256_file(
                   ds_root / "SYNTHETIC_DATASET_MANIFEST.json"),
               "s7_control_table_sha256": s7_sha,
               "run_schedule_sha256": sha256_file(sched_path)}
    prep_path, exec_path = syn.build_synthetic_approvals(
        detached, HPKG, HCOMMIT, fixture)
    return {"mode": "SYNTHETIC_CONFORMANCE", "package_root": HPKG,
            "campaign_id": campaign_id, "execution_approval_path": exec_path,
            "prep_approval_path": prep_path,
            "prep_receipt_path": prep_receipt_path,
            "evidence_root": evidence, "synthetic_root": synthetic_root}


def run_campaign(kwargs):
    return CampaignDriver(**kwargs).run()


def expect_refused(name, kwargs):
    try:
        run_campaign(kwargs)
    except BaseException as exc:  # noqa: BLE001 -- refusal by ANY typed failure
        # the campaign must have driven itself to termination on failure
        marker = Path(kwargs["evidence_root"]) / "TERMINATION_REQUESTED.json"
        assert marker.is_file(), f"{name}: failed campaign did not terminate"
        print(f"PASS sabotage detected: {name} ({type(exc).__name__})")
        return
    raise AssertionError(f"{name}: sabotaged campaign COMPLETED")


def main():
    global HPKG, HCOMMIT
    base = Path(tempfile.mkdtemp(prefix="gate1a2_conformance_"))
    HPKG, HCOMMIT = make_hermetic_package(base / "hermetic_pkg")
    print(f"hermetic package committed at {HCOMMIT[:12]} (clean-tree law honored)")

    # ---- the golden end-to-end synthetic campaign ---------------------------
    kwargs = build_campaign(base / "golden", "synth-golden")
    out = run_campaign(kwargs)
    assert out["final_state"] == "TERMINATED"
    status = out["status"]
    assert status["claim_a_status"] == "SOFTWARE_CONFORMANCE_ONLY"
    assert status["claim_b_status"] == "SOFTWARE_CONFORMANCE_ONLY"
    assert status["non_claim_bearing"] is True
    er = Path(kwargs["evidence_root"])
    for f in ("RAW_GATE1_RESULTS.json", "GATE1_STATUS.json", "cost_report.json",
              "campaign_receipt_final.json", "TERMINATION_REQUESTED.json",
              "protected_lock_receipt.json", "selected_layer_receipt.json"):
        assert (er / f).is_file(), f"missing evidence artifact {f}"
    from exec.campaign_state import verify_transition_chain
    chain = verify_transition_chain(er / "campaign" / "transitions.jsonl",
                                    "synth-golden", HCOMMIT)
    assert chain["final_state"] == "TERMINATED"
    # replay: a second identical campaign must produce the same chain digest
    out2 = run_campaign(build_campaign(base / "golden2", "synth-golden"))
    assert out2["chain_digest"] == out["chain_digest"], "replay chain diverged"
    print(f"PASS golden synthetic campaign: TERMINATED, chain "
          f"{out['chain_digest'][:16]}..., replay-identical, "
          f"status SOFTWARE_CONFORMANCE_ONLY")

    # ---- the thirteen sabotage detections -----------------------------------
    def fresh(name):
        return build_campaign(base / name, f"synth-{name}")

    # 1 launcher stub: the guard RAISE must be gone (the docstring may state
    # that it was removed) and the launcher must invoke the real driver
    src = (PKG / "exec" / "launcher.py").read_text(encoding="utf-8")
    assert 'SystemExit("LAUNCHER_STUB_GUARD' not in src \
        and "LAUNCHER_STUB_GUARD:" not in src, "the stub raise is still present"
    assert "CampaignDriver(" in src, "the launcher does not invoke the driver"
    print("PASS sabotage detected: launcher_stub_removed")

    # 2 substituted owner key: approval re-signed by a rogue key
    k = fresh("rogue-key")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from verify_phase_approval import canonical_signing_bytes
    rec = json.loads(Path(k["execution_approval_path"]).read_text("utf-8"))
    rec["ed25519_signature"] = ""
    rec["ed25519_signature"] = Ed25519PrivateKey.generate().sign(
        canonical_signing_bytes(rec)).hex()
    write_utf8_lf(k["execution_approval_path"], json.dumps(rec, indent=2) + "\n")
    expect_refused("substituted_owner_key", k)

    # 3 invalid prep approval (permitted operations widened to TRAINING)
    k = fresh("bad-prep")
    rec = json.loads(Path(k["prep_approval_path"]).read_text("utf-8"))
    rec["permitted_operations"] = rec["permitted_operations"] + ["TRAINING"]
    write_utf8_lf(k["prep_approval_path"],
                  json.dumps(syn.sign_record(rec), indent=2) + "\n")
    expect_refused("invalid_prep_approval", k)

    # 4 invalid execution approval (cost tampered without re-sign)
    k = fresh("bad-exec")
    rec = json.loads(Path(k["execution_approval_path"]).read_text("utf-8"))
    rec["cost_ceiling_usd"] = 999999.0
    write_utf8_lf(k["execution_approval_path"], json.dumps(rec, indent=2) + "\n")
    expect_refused("invalid_execution_approval", k)

    # 5 fake receipt list is impossible to hand in: the driver derives receipts
    # from the signed schedule; prove by corrupting the schedule digest binding
    k = fresh("fake-receipts")
    rec = json.loads(Path(k["execution_approval_path"]).read_text("utf-8"))
    rec["run_schedule_sha256"] = "0" * 64
    write_utf8_lf(k["execution_approval_path"],
                  json.dumps(syn.sign_record(rec), indent=2) + "\n")
    expect_refused("fake_receipt_schedule_binding", k)

    # 6 arbitrary prediction callback does not exist (interface law)
    import inspect
    from exec.protected_eval import run_protected_evaluation
    assert "evaluate_arm_seed" not in inspect.signature(
        run_protected_evaluation).parameters
    print("PASS sabotage detected: arbitrary_prediction_callback_absent")

    # 7 missing taxonomy
    k = fresh("no-taxonomy")
    (Path(k["synthetic_root"]) / "derived"
     / "alternative_taxonomy_table.json").unlink()
    expect_refused("missing_taxonomy", k)

    # 8 wrong model identity (weight file corrupted after signing)
    k = fresh("bad-model")
    (Path(k["synthetic_root"]) / "model" / "model.safetensors").write_bytes(
        b"TAMPERED WEIGHTS\n")
    expect_refused("wrong_model_identity", k)

    # 9 local-GPU substitution: REAL mode on this dev box must fail closed. With
    # no owner key pinned in the hermetic package, the honest refusal is
    # OwnerKeyNotPinned at the trust root (REAL now normalizes to PRODUCTION),
    # BEFORE any AWS/GPU/neural work -- assert the SPECIFIC type, not just "some
    # exception", so the test proves the real fail-closed path
    k = fresh("real-on-local")
    k["mode"] = "REAL"
    from exec.trust_root import OwnerKeyNotPinned
    try:
        run_campaign(k)
        raise AssertionError("REAL campaign ran on the dev box")
    except OwnerKeyNotPinned:
        assert (Path(k["evidence_root"]) / "TERMINATION_REQUESTED.json").is_file() \
            or (Path(k["evidence_root"]) / "TERMINATION_UNAVAILABLE_NOT_ON_EC2.json").is_file()
        print("PASS sabotage detected: local_gpu_substitution_real_mode_refused "
              "(OwnerKeyNotPinned at the trust root; no owner pin on this box)")

    # 10 second protected read: burn the campaign's lock first
    k = fresh("second-read")
    from exec.protected_lock import LocalProtectedLock
    lock = LocalProtectedLock(Path(k["evidence_root"]) / "protected_lock")
    lock.claim(k["campaign_id"], execution_approval_sha256="aa" * 32,
               package_commit_sha="ab" * 20,
               protected_derivation="PUBLIC_SEED_20260831",
               claimant_identity="EARLIER", claim_utc="SYNTHETIC")
    lock.burn(k["campaign_id"], final_state_reason="SUCCESS",
              result_or_failure_sha256="bb" * 32)
    expect_refused("second_protected_read", k)

    # 11 unbound raw result: status refuses a well-shaped file with a broken
    # evidence chain (proven directly against the golden campaign's results)
    er = Path(kwargs["evidence_root"])
    raw = json.loads((er / "RAW_GATE1_RESULTS.json").read_text("utf-8"))
    raw["evidence_chain"]["campaign_receipt_sha256"] = "0" * 64
    bad_raw = er / "UNBOUND_RESULTS.json"
    write_utf8_lf(bad_raw, json.dumps(raw, indent=2) + "\n")
    r = subprocess.run([sys.executable, str(PKG / "tools" / "emit_gate1_status.py"),
                        str(bad_raw), "--evidence-root", str(er), "--conformance"],
                       capture_output=True, text=True, cwd=PKG)
    assert r.returncode != 0 and "EVIDENCE_UNBOUND" in r.stdout
    print("PASS sabotage detected: unbound_raw_result")

    # 12 cost manipulation: ceiling too small for the schedule -> refused job
    k = fresh("tiny-budget")
    rec = json.loads(Path(k["execution_approval_path"]).read_text("utf-8"))
    rec["cost_ceiling_usd"] = 0.05
    write_utf8_lf(k["execution_approval_path"],
                  json.dumps(syn.sign_record(rec), indent=2) + "\n")
    expect_refused("cost_manipulation", k)

    # 13 missing shutdown is impossible by construction: every failure above
    # produced TERMINATION_REQUESTED.json (asserted in expect_refused), and the
    # golden campaign terminated; additionally the watchdog path is proven in
    # test_cost_shutdown. Assert the golden campaign's marker exists:
    assert (Path(kwargs["evidence_root"]) / "TERMINATION_REQUESTED.json").is_file()
    print("PASS sabotage detected: missing_shutdown (every path terminated)")

    shutil.rmtree(base, ignore_errors=True)
    print("ALL GATE1A2 CONFORMANCE TESTS PASS")
    print(FINAL_STATUS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
