# Controlled Helm repairs and complementary evidence â€” 2026-09-23

The original historical results are reproduced: **Helm1 PASS/PASS/PASS; Helm2 PASS/PASS/FAIL**.
The missing analogy focus comparison is implemented and has CPU effect/gradient evidence.
No new learned generalization claim, Helm release, training run or late-reach replay is made.

## Ownership and source
Codex is builder; Claude is independent checker and evaluation-design lead.
Read ../../_handoffs/HELM_NEXT_PHASE_20260923/COORDINATION_CODEX.md for accepted ownership, discovered concurrent work and targeted design questions.
Claude's pre-division rescorer is a reference implementation; its running jobs were not interrupted.
No sealed final evaluation inputs/answers were read.

- Implementation branch: codex/helm-integrated-repairs-20260923.
- Worktree: C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-integrated-repairs
- Baseline: a6e6f95bcae348775b910438109c9ed3842a5c19.
- Evaluation draft committed before model edits: fe15a8ef.
- Complementary review imported byte-for-byte: 26f1b46515c960a7aed6023f370df95d591ca36a.
- Historical Helm1 source: af0970cfa6d54a85aeb16e5a99a84d791ace59c0.
- Historical Helm2 source: 20208c923d41c24614504d4ecc2b289ecb66eda8.
- Historical Q4 source: d4c3fc7643201a83693ea9073c14ab42ecc5a570.
- Current owner authority: docs/OWNER_RUN_AUTHORIZATION_20260922.md and the current repair/coordination request. Agent records are not signatures.

INVESTIGATION_EVIDENCE_VERIFICATION.json verifies all 429 manifested research outputs:
145 Codex, 284 Claude (including 2 archive-only inputs). This verifies bytes, not every research experiment.
Both reports remain intact. There is no competing-verdict vote.

## Historical rescorer repair
trusted_rescore.py now uses exact Fraction arithmetic for the original paired rule:
b > c, one-sided Binomial(b+c,1/2) upper-tail p <= 1/100, gains in >= 2 kinds and >= 2 worlds,
and all seeds pass. There is no zero-loss veto.
Frozen-reading agreement checks each seed's counts, boolean pass, exact probability, kind/world identities and the seed set.
Future criteria are separately named HELM_TRANSFER_EVALUATION_DRAFT_20260923 in EVALUATION_DESIGN.md, never substituted into this historical rule.

| Historical version | Seed | Initialâ†’final /18 | Gains/losses | Exact p | Result |
|---|---:|---:|---:|---|---|
| Helm1 |20260917|2â†’12|10/0|1/1024|PASS|
| Helm1 |20260918|0â†’12|12/0|1/4096|PASS|
| Helm1 |20260919|0â†’11|11/0|1/2048|PASS|
| Helm2 |20260917|2â†’12|11/1|13/4096|PASS|
| Helm2 |20260918|0â†’12|12/0|1/4096|PASS|
| Helm2 |20260919|4â†’10|7/1|9/256|FAIL|

Acceptance: historical_population_recheck.json. It identity-checks all saved prediction files,
then checks 55 presentations per phase of all 18 original questions in each of 6 runs: 660 presentation checks,
88 unique private-checker calls and 572 reuses of byte-identical checker inputs.
It uses the corrected active tool's rule and agreement functions. It reproduces both original labels.
The exact population is taken from original gate keys and matched to unchanged anchors;
the expensive population selection/zero-learning-floor calculation was NOT rerun.

Limit: the full 564-record-per-phase rescorer CLI exceeded its 900-second CPU limit on the first study.
It produced no complete fresh RESCORE_OK receipt. The targeted acceptance above is not relabeled as that full run.
Original 0.2 anchors/readings remain unchanged, including the erroneous old seed17 pass field.
The repaired tool explicitly reports the old anchor's rule metadata beside the applied frozen-grader rule.
This is a disclosed historical compatibility choice; Claude's proposed strict 0.3-anchor policy remains a review difference.
No anchor is presented as independent custody.

## Analogy repair
An experimental analogy head compares the focus and each candidate's world/domain vectors,
their products and absolute differences, together with query and flags.
Other world-choice heads and the complete-assignment decoder retain their previous computation.
No checker, graph oracle or compiler answer is inserted into learned scores.

The diagnostic switch is _build_container(..., analogy_focus_comparison=False/True).
False preserves the old tensor layout/scoring path and accepts that layout with strict=True.
True is the default experimental descendant. New head initialization uses separate CPU RNG state,
seed 20260923; shared initial tensors and caller RNG state are bitwise unchanged.
The new checkpoint/profile schema prevents silent historical checkpoint loading as the repaired model.

