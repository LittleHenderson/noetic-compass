
## Amendment A-TEACH2-11 (2026-10-22 PDT) — when HELM is online, the Eye's deep search also reads the fold records in the cloud; written before the code

Status: appended after A-TEACH2-10 (`d7242340…`); nothing above is edited. Where it disagrees with A-TEACH2-9 F5 ("fold records already in the cloud are not deep-searched"), this governs.

**The owner's words (verbatim, 2026-10-22):** "Yes: when a question misses everything on the device and HELM is online, let the Eye's deep search also read the fold records in the cloud, so rare words of old lines can still be found. Amendment first, test-first, 0 USD; measure reach and time before and after."

**Before (A-TEACH2-10 record):** a word past a folded row's 48-word cap is found only through fold records still on the device; once they are in the cloud it is not found (pinned test `test_words_past_the_cap_are_not_found_once_fold_records_are_in_the_cloud`).

**D1. Order.** A question is matched against working memory first (rows, then the folded rows that hold every word), then the deep search of the fold records on the device (A-TEACH2-9 F5). Only if all of that finds nothing, and the cloud says it can be reached, does the deep search read the fold records in the cloud too.

**D2. Every cloud read is checked** exactly like a device read: the fold record's sha256 must begin with the 16 characters its row kept; a mismatch is held (`LEAN_REBUILD_MISMATCH`), never used. Then the found capsule is fetched and checked as before (A-TEACH2-8 M5).

**D3. Nothing read from the cloud is kept in working memory.** The records are read, searched and dropped. Nothing is deleted anywhere.

**D4. Offline, or the cloud cannot be reached:** no cloud search; if the device has nothing, HELM says its notes are stored away and it can't reach them right now (never EXACT, never a guess).

**D5. Measured and reported, before and after, on the pinned chat** (600 lines, limit 4,000, device limit 2,000, a stand-in cloud): reach (lines sampled across the chat recalled EXACT by their own word), the number of cloud reads per question, and the time per question on the stand-in cloud. Real cloud time is not measured (0 USD); it is estimated from the live smoke test of 2026-10-21 (`CLOUD_SMOKE_20261021.json`: 20.1 seconds for its calls through the AWS command line tool) and reported as an estimate, not a measurement.

`ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).
