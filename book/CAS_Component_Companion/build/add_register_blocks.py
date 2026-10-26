#!/usr/bin/env python3
"""Insert an explicit four-register block into every component entry.

The claim this guide makes is that each electrical symbol is isomorphic to
**mental, emotional, physical and spiritual** human experience — which are the
framework's four Registers, read in ordinary language:

    |A Analytical = mental     |f Affective  = emotional
    |E Embodied   = physical   |T Transcendent = spiritual

A mapping that only ever mentions one register has not made that claim. This
script puts all four on the page for every entry, immediately after the opening
scenario, so the claim is visible forty-two times rather than asserted once.

Run once from build/; it edits the chapter files in place and is idempotent.
"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent

# heading keyword -> (mental |A, emotional |f, physical |E, spiritual |T)
REGISTERS = {
    "Resistor": (
        "counting to ten before you answer; the argument you build and then decline to make",
        "not letting someone see how much they have just hurt you",
        "the slow breath; the hand that stops halfway to the phone",
        "restraint kept because of who you intend to be, when nobody would ever know",
    ),
    "Capacitor": (
        "a fact you can still recall on demand",
        "warmth that colours a room twenty years later",
        "the softening in your shoulders at the sound of a voice",
        "part of what you would name if asked who you are",
    ),
    "Inductor": (
        "the reasoning that keeps arriving back at the old conclusion",
        "loyalty to a person or an idea you have already outgrown",
        "the hand that cracks a knuckle before you notice",
        "a faith or a vocation that will not be hurried into changing",
    ),
    "Varactor": (
        "reframing: the same fact, carrying less weight",
        "a hurt that softens from agony into tenderness",
        "a flinch that becomes a pause",
        "a loss that slowly becomes a source of meaning rather than a wound",
    ),
    "LC tank": (
        "the argument you could have in your sleep — the same three points",
        "the subject that always ends the same way",
        "the room, the hour, the particular tone that sets it off",
        "the unresolved question about what it all meant, re-asked every time",
    ),
    "Diode": (
        "knowing something you cannot un-know",
        "forgiveness that is real, and trust that did not come back with it",
        "a body that will not relax in that person's presence",
        "a blessing you can still give, in one direction, to someone you cannot let back in",
    ),
    "Zener": (
        "the smooth, agreeable sentence that arrives once you are past your limit",
        "going flat and warm and unreachable under one specific criticism",
        "the face that stops moving; the voice that levels out",
        "protecting a core commitment instead of arguing about it",
    ),
    "Transformer": (
        "the same idea expressed at three levels of abstraction",
        "saying a hard thing gently without removing the hardness",
        "pitch, pace and posture adjusted to whoever is in the room",
        "carrying a meaning across a gulf — to a child, a culture, or a generation",
    ),
    "Photodiode": (
        "a new fact that changes what you thought you knew",
        "being moved by music, a building, or a face",
        "the hair lifting; the breath catching",
        "awe — an encounter with something you did not make",
    ),
    "Bridge rectifier": (
        "realising you cannot say whether the day was good or bad, only that it was loud",
        "keyed up with no direction; arousal without valence",
        "restlessness, prickling skin, no target",
        "**no honest reading.** This is why the badge is PED. `|T` cannot be manufactured from raw activation",
    ),
    "CJT": (
        "one sentence, two people, two entirely different conclusions",
        "the same remark landing as mild irritation in one and a wound in the other",
        "the stomach dropping before any thought has formed",
        "a sentence that lands as calling, because of the life it meets",
    ),
    "Op-amp": (
        "building a three-week theory out of one flat tone of voice",
        "one cool goodbye, and a certainty that you are not loved",
        "hearing a quarter-tone in a voice before you know you heard it",
        "reading a small event as a verdict on your whole direction — usually a gain error",
    ),
    "Differential pair": (
        "two people given identical news, reaching different conclusions; the difference is them",
        "the same bereavement, two different depths of grief",
        "the same cold room, and only one of you shivers",
        "the same loss, and one person's faith holds while another's does not",
    ),
    "Current mirror": (
        "an inherited way of reasoning you never chose and never noticed",
        "your mother's dread arriving in your chest at an airport",
        "a gesture, a posture, a way of holding a cup",
        "an inherited faith, or an inherited cynicism",
    ),
    "Active load": (
        "the moment a vague suspicion becomes a decision",
        "unease turning into resolve",
        "standing up and reaching for your coat",
        "a long-felt sense that something is wrong becoming a commitment to change a life",
    ),
    "Oscillator": (
        "rumination — the loop that produces no new thought",
        "a mood sustaining itself without new cause",
        "pacing; the body keeping the loop running",
        "a question about meaning that returns every night and is never answered",
    ),
    "Crystal": (
        "a principle you apply the same way every time",
        "warmth that is the same on a bad day as a good one",
        "a daily practice kept at a fixed hour",
        "integrity — a reference other people set their clocks by",
    ),
    "PLL": (
        "absorbing a team's way of thinking in a month",
        "moods synchronising with a partner's",
        "falling into step; a sleep schedule entraining the household",
        "taking on a community's sense of what matters",
    ),
    "ADC": (
        "finding the word for what you have been feeling for three weeks",
        "the feeling becoming nameable, and therefore bearable",
        "noticing the clenched jaw and calling it tension",
        "naming a nameless longing as a question of meaning",
    ),
    "DAC": (
        "a decision becoming a plan",
        "a commitment showing up as daily kindness",
        "the decision rendered as habit, posture and routine",
        "a conversion becoming a life's work",
    ),
    "AND": (
        "two conditions that must both hold before you act",
        "love and trust as separate flags; either one alone is not enough",
        "calm body **and** willing mind — both, or you will not sleep",
        "conviction together with practice",
    ),
    "OR": (
        "any one of three reasons is enough to stop",
        "any one of several feelings means leave",
        "any one physical warning sign",
        "any one thing that breaks a commitment",
    ),
    "NOT": (
        "\u201cI'm not angry\u201d as a threshold statement, not a fact",
        "equanimity misread by others as coldness",
        "stillness that is not calm",
        "doubt that is not disbelief",
    ),
    "NAND": (
        "the one combination that must never both be true",
        "exhaustion plus resentment: stop",
        "pain plus pushing through",
        "a compromise that would defeat the entire point",
    ),
    "NOR": (
        "act only when every condition is quiet",
        "have the conversation only when nobody is raw",
        "only when rested, fed and well",
        "only when the motive is clean",
    ),
    "XOR": (
        "two conclusions, only one of which can be acted on",
        "two loyalties, one choice",
        "two commitments at the same hour",
        "two callings; you cannot serve both",
    ),
    "XNOR": (
        "agreement — both think it, or neither does",
        "mutual indifference mistaken for peace",
        "two bodies relaxing at the same moment",
        "shared conviction",
    ),
    "MUX": (
        "which argument you reach for depending on who is asking",
        "the version of your warmth that appears for family",
        "accent, posture and volume changing with the room",
        "which self you present in a place of worship and a place of work",
    ),
    "DEMUX": (
        "one insight routed to one problem",
        "one feeling allowed into one relationship",
        "one habit applied in one setting",
        "a conviction expressed in one domain of life",
    ),
    "Relay": (
        "one sentence that changes a career",
        "\u201cI'm leaving\u201d — and everything changes",
        "a small movement with a large consequence",
        "a vow that reorganises a life",
    ),
    "Schmitt": (
        "deciding once instead of hourly",
        "holding a decision through a bad night",
        "steady hands because the decision is settled",
        "a commitment that does not wobble with mood",
    ),
    "Regulator": (
        "attention restored by two nights of sleep",
        "mood returning to baseline",
        "sleep, food, movement",
        "a practice that keeps you oriented",
    ),
    "Fuse": (
        "a rule that ends the argument permanently",
        "the last time",
        "leaving the building",
        "a line that cannot be crossed without breaking faith",
    ),
    "Circuit breaker": (
        "\u201cwe will talk about it tomorrow\u201d",
        "leaving the room for twenty minutes",
        "going for a walk mid-argument",
        "a sabbath — a deliberate stop that can be resumed",
    ),
    "Rail": (
        "curiosity as fuel for thinking",
        "connection as fuel for feeling",
        "vitality: sleep and food",
        "purpose as the supply that makes the rest worth running",
    ),
    "Reference": (
        "the assumption you reason from",
        "what you call a normal amount of love",
        "what your body calls a normal level of tension",
        "what you assume a life is for",
    ),
    "Probe": (
        "noticing a thought as a thought",
        "naming the feeling while it is happening",
        "noticing the jaw, the breath, the shoulders",
        "noticing what you are actually living for, without editing it",
    ),
    "Switch": (
        "deciding not to think about it tonight",
        "deciding to let it go, for now",
        "putting the phone in the other room",
        "choosing to stop asking the question for a season",
    ),
    "Meter": (
        "\u201cI could not concentrate for more than ten minutes\u201d",
        "\u201cthe sadness was 6 of 10\u201d — with the scale stated",
        "resting heart rate; hours slept",
        "how often you acted on what you say you value",
    ),
    "Net label": (
        "naming the belief",
        "naming the feeling",
        "naming the sensation",
        "naming what you are living for",
    ),
    "Solid arrow": (
        "this belief leads to that conclusion",
        "this fear leads to that withdrawal",
        "this tension leads to that headache",
        "this commitment leads to that way of living",
    ),
    "Dashed arrow": (
        "the conclusion returning to reshape the premise",
        "the mood returning to colour the memory",
        "the posture returning to deepen the state",
        "the way you live returning to change what you believe",
    ),
}

BLOCK = """**The same thing, in all four registers.**

