# `_archived_chapter_drafts/` — Superseded chapter drafts

These files are earlier drafts preserved for historical reference. They are **SUPERSEDED** by `FULL_MANUSCRIPT.md`, which is the authoritative book manuscript.

**Do not edit these archived files.** All reformation and revision work targets `FULL_MANUSCRIPT.md` exclusively.

Archived **2026-04-19** as part of Phase 2 reformation file-authority cleanup.

## Why these files are superseded

An investigation during Phase 2 Session 1 confirmed that the prose in these individual chapter files is shorter and less detailed than the corresponding chapter content in `FULL_MANUSCRIPT.md`. Both sets of files were committed to the repository together in commit `5eae335` (the only commit that touched them at time of archival), but `FULL_MANUSCRIPT.md` is the authoritative, richer version that will be formatted in Atticus and uploaded to KDP.

Example of the prose difference (Chapter 2 opening paragraph):

- **This archived draft** opens with: *"Grandmaster Garry Kasparov is staring at a chessboard. The game is highly complex, the tension is palpable, and the clock is ticking down."*
- **`FULL_MANUSCRIPT.md` Chapter 2 (lines 358+)** opens with: *"On November 26, 1985, Grandmaster Garry Kasparov is staring at a chessboard in a fluorescent-lit convention hall in Moscow. Across from him sits Anatoly Karpov, the reigning World Champion and the most methodical player in the history of the game. The match is in its 24th and final game. Kasparov, only twenty-two years old, trails by one point. He must win this game to take the crown."*

The same pattern holds across every chapter: the archived drafts are earlier, shorter versions; `FULL_MANUSCRIPT.md` contains the richer prose that constitutes the actual manuscript.

## Contents

- `Chapter_02_The_Ten_Cognitive_Operators.md` — earlier draft, 172 lines, superseded.
- `Chapter_06_Inversions.md` — earlier draft, 93 lines, superseded.
- `Appendices.md` — earlier draft of the appendix set (A–E), 148 lines, superseded. The authoritative appendices are at `FULL_MANUSCRIPT.md` lines 5617–end.

## Other chapter files not yet archived

The Phase 2 Session 1 investigation focused on three files (Ch 2, Ch 6, Appendices — the specific targets of the initial reformation batch). The other per-chapter files in `book/manuscript/` (Chapter_01, Chapter_03 through Chapter_05, Chapter_07 through Chapter_27, and 00_Front_Matter.md) are almost certainly in the same category — earlier drafts superseded by the consolidation into `FULL_MANUSCRIPT.md`. Their archival is a separate decision for a future session; until then, they remain at `book/manuscript/` but should be treated as reference copies, not edited.

## Recovery

If any content from these archived drafts needs to be restored or referenced, open the file directly — no special tooling required; they are clean UTF-8 markdown. Alternatively, git history preserves every version of every file from commit `5eae335` onward.
