"""run_cube.py -- the CUBE TRAIN job on the GPU host, end to end (PREREGISTRATION_CUBE_TRAIN §7–§9, A-CUBE-TRAIN-1..5).

    python3 -X utf8 -B run_cube.py --zip <the sealed zip> --zip-sha256 <its sealed sha256> --out <dir>

1. instrument I1: the zip's sha256 equals the sealed one; I5/I6: the package tests (tests_cube) pass;
2. smoke: A5-s1 trained 20 steps, then 16 DEV rows decoded by the audited cube_serve process (I2: audit clean);
3. the four models fine-tuned (A4-s1, A4-s2, A4-s3, A5-s1), the frozen steps each (I3: all finished, no NaN);
4. DEV-SDG and DEV-LLM decoded by every model through cube_serve (audited); the kept CAS validation rows decoded by
   the c45 serve.py for each main copy with its start weights and its final weights (G-KEEP-OLD);
5. the frozen reader (cube_task/read.py) writes CUBE_TRAIN_READING.json with the status word.
The house-rule seed: sha256("CUBE TRAIN at 3 USD" + ":" + the sealed zip's sha256) mod 2^63 sets the batch order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

PKG = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PKG)

from cube_task import audit_judge, read, target  # noqa: E402

APPROVAL = "CUBE TRAIN at 3 USD"
PRICE_PER_HOUR = 1.006          # g5.xlarge on demand, us-west-2 (list price; the controller records the real one)
MODELS = ("A4-s1", "A4-s2", "A4-s3", "A5-s1")
COPIES = ("A4-s1", "A4-s2", "A4-s3")
T0 = time.time()


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def note(out, obj):
    obj = dict(obj, t=round(time.time() - T0, 1))
    print(json.dumps(obj, sort_keys=True), flush=True)
    with open(os.path.join(out, "RUN_LOG_CUBE.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, sort_keys=True) + "\n")


def rows(name):
    with open(os.path.join(PKG, "data", name), encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def run(cmd, log_path):
    with open(log_path, "w", encoding="utf-8") as fh:
        return subprocess.run(cmd, cwd=PKG, stdout=fh, stderr=subprocess.STDOUT).returncode


def serve(script, args, batches, audit_path, forbidden):
    """Run an audited decoding process; return (answers by id, audit violations)."""
    cmd = [sys.executable, "-X", "utf8", "-I", "-B", os.path.join(PKG, script)] + args + ["--audit", audit_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    answers = {}
    died = False
    for b in batches:
        try:                                   # a decoder that dies must not kill this script (review, MAJOR 1)
            p.stdin.write(json.dumps({"batch": b}, ensure_ascii=False) + "\n")
            p.stdin.flush()
            for a in json.loads(p.stdout.readline())["batch"]:
                answers[a["id"]] = a
        except (OSError, ValueError, KeyError, TypeError):
            died = True
            break
    try:
        p.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
        p.stdin.flush()
    except OSError:
        died = True
    try:
        p.wait(timeout=600)
    except subprocess.TimeoutExpired:
        p.kill()
        died = True
    rep = json.load(open(audit_path, encoding="utf-8")) if os.path.isfile(audit_path) else None
    bad = audit_judge.audit_violations(rep, audit_path, forbidden)
    if died or p.returncode != 0:
        bad = bad + ["decoder died (return code %s)" % p.returncode]
    return answers, bad


def chunks(items, n=64):
    return [items[i:i + n] for i in range(0, len(items), n)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--zip-sha256", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    fz = json.load(open(os.path.join(PKG, "FROZEN_CUBE_TRAIN.json"), encoding="utf-8"))
    man = json.load(open(os.path.join(PKG, "data", "DATA_MANIFEST_CUBE.json"), encoding="utf-8"))
    vocab = os.path.join(PKG, "data", "vocab.json")
    forbidden = [os.path.join(PKG, "data"), os.path.join(PKG, "weights"), os.path.join(out, "runs")]
    inst = {}
    inst["I1_zip_sha256"] = sha256_file(a.zip) == a.zip_sha256
    order_seed = int(hashlib.sha256((APPROVAL + ":" + a.zip_sha256).encode()).hexdigest(), 16) % (2 ** 63)
    note(out, {"event": "start", "I1": inst["I1_zip_sha256"], "order_seed": order_seed})
    inst["I5_I6_package_tests"] = run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests_cube", "-t", "."],
                                     os.path.join(out, "unittest.log")) == 0
    # ---- smoke
    smoke = os.path.join(out, "smoke")
    ok = run([sys.executable, "-X", "utf8", "-B", "-m", "ctt_train.train_cube", "--model", "A5-s1", "--out", smoke,
              "--order-seed", str(order_seed), "--max-steps", "20"], os.path.join(out, "smoke_train.log")) == 0
    dev_sdg, dev_llm = rows("dev_sdg.jsonl"), rows("dev_llm.jsonl")
    probe = [{"id": "s%d" % i, "text": r["text"]} for i, r in enumerate(dev_sdg[:16])]
    viol = ["smoke training failed"]
    if ok:
        _ans, viol = serve("cube_task/cube_serve.py", ["--weights", os.path.join(smoke, "final.pt"), "--vocab", vocab,
                                                       "--config", fz["models"]["A5-s1"]["config"]],
                           [probe], os.path.join(out, "audit_smoke.json"), forbidden)
    audits = {"smoke": viol}
    note(out, {"event": "smoke", "trained": ok, "audit_violations": viol})
    if not inst["I1_zip_sha256"] or not inst["I5_I6_package_tests"] or viol:
        inst["I2_audits_clean"] = False
        return finish(out, inst, None, None, None, None, audits, fz, man)
    # ---- training
    finals, trained = {}, {}
    for m in MODELS:
        d = os.path.join(out, "runs", m)
        rc = run([sys.executable, "-X", "utf8", "-B", "-m", "ctt_train.train_cube", "--model", m, "--out", d,
                  "--order-seed", str(order_seed)], os.path.join(out, "train_%s.log" % m))
        wm = os.path.join(d, "WEIGHTS_MANIFEST.json")
        trained[m] = rc == 0 and os.path.isfile(wm) and json.load(open(wm))["steps"] == fz["steps"]
        finals[m] = os.path.join(d, "final.pt")
        note(out, {"event": "trained", "model": m, "ok": trained[m]})
    inst["I3_trained_no_nan"] = all(trained.values())
    if not inst["I3_trained_no_nan"]:
        return finish(out, inst, None, None, None, None, audits, fz, man)
    # ---- decoding DEV (audited)
    dev_rows = [dict(r, id="sdg%d" % i) for i, r in enumerate(dev_sdg)] + [dict(r, id="llm%d" % i)
                                                                           for i, r in enumerate(dev_llm)]
    outputs = {}
    for m in MODELS:
        ans, v = serve("cube_task/cube_serve.py", ["--weights", finals[m], "--vocab", vocab,
                                                   "--config", fz["models"][m]["config"]],
                       chunks([{"id": r["id"], "text": r["text"]} for r in dev_rows]),
                       os.path.join(out, "audit_dev_%s.json" % m), forbidden)
        audits["dev_" + m] = v
        text_of = {r["id"]: r["text"] for r in dev_rows}
        # one standard order (review note 1): copies that agree on the reading but list slots in another order agree
        outputs[m] = {i: (target.canonical(x["tokens"], text_of[i]) if x["complete"] else None)
                      for i, x in ans.items()}
        note(out, {"event": "decoded", "model": m, "rows": len(ans), "audit_violations": v})
    # ---- keep-old: c45 serve.py on the kept validation rows, start weights vs final weights
    cas_val = rows("cas_val.jsonl")
    keep_old = {}
    for m in COPIES:
        rates = {}
        for when, w in (("before", os.path.join(PKG, "weights", m + ".pt")), ("after", finals[m])):
            ans, v = serve("helm_cas_translator/serve.py", ["--weights", w, "--vocab", vocab,
                                                            "--config", fz["models"][m]["config"]],
                           chunks([{"id": "v%d" % i, "direction": r["direction"], "text": r["text"],
                                    "context": r.get("context") or []} for i, r in enumerate(cas_val)]),
                           os.path.join(out, "audit_keep_%s_%s.json" % (m, when)), forbidden)
            audits["keep_%s_%s" % (m, when)] = v
            exact = sum(1 for i, r in enumerate(cas_val)
                        if ans.get("v%d" % i, {}).get("complete") and ans["v%d" % i]["tokens"] == r["target"])
            rates[when] = exact / len(cas_val)
        keep_old[m] = rates
        note(out, {"event": "keep_old", "model": m, **rates})
    return finish(out, inst, dev_rows, outputs, keep_old, finals, audits, fz, man)


def finish(out, inst, dev_rows, outputs, keep_old, finals, audits, fz, man) -> int:
    inst.setdefault("I2_audits_clean", all(not v for v in audits.values()))
    inst["I6_dev_floors"] = man["counts"]["dev_llm"] >= 270 and man["counts"]["dev_sdg"] == 2000
    est = round((time.time() - T0) / 3600 * PRICE_PER_HOUR, 4)
    inst["I7_cost_under_cap_estimate"] = est <= fz["cap_usd"]
    reading = {"schema": "cube-train.reading/1", "instrument": inst, "audits": audits,
               "estimated_cost_usd_this_script": est, "labels": fz["labels"]}
    if outputs is not None:
        split = {"sdg": [r for r in dev_rows if r["id"].startswith("sdg")],
                 "llm": [r for r in dev_rows if r["id"].startswith("llm")]}
        copies = {}
        for m in MODELS:
            copies[m] = {s: read.score_copy(rs, [outputs[m].get(r["id"]) for r in rs]) for s, rs in split.items()}
        vote = {s: read.score_copy(rs, [read.unanimous([outputs[m].get(r["id"]) for m in COPIES]) for r in rs])
                for s, rs in split.items()}
        flat = {m: {"invented": c["sdg"]["invented"] + c["llm"]["invented"]} for m, c in copies.items()}
        reading.update(copies=copies, vote=vote, keep_old=keep_old,
                       gates=read.gates(vote["sdg"], vote["llm"], flat, keep_old, fz["gates"]),
                       final_sha256={m: sha256_file(p) for m, p in finals.items()},
                       repetition_note="each AI-written row about 100 times, each SDG row about 23 times (A-CUBE-TRAIN-5)")
    else:
        reading["gates"] = {"not_reached": False}
    reading["status_word"] = read.status_word(reading)
    with open(os.path.join(out, "CUBE_TRAIN_READING.json"), "w", encoding="utf-8") as fh:
        json.dump(reading, fh, indent=1, sort_keys=True)
    note(out, {"event": "done", "status_word": reading["status_word"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
