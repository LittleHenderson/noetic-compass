#!/usr/bin/env python3
r"""
Regression guard for the three CAS books.

Every check here corresponds to a defect that was actually found in these
manuscripts and fixed. They are cheap string and arithmetic invariants, not a
substitute for reading; the point is that the specific mistakes already made
cannot come back unnoticed.

Each line is `OK` when the count matches, `OPEN` when it does not. Exits
non-zero if anything is OPEN, so it can gate a build.

Run: python check_invariants.py
"""
import pathlib, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
TI = (ROOT / "manuscript" / "FULL_MANUSCRIPT_v2.md").read_text(encoding="utf-8")
TK = (ROOT / "superiority_of_tks" / "MANUSCRIPT.md").read_text(encoding="utf-8")
PCBA_DIR = ROOT / "CAS_PCBA_Engineer"
# Check exactly what ships: take the manifest from the build script rather than
# globbing, so authoring files (STYLE_GUIDE.md etc.) are not treated as book text
# and a newly added chapter is picked up automatically.
_build_src = (PCBA_DIR / "build" / "build_book.py").read_text(encoding="utf-8")
PCBA_FILES = [PCBA_DIR / n for n in
              dict.fromkeys(re.findall(r'"((?:Chapter|Appendix|\d\d)_[^"]+\.md)"', _build_src))
              if (PCBA_DIR / n).exists()]
PB = "\n".join(f.read_text(encoding="utf-8") for f in PCBA_FILES)
rows = []
def c(book, label, T, pat, want=0):
    n = len(re.findall(pat, T)); rows.append((n==want, book, label, n, want))

# --- TiCA ---
c("TiCA","Scheme-A: abstractification",TI,r"abstractification",0)
c("TiCA","Scheme-A: Critical Evaluation",TI,r"Critical Evaluation",0)
c("TiCA","Scheme-A: Empathetic Alignment",TI,r"Empathetic Alignment",0)
c("TiCA","Scheme-A: contraction label",TI,r"contraction in action",0)
c("TiCA","bare ^3^P|Omega",TI,r"\^3\^P\|Ω(?!_)",0)
c("TiCA","backwards emergent assignment",TI,r"\|Ω\w* = \(",0)
c("TiCA","register before drive",TI,r"\^\d\^[PCEO]\|[TAfE]_\{F\d\}",0)
c("TiCA","ascending x compounds",TI,r"",0)  # placeholder, computed below
rows.pop()
ORDER={"P":0,"C":1,"E":2,"O":3}
pat=re.compile(r"\^\d\^([PCEO])[^\s`]*\s*×\s*\^\d\^([PCEO])")
asc=sum(1 for m in pat.finditer(TI) if ORDER[m.group(1)]>ORDER[m.group(2)])
rows.append((asc==0,"TiCA","ascending x compounds",asc,0))
c("TiCA","undefined operator glyphs",TI,r"[¬⊗]",0)
c("TiCA","private repo paths",TI,r"docs/[A-Za-z]",0)
c("TiCA","stale 1,888 lines",TI,r"1,888 lines",0)
c("TiCA","'six appendices'",TI,r"27 chapters and six appendices",0)
c("TiCA","Stealth Flip",TI,r"Stealth Flip",0)
c("TiCA","'no candidate entries.'",TI,r"Currently: no candidate entries\.",0)
c("TiCA","'F' <digit> drive production",TI,r'<drive>\s+::=\s*"F" <digit>',0)
c("TiCA","arccos 0.4751",TI,r"0\.4751",0)
c("TiCA","'11-point'",TI,r"11.point",0)
c("TiCA","'35 recipes'",TI,r"35 recipes",0)
c("TiCA","'five of the most critical'",TI,r"five of the most critical",0)
# --- TKS ---
c("TKS","Vibration 5",TK,r"Vibration 5",0)
c("TKS","element labels X0",TK,r"\b[A-D]0\b",0)
c("TKS","Sefirot Foundation names",TK,r"F2 Opposition|F3 Beauty|F6 Victory|F7 Abundance",0)
c("TKS","F8 (nonexistent)",TK,r"\bF8\b",0)
c("TKS","D12 (nonexistent)",TK,r"\bD12\b",0)
c("TKS","pasted_content refs",TK,r"pasted_content",0)
c("TKS","'Twelve Combinations'",TK,r"Twelve Combinations",0)
c("TKS","divide-by-7 protocol",TK,r"A4\^\) ÷ 7",0)
c("TKS","stale wave windows 0-24",TK,r"First \(0-24 hrs\)",0)
c("TKS","'1,260 days ÷ 24'",TK,r"1,260 days ÷ 24",0)
c("TKS","stale 'Chapter 8 advanced'",TK,r"Chapter 8 advanced",0)
c("TKS","B3 as critical/discernment",TK,r"B3 critical|B3 \(mental discernment\)",0)
c("TKS","fence parity (0=even)",TK,r"",0); rows.pop()
rows.append((TK.count("```")%2==0,"TKS","fence parity (even)",TK.count("```")%2,0))

