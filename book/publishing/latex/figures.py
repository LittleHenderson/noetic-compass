r"""
The eight structural figures for Thinking in Cognitive Architecture, and the
anchors they are inserted before.

The book ran 786 pages with zero figures while describing, in prose, a
"40-State Heatmap" that "provides an instant visual diagnostic". These are the
diagrams the text already assumes the reader can see.

Each figure is inserted immediately BEFORE its anchor line, which is matched on
exact text. If an anchor stops matching because the manuscript changed, the
inserter fails loudly rather than silently dropping the figure.
"""

FIG_NOETICS = r"""
\begin{tikzpicture}
  % Involution pairs placed FACING each other, which is the structural claim.
  % A ring layout would put them side by side and say nothing.
  \foreach \i/\sym/\name in {0/2/Positive, 1/5/Female, 2/8/{Above/Cause}} {
    \node[casnode, minimum width=30mm, font=\scriptsize]
      (L\i) at (0, -\i*11mm) {\texttt{\^{}\sym} \; \name};
  }
  \foreach \i/\sym/\name in {0/3/Negative, 1/6/Male, 2/9/{Below/Effect}} {
    \node[casnode, minimum width=30mm, font=\scriptsize]
      (R\i) at (56mm, -\i*11mm) {\texttt{\^{}\sym} \; \name};
  }
  \foreach \i in {0,1,2} { \draw[casinvol] (L\i) -- (R\i); }

  \node[caslabel, font=\tiny] at (28mm, 7mm) {three involution pairs};

  % the four self-duals
  \foreach \i/\sym/\name in {0/0/Idea, 1/1/Mind, 2/4/Vibration, 3/7/Rhythm} {
    \node[casnode, minimum width=24mm, font=\scriptsize]
      (S\i) at (\i*30mm - 17mm, -40mm) {\texttt{\^{}\sym} \; \name};
    \draw[casinvol] (S\i.south) ++(-4mm,-1mm)
      arc (200:-20:4mm and 2.6mm);
  }
  \node[caslabel, font=\tiny, align=center] at (28mm, -50mm)
    {four self-duals --- each its own inverse};
\end{tikzpicture}
"""

FIG_DOMAINS = r"""
\begin{tikzpicture}[node distance=7mm]
  \node[casdomain] (P) {P \; Principled};
  \node[casdomain, below=of P] (C) {C \; Cognitive};
  \node[casdomain, below=of C] (E) {E \; Evaluative};
  \node[casdomain, below=of E] (O) {O \; Operational};
  \draw[casflow] (P) -- (C);
  \draw[casflow] (C) -- (E);
  \draw[casflow] (E) -- (O);
  \node[caslabel, right=2mm of P] {commitments, values, hard boundaries};
  \node[caslabel, right=2mm of C] {reasoning, analysis, representation};
  \node[caslabel, right=2mm of E] {judgment, weighing, assessment};
  \node[caslabel, right=2mm of O] {action, output, execution};
  % feedback path
  \draw[casfeedback] (O.west) -- ++(-9mm,0) |- (P.west);
  \node[caslabel, rotate=90, anchor=south] at ($(O.west)+(-11mm,19mm)$)
    {feedback};
  \node[caslabel, anchor=north west] at ($(O.south west)+(0,-4mm)$)
    {Descent is causal precedence: $P \succ C \succ E \succ O$.
     The return path carries signal, not authority.};
\end{tikzpicture}
"""

FIG_DRIVES = r"""
\begin{tikzpicture}
  % Six drives in inversion pairs, F4 self-dual at the centre.
  \foreach \i/\lab/\nm in {0/F1/Unity, 1/F2/Wisdom, 2/F3/Vitality} {
    \node[casnode, minimum width=26mm] (L\i) at (0, -\i*11mm) {\lab \; \nm};
  }
  \foreach \i/\lab/\nm in {0/F7/Purpose, 1/F6/Structure, 2/F5/Agency} {
    \node[casnode, minimum width=26mm] (R\i) at (58mm, -\i*11mm) {\lab \; \nm};
  }
  \foreach \i in {0,1,2} { \draw[casinvol] (L\i) -- (R\i); }
  \node[casnode, minimum width=26mm] (F4) at (29mm, -36mm) {F4 \; Connection};
  \node[draw=casmuted, circle, inner sep=1.1mm, line width=0.4pt] at (F4) {};
  \node[caslabel, anchor=north] at (29mm, -44mm)
    {F4 is self-dual: it has no opposing drive.};
\end{tikzpicture}
"""

