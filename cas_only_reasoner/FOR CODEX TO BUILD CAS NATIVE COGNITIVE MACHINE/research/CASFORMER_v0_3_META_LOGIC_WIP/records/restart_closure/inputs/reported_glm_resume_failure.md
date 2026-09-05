# Preserved reported GLM audit narrative

Source task: Developing Reasoning Systems
Task ID: 6a888796-c678-83e8-a5cd-77473c2e038c
User message ID: ac83f915-816f-42b6-b56b-0ce919ff91a1
Retrieved through the task reader. This is the original supplied narrative, not an independently authenticated execution receipt. Original raw failing checkpoint/database/command/traceback were not supplied with it.

---

Now I can answer fully — and the resume leg, which I have now run myself, **does not pass**:

## What I ran with my own hands

| Check | My run |
|---|---|
| 247-test meta suite | ✅ **247 passed** (124s) |
| 5 manifest checks | ✅ **5 passed** |
| Demo `--output` leg | ✅ exit 0 — semantic fields reproduce the receipt **byte-identically** |
| Demo `--resume` leg | ❌ **fails** — and not for lack of the right arguments |

## The resume failures, exactly

1. First attempt: `--resume` with the **receipt's** recorded checkpoint digest → `MetaRuntimeError: CHECKPOINT_RECEIPT_MISMATCH`. That guard firing is correct behavior — but see finding 2.
2. **`checkpoint_digest` is not reproducible.** Three runs of the identical deterministic program: builder's `e6327439…`, my first `085689b6…`, my second `7bc1e468…` — different every time, even with the same output directory. The semantic digests (`program_digest` `274bd1df…`, `semantic_projection_digest` `00054db1…`, `model_digest` `fa4f90cc…`) are byte-identical across all runs; the checkpoint receipt digest is salted by something run-varying (timestamp/nonce). So a third party **cannot** use the receipt's `--expected-digest` value against their own checkpoint.
3. Self-consistent attempt: my own checkpoint + **its own** digest → passes the digest guard, then fails deeper: `MetaRuntimeError: NATIVE_HEAD_MISMATCH` at `_check_boundary()`, in a fresh process. That is the restart claim itself failing.

## What this means

The receipt records `fresh_process_restart: true`, and the 247-test suite passes (including `test_demo.py` — so the test-suite restart path works). But the **standalone CLI resume path as documented does not restart in a fresh process in my hands** — it dies at the native-head boundary check. Either the resume invocation I used is missing a required step that the documentation doesn't state, or there is a real ordering bug (boundary check running before the native head is restored).

So my audit status changes for that one item — from "not run by me" to "run by me, failed":

**`RESUME_LEG_FAILS_IN_FRESH_PROCESS`** — `NATIVE_HEAD_MISMATCH` on a self-consistent resume; the receipt's `fresh_process_restart: true` is **not verified by this audit**.
**`CHECKPOINT_DIGEST_NOT_REPRODUCIBLE`** — salted per-run; the receipt's `e6327439…` cannot be re-derived by a third party.

Everything else in my previous report stands exactly as verified. The two new items go to the builder, not to the frozen v0.2 release — this is the WIP meta layer, and its restart story needs either a corrected invocation or a corrected boundary check before `CAS_META_0` claims restart.
