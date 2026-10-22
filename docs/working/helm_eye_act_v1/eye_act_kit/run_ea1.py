"""EYE-ACT-1 driver: one process, laptop, standard library (PREREGISTRATION_EYE_ACT_V1.precode.md section 7).

  python -B run_ea1.py practice <out_dir>
  python -B run_ea1.py scored <out_dir> --owner-line "<the owner's typed line>" --zip-sha <sealed zip sha256>

Writes <out_dir>/RUN_RESULTS.json (every world x arm, the unplanted twins, the replay, the test results, the generator
check, source hashes, timing). The reader (read_ea1.py) turns it into READING.json. Nothing here scores."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent
REPO = KIT.parents[3]
sys.path[:0] = [str(KIT), str(REPO)]
sys.dont_write_bytecode = True

import ea1_world as G  # noqa: E402
import ea1_arms as A  # noqa: E402

SOURCES = ["helm_eye_act.py", "helm_end_to_end_loop.py", "helm_wide_turn.py", "helm_brain_wide.py", "test_helm_eye_act.py",
           "docs/working/helm_eye_act_v1/eye_act_kit/ea1_world.py", "docs/working/helm_eye_act_v1/eye_act_kit/ea1_arms.py",
           "docs/working/helm_eye_act_v1/eye_act_kit/read_ea1.py", "docs/working/helm_eye_act_v1/eye_act_kit/run_ea1.py",
           "docs/working/helm_eye_act_v1/eye_act_kit/test_ea1_kit.py",
           "docs/working/helm_eye_act_v1/PREREGISTRATION_EYE_ACT_V1.precode.md"]
PER_KIND_SCORED = 40


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def plan(mode: str, owner_line: str = "", zip_sha: str = ""):
    if mode == "practice":
        kinds = list(G.KINDS) + ["CLEAN", "CLEAN", "CLEAN"]
        return [{"seed": "dev:%d" % (i + 1), "kind": k} for i, k in enumerate(kinds)]
    return [{"seed": G.scored_seed(owner_line, zip_sha, k, i), "kind": k} for k in G.KINDS for i in range(PER_KIND_SCORED)]


def run_tests() -> dict:
    env = dict(os.environ)
    env.pop("HELM_EYE_ACT", None)
    t = subprocess.run([sys.executable, "-B", "-m", "unittest", "test_helm_eye_act"], cwd=REPO, env=env,
                       capture_output=True, text=True)
    k = subprocess.run([sys.executable, "-B", "-m", "unittest", "test_ea1_kit"], cwd=KIT, env=env,
                       capture_output=True, text=True)
    pin = subprocess.run([sys.executable, "-B", "-m", "unittest", "test_helm_cas_address"], cwd=REPO, env=env,
                         capture_output=True, text=True)
    tail = lambda p: [l for l in p.stderr.strip().splitlines() if l.startswith(("Ran ", "OK", "FAILED"))]
    return {"ok": t.returncode == 0 and k.returncode == 0, "off_pin_ok": pin.returncode == 0,
            "eye_tests": tail(t), "kit_tests": tail(k), "off_pin": tail(pin)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("practice", "scored"))
    ap.add_argument("out")
    ap.add_argument("--owner-line", default="")
    ap.add_argument("--zip-sha", default="")
    a = ap.parse_args()
    if a.mode == "scored" and not (a.owner_line and a.zip_sha):
        sys.exit("scored needs --owner-line and --zip-sha")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    tests = run_tests()
    items = plan(a.mode, a.owner_line, a.zip_sha)
    worlds_def = {(p["seed"], p["kind"]): G.make_world(p["seed"], p["kind"]) for p in items}
    gen_ok = all(G.make_world(s, k) == w for (s, k), w in worlds_def.items())
    worlds, twins = [], []
    for (s, k), w in worlds_def.items():
        twins.append(A.run_world(w, "A0", planted=False))
        for arm in A.ARMS:
            worlds.append(A.run_world(w, arm))
    first_of = {}
    for p in items:
        if p["kind"] != "CLEAN" and p["kind"] not in first_of:
            first_of[p["kind"]] = p
    replay_set = list(first_of.values()) + [p for p in items if p["kind"] == "CLEAN"][:4]
    replay = []
    for p in replay_set:
        w = worlds_def[(p["seed"], p["kind"])]
        eq = True
        for arm in ("A0", "A3"):
            again = A.run_world(w, arm)
            first = next(r for r in worlds if r["seed"] == p["seed"] and r["kind"] == p["kind"] and r["arm"] == arm)
            eq = eq and (again["items"], again["final"], again["statuses"]) == (first["items"], first["final"], first["statuses"])
        replay.append({"seed": p["seed"], "kind": p["kind"], "equal": eq})
    res = {"version": "eye_act_1_run_v1", "mode": a.mode, "owner_line": a.owner_line, "zip_sha256": a.zip_sha,
           "plan": items, "worlds": worlds, "twins": twins, "replay": replay, "tests": tests,
           "generator_check": gen_ok, "seconds": round(time.time() - t0, 3),
           "sources": {s: sha_file(REPO / s) for s in SOURCES if (REPO / s).exists()},
           "python": sys.version.split()[0]}
    path = out / "RUN_RESULTS.json"
    path.write_bytes(json.dumps(res, indent=1, sort_keys=True).encode("utf-8"))
    print(json.dumps({"worlds": len(worlds), "seconds": res["seconds"], "tests": tests, "generator_check": gen_ok,
                      "replay_equal": sum(r["equal"] for r in replay), "sha256": sha_file(path)}, indent=1))


if __name__ == "__main__":
    main()
