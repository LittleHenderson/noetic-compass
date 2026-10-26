#!/usr/bin/env python3
"""Wrap CAS_Component_Mathematics.html as a standalone print document.

The source file starts at `<title>` — it is a fragment with no `<!doctype>`,
`<head>` or `<body>`. Headless Chrome will render it, but print geometry and
font loading are both unreliable without a real document shell, so this builds
a proper one and appends the print stylesheet.

The print rules do three jobs:

  1. **Force the light palette.** The source has a `prefers-color-scheme: dark`
     block; headless print rendering reports a dark preference on some builds,
     which would print ink-on-black. The override is written after that block
     and at equal specificity so it wins the cascade.
  2. **Turn on exact colour adjustment**, so the tinted surfaces and domain
     chips survive printing instead of being dropped to white.
  3. **Stop content splitting across pages** — a part, a circuit line, a rule
     row, a figure or a guard must not be broken in half. A family heading is
     kept with the rows that follow it.

Run from build/:  python build_ccm_print.py
Then render:      see render_ccm_pdf.ps1 / the command in BUILD notes.
"""
from __future__ import annotations

import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE.parent
SRC = BOOK / "CAS_Component_Mathematics.html"
OUT = HERE / "ccm_print.html"

PRINT_CSS = """
<style>
@page { size: A4; margin: 13mm 12mm 15mm; }
@media print {
  /* Force the light palette. Listed after the dark block and at equal
     specificity, so it wins. */
  :root, :root:not([data-theme="light"]) {
    --ground:#FFFFFF; --surface:#F4F5F2; --surface-2:#ECEDE9;
    --ink:#14171A; --ink-2:#394044; --muted:#5C6367;
    --rule:#B6B9B1; --rule-soft:#D1D4CC;
    --copper:#844C22; --copper-2:#9E6337;
    --dom-p:#8A6013; --dom-c:#2C5580; --dom-e:#84322E; --dom-o:#2C5C3E;
  }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { background:#fff; font-size:10.2pt; line-height:1.44; padding:0; }
  .wrap { max-width:none; }
  header { padding:0 0 14px; }
  h1 { font-size:27pt; }
  .dek { font-size:11pt; }
  section { margin-top:18px; }
  /* never split a part, a circuit line, a rule row or a figure across pages */
  .part, .circuit, .row2, .guards li, figure, .boundary, .colophon, .grade-row {
    break-inside: avoid; page-break-inside: avoid;
  }
  /* a family heading must not be orphaned at the foot of a page */
  .fam { break-after: avoid; page-break-after: avoid; }
  .ex { font-size:9.6pt; }
  .verbs { font-size:8.9pt; }
  figure svg { min-width:0; width:100%; max-width:430px; }
  a { text-decoration:none; color:inherit; }
}
</style>
"""

HEAD_OPEN = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
             '<meta name="viewport" content="width=device-width,initial-scale=1">\n')


def main() -> int:
    s = io.open(SRC, encoding="utf-8").read()
    marker = "</style>"
    i = s.index(marker) + len(marker)
    out = (HEAD_OPEN + s[:i] + PRINT_CSS + "\n</head>\n<body>\n"
           + s[i:] + "\n</body>\n</html>\n")
    io.open(OUT, "w", encoding="utf-8").write(out)
    print(f"wrote {OUT}  ({len(out):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
