# X1 — the fresh exam of HELM-R1 wave 2: what the custodian session must build and seal

Written 2026-10-18 by the wave-2 builder. The builder never sees X1. A **separate custodian session** builds it,
checks it with the receiver's own checker, seals it, and hands over **hashes only** (`X1_PINS.json`).

## 1. When

Only **after** the owner signs the R1W2 line. The exact bytes of that line are X1's seed source (section 3).
X1 is part of the R1W2 wave and its money comes out of the wave cap (proposed 5 USD; the X1 job's own cap 0.50 USD,
the same as X0's).

## 2. Where

On AWS, like X0 (job c33: one `m6i.xlarge`, us-west-2, the c21 image, a 2-CPU slice). The Gate B worlds need GB3's
own torch `world()`; torch never runs on the laptop. The custodian's package is derived from X0's sealed package
(`Documents\Codex\2026-10-15\r1_x0_custodian\HELM_R1_X0_FRESH_W1_20261015_SOURCE.zip`, sha256
`0ee88a763bcde247f9f8f4df3fdac8932f5eb12cce25115184a544215facb26b`) with the changes in sections 3–5 only.

## 3. Seeds — from the owner's own words, nobody picks them

- Input: the exact UTF-8 bytes of the owner's R1W2 sign-line message as received. `H2 = sha256(bytes)`.
  The pins file records them: `"owner_seed_source": {"sha256": H2, "bytes_hex": "...", "verbatim": "..."}`.
- Rule: X0's `SEED_RULE_FRESH_W1.md` sections 1–4, word for word, with `H` replaced by `H2`; the same four cuts
  `k1..k4`, the same bands, the same overlap check and step rule.
- Used-region table: X0's table **plus X0's own blocks** (from `SEED_DERIVATION_FRESH_W1.json`, sha256
  `641b246a5db9eefc185191d62fbcae99065b38eb019dd6da536904cedab3f7f7`): its Gate B block, its Task B draws
  6550–6569 and its 60-draw window, its depth block, its language seed.
- English-16: `E16_SEED = 1,801,000,001 + (k4 mod 1,000,000)` (a band next to X0's language band, disjoint from it).

## 4. The seven files (names are the wave-1 contract's, so wave 1's loaders read them unchanged)

| Slot | File | Format |
|---|---|---|
| `GB_FRESH_WORLDS` | `GB_FRESH_W1.json` | wave-1 `FROZEN.precode.json` `custodian_contract` (sha256 `bbde22c7...`), exactly as X0 |
| `TB_FRESH_WORLDS` | `TB_FRESH_W1.json` | same contract (20 draws, the c25 selection record, the label audit) |
| `CCE_PLANTED_ITEMS` | `CCE_PLANTED_W1.json` | schema `helm.r1.cce_planted/1`; expectations under the key `expect` (X0 used `key`: refused) |
| `D34_FRESH_TASKB_D3` / `_D4` | `D34_FRESH_TaskB_d3.json` / `_d4.json` | `y` a plain exact `"p/q"` string; `x` binary64 hexadecimal strings (X0 used tagged objects and decimal floats: refused) |
| `ENGLISH16_ITEMS` | `ENGLISH16_X1.json` | schema `helm.r1w2.english16/1` (section 5) |
| `X1_SEAL_RECORD` | `X1_SEAL_RECORD.json` | schema `helm.r1w2.x1-seal/1` (section 6) |

## 5. English-16: sixteen plain-English turns

- Families and counts (frozen): `F1_STOCK_THEN_ASK` 4 (key ANSWER), `F2_ABSENT_THEN_ASK` 2 (ASK),
  `F3_QUESTION_FORMS` 3 (ANSWER), `F4_BAKE_A_BATCH` 2 (ANSWER), `F5_WITNESS_IN_ENGLISH` 2 (LEARN), `F6_MUST_ASK` 3 (ASK:
  approximate, what-if, negated or relative amounts).
- Item: `{"id", "family", "setup": [...], "turns": [...], "key": {...}}`. Setup steps are the loop's own channels and
  identical in every arm: `{"kind": "checked", "text": "There is 14 of Ω_Flour."}` or
  `{"kind": "witness", "product", "stock_before": {name: "p/q"}, "made": "p/q", "ran_out": name}`. Turns are plain
  English as a person would type it; **only the last turn is scored**.
- Names: the canonical brain's binding only (`helm_brain_canonical.DEFAULT_BINDING`: Flour, Water, Sugar, Butter, Milk,
  Egg, Yeast, Salt; Bread = Flour + Water, Frosting = Sugar + Butter, Starter = Milk + Egg + Yeast, Meringue = Sugar +
  Egg + Salt).
- Keys, computed by the custodian with exact fractions: a witnessed batch teaches `a[i] = x_i / made` for the
  ingredient that ran out first; `yield = min_i(stock_i / a_i)` over the recipe's ingredients; `limiting` = the
  argmin. **No ties** in an ANSWER item (a tie is the brain's gate G3: it would answer "can't tell"). Every
  witnessed batch must agree with the others (the brain refuses a contradiction).
- Wording: written by the custodian with `E16_SEED`; **never copy a sentence** from the packaged English tests
  (`helm/test_helm_*.py`) or the builder's fixture — the host checks exact overlap and requires 0 (instrument I1).
- The custodian may run the setup steps through the loop to confirm they are accepted; it must **not** run the scored
  turns through HELM before sealing.

## 6. The seal, and the check that X0 skipped

1. Run the **receiver's** check on the folder: `python -B -m r1w2.check_x1_format <folder> --w1-dir <wave-1 v3>`
   (from the sealed R1W2 package). It runs wave 1's own `r1/check_fresh_format.py` on the five wave-1-format files and
   the English-16 format check. It must print `all_pass: true`. If it fails, the custodian fixes **its own generator**
   and regenerates; nobody converts the files afterwards.
2. Write `X1_SEAL_RECORD.json`: `{"schema": "helm.r1w2.x1-seal/1", "files": {<file>: <sha256>} for all six exam
   files, "owner_seed_source": {...}, "seed_rule_sha256", "seed_derivation_sha256", "receiver_check": <the JSON of
   step 1>, "x0_overlap": {...}}`.
3. Write `X1_PINS.json` (schema `helm.r1w2.pins/1`, all seven slots, `owner_seed_source`). The custodian writes it;
   the coordinator only re-hashes it.
4. Hand over `X1_PINS.json` and its sha256. The files go to the host by the coordinator, never to the builder.
