#!/usr/bin/env python3
r"""
Build Kindle-ready EPUB3 editions of all three Noetic Compass Press titles.

Why the flags matter
--------------------
--mathml           Without it pandoc falls back to printing raw LaTeX. A naive
                   `pandoc x.md -o x.epub` emits the literal string
                   "$$d(p,q) = 2\arccos(...)$$" into the reader's page. With
                   --mathml the equations become real MathML, which EPUB3 and
                   modern Kindle both render.
--toc-depth=2      Chapters and sections. All three books mark their headings
                   with a single leading space rather than '#', so this only
                   works against the *preprocessed* sources, never the raw
                   manuscripts.
--epub-chapter-level=1  One XHTML file per chapter. Kindle handles a 180k-word
                   single file badly; splitting keeps navigation responsive.

Run:  python build_epubs.py
Out:  ../<book>/<Title>.epub  for each title, plus an epubcheck-style summary.
"""
import io
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent          # .../book
CSS = Path(__file__).with_name("epub.css")

BOOKS = [
    {
        "key": "pcba",
        "title": "CAS PCBA Engineer",
        "subtitle": "Designing Cognitive Circuits with the Cognitive Architecture System",
        "src": [ROOT / "CAS_PCBA_Engineer" / "build" / "front_prose.md",
                ROOT / "CAS_PCBA_Engineer" / "build" / "main_body.md"],
        "out": ROOT / "CAS_PCBA_Engineer" / "CAS_PCBA_Engineer.epub",
        "subject": "Computers / Artificial Intelligence",
    },
    {
        "key": "tica",
        "title": "Thinking in Cognitive Architecture",
        "subtitle": "A Universal Framework for Humans, AI, and Biological Minds",
        "src": [ROOT / "publishing" / "latex" / "manuscript_preprocessed.md"],
        "out": ROOT / "publishing" / "Thinking_in_Cognitive_Architecture.epub",
        "subject": "Computers / Artificial Intelligence",
    },
    {
        "key": "tks",
        "title": "The Superiority of TKS",
        "subtitle": "The Tootra Kabbalistic System: A Complete Operating Manual for Reality Engineering",
        "src": [ROOT / "superiority_of_tks" / "MANUSCRIPT.md"],
        "out": ROOT / "superiority_of_tks" / "The_Superiority_of_TKS.epub",
        "subject": "Body, Mind & Spirit / Magick Studies",
    },
]

# Raw-LaTeX blocks are print-only scaffolding (\part, \mainmatter, \appendix,
# \chapter*). Pandoc's epub writer drops unknown raw latex, but \chapter*
# blocks carry real headings we must keep, so convert those to markdown first.
RAW_CHAPTER = re.compile(
    r"```\{=latex\}\s*\\chapter\*\{(?P<t>[^}]*)\}.*?```", re.S)
RAW_OTHER = re.compile(r"```\{=latex\}.*?```", re.S)

# Custom math macros. These are defined in the print preamble, which the EPUB
# path never sees, so pandoc's MathML converter meets an unknown control
# sequence and falls back to emitting the raw TeX into the reader's page.
# Expand them textually first. Longest name first so \Noetica is not clipped by
# a shorter prefix.
MACROS = [
    (r"\Jnoe", r"\mathcal{J}_{\mathcal{N}}"),
    (r"\Noetica", r"\mathcal{N}"),
    (r"\Obj", r"\operatorname{Obj}"),
    (r"\Sh", r"\operatorname{Sh}"),
    (r"\id", r"\mathrm{id}"),
]


def expand_macros(text):
    for name, expansion in MACROS:
        # \Obj must not match \Object; require a non-letter boundary.
        text = re.sub(re.escape(name) + r"(?![A-Za-z])", expansion.replace("\\", "\\\\"), text)
    return text


def prepare(paths):
    text = "\n\n".join(p.read_text(encoding="utf-8", errors="replace")
                       for p in paths if p.exists())
    text = RAW_CHAPTER.sub(lambda m: f"\n\n# {m.group('t')}\n\n", text)
    text = RAW_OTHER.sub("", text)
    text = expand_macros(text)
    return text


