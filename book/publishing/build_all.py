#!/usr/bin/env python3
r"""
Build all four books end to end, in the right order, with indexes.

The ordering matters and is easy to get wrong by hand:

    assemble -> pandoc -> postprocess -> INDEX MARKS -> xelatex
             -> makeindex -> xelatex -> xelatex

The index marks must go in after pandoc (they are LaTeX, not Markdown) and
before the first xelatex pass (which writes the .idx). makeindex then turns the
.idx into an .ind, and a further xelatex pass typesets it. A book built without
that middle step silently ships with an empty index.

Run: python build_all.py [pcba|tica|tks|grimoire]
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
INDEX_CONTROL_WORD_SPACE = re.compile(r"(\\[A-Za-z]+) (?=[$_=,)}])")


def run(cmd, cwd, quiet=True, must_succeed=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 and not quiet:
        print(r.stdout[-1500:])
    if r.returncode != 0 and must_succeed:
        # An assemble or postprocess step that dies leaves the PREVIOUS
        # intermediate on disk, and every later stage happily consumes it. The
        # build then reports a page count and a clean glyph check for a book
        # that does not contain the edits just made. This has happened; do not
        # let it happen quietly.
        raise SystemExit(
            f"build_all: {' '.join(str(c) for c in cmd)} exited "
            f"{r.returncode} — refusing to build from a stale intermediate.\n"
            f"--- stdout ---\n{r.stdout[-2000:]}\n"
            f"--- stderr ---\n{r.stderr[-2000:]}"
        )
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
    "grimoire": {
        "dir": ROOT / "cognitive-circuit-grimoire" / "build",
        "master": "manuscript_grimoire.tex",
        "pdf": "manuscript_grimoire.pdf",
        "target": ROOT / "cognitive-circuit-grimoire" / "Cognitive_Circuit_Grimoire.pdf",
        # Assemble first, then replace markers in the generated main_body.md.
        # Chapter sources remain canonical and unmodified. insert_figures exits
        # non-zero while any marker is still undrawn, which is deliberate.
        "assemble": [[sys.executable, "build_board_appendix.py"],
                     [sys.executable, "build_answer_appendix.py"],
                     [sys.executable, "check_chapter_structure.py"],
                     [sys.executable, "check_exercise_answers.py"],
                     [sys.executable, "check_cross_references.py"],
                     [sys.executable, "check_cjt_domains.py"],
                     [sys.executable, "check_figure_inventory.py"],
                     [sys.executable, "figtest.py", "--all"],
                     [sys.executable, "build_book.py"],
                     [sys.executable, "insert_figures.py"]],
        "pandoc": [("front_prose.md", "front_prose.tex"),
                   ("main_body.md", "body.tex")],
        "post": [[sys.executable, "postprocess_grimoire.py"],
                 [sys.executable, "tabletest.py"]],
        "outdir": None,
    },
}


def build(key):
    cfg = BOOKS[key]
    d = cfg["dir"]
    print(f"=== {key} ===")

    for cmd in cfg["assemble"]:
        run(cmd, d, quiet=False, must_succeed=True)
    # tks patches its own preamble inside build_book.py; run it for the styles
    if key == "tks":
        run([sys.executable, "-c",
             "import build_book; build_book.patch_preamble()"], d,
            must_succeed=True)

    for src, dst in cfg["pandoc"]:
        run(["pandoc", src, "-o", dst] + PANDOC, d, quiet=False, must_succeed=True)
    for cmd in cfg["post"]:
        run(cmd, d, must_succeed=True)

    # index marks -- must be after pandoc, before the first xelatex
    run([sys.executable, str(HERE / "build_indexes.py"), key],
        HERE, must_succeed=True)

    tex = [cfg["master"]]
    out = ["-output-directory=" + cfg["outdir"]] if cfg["outdir"] else []
    idx_dir = d / cfg["outdir"] if cfg["outdir"] else d
    stem = Path(cfg["master"]).stem
    for suffix in (
        ".aux", ".idx", ".ilg", ".ind", ".lof", ".log", ".out", ".pdf", ".toc"
    ):
        (idx_dir / f"{stem}{suffix}").unlink(missing_ok=True)

    latex = ["xelatex", "-interaction=nonstopmode", "-halt-on-error"]
    run(latex + out + tex, d,
        quiet=False, must_succeed=True)

    idx = idx_dir / (Path(cfg["master"]).stem + ".idx")
    if idx.exists():
        # TeX may serialize the same protected math control word both with and
        # without its ignored delimiter space (for example ``\\beta `` versus
        # ``\\beta``). makeindex treats those byte forms as different display
        # strings and prints duplicate headwords, even though the PDF renders
        # them identically. Canonicalize only spaces that TeX itself ignores.
        idx_text = idx.read_text(encoding="utf-8", errors="replace")
        idx_text, normalized_index_spaces = INDEX_CONTROL_WORD_SPACE.subn(
            r"\1", idx_text
        )
        idx.write_text(idx_text, encoding="utf-8")
        print(f"  normalized index control-word spaces: {normalized_index_spaces}")
        run(["makeindex", "-q", idx.name], idx_dir,
            quiet=False, must_succeed=True)
        ind = idx.with_suffix(".ind")
        n = len(re.findall(r"\\item ", ind.read_text(encoding="utf-8", errors="replace"))) \
            if ind.exists() else 0
        print(f"  index entries: {n}")
        if not ind.exists() or n == 0:
            raise SystemExit("build_all: makeindex produced no usable index entries")
    else:
        raise SystemExit("build_all: no .idx produced -- refusing to ship an empty index")

    for _ in range(2):
        run(latex + out + tex, d,
            quiet=False, must_succeed=True)

    pdf = d / cfg["pdf"]
    if not pdf.exists():
        raise SystemExit("build_all: LaTeX completed without producing a PDF")
    import pypdf
    n = len(pypdf.PdfReader(str(pdf)).pages)
    log = (idx_dir / (Path(cfg["master"]).stem + ".log")).read_text(
        encoding="utf-8", errors="replace")
    missing_glyphs = len(re.findall("Missing character", log))
    undefined_refs = len(re.findall(
        r"LaTeX Warning: (?:Reference .* undefined|There were undefined references)",
        log,
    ))
    undefined_citations = len(re.findall(
        r"LaTeX Warning: (?:Citation .* undefined|There were undefined citations)",
        log,
    ))
    rerun_warnings = len(re.findall(
        r"(?:Label\(s\) may have changed|Rerun to get cross-references right|"
        r"Package rerunfilecheck Warning: .* has changed)",
        log,
    ))
    overfull_hboxes = [
        float(value) for value in re.findall(
            r"Overfull \\hbox \(([0-9.]+)pt too wide\)", log
        )
    ]
    overfull_vboxes = [
        float(value) for value in re.findall(
            r"Overfull \\vbox \(([0-9.]+)pt too high\)", log
        )
    ]
    material_hboxes = [value for value in overfull_hboxes if value > 2.0]
    material_vboxes = [value for value in overfull_vboxes if value > 2.0]
    oversized_floats = re.findall(
        r"LaTeX Warning: Float too large for page by ([0-9.]+)pt", log
    )
    header_overflow = "material used in the headers is too large" in log
    empty_plot_range = "axis range is approximately empty" in log
    print(
        "  overfull hboxes: "
        f"{len(overfull_hboxes)} total, {len(material_hboxes)} over 2pt, "
        f"max {max(overfull_hboxes, default=0.0):.5f}pt"
    )
    print(
        "  overfull vboxes: "
        f"{len(overfull_vboxes)} total, {len(material_vboxes)} over 2pt, "
        f"max {max(overfull_vboxes, default=0.0):.5f}pt"
    )
    if missing_glyphs:
        raise SystemExit(
            f"build_all: {missing_glyphs} missing glyph(s) in final LaTeX log"
        )
    if undefined_refs:
        raise SystemExit(
            f"build_all: {undefined_refs} unresolved-reference warning(s) in final LaTeX log"
        )
    if undefined_citations:
        raise SystemExit(
            f"build_all: {undefined_citations} unresolved-citation warning(s) "
            "in final LaTeX log"
        )
    if rerun_warnings:
        raise SystemExit(
            f"build_all: {rerun_warnings} rerun-needed warning(s) in final LaTeX log"
        )
    layout_failures = []
    if material_hboxes:
        layout_failures.append(
            f"{len(material_hboxes)} overfull hbox(es) above 2pt"
        )
    if material_vboxes:
        layout_failures.append(
            f"{len(material_vboxes)} overfull vbox(es) above 2pt"
        )
    if oversized_floats:
        layout_failures.append(f"{len(oversized_floats)} oversized float(s)")
    if header_overflow:
        layout_failures.append("running-header overflow")
    if empty_plot_range:
        layout_failures.append("approximately empty pgfplots axis range")
    if layout_failures:
        raise SystemExit(
            "build_all: final layout gate failed: " + "; ".join(layout_failures)
        )
    if key == "grimoire":
        marker_numbers = []
        manuscript_dir = d.parent / "manuscript"
        for source in sorted(manuscript_dir.glob("ch[0-2][0-9]_*.md")):
            marker_numbers.extend(
                f"{chapter}-{letter}"
                for chapter, letter in re.findall(
                    r"\[\[FIGURE\s+(\d+)-([A-Z]):",
                    source.read_text(encoding="utf-8"),
                )
            )
        lof = (idx_dir / f"{stem}.lof").read_text(
            encoding="utf-8", errors="replace"
        )
        printed_numbers = re.findall(r"\\numberline \{([^{}]+)\}", lof)
        if printed_numbers != marker_numbers:
            raise SystemExit(
                "build_all: List of Figures does not preserve authored marker "
                f"numbers ({len(printed_numbers)} printed / "
                f"{len(marker_numbers)} expected)"
            )
    cfg["target"].write_bytes(pdf.read_bytes())
    print(f"  pages: {n}")
    print(f"  missing glyphs: {missing_glyphs}")
    print(f"  unresolved references: {undefined_refs}")
    print(f"  unresolved citations: {undefined_citations}")
    print(f"  rerun-needed warnings: {rerun_warnings}")
    print(f"  -> {cfg['target'].name}\n")


def main():
    which = sys.argv[1:] or list(BOOKS)
    for k in which:
        build(k)


if __name__ == "__main__":
    main()
