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


# --------------------------------------------------------------------------
# Content corrections applied to the source lines before anything else.
#
# SOURCE_ORIGINAL.md is vendored untouched with a recorded sha256, so every
# correction lives here where it is reviewable, rather than being edited into
# the original. These are the passages a pre-publication sweep identified as
# carrying real reader risk -- care avoidance, uncredited third-party work,
# quoted lyrics, and assertions about a named living person.
# --------------------------------------------------------------------------
CONTENT_FIXES = [
    # The single most dangerous sentence in the three books: it anticipates a
    # reader substituting this practice for medical treatment and then
    # disclaims responsibility for the outcome.
    ("If you use TKS instead of medical treatment and get worse, that's on you. "
     "If you use TKS to supplement medical treatment and get better faster, "
     "that's the intended use.",
     "Do not use TKS instead of medical treatment. It is not a treatment and it "
     "does not replace one. Used alongside proper care, as a way of noticing "
     "your own patterns and staying engaged with your own recovery, it is doing "
     "the job it is meant to do. If you are unwell, see a clinician; nothing in "
     "this book changes that."),

    # Recasts a clinical finding as spiritual attainment, two lines after
    # conceding that practitioners "break down completely".
    ("Without proper grounding, advanced practitioners develop what psychiatrists "
     "would diagnose as dissociative disorders—but what's actually consciousness "
     "existing simultaneously across multiple probability streams.",
     "Without proper grounding, advanced practitioners can develop symptoms a "
     "psychiatrist would recognise as dissociative. Take that seriously and get "
     "assessed. Whatever else it may be, it is also exactly what it looks like, "
     "and it is the point at which the practice needs to stop rather than "
     "deepen."),

    ("After 30 days, patterns emerge. After 90 days, you know your condition "
     "better than most doctors.",
     "After 30 days, patterns emerge. After 90 days, you will know your own "
     "day-to-day patterns in a detail no appointment can capture — which is "
     "information to bring your doctor, not to replace them."),

    # Cialdini's six principles are reproduced by his own names as a
    # TKS-native taxonomy. The book credits CCRU and Overton correctly, which
    # makes this the one uncredited case.
    (" The Authority Pattern",
     " *The six patterns that follow were first catalogued by Robert Cialdini "
     "in* Influence: The Psychology of Persuasion *(1984). They are not "
     "original to TKS; what follows is a TKS analysis of why they work.*\n\n"
     " The Authority Pattern"),

    # Table 8 named four of the seven Foundations differently from the rest of
    # the book. Three of the four substitutes -- Opposition, Beauty, Victory --
    # are traditional Sefirot vocabulary that leaked in from another system.
    # The canonical names are fixed by fourteen chapter headings (Foundation N:
    # ... and Foundation N: ... Across the 4 Worlds), which agree with each
    # other and with the second appendix listing. Table 8 is the appendix the
    # Usage Guide sends readers to for diagnosis, so it is the worst place in
    # the book to carry a private naming scheme.
    ("**F2 Opposition**", "**F2 Wisdom / Knowledge**"),
    ("**F3 Beauty**", "**F3 Health / Life**"),
    ("**F6 Victory**", "**F6 Wealth / Structure**"),
    ("**F7 Abundance**", "**F7 Purpose / Rhythm**"),

    # The appendix titled "The 22 Acquisitions" published only 21 distinct
    # numbers: 10 was absent and its entry was printed as a second 12, so 12
    # appeared twice with contradictory roles ("Power to obtain..." and "Desire
    # to obtain..."). The appendix's own rule -- Foundation k uses 3k-2 Desire,
    # 3k-1 Wisdom, 3k Power -- settles it, and 21 of the 22 entries obey it:
    # Foundation 4 is {10 Desire, 11 Wisdom, 12 Power}. 11 Wisdom and 12 Power
    # are both already correct and present, so the duplicate is 10 Desire.
    ("   Acquisition 12: Desire to obtain companionship love friendship",
     "   Acquisition 10: Desire to obtain companionship love friendship"),

    # Song lyrics are the one category publishers pursue regardless of length,
    # and neither quotation is load-bearing -- both are tags on a name.
    ('- Nas ("I know I can be what I wanna be")', "- Nas"),
    ('- Big Daddy Kane ("I\'m giving lessons")', "- Big Daddy Kane"),

    # Asserts a living public figure's religious formation over his own stated
    # awareness.
    ("When Jay-Z talks about \"understanding,\" he's speaking Supreme "
     "Mathematics whether he's conscious of it or not.",
     "When a rapper uses \"understanding\" as a term of art, the vocabulary "
     "itself comes from Supreme Mathematics, whatever any individual artist "
     "takes it to mean."),

    # The reading map in "How to Use This Book" gave chapter ranges matching no
    # version of the book, and omitted Part IV entirely -- nine chapters. It is
    # the first thing a reader uses, so it misrouted them for 800 pages. This
    # predates the repair; the ranges below are the delivered ones.
    ("**PART I-III: THE FOUNDATIONS (Chapters 1-23)**\n"
     "- Chapters 1-2: Clear out your old bullshit. Understand why traditional systems fail functionally.\n"
     "- Chapters 3-6: Learn the TKS framework – the 4 Worlds, 10 Noetics, 40 Elements, 7 Foundations. This is the operating system.\n"
     "- Chapters 7-8: See why TKS outperforms other systems and learn the RPM methodology – your diagnostic and operational tool.\n"
     "- Chapters 9-23: Apply the system to real manifestation and glimpse where this is all heading.",
     "**PARTS I-III: THE FOUNDATIONS (Chapters 1-13)**\n"
     "- Chapters 1-2: Clear out the old assumptions. Understand why traditional systems fail functionally.\n"
     "- Chapters 3-8: Learn the framework – the 4 Worlds, the 10 Noetics, the 40 Elements, the 7 and 28 Foundations. This is the operating system.\n"
     "- Chapters 9-10: See why TKS outperforms other systems, and learn the Recursive Prerequisite Model – your diagnostic and operational tool.\n"
     "- Chapters 11-13: Apply it to manifestation, and glimpse where this is all heading.\n"
     "\n"
     "**PART IV: ADVANCED APPLICATIONS (Chapters 14-22)**\n"
     "- Hyperstition, the Overton Window, social engineering, the mathematical formalism, expression scenarios, the NJT, the operations workbook, mastery stages, and the validation framework.\n"
     "\n"
     "**PARTS V-VII: THE PRACTICAL SYSTEM (Chapters 23-27 and the Workshops)**\n"
     "- Chapters 23-25: prerequisite life cycles, timing windows, and the protocols decoded.\n"
     "- The five Workshops: money, love, health, protection, career.\n"
     "- Chapters 26-27: the Three Controls and the Forty Days."),

    # Validation study designs are Chapter 22 (The Empirical Validation
    # Framework); Chapter 23 is The Prerequisite Life Cycles.
    ("3. Consult Chapter 23 for validation study designs",
     "3. Consult Chapter 22 for validation study designs"),

    # A circular pointer: these two lines sit inside Appendix B and send the
    # reader to "Appendix B (Noetic Interactions)", which does not exist. The
    # Noetic-interaction reference is Appendix A, the 40 Elements table.
    ("Revisit Appendix B (Noetic Interactions).",
     "Revisit Appendix A (The 40 Elements)."),
    ("Use the advanced diagnostic questions from Appendix B.",
     "Use the advanced diagnostic questions earlier in this appendix."),

    # Author's build-machine paths, printed to readers.
    ("(I will now proceed to rewrite the remaining case studies, the "
     "troubleshooting section, and the exercises in "
     "`/home/ubuntu/expanded_chapter_8_take_7.md` following this canonical "
     "structure. This will take considerable time.)", ""),
    ("(Note: The following elaborations are drawn from "
     "`/home/ubuntu/upload/pasted_content_2.txt`.)", ""),
]


