# Gate 3 — freeze audit — 2026-08-21

Gate 3 is: **freeze the code, pin the exact commit, image, hardware, and receipts, and re-run the full test suites — runtime, canary, guardian, and hostile inputs.**

This is the audit **and the re-pin that followed it**. Read it in order: the audit found the freeze stale, the re-pin fixed it, and one claim in the audit turned out to be wrong and is corrected below rather than edited away.

**No gate was weakened.** `execution_authority` was not touched and the document is still inert in four separate places. **Final state: 488 passed, 0 failed across all four suites.**

---

## Test suite results — BEFORE the re-pin

| Suite | Result |
|---|---|
| Guardian runtime + core + timing harness + precreate | **355 passed, 0 failed** |
| C14 interpretability adapter (hostile inputs included) | **48 passed, 0 failed** |
| Open-weight canary v2 + trajectory runtime | **77 passed, 8 FAILED** — cause diagnosed below, fixed by the re-pin |

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

## CORRECTION — I was wrong about the two `None` bindings

**What I wrote in the first version of this audit:** that a complete re-pin must *"fill both `None` bindings"* — `required_source_commit_sha256` and `required_provider_launcher_source_sha256`.

**That was wrong, and doing it would have broken the document.** The canary validator enforces the opposite:

```python
if launch.get("execution_authority") == UNBOUND_EXECUTION_AUTHORITY:
    if launcher_sha256 is not None:
        raise ValueError("inert provider launcher hash must remain unbound")
```

While `execution_authority` is `NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN`, those two fields **must be `None`.** They are not unfilled gaps; they are enforced-null inertness markers. Filling them requires flipping `execution_authority` to `GO_FOR_ONE_ENGINEERING_CANARY_ONLY` — which **is** granting execution authority, and is an owner act, not an agent's.

So the correct re-pin was **narrower than I described**: one manifest hash, plus the self-hash that follows from it.

---

## The re-pin — DONE, 2026-08-21

**Two values changed. Nothing else.** The diff is two lines:

| Field | From | To |
|---|---|---|
| `required_source_file_manifest_sha256` | `7E496CB8A008C1AC37C7D6A09570FF90C1D97B4E55405E4AF4D5A965E644BC61` | `6EC46F9A42A52B6EE13F65EEEE81AB73889BD56B247F828393C84794A4227CCF` |
| `preregistration_sha256` | `07C8A4FA1007CA8B7DE0025F91865CF1EBDD81F9BB1B68E03BC648EBF37B55CF` | `30798FA6C04EA0B101161FB37A5D21518E05752B0017129DCAEBBC0F2CD1DDE7` |

A first attempt rewrote the file with `json.dumps(indent=2)` and produced an **83-insertion / 18-deletion** diff of pure reformatting around those two values. That was reverted and redone as a surgical text substitution. **A frozen document whose diff cannot be read at a glance is not reviewable, and an unreviewable diff on an execution-gating artifact is its own defect.**

**Invariants re-verified as unmoved after the re-pin:** `execution_authority` `NO_GO_UNTIL_EXACT_BINDINGS_ARE_FROZEN`; `provider_launcher_live_status` `NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE`; `required_source_commit_sha256` `None`; `required_provider_launcher_source_sha256` `None`; `required_oci_image_digest`; `required_image_name`; `required_cloud_type` `SECURE`; `required_interruptible` `False`; `required_volume_encrypted` `True`; `maximum_wall_seconds` `1800`; `maximum_spend_usd` the **string** `"0.50"` (a string, not a float, and it stayed one); `maximum_provider_create_attempts` `1`; `status` `FROZEN_DESIGN_ONLY_NO_EXECUTION_AUTHORITY`; `packet_eligibility` `NOT_PACKET_ELIGIBLE`; `scientific_status` `NOT_SCIENTIFIC_RESULT`. The individually pinned runner, watchdog, and supervisor hashes all still match.

**One test literal was updated:** `test_preregistration_is_exact_self_hashed_and_inert` hard-codes the frozen self-hash. It was re-pinned with a comment recording exactly why the value moved. **Every other assertion in that same test — the unbound execution authority, the `None` source commit, the OCI digest — was left untouched and still passes.**

### The acceptance test, and it was met

The criterion set **before** the re-pin was: the four blinded negative tests must go back to failing **for their own stated reasons**, not pass by accident. They did. All five previously-failing behaviour tests now pass on their own assertions:

`test_portable_verifier_rejects_cross_mismatched_watchdog_deadline`, `test_portable_verifier_rejects_github_arm_after_capture_start`, `test_tensor_tamper_and_result_overwrite_fail_closed`, `test_missing_downstream_effect_recomputes_fail`, `test_duplicate_execution_nonce_recomputes_fail`.

**Suites after the re-pin — 488 passed, 0 failed:**

| Suite | Before | After |
|---|---|---|
| Canary v2 + trajectory runtime | 77 passed, **8 failed** | **85 passed, 0 failed** |
| Guardian + core + timing + precreate | 355 passed, 0 failed | **355 passed, 0 failed** |
| C14 adapter incl. hostile inputs | 48 passed, 0 failed | **48 passed, 0 failed** |

## Standing

The freeze is now **current**: all 15 frozen files hash to what the preregistration expects, and the safety tests can prove what they were written to prove again.

**This is not execution authority and did not create any.** The document still declares itself inert in four separate places. `required_source_commit_sha256` and the provider launcher hash remain `None` **by enforcement**, and flipping `execution_authority` to `GO_FOR_ONE_ENGINEERING_CANARY_ONLY` remains an owner decision that nothing here anticipates. The A40/Pythia experiment remains **`NOT RUN`** — it has neither passed nor failed.
