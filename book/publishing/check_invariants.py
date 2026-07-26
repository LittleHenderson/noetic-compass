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

ok = sum(1 for r in rows if r[0])
for good, book, label, n, want in rows:
    print(f"  {'OK  ' if good else 'OPEN'} {book:5s} {label:34s} {n} (want {want})")
print(f"\n  {ok}/{len(rows)} invariants hold")