def apply_content_fixes(lines):
    text = "\n".join(lines)
    n = 0
    for old, new in CONTENT_FIXES:
        if old in text:
            text = text.replace(old, new)
            n += 1
    stats_pending.append(n)
    return text.split("\n")


stats_pending = []

def seg(a, b):
    """1-based inclusive line range from the original source."""
    return RAW[a - 1:b]


# CONTENT_FIXES are deliberately NOT applied here.
#
# They used to be, and it silently corrupted the book. Two of the thirteen
# fixes inject lines (+2 near source line 495, +8 near 11659, net +10). Every
# index in the R region map below is written in ORIGINAL-source numbering, so
# once RAW had grown, 31 of the 39 regions were sliced 2 or 10 lines early:
# each one inherited the tail of the region before it and lost its own tail.
# That is what put three chapters inside verbatim blocks, left the Glossary
# with no heading, and severed the "Warning Signs to Stop" safety list from its
# emergency-grounding protocol.
#
# The old guard was `assert len(RAW) >= _orig_len - 2`, which is one-sided: it
# caught shrinkage and let a +10 growth through without a word.
#
# Fixed by applying them at the end, to the assembled text, exactly as the XREF
# fixes already do. RAW now keeps original numbering, so the region map is
# valid by construction.
_orig_len = len(RAW)
assert len(RAW) == _orig_len, "RAW must not be mutated before the region map is applied"


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

