"""Evaluate the STRUCTURAL FORGERY DEFENCE trigger.

Registered 2026-09-02. Owner rulings 2026-09-02 applied: Fixes A-D, then v0.3 job-scoping.
Spec: STRUCTURAL_FORGERY_DEFENCE_TRIGGER.md

    python check_structural_trigger.py
    python check_structural_trigger.py --corpus <snapshot.json>
    python check_structural_trigger.py --manifest CMB_RP1_JOB_MANIFEST.json \
        --expected-scope DEVELOPMENT_REPLAY --job-id CMB-RP1 \
        --pipeline-config <emitted_by_the_launcher.json> --job pre-training \
        --receipt-out trigger_receipt.json

v0.3 -- THE GAP THIS CLOSES. A PRODUCTION manifest saying "no production system feeds
training" returns DORMANT. That is true, and it is USELESS as clearance for a DEVELOPMENT
replay job that really does put retrieved memories into training. The checker would have
truthfully reported the empty production building safe while the experimental workshop next
door was running the furnace. A manifest is now bound to a SCOPE and a JOB, and the launcher
must declare both -- a mismatch is REFUSED, not quietly accepted.

EXIT CODES. For any memory-to-training job, EVERY NONZERO CODE BLOCKS LAUNCH.

     0   DORMANT | CLEAR | WATCH_ACKNOWLEDGED
     5   WATCH              -- no demonstrated failure, but scale/exposure. Passes ONLY with an
                               owner acknowledgement BOUND TO THIS JOB. Never silently green.
    10   WATCH_UNRESOLVED   -- a required fact is unknown. UNKNOWN IS NOT "NO".
    10   REFUSED            -- manifest scope / job identity / derivation mismatch
    20   NECESSARY          -- a defence condition has FIRED
    30   URGENT             -- fired, and the system is exposed, large, or observable

Pure CPU, stdlib only. Reads files, computes, prints. Spends nothing, launches nothing.
"""
import argparse
import hashlib
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
MANIFEST_SCHEMA_VERSION = "1.0"

# A manifest is valid only for the scope it declares. The flag names differ by scope so a file
# cannot be repurposed across the boundary by editing one field.
SCOPES = {
    "PRODUCTION_DEPLOYMENT": {"prefix": "production_", "id_field": "deployment_id"},
    "DEVELOPMENT_REPLAY":    {"prefix": "",            "id_field": "job_id"},
}
FLAG_STEMS = ("memory_feeds_training", "untrusted_write_path", "observable_thresholds")
AUTHORITY_FIELDS = ("schema_version", "scope", "config_digest", "declared_owner",
                    "timestamp", "source_commit", "derivation")
DERIVATIONS = ("declared", "derived_from_pipeline_config")

