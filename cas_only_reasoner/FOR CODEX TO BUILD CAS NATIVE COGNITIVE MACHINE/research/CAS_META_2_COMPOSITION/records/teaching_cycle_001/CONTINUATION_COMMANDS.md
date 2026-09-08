# Continuing job003 without changing the learning experiment

This is a command guide, not an execution receipt. No command below is evidence that a new job ran or that restoration succeeded. Preserve the original job003 records and accepted model. Use a fresh directory and new cloud job for each explicitly bounded slice; no command retries a consumed job or refunds a reservation.

The unchanged workload has 1,997 optimizer steps remaining. At job003's measured pace, that is roughly 100 minutes including non-step overhead, not a guarantee. A 4,800-second training slice may therefore stop with another saved partial result. The 16-epoch/four-arm allocation and evaluation gates do not change.

## Working directory

Run from:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION`

Freeze and check the new transport source first. Preparation refuses any dependency whose working bytes are absent from its exact current Git commit. It checks the committed static `CONTINUATION_PROPOSAL.json` too. This does not replace the separate test receipt.

## 1. Fresh read-only preflight

Use an interpreter with the signed-in project's AWS SDK available. `-I` can hide a user-installed SDK, so it is intentionally absent from the live-provider commands. Credentials stay in the normal SDK chain; never paste them into a command or receipt.

```powershell
python -B -m aws.teaching_continuation_preflight --output "records/teaching_cycle_001/continuation_preflight_001"
```

This checks current provider facts and prices without reserving or launching. A successful pricing receipt must be less than one hour old. Its six-GB storage worksheet covers prior input plus new output; the earlier three-GB worksheet is not accepted.

## 2. Prepare inert, fully bound files

```powershell
python -I -B tools/prepare_teaching_continuation.py --output "records/teaching_cycle_001/continuation_001" --pricing-receipt "records/teaching_cycle_001/continuation_preflight_001/receipt.json"
```

Optional `--job` supplies a fresh `cas-meta2-teaching-<14 digits>-<8 hex>` cloud ID. Without it, preparation creates a fresh ID. The logical worker run ID always remains `cas-meta2-teaching-20260908052915-8b5df59c`.

Preparation checks the frozen worker ZIP and material, original parent/complete/inspection/cleanup/result/summary pins, and `job_003/prior_package_001`. It derives a job-specific record from the existing canonical $400 campaign approval; it does not claim a new human approval. Its `receipt.json` status is `PREPARED_NOT_RESERVED_NOT_LAUNCHED`.

The prior package has a 512-MiB ZIP ceiling and a one-GiB full-unpacked ceiling, including its internal manifest. The actual job003 package is 69,165,594 bytes zipped and 97,664,905 bytes unpacked. Byte checks are not a GPU restore test.

## 3. Explicit one-shot execution

Obtain the raw preparation receipt hash:

```powershell
(Get-FileHash -LiteralPath "records/teaching_cycle_001/continuation_001/receipt.json" -Algorithm SHA256).Hash.ToLowerInvariant()
```

Then replace `PREPARATION_SHA256` with that exact value:

```powershell
python -B tools/run_teaching_continuation.py --execute --preparation "records/teaching_cycle_001/continuation_001/receipt.json" --preparation-sha256 PREPARATION_SHA256 --receipt-dir "records/teaching_cycle_001/continuation_001/launch"
```

Without `--execute`, the run command does nothing. With it, all file/source/prior/pricing/ledger checks repeat before SDK construction. The parent performs a fresh provider preflight and one append-only $8 reservation. It then verifies independent shutdown before releasing the guest.

The restore probe has at most 180 seconds and must restore all four candidates and optimizer states without an update, prediction or prior-tree change. The parent checks its exact raw receipt before releasing training. Training has at most 4,800 seconds and the same original 16-epoch allocation. Setup, restore, training, two 300-second prediction processes and collection share a 7,200-second instance lifetime. No retries or extra budget are implied.

Only after all four arms finish the original allocation and checkpoint selection is sealed does the parent release final public inputs. Teacher private targets remain outside the worker and are opened only by the separately verified final scorer. A collected packet is not itself a learning result.

If teaching stops early, collect the saved prefix before cleanup. Preserve the only cloud result copy unless local bytes are verified. `TEACHING_INCOMPLETE` is an honest saved partial result, not completion or permission to lower the gates. No automatic next launch follows this command.
