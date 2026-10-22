"""EYE-ACT-1 reader (PREREGISTRATION_EYE_ACT_V1.precode.md sections 4-6). Reads RUN_RESULTS.json and computes every
hard gate, mark and status word from counts only. Writes READING.json; its sha256 is taken from the bytes on disk.
Standard library only. The operator does not choose the word."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

ARMS = ("A0", "A1", "A2", "A3", "R1", "R2", "C1")
EYE = ("A1", "A2", "A3")
FAULTED = ("F1_TAMPER_COEFF", "F2_TAMPER_STOCK", "F3_SLIPPED_LESSON", "F4_LOST_SOURCE")
RANK = {"WRONG": 0, "ASK": 1, "RIGHT": 2}


def read(run: dict) -> dict:
    worlds = run["worlds"]
    gates, notes = {}, []
    # ---------------------------------------------------------------- H1 tests, H2 OFF pin
    gates["H1_G_TESTS"] = bool(run["tests"]["ok"])
    gates["H2_G_OFF_PIN"] = bool(run["tests"]["off_pin_ok"])
    # ---------------------------------------------------------------- H3 instrument
    planned = {(w["seed"], w["kind"]) for w in run["plan"]}
    seen = {}
    for r in worlds:
        seen.setdefault((r["seed"], r["kind"]), set()).add(r["arm"])
    counted_once = all(len([r for r in worlds if (r["seed"], r["kind"]) == k and r["arm"] == a]) == 1
                       for k in planned for a in ARMS)
    every_arm = all(seen.get(k) == set(ARMS) for k in planned) and set(seen) == planned
    twins_ok = all(all(v["outcome"] == "RIGHT" for v in t["items"].values()) for t in run["twins"])
    p1_ok = all(r["items"]["P1"]["outcome"] == "RIGHT" for r in worlds)
    void = {}
    for k in FAULTED:
        a0 = [r for r in worlds if r["kind"] == k and r["arm"] == "A0"]
        void[k] = [r["seed"] for r in a0 if r["items"]["P2"]["outcome"] == "RIGHT"]
    void_ok = all(len(void[k]) * 10 <= max(1, len([r for r in worlds if r["kind"] == k and r["arm"] == "A0"]))
                  for k in FAULTED)
    gates["H3_G_INSTRUMENT"] = bool(counted_once and every_arm and twins_ok and p1_ok and void_ok
                                    and run["generator_check"])
    void_seeds = {s for k in FAULTED for s in void[k]}
    # ---------------------------------------------------------------- H4 replay
    gates["H4_G_REPLAY"] = all(x["equal"] for x in run["replay"]) and len(run["replay"]) == 8
    # ---------------------------------------------------------------- H5 clean
    clean_diff = []
    for r in worlds:
        if r["kind"] == "CLEAN" and r["arm"] in EYE:
            a0 = next(x for x in worlds if x["seed"] == r["seed"] and x["kind"] == "CLEAN" and x["arm"] == "A0")
            for p in ("P1", "P2", "P3"):
                if (r["items"][p]["value"], r["items"][p]["limiting"], r["items"][p]["outcome"]) != \
                        (a0["items"][p]["value"], a0["items"][p]["limiting"], a0["items"][p]["outcome"]):
                    clean_diff.append([r["arm"], r["seed"][:12], p])
    gates["H5_G_CLEAN"] = not clean_diff
    # ---------------------------------------------------------------- H6 / H7 / H8 eye ledgers
    eyes = [r for r in worlds if r["arm"] in EYE]
    gates["H6_G_NO_NEW_KNOWLEDGE"] = all(r["eye"]["restores_verified"] for r in eyes)
    gates["H7_G_READS_PURE"] = all(r["eye"]["sweeps_pure"] for r in eyes)
    gates["H8_G_LEDGERED"] = all(r["eye"]["restores"] == r["eye"]["restores_in_trace"] for r in eyes)
    # ---------------------------------------------------------------- marks
    def faulted(arm):
        return [r for r in worlds if r["arm"] == arm and r["kind"] in FAULTED and r["seed"] not in void_seeds]

    marks = {"by_arm": {}, "by_arm_kind": {}, "interventions": {}, "interventions_clean": {}, "holds": {},
             "bytes_held_max": {}, "fix": {}}
    for a in ARMS:
        c = {"RIGHT": 0, "ASK": 0, "WRONG": 0}
        for r in faulted(a):
            for p in ("P2", "P3"):
                c[r["items"][p]["outcome"]] += 1
        marks["by_arm"][a] = c
        marks["by_arm_kind"][a] = {}
        for k in FAULTED:
            ck = {"RIGHT": 0, "ASK": 0, "WRONG": 0}
            for r in faulted(a):
                if r["kind"] == k:
                    for p in ("P2", "P3"):
                        ck[r["items"][p]["outcome"]] += 1
            marks["by_arm_kind"][a][k] = ck
        mine = [r for r in worlds if r["arm"] == a]
        marks["interventions"][a] = sum(r["interventions"] for r in mine)
        marks["interventions_clean"][a] = sum(r["interventions"] for r in mine if r["kind"] == "CLEAN")
        marks["holds"][a] = sum(r["holds"] for r in mine)
        marks["bytes_held_max"][a] = max([r["bytes_held"] for r in mine] or [0])
        marks["fix"][a] = len([r for r in faulted(a) if r["items"]["P3"]["outcome"] == "RIGHT"])
    # ---------------------------------------------------------------- H9 control, H10 no invent
    E = V = Fraction(0)
    for r in faulted("C1"):
        if r["kind"] == "F4_LOST_SOURCE":
            continue                                   # nothing can restore F4: p = 0
        n = r["c1"]["picks_after_plant"]
        p = 1 - Fraction(1, 2) ** n
        E += p
        V += p * (1 - p)
    bound = float(E) + 3 * math.sqrt(float(V))
    marks["c1_chance"] = {"E": "%.4f" % float(E), "bound": "%.4f" % bound, "fix": marks["fix"]["C1"]}
    gates["H9_G_CONTROLS"] = marks["fix"]["C1"] <= bound
    # H10 as amended (AMENDMENT_EA1_A2.md): a WRONG equal to A0's same answer is "not yet noticed", not invented
    inventions = []
    for r in worlds:
        if r["kind"] != "F4_LOST_SOURCE" or r["arm"] not in EYE:
            continue
        a0 = next(x for x in worlds if x["seed"] == r["seed"] and x["kind"] == r["kind"] and x["arm"] == "A0")
        for p in ("P2", "P3"):
            it, ref = r["items"][p], a0["items"][p]
            if it["outcome"] == "WRONG" and (it["value"], it["limiting"]) != (ref["value"], ref["limiting"]):
                inventions.append([r["arm"], r["seed"][:12], p])
    marks["f4_inventions"] = inventions
    gates["H10_G_NO_INVENT"] = not inventions
    # ---------------------------------------------------------------- words
    words, why = [], {}
    if not all(gates.values()):
        words = ["INCONCLUSIVE"]
        why["failed_gates"] = [g for g, v in gates.items() if not v]
    else:
        harm = []
        for r in worlds:
            if r["arm"] not in EYE or r["kind"] not in FAULTED or r["seed"] in void_seeds:
                continue
            a0 = next(x for x in worlds if x["seed"] == r["seed"] and x["kind"] == r["kind"] and x["arm"] == "A0")
            a1 = next(x for x in worlds if x["seed"] == r["seed"] and x["kind"] == r["kind"] and x["arm"] == "A1")
            for p in ("P2", "P3"):
                if r["items"][p]["outcome"] == "WRONG" and a0["items"][p]["outcome"] in ("RIGHT", "ASK"):
                    harm.append([r["arm"], r["seed"][:12], p, "worse_than_A0"])
                if r["arm"] in ("A2", "A3") and RANK[r["items"][p]["outcome"]] < RANK[a1["items"][p]["outcome"]]:
                    harm.append([r["arm"], r["seed"][:12], p, "worse_than_A1"])
        why["harm_items"] = harm[:20]
        why["harm_count"] = len(harm)
        if harm:
            words.append("EYE_ACT_HARMFUL")
        else:
            m = marks["by_arm"]
            ek = m["A2"]["RIGHT"] > m["A1"]["RIGHT"] and m["A2"]["WRONG"] <= m["A1"]["WRONG"]
            ck = (m["A3"]["WRONG"] <= m["A2"]["WRONG"] and m["A3"]["RIGHT"] > m["A2"]["RIGHT"]) or \
                 (m["A3"]["WRONG"] == m["A2"]["WRONG"] and m["A3"]["RIGHT"] == m["A2"]["RIGHT"]
                  and marks["interventions"]["A3"] < marks["interventions"]["A2"])
            why["EYE_ACT_EARNED_KEEP"] = ek
            why["CONCERT_ACT_EARNED_KEEP"] = ck
            if ek:
                words.append("EYE_ACT_EARNED_KEEP")
            if ck:
                words.append("CONCERT_ACT_EARNED_KEEP")
            best = min(("A2", "A3"), key=lambda a: (m[a]["WRONG"], -m[a]["RIGHT"]))
            why["better_eye_arm"] = best
            for rv, label in (("R1", "CHECKSUM_COPY"), ("R2", "REBUILD_ALWAYS")):
                e, o = (m[best]["WRONG"], -m[best]["RIGHT"]), (m[rv]["WRONG"], -m[rv]["RIGHT"])
                words.append("EYE_ACT_BEATS_" + label if e < o else (label + "_BEATS_EYE_ACT" if o < e else "TIES_" + label))
            if not (ek or ck):
                words.append("NO_EYE_ACT_WORD")
    return {"reader": "read_ea1.py", "hard_gates": gates, "status_words": words, "why": why, "marks": marks,
            "void": void, "clean_differences": clean_diff[:20], "worlds": len(worlds),
            "planned_worlds": len(planned), "notes": notes}


if __name__ == "__main__":
    run_path = Path(sys.argv[1])
    out = Path(sys.argv[2])
    res = read(json.loads(run_path.read_text("utf-8")))
    out.write_bytes(json.dumps(res, indent=1, sort_keys=True).encode("utf-8"))
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    print(json.dumps({"words": res["status_words"], "gates_failed": [g for g, v in res["hard_gates"].items() if not v],
                      "by_arm": res["marks"]["by_arm"], "sha256": sha}, indent=1))
