"""Run the four LM-T1 test suites and print their exact counts.

Each suite is a plain unittest module in this folder; this tool runs them in one process and reports the counts.
It deliberately loads them by name, one at a time, so a failure in one suite is reported as itself rather than
mixed into another.

Run from this folder, with PYTHONPATH as recorded in PROVENANCE.md:

    C:\\Python314\\python.exe -X utf8 -B run_suites.py

Expected: 26, 11, 5 (the base suites, unchanged) and 26 (the language_v3 suite).
"""
import io
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
BRIDGE_ROOT = Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011")
LACUNA_ROOT = Path(r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1")
SUITES = (("test_lm_t1", "base suite LM-T1 (cce.py)"),
          ("test_lm_t1b", "base suite LM-T1b (cce_v01b.py)"),
          ("test_lm_t1c", "base suite LM-T1c (cce_v01c.py)"),
          ("test_lm_t1v3", "language_v3 suite: p/q numbers and the REFUSE and CLOSE turns"))


def main():
    for p in (str(HERE), str(LACUNA_ROOT), str(BRIDGE_ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)
    ok = True
    for name, what in SUITES:
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.TestLoader().loadTestsFromName(name))
        ok = ok and result.wasSuccessful()
        print("%-14s Ran %d tests, failures %d, errors %d -> %s   (%s)"
              % (name, result.testsRun, len(result.failures), len(result.errors),
                 "OK" if result.wasSuccessful() else "FAILED", what))
        for test, trace in result.failures + result.errors:
            print("  FAILED", test)
            print("  " + "\n  ".join(trace.strip().splitlines()[-6:]))
    print("ALL SUITES OK" if ok else "A SUITE FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
