"""run_mouth.py -- the MOUTH TRAIN host runner (A-TALK-4, A-TALK-5). GPU host only.

    python3 -X utf8 -B run_mouth.py --zip <sealed zip> --zip-sha256 <sha> --out <dir>

1. I1: the zip equals its seal; the package tests pass.
2. Smoke: A5-s1 trains 20 steps; the audited server writes 16 exam replies (write-audit judged).
3. Training: A4-s1, A4-s2, A4-s3, A5-s1, the frozen steps each (ctt_train.train_mouth).
4. The mouth's exam (speaker A4-s1): every held-out exam input once (turn "exam", >= 1,000 replies, A-TALK-5 F2); the
   first VARIED_INPUTS inputs five more times (turns v0..v4); the DEV inputs once (reported). A4-s2, A4-s3 and A5-s1
   also write the exam (fallback reported only).
5. The guard on every reply (mouth_task.check + the lock re-checked): a failure is a FALLBACK.
6. Round trip: every fact reply that passed the guard is read by the ear ([B], A4-s1..s3, unanimous); it must give the
   same thing, value, month and old value.
7. The ear and the old skills: DEV-SDG / DEV-LLM by the three copies' unanimous vote (cube_task.read, CUBE TRAIN's
   frozen rule), and the kept CAS validation rows before (c57 weights) and after (A-TALK-4 W7).
Writes MOUTH_EXAM_OUTPUTS.json (every reply with its guard and round-trip result) and MOUTH_HOST_READING.json (the
frozen reader read_mouth.read_host); the AI raters (SOUNDS-HUMAN, TONE) run after the download, on the laptop.
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

from cube_task import audit_judge, read as cube_read, target  # noqa: E402
from mouth_task import check, names as N, roundtrip  # noqa: E402

APPROVAL = "MOUTH TRAIN v2 at 3 USD"
MODELS = ("A4-s1", "A4-s2", "A4-s3", "A5-s1")
COPIES = ("A4-s1", "A4-s2", "A4-s3")
SPEAKER = "A4-s1"
T0 = time.time()


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def note(out, obj) -> None:
    obj = dict(obj, t=round(time.time() - T0, 1))
    print(json.dumps(obj, sort_keys=True), flush=True)
    with open(os.path.join(out, "RUN_LOG_MOUTH.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, sort_keys=True) + "\n")


def run(cmd, log_path) -> int:
    with open(log_path, "w", encoding="utf-8") as fh:
        return subprocess.run(cmd, cwd=PKG, stdout=fh, stderr=subprocess.STDOUT).returncode


def rows(name):
    return [json.loads(l) for l in open(os.path.join(PKG, "data", name), encoding="utf-8") if l.strip()]


class Server:
    """One audited mouth_serve process; a dead server gives empty answers and is reported."""

    def __init__(self, weights, audit_path):
        cfgs = json.load(open(os.path.join(PKG, "FROZEN_MOUTH.json"), encoding="utf-8"))["models"]
        cmd = [sys.executable, "-X", "utf8", "-I", "-B", os.path.join(PKG, "mouth_task", "mouth_serve.py"),
               "--audit", audit_path]
        for name, w in weights.items():
            cmd += ["--copy", f"{name}={w}:{cfgs[name]['config']}"]
        self.audit_path = audit_path
        self.err = open(audit_path + ".stderr.log", "w", encoding="utf-8")
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.err, text=True,
                                  encoding="utf-8", cwd=PKG)
        self.died = False

    def ask(self, req):
        if self.died:
            return None
        try:
            self.p.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
            self.p.stdin.flush()
            return json.loads(self.p.stdout.readline())
        except (OSError, ValueError):
            self.died = True
            return None

    def close(self, forbidden):
        try:
            self.p.stdin.write(json.dumps({"cmd": "quit"}) + "\n")
            self.p.stdin.flush()
        except OSError:
            self.died = True
        try:
            self.p.wait(timeout=900)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.died = True
        self.err.close()
        rep = json.load(open(self.audit_path, encoding="utf-8")) if os.path.isfile(self.audit_path) else None
        bad = audit_judge.audit_violations(rep, self.audit_path, forbidden)
        if self.died or self.p.returncode != 0:
            bad = bad + ["server died (return code %s)" % self.p.returncode]
        return bad


def chunks(items, n=64):
    return [items[i:i + n] for i in range(0, len(items), n)]


def mouth_item(x, turn, number_words):
    return {"id": f"{x['input_key']}#{turn}", "situation": x["situation"], "tone": list(x["tone"]),
            "input_text": x["input_text"], "turn": turn, "style": x.get("style"),
            "names": N.names_for(x.get("reading"), x.get("person_line"), number_words)}


def write_all(server, copy, items):
    out = {}
    for b in chunks(items):
        r = server.ask({"mode": "mouth", "copy": copy, "top_p": FZ["top_p"], "items": b})
        for o in (r or {}).get("outputs") or []:
            out[o["id"]] = o
    return out


def same_fact(reading_str, x) -> bool:
    return roundtrip.same_fact(reading_str, x["reading"], x["situation"])     # A-TALK-7 H3: ASK on thing/value/month


def main(argv=None) -> int:
    global FZ
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--zip-sha256", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    FZ = json.load(open(os.path.join(PKG, "FROZEN_MOUTH.json"), encoding="utf-8"))
    fact_words = set(json.load(open(os.path.join(PKG, "data", "FACT_WORDS.json"), encoding="utf-8")))
    function = json.load(open(os.path.join(PKG, "data", "FUNCTION_WORDS.json"), encoding="utf-8"))
    number_words = set(FZ["number_words"])
    forbidden = [os.path.join(PKG, "data"), os.path.join(PKG, "weights"), os.path.join(out, "runs")]
    inst = {"I1_zip_sha256": sha256_file(a.zip) == a.zip_sha256}
    order_seed = int(hashlib.sha256((APPROVAL + ":" + a.zip_sha256).encode()).hexdigest(), 16) % (2 ** 63)
    note(out, {"event": "start", "I1": inst["I1_zip_sha256"], "order_seed": order_seed})
    inst["I2_package_tests"] = run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests_mouth", "-t", "."],
                                   os.path.join(out, "unittest.log")) == 0
    exam = rows("mouth_exam.jsonl")
    dev = {r["input_key"]: r for r in rows("mouth_dev.jsonl")}
    # ---- smoke
    smoke = os.path.join(out, "smoke")
    ok = run([sys.executable, "-X", "utf8", "-B", "-m", "ctt_train.train_mouth", "--model", "A5-s1", "--out", smoke,
              "--order-seed", str(order_seed), "--max-steps", "20"], os.path.join(out, "smoke_train.log")) == 0
    audits = {}
    if ok:
        s = Server({"A5-s1": os.path.join(smoke, "final.pt")}, os.path.join(out, "audit_smoke.json"))
        write_all(s, "A5-s1", [mouth_item(x, "smoke", number_words) for x in exam[:16]])
        audits["smoke"] = s.close(forbidden)
    else:
        audits["smoke"] = ["smoke training failed"]
    note(out, {"event": "smoke", "trained": ok, "audit_violations": audits["smoke"]})
    if not inst["I1_zip_sha256"] or not inst["I2_package_tests"] or audits["smoke"]:
        return finish(out, inst, audits, None)
    # ---- training
    finals, trained = {}, {}
    for m in MODELS:
        d = os.path.join(out, "runs", m)
        rc = run([sys.executable, "-X", "utf8", "-B", "-m", "ctt_train.train_mouth", "--model", m, "--out", d,
                  "--order-seed", str(order_seed)], os.path.join(out, "train_%s.log" % m))
        wm = os.path.join(d, "WEIGHTS_MANIFEST.json")
        trained[m] = rc == 0 and os.path.isfile(wm) and json.load(open(wm))["steps"] == FZ["steps"]
        finals[m] = os.path.join(d, "final.pt")
        note(out, {"event": "trained", "model": m, "ok": trained[m]})
    inst["I3_trained_no_nan"] = all(trained.values())
    if not inst["I3_trained_no_nan"]:
        return finish(out, inst, audits, None)
    s = Server(finals, os.path.join(out, "audit_exam.json"))
    # ---- the mouth's exam
    items = [mouth_item(x, "exam", number_words) for x in exam]
    varied = [mouth_item(x, f"v{k}", number_words) for x in exam[:FZ["varied_inputs"]] for k in range(5)]
    dev_items = [mouth_item(x, "dev", number_words) for x in dev.values()]
    spoken = write_all(s, SPEAKER, items + varied + dev_items)
    others = {m: write_all(s, m, items) for m in MODELS if m != SPEAKER}
    by_key = {x["input_key"]: x for x in exam}
    by_key.update(dev)

    def guard(o, x):
        if not o or not o.get("complete") or not o.get("text"):
            return False, "no complete line"
        allowed = set(function) | set(check.WORD_RX.findall(x["input_text"].lower()))
        if not check.only_allowed_words(o["text"], allowed):
            return False, "a word outside the lock"
        return check.check(x["situation"], x["input_text"], o["text"], fact_words, x.get("reading"))

    records = []
    for it in items + varied + dev_items:
        key, turn = it["id"].rsplit("#", 1)
        x = by_key[key]
        o = spoken.get(it["id"])
        ok_, why = guard(o, x)
        records.append({"id": it["id"], "split": "DEV" if turn == "dev" else ("VARIED" if turn.startswith("v") else "EXAM"),
                        "situation": x["situation"], "input_text": x["input_text"], "text": (o or {}).get("text"),
                        "guard_ok": ok_, "guard_why": why,
                        "new_word": bool(o and o.get("text") and not check.only_allowed_words(
                            o["text"], set(function) | set(check.WORD_RX.findall(x["input_text"].lower()))))})
    # ---- round trip by the ear
    facts = [r for r in records if r["guard_ok"] and r["situation"] in check.FACT_SITUATIONS]
    rt = {}
    for b in chunks(facts):
        r = s.ask({"mode": "ear", "copies": list(COPIES), "texts": [f["text"] for f in b]}) or {}
        outs = r.get("outputs") or {}
        for i, f in enumerate(b):
            reads = []
            for c in COPIES:
                o = (outs.get(c) or [{}] * len(b))[i]
                reads.append(target.fill(o["tokens"], f["text"]) if o.get("complete") else None)
            same = reads[0] if all(rr == reads[0] for rr in reads) else None
            rt[f["id"]] = same_fact(same, by_key[f["id"].rsplit("#", 1)[0]])
    for r in records:
        if r["id"] in rt:
            r["round_trip"] = rt[r["id"]]
    other_fallbacks = {m: sum(1 for it in items if not guard(o.get(it["id"]), by_key[it["id"].rsplit("#", 1)[0]])[0])
                       for m, o in others.items()}
    # ---- the ear and the old skills (A-TALK-4 W7): CUBE TRAIN's own frozen reading on the new weights
    dev_sdg, dev_llm = rows("dev_sdg.jsonl"), rows("dev_llm.jsonl")
    ear_rows = [dict(r, id="sdg%d" % i) for i, r in enumerate(dev_sdg)] + [dict(r, id="llm%d" % i) for i, r in enumerate(dev_llm)]
    ear_out = {c: {} for c in COPIES}
    for b in chunks(ear_rows):
        r = s.ask({"mode": "ear", "copies": list(COPIES), "texts": [x["text"] for x in b]}) or {}
        for c in COPIES:
            for i, x in enumerate(b):
                o = ((r.get("outputs") or {}).get(c) or [{}] * len(b))[i]
                ear_out[c][x["id"]] = target.canonical(o["tokens"], x["text"]) if o.get("complete") else None
    split = {"sdg": [x for x in ear_rows if x["id"].startswith("sdg")], "llm": [x for x in ear_rows if x["id"].startswith("llm")]}
    vote = {k: cube_read.score_copy(v, [cube_read.unanimous([ear_out[c].get(x["id"]) for c in COPIES]) for x in v])
            for k, v in split.items()}
    copies = {c: {"invented": sum(cube_read.score_copy(v, [ear_out[c].get(x["id"]) for x in v])["invented"] for v in split.values())}
              for c in COPIES}
    cas_val = rows("cas_val.jsonl")
    after = {}
    for c in COPIES:
        good = 0
        for b in chunks([dict(r, id="v%d" % i) for i, r in enumerate(cas_val)]):
            r = s.ask({"mode": "cas", "copy": c, "batch": [{"id": x["id"], "direction": x["direction"], "text": x["text"],
                                                            "context": x.get("context") or []} for x in b]}) or {}
            for o, x in zip(r.get("batch") or [], b):
                good += bool(o.get("complete") and o["tokens"] == x["target"])
        after[c] = good / len(cas_val)
    audits["exam"] = s.close(forbidden)
    keep_old = {c: {"before": FZ["keep_old_before"][c], "after": after[c]} for c in COPIES}
    ear = {"vote": vote, "copies": copies, "keep_old": keep_old,
           "gates": cube_read.gates(vote["sdg"], vote["llm"], copies, keep_old, FZ["ear_gates"])}
    with open(os.path.join(out, "MOUTH_EXAM_OUTPUTS.json"), "w", encoding="utf-8") as fh:
        json.dump({"records": records, "other_copy_fallbacks": other_fallbacks}, fh, indent=1, ensure_ascii=False)
    finals_sha = {m: sha256_file(p) for m, p in finals.items()}
    return finish(out, inst, audits, {"records": records, "ear": ear, "finals_sha256": finals_sha,
                                      "other_copy_fallbacks": other_fallbacks})


def finish(out, inst, audits, body) -> int:
    from read_mouth import read_host
    inst.setdefault("I4_audits_clean", all(not v for v in audits.values()))
    est = round((time.time() - T0) / 3600 * FZ_PRICE, 4)
    inst["I5_cost_under_cap_estimate"] = est <= FZ["cap_usd"]
    reading = read_host(inst, audits, body, FZ)
    reading["estimated_cost_usd_this_script"] = est
    with open(os.path.join(out, "MOUTH_HOST_READING.json"), "w", encoding="utf-8") as fh:
        json.dump(reading, fh, indent=1, sort_keys=True)
    note(out, {"event": "done", "host_word": reading["host_word"]})
    return 0


FZ = None
FZ_PRICE = 1.006

if __name__ == "__main__":
    sys.exit(main())
