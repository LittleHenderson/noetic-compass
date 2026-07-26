r"""
Seven figures for Reality Engineering, and the anchors they sit before.

The book teaches four Worlds (93 references), a Recursive Prerequisite Model
(182), prerequisites (243) and a "Desire Tree" that is never actually drawn as
a tree. All of it was prose and ASCII.

Note on the Four Worlds figure: the manuscript uses TWO name sets for the same
four Worlds -- Atziluth/Briah/Yetzirah (35/32/39 uses) and Atum/Bodhi/Citta
(17/18/24). Rather than pick one and silently contradict half the book, the
figure carries both, which turns an ambiguity the prose creates into the one
place a reader can resolve it.
"""

FIG_WORLDS = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
  w/.style={rounded corners=1pt, minimum width=62mm, minimum height=12mm,
            draw, line width=0.6pt, align=center}]
  \node[w, fill=tksAfill, draw=tksAedge] (A) at (0,0)
    {\textbf{A} \; Atziluth / Atum \quad {\scriptsize spiritual, causal}};
  \node[w, fill=tksBfill, draw=tksBedge] (B) at (0,-17)
    {\textbf{B} \; Briah / Bodhi \quad {\scriptsize mental, intellectual}};
  \node[w, fill=tksCfill, draw=tksCedge] (C) at (0,-34)
    {\textbf{C} \; Yetzirah / Citta \quad {\scriptsize emotional, relational}};
  \node[w, fill=tksDfill, draw=tksDedge] (D) at (0,-51)
    {\textbf{D} \; Deha \quad {\scriptsize physical, manifest}};
  \foreach \a/\b in {A/B, B/C, C/D} {
    \draw[-{Latex[length=2mm]}, tksInk, line width=0.7pt] (\a) -- (\b);
  }
  \node[anchor=west, rotate=-90, font=\scriptsize, text=tksInk]
    at (34,-25) {blueprint $\rightarrow$ manifestation};
  \draw[-{Latex[length=2mm]}, tksMuted, line width=0.6pt,
        dash pattern=on 1.6pt off 1.4pt]
    (-34,-51) -- (-34,0);
  \node[anchor=east, rotate=90, font=\scriptsize, text=tksMuted]
    at (-36,-25) {feedback};
\end{tikzpicture}
"""

FIG_ELEMENTS = r"""
\begin{tikzpicture}[x=8.3mm, y=7.0mm, font=\sffamily]
  \foreach \c/\n in {0/1,1/2,2/3,3/4,4/5,5/6,6/7,7/8,8/9,9/10} {
    \node[font=\tiny, text=tksMuted] at (\c+0.5, 0.62) {\n};
  }
  \foreach \r/\w/\f in {0/A/tksAfill, 1/B/tksBfill, 2/C/tksCfill, 3/D/tksDfill} {
    \node[font=\tiny\bfseries, text=tksInk] at (-0.45, -\r-0.5) {\w};
    \foreach \c/\n in {0/1,1/2,2/3,3/4,4/5,5/6,6/7,7/8,8/9,9/10} {
      \draw[draw=tksMuted, line width=0.35pt, fill=\f]
        (\c, -\r) rectangle (\c+1, -\r-1);
      \node[font=\tiny, text=tksInk] at (\c+0.5, -\r-0.5) {\w\n};
    }
  }
  \node[anchor=north, text width=78mm, align=center, font=\scriptsize,
        text=tksMuted] at (5, -4.5)
    {Ten Noetics across, four Worlds down. Every Element is one Noetic
     operating in one World --- B5 is Female in the Mental World, D5 the same
     Noetic made physical.};
