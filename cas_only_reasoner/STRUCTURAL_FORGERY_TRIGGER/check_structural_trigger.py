"""Evaluate the STRUCTURAL FORGERY DEFENCE trigger.

Registered 2026-09-02 on owner instruction. Spec: STRUCTURAL_FORGERY_DEFENCE_TRIGGER.md

    python check_structural_trigger.py                          # state from declared flags only
    python check_structural_trigger.py --corpus <path.json>     # also compute T1, T2, T3
    python check_structural_trigger.py --flags <path.json>      # override the declared flags

Exit codes, so this can gate a pipeline rather than only inform a human:
    0  DORMANT or WATCH
    3  WATCH_UNRESOLVED   -- memory feeds training and a condition could not be evaluated
    4  NECESSARY
    5  URGENT

DESIGN RULE: UNKNOWN IS NOT "NO". Every condition this script cannot evaluate is reported
UNKNOWN, and an UNKNOWN on T1 or T2 while T5 holds escalates rather than passes. This program
has repeatedly been damaged by checks that were silent when they should have been loud.

Pure CPU, stdlib only. Reads files, computes, prints. Spends nothing, launches nothing.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FLAGS_DEFAULT = os.path.join(HERE, "declared_flags.json")

# Thresholds, frozen with the trigger. Changing one is a governance act: record it here and in
# the spec sheet, with the measurement that motivated the change.
T1_BAND_LO, T1_BAND_HI = 0.80, 0.99      # the contradiction band, from RGM-0.2
T1_MAX_LEGIT_FRACTION = 0.005            # >0.5% of legitimate pairs in band -> collision
T2_MIN_DEGREE_AUC = 0.65                 # below this, the cheap structural signal is gone
T3_MAX_MEMORIES = 10_000
T3_MAX_WRITES_PER_DAY = 500

UNKNOWN = "UNKNOWN"


def _levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def traj_sim(s1, s2):
    if not s1 and not s2:
        return 1.0
    return 1.0 - _levenshtein(s1, s2) / max(len(s1), len(s2))


def auc(pos, neg):
    """Mann-Whitney AUC of `pos` scoring above `neg`, ties counted as half."""
    if not pos or not neg:
        return None
    wins = ties = 0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1
            elif p == n:
                ties += 1
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


def load_corpus(path):
    """Expected shape -- documented so a future corpus can be made to fit it:

        {"memories": [{"id": str,
                       "trajectory": [int, ...],
                       "links": [id, ...],
                       "is_forgery": bool,        # optional; needed for T2
                       "legitimate_group": any},  # optional; pairs within a group are
                                                  # legitimate near-duplicates, needed for T1
                      ...],
         "writes_per_day": number}                # optional; needed for T3
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_T1(c):
    """BAND COLLISION: legitimate pairs landing inside the contradiction band."""
    if not c:
        return UNKNOWN, "no corpus supplied"
    mems = c.get("memories", [])
    groups = {}
    for m in mems:
        if m.get("is_forgery"):
            continue
        g = m.get("legitimate_group")
        if g is not None:
            groups.setdefault(g, []).append(m)
    pairs = [(a, b) for g in groups.values() for i, a in enumerate(g) for b in g[i + 1:]]
    if not pairs:
        return UNKNOWN, ("no legitimate_group labels in corpus -- T1 CANNOT be evaluated, and "
                         "that is not the same as passing")
    inband = sum(1 for a, b in pairs
                 if T1_BAND_LO <= traj_sim(a["trajectory"], b["trajectory"]) < T1_BAND_HI)
    frac = inband / len(pairs)
    fired = frac > T1_MAX_LEGIT_FRACTION
    return fired, (f"{inband}/{len(pairs)} legitimate pairs = {frac:.4%} inside "
                   f"[{T1_BAND_LO}, {T1_BAND_HI}); threshold {T1_MAX_LEGIT_FRACTION:.2%} "
                   f"(RGM-0.2 measured 0/3794 = 0.0000%)")


def check_T2(c):
    """STRUCTURAL SIGNAL LOST: can degree still tell a forgery from a memory?"""
    if not c:
        return UNKNOWN, "no corpus supplied"
    mems = c.get("memories", [])
    if not any("is_forgery" in m for m in mems):
        return UNKNOWN, ("no is_forgery labels -- T2 CANNOT be evaluated. Without known or "
                         "synthesised forgeries there is nothing to measure separability on")
    real = [len(m.get("links", [])) for m in mems if not m.get("is_forgery")]
    forged = [len(m.get("links", [])) for m in mems if m.get("is_forgery")]
    a = auc(real, forged)          # real scoring ABOVE forged == forgeries are low-degree
    if a is None:
        return UNKNOWN, "one of the two populations is empty"
    sep = max(a, 1.0 - a)          # separability in either direction
    fired = sep < T2_MIN_DEGREE_AUC
    return fired, (f"degree AUC {a:.4f} (separability {sep:.4f}), threshold "
                   f"{T2_MIN_DEGREE_AUC}; CMB-RP0 measured mean degree 4.89 forged vs 6.67 "
                   f"real, and a degree filter BEAT the verifier there")


