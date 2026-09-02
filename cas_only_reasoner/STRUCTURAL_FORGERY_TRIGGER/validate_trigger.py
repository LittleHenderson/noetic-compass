"""Self-validation for the structural-forgery trigger.

An untested trigger is not a trigger. This constructs the scenarios the firing rule is meant to
distinguish and asserts the checker returns the right state and exit code for each. It also
proves the case this program keeps getting wrong: that an UNEVALUATED condition ESCALATES
instead of silently passing.

    python validate_trigger.py
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHK = os.path.join(HERE, "check_structural_trigger.py")


def corpus(*, legit_in_band, degree_separable, n=60):
    """Synthesise a corpus with the two properties the automatic conditions measure."""
    # Groups are PAIRS (legitimate_group = i//2). To land a pair INSIDE the band the two
    # members must differ by exactly ONE position: lev 1 of 6 -> sim 0.8333, inside
    # [0.80, 0.99). My first fixture mutated BOTH members, giving lev 2 -> 0.667, which is
    # BELOW the band -- so the fixture, not the checker, was wrong.
    mems = []
    for i in range(n):
        g = i // 2
        base = [(g + k) % 10 for k in range(6)]
        if legit_in_band and i % 2 == 1:
            t = base[:]; t[0] = (t[0] + 5) % 10                   # exactly one position differs
        elif legit_in_band:
            t = base[:]
        else:
            t = [(i * 3 + k * 2) % 10 for k in range(6)]          # spread out, well below band
        mems.append({"id": f"m{i}", "trajectory": t,
                     "links": ["x"] * 7, "is_forgery": False, "legitimate_group": g})
    for j in range(20):
        deg = 4 if degree_separable else 7                        # 7 == identical to real
        mems.append({"id": f"f{j}", "trajectory": [9, 9, 9, 9, 9, 9],
                     "links": ["x"] * deg, "is_forgery": True})
    return {"memories": mems, "writes_per_day": 0}


def run(corpus_obj, flags):
    with tempfile.TemporaryDirectory() as d:
        args = [sys.executable, CHK, "--flags", os.path.join(d, "f.json")]
        json.dump(flags, open(os.path.join(d, "f.json"), "w"))
        if corpus_obj is not None:
            cp = os.path.join(d, "c.json"); json.dump(corpus_obj, open(cp, "w"))
            args += ["--corpus", cp]
        r = subprocess.run(args, capture_output=True, text=True)
        state = [l for l in r.stdout.splitlines() if l.startswith("TRIGGER STATE:")]
        return (state[0].split(": ")[1] if state else "NO_STATE"), r.returncode, r.stdout


OFF = {"untrusted_write_path": False, "memory_feeds_training": False,
       "observable_thresholds": False}
TRAIN = dict(OFF, memory_feeds_training=True)
ADVERSARY = dict(TRAIN, untrusted_write_path=True)

CASES = [
    ("current state: bench only, healthy corpus",
     corpus(legit_in_band=False, degree_separable=True), OFF, "DORMANT", 0),
    ("memory feeds training, but both defences healthy",
     corpus(legit_in_band=False, degree_separable=True), TRAIN, "WATCH", 0),
    ("memory feeds training, NO corpus -- conditions UNEVALUATED",
     None, TRAIN, "WATCH_UNRESOLVED", 3),
    ("BAND COLLISION + training  -> the verifier starts blocking truth",
     corpus(legit_in_band=True, degree_separable=True), TRAIN, "NECESSARY", 4),
    ("DEGREE SIGNAL GONE + training -> the cheap defence has evaporated",
     corpus(legit_in_band=False, degree_separable=False), TRAIN, "NECESSARY", 4),
    ("degree signal gone + training + untrusted write path",
     corpus(legit_in_band=False, degree_separable=False), ADVERSARY, "URGENT", 5),
    ("band collision alone, memory does NOT feed training",
     corpus(legit_in_band=True, degree_separable=True), OFF, "WATCH", 0),
]

fails = 0
print(f"{'scenario':<58}{'expect':>18}{'got':>18}{'rc':>4}")
for name, c, f, want, want_rc in CASES:
    got, rc, out = run(c, f)
    ok = (got == want and rc == want_rc)
    fails += not ok
    print(f"{name:<58}{want:>18}{got:>18}{rc:>4}  {'ok' if ok else '<-- FAIL'}")
print()
print("SELF-VALIDATION:", "PASS" if not fails else f"FAIL ({fails} case(s))")
sys.exit(1 if fails else 0)
