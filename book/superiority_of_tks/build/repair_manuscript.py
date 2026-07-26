r"""
Repair SOURCE_ORIGINAL.md into a single, correctly ordered manuscript.

The source is three draft layers concatenated in the wrong order. Forensic
analysis (2,716 paragraphs hashed; zero duplicate hashes; cross-region 5-gram
Jaccard 0.0000) established that almost NO prose is redundant -- the book is
structurally disordered and cosmetically unfinished, not substantively
duplicated. Total prose deleted here is under 2% of the manuscript.

What this fixes
---------------
1. ORDER. Layer 1's own appendices and its terminal conclusion sat at PDF
   262-283, so the reader hit "Now Go Build Something" a third of the way in
   and then found 263 more pages. Appendices move to the back; the terminal
   conclusion folds into the Epilogue.
2. NUMBERING. Five chapters carried no number at all. Chapter 20 (a thin
   1,309-word workshop set) is superseded 15x by the full Part on workshops and
   is dropped; everything after renumbers. Result: Chapters 1-27, each once.
3. APPENDICES. Two colliding A-E series plus a stray F-G. Relabelled to a
   single A-L run. Appendix B's heading was lost entirely (its content survived
   headless between A and C) and is restored.
4. PART STRUCTURE. Parts II and III were never declared in the body, and two
   different sections both called themselves "PART V". Declared I-VII, no
   collisions.
5. SCAFFOLDING. 26 drafting stamps ("(Chapter 15 Complete: ... 4,500 words.)"),
   11 page-break comments, and the terminal production-statistics block are
   removed. 516 stray code fences are dropped -- they wrap nothing, and the
   previous PDF printed them literally.
6. HEADINGS. Like the CAS manuscripts, this source marks headings with a single
   leading space rather than '#'. Those are promoted so the book has real
   navigation in print and EPUB. Fenced regions are tracked and left alone.
7. COPYRIGHT. The page named no rights holder, no year, no ISBN and no
   publisher -- the string "Little Henderson" appeared nowhere in 181,325
   words. Replaced with a complete page.
8. CROSS-REFERENCES. Three point at pre-insertion chapter numbers.

Run:  python repair_manuscript.py
Out:  ../MANUSCRIPT.md  +  a report on stdout
"""

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BOOK = Path(__file__).resolve().parent.parent
SRC = BOOK / "SOURCE_ORIGINAL.md"
DST = BOOK / "MANUSCRIPT.md"

RAW = SRC.read_text(encoding="utf-8", errors="replace").splitlines()

sys.path.insert(0, str(Path(__file__).parent))
from figures import FIGURES  # noqa: E402

# heading text -> (tikz, label, caption); emitted just before that heading
FIG_BY_ANCHOR = {a: (b, l, c) for a, b, l, c in FIGURES}


def seg(a, b):
    """1-based inclusive line range from the original source."""
    return RAW[a - 1:b]


# --------------------------------------------------------------------------
# Region boundaries, established from the structural map of SOURCE_ORIGINAL.md
# --------------------------------------------------------------------------
R = {
    "title":        (1, 34),
    "copyright":    (35, 50),      # replaced wholesale
    "dedication":   (51, 72),
    "preface":      (73, 138),
    "prologue":     (139, 198),
    "toc":          (199, 460),    # dropped; LaTeX generates the real one
    "part1_hdr":    (461, 468),
    "introduction": (469, 535),
    "ch1_13":       (536, 9427),
    "apxA":         (9428, 9644),  # 40 Elements
    "apxB":         (9645, 9709),  # RPM Troubleshooting -- heading was lost
    "apxC":         (9710, 9824),  # TKS vs The World
    "apxD":         (9825, 9880),  # 22 Acquisitions
    "apxE":         (9881, 9938),  # 28 Foundations
    "terminal":     (9939, 9995),  # Layer-1 ending -> folds into Epilogue
    "ch14_16":      (9996, 12097),
    "partv_clash":  (12098, 12101),  # dropped: collides with the real Part V
    "ch17_19":      (12102, 13146),
    "ch20_thin":    (13147, 13463),  # dropped: superseded 15x by the workshops
    "ch21_22":      (13464, 14018),
    "ch23":         (14019, 14335),
    "apxF":         (14336, 14739),  # NCD Logic Circuit Methodology
    "apxG":         (14740, 14891),  # Cross-Reference Tables
    "l3_part4":     (14892, 14895),
    "l3_ch_a":      (14896, 16691),  # Life Cycles, Timing Windows, Protocols
    "l3_part5":     (16692, 16695),
    "l3_workshops": (16696, 20066),
    "l3_part6":     (20067, 20070),
    "l3_ch_b":      (20071, 20920),  # Three Controls, Forty Days
    "apx_hdrs":     (20921, 20929),  # "NEW APPENDICES" / "APPENDICES" -- dropped
    "apxH":         (20930, 21096),  # Quick Reference Tables
    "apxI":         (21097, 21277),  # Operation Templates
    "apxJ":         (21278, 21353),  # Glossary
    "apxK":         (21354, 21412),  # Safety Checklist
    "apxL":         (21413, 21493),  # Practice Schedule
    "epilogue":     (21494, 21611),
    "index":        (21612, 21833),
    "about":        (21834, 21849),
    "end_stats":    (21850, len(RAW)),  # dropped
}

