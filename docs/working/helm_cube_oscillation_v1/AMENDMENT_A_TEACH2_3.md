
## Amendment A-TEACH2-3 (2026-10-21 PDT) — two corrections to A-TEACH2-2, found while writing the tests; still before any code

Status: appended after A-TEACH2-2 (`ec3d65fc…`); nothing above is edited. No v2 code existed when it was written.

1. **The first word of a line (B2).** A-TEACH2-2 said a line's first word is never a proper name, to skip "The". That
   loses a name that opens the line ("Halden drove the Eastwold line"). Corrected rule: the first word counts as a
   proper name when it is capitalised and its lower-case form is in none of: the cut's `STOP_WORDS`, B2's discourse
   list, and this frozen list of openers: `the, this, that, there, then, these, those, our, my, your, one, also, and,
   but, so, oh, okay, ok, by, let, back, in, on, at, for, from, after, during, last, next, every, each, honestly,
   correction, actually, sorry, yes, well, anyway, right, just, now, around, about, over, since, when, as, it, we,
   they, he, she, i`.
2. **A confound in C2, and a reported arm to show it.** TABLE uses the rule reader while CUBE_OSC uses the CTT's agreed
   reading, so a C2 win could come from the reader rather than from the cube. New arm **TABLE_OSC**, **reported only,
   deciding nothing**: the same agreed readings as CUBE_OSC, stored in a plain dict `(thing, slot) → value` (no cube,
   no Atlas, no ladder). C2 is unchanged; TABLE_OSC lets the owner see the store's part apart from the reader's part.
