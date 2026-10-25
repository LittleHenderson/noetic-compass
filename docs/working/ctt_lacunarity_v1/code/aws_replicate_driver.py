"""AWS replication driver — dose 0.20 on seeds A4-s2 and A4-s3, plus the fixed RPM selector test on A4-s1.

Expects: data/, ckpt/{s1,s2,s3}.pt, weights/A4-s1.pt, and the scripts. Writes results.json.

    python aws_replicate_driver.py --out results.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
SEEDS = ("A4-s2", "A4-s3")
DOSES = ("0", "0.2")


def run(args, timeout=3600):
    r = subprocess.run([PY, "-X", "utf8"] + args, cwd=str(HERE), capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[-2000:]}
    try:
        return json.loads(r.stdout[r.stdout.find("{"):])
    except Exception:
        return {"raw": r.stdout[-1500:]}


def main() -> int:
    ap_out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "results.json"
    sys.path.insert(0, str(HERE))
    from mouth_task import check
    fact = set(json.load(open(HERE / "data" / "FACT_WORDS.json", encoding="utf-8")))
    exam = [json.loads(l) for l in open(HERE / "data" / "mouth_exam.jsonl", encoding="utf-8") if l.strip()]

    out = {"seeds": {}, "errors": [], "rpm_select": None}
    for seed in SEEDS:
        entry = {}
        for dose in DOSES:
            tag = f"steered_d{dose}"
            g = run(["gen_steer.py", "--seed", seed, "--rows", "300", "--dose", dose,
                     "--out-dir", str(HERE / "guard"), "--results", str(HERE / "ckpt_src")])
            if "error" in g:
                out["errors"].append({"seed": seed, "dose": dose, "stage": "gen", "detail": g["error"]})
                continue
            gen = HERE / "guard" / f"gen_{seed}_{tag}.jsonl"
            rows = [json.loads(l) for l in open(gen, encoding="utf-8") if l.strip()]
            for i, r in enumerate(rows):
                ok, why = check.check(exam[i]["situation"], exam[i]["input_text"], r["text"], fact, exam[i].get("reading"))
                r["guard_ok"] = bool(ok); r["guard_why"] = why
            with open(gen, "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            scored = HERE / "guard_scored" / f"{seed}_{tag}.scored.jsonl"
            scored.parent.mkdir(exist_ok=True)
            r1 = run(["rt_score.py", "--gen", str(gen), "--out", str(scored)])
            if "error" in r1:
                out["errors"].append({"seed": seed, "dose": dose, "stage": "rt_score", "detail": r1["error"]})
                continue
            r2 = run(["composite.py", "--scored", str(scored)])
            key = [k for k in r2 if k.startswith(seed)]
            entry[dose] = r2[key[0]] if key else r2
            print(seed, dose, entry[dose], flush=True)
        out["seeds"][seed] = entry

    out["rpm_select"] = run(["rpm_select.py", "--checkpoint", "ckpt/s1.pt", "--out", "rpm_select.json"])
    json.dump(out, open(HERE / ap_out, "w", encoding="utf-8"), indent=1)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
