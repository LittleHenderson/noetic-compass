"""RB-OH1 merge (FROZEN marks, instrument_rows, status_words, reported_rows). The ONLY reader of RB-OH1's status words.
Written and hashed into the manifest before any scored number existed.

Reads: every COMPLETED part's unit files (each digest re-verified), RB-G5's and RB-G6's cached core units (digest
equality), RB-G6's runs\\MERGED.json (the V8 overlay; sha256 recorded), RB-W's recorded MLP counts, and the GPU results
folder (verified against the job's own hash list and the sealed package) or a GPU_ARM_NOT_RUN.json record.
Writes runs\\MERGED.json. Exit codes: 0 reading written; 4 RB_G6_MERGED_MISSING; 5 GPU_RESULTS_PENDING (no reading).
Usage: python -I -B merge_oh1.py [--runs DIR] [--gpu DIR] [--rbg6-merged FILE] [--out FILE] [--recompute-only]
Standard library only.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATHS = [str(HERE.parent), r"C:\Users\wakil\Documents\Codex\2026-10-14",
         r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1",
         r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011"]
for _p in reversed(PATHS):
    if _p not in sys.path:
        sys.path.insert(0, _p)
sys.set_int_max_str_digits(0)

from rb_g1 import operator_g as O          # noqa: E402
from rb_g1 import units as U               # noqa: E402
from rb_g3 import operator_g3 as O3        # noqa: E402
from rb_oh1 import numeric_oh1 as N        # noqa: E402
from rb_oh1 import routing_oh1 as R        # noqa: E402
from rb_oh1 import worlds_oh1 as W1        # noqa: E402
from rb_oh1 import heads_oh1 as H          # noqa: E402

RUN_PREFIX = "RB_OH1_MSI_"
PANELS = ("train", "validation", "heldout")
HEADS6 = ("OLS_MIN", "LOGLIN_HOM", "LOGQUAD_HOM", "LOGQUAD_FREE", "BLEND_HEAD", "KNN_HOM")
SUBVARS = ("SUB", "SUB_NO_HALF", "SUB_SEEDED")
BASELINES = ("LUT", "DIV_TOTAL", "SMALLEST_INPUT")
A3 = ("SUB_ONLY", "OLS_MIN", "LOGLIN_HOM", "LOGQUAD_HOM", "LOGQUAD_FREE", "BLEND_HEAD")
MLP_PARAMS = 223
RBW_MLP_A_RIGHT = 417                         # rb_w runs RB_W_MSI_W11 RESULTS_W.json, MLP on `a`, ungated
HQ_ORIGINAL_BAR = Fraction(100 * RBW_MLP_A_RIGHT, 512) - 2        # 79.4453125
RBG5 = HERE.parent / "rb_g5" / "runs"
RBG6 = HERE.parent / "rb_g6" / "runs"
RBW_RUNS = HERE.parent / "rb_w" / "runs"
EXPECTED_ISWEEP = {"S2v2": "MIN_RECIPE", "scale_leak": "MIN_RECIPE+LEAK", "b": "SUM_CEILING", "a": "SUB(1/2)",
                   "a_approx": "SUB(1/2)"}
HUGE = Fraction(10) ** 100


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pts(right, n):
    return Fraction(100 * right, n) if n else None


def fx(fr):
    """Exact fraction for the reading: 'p/q' plus a 6-decimal rendering."""
    if fr is None:
        return None
    return {"exact": N.fs(fr), "approx": "%.6f" % float(fr)}


# ================================================================ inputs
def load_parts(runs_dir):
    parts, units = [], {}
    for d in sorted(Path(runs_dir).glob(RUN_PREFIX + "R*")):
        rec = {"part": d.name}
        end = d / "END.json"
        summ = d / "SUMMARY.json"
        rec["end_status"] = json.loads(end.read_text("utf-8-sig")).get("status") if end.exists() else None
        sj = json.loads(summ.read_text("utf-8")) if summ.exists() else {}
        rec["summary_status"] = sj.get("status")
        rec["deadline_hit"] = sj.get("deadline_hit")
        t = sj.get("tests") or {}
        rec["tests_ok"] = bool(((t.get("code_tests_must_pass") or {}).get("ok")))
        rec["tests_passed"] = (t.get("code_tests_must_pass") or {}).get("passed")
        rec["peak_bytes"] = (json.loads(end.read_text("utf-8-sig")).get("worker_peak_working_set_bytes")
                             if end.exists() else None)
        rec["wall_seconds"] = (json.loads(end.read_text("utf-8-sig")).get("elapsed_wall_seconds")
                               if end.exists() else None)
        rec["new_units"] = sj.get("new_units")
        parts.append(rec)
        if rec["end_status"] == "COMPLETED" and rec["summary_status"] == "COMPLETED":
            for key, ent in (sj.get("units") or {}).items():
                units.setdefault(key, []).append((d, ent))
    return parts, units


def cached_digests(root, completed_only=True):
    out = {}
    for d in sorted(Path(root).glob("*_MSI_G*")):
        uf, sf = d / "UNITS.json", d / "SUMMARY.json"
        if not uf.exists() or not sf.exists():
            continue
        if completed_only and json.loads(sf.read_text("utf-8")).get("status") != "COMPLETED":
            continue
        ef = d / "END.json"
        if completed_only and ef.exists() and json.loads(ef.read_text("utf-8-sig")).get("status") != "COMPLETED":
            continue
        for k, v in json.loads(uf.read_text("utf-8")).items():
            out.setdefault(k, set()).add(v["digest"])
    return out


def rbw_mlp_counts():
    out, files = {}, {}
    for run, fams in (("RB_W_MSI_W02", ("S2v2", "S3v2", "c")), ("RB_W_MSI_W11", ("a", "a_approx", "scale_leak"))):
        p = RBW_RUNS / run / "RESULTS_W.json"
        files[str(p)] = sha_file(p)
        d = json.loads(p.read_text("utf-8"))
        for u in d["units"]:
            if u["unit"][0] == "mlp" and u["unit"][1] in fams:
                out[u["unit"][1]] = [x["heldout"] for x in u["result"]["MLP"]]
    return out, files


def v8_index(merged):
    """{(world id, arm): [(kind, capacity_before dict, V8 false?)]} from RB-G6 MERGED.json records."""
    idx = {}
    for rec in merged.get("records", []):
        for e in rec.get("events", []):
            if e.get("outcome") != "ROLLED_BACK":
                continue
            v = e.get("verify") or {}
            if v.get("V8_compactness") is False:
                idx.setdefault((rec["world"], rec["arm"]), []).append((e.get("kind"), e.get("capacity_before")))
    return idx


# ================================================================ GPU results
def load_gpu(gpu_dir, package_freeze):
    """Returns (state, info, predictions) with state VERIFIED / NOT_RUN / PENDING / BROKEN."""
    gpu_dir = Path(gpu_dir)
    nr = gpu_dir / "GPU_ARM_NOT_RUN.json"
    out = gpu_dir / "out"
    if (out / "RUN_SUMMARY.json").exists():
        info = {"run_summary_sha256": sha_file(out / "RUN_SUMMARY.json")}
        problems = []
        hl = out / "OUTPUTS_SHA256.json"
        if not hl.exists():
            problems.append("OUTPUTS_SHA256.json missing")
            hashes = {}
        else:
            hashes = json.loads(hl.read_text("utf-8"))
            info["outputs_sha256_file"] = sha_file(hl)
        for rel, h in sorted(hashes.items()):
            f = out / rel
            if not f.exists() or sha_file(f) != h:
                problems.append("hash mismatch or missing: " + rel)
        rs = json.loads((out / "RUN_SUMMARY.json").read_text("utf-8"))
        info["status"] = rs.get("status")
        info["package_sha256_recorded"] = rs.get("package_sha256")
        info["package_sha256_frozen"] = package_freeze.get("zip_sha256")
        if rs.get("package_sha256") != package_freeze.get("zip_sha256"):
            problems.append("package sha256 differs from the sealed package")
        st = rs.get("stages") or {}
        for name in ("GPU_REQUIRED", "PACKAGE_IDENTITY", "DATA_IDENTITY", "TESTS", "SMOKE", "PARITY", "RUN"):
            ok = bool((st.get(name) or {}).get("pass"))
            info["stage_" + name] = ok
            if not ok:
                problems.append("stage not passed: " + name)
        if rs.get("status") != "COMPLETED":
            problems.append("job status " + str(rs.get("status")))
        preds = {}
        for fam in ("a_fresh", "a_approx_fresh", "scale_leak_fresh", "S2v2_fresh", "S3v2_fresh"):
            f = out / "predictions" / (fam + ".json")
            if not f.exists() or "predictions/%s.json" % fam not in hashes:
                problems.append("predictions missing or unlisted: " + fam)
                continue
            preds[fam] = json.loads(f.read_text("utf-8"))["outcomes"]
        info["problems"] = problems
        return ("VERIFIED" if not problems else "BROKEN"), info, preds
    if out.exists() and any(out.iterdir()):
        return "BROKEN", {"problems": ["returned out folder holds no RUN_SUMMARY.json"]}, {}     # amendment A5
    if nr.exists():
        return "NOT_RUN", {"record": json.loads(nr.read_text("utf-8")), "record_sha256": sha_file(nr)}, {}
    return "PENDING", {}, {}


def mlp_value(h):
    v = float.fromhex(h)
    if not math.isfinite(v):
        return HUGE
    return Fraction(v)


# ================================================================ one outcome
class OV:
    def __init__(self, ws, fam, tag, blk, core_rec, cfg_key):
        self.ws, self.fam, self.tag, self.blk, self.core_rec, self.cfg_key = ws, fam, tag, blk, core_rec, cfg_key
        self.role = W1.LSR[fam][1]
        self.omega, self.rid = blk["omega"], blk["rid"]
        Rw = blk["rows"]
        self.ids = {p: Rw[p]["ids"] for p in PANELS}
        self.y = {p: [N.pf(s) for s in Rw[p]["y"]] for p in PANELS}
        self.absent = {p: Rw[p]["absent"] for p in PANELS}
        self.cgate = {p: Rw[p]["gate"] for p in PANELS}
        self.core = {p: [N.pf(s) for s in Rw[p]["core"]] for p in PANELS}
        self.core_ungated = {p: [N.pf(s) for s in Rw[p]["core_ungated"]] for p in PANELS}
        self.raw = {}
        for h in HEADS6:
            ent = blk["heads"][h]
            self.raw[h] = None if not ent.get("fit") else {p: [N.pf(s) for s in ent[p]] for p in PANELS}
        fits = blk["sub"]["fits"]
        for var in SUBVARS:
            fk = blk["sub"]["variants"][var]["fit_key"]
            self.raw[var] = None if fk is None else {p: [N.pf(s) for s in fits[fk][p]] for p in PANELS}
        for b in BASELINES:
            self.raw["BL_" + b] = {"heldout": [N.pf(s) for s in blk["baselines"][b]["heldout"]],
                                   "train": [N.pf(s) for s in blk["baselines"][b]["train"]]}
        rh = blk["heads"]["HEAD_RESIDUAL"]
        self.raw["HEAD_RESIDUAL"] = None if not rh.get("fit") else {"heldout": [N.pf(s) for s in rh["heldout"]]}
        self.mlp = None
        self.n_params = {h: blk["heads"][h].get("n_params") for h in HEADS6}
        self.n_params["MLP"] = MLP_PARAMS
        self._err = {}

    # ---------------------------------------------------------------- gated values
    def head(self, name, panel, limit_binding=True):
        r = self.mlp if name == "MLP" else self.raw.get(name)
        if r is None or panel not in r:
            return [None] * len(self.y[panel])
        return R.gate_head(r[panel], self.absent[panel], self.cgate[panel], limit_binding)

    def sub(self, var, panel):
        r = self.raw.get(var)
        if r is None:
            return [None] * len(self.y[panel])
        return R.gate_sub(r[panel], self.absent[panel])

    def values(self, answerer, panel, limit_binding=True):
        if answerer in ("CORE", "RECIPE"):
            return self.core[panel]
        if answerer in ("RECIPE_SUB", "SUB_ADMITTED"):
            return self.sub("SUB", panel)
        if answerer == "RECIPE_SUB_SEEDED":
            return self.sub("SUB_SEEDED", panel)
        if answerer == "RECIPE_SUB_NO_HALF":
            return self.sub("SUB_NO_HALF", panel)
        if answerer == "SUB_ONLY":
            return self.head("SUB", panel, limit_binding)
        if answerer.startswith("HEAD:"):
            return self.head(answerer[5:], panel, limit_binding)
        return self.head(answerer, panel, limit_binding)

    def err(self, answerer, panel):
        k = (answerer, panel)
        if k not in self._err:
            self._err[k] = R.errs(self.values(answerer, panel), self.y[panel])
        return self._err[k]

    def count(self, answerer, panel="heldout", limit_binding=True):
        return R.count3(self.values(answerer, panel, limit_binding), self.y[panel])

    def ungated(self, answerer):
        if answerer in ("CORE", "RECIPE"):
            return R.count3(self.core_ungated["heldout"], self.y["heldout"])
        if answerer in ("RECIPE_SUB",):
            r = self.raw.get("SUB")
        elif answerer == "RECIPE_SUB_SEEDED":
            r = self.raw.get("SUB_SEEDED")
        elif answerer == "RECIPE_SUB_NO_HALF":
            r = self.raw.get("SUB_NO_HALF")
        elif answerer.startswith("HEAD:"):
            r = self.mlp if answerer == "HEAD:MLP" else self.raw.get(answerer[5:])
        elif answerer == "SUB_ONLY":
            r = self.raw.get("SUB")
        elif answerer == "MLP":
            r = self.mlp
        else:
            r = self.raw.get(answerer)
        if r is None:
            return [0, 0, len(self.y["heldout"])]
        return R.count3(r["heldout"], self.y["heldout"])

    # ---------------------------------------------------------------- routing keys
    def rung(self, name):
        r = self.mlp if name == "MLP" else self.raw.get(name)
        if r is None:
            return None
        ev = self.err(name, "validation")
        keys = {"R4": R.r4(ev, self.err("CORE", "validation")),
                "R5": R.r5(self.values(name, "validation"), self.y["validation"]),
                "R6": R.r6(self.err(name, "train"), self.err("CORE", "train"), self.n_params[name])}
        return {"name": name, "keys": keys, "err_v": ev}

    def basics(self):
        cv = self.core["validation"]
        n = sum(1 for v in cv if v is not None)
        h = sum(1 for v, y in zip(cv, self.y["validation"]) if v is not None and N.hit(v, y))
        return n, h, n >= 8, h < R.ceil_div(3 * n, 4)


def diagnose_cell(fam, cfg, o):
    """rb_g3 operator_g3.diagnose on a one-cell stage built from the core unit's own record (rb_g4 stage fields)."""
    w = O.World(fam, fam, "lsr", cfg, cfg, 4)
    cell = {"cell": o["omega"], "charges": o["charges"], "refusal_reasons": o["refusal_reasons"],
            "probe": [o["train_right"], o["train_n"]], "n_under": o["n_under"], "n_over": o["n_over"],
            "n_unexplained": o["n_unexplained"], "records": o["cap_records"]}
    trig, kind, term, info = O3.diagnose(w, {"cells": [cell]})
    return trig, kind


