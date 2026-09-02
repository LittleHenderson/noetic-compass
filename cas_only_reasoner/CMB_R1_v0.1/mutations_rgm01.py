# mutations_rgm01.py — CHK-M battery for the RGM-0.1 gates (2-world demonstrations).
import json, sys
import run_rgm01 as R

EXPECT = {"N1": "G_STATIC fires (STATIC fails) when the static term is zeroed",
          "N2": "G_TRAJ fires when trajectory comparison is order-insensitive",
          "N3": "G_PROP fires when propagation is disabled (pattern completion collapses)",
          "N4": "G_GENERIC fails to establish when the generic arm equals the CAS arm (law-level)",
          "N5": "G_COHECHO fires when coherence is removed from the BOTH config",
          "N6": "G_EFF flags the family-level charging bug (recomputed ratio exceeds cap)",
          "N7": "G_ROOT reports NOT_SUPPORTED on measurements despite any fiat"}
out = []
ok = True
for mid in ["N1", "N2", "N3", "N4", "N5", "N6", "N7"]:
    r = R.run_mutant(mid)
    r["expectation"] = EXPECT[mid]
    out.append(r)
    ok = ok and r["fired"]
report = {"mutants": out, "all_mutants_behaved": ok,
          "note": "2-world demonstration subsets; pristine 20-world battery in RGM01_RECEIPT.json"}
with open("RGM01_MUTATION_REPORT.json", "w") as f:
    json.dump(report, f, indent=1, sort_keys=True)
print("ALL_BEHAVED:", ok)
for r in out:
    print(r["mutant"], "->", "FIRED" if r["fired"] else "GAP", "|", r["observed"])
sys.exit(0 if ok else 1)
