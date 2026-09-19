# Does a freshly built ^6 block reproduce the practice study's start weights?

**Question this answers.** The hand-off §3 and `CASFORMER_V0_2_MAP.md` claim that "the bank draws ^6 weights FIRST
from the seeded RNG, so **for the same seed the ^6 block starts from exactly the practice study's weights**".
`INTERFACE_SPEC_SHARED.md` could prove this only from source order and marked it `UNCERTAIN`, because it was never
executed. The checkpoint check depends on it: if the pointer machine does not start from the practice study's weights,
phase A's comparison and DG4's I3 have no referent.

**How it was measured.** `probe_framework_start.py` in this directory. It builds
`cncm.typed_matched_worker._framework(torch, "cuda", seed)` for each of the three model seeds and compares the result
against the practice study's own `receipt_<seed>/checkpoints/initial.pt`, using the learner's OWN identity algorithm
(`learner.state_identity`, `learner.py:47-61`) rather than an ad-hoc digest.

Dev-only check on the local RTX 4070. NOT claim-bearing. $0. No AWS call. No training, no claim-bearing evaluation.
The checkpoints are read read-only.

**Result — the premise holds numerically, but NOT bit-exactly off the AWS instance.**

| Seed | Algorithm sanity (checkpoint reproduces its own recorded identity) | Fresh build equals recorded start | Worst per-tensor abs difference |
|---|---|---|---|
| 20260917 | **true** | **false** | 7.450580596923828e-09 |
| 20260918 | **true** | **false** | 7.450580596923828e-09 |
| 20260919 | **true** | **false** | 7.450580596923828e-09 |

- **The sanity check passes**, so the measurement is sound: recomputing `state_identity` over the checkpoint's own
  `model_state` returns exactly the recorded `metadata.model_state_identity`
  (`91279389cfc22df46415dd56a26b1285fb3ef1ecd59e3aaccef553564528c12e` for seed 20260919). The comparison is therefore
  between like and like.
- **The key sets are identical** (`left.weight` 64x64, `merge.weight` 64x128, `right.weight` 64x64) and the framework
  module contains exactly those three tensors — the ^6 block is the whole module.
- **The weights differ only in the last bits.** The worst absolute difference across every tensor is
  **7.450580596923828e-09**, and the first element of `right.weight` is bit-identical
  (`0.11040803790092468` on both sides). So the fresh build draws the same weights, differing by float rounding.
- `state_identity` is a **byte-exact SHA-256 of the tensor bytes**, so a 7.45e-09 difference makes the identities
  differ even though the weights are numerically equal.

**Why the AWS run is unaffected.** The practice study's integrity check I3 compared its own freshly built start
against the matched study's recorded identity and **PASSED on the AWS instance** (`PRACTICE_STUDY_RESULT.md`;
I0-I4 PASS in all three seeds). So on the AWS instance — same AMI, same torch 2.11.0+cu128, same GPU — the build
IS bit-exact with the recorded start. The difference measured here is a property of this laptop's build path, not of
the claim.

**Consequences for the build — three concrete instructions.**

1. **DG4's I3 and smoke S5 cannot be run locally as written.** Do not add a local test that asserts the fresh ^6
   identity equals the practice study's recorded `model_state_identity`; it will fail for the wrong reason
   (7.45e-09, not a wrong seed). It is an **in-job check only**, on the AWS instance, exactly as the pipeline review
   DG4 already scopes it.
2. **Keep the two checks apart.** DG4(a) as the review worded it compares a *container* module's identity against the
   recorded value — that can never pass, because `model_state_identity` digests the whole `module.state_dict()`
   (`learner.py:111`, `:306`) and the pointer container holds far more than three tensors. The correct in-job check is
   to digest **the three ^6 tensors on their own**, then compare that against the recorded start.
3. **A local smoke may still check the reproducible parts, which this probe confirmed:** building `_framework` twice
   with the same seed gives identical weights (`REBUILD_IDENTICAL` true in an earlier run of this probe), and the three
   seeds are pairwise different. Those are safe local assertions.

**Claim state.** MEASURED on the local dev GPU, not claim-bearing: the ^6 start reproduces the practice study's
weights to within 7.450580596923828e-09 but not bit-exactly off the AWS instance. NOT measured here: the AWS-instance
bit-exactness, which is established by the practice study's own passing I3 rather than by this probe.

**Cost and time.** $0. Local RTX 4070, a few seconds per seed.
