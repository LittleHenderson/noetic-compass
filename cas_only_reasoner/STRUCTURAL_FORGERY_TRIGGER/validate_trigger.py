"""Self-validation for the structural-forgery trigger. An untested trigger is not a trigger.

Covers the owner's fixes:

  Fix A   T2 separability is DIRECTION-FREE -- forgeries that are HIGH degree read as
          well-separated, not as an alarm.
  Fix B   the state ladder, with T3 (scale) given real authority, and scale read from BOTH the
          corpus sample and the declared deployment.
  Fix C   UNKNOWN blocks; exit codes 0/5/10/20/30.
  Fix D   a missing, malformed, mis-scoped or non-boolean manifest yields UNKNOWN, never False.

  v0.3    JOB SCOPING -- the gap that mattered most. A PRODUCTION manifest reading
          "no production system feeds training" returns DORMANT, which is TRUE and USELESS as
          clearance for a DEVELOPMENT replay job that really does feed memory into training.
          The checker must REFUSE a manifest that does not govern the job being launched.
  v0.3    WATCH requires an owner acknowledgement BOUND TO THIS JOB; it may never be a silent
          green exit.

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
    """Legitimate groups are PAIRS. To land a pair INSIDE the band the two members must differ
    by exactly ONE position: lev 1 of 6 -> sim 0.8333, inside [0.80, 0.99)."""
    mems = []
    for i in range(n):
        g = i // 2
        base = [(g + k) % 10 for k in range(6)]
        if legit_in_band and i % 2 == 1:
            t = base[:]
            t[0] = (t[0] + 5) % 10
        elif legit_in_band:
            t = base[:]
        else:
            t = [(i * 3 + k * 2) % 10 for k in range(6)]
        mems.append({"id": f"m{i}", "trajectory": t, "links": ["x"] * 7,
                     "is_forgery": False, "legitimate_group": g})
    for j in range(20):
        deg = 7 if not degree_separable else (20 if reverse_degree else 4)
        mems.append({"id": f"f{j}", "trajectory": [9, 9, 9, 9, 9, 9],
                     "links": ["x"] * deg, "is_forgery": True})
    return {"memories": mems, "writes_per_day": 0}


def manifest(scope="PRODUCTION_DEPLOYMENT", **over):
    pre = "production_" if scope == "PRODUCTION_DEPLOYMENT" else ""
    body = {"schema_version": "1.0", "scope": scope, "config_digest": "",
            "declared_owner": "test", "timestamp": "2026-09-02T00:00:00Z",
            "source_commit": "0" * 40, "derivation": "declared",
            pre + "memory_feeds_training": False,
            pre + "untrusted_write_path": False,
            pre + "observable_thresholds": False,
            "n_memories": 0, "writes_per_day": 0}
    body["deployment_id" if scope == "PRODUCTION_DEPLOYMENT" else "job_id"] = "test-id"
    body.update(over)
    body["config_digest"] = hashlib.sha256(json.dumps(
        {k: v for k, v in body.items() if not k.startswith("_") and k != "config_digest"},
        sort_keys=True).encode()).hexdigest()
    return body


def ack_for(man, scope="PRODUCTION_DEPLOYMENT", **over):
    idf = "deployment_id" if scope == "PRODUCTION_DEPLOYMENT" else "job_id"
    a = {"acknowledges": "WATCH", idf: man.get(idf),
         "manifest_digest": man.get("config_digest"), "acknowledged_by": "owner"}
    a.update(over)
    return a


def run(corpus_obj, man_obj, *, expected_scope=None, job_id=None, pipeline=None, ack=None):
    with tempfile.TemporaryDirectory() as d:
        mp = os.path.join(d, "m.json")
        if man_obj is not None:
            json.dump(man_obj, open(mp, "w"))
        args = [sys.executable, CHK, "--manifest", mp]
        if corpus_obj is not None:
            cp = os.path.join(d, "c.json")
            json.dump(corpus_obj, open(cp, "w"))
            args += ["--corpus", cp]
        if expected_scope:
            args += ["--expected-scope", expected_scope]
        if job_id:
            args += ["--job-id", job_id]
        if pipeline is not None:
            pp = os.path.join(d, "p.json")
            json.dump(pipeline, open(pp, "w"))
            args += ["--pipeline-config", pp]
        if ack is not None:
            akp = os.path.join(d, "a.json")
            json.dump(ack, open(akp, "w"))
            args += ["--watch-ack", akp]
        r = subprocess.run(args, capture_output=True, text=True)
        line = [l for l in r.stdout.splitlines() if l.startswith("TRIGGER STATE:")]
        return (line[0].split()[2] if line else "NO_STATE"), r.returncode


PROD = manifest()
PROD_TRAIN = manifest(production_memory_feeds_training=True)
DEV = manifest("DEVELOPMENT_REPLAY", job_id="CMB-RP1")
DEV_TRAIN = manifest("DEVELOPMENT_REPLAY", job_id="CMB-RP1", memory_feeds_training=True)
DEV_TRAIN_DERIVED = manifest("DEVELOPMENT_REPLAY", job_id="CMB-RP1",
                             memory_feeds_training=True,
                             derivation="derived_from_pipeline_config")
HEALTHY = corpus(legit_in_band=False, degree_separable=True)
WATCH_MAN = manifest(production_memory_feeds_training=True, n_memories=50_000)

CASES = [
    # ---- v0.3: THE GAP. A production manifest may not clear a development replay job. ----
    ("v0.3 THE GAP: PRODUCTION manifest used to clear a DEVELOPMENT_REPLAY job -> REFUSED",
     HEALTHY, PROD, "REFUSED", 10, dict(expected_scope="DEVELOPMENT_REPLAY", job_id="CMB-RP1")),
    ("v0.3 the same manifest with NO declared scope would have passed as DORMANT",
     HEALTHY, PROD, "DORMANT", 0, {}),
    ("v0.3 CMB-RP1's own dev manifest, training on, no corpus -> BLOCKS (not DORMANT)",
     None, DEV_TRAIN, "WATCH_UNRESOLVED", 10,
     dict(expected_scope="DEVELOPMENT_REPLAY", job_id="CMB-RP1")),
    ("v0.3 CMB-RP1 dev manifest + healthy corpus -> CLEAR",
     HEALTHY, DEV_TRAIN, "CLEAR", 0,
     dict(expected_scope="DEVELOPMENT_REPLAY", job_id="CMB-RP1")),
    ("v0.3 job_id mismatch -> REFUSED",
     HEALTHY, DEV_TRAIN, "REFUSED", 10,
     dict(expected_scope="DEVELOPMENT_REPLAY", job_id="CMB-RP2")),
    ("v0.3 DEV manifest used to clear a PRODUCTION job -> REFUSED",
     HEALTHY, DEV, "REFUSED", 10, dict(expected_scope="PRODUCTION_DEPLOYMENT")),

    # ---- v0.3: derivation must be verifiable, not asserted ----
    ("v0.3 derivation claims 'derived' but no pipeline config supplied -> REFUSED",
     HEALTHY, DEV_TRAIN_DERIVED, "REFUSED", 10,
     dict(expected_scope="DEVELOPMENT_REPLAY", job_id="CMB-RP1")),
    ("v0.3 derived manifest agrees with pipeline config -> CLEAR",
     HEALTHY, DEV_TRAIN_DERIVED, "CLEAR", 0,
     dict(expected_scope="DEVELOPMENT_REPLAY", job_id="CMB-RP1",
          pipeline={"memory_feeds_training": True})),
    ("v0.3 manifest says training OFF, pipeline says ON -> REFUSED",
     HEALTHY, DEV, "REFUSED", 10,
     dict(expected_scope="DEVELOPMENT_REPLAY", job_id="CMB-RP1",
          pipeline={"memory_feeds_training": True})),

    # ---- v0.3: WATCH must not be a silent green ----
    ("v0.3 WATCH without acknowledgement -> exit 5, blocks",
     HEALTHY, WATCH_MAN, "WATCH", 5, {}),
    ("v0.3 WATCH with an owner ack bound to this job -> passes",
     HEALTHY, WATCH_MAN, "WATCH_ACKNOWLEDGED", 0, dict(ack=ack_for(WATCH_MAN))),
    ("v0.3 WATCH with an ack for a DIFFERENT job -> still blocks",
     HEALTHY, WATCH_MAN, "WATCH", 5,
     dict(ack=ack_for(WATCH_MAN, deployment_id="some-other-deployment"))),
    ("v0.3 WATCH with an ack bound to a different manifest digest -> still blocks",
     HEALTHY, WATCH_MAN, "WATCH", 5, dict(ack=ack_for(WATCH_MAN, manifest_digest="deadbeef"))),

    # ---- Fix D: authority ----
    ("Fix D: NO manifest at all -> blocks", HEALTHY, None, "WATCH_UNRESOLVED", 10, {}),
    ("Fix D: missing a required authority field -> blocks",
     HEALTHY, {k: v for k, v in PROD_TRAIN.items() if k != "declared_owner"},
     "WATCH_UNRESOLVED", 10, {}),
    ("Fix D: tampered config_digest -> blocks",
     HEALTHY, dict(PROD_TRAIN, config_digest="0" * 64), "WATCH_UNRESOLVED", 10, {}),
    ("Fix D: flag not a boolean -> blocks",
     HEALTHY, manifest(production_memory_feeds_training="yes"), "WATCH_UNRESOLVED", 10, {}),

    # ---- Fix A / Fix B / Fix C ----
    ("Fix A: forgeries are HUBS (reverse direction) -> well separated, no alarm",
     corpus(legit_in_band=False, degree_separable=True, reverse_degree=True),
     PROD_TRAIN, "CLEAR", 0, {}),
    ("Fix C: training on, NO corpus -> defences unevaluated -> blocks",
     None, PROD_TRAIN, "WATCH_UNRESOLVED", 10, {}),
    ("band collision + training -> NECESSARY",
     corpus(legit_in_band=True, degree_separable=True), PROD_TRAIN, "NECESSARY", 20, {}),
    ("degree signal gone + training -> NECESSARY",
     corpus(legit_in_band=False, degree_separable=False), PROD_TRAIN, "NECESSARY", 20, {}),
    ("Fix B: NECESSARY + declared SCALE (sample would have hidden it) -> URGENT",
     corpus(legit_in_band=False, degree_separable=False),
     manifest(production_memory_feeds_training=True, n_memories=50_000), "URGENT", 30, {}),
    ("Fix B: NECESSARY + untrusted write path -> URGENT",
     corpus(legit_in_band=False, degree_separable=False),
     manifest(production_memory_feeds_training=True, production_untrusted_write_path=True),
     "URGENT", 30, {}),
    ("baseline: production memory does not feed training -> DORMANT",
     HEALTHY, PROD, "DORMANT", 0, {}),
    ("band collision but training OFF -> DORMANT (trigger is training-scoped)",
     corpus(legit_in_band=True, degree_separable=True), PROD, "DORMANT", 0, {}),
]

fails = 0
print(f"{'scenario':<74}{'expect':>20}{'got':>20}{'rc':>4}")
for name, c, m, want, want_rc, kw in CASES:
    got, rc = run(c, m, **kw)
    ok = (got == want and rc == want_rc)
    fails += not ok
    print(f"{name:<74}{want:>20}{got:>20}{rc:>4}  {'ok' if ok else '<-- FAIL'}")
print()
print("SELF-VALIDATION:", "PASS" if not fails else f"FAIL ({fails} case(s))")
sys.exit(1 if fails else 0)
