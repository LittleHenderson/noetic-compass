#!/usr/bin/env python3
r"""
Promote the book's twelve TikZ diagrams from bare centred pictures to numbered,
captioned figures.

They were embedded as \begin{center}...\end{center}, which means no number, no
caption, no entry in a list of figures, and no way for the prose to reference
them. Chapter 9's is titled, in the text, "Characteristic Curves --- The Most
Important Picture in the Book" and had neither a number nor a caption.

Idempotent: a block already inside a figure environment is left alone.
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BOOK = Path(__file__).resolve().parent.parent

# file stem -> (label, caption)
CAPTIONS = {
    "Chapter_03": ("cjt-terminals",
        "The Cognitive Junction Transistor. Cause enters at the collector, "
        "bias controls the junction, and effect leaves at the emitter."),
    "Chapter_06": ("leakage",
        "Leakage curves for the same stored experience at two decay rates --- "
        "the design choice between a memory that holds and one that fades."),
    "Chapter_09": ("cjt-curves",
        "CJT characteristic curves at four bias levels. Each curve plots "
        "effect against cause, crossing cutoff, active, and saturation."),
    "Chapter_12": ("filter-shapes",
        "The four filter shapes on a single cognitive-frequency axis: "
        "low-pass, high-pass, band-pass, and notch."),
    "Chapter_16": ("bode",
        "Bode plot of gain and phase against frequency. Each pole contributes "
        "a further $-20$\\,dB per decade and $-90^\\circ$ of phase."),
    "Chapter_17": ("domain-layers",
        "The four Processing Domains as board layers. Signals route within a "
        "layer; a cross-domain transition is a via."),
    "Chapter_18": ("csb-blocks",
        "Cognitive Safety Board block diagram. A prompt flows left to right "
        "through five stages to either a response or a refusal."),
    "Chapter_19": ("cob-chain",
        "Cognitive Oscillator Board signal chain: clock, LC tank, "
        "phase-locked loop, and duty-cycle modulator."),
    "Chapter_20": ("diff-pair",
        "The differential pair. Two matched CJTs share one bias, with a "
        "current mirror as active load."),
    "Chapter_21": ("cmb-paths",
        "Cognitive Memory Board write and read paths, from encoder through "
        "address decoder to recalled output."),
    "Chapter_22": ("cpmb-topology",
        "Cognitive Power Management Board reference topology. Drive energy is "
        "regulated, limited, sequenced, and thermally managed per domain."),
    "Chapter_25": ("deploy-ladder",
        "The deployment ladder: five stages from simulation to full "
        "enforcement, each granting the board more authority."),
}

# \begin{center} ... tikzpicture ... \end{center}
BLOCK = re.compile(
    r"\\begin\{center\}\s*(?P<pic>\\begin\{tikzpicture\}.*?\\end\{tikzpicture\})\s*"
    r"\\end\{center\}", re.S)


def main() -> None:
    converted = 0
    for path in sorted(BOOK.glob("Chapter_*.md")):
        stem = path.name[:10]
        if stem not in CAPTIONS:
            continue
        text = path.read_text(encoding="utf-8")
        if "\\begin{figure}" in text:
            print(f"  skip {path.name[:44]} (already a figure)")
            continue
        label, caption = CAPTIONS[stem]

        def repl(m):
            return ("\\begin{figure}[htbp]\n\\centering\n"
                    + m.group("pic")
                    + f"\n\\caption{{{caption}}}\\label{{fig:{label}}}\n"
                    + "\\end{figure}")

        new, n = BLOCK.subn(repl, text)
        if n:
            path.write_text(new, encoding="utf-8")
            converted += n
            print(f"  OK   {path.name[:44]}  -> fig:{label}")
        else:
            print(f"  MISS {path.name[:44]}  (pattern did not match)")

    print(f"\n{converted}/{len(CAPTIONS)} figures captioned")
    if converted != len(CAPTIONS):
        raise SystemExit("caption_figures: not every figure was converted")


if __name__ == "__main__":
    main()
