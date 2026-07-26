#!/usr/bin/env python3
r"""
Add six schematics to chapters that carry none, using the book's existing
visual grammar from figures_preamble.tex (domain palette, rounded blocks,
-{Latex} flow arrows, <= 11cm wide for the 6x9 measure).

Chosen where the prose describes a structure the reader has to hold in their
head with no picture to hold it against: the divider Chapter 5 promises you
will build, the one-way domain chain that is the whole point of Chapter 8, the
gain cascade behind beta_total, the Phi loop, the walk-down the book calls the
single most valuable skill an engineer owns, and the three CAS-Ohm modes.

Idempotent: an anchor whose figure is already present is skipped.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BOOK = Path(__file__).resolve().parent.parent


def fig(body, label, caption):
    return ("```{=latex}\n\\begin{figure}[htbp]\n\\centering\n"
            + body.strip()
            + f"\n\\caption{{{caption}}}\\label{{fig:{label}}}\n"
            + "\\end{figure}\n```\n")


DIVIDER = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize]
  \draw[casNedge, line width=0.6pt] (0,42) -- (34,42);
  \node[anchor=south] at (17,43) {$V_{\text{drive}}$ \; (Agency rail)};
  \draw[casNedge, line width=0.6pt] (17,42) -- (17,34);
  \draw[fill=casPfill, draw=casPedge, line width=0.6pt] (11,22) rectangle (23,34);
  \node at (17,28) {$R_{\text{expand}}$};
  \draw[casNedge, line width=0.6pt] (17,22) -- (17,14);
  \draw[fill=casEfill, draw=casEedge, line width=0.6pt] (11,2) rectangle (23,14);
  \node at (17,8) {$R_{\text{constrain}}$};
  \draw[casNedge, line width=0.6pt] (17,2) -- (17,-4) -- (10,-4);
  \draw[casNedge, line width=0.6pt] (6,-4) -- (28,-4);
  \foreach \i in {0,1,2} {
    \draw[casNedge, line width=0.5pt] (11+\i*4,-6) -- (17+\i*4,-6);
  }
  \node[anchor=north] at (17,-8) {ground};
  \draw[-{Latex[length=1.8mm]}, casCedge, line width=0.6pt] (23,18) -- (36,18);
  \node[anchor=west, align=left, text=casCedge] at (36,18)
    {tap: the split\\[-1pt]{\scriptsize$V_{\text{out}} =
      V_{\text{drive}}\dfrac{R_{\text{constrain}}}
      {R_{\text{expand}}+R_{\text{constrain}}}$}};
\end{tikzpicture}
"""

DESCENT = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
                    dnode/.style={rounded corners=1pt, minimum width=20mm,
                                  minimum height=8mm, draw, line width=0.6pt}]
  \node[dnode, fill=casPfill, draw=casPedge] (P) at (0,0)  {\textbf{P}};
  \node[dnode, fill=casCfill, draw=casCedge] (C) at (0,-14){\textbf{C}};
  \node[dnode, fill=casEfill, draw=casEedge] (E) at (0,-28){\textbf{E}};
  \node[dnode, fill=casOfill, draw=casOedge] (O) at (0,-42){\textbf{O}};
  % forward-biased diodes between domains
  \foreach \a/\b in {P/C, C/E, E/O} {
    \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (\a) -- (\b);
    \begin{scope}[shift={($(\a)!0.5!(\b)$)}]
      \draw[casNedge, line width=0.6pt] (-2.4,1.4) -- (2.4,1.4) -- (0,-1.4) -- cycle;
      \draw[casNedge, line width=0.6pt] (-2.4,-1.4) -- (2.4,-1.4);
    \end{scope}
  }
  \node[anchor=west, align=left, text=casNedge] at (14,-21)
    {forward bias:\\ conducts};
  % blocked reverse path
  \draw[casRed, line width=0.6pt, dash pattern=on 1.4pt off 1.4pt]
    (-13,-42) -- (-13,0);
  \draw[casRed, line width=0.7pt] (-15.6,-2.6) -- (-10.4,-7.8);
  \draw[casRed, line width=0.7pt] (-15.6,-7.8) -- (-10.4,-2.6);
  \node[anchor=east, align=right, text=casRed] at (-17,-21)
    {reverse bias:\\ blocked};