# Chapter renumbering. Ch20 (thin workshops) is dropped, so 21->20, 22->21,
# 23->22, and the five unnumbered chapters take 23-27.
RENUMBER = {21: 20, 22: 21, 23: 22}

UNNUMBERED = {
    "The Prerequisite Life Cycles": 23,
    "Timing Windows": 24,
    "The Protocols Decoded": 25,
    "The Three Controls": 26,
    "The Forty Days": 27,
}

APPENDIX_TITLES = {
    "apxA": "The 40 Elements — Your Periodic Table of Reality",
    "apxB": "Advanced RPM Troubleshooting",
    "apxC": "TKS vs. The World — A Comparative Chart",
    "apxD": "The 22 Acquisitions — Mapping the Flow of Consciousness",
    "apxE": "The 28 Foundations — The Core Drives Across Four Worlds",
    "apxF": "NCD Logic Circuit Methodology — Diagramming Consciousness Operations",
    "apxG": "Cross-Reference Tables — Integrated TKS Quick Lookup",
    "apxH": "Quick Reference Tables",
    "apxI": "Operation Templates",
    "apxJ": "Glossary of Terms",
    "apxK": "Safety Checklist",
    "apxL": "Recommended Practice Schedule",
}
APPENDIX_ORDER = ["apxA", "apxB", "apxC", "apxD", "apxE", "apxF",
                  "apxG", "apxH", "apxI", "apxJ", "apxK", "apxL"]

PARTS = [
    ("I", "The Critique"),
    ("II", "The Framework"),
    ("III", "The Prerequisites"),
    ("IV", "Advanced Applications"),
    ("V", "The Practical System"),
    ("VI", "Applied Manifestation"),
    ("VII", "Advanced Operations"),
]

# Chapter numbers that open each part (post-renumber).
PART_OPENS = {1: "I", 3: "II", 10: "III", 14: "IV", 23: "V", 26: "VII"}

COPYRIGHT = """# Copyright

**The Superiority of TKS**
*The Tootra Kabbalistic System: A Complete Operating Manual for Reality Engineering*

Copyright © 2026 Little Henderson. All rights reserved.

No part of this publication may be reproduced, distributed, or transmitted in
any form or by any means, including photocopying, recording, or other
electronic or mechanical methods, without the prior written permission of the
author, except in the case of brief quotations embodied in critical reviews and
certain other noncommercial uses permitted by copyright law.

First Edition, 2026. Published by Noetic Compass Press.

ISBN: [pending publisher assignment]

*This book describes a system of practice. It is not medical, psychological,
financial, or legal advice, and it is not a substitute for professional care.
The operations described here are offered as a framework for reflection and
self-directed work. Decisions about your health, finances, relationships, and
safety remain yours, and are properly made with qualified professionals.*
"""

