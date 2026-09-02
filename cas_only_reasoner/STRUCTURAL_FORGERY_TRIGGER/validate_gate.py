"""Prove the interlock actually stops training. An untested gate is not a gate.

The trigger's own suites prove it emits the right STATE. This proves the launcher-side wiring
turns a blocking state into TRAINING THAT DOES NOT HAPPEN -- which is the only thing that
matters once it is installed.

Every case runs a MOCK LAUNCHER whose "trainer" sets a flag when it executes. The assertion is
not merely "an exception was raised"; it is "the trainer never ran".

    python validate_gate.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from replay_training_gate import (  # noqa: E402
    TrainingBlocked, bind_into_receipt, derive_manifest, require_clearance)

OWNER = "test-owner"
COMMIT = "0" * 40
TS = "2026-09-02T00:00:00Z"

TRAINED = {"ran": False}


def mock_launcher(*, corpus_path=None, pipeline_config, watch_ack=None, memory_count=None):
    """A launcher that does it the required way: gate FIRST, then train, then bind."""
    TRAINED["ran"] = False
    clearance = require_clearance(                 # step 1-4; raises if not permitted
        job_id="DEMO-RP", pipeline_config=pipeline_config, declared_owner=OWNER,
        source_commit=COMMIT, timestamp=TS, corpus_path=corpus_path,
        watch_ack=watch_ack, memory_count=memory_count, event="pre-training")
    TRAINED["ran"] = True                          # <- reached ONLY if the gate permitted
    return bind_into_receipt({"project": "demo", "result": "..."}, clearance)   # step 5


def corpus(*, legit_in_band, degree_separable, n=60, path=None):
    mems = []
    for i in range(n):
        g = i // 2
        base = [(g + k) % 10 for k in range(6)]
        if legit_in_band and i % 2 == 1:
            t = base[:]
            t[0] = (t[0] + 5) % 10                 # exactly one position differs -> 0.8333
        elif legit_in_band:
            t = base[:]
        else:
            t = [(i * 3 + k * 2) % 10 for k in range(6)]
        mems.append({"id": f"m{i}", "trajectory": t, "links": ["x"] * 7,
                     "is_forgery": False, "legitimate_group": g})
    for j in range(20):
        mems.append({"id": f"f{j}", "trajectory": [9] * 6,
                     "links": ["x"] * (4 if degree_separable else 7), "is_forgery": True})
    blob = {"memories": mems, "writes_per_day": 0}
    p = path or os.path.join(tempfile.mkdtemp(), "corpus.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(blob, f)
    return p


HEALTHY = corpus(legit_in_band=False, degree_separable=True)
COLLIDED = corpus(legit_in_band=True, degree_separable=True)
NO_SIGNAL = corpus(legit_in_band=False, degree_separable=False)

TRAINS = {"memory_feeds_training": True}
NO_TRAIN = {"memory_feeds_training": False}

results = []


def case(label, fn, *, expect_blocked, expect_state=None, expect_code=None):
    try:
        receipt = fn()
        blocked, state, code, err = False, None, 0, None
    except TrainingBlocked as e:
        receipt, blocked, state, code, err = None, True, e.state, e.code, str(e)
    ok = (blocked == expect_blocked)
    if ok and expect_state:
        ok = (state == expect_state)
    if ok and expect_code is not None:
        ok = (code == expect_code)
    # THE LOAD-BEARING ASSERTION: blocked means the trainer never executed.
    if blocked and TRAINED["ran"]:
        ok, err = False, "BLOCKED BUT THE TRAINER STILL RAN"
    if not blocked and not TRAINED["ran"] and expect_blocked is False:
        ok, err = False, "permitted but the trainer did not run"
    if (not blocked) and receipt is not None:
        if "structural_forgery_clearance" not in receipt:
            ok, err = False, "receipt has no clearance bound into it"
    results.append((label, expect_blocked, blocked, state, code,
                    TRAINED["ran"], ok, err))


# ---- the gate must stop training ----------------------------------------------------------
case("memory feeds training, NO corpus -> defences unevaluated",
     lambda: mock_launcher(pipeline_config=TRAINS),
     expect_blocked=True, expect_state="WATCH_UNRESOLVED", expect_code=10)

case("band collision -> verifier would start blocking truth",
     lambda: mock_launcher(corpus_path=COLLIDED, pipeline_config=TRAINS),
     expect_blocked=True, expect_state="NECESSARY", expect_code=20)

case("degree signal gone -> cheap defence evaporated",
     lambda: mock_launcher(corpus_path=NO_SIGNAL, pipeline_config=TRAINS),
     expect_blocked=True, expect_state="NECESSARY", expect_code=20)

case("scale past review + defence fired -> URGENT",
     lambda: mock_launcher(corpus_path=NO_SIGNAL, pipeline_config=TRAINS,
                           memory_count=50_000),
     expect_blocked=True, expect_state="URGENT", expect_code=30)

case("scale raised, defences healthy, NO ack -> WATCH blocks",
     lambda: mock_launcher(corpus_path=HEALTHY, pipeline_config=TRAINS,
                           memory_count=50_000),
     expect_blocked=True, expect_state="WATCH", expect_code=5)

# ---- the gate must permit a clean run, and the receipt must carry the clearance ------------
case("healthy corpus, training on -> CLEAR, trainer runs, receipt bound",
     lambda: mock_launcher(corpus_path=HEALTHY, pipeline_config=TRAINS),
     expect_blocked=False, expect_state=None)

case("pipeline says training OFF -> DORMANT, trainer runs",
     lambda: mock_launcher(corpus_path=HEALTHY, pipeline_config=NO_TRAIN),
     expect_blocked=False)


def _ack_case():
    m = derive_manifest(job_id="DEMO-RP", pipeline_config=TRAINS, declared_owner=OWNER,
                        source_commit=COMMIT, timestamp=TS, memory_count=50_000)
    ack = {"acknowledges": "WATCH", "job_id": "DEMO-RP",
           "manifest_digest": m["config_digest"], "acknowledged_by": OWNER}
    return mock_launcher(corpus_path=HEALTHY, pipeline_config=TRAINS,
                         memory_count=50_000, watch_ack=ack)


case("WATCH with an owner ack bound to this job -> permitted",
     _ack_case, expect_blocked=False)


def _bad_ack_case():
    ack = {"acknowledges": "WATCH", "job_id": "SOME-OTHER-JOB",
           "manifest_digest": "deadbeef", "acknowledged_by": OWNER}
    return mock_launcher(corpus_path=HEALTHY, pipeline_config=TRAINS,
                         memory_count=50_000, watch_ack=ack)


case("WATCH with an ack for a DIFFERENT job -> still blocks",
     _bad_ack_case, expect_blocked=True, expect_state="WATCH", expect_code=5)

# ---- the receipt path must not be forgeable ------------------------------------------------
forge = []
try:
    bind_into_receipt({"project": "demo"}, {"gate": "STRUCTURAL_FORGERY_DEFENCE",
                                            "trigger_exit_code": 0, "job_id": "x",
                                            "scope": "y", "event": "z",
                                            "trigger_state": "CLEAR",
                                            "manifest_digest": "fake",
                                            "pipeline_derived_memory_feeds_training": True,
                                            "trigger_receipt": {}})
    forge.append(("REFUSES a hand-built clearance citing no trigger receipt", False))
except TrainingBlocked:
    forge.append(("REFUSES a hand-built clearance citing no trigger receipt", True))


def _tampered_state():
    """A real clearance whose STATE has been edited after the fact."""
    c = dict(_real_clearance)
    c["trigger_state"] = "CLEAR"
    c["trigger_exit_code"] = 0
    return bind_into_receipt({"project": "demo"}, c)

# capture a genuine BLOCKING clearance to test post-hoc tampering
_real_clearance = None
try:
    mock_launcher(corpus_path=COLLIDED, pipeline_config=TRAINS)
except TrainingBlocked as e:
    _real_clearance = e.receipt

try:
    _tampered_state()
    forge.append(("REFUSES a real clearance whose state was edited to CLEAR", False))
except TrainingBlocked:
    forge.append(("REFUSES a real clearance whose state was edited to CLEAR", True))

for label, cl in (("no clearance at all", None),
                  ("clearance from a BLOCKING result", {"gate": "STRUCTURAL_FORGERY_DEFENCE",
                                                        "trigger_exit_code": 20})):
    try:
        bind_into_receipt({"project": "demo"}, cl)
        forge.append((f"bind_into_receipt REFUSES {label}", False))
    except TrainingBlocked:
        forge.append((f"bind_into_receipt REFUSES {label}", True))

try:
    derive_manifest(job_id="X", pipeline_config={"memory_feeds_training": "true"},
                    declared_owner=OWNER, source_commit=COMMIT, timestamp=TS)
    forge.append(("derive_manifest REFUSES a non-boolean pipeline flag", False))
except ValueError:
    forge.append(("derive_manifest REFUSES a non-boolean pipeline flag", True))

# ---- report --------------------------------------------------------------------------------
fails = 0
hdr = (f"{'scenario':<58}{'expect':>9}{'blocked':>9}{'state':>20}{'rc':>4}{'trained':>9}")
print("INTERLOCK PROOF -- does a blocking state actually stop training?")
print()
print(hdr)
print("-" * len(hdr))
for label, exp, got, state, code, trained, ok, err in results:
    fails += not ok
    print(f"{label:<58}{'BLOCK' if exp else 'allow':>9}{'BLOCK' if got else 'allow':>9}"
          f"{str(state):>20}{code:>4}{str(trained):>9}  {'ok' if ok else '<-- FAIL: ' + str(err)}")

print()
print("RECEIPT PATH -- a run receipt must not be obtainable without a real clearance")
for label, ok in forge:
    fails += not ok
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}")

print()
print("SELF-VALIDATION:", "PASS" if not fails else f"FAIL ({fails})")
sys.exit(1 if fails else 0)
