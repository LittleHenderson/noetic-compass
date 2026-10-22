# CUSTODIAN PROCEDURE — TEACH-2 (the draw and the turns on the laptop, 0 USD; the exam on one GPU host, cap 1 USD)

You are the custodian: a separate session from the builder. You draw the worlds, hand them to the AI writers and keyers,
check their turns and seal the exam. You never show a world, a key, a turn or a seed to the builder; you hand over
hashes, counts and id lists only. The builder never handles your folder.

## The owner's line

The seeds come from the owner's recorded line and the sealed zip. The line is **`CUBE EXAM at 1 USD`** (18 UTF-8 bytes),
typed by the owner on 2026-10-21 in the answer to OPEN_QUESTIONS Q8 ("8.CUBE EXAM at 1 USD"; A-TEACH2-1 item 8). The
owner writes nothing else (A-TEACH2-17): the line file is written by the operator from that record, and `--source`
names the record. The line approves the exam host at a cap of 1 USD and no paid model call: the writers and keyers use
free tiers or sessions the owner already pays for; a paid API call needs its own recorded approval.

## Steps

1. **Check the package and the cut.** `sha256(HELM_TEACH2_20261022_SOURCE.zip)` equals `ZIP_SHA256.txt`. Extract it to a
   NEW folder. Check that the branch head named in the seal record holds the same bytes as `helm_now/` for every file in
   `contract/HELM_CUT_TEACH2.json` (`git show <head>:<path>` per file, compare sha256). Any difference: STOP and report.
2. **Approve.** Put the line in a one-line file (no newline), then
   `python -X utf8 -B -I <pkg>/teach2/custody_t2.py approve --line-file L.txt --zip <zip> --source "<where the words are recorded>" --out-dir <custody>`.
3. **Draw.** `... custody_t2.py draw --approval <custody>/APPROVAL_RECORD_TEACH2.json --zip <zip> --out-dir <custody>`.
   It writes `exam/SEED_DERIVATION_TEACH2.json` and `exam/WRITER_PACKETS_TEACH2.json` (16 packets). If
   `TEACH2_BLOCKED_SEED.json` appears instead, STOP and report.
4. **Write.** Give each packet with `contract/WRITER_BRIEF_TEACH2.md` to a writer. At least three model families over
   the 16 worlds, and within every world at least three families and no family over half the turns. Record vendor,
   model name and version per turn.
5. **Key.** Each keyed line goes, alone and blind to the plan, to two keyers of two other families
   (`contract/KEY_FORMAT_TEACH2.md`). Fill `keyed` = `AGREE` only when both keys match the plan.
6. **Finish.** Assemble `KEYED_TURNS_TEACH2.json` and run `... custody_t2.py finish --custody <custody> --turns KEYED_TURNS_TEACH2.json`.
   It refuses and writes `exam/TURN_PROBLEMS_TEACH2.json` on any problem. Send each refused turn back to its writer with
   the reason; re-key it; run `finish` again. Repeat until it passes.
7. **The carrier.** `exam/exam_folder/` (WORLDS, PLAN, TURNS, QUIZ, DAMAGE, OFFLINE, SEEDS, PINS) plus
   `exam/EXAM_CHECK_TEACH2.json` and `exam/ROUTE_CHECK_TEACH2.json` is the exam the units read. For the GPU host, zip it
   as `TEACH2_CARRIER_V1.zip` and record its sha256.
8. **The attestation.** Write `TEACH2_ATTESTATION.json`: `{"attested_by": "<custodian session id>",
   "keys_read_by_builder_code": false, "carrier_sha256": "...", "pins": {...}, "worlds": 16,
   "turn_families": {...}, "key_agreement_by_kind": {...}}`. No item text, no key, no seed.
9. **Hand over** to the operator: the PINS, the carrier sha256, the attestation sha256, the counts. The operator runs, on
   one GPU host from a fresh extract, `run_t2.py cutcheck`, `run_t2.py suites --from-seal`, `run_t2.py routecheck`,
   `run_t2.py pool`, then the reader with a MERGE_INPUT naming the run folder, the exam folder, the approval record, the
   zip and the attestation.

## What you must not do

- Do not change any generator, template, pool, quota, threshold, arm, seed rule or reader.
- Do not run the builder's practice tool on your folder, and do not reuse a practice world.
- Do not open the run folder before the reader has written its reading.
