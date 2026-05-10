# v1c + RPM Seed + RPM Repair Phase 1 + Phase 2 Semantic Verifier Audit

Source artifacts:

- `v1_eval_pack_24records_20260510T042914Z.md`
- `v1_eval_pack_24records_20260510T042914Z.jsonl`

Baseline:

- Phase 1 graded audit: `v1_eval_pack_24records_20260510T041621Z_CODEX_GRADED.md`

## Verdict

Phase 2 is a successful flag-only semantic verifier.

It does not change the human grade because it intentionally does not rewrite `final_text`. All 24 final outputs are byte-identical to the Phase 1 run.

Human-quality gate remains:

- Acceptable+: `16/24`
- Target: `>=18/24`
- Verdict: FAIL

Structural / diagnostic gate:

- RPM chain parsed: exactly records `19, 20, 21`
- RPM wrong-task hijack: still `0/3`
- RPM final edge match after Phase 1 repair: still `3/3`
- Phase 2 semantic drifts: present on all three RPM records
- Non-RPM final text changed: `0/21`
- Invalid explanation records touched: no

## Grade Counts

Unchanged from Phase 1:

| Band | Count | Records |
|---|---:|---|
| Green | 7 | 1, 2, 4, 6, 7, 23, 24 |
| High yellow | 2 | 17, 21 |
| Yellow | 7 | 5, 8, 9, 11, 19, 20, 22 |
| Wrong / flop / incoherent | 8 | 3, 10, 12, 13, 14, 15, 16, 18 |

Phase 2 adds diagnostic visibility, not grade movement.

## RPM Semantic Drift Findings

### Record 19

Source pattern:

`stageD3_3_0234 = ^9^P_{F3}`, `stageW3_3_0234 = ^9^C_{F3}`, `stageP3_3_0234 = ^9^E_{F3}`

Phase 2 correctly detects the same issue the manual audit called out:

- Expected noetic: `^9` / popped into mind / just clicked
- Rendered noetic evidence: `^4` / struck a chord, and `^5`-like shaped phrasing
- Expected drive: `F3` / vitality
- Rendered drive evidence: `F2` / wisdom and insight

This is the clearest evidence that Phase 2 is useful. It catches a real semantic swap that Phase 1 intentionally did not repair.

### Record 20

Source pattern:

`stageD2_2_0277 = ^5^P_{F2}`, `stageW2_2_0277 = ^5^C_{F2}`, `stageP2_2_0277 = ^5^E_{F2}`

Phase 2 detects:

- `stageD2_2_0277`: expected `^5`, rendered as `^2` style "speaks to you."
- `stageW2_2_0277`: expected `^5`, rendered as `^1` style "attention."
- `stageP2_2_0277`: expected `^5`, no matching `^5` evidence.

This matches the audit: identifiers and edge are repaired, but the internal noetic body still does not preserve "who one is shaped by experience."

### Record 21

Source pattern:

`stageD2_2_0287 = ^2^P_{F2}`, `stageW2_2_0287 = ^2^C_{F2}`, `stageP2_2_0287 = ^2^E_{F2}`

Phase 2 detects:

- `stageD2_2_0287`: domain marker for principled/foundational is missing, while the noetic/drive evidence is broadly present.
- `stageW2_2_0287`: expected `^2`, rendered as `^1` style cognitive attention.
- `stageP2_2_0287`: expected `^2`, no explicit `^2` evidence.

This supports the Phase 1 grade of high-yellow, not green. The overall chain is now structurally faithful, but stage-level semantic evidence is incomplete.

## Overclaim Guard

Do not say Phase 2 improved model output. It did not.

Correct claim:

> Phase 2 makes RPM semantic drift auditable and localizes the remaining errors by stage and axis.

Incorrect claim:

> Phase 2 improved RPM generations.

The generations are byte-identical to Phase 1.

## Recommendation

Keep Phase 2 flag-only for now.

Do not promote broad semantic rewriting yet. The verifier is accurate enough to trust as an audit signal, but automatic semantic substitution would risk turning RPM output into a deterministic template and could damage natural phrasing.

Next best move:

1. Use the Phase 2 drift logs to run a small targeted retry experiment on records 19-21 only.
2. The retry prompt should include the exact stage-level drift log:
   - stage variable
   - expected noetic/domain/drive
   - observed wrong evidence
3. Do not rewrite the model output by blind substitution yet.
4. Re-grade records 19-21 after retry.

Success condition for the targeted retry:

- Record 19 moves yellow -> high yellow or green.
- Record 20 moves yellow -> high yellow or green.
- Record 21 stays high yellow or moves green.
- No regression in stage identifiers or final edge.

If that works, use Phase 2 as the trigger for RPM-only corrective retry. If it fails, shift attention to the broader wrong-band records instead of overfitting RPM.