# The source page read only "The author prefers to remain behind the work...
# Test it. That's the only biography that matters." That stance is kept as the
# closing line -- but the book now carries a byline, and a reader who has spent
# 800 pages with a system is owed some account of where it came from. In this
# category the author's lineage and years of practice are a primary reason
# people buy at all.
ABOUT_AUTHOR = """**Little Henderson** is the author of *Majik and the True Kabbalah, the Book
of Tootra* — the work from which this system descends.

The Tootra Kabbalistic System was not assembled out of reading. It was worked,
tested, and revised against results over years of practice, and the parts that
did not survive contact with outcomes were cut. What is left is what functioned.

The same framework was later rebuilt in secular engineering terms as the
Cognitive Architecture System and filed as USPTO Provisional Application
#64/037,173. In that form it underpins Noetic Compass, an AI interpretability
suite that applies the ten Noetics to machine cognition and audits language
models for the same structural failures this book teaches you to find in
yourself.

By day the author inspects flight-grade satellite hardware to aerospace Class 3
acceptance criteria — a discipline built on naming a defect precisely instead of
gesturing at it, and on refusing to pass an unresolved failure downstream. That
is the same demand this book makes of you.

None of which should matter more than it deserves to. What matters is whether
the system functions when you apply it.

Test it. That is the only biography that counts.
"""

STAMP = re.compile(r"^\(.*\bComplete\b.*\)\s*$")
PAGEBREAK = re.compile(r"<!--\s*PAGE BREAK\s*-->", re.I)

# Emoji were used as decorative markers in section headings ("Foundation 1:
# Association / Unity (link-emoji)"). A black-and-white print interior renders
# them as blobs or not at all, so they are stripped for the print edition along
# with the variation selectors and zero-width joiners that follow them. The
# leftover empty brackets are cleaned up too.
# Deliberately narrow: the emoji planes plus the four non-plane pictographs
# actually used, the variation selectors and the ZWJ. It must NOT touch the
# arrow block (U+2190-21FF), the math operators (U+2200-22FF) or the
# box-drawing block (U+2500-257F) -- all three carry meaning in this book.
EMOJI = re.compile("[\U0001F000-\U0001FAFF❤⚡⛓⏳︎️‍]")
EMPTY_BRACKETS = re.compile(r"\(\s*\)|\[\s*\]|\{\s*\}")
CH_LINE = re.compile(r"^ Chapter\s+(\d+)\s*[:–—-]\s*(.+)$")
CH_UNNUM = re.compile(r"^#\s*Chapter:\s*(.+)$")
CH_H1 = re.compile(r"^#\s*Chapter\s+(\d+)\s*[:–—-]\s*(.+)$")

stats = {"stamps": 0, "fences": 0, "pagebreaks": 0, "promoted": 0, "rules": 0,
         "emoji": 0, "titles": 0, "softened": 0, "figures": 0}


def clean_and_promote(lines, allow_headings=True):
    """Strip scaffolding; promote single-space headings to '##'.

    Fenced blocks are PRESERVED. The 516 fence lines in the source are 258
    correctly paired blocks, all with content and 33 of them holding ASCII
    box-drawing diagrams. The previous PDF printed the fences literally because
    that build never ran the Markdown through a renderer -- the fences
    themselves are correct and load-bearing.
    """
    out = []
    in_code = False
    for ln in lines:
        s = ln.strip()

        if s.startswith("```"):
            in_code = not in_code
            stats["fences"] += 1
            out.append(ln)
            continue
        if in_code:
            out.append(ln)      # verbatim: no stripping, no promotion
            continue
        if PAGEBREAK.search(ln):
            stats["pagebreaks"] += 1
            continue
        if STAMP.match(s):
            stats["stamps"] += 1
            continue
        if s == "---":
            stats["rules"] += 1
            continue

        if EMOJI.search(ln):
            stats["emoji"] += len(EMOJI.findall(ln))
            ln = EMOJI.sub("", ln)
            ln = EMPTY_BRACKETS.sub("", ln)
            ln = re.sub(r"[ \t]{2,}", " ", ln).rstrip()
            s = ln.strip()
            if not s:
                continue

        if allow_headings and ln.startswith(" ") and not ln.startswith("  ") and s:
            if 0 < len(s) <= 95 and not s.endswith(".") and not s[:1].islower():
                head = soften_heading(f"## {s}")
                if head in FIG_BY_ANCHOR:
                    body, label, cap = FIG_BY_ANCHOR.pop(head)
                    out += ["", "```{=latex}", "\\begin{figure}[htbp]",
                            "\\centering", body.strip(),
                            f"\\caption{{{cap}}}\\label{{fig:{label}}}",
                            "\\end{figure}", "```", ""]
                    stats["figures"] += 1
                out += ["", head, ""]
                stats["promoted"] += 1
                continue

        out.append(ln)
    return out


