"""AWS scoring driver — runs the dose scoring and the RPM selector test in one process.

Expects the payload at the current directory: data/, guard/, ckpt/, and the scoring scripts.
Writes results.json and prints it.

    python aws_score_driver.py --ckpt ckpt/step_01000.pt --out results.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
TAGS = ("baseline", "steered", "steered_d0.05", "steered_d0.1", "steered_d0.2", "steered_d0.4")


def run(args):
    r = subprocess.run([PY, "-X", "utf8"] + args, cwd=str(HERE), capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[-2000:]}
    try:
        return json.loads(r.stdout[r.stdout.find("{"):])
    except Exception:
        return {"raw": r.stdout[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="ckpt/step_01000.pt")
    ap.add_argument("--out", default="results.json")
    a = ap.parse_args()

    out = {"composites": {}, "errors": []}
    sys.path.insert(0, str(HERE))
    from mouth_task import check
    fact = set(json.load(open(HERE / "data" / "FACT_WORDS.json", encoding="utf-8")))
    exam = [json.loads(l) for l in open(HERE / "data" / "mouth_exam.jsonl", encoding="utf-8") if l.strip()]
    for tag in TAGS:
        gen_path = HERE / "guard" / f"gen_A4-s1_{tag}.jsonl"
        rows = [json.loads(l) for l in open(gen_path, encoding="utf-8") if l.strip()]
        if rows and "guard_ok" not in rows[0]:
            for i, r in enumerate(rows):
                ok, why = check.check(exam[i]["situation"], exam[i]["input_text"], r["text"], fact, exam[i].get("reading"))
                r["guard_ok"] = bool(ok); r["guard_why"] = why
            with open(gen_path, "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    for tag in TAGS:
        gen = HERE / "guard" / f"gen_A4-s1_{tag}.jsonl"
        scored = HERE / "guard_scored" / f"A4-s1_{tag}.scored.jsonl"
        scored.parent.mkdir(exist_ok=True)
        r1 = run(["rt_score.py", "--gen", str(gen), "--out", str(scored)])
        if "error" in r1:
            out["errors"].append({"tag": tag, "stage": "rt_score", "detail": r1["error"]})
            continue
        r2 = run(["composite.py", "--scored", str(scored)])
        if "error" in r2:
            out["errors"].append({"tag": tag, "stage": "composite", "detail": r2["error"]})
            continue
        key = [k for k in r2 if k.startswith("A4-s1_")]
        out["composites"][tag] = r2[key[0]] if key else r2
        print("scored", tag, out["composites"][tag], flush=True)

    out["dose_nll"] = run(["dose_nll.py", "--checkpoint", a.ckpt, "--doses", "0.05,0.1,0.2,0.4,1.0"])
    out["rpm_select"] = run(["rpm_select.py", "--checkpoint", a.ckpt, "--out", "rpm_select.json"])
    json.dump(out, open(HERE / a.out, "w", encoding="utf-8"), indent=1)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