STAMP = re.compile(
    r"^\(.*\bComplete\b.*\)\s*$"
    r"|^\(?(Approx\.?|Approximately)\s+[\d,]+\s+words?\b.*$"
    r"|^.*\bNeed to expand\b.*$"
    r"|^.*\bnow ~?[\d,]+\s+words\b.*$"
    r"|^\(I will now proceed\b.*$"
    r"|^\(.*\b(Approx\.?|Approximately)\s+[\d,]+\s+words?\b.*\)\s*$",
    re.I)
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

# The source Index lists topics with no page numbers, which is unusable
# in an 800-page manual. Replaced with a real index built from the
# \index marks that publishing/build_indexes.py inserts into body.tex.
doc += ["", "```{=latex}", "\printindex", "```", ""]
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

# Content fixes run HERE, on the assembled text, not on RAW. See the note at the
# region map for why. Fail loudly on any that no longer match: a silently
# skipped fix means profanity, a drafting stamp or a care-avoidance passage
# ships in the printed book.
# Check the END STATE, not whether each fix fired. A fix whose `old` text was
# already removed by an earlier cleanup pass is a no-op, which is fine; a fix
# whose `old` text is still present afterwards is a real failure.
# --------------------------------------------------------------------------
# Excise the duplicated Worlds C/D draft layer.
#
# Chapter 5's 40-Elements expansion was published twice. The first copy runs to
# "(End of Chapter 5 Expansion)"; a second, older copy of the same 20 elements
# (C1-C10, D1-D10) plus its own Cross-World Interactions section follows
# immediately AFTER that closing stamp, carrying 20 different `Definition:`
# strings for the same cells -- both quoted as verbatim source text.
#
# The second copy is the superseded layer: it uses the old number-first notation
# (1b, 3c, 1d) throughout -- 132 such tokens against 1 in the retained copy --
# and it introduces no element the first copy does not already define. Cut it.
_DUP_START = "(End of Chapter 5 Expansion)"
_DUP_END = ("Intervention often requires addressing blocks across multiple "
            "levels, not just the physical.")
_a, _b = text.find(_DUP_START), text.find(_DUP_END)
if _a == -1 or _b == -1 or _b <= _a:
    raise SystemExit(
        "repair_manuscript: duplicate Worlds C/D block not locatable "
        f"(start={_a}, end={_b}); anchors moved -- re-derive before building"
    )
