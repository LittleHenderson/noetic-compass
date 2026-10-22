"""Builder tool (NOT in the sealed package): one PRACTICE round of TEACH-1 on practice worlds (never the sealed ones).

    python -X utf8 -B practice_teach1.py --out <scratch folder> [--worlds 16] [--skip-suites]

Builds the practice exam at the practice seed texts (seed_rule_t1.practice_seeds), runs the cut check, HELM's suites
from a copy of helm_now/, the pool (7 arms x N worlds, one process at a time), then the frozen reader. A practice reading
is INCONCLUSIVE by I0 by construction; `practice_view` says which word the marks would print if the seal rows held.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE / "HELM_TEACH1_20261021"
sys.path.insert(0, str(PKG))
from teach1 import common_t1 as C      # noqa: E402
from teach1 import exam_t1 as E        # noqa: E402
from teach1 import seed_rule_t1 as SR  # noqa: E402

PY = [sys.executable, "-X", "utf8", "-B", "-I"]
RUN = str(PKG / "teach1" / "run_t1.py")
READER = str(PKG / "teach1" / "reader_t1.py")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--worlds", type=int, default=C.WORLDS)
    ap.add_argument("--skip-suites", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    exam, run = out / "exam", out / "run"
    run.mkdir(parents=True, exist_ok=True)
    print(json.dumps(E.build_exam(SR.practice_seeds(), exam, practice=True, count=a.worlds)["pins"]))
    subprocess.run(PY + [RUN, "cutcheck", "--out", str(run)], check=True)
    subprocess.run(PY + [RUN, "routecheck", "--exam", str(exam), "--out", str(run)])
    if not a.skip_suites:
        subprocess.run(PY + [RUN, "suites", "--out", str(run)])
    subprocess.run(PY + [RUN, "pool", "--exam", str(exam), "--out", str(run)])
    mi = {"schema": "helm.teach1.merge-input/1", "run_dir": str(run), "exam_dir": str(exam), "practice_mock": True}
    C.write_json(out / "MERGE_INPUT_TEACH1.json", mi)
    subprocess.run(PY + [READER, "--merge-input", str(out / "MERGE_INPUT_TEACH1.json"), "--out", str(out / "TEACH1_READING.json")])


if __name__ == "__main__":
    main()
