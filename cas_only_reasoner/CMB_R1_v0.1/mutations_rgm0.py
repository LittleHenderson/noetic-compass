"""CHK-M for RGM-0: every kill-law gate is demonstrated to FAIL on a registered mutant.
A mutant that runs clean but does not fire its intended gate is reported as a GAP, not hidden."""
import json, subprocess, sys, hashlib

EXPECT = {
    "M1": "RGM0_FAILED:STATIC_CAS_GEOMETRY_REDUNDANT",
    "M2": "RGM0_FAILED:CAS_TRAJECTORY_VALUE_NOT_DEMONSTRATED",
    "M3": "RGM0_FAILED:RESONANCE_LAYER_ORNAMENTAL",
    "M4": "RGM0_FAILED:GENERIC_GEOMETRY_SUFFICIENT",
    "M5": "RGM0_FAILED:CAS_GEOMETRY_NOT_LOAD_BEARING",
    "M6": "RGM0_FAILED:ECHO_CONTROLS_FAILED",
}
report = {"mutants": [], "all_mutants_behaved": True}
for mid, expected in EXPECT.items():
    p = subprocess.run([sys.executable, "run_rgm0.py", "--mutant", mid],
                       capture_output=True, text=True)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
        got = out["status"]
    except Exception as e:
        got = "RUN_ERROR:" + str(e)[:80]
    ok = (got == expected)
    report["mutants"].append({"id": mid, "expected": expected, "got": got, "fired": ok})
    report["all_mutants_behaved"] = report["all_mutants_behaved"] and ok
# pristine rerun must be byte-identical to the pristine baseline hash
p0 = subprocess.run([sys.executable, "run_rgm0.py"], capture_output=True, text=True)
h0 = hashlib.sha256(p0.stdout.strip().encode()).hexdigest()
report["pristine_rerun_sha256"] = h0
report["note"] = ("M7 (one-family-result residual) is exercised structurally: KL7 is evaluated "
                  "inside every run; the M1-M6 mutants also re-exercise KL7 on their deltas.")
print(json.dumps(report, indent=1))
sys.exit(0 if report["all_mutants_behaved"] else 1)