_b += len(_DUP_END)
_cut = text[_a + len(_DUP_START):_b]
if "1c" not in _cut or "World of Citta" not in _cut:
    raise SystemExit(
        "repair_manuscript: the span between the duplicate anchors does not "
        "look like the old-notation Worlds C/D copy; refusing to cut it"
    )
dup_lines_cut = _cut.count("\n")
text = text[:_a + len(_DUP_START)] + "\n" + text[_b:]

# --------------------------------------------------------------------------
# Replace Table 3, which contradicted the canonical Prerequisites.
#
# The chapter "The Canonical Prerequisites & The Recursive Prerequisite Model"
# defines the 12 as three cycles of four, keyed to the face cards:
# P1-P4 Desire (Kings), P5-P8 Power (Queens), P9-P12 Wisdom (Jacks).
#
# Table 3 published a different naming scheme entirely (Desire / Intent /
# Resource / Plan / Knowledge / ...) AND inverted two of the three cycles,
# assigning P5-P8 to Wisdom and P9-P12 to Power. Since the Usage Guide directly
# tells the reader to "Check Table 3 for Prerequisite deficiencies", the
# appendix a reader is sent to disagreed with the chapter that defines the term.
#
# The Element and Fractal columns are dropped rather than relabelled. They were
# chosen to match the superseded concepts -- "Resource", "Plan", "Feedback" --
# so carrying them over onto the canonical names would silently assert
# correspondences nobody established. Losing a column beats fabricating one.
_T3_START = "## Table 3: 12 Prerequisites to Element/Fractal Mapping"
_T3_END = "## Table 4"
_t3a, _t3b = text.find(_T3_START), text.find(_T3_END)
if _t3a == -1 or _t3b == -1 or _t3b <= _t3a:
    raise SystemExit("repair_manuscript: Table 3 block not locatable for replacement")
_T3_NEW = """## Table 3: The 12 Prerequisites

Three cycles of four. Kings carry Desire, Queens carry Power, Jacks carry
Wisdom — the structure developed in *The Canonical Prerequisites & The
Recursive Prerequisite Model*, which is where the full treatment of each stage
lives. Use this table to name which stage is deficient; go to that chapter for
what to do about it.

| Prerequisite | Cycle | Card | Stage |
|--------------|-------|------|-------|
| **P1** | Desire | King of Clubs | Beginning Desire — the want is just dawning |
| **P2** | Desire | King of Hearts | Strong Desire — the will is fully engaged |
| **P3** | Desire | King of Spades | Weakening Desire — motivation is fading |
| **P4** | Desire | King of Diamonds | Absent Desire — the will is gone |
| **P5** | Power | Queen of Diamonds | Birth of Power — ability just emerging |
| **P6** | Power | Queen of Clubs | Adolescent Power — progressing, not yet effective |
| **P7** | Power | Queen of Hearts | Mature Power — fully effective for the task |
| **P8** | Power | Queen of Spades | Waning Power — capability diminishing |
| **P9** | Wisdom | Jack of Clubs | Learning Wisdom — knowledge being acquired |
| **P10** | Wisdom | Jack of Diamonds | Knowing Wisdom — present, application may lag |
| **P11** | Wisdom | Jack of Spades | Understanding Wisdom — a working grasp |
| **P12** | Wisdom | Jack of Hearts | Mastering Wisdom — full comprehension |

"""
text = text[:_t3a] + _T3_NEW + text[_t3b:]