FIG_RPM = r"""
\begin{tikzpicture}[node distance=6mm]
  \node[casnode] (A0) {A0\\[-2pt]{\tiny Pure Desire}};
  \node[casnode, right=of A0] (D) {$D_n$\\[-2pt]{\tiny Desire}};
  \node[casnode, right=of D] (W) {$W_n$\\[-2pt]{\tiny Wisdom}};
  \node[casnode, right=of W] (P) {$P_n$\\[-2pt]{\tiny Power}};
  \node[casnode, right=of P] (O) {Outcome};
  \draw[casflow] (A0) -- (D);
  \draw[casflow] (D) -- (W);
  \draw[casflow] (W) -- (P);
  \draw[casflow] (P) -- (O);
  \node[caslabel, anchor=north, text width=88mm, align=center]
    at ($(W.south)+(0,-7mm)$)
    {Satisfaction runs one way. Reaching a later stage does not re-derive or
     un-satisfy an earlier one --- the chain is a section-retraction, not an
     adjunction. A gap at any stage blocks everything downstream of it.};
\end{tikzpicture}
"""

FIG_INVERSION = r"""
\begin{tikzpicture}
  \def\R{24mm}
  \node[casnode, font=\scriptsize] (c) at (0,0) {Inversion};
  \foreach \i/\ax/\desc in {
    0/N/{operator},
    1/W/{domain},
    2/F/{drive},
    3/E/{entropy},
    4/S/{sub-drive},
    5/A/{pathway},
    6/P/{compound}} {
    \pgfmathsetmacro\ang{90 - \i*(360/7)}
    \node[casnode, font=\scriptsize, minimum width=15mm]
      (a\i) at (\ang:\R) {\textbf{\ax}\\[-2pt]{\tiny\desc}};
    \draw[casflow, draw=casmuted] (c) -- (a\i);
  }
  \node[caslabel, align=center] at (0,-34mm)
    {\textbf{P} is the seventh axis but not a seventh mechanism ---
     it is two or more of the other six firing together.};
\end{tikzpicture}
"""

FIG_STATES = r"""
\begin{tikzpicture}[x=8.6mm, y=7.2mm]
  \foreach \c/\sym in {0/0,1/1,2/2,3/3,4/4,5/5,6/6,7/7,8/8,9/9} {
    \node[caslabel, font=\tiny] at (\c+0.5, 0.62) {\texttt{\^{}\sym}};
  }
  \foreach \r/\d in {0/P, 1/C, 2/E, 3/O} {
    \node[caslabel, font=\tiny\bfseries] at (-0.45, -\r-0.5) {\d};
    \foreach \c in {0,...,9} {
      \draw[draw=casmuted, line width=0.35pt, fill=caswash]
        (\c, -\r) rectangle (\c+1, -\r-1);
      \node[font=\tiny, text=casink] at (\c+0.5, -\r-0.5) {\d\c};
    }
  }
  \node[caslabel, anchor=north, text width=80mm, align=center]
    at (5, -4.55)
    {Ten Noetics across, four Domains down. The same Noetic behaves
     differently in each Domain --- position, not label, carries the meaning.};
\end{tikzpicture}
"""

