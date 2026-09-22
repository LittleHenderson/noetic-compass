# Restoring the four tests my merge deleted — receipts, 2026-09-22

**What happened.** My merge `078d00ed` (2026-09-21) deleted seven passing test functions. I found and restored
three on 2026-09-22 (`626cc84b`). An independent peer audit (`codex/helm-peer-audit-20260922` @ `0922f339`,
`records/peer_audit_20260922/merge/REPORT.md`) found **four more** in
`noetic-compass-scaffold/noetic-compass/tests/test_notation_compiler_nesting_and_defects.py`:

- `test_review_a_deep_flat_chain_fails_cleanly_and_still_serialises`
- `test_review_fn_names_are_not_reserved_but_let_names_and_parameters_are`
- `test_review_no_cross_domain_warning_when_a_side_has_no_known_domain_at_typecheck`
- `test_review_the_worlds_warning_comes_from_the_alias_not_from_the_word`

My audit package had told the auditor to "check whether anything else went the same way". I should have run
that check myself before handing the package over. I did not.

**What these receipts show, in order.**

| file | what it records | observed |
|---|---|---|
| `before_compiler_suite_65ad3008.*` | five-file compiler suite at `65ad3008`, before the restore | `639 passed` |
| `original_four_bodies_vs_current_compiler_65ad3008.*` | the four ORIGINAL bodies, from `git show d50abbbc:<file>` unmodified, run against today's compiler | `4 passed` |
| `after_compiler_suite_restored.*` | the same five-file suite after the restore | `643 passed` |

The case-ID comparison of the two XML files: **0 cases lost, 0 non-passing, exactly the four names added.**
The four behaviours were never broken. What was lost was the protection against breaking them later.

**How the restore was done.** `restore_four_tests.py` copies the text block byte-for-byte from `d50abbbc` and
inserts it where it stood (after `test_defect_7`, before `test_defect_8`). It refuses to write unless every
restored function's source is identical to the original and every other function is undisturbed.

**Was anything else lost? Checked this time, not assumed.**

- `function_census.py` → `function_census_output.txt`: every function, method and class defined at `d50abbbc`
  in the 12 `.py` files my side of the merge changed (merge-base `c3855275`) still exists at the same path.
  **0 missing.** Production code included, nested definitions included.
- `test_body_census.py` → `test_body_census_output.txt`: 93 my-side test functions compared body-by-body.
  0 missing. Four bodies differ from `d50abbbc`, each explained in `body_diff_output.txt`:
  - `test_the_manifest_cites_exactly_the_current_contract`: `/0.5` became `/0.7` — the merge kept the other
    line's newer Q3 data version. An update, not a weaker check.
  - The three help-text guards I restored on 2026-09-22 differ **only by docstrings I added** during that
    restore. Their assertions are identical to `7f32129d`/`d50abbbc`. My earlier word "restored" should read
    "restored, with added docstrings".
- `constant_census.py` → `constant_census_output.txt`: that restore also re-typed the module-level word lists
  rather than copying them. All ten module-level constants are identical in value to `7f32129d`.

**Environment.** Python 3.14.0 at `C:/Python314/python.exe`, pytest 9.0.2, `TEMP`/`TMP` outside the repository,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `--noconftest -o addopts= -p no:cacheprovider`. The one warning in each run
is pytest reporting an unknown `asyncio_mode` config option; it is not a test result.

**Line endings.** Python on Windows wrote the `.txt` captures with CRLF. They were normalised to LF before
commit; no other byte was changed. The `.xml` files are pytest's own output, unmodified.
