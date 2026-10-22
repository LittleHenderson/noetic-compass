"""The unit runner and the pool of TEACH-2.

One unit = one (arm, world) in one fresh process:
    python -X utf8 -B -I <pkg>/teach2/run_t2.py unit --arm CUBE_OSC --world W01 --exam <exam dir> --out <out dir>
The pool runs VERBATIM_ONLY on every world first, then computes the working and device limits by the frozen rule
(A-TEACH2-18 P7) and writes LIMITS_TEACH2.json, then every other arm (CUBE_OSC before REPLAY), one process at a time by
default; each unit's stdout/stderr is logged under out/logs/:
    python -X utf8 -B -I <pkg>/teach2/run_t2.py pool --exam <exam dir> --out <out dir> [--workers 1] [--worlds W01,W02]
                                                     [--arms VERBATIM_ONLY,CUBE_OSC] [--ctt-python <python with torch>]
`--helm-dir <repo root>` is the builder's PRACTICE override (the unit records it; the reader refuses it in a sealed
reading). `--ctt-python` names the interpreter for the CTT serving process (default: this one). The units write raw
records only.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))
from teach2 import common_t2 as C          # noqa: E402
from teach2 import exam_t2 as E            # noqa: E402

LIMITS_FILE = "LIMITS_TEACH2.json"


def unit_name(arm: str, world_id: str) -> str:
    return f"UNIT_{arm}_{world_id}.json"


def limits_from_verbatim(out: Path, worlds) -> dict:
    """A-TEACH2-15 T2 / A-TEACH2-18 P7: working limit = floor(median VERBATIM_ONLY working bytes at the end of
    Q-REFRESHED / 2 / 100) * 100; device limit = the working limit."""
    per = {}
    for w in worlds:
        p = out / unit_name("VERBATIM_ONLY", w)
        if not p.is_file():
            raise SystemExit(f"REFUSED: the limits need VERBATIM_ONLY on every world first ({w} missing)")
        u = C.read_json(p)
        per[w] = int(u["phase_marks"]["Q_REFRESHED"]["working_bytes"])
    med = statistics.median(per.values())
    lim = int(med // 2 // C.LIMIT_ROUND_TO) * C.LIMIT_ROUND_TO
    return {"schema": "helm.teach2.limits/1", "rule": "floor(median(VERBATIM_ONLY bytes at Q_REFRESHED end) / 2 / 100) * 100",
            "verbatim_bytes_at_q_refreshed": per, "median": med, "working_limit_bytes": lim, "device_limit_bytes": lim}


def cmd_unit(a) -> int:
    from teach2 import arms_t2 as A
    exam = E.load_exam(a.exam)
    world = next(w for w in exam["worlds"] if w["world_id"] == a.world)
    wid = world["world_id"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scratch = out / "scratch" / f"{a.arm}_{wid}"
    scratch.mkdir(parents=True, exist_ok=True)
    limits = C.read_json(out / LIMITS_FILE) if (out / LIMITS_FILE).is_file() else None
    t0 = time.perf_counter()
    u = A.Unit(a.arm, world, exam["plan"][wid], exam["turns"][wid], exam["quiz"][wid], exam["damage"][wid],
               exam["offline"][wid], exam["seeds"], scratch, limits=limits, helm_dir_override=a.helm_dir,
               ctt_python=a.ctt_python)
    rec = u.run()
    rec["exam_pins"] = exam["pins"]
    rec["turns_label"] = exam["turns_label"]
    rec["elapsed_seconds"] = round(time.perf_counter() - t0, 3)
    rec["python"] = sys.version.split()[0]
    rec["isolated"] = bool(sys.flags.isolated)
    rec["net_attempts"] = 0
    sha = C.write_json(out / unit_name(a.arm, wid), rec)
    print(json.dumps({"unit": unit_name(a.arm, wid), "sha256": sha, "errors": len(rec["errors"]),
                      "branches": len(rec.get("branches_end") or []), "refresh": len(rec["refresh"]),
                      "ctt_violations": len((rec.get("ctt") or {}).get("violations") or []),
                      "elapsed": rec["elapsed_seconds"]}))
    return 0


def _run_units(a, plan, out: Path, results: dict) -> None:
    running = []

    def launch(arm, w):
        cmd = [sys.executable, "-X", "utf8", "-B", "-I", str(Path(__file__)), "unit", "--arm", arm, "--world", w,
               "--exam", a.exam, "--out", a.out] + (["--helm-dir", a.helm_dir] if a.helm_dir else []) + \
              (["--ctt-python", a.ctt_python] if a.ctt_python else [])
        log = open(out / "logs" / f"{arm}_{w}.log", "w", encoding="utf-8")
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=str(PKG.parent))
        return (arm, w, p, log, time.perf_counter())

    i = 0
    while i < len(plan) or running:
        while i < len(plan) and len(running) < a.workers:
            arm, w = plan[i]
            if arm == "REPLAY" and any(r[0] == "CUBE_OSC" and r[1] == w for r in running):
                break
            running.append(launch(arm, w))
            i += 1
        done = [r for r in running if r[2].poll() is not None]
        if not done:
            time.sleep(0.05)
            continue
        for arm, w, p, log, ts in done:
            log.close()
            running.remove((arm, w, p, log, ts))
            results[f"{arm}:{w}"] = {"exit": p.returncode, "seconds": round(time.perf_counter() - ts, 2),
                                     "file": unit_name(arm, w), "present": (out / unit_name(arm, w)).is_file()}
            print(json.dumps({"unit": f"{arm}:{w}", "exit": p.returncode, "seconds": results[f"{arm}:{w}"]["seconds"]}),
                  flush=True)


def cmd_pool(a) -> int:
    exam = E.load_exam(a.exam)
    worlds = [w["world_id"] for w in exam["worlds"]]
    if a.worlds:
        worlds = [w for w in worlds if w in set(a.worlds.split(","))]
    arms = list(C.ARMS) if not a.arms else [x for x in C.ARMS if x in set(a.arms.split(","))]
    out = Path(a.out)
    (out / "logs").mkdir(parents=True, exist_ok=True)
    results: dict = {}
    t0 = time.perf_counter()
    limits = None
    if "VERBATIM_ONLY" in arms:
        _run_units(a, [("VERBATIM_ONLY", w) for w in worlds], out, results)
        limits = limits_from_verbatim(out, worlds)
        limits["worlds"] = worlds
        C.write_json(out / LIMITS_FILE, limits)
        print(json.dumps({"limits": {k: limits[k] for k in ("median", "working_limit_bytes", "device_limit_bytes")}}),
              flush=True)
    rest = [x for x in arms if x != "VERBATIM_ONLY"]
    order = [x for x in ("CUBE_OSC", "REPLAY") if x in rest] + [x for x in rest if x not in ("CUBE_OSC", "REPLAY")]
    _run_units(a, [(arm, w) for arm in order for w in worlds], out, results)
    summary = {"schema": "helm.teach2.pool/1", "exam": a.exam, "exam_pins": exam["pins"], "practice_mock": exam["practice_mock"],
               "units": results, "planned": len(worlds) * len(arms), "arms": arms, "worlds": worlds,
               "all_exit_0": len(results) == len(worlds) * len(arms) and all(r["exit"] == 0 and r["present"] for r in results.values()),
               "elapsed_seconds": round(time.perf_counter() - t0, 2), "workers": a.workers, "python": sys.version.split()[0],
               "helm_dir_override": a.helm_dir, "ctt_python": a.ctt_python, "limits": limits}
    C.write_json(out / "POOL_SUMMARY.json", summary)
    print(json.dumps({"planned": summary["planned"], "all_exit_0": summary["all_exit_0"], "elapsed": summary["elapsed_seconds"]}))
    return 0 if summary["all_exit_0"] else 1


ALLOWED_TEACH_INTENTS = ("GENERAL_KNOWLEDGE_INQUIRY", "GENERAL_CONVERSATION")


def cmd_routecheck(a) -> int:
    """TEACH-1 D-TEACH1-2: ask HELM's own chat (switches OFF, fresh session per world, no budget) how it routes every
    teaching turn and every quiz question. A teaching turn must land in ALLOWED_TEACH_INTENTS and save no user fact;
    a quiz question must land in QUERY_MEMORY_RECALL."""
    import contextlib
    import io
    from teach2 import arms_t2 as A
    exam = E.load_exam(a.exam)
    out = Path(a.out)
    os.environ["HELM_MEMORY_COMPACT"] = "0"
    os.environ.pop("HELM_CUBE_OSC", None)
    os.environ["HELM_SESSION_DIR"] = str(out / "routecheck_sessions")
    A.install_frozen_clock()
    A.netguard()
    helm = C.import_helm_now()
    report, bad = {}, 0
    for w in exam["worlds"]:
        wid = w["world_id"]
        with contextlib.redirect_stdout(io.StringIO()):
            s = helm["helm_chat"].HELMConversationalSession(session_id=f"routecheck-{wid}")
        rows = {}
        for t in exam["turns"][wid]:
            uf = len(s.memory.context.user_facts)
            with contextlib.redirect_stdout(io.StringIO()):
                s.handle_turn(t["text"])
            it = s.memory.turns[-1].intent if s.memory.turns else None
            why = []
            if it not in ALLOWED_TEACH_INTENTS:
                why.append(f"intent {it}")
            if len(s.memory.context.user_facts) != uf:
                why.append("saved a user fact")
            rows[str(t["turn_index"])] = "; ".join(why) or None
            bad += bool(why)
        for i, it_ in enumerate(exam["quiz"][wid]["items"]):
            with contextlib.redirect_stdout(io.StringIO()):
                s.handle_turn(it_["question"])
            got = s.memory.turns[-1].intent
            rows[f"quiz:{i}"] = None if got == "QUERY_MEMORY_RECALL" else f"quiz question routed to {got}"
            bad += got != "QUERY_MEMORY_RECALL"
        report[wid] = rows
    doc = {"schema": "helm.teach2.routecheck/1", "exam_pins": exam["pins"], "allowed": list(ALLOWED_TEACH_INTENTS),
           "bad": bad, "report": report, "ok": bad == 0}
    C.write_json(out / "ROUTE_CHECK_TEACH2.json", doc)
    chk = E.check_exam(exam, route_report=report)
    C.write_json(out / "EXAM_CHECK_TEACH2.json", chk)
    print(json.dumps({"route_bad": bad, "exam_check_all_ok": chk["all_ok"]}))
    return 0 if bad == 0 and chk["all_ok"] else 1


def cmd_cutcheck(a) -> int:
    hc = C.check_helm_cut()
    ct = C.check_ctt()
    doc = dict(hc, ctt=ct, ok=hc["ok"] and ct["ok"], helm_cut_ok=hc["ok"])
    C.write_json(Path(a.out) / "CUT_CHECK_TEACH2.json", doc)
    print(json.dumps(doc))
    return 0 if doc["ok"] else 1


def cmd_suites(a) -> int:
    """I2 / HG-TESTS: HELM's suites from a scratch COPY of helm_now/ (the package copy is never written to)."""
    import shutil
    out = Path(a.out)
    scratch = out / "suites_scratch"
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(C.helm_now_dir(), scratch)
    env = dict(os.environ)
    env["HELM_SESSION_DIR"] = str(out / "suites_sessions")
    for k in ("HELM_MEMORY_COMPACT", "HELM_WIDE_BRAIN", "HELM_CUBE_OSC", "HELM_EYE_ACT"):
        env.pop(k, None)
    if C.brain_dir().is_dir():
        env[C.BRAIN_DIR_ENV] = str(C.brain_dir())
    rows = {}
    cmd_u = [sys.executable, "-X", "utf8", "-B", "-m", "unittest", *C.HELM_TESTS_UNITTEST]
    t0 = time.perf_counter()
    r = subprocess.run(cmd_u, cwd=str(scratch), env=env, capture_output=True, text=True)
    rows["unittest"] = {"command": cmd_u[3:], "exit": r.returncode, "tail": (r.stderr or "").strip().splitlines()[-3:],
                        "seconds": round(time.perf_counter() - t0, 1)}
    have_pytest = subprocess.run([sys.executable, "-c", "import pytest"], capture_output=True).returncode == 0
    if have_pytest:
        cmd_p = [sys.executable, "-X", "utf8", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", *C.HELM_TESTS_PYTEST]
        t0 = time.perf_counter()
        r2 = subprocess.run(cmd_p, cwd=str(scratch), env=env, capture_output=True, text=True)
        rows["pytest"] = {"command": cmd_p[3:], "exit": r2.returncode, "tail": (r2.stdout or "").strip().splitlines()[-2:],
                          "seconds": round(time.perf_counter() - t0, 1)}
    else:
        rows["pytest"] = {"command": None, "exit": None, "tail": ["pytest not installed on this host"], "seconds": 0}
    stray = sorted(set(C.tree_listing(scratch)) - set(C.tree_listing(C.helm_now_dir())))
    doc = {"schema": "helm.teach2.suites/1", "from_seal": bool(a.from_seal), "rows": rows,
           "all_ok": rows["unittest"]["exit"] == 0 and rows["pytest"]["exit"] in (0,),
           "summary": {k: v["tail"] for k, v in rows.items()}, "stray_files_written_by_suites": stray[:20],
           "helm_now_unchanged": C.check_helm_cut()["ok"]}
    C.write_json(out / "SUITES_TEACH2.json", doc)
    print(json.dumps({"all_ok": doc["all_ok"], "summary": doc["summary"]}, indent=1))
    return 0 if doc["all_ok"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("unit")
    u.add_argument("--arm", required=True)
    u.add_argument("--world", required=True)
    u.add_argument("--exam", required=True)
    u.add_argument("--out", required=True)
    u.add_argument("--helm-dir", default=None)
    u.add_argument("--ctt-python", default=None)
    p = sub.add_parser("pool")
    p.add_argument("--exam", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--worlds", default=None)
    p.add_argument("--arms", default=None)
    p.add_argument("--helm-dir", default=None)
    p.add_argument("--ctt-python", default=None)
    r = sub.add_parser("routecheck")
    r.add_argument("--exam", required=True)
    r.add_argument("--out", required=True)
    c = sub.add_parser("cutcheck")
    c.add_argument("--out", required=True)
    t = sub.add_parser("suites")
    t.add_argument("--out", required=True)
    t.add_argument("--from-seal", action="store_true")
    a = ap.parse_args(argv)
    return {"unit": cmd_unit, "pool": cmd_pool, "cutcheck": cmd_cutcheck, "suites": cmd_suites, "routecheck": cmd_routecheck}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
