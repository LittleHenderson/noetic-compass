"""seal_mouth.py -- seal the MOUTH TRAIN v2 package (A-TALK-4 .. A-TALK-11). Standard library only. 0 USD.

    python -X utf8 -B seal_mouth.py <out_dir>

Writes <out_dir>/HELM_MOUTH_TRAIN_20261022_SOURCE.zip (fixed order, fixed timestamps, so the same files give the same
bytes), PACKAGE_FREEZE_MOUTH_TRAIN.json (every file's sha256 + the amendments' sha256) and ZIP_SHA256.txt. Refuses when
a start weight does not match FROZEN_MOUTH.json, when the package tests fail, or when the exam has fewer than the
frozen minimum of replies. Nothing is trained, nothing is spent.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "package_source")
DESIGN = os.path.dirname(HERE)
NAME = "HELM_MOUTH_TRAIN_V2_20261022"
AMENDMENTS = tuple("AMENDMENT_A_TALK_%d.md" % k for k in range(4, 12))
SKIP_DIRS = {"__pycache__", "smoke_out"}
SKIP_FILES = {".gitignore"}
SKIP_DIRS_EXTRA = ("smoke_out",)


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files() -> list:
    out = []
    for dp, dn, fn in os.walk(PKG):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)
        for n in sorted(fn):
            if n not in SKIP_FILES and not n.endswith(".pyc"):
                out.append(os.path.relpath(os.path.join(dp, n), PKG).replace(os.sep, "/"))
    return sorted(out)


def main(argv) -> int:
    out = os.path.abspath(argv[1])
    os.makedirs(out, exist_ok=True)
    fz = json.load(open(os.path.join(PKG, "FROZEN_MOUTH.json"), encoding="utf-8"))
    for m, rec in fz["models"].items():
        w = os.path.join(PKG, "weights", m + ".pt")
        if not os.path.isfile(w) or sha(w) != rec["init_sha256"]:
            raise SystemExit("refused: start weights of %s missing or not the frozen c57 final" % m)
    exam = sum(1 for l in open(os.path.join(PKG, "data", "mouth_exam.jsonl"), encoding="utf-8") if l.strip())
    if exam < fz["exam_min_replies"]:
        raise SystemExit("refused: the exam has %d replies, fewer than %d" % (exam, fz["exam_min_replies"]))
    t = subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "unittest", "discover", "-s", "tests_mouth", "-t", "."],
                       cwd=PKG, capture_output=True, text=True)
    if t.returncode != 0:
        raise SystemExit("refused: package tests fail\n" + t.stderr[-2000:])
    names = files()
    zpath = os.path.join(out, NAME + "_SOURCE.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            info = zipfile.ZipInfo(NAME + "/" + n, date_time=(2026, 10, 22, 0, 0, 0))   # one top folder, as CUBE TRAIN's
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(os.path.join(PKG, n), "rb") as fh:
                z.writestr(info, fh.read())
    zsha = sha(zpath)
    freeze = {"schema": "mouth-train.package-freeze/2", "package": NAME,
              "amendments": {a: sha(os.path.join(DESIGN, a)) for a in AMENDMENTS},
              "files": {n: sha(os.path.join(PKG, n)) for n in names}, "exam_replies": exam,
              "zip": os.path.basename(zpath), "zip_sha256": zsha}
    with open(os.path.join(out, "PACKAGE_FREEZE_MOUTH_TRAIN.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(freeze, fh, indent=1, sort_keys=True)
    with open(os.path.join(out, "ZIP_SHA256.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(zsha + "  " + os.path.basename(zpath) + "\n")
    print(json.dumps({"zip": zpath, "zip_sha256": zsha, "files": len(names), "exam_replies": exam}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
