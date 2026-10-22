"""Run HELM's own unittest modules (scratch copy of the v9 helm_now) with the FINAL v7.3 rules (final_patch.install).
usage: python -X utf8 -B -I final_tests.py <helm_now copy> <scripts dir> [module ...]"""
import os, sys, unittest
root, scripts = sys.argv[1], sys.argv[2]
sys.path.insert(0, root); sys.path.insert(0, scripts); os.chdir(root)
import helm_wide_turn as WT  # noqa: E402
import final_patch  # noqa: E402
final_patch.install(WT)
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[3:])
res = unittest.TextTestRunner(verbosity=1).run(suite)
for t, tb in res.failures + res.errors:
    print("FAIL/ERROR:", t.id(), tb.strip().splitlines()[-1][:300])
