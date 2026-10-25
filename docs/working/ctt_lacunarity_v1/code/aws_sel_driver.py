"""AWS selector driver — runs the fixed RPM-guided selector test only."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
r = subprocess.run([sys.executable, "-X", "utf8", "rpm_select.py", "--checkpoint", "ckpt/s1.pt",
                    "--out", "rpm_select.json"], cwd=str(HERE), capture_output=True, text=True, timeout=3600)
out = {"rc": r.returncode}
if r.returncode != 0:
    out["error"] = (r.stderr or r.stdout)[-3000:]
else:
    try:
        out["result"] = json.loads(r.stdout[r.stdout.find("{"):])
    except Exception:
        out["raw"] = r.stdout[-2000:]
json.dump(out, open(HERE / "results.json", "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
