"""Builder tool (NOT in the sealed package): write PACKAGE_FREEZE.json and the deterministic sealed v8 zip.

    python -X utf8 -B -I seal_w7_v8.py     (from r1_wave7/build_v8/build; writes ../HELM_R1_W7_20261020_SOURCE_R1W7_v8.zip,
                                            ../PACKAGE_FREEZE_R1W7_v8.json and ../ZIP_SHA256_v8.txt; seals twice and refuses unless
                                            both are identical)

Members: every file under HELM_R1_W7_20261020/ except PACKAGE_FREEZE.json itself, __pycache__, *.pyc, *.partial. The freeze
carries no wall-clock time, so a re-seal of the same tree gives the same bytes. Zip entries are sorted, stored under
HELM_R1_W7_20261020/, with a fixed timestamp and fixed permissions (wave 6's seal script, this package's names). CRLF in
.py / .json / .md is refused (the CRLF trap) except for HELM cut files pinned with CRLF. Byte copies (the supervisor and
plan check) are checked. The HELM cut is checked against contract/HELM_CUT_R1W7.json before sealing.
"""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "HELM_R1_W7_20261020"
PKG = ROOT / NAME
ZIP = ROOT / f"{NAME}_SOURCE_R1W7_v8.zip"
STAMP = (2026, 10, 20, 0, 0, 0)
sys.path.insert(0, str(PKG))
from r1w7 import common_w7 as C  # noqa: E402

BYTE_COPIES = {"kit/job_supervisor.py": "3b2337ca75b189287c4591ed44671e308d37ef92d043f7bebb37ede77e6a1b01",
               "kit/plan_check.py": "84257a23545bfe87d7d4ef4565feae12adc9c325fa0fff06fefcb626c3301035"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


HELM_CUT = json.loads((PKG / "helm_now" / "SOURCE_CUT.json").read_text(encoding="utf-8"))


def members():
    out = {}
    for p in sorted(PKG.rglob("*")):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix == ".pyc" or p.name.endswith(".partial"):
            continue
        rel = p.relative_to(PKG).as_posix()
        if rel == "PACKAGE_FREEZE.json":
            continue
        raw = p.read_bytes()
        if b"\r\n" in raw and p.suffix in (".py", ".json", ".md"):
            ok = rel.startswith("helm_now/") and HELM_CUT["files"].get(rel[len("helm_now/"):], {}).get("sha256") == sha(raw)
            if not ok:
                raise SystemExit(f"CRLF in {rel}: refuse (the CRLF trap)")
        if rel in BYTE_COPIES and sha(raw) != BYTE_COPIES[rel]:
            raise SystemExit(f"{rel} is not the run-proven byte copy")
        out[rel] = {"sha256": sha(raw), "bytes": len(raw)}
    return out


def freeze_doc(mem):
    return {"schema": "helm.r1w7.package-freeze/1", "label": "R1W7", "package": NAME, "package_version": C.PACKAGE_VERSION,
            "sealed_on": "2026-10-21 (Pacific); v8 reseal (A-R1W7-9 on the reader v7.1 fix)", "members": mem, "member_count_excluding_freeze": len(mem),
            "frozen_r1w7_sha256": sha((PKG / "FROZEN_R1W7.json").read_bytes()),
            "helm_cut_commit": C.HELM_CUT_COMMIT, "helm_cut_files": len(HELM_CUT["files"]),
            "helm_brain_canonical_base": C.HELM_BRAIN_CANONICAL_BASE,
            "neighbours": {k: {"zip_sha256": v["zip_sha256"], "freeze_sha256": v["freeze_sha256"]} for k, v in C.NEIGHBOURS.items()},
            "not_inside": "the five neighbour zips (shipped beside it, checked by freeze), X7 (by its pins), the public frames "
                          "(custodian and reader only), the approval record (written after the owner signs)"}


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


def main():
    if C.PACKAGE_VERSION != "v8":
        raise SystemExit("package is not labelled v8: " + C.PACKAGE_VERSION)
    hc = C.check_helm_cut()
    if not hc["ok"]:
        raise SystemExit(f"helm_now/ does not equal the recorded cut: {hc}")
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
    (ROOT / "PACKAGE_FREEZE_R1W7_v8.json").write_bytes(fb)
    (ROOT / "ZIP_SHA256_v8.txt").write_text(sha(z1) + "  " + ZIP.name + "\n", encoding="ascii", newline="\n")
    print(json.dumps({"zip": ZIP.name, "zip_sha256": sha(z1), "zip_bytes": len(z1), "freeze_sha256": sha(fb),
                      "members": len(mem), "resealed_identical": True}, indent=1))


if __name__ == "__main__":
    main()
