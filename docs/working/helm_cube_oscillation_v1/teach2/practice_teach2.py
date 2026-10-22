"""Builder tool (NOT in the sealed package): one PRACTICE round of TEACH-2 on practice worlds (never the sealed ones;
A-TEACH2-18 P12).

    python -X utf8 -B practice_teach2.py --out <scratch folder> [--worlds 4] [--skip-suites]
                                         [--ctt-python C:/Users/wakil/venvs/cas-gpu/Scripts/python.exe] [--pkg <folder>]

Builds the practice exam at the practice seed texts, runs the cut check, HELM's suites from a copy of helm_now/, the route
check, the pool (11 arms x N worlds; VERBATIM_ONLY first, then the limits, then the rest; the CTT on the laptop's own
GPU through --ctt-python, the house rule's smoke/dev use), then the frozen reader. A practice reading is INCONCLUSIVE by
I0 by construction; `practice_view` says which word the marks would print if the seal rows held. Decides nothing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_PKG = Path(r"C:\Users\wakil\Documents\Codex\2026-10-22\teach2\HELM_TEACH2_20261022")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--worlds", type=int, default=4)
    ap.add_argument("--skip-suites", action="store_true")
    ap.add_argument("--ctt-python", default=None)
    ap.add_argument("--pkg", default=str(DEFAULT_PKG))
    a = ap.parse_args()
    pkg = Path(a.pkg)
    sys.path.insert(0, str(pkg))
    from teach2 import common_t2 as C
    from teach2 import exam_t2 as E
    from teach2 import seed_rule_t2 as SR
    py = [sys.executable, "-X", "utf8", "-B", "-I"]
    run_py, reader_py = str(pkg / "teach2" / "run_t2.py"), str(pkg / "teach2" / "reader_t2.py")
    out = Path(a.out)
    exam, run = out / "exam", out / "run"
    run.mkdir(parents=True, exist_ok=True)
    print(json.dumps(E.build_exam(SR.practice_seeds(), exam, practice=True, count=a.worlds)["pins"]), flush=True)
    subprocess.run(py + [run_py, "cutcheck", "--out", str(run)], check=True)
    subprocess.run(py + [run_py, "routecheck", "--exam", str(exam), "--out", str(run)])
    if not a.skip_suites:
        subprocess.run(py + [run_py, "suites", "--out", str(run)])
    subprocess.run(py + [run_py, "pool", "--exam", str(exam), "--out", str(run)] +
                   (["--ctt-python", a.ctt_python] if a.ctt_python else []))
    mi = {"schema": "helm.teach2.merge-input/1", "run_dir": str(run), "exam_dir": str(exam), "practice_mock": True}
    C.write_json(out / "MERGE_INPUT_TEACH2.json", mi)
    subprocess.run(py + [reader_py, "--merge-input", str(out / "MERGE_INPUT_TEACH2.json"), "--out", str(out / "TEACH2_READING.json")])


if __name__ == "__main__":
    main()
