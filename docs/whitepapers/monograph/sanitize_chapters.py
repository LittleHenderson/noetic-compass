"""Pre-compile sanity check for monograph chapter files.

Reports (does not modify): non-ASCII bytes, forbidden preamble commands,
unbalanced begin/end environments, and unknown environments. Run from
docs/whitepapers/monograph.
"""
import re
import sys
from pathlib import Path

ALLOWED_ENVS = {
    "theorem", "proposition", "lemma", "corollary", "conjecture", "axiom",
    "definition", "construction", "example", "exercise", "algorithm",
    "ruleenv", "protocol", "invariant", "checkclass", "finding", "conflict",
    "hypothesis", "remark", "boundary", "threat", "notation", "proof",
    "enumerate", "itemize", "description", "center", "tabular", "longtable",
    "align", "align*", "equation", "equation*", "gather", "gather*",
    "array", "cases", "pmatrix", "bmatrix", "matrix", "quote", "quotation",
    "flushleft", "flushright", "small", "footnotesize", "table", "figure", "smallmatrix", "subequations", "multline", "split", "aligned", "gathered", "verbatim",
}
FORBIDDEN = [r"\\documentclass", r"\\usepackage", r"\\begin\{document\}",
             r"\\end\{document\}", r"\\newcommand", r"\\renewcommand",
             r"\\def\\", r"\\newtheorem", r"\\newenvironment"]

def check(path: Path) -> list[str]:
    problems = []
    data = path.read_bytes()
    for i, b in enumerate(data):
        if b > 127:
            line = data[:i].count(b"\n") + 1
            snippet = data[max(0, i - 20):i + 20].decode("utf-8", "replace")
            problems.append(f"non-ASCII byte at line {line}: ...{snippet!r}...")
            break
    text = data.decode("utf-8", "replace")
    for pat in FORBIDDEN:
        m = re.search(pat, text)
        if m:
            line = text[:m.start()].count("\n") + 1
            problems.append(f"forbidden command {m.group(0)!r} at line {line}")
    begins = re.findall(r"\\begin\{([^}]*)\}", text)
    ends = re.findall(r"\\end\{([^}]*)\}", text)
    for env in set(begins) | set(ends):
        if begins.count(env) != ends.count(env):
            problems.append(
                f"unbalanced environment {env!r}: "
                f"{begins.count(env)} begin / {ends.count(env)} end")
        if env not in ALLOWED_ENVS:
            problems.append(f"unknown environment {env!r}")
    if not re.match(r"\s*(%[^\n]*\n\s*)*\\chapter", text):
        problems.append("does not start with \\chapter")
    return problems

def main() -> int:
    bad = 0
    for mono in ("noetic_topos2", "tks_v8", "cas_core8", "cas_pcba8", "cas_ohm1"):
        for f in sorted(Path(mono, "chapters").glob("*.tex")):
            if f.read_text(encoding="utf-8", errors="replace").lstrip().startswith("% placeholder"):
                print(f"PLACEHOLDER {f}")
                continue
            problems = check(f)
            words = len(f.read_text(encoding="utf-8", errors="replace").split())
            status = "OK " if not problems else "BAD"
            print(f"{status} {f} ({words} words)")
            for p in problems:
                print(f"    - {p}")
                bad += 1
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
