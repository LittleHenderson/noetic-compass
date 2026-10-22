# X3 — the fresh exam of HELM-R1 wave 3b: what the custodian session must build and seal

Written 2026-10-19 by the wave-3b builder. The builder never sees X3. A **separate custodian session** builds it,
checks it with the receiver's own checker, seals it, and hands over **hashes only** (`X3_PINS.json`).

## 1. When, where, money

- Only **after** the owner signs the R1W3b line. Its exact bytes are X3's seed source.
- Everything is pure Python on the laptop: one process at a time, at least 300 MB free RAM, 0 USD. No torch, no AWS
  helper job (X3 has no Gate B worlds).
- Use an extracted copy of the SEALED wave-3b zip and of the SEALED wave-3 v3 zip (`152bca2a...`). Run every command
  from the wave-3b package folder with `python -B`.

## 2. The three slots (file names fixed)

| Slot | File | Made by |
|---|---|---|
| `ENGLISH64_ITEMS` | `ENGLISH64_X3.json` | `python -B -m r1w3b.gen64 --exam E64 --seed <E64_SEED> --w3-dir <wave-3> --out ...` |
| `FACES64_ITEMS` | `FACES64_X3.json` | `python -B -m r1w3b.gen64 --exam F64 --seed <F64_SEED> --w3-dir <wave-3> --out ...` |
| `X3_SEAL_RECORD` | `X3_SEAL_RECORD.json` | the custodian (section 5) |

## 3. Seeds — from the owner's own words, nobody picks them

1. Put the owner's R1W3b line, verbatim, into a file with no trailing newline.
2. Run `python -B -m r1w3b.seed_rule_x3 --x0-pkg <X0 generator package> --derivation X0=<...> --derivation X1=<...>
   --derivation X2V1_ATTEMPT1=<...> --derivation X2V1=<...> --derivation X2V2_PRE_TEXT_STEP=<...>
   --derivation X2V2=<...> --line-file <the file> --out SEED_DERIVATION_X3.json` (paths in `SEED_RULE_X3.md`). It
   refuses (exit 3) on a wrong derivation file, any overlap or a dead band. Nothing is generated before it prints
   `overlap_check: PASS`.
3. Text step rule: if the receiver's check reports a text-rule hit for a file, step that file's seed (`--start-slot`),
   regenerate, re-check, and record every step. No other change is ever made to a file.

## 4. The two exam files

The custodian runs the sealed generator; it writes no item by hand. Keys are computed by the generator from the hidden
truth and the written rung rules, never by running HELM. The custodian must **not** run any arm on X3 before sealing.

## 5. The seal

1. Receiver's check: `python -B -m r1w3b.check_x3_format <X3 folder> --w3-dir <wave-3> --derivation
   SEED_DERIVATION_X3.json --extra-text-file <X1 ENGLISH16_X1.json> --extra-text-file <X2 ENGLISH16_X2.json>
   --extra-text-file <X2 FACES16_X2.json>` (the three extra files are pinned by sha256 in the checker). It must print
   `all_pass: true`. The custodian may read X2's files only as this checker reads them (the overlap rule).
2. `X3_SEAL_RECORD.json` (schema `helm.r1w3b.x3-seal/1`): `files` {file: sha256} for the two exam files;
   `owner_seed_source` {sha256, verbatim}; `seed_rule_sha256` (`SEED_RULE_X3.md`); `derivation` = the full
   `SEED_DERIVATION_X3.json` content (read by the frozen reader, instrument I10); `derivation_sha256`;
   `receiver_check` = step 1's JSON; `text_steps` [...].
3. `X3_PINS.json` (schema `helm.r1w3b.pins/1`, all three slots, `owner_seed_source` {sha256, verbatim}). Hand over the
   pins and their sha256. Files go to the host by the coordinator (an X3 carrier zip, top folder `x3`, pinned by
   sha256), never to the builder.
