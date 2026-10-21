"""Builder tool (NOT in the sealed package): write the final preregistration, PACKAGE_FREEZE.json and the deterministic
sealed zip; then test from a fresh extract of the zip.

    python -X utf8 -B seal_teach1.py            (from the repository root; writes beside this file:
                                                 HELM_TEACH1_20261021_SOURCE_TEACH1_v1.zip, PACKAGE_FREEZE_TEACH1.json,
                                                 ZIP_SHA256.txt, AMENDMENT_A_TEACH1_1.sha256, TEST_COUNTS_TEACH1.json)

PREREGISTRATION_TEACH1.md = the pre-code's bytes (checked against 7eef0edc...) + AMENDMENT_A_TEACH1_1.md's bytes.
Members: every file under HELM_TEACH1_20261021/ except PACKAGE_FREEZE.json, __pycache__, *.pyc, *.partial. Sorted
entries, fixed timestamp and permissions; sealed twice, refused unless identical. CRLF in .py / .json / .md is refused
except in helm_now/ files pinned with CRLF by the cut. The helm_now/ cut is checked against contract/HELM_CUT_TEACH1.json.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "HELM_TEACH1_20261021"
PKG = HERE / NAME
ZIP = HERE / f"{NAME}_SOURCE_TEACH1_v1.zip"
STAMP = (2026, 10, 21, 0, 0, 0)
PRECODE = HERE.parent / "PREREGISTRATION_MEMORY_COMPACTION_V1.precode.md"
PRECODE_SHA = "7eef0edc7d342bb0438e4052db646528442badefa92d6bdf31e8485914073bf1"
AMEND = HERE / "AMENDMENT_A_TEACH1_1.md"
sys.path.insert(0, str(PKG))
from teach1 import common_t1 as C  # noqa: E402


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def members():
    cut = C.helm_cut()
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
            if not ok:
                raise SystemExit(f"CRLF in {rel}: refuse (the CRLF trap)")
        out[rel] = {"sha256": sha(raw), "bytes": len(raw)}
    return out


def freeze_doc(mem):
    cut = C.helm_cut()
    return {"schema": "helm.teach1.package-freeze/1", "label": C.LABEL, "package": NAME, "package_version": C.PACKAGE_VERSION,
            "sealed_on": "2026-10-21 (Pacific)", "members": mem, "member_count_excluding_freeze": len(mem),
            "precode_sha256": PRECODE_SHA, "amendment_a_teach1_1_sha256": sha(AMEND.read_bytes()),
            "frozen_teach1_sha256": sha((PKG / "FROZEN_TEACH1.json").read_bytes()),
            "helm_cut_commit": cut["commit"], "helm_cut_files": len(cut["files"]), "helm_cut_pinned": cut["pinned"],
            "wave1_brain_neighbour": C.WAVE1_BRAIN,
            "not_inside": "the wave-1 brain package (beside it, checked by its freeze by helm_brain_canonical), the exam "
                          "(drawn by the custodian after the owner's line), the approval record, the attestation"}


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


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return {"command": [Path(c).name if i == 0 else c for i, c in enumerate(cmd)][1:], "exit": r.returncode,
            "tail": ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-4:]}


def main() -> None:
    pre = PRECODE.read_bytes()
    if sha(pre) != PRECODE_SHA:
        raise SystemExit("the pre-code changed: refuse")
    amend = AMEND.read_bytes()
    if b"\r\n" in amend:
        raise SystemExit("CRLF in the amendment: refuse")
    (HERE / "AMENDMENT_A_TEACH1_1.sha256").write_text(f"{sha(amend)}  {AMEND.name}\n", encoding="ascii", newline="\n")
    (PKG / "PREREGISTRATION_TEACH1.md").write_bytes(pre + amend)
    hc = C.check_helm_cut()
    if not hc["ok"]:
        raise SystemExit(f"helm_now/ does not equal the recorded cut: {hc}")
    shutil.rmtree(PKG / "tests_teach1" / "__pycache__", ignore_errors=True)
    mem = members()
    fb = (json.dumps(freeze_doc(mem), indent=1, sort_keys=True) + "\n").encode("ascii")
    (PKG / "PACKAGE_FREEZE.json").write_bytes(fb)
    z1 = build_zip(fb, mem)
    mem2 = members()
    fb2 = (json.dumps(freeze_doc(mem2), indent=1, sort_keys=True) + "\n").encode("ascii")
    z2 = build_zip(fb2, mem2)
    if z1 != z2 or fb != fb2:
        raise SystemExit("RESEAL_NOT_IDENTICAL")
    ZIP.write_bytes(z1)
    (HERE / "PACKAGE_FREEZE_TEACH1.json").write_bytes(fb)
    zsha = sha(z1)
    (HERE / "ZIP_SHA256.txt").write_text(zsha + "  " + ZIP.name + "\n", encoding="ascii", newline="\n")

    # ---- test from a fresh extract of the sealed zip (outside the repository)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="teach1_seal_"))
    with zipfile.ZipFile(ZIP) as zf:
        zf.extractall(tmp)
    ext = tmp / NAME
    seal = C.package_seal(ext, sha(fb))
    py = [sys.executable, "-X", "utf8", "-B", "-I"]
    runner = str(ext / "teach1" / "run_t1.py")
    out = tmp / "out"
    counts = {"schema": "helm.teach1.test-counts/1", "zip_sha256": zsha, "freeze_sha256": sha(fb),
              "members_rehashed_equal": seal["members_ok"] and seal["sha256_ok"], "members": seal["members"],
              "package_tests": run(py + ["-m", "unittest", "discover", "-s", "tests_teach1", "-t", "."], ext),
              "cutcheck": run(py + [runner, "cutcheck", "--out", str(out)], ext),
              "suites_from_seal": run(py + [runner, "suites", "--out", str(out), "--from-seal"], ext)}
    sys.path.insert(0, str(ext))
    prac = run(py + ["-c", "import sys; sys.path.insert(0, r'%s'); from teach1 import exam_t1 as E, seed_rule_t1 as SR; "
                     "E.build_exam(SR.practice_seeds(), r'%s', practice=True, count=2)" % (ext, out / "exam")], ext)
    counts["practice_exam_from_seal"] = prac
    counts["routecheck_from_seal"] = run(py + [runner, "routecheck", "--exam", str(out / "exam"), "--out", str(out)], ext)
    counts["pool_from_seal_2_worlds"] = run(py + [runner, "pool", "--exam", str(out / "exam"), "--out", str(out)], ext)
    counts["helm_now_unchanged_after"] = C.package_seal(ext, sha(fb))["members_ok"]
    C.write_json(HERE / "TEST_COUNTS_TEACH1.json", counts)
    shutil.rmtree(tmp, ignore_errors=True)
    print(json.dumps({"zip": ZIP.name, "zip_sha256": zsha, "zip_bytes": len(z1), "freeze_sha256": sha(fb),
                      "members": len(mem), "resealed_identical": True,
                      "from_seal": {k: (v["exit"], v["tail"][-1:]) if isinstance(v, dict) and "exit" in v else v
                                    for k, v in counts.items() if k not in ("schema",)}}, indent=1))


if __name__ == "__main__":
    main()
