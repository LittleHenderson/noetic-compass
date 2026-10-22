# X2 — the fresh exam of HELM-R1 wave 3: what the custodian session must build and seal

Written 2026-10-19 by the wave-3 builder. The builder never sees X2. A **separate custodian session** builds it, checks
it with the receiver's own checker, seals it, and hands over **hashes only** (`X2_PINS.json`).

## 1. When, where, money

- Only **after** the owner signs the R1W3 line. Its exact bytes are X2's seed source (section 3).
- The five carried parts are built exactly as X1 was built (custodian kit `Documents\Codex\2026-10-18\r1_wave2\
  x1_custody\generator\` = X0's sealed generator package + the `x1/` modules), with ONLY the X2 numbers of
  `SEED_RULE_X2.md` in place of X1's. The Gate B worlds need GB3's own torch `world()`: one blind AWS helper job
  (as c35a under amendment R1W2-A1.2: `m6i.xlarge`, us-west-2, the c21 image, helper cap 0.50 USD inside the wave cap;
  the operator ships files by path and verifies by sha256 only, never opens them). Everything else is pure Python on
  the laptop (one process, at least 300 MB free RAM) or on the same helper host.
- The four new parts are made by the generators SEALED IN THIS PACKAGE, unchanged (section 5).

## 2. The ten slots (file names fixed; the five carried names are wave 1's so its loaders read them unchanged)

| Slot | File | Made by |
|---|---|---|
| `GB_FRESH_WORLDS` | `GB_FRESH_W1.json` | X1's Gate B generator path (torch helper), X2 seeds |
| `TB_FRESH_WORLDS` | `TB_FRESH_W1.json` | `x1/taskb_x1.py` logic, X2 window |
| `CCE_PLANTED_ITEMS` | `CCE_PLANTED_W1.json` | `x1/gen_language_x1.py` logic, X2 language seed |
| `D34_FRESH_TASKB_D3` / `_D4` | `D34_FRESH_TaskB_d3.json` / `_d4.json` | `x1/gen_depth_x1.py` logic, X2 depth bases |
| `ENGLISH16_ITEMS` | `ENGLISH16_X2.json` | `python -B -m r1w3.gen_live --exam E16 --seed <E16_SEED> --out ...` |
| `FACES16_ITEMS` | `FACES16_X2.json` | `python -B -m r1w3.gen_live --exam F16 --seed <F16_SEED> --out ...` |
| `CASCADE_CHAINS` | `CASCADE_X2.json` | `python -B -m r1w3.gen_cascade --seed <CASC_SEED> --out ...` |
| `IDLE_SESSIONS` | `IDLE_X2.json` | `python -B -m r1w3.drive_w3 make --seed <IDLE_SEED> --out ...` |
| `X2_SEAL_RECORD` | `X2_SEAL_RECORD.json` | the custodian (section 6) |

## 3. Seeds — from the owner's own words, nobody picks them

1. Put the owner's R1W3 line, verbatim, into a file with no trailing newline. `H3 = sha256(its UTF-8 bytes)`.
2. Run `python -B -m r1w3.seed_rule_x2 --x0-pkg <X0 generator package> --x0-derivation <SEED_DERIVATION_FRESH_W1.json>
   --x1-derivation <SEED_DERIVATION_X1.json> --line-file <the file> --out SEED_DERIVATION_X2.json` (this package). It
   implements `SEED_RULE_X2.md` exactly and refuses (exit 3) on any overlap or a dead band. Nothing is generated before
   it prints `overlap_check: PASS`.
3. Text step rule (English-16 and Faces-16 only): if the receiver's check (section 6) reports a text-rule hit for a
   file, step that file's seed to the next slot in its band (`s <- s + 1`), regenerate, re-check, and record every step
   in the seal record. No other part is ever re-drawn.

## 4. The carried five parts

X1's formats exactly (they passed the receiver's check in c35): Gate B as wave 1's `custodian_contract`; Task B 20
draws with the c25 selection record and the label audit; CCE planted items with expectations under `expect`; depth
files with `y` a plain exact `"p/q"` string and `x` binary64 hexadecimal strings.

## 5. The four new parts (the custodian runs the sealed generators; it writes no item by hand)

- `ENGLISH16_X2.json` (schema `helm.r1w3.english16/1`): families G1-G7 (`r1w3/live_w3.py` `E16_FAMILIES`).
- `FACES16_X2.json` (schema `helm.r1w3.faces16/1`): families H1-H7 (`F16_FAMILIES`).
- `CASCADE_X2.json` (schema `helm.r1w3.cascade/1`): 64 chains, families C1-C8.
- `IDLE_X2.json` (schema `helm.r1w3.idle/1`): 16 idle sessions.
Keys are computed by the generators from the hidden truth, never by running HELM. The custodian must **not** run any
arm on X2 before sealing.

## 6. The seal

1. Receiver's check: `python -B -m r1w3.check_x2_format <X2 folder> --w1-dir <wave-1 v3> --extra-text-file
   <X1's ENGLISH16_X1.json>`. It must print `all_pass: true`. On a failure the custodian fixes its own generator path
   for the five carried parts (as X1) or steps the text seed (section 3.3); nobody converts a file afterwards.
2. `X2_SEAL_RECORD.json` (schema `helm.r1w3.x2-seal/1`): `files` {file: sha256} for all nine exam files;
   `owner_seed_source` {sha256: H3, verbatim}; `seed_rule_sha256` (SEED_RULE_X2.md); `derivation` = the full
   `SEED_DERIVATION_X2.json` content (its `parts.*.in_band`, `overlap_check`, `used_table`, `input_sha256` are read by
   the frozen reader, instrument I10); `derivation_sha256`; `receiver_check` = step 1's JSON; `text_steps` [...].
3. `X2_PINS.json` (schema `helm.r1w3.pins/1`, all ten slots, `owner_seed_source`). Hand over the pins and their
   sha256. Files go to the host by the coordinator (an X2 carrier zip pinned by sha256), never to the builder.
4. Depth (laptop, after the seal, by the coordinator): `python -B -m r1w3.d34_x2 drive --w2-dir <wave-2 package>
   --x2-dir <X2> --runs <r1_wave3>\d34_x2\runs --freeze-sha256 <wave-3 freeze>` then `... merge`.