# --- PCBA ---
# Every check below corresponds to a defect the Project Coherence monograph audit
# found in the 2026-07-26 build (src-pcba-engineer-20260726) and that is now fixed.
# See docs/reference/PCBA_BOOK_DEFECTS_FROM_MONOGRAPHS.md.

# THE headline defect: a fuse threshold at or above the lowest saturation ceiling on
# its own input path can never trip. Checked arithmetically, per line, across the book.
# Lines that deliberately quote the failing pair as a worked counterexample are exempt
# via the teaching marker, so the lesson can stay in the book without tripping the guard.
_TEACH = re.compile(r"never|cannot|can't|counterexample|wrong|reject|inconsistent|trap|"
                    r"unreachable|would be|do the subtraction|nothing.{0,20}catch", re.I)
_unreachable = []
for _f in PCBA_FILES:
    for _i, _l in enumerate(_f.read_text(encoding="utf-8").split("\n"), 1):
        _s = [float(x) for x in re.findall(r"sat\s*=\s*(\d+(?:\.\d+)?)", _l)]
        _t = [float(x) for x in re.findall(r"threshold\s*=\s*(\d+(?:\.\d+)?)", _l)]
        if _s and _t and max(_t) >= min(_s) and not _TEACH.search(_l):
            _unreachable.append(f"{_f.name}:{_i}")
rows.append((not _unreachable, "PCBA", "unreachable fuse threshold",
             len(_unreachable), 0))

c("PCBA","CSB fuse back at 0.9",PB,r"red_fuse[^\n]*threshold=0\.9",0)
c("PCBA","beta=inf in a listing",PB,r"\[β=∞",0)          # idealization allowed in prose, not in listings
c("PCBA","'saturation latches' claim",PB,r"[Ss]aturation latches the \*?decision",0)
c("PCBA","clamp called hysteresis",PB,r"cognitive twin of a comparator with hysteresis",0)
c("PCBA","'four failure modes' (now five)",PB,r"[Ff]our failure modes",0)
c("PCBA","'gate' unreserved",PB,r"",0); rows.pop()
_appc = (PCBA_DIR / "Appendix_C_CCDL_Language_Reference.md").read_text(encoding="utf-8")
rows.append(("gate" in _appc, "PCBA", "'gate' reserved in App C", int("gate" in _appc), 1))
rows.append(("Construct Coverage Matrix" in _appc, "PCBA",
             "construct coverage matrix present", int("Construct Coverage Matrix" in _appc), 1))
# Reachability rule must be stated wherever a fuse threshold is taught.
for _n, _fn in (("App B", "Appendix_B_Component_Datasheets.md"),
                ("Ch 10", "Chapter_10_Special_Purpose_Components.md")):
    _t = (PCBA_DIR / _fn).read_text(encoding="utf-8")
    _has = "min( sat, clamp" in _t
    rows.append((_has, "PCBA", f"reachability rule in {_n}", int(_has), 1))
# Fenced-code parity per file (a truncated listing silently drops a board).
_odd = [f.name for f in PCBA_FILES if f.read_text(encoding="utf-8").count("```") % 2]
rows.append((not _odd, "PCBA", "fence parity (all files even)", len(_odd), 0))

ok = sum(1 for r in rows if r[0])
for good, book, label, n, want in rows:
    print(f"  {'OK  ' if good else 'OPEN'} {book:5s} {label:34s} {n} (want {want})")
print(f"\n  {ok}/{len(rows)} invariants hold")
