
## Amendment A-TEACH2-21 (2026-10-22 PDT) — four counting and checking defects found by the one independent review round, fixed before the seal and before any exam world exists

Status: appended after A-TEACH2-20 (`a29ebaf4…`); nothing above is edited. Where it disagrees with A-TEACH2-19 K4 or A-TEACH2-18 P10, this governs. Only builder practice worlds have run. The operator flags this amendment to the owner in the seal report.

**Why.** One independent review round (an AI reviewer that read the code and ran nothing) found four MAJOR defects: each could make a gate read true when it should be false, or false when it should be true. None changes an arm, a threshold, a mark or a status word.

**R1. The TABLE arms' source lines (HG-H8).** Arms without a compactor number lines by their position (`len(turns)+1`), so once the 12-line budget is full every new line has the same number, and a dropped line's number points at a live line. The unit now records, for every table entry, the person's line that wrote it; a table answer's source is *exact now* only when a live line has that number **and** that text. (The reviewer's note, recorded: with this fixed, HG-H8 may read false on the TABLE rival, and A-TEACH2-19 K3 puts HG-H8 on every answer every arm serves; that is the frozen reading.)

**R2. HG-LIMIT's stretch rule.** HELM raises a limit flag only when the kind of flag changes (`CubeOsc._limit_flag`), so a stretch that dips under the working limit and goes over again with the same reason raises nothing new. An over-limit turn is now also explained when the memory's own current flag at that turn (`limit_flag`, recorded per turn) is one of `OVER_LIMIT_PROTECTED`, `BATCH_NO_GAIN`, `OVER_LIMIT_INDEX`. `MOVE_FAILED` still explains nothing.

**R3. HG-HOLD counts answers served from a held record.** K4 said "answers whose capsule is in the Eye's held set". A cube answer whose source capsule is held is told by HELM that the words are missing and answers RECONSTRUCTED from its branch — it did not use the held record. HG-HOLD now counts: answers served from a capsule (the memory's recall path) whose capsule is held, and cube answers labelled EXACT whose source capsule is held.

**R4. The custodian's turn check compares every turn with its plan slot.** In sealed mode `turns_t2.check_turns` now also requires, per turn: `turn_index`, `kind`, `fact_id`, `value`, `not_value` and `trap_role` equal to the drawn plan's slot; on every FACT, TRAP, FIX and RESTATE line the value word appears in the line; and `keyed` is recomputed — `AGREE` only when both keys name the plan's fact id and value (FIX: the new value; TRAP: the true value; UNKNOWN: no value). A turn file's own `keyed` field is not trusted.

**R5. Two small hardenings (MINOR, done because they are cheap):** a CTT server reply with the wrong shape counts as a dead server (no reading; I20 false); the seal refuses unless every test from the fresh extract exits 0 and the assembled harness equals the committed source byte for byte.

**R6. Unchanged:** every threshold number, the arms, the marks, the status words and their order, the labels, the licence ceiling. Reported, not changed (the reviewer's MINOR N1): by the pre-code §9 as frozen, C4 between 2 and 4 lost items is neither NO_GAIN nor HARMED.
