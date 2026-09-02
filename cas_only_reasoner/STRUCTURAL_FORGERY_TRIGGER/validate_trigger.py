"""Self-validation for the structural-forgery trigger. An untested trigger is not a trigger.

Covers the owner's four fixes (ruling 2026-09-02) explicitly:

  Fix A  T2 separability is DIRECTION-FREE -- forgeries that are HIGH degree must read as
         well-separated, not as an alarm. A raw-AUC rule would have fired on them.
  Fix B  the state ladder, with T3 (scale) given real authority -- scale must be able to
         escalate NECESSARY to URGENT, which it could not do before.
  Fix C  WATCH_UNRESOLVED exits NONZERO and blocks; exit codes are 0/10/20/30.
  Fix D  a missing, malformed, or wrongly-scoped manifest yields UNKNOWN, never False, and
         therefore BLOCKS rather than silently permitting.

    python validate_trigger.py
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHK = os.path.join(HERE, "check_structural_trigger.py")


def corpus(*, legit_in_band, degree_separable, reverse_degree=False, n=60):
    """Synthesise a corpus with the properties the automatic conditions measure.

    Legitimate groups are PAIRS. To land a pair INSIDE the band the two members must differ by
    exactly ONE position: lev 1 of 6 -> sim 0.8333, inside [0.80, 0.99).
    """
    mems = []
    for i in range(n):
        g = i // 2
        base = [(g + k) % 10 for k in range(6)]
        if legit_in_band and i % 2 == 1:
            t = base[:]
            t[0] = (t[0] + 5) % 10                       # exactly one position differs
        elif legit_in_band:
            t = base[:]
        else:
            t = [(i * 3 + k * 2) % 10 for k in range(6)]  # spread out, well below band
        mems.append({"id": f"m{i}", "trajectory": t, "links": ["x"] * 7,
                     "is_forgery": False, "legitimate_group": g})
    for j in range(20):
        if not degree_separable:
            deg = 7                                       # identical to real -> no signal
        elif reverse_degree:
            deg = 20                                      # forgeries are HUBS (Fix A case)
        else:
            deg = 4                                       # forgeries are low-degree
        mems.append({"id": f"f{j}", "trajectory": [9, 9, 9, 9, 9, 9],
                     "links": ["x"] * deg, "is_forgery": True})
    return {"memories": mems, "writes_per_day": 0}


def manifest(**over):
    body = {"schema_version": "1.0", "scope": "PRODUCTION_DEPLOYMENT",
            "deployment_id": "test", "config_digest": "", "declared_owner": "test",
            "timestamp": "2026-09-02T00:00:00Z", "source_commit": "0" * 40,
            "derivation": "declared",
            "production_memory_feeds_training": False,
            "production_untrusted_write_path": False,
            "production_observable_thresholds": False,
            "n_memories": 0, "writes_per_day": 0}
    body.update(over)
    body["config_digest"] = hashlib.sha256(
        json.dumps({k: v for k, v in body.items() if k != "config_digest"},
                   sort_keys=True).encode()).hexdigest()
    return body


def run(corpus_obj, man_obj):
    with tempfile.TemporaryDirectory() as d:
        mp = os.path.join(d, "m.json")
        if man_obj is not None:
            json.dump(man_obj, open(mp, "w"))
        args = [sys.executable, CHK, "--manifest", mp]
        if corpus_obj is not None:
            cp = os.path.join(d, "c.json")
            json.dump(corpus_obj, open(cp, "w"))
            args += ["--corpus", cp]
        r = subprocess.run(args, capture_output=True, text=True)
        line = [l for l in r.stdout.splitlines() if l.startswith("TRIGGER STATE:")]
        return (line[0].split()[2] if line else "NO_STATE"), r.returncode


TRAIN = manifest(production_memory_feeds_training=True)
HEALTHY = corpus(legit_in_band=False, degree_separable=True)

CASES = [
    # (label, corpus, manifest, expected state, expected exit)
    ("baseline: production memory does not feed training",
     HEALTHY, manifest(), "DORMANT", 0),
    ("training on, both defences measured healthy",
     HEALTHY, TRAIN, "CLEAR", 0),

    # --- Fix D: authority. Missing / malformed / mis-scoped manifests must BLOCK. ---
    ("Fix D: NO manifest at all -> T5 unknown -> blocks",
     HEALTHY, None, "WATCH_UNRESOLVED", 10),
    ("Fix D: manifest missing a required authority field -> blocks",
     HEALTHY, {k: v for k, v in TRAIN.items() if k != "config_digest"},
     "WATCH_UNRESOLVED", 10),
    ("Fix D: manifest with the OLD dev-scoped field names -> blocks",
     HEALTHY, {"memory_feeds_training": False, "untrusted_write_path": False,
               "observable_thresholds": False}, "WATCH_UNRESOLVED", 10),
    ("Fix D: wrong scope (bench, not production) -> blocks",
     HEALTHY, manifest(scope="DEVELOPMENT_BENCH"), "WATCH_UNRESOLVED", 10),
    ("Fix D: production flag not a boolean -> blocks",
     HEALTHY, manifest(production_memory_feeds_training="yes"), "WATCH_UNRESOLVED", 10),

    # --- Fix C: unknown must block, not warn. ---
    ("Fix C: training on, NO corpus -> defences unevaluated -> blocks",
     None, TRAIN, "WATCH_UNRESOLVED", 10),

    # --- Fix A: direction-free separability. ---
    ("Fix A: forgeries are HUBS (reverse direction) -> still well separated, no alarm",
     corpus(legit_in_band=False, degree_separable=True, reverse_degree=True),
     TRAIN, "CLEAR", 0),

    # --- the defence conditions themselves ---
    ("band collision + training -> verifier starts blocking truth",
     corpus(legit_in_band=True, degree_separable=True), TRAIN, "NECESSARY", 20),
    ("degree signal gone + training -> cheap defence evaporated",
     corpus(legit_in_band=False, degree_separable=False), TRAIN, "NECESSARY", 20),

    # --- Fix B: T3 now has authority; raisers escalate and can also produce WATCH. ---
    ("Fix B: NECESSARY + SCALE past review -> URGENT (T3 was previously decorative)",
     corpus(legit_in_band=False, degree_separable=False), manifest(
         production_memory_feeds_training=True, n_memories=50_000), "URGENT", 30),
    ("Fix B: NECESSARY + untrusted write path -> URGENT",
     corpus(legit_in_band=False, degree_separable=False), manifest(
         production_memory_feeds_training=True, production_untrusted_write_path=True),
     "URGENT", 30),
    ("Fix B: healthy defences + scale -> WATCH, not blocking",
     HEALTHY, manifest(production_memory_feeds_training=True, n_memories=50_000),
     "WATCH", 0),
    ("Fix B: healthy defences + observable thresholds -> WATCH, not blocking",
     HEALTHY, manifest(production_memory_feeds_training=True,
                       production_observable_thresholds=True), "WATCH", 0),
    ("band collision but production training OFF -> dormant (trigger is training-scoped)",
     corpus(legit_in_band=True, degree_separable=True), manifest(), "DORMANT", 0),
]

fails = 0
print(f"{'scenario':<66}{'expect':>18}{'got':>18}{'rc':>4}")
for name, c, m, want, want_rc in CASES:
    got, rc = run(c, m)
    ok = (got == want and rc == want_rc)
    fails += not ok
    print(f"{name:<66}{want:>18}{got:>18}{rc:>4}  {'ok' if ok else '<-- FAIL'}")
print()
print("SELF-VALIDATION:", "PASS" if not fails else f"FAIL ({fails} case(s))")
sys.exit(1 if fails else 0)
