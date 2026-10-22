"""Builder tool (NOT in the sealed package): assemble the TEACH-2 package folder (A-TEACH2-18 P1).

    python -X utf8 -B docs/working/helm_cube_oscillation_v1/teach2/assemble_teach2.py --commit <sha> [--out <folder>]
    (run from the repository root)

1. helm_now/  HELM cut by `git show <commit>:<path>` (never the working tree). List = wave 7 v8's cut + every helm_*.py /
   test_helm_*.py at the commit + the compiler of record + the Atlas + the cube store's modules + the exam-side rule
   reader the cube tests import (docs/working/helm_cube_oscillation_v1/teach2_rule_reader.py). Writes
   helm_now/SOURCE_CUT.json and contract/HELM_CUT_TEACH2.json (byte-identical), with the pinned files of I3.
2. brain/HELM_R1_W1_20261015_v3/  the wave-1 brain package: its PACKAGE_FREEZE.json (sha256 checked) and every member.
3. ctt/  from the SEALED CUBE TRAIN zip (sha256 checked): helm_cas_translator/ and cube_task/ byte for byte, and
   data/vocab.json as ctt/vocab.json; ctt/weights/<copy>.pt = the c57 final weights, each checked against its pin.
4. teach2/, tests_teach2/, contract/*.md, README_TEACH2.md  from pkg_src/ (this folder).
Re-running replaces the package folder's parts; nothing outside it is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "pkg_src"
DEFAULT_OUT = Path(r"C:\Users\wakil\Documents\Codex\2026-10-22\teach2\HELM_TEACH2_20261022")
V8_CUT = "docs/working/r1_wave7/HELM_CUT_R1W7_v8.json"
TOOLS = ("noetic-compass-scaffold/noetic-compass/api/__init__.py",
         "noetic-compass-scaffold/noetic-compass/api/notation/__init__.py",
         "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
         "docs/working/noetic_council/continuity_build_v2/atlas.py",
         "docs/working/noetic_council/cube_store/cube.py",
         "docs/working/noetic_council/cube_store/operations.py",
         "docs/working/noetic_council/cube_store/store.py",
         "docs/working/noetic_council/cube_store/turn.py",
         "docs/working/noetic_council/cube_store/test_all.py",
         "docs/working/helm_cube_oscillation_v1/teach2_rule_reader.py")
PINNED = ("helm_brain_canonical.py", "helm_brain_wide.py", "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
          "helm_memory.py", "helm_memory_compact.py", "helm_chat.py", "helm_cube_osc.py", "helm_eye_act.py",
          "helm_cold_cloud.py")
BRAIN = Path(r"C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3")
BRAIN_FREEZE_SHA = "8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b"
CUBE_ZIP = Path(r"C:\Users\wakil\Documents\Codex\2026-10-22\cube_train\HELM_CUBE_TRAIN_20261022_SOURCE.zip")
CUBE_ZIP_SHA = "706e1fa6f3ce77ae4fee7a21cbb05b820c87f8a01c5df237858f81545eb2e899"
C57_RUNS = Path(r"C:\Users\wakil\Documents\Codex\2026-10-22\cube_train\c57_result\c57_out\cube_out\runs")
WEIGHTS = {"A4-s1": "c39eafb6db92845a463a0c6bc711c73d45ddcb482b5e5eaffad466f337d7a69a",
           "A4-s2": "3bfbf1f064e4dd96980bfa971cbd089706a4b99cfdaba0b84324f4a4b3a883ee",
           "A4-s3": "6418ef1e27ffd18df9f571e9f5410af1afae6843d9d56cbcb01d31ccf947564b",
           "A5-s1": "07a54adcdb58cfb746f35e0d4350a9bde536eb72f97d6b29451960313fca4bc1"}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def fresh(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)


def cut(commit: str, pkg: Path) -> dict:
    v8 = json.loads(git("show", f"{commit}:{V8_CUT}"))
    names = set(v8["files"])
    for p in git("ls-tree", "--name-only", commit).decode().splitlines():
        if (p.startswith("helm_") and p.endswith(".py")) or (p.startswith("test_helm_") and p.endswith(".py")):
            names.add(p)
    names.update(TOOLS)
    hn = pkg / "helm_now"
    fresh(hn)
    files = {}
    for rel in sorted(names):
        raw = git("show", f"{commit}:{rel}")
        dest = hn / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        files[rel] = {"sha256": sha(raw), "bytes": len(raw)}
    doc = {"schema": "helm.teach2.source-cut/1", "commit": commit,
           "rule": "git show <commit>:<path> for every file (never the working tree); list = wave 7 v8's cut + every "
                   "helm_*.py / test_helm_*.py at the commit + the compiler of record + the Atlas + the cube store's "
                   "modules + the exam-side rule reader the cube tests import; helm_ui/ and helm_hub/ are not cut",
           "files": files, "pinned": {rel: files[rel]["sha256"] for rel in PINNED}, "not_cut": ["helm_ui/", "helm_hub/"]}
    data = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("ascii")
    (hn / "SOURCE_CUT.json").write_bytes(data)
    (pkg / "contract").mkdir(parents=True, exist_ok=True)
    (pkg / "contract" / "HELM_CUT_TEACH2.json").write_bytes(data)
    return {"commit": commit, "files": len(files), "cut_sha256": sha(data)}


def brain(pkg: Path) -> dict:
    fz = (BRAIN / "PACKAGE_FREEZE.json").read_bytes()
    if sha(fz) != BRAIN_FREEZE_SHA:
        raise SystemExit("the wave-1 brain's freeze changed: refuse")
    dest = pkg / "brain" / BRAIN.name
    fresh(dest)
    members = json.loads(fz)["members"]
    for rel, pin in members.items():
        raw = (BRAIN / rel).read_bytes()
        if sha(raw) != pin["sha256"]:
            raise SystemExit(f"brain member {rel} differs from its freeze: refuse")
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_bytes(raw)
    (dest / "PACKAGE_FREEZE.json").write_bytes(fz)
    return {"members": len(members), "freeze_sha256": BRAIN_FREEZE_SHA}


def ctt(pkg: Path) -> dict:
    if sha(CUBE_ZIP.read_bytes()) != CUBE_ZIP_SHA:
        raise SystemExit("the CUBE TRAIN zip is not the sealed one: refuse")
    dest = pkg / "ctt"
    fresh(dest)
    n = 0
    with zipfile.ZipFile(CUBE_ZIP) as z:
        for info in z.infolist():
            parts = info.filename.split("/", 1)
            if len(parts) != 2 or info.is_dir():
                continue
            rel = parts[1]
            if rel.startswith(("helm_cas_translator/", "cube_task/")) and "__pycache__" not in rel:
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                (dest / rel).write_bytes(z.read(info))
                n += 1
            elif rel == "data/vocab.json":
                (dest / "vocab.json").write_bytes(z.read(info))
                n += 1
    (dest / "weights").mkdir()
    for copy, want in WEIGHTS.items():
        raw = (C57_RUNS / copy / "final.pt").read_bytes()
        if sha(raw) != want:
            raise SystemExit(f"{copy} weights differ from the pin: refuse")
        (dest / "weights" / f"{copy}.pt").write_bytes(raw)
    return {"files_from_cube_train_zip": n, "weights": len(WEIGHTS)}


def harness(pkg: Path) -> dict:
    n = 0
    for sub in ("teach2", "tests_teach2"):
        fresh(pkg / sub)
        for p in sorted((SRC / sub).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                d = pkg / sub / p.relative_to(SRC / sub)
                d.parent.mkdir(parents=True, exist_ok=True)
                d.write_bytes(p.read_bytes())
                n += 1
    for p in sorted((SRC / "contract").glob("*.md")):
        (pkg / "contract" / p.name).write_bytes(p.read_bytes())
        n += 1
    for name in ("README_TEACH2.md",):
        if (SRC / name).is_file():
            (pkg / name).write_bytes((SRC / name).read_bytes())
            n += 1
    return {"files": n}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--harness-only", action="store_true", help="refresh teach2/, tests_teach2/, contract/*.md only")
    a = ap.parse_args()
    pkg = Path(a.out)
    pkg.mkdir(parents=True, exist_ok=True)
    out = {"package": str(pkg)}
    if not a.harness_only:
        out["cut"] = cut(git("rev-parse", a.commit).decode().strip(), pkg)
        out["brain"] = brain(pkg)
        out["ctt"] = ctt(pkg)
    out["harness"] = harness(pkg)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