def chapter_block(key, want_part=True, lines_override=None):
    """Emit a region's chapters with corrected numbering and part dividers."""
    lines = lines_override if lines_override is not None else seg(*R[key])
    out = []
    for ln in lines:
        m = CH_LINE.match(ln) or CH_H1.match(ln)
        if m:
            num, title = int(m.group(1)), m.group(2).strip()
            num = RENUMBER.get(num, num)
            if want_part and num in PART_OPENS:
                out += part_divider(PART_OPENS[num])
            # memoir's \chapter already prints "Chapter N"; emit the bare title
            # so the printed page and the TOC do not read "3 Chapter 3: ...".
            emitted_chapters.append(num)
            out += ["", soften_heading(clean_title(f"# {title}")), ""]
            continue
        m = CH_UNNUM.match(ln)
        if m:
            title = m.group(1).strip()
            num = UNNUMBERED.get(title)
            if num:
                if want_part and num in PART_OPENS:
                    out += part_divider(PART_OPENS[num])
                emitted_chapters.append(num)
                out += ["", soften_heading(f"# {title}"), ""]
                continue
        out.append(ln)
    return clean_and_promote(out)


# Drafting labels that leaked into chapter titles. These are production
# markers, not part of the title, and they print in the TOC and in Amazon's
# "Look Inside". "Deep Dive" is left alone where it is genuinely part of a
# title (Chapters 15 and 16); only the parenthetical markers go.
TITLE_CLEANUPS = [
    (" (EXTREME ULTRA MAX MEGA Deep Dive Expansion - Part 1)", ""),
    (" (Using the REAL 12 Prerequisites - D/W/P Cycles - EXTREME ULTRA MAX MEGA"
     " Deep Dive Expansion - Part 3)", " (Using the 12 Prerequisites and D/W/P Cycles)"),
    (" (Deep Dive Expansion)", ""),
    (" (Deep Dive)", ""),
    (" (Re-Expanded Edition)", ""),
]


def clean_title(line):
    for old, new in TITLE_CLEANUPS:
        if old in line:
            line = line.replace(old, new)
            stats["titles"] += 1
    return line


# Profanity is kept in the prose -- 66 instances, it is the book's voice and the
# Preface defends it explicitly. It is removed from HEADINGS ONLY, because
# headings are what appear in the table of contents, in Amazon's "Look Inside",
# and in the Kindle sample. Amazon Advertising rejects Sponsored Products for
# books whose content includes profanity, and that is the main discovery
# channel for a self-published title. This is a distribution decision, not an
# editorial one.
HEADING_SOFTENING = [
    ("Ditch the Dusty Relic, Get a Fucking Toolkit",
     "Ditch the Dusty Relic, Get a Real Toolkit"),
    ("Ditching the Mystical Mind-Fucks for Functional Mastery",
     "Ditching the Mystical Mind-Games for Functional Mastery"),
    ("The Noetic Symphony: How the Fuck They Actually Work Together",
     "The Noetic Symphony: How They Actually Work Together"),
    ("The 40 Fucking Elements - Reality Decoded",
     "The 40 Elements: Reality Decoded"),
    ("The 7 Foundations - Reality's Fucking Bedrock",
     "The 7 Foundations: Reality's Bedrock"),
    ("Why TKS Kicks Other Esoteric Ass (Beyond Kabbalah)",
     "Why TKS Outclasses Every Other Esoteric System"),
    ("Ditching the Bullshit: What Are the REAL Prerequisites?",
     "Cutting Through the Noise: What Are the REAL Prerequisites?"),
    ("The Desire Tree: Mapping Your Path (and Your Bullshit)",
     "The Desire Tree: Mapping Your Path (and Your Excuses)"),
    ("Doubt, Naysayers, and Other Assorted Bullshit",
     "Doubt, Naysayers, and Other Assorted Noise"),
    ("Common Ways You Fuck Up Skill Acquisition (Avoid These, Dumbass)",
     "Common Ways You Botch Skill Acquisition (Avoid These)"),
    ("AI, Neurofeedback, and Cosmic Fucking Domination",
     "AI, Neurofeedback, and Total Domination"),
    ("Introduction: What the Fuck is Hyperstition?",
     "Introduction: What Is Hyperstition?"),
]


