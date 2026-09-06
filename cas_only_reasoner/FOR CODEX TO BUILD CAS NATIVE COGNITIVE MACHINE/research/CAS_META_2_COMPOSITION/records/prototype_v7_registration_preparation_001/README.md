# V7 registration preparation — not launch authority

The recovery packet has been collected, and its two timing records below match
the pinned packet bytes. The independent stored review has not yet supplied its
final status and hash. This note does not register v7 or authorize a launch.

## Pending registration changes

Root owns `EXPERIMENT_PROTOTYPE_V7.json` and the v7 `NATIVE_GATE_READY` constant.
The packaging agent owns the profile's `REGISTERED_SPEC`, literal prerequisite
review path/hash, and the plan's `launch_enabled` flag. Those switches remain
disabled until the independent review passes and root supplies its exact hash.

The future profile must reproduce the final registered specification exactly,
bind the review as an additional source input, and preserve the original 538
source inputs and 316 protected files. The source input count will move from
602 to 603; the generated launch manifest is an additional ZIP member.

The expected prerequisite identity is:

- Job: `cas-meta2-20260906082659-383a339d`.
- Source: `cbf13795202094865744f7c0b5efa234451f9208`.
- Recovery source manifest:
  `897c6a72c7411676c4ad80ac9734b3dbe7a7ac169951f58d2ab2fd6d387ecb37`.
- Collected packet:
  `4b5022d57c6d6f446463284dd79c7a9b3bf588754314b9110029a39827c6a57c`.
- Expected review path:
  `records/contrast_recovery_v6_review_001/run_001/recovery_stored_review.json`.
- Final review hash: **not yet supplied; no placeholder is launchable**.

The current-job GPU gate remains required even after registration. It must run
the v7 known-fixture pipeline, including one epoch, 22 steps per family, nine
native references and 45 candidate outcomes. A recovery review does not replace
this check. The original four META-1 GPU checks also remain required.

## Time and budget decision

Root selected these limits before source freeze, within the unchanged $7
reservation: GPU gate 450 seconds; dataset 180; training 3300; native 2700;
parent 6900; shared compute 7200; instance lifetime 7800. No automatic retry or
timeout extension is allowed. No reservation or provider action was made here.

The phase limits total 6630 seconds. The parent's 30-second shutdown allowance
leaves 6870 seconds, or 240 seconds beyond that phase sum. Before training, the
parent must still have at least 3300 + 2700 + 90 = 6090 seconds available.
At the maximum approved hourly estimate, 2.52 * 7800 / 3600 + 1.00 = $6.46,
below the $7 reservation. This is a conservative plan calculation, not an AWS
invoice or a provider-enforced account spending cap.

Measured recovery native time was 2221.573727747 seconds, with exit code 0.
The new 2700-second bound leaves 478.426272253 seconds above that measurement.
This is not proof that fresh v7 cases or different learned actions will fit.

The old v6 nine-case smoke took 203.235451228 seconds. The new 450-second bound
leaves 246.764548772 seconds above that older measurement. V7 adds 16 optimizer
steps per family, exact-original input assembly, and separate validation
children. The complete v7 smoke time is still unmeasured. The recovery GPU
process took 256.618320487 seconds, but it ran two different recovery tests; it
is not a v7 nine-case smoke measurement.

The unchanged 3300-second training configuration reserves its final 600 seconds
for prediction and completion, leaving an effective 2700-second training and
validation deadline. The previous complete v6 training wall was about 1953.51
seconds. Simple example-count scaling is only an estimate, not a measured v7
training time. No loss, optimizer, scoring, model, or executor behavior changed.

## Checks performed during preparation

PowerShell `Get-FileHash` matched the externally supplied packet SHA-256. A
read-only ZIP check hashed exactly the two process receipt members listed in
`timing.json`, then confirmed their extracted copies have identical bytes.
No model, checkpoint, private task, SQLite database, or provider was opened.

The following pure checks passed after the revised launch bounds:

```text
python -B -m pytest tests/test_prototype_v7_profile.py tests/test_prototype_v7_launcher.py tests/test_prototype_v7_remote.py -q -p no:cacheprovider -p cas_meta2.pytest_no_aliases_v4
CAS_PYTEST_ALIAS_SUPPRESSIONS=24
68 passed in 5.03s
```

The pure checks do not prove GPU speed, native task correctness, fresh data
generation, registration readiness, or a paid launch. The earlier logging fix
is preserved: one bounded public progress object, no private inputs.