\end{tikzpicture}
"""

FIG_FOUNDATIONS = r"""
\begin{tikzpicture}[x=13.6mm, y=7.0mm, font=\sffamily]
  \foreach \c/\f/\nm in {0/F1/Unity, 1/F2/Wisdom, 2/F3/Health, 3/F4/Love,
                         4/F5/Power, 5/F6/Wealth, 6/F7/Purpose} {
    \node[font=\tiny\bfseries, text=tksInk] at (\c+0.5, 0.68) {\f};
    \node[font=\tiny, text=tksMuted] at (\c+0.5, 0.28) {\nm};
  }
  \foreach \r/\w/\f in {0/A/tksAfill, 1/B/tksBfill, 2/C/tksCfill, 3/D/tksDfill} {
    \node[font=\tiny\bfseries, text=tksInk] at (-0.3, -\r-0.5) {\w};
    \foreach \c in {0,...,6} {
      \draw[draw=tksMuted, line width=0.35pt, fill=\f]
        (\c, -\r) rectangle (\c+1, -\r-1);
      \pgfmathtruncatemacro\num{\c+1}
      \node[font=\tiny, text=tksInk] at (\c+0.5, -\r-0.5) {\num\w};
    }
  }
  \node[anchor=north, text width=88mm, align=center, font=\scriptsize,
        text=tksMuted] at (3.5, -4.5)
    {Seven Foundations across four Worlds. A Drive blocked in one World is not
     the same problem as the same Drive blocked in another --- and does not
     take the same fix.};
\end{tikzpicture}
"""

FIG_RPM = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
  st/.style={rounded corners=1pt, minimum width=21mm, minimum height=10mm,
             draw, line width=0.6pt}]
  \node[st, fill=tksAfill, draw=tksAedge] (D) at (0,0)   {D \; Desire};
  \node[st, fill=tksBfill, draw=tksBedge] (W) at (32,0)  {W \; Wisdom};
  \node[st, fill=tksCfill, draw=tksCedge] (P) at (64,0)  {P \; Power};
  \node[st, fill=tksDfill, draw=tksDedge] (O) at (96,0)  {Outcome};
  \foreach \a/\b in {D/W, W/P, P/O} {
    \draw[-{Latex[length=2mm]}, tksInk, line width=0.7pt] (\a) -- (\b);
  }
  \node[font=\scriptsize, text=tksMuted] at (48,9) {scan in order};
  % recursion on the first unmet prerequisite
  \draw[-{Latex[length=2mm]}, tksAccent, line width=0.7pt]
    (W.south) -- ++(0,-9) -- ++(-32,0) -- ++(0,9);
  \node[anchor=north, font=\scriptsize, text=tksAccent] at (16,-10)
    {first unmet prerequisite $\rightarrow$ recurse};
  \node[anchor=north, text width=92mm, align=center, font=\scriptsize,
        text=tksMuted] at (48,-19)
    {Descending into a sub-goal and returning is traversal, not reversal.
     Nothing already satisfied becomes unsatisfied on the way back.};
\end{tikzpicture}
"""

FIG_TREE = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
  n/.style={rounded corners=1pt, minimum width=26mm, minimum height=9mm,
            draw, line width=0.55pt, align=center, font=\scriptsize},
  blocked/.style={n, fill=tksEfill, draw=tksEedge}]
  \node[n, fill=tksAfill, draw=tksAedge] (root) at (44,0) {Prime Desire};
  \node[n, fill=tksBfill, draw=tksBedge] (b1) at (0,-18)  {branch};
  \node[blocked]                          (b2) at (44,-18) {\textbf{blocked}};
  \node[n, fill=tksBfill, draw=tksBedge] (b3) at (88,-18) {branch};
  \foreach \b in {b1,b2,b3} {
    \draw[-{Latex[length=1.7mm]}, tksInk, line width=0.5pt] (root) -- (\b);
  }
  \node[n, fill=tksCfill, draw=tksCedge] (c1) at (26,-36) {sub-prereq};
  \node[blocked]                          (c2) at (62,-36) {\textbf{root block}};
  \draw[-{Latex[length=1.7mm]}, tksInk, line width=0.5pt] (b2) -- (c1);
  \draw[-{Latex[length=1.7mm]}, tksInk, line width=0.5pt] (b2) -- (c2);
  \node[anchor=north, text width=92mm, align=center, font=\scriptsize,
        text=tksMuted] at (44,-46)
    {A Desire Tree. You do not work the Prime Desire --- you walk down to the
     deepest unmet branch and work that. Everything above it is waiting on it.};
