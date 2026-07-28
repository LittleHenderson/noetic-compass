#!/usr/bin/env python3
r"""
Build real, page-accurate indexes for all four books.

None of the three had one. Reality Engineering shipped an "Index" that listed
topics with no page numbers at all -- for an 800-page operating manual, that is
the single most-used page in the book and it was unusable.

Approach
--------
Index terms are taken from each book's OWN glossary, which makes them
authoritative rather than my guesses about what matters. They are then marked
in the generated body.tex, after pandoc and before xelatex, so the markdown
sources stay clean and the whole thing is reproducible.

Two things stop this producing a useless index:

1. OCCURRENCE CAP. A term like "Bias" appears hundreds of times. An index entry
   with 200 page numbers is worse than no entry. Each term is marked at most
   MAX_HITS times, preferring the earliest occurrences -- which in practice are
   the definition and the first substantive uses.

2. VERBATIM EXCLUSION. Code listings, CCDL blocks and ASCII diagrams are
   skipped entirely. Indexing a keyword because it appeared in a code sample
   sends the reader to a listing, not an explanation.

Run:  python build_indexes.py                 (marks every book's body.tex)
      python build_indexes.py grimoire        (marks one book's body.tex)
      python build_indexes.py --terms         (just print extracted terms)
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

MAX_HITS = 8          # page references per term
MIN_LEN = 4           # ignore very short terms

# Terms that are navigational rather than conceptual. "Chapter 11" as an index
# entry sends the reader to a list of the places that mention Chapter 11, which
# is worse than useless -- the table of contents already does that job.
TERM_REJECT = re.compile(
    r"^(Chapter|Appendix|Part|Figure|Table|Step|Section|Exercise|Worked|Bench)\b"
    r"|^[^A-Za-z0-9]"          # must start with a letter or digit
    r"|^\d+$",                 # bare numbers
    re.I)


def normalise(term):
    """Index under the significant word: 'The Desire Tree' -> 'Desire Tree'."""
    return re.sub(r"^(The|A|An)\s+", "", term).strip()

# Words that are common English first and jargon second. Indexing them buries
# the reader.
STOP_TERMS = {
    "bias", "gain", "state", "drive", "domain", "mind", "idea", "effect",
    "cause", "power", "wisdom", "desire", "value", "system", "signal",
    "output", "input", "current", "energy", "action", "pattern", "process",
    "structure", "health", "unity", "purpose", "rhythm", "male", "female",
    "positive", "negative", "vibration", "world", "worlds", "element",
}


def escape_index(term):
    """makeindex treats ! @ | " as control characters."""
    out = []
    for ch in term:
        if ch in '!@|"':
            out.append('"' + ch)
        else:
            out.append(ch)
    return "".join(out)


def clean_term(raw):
    t = raw.strip()
    t = t.replace("`", "")                         # keep inline notation text
    t = re.sub(r"\([^)]*\)", "", t)               # drop parentheticals
    t = re.sub(r"\*+", "", t)                     # drop markdown emphasis
    t = re.sub(r"\s+", " ", t).strip(" —-–:,.")
    return t


# Symbolic glossary entries need two things the ordinary term path cannot give
# them: a TeX-safe printed form and a search needle matching pandoc's output.
# Their ASCII sort keys keep makeindex deterministic and place them where a
# reader will look rather than in an arbitrary Unicode-symbol bucket.
SPECIAL_INDEX = {
    "β": ("beta", r"$\beta$", "β"),
    "β=∞": ("beta infinite", r"$\beta=\infty$", "β=∞"),
    "g_m": ("gm", r"$g_m$", r"g\_m"),
    "rπ": ("r pi", r"$r\pi$", "rπ"),
    "τ": ("tau", r"$\tau$", "τ"),
    "η": ("eta", r"$\eta$", "η"),
    "Ω_c, V_c, A_c, F_c, h·Ω_c": (
        "cognitive units",
        r"Cognitive units ($\Omega_c$, $V_c$, $A_c$, $F_c$, $h\cdot\Omega_c$)",
        "Cognitive ohms",
    ),
    "^n^D_{Fk}|R": ("state literal", "State literal", "state literal"),
    "|": ("register pipe", r"Register pipe (\texttt{|})", "Introduces the Register"),
    "+ / × / |⟨…⟩": (
        "operators cas",
        "Operators (+, ×, register set)",
        "Co-presence",
    ),
    "A0": ("A0", "A0 (Pure Desire)", "A0"),
}


def index_payload(term):
    """Return a makeindex payload, including sort/display forms when needed."""
    if term not in SPECIAL_INDEX:
        return escape_index(term)
    sort_key, display, _ = SPECIAL_INDEX[term]
    return escape_index(sort_key) + "@" + escape_index(display)


# --- per-book glossary parsers -------------------------------------------

def terms_pcba():
    f = ROOT / "CAS_PCBA_Engineer" / "Appendix_G_Glossary.md"
    out = []
    for m in re.finditer(r"^\*\*(.+?)\*\*\s*[—–-]", f.read_text(encoding="utf-8"), re.M):
        out.append(clean_term(m.group(1)))
    return out


def terms_tica():
    f = ROOT / "manuscript" / "FULL_MANUSCRIPT_v2.md"
    text = f.read_text(encoding="utf-8")
    i = text.find("## Glossary")
    j = text.find("## Bibliography", i + 1)
    seg = text[i:j] if i > 0 and j > i else text[i:i + 40000] if i > 0 else ""
    out = []
    for m in re.finditer(r"^\s*[-*]\s*\*\*(.+?)\*\*\s*[—–-]", seg, re.M):
        out.append(clean_term(m.group(1)))
    for m in re.finditer(r"^\*\*(.+?)\*\*\s*[—–-]", seg, re.M):
        out.append(clean_term(m.group(1)))
    return out