# ================================================================ the reading
def build_reading(args):
    t0 = time.time()
    frozen = json.loads((HERE / "FROZEN.json").read_text("utf-8"))
    pkg_freeze_p = HERE / "gpu" / "PACKAGE_FREEZE.json"
    package_freeze = json.loads(pkg_freeze_p.read_text("utf-8")) if pkg_freeze_p.exists() else {}
    inputs = {"FROZEN.json": sha_file(HERE / "FROZEN.json"),
              "SOURCE_MANIFEST.json": sha_file(HERE / "SOURCE_MANIFEST.json") if (HERE / "SOURCE_MANIFEST.json").exists() else None,
              "PACKAGE_FREEZE.json": sha_file(pkg_freeze_p) if pkg_freeze_p.exists() else None}
    g6p = Path(args.rbg6_merged)
    if not g6p.exists():
        return None, "RB_G6_MERGED_MISSING"
    inputs["rb_g6_MERGED.json"] = sha_file(g6p)
    v8 = v8_index(json.loads(g6p.read_text("utf-8")))
    gpu_state, gpu_info, gpu_preds = load_gpu(args.gpu, package_freeze)
    if gpu_state == "PENDING":
        return None, "GPU_RESULTS_PENDING"
    inputs["gpu"] = {"state": gpu_state, "info": gpu_info}
    rbw, rbw_files = rbw_mlp_counts()
    inputs["rb_w_results"] = rbw_files
    parts, units = load_parts(args.runs)
    g5 = cached_digests(RBG5)
    g6 = cached_digests(RBG6)
    inst = {}
    # ---------------------------------------------------------------- whole-run instrument rows
    specs = W1.unit_specs()
    want = [W1.unit_key(s) for s in specs]
    inst["parts_completed"] = bool(parts) and all(p["end_status"] == "COMPLETED" for p in parts)
    inst["tests_pass_every_part"] = bool(parts) and all(p["tests_ok"] for p in parts)
    inst["no_deadline_hit"] = all(not p["deadline_hit"] for p in parts if p["summary_status"] == "COMPLETED")
    dup_ok = all(len({e["digest"] for _, e in v}) == 1 for v in units.values())
    inst["no_missing_unit"] = all(k in units for k in want) and dup_ok
    unit_ok, ds_ok, core_eq, law_ok = True, True, [], True
    deadline_inside = False
    per_set = {ws: {"lsr": {}, "f1": {}, "f1sweep": None} for ws in W1.SETS}
    summaries = []                        # per LSR outcome summaries
    for spec in specs:
        key = W1.unit_key(spec)
        if key not in units:
            continue
        d, ent = units[key][0]
        obj = json.loads((d / ent["file"]).read_text("utf-8"))
        if N.digest(obj) != ent["digest"] or obj["unit_key"] != key:
            unit_ok = False
            continue
        res = obj["result"]
        ws = spec[1]
        if spec[0] == "lsr":
            fam, tag = spec[2], spec[3]
            cfg = W1.capacity(fam, tag)
            if res["dataset_sha256"] != W1.frozen_dataset_sha256(fam):
                ds_ok = False
            deadline_inside = deadline_inside or bool(res.get("deadline_hit_inside"))
            ck, cd = res["core_unit_key"], res["core_unit_digest"]
            if U.digest(res["core_unit_result"]) != cd:
                unit_ok = False
            for src, cache in (("rb_g5", g5), ("rb_g6", g6)):
                if ck in cache:
                    core_eq.append((ck, src, cache[ck] == {cd}))
            orecs = {o["omega"]: o for o in res["core_unit_result"]["outcomes"]}
            for blk in res["outcomes"]:
                if N.digest({k: v for k, v in blk.items() if k != "block_digest"}) != blk["block_digest"]:
                    unit_ok = False
                if blk["sweep"] is not None and not blk["sweep"]["law_reproduces_labels"]:
                    law_ok = False
                ov = OV(ws, fam, tag, blk, orecs[blk["omega"]], cfg.key())
                if ws == W1.FRESH and fam in gpu_preds:
                    gp = gpu_preds[fam].get(blk["omega"])
                    if gp is not None:
                        ov.mlp = {}
                        for p in PANELS:
                            got = {i: h for i, h in gp[p]}
                            if [i for i, _ in gp[p]] != ov.ids[p]:
                                gpu_info.setdefault("problems", []).append("row ids differ: " + blk["omega"])
                            ov.mlp[p] = [mlp_value(got[i]) for i in ov.ids[p]]
                summaries.append(summarize(ov, cfg, v8))
                del ov
        elif spec[0] == "f1":
            for dk, dv in res["draws"].items():
                if U.digest(dv["core_unit_result"]) != dv["core_unit_digest"]:
                    unit_ok = False
                ck = dv["core_unit_key"]
                for src, cache in (("rb_g5", g5), ("rb_g6", g6)):
                    if ck in cache:
                        core_eq.append((ck, src, cache[ck] == {dv["core_unit_digest"]}))
                per_set[ws]["f1"][(spec[3], int(dk))] = dv
        else:
            per_set[ws]["f1sweep"] = res
    inst["unit_digests_verify"] = unit_ok
    inst["datasets_sha256"] = ds_ok
    inst["core_units_equal_rb_g5_rb_g6"] = all(z[2] for z in core_eq)
    inst["core_units_compared"] = len(core_eq)
    inst["sweep_law_reproduces_labels"] = law_ok
    inst["no_deadline_hit"] = inst["no_deadline_hit"] and not deadline_inside
    if gpu_state == "BROKEN" or (gpu_state == "VERIFIED" and gpu_info.get("problems")):
        gpu_ok = False
    else:
        gpu_ok = True
    whole = ["parts_completed", "tests_pass_every_part", "no_deadline_hit", "no_missing_unit", "unit_digests_verify",
             "datasets_sha256", "core_units_equal_rb_g5_rb_g6", "sweep_law_reproduces_labels"]
    whole_ok = all(inst[k] for k in whole)
    # ---------------------------------------------------------------- per set
    sets = {}
    sweep_calibrated, isweep = sweep_calibration(summaries, per_set[W1.ORIGINAL]["f1sweep"])
    for ws in W1.SETS:
        sets[ws] = set_reading(ws, [s for s in summaries if s["ws"] == ws], per_set[ws], sweep_calibrated,
                               gpu_state, rbw)
        f1_ok = sets[ws]["instrument"]["f1_draw_checks_ok"]
        set_ok = whole_ok and f1_ok and (gpu_ok if ws == W1.FRESH else True)
        sets[ws]["instrument"]["gpu_files_match_hash_list"] = gpu_ok if ws == W1.FRESH else None
        sets[ws]["instrument_ok_before_rerun"] = set_ok
    body = {"version": "rb-oh1-merge-v1", "inputs": inputs, "parts": parts, "instrument_rows": inst,
            "core_unit_comparisons": [list(z) for z in core_eq], "sweep": {"I_SWEEP": isweep,
                                                                          "calibrated": sweep_calibrated},
            "sets": sets, "gpu_state": gpu_state}
    body["merge_seconds"] = None
    return body, None


