# Build v2 record — HELM cube oscillation behind `HELM_CUBE_OSC` (default OFF), FIX FIRST, 0 USD (2026-10-21 PDT, laptop)

Owner's words (2026-10-21, verbatim): "1.A, 2.A, 3.A.(WE MAY NEED MORE THAN 3 ROUNDS SO JUST KEEP THAT IN MIND), 4.A,5.A
FOR TEST THEN C FOR REAL LIFE, 6.A,7.A, 8.CUBE EXAM at 1 USD"; then, offered a separate session for the build, "Do it here".

Claim state: **`ENGINEERED-NOT-VALIDATED`.** Built and unit-tested on the laptop. Nothing trained, nothing scored, no
exam drawn. The build specification was frozen before any code: A-TEACH2-2 (`ec3d65fc…`, commit `eb4c9520`) and
A-TEACH2-3 (`fdf912d2…`, commit `f19c66c4`).

## 1. What was built (commit `0cf970a0`)

| File | Change |
|---|---|
| `helm_cube_osc.py` | new: the rule reader (B2, with A-TEACH2-3's first-word rule); the proposer interface and a test-only `StandInProposer` (**not the CTT**, `is_ctt = False`); the round (unanimous proposal → brain-side check → plain say-back → re-read); keep after 2 agreeing rounds in ≤ 3; shadow rounds 4–6 reported, never stored; one cube per (thing, slot), corrections as new revisions with the history kept; the Atlas endpoint (`thing:<x>` CONTEXT, `cube:<id>:r<n>` POSSIBILITY, `fact:…` on confirmation); current-value answers (`EXACT` only while the person's line is fetchable); the fading ladder S0 → S1 → S2 every 4 turns with exact-fraction mass; arms OSC, ONE_READER, CTT_ONLY, TABLE, TABLE_OSC, ONE_STEP_FADE |
| `helm_memory.py` | the switch: `cube_osc` is `None` when OFF; a per-turn hook on the ON path only |
| `helm_chat.py` | the memory-recall branch asks the cube oscillator first, only when ON |
| `test_helm_cube_osc.py` | new, 38 tests |

## 2. FIX FIRST record (Python 3.14.0, pytest)

| Step | `test_helm_cube_osc.py` |
|---|---|
| (a) module absent | collection error |
| (b) module built | **1 failed, 36 passed**: the byte test (below) |
| (c) S2 record made lean; the byte test rewritten to pin the measured truth; the chat test added | **38 passed** |

Every HELM suite, both switches OFF, committed tree: **392 passed** (the 335 before + 38 new + 19 from the merged
EYE-ACT-1 work on the thread). With `HELM_CUBE_OSC=1` forced, the three memory suites: 76 passed, 1 failed, and that
failure is by design: `test_helm_memory_compact.py::test_off_path_is_todays_fifo` checks the OFF path of
compaction, but turning cube oscillation ON attaches the v1 compactor (the ladder's S1 is v1's capsule).

## 3. The measured finding: fading costs space on short lines (reported to the owner as a decision)

On a 72-line practice chat (lines 31–105 bytes), budget 6:

| Item | Bytes (median) |
|---|---|
| a person's line | **31** |
| an S1 capsule (v1's record: CAS sentence and notation, clues, binds, breadcrumb with the cold path, mass, receipt, Atlas address) | **813** (the breadcrumb alone 321) |
| an S2 record before D-BUILD-3 | 592 |
| an S2 record, lean (D-BUILD-3) | **363** |
| working memory at the end | **49,863**, against **2,238** for never forgetting |

In plain words, each faded memory carries its fingerprint, receipt and cold-copy address, so that HELM can prove a
memory was not changed. For short sentences that proof is many times bigger than the sentence. The design goal "to
save space" (owner item O5) is not met by this record format. The mark S-SPACE of TEACH-2 (≤ ½ of VERBATIM_ONLY's
bytes) would fail by a wide margin, and TEACH-1's compaction had the same property, unmeasured until now. Options for
the owner, none taken here: fade several lines together under one capsule, breadcrumb and receipt; shorten
fingerprints; count space differently. Each is a design change that needs the owner's word and an amendment before
TEACH-2 is sealed.

## 4. Build deviations (recorded, small)

- **D-BUILD-1.** "replaces X" is read as a replaced value, and "replaces" is a discourse word, so that B4's own
  say-back line ("… This replaces eight.") reads back to the same reading. Found by the round tests.
- **D-BUILD-2.** "one" is not a value number word (it is also a pronoun: "One more thing: …").
- **D-BUILD-3.** The S2 breadcrumb keeps the capsule id, the cold copy's sha256 and the turn ids; the cold path is
  rebuilt from the capsule id and the cold folder.
