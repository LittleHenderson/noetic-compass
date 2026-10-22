
## Amendment A-TEACH2-7 (2026-10-22 PDT) — the Eye runs a lean capsule: store only what cannot be rebuilt; every rebuild must match its receipt; written before the code

Status: appended after A-TEACH2-6 (`2c019244…`); nothing above is edited. Where it disagrees with A-TEACH2-5 L2 (the capsule written per batch), this governs.

**The owner's words (verbatim, 2026-10-22):** "bro put the Eye in charge of this part that is causing or is an issue: 2.; Shrink the capsule: don’t save what can be rebuilt. Rebuild the CAS sentence (from the clues plus the Noetic digits, with a template version stored), the compile and round-trip checks, the cold-copy path (folder plus capsule name), the line-number list (from the first and last ids in the capsule name), and the Atlas node id and side. Keep the clues, the Noetic digits, the fingerprint of the original, the bound cubes, the mass and the receipt. A rebuilt capsule must match its receipt. Amendment first, test-first, 0 USD; measure bytes before and after."

**The issue being fixed (BUILD_V2_RECORD §7, measured):** one capsule is about 810 bytes (breadcrumb 251, CAS sentence and checks 169, Atlas 89, clues 69, receipt 66, …) and replaces about 900 bytes of lines. Working memory after 200 lines with a 4,000-byte limit: **11,165 bytes** (the "before" number).

**E1. The lean record keeps only:** the capsule name; the clues; the Noetic digits (one digit per CCE frame, in order); the template version of the sentence (`1` = today's `Compactor._sentence`); the fingerprint (sha256) of the original; the bound cubes (and bound coefficients only when there are any); the mass; the receipt. Two markers are kept only when needed: the kind when it is "question", and the original clue count when strengthening has added clues. The line-number list is kept explicitly only when the ids in a batch are not consecutive (so the first and last cannot rebuild it).

**E2. Rebuilt on every read, never stored:** the CAS sentence and notation (from the clues and the Noetic digits with template 1); the compile check and the round-trip check (run again on the rebuilt sentence and notation) and the compiler's name; the cold-copy path (the cold folder plus the capsule name plus `.jsonl`); the line-number list (from the first and last ids in the capsule name); the Atlas thread node (from the capsule's place in order: 8 capsules per thread node), the capsule node id (`capsule:<name>`), the side (`fact` once strengthened, else `possibility`) and the fact node id when strengthened.

**E3. A rebuilt capsule must match its receipt.** The receipt is the sha256 written at compaction over the name, the CAS part, the clues, the binds, the fingerprint plus line numbers, and the mass. The rebuild check recomputes it from the rebuilt capsule, using the clues and the mass as they were at compaction (the original clue count; the mass at compaction is the number of lines, 0 confirmations). Equal = the rebuild is faithful.

**E4. The Eye is in charge of this step** (`helm_eye_act.py`, the same Eye as EYE-ACT-1, a new watch `CapsuleEye`; its words are the same):
- **ACT — shrink:** when a capsule is written, the Eye stores the lean record in place of the full capsule, then at once rebuilds it and checks the receipt. If the check fails, the Eye keeps the full capsule (nothing is lost) and logs `LEAN_REFUSED`.
- **READ — rebuild:** every use of a capsule (recall, fetch, fit check, answers, the cloud move) goes through the Eye's rebuild and receipt check.
- **HOLD:** a lean record whose rebuild does not match its receipt is held: it is never used for an answer (UNKNOWN, never EXACT, never RECONSTRUCTED from it), and the Eye report flags `LEAN_REBUILD_MISMATCH`.
- Every act and hold is logged with the capsule name and the digests before and after. The Eye never changes a clue, a cube, a mass, a receipt or a fingerprint.

**E5. Where it runs:** on the size-limit path only (A-TEACH2-5; `HELM_CUBE_OSC` ON with a limit). The ladder path and plain compaction (`HELM_MEMORY_COMPACT` alone) keep full capsules. The Eye's acting stays **NOT LICENSED** as a claim (spec 7.38); this is engineering behind a switch that is OFF by default, `ENGINEERED-NOT-VALIDATED`.

**E6. Measured and reported:** bytes per capsule before and after, and working memory on the same 200-line, 4,000-limit chat before (11,165) and after. If memory still does not stay under the limit, that is reported as such, not as a pass.