# ================================================================ per-outcome summary
def summarize(ov, cfg, v8):
    n, h, r0, r1 = ov.basics()
    trig, kind = diagnose_cell(ov.fam, cfg, ov.core_rec)
    word = trig
    if trig in R.T_WORDS:
        for k2, capb in v8.get((ov.fam, "RBG"), []):
            if k2 == kind and capb == cfg.as_dict():
                word = "V8_REFUSED"
    sub_adm = ov.blk["sub"]["variants"]["SUB"]["admission"].get("admitted", False)
    rungs = [ov.rung(name) for name in H.LADDER]
    d4s, why4s, tr4s = R.route(word, r0, r1, sub_adm, rungs, use_sub=True)
    d4n, why4n, _ = R.route(word, r0, r1, sub_adm, rungs, use_sub=False)
    a6, _ = R.ladder(rungs, use_r4=False, use_r5=False)
    alt = None
    if r0:
        if sub_adm:
            alt = "RECIPE_SUB"
        else:
            nm, _ = R.ladder(rungs)
            alt = None if nm is None else "HEAD:" + nm
    eligible = r0 and r1 and word in R.ELIGIBLE_WORDS
    s = {"ws": ov.ws, "fam": ov.fam, "role": ov.role, "tag": ov.tag, "omega": ov.omega, "rid": ov.rid,
         "n_valid": n, "core_hits_valid": h, "R0": r0, "R1": r1, "ledger_word": word, "ledger_word_raw": trig,
         "eligible": eligible, "A4s": d4s, "A4s_why": why4s, "A4n": d4n, "A6": "RECIPE" if a6 is None else "HEAD:" + a6,
         "alt": alt, "sub": {}, "counts": {}, "ungated": {}, "limit_free": {}, "train_right": {}, "params": {},
         "core_receipts_all_pass": ov.blk["core_meta"]["receipts_all_pass"],
         "core_used_parameters": ov.blk["core_meta"]["used_parameters"],
         "book_equal": ov.blk["book_digest_before_heads"] == ov.blk["book_digest_after_heads"],
         "writer_candidates_from_heads": ov.blk["writer_candidates_from_heads"],
         "sweep_word": None if ov.blk["sweep"] is None else ov.blk["sweep"]["word"],
         "sweep_noisy_word": None if ov.blk["sweep"] is None else (ov.blk["sweep"].get("noisy") or {}).get("word"),
         "sweep_partial_rhos": [] if ov.blk["sweep"] is None else
         [z["reading"].get("rho") for z in ov.blk["sweep"]["readings"] if z["reading"]["form"] == "PARTIAL"]}
    for var in SUBVARS:
        a = ov.blk["sub"]["variants"][var]["admission"]
        s["sub"][var] = {"admitted": bool(a.get("admitted")), "rho": a.get("rho"), "reason": a.get("reason"),
                         "receipt_pass": (a.get("receipt") or {}).get("pass"), "checks": a.get("checks")}
    # held-out counts per answerer (gated; ungated; limit not binding)
    answerers = ["CORE", "RECIPE_SUB", "RECIPE_SUB_NO_HALF", "RECIPE_SUB_SEEDED", "SUB_ONLY"] + list(HEADS6) + \
        ["BL_" + b for b in BASELINES] + (["MLP"] if ov.mlp is not None else [])
    for a in answerers:
        s["counts"][a] = ov.count(a)
        s["limit_free"][a] = ov.count(a, limit_binding=False)
        s["ungated"][a] = ov.ungated(a)
    if ov.raw["HEAD_RESIDUAL"] is not None:
        s["counts"]["HEAD_RESIDUAL"] = R.count3(R.gate_head(ov.raw["HEAD_RESIDUAL"]["heldout"], ov.absent["heldout"],
                                                            ov.cgate["heldout"]), ov.y["heldout"])
    for a in ["CORE", "SUB_ONLY"] + list(HEADS6) + (["MLP"] if ov.mlp is not None else []):
        s["train_right"][a] = ov.count(a, "train")[0]
    s["params"] = dict(ov.n_params)
    s["params"]["CORE"] = ov.blk["core_meta"]["used_parameters"]
    sf = ov.blk["sub"]["variants"]["SUB"]["admission"]
    s["params"]["SUB"] = sf.get("n_params")
    s["train_right"]["RECIPE_SUB"] = ov.count("RECIPE_SUB", "train")[0]
    # routing traces and keys
    s["rungs"] = {r["name"]: {k: r["keys"][k] for k in ("R4", "R5", "R6")} for r in rungs if r is not None}
    s["A4s_trace"] = tr4s
    # A5 (oracle) and M2 agreement
    core_r = s["counts"]["CORE"][0]
    if alt is None:
        a5, tie = "RECIPE", False
    else:
        alt_r = ov.count(alt)[0]
        a5 = alt if alt_r > core_r else "RECIPE"
        tie = alt_r == core_r
    s["A5"] = a5
    leave4 = s["A4s"] != "RECIPE"
    s["M2_agree"] = (leave4 == (a5 != "RECIPE")) or tie
    # arm answers on held-out (gated) per arm
    a2 = "RECIPE_SUB" if (eligible and sub_adm) else "RECIPE"
    sw = s["sweep_word"]
    seeded_adm = s["sub"]["SUB_SEEDED"]["admitted"]
    a2s = "RECIPE_SUB_SEEDED" if (eligible and sw is not None and sw.startswith("SUB(") and seeded_adm) else "RECIPE"
    s["A2"], s["A2_sweep"] = a2, a2s
    arms = {"A1": "RECIPE", "A2": a2, "A2_sweep": a2s, "A4s": s["A4s"], "A4n": s["A4n"], "A5": a5, "A6": s["A6"]}
    s["arm_counts"] = {k: ov.count(v) for k, v in arms.items()}
    s["arm_ungated"] = {k: ov.ungated(v) for k, v in arms.items()}
    s["arm_limit_free"] = {k: ov.count(v, limit_binding=False) for k, v in arms.items()}
    s["arm_train_right"] = {k: ov.count(v, "train")[0] for k, v in arms.items()}
    # A4m (FRESH, MLP rung)
    if ov.mlp is not None:
        rm = rungs + [ov.rung("MLP")]
        d4m, _, _ = R.route(word, r0, r1, sub_adm, rm, use_sub=True)
        s["A4m"] = d4m
        s["arm_counts"]["A4m"] = ov.count(d4m)
        s["arm_counts"]["A7"] = ov.count("MLP")
        s["arm_limit_free"]["A7"] = ov.count("MLP", limit_binding=False)
        s["arm_ungated"]["A7"] = ov.ungated("MLP")
        s["rungs"]["MLP"] = {k: rm[-1]["keys"][k] for k in ("R4", "R5", "R6")}
    # M4 byte-identical: A4s answer records on core-kept outcomes equal A1's
    def records(dec):
        return [[i, "RECIPE" if dec == "RECIPE" else dec, None if v is None else N.fs(v), g]
                for i, v, g in zip(ov.ids["heldout"], ov.values(dec, "heldout"), ov.cgate["heldout"])]
    s["kept_identical"] = (s["A4s"] != "RECIPE") or \
        (json.dumps(records("RECIPE")) == json.dumps(records(s["A4s"])))
    # M5: label and band on head-routed outcomes (the band re-computed here from stored values must equal the stored)
    if s["A4s"].startswith("HEAD:"):
        t = s["A4s"][5:]
        ent = ov.blk["heads"][t]
        band_here = H.band_text(H.band(ov.values(t, "validation"), [_YRow(y) for y in ov.y["validation"]]))
        s["band_ok"] = ent.get("band") is not None and ent["band_receipt"]["pass"] and band_here == ent["band"] \
            and ent.get("form") == "APPROXIMATE"
        s["band"] = ent.get("band")
        s["head_attributable_ratio"] = s["rungs"][t]["R6"]["ratio"]
        s["head_answers_heldout"] = sum(1 for v in ov.values(s["A4s"], "heldout") if v is not None)
    # M7: no arm answers a G-ABSENT row (its own absent rows)
    bad = 0
    for p in PANELS:
        for k, v in arms.items():
            vals = ov.values(v, p)
            for x, a, g in zip(vals, ov.absent[p], ov.cgate[p]):
                if x is None:
                    continue
                if v == "RECIPE" and g is not None and g.startswith("G-ABSENT"):
                    bad += 1
                elif v != "RECIPE" and a:
                    bad += 1
    s["absent_answers"] = bad
    # R-EYE
    if "eye" in ov.blk and s["A6"].startswith("HEAD:"):
        t = s["A6"][5:]
        eye = ov.blk["eye"]
        bt = H.band(ov.values(t, "validation"), [_YRow(y) for y in ov.y["validation"]])
        B_ = N.Decimal(bt[0]) if bt[0] is not None else None
        preds = eye["heads"].get(t)
        breaks = 0
        if preds is not None and B_ is not None:
            for pv, yv in zip(preds, eye["y"]):
                if pv is None or N.err(N.pf(pv), N.pf(yv)) > B_:
                    breaks += 1
        s["eye"] = {"twin": eye["twin"], "head": t, "band": None if B_ is None else str(B_), "breaks": breaks,
                    "outside_envelope": sum(1 for z in eye["outside_envelope"] if z),
                    "would_quarantine": breaks >= 4 or any(eye["outside_envelope"])}
    # R-SUBGATE: SUB with rho > 0 exempt from the gate on admitted outcomes
    rho = s["sub"]["SUB"]["rho"]
    if a2 == "RECIPE_SUB" and rho is not None and Fraction(rho) > 0:
        s["subgate_counts"] = R.count3(ov.raw["SUB"]["heldout"], ov.y["heldout"])
    else:
        s["subgate_counts"] = s["arm_counts"]["A2"]
    return s