- `|A` **Mental** — {a}
- `|f` **Emotional** — {f}
- `|E` **Physical** — {e}
- `|T` **Spiritual** — {t}
"""

HEAD = re.compile(r"^### ([A-Za-z][^\n]*?) — ", re.MULTILINE)
EXPERIENCE = re.compile(r"^\*\*The experience\.\*\*.*?(?=\n\n)", re.DOTALL | re.MULTILINE)


def key_for(heading: str) -> str | None:
    for key in sorted(REGISTERS, key=len, reverse=True):
        if heading.startswith(key):
            return key
    return None


def main() -> int:
    total = 0
    for path in sorted(BOOK.glob("0[2-8]_*.md")):
        text = path.read_text(encoding="utf-8")
        if "**The same thing, in all four registers.**" in text:
            print(f"{path.name}: already annotated")
            continue
        heads = list(HEAD.finditer(text))
        out, cursor, added = [], 0, 0
        for i, m in enumerate(heads):
            key = key_for(m.group(1))
            if key is None:
                continue
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            section = text[m.start():end]
            exp = EXPERIENCE.search(section)
            if not exp:
                continue
            a, f, e, t = REGISTERS[key]
            block = "\n" + BLOCK.format(a=a, f=f, e=e, t=t)
            new_section = section[:exp.end()] + "\n" + block + section[exp.end():]
            out.append(text[cursor:m.start()])
            out.append(new_section)
            cursor = end
            added += 1
        out.append(text[cursor:])
        if added:
            path.write_text("".join(out), encoding="utf-8")
            total += added
            print(f"{path.name}: annotated {added} entries")
    print(f"\ntotal entries annotated: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
