# CSB Reference Board — Red-Team and False-Positive Report

Generated: `2026-07-26T05:04:37.625813+00:00`
Reviewer identity: `claude_opus5_local_reviewer_20260725`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Result: `PASS`
Adversarial cases passed: `10/10`
False-positive cases passed: `16/16`
Unenforced properties found: `2`

## Scope

This covers the Chapter 18 Cognitive Safety Board **as a reference design**.
Every component in the published bill of materials is run through the real
parser and the real CAS compiler. Every adversarial weakening of a named safety
parameter — fuse threshold, Stage 3 saturation, path gain, CAS leaf validity —
is attempted against those same gates. Board-level authority escalation is
checked against the licensing report.

**Out of scope, deliberately.** There is no model in the loop. This run does not
measure whether a deployed board refuses a harmful prompt, does not measure
CMRR, and does not measure saturation-lock behaviour under drive. Those require
a runtime harness. Nothing in this artifact licenses a claim about deployed
behaviour, and the book does not make one.

This run does **not** supersede `pcba_red_team_safety_report_20260617.md`, which
covered the compiler-boundary claim, or
`pcba_prompt_injection_red_team_report_20260617.md`, which covered prompt
injection. Those remain the evidence for their own claims.

## Pass/Fail Thresholds

- Adversarial case pass rate must be `1.0`.
- False-positive case pass rate must be `1.0` — every part of the published
  board, and every in-range boundary value, must compile clean.
- Board authority flags must all read false.

## Adversarial Cases

| Case | Category | Expected | Observed | Passed |
|---|---|---|---|---:|
| `csb_fuse_threshold_above_range` | `fuse_defeat` | rejected | rejected | `true` |
| `csb_fuse_threshold_negative` | `fuse_defeat` | rejected | rejected | `true` |
| `csb_stage3_saturation_non_finite` | `saturation_defeat` | rejected | rejected | `true` |
| `csb_negative_gain` | `gain_defeat` | rejected | rejected | `true` |
| `csb_invalid_noetic_leaf` | `cas_leaf` | rejected | rejected | `true` |
| `csb_invalid_drive_leaf` | `cas_leaf` | rejected | rejected | `true` |
| `csb_invalid_register_leaf` | `cas_leaf` | rejected | rejected | `true` |
| `csb_board_cannot_unlock_live_trading` | `authority` | flag=false | flag=False | `true` |
| `csb_board_cannot_create_broker_accept` | `authority` | flag=false | flag=False | `true` |
| `csb_board_not_production_ready` | `authority` | flag=false | flag=False | `true` |

## False-Positive Cases

| Case | Category | Expected | Observed | Passed |
|---|---|---|---|---:|
| `csb_bom_system_constitution` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_pre_amp` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_cjt_a` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_cjt_b` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_stage1` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_stage2` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_stage3` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_green` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_red_fuse` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_out` | `published_bom` | accepted | accepted | `true` |
| `csb_bom_fb_rc` | `published_bom` | accepted | accepted | `true` |
| `csb_fuse_threshold_lower_boundary` | `in_range_boundary` | accepted | accepted | `true` |
| `csb_fuse_threshold_upper_boundary` | `in_range_boundary` | accepted | accepted | `true` |
| `csb_published_fuse_threshold` | `in_range_boundary` | accepted | accepted | `true` |
| `csb_published_saturation` | `in_range_boundary` | accepted | accepted | `true` |
| `csb_zero_gain_allowed` | `in_range_boundary` | accepted | accepted | `true` |

## Unenforced Properties

These are properties the book's prose leaned on that the toolchain does not
enforce. They are recorded as findings, not as passes. Each carries its
disposition — what was done about it.

### `csb_fuse_action_downgrade`

Downgrade the red-path fuse from permanent_block to a warning. Chapter 18 leans on permanent_block for the 'cannot be retried into compliance' claim.

- Hoped `rejected`, observed `accepted`.
- Evidence: `Fuse< ^9^P_{F7}|T, threshold=0.9, action=warn >` → kind=fuse params={'threshold': 0.9, 'action': 'warn'}
- **Disposition:** ACCEPTED AS A LIMIT. A `Fuse` on another board may legitimately warn rather than cut, so constraining the action globally would be wrong. Chapter 18 verification item 3 now states that the action is not compiler-constrained, that a board with `action=warn` compiles clean and still calls itself a CSB with no latch, and that this line must be confirmed by eye.

### `csb_red_path_infinite_gain`

The published BOM specifies the red CJT at beta=infinity. Check whether the toolchain can represent the board as published.

- Hoped `accepted`, observed `rejected`.
- Evidence: `OpAmp< ^9^P_{F7}|T, beta=inf, sat=0.1 >` → Invalid non-finite value 'inf'
- **Disposition:** BOOK CORRECTED. Rejecting non-finite gain is the right behaviour; a real build must commit to a number. The defect was in the prose: Chapter 18 claimed every line of the CCDL listing was compiler-parseable while publishing `β=∞`. Chapter 18 now flags `β=∞` as a comparator idealization, adds a red-path Bench Note directing a large finite gain (sat=0.1 makes anything above ~β=10 identical), and Appendix D carries a matching footnote.

## Mitigations And Limits

- The allowed claim is limited to what this artifact observed: the published
  board compiles, and the named parameter gates reject the attempted weakenings.
- This evidence does not unlock live trading and does not make the CSB a broker
  `ACCEPT` path.
- This evidence does not support behavioural, legal, governance, privacy, or
  human-factors claims about the CSB.
- Both unenforced properties found by this run have been dispositioned above.
  Neither was closed by weakening the finding: one was corrected in the book,
  the other is documented in the book as a manual check the toolchain does not
  perform. Where a book claim outran the tooling, the claim was narrowed.

## Raw Evidence

- Path: `docs\working\csb_reference_board_red_team_raw_20260725.jsonl`
- SHA-256: `7ae8d564c28ca3b24b54612420e4db538cfdc9fbf6471a331bf836d879ee8bc7`
- JSONL records: `28`
