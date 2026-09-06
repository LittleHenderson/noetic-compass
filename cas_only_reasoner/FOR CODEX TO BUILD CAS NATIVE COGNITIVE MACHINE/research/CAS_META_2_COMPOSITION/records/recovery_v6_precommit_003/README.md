# Recovery precommit checks

`run.py` completed with 163 passing test functions and 160 passing subtests.
The two GPU tests were deliberately deselected. They must pass on AWS before
the 72-case replay. This is a focused check, not the full clean-checkout suite.
All 557 proposed package file hashes matched before and after the checks.

Earlier attempts are retained unchanged:

- `recovery_v6_precommit_001` selected two tests from the wrong file name.
  Pytest stopped with exit 4 before running tests.
- `recovery_v6_precommit_002` ran all 163 functions and 160 subtests successfully,
  but the receipt helper expected GPU skips instead of the project's configured
  GPU deselection. Its overall receipt therefore says `completed: false`.
- This run explicitly selects `not gpu` and verifies two deselected GPU tests.

Staged file bytes were checked against raw disk bytes. The whitespace check did
not pass: retained raw outputs contain original whitespace, and some new text
files have a trailing blank line. Tested source and raw evidence were not
rewritten merely to clear that check.
