# The Signal and Annotation Legend

*Plate S0.*

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm,font=\sffamily\scriptsize]
  \node[casterm] (a) at (-38,20) {source / port};
  \node[casterm] (b) at (38,20) {target / port};
  \draw[flow] (a) -- node[flowlbl] {forward state path} (b);

  \node[casterm] (c) at (-38,4) {effect};
  \node[casterm] (d) at (38,4) {bias};
  \draw[fbflow] (c) -- node[flowlbl] {feedback $\beta$, $\tau$} (d);

  \draw[caswire] (-45,-13) -- (-22,-13);
  \node[casnetlbl,anchor=west] at (-42,-9)
    {\casnote{\textasciicircum8\textasciicircum C\_\{F2\}|A}};
  \node[cassymrole,anchor=west] at (-42,-17) {typed state net};

  \draw[caswire] (-4,-13) -- (19,-13);
  \node[casprobe] at (7.5,-13) {};
  \node[font=\sffamily\tiny\bfseries,anchor=south] at (7.5,-10) {TP1};
  \node[cassymrole,anchor=west] at (-1,-17) {probe / test point};

  \pic at (38,-12) {casreference};
  \node[cassymrole,align=center] at (38,-18) {reference / rest node\\(engineered convention)};

  \draw[line width=0.6pt,draw=casPedge,fill=casPfill] (-48,-35) rectangle (-30,-26);
  \draw[line width=0.6pt,draw=casCedge,fill=casCfill] (-24,-35) rectangle (-6,-26);
  \draw[line width=0.6pt,draw=casEedge,fill=casEfill] (0,-35) rectangle (18,-26);
  \draw[line width=0.6pt,draw=casOedge,fill=casOfill] (24,-35) rectangle (42,-26);
  \node at (-39,-30.5) {P}; \node at (-15,-30.5) {C};
  \node at (9,-30.5) {E};  \node at (33,-30.5) {O};
  \node[cassymrole,align=center] at (0,-41)
    {Domain color reinforces labels; shape and text carry the claim in grayscale.};
\end{tikzpicture}
\caption{The signal-and-annotation legend. Solid arrows move forward; dashed arrows return feedback; every cognitive net is typed or explicitly named.}\label{fig:sym-s0-legend}
\end{figure}
```

**The legend in one sentence: port, name, direction, return, reference.** A port begins or ends a path. A name says what the whole signal is. A solid arrow carries it forward. A dashed arrow brings a sampled piece of it back. A reference fixes the engineered zero.

Read as a person rather than a board, the five parts are the five things you need in order to say anything precise about an experience.

**A port** is a boundary. *"This starts when she walks in. This ends when I leave the car."* Without boundaries, a description of what happened spreads until it covers the whole week and stops being useful.

**A name** is what the wire carries, written down. Not *"I was in a mood"* — a mood is not a signal, it is a weather report. *"I was angry with him, and underneath it I was frightened"* names two wires. Naming is not decoration: an unnamed wire cannot be traced, and most of what people call confusion is a bundle of unnamed signals.

**A solid arrow** is the forward path: this leads to that. *"I did not sleep, and by Thursday I was snapping at people."* Forward paths are what you intervene on if you want to change an outcome.

**A dashed arrow** is the return. A sampled piece of what came out goes back and changes what goes in. This is the one people miss, and it is why the same argument happens five times: the second argument is not a new event, it is the first one coming back around. On a schematic this is drawn dashed so you can tell the difference at a glance. In a life, the returning signal usually arrives wearing the clothes of a fresh cause, which is exactly why you have to look for it on purpose.

**A reference** is the zero you measure from — and this is the one that surprises people. A reference is a **convention**, chosen so that other things can be compared. It is not discovered, and it is not sacred. The most useful question anyone can ask about a strongly-held reaction is not *"why do I feel this?"* but *"what am I measuring this against, and who set that zero?"*

Two rules come with the reference, and both matter later:

- **It is not `^0` Idea by identity.** Calling a calm baseline "ground" is an engineering convenience, not a metaphysical claim.
- **A reference can be wrong.** Somebody raised in a house where the atmosphere had to be monitored has a zero point set by that house. By that zero, a quiet room reads as *something is about to happen*. Nothing is broken except the calibration, and recalibration is a real, slow, possible thing.