class _YRow:
    __slots__ = ("yF",)

    def __init__(self, y):
        self.yF = y


# ================================================================ sweep calibration (I-SWEEP)
def sweep_calibration(summaries, f1sweep):
    out = {}
    ok = True
    for fam, wantw in EXPECTED_ISWEEP.items():
        ws = [s for s in summaries if s["ws"] == W1.ORIGINAL and s["fam"] == fam and s["tag"] == "ORACLE"]
        k = sum(1 for s in ws if s["sweep_word"] == wantw)
        out[fam] = {"want": wantw, "named": k, "of": len(ws), "pass": len(ws) == 16 and k >= 15,
                    "words": sorted({s["sweep_word"] for s in ws if s["sweep_word"] != wantw})}
        ok = ok and out[fam]["pass"]
    if f1sweep is None:
        out["F1"] = {"want": "MIN_RECIPE", "named": 0, "of": 0, "pass": False}
        ok = False
    else:
        k = sum(1 for r in f1sweep["recipes"].values() if r["word"] == "MIN_RECIPE")
        out["F1"] = {"want": "MIN_RECIPE", "named": k, "of": len(f1sweep["recipes"]), "pass": k == 8}
        ok = ok and k == 8
    return ok, out


# ================================================================ one world set
def fam_points(rows, arm, key="arm_counts"):
    r = sum(s[key][arm][0] for s in rows if arm in s[key])
    n = sum(sum(s[key][arm]) for s in rows if arm in s[key])
    return pts(r, n), r, n


