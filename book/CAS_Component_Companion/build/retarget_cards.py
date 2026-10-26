#!/usr/bin/env python3
"""Re-aim the 56-card deck at human experience.

The book now leads with lived experience and states all four registers for every
symbol. The deck has to match, or the two artifacts teach different things.

Body labels change from ELECTRICAL / COGNITIVE / EXAMPLE / GUARD to
**THE PART / IN LIFE / REGISTERS / GUARD** on component cards, and to
**WHAT IT IS / IN A LIFE / THE CHAIN / GUARD** on the ten circuit cards.
Every component card carries one compact line naming all four registers.

Only the four body arguments of each card are rewritten; the number, name,
badge, symbol and tagline are left byte-for-byte alone. Idempotent.
"""
from __future__ import annotations

from pathlib import Path

BUILD = Path(__file__).resolve().parent
CARDS = BUILD / "companion_cards.tex"
BS = chr(92)

from retarget_data import CIRCUITS, COMPONENTS  # noqa: E402


def args_with_spans(text, start):
    """[(value, content_start, content_end)] for consecutive {..} groups."""
    out, i = [], start
    while True:
        while i < len(text) and text[i] in " \t\r\n%":
            i += 1
        if i >= len(text) or text[i] != "{":
            break
        depth, j = 1, i + 1
        while j < len(text) and depth:
            if text[j] == BS:
                j += 2
                continue
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        out.append((text[i + 1:j - 1], i + 1, j - 1))
        i = j
    return out, i


def rewrite(text, macro, num, body):
    """Replace the four body arguments of one card."""
    key = BS + macro + "{" + str(num) + "}"
    k = text.find(key)
    if k == -1:
        print(f"  ! {macro} {num} not found")
        return text
    args, _ = args_with_spans(text, k + len(key))
    if len(args) < 8:
        print(f"  ! {macro} {num}: only {len(args)} args")
        return text
    first = args[4]
    last = args[7]
    # args_with_spans returns content spans, so the opening brace of arg 4 and
    # the closing brace of arg 7 are OUTSIDE the replaced range and must not be
    # re-emitted here.
    new = ("}%\n{".join(body))
    return text[:first[1]] + new + text[last[2]:]


def main() -> int:
    text = CARDS.read_text(encoding="utf-8")

    text = text.replace(r"\BodyLine{ELECTRICAL}", r"\BodyLine{THE PART}")
    text = text.replace(r"\BodyLine{COGNITIVE}", r"\BodyLine{IN LIFE}")
    text = text.replace(r"\BodyLine{EXAMPLE}", r"\BodyLine{REGISTERS}")

    n = 0
    for num, body in COMPONENTS.items():
        text = rewrite(text, "PCard", num, list(body))
        n += 1
    for num, life in CIRCUITS.items():
        key = BS + "CCard{" + str(num) + "}"
        k = text.find(key)
        args, _ = args_with_spans(text, k + len(key))
        body = [args[4][0], life, args[6][0], args[7][0]]
        text = rewrite(text, "CCard", num, body)
        n += 1

    # Circuit cards get their own labels for the same four lines.
    if r"\ChainBlock" not in text:
        text = text.replace(
            r"""\newcommand{\CCard}[9]{\CARD{#1}{#2}{#3}{\ChainRow{#4}}{\TagLineRow{#5}}{#6}{#7}{#8}{#9}}""",
            r"""\newcommand{\ChainBlock}[4]{%
  \BodyLine{WHAT IT IS}{#1}%
  \BodyLine{IN A LIFE}{#2}%
  \BodyLine{THE CHAIN}{#3}%
  \BodyLine{GUARD}{#4}}
% #1 number  #2 name  #3 badge  #4 chain  #5 tagline  #6..9 body
\newcommand{\CCard}[9]{%
  \fbox{\begin{minipage}[t][\cardInH][t]{\cardInW}\raggedright\sloppy
    \TitleRow{#1}{#2}{#3}%
    \CardMidRule
    \ChainRow{#4}\TagLineRow{#5}%
    \CardMidRule
    \ChainBlock{#6}{#7}{#8}{#9}%
  \end{minipage}}}""")

    CARDS.write_text(text, encoding="utf-8")
    print(f"rewrote {n} cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