def check_T3(c, flags):
    n = len(c.get("memories", [])) if c else flags.get("n_memories")
    w = (c or {}).get("writes_per_day", flags.get("writes_per_day"))
    if n is None and w is None:
        return UNKNOWN, "no corpus and no declared n_memories / writes_per_day"
    hits = []
    if n is not None and n > T3_MAX_MEMORIES:
        hits.append(f"{n} memories > {T3_MAX_MEMORIES}")
    if w is not None and w > T3_MAX_WRITES_PER_DAY:
        hits.append(f"{w} writes/day > {T3_MAX_WRITES_PER_DAY}")
    return (bool(hits), "; ".join(hits) if hits
            else f"n_memories={n}, writes_per_day={w} -- both inside review scale")


def declared(flags, key, desc):
    if key not in flags:
        return UNKNOWN, f"{desc} -- not declared"
    return bool(flags[key]), f"{desc} -- declared {flags[key]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus")
    ap.add_argument("--flags", default=FLAGS_DEFAULT)
    a = ap.parse_args()

    corpus = load_corpus(a.corpus) if a.corpus and os.path.exists(a.corpus) else None
    flags = {}
    if os.path.exists(a.flags):
        with open(a.flags, encoding="utf-8") as f:
            flags = json.load(f)

    checks = {
        "T1_BAND_COLLISION": check_T1(corpus),
        "T2_STRUCTURAL_SIGNAL_LOST": check_T2(corpus),
        "T3_SCALE_PAST_REVIEW": check_T3(corpus, flags),
        "T4_UNTRUSTED_WRITE_PATH": declared(flags, "untrusted_write_path",
                                            "memory writes not first-party and reviewed"),
        "T5_MEMORY_FEEDS_TRAINING": declared(flags, "memory_feeds_training",
                                             "memory contents enter training/replay"),
        "T6_OBSERVABLE_THRESHOLDS": declared(flags, "observable_thresholds",
                                             "a writer can observe/infer the thresholds"),
    }

    print("STRUCTURAL FORGERY DEFENCE -- TRIGGER CHECK")
    print(f"corpus: {a.corpus or '(none)'}    flags: "
          f"{a.flags if os.path.exists(a.flags) else '(none)'}")
    print()
    for k, (v, why) in checks.items():
        mark = {True: "FIRED  ", False: "clear  ", UNKNOWN: "UNKNOWN"}[v]
        print(f"  [{mark}] {k}")
        print(f"            {why}")
    print()

    T = {k: v for k, (v, _) in checks.items()}
    t5 = T["T5_MEMORY_FEEDS_TRAINING"]
    t12 = (T["T1_BAND_COLLISION"], T["T2_STRUCTURAL_SIGNAL_LOST"])
    t46 = (T["T4_UNTRUSTED_WRITE_PATH"], T["T6_OBSERVABLE_THRESHOLDS"])

    if t5 is True and any(x is True for x in t12):
        state = "URGENT" if any(x is True for x in t46) else "NECESSARY"
    elif t5 is True and any(x is UNKNOWN for x in t12):
        # UNKNOWN IS NOT "NO". Memory feeds training and a defence condition is unevaluated.
        state = "WATCH_UNRESOLVED"
    elif any(v is True for v in T.values()):
        state = "WATCH"
    else:
        state = "DORMANT"

    print(f"TRIGGER STATE: {state}")
    msg = {
        "DORMANT": "No condition met. The deferred build stays deferred.",
        "WATCH": ("At least one condition is met but the firing rule is not satisfied. "
                  "Re-check when deployment changes."),
        "WATCH_UNRESOLVED": ("Memory feeds training AND a defence condition could NOT be "
                             "evaluated. This is NOT a pass. Supply the labels the checker "
                             "needs (legitimate_group for T1, is_forgery for T2) or make an "
                             "explicit owner decision to proceed without them."),
        "NECESSARY": ("FIRING RULE MET. Memory feeds training and one of the two defences has "
                      "lost its footing. The structural-forgery defence is needed. It is NOT "
                      "authorized -- it requires its own preregistration, its own "
                      "mechanism-free baselines, and owner authorization."),
        "URGENT": ("FIRING RULE MET WITH AN ADVERSARY WRITE-PATH. As NECESSARY, and there is a "
                   "party who can write memories and observe or infer the thresholds."),
    }[state]
    print()
    for line in msg.split(". "):
        if line.strip():
            print("  " + line.strip().rstrip(".") + ".")
    return {"DORMANT": 0, "WATCH": 0, "WATCH_UNRESOLVED": 3,
            "NECESSARY": 4, "URGENT": 5}[state]


if __name__ == "__main__":
    sys.exit(main())
