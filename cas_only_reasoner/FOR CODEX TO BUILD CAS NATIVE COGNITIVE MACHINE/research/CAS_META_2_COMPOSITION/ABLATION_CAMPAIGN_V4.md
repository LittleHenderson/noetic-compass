# Retrospective comparison coordinator

The entry point is `python -B -m cas_meta2.ablation_campaign_v4`, with explicit
`--archive`, new `--output`, and `--job` arguments. The job environment must
contain matching `CAS_META2_AWS_JOB_ID` and `CAS_META2_RUN_DECODER_ABLATION=1`.
Linux/AWS CUDA is required; a T4 is refused. This coordinator does not launch AWS
instances, reserve spending, install dependencies, or authorize a release.

The parent performs these steps in order:

1. Check the pinned input artifact and protected baseline, then reconstruct and
   hash-check all five original dataset files in a separate child.
2. Capture the actual CUDA runtime identity in a child, then execute the two
   authored CUDA decoder-contract tests with the opt-in pytest alias-prevention
   plugin. Both tests must pass without skips.
3. Run the saved-checkpoint predictor in a new process group. The child has a
   900-second internal bound; the parent allows 930 seconds including setup and
   exit. It must exit successfully before any evaluation child starts.
4. Check both prediction seals, all 72 public-case mappings and five-arm coverage,
   and save the successful prediction-exit gate. A failed child cannot qualify
   merely because it left apparently complete prediction files.
5. Run each mode through the unchanged `campaign_v3.evaluate_sealed` and grouped
   reporting in its own child. Each receives a 2,400-second parent bound; it checks
   the prediction gate and the original dataset hashes before opening targets.
6. Recheck source/baseline identity and prediction seals, record 72 cases / 360
   arm verdicts per mode, and build the unchanged strict artifact index.

The parent has a 6,600-second work bound with a final-record reserve. Frozen
process helpers terminate the complete Linux child group on timeout or failure.
No automatic retry is performed. An independent paid-instance termination timer
is still required: Python checks cannot guarantee termination after a machine or
provider failure, and final evidence collection is not itself a provider timer.
If artifact indexing fails, the campaign receipt is marked incomplete and the
command fails; native results, if any, are retained without release acceptance.

## Evidence boundary

Local tests check the actual reconstructed dataset, seal rejection and parent
ordering with simulated subprocesses. Those simulations do not execute neural
models or prove AWS process cleanup. The full coordinator has not run on AWS.
The prediction stage still has no OS sandbox against arbitrary reads; the frozen
public-input reader and separate evaluation process supply the implemented data
boundary. This is not a new blind test set.

Before paid execution, supply the source-bound launcher, exact dependency and
GPU provisioning checks, bounded spending reservation, independent termination,
artifact-size/retention controls, and post-run verification of the complete
packet. Preserve all original failed v3 records and checkpoints. No CAS learning
advantage, new learned skill, or release acceptance follows from building this
coordinator or passing its local tests.