- **Not wired yet:** a refresh confirmation in the chat does not yet call `confirm` on the bound cubes (the function and
  its test exist); the real CTT adapter (with the retraining step).

## 5. Cost

0 USD. Laptop only. Nothing trained; no GPU; no host.

## 6. Rework onto the existing Cube Node Schema and cube store (A-TEACH2-4, commit `0897312a`)

Owner's words (2026-10-21, verbatim): "BRO THERE WAS ALREADY A CUBE NODE SYSTEM BUILT YOU NEED TO FIND THAT A BUILD BEFORE
YOU DO THIS TWICE SHIT"; "IT SUPPOSE TO HAVE A 6 ITEMS ON EACH SIDE ONE BEING ANALOGY OR METAPHOR THE EDGES ARE WHAT 2
NODES HAVE IN COMMON LOOK FOR THESE"; then "Yes: rework v2 onto the existing Cube Node Schema and cube store (things as
cubes, facts as branches with commonality, answers through the three operations, no second parser). Write it as an
amendment first, test-first, 0 USD."

What was found: `Cube_Node_Schema_v0.1.md` (`C:\Users\wakil\Downloads\`: one core, six faces — technical, context,
analogy or metaphor, mapping, decomposition, recomposition — branches with a `commonality` that names what two nodes
share, and the three operations), `SPEC_CUBE_STORE_UNIFIED_20261018.md` (one store, two producers, "no new parser", "no
schema fork"), and their code `docs/working/noetic_council/cube_store/`. The first v2 build had forked the schema (one
cube per fact, only face_1, its own layout), used no branches, carried a rule reader inside HELM and answered by its own
lookup. A-TEACH2-4 (`efe358ad…`) was written and committed before the rework.

| Step | `test_helm_cube_osc.py` (rewritten first) |
|---|---|
| old v2 code | **25 failed, 16 passed** |
| rework, first run | **5 failed**: a name value said back in lower case never re-read as a name (name facts could not agree); a thing the question names that is not in the fact did not rule the fact out |
| both fixed | **41 passed** |

Every HELM suite, both switches OFF: **395 passed**. The cube store's own suite: 21 of 21 (both copies). The change
to `operations.list_parts` is additive (latest branch per target and commonality kind; parts carry their commonality
and branch id); the pantry's kind-less branches behave as before. The nested copy
`cube_store/cube_store/operations.py` was not changed (it is not the one HELM imports).

Demo (stand-in reader, not the CTT): 5 of 5 facts kept as 5 thing cubes and 5 branches; "the buses on the Oxley line in
September" gives "You told me: Oxley, buses line, September: nine." (`LIST_PARTS`, the correction's value); what Oxley and
Eastwold have in common gives Moorcroft (`FIND_SHARED_PART`); Oxley to Moorcroft gives direct (`REACHED_VIA`).

Space, re-measured: working memory 53,370 bytes against 2,450 for never forgetting; the cube store adds 9,113 bytes for
5 things (each cube carries its six faces and their explanations). The space finding of section 3 stands and waits for
the owner's choice (batch fading, shorter fingerprints, or another way to count).

## 7. Size limit, widening batches and the cloud tier (A-TEACH2-5 `257a8145…`, A-TEACH2-6 `2c019244…`, commit `242a8d45`)

Owner's words (2026-10-21, verbatim): "how about if we keep every line and only start thee fade process once that reaches
53370? could that work what do you think?"; then "“yes, size limit plus batches” and to go even further add the technique
of once that becomes filled begin moving things to an aws server where if HELM has wifi he can reach it".

Both amendments were committed before any code. A-TEACH2-6 was written after measuring, before code, that a batch of 16
short lines (603 bytes) becomes a 794-byte capsule, so batches widen by 16 until they save space.

| What | Built |
|---|---|
| Keep every line | With a limit (live default 53,370 bytes) the turn budget no longer drops or compacts; the per-4-turn sweep is retired (the ladder path stays reachable with `limit_bytes=None`) |
| Batch fading | Past the limit, the oldest unprotected lines (never the last 2, never a line holding an unconfirmed fact) become ONE v1 capsule per batch: 16 lines, widened by 16 until the capsule is smaller than its lines; measured with a dry run that writes nothing; down to 90 % of the limit; `BATCH_NO_GAIN` / `OVER_LIMIT_PROTECTED` otherwise |
| Cloud tier | `helm_cold_cloud.py`: `FakeCloud` (tests, no network) and `S3Cloud` (the AWS command line tool, standard library only, SSE-S3, no ACL, no delete). When the device's cold folder passes its limit (live default 50 MB), the oldest originals are uploaded, read back, fingerprint-checked, and only then removed locally (`MOVED_TO_CLOUD` receipt); otherwise the local copy stays (`MOVE_FAILED`) |
| Fetching back | The device folder first, then the cloud; `EXACT` only when the bytes hash to the breadcrumb; a moved original that cannot be reached is `OFFLINE`, never `EXACT`, and HELM says "My full notes are stored away and I can't reach them right now" |

FIX FIRST (`test_helm_cube_tiers.py`, written first): (a) collection error, module absent; (b) cloud module only: 17
failed, 2 passed; (c) built: 2 failed, both the claim that memory stays under the limit (below); those two tests were
rewritten to pin the measured truth; 19 passed. `test_helm_cube_osc.py`'s helper now asks for the ladder path by name.
Every HELM suite, both switches OFF: **414 passed** (395 + 19).

**Measured negative 🟥: memory does not stay under the limit.** On 200 lines of about 60 bytes with a 4,000-byte limit,
each capsule (about 810 bytes: breadcrumb 251, CAS sentence 169, Atlas 89, clues 69, receipt 66, …) replaces about 900
bytes of lines, so a batch saves about 15 %; the capsules stay in working memory and pile up. Working memory ends at
**11,165 bytes**, against about 12,000 for keeping every line and a 4,000 limit. The cloud tier moves only the
verbatim originals (A-TEACH2-5 L5), which are not counted in working memory. In plain words: fading in batches
barely shrinks working memory, and the limit cannot be held forever this way. The design choices that would (move old
capsules off working memory too, keeping only a small index of clues; or a much smaller capsule) are the owner's.

**Live smoke test on AWS ✅ (2026-10-21 23:46 PDT; `CLOUD_SMOKE_20261021.json`).** Bucket
`helm-cold-memory-807562639912-usw2` (us-west-2) created by this build: all public access blocked, versioning on,
default encryption SSE-S3, tags purpose/owner/spec; nothing is ever deleted by code. Source: this commit's
`helm_cold_cloud.S3Cloud`; purpose: prove the move and fetch-back on the real bucket; instance: none (the laptop's AWS
command line tool, 20 seconds); data: synthetic lines only (`SYNTHETIC_ONLY`). 121 lines → 7 capsules; 7 originals
(52,178 bytes) moved under `smoke/20261022T064603Z/`, each read back and fingerprint-checked before the local copy was
removed; local cold folder 0 bytes after. Online: the first original came back `EXACT` ("The Oxley line ran eight buses
in September."), and the cube answer was `EXACT` "You told me: Oxley, buses line, September: eight." With the cloud made
unreachable: `OFFLINE`, and the answer `RECONSTRUCTED`, value eight, "My full notes are stored away and I can't reach
them right now, but my notes say: …". Cost: about 52 KB stored (≈ 0.000001 USD a month) and about 20 requests (≈
0.0001 USD); under 0.001 USD in all, inside the 200 USD ceiling. Cleanup: none by design (keep indefinitely; the owner
deletes); the smoke objects are 7 small synthetic files.

Gaps kept: client-side encryption with keys on the device (needs a crypto library outside HELM's standard-library rule);
sensitivity classes for real personal data (owner's word); the live switch attaches no cloud yet (`cloud=None` until the
owner says to point real conversations at the bucket).

## 8. The Eye runs a lean capsule (A-TEACH2-7 `58ef426e…`, commit `6ef29c83`)

Owner's words (2026-10-22, verbatim): "bro put the Eye in charge of this part that is causing or is an issue: 2.; Shrink
the capsule: don’t save what can be rebuilt. … A rebuilt capsule must match its receipt. Amendment first, test-first,
0 USD; measure bytes before and after."

The amendment was committed before any code (`c44c6e07`). The Eye is the same Eye as EYE-ACT-1 (`helm_eye_act.py`), with
a second watch, `CapsuleEye`, and the capsule list it runs, `LeanCapsules`. It runs only on the size-limit path.

| Eye step | What it does |
|---|---|
| ACT (shrink) | Stores a lean record: name, clues, Noetic digits, template version 1, fingerprint of the original, bound cubes, mass, receipt (plus the kind only for a "question" capsule, the original clue count only after strengthening added clues, and the line numbers only when they are not consecutive). It rebuilds the record at once and keeps it lean only if the rebuild is the same capsule and matches its receipt; otherwise the full capsule is kept (`LEAN_REFUSED`) |
| READ (rebuild) | Every use rebuilds the CAS sentence and notation (clues + digits, template 1), runs the compile and round-trip checks again (results remembered per exact text), rebuilds the cold-copy path, the line numbers (first and last id in the name), the Atlas thread (8 capsules per thread), node id, side and fact node, then checks the receipt |
| HOLD | A record whose rebuild does not match its receipt is never offered to recall, answers, fit checks or the cloud move; the Eye report flags `LEAN_REBUILD_MISMATCH` |

Receipt check: the compaction receipt is recomputed from the rebuilt capsule with the clues and mass as they were at
compaction; a strengthened capsule must also carry exactly the mass and clues of its latest STRENGTHEN receipt. A
change to any kept field (clue, digits, fingerprint, cubes, mass, receipt, template) makes the Eye hold the capsule
(tested field by field).

FIX FIRST (`test_helm_cube_lean.py`, written first): (a) 11 failed, 3 passed; (b) built: 3 failed — two were test
faults (a test spy also caught the size measurements, and the strengthening test expected a ninth clue under the cap
of 8), one was real (a changed mass was not caught; fixed by the STRENGTHEN receipt check); (c) 14 passed. Found by
reading, then tested: the strengthened capsule was written back before its STRENGTHEN receipt existed, so the Eye kept
it full; the write-back now follows the receipt and a test checks it stays lean. Two older tests pinned facts of full
capsules (batches of short lines widen; memory over the limit at 200 lines); both now run with full capsules (the Eye
off), so the old negative stays tested. Every HELM suite, both switches OFF: **429 passed**.

**Bytes before (full capsules) and after (the Eye's lean records), same chats** (`LEAN_BYTES_20261022.json`):

| Chat | One capsule (median) | Working memory | Keeping every line | Under the limit |
|---|---|---|---|---|
| 200 lines of ~60 bytes, limit 4,000 | 812 → **281** | 11,126 → **3,955** | 11,910 | 🟥 → ✅ |
| 2,000 lines of ~60 bytes, limit 53,370 | 828 → **280** | 110,746 → **48,745** | 120,294 | 🟥 → ✅ |
| 600 lines of ~60 bytes, limit 4,000 | 820 → **280** | 34,515 → **26,126** | 35,730 | 🟥 → 🟥 |
| 300 short lines of ~32 bytes, limit 3,000 | 874 → **282** | 8,948 → **7,202** | 9,474 | 🟥 → 🟥 |

(The 200-line "before" is 11,126 here against 11,165 in section 7 because the test lines gained a unique word.) The Eye
refused to shrink 0 capsules in all four runs.

**Measured negative kept 🟥:** a lean capsule still stays in working memory and costs about 3 bytes in 10 of the lines it
replaces, so capsules still pile up. The lean capsule moves the point where the limit breaks (about 3.4 times the limit
in lines of 60 bytes); it does not remove it. At the owner's 53,370 bytes that is roughly 3,000 lines of this length.
Holding the limit for ever still needs the other choice (old capsules leave working memory too, with a small clue
index), which is the owner's.

## 9. The Eye moves old capsules off working memory (A-TEACH2-8 `d5fbf746…`, commit `5523585b`)

Owner's words (2026-10-22, verbatim): "Yes: let the Eye move old capsules off working memory too (device folder, then
the cloud), keeping only a small index of clue words in working memory. Amendment first, test-first, 0 USD; measure
bytes before and after."

The amendment was committed before any code (`717edc58`). What was built (`helm_eye_act.LeanCapsules`,
`helm_memory_compact`, `helm_cube_osc`):

| Step | What happens |
|---|---|
| Move off | After the batch fading of a turn, if working memory is still over 90 % of the limit, the Eye moves the oldest capsules out: the record is written to `<cold folder>/<capsule name>.lean.json`, read back byte for byte, and only then replaced in working memory by an index row (name, clue words, first 16 characters of the receipt; the kind and line numbers only when needed). A failed write keeps the capsule (`MOVE_OFF_FAILED`) |
| Recall | Matches the question's words against the clue words of every capsule (in working memory or moved off) without fetching anything; only the matching capsule is fetched (device folder, then the cloud) |
| Check | A fetched record must carry the same name, the same clue words as its index row and a receipt beginning with the kept 16 characters, then pass the A-TEACH2-7 rebuild and receipt check; otherwise it is held (`LEAN_REBUILD_MISMATCH`), never answered from |
| Cloud | The device folder's limit counts the moved records too; past it, the oldest capsule's original (checked by its fingerprint) and its record (checked byte for byte) are uploaded and read back before either is removed locally; one `MOVED_TO_CLOUD` receipt names both keys |
| Out of reach | A capsule whose record is in the cloud that cannot be reached gives no answer: recall says "my full notes are stored away and I can't reach them right now"; a cube answer is RECONSTRUCTED, never EXACT |
| Strengthening | Brings a moved capsule back into working memory; its device copy of the record is removed (the cloud keeps its copy) |

FIX FIRST (`test_helm_cube_offload.py`, written first): 9 failed, 2 passed → 11 passed. Two older cloud tests in
`test_helm_cube_tiers.py` assumed every capsule stays in working memory and only originals go to the cloud; they now
find capsules by name and allow the Eye's records next to their originals (A-TEACH2-8 M4 amends A-TEACH2-5 L5; cubes
still never leave the device, still tested). A pinned negative test was added after measuring. Every HELM suite, both
switches OFF: **440 passed** (+1 pinned negative).

**Bytes before (lean capsules kept in working memory) and after (moved off, index only)** (`OFFLOAD_BYTES_20261022.json`):

| Chat | Working memory before → after | Capsules moved off | Under the limit | Time |
|---|---|---|---|---|
| 200 lines, limit 4,000 | 3,943 → 3,943 | 0 (not needed) | ✅ → ✅ | 0.3 s |
| 2,000 lines, limit 53,370 | 48,640 → 48,640 | 0 (not needed) | ✅ → ✅ | 3.8 s |
| 300 short lines, limit 3,000 | 7,145 → **2,830** | 21 | 🟥 → ✅ | 0.8 s |
| 600 lines, limit 4,000 | 26,034 → **10,870** | 83 | 🟥 → 🟥 | 3.6 s |
| 3,000 lines, limit 4,000 | 159,034 → **72,222** | 563 | 🟥 → 🟥 | 30.3 s |

One index row is about 129 bytes (median 127–131) against about 281 for a lean record.

**Measured negatives kept 🟥:**
1. The index also grows with the chat: about 129 bytes per capsule stay in working memory, so a long chat at a small
   limit still goes over (600 lines at 4,000: 10,870 bytes). The limit breaks later again, not never. At the owner's
   53,370 bytes and 16-line capsules of 60-byte lines, the index alone fills the limit after roughly 6,600 lines.
2. Once working memory stays over the limit, each turn fades whatever short run of lines it can, so capsules get small
   (600 lines made 83 capsules where 16-line batches would make about 37), and each small capsule adds its own index
   row. In plain words: when memory is permanently full, the folding gets less efficient.
Holding the limit for ever would need the index itself to fold (for example, many old index rows merged into one row
per thread of conversation), which is the owner's choice.

## 10. The Eye folds old index rows together, row upon row (A-TEACH2-9 `22364836…`, commit `6e9c9a56`)

Owner's words (2026-10-22, verbatim): "Yes: let the Eye fold old index rows together (for example, one row per thread
of conversation, holding the clue words of its capsules), so working memory can stay under the limit for good.
Amendment first, test-first, 0 USD; measure bytes before and after."

The amendment was committed before any code (`5f9dcc49`). It says plainly that one row per thread alone only slows the
growth, so the folding repeats: 8 index rows → one level-1 row (one thread of 8 capsules), 8 level-k rows → one
level-(k+1) row. A folded row keeps at most 48 clue words (the words in the most capsules; ties the newest), its
first and last line number, and 16 characters of its fold record's sha256. The folded rows go to
`<cold folder>/<fold>.fold.json`, read back byte for byte before they leave working memory; past the device limit
they go to the cloud like the other files.

Finding a folded memory: recall matches the rows in working memory, opens only the folded rows whose words hold every
question word, and, if nothing matched, does a DEEP SEARCH of the fold records on the device (read from disk, not kept
in working memory) for words past the cap. Every record read back is checked; a mismatch is held. A cube answer finds
a folded capsule by its line number. Strengthening brings a folded capsule back.

FIX FIRST (`test_helm_cube_fold.py`, written first): 10 failed, 1 passed → 9 passed, 2 failed → 12 passed. The two
failures were test faults: the reachability test sampled fixed line numbers instead of the first line of each batch
(the amendment's measure), and the cloud test's device limit was so large that fold records never needed to move.
Found on the way, a **test-data fault**: the made-up unique word per line (`plotaa`, `plotab`, …) ran out of letters
after line 676 (`chr(123)` is `{`), so every later line's word read as `plot`; fixed in `test_helm_cube_tiers.plot`
(lines below 676 keep the same words, so earlier measurements stand). One pinned negative was added (below). Three
older tests changed: two pinned negatives of follow-ups 5 and 6 now switch the later steps off so they stay tested;
one tamper test now picks line 1's capsule by line number. Every HELM suite, both switches OFF: **453 passed**.

**Bytes before (index rows only, folding off) and after (folded)** (`FOLD_BYTES_20261022.json`; peak = the highest
value after any turn):

| Chat | Working memory at the end, before → after | Peak after | Levels | Old memories recalled EXACT | Under the limit |
|---|---|---|---|---|---|
| 600 lines, limit 4,000 | 10,953 → **3,832** | 4,000 | 1 | 20 of 20 | 🟥 → ✅ |
| 300 short lines, limit 3,000 | 2,823 → **2,123** | 2,998 | 1 | (not sampled) | ✅ → ✅ |
| 8,000 lines, limit 53,370 (the owner's) | 100,721 → **52,429** | 53,370 | 1 | 20 of 20 | 🟥 → ✅ |
| 3,000 lines, limit 4,000 | 74,177 → **4,542** | 5,127 | 1 and 2 | 20 of 20 (17 through the deep search) | 🟥 → 🟥 |

"Old memories recalled EXACT" samples the first line of 20 batches spread over the whole chat and asks for it by its
unique word; EXACT means the original line came back and its fingerprint matched. Run time also fell (3,000 lines:
37.7 s → 12.9 s; 8,000 lines: 59.9 s → 34.2 s) because fewer rows are read each turn.

**What "for good" means here, measured and computed:** each level can hold up to 7 unfolded rows before 8 fold upward;
a level-1 row is about 270–350 bytes and a higher row about 490 (48 words). So working memory has a FLOOR that grows by
about 3,500 bytes per level, and each level covers 8 times as many capsules as the one below. At the owner's 53,370
bytes the floor stays below the limit for about 14 levels, that is 8^14 (about 4 × 10^12) capsules: in practice, for
good. 8,000 lines at 53,370 never needed a second level.

**Measured negatives kept 🟥:**
1. A small limit sits below the floor: at 4,000 bytes, two levels can hold about 5,800 bytes, so 3,000 lines end at
   4,542 (peak 5,127). Pinned as a test.
2. A line in the middle of a capsule was never findable by its own words: a capsule's clue words come only from its
   first lines (at most 8 words, since compaction v1). Folding did not cause this and does not fix it.
3. Logs, receipts and the maps of cloud keys still grow and are not counted as working memory (as before).
4. The deep search reads every fold record on the device after a miss, so its time grows with the chat; fold records
   already in the cloud are not deep-searched.

## 11. Clue words from every line of a batch (A-TEACH2-10 `d7242340…`, commit `d6155be5`)

Owner's words (2026-10-22, verbatim): "Yes: let each capsule take its clue words from every line in its batch (not just
the first lines), so any old line can be found by its own words. Amendment first, test-first, 0 USD; measure bytes and
reach before and after."

The amendment was committed before any code (`bb7747be`). On the size-limit path a capsule's clue words are now every
distinct content word of every line in its batch. The CAS sentence is still built from the first 8 (the Eye's template
2; template 1 records still rebuild). Plain compaction and the ladder path keep the first-8 rule.

FIX FIRST (`test_helm_cube_everyline.py`, written first): 5 failed, 2 passed → 6 passed, 1 failed (a test fault: it
counted the comma in "From my notes, …") → 7 passed; two pinned negatives added after measuring (below) → 9 passed.
Nine older tests in the tiers, offload and fold files failed under the new rule because they assumed capsules stay in
working memory longer (rows are bigger now, so capsules move off sooner); those four older test files now keep the
first-8 rule they were written for, so they still test what they claimed. Every HELM suite, both switches OFF:
**462 passed**.

**Before (first-8 rule) and after (every line), same chats** (`EVERYLINE_BYTES_20261022.json`). "Reach" asks for 30
lines spread over the whole chat, middle lines included (not the newest 20), each by its own unique word; EXACT means the
original line came back and its fingerprint matched. No sampled question was ever answered with a wrong line.

| Chat | Working memory at the end (peak) | Reach: lines recalled EXACT | Under the limit at the end |
|---|---|---|---|
| 8,000 lines, limit 53,370 (the owner's) | 49,542 (53,370) → **48,743 (53,369)** | **1 → 30 of 30** (27 through the deep search) | ✅ → ✅ |
| 600 lines, limit 4,000 | 3,743 (4,000) → **4,742 (4,924)** | **0 → 30 of 30** (28 deep) | ✅ → 🟥 |
| 3,000 lines, limit 4,000 | 5,007 (5,199) → **4,088 (7,821)** | **4 → 30 of 30** (30 deep) | 🟥 → 🟥 |
| 300 short lines, limit 3,000 | 2,299 (3,000) → **2,995 (3,000)** | (not sampled) | ✅ → ✅ |

Row sizes: an index row about 131–134 bytes → about 201–430 bytes (it now carries every line's words); folded rows are
still capped at 48 words.

In plain words: at the owner's limit, almost no old line could be found by its own words before (1 in 30), and now
every sampled line can (30 in 30), with memory still under 53,370 bytes. Most of those answers come through the deep
search of the device folder, because a folded row keeps only 48 of a thread's words.

**Measured negatives kept 🟥:**
1. Bigger rows cost space at small limits: 600 lines at 4,000 now end over it (4,742 bytes); a 3,000-line chat peaks at
   7,821. Pinned as a test.
2. Once fold records are in the cloud, words past the 48-word cap are not found: the deep search (A-TEACH2-9 F5) reads
   only fold records still on the device. HELM then says it does not know (never a wrong line). Pinned as a test.
3. Most old lines are now found through the deep search, whose time grows with the chat (it reads every fold record on
   the device after a miss in working memory).

## 12. The deep search reads the cloud's fold records when online (A-TEACH2-11 `43b11166…`, commit `d031ea42`)

Owner's words (2026-10-22, verbatim): "Yes: when a question misses everything on the device and HELM is online, let the
Eye's deep search also read the fold records in the cloud, so rare words of old lines can still be found. Amendment
first, test-first, 0 USD; measure reach and time before and after."

The amendment was committed before any code (`6e28c9aa`). Order: working memory, then the device's fold records, and
only if both find nothing and the cloud says it can be reached, the cloud's fold records. Each cloud read is checked
against the 16 characters its row kept (a mismatch is held); nothing read is kept in working memory. Offline, HELM says
its notes are stored away; never EXACT.

FIX FIRST (`test_helm_cube_cloudsearch.py`, written first): 3 failed, 2 passed → 5 passed. The A-TEACH2-10 pinned
negative ("words past the cap are not found once fold records are in the cloud") failed as expected, because they are
now found online; it was narrowed to what is still true, OFFLINE. Every HELM suite, both switches OFF: **467 passed**.

**Before (device only) and after (cloud too, when online)** — 600 lines, limit 4,000, device limit 2,000, a stand-in
cloud; 30 lines sampled across the chat, each asked by its own word (`CLOUDSEARCH_REACH_20261022.json`):

| | Recalled EXACT | Cloud reads per question (median / most) | Time per question, stand-in cloud (median / most) | Estimated time on the real bucket (median / most) |
|---|---|---|---|---|
| Before | **1 of 30** | 0 / 4 | 0.1 / 0.6 ms | 0 / 4.5 s |
| After | **30 of 30** | 9 / 9 | 0.8 / 1.0 ms | **10.1 / 10.1 s** |

No sampled question was answered with a wrong line. The real-bucket time is an ESTIMATE, not a measurement: the live
smoke test of 2026-10-21 took 20.1 seconds for about 18 calls through the AWS command line tool (≈ 1.12 s per call),
times the measured number of cloud reads. No AWS call was made for this step (0 USD).

**Measured negatives kept 🟥:**
1. Slow on the real cloud: about 9 reads per question, about 10 seconds through the AWS command line tool (estimate).
   Each read starts a new command-line process; a faster client or a small device-side cache of fold records would cut
   this, but either is a design change for the owner.
2. Offline, rare words whose fold records are in the cloud are still not found (pinned test).

## 13. The cloud search fetches all fold records in one call; live timing (A-TEACH2-12 `5b42e233…`, commit `e8382fbc`)

Owner's word (2026-10-22): "“Yes, make it faster”", answering the offer to read the cloud's fold records in one go (or
keep a device copy) and to measure the real time with a tiny live test.

The amendment was committed before any code (`b551781b`). A device copy was not chosen: it would refill the device
folder whose limit sent the records to the cloud. When the cloud search runs, the Eye now fetches every fold record of
the conversation's cloud folder in ONE call (`aws s3 cp --recursive … --exclude * --include *.fold.json` into a
temporary folder that is removed; `get_many` on the stand-in cloud). Each record is still checked against its kept 16
characters; nothing is kept. The search hands the found capsule's index row to the fetch for that one question, so the
fold record is not read again.

FIX FIRST (`test_helm_cube_cloudbatch.py`, written first): 3 failed, 3 passed → 5 passed, 1 failed (the found capsule's
fold record was read a second time, one call on its own) → 6 passed. Every HELM suite, both switches OFF:
**473 passed**.

**Live timing on the real bucket ✅ (2026-10-22, `CLOUD_BATCH_TIMING_20261022.json`).** Source: commit `e8382fbc`;
purpose: time the cloud search before and after; place: bucket `helm-cold-memory-807562639912-usw2` (us-west-2),
prefix `smoke/20261022T092048Z-batch/`, from the laptop's AWS command line tool, no instance; data: made-up planting lines
only (`SYNTHETIC_ONLY`); limits: a 200-line chat, limit 2,000 bytes, device limit 1,000 bytes; cleanup: none by design
(nothing is deleted by code). Building the chat took 94.6 seconds and 106 calls; 2 fold records reached the cloud.
Cost: about 140 requests of a few kilobytes, well under 0.01 USD.

| 8 questions, each by an old line's own word | Seconds per question (median) | Calls per question (median) | Recalled EXACT |
|---|---|---|---|
| Before (one call per fold record) | **4.16** | 5 | 8 of 8 |
| After (one batched call) | **3.54** | 4 | 8 of 8 |

No question was answered with a wrong line. One real call took about 0.83 seconds here (the earlier estimate was 1.12).
Before, a question costs 3 calls plus one per fold record read; after, it costs 4 calls however many fold records
there are (the reachability check, the batch, the capsule's record, its original). On the 600-line chat of
A-TEACH2-11 (9 calls before) that projects to about 7.5 seconds before against about 3.3 after: a PROJECTION from the
measured 0.83 s per call, not a measurement.

**Measured negatives kept 🟥:**
1. Still about 3.5 seconds per cloud question: 4 command-line calls of about 0.83 s each. The reachability check is one
   of them; a faster client (no new process per call) or remembering the last check for a short time would cut it;
   both are design changes for the owner.
2. The saving on this small live chat is small (one call), because only 2 fold records were in the cloud; the bigger
   saving on longer chats is projected, not measured live.

## 14. HELM remembers a "cloud reachable" yes for 60 seconds; live timing (A-TEACH2-13 `9c8e3daa…`, commit `8e8bf338`)

Owner's words (2026-10-22, verbatim): "Yes: let HELM remember for a short while that the cloud was reachable, so a
cloud question skips that check (one call fewer). Amendment first, test-first; time it live with a tiny test."

The amendment was committed before any code (`3dc12252`). A yes (a reachability check that answered yes, or a
successful batched read) is remembered for 60 seconds; a no is never remembered; any failed cloud call forgets it at
once, and that question behaves as before (notes stored away, never EXACT). The same memory serves the cloud search and
the cloud move. It is one timestamp per cloud adapter and holds no data.

FIX FIRST (`test_helm_cube_reach_memory.py`, written first): 5 failed → 5 passed. Every HELM suite, both switches OFF:
**478 passed**.

**Live timing on the real bucket ✅ (2026-10-22, `CLOUD_REACH_TIMING_20261022.json`).** Source: commit `8e8bf338`;
purpose: time the change; place: bucket `helm-cold-memory-807562639912-usw2` (us-west-2), prefixes
`smoke/20261022T093130Z-reach-off/` and `smoke/20261022T093130Z-reach-on/`, from the laptop's AWS command line tool, no
instance; data: made-up planting lines only (`SYNTHETIC_ONLY`); the same 200-line chat (limit 2,000, device limit
1,000) built twice; cleanup: none by design. Cost: about 190 requests for the two builds plus 56 for the questions,
a few kilobytes each, well under 0.01 USD.

| | Building the 200-line chat | Per cloud question (median of 8) | Recalled EXACT |
|---|---|---|---|
| Before (memory off) | 93.6 s, 106 calls, 22 reachability checks | **3.46 s**, 4 calls | 8 of 8 |
| After (memory on) | **73.8 s**, 86 calls, **2** reachability checks | **2.66 s**, 3 calls | 8 of 8 |

No question was answered with a wrong line. Across follow-ups 9–11 a cloud question went from about 10 s (estimated)
to 4.16 s (measured), 3.54 s, and now 2.66 s.

**Measured negative kept 🟥:** a cloud question still takes about 2.7 seconds: 3 command-line calls (the batched fold
read, the capsule's record, its original) of about 0.85 s each, most of it starting a new AWS command-line process per
call. A client that keeps one connection open would cut that further; it is a design change for the owner (HELM is
standard-library only, so it would mean signing requests to the bucket by hand).
