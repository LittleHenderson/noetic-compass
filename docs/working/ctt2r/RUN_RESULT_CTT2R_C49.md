# CTT-2R, the acceptance-rule test on the c45 weights ("RULE FIRST"), job c49 (2026-10-19 Pacific): verdict `INSTRUMENT_ERROR`; status word `INCONCLUSIVE` (rule 1: Part R `NOT_EXERCISED`); Part K line `EARS_EARNED_KEEP` (reported only, never the word)

Status: REAL run. Every word below comes from a program, not from prose: `CTT2R_READING.json` (sha256
`002ac7fbaee2b1371219840304051c64e5b4afd69dc480f26d479c214667d59e`) was written by the frozen reader
`ctt2r/merge_2r.py` of the sealed zip `d97a16d6683b41037b51d028bcc4776be86ae1db66b117bd2af0126bab6159b6`, run on the
laptop (2026-10-20 14:09 PDT) through the package's own isolated launcher `contract/xrun.py` from the extract
`reading_pkg/HELM_CTT2R_20261019/` (34 of 34 freeze members re-hashed, 0 bad; freeze `7cccf18e…`), with the CTT v3 extract
beside it and the pinned reader v1.1 overlay (`reader_overlay/`, 174 files, tree `4ee67633…`). Merge input
`MERGE_INPUT_CTT2R.json` sha256 `42d8f01b9f073118d942cb4d3c9774086728b3c8ce9074fd9ae679b5c3de1c27`. Reader exit 0, empty stderr.
Reader stdout: `{"part_k_line": "EARS_EARNED_KEEP", "rule": 1, "verdict": "INSTRUMENT_ERROR", "word": "INCONCLUSIVE"}`.

**Said plainly first.**
- CTT-2R asked one question: if HELM's small translator (the "ear", 9,585,566 parameters, trained in job c45 and NOT
  retrained here) is only allowed to speak when all three of its trained copies give the identical checked reading, and
  then only as a question the user confirms, does the lift of c45 (§7.90) become a safe lift?
- The test had two halves. **Part R** (real public sentences that state stock and that the reader gives up on) could not
  be run: the custodian's census found **7** such sentences in the whole eligible frame, against a floor of **24**. The
  preregistration said in advance that this makes the whole reading `INCONCLUSIVE` by rule 1 🟧. That is what the frozen
  reader printed. **No status word is earned. The translator stays `ENGINEERED-NOT-VALIDATED`.**
- **Part K** (128 AI-written kitchen sentences, 32 of them traps, plus 16 AI-written dialogues of 60 turns) did run, and
  the reader prints its line beside the word, as the preregistration requires, **reported only**: every harm gate true;
  with the agreement rule the ear read **79** singles right against the reader's **63** (bar +8) and **40** dialogue turns
  right against **27** (bar +4), with **0** confident wrong proposals (the three copies without the rule made 0 / 5 / 5 on
  singles and 2 / 0 / 1 on dialogue turns); it beat the no-learning copy-closest rival held to the same rule (65) and the
  untrained copies under the rule (63). The line reads `EARS_EARNED_KEEP` 🟩 **for Part K alone**. By the preregistration's
  own words this line "never becomes the reading's word".
- Two negatives are kept. (1) The stock-dense real sentences the design wanted do not exist in the frame in that number
  (7 of 15,255; the same rarity USE-1 found, §7.94) 🟥. (2) Reader v1.1 itself read **5** of the 128 AI-written singles
  wrongly and **saved 3** of those wrong readings; the agreement rule runs only where the reader asks, so it cannot catch
  a reader error 🟥. The rule's own counts are clean: 0 wrong model or copy readings saved, 0 used without a yes.
- Result: **nothing moves.** No claim. Cost 0.22 USD. Machine gone, checked three ways.

## How we got here (governance)

- **Package:** `HELM_CTT2R_20261019_SOURCE_CTT2R.zip` sha256 `d97a16d6683b41037b51d028bcc4776be86ae1db66b117bd2af0126bab6159b6`
  (181,203 bytes, 35 members; inner `PACKAGE_FREEZE.json` `7cccf18eca4d1b656de9c4b9a5ef38a5d7301f9ad67d11ffd1de19e221c75382`;
  outside `PACKAGE_FREEZE_CTT2R.json` `26367200…`). Preregistration pre-code `23c0ae7c…`, final with amendment A-2R-1 `26843f32…`.