\end{tikzpicture}
"""

CASCADE = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
                    st/.style={rounded corners=1pt, minimum width=19mm,
                               minimum height=11mm, draw, line width=0.6pt}]
  \node[st, fill=casCfill, draw=casCedge] (s1) at (0,0)  {understand};
  \node[st, fill=casEfill, draw=casEedge] (s2) at (30,0) {evaluate};
  \node[st, fill=casOfill, draw=casOedge] (s3) at (60,0) {respond};
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (-13,0) -- (s1);
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (s1) -- (s2)
    node[midway, above, font=\scriptsize] {$\beta_1$};
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (s2) -- (s3)
    node[midway, above, font=\scriptsize] {$\beta_2$};
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (s3) -- (73,0)
    node[midway, above, font=\scriptsize] {$\beta_3$};
  \node[anchor=north] at (30,-10)
    {$\beta_{\text{total}} = \beta_1 \cdot \beta_2 \cdot \beta_3$};
  \node[anchor=north, text width=76mm, align=center, text=casNedge,
        font=\scriptsize] at (30,-17)
    {Gain multiplies along the chain. Flow does not --- each stage draws its
     own current from its own local drive and resistance.};
\end{tikzpicture}
"""

PHILOOP = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize]
  \node[rounded corners=1pt, minimum width=24mm, minimum height=10mm,
        fill=casPfill, draw=casPedge, line width=0.6pt] (a) at (0,0)
        {\texttt{\^{}8} Above/Cause};
  \node[rounded corners=1pt, minimum width=24mm, minimum height=10mm,
        fill=casOfill, draw=casOedge, line width=0.6pt] (b) at (46,0)
        {\texttt{\^{}9} Below/Effect};
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt]
    (a) to[bend left=32] node[midway, above, font=\scriptsize] {triggers} (b);
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt]
    (b) to[bend left=32] node[midway, below, font=\scriptsize] {becomes cause} (a);
  \node[anchor=north, text width=76mm, align=center, text=casNedge,
        font=\scriptsize] at (23,-16)
    {A Phi loop. The effect of one cycle is the cause of the next; the period
     is set by how long the return takes.};
\end{tikzpicture}
"""

WALKDOWN = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
                    tp/.style={circle, minimum size=8mm, draw,
                               line width=0.6pt, inner sep=0pt}]
  \foreach \i/\x/\lab/\f/\e in {
      1/0/TP1/casOfill/casOedge, 2/24/TP2/casOfill/casOedge,
      3/48/TP3/casEfill/casEedge, 4/72/TP4/casNfill/casNedge} {
    \node[tp, fill=\f, draw=\e] (t\i) at (\x,0) {\lab};
  }
  \foreach \a/\b in {1/2, 2/3, 3/4} {
    \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (t\a) -- (t\b);
  }
  \node[anchor=south, font=\scriptsize, text=casOedge] at (0,6)  {as expected};
  \node[anchor=south, font=\scriptsize, text=casOedge] at (24,6) {as expected};
  \node[anchor=south, font=\scriptsize, text=casEedge] at (48,6) {\textbf{first deviation}};
  \node[anchor=south, font=\scriptsize, text=casNedge] at (72,6) {downstream symptom};
  \draw[casEedge, line width=0.7pt] (48,-6) -- (48,-11);
  \node[anchor=north, text width=80mm, align=center, text=casNedge,
        font=\scriptsize] at (36,-12)
    {The fault is at the stage where the signal first departs from
     specification. Everything before it is healthy; everything after it is
     consequence. The cause usually sits one terminal deeper --- on that
     stage's bias.};
\end{tikzpicture}
"""

