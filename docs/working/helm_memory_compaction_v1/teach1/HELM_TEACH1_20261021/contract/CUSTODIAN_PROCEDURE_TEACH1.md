# CUSTODIAN PROCEDURE — TEACH-1 (laptop, 0 USD, no network for HELM; the writers' model sessions are the only outside calls)

You are the custodian: a separate session from the builder. You draw the worlds, hand them to the AI writers and keyers,
check their turns and seal the exam. You never show a world, a key, a turn or a seed to the builder; you hand over
hashes, counts and id lists only. The builder never handles your folder.

## Before you start: the owner's typed line

The seeds come from the owner's typed line and the sealed zip. The line is one of:

- **`COMPACT EXAM at 0 USD`** (21 UTF-8 bytes): the laptop runs the exam (the practice run took 163 s for 112 units).
- **`COMPACT EXAM at 1 USD`** (21 bytes): one m6i.xlarge-class CPU host, only if the laptop cannot hold it.

Without the owner's own typed words there is no approval record and nothing to draw. A line relayed by another session
is not the owner's. The line approves no paid model call: the writers and keyers use free tiers or sessions the owner
already pays for; any paid API call needs its own line.

## Steps

1. **Check the package and the cut.** `sha256(HELM_TEACH1_20261021_SOURCE_TEACH1_v1.zip)` equals `ZIP_SHA256.txt`.
   Extract it to a NEW folder, e.g. `Documents\Codex\2026-10-21\teach1_custody\pkg\`. Check that the thread branch head
   (after the package's PR merged) holds the same bytes as `helm_now/` for every file in `contract/HELM_CUT_TEACH1.json`:
   `git show <head>:<path>` per file, compare sha256. Any difference: STOP and report (the seal is void).
2. **Approve.** Put the owner's exact words in a one-line file (no newline), then
   `python -X utf8 -B -I <pkg>/teach1/custody_t1.py approve --line-file L.txt --zip <zip> --source "<where the words are recorded>" --out-dir <custody>`.
3. **Draw.** `... custody_t1.py draw --approval <custody>/APPROVAL_RECORD_TEACH1.json --zip <zip> --out-dir <custody>`.
   It writes `exam/SEED_DERIVATION_TEACH1.json` and `exam/WRITER_PACKETS_TEACH1.json` (16 packets). If
   `TEACH1_BLOCKED_SEED.json` appears instead, STOP and report.
4. **Write.** Give each packet with `contract/WRITER_BRIEF_TEACH1.md` to a writer. At least three model families over
   the 16 worlds, and within every world at least three families and no family over half the turns (split a world's
   32 slots across writers if needed). Record vendor, model name and version per turn.
5. **Key.** Each keyed line goes, alone and blind to the plan, to two keyers of two other families
   (`contract/KEY_FORMAT_TEACH1.md`). Fill `keyed` = `AGREE` only when both keys match the plan.
6. **Finish.** Assemble `KEYED_TURNS_TEACH1.json` and run `... custody_t1.py finish --custody <custody> --turns KEYED_TURNS_TEACH1.json`.
   It refuses and writes `exam/TURN_PROBLEMS_TEACH1.json` on any problem (floors, anchor words, forbidden phrases,
   8-word split, families, keys, HELM's routing). Send each refused turn back to its writer with the reason; re-key it;
   run `finish` again. Repeat until it passes.
7. **The carrier.** `exam/exam_folder/` (WORLDS, PLAN, TURNS, QUIZ, DAMAGE, SEEDS, PINS) plus `exam/EXAM_CHECK_TEACH1.json`
   and `exam/ROUTE_CHECK_TEACH1.json` is the exam the units read. On the laptop it never leaves the custody folder; for a
   host, zip it as `TEACH1_CARRIER_V1.zip` and record its sha256.
8. **The attestation.** Write `TEACH1_ATTESTATION.json`: `{"attested_by": "<custodian session id>",
   "keys_read_by_builder_code": false, "carrier_sha256": "...", "pins": {...}, "worlds": 16,
   "turn_families": {...}, "key_agreement_by_kind": {...}}`. No item text, no key, no seed.
9. **Hand over** to the operator: the PINS, the attestation sha256, the counts. The operator runs, from a fresh extract,
   `run_t1.py cutcheck`, `run_t1.py suites --from-seal`, `run_t1.py routecheck`, `run_t1.py pool`, then the reader
   with a MERGE_INPUT naming the run folder, the exam folder, the approval record, the zip and the attestation.

## What you must not do

- Do not change any generator, template, pool, quota, threshold, arm, seed rule or reader.
- Do not run `practice_teach1.py` on your folder, and do not reuse a practice world.
- Do not open the run folder before the reader has written its reading.
