
## Amendment A-TEACH2-13 (2026-10-22 PDT) — HELM remembers for a short while that the cloud was reachable; written before the code

Status: appended after A-TEACH2-12 (`5b42e233…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "Yes: let HELM remember for a short while that the cloud was reachable, so a cloud question skips that check (one call fewer). Amendment first, test-first; time it live with a tiny test."

**Before (A-TEACH2-12 record, live):** a cloud question makes 4 calls (reachability check, batched fold read, the capsule's record, its original), median 3.54 seconds on the real bucket; one call is about 0.83 seconds.

**R1. Remember only a yes, for 60 seconds.** After a reachability check that says yes, or after a successful batched fold read, HELM treats the cloud as reachable for the next **60 seconds** without asking again. A "no" is never remembered: the next need checks again.

**R2. Forget at the first failure.** If any cloud call fails while HELM still remembers "reachable", the memory is dropped at once; that question then behaves exactly as before (A-TEACH2-11 D4: the notes are stored away, never EXACT, never a guess), and the next need checks again.

**R3. Where.** The same short memory serves the cloud search (A-TEACH2-11/12) and the cloud move of the device folder (A-TEACH2-5 L3, A-TEACH2-8 M4, A-TEACH2-9 F6). It is one timestamp per cloud adapter; it holds no data.

**R4. The live timing test (owner-approved, tiny):** the same bucket, a new prefix under `smoke/`, made-up lines only, the same 200-line chat as A-TEACH2-12; the same questions timed back to back with the memory off (before) and on (after). Expected cost well under 0.01 USD; recorded per CLAUDE.md; nothing deleted by code.

**R5. Measured and reported:** calls and seconds per question, before and after, and how many reachability checks the 200-line chat itself made, before and after. `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).