FIG_HEATMAP = r"""
\begin{tikzpicture}[x=8.6mm, y=7.2mm]
  \foreach \c/\sym in {0/0,1/1,2/2,3/3,4/4,5/5,6/6,7/7,8/8,9/9} {
    \node[caslabel, font=\tiny] at (\c+0.5, 0.62) {\texttt{\^{}\sym}};
  }
  \foreach \r/\d in {0/P, 1/C, 2/E, 3/O} {
    \node[caslabel, font=\tiny\bfseries] at (-0.45, -\r-0.5) {\d};
    \foreach \c in {0,...,9} {
      \draw[draw=casmuted, line width=0.35pt, fill=caswash]
        (\c, -\r) rectangle (\c+1, -\r-1);
    }
  }
  % the worked example: 60% ^3^C, 30% ^1^C, 10% ^0^P
  \fill[casaccent, opacity=0.85] (3,-1) rectangle (4,-2);
  \node[font=\tiny, text=white] at (3.5,-1.5) {60};
  \fill[casaccent, opacity=0.45] (1,-1) rectangle (2,-2);
  \node[font=\tiny, text=casink] at (1.5,-1.5) {30};
  \fill[casaccent, opacity=0.18] (0,0) rectangle (1,-1);
  \node[font=\tiny, text=casink] at (0.5,-0.5) {10};
  \node[caslabel, anchor=north, text width=82mm, align=center]
    at (5, -4.55)
    {A mind is never wholly in one state. This reading is
     60\% \texttt{\^{}3\^{}C}, 30\% \texttt{\^{}1\^{}C}, 10\%
     \texttt{\^{}0\^{}P} --- cognitive aversion dominant, awareness
     secondary, a trace of principled Idea.};
\end{tikzpicture}
"""

FIG_DIALS = r"""
\begin{tikzpicture}[x=7.4mm, y=6.2mm]
  % Legal band for an involution pair: |a - b| <= 4, each in [3,9].
  \foreach \v in {3,4,5,6,7,8,9} {
    \node[caslabel, font=\tiny] at (\v-2, 0.55) {\v};
    \node[caslabel, font=\tiny] at (-0.55, -\v+2) {\v};
  }
  \foreach \a in {3,...,9} {
    \foreach \b in {3,...,9} {
      \pgfmathtruncatemacro\diff{abs(\a-\b)}
      \ifnum\diff>4
        \fill[casmuted, opacity=0.18] (\a-2.5, -\b+2.5) rectangle (\a-1.5, -\b+1.5);
      \else
        \fill[casaccent, opacity=0.30] (\a-2.5, -\b+2.5) rectangle (\a-1.5, -\b+1.5);
      \fi
      \draw[draw=casmuted, line width=0.3pt]
        (\a-2.5, -\b+2.5) rectangle (\a-1.5, -\b+1.5);
    }
  }
  \node[caslabel, font=\tiny, rotate=90] at (-1.6, -2.5) {dial \texttt{\^{}3}};
  \node[caslabel, font=\tiny] at (2.5, 1.5) {dial \texttt{\^{}2}};
  \node[caslabel, anchor=north, text width=76mm, align=center]
    at (2.5, -6.2)
    {Shaded: admissible. Grey: rejected with HTTP 422. Both dials must sit in
     $[3,9]$ and may not diverge by more than four points.};
\end{tikzpicture}
"""

# (anchor text matched exactly, figure body, label, caption)
FIGURES = [
    (" The Geometry of Thought", FIG_NOETICS, "noetics",
     "The ten Noetics. Three involution pairs, each Noetic facing its "
     "opposite, and four self-duals that invert to themselves."),
    (" The Descent: How Ideas Become Reality (P → C → E → O)",
     FIG_DOMAINS, "domains",
     "Domain Descent. Causation flows downward through the precedence order; "
     "experience returns as signal along the feedback path."),
    (" The Spectrum of Drives (F1 to F7)", FIG_DRIVES, "drives",
     "The seven Core Drives in inversion pairs, with F4 Connection self-dual "
     "at the centre."),
    (" The Universal Sequence: D/W/P", FIG_RPM, "rpm",
     "The Recursive Prerequisite Model. Desire, then Wisdom, then Power --- "
     "each stage gated by the one before it."),
    (" The Seven Axes of Inversion", FIG_INVERSION, "inversion",
     "The seven Inversion Axes. Compound inversion is not a seventh kind but "
     "the simultaneous firing of several."),
    (" Navigating the Matrix: The Rows and Columns", FIG_STATES, "states",
     "The forty Cognitive States: ten Noetics by four Processing Domains."),
    (" The 40-State Heatmap", FIG_HEATMAP, "heatmap",
     "A 40-State Heatmap. Activation is a distribution across the matrix, not "
     "a single occupied cell."),
    (" Why Involution Pairs Can't Diverge Beyond 4 Points", FIG_DIALS, "dials",
     "The admissible dial region for an involution pair. Settings outside the "
     "band are rejected at configuration time."),
]
