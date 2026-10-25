"""AWS gain driver — internal notation gain at dose 0.2 for seeds 2 and 3, plus the fixed selector test."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
PY = sys.executable

def run(args):
    r = subprocess.run([PY, "-X", "utf8"] + args, cwd=str(HERE), capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[-2000:]}
    try:
        return json.loads(r.stdout[r.stdout.find("{"):])
    except Exception:
        return {"raw": r.stdout[-1500:]}

out = {}
for seed in ("A4-s2", "A4-s3"):
    out[seed] = run(["dose_nll.py", "--checkpoint", "ckpt_src/%s/step_01000.pt" % seed,
                     "--doses", "0.05,0.1,0.2,0.4,1.0"])
    print(seed, out[seed], flush=True)
out["rpm_select"] = run(["rpm_select.py", "--checkpoint", "ckpt/s1.pt", "--out", "rpm_select.json"])
json.dump(out, open(HERE / "results.json", "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
