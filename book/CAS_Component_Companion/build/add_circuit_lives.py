#!/usr/bin/env python3
"""Add a human reading to every schematic in the two schematic chapters.

A schematic is only worth drawing if it can be pointed at a life. Each circuit
gets a short "**In a life.**" paragraph, placed after the circuit's existing
caption text and before the next `## Circuit` heading, so the drawings stay
exactly as audited and the human reading sits underneath each one.

Run once from build/; it is idempotent.
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent

IN_A_LIFE = {
    1: (
        "Someone says your name in a particular tone and you are eight years old in a "
        "kitchen. The tone is the `^8` trigger, the eight-year-old is not a memory you "
        "fetched — she is the `^9` that arrived — and the household you grew up in is the "
        "`^5` substrate that decided what the tone would land as. Change the substrate and "
        "the same tone lands as an ordinary question, which is why two siblings hear the "
        "same sentence and one of them flinches."
    ),
    2: (
        "A conviction you hold in principle reaches your hands as a way of behaving, or it "
        "does not. *I believe people deserve a second chance* is `P`. *I will hear him out "
        "on Thursday* is `C`. *This is unfair and I am angry about it* is `E`. *I have "
        "written the email* is `O`. Each crossing is a diode: it can happen or be refused, "
        "and the refusal is not the same event as never having had the conviction."
    ),
    3: (
        "One small habit, repeated, becomes a disposition. The first honest sentence is "
        "effortful. The hundredth is character. This is a cascade, and it explains why "
        "single dramatic decisions change so much less than people expect: the gain of one "
        "stage is not the gain of the chain, and every stage in the chain has its own "
        "ceiling."
    ),
    4: (
        "You say something in a meeting, someone's face changes, and by the time you are "
        "back at your desk you have revised what you said into something safer. The "
        "revision is the feedback resistor: it slows the return of your own output so that "
        "it can inform the next thing you say rather than simply echo the last thing. "
        "Without it you would repeat yourself all day; with too much of it you never say "
        "anything again."
    ),
    5: (
        "You want to go and you want to stay, both at once, and you are standing in the "
        "hallway unable to move. That is not indecision — it is two flags active at the "
        "same time, and the honest reading is *conflict*, not *confusion*. Name both. The "
        "hallway is what happens when a person tries to resolve a both-active state by "
        "waiting for one of them to disappear."
    ),
    6: (
        "A small sentence switches something enormous. *I am going to say it tonight* "
        "changes a marriage; the sentence itself took a second. The isolation matters: the "
        "decision can be made in a calm hour without the consequence reaching back and "
        "moving the deciding. Note the direction, always — the large path does not get to "
        "steer the small one, however much it feels as though it does."
    ),
    7: (
        "Two people hear the same criticism. One of them is fine and the other is not, and "
        "the difference is not the criticism. Something both of you share — the fact of "
        "being criticised, the fact of the week you have both had — is cancelling out, and "
        "what is left is the part that is actually about each of you. That is uncomfortable "
        "precisely because it is informative."
    ),
    8: (
        "A practice rhythm and an external rhythm find each other: a new baby's sleep and "
        "the household's week; a runner's cadence and a partner's; a team's pace and a new "
        "starter's. The lock is gradual and it has a range, which is the practical fact — "
        "you cannot drag somebody into a rhythm far from their own, and you can walk them "
        "into it in steps."
    ),
    9: (
        "You remember, and you are changed by the remembering, and over years the change "
        "softens. This is retention with a leak, refreshed by rehearsal, occasionally "
        "showing a gap where none was. The gap is the part people fear most, and it is worth "
        "saying plainly: a low reading cannot tell you whether something was never written "
        "or has faded since. Only the history can."
    ),
    10: (
        "The whole board in one picture. Somebody is running on purpose and structure, has "
        "not slept properly in four months, and is still delivering — right up until the "
        "afternoon when the lights go out. The output was clean the entire time, which is "
        "precisely why nobody looked at the supply."
    ),
}

HEAD = re.compile(r"^## Circuit (\d+) — ", re.MULTILINE)


def main() -> int:
    total = 0
    for name in ("17_Single_Stage_Schematics.md", "18_Board_Level_Schematics.md"):
        path = BOOK / name
        text = path.read_text(encoding="utf-8")
        if "**In a life.**" in text:
            print(f"{name}: already annotated")
            continue
        heads = list(HEAD.finditer(text))
        out, cursor, added = [], 0, 0
        for i, m in enumerate(heads):
            n = int(m.group(1))
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            section = text[m.start():end]
            # Insert at the very end of the section, after its existing prose.
            body = section.rstrip()
            new = body + f"\n\n**In a life.** {IN_A_LIFE[n]}\n\n"
            out.append(text[cursor:m.start()])
            out.append(new)
            cursor = end
            added += 1
        out.append(text[cursor:])
        if added:
            path.write_text("".join(out), encoding="utf-8")
            total += added
            print(f"{name}: annotated {added} circuits")
    print(f"\ntotal circuits annotated: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
