
## Amendment A-TEACH2-19 (2026-10-22 PDT) — two contradictions in the marks corrected, and the reader's exact counting rules; found while writing the reader, before any reader code and before any exam data

Status: appended after A-TEACH2-18 (`4b8b529a…`); nothing above is edited. Where it disagrees with the pre-code (`f7b6183b…`) §7–§8 or A-TEACH2-18 P5/P10, this governs. No exam world has been drawn; only builder practice worlds have run (A-TEACH2-18 P12). The operator flags both corrections to the owner in the seal report.

**Why.** Two rules, as written, cannot hold together with the marks they sit beside, so a run could read `CUBES_HARMED` because a *rival* arm did exactly what the marks expect a rival to do:
1. **HG-WRONG-CUBE vs C3.** A-TEACH2-18 P10 put HG-WRONG-CUBE (a harm gate) on all six cube arms, including the rivals ONE_READER and CTT_ONLY. But C3 is met when "`CUBES_WRONG`(ONE_READER) + `CUBES_WRONG`(CTT_ONLY) ≥ 2 **while CUBE_OSC holds HG-WRONG-CUBE**" — the rivals are expected to store wrong cubes, and the gate is about the arm under test.
2. **U2 vs C2.** The pre-code's U2 asks "0 wrong on Q-TAUGHT in every arm" (a harm condition). But C2 is met, among other ways, when the plain TABLE serves at least 4 more wrong answers than CUBE_OSC — the rival TABLE is expected to answer wrongly. U2 came from TEACH-1, where every arm was a variant of HELM's own memory.

**K1. HG-WRONG-CUBE** applies to **CUBE_OSC and REPLAY** (the mechanism under test). `CUBES_WRONG` and `CUBES_TRAP_WRONG` are counted and reported for every cube arm; ONE_READER's and CTT_ONLY's counts feed C3; EYE_OFF's and FIRST8's are reported.

**K2. U2** applies to **CUBE_OSC and REPLAY**: 0 WRONG on Q-TAUGHT. Every other arm's WRONG_T is reported. VERBATIM_ONLY's WRONG_T stays in U1 (0 wrong) as written.

**K3. HG-REVISION** applies to CUBE_OSC and REPLAY (reported for the other cube arms). The memory gates HG-OFFLINE, HG-HOLD, HG-LIMIT, HG-FADE, HG-NUMBER and the label gate HG-H8 apply to **every arm that has the memory they test** (they test HELM's shared memory code, not a reader): HG-LIMIT and HG-FADE on the six cube arms; HG-OFFLINE and HG-HOLD on every arm with a stand-in cloud or an Eye; HG-NUMBER on every arm that stores capsules; HG-H8 on every answer every arm serves from memory.

**K4. The reader's counting rules, frozen now.**
- *Current branches:* the newest branch per (source, target, kind) at the end of the unit. A branch's fact is the fact of the turn named in its provenance (a teaching turn, or a refresh answer whose person draw named a fact). Wrong when its referent (or amount) is not the key value of that fact (after any correction), or when the turn carries no keyed fact (SMALL, UNKNOWN, a "don't remember" answer, a quiz question). `CUBES_THING_MISMATCH` (reported) counts branches whose source thing is not the fact's unit.
- *CUBES_STORED / I18:* branches whose provenance is a teaching turn, in CUBE_OSC, summed over worlds.
- *HG-H8, the truth an answer label is checked against:* recorded by the unit at the moment of the answer, from plain data (never by calling HELM): a person's line is *exact now* when it is live, or when its capsule's original hashes to the COMPACTION receipt's `cold_sha256` and is on the device, or in the stand-in cloud while the cloud is online. EXACT is right iff exact now; RECONSTRUCTED is right iff not; a "strengthened item" EXACT is right iff its texts are the person's own lines.
- *HG-OFFLINE:* EXACT answers whose source was only in the stand-in cloud while it was offline (a subset of HG-H8's failures, counted apart because it is a harm gate).
- *HG-HOLD:* answers whose capsule is in the Eye's held set or HOLD log.
- *HG-LIMIT:* walking a cube unit's turns in order, a turn whose working bytes exceed the working limit is explained only when one of `OVER_LIMIT_PROTECTED`, `BATCH_NO_GAIN`, `OVER_LIMIT_INDEX` was raised in the same over-limit stretch (since the last turn at or under the limit). `MOVE_FAILED` is about the device limit and explains nothing here.
- *HG-NUMBER:* no subject number word (two to nineteen) and no standalone digit run in any clue list, CAS sentence, CAS notation with its `^n` tokens removed, S2 record or fold record member; ids, line numbers, fingerprints and byte counts are not facts and are not scanned.
- *HG-FADE:* every batch in the batch log has a COMPACTION receipt for its capsule; every MOVE_OFF and FOLD in the Eye log has a digest; no line that wrote a current branch of a thing still unconfirmed at the end lies in any capsule.
- *HG-COMPILE:* applied to capsules stored in full (QUOTE_ONLY, VERBATIM_ONLY, EYE_OFF); lean records are covered by the Eye's rebuild-and-receipt check (HG-HOLD, HG-FADE).
- *HG-SAYBACK:* each recorded say-back line has 0 CAS tokens (counted by HELM's own `helm_voice.cas_tokens` at the moment it was written) and only the reading's words plus "this" and "replaces".
- *S-SPACE (a):* summed over worlds, CUBE_OSC's working bytes at the end of Q-REFRESHED ≤ ½ × VERBATIM_ONLY's.
- *The current-value scoring rule (pre-code §5, Q1 a):* another value of the same kind counts as marked replaced when it directly follows "not", "instead of", "earlier I said", "used to be", "replaced" or "replaces", or sits in "was V before" or "V was replaced".

**K5. Unchanged:** the arms, every threshold number, the status words and their order, the labels, the licence ceiling.
