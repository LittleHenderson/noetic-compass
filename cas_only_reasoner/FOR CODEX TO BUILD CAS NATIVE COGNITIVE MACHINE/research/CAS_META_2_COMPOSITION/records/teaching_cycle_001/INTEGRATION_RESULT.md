# Seven-stage teaching integration: final preparation record

Status: CAS_TEACHING_V2_INTEGRATED_NOT_TRAINED.

The four-arm runner, persistent exposure/checkpoint journal, AWS-only worker,
blind prediction stage, public-input exporter and teacher-only scorer are
implemented. No new neural lessons or optimizer steps have been delivered.
This is not a learning result, release acceptance, or a claim of launch readiness.

## Source and checks

- Final source commit: c8c0e558cf30cd5fe06c2bf3d475697e97698a3e.
- Teaching integration commit: 4cb8dfe7933ffb7d630417385561c7e90fbdb216.
- Launch transport correction: 5163b76c (its full identity is in Git).
- Before these changes: 2a4791d6d0fddd04b23882248c679c03e0fbe92f.

Final guarded check: **352 passed, 1 warning**, 198.02 seconds. The receipt
reports exit 0, no timeout, and identical before/after file hashes.
[Raw output](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/checks_006/stdout.txt>),
[receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/checks_006/receipt.json>).

Launch-path regression: **417 passed, 1 warning, 24 subtests passed**,
72.41 seconds. It used fake AWS clients and blocked real provider/network,
neural and database execution.
[Raw output](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/condition_skill_v9_001/launch_repair_integrated_001/stdout.txt>).

The warning in each suite comes from deliberately constructing a duplicate
ZIP member for a rejection test. These checks prove covered code behavior,
not real CUDA learning, AWS readiness, correct native execution or retention.

The earlier checks_004 had 335 passing tests but detected source changes during
capture; it is NOT the frozen validation receipt. checks_005 had 338 passing
tests with unchanged files before the Windows build-check wrapper correction.
Both records are preserved. No failed/unstable capture is substituted for the
final 352-test receipt.

## Committed-source training bundle

[training.zip](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/bundle_002/training.zip>)
contains 17 files, 142,163 bytes compressed, with 256 training cases and 64
development cases. It was built exclusively from the final source commit's
Git blobs and the already pinned reference wheel.

- Archive SHA256: 494f44d467a85e2edd54b568cf4b0822db6e25355003a8a6ae8c7d4c09dd8cec.
- Manifest SHA256: 975296defc543e234d4bd09fcf9e46a25dc42792e4cf6aed5ad35332de3167a9.
- Worker source-map SHA256: 60340b5865c674cc5558a27da6524928ec0db7042163b1ef031591ad7794555e.

A fresh isolated process admitted the extracted bundle and loaded its worker
orchestration modules from that directory. All 13 worker source-file hashes
also match the tested repository files.
[Clean check](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/bundle_002/clean_check.json>).

The training bundle excludes the teacher generator, construction seed, all
final evaluation data and the scorer. CUDA model initialization and installed
wheel execution were not performed locally. The first wrapper attempt's
Windows working-directory failure remains documented in bundle_001; the
successful second attempt retains raw output and its command/cwd receipt.

## Inspect the actual lesson and run instructions

[Complete seven-stage lesson](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/lesson_v2_002/LESSON.md>)
shows every actual student text, shared observations, teacher-only target and
intended parameter-update path. Its solved demonstration answers BIND0;
its practice task requires BIND1. The student predicts a binding, not a prose
answer to the teaching questions. Guided ^6 here is textual decomposition,
not a native ^6 operation.

[Integration and commands](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/INTEGRATION_V2.md>)
describes all four arms and their boundaries. Each learner has a minimum of
1,024 complete guided blocks, with at least 4 per family, before readiness is
eligible. The full matched allocation is 4,096 blocks and 896 updates per arm.
Development alone chooses checkpoints and reduces assistance. Counts alone
do not mean understanding.

Final splits are 64 fresh instances, 64 unseen context combinations and 64
unseen tag combinations. None tests unfamiliar nested program combinations.
The scorer checks all 24 prediction artifacts and checkpoint byte chains
before opening private targets. Its float32 check calculates 32 selected bytes;
it does not observe the actual native call boundary.

## Budget and next action

[Machine-readable launch proposal](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/LAUNCH_PROPOSAL.json>):
at most **$8**, one g7.2xlarge / RTX PRO 4500, no T4, at most two instance hours.
The ledger remains revision 17, **$102 reserved and $298 unreserved** of the
$400 campaign cap. Reservations are not invoices. No reservation or paid job
was created for this integration. The failed v9 $4 is neither refunded nor reused.

Next: connect the new teaching-specific AWS parent/guest launch profile, with
public-data release after training, shared time/artifact limits and verified
shutdown/collection. Then perform the bounded teaching run and fresh-process
prediction checks. Current pricing, capacity, installed environment and live
IAM/schedule behavior remain unverified for that proposed job.

Actual native input-byte/output checks and retention after intervening
learning remain separate later phases. Synthetic restart tests and loading a
checkpoint are not evidence of retained neural skill. The learner's actual
exposure, checkpoint identities, per-arm token/time measurements and before/
after held-out correctness must come from the future run.

Accepted weights/executor and the frozen v9 training/data/protocol were not
edited. Historical familiar-program 24/24 and held-out composition CAS 0/72
remain separate, unchanged evidence. No language, general reasoning,
CAS-specific advantage or CNCM completion is claimed.