def build(book):
    missing = [p for p in book["src"] if not p.exists()]
    if missing:
        print(f"  SKIP {book['title']}: missing {missing}")
        return None

    tmp = ROOT / "publishing" / f"_epub_{book['key']}.md"
    body = prepare(book["src"])
    meta = (
        "---\n"
        f"title: \"{book['title']}\"\n"
        f"subtitle: \"{book['subtitle']}\"\n"
        "author: \"Little Henderson\"\n"
        "publisher: \"Noetic Compass Press\"\n"
        "rights: \"Copyright © 2026 Little Henderson. All rights reserved.\"\n"
        "date: \"2026\"\n"
        "lang: en-US\n"
        f"subject: \"{book['subject']}\"\n"
        "---\n\n"
    )
    tmp.write_text(meta + body, encoding="utf-8")

    cmd = ["pandoc", str(tmp), "-o", str(book["out"]),
           "-f", "markdown-superscript-subscript",
           "-t", "epub3", "--mathml",
           "--toc", "--toc-depth=2",
           "--epub-chapter-level=1",
           "--syntax-highlighting=none"]
    if CSS.exists():
        cmd += ["--css", str(CSS)]

    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        print(f"  FAIL {book['title']}\n{r.stderr[-1500:]}")
        return None

    fixed = fix_pipes(book["out"])
    if fixed:
        print(f"  ..  unescaped {fixed} register pipe(s)")
    return inspect(book)


def fix_pipes(epub):
    """Unescape register pipes inside the generated XHTML.

    The CAS sources write the register suffix as "\\|A" so the pipe does not
    split a Markdown table cell. Inside a code span, Markdown escapes do not
    apply, so pandoc faithfully emits a literal backslash and the reader sees
    "^3^C_{F6}\\|A". The print build strips this in postprocess_pcba.py, which
    operates on the LaTeX; the EPUB path needs the same fix applied to the
    XHTML. Unescaping in the Markdown itself is not an option -- it would break
    every table that relies on it.
    """
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp()) / "fixed.epub"
    n = 0
    with zipfile.ZipFile(epub) as src, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename.endswith((".xhtml", ".html")):
                text = data.decode("utf-8", "replace")
                n += text.count("\\|")
                data = text.replace("\\|", "|").encode("utf-8")
            # mimetype must stay first and stored, which infolist order preserves
            dst.writestr(item, data)
    shutil.move(str(tmp), str(epub))
    return n


def inspect(book):
    """Report what actually landed in the container."""
    out = book["out"]
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        xhtml = [n for n in names if n.endswith((".xhtml", ".html"))]
        blob = "".join(
            z.read(n).decode("utf-8", "replace") for n in xhtml[:400])
    # MathML carries the original TeX inside <annotation encoding="application/
    # x-tex"> as a semantic fallback. That is correct markup and no reader ever
    # sees it, so strip annotations before looking for TeX that actually leaked
    # into visible text.
    visible = re.sub(r"<annotation\b[^>]*>.*?</annotation>", "", blob, flags=re.S)
    raw_tex = len(re.findall(r"\$\$|\\begin\{|\\arccos|\\sum_", visible))
    mathml = blob.count("<math")
    pipes = blob.count("\\|")
    size_kb = out.stat().st_size // 1024
    print(f"  OK  {book['title']}")
    print(f"        {out.name}  ({size_kb:,} KB, {len(xhtml)} XHTML files)")
    print(f"        MathML elements: {mathml}")
    print(f"        leaked raw LaTeX: {raw_tex}"
          f"{'   <-- INVESTIGATE' if raw_tex else ''}")
    print(f"        leaked \\| escapes: {pipes}"
          f"{'   <-- INVESTIGATE' if pipes else ''}")
    return out


def main():
    print("Building EPUB3 editions\n")
    built = [b for b in (build(bk) for bk in BOOKS) if b]
    print(f"\n{len(built)}/{len(BOOKS)} built.")
    print("\nNext: validate with epubcheck and open in Kindle Previewer before "
          "uploading. KDP accepts EPUB directly for Kindle; the print interior "
          "stays PDF.")


if __name__ == "__main__":
    main()