# --------------------------------------------------------------------------
# Normalise the Noetic index base in the Cross-Reference Tables.
#
# The book publishes ONE canonical listing of the ten Noetics -- "The Canonical
# Noetic Definitions" -- and it runs 1 Mind ... 9 Below/Effect, 10 Idea. Idea is
# Noetic 10; there is no Noetic 0. The rest of the book agrees overwhelmingly:
# the Idea row of the element grid is written X10 roughly 485 times against 8
# stray X0.
#
# Those 8 strays all sit in the Cross-Reference Tables appendix, and they take
# two forms: element labels (D0 for D10) and fractal cells with a zero
# component (5.0 for 5.10, 0.1 for 10.1). None of the zero-component cells
# exist in the book's own 100-cell table, so a reader following Table 3 or
# Table 8 is sent to a cell that is not there.
#
# Normalising can collide -- P1 lists both "2.0" and "2.10", which are the same
# cell written two ways. Where that happens the duplicate is dropped rather than
# invented over: two correct cells beat three with one fabricated.
def _normalise_noetic_base(block: str) -> tuple[str, int]:
    n = 0

    def elem(m):
        nonlocal n
        n += 1
        return m.group(1) + "10"

    block = re.sub(r"\b([A-D])0\b", elem, block)

    def cell(m):
        nonlocal n
        a, b = m.group(1), m.group(2)
        if a != "0" and b != "0":
            return m.group(0)
        n += 1
        return f"{'10' if a == '0' else a}.{'10' if b == '0' else b}"

    block = re.sub(r"(?<![\d.])(10|[0-9])\.(10|[0-9])(?![\d])", cell, block)

    # drop cells that normalisation turned into duplicates inside one table cell
    def dedupe(m):
        seen, out = set(), []
        for part in [p.strip() for p in m.group(1).split(",")]:
            if part and part not in seen:
                seen.add(part)
                out.append(part)
        return "| " + ", ".join(out) + " |"

    block = re.sub(r"\|\s*((?:(?:10|[1-9])\.(?:10|[0-9])\s*,\s*)+(?:10|[1-9])\.(?:10|[0-9]))\s*\|",
                   dedupe, block)
    return block, n

_xr = text.find(_T3_START.replace("12 Prerequisites to Element/Fractal Mapping",
                                  "The 12 Prerequisites"))
_xrend = text.find("## Usage Guide", _xr) if _xr != -1 else -1
if _xr == -1 or _xrend == -1:
    raise SystemExit("repair_manuscript: Cross-Reference Tables region not found "
                     "for Noetic-base normalisation")
_head, _mid, _tail = text[:_xr], text[_xr:_xrend], text[_xrend:]
_mid, noetic_base_fixed = _normalise_noetic_base(_mid)
text = _head + _mid + _tail
text = text.replace("(A1-D0 Elements", "(A1-D10 Elements")

# Verify by the RESULT, not by whether the fix fired. Two shapes exist here:
# replacements (new does not contain old) and insertions (new contains old, e.g.
# prepending an attribution before a heading). Checking `old not in text`
# afterwards is wrong for the second shape, and checking that every fix fired is
# wrong for the first, because an earlier cleanup pass may already have removed
# the target. `new in text` is the property that holds for both.
content_fixed = 0
for old, new in CONTENT_FIXES:
    if new and new in text:
        continue                      # already applied; do not double-insert
    if old in text:
        text = text.replace(old, new)
        content_fixed += 1
_bad = [(old, new) for old, new in CONTENT_FIXES
        if ((new not in text) if new else (old in text))]
if _bad:
    raise SystemExit(
        "repair_manuscript: %d content fix(es) did not land. A skipped fix "
        "ships profanity, a drafting stamp, or a care-avoidance passage into "
        "the printed book. First: %r" % (len(_bad), _bad[0][0][:90])
    )
stats_pending.append(content_fixed)

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
print(f"  content fixes applied: "
      f"{stats_pending[0] if stats_pending else 0}/{len(CONTENT_FIXES)}"
      f"  (the rest were already handled upstream)")
print(f"  duplicate C/D lines cut: {dup_lines_cut}")
print(f"  Noetic base normalised: {noetic_base_fixed} label(s)")
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