MANDATORY_EVENTS = (
    "before every replay-training launch",
    "before enabling memory-to-training",
    "after verifier logic changes",
    "after threshold changes",
    "after memory schema changes",
    "after write-path trust changes",
    "after major scale thresholds",
    "during deployment release",
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


def digest_of(m):
    return hashlib.sha256(json.dumps(
        {k: v for k, v in m.items() if not k.startswith("_") and k != "config_digest"},
        sort_keys=True).encode()).hexdigest()


def load_manifest(path, expected_scope, expected_job_id, pipeline_cfg):
    """Validate authority AND fitness for the job being launched.

    Returns (manifest_or_None, problems, refusals). `problems` make flags UNKNOWN;
    `refusals` are active misuse -- a manifest presented for a job it does not govern.
    """
    m = load_json(path)
    if m is None:
        return None, [f"no readable manifest at {path}"], []
    problems, refusals = [], []

    scope = m.get("scope")
    if scope not in SCOPES:
        problems.append(f"scope {scope!r} is not one of {sorted(SCOPES)}")
        return None, problems, refusals
    spec = SCOPES[scope]

    for k in AUTHORITY_FIELDS:
        if k not in m:
            problems.append(f"missing required field '{k}'")
    if spec["id_field"] not in m:
        problems.append(f"scope {scope} requires '{spec['id_field']}'")
    if m.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        problems.append(f"schema_version {m.get('schema_version')!r}, "
                        f"expected {MANIFEST_SCHEMA_VERSION!r}")
    if m.get("derivation") not in DERIVATIONS:
        problems.append(f"derivation must be one of {DERIVATIONS}")
    for stem in FLAG_STEMS:
        k = spec["prefix"] + stem
        if k not in m:
            problems.append(f"scope {scope} requires flag '{k}'")
        elif not isinstance(m[k], bool):
            problems.append(f"flag '{k}' is not a boolean")
    if "config_digest" in m and m["config_digest"] != digest_of(m):
        problems.append("config_digest does not match the manifest contents")

    # --- refusals: the manifest may be perfectly valid and STILL not govern this job ---
    if expected_scope and scope != expected_scope:
        refusals.append(
            f"manifest scope is {scope}, but the launcher declared {expected_scope}. "
            f"A {scope} manifest MAY NEVER authorize a {expected_scope} job.")
    if expected_job_id:
        actual = m.get(spec["id_field"])
        if actual != expected_job_id:
            refusals.append(f"manifest {spec['id_field']} is {actual!r}, launcher declared "
                            f"{expected_job_id!r}")

    # --- derivation must be verifiable, not merely asserted ---
    flag_key = spec["prefix"] + "memory_feeds_training"
    if m.get("derivation") == "derived_from_pipeline_config":
        if pipeline_cfg is None:
            refusals.append("derivation claims 'derived_from_pipeline_config' but no "
                            "--pipeline-config was supplied, so the claim cannot be verified")
        else:
            derived = pipeline_cfg.get("memory_feeds_training")
            if not isinstance(derived, bool):
                refusals.append("pipeline config has no boolean 'memory_feeds_training'")
            elif flag_key in m and m[flag_key] != derived:
                refusals.append(
                    f"DECLARED {flag_key}={m[flag_key]} DISAGREES with the pipeline "
                    f"configuration ({derived}). The pipeline is the fact; the manifest is a "
                    f"claim about it.")
    elif pipeline_cfg is not None:
        derived = pipeline_cfg.get("memory_feeds_training")
        if isinstance(derived, bool) and flag_key in m and m[flag_key] != derived:
            refusals.append(
                f"declared {flag_key}={m[flag_key]} disagrees with the supplied pipeline "
                f"configuration ({derived})")

    return (None if problems else m), problems, refusals


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
    """STRUCTURAL SIGNAL LOST -- DIRECTION-FREE (Fix A).

    Separability is max(AUC, 1-AUC): 0.50 = none, 1.00 = perfect in EITHER direction. A raw
    AUC of 0.10 is excellent reverse-direction separation, not a failure.
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
    """SCALE PAST REVIEW. Corpus is a SAMPLE; the manifest declares the DEPLOYMENT.

    Reading only the corpus let an 80-memory synthetic sample override a declared 50,000-memory
    deployment, so T3 could not fire in the one case it exists for. Both are read; larger wins.
    """
    def bigger(a, b):
        vals = [v for v in (a, b) if v is not None]
        return max(vals) if vals else None

    man = man or {}
    n_c = len(c.get("memories", [])) if c else None
    n_m = man.get("n_memories", man.get("memory_count"))
    w_c = (c or {}).get("writes_per_day")
    w_m = man.get("writes_per_day")
    n, w = bigger(n_c, n_m), bigger(w_c, w_m)
    if n is None and w is None:
        return UNKNOWN, "no corpus and no manifest memory count / writes_per_day"
    hits = []
    if n is not None and n > T3_MAX_MEMORIES:
        hits.append(f"{n} memories > {T3_MAX_MEMORIES} "
                    f"(corpus {n_c}, manifest {n_m} -- larger wins)")
    if w is not None and w > T3_MAX_WRITES_PER_DAY:
        hits.append(f"{w} writes/day > {T3_MAX_WRITES_PER_DAY} "
                    f"(corpus {w_c}, manifest {w_m} -- larger wins)")
    return (bool(hits), "; ".join(hits) if hits
            else f"memories={n} (corpus {n_c}, manifest {n_m}), writes_per_day={w} "
                 f"-- both inside review scale")


def declared(man, scope, stem, desc):
    if man is None:
        return UNKNOWN, f"{desc} -- NO VALID MANIFEST, so authority cannot be established"
    key = SCOPES[scope]["prefix"] + stem
    if key not in man:
        return UNKNOWN, f"{desc} -- '{key}' absent from manifest"
    return bool(man[key]), f"{desc} -- manifest '{key}' = {man[key]}"


def valid_ack(ack, man, scope, job_id):
    """An acknowledgement must be BOUND TO THIS JOB, not a standing waiver."""
    if ack is None or man is None:
        return False, "none supplied"
    idf = SCOPES[scope]["id_field"]
    want = job_id or man.get(idf)
    if ack.get("acknowledges") != "WATCH":
        return False, "ack does not acknowledge state WATCH"
    if ack.get(idf) != want:
        return False, f"ack {idf} {ack.get(idf)!r} does not match {want!r}"
    if ack.get("manifest_digest") != man.get("config_digest"):
        return False, "ack manifest_digest does not match this manifest"
    if not ack.get("acknowledged_by"):
        return False, "ack has no acknowledged_by"
    return True, (f"acknowledged by {ack['acknowledged_by']} for {idf}={want}, "
                  f"bound to manifest {str(man.get('config_digest'))[:16]}")


def decide(T, refused, ack_ok):
    if refused:
        return "REFUSED"
    t5 = T["T5_MEMORY_FEEDS_TRAINING"]
    defences = (T["T1_BAND_COLLISION"], T["T2_STRUCTURAL_SIGNAL_LOST"])
    raisers = (T["T3_SCALE_PAST_REVIEW"], T["T4_UNTRUSTED_WRITE_PATH"],
               T["T6_OBSERVABLE_THRESHOLDS"])
    if t5 is UNKNOWN:
        return "WATCH_UNRESOLVED"
    if t5 is not True:
        return "DORMANT"
    if any(x is True for x in defences):
        return "URGENT" if any(x is True for x in raisers) else "NECESSARY"
    if any(x is UNKNOWN for x in defences):
        return "WATCH_UNRESOLVED"
    if any(x is True for x in raisers):
        return "WATCH_ACKNOWLEDGED" if ack_ok else "WATCH"
    return "CLEAR"


EXIT = {"DORMANT": 0, "CLEAR": 0, "WATCH_ACKNOWLEDGED": 0, "WATCH": 5,
        "WATCH_UNRESOLVED": 10, "REFUSED": 10, "NECESSARY": 20, "URGENT": 30}

MESSAGE = {
    "DORMANT": ["Memory does not feed training in the declared scope.",
                "The deferred build stays deferred."],
    "CLEAR": ["Memory feeds training, both defence conditions are measured healthy, and no "
              "scale or exposure condition is raised."],
    "WATCH_ACKNOWLEDGED": ["Scale or exposure is raised, defences measured healthy, and an "
                           "owner acknowledgement BOUND TO THIS JOB is present."],
    "WATCH": ["BLOCKS UNTIL ACKNOWLEDGED.",
              "No demonstrated defence failure, but scale, an untrusted write path, or "
              "observable thresholds is raised.",
              "This must not disappear into an ordinary green exit. Supply an owner "
              "acknowledgement bound to this job's id and manifest digest."],
    "WATCH_UNRESOLVED": ["THIS BLOCKS.",
                         "Either authority could not be established, or a defence condition "
                         "could not be evaluated while memory feeds training.",
                         "UNKNOWN IS NOT 'NO'."],
    "REFUSED": ["THIS BLOCKS.",
                "The manifest does not govern the job being launched.",
                "A manifest for one scope or job MAY NEVER authorize another."],
    "NECESSARY": ["THIS BLOCKS.",
                  "Memory feeds training and a defence condition has FIRED: either the "
                  "semantic band has collided or the structural signal is gone.",
                  "The structural-forgery defence is needed before memory may train the model.",
                  "It is NOT authorized -- it requires its own preregistration, its own "
                  "mechanism-free baselines, and owner authorization."],
    "URGENT": ["THIS BLOCKS.",
               "As NECESSARY, and scale or an adversary write-path raises it further."],
}


class _LadderParser(argparse.ArgumentParser):
    """Any CLI misuse must BLOCK with a ladder code, never argparse's exit 2.

    Found by an EXTERNAL spec-only fixture (SB06): an illegal --expected-scope value made
    argparse exit 2, a code the frozen contract does not define -- in the same commit where
    that contract says a launcher "must not be able to reinterpret an exit code". A caller
    doing `rc == 0 or block` is safe either way, but a caller switching on the documented
    codes would meet an undocumented one. Every parse failure is now REFUSED / 10.
    """

    def error(self, message):
        print("STRUCTURAL FORGERY DEFENCE -- TRIGGER CHECK")
        print("TRIGGER STATE: REFUSED    EXIT 10   (BLOCKS LAUNCH)")
        print(f"  The launcher invoked the checker incorrectly: {message}")
        print("  A malformed invocation cannot authorize anything.")
        sys.exit(EXIT["REFUSED"])


def main():
    ap = _LadderParser()
    ap.add_argument("--corpus")
    ap.add_argument("--manifest", default=MANIFEST_DEFAULT)
    # NOT argparse `choices=`: an unknown scope is a governance refusal with a ladder code,
    # not a usage error with argparse's undocumented exit 2.
    ap.add_argument("--expected-scope",
                    help=f"scope the LAUNCHER declares, one of {sorted(SCOPES)}; "
                         f"a mismatch or an unknown value is REFUSED")
    ap.add_argument("--job-id", help="job id the LAUNCHER declares; a mismatch is REFUSED")
    ap.add_argument("--pipeline-config",
                    help="config emitted by the pipeline; memory_feeds_training is DERIVED "
                         "from it and a disagreeing manifest is REFUSED")
    ap.add_argument("--watch-ack", help="owner acknowledgement bound to this job")
    ap.add_argument("--job", help="label of the invoking event, for the log")
    ap.add_argument("--receipt-out", help="write a machine-readable trigger receipt here, to "
                                          "be bound into the run receipt")
    a = ap.parse_args()

    if a.expected_scope is not None and a.expected_scope not in SCOPES:
        print("STRUCTURAL FORGERY DEFENCE -- TRIGGER CHECK")
        print()
        print("  REFUSED -- the launcher declared an unrecognised scope:")
        print(f"    - --expected-scope {a.expected_scope!r} is not one of {sorted(SCOPES)}")
        print()
        print(f"TRIGGER STATE: REFUSED    EXIT {EXIT['REFUSED']}   (BLOCKS LAUNCH)")
        print()
        for line in MESSAGE["REFUSED"]:
            print("  " + line)
        return EXIT["REFUSED"]

    corpus = load_json(a.corpus) if a.corpus else None
    pipeline_cfg = load_json(a.pipeline_config) if a.pipeline_config else None
    man, problems, refusals = load_manifest(a.manifest, a.expected_scope, a.job_id, pipeline_cfg)
    scope = (man or {}).get("scope") or a.expected_scope or "PRODUCTION_DEPLOYMENT"

    checks = {
        "T1_BAND_COLLISION": check_T1(corpus),
        "T2_STRUCTURAL_SIGNAL_LOST": check_T2(corpus),
        "T3_SCALE_PAST_REVIEW": check_T3(corpus, man),
        "T4_UNTRUSTED_WRITE_PATH": declared(man, scope, "untrusted_write_path",
                                            "memory writes not first-party and reviewed"),
        "T5_MEMORY_FEEDS_TRAINING": declared(man, scope, "memory_feeds_training",
                                             "memory contents enter training/replay"),
        "T6_OBSERVABLE_THRESHOLDS": declared(man, scope, "observable_thresholds",
                                             "a writer can observe/infer the thresholds"),
    }
    ack_ok, ack_why = valid_ack(load_json(a.watch_ack) if a.watch_ack else None,
                                man, scope, a.job_id)

    print("STRUCTURAL FORGERY DEFENCE -- TRIGGER CHECK")
    print(f"corpus:          {a.corpus or '(none)'}")
    print(f"manifest:        {a.manifest}")
    print(f"declared scope:  {a.expected_scope or '(not declared by launcher)'}"
          f"    job-id: {a.job_id or '(not declared)'}")
    if a.job:
        print(f"event:           {a.job}")
    if refusals:
        print()
        print("  REFUSED -- this manifest does not govern this job:")
        for r in refusals:
            print(f"    - {r}")
    if problems:
        print()
        print("  MANIFEST AUTHORITY NOT ESTABLISHED -- every declared flag is UNKNOWN:")
        for pr in problems:
            print(f"    - {pr}")
    elif man:
        idf = SCOPES[scope]["id_field"]
        print(f"authority:       scope {scope}, {idf} {man.get(idf)}, owner "
              f"{man['declared_owner']}, config {man['config_digest'][:16]}, "
              f"{man['derivation']}")
    print()
    for k, (v, why) in checks.items():
        mark = {True: "FIRED  ", False: "clear  ", UNKNOWN: "UNKNOWN"}[v]
        print(f"  [{mark}] {k}")
        print(f"            {why}")
    print()

    state = decide({k: v for k, (v, _) in checks.items()}, refusals, ack_ok)
    rc = EXIT[state]
    print(f"TRIGGER STATE: {state}    EXIT {rc}"
          f"{'   (BLOCKS LAUNCH)' if rc else ''}")
    if state in ("WATCH", "WATCH_ACKNOWLEDGED"):
        print(f"  acknowledgement: {ack_why}")
    print()
    for line in MESSAGE[state]:
        print("  " + line)

    if a.receipt_out:
        receipt = {
            "trigger": "STRUCTURAL_FORGERY_DEFENCE", "version": "v0.3",
            "state": state, "exit_code": rc,
            "declared_scope": a.expected_scope, "declared_job_id": a.job_id,
            "event": a.job,
            "manifest_path": a.manifest,
            "manifest_digest": (man or {}).get("config_digest"),
            "manifest_scope": (man or {}).get("scope"),
            "manifest_derivation": (man or {}).get("derivation"),
            "corpus_path": a.corpus,
            "refusals": refusals, "authority_problems": problems,
            "acknowledgement": {"valid": ack_ok, "detail": ack_why},
            "conditions": {k: {"fired": v, "detail": why} for k, (v, why) in checks.items()},
            "thresholds": {"T1_band": [T1_BAND_LO, T1_BAND_HI],
                           "T1_max_legit_fraction": T1_MAX_LEGIT_FRACTION,
                           "T2_min_separability": T2_MIN_SEPARABILITY,
                           "T3_max_memories": T3_MAX_MEMORIES,
                           "T3_max_writes_per_day": T3_MAX_WRITES_PER_DAY},
        }
        with open(a.receipt_out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(receipt, f, indent=2, sort_keys=True)
        print()
        print(f"  trigger receipt -> {a.receipt_out}  (bind this into the run receipt)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
