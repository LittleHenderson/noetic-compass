
## Amendment A-TEACH2-10 (2026-10-22 PDT) — on the size-limit path, a capsule takes its clue words from every line of its batch; written before the code

Status: appended after A-TEACH2-9 (`22364836…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "Yes: let each capsule take its clue words from every line in its batch (not just the first lines), so any old line can be found by its own words. Amendment first, test-first, 0 USD; measure bytes and reach before and after."

**Before (A-TEACH2-9 record):** a capsule's clue words are the first 8 content words of its first lines (compaction v1, DESIGN 3.1, `MAX_CLUES = 8`), so a line in the middle of a capsule cannot be found by its own words.

**C1. Every line.** On the size-limit path (where the Eye runs the capsules: `HELM_CUBE_OSC` with a limit), a capsule's clue words are every distinct content word of every line in its batch, in order (the same word rule as before: letters only, at least 4 letters, no stop word, no number word). Plain compaction (`HELM_MEMORY_COMPACT` alone, the TEACH-1 path) and the ladder path keep the first-8 rule unchanged.

**C2. The CAS sentence stays as it is.** The CAS sentence and its notation are built from the first 8 clue words only, which is exactly what they are built from today. The full list is kept for finding lines. The Eye's lean record names this template **2** ("the sentence from the first 8 clue words"); template 1 (the sentence from all clue words) is still rebuilt the same way for records that have it, and for 8 words or fewer the two give the same sentence. The receipt covers the full clue list, as before.

**C3. Everything else is unchanged:** the batch gain check (a batch is written only if its stored record is smaller than its lines), move-off, index rows (they now carry the full clue list), folding (a folded row still keeps at most 48 words; the rest stay in the fold record and the deep search finds them), strengthening (its clue growth is still capped at 8, so a capsule that already has 8 or more words gains none), and the "from my notes" sentence (it names at most the first 8 words).

**C4. Measured and reported, before (first-8 rule) and after (every line), on the same chats as A-TEACH2-9:** working memory at the end and at its peak; bytes per lean record and per index row; and REACH: of lines sampled across the whole chat (not only first lines), how many are recalled EXACT by their own unique word. If the bigger rows push a chat over its limit, that is reported, not hidden.

`ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).
