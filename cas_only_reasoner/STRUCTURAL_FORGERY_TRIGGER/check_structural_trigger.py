"""Evaluate the STRUCTURAL FORGERY DEFENCE trigger.

Registered 2026-09-02. Owner ruling 2026-09-02 (Fixes A-D) applied.
Spec: STRUCTURAL_FORGERY_DEFENCE_TRIGGER.md

    python check_structural_trigger.py
    python check_structural_trigger.py --corpus <corpus.json>
    python check_structural_trigger.py --manifest <deployment_manifest.json> --job replay-train

EXIT CODES (owner ruling, Fix C). For any memory-to-training job, EVERY NONZERO CODE BLOCKS.

     0   DORMANT | CLEAR | WATCH   -- production memory does not feed training, or it does and
                                      both defence conditions are measured healthy
    10   WATCH_UNRESOLVED          -- production memory feeds training AND a defence condition
                                      could not be evaluated, OR authority could not be
                                      established. UNKNOWN IS NOT "NO". THIS BLOCKS.
    20   NECESSARY                 -- a defence condition has FIRED
    30   URGENT                    -- a defence condition has fired AND scale/adversary raises it

Pure CPU, stdlib only. Reads files, computes, prints. Spends nothing, launches nothing.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST_DEFAULT = os.path.join(HERE, "deployment_manifest.json")

# Thresholds, frozen with the trigger. Changing one is a governance act: record it here and in
# the spec sheet, with the measurement that motivated the change.
T1_BAND_LO, T1_BAND_HI = 0.80, 0.99      # the contradiction band, from RGM-0.2
T1_MAX_LEGIT_FRACTION = 0.005            # >0.5% of legitimate pairs in band -> collision
T2_MIN_SEPARABILITY = 0.65               # DIRECTION-FREE: max(AUC, 1-AUC). See Fix A.
T3_MAX_MEMORIES = 10_000
T3_MAX_WRITES_PER_DAY = 500

UNKNOWN = "UNKNOWN"

# Fix D: the flags are not ordinary editable booleans. They must arrive inside an
# exact-schema, owner-attributed deployment manifest. A missing or malformed manifest yields
# UNKNOWN -- never False -- so a deleted or corrupted file cannot read as "everything is safe".
MANIFEST_REQUIRED = ("schema_version", "scope", "deployment_id", "config_digest",
                     "declared_owner", "timestamp", "source_commit", "derivation")
MANIFEST_SCHEMA_VERSION = "1.0"
MANIFEST_SCOPE = "PRODUCTION_DEPLOYMENT"
PRODUCTION_FLAGS = ("production_memory_feeds_training", "production_untrusted_write_path",
                    "production_observable_thresholds")

# The events at which this check is MANDATORY (owner ruling section 4). Event-driven, not
# polled: a weekly job would currently just reprint DORMANT, which is ceremony, not protection.
MANDATORY_EVENTS = (
    "before any replay-training job",
    "before memory-to-training is enabled",
    "after verifier thresholds change",
    "after memory schema changes",
    "after the write path becomes untrusted",
    "after every registered corpus snapshot",
    "after a major memory-volume threshold is crossed",
)


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


def load_json(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_manifest(path):
    """Fix D: validate authority. Returns (flags_dict_or_None, list_of_problems).

    A manifest that fails validation contributes NOTHING -- every production flag becomes
    UNKNOWN. It does not fall back to False.
    """
    m = load_json(path)
    if m is None:
        return None, [f"no readable manifest at {path}"]
    problems = []
    for k in MANIFEST_REQUIRED:
        if k not in m:
            problems.append(f"missing required field '{k}'")
    if m.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        problems.append(f"schema_version is {m.get('schema_version')!r}, "
                        f"expected {MANIFEST_SCHEMA_VERSION!r}")
    if m.get("scope") != MANIFEST_SCOPE:
        problems.append(f"scope is {m.get('scope')!r}, expected {MANIFEST_SCOPE!r} -- this "
                        f"trigger governs PRODUCTION deployment, not development benches")
    for k in PRODUCTION_FLAGS:
        if k not in m:
            problems.append(f"missing production flag '{k}'")
        elif not isinstance(m[k], bool):
            problems.append(f"production flag '{k}' is not a boolean")
    if m.get("derivation") not in ("declared", "derived_from_pipeline_config"):
        problems.append("derivation must be 'declared' or 'derived_from_pipeline_config'")
    return (None if problems else m), problems


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
    return frac > T1_MAX_LEGIT_FRACTION, (
        f"{inband}/{len(pairs)} legitimate pairs = {frac:.4%} inside "
        f"[{T1_BAND_LO}, {T1_BAND_HI}); threshold {T1_MAX_LEGIT_FRACTION:.2%} "
        f"(RGM-0.2 measured 0/3794 = 0.0000%)")


def check_T2(c):
    """STRUCTURAL SIGNAL LOST: can degree still tell a forgery from a memory?

    Fix A -- DIRECTION-FREE. Separability is max(AUC, 1-AUC), so 0.50 means no separability and
    BOTH 1.00 and 0.00 mean perfect separation. Reporting the raw AUC alone was ambiguous: an
    AUC of 0.10 is excellent reverse-direction separation, not a failure, and a spec written as
    "AUC < 0.65" would have read it as an alarm.
    """
    if not c:
        return UNKNOWN, "no corpus supplied"
    mems = c.get("memories", [])
    if not any("is_forgery" in m for m in mems):
        return UNKNOWN, ("no is_forgery labels -- T2 CANNOT be evaluated. Without known or "
                         "synthesised forgeries there is nothing to measure separability on")
    real = [len(m.get("links", [])) for m in mems if not m.get("is_forgery")]
    forged = [len(m.get("links", [])) for m in mems if m.get("is_forgery")]
    a = auc(real, forged)
    if a is None:
        return UNKNOWN, "one of the two populations is empty"
    sep = max(a, 1.0 - a)
    return sep < T2_MIN_SEPARABILITY, (
        f"degree separability max(AUC, 1-AUC) = {sep:.4f} (raw AUC {a:.4f}), threshold "
        f"{T2_MIN_SEPARABILITY}; 0.50 = none, 1.00 = perfect in either direction. CMB-RP0 "
        f"measured mean degree 4.89 forged vs 6.67 real, and a degree filter BEAT the verifier")


def check_T3(c, man):
    """SCALE PAST REVIEW.

    Fix B, second half. A supplied corpus is a SAMPLE; the manifest declares the DEPLOYMENT.
    This originally read the count from the corpus whenever one was given and discarded the
    manifest entirely, so an 80-memory synthetic sample silently overrode a declared 50,000-
    memory deployment and T3 could never fire in the one case it exists for. Both sources are
    now considered and the LARGER wins -- a sample cannot bound the real store, and a corpus
    bigger than declared is itself worth surfacing.
    """
    def bigger(a, b):
        vals = [v for v in (a, b) if v is not None]
        return max(vals) if vals else None

    n_c = len(c.get("memories", [])) if c else None
    n_m = (man or {}).get("n_memories")
    w_c = (c or {}).get("writes_per_day")
    w_m = (man or {}).get("writes_per_day")
    n, w = bigger(n_c, n_m), bigger(w_c, w_m)
    if n is None and w is None:
        return UNKNOWN, "no corpus and no manifest n_memories / writes_per_day"
    hits = []
    if n is not None and n > T3_MAX_MEMORIES:
        hits.append(f"{n} memories > {T3_MAX_MEMORIES} "
                    f"(corpus {n_c}, manifest {n_m} -- larger wins)")
    if w is not None and w > T3_MAX_WRITES_PER_DAY:
        hits.append(f"{w} writes/day > {T3_MAX_WRITES_PER_DAY} "
                    f"(corpus {w_c}, manifest {w_m} -- larger wins)")
    return (bool(hits), "; ".join(hits) if hits
            else f"n_memories={n} (corpus {n_c}, manifest {n_m}), writes_per_day={w} "
                 f"-- both inside review scale")


def declared(man, key, desc):
    if man is None:
        return UNKNOWN, f"{desc} -- NO VALID MANIFEST, so authority cannot be established"
    if key not in man:
        return UNKNOWN, f"{desc} -- absent from manifest"
    return bool(man[key]), f"{desc} -- manifest says {man[key]}"


def decide(T):
    """Owner ruling Fix B -- the explicit state ladder, with T3 given real authority.

        DORMANT   not T5
        WATCH     T5 and any of T3, T4, T6   (defences measured healthy)
        NECESSARY T5 and (T1 or T2)
        URGENT    NECESSARY and (T3 or T4 or T6)

    Plus the fail-closed rule that outranks the ladder: an UNKNOWN that could change the answer
    escalates to WATCH_UNRESOLVED rather than passing. T5 UNKNOWN is included -- if we cannot
    establish that production memory does NOT feed training, we may not call it DORMANT.
    """
    t5 = T["T5_PROD_MEMORY_FEEDS_TRAINING"]
    defences = (T["T1_BAND_COLLISION"], T["T2_STRUCTURAL_SIGNAL_LOST"])
    raisers = (T["T3_SCALE_PAST_REVIEW"], T["T4_PROD_UNTRUSTED_WRITE_PATH"],
               T["T6_PROD_OBSERVABLE_THRESHOLDS"])

    if t5 is UNKNOWN:
        return "WATCH_UNRESOLVED"
    if t5 is not True:
        return "DORMANT"
    if any(x is True for x in defences):
        return "URGENT" if any(x is True for x in raisers) else "NECESSARY"
    if any(x is UNKNOWN for x in defences):
        return "WATCH_UNRESOLVED"
    if any(x is True for x in raisers):
        return "WATCH"
    return "CLEAR"


EXIT = {"DORMANT": 0, "CLEAR": 0, "WATCH": 0,
        "WATCH_UNRESOLVED": 10, "NECESSARY": 20, "URGENT": 30}

MESSAGE = {
    "DORMANT": ["Production memory does not feed training.",
                "The deferred build stays deferred."],
    "CLEAR": ["Production memory feeds training, and both defence conditions are measured "
              "healthy.",
              "No scale or adversary condition is raised."],
    "WATCH": ["Production memory feeds training and both defences are measured healthy, but "
              "scale, an untrusted write path, or observable thresholds is raised.",
              "Not blocking. Re-check at the next mandatory event."],
    "WATCH_UNRESOLVED": ["THIS BLOCKS ANY MEMORY-TO-TRAINING JOB.",
                         "Either authority could not be established, or a defence condition "
                         "could not be evaluated while production memory feeds training.",
                         "UNKNOWN IS NOT 'NO'.",
                         "Supply a valid deployment manifest, and the corpus labels the "
                         "checker needs -- legitimate_group for T1, is_forgery for T2 -- or "
                         "obtain an explicit owner decision to proceed without them."],
    "NECESSARY": ["THIS BLOCKS ANY MEMORY-TO-TRAINING JOB.",
                  "Production memory feeds training and a defence condition has FIRED: either "
                  "the semantic band has collided or the structural signal is gone.",
                  "The structural-forgery defence is needed before memory may train the model.",
                  "It is NOT authorized -- it requires its own preregistration, its own "
                  "mechanism-free baselines, and owner authorization."],
    "URGENT": ["THIS BLOCKS ANY MEMORY-TO-TRAINING JOB.",
               "As NECESSARY, and scale or an adversary write-path raises it further.",
               "A party may be able to write memories and observe or infer the thresholds."],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus")
    ap.add_argument("--manifest", default=MANIFEST_DEFAULT)
    ap.add_argument("--job", default=None,
                    help="label of the pipeline event invoking this check, for the log")
    a = ap.parse_args()

    corpus = load_json(a.corpus) if a.corpus else None
    man, problems = load_manifest(a.manifest)

    checks = {
        "T1_BAND_COLLISION": check_T1(corpus),
        "T2_STRUCTURAL_SIGNAL_LOST": check_T2(corpus),
        "T3_SCALE_PAST_REVIEW": check_T3(corpus, man),
        "T4_PROD_UNTRUSTED_WRITE_PATH": declared(
            man, "production_untrusted_write_path",
            "production memory writes not first-party and reviewed"),
        "T5_PROD_MEMORY_FEEDS_TRAINING": declared(
            man, "production_memory_feeds_training",
            "PRODUCTION memory contents enter training/replay"),
        "T6_PROD_OBSERVABLE_THRESHOLDS": declared(
            man, "production_observable_thresholds",
            "a production writer can observe/infer the thresholds"),
    }

    print("STRUCTURAL FORGERY DEFENCE -- TRIGGER CHECK")
    print(f"corpus:   {a.corpus or '(none)'}")
    print(f"manifest: {a.manifest}")
    if a.job:
        print(f"job:      {a.job}")
    if problems:
        print()
        print("  MANIFEST AUTHORITY NOT ESTABLISHED -- every production flag is UNKNOWN:")
        for pr in problems:
            print(f"    - {pr}")
    elif man:
        print(f"authority: deployment {man['deployment_id']}, owner {man['declared_owner']}, "
              f"config {man['config_digest'][:16]}, {man['derivation']}, {man['timestamp']}")
    print()
    for k, (v, why) in checks.items():
        mark = {True: "FIRED  ", False: "clear  ", UNKNOWN: "UNKNOWN"}[v]
        print(f"  [{mark}] {k}")
        print(f"            {why}")
    print()

    state = decide({k: v for k, (v, _) in checks.items()})
    rc = EXIT[state]
    print(f"TRIGGER STATE: {state}    EXIT {rc}"
          f"{'   (BLOCKS memory-to-training)' if rc else ''}")
    print()
    for line in MESSAGE[state]:
        print("  " + line)
    return rc


if __name__ == "__main__":
    sys.exit(main())