OHMMODES = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize]
  \draw[casNedge, line width=0.7pt] (0,0) -- (44,0) -- (22,26) -- cycle;
  \draw[casNedge, line width=0.5pt] (11,13) -- (33,13);
  \node at (22,19) {$V$};
  \node at (13,6)  {$I$};
  \node at (31,6)  {$R$};
  \foreach \x/\y/\t/\f in {
      70/22/{\textbf{Measure}\\$I = V / R$}/casCfill,
      70/11/{\textbf{Design}\\$V = I \times R$}/casPfill,
      70/0/{\textbf{Diagnose}\\$R = V / I$}/casEfill} {
    \node[anchor=west, rounded corners=1pt, minimum width=34mm,
          minimum height=9mm, fill=\f, draw=casNedge, line width=0.5pt,
          align=center, font=\scriptsize] at (\x,\y) {\t};
  }
  \node[anchor=north, text width=88mm, align=center, text=casNedge,
        font=\scriptsize] at (44,-7)
    {Cover the term you do not know; the remaining two show how to combine
     them. Which mode you are in depends entirely on which term is unknown.};
\end{tikzpicture}
"""

INSERTS = [
    ("Chapter_05_Resistors.md",
     "## Resistor Networks: The Voltage Divider",
     DIVIDER, "drive-divider",
     "The Drive voltage divider. Two resistors in series split one Drive rail "
     "between expansion and constraint; the tap is the behaviour you get."),
    ("Chapter_08_Diodes.md",
     "## The PN Junction in Cognition: Domain Descent as Forward Bias",
     DESCENT, "descent-diodes",
     "Domain Descent as a diode chain. Forward bias conducts down the "
     "precedence order; the reverse path is blocked."),
    ("Chapter_11_Amplifiers.md",
     "## Multi-Stage Amplifiers: The Understanding → Evaluation → Response Cascade",
     CASCADE, "gain-cascade",
     "A three-stage cascade. Stage gains multiply into "
     "$\\beta_{\\text{total}}$, but attention flow stays local to each stage."),
    ("Chapter_13_Oscillators.md",
     "## The CAS Mapping: A Cognitive Oscillator",
     PHILOOP, "phi-loop",
     "The Phi loop. Above/Cause triggers Below/Effect, which becomes the next "
     "cause --- the structure behind every cognitive rhythm."),
    ("Chapter_24_Debugging_Cognitive_Circuits.md",
     "## The Walk-Down: Probing TP1 → TP2 → TP3 → TP4 in Order",
     WALKDOWN, "walkdown",
     "The walk-down. Probe the test points in order and stop at the first "
     "reading that departs from specification --- that stage is the fault."),
    ("Appendix_I_CAS_Ohm_Measurement_and_Calibration.md",
     "## The three modes",
     OHMMODES, "ohm-modes",
     "The three CAS-Ohm modes. One equation, three uses, selected by which "
     "term you do not already know."),
]


def main() -> None:
    added = 0
    for fname, anchor, body, label, caption in INSERTS:
        path = BOOK / fname
        text = path.read_text(encoding="utf-8")
        if f"fig:{label}" in text:
            print(f"  skip {fname[:46]} (already present)")
            continue
        if anchor not in text:
            print(f"  MISS {fname[:46]}  anchor not found: {anchor[:44]!r}")
            continue
        text = text.replace(anchor, fig(body, label, caption) + "\n" + anchor, 1)
        path.write_text(text, encoding="utf-8")
        added += 1
        print(f"  OK   {fname[:46]}  -> fig:{label}")
    print(f"\n{added}/{len(INSERTS)} figures added")
    if added != len(INSERTS) and added != 0:
        raise SystemExit("add_figures: not every anchor matched")


if __name__ == "__main__":
    main()