def soften_heading(line):
    for old, new in HEADING_SOFTENING:
        if old in line:
            line = line.replace(old, new)
            stats["softened"] += 1
    return line


def fix_appendix_b(lines):
    """Appendix B lost its heading and starts its item list at 6.

    The first-line diagnostics it refers to ("you've checked the initial
    diagnostics") are real -- they are Chapter 11's list, which runs 1-6. The
    appendix was numbered to continue from 5, so its item 6 collides with
    Chapter 11's item 6. Since the appendix now carries its own heading and
    stands alone in the back matter, its five items are renumbered 1-5 and the
    lead-in is pointed explicitly at Chapter 11.
    """
    out = []
    n = 0
    for ln in lines:
        m = re.match(r"^(\s*)(\d+)\.(\s+)(\S.*)$", ln)
        if m and m.group(2) in {"6", "7", "8", "9", "10"}:
            n += 1
            out.append(f"{m.group(1)}{n}.{m.group(3)}{m.group(4)}")
            continue
        if ln.startswith("Okay, so you've checked the initial diagnostics"):
            out.append(
                "You have run the first-line diagnostics in Chapter 11 and you "
                "are still stuck. Time to dig deeper into the subtler failure "
                "modes."
            )
            continue
        out.append(ln)
    return out


def unnumbered_chapter(title):
    """A chapter that carries no number but still appears in the TOC."""
    up = title.upper().replace("&", r"\&")
    esc = title.replace("&", r"\&")
    return ["", "```{=latex}",
            rf"\chapter*{{{esc}}}",
            rf"\addcontentsline{{toc}}{{chapter}}{{{esc}}}",
            rf"\markboth{{{up}}}{{{up}}}",
            "```", ""]


def demote_h1(lines, pattern):
    """Demote stray H1s that are really sections inside a chapter."""
    out = []
    for ln in lines:
        if re.match(pattern, ln):
            out.append("#" + ln)   # '# X' -> '## X'
        else:
            out.append(ln)
    return out


emitted_parts = set()
emitted_chapters = []


def part_divider(roman):
    if roman in emitted_parts:
        return []
    emitted_parts.add(roman)
    title = dict(PARTS)[roman]
    return ["", "```{=latex}", rf"\part{{{title}}}", "```", ""]


# --------------------------------------------------------------------------
# Assemble
# --------------------------------------------------------------------------
doc = []

# Title page, copyright and dedication are supplied by frontmatter_tks.tex so
# they can be typeset as real book front matter rather than as chapters.
doc += unnumbered_chapter("Preface")
doc += clean_and_promote(seg(*R["preface"])[1:])
doc += unnumbered_chapter("Prologue")
doc += clean_and_promote(seg(*R["prologue"])[1:])

# Main matter starts here; Part I divider comes from PART_OPENS on Chapter 1.
doc += ["", "```{=latex}", r"\mainmatter", "```", ""]
doc += clean_and_promote(seg(*R["introduction"]))

doc += chapter_block("ch1_13")
doc += chapter_block("ch14_16")
doc += chapter_block("ch17_19")
doc += chapter_block("ch21_22")
doc += chapter_block("ch23")

# PROTOCOL ONE/TWO/THREE are sections inside Chapter 25, not chapters.
l3a = demote_h1(seg(*R["l3_ch_a"]), r"^#\s*PROTOCOL\s+(ONE|TWO|THREE)\b")
doc += chapter_block("l3_ch_a", lines_override=l3a)

