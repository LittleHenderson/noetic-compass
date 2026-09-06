# Byte-preserving checkout policy

This changes future checkout preparation, not the model, accepted hashes, or historical commits.

The new `research/.gitattributes` contains exactly 316 quoted, anchored literal-path rules from the unchanged META1 `BASELINE_MANIFEST.json`, each setting only `-text`. It covers source, schemas, tests, and evidence, not merely `records` folders. It sets neither `binary` nor `-diff`; readable text diffs retain their previous behavior. The other 287 files in the frozen v7 source package already have effective `-text` through the unchanged META1/META2 attributes. No broad repository rule was added.

The new research-level attributes file is outside the 316-file baseline and the 603-file v7 source package. The frozen META2 `.gitattributes`, accepted manifests, and all 603 source bytes are unchanged. Adding attributes does not repair files already converted in an existing checkout. Do not update accepted hashes to match such a checkout.

## Explicit pre-test gate

From `research/CAS_META_2_COMPOSITION`, run this **before** the functional suite. It requires the saved source archive and its Git objects; it does not install dependencies or run model/provider code.

```powershell
C:/Python314/python.exe -I -S -B records/hash_bound_checkout_policy_001/verify.py --before records/hash_bound_checkout_policy_001/before_001.json --output records/hash_bound_checkout_policy_001/checks_002.json
```

Use a new output filename for every rerun. Proceed to the unchanged functional-suite command only if this exits 0 and emits `CHECKOUT_POLICY_AND_MANIFEST_GATE_PASSED`. On mismatch, preserve the report/terminal error and restore a byte-faithful checkout from the pinned Git source; do not weaken the verifier or regenerate the manifest. This gate is pinned to source `42f9164754312f12850d9b8789c062fa7fb8069f` and its 603-file archive. It is not a claim that the historical commit contains these new attributes.

Before any policy assertions or tests, the gate checks the accepted manifest SHA256 `476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0`, all 316 baseline identities, and every one of the 603 source files against its exact Git blob, local bytes and frozen ZIP bytes. It repeats source checks at the end. It never parses current experiment outputs or loads checkpoints.

The policy checks then verify:

- Exact 316-path content, and effective `text: unset` for all 603 frozen inputs under `core.autocrlf=true`, `false`, and `input`.
- All seven inspected attributes unchanged for unrelated tracked research paths. Only `text` can change for the 316 named targets; their other attributes, including `diff` and `binary`, stay unchanged.
- Five pure path-format tests, including six unsafe-path rejection subtests.

## Retained proof

`before_001.json` was captured before the new research-level attributes file existed. Its SHA256 is `f816cd66437c350981d4dd34f79c55a759f0732715792f82c607bdd775941231`.

`checks_001.json` passed after the policy was added. Its SHA256 is `f62acc196c2927ec9b61514fb533b227555df1d49d545a4148371bd693b92ef5`. It records the verifier and attributes identities, tested settings, exact invocation, tracked-path count, and elapsed time. The five pure tests passed, including all six rejection subtests. The 603-file source gate and unrelated-attribute checks also passed.

These checks are read-only for Git and protected files. They write only a newly named JSON receipt in this record directory. No checkout/reset, normalization, staging, commit, neural execution, AWS call, training, or functional capability test was performed. Repository/user-specific conversion filters, encoding or `ident` rules are refused for the frozen files. A failing assertion exits nonzero; no successful receipt is written on failure.
