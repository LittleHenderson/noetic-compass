"""Builder tool (NOT in the sealed package): freeze and zip HELM_RBW1T_20261019, then test from the sealed extract.

    python -X utf8 -B seal_rbw1t.py <workspace rbw1t dir>

Writes <pkg>/PACKAGE_FREEZE.json, the deterministic zip, ZIP_SHA256.txt, PACKAGE_FREEZE_RBW1T.json (copy), then
extracts the zip to a fresh folder and runs there: every member re-hashed, the RB-W1T suites, HELM's suites (on a
scratch copy of helm_now), plan_check. Writes TEST_COUNTS_RBW1T.json.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

WS = Path(sys.argv[1]).resolve()
PKG = WS / "HELM_RBW1T_20261019"
ZIP = WS / "HELM_RBW1T_20261019_SOURCE_RBW1T.zip"
W1 = r"C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3"


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def sha(p):
    return sha_b(Path(p).read_bytes())


def parse(text):
    summary = re.findall(r'^(OK|FAILED)(?: \(([^)]*)\))?\s*$', text, flags=re.MULTILINE)
    ran = re.findall(r'^Ran ([0-9]+) tests?', text, flags=re.MULTILINE)
    return {"verdict": summary[0][0] if len(summary) == 1 else None, "ran": [int(x) for x in ran],
            "detail": summary[0][1] if len(summary) == 1 else ""}


def main():
    shutil.copyfile(WS / "PREREGISTRATION_RBW1T.md", PKG / "PREREGISTRATION_RBW1T.md")
    for p in list(PKG.rglob("__pycache__")):
        shutil.rmtree(p)
    if (PKG / "helm_now" / "sessions").exists():
        shutil.rmtree(PKG / "helm_now" / "sessions")
    files = sorted(p for p in PKG.rglob("*") if p.is_file() and p.name != "PACKAGE_FREEZE.json")
    members = {p.relative_to(PKG).as_posix(): {"sha256": sha(p), "bytes": p.stat().st_size} for p in files}
    freeze = {"schema": "helm.rbw1t.package-freeze/1", "package": "HELM_RBW1T_20261019", "members": members,
              "member_count": len(members), "package_version": "v2",
              "commit_now": "045548b6a89205f65b419ac95753938ad738f037",
              "commit_base": "045548b6a89205f65b419ac95753938ad738f037 with RB-W1 removed (helm_end_to_end_loop.py at d4488f2a4a32992f6d8f80f24ea8cefe045ac9d7)",
              "supersedes": "v1 zip b50f4ca42178d4c43e43945267cc980aebd05a10f8e0d932d00e3eabd4495809 (VOID_SUPERSEDED_BY_V2, never launched)",
              "precode_preregistration_sha256": (WS / "PREREGISTRATION_RBW1T.precode.sha256").read_text().split()[0],
              "status": "SEALED, NOT LAUNCHED"}
    raw = (json.dumps(freeze, indent=1, sort_keys=True) + "\n").encode("ascii")
    (PKG / "PACKAGE_FREEZE.json").write_bytes(raw)
    fsha = sha_b(raw)
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in sorted(list(members) + ["PACKAGE_FREEZE.json"]):
            info = zipfile.ZipInfo("HELM_RBW1T_20261019/" + rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, (PKG / rel).read_bytes())
    zsha = sha(ZIP)
    (WS / "ZIP_SHA256.txt").write_text(f"{zsha}  {ZIP.name}\n", encoding="ascii", newline="\n")
    shutil.copyfile(PKG / "PACKAGE_FREEZE.json", WS / "PACKAGE_FREEZE_RBW1T.json")
    # ---- test from the sealed extract
    tmp = Path(tempfile.mkdtemp(prefix="rbw1t_seal_test_"))
    with zipfile.ZipFile(ZIP) as zf:
        zf.extractall(tmp)
    ex = tmp / "HELM_RBW1T_20261019"
    bad = [r for r, pin in members.items() if sha(ex / r) != pin["sha256"]]
    env = dict(os.environ, PYTHONPATH=str(ex), PYTHONDONTWRITEBYTECODE="1", HELM_CANONICAL_BRAIN_DIR=W1)
    env.pop("HELM_WIDE_BRAIN", None)
    r1 = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "unittest", "tests_rbw1t.test_units_rbw1t",
                         "tests_rbw1t.test_kit_rbw1t", "-v"], cwd=str(ex), env=env, capture_output=True, text=True,
                        timeout=280)
    hc = tmp / "helm_now_tests"
    shutil.copytree(ex / "helm_now", hc)
    r2 = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "unittest", "test_helm_brain_wide",
                         "test_helm_end_to_end_loop", "test_helm_english_in", "test_helm_english_in_stock_frame",
                         "test_helm_voice", "test_helm_faces_in", "test_helm_triad"], cwd=str(hc),
                        env=dict(env, PYTHONPATH=str(hc)), capture_output=True, text=True, timeout=280)
    stage = ex / "kit" / "STAGE_RBW1T.json"
    r3 = subprocess.run([sys.executable, "-B", str(ex / "kit" / "plan_check.py"), str(stage),
                         str(ex / "kit" / "run_rbw1t.py")], capture_output=True, text=True, timeout=60)
    sealed_untouched = not any((ex / "helm_now").glob("sessions"))
    counts = {"schema": "helm.rbw1t.test-counts/1", "package_zip_sha256": zsha, "package_freeze_sha256": fsha,
              "members": len(members) + 1, "members_rehashed_bad": bad,
              "rbw1t_suites_from_sealed_extract": parse(r1.stderr + r1.stdout),
              "helm_suites_from_sealed_extract_scratch_copy": parse(r2.stderr + r2.stdout),
              "plan_check": json.loads(r3.stdout)["verdict"] if r3.stdout.strip().startswith("{") else r3.stdout[:200],
              "sealed_helm_now_not_written": sealed_untouched,
              "dry_run_summary_sha256": sha(WS / "dry_run" / "DRY_RUN_SUMMARY_RBW1T.json"),
              "reader_classes_sha256": sha(WS / "dry_run_v2_reader_classes.json"),
              "dry_reading_sha256": sha(WS / "dry_run" / "DRY_READING_RBW1T.json")}
    (WS / "TEST_COUNTS_RBW1T.json").write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n", encoding="ascii",
                                               newline="\n")
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps(counts, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