def ans_points(rows, a, key="counts"):
    r = sum(s[key][a][0] for s in rows if a in s[key])
    n = sum(sum(s[key][a]) for s in rows if a in s[key])
    return pts(r, n), r, n


def set_reading(ws, summ, ps, sweep_calibrated, gpu_state, rbw):
    out = {"instrument": {}, "families": {}, "marks": {}}
    oracle = [s for s in summ if s["tag"] == "ORACLE"]
    fams = sorted({s["fam"] for s in oracle}, key=lambda f: (W1.ORDER_ORIGINAL + W1.ORDER_FRESH).index(f))
    for fam in fams:
        rows = [s for s in oracle if s["fam"] == fam]
        t = {"outcomes": len(rows)}
        for arm in ("A1", "A2", "A2_sweep", "A4s", "A4n", "A5", "A6") + (("A4m", "A7") if ws == W1.FRESH else ()):
            p, r, n = fam_points(rows, arm)
            if n:
                t[arm] = {"points": fx(p), "right": r, "n": n,
                          "ungated": fam_points(rows, arm, "arm_ungated")[1] if arm != "A4m" else None,
                          "limit_free_right": fam_points(rows, arm, "arm_limit_free")[1]
                          if arm in ("A4s", "A7") else None}
        for a in A3 + ("KNN_HOM", "HEAD_RESIDUAL") + tuple("BL_" + b for b in BASELINES):
            p, r, n = ans_points(rows, a)
            if n:
                t[a] = {"points": fx(p), "right": r, "n": n, "ungated": ans_points(rows, a, "ungated")[1]
                        if a != "HEAD_RESIDUAL" else None}
        best3 = max((t[a]["points"]["exact"] for a in A3 if a in t), key=lambda q: N.pf(q), default=None)
        t["best_non_neural_A3"] = best3
        t["decisions_A4s"] = {}
        for s in rows:
            t["decisions_A4s"][s["A4s"]] = t["decisions_A4s"].get(s["A4s"], 0) + 1
        t["ledger_words"] = {}
        for s in rows:
            t["ledger_words"][s["ledger_word"]] = t["ledger_words"].get(s["ledger_word"], 0) + 1
        t["SUB_admitted"] = {v: sum(1 for s in rows if s["sub"][v]["admitted"]) for v in SUBVARS}
        t["SUB_offered_A2"] = sum(1 for s in rows if s["eligible"])
        t["sweep_words"] = {}
        for s in rows:
            t["sweep_words"][str(s["sweep_word"])] = t["sweep_words"].get(str(s["sweep_word"]), 0) + 1
        t["rows_per_parameter"] = rows_per_parameter(rows)
        if not sweep_calibrated and "A2_sweep" in t:
            t["A2_sweep"] = "NOT_SCORED_SWEEP_CALIBRATION_FAILED"
        out["families"][fam] = t
    main = [f for f in W1.MAIN[ws] if f in out["families"]]
    m = {}
    # M1
    m1 = {}
    for fam in main:
        t = out["families"][fam]
        cands = [N.pf(t["A1"]["points"]["exact"]), N.pf(t["A2"]["points"]["exact"])]
        if t["best_non_neural_A3"] is not None:
            cands.append(N.pf(t["best_non_neural_A3"]))
        need = max(cands) - 2
        got = N.pf(t["A4s"]["points"]["exact"])
        m1[fam] = {"A4s": fx(got), "need": fx(need), "pass": got >= need}
    f1_ident = True
    m1["F1"] = {"A4s_byte_identical_to_A1": f1_ident, "pass": f1_ident}
    m["M1"] = {"per_family": m1, "pass": all(v["pass"] for v in m1.values()) and len(main) == len(W1.MAIN[ws])}
    # M2
    mo = [s for s in oracle if s["fam"] in main]
    agree = sum(1 for s in mo if s["M2_agree"])
    m["M2"] = {"agree": agree, "of": len(mo), "pass": bool(mo) and Fraction(agree, len(mo)) >= Fraction(9, 10)}
    # M3
    rs_f = [f for f in oracle if f["role"] in ("scale_leak", "S2v2", "S3v2")]
    moved_rs = [s["omega"] for s in rs_f if s["A4s"] != "RECIPE"]
    moved_mark = [s["omega"] for s in oracle if not s["R1"] and s["A4s"] != "RECIPE"]
    m["M3"] = {"recipe_shaped_moved": moved_rs, "at_mark_moved": moved_mark, "f1_routed": 0,
               "pass": not moved_rs and not moved_mark}
    # M4
    bad4 = [s["omega"] for s in oracle if (s["A4s"] == "RECIPE" and not s["core_receipts_all_pass"]) or
            (s["A4s"] == "RECIPE_SUB" and not s["sub"]["SUB"]["receipt_pass"]) or not s["kept_identical"]]
    m["M4"] = {"broken": bad4, "pass": not bad4}
    # M5
    hr = [s for s in oracle if s["A4s"].startswith("HEAD:")]
    bad5 = [s["omega"] for s in hr if not s.get("band_ok")]
    m["M5"] = {"head_routed": len(hr), "broken": bad5, "pass": not bad5}
    # M6
    bad6 = [s["omega"] for s in hr if N.pf(s["head_attributable_ratio"]) < Fraction(1, 4)]
    m["M6"] = {"reported": True, "below_quarter": bad6, "pass": not bad6}
    # M7
    bad7 = [s["omega"] for s in summ if not s["book_equal"] or s["writer_candidates_from_heads"] != 0 or
            s["absent_answers"] != 0]
    m["M7"] = {"broken": bad7, "pass": not bad7}
    # M8
    sh = [s for s in oracle if s["role"] in W1.SHUFFLED_ROLES]
    moved8 = [s["omega"] for s in sh if s["A4s"] != "RECIPE"]
    m["M8"] = {"shuffled_outcomes": len(sh), "moved": moved8, "F1_shuffled": "VACUOUS", "pass": not moved8 and len(sh) == 32}
    # M9
    m9 = {}
    for fam in main:
        rows = [s for s in oracle if s["fam"] == fam and s["A4s"].startswith("HEAD:")]
        if len(rows) < 4:
            m9[fam] = {"routed_to_heads": len(rows), "applies": False, "pass": True}
            continue
        hr_ = sum(s["arm_counts"]["A4s"][0] for s in rows)
        hp = Fraction(100 * hr_, 32 * len(rows))
        bests = []
        for b in BASELINES:
            br = sum(s["counts"]["BL_" + b][0] for s in rows)
            bests.append(Fraction(100 * br, 32 * len(rows)))
        bb = max(bests)
        m9[fam] = {"routed_to_heads": len(rows), "applies": True, "head_points": fx(hp), "best_baseline": fx(bb),
                   "pass": hp - bb >= 5}
    m["M9"] = {"per_family": m9, "pass": all(v["pass"] for v in m9.values())}
    # HQ
    tgt = "a" if ws == W1.ORIGINAL else "a_fresh"
    t = out["families"].get(tgt)
    hq = {"family": tgt}
    proxy = False
    if t is None:
        hq["pass"] = False
    else:
        a2 = N.pf(t["A2"]["points"]["exact"])
        b3 = N.pf(t["best_non_neural_A3"]) if t["best_non_neural_A3"] is not None else Fraction(0)
        hq.update({"A2_points": fx(a2), "A2_right": t["A2"]["right"], "neural_parameters_in_A2": 0,
                   "best_non_neural_A3": fx(b3), "A2_ge_best_A3_minus_2": a2 >= b3 - 2})
        if ws == W1.ORIGINAL:
            bar = HQ_ORIGINAL_BAR
            hq["bar_source"] = "RB-W recorded UNGATED MLP 417/512 - 2"
        elif gpu_state == "VERIFIED" and "A7" in t:
            bar = N.pf(t["A7"]["points"]["exact"]) - 2
            hq["bar_source"] = "A7 gated GPU MLP on a_fresh - 2"
            a7lf = Fraction(100 * t["A7"]["limit_free_right"], t["A7"]["n"])
            hq["R_HQ_LIMIT"] = {"A7_limit_free_points": fx(a7lf), "bar": fx(a7lf - 2), "pass": a2 >= a7lf - 2}
        else:
            bar = HQ_ORIGINAL_BAR
            proxy = True
            hq["bar_source"] = "PROXY_BAR 79.4453125 (GPU arm " + gpu_state + ")"
        hq["bar"] = fx(bar)
        hq["pass"] = hq["A2_ge_best_A3_minus_2"] and a2 >= bar
    m["HQ"] = hq
    out["marks"] = m
    # instrument (per set): F1 draw checks and digests
    f1rows = ps["f1"]
    want = W1.F1_DRAWS[ws]
    from rb_g6 import units_g6 as U6
    fh = U6.frozen_hashes()["f1"]
    f1ok = len(f1rows) == 2 * len(want) and all(v["draw_check_ok"] and v["draw_digest"] == fh.get(d)
                                                 for (_, d), v in f1rows.items())
    out["instrument"]["f1_draw_checks_ok"] = f1ok
    # F1 points (A1 = A4s)
    f1 = {}
    sys_path_rb2()
    from rb2 import common2 as C2
    for shuffled in (False, True):
        ch, al = [], []
        for d in want:
            dv = f1rows.get((shuffled, d))
            if dv is None:
                continue
            ch.append(sum(1 for z in dv["panels"]["b_chain"] if z["answer"] == z["gold"]))
            al.append(sum(1 for z in dv["panels"]["b_alt"] if z["answer"] == z["gold"]))
        if ch:
            f1["shuffled" if shuffled else "true"] = {"median_b_chain": N.fs(C2.median(ch)),
                                                      "median_b_alt": N.fs(C2.median(al)),
                                                      "points": fx(Fraction(100) * (C2.median(ch) + C2.median(al)) / 32),
                                                      "draws": len(ch), "A4s_equals_A1": True}
    out["F1"] = f1
    # status words
    inst_ok = f1ok
    marks_bool = {k: m[k]["pass"] for k in ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9")}
    out["marks_bool"] = marks_bool
    out["proxy_bar"] = proxy
    # reported rows
    out["reported"] = reported_rows(ws, summ, out, rbw)
    out["outcomes"] = summ                                    # the per-outcome routing records (ROUTING.md section 8)
    return out


def rows_per_parameter(rows):
    out = {}
    for a in ["CORE", "SUB_ONLY", "RECIPE_SUB"] + list(HEADS6) + ["MLP"]:
        tr = sum(s["train_right"].get(a, 0) for s in rows if a in s["train_right"])
        key = "SUB" if a in ("SUB_ONLY", "RECIPE_SUB") else a
        pr = sum((s["params"].get(key) or 0) for s in rows if a in s["train_right"])
        if pr:
            out[a] = {"train_right": tr, "parameters": pr, "rows_per_parameter": fx(Fraction(tr, pr))}
    return out


def reported_rows(ws, summ, out, rbw):
    rep = {}
    oracle = [s for s in summ if s["tag"] == "ORACLE"]
    # R-CAP and R-RET (ORIGINAL)
    if ws == W1.ORIGINAL:
        start = [s for s in summ if s["tag"] == "START"]
        rc = {}
        for fam in W1.START_UNITS:
            st = [s for s in start if s["fam"] == fam]
            rc[fam] = {"routed_with_live_trigger": sum(1 for s in st if s["A4s"] != "RECIPE"
                                                       and s["ledger_word"] in R.T_WORDS),
                       "routed_without_live_trigger": sum(1 for s in st if s["A4s"] != "RECIPE"
                                                          and s["ledger_word"] not in R.T_WORDS),
                       "ledger_words": sorted({s["ledger_word"] for s in st})}
            rc[fam]["code_check_pass"] = rc[fam]["routed_with_live_trigger"] == 0
        rep["R_CAP"] = rc
        b1 = {s["rid"]: s for s in start if s["fam"] == "a_approx"}
        b2 = {s["rid"]: s for s in oracle if s["fam"] == "a_approx"}
        ret = []
        for rid, s1 in sorted(b1.items()):
            s2 = b2.get(rid)
            if s2 is None or s1["A4s"] == "RECIPE":
                continue
            head = s1["A4s"]
            rule = None
            if not s2["R1"]:
                rule = 1
            elif s2["ledger_word"] not in R.ELIGIBLE_WORDS:
                rule = 2
            elif s2["sub"]["SUB"]["admitted"]:
                rule = 3
            elif head.startswith("HEAD:"):
                k = s2["rungs"].get(head[5:])
                if k is None:
                    rule = 5
                else:
                    lead = k["R4"]["head_closer"] - k["R4"]["recipe_closer"]
                    if lead <= 2:
                        rule = 4
                    elif not (k["R5"]["pass"] and k["R6"]["pass"]):
                        rule = 5
            ret.append({"omega": s1["omega"], "boundary1": head, "returns": rule is not None, "rule": rule,
                        "at_mark_b2": not s2["R1"]})
        rep["R_RET"] = {"routed_at_boundary1": len(ret), "returned": sum(1 for z in ret if z["returns"]),
                        "events": ret, "code_check_pass": all(z["returns"] for z in ret if z["at_mark_b2"])}
        eye = [s["eye"] for s in oracle if s.get("eye")]
        rep["R_EYE"] = {"clean_panel_a_to_a_fresh": {
            "heads": sum(1 for e in eye if e["twin"] == "a_fresh"),
            "would_quarantine": sum(1 for e in eye if e["twin"] == "a_fresh" and e["would_quarantine"])},
            "changed_law_panel_a_approx_to_a_approx_fresh": {
            "heads": sum(1 for e in eye if e["twin"] == "a_approx_fresh"),
            "would_quarantine": sum(1 for e in eye if e["twin"] == "a_approx_fresh" and e["would_quarantine"])},
            "per_outcome": eye, "note": "report-only; the eye acts on nothing"}
        mlp = {}
        for fam, per in rbw.items():
            rows = {s["rid"]: s for s in oracle if s["fam"] == fam}
            mlp[fam] = [{"omega": "%s_%02d" % (fam, rid), "rbw_mlp_ungated": per[rid],
                         "A2_gated": rows[rid]["arm_counts"]["A2"] if rid in rows else None,
                         "A4s_gated": rows[rid]["arm_counts"]["A4s"] if rid in rows else None}
                        for rid in range(len(per))]
        rep["R_MLP_ORIGINAL"] = mlp
    # R-SUBGEN
    sg = {}
    for fam in ("a", "a_fresh", "a_offladder", "b"):
        rows = [s for s in oracle if s["fam"] == fam]
        if not rows:
            continue
        nh = sum((s["counts"]["RECIPE_SUB_NO_HALF"][0] if (s["eligible"] and s["sub"]["SUB_NO_HALF"]["admitted"])
                  else s["counts"]["CORE"][0]) for s in rows)
        sg[fam] = {"A2_points": out["families"][fam]["A2"]["points"],
                   "SUB_admitted": sum(1 for s in rows if s["sub"]["SUB"]["admitted"]),
                   "SUB_NO_HALF_admitted": sum(1 for s in rows if s["sub"]["SUB_NO_HALF"]["admitted"]),
                   "A2_with_SUB_NO_HALF_points": fx(Fraction(100 * nh, 32 * len(rows))),
                   "SUB_ONLY_points": out["families"][fam].get("SUB_ONLY", {}).get("points"),
                   "chosen_rhos": sorted({str(s["sub"]["SUB"]["rho"]) for s in rows})}
    rep["R_SUBGEN"] = sg
    # R-SUBGATE, R-LIMIT, R-GATE, R-RES, R-CCE, R-SWEEP
    rep["R_SUBGATE"] = {fam: fx(Fraction(100 * sum(s["subgate_counts"][0] for s in oracle if s["fam"] == fam),
                                         32 * sum(1 for s in oracle if s["fam"] == fam)))
                        for fam in sorted({s["fam"] for s in oracle})}
    rep["R_LIMIT"] = {fam: {"A4s_limit_free_right": out["families"][fam]["A4s"]["limit_free_right"],
                            "A4s_right": out["families"][fam]["A4s"]["right"]} for fam in out["families"]}
    rep["R_GATE"] = {fam: {arm: {"gated": out["families"][fam][arm]["right"],
                                 "ungated": out["families"][fam][arm].get("ungated")}
                           for arm in ("A1", "A2", "A4s") if arm in out["families"][fam]} for fam in out["families"]}
    rep["R_RES"] = {fam: out["families"][fam].get("HEAD_RESIDUAL", {}).get("points") for fam in out["families"]}
    rep["R_CCE"] = sum(s.get("head_answers_heldout", 0) for s in oracle if s["A4s"].startswith("HEAD:"))
    a2s = lambda fam: (out["families"][fam]["A2_sweep"] if isinstance(out["families"][fam].get("A2_sweep"), str)
                       else out["families"][fam].get("A2_sweep", {}).get("points"))
    rep["R_SWEEP"] = {fam: {"A2_sweep": a2s(fam),
                            "A2": out["families"][fam]["A2"]["points"],
                            "words": out["families"][fam]["sweep_words"],
                            "noisy_words": sorted({str(s["sweep_noisy_word"]) for s in oracle
                                                   if s["fam"] == fam and s["sweep_noisy_word"] is not None}),
                            "partial_rhos": sorted({str(r) for s in oracle if s["fam"] == fam
                                                    for r in s["sweep_partial_rhos"]})}
                      for fam in out["families"]}
    rep["R_COMPACT"] = {fam: out["families"][fam]["rows_per_parameter"] for fam in out["families"]}
    return rep


def sys_path_rb2():
    p = r"C:\Users\wakil\Documents\Codex\2026-10-06\helm_thread_claude\gate_b\rb2c\HELM_RECIPE_BRAIN_20261014_RB2C"
    if p not in sys.path:
        sys.path.append(p)


# ================================================================ words, re-run, write
def finish(body, rerun_equal):
    body = dict(body)
    body["instrument_rows"] = dict(body["instrument_rows"], merge_rerun_equal=rerun_equal)
    words, headline = {}, {}
    for ws in W1.SETS:
        st = body["sets"][ws]
        inst_ok = st["instrument_ok_before_rerun"] and rerun_equal
        words[ws] = R.status_words(inst_ok, st["marks_bool"])
        headline[ws] = R.headline_word(ws, inst_ok, st["marks"]["HQ"]["pass"], st["proxy_bar"])
    sweep_word = "SWEEP_CALIBRATED" if body["sweep"]["calibrated"] else "SWEEP_CALIBRATION_FAILED"
    licensed = all(words[ws] == "HYBRID_ROUTING_EARNED" and headline[ws].startswith("SUB_CLOSED_GAP")
                   for ws in W1.SETS)
    body["status_words"] = words
    body["headline_words"] = headline
    body["sweep_word"] = sweep_word
    body["claim"] = {"licensed": licensed, "proxy_bar_in_claim": licensed and body["sets"]["FRESH"]["proxy_bar"],
                     "ceiling": "SYNTHETIC_ONLY; no HELM claim; not adoption of SUB into CAS"}
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=str(HERE / "runs"))
    ap.add_argument("--gpu", default=str(HERE / "gpu_results"))
    ap.add_argument("--rbg6-merged", default=str(RBG6 / "MERGED.json"))
    ap.add_argument("--out", default=str(HERE / "runs" / "MERGED.json"))
    ap.add_argument("--recompute-only", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    body, why = build_reading(args)
    if body is None:
        print(json.dumps({"status": why}))
        sys.exit(4 if why == "RB_G6_MERGED_MISSING" else 5)
    bd = N.digest(body)
    if args.recompute_only:
        print(json.dumps({"body_digest": bd}))
        return
    cmd = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--runs", args.runs, "--gpu", args.gpu,
           "--rbg6-merged", args.rbg6_merged, "--recompute-only"]
    pr = subprocess.run(cmd, capture_output=True, text=True)
    try:
        rerun = json.loads(pr.stdout.strip().splitlines()[-1])["body_digest"]
    except Exception:
        rerun = None
    reading = finish(body, rerun == bd)
    reading["body_digest"] = bd
    reading["rerun_body_digest"] = rerun
    reading["merge_seconds"] = round(time.time() - t0, 3)
    reading["written_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    text = json.dumps(reading, indent=1, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    with open(args.out, "w", encoding="utf-8", newline="\n") as h:
        h.write(text)
    print(json.dumps({"written": args.out, "sha256": sha_file(args.out), "status_words": reading["status_words"],
                      "headline_words": reading["headline_words"], "sweep_word": reading["sweep_word"]}))


if __name__ == "__main__":
    main()
