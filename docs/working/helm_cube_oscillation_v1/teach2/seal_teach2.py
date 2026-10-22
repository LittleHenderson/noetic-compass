"""Builder tool (NOT in the sealed package): write the final preregistration, PACKAGE_FREEZE.json and the deterministic
sealed zip of TEACH-2; then test from a fresh extract (A-TEACH2-18 P13).

    python -X utf8 -B docs/working/helm_cube_oscillation_v1/teach2/seal_teach2.py [--ctt-python <python with torch>]

PREREGISTRATION_TEACH2.md = the pre-code's bytes (checked against f7b6183b...) + the bytes of amendments A-TEACH2-1 to
-19 in order (each checked against its .sha256 file). Members: every file under the package folder except
PACKAGE_FREEZE.json, __pycache__, *.pyc, *.partial. Sorted entries, fixed timestamp and permissions; sealed twice, refused
unless identical. CRLF in .py / .json / .md is refused except in helm_now/ files pinned with CRLF by the cut. The zip and
its records go beside the package folder (Documents/Codex/2026-10-22/teach2/); the records are copied to sealed/ in the
repository (the zip is too large for git). From a fresh extract: the package tests, the cut and CTT check, HELM's suites,
a practice exam of 2 worlds, the route check, and the pool on 1 world with every arm (the CTT on the laptop's GPU).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent
NAME = "HELM_TEACH2_20261022"
OUTDIR = Path(r"C:\Users\wakil\Documents\Codex\2026-10-22\teach2")
PKG = OUTDIR / NAME
ZIP = OUTDIR / f"{NAME}_SOURCE.zip"
STAMP = (2026, 10, 22, 0, 0, 0)
PRECODE = PACKET / "PREREGISTRATION_TEACH2.precode.md"
PRECODE_SHA = "f7b6183bba5f8a1a241e3c64c8930f6a2c6df06fbe8c5845c0207f6d2a84c855"
AMENDS = [PACKET / f"AMENDMENT_A_TEACH2_{i}.md" for i in range(1, 20)]
SEALED = HERE / "sealed"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def members(cut):
    out = {}
    for p in sorted(PKG.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix == ".pyc" or p.name.endswith(".partial"):
            continue
        rel = p.relative_to(PKG).as_posix()
        if rel == "PACKAGE_FREEZE.json":
            continue
        raw = p.read_bytes()
        if b"\r\n" in raw and p.suffix in (".py", ".json", ".md"):
            ok = rel.startswith("helm_now/") and cut["files"].get(rel[len("helm_now/"):], {}).get("sha256") == sha(raw)
            ok = ok or rel.startswith("brain/")
            if not ok:
                raise SystemExit(f"CRLF in {rel}: refuse (the CRLF trap)")
        out[rel] = {"sha256": sha(raw), "bytes": len(raw)}
    return out


def freeze_doc(C, mem, amend_shas):
    cut = C.helm_cut()
    return {"schema": "helm.teach2.package-freeze/1", "label": C.LABEL, "package": NAME, "package_version": C.PACKAGE_VERSION,
            "sealed_on": "2026-10-22 (Pacific)", "members": mem, "member_count_excluding_freeze": len(mem),
            "precode_sha256": PRECODE_SHA, "amendments_sha256": amend_shas,
            "frozen_teach2_sha256": sha((PKG / "FROZEN_TEACH2.json").read_bytes()),
            "helm_cut_commit": cut["commit"], "helm_cut_files": len(cut["files"]), "helm_cut_pinned": cut["pinned"],
            "ctt_weights_sha256": C.CTT_WEIGHTS_SHA256, "cube_train_zip_sha256": C.CUBE_TRAIN_ZIP_SHA256,
            "wave1_brain": C.WAVE1_BRAIN,
            "not_inside": "the exam (drawn by the custodian after the seal), the approval record, the attestation"}


def build_zip(freeze_bytes, mem):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in sorted(list(mem) + ["PACKAGE_FREEZE.json"]):
            data = freeze_bytes if rel == "PACKAGE_FREEZE.json" else (PKG / rel).read_bytes()
            info = zipfile.ZipInfo(f"{NAME}/{rel}", date_time=STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3
            zf.writestr(info, data)
    return buf.getvalue()


def run(cmd, cwd, timeout=3600):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return {"command": [Path(c).name if i == 0 else c for i, c in enumerate(cmd)][1:], "exit": r.returncode,
            "tail": ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-4:]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ctt-python", default=None)
    a = ap.parse_args()
    sys.path.insert(0, str(PKG))
    from teach2 import common_t2 as C
    pre = PRECODE.read_bytes()
    if sha(pre) != PRECODE_SHA:
        raise SystemExit("the pre-code changed: refuse")
    body, amend_shas = pre, {}
    for p in AMENDS:
        raw = p.read_bytes()
        want = (p.with_suffix(".sha256")).read_text(encoding="ascii").split()[0]
        if sha(raw) != want or b"\r\n" in raw:
            raise SystemExit(f"{p.name} differs from its .sha256 or has CRLF: refuse")
        amend_shas[p.stem] = want
        body += raw
    (PKG / "PREREGISTRATION_TEACH2.md").write_bytes(body)
    hc = C.check_helm_cut()
    if not hc["ok"] or not C.check_ctt()["ok"]:
        raise SystemExit(f"helm_now/ or the CTT weights do not equal their pins: {hc}")
    for d in ("teach2", "tests_teach2"):
        shutil.rmtree(PKG / d / "__pycache__", ignore_errors=True)
    cut = C.helm_cut()
    mem = members(cut)
    fb = (json.dumps(freeze_doc(C, mem, amend_shas), indent=1, sort_keys=True) + "\n").encode("ascii")
    (PKG / "PACKAGE_FREEZE.json").write_bytes(fb)
    z1 = build_zip(fb, mem)
    mem2 = members(cut)
    fb2 = (json.dumps(freeze_doc(C, mem2, amend_shas), indent=1, sort_keys=True) + "\n").encode("ascii")
    z2 = build_zip(fb2, mem2)
    if z1 != z2 or fb != fb2:
        raise SystemExit("RESEAL_NOT_IDENTICAL")
    ZIP.write_bytes(z1)
    (OUTDIR / "PACKAGE_FREEZE_TEACH2.json").write_bytes(fb)
    zsha = sha(z1)
    (OUTDIR / "ZIP_SHA256.txt").write_text(zsha + "  " + ZIP.name + "\n", encoding="ascii", newline="\n")

    tmp = Path(tempfile.mkdtemp(prefix="teach2_seal_"))
    with zipfile.ZipFile(ZIP) as zf:
        zf.extractall(tmp)
    ext = tmp / NAME
    seal = C.package_seal(ext, sha(fb))
    py = [sys.executable, "-X", "utf8", "-B", "-I"]
    runner = str(ext / "teach2" / "run_t2.py")
    out = tmp / "out"
    ctt = ["--ctt-python", a.ctt_python] if a.ctt_python else []
    counts = {"schema": "helm.teach2.test-counts/1", "zip_sha256": zsha, "zip_bytes": len(z1), "freeze_sha256": sha(fb),
              "members_rehashed_equal": seal["members_ok"] and seal["sha256_ok"], "members": seal["members"],
              "package_tests": run([sys.executable, "-X", "utf8", "-B", "-m", "unittest", "discover", "-s", "tests_teach2", "-t", "."], ext),
              "cutcheck": run(py + [runner, "cutcheck", "--out", str(out)], ext),
              "suites_from_seal": run(py + [runner, "suites", "--out", str(out), "--from-seal"], ext)}
    counts["practice_exam_from_seal"] = run(py + ["-c", "import sys; sys.path.insert(0, r'%s'); from teach2 import exam_t2 as E, "
                                                  "seed_rule_t2 as SR; E.build_exam(SR.practice_seeds(), r'%s', practice=True, count=2)"
                                                  % (ext, out / "exam")], ext)
    counts["routecheck_from_seal"] = run(py + [runner, "routecheck", "--exam", str(out / "exam"), "--out", str(out)], ext)
    counts["pool_from_seal_1_world_every_arm"] = run(py + [runner, "pool", "--exam", str(out / "exam"), "--out", str(out),
                                                           "--worlds", "W01"] + ctt, ext)
    counts["helm_now_unchanged_after"] = C.package_seal(ext, sha(fb))["members_ok"]
    C.write_json(OUTDIR / "TEST_COUNTS_TEACH2.json", counts)
    SEALED.mkdir(parents=True, exist_ok=True)
    for n in ("PACKAGE_FREEZE_TEACH2.json", "ZIP_SHA256.txt", "TEST_COUNTS_TEACH2.json"):
        shutil.copyfile(OUTDIR / n, SEALED / n)
    shutil.copyfile(PKG / "PREREGISTRATION_TEACH2.md", SEALED / "PREREGISTRATION_TEACH2.md")
    shutil.copyfile(PKG / "contract" / "HELM_CUT_TEACH2.json", SEALED / "HELM_CUT_TEACH2.json")
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"zip": ZIP.name, "zip_sha256": zsha, "zip_bytes": len(z1), "freeze_sha256": sha(fb),
                      "members": len(mem), "resealed_identical": True,
                      "from_seal": {k: (v["exit"], v["tail"][-1:]) if isinstance(v, dict) and "exit" in v else v
                                    for k, v in counts.items() if k not in ("schema",)}}, indent=1))


if __name__ == "__main__":
    main()