- **Owner's line** (verbatim, pinned 25 UTF-8 bytes, sha256 `0ed5828323f6fa100eb7287000ca454602ead9b1547bfc09d52862d5efa1a193`):
  `CTT RULE TEST at 1.50 USD` (`OWNER_APPROVALS_20261018.md`, "Owner words (2026-10-19 night, verbatim)"). Records:
  `APPROVAL_RECORD_CTT2R.md` / `.json`, written by the sealed program `ctt2r/approval_2r.py`: cap 1.50 USD, one attempt
  + one plumbing retry; seed source `c0230aa3e579536d03f9ba25d618c8dc61398963a30b986ea560f80284c1dc8c`.
- **Custodian (separate session, laptop, before launch):** census first (counts only; `CENSUS_R_CTT2R.json`): eligible frame
  15,255 sentences (two keys agree on 15,237); FACTS keys 29; **R1 = 7** (reader hands over on a FACTS sentence) against
  the floor of 24; R2 12,746; R3 139; R4 22; skipped as used elsewhere: X-REAL 128, CTT 135, RTR 140; forbidden text 11;
  builder-seen 3. **Part R `NOT_EXERCISED`** by the pre-registered STOP (amendment A-2R-1 item 4). The coordinator chose
  option (b), Part K only on this package, knowing the word would be `INCONCLUSIVE` by rule 1. New LLM-written pool
  (label `LLM_WRITTEN`): Gemini (asked gemini-3.5 / 3.7 / 3.8-flash, served 3.6 / 3.8-flash; 6 calls succeeded, 11 tries
  refused HTTP 503) and DeepSeek (asked deepseek-chat, served deepseek-flash; 6 succeeded, 1 HTTP 200 with malformed
  JSON, dropped); cleaned pool 249 units, 216 eligible after the 0-overlap gate (33 excluded). Custodian amendments
  CTT2R-A1 (retry spacing; the malformed DeepSeek reply redone in a new folder `k_pool_v2`) and CTT2R-A2 (one top-up
  writer call per short cell, 0-overlap eligibility gate, `k_pool_v3`; disclosed: the seed was derived at about 05:15 UTC,
  before A2, and is a fixed function of the owner line and the zip, so no new seed could be chosen). Drawn: 128 singles
  (32 traps) and 16 dialogues (60 turns); overlap on the drawn exam 0 on every rule; receiver check `all_pass: true`;
  sealed 2026-10-20T05:34:17Z (`CTT2R_SEALED_20261020T053417Z.json`). Bands KS 1,966 M, KD 1,968 M; R unused.
  Custodian spend: AWS 0; DeepSeek 9,377 in / 12,076 out tokens, about 0.016 USD at list; Gemini free tier.
- **Operator I-checks by program before the reader** (`OPERATOR_I_CHECKS_C49.json`, all 15 true): zip sha256; owner-line
  file = the 25 pinned bytes; seed source recomputed = approval record = seal record = derivation; approval and seal
  record both name this zip; `MANIFEST_CTT2R.json` `7d06d157…`; `KEYS_K_CTT2R.json` `abf0fd32…` = sealed record;
  carrier files `INPUTS_K_CTT2R.json` `5e57a87b…` + `SEAL_RECORD_CTT2R.json` `9d88a365…` = sealed record; seal record says
  Part R `NOT_EXERCISED`. Seal confirm after the run by the package's own program (`ctt2r.seal_2r confirm`):
  `SEAL_CONFIRM_CTT2R.json` `unchanged: true` (the three custodian-only files equal their seal hashes).
- **The operator never opened, printed or parsed an exam file, a key file or the decisions file.** Exam inputs went to the
  host by carrier (hashed, never read); keys stayed on the laptop; only the frozen reader read them.
- **Attempts:** ONE scored attempt; 0 plumbing retries used.
- **Laptop plumbing, recorded:** the closeout program's third cleanup check asserted that AWS still lists the instance as
  `terminated`; this check ran about 15 hours after termination and AWS no longer lists an instance that long after it
  ends (`instance: []`, ABSENT). One assertion was widened to accept ABSENT when the controller's own cleanup receipt
  recorded `terminated` ("User initiated") and the independent check read ABSENT (`closeout_c49.py`; original kept as
  `closeout_c49.py.orig`). No package, host or reading change.

