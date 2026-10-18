"""LM-T1 scoring parts: recipe contents from SDG seeds, M1, M2 (+ COIN), M3 (+ LOOKUP), M4/M5/M5b, M7.

Imports sdg_bridge_v2 (grammar, english) and fair_data_experiment_v2_sdg.sdg_source read-only. No file is changed.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import statistics

import cce
import aliaswide

HERE = Path(__file__).resolve().parent
SEED_SHA256 = "df68d2447ccd7371f8b9a18e48fa90269914be2505f1a96d92e4164aabe91639"
ENGLISH_DIR = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-synthetic\data\path_d")
ENGLISH_FILES = ("wave3_step2_5_english_descriptions_20260508T203848Z.jsonl",
                 "wave3_step2_5_english_descriptions_20260509T002355Z.jsonl",
                 "wave3_step2_5_english_descriptions_20260509T002541Z.jsonl")
SUSPECT_SIX = ("seed_recipe_00229", "seed_recipe_00193", "seed_recipe_00360", "seed_recipe_00353",
               "seed_recipe_00320", "seed_recipe_00528")
SEEDS = (11, 29, 47)


def _state_from_cell(cell, drive, register):
    m = re.fullmatch(r"\^([0-9])\^([PCEO])", cell)
    return {"noetic": int(m.group(1)), "domain": m.group(2), "register": [register] if register else None,
            "drive": drive}


def content_from_parse(p):
    """bridge v2 parse_recipe output -> CCE content (recipe)."""
    terms = []
    for t in p["core"]:
        if t["kind"] == "state":
            s = _state_from_cell(t["cell"], t["drive"], t["register"])
            s.update({"kind": "state", "coefficient": t["coefficient"]})
            terms.append(s)
        elif t["kind"] == "outcome":
            terms.append({"kind": "outcome", "coefficient": t["coefficient"], "name": t["cell"]})
        else:
            terms.append({"kind": "emergent", "coefficient": t["coefficient"], "result": t["cell"],
                          "components": [_state_from_cell(x["cell"], x["drive"], x["register"])
                                         for x in t["components"]]})
    c = cce.empty_content()
    c["recipe"] = {"omega": "Ω_" + p["omega"], "terms": terms,
                   "leakage": [{"coefficient": k["coefficient"], "side": "Ω_" + k["side"],
                                "implicit": k["implicit_coefficient"]} for k in p["leakage"]],
                   "catalysts": [], "inhibitors": []}
    return c


def load_recipes():
    from fair_data_experiment_v2_sdg import sdg_source
    from sdg_bridge_v2.grammar import parse_recipe
    out = []
    for line, record in sdg_source.load_recipe_seeds(SEED_SHA256):
        p = parse_recipe(record["expression"])
        out.append({"seed_id": record["seed_id"], "expression": record["expression"], "parsed": p,
                    "content": content_from_parse(p) if p["accepted"] else None})
    return out


# --- M1 / M2 ---------------------------------------------------------------------------------------------------
def m1(recipes):
    rows, ok = [], 0
    for r in recipes:
        rec = cce.round_trip(r["content"]) if r["content"] is not None else {"ok": False, "rejection": "BRIDGE_REJECTED"}
        ok += rec["ok"]
        rows.append({"seed_id": r["seed_id"], "ok": rec["ok"], "receipt_id": rec.get("receipt_id"),
                     "rejection": rec.get("rejection")})
    return {"recipes": len(recipes), "round_trip_ok": ok, "pass": ok == len(recipes) == 576, "rows": rows}


def coin_sentence(rng, content):
    words = cce.lexicon_words()
    names = re.findall(r'"[^"]+"|Ω_[A-Za-z0-9_]+', json.dumps(cce.canonical(content), ensure_ascii=False)
                       .replace('\\"', '"'))
    pool = words + names + [str(rng.randint(1, 9))]
    n = rng.randint(6, 14)
    return " ".join(rng.choice(pool) for _ in range(n)) + "."


def m2(recipes):
    said_failing = sayable = 0
    distinct, coin_equal, coin_total, draws = [], 0, 0, 0
    for r in recipes:
        c = r["content"]
        sentences = set()
        any_ok = False
        for seed in SEEDS:
            rng = random.Random(seed * 1000003 + hash_int(r["seed_id"]))
            for _ in range(8):
                draws += 1
                rec = cce.round_trip(c, rng, seed)
                if rec["ok"]:
                    sentences.add(rec["sentence"])
                    any_ok = True
                # a failing draw is refused, never said (counted only if it were said: it is not)
            crng = random.Random(seed * 7919 + hash_int(r["seed_id"]))
            for _ in range(8):
                coin_total += 1
                try:
                    back = cce.parse(coin_sentence(crng, c))
                    coin_equal += cce.normalize(back) == cce.normalize(c)
                except cce.Refusal:
                    pass
        fixed = cce.round_trip(c)
        if any_ok or fixed["ok"]:
            sayable += 1
        if not fixed["ok"]:
            sentences.discard(None)
        distinct.append(len(sentences | ({fixed["sentence"]} if fixed["ok"] else set())))
        for seed in SEEDS:
            s = cce.say(c, seed)
            if s["sentence"] is not None and s.get("receipt", {}).get("ok") is False:
                said_failing += 1
    return {"contents": len(recipes), "draws_tried": draws, "said_failing_readback": said_failing,
            "sayable_contents": sayable, "coin_tried": coin_total, "coin_readback_equal": coin_equal,
            "distinct_admitted_wordings": {"min": min(distinct), "median": statistics.median(distinct),
                                           "max": max(distinct)},
            "pass": said_failing == 0 and sayable == len(recipes) == 576 and coin_equal == 0}


def hash_int(text):
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


# --- LOOKUP baseline ------------------------------------------------------------------------------------------
class Lookup:
    """Content -> its fixed CANON sentence; that exact sentence -> content. Nothing else."""

    def __init__(self, contents):
        self.table = {}
        for c in contents:
            try:
                self.table[cce.render(c)] = cce.normalize(c)
            except Exception:
                pass

    def parse(self, text):
        if text in self.table:
            return self.table[text]
        raise cce.Refusal("NOT_IN_TABLE", text[:40])


# --- M3 hand set ------------------------------------------------------------------------------------------------
def m3(items, lookup):
    rows = []
    for it in items:
        exp = it["expect"]
        row = {"id": it["id"], "kind": it["kind"], "wording": it.get("wording"),
               "nondefault_order": it.get("nondefault_order"), "fundamentals": it.get("fundamentals")}
        try:
            got = cce.parse(it["text"])
            row["cce_parse"] = "PARSED"
            row["cce_refusal"] = None
        except cce.Refusal as exc:
            got, row["cce_parse"], row["cce_refusal"] = None, "REFUSED", exc.code
            row["cce_refusal_detail"] = exc.detail[:160]
        if "refusal" in exp:
            row["expected"] = exp["refusal"]
            row["cce_ok"] = got is None and row["cce_refusal"] == exp["refusal"]
        else:
            try:
                gold = cce.normalize(exp["content"])
                row["gold_valid"] = True
            except Exception as exc:      # a malformed gold record is reported, never repaired
                gold, row["gold_valid"] = None, False
                row["gold_error"] = "%s: %s" % (type(exc).__name__, exc)
            same = got is not None and gold is not None and cce.normalize(got) == gold
            rt = cce.round_trip(got) if got is not None else {"ok": False}
            row["cce_content_equal"] = same
            row["cce_round_trip"] = rt["ok"]
            row["cce_ok"] = bool(same and rt["ok"])
            if got is not None and not same:
                row["cce_got"] = cce.canonical(got)
        try:
            lk = lookup.parse(it["text"])
            row["lookup_ok"] = ("content" in exp and gold is not None and lk == gold)
        except cce.Refusal as exc:
            row["lookup_ok"] = ("refusal" in exp and exp["refusal"] == exc.code)
        rows.append(row)
    ok = sum(r["cce_ok"] for r in rows)
    by_kind = Counter((r["kind"], r["cce_ok"]) for r in rows)
    return {"items": len(rows), "cce_ok": ok, "lookup_ok": sum(r["lookup_ok"] for r in rows),
            "by_kind": {"%s_%s" % (k, "ok" if v else "fail"): n for (k, v), n in sorted(by_kind.items())},
            "alias_positive_ok": sum(1 for r in rows if r["kind"] == "POSITIVE" and r["wording"] != "CANON" and r["cce_ok"]),
            "alias_positive_total": sum(1 for r in rows if r["kind"] == "POSITIVE" and r["wording"] != "CANON"),
            "lookup_alias_positive_ok": sum(1 for r in rows if r["kind"] == "POSITIVE" and r["wording"] != "CANON" and r["lookup_ok"]),
            "pass": ok == len(rows) == 64, "rows": rows}


# --- M4 / M5 / M5b ------------------------------------------------------------------------------------------------
def load_english(excluded):
    from sdg_bridge_v2.grammar import parse_recipe
    rows, total = [], 0
    for name in ENGLISH_FILES:
        with (ENGLISH_DIR / name).open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                total += 1
                row = json.loads(line)
                p = parse_recipe(row["source_cas"])
                if not p["accepted"]:
                    continue
                rows.append({"file": name, "line": line_no, "seed_id": row.get("seed_id"), "parsed": p,
                             "english": row["english_description"], "excluded": row.get("seed_id") in excluded,
                             "category": row.get("grammar_category")})
    return rows, total


def m4(rows, lookup):
    from sdg_bridge_v2.english import check_binding
    head = [r for r in rows if not r["excluded"]]
    verdicts, bridge_v, second, strict_ok, lookup_ok, reasons = Counter(), Counter(), 0, 0, 0, Counter()
    per_row = []
    for r in head:
        v = aliaswide.check(r["parsed"], r["english"])
        b = check_binding(r["parsed"], r["english"])["verdict"]
        verdicts[v["verdict"]] += 1
        bridge_v[b] += 1
        if v["verdict"] == "MATCH" and v["second_number_agrees"]:
            second += 1
        for code in v["reasons"]:
            reasons[code] += 1
        content = content_from_parse(r["parsed"])
        try:
            strict_ok += cce.normalize(cce.parse(r["english"])) == cce.normalize(content)
        except cce.Refusal:
            pass
        try:
            lookup_ok += lookup.parse(r["english"]) == cce.normalize(content)
        except cce.Refusal:
            pass
        per_row.append({"seed_id": r["seed_id"], "line": r["line"], "verdict": v["verdict"], "bridge_v2": b,
                        "second_number_agrees": v["second_number_agrees"], "reasons": v["reasons"]})
    match = verdicts["MATCH"]
    return {"headline_rows": len(head), "alias_wide": dict(verdicts), "alias_wide_match": match,
            "bridge_v2_on_same_rows": dict(bridge_v), "mark": 176, "mark_met": match >= 176,
            "second_number_register_and_drive_agree_among_match": second,
            "strict_cce_parses_equal": strict_ok, "lookup_equal": lookup_ok,
            "unparseable_reason_counts": dict(reasons), "rows": per_row}


def m5(rows):
    out = {}
    for r in rows:
        if r["seed_id"] == "seed_recipe_00459" or r["seed_id"] in SUSPECT_SIX or r["seed_id"] == "seed_recipe_00026":
            v = aliaswide.check(r["parsed"], r["english"])
            entry = {"verdict": v["verdict"], "offending_pair": v.get("offending_pair"), "reasons": v["reasons"]}
            if r["seed_id"] in SUSPECT_SIX:
                entry["flag"] = "FLAG_FOR_HUMAN_REVIEW" if v["verdict"] == "MATCH" else None
            out[r["seed_id"]] = entry
    return {"rows": out, "positive_control_00459_mismatch": out.get("seed_recipe_00459", {}).get("verdict") == "MISMATCH",
            "suspect_six_match_flags": sum(1 for k in SUSPECT_SIX if out.get(k, {}).get("flag"))}


def m5b(rows):
    from sdg_bridge_v2.english import cas_tuples
    head = sorted((r for r in rows if not r["excluded"]), key=lambda r: r["seed_id"])
    keys = [tuple(sorted(map(repr, cas_tuples(r["parsed"])))) for r in head]
    n = len(head)
    rng = random.Random(11)
    perm = list(range(n))
    for i in range(n - 1, 0, -1):          # Sattolo: one cycle, so no fixed point
        j = rng.randrange(i)
        perm[i], perm[j] = perm[j], perm[i]

    def bad(i):
        return perm[i] == i or keys[perm[i]] == keys[i]
    for i in range(n):                     # repair same-content pairs one at a time, deterministically
        if not bad(i):
            continue
        for step in range(1, n):
            j = (i + step) % n
            perm[i], perm[j] = perm[j], perm[i]
            if not bad(i) and not bad(j):
                break
            perm[i], perm[j] = perm[j], perm[i]
    valid = all(not bad(i) for i in range(n))
    match = 0
    for i, r in enumerate(head):
        match += aliaswide.check(r["parsed"], head[perm[i]]["english"])["verdict"] == "MATCH"
    return {"pairs": n, "derangement_valid": valid, "shuffled_match": match, "pass": valid and match == 0}


# --- M7 compiler cross-check ---------------------------------------------------------------------------------------
DOMAIN_INDEX = {"P": 0, "C": 1, "E": 2, "O": 3}


def _coef_key(x):
    if isinstance(x, float):
        return cce.num(repr(x))
    return cce.num(x)


def m7(recipes, round_tripped, frame_terms):
    from fair_data_experiment_v2_sdg import sdg_source
    try:
        comp = sdg_source.load_compiler()
    except Exception as exc:
        return {"status": "NOT_USED", "reason": "%s: %s" % (type(exc).__name__, exc), "pass": False}
    agree = 0
    rows = []
    for r, back in zip(recipes, round_tripped):
        art = comp.compile_expression(r["expression"])
        if not (art.valid and art.result is not None) or back is None:
            rows.append({"seed_id": r["seed_id"], "agree": False})
            continue
        theirs = sorted((_coef_key(q["coefficient"]), q["primitive"]["operator"], q["primitive"]["domain"],
                         q["primitive"].get("drive"), q["primitive"].get("register")) for q in art.result.prerequisites)
        theirs_leak = sorted((_coef_key(k["coefficient"]), k["target"]) for k in art.result.leakages)
        rec = cce.canonical(back)["recipe"]
        ours = sorted((_coef_key(t["coefficient"]), "CO-%d" % t["noetic"], t["domain"], t["drive"],
                       t["register"][0] if t["register"] else None) for t in rec["terms"] if t["kind"] == "state")
        ours_leak = sorted((_coef_key(k["coefficient"]), k["side"][2:]) for k in rec["leakage"])
        ok = theirs == ours and theirs_leak == ours_leak
        agree += ok
        rows.append({"seed_id": r["seed_id"], "agree": ok})
    t_ok = t_total = t_skipped = 0
    for t in frame_terms:
        reg = t.get("register")
        if reg is not None and len(reg) > 1:
            t_skipped += 1
            continue
        expr = "^%d" % t["noetic"] + ("^%s" % t["domain"] if t["domain"] else "")
        if t.get("drive"):
            expr += "_{%s}" % t["drive"]
        if reg:
            expr += "|" + reg[0]
        art = comp.compile_expression(expr)
        t_total += 1
        if not (art.valid and art.result is not None):
            continue
        v = art.result
        states = set(v.states.keys())
        if t["domain"]:
            want_states = {DOMAIN_INDEX[t["domain"]] * 10 + t["noetic"]}
            st_ok = states == want_states
        else:
            st_ok = bool(states) and all(k % 10 == t["noetic"] for k in states)
        dr_ok = (set(v.drive_weights.keys()) == {int(t["drive"][1:])}) if t.get("drive") else not v.explicit_drive
        rg_ok = v.register == (reg[0] if reg else None)
        t_ok += st_ok and dr_ok and rg_ok
    return {"status": "RUN", "recipes": len(recipes), "recipe_agree": agree, "frame_terms_checked": t_total,
            "frame_terms_agree": t_ok, "frame_terms_register_set_unit_test_only": t_skipped,
            "pass": agree == len(recipes) == 576 and t_ok == t_total, "rows_disagree": [x for x in rows if not x["agree"]]}


def walk_terms(content):
    """All frame terms (including nested and sequence) of a content, for M7."""
    c = cce.canonical(content)
    out = []

    def walk(t):
        out.append(t)
        for k in ("I", "J"):
            v = t["slots"].get(k)
            if isinstance(v, dict):
                walk(v["that"])
    for t in c["terms"] + c["sequence"]:
        walk(t)
    return out
