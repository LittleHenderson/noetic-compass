
## Amendment A-TEACH2-12 (2026-10-22 PDT) — the cloud search fetches all fold records in ONE call; a tiny live timing test; written before the code

Status: appended after A-TEACH2-11 (`43b11166…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "“Yes, make it faster”" — answering the offer: "make the cloud search faster (for example, keep a small copy of the cloud's fold records in the device folder, or read them in one go instead of one call each). Amendment first, test-first, 0 USD for the build; measure the real time on the bucket with a tiny live test."

**Before (A-TEACH2-11 record):** about 9 cloud reads per question (one AWS command-line call each, about 1.12 s per call), estimated about 10 seconds per question.

**Choice: read in one go.** A device-side copy of the cloud's fold records would refill the device folder whose limit sent them to the cloud, so it is not chosen.

**B1. One batched read.** When the cloud deep search runs (A-TEACH2-11 D1), the Eye fetches every fold record of this conversation's cloud folder in ONE call: on the bucket, one `aws s3 cp --recursive` of the conversation's prefix filtered to `*.fold.json` into a temporary folder; on the stand-in cloud, one `get_many`. Each record is then checked exactly as before (its sha256 must begin with the 16 characters its row kept; a mismatch is held), searched, and dropped; the temporary folder is removed. Nothing is kept in working memory.

**B2. Then as before:** the found capsule's record and its original are fetched and checked (A-TEACH2-8 M5): at most 2 more calls.

**B3. Offline:** unchanged (A-TEACH2-11 D4).

**B4. The live timing test (owner-approved, tiny):** the bucket `helm-cold-memory-807562639912-usw2`, a new prefix under `smoke/`, made-up lines only (`SYNTHETIC_ONLY`), a chat sized so that fold records reach the cloud. The same questions are timed with one call per read (before) and with the batched read (after). Expected cost: a few hundred uploads and reads of a few kilobytes each, well under 0.01 USD, inside the owner's 200 USD AWS ceiling; recorded per CLAUDE.md (source, purpose, place, limits, cleanup: none, nothing is deleted by code).

**B5. Measured and reported:** cloud calls per question and seconds per question, before and after, on the stand-in cloud and on the real bucket. `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).