Measured tensor count: 174303â†’203424 (+29121). All shared tensors retain their shapes and values;
the added head has five state tensors, with no reshaped old tensor. See analogy_tensor_inventory.json.
No historical trained checkpoint was migrated. A future migration/training arm needs an explicit job record.

The old source method has exactly 0 score change when only focus structure changes.
The repaired path changes candidate-relative scores at all 3 tested initialized seeds.
Gradients reach focus structure, focus domain and the new head. Domain-only intervention and public head dispatch pass.
The switch-off path matches old scores; other world-choice paths are unchanged.
This proves an information path, not correct answers or useful learned generalization.
Earlier effect tests showed a sub-1e-6 response in one initialization; the criterion now tests
nonzero dependency plus independent gradient evidence, not an unsupported minimum effect size.
All failure receipts are retained.

## Q4 remains a separate laboratory experiment
Existing original-checkpoint evidence, transparently reconciled in q4/README.md:
- Teaching fit: 0/128 exact, using all reconstructed consumed rows and retained RT1 results.
- New content on familiar operator/tree structures: 0/113, a derived subset of unused teaching-pool rows.
- New bare structures: 0/16 from original per-row development predictions; 15 size/depth matched, 1 unmatched.

The 113-row result is derived from RT1's uniform histogram, not invented original per-row records.
It is distinct from the newly prepared, stricter outside-teaching-pool content panel, which remains unrun.
The eight-row RT7 memorization and 256-row RT2 negative diagnostic are separate models/jobs.
They do not prove that longer training or a larger representation solves reconstruction.

The new evaluator freezes identities and three panels before inference. One selected attempt failed shell discovery.
After a tested fix and explicit new source-bound selection, the original GPU guard refused run 002 as GPU_BUSY.
Both stopped before model loading: zero new predictions, zero updates, no cloud/API/CPU fallback.
The failed guard did not preserve the exact utilization sample; the earlier 30% snapshot is not substituted for it.

After integration, direct CLI verification exposed an adjacent-module import failure in this longer Windows workspace. The evaluator now adds its own module directory explicitly and verifies that the executing runner itself is pinned. Three new identity tests pass; final Q4 tests are 38 passed. The frozen prepared manifest q4_input_manifest_003.json binds the repaired local runner. It was verified without neural execution and has NOT been selected for another GPU launch. The earlier 35-test helper receipt and its manifest remain tied to the helper commits, not to this later runner revision. The attempted cas-gpu pytest invocation also failed because that environment has no pytest; the final pure tests used C:/Python314/python.exe.

## Verification and limits
Final completed selected runs: 842 passed cases, 9 skipped, 62 test functions.
New: 823 passed cases / 37 functions. Existing: 19 passed + 9 skipped cases / 25 functions.
Four files completed selected runs; one older decoder file was additionally attempted and timed out in its large shared fixture.
TEST_ACCOUNTING.json has exact commands, XML fingerprints, per-case status and unloaded-file census.
Initial rescorer 2 failures, analogy 1 failure and Q4 fixture 1 failure are preserved and superseded by final receipts.
The decoder file's byte identity is tested, but its older broad regression attempt is NOT claimed green.
No existing compiler, PCBA, CAS-Ohm, atlas, grader, historical model or original receipt was edited.

## Next handoff and command
Claude independently checks this committed source, starting with the six-run table, effect tests and
the shared design review. No model tuning starts merely because wiring tests pass.
Before a claim-bearing learning job, resolve HSET's paired-test power assumptions, shape clustering,
comparator custody and unsupported five-node correspondence cell.
Late Helm reach (seed 20260919, pass 1, 0.003 vs 0.0003) remains a distinct unrun experiment.

The next safe command from this CNCM folder verifies the prepared Q4 inputs without model execution:

    C:/Python314/python.exe -B research/helm_cas_expression_lab/q4_panel_evaluation.py verify --manifest records/helm_integrated_repairs_20260923/q4_input_manifest_003.json --sha256 3fc2de03c7744d85558611627ff8e9e4f4c57784f5c4f09ef92de615e79eea86

The targeted historical reproduction command (use a new output location/copy; acceptance receipts are create-only) is:

    C:/Python314/python.exe -B records/helm_integrated_repairs_20260923/reproduce_historical_population.py "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001"

OUTPUT_MANIFEST.json supplies paths, raw/LF hashes and sizes for acceptance records.
Historical input identities remain in the two preserved investigations and their verified manifests.
