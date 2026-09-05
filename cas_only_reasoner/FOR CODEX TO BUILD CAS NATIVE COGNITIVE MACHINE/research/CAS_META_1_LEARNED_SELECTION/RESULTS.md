# CAS-META-1 measured learning result

The GPU result, complete packet, all 72 references and 360 stored outcomes are
verified. AWS cleanup is closed. The original launch receipts retain their
temporary cleanup warnings; separate provider receipts confirm final closure.

CASformer improved from **8/72 (11.1%)** to **66/72 (91.7%)** correctly solved
held-out tasks. These scores require the actual executed input, published output,
workflow and repair state to match the checked reference. A valid trace alone
does not count. All 360 candidate executions produced valid evidence, but only
the correctly solved tasks count below.

| Selector | Correct tasks /72 | Procedure /72 | Input binding /72 | Correct repair-required tasks /24 | Reserved native policy units |
| --- | ---: | ---: | ---: | ---: | ---: |
| CAS untrained | 8 | 24 | 24 | 8 | 25,920 |
| CAS trained | 66 | 72 | 66 | 22 | 13,824 |
| Generic untrained | 8 | 24 | 24 | 8 | 25,920 |
| Generic trained | 61 | 71 | 61 | 21 | 14,040 |
| Simple rule | 72 | 72 | 72 | 24 | 13,824 |

The CAS improvement is 58 tasks, or 80.56 percentage points. Its six remaining
errors are input-binding errors, not procedure-selection errors. The generic
improvement is 53 tasks, or 73.61 percentage points. CAS solved five more tasks
than this generic candidate in this one run. That is not proof of a CAS-specific
advantage. The simple rule still performed best on this small structured task.

All selectors closed repair successfully on the 24 repair-required cases. The
repair-task column is stricter: it also requires the correct input and final
answer. For example, trained CAS closed all 24 repairs but solved 22 of those
tasks correctly. Untrained models often selected the long repair procedure for
tasks that did not need it; this is why their policy-unit totals are larger.

## What was held fixed

One seed; 864 training, 72 validation and 72 held-out tasks; three supported
procedures and three input slots. Formal instances and wording templates were
held out. Each model received only the problem and permitted observations.
Checkpoint selection used validation data. All five arms' test predictions were
sealed before test answers were opened. The recovery reused those predictions
without training, retuning, changing a case or dropping a result.

The accepted executor baseline is
`0917267b1354e5d036263eaa6ba9a7197eafb776`. All 316 protected source files and both
installed frozen wheels were checked before and after execution. Native weights,
permissions and the verifier were preserved. All 72 fresh Blackwell references
matched the original T4 reference output bytes exactly.

## Compute and checkpoints

Original training source: `a4dc9f2fc6f6d4f3d5e0b31100ac131327e02109`.
CAS has 24,302 active trainable parameters; generic has 24,278, a 24-parameter
difference (0.09876%). Both trained for 60 epochs and 840 optimizer steps.
CAS training took 57.839461555 seconds; generic took 13.099626616 seconds on AWS.
Validation selected CAS epoch 28 and generic epoch 55. The initial, selected and
last checkpoint bytes for both models remain in the original training packet.

Recovery source: `cfd22ab96c479703d09e0792a139901f2931f5bd`.
Recovery used one AWS `g7.2xlarge`, an NVIDIA RTX PRO 4500 Blackwell Server Edition
GPU, and eight physical CPU cores. Python 3.12.3, PyTorch 2.11.0+cu128, CUDA 12.8.
The CUDA hardware probe passed. All four GPU integration tests passed in 73.79
seconds. All 72 references plus 360 candidate executions completed in
**698.030042410 seconds (11 minutes 38 seconds)**, including recovery setup and
the fixed first-case profile. This is elapsed recovery time, not GPU kernel time.

Recorded candidate execution wall-time sums were 1,169.284 seconds for untrained
CAS, 559.188 trained CAS, 557.726 rule, 1,139.750 untrained generic and 569.490
trained generic. These run concurrently on one GPU and include CPU work; the
sums must not be treated as separate billed durations or added GPU kernel time.
Case zero's untrained CAS execution was profiled, which adds timing overhead.

The profile identifies the main bottleneck as CPU-side contract validation:
`validate_contract` accounted for 35.988 of the profiled 44.572 seconds. This is
one instrumented case, not a general speed benchmark. No validation checks were
removed or weakened. The full recovery succeeded by using faster hardware and
parallel case execution. No further T4 job was launched, and no neural work ran
on the laptop.

## Evidence identity

- Original packet SHA-256: `76fbb522a97e3018e946857ce71599fbdea8bb6daffd29bd15fb7cf2d091f7a0`.
- Recovery packet SHA-256: `b42598370145843182515afe202a2b340e14d9a248517b4e35d62bc4daaa541e`.
- Original sealed predictions SHA-256: `00e7a2b7d72c86d4dc9d7bdb3dd74f2c7338bb650b7e7e8136dfa6dd9ee09bc8`.
- CAS selected checkpoint SHA-256: `f6897996f796dfab8f3031bddef455a0280aae283fd86f0d8ea636ccb6ce625a`.
- Generic selected checkpoint SHA-256: `efb74c8b10eb747af45a3e001d57afb4f9c69bc68acfc9af37ebdd31cc4f7fa6`.

The complete recovery archive has 3,181 files and 593,408,720 expanded bytes,
with no omitted evidence. Both packets and all six checkpoint hashes were
checked without loading a checkpoint locally. Exact commands, runtime identity,
raw logs, profiles, SQLite records, trace schemas and source hashes are available
through `AUDIT_START_HERE.md`.

## Boundary

Two AWS attempts reserved $4 of the approved $100 task budget. That is a budget
reservation, not the final bill. The instance and scratch volume are gone and
job-owned access roles, profile, schedule and security group were removed. S3
evidence is retained with a verified seven-day expiry and is also saved locally.

This demonstrates one learned skill: selecting and binding existing CJT
procedures on held-out synthetic tasks, then solving those tasks through the
accepted runtime. It is not arbitrary program composition, complete Noetic
fractals, general reasoning, language-model capability, AGI or production
readiness. One seed and this small authored curriculum do not establish a
CAS-specific learning or reasoning advantage.
