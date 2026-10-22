
## Amendment A-TEACH2-8 (2026-10-22 PDT) — the Eye moves old capsules off working memory (device folder, then the cloud), keeping only a small clue index; written before the code

Status: appended after A-TEACH2-7 (`58ef426e…`); nothing above is edited. Where it disagrees with A-TEACH2-5 L5 ("capsules never go to the cloud"), this governs for the Eye's lean capsule records.

**The owner's words (verbatim, 2026-10-22):** "Yes: let the Eye move old capsules off working memory too (device folder, then the cloud), keeping only a small index of clue words in working memory. Amendment first, test-first, 0 USD; measure bytes before and after."

**Before (A-TEACH2-7 record, `LEAN_BYTES_20261022.json`):** a lean capsule is about 281 bytes and stays in working memory, so capsules pile up: 600 lines at a 4,000-byte limit end at **26,126 bytes**; 300 short lines at 3,000 end at **7,202 bytes**.

**M1. When.** After the batch fading of a turn (A-TEACH2-5 L2), if working memory is still above 90 % of the limit, the Eye moves the OLDEST capsules still in working memory off it, one by one, until working memory is at or under 90 % of the limit or none is left. A capsule that was just used for a strengthening comes back into working memory (it is written back there).

**M2. The index row kept in working memory, per moved capsule:** the capsule name, its clue words, the first 16 characters of its receipt, and only when needed the kind ("question") and an explicit line-number list (when not consecutive). Nothing else.

**M3. The device folder.** The moved record (the lean record, or the full capsule the Eye refused to shrink) is written to the cold folder as `<capsule name>.lean.json`, read back and compared byte for byte; only then is it removed from working memory (Eye log `MOVE_OFF`). A failed write leaves it in working memory (`MOVE_OFF_FAILED`).

**M4. The cloud.** The device folder's limit (A-TEACH2-5 L3) now counts these record files too. When it is passed, the oldest capsule's verbatim original AND its moved record go to the bucket together: each uploaded, read back and checked (the original by its fingerprint, the record byte for byte), then removed locally, with one `MOVED_TO_CLOUD` receipt. Nothing is ever deleted in the cloud.

**M5. Fetching a moved capsule.** Recall matches the question's words against the index clue words; only a matching capsule is fetched (device folder first, then the cloud). The Eye checks the fetched record: the same name, the same clue words as the index, a receipt beginning with the kept 16 characters, then the A-TEACH2-7 rebuild and receipt check. A failed check is a HOLD (`LEAN_REBUILD_MISMATCH`), never an answer. A record in the cloud that cannot be reached gives no answer from it: HELM says its notes are stored away and it can't reach them right now (never EXACT, never invented).

**M6. Unchanged:** cubes, branches, the Atlas and every receipt log stay on the device. The ladder path and plain compaction are not touched. `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).

**M7. Measured and reported:** the same four chats as A-TEACH2-7, before (lean capsules in working memory) and after (moved off, index only), plus the bytes per index row. If memory still breaks the limit somewhere (the index also grows with every capsule), that is reported, not hidden.
