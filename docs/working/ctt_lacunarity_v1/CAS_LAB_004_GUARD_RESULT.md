# CAS-LAB-004 — Reply-quality guard: steering is REJECTED as a repair (2026-10-24)

Status: **failed guard, preregistered condition.** Local GPU, weights frozen, diagnostic. This is the condition written
in `CAS_LAB_003_CONFIRMATION_RESULT.md` §5 before the run: *the composite must not fall by more than 0.02 in any seed.*

## 1. What ran

Seed A4-s1, 300 fixed exam items, frozen decoding (same lock, same per-item seeds, top-p 0.9). Baseline used the
unmodified model; steered injected the kNN direction (mean of the 10 nearest notation discovery rows' oracle
directions) at the last source position, scaled by the row's own memory norm. Identical decode otherwise.

## 2. Result

| Condition | Guard | Fact exact | Read-back | Composite |
|---|---:|---:|---:|---:|
| Baseline | 0.740000 | 0.740000 | 0.423333 | **0.231817** |
| Steered | 0.603333 | 0.603333 | 0.326667 | **0.118910** |

**Change: −0.112907** — five and a half times the 0.02 allowance, in the wrong direction, on every component at once.

Guard passes fell from 222 of 300 to 181 of 300. The replies got worse by every check the project uses.

## 3. Verdict

**Steering is rejected as a repair mechanism at this setting.** The notation-error gain it produces (44.8%–62.4% of
the oracle, confirmed across three seeds) does not transfer to the task the model is actually for; it damages it.

This is the third time in this programme that an internal improvement failed to survive contact with reply quality,
and it is consistent with the checkpoint result: held-out prediction and generated replies move in opposite
directions. It is now demonstrated for a steering intervention, not only for training length.

## 4. What was not tried (and is not claimed)

- No dose-response sweep. A much smaller injection might be harmless or even helpful, but testing that after seeing a
  failure is tuning on the outcome. If it is done, it must be preregistered: doses fixed in advance, guard as the
  primary outcome, three seeds.
- Seeds A4-s2 and A4-s3 were not run. The preregistered pass condition requires **no** seed to fall by more than 0.02;
  one decisive failure rejects the run. Running the other two would not change the verdict, only the size of the loss.
- The direction was transferred from notation rows to mouth items with no shared structure check. A different
  transfer (e.g. steering only within notation decoding) might behave differently, but that is a different claim.

## 5. What this means for the goal

The build asked three questions: can we label cells structurally, can we steer them, and does steering repair them.

1. **Labelling:** done — recipe ingredients and RPM chains, with unknowns explicit (`cas_label.py`, 700 rows).
2. **Steering:** done, and it works on the internal measure — the answer-free probe recovers 44.8%–62.4% of the
   gradient gain on unseen rows, 3 of 3 seeds.
3. **Repair:** **no.** The same steering costs 0.112907 of reply quality. It is not a repair.

The honest conclusion is that the internal control signal is real but misaligned with the task: moving the memory in
the direction that lowers notation error moves the replies away from the guarded, fact-exact, readable form the task
requires.

## 6. Claim status

| Statement | Status |
|---|---|
| The kNN probe captures 44.8%–62.4% of the oracle gain on notation error | `REAL` |
| The same steering lowers the reply composite from 0.231817 to 0.118910 | `REAL` |
| Steering is a usable repair for weak cells | `REJECTED` |
| Internal error gains transfer to reply quality | `FAILED` (this setting) |
| A small dose would be safe | `UNTESTED` — would need preregistration |

## 7. Artifacts

- `lacunarity_e1/gen_steer.py`; generation `cs_aws/guard/gen_A4-s1_{baseline,steered}.jsonl`;
  scores `cs_aws/guard_scored/A4-s1_*.scored.jsonl`.
- Spend: **0 USD**, local.
