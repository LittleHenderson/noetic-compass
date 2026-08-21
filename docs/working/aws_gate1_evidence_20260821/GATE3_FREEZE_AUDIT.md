# Gate 3 — freeze audit — 2026-08-21

Gate 3 is: **freeze the code, pin the exact commit, image, hardware, and receipts, and re-run the full test suites — runtime, canary, guardian, and hostile inputs.**

This is the audit. **Nothing was re-pinned and no gate was weakened.** Re-pinning an execution-gating document is a deliberate act and is listed at the end as an owner decision, with the exact values it would need.

---

## Test suite results

| Suite | Result |
|---|---|
| Guardian runtime + core + timing harness + precreate | **355 passed, 0 failed** |
| C14 interpretability adapter (hostile inputs included) | **48 passed, 0 failed** |
| Open-weight canary v2 + trajectory runtime | **77 passed, 8 FAILED** |

Two operational notes, both real and both easy to trip over:

- Run the guardian suite with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`. `test_candidate_tree_contains_no_python_or_pytest_cache_artifacts` asserts the candidate tree carries no `__pycache__`, so a plain `pytest` run fails that test on its **own** bytecode. That is the test working.
- The canary suite and the adapter suite **cannot be run in one pytest invocation**. Two different `tests/conftest.py` files collide as the same module name and pytest aborts with `ImportPathMismatchError`. Run each from its own root.

---

## The 8 canary failures — one cause, and it is the known stale freeze

All eight failures reduce to a single root cause. Seven raise `bundle source-file manifest differs from preregistration`; one raises `current source-file manifest differs from preregistration`.

**Root cause, located exactly.** `FROZEN_SOURCE_RELATIVE_PATHS` is an explicit list of **15** files. Diffing all 15 between the freeze commit `709cca09` — the commit that introduced `required_source_file_manifest_sha256` — and current `HEAD`:

```
noetic-compass-scaffold/noetic-compass/api/services/
  cas_harness_interpretability_adapter.py   | 1081 +++++++++++++++++++-
1 file changed, 1074 insertions(+), 7 deletions(-)
```

**Exactly one of the fifteen moved.** It is the C14 adapter, changed by the C14 work at `fd90d88e`. The other fourteen are byte-identical to the freeze.

That one change moves the aggregate manifest hash:

| | value |
|---|---|
| Preregistration pins | `7E496CB8A008C1AC37C7D6A09570FF90C1D97B4E55405E4AF4D5A965E644BC61` |
| Current sources produce | `6EC46F9A42A52B6EE13F65EEEE81AB73889BD56B247F828393C84794A4227CCF` |

This is precisely what the handoff warned about: *"The canary execution freeze is not current after the C13/C14 source changes. Do not launch from the old preregistration/source manifest."* **The failures confirm that warning empirically rather than contradicting it.**

**This was not caused by work done today.** The 15 frozen paths do not include `measure_guardian_timing_evidence.py`, its tests, or `.gitattributes`, and the diff above shows the adapter as the sole change.

### The part that matters more than the count

**Four of the eight failures are negative tests, and the stale manifest is blinding them.** They are written to prove that the canary refuses a specific abuse, each asserting on a specific refusal message:

- `watchdog/provider deadline mismatch`
- `watchdog window`
- `evidence-file manifest`
- `canary is inert`

Each now fails with `Regex pattern did not match`, because the manifest check fires **first** and returns `bundle source-file manifest differs from preregistration` instead. The refusals may still work. **The point is that these tests can no longer prove it.** A stale freeze is not merely noise here — it disarms the tests whose whole job is to catch a bad launch, and it does so silently, in the direction of looking like an ordinary failure.

Individually confirmed still passing after the line-ending fix, so the freeze itself is intact where it is checkable:

| Binding | Status |
|---|---|
| `required_runner_source_sha256` `D94DCD70…` | **MATCH** |
| `required_watchdog_script_sha256` `E57BDC11…` | **MATCH** |
| `required_github_supervisor_source_sha256` `D5DB5CD6…` | **MATCH** |
| `required_dependency_lock_sha256` `9E990C06…` | **MATCH** |
| `required_source_file_manifest_sha256` `7E496CB8…` | **DRIFTED** → `6EC46F9A…` |

---

## What a correct re-pin would need — owner decision, not an agent's

Re-pinning to `6EC46F9A…` would make the eight tests pass. **That is exactly why it must not be done casually.** Making a red suite green by editing the document it checks against is the shape of weakening a gate, even when the edit is legitimate. It is legitimate only if the source set is genuinely final and the re-pin is complete.

It would not be complete today. Two bindings in the same block are still unset:

- `required_source_commit_sha256` = **`None`**
- `required_provider_launcher_source_sha256` = **`None`**

and the document still declares `execution_authority` = `NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN`, `provider_launcher_live_status` = `NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE`.

A complete re-pin therefore means: confirm the 15-file source set is final, set the manifest hash to `6EC46F9A42A52B6EE13F65EEEE81AB73889BD56B247F828393C84794A4227CCF`, fill both `None` bindings, re-run all four suites, and confirm the four blinded negative tests go back to failing **for their own stated reasons** rather than passing. **If those four do not recover their original assertions, the re-pin is wrong and must be reverted.**

## Standing

Gate 3 is **`OPEN`**. The freeze is stale by exactly one file, the cause is known and located, and the remedy is a deliberate, complete re-pin rather than a one-line hash edit. Nothing here is execution authority. The A40/Pythia experiment remains **`NOT RUN`** — it has neither passed nor failed.
