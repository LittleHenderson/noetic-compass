"""test_byte_domain.py -- PERMANENT byte-domain and regeneration-invariance tests.

Owner directive GATE 1A.1R section 6. The freeze at ff6f40f9 was REFUTED because
the package manifest bound working-tree bytes (CRLF, produced by an unpinned
writer) that were not the committed blob bytes (LF, produced by autocrlf at an
early staging). These tests make that entire failure class permanent-detectable
by proving three separate facts about every frozen artifact:

    same logical dataset      (regeneration equality, cross-interpreter)
    same canonical bytes      (LF law; manifest == working tree)
    same committed bytes      (manifest == `git show HEAD:<path>` blob)

The committed-blob tests FAIL by construction under the original ff6f40f9 tree
-- that failing run is the recorded negative fixture.

Named tests (all run by default; --skip-fresh-clone skips the worktree gate):
  test_authority_files_use_lf_bytes
  test_dataset_manifest_has_no_runtime_interpreter_value
  test_regeneration_does_not_modify_frozen_source_tree
  test_second_regeneration_is_byte_identical
  test_build_manifests_check_mode_is_write_free
  test_every_package_manifest_digest_matches_working_tree_bytes
  test_every_package_manifest_digest_matches_committed_blob_bytes
  test_python311_and_python314_dataset_content_digests_match
  test_fresh_clone_package_is_self_consistent
  test_fresh_clone_verify_full_accepts_fully_bound_test_record
  test_clean_checkout_regeneration_leaves_no_diff
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
PY = sys.executable


def sh(args, cwd=PKG, check=True):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"command failed ({args}): {r.stdout}\n{r.stderr}")
    return r


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def repo_prefix() -> str:
    return sh(["git", "rev-parse", "--show-prefix"]).stdout.strip().replace("\\", "/")


def manifest_map():
    return json.loads((PKG / "PACKAGE_MANIFEST.json").read_text("utf-8"))["sha256"]


def tree_snapshot():
    out = {}
    for f in sorted(PKG.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts \
                and "results" not in f.relative_to(PKG).parts:
            out[f.relative_to(PKG).as_posix()] = sha256_bytes(f.read_bytes())
    return out


def test_authority_files_use_lf_bytes():
    offenders = []
    files = list(manifest_map()) + ["PACKAGE_MANIFEST.json",
                                    "OWNER_PHASE_APPROVAL_UNSIGNED.json"]
    for rel in files:
        if b"\r" in (PKG / rel).read_bytes():
            offenders.append(rel)
    assert not offenders, f"CR bytes in frozen files: {offenders}"
    print(f"PASS test_authority_files_use_lf_bytes ({len(files)} files, 0 CR bytes)")


def test_dataset_manifest_has_no_runtime_interpreter_value():
    raw = (PKG / "DATASET_MANIFEST_CANDIDATE.json").read_text("utf-8")
    obj = json.loads(raw)
    assert "generation_interpreter" not in obj, "runtime interpreter field present"
    import platform
    assert platform.python_version() not in raw, \
        "the running interpreter's version string leaked into the frozen manifest"
    for key in ("generator_algorithm", "generator_code_sha256",
                "checker_code_sha256", "compatibility_claim"):
        assert key in obj, f"invariant declaration {key} missing"
    assert obj["generator_algorithm"] == "HashPRNG_SHA256_COUNTER_V1"
    print("PASS test_dataset_manifest_has_no_runtime_interpreter_value")


def test_regeneration_does_not_modify_frozen_source_tree():
    before = tree_snapshot()
    with tempfile.TemporaryDirectory() as td:
        sh([PY, "tools/generate_construction_gold.py", "--output-root", td])
    sh([PY, "tools/generate_construction_gold.py", "--check"])
    assert tree_snapshot() == before, "regeneration mutated the frozen tree"
    print("PASS test_regeneration_does_not_modify_frozen_source_tree")


def test_second_regeneration_is_byte_identical():
    with tempfile.TemporaryDirectory() as ta, tempfile.TemporaryDirectory() as tb:
        sh([PY, "tools/generate_construction_gold.py", "--output-root", ta])
        sh([PY, "tools/generate_construction_gold.py", "--output-root", tb])
        for rel in ("data/candidate/train.jsonl", "data/candidate/val.jsonl",
                    "DATASET_MANIFEST_CANDIDATE.json"):
            a = (Path(ta) / rel).read_bytes()
            b = (Path(tb) / rel).read_bytes()
            assert a == b, f"second regeneration differs at {rel}"
            assert a == (PKG / rel).read_bytes(), \
                f"regenerated {rel} differs from the frozen package copy"
    print("PASS test_second_regeneration_is_byte_identical (and == frozen copy)")


def test_build_manifests_check_mode_is_write_free():
    targets = ["PACKAGE_MANIFEST.json", "GATE1B_CODE_MANIFEST.json",
               "OWNER_PHASE_APPROVAL_UNSIGNED.json"]
    before = {t: (PKG / t).read_bytes() for t in targets}
    r = sh([PY, "tools/build_manifests.py", "--check"])
    assert "BUILD_MANIFESTS_CHECK_PASS" in r.stdout, r.stdout
    for t in targets:
        assert (PKG / t).read_bytes() == before[t], f"--check modified {t}"
    print("PASS test_build_manifests_check_mode_is_write_free")


def test_every_package_manifest_digest_matches_working_tree_bytes():
    bad = [rel for rel, d in manifest_map().items()
           if sha256_bytes((PKG / rel).read_bytes()) != d]
    assert not bad, f"manifest != working tree: {bad}"
    print(f"PASS test_every_package_manifest_digest_matches_working_tree_bytes "
          f"({len(manifest_map())} files)")


def test_every_package_manifest_digest_matches_committed_blob_bytes():
    prefix = repo_prefix()
    bad = []
    entries = dict(manifest_map())
    for extra in ("PACKAGE_MANIFEST.json", "OWNER_PHASE_APPROVAL_UNSIGNED.json"):
        entries[extra] = sha256_bytes((PKG / extra).read_bytes())
    for rel, want in sorted(entries.items()):
        r = subprocess.run(["git", "show", f"HEAD:{prefix}{rel}"],
                           cwd=PKG, capture_output=True)
        blob = sha256_bytes(r.stdout) if r.returncode == 0 else "MISSING_IN_HEAD"
        if blob != want:
            bad.append(f"{rel}: committed blob {blob[:16]}... != expected {want[:16]}...")
    assert not bad, "manifest != committed blobs:\n  " + "\n  ".join(bad)
    print(f"PASS test_every_package_manifest_digest_matches_committed_blob_bytes "
          f"({len(entries)} files)")


def find_python(spec):
    for cand in spec:
        try:
            r = subprocess.run([*cand, "-c", "import sys;print(sys.version_info[:2])"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                return list(cand), r.stdout.strip()
        except OSError:
            continue
    return None, None


def test_python311_and_python314_dataset_content_digests_match():
    py311, v = find_python([("py", "-3.11"), ("python3.11",)])
    if py311 is None:
        print("SKIP test_python311_and_python314_dataset_content_digests_match "
              "(no local 3.11; the Gate 1B container gate covers it)")
        return
    r1 = sh([*py311, "tools/generate_construction_gold.py", "--check"])
    assert "GENERATOR_CHECK_PASS" in r1.stdout, f"3.11 check failed: {r1.stdout}"
    r2 = sh([PY, "tools/generate_construction_gold.py", "--check"])
    assert "GENERATOR_CHECK_PASS" in r2.stdout, f"current-interpreter check failed"
    print(f"PASS test_python311_and_python314_dataset_content_digests_match "
          f"(3.11 {v} and {sys.version.split()[0]} both byte-match the freeze)")


def fresh_worktree():
    wt = Path(tempfile.mkdtemp(prefix="g1a1r_freshclone_")) / "wt"
    sh(["git", "worktree", "add", "--detach", "--no-checkout", str(wt), "HEAD"])
    sh(["git", "-C", str(wt), "sparse-checkout", "set",
        "cas_only_reasoner/cjt_gate1a_static_neural_v1"])
    # --no-checkout leaves the worktree index empty, so a pathspec checkout has
    # nothing to match; reset --hard populates index + files per the sparse cone
    sh(["git", "-C", str(wt), "reset", "--hard", "HEAD"])
    return wt, wt / "cas_only_reasoner" / "cjt_gate1a_static_neural_v1"


def drop_worktree(wt: Path):
    subprocess.run(["git", "worktree", "remove", "--force", str(wt)],
                   cwd=PKG, capture_output=True)
    shutil.rmtree(wt.parent, ignore_errors=True)


def run_fresh_clone_gate():
    wt, wpkg = fresh_worktree()
    try:
        mm = json.loads((wpkg / "PACKAGE_MANIFEST.json").read_text("utf-8"))["sha256"]
        bad = [rel for rel, d in mm.items()
               if sha256_bytes((wpkg / rel).read_bytes()) != d]
        assert not bad, f"fresh-clone manifest mismatch: {bad}"
        cm = json.loads((wpkg / "GATE1B_CODE_MANIFEST.json").read_text("utf-8"))["sha256"]
        bad = [rel for rel, d in cm.items()
               if sha256_bytes((wpkg / rel).read_bytes()) != d]
        assert not bad, f"fresh-clone code-manifest mismatch: {bad}"
        print("PASS test_fresh_clone_package_is_self_consistent "
              f"({len(mm)} + {len(cm)} entries verified in a pristine checkout)")

        r = sh([PY, "tools/generate_construction_gold.py", "--check"], cwd=wpkg)
        assert "GENERATOR_CHECK_PASS" in r.stdout
        r = sh([PY, "tools/build_manifests.py", "--check"], cwd=wpkg)
        assert "BUILD_MANIFESTS_CHECK_PASS" in r.stdout
        r = sh([PY, "tools/independent_roundtrip_checker.py",
                "data/candidate/train.jsonl", "data/candidate/val.jsonl"], cwd=wpkg)
        assert "ALL ROUNDTRIPS PASS" in r.stdout

        # the fully-bound test-key record against the pristine tree (mechanism
        # proof; production pins the OWNER's key) -- includes the untracked-file
        # and tamper suite, and requires verify_full to ACCEPT the bound record
        r = sh([PY, "tools/test_authority_verifier.py"], cwd=wpkg)
        assert "ALL AUTHORITY-VERIFIER TESTS PASS" in r.stdout
        print("PASS test_fresh_clone_verify_full_accepts_fully_bound_test_record")

        # full regeneration inside the pristine checkout must leave ZERO diff
        sh([PY, "tools/generate_construction_gold.py"], cwd=wpkg)
        sh([PY, "tools/run_surface_baselines.py"], cwd=wpkg)
        sh([PY, "tools/audit_candidate_occurrence.py"], cwd=wpkg)
        sh([PY, "tools/build_manifests.py"], cwd=wpkg)
        porcelain = sh(["git", "-C", str(wt), "status", "--porcelain"]).stdout.strip()
        assert porcelain == "", f"regeneration dirtied the pristine checkout:\n{porcelain}"
        print("PASS test_clean_checkout_regeneration_leaves_no_diff "
              "(git status --porcelain empty after full regeneration)")
    finally:
        drop_worktree(wt)


def main():
    skip_fresh = "--skip-fresh-clone" in sys.argv
    test_authority_files_use_lf_bytes()
    test_dataset_manifest_has_no_runtime_interpreter_value()
    test_build_manifests_check_mode_is_write_free()
    test_every_package_manifest_digest_matches_working_tree_bytes()
    test_every_package_manifest_digest_matches_committed_blob_bytes()
    test_regeneration_does_not_modify_frozen_source_tree()
    test_second_regeneration_is_byte_identical()
    test_python311_and_python314_dataset_content_digests_match()
    if not skip_fresh:
        run_fresh_clone_gate()
    else:
        print("SKIPPED fresh-clone gate (--skip-fresh-clone)")
    print("ALL BYTE-DOMAIN TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
