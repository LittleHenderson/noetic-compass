"""AWS operator-selector driver — D1 vs D3 across three seeds (CAS-LAB-011)."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
out = {}
for seed in ("A4-s1", "A4-s2", "A4-s3"):
    r = subprocess.run([sys.executable, "-X", "utf8", "rpm_select.py", "--checkpoint", "ckpt/%s.pt" % seed,
                        "--out", "sel_%s.json" % seed], cwd=str(HERE), capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        out[seed] = {"error": (r.stderr or r.stdout)[-3000:]}
    else:
        try:
            out[seed] = json.loads(r.stdout[r.stdout.find("{"):])
        except Exception:
            out[seed] = {"raw": r.stdout[-2000:]}
    print(seed, json.dumps(out[seed])[:400], flush=True)
json.dump(out, open(HERE / "results.json", "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