\end{tikzpicture}
"""

FIG_OVERTON = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize]
  \draw[tksMuted, line width=0.6pt] (0,0) -- (104,0);
  \foreach \x/\lab in {4/unthinkable, 26/radical, 52/acceptable,
                       78/sensible, 100/policy} {
    \draw[tksMuted, line width=0.5pt] (\x,-1.6) -- (\x,1.6);
    \node[anchor=north, font=\tiny, text=tksMuted, rotate=-24, anchor=east]
      at (\x,-2.4) {\lab};
  }
  \draw[fill=tksBfill, draw=tksBedge, line width=0.6pt, rounded corners=1pt]
    (14,4) rectangle (52,13);
  \node[font=\scriptsize] at (33,8.5) {window, before};
  \draw[fill=tksAfill, draw=tksAedge, line width=0.6pt, rounded corners=1pt]
    (44,17) rectangle (86,26);
  \node[font=\scriptsize] at (65,21.5) {window, after};
  \draw[-{Latex[length=2mm]}, tksAccent, line width=0.7pt] (52,15) -- (66,15);
  \node[anchor=north, text width=94mm, align=center, font=\scriptsize,
        text=tksMuted] at (52,-13)
    {The window does not move because opinion changes. It moves because the
     anchors at its edges are repositioned --- and then opinion follows.};
\end{tikzpicture}
"""

FIG_NJT = r"""
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize]
  \node[rounded corners=1pt, minimum width=22mm, minimum height=20mm,
        fill=tksBfill, draw=tksBedge, line width=0.7pt] (n) at (0,0)
        {\textbf{NJT}};
  \draw[-{Latex[length=2mm]}, tksInk, line width=0.7pt] (-30,0) -- (n.west);
  \node[anchor=east, align=right, font=\scriptsize] at (-31,0)
    {\textbf{Cause}\\{\tiny the incoming Idea}};
  \draw[-{Latex[length=2mm]}, tksInk, line width=0.7pt] (0,-24) -- (n.south);
  \node[anchor=north, align=center, font=\scriptsize] at (0,-25)
    {\textbf{Bias}\\{\tiny what you bring to it}};
  \draw[-{Latex[length=2mm]}, tksInk, line width=0.7pt] (n.east) -- (30,0);
  \node[anchor=west, align=left, font=\scriptsize] at (31,0)
    {\textbf{Effect}\\{\tiny the Idea that lands}};
  \node[anchor=north, text width=92mm, align=center, font=\scriptsize,
        text=tksMuted] at (0,-38)
    {A small change at the bias produces a large change in the effect. That is
     why the same event lands differently on two people --- and why the bias,
     not the cause, is where the leverage is.};
\end{tikzpicture}
"""

# (anchor line matched exactly, tikz body, label, caption)
FIGURES = [
    ("## The Four Worlds: Reality Isn't Flat, You Idiot", FIG_WORLDS, "worlds",
     "The Four Worlds, from causal blueprint down to physical manifestation. "
     "Each World goes by two names; both are in use, and both are given here."),
    ("## Cross-World Interaction Patterns: The Deep Mechanics",
     FIG_ELEMENTS, "elements",
     "The 40 Elements: ten Noetics across four Worlds."),
    ("## The 28 Foundations Integration Matrix", FIG_FOUNDATIONS, "foundations",
     "The 28 Foundations: seven Foundations expressed in each of the four "
     "Worlds."),
    ("## The Recursive Prerequisite Model (RPM): Your Reality Debugger",
     FIG_RPM, "rpm",
     "The Recursive Prerequisite Model. Scan Desire, Wisdom, Power in order "
     "and recurse on the first one that is not met."),
    ("## The Desire Tree: Mapping Your Path (and Your Excuses)",
     FIG_TREE, "tree",
     "A Desire Tree, with the working branch at the deepest unmet "
     "prerequisite rather than at the Prime Desire."),
    ("## The Standard Overton Model", FIG_OVERTON, "overton",
     "Shifting the Overton window by repositioning its anchors."),
    ("## The Core Insight", FIG_NJT, "njt",
     "The Noetic Junction Transistor. Cause in, bias controlling, effect out "
     "--- with the gain sitting on the bias."),
]