def terms_tks():
    f = ROOT / "superiority_of_tks" / "MANUSCRIPT.md"
    text = f.read_text(encoding="utf-8")
    i = text.find("# Glossary of Terms")
    seg = text[i:i + 30000] if i > 0 else ""
    out = []
    for m in re.finditer(r"^\*\*(.+?)\*\*\s*:", seg, re.M):
        out.append(clean_term(m.group(1)))
    return out


def terms_grimoire():
    f = ROOT / 'cognitive-circuit-grimoire' / 'manuscript' / 'appendix_i_glossary.md'
    out = []
    for m in re.finditer(r'^\*\*(.+?)\*\*\s+', f.read_text(encoding='utf-8'), re.M):
        out.append(clean_term(m.group(1)))
    return out


BOOKS = {
    'grimoire': {
        'terms': terms_grimoire,
        'body': ROOT / 'cognitive-circuit-grimoire' / 'build' / 'body.tex',
    },
    "pcba": {
        "terms": terms_pcba,
        "body": ROOT / "CAS_PCBA_Engineer" / "build" / "body.tex",
    },
    "tica": {
        "terms": terms_tica,
        "body": ROOT / "publishing" / "latex" / "body.tex",
    },
    "tks": {
        "terms": terms_tks,
        "body": ROOT / "superiority_of_tks" / "build" / "body.tex",
    },
}

# Regions of the .tex that must never be indexed.
#
# Verbatim/TikZ: indexing a keyword because it appeared in a code listing or a
# diagram label sends the reader to a picture, not an explanation.
#
# Headings and captions: these are MOVING ARGUMENTS -- LaTeX writes them to the
# .aux and .toc. An \index{} inside one produces
#   "! Use of \@index doesn't match its definition"
# and a corrupted .aux that poisons every subsequent run. This is not a style
# preference; it breaks the build.
SKIP = re.compile(
    r"\\begin\{(Verbatim|verbatim|lstlisting|tikzpicture|axis)\}.*?"
    r"\\end\{(Verbatim|verbatim|lstlisting|tikzpicture|axis)\}"
    r"|\\(chapter|section|subsection|subsubsection|part|caption|"
    r"markboth|markright|addcontentsline|hypertarget|label|index)"
    r"\*?(\[[^\]]*\])?\{[^{}]*(\{[^{}]*\}[^{}]*)*\}",
    re.S)


def mark(body_path, terms):
    text = body_path.read_text(encoding="utf-8")

    # blank out skip regions so offsets stay stable, then restore
    holes = [(m.start(), m.end()) for m in SKIP.finditer(text)]

    def in_hole(pos):
        return any(a <= pos < b for a, b in holes)

    # Section headings are the other authoritative source of index terms: they
    # are what the author thought was worth naming. Take the multi-word,
    # capitalised ones and treat them as terms too.
    for m in re.finditer(r"\\(?:section|subsection)\{([^{}]{6,60})\}", text):
        h = clean_term(m.group(1))
        h = re.sub(r"^\d+[.)]\s*", "", h)          # drop leading ordinals
        h = h.split(":")[0].split(" --- ")[0].strip()
        if (len(h.split()) >= 2 and len(h) >= 8
                and h[0].isupper() and h.lower() not in STOP_TERMS):
            terms.append(h)

    # longest first so "Cognitive Junction Transistor" is claimed before
    # "Transistor" can swallow the same span
    usable = sorted(
        {normalise(t) for t in terms
         if (t in SPECIAL_INDEX or (
             len(t) >= MIN_LEN
             and t.lower() not in STOP_TERMS
             and not TERM_REJECT.search(t)
             and normalise(t).lower() not in STOP_TERMS
         ))},
        key=len, reverse=True)

    inserts = []          # (position, text)
    claimed = []          # spans already indexed, to avoid nesting
    marked = 0
    for term in usable:
        needle = SPECIAL_INDEX.get(term, (None, None, term))[2]
        pat = re.compile(r"(?<![\w\\])" + re.escape(needle) + r"(?![\w])")
        hits = 0
        for m in pat.finditer(text):
            if hits >= MAX_HITS:
                break
            if in_hole(m.start()):
                continue
            if any(a <= m.start() < b for a, b in claimed):
                continue
            inserts.append((m.end(), "\\index{" + index_payload(term) + "}"))
            claimed.append((m.start(), m.end()))
            hits += 1
        marked += hits

    for pos, ins in sorted(inserts, reverse=True):
        text = text[:pos] + ins + text[pos:]

    body_path.write_text(text, encoding="utf-8")
    return len(usable), marked


def main():
    only_terms = "--terms" in sys.argv
    requested = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    unknown = sorted(set(requested) - set(BOOKS))
    if unknown:
        raise SystemExit(f"unknown book key(s): {', '.join(unknown)}")

    selected = requested or list(BOOKS)
    for key in selected:
        cfg = BOOKS[key]
        terms = [t for t in cfg["terms"]() if t]
        terms = list(dict.fromkeys(terms))
        print(f"=== {key} ===")
        print(f"  glossary terms extracted: {len(terms)}")
        if only_terms:
            for t in terms[:14]:
                print(f"    {t}")
            print()
            continue
        if not cfg["body"].exists():
            print(f"  SKIP: {cfg['body']} not built yet\n")
            continue
        if "\\index{" in cfg["body"].read_text(encoding="utf-8"):
            print("  already marked (rebuild body.tex to re-mark)\n")
            continue
        n_terms, n_marks = mark(cfg["body"], terms)
        print(f"  indexable terms         : {n_terms}")
        print(f"  index marks inserted    : {n_marks}")
        print(f"  (capped at {MAX_HITS} page references per term)\n")


if __name__ == "__main__":
    main()
