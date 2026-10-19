# X5 — the fresh exam of HELM-R1 wave 5: what the custodian session must build and seal

Written 2026-10-19 by the wave-5 builder. The builder never sees X5 and derives no seed. A **separate custodian
session** builds X5 blind, checks it with the receiver's own checker, seals it, and hands over **hashes only**
(`X5_PINS.json`).

## 1. When, where, money

- Only **after** the owner signs the R1W5 line in `OWNER_SIGN_REQUEST_R1W5.md`. Its exact bytes are X5's seed source.
- Pure Python on the laptop: one process at a time, at least 300 MB free RAM, each command under 300 s, 0 USD, no
  network. No torch. No AWS.
- Use extracted copies of the SEALED zips: wave 5 (this package), wave 3b `a4f82556...`, wave 3 v3 `152bca2a...`, and
  the wave-1 v3 folder (`HELM_R1_W1_20261015_v3`, freeze `8c55c413...`). Run every command from the wave-5 package
  folder with `python -B`, with `R1W5_W3B_DIR`, `R1W5_W3_DIR`, `R1W5_W1_DIR` set to those folders (or pass
  `--w3b-dir --w3-dir --w1-dir`).
- The custodian must **not** run any arm on X5, open an exam file to read it, or print an item. Programs read the files;
  people read hashes and PASS/FAIL lines.

## 2. The four slots (file names fixed)

| Slot | File | Made by |
|---|---|---|
| `ENGLISH64_ITEMS` | `ENGLISH64_X5.json` | `r1w5.custody_x5 build` (wave 3b's sealed `r1w3b.gen64.build`, seed read from the derivation) |
| `FACES64_ITEMS` | `FACES64_X5.json` | the same |
| `X5PAIR_WORLDS` | `X5PAIR_WORLDS.json` | the same (`r1w5.gen_x5pair.generate` over RB-I3's World, 11 seeds read from the derivation) |
| `X5_SEAL_RECORD` | `X5_SEAL_RECORD.json` | `python -B -m r1w5.seal_x5` (step 6) |

Every seed is read by the program from `SEED_DERIVATION_X5.json` and passed straight to the sealed generators; nobody
reads, types or chooses a seed.

## 3. Seeds — from the owner's own words (`SEED_RULE_X5.md`)

1. Put the owner's R1W5 line, verbatim, into a file with no trailing newline.
2. Run (paths on the laptop):

   ```
   python -B -m r1w5.seed_rule_x5 --x0-pkg C:\Users\wakil\Documents\Codex\2026-10-15\r1_x0_custodian\HELM_R1_X0_FRESH_W1_20261015
     --derivation X0=C:\Users\wakil\Documents\Codex\2026-10-15\r1_x0_custodian\SEED_DERIVATION_FRESH_W1.json
     --derivation X1=C:\Users\wakil\Documents\Codex\2026-10-18\r1_wave2\x1_custody\work\SEED_DERIVATION_X1.json
     --derivation X2V1_ATTEMPT1=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody_v1_void\work\SEED_DERIVATION_X2_attempt1.json
     --derivation X2V1=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody_v1_void\work\SEED_DERIVATION_X2.json
     --derivation X2V2_PRE_TEXT_STEP=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody\work\SEED_DERIVATION_X2_pre_text_step.json
     --derivation X2V2=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody\work\SEED_DERIVATION_X2.json
     --derivation X3=C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3b\x3_custody\work\SEED_DERIVATION_X3.json
     --line-file <the file> --out SEED_DERIVATION_X5.json
   ```

   It refuses (exit 3) on a wrong derivation file, any overlap, a dead band, or a pair seed that collides. Nothing is
   generated before it prints `overlap_check: PASS`.

## 4. The three exam files

```
python -B -m r1w5.custody_x5 build --derivation SEED_DERIVATION_X5.json --out-dir <X5 folder>
```

It refuses unless the derivation says `PASS`, and prints the three files' sha256 only. The custodian writes no item by
hand. Every key is computed by a generator from the hidden truth and written rules, never by running HELM.

## 5. The receiver's check (must pass BEFORE the seal)

```
python -B -m r1w5.check_x5_format <X5 folder> --derivation SEED_DERIVATION_X5.json
  --extra-text-file C:\Users\wakil\Documents\Codex\2026-10-18\r1_wave2\x1_custody\exam\ENGLISH16_X1.json
  --extra-text-file C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody\exam\ENGLISH16_X2.json
  --extra-text-file C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3\x2_custody\exam\FACES16_X2.json
  --extra-text-file C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3b\x3_custody\exam\ENGLISH64_X3.json
  --extra-text-file C:\Users\wakil\Documents\Codex\2026-10-19\r1_wave3b\x3_custody\exam\FACES64_X3.json
  --out RECEIVER_CHECK_X5.json
```

The five extra files are SPENT exams, pinned by sha256 in the checker; the custodian lets the checker read them (the
overlap rule) and never opens them. It must print `all_pass: true`.

**Text step rule.** If the check reports a text-rule hit for `ENGLISH64_X5.json` or `FACES64_X5.json`, re-run the seed rule with
`--step-after E64=<the previous SEED_DERIVATION file>` (or `F64=...`) and a new `--out` file (it starts at the previous
chosen slot + 1, so nobody reads a slot), rebuild that file only (`custody_x5 build --only E64` with the new
derivation), re-check with the new derivation, and record every step in a `text_steps` list (`[{"part", "derivation_before_sha256", "derivation_after_sha256",
"text_rule_hits"}]`, hashes and counts only). No other change is ever made to a file.
`X5PAIR_WORLDS.json` has no text rule. On the builder's samples about one English-64 seed in six needed a step.

## 6. The seal

```
python -B -m r1w5.seal_x5 <X5 folder> --derivation SEED_DERIVATION_X5.json --receiver-check RECEIVER_CHECK_X5.json
  --line-file <the owner line file> [--text-steps <text_steps.json>]
```

It refuses unless the check passed and every file still has the hash the check saw, and the derivation comes from
this exact line. It writes `X5_SEAL_RECORD.json` (schema `helm.r1w5.x5-seal/1`: files, owner_seed_source, the full
derivation, the receiver check, text steps) and `X5_PINS.json` (schema `helm.r1w5.pins/1`, all four slots). Hand over
`X5_PINS.json` and its sha256. The coordinator ships the folder to the host as an X5 carrier (top folder `x5`), pinned
by sha256, never to the builder.
