#!/usr/bin/env python3
r"""
Build all three books end to end, in the right order, with indexes.

The ordering matters and is easy to get wrong by hand:

    assemble -> pandoc -> postprocess -> INDEX MARKS -> xelatex
             -> makeindex -> xelatex -> xelatex

The index marks must go in after pandoc (they are LaTeX, not Markdown) and
before the first xelatex pass (which writes the .idx). makeindex then turns the
.idx into an .ind, and a further xelatex pass typesets it. A book built without
that middle step silently ships with an empty index.

Run: python build_all.py [pcba|tica|tks]
"""
import io
import re
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

PANDOC = ["-t", "latex", "--top-level-division=chapter",
          "-f", "markdown-superscript-subscript", "--syntax-highlighting=none"]


def run(cmd, cwd, quiet=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 and not quiet:
        print(r.stdout[-1500:])
    return r


BOOKS = {
    "pcba": {
        "dir": ROOT / "CAS_PCBA_Engineer" / "build",
        "master": "manuscript_pcba.tex",
        "pdf": "manuscript_pcba.pdf",
        "target": ROOT / "CAS_PCBA_Engineer" / "CAS_PCBA_Engineer.pdf",
        "assemble": [[sys.executable, "build_book.py"]],
        "pandoc": [("front_prose.md", "front_prose.tex"),
                   ("main_body.md", "body.tex")],
        "post": [[sys.executable, "postprocess_pcba.py"]],
        "outdir": None,
    },
    "tica": {
        "dir": ROOT / "publishing" / "latex",
        "master": "manuscript.tex",
        "pdf": "build/manuscript.pdf",
        "target": ROOT / "publishing" / "Thinking_in_Cognitive_Architecture_v1.pdf",
        "assemble": [[sys.executable, "preprocess.py"]],
        "pandoc": [("manuscript_preprocessed.md", "body.tex")],
        "post": [[sys.executable, "postprocess.py"]],
        "outdir": "build",
    },
    "tks": {
        "dir": ROOT / "superiority_of_tks" / "build",
        "master": "manuscript_tks.tex",
        "pdf": "manuscript_tks.pdf",
        "target": ROOT / "superiority_of_tks" / "Reality_Engineering.pdf",
        "assemble": [[sys.executable, "repair_manuscript.py"]],
        "pandoc": [(str(ROOT / "superiority_of_tks" / "MANUSCRIPT.md"), "body.tex")],
        "post": [],
        "outdir": None,
    },
}


def build(key):
    cfg = BOOKS[key]
    d = cfg["dir"]
    print(f"=== {key} ===")

    for cmd in cfg["assemble"]:
        run(cmd, d, quiet=False)
    # tks patches its own preamble inside build_book.py; run it for the styles
    if key == "tks":
        run([sys.executable, "-c",
             "import build_book; build_book.patch_preamble()"], d)

    for src, dst in cfg["pandoc"]:
        run(["pandoc", src, "-o", dst] + PANDOC, d, quiet=False)
    for cmd in cfg["post"]:
        run(cmd, d)

    # index marks -- must be after pandoc, before the first xelatex
    run([sys.executable, str(HERE / "build_indexes.py")], HERE)

    tex = [cfg["master"]]
    out = ["-output-directory=" + cfg["outdir"]] if cfg["outdir"] else []
    run(["xelatex", "-interaction=nonstopmode"] + out + tex, d)

    idx_dir = d / cfg["outdir"] if cfg["outdir"] else d
    idx = idx_dir / (Path(cfg["master"]).stem + ".idx")
    if idx.exists():
        r = run(["makeindex", "-q", idx.name], idx_dir)
        ind = idx.with_suffix(".ind")
        n = len(re.findall(r"\\item ", ind.read_text(encoding="utf-8", errors="replace"))) \
            if ind.exists() else 0
        print(f"  index entries: {n}")
    else:
        print("  WARNING: no .idx produced -- index will be empty")

    for _ in range(2):
        run(["xelatex", "-interaction=nonstopmode"] + out + tex, d)

    pdf = d / cfg["pdf"]
    if not pdf.exists():
        print("  FAILED: no PDF\n")
        return
    import pypdf
    n = len(pypdf.PdfReader(str(pdf)).pages)
    log = (idx_dir / (Path(cfg["master"]).stem + ".log")).read_text(
        encoding="utf-8", errors="replace")
    cfg["target"].write_bytes(pdf.read_bytes())
    print(f"  pages: {n}")
    print(f"  missing glyphs: {len(re.findall('Missing character', log))}")
    print(f"  -> {cfg['target'].name}\n")


def main():
    which = sys.argv[1:] or list(BOOKS)
    for k in which:
        build(k)


if __name__ == "__main__":
    main()