## Job, machine, money

| Job | What | Instance | Launch / end (UTC) | Host s | Charge |
|---|---|---|---|---|---|
| c49 | scored host run, `kit/run_2r.py` `RAN_ALL_STAGES`, exit 0 (8 of 8 stages exit 0) | `i-01ee2ab9b0726fe85` g5.xlarge (NVIDIA A10G, 23,028 MiB), us-west-2b, `ami-0dddfa1ffa6b87af7` (Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.9, Ubuntu 24.04), 40 GiB gp3, no instance profile | 05:43:24 / 05:51:10 (terminated); controller cleanup 05:56:08 | 764.3 | 0.22 |

- **Source:** payload `c49-payload.zip` sha256 `cc2b4eb0142857aea4bd64a4fa1a1cbe182eabb602c483e74416b2c598f2006b` (the CTT2R
  zip; CTT v3 `f280633d…`; waves `b6598687` `a4f82556` `152bca2a` `31f97d67`; the spent wave carriers; the c45 weights
  carrier A4-s1 `db53775b…`, A4-s2 `16aebd0d…`, A4-s3 `76abf019…`, A5-s1 `525898b8…`, C1-s1 `e7028fe7…`, C2-s1 `d293039b…`,
  vocab `825b417a…`, train rows `d92a070b…`; the custodian's carrier; the approval record). Host manifest check: 34 members,
  0 bad. Builder `payload_c49/build_payload_c49.py`.
- **Purpose:** the CTT-2R scored run per `LAUNCH_BRIEF_CTT2R.md`: refusals, reader v1.1 overlay, preflight with a GPU
  smoke, two never-trained C2 initialisations from recorded seeds, decisions on Part K, NO-HARM OFF / OFF-removed / ON
  with ACCEPT-2, merge-input draft. No training. Raw data only; the verdict came from the frozen laptop reader.
- **Limits:** cap 1.50 USD; force cutoff 77 min, OS shutdown 83 min; job wall 90 min; preflight 10 min; `GPU_REQUIRED`;
  no automatic retry.
- **Transport:** own prefix `helm-ctt2r-c49-20261020/` via four presigned URLs; no instance profile, no SSM; the shared
  four-key prefix was never touched (lease `CLAUDE_CTT2R_C49_TRANSPORT_LEASE.json`).
- **Pacific time:** launched 10:43 PM, terminated 10:51 PM, 2026-10-19. Reading on the laptop 2:09 PM 2026-10-20.
- **Timing:** boot to torch found 05:45:30-05:48:23; `run_2r.py` 05:48:23-05:50:57 (154 s: overlay 0 s, unit tests 1 s,
  C2 inits 2 + 2 s, decide 58 s, NO-HARM 5 + 5 + 52 s); terminal record present at 05:51:06; deliverable 140,815,729 bytes
  sha256 `6598fc5b4c3609045afea7593e807f30a85a288ad7b5ba1640b02787379dfb37` downloaded and verified 05:51:13.
- **Tests on host:** `tests_2r` Ran 56, OK (skipped 6, host-only skips); GPU smoke of `serve2r.py` on A4-s1: 9,585,566
  parameters asserted, 3 proposals, audit clean (write-opens only `/dev/null` ×4 and one own temp file, A-CTT-2 rule),
  0 network calls, 0 process starts; static separation PASS; 0 pretrained-like files. C2-s2 and C2-s3 initialised from
  recorded seeds, 9,585,566 parameters each (C2-s2 final `ee42017e…`).
- **Charge:** **0.22 USD** (list price from host time, launch intent to controller cleanup: g5.xlarge 1.006 USD/h + root
  disk + public IPv4 = 0.215577 USD, rounded up to the cent; bill not posted). Cautious figure 0.27 USD (shown, not
  charged). Under the 1.50 USD cap; inside the brief's expected 0.35-0.60 because the host needed 13 minutes, not 20-35.
- **Ledger:** 112.99 before the hold; hold 1.50: 112.99 → 114.49 (`BUDGET_RESERVATION_CTT2R_C49.json` `785c3265…`,
  2026-10-20T05:42:59Z); closed 114.49 → **113.21** of 200.00 (unreserved 86.79) at 2026-10-20T21:12:19Z. Addendum
  `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_CTT2R_C49_20261020T211219Z.json` (`775c8dae…`); ledger after `a3d18eed…`. One
  HISTORY line each for hold and closeout. The hold stayed open about 15 hours because the previous session ended after
  the download and before the reading; nothing ran or cost money in that time (the machine was already gone).
- **Cleanup VERIFIED, three ways** (`CLEANUP_PROOF_CTT2R_C49.json` `72a35072…`):
  - controller at 05:56:08Z: instance `terminated` ("User initiated (2026-10-20 05:51:10 GMT)"), volume
    `vol-07e85be336aaf56f7` DELETED, own prefix purged (4 keys) and verified empty, 0 multipart uploads
    (`aws-c49-a1-cleanup.json` `92a76748…`, status `PRESERVED_AND_PREFIX_PURGE_VERIFIED`);
  - independent read-only check at 21:08:36Z (separate code path): instance ABSENT, no instance by tag or client token,
    volume ABSENT, no tag-discovered volumes, prefix empty, 0 multipart uploads → `VERIFIED`
    (`aws-c49-a1-independent-cleanup.json`);
  - direct read-only look at 21:08:39Z: no instance, no live project instance, no volume, no prefix version or delete
    marker, no multipart upload (`aws-c49-a1-direct-observation.json`).
  - No temporary role, profile or bucket created. The account-wide read-only look at 21:08Z (describe-instances,
    describe-volumes, us-west-2) listed no instance and no volume at all.
- Benign control note (as at c47 and c48): `InvalidInstanceID.NotFound` once, 0.1 s after launch, while AWS registered the instance.

## The reading

- **Verdict `INSTRUMENT_ERROR`, word `INCONCLUSIVE`, rule 1.** `instrument_problems`: `Part R NOT_EXERCISED (census R1 below 24)`.
  This is the pre-registered consequence (PREREGISTRATION_CTT2R.md §9 rule 1 and amendment A-2R-1 item 4), forecast by the
  builder at about 0.6 before any exam existed. **A word is licensed only with verdict `PASS`; none is.** Human pass K-H:
  `NOT_RUN (HUMAN_EXAM_ABSENT)`. Label `NAMED_CORPORA_ONLY (Part R) + LLM_WRITTEN (Part K)`.
- **Gates (all true, Part K):** H-CWFW (A4E 0 / 0, A2E 0 / 0), H-SAVED, H-USED, H-READBACK, H-WRITE, H-NOHARM, H-REMOVE,
  H-SEP, H-RT (0 used readings fail the round trip; well-formed 38/38, 43/43, 41/41 for the three copies), H-LEN (0 truncated).
  Instrument rows: H-VOTE, H-CUSTODY, H-NOFOREIGN true by the reader running to a word; I-REACH ok on both Part K parts
  (singles H 60 ≥ floor 16; dialogue H 33 ≥ floor 8).
- **Marks (Part K):** M-K1 ✅ (79 − 63 = +16 ≥ 8), M-K2 ✅ (79 − 65 = +14 ≥ 4), M-K3 ✅ (79 − 63 = +16 ≥ 8), M-K4 ✅ (40 − 27 = +13 ≥ 4).
  M-R1, M-R2: not evaluable (Part R `NOT_EXERCISED`).
- **Part K line** (printed beside the word, Part K only, `LLM_WRITTEN`): verdict `PASS`, rule 4, word **`EARS_EARNED_KEEP`**.
  Reported only; by the preregistration it never becomes the reading's word.

## Part K counts (128 singles, 60 dialogue turns in 16 dialogues; reader v1.1 first in every arm)

| Arm | What | Singles RIGHT / 128 | Singles CWFW | Singles offered → used with yes | Dialogue RIGHT / 60 | Dialogue CWFW | Dialogue offered → used |
|---|---|---|---|---|---|---|---|
| A0 | reader v1.1 alone | 63 | — | — | 27 | — | — |
| **A4E** | **reader + three-copy vote under ACCEPT-2 (the arm under test)** | **79** | **0** | 16 → 16 | **40** | **0** | 13 → 13 |
| A2E | reader + copy-closest under the same rule (mechanism-free baseline) | 65 | 0 | 2 → 2 | 28 | 0 | 1 → 1 |
| C2E | reader + three never-trained copies under the rule | 63 | 0 | 0 | 27 | 0 | 0 |
| A4-s1 as run | copy 1 alone, CTT-1 rule (no vote) | 84 | 0 | 21 → 21 | 42 | 2 | 17 → 15 |
| A4-s2 as run | copy 2 alone | 82 | **5** | 27 → 22 | 43 | 0 | 16 → 16 |
| A4-s3 as run | copy 3 alone | 79 | **5** | 25 → 20 | 42 | 1 | 16 → 15 |
| A5-s1 as run | twin (2,482,718 parameters) alone | 81 | 2 | 21 → 19 | 42 | 0 | 15 → 15 |
| A2 as run | copy-closest, no rule | 65 | 3 | 6 → 3 | 30 | 0 | 3 → 3 |
| A1 | retrieval-only control | 44 | 0 | — | 6 | 0 | — |
| C1-s1 as run | shuffled-label control, CTT-1 rule | 63 | 2 | 2 → 0 | 28 | 0 | 1 → 1 |

- In every arm the reader's own readings are the same: on singles **READER_WRONG 5, of which 3 were saved**
  (`READER_WRONG_saved 3`); on dialogue turns 0. These are the reader's errors, not the translator's; H-SAVED counts model
  and copy readings and is true. **Negative kept** (see below).
- Traps (32 singles; per family RIGHT, A0 = A2E = A4E): condition 3 right + 1 READER_WRONG (the reader's), negation scope
  5 / 5, number-not-stock 6 / 6, other person 6 / 6, past / future 6 / 6, reported or unsure 5 / 5. The vote added 0 trap errors.
- Of the 109 turns where the reader would ask (188 turns in all; 0 excluded for leakage; retrieval over 201,540 rows):
  A4E three copies agreed 29 times (= the 29 offers), two of three 13, one of three 5, none read 62. A2E: 3 / 2 / 12 / 92.
  C2E: 0 / 0 / 6 / 103. The rule gives up on 80 of the 109 ask-turns; where it speaks it was right 29 of 29 times here.
- Logs (reported only): alignment of A4 proposals ALIGNED 78, CONTEXT_ONLY 22, NOT_ALIGNED 11, NO_ITEMS 11; margin
  argmax-consistent 122 of 122. Diff classes of the as-run copies' wrong proposals: EXTRA_CLAUSE, MISSING_CLAUSE,
  WRONG_KIND, WRONG_POLARITY, WRONG_AMOUNT_BINDING, WRONG_NAME, WRONG_CONTEXT_REF (counts in the reading).

## NO-HARM (the brain's six spent wave exams)

| Exam | Items | Engaged | Offered by the hook | Applied | ON = this host's OFF |
|---|---|---|---|---|---|
| ENGLISH64_X3 | 64 | 37 | 12 | 0 | ✅ |
| ENGLISH64_X4 | 64 | 33 | 8 | 0 | ✅ |
| ENGLISH64_X5 | 64 | 34 | 6 | 0 | ✅ |
| FACES64_X3 | 64 | 32 | 13 | 0 | ✅ |
| FACES64_X4 | 64 | 32 | 18 | 0 | ✅ |
| FACES64_X5 | 64 | 32 | 14 | 0 | ✅ |

- `all_same_as_off: true`, `applied_total 0` (H-NOHARM, H-USED live part). OFF and OFF-with-`helm_cas_translator/`-deleted
  are byte-identical (`NOHARM_OFF.json` = `NOHARM_OFF_REMOVED.json`, sha256 `372f3c98…`; H-REMOVE). The three translator
  processes closed audit-clean after 200 calls each (H-WRITE).
- **Information only (amendment A-2R-1 item 1):** this host's OFF digests differ from c45's pinned OFF digests on all six
  exams (`this_off_equals_c45_off: false`), because receipt hashes carry the brain folder's path, which differs per host.
  The gate compares ON with the SAME host's OFF, as written before the seal.

## What this licenses, and what it does not

- **Licenses:** nothing. Verdict `INSTRUMENT_ERROR`, word `INCONCLUSIVE`. The translator's claim status stays
  `ENGINEERED-NOT-VALIDATED`. Part R: `VACUOUS` (`NOT_EXERCISED`). The licensed sentence of §13 of the preregistration
  may not be filled in.
- **Reported only, not a license:** the Part K line `EARS_EARNED_KEEP` on AI-written kitchen turns (label `LLM_WRITTEN`):
  singles 79 vs 63 (reader) vs 65 (copy-closest, same rule) vs 63 (untrained, same rule); dialogue turns 40 vs 27; 0
  confident wrong proposals under the rule against 0 / 5 / 5 and 2 / 0 / 1 without it; 0 wrong model readings saved;
  0 used without a yes; 0 trap errors added; NO-HARM 6 of 6.
- **Negatives kept:**
  - Part R could not be exercised: 7 stock-stating sentences the reader gives up on, in a frame of 15,255, against a floor
    of 24. The design's "48 real stock-dense sentences" do not exist in X-REAL's frame in that number. Not padded, not
    loosened; the pre-registered STOP fired. Same rarity as USE-1 (§7.94).
  - Reader v1.1 read 5 of 128 AI-written singles wrongly and saved 3 wrong readings (reader-first design: the vote never
    sees a turn the reader already read). On 128 real public sentences (RTR-1, §7.87) the same reader wrote 0 wrong facts;
    on AI-written kitchen English it did not. `FLAG_FOR_HUMAN_REVIEW`: a reader defect to diagnose on the spent exam by a
    builder or the custodian (the operator may not open the keys), as was done for K4 in wave 6.
  - The copies without the rule still make confident wrong proposals (singles 0 / 5 / 5, dialogue 2 / 0 / 1), as in c45.
  - The rule is silent on 80 of 109 ask-turns; its gain is bounded by how often three copies agree.
  - This host's OFF digests ≠ c45's OFF digests (explained, information only).
- **Never, by this run:** people typing to HELM (only a human-written exam, K-H, can carry that; `NOT_RUN`); English outside
  the 8 ingredients and 4 recipes; frames or Noetics; the translator without the vote; live use on the laptop; statistical
  superiority (one draw, one run); any retrained model; anything about Part R.
- **Prediction check (builder, not read by any program):** `INCONCLUSIVE` about 0.6 after the practice census — happened.
  Section 10 ranges for Part K: singles A4E − A0 +5 to +12 — observed **+16** (above the range); dialogues +2 to +6 —
  observed **+13** (above); A4E CWFW 0-2 — observed 0; A2E close to A0 — observed +2; C2E = A0 — observed equal; A4 as run
  more right and more confident-wrong than A4E — observed (84 / 82 / 79 right, 0 / 5 / 5 CWFW); NO-HARM identical — observed.
- **Open:** whether to widen the Part R frame (a new design: human-written stock sentences per the owner's USE-1 picks, or
  another source) so the primary word can ever be read; the reader's 5 wrong readings on AI-written singles; whether the
  owner wants a Part K-primary test designed and sealed (new owner word and cap).

## Files

Run folder `C:\Users\wakil\Documents\Codex\2026-10-19\ctt2r\run_c49_ctt2r_20261020\`: `CTT2R_READING.json` (+ `.sha256`),
`MERGE_INPUT_CTT2R.json`, `OPERATOR_I_CHECKS_C49.json`, `custody_confirm\SEAL_CONFIRM_CTT2R.json`, `fill_and_check_c49.py`
(+ logs), `reader.stdout.log` / `reader.stderr.log`, `a1_unpacked\c49_out\` (host `RUN_RECORD_CTT2R.json`,
`PREFLIGHT_CTT2R.json`, `DECISIONS_CTT2R.json` `de4286a0…` (never opened by the operator), `NOHARM_*.json`, `audits\`,
`weights\` C2-s2 / C2-s3, logs, `host_info.txt`, `nvidia_smi.txt`, `torch_info.txt`), `reading_pkg\` (fresh extracts of the
sealed CTT2R and CTT v3 zips), `reader_overlay\`, `payload_c49\` (`c49-payload.zip`, builder, result), `job_record\`
(controller, worker, receipts, events, console, deliverable zip `6598fc5b…`, cleanup proof, independent and direct checks,
closeout + `.orig`, ledger hold). Custodian folder `ctt2r\ctt2r_custody\` (exam and keys: never opened by the operator).
Repo copies: `docs/working/ctt2r/RUN_RESULT_CTT2R_C49.md`, `docs/working/ctt2r/CTT2R_READING_C49.json`,
`docs/working/ctt2r/OPERATOR_I_CHECKS_C49.json`. Backup `D:\tksCAS-archive\ctt2r_c49_20261020\` (three hash passes;
`BACKUP_MANIFEST_CTT2R_C49.json`).