# The five Workshops are the content of Part VI. They are chapter-level but
# carry their own naming, so they are unnumbered rather than "Chapter 28:
# Workshop One: ...".
doc += part_divider("VI")
for ln in clean_and_promote(seg(*R["l3_workshops"])):
    m = re.match(r"^#\s*(Workshop\s+\w+:.*)$", ln)
    if m:
        doc += unnumbered_chapter(m.group(1).strip())
    else:
        doc.append(ln)

doc += chapter_block("l3_ch_b")

# Back matter -------------------------------------------------------------
doc += ["", "```{=latex}", r"\backmatter", "```", ""]

# Epilogue absorbs Layer 1's terminal conclusion, which had been stranded on
# page 283 with 263 pages of book still to come.
doc += unnumbered_chapter("Epilogue")
doc += clean_and_promote(seg(*R["epilogue"])[1:])
doc += clean_and_promote(seg(*R["terminal"]))

doc += ["", "```{=latex}", r"\appendix", "```", ""]
for i, key in enumerate(APPENDIX_ORDER):
    letter = chr(ord("A") + i)
    body = seg(*R[key])
    # drop the region's own (possibly absent or wrongly lettered) heading line
    body = [l for l in body
            if not re.match(r"^\s*#*\s*APPENDIX\s+[A-Z]\s*[:–—-]", l, re.I)
            and not re.match(r"^ Appendix\s+[A-Z]\s*[:–—-]", l)]
    if key == "apxB":
        body = fix_appendix_b(body)
    doc += ["", f"# {APPENDIX_TITLES[key]}", ""]
    doc += clean_and_promote(body)

doc += unnumbered_chapter("Index")
doc += clean_and_promote(seg(*R["index"])[1:])
doc += unnumbered_chapter("About the Author")
doc += ["", ABOUT_AUTHOR, ""]

# --------------------------------------------------------------------------
# Cross-reference corrections (pre-insertion numbering survived in 3 places)
# --------------------------------------------------------------------------
text = "\n".join(doc)
XREF = [
    ("Hyperstition Engine (Chapter 11)", "Hyperstition Engine (Chapter 14)"),
    ("Use Overton mechanics (Chapter 12)", "Use Overton mechanics (Chapter 15)"),
    ("the major contenders discussed in Chapter 7",
     "the major contenders discussed in Chapter 9"),
]
xref_fixed = 0
for old, new in XREF:
    if old in text:
        text = text.replace(old, new)
        xref_fixed += 1

# collapse runs of blank lines
text = re.sub(r"\n{4,}", "\n\n\n", text)
DST.write_text(text + "\n", encoding="utf-8")

# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
words_before = len(SRC.read_text(encoding="utf-8", errors="replace").split())
words_after = len(text.split())
chapters = len(emitted_chapters)
appendices = sum(1 for k in APPENDIX_ORDER)
parts = len(re.findall(r"\\part\{", text))

print(f"wrote {DST}")
print(f"  words     : {words_before:,} -> {words_after:,} "
      f"({words_before - words_after:,} removed, "
      f"{(words_before - words_after) / words_before * 100:.1f}%)")
print(f"  chapters  : {chapters} (expect 27, each exactly once)")
print(f"  appendices: {appendices} (A-L)")
print(f"  parts     : {parts} (expect 7)")
print(f"  headings promoted    : {stats['promoted']}")
print(f"  drafting stamps cut  : {stats['stamps']}")
print(f"  fenced blocks kept   : {stats['fences'] // 2}")
print(f"  page-break comments  : {stats['pagebreaks']}")
print(f"  decorative emoji cut : {stats['emoji']}")
print(f"  drafting labels cut  : {stats['titles']}")
print(f"  headings softened    : {stats['softened']}")
print(f"  figures inserted     : {stats['figures']}")
print(f"  '---' rules cut      : {stats['rules']}")
print(f"  cross-refs corrected : {xref_fixed}/3")

nums = emitted_chapters
missing = [i for i in range(1, 28) if i not in nums]
dupes = sorted({i for i in nums if nums.count(i) > 1})
print(f"  chapter sequence     : {'OK 1-27' if not missing and not dupes else ''}"
      f"{' MISSING ' + str(missing) if missing else ''}"
      f"{' DUPLICATE ' + str(dupes) if dupes else ''}")
