# Second faithful continuation: running and auditing

This continues the same four candidate models. It does not change the neural
architecture, curriculum, seed, original 16-epoch allocation, checkpoint selection,
or final scoring method. The accepted model and executor remain unchanged.

## Current evidence

- First continuation evidence commit: `0615526605569fa4d5a5fbd5e24da27d04fffe83`.
- First continuation source: `a4b1af8519bd8def6e8cbb16f6d14ef72d99fa6b`.
- Frozen neural source: `c8c0e558cf30cd5fe06c2bf3d475697e97698a3e`.
- Saved updates: CAS aligned 784, CAS ordinary 784, generic aligned 784,
  generic ordinary 774; 458 updates remain.
- Local inspection exited 0. It verified 6,441 retained payload files /
  189,306,349 bytes, all four controller replays, no uncommitted tails, and
  unchanged earlier-history prefixes. It did not deserialize tensors.
- Inspection receipt: `continuation_001/continuation_inspection_002.json`,
  SHA-256 `e21c3ad7aa7cd2b2c278f5eff11a215ed4fb785beb16154d07413c7a1544d6db`.
- Cleanup receipt: `continuation_001/cleanup_recovery_002/result.json`,
  SHA-256 `4e49318d473776359a2c2097a180604e1d72e56aa1e4555569d7d6a3e06efc63`.
  Compute was confirmed absent; this is not a fresh termination receipt.
- Final scores are still unavailable. Partial development scores remain in
  `continuation_001/PARTIAL_TRAINING_REVIEW.md`; no CAS learning advantage is claimed.

Paths in this document are relative to this directory unless shown otherwise.
Commands below run from the CAS_META_2_COMPOSITION root:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION
```

## Artifact requirement

The evidence commit does not contain the 201,729,956-byte original result ZIP.
Full checkpoint inspection requires the retained local file:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/continuation_001/launch/partial_collected/artifacts.zip
```

Its SHA-256 is
`43795d51cdc1fba4c70b0d7c0cd27f4beaedbb7dbfbf1c89dc358946f069cd38`.
An authorized cloud copy was retained at bucket
`cas-meta2-teaching-20260908080138-5518e287-807562639912`,
key `results/artifacts.zip`, under a seven-day lifecycle policy.
The policy is not an exact deletion deadline or a permanent archive.
Do not claim a clone contains the checkpoints unless this external dependency
has been obtained and its bytes verified.

Original evidence contains absolute machine paths. The transport intentionally
preserves the original Linux campaign root and logical run identity; audit
relocation must not silently relabel those identities.

The exact paid preparation is machine/path-bound: the inspection records its
local campaign root, the package builder checks that complete inspection, and
the plan pins its digest. A relocated read-only audit may produce separately
labeled inspection and package receipts. It must not substitute those changed
receipts into this frozen paid request. Relocated paid preparation needs a
separately reviewed binding flow or the preserved exact paths.

The second prior-state ZIP is another external checkpoint dependency:
`continuation_001/prior_package_002/prior_state.zip`. The builder exited 0 after
repeating the full inspection and checking every package member. The original
source files retained their before/after hashes. Exact identities are:

- ZIP: 133,636,175 bytes, SHA-256
  `9998420eb409e1663ecce2dc38f1ab1883399382bca40f2bf47e0765a1cee855`.
- Adjacent `manifest.json`: 1,007,453 bytes, SHA-256
  `467bdea5daee1c28de7b0806eda3d98adbbd799f1fb835401d0ccd2949806752`.
- Adjacent `receipt.json`: SHA-256
  `024379be9d10fa41879f54c1037cd4492967deec776937a88b4896a7c37ef500`.
- Payload: 6,441 files / 189,306,349 bytes; expanded ZIP including its manifest:
  190,313,802 bytes.

The manifest and receipt are committed separately from the external ZIP.
Package verification is not an actual GPU/optimizer restore.

## Local checks and package preparation

Use Python 3.12 with `-I -B`. The inspection, packaging and guarded test tools
reject neural, database and provider imports. Do not run real neural work locally.

The completed inspection command was:

```powershell
& 'C:/Users/wakil/AppData/Local/Programs/Python/Python312/python.exe' -I -B tools/inspect_teaching_continuation_v2.py --parent-result records/teaching_cycle_001/continuation_001/launch/result.json --complete-marker records/teaching_cycle_001/continuation_001/launch/partial_collected/complete.json --archive records/teaching_cycle_001/continuation_001/launch/partial_collected/artifacts.zip --extracted-root records/teaching_cycle_001/continuation_001/evaluation_001/extracted --parent-sha256 ffb42912a72759a2c440571bcd929c397a8cc653b3d288d3a758221d52e4d86d --complete-sha256 aac9bfe609b3c9d04c0ad83f8fb209bcf7da12f1c79529e02c39b4f162db7d84 --archive-sha256 43795d51cdc1fba4c70b0d7c0cd27f4beaedbb7dbfbf1c89dc358946f069cd38 --evaluation-report records/teaching_cycle_001/continuation_001/evaluation_001/evaluation.json --evaluation-sha256 cd2d7cce4a3b75385d8f8348d6628b5edc43bcb18a10134f82f62567bc04ba05 --output records/teaching_cycle_001/continuation_001/continuation_inspection_002.json
```

The output is exclusive: do not overwrite that receipt. A reproduction needs a
fresh output path. The package builder likewise requires a fresh directory,
repeats the full frozen controller replay, copies from the pinned archive, and
validates every resulting member. It does not trust counts or a self-declared
report digest in place of replay.

The first combined check is retained in `continuation_002_integrated_checks_001`:
315 passed and one failed, with unchanged inputs. The positive 900-second test
had used a synthetic fault flag that marked the final receipt BLOCKED. The
checker correctly rejected that receipt. A fixture-only correction gave all
37 second-launch tests passing in `continuation_002_boundary_fixture_checks_001`.
The combined rerun passed all 316 tests in 286.12 seconds, with exit 0 and
identical before/after inputs. Its command, raw outputs and maps are in
`continuation_002_integrated_checks_002`. Its receipt SHA-256 is
`1fa4007d1ddbe193e186e8f1f5bb55f04605a1b0b8e6559315f0c96a64a23bc6`.
Fake tests do not prove that a GPU restore or learning result happened.

## Restore timing revision

The old GPU restore took 155.05006252200002 seconds for 1,587 saved updates.
The new state has 3,126 updates. The unchanged runner replays saved batches,
and the controller repeatedly scans the growing history. Code-based scaling
estimates are about 305 seconds (linear), 601 seconds (per-arm quadratic),
and 738 seconds (scan-dominated). These alternatives are not measured new
restore times or completion guarantees.
This timing finding does not explain CAS's low binding accuracy; that remains
a separate measured-behavior question for the diagnostic.

The initial 360-second proposal was therefore revised to a 900-second restore
allowance. The same shared 7,200-second lifetime, 4,800-second training maximum,
two 300-second prediction processes, $8 reservation and no-retry rule remain.
Remaining lifetime can shorten any individual allowance. No additional epochs
or optimizer updates are authorized by this timing change.

## Freeze, provider checks, and launch

Commit every source returned by
`aws.teaching_continuation_provider_v2.source_dependencies()`, the new tests,
and `CONTINUATION_002_PROPOSAL.json` before preparation. Preparation checks
working bytes against the exact Git HEAD; it does not accept uncommitted helpers.

After the package and software checks pass:

1. Run the read-only `aws.teaching_continuation_preflight_v2` module using
   the configured AWS profile and a fresh record directory. It checks the actual
   account, Blackwell instance description, conflicting jobs, quota and prices.
   Offering and quota checks are not proof that launch capacity is available.
2. Run `tools/prepare_teaching_continuation_v2.py` with that fresh pricing
   receipt and a fresh output directory. It checks the canonical ledger and
   prior identities; it creates no reservation and starts no job.
3. Use `tools/run_teaching_continuation_v2.py --execute` with the actual
   preparation path and digest. The parent checks live facts, reserves one
   bounded job under the existing $400 campaign approval, and requires an actual
   restore receipt before training. No automatic retry follows a failed job.
4. Only after all four candidates finish their original allocation may final
   public inputs be released. Two separate prediction processes must agree and
   pass admission before the frozen scorer reads private targets.
5. Evaluate using `tools/evaluate_teaching_continuation_v2.py` with the actual
   parent, completion-marker and archive digests, and a fresh output directory.
   It checks the scorer plus its five active helper files against frozen bytes.
   A partial run produces a partial report, not invented final scores.

Retain original results and failures. Bind new commands, environment, raw
outputs, package identities, source SHA and cleanup receipts separately after
execution. Do not merge automatically. The complete V01-V18 CAS/CNCM goal
remains open.
