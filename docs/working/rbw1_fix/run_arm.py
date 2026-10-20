"""Run one RB-W1T harness unit (main or nh) against a CHOSEN HELM folder (builder practice only; never the exam).

    python -X utf8 -I -B run_arm.py <RB-W1T package dir> <helm dir> main <arm> <inputs json> <out json>
    python -X utf8 -I -B run_arm.py <RB-W1T package dir> <helm dir> nh <W5P_E64|W5P_F64> <arm> <out json>

The harness code is the sealed package's own (rbw1t.arms_rbw1t), unchanged; only `helm_dir` is pointed at <helm dir>
(for OFF_BASE it stays the package's helm_base). Each unit is its own process.
"""
import json
import sys
import time
from pathlib import Path

PKG, HELM = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(PKG))
from rbw1t import arms_rbw1t as A      # noqa: E402
from rbw1t import common_rbw1t as C    # noqa: E402
from rbw1t import netguard             # noqa: E402

_orig = A.helm_dir
A.helm_dir = lambda which: _orig(which) if which == "base" else HELM


def main():
    netguard.install()
    import os
    os.environ.pop("HELM_WIDE_BRAIN", None)
    t0 = time.time()
    if sys.argv[3] == "main":
        arm, inputs, out = sys.argv[4], sys.argv[5], sys.argv[6]
        doc = A.run_main(inputs, C.sha256_file(inputs), arm)
    else:
        fkey, arm, out = sys.argv[4], sys.argv[5], sys.argv[6]
        doc = A.run_nh(fkey, arm, str(PKG / "nh_fixtures" / C.NH_FILES[fkey]["file"]))
    doc["helm_dir_used"] = str(HELM)
    doc["seconds"] = round(time.time() - t0, 3)
    sha = C.write_json(Path(out), doc)
    print(json.dumps({"out": out, "sha256": sha, "seconds": doc["seconds"]}))


if __name__ == "__main__":
    main()
