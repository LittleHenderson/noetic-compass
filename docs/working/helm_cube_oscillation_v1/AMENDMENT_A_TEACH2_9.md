
## Amendment A-TEACH2-9 (2026-10-22 PDT) — the Eye folds old index rows together, row upon row, so working memory can stay under the limit; written before the code

Status: appended after A-TEACH2-8 (`d5fbf746…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "Yes: let the Eye fold old index rows together (for example, one row per thread of conversation, holding the clue words of its capsules), so working memory can stay under the limit for good. Amendment first, test-first, 0 USD; measure bytes before and after."

**Before (A-TEACH2-8 record, `OFFLOAD_BYTES_20261022.json`):** each moved capsule leaves an index row of about 129 bytes, so the index grows with the chat: 600 lines at a 4,000-byte limit end at **10,870 bytes**; 3,000 lines at 4,000 end at **72,222 bytes**.

**Why one row per thread alone is not "for good":** a thread row still adds a row for every 8 capsules, so it only slows the growth. To stay under a fixed limit the folding must repeat, and each folded row must have a fixed most size.

**F1. Level 1 (the owner's example).** After moving capsules off (A-TEACH2-8 M1), if working memory is still over 90 % of the limit, the Eye folds the oldest 8 consecutive moved-off index rows into ONE level-1 row: one row per thread of 8 capsules, the same 8 that share an Atlas thread node.

**F2. Row upon row.** If memory is still over, the Eye folds the oldest 8 rows of level 1 into one level-2 row, then level 2 into level 3, and so on. At most 7 unfolded rows remain at each level, so the number of rows grows like the number of digits of the capsule count in base 8 (7 levels cover about 2 million capsules, about 33 million lines).

**F3. A folded row holds:** its name (`fold-<level>-<number>`), its level, the clue words of everything inside it, the first and last line number inside it, and the first 16 characters of the sha256 of its fold record. Clue words are capped at **48 per row**: the words found in the most capsules are kept (ties: the newest). The words past the cap are not lost; they stay in the fold record on the device.

**F4. The fold record.** The rows that were folded (index rows at level 1, folded rows above) are written to `<cold folder>/<fold name>.fold.json`, read back byte for byte, checked against the kept 16 characters, and only then removed from working memory (Eye log `FOLD`). A failed write leaves the rows unfolded (`FOLD_FAILED`).

**F5. Finding a folded memory.** Recall first matches the question's words against the rows in working memory (capsule rows, index rows, folded rows). A folded row whose words hold every question word is opened (its fold record read from the device, or the cloud), down to the matching capsule, which is fetched and checked as in A-TEACH2-8 M5. If nothing in working memory matches, the Eye does a DEEP SEARCH: it reads the fold records on the device, without loading them into working memory, to find words that were past the cap. Fold records already in the cloud are not deep-searched. A record that fails its check is held, never answered from. A cube answer for a folded capsule finds it by its line number.

**F6. The cloud.** The device folder's limit counts fold records too. They move to the cloud like the other files: upload, read back byte for byte, then remove locally.

**F7. What stays honest.** Strengthening brings a folded capsule back into working memory. Logs, receipts and the maps of cloud keys are not counted as working memory (as before, A-TEACH2-2 B8); that gap is reported. The Eye's acting stays `NOT LICENSED`; `ENGINEERED-NOT-VALIDATED`.

**F8. Measured and reported:** the same chats as A-TEACH2-8, before (index rows only) and after (folded), the bytes per folded row, the number of levels, and REACHABILITY: of the first line of every 16-line batch, how many can still be recalled EXACT through the index, the folded rows or the deep search. A memory that cannot be reached any more is reported as lost reach, not hidden.
