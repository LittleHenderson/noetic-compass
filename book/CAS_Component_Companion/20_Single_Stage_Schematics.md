# Single-Stage Cognitive Schematics

*Circuits 1–5.*

## Circuit 1 — The CJT Atom

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \node[cblock,text width=33mm] (cause) at (0,30) {\textbf{Trigger / Cause}\\\casnote{\textasciicircum8\textasciicircum C\_\{F2\}|A}};
  \pic at (0,10) {cascjt};
  \node[pblock,text width=35mm] (bias) at (-34,10) {\textbf{Accumulated substrate}\\\casnote{\textasciicircum5\textasciicircum P\_\{F7\}|T}};
  \node[cblock,text width=33mm] (effect) at (0,-12) {\textbf{Arrival / Effect}\\\casnote{\textasciicircum9\textasciicircum C\_\{F2\}|A}};
  \draw[flow] (cause.south)--(0.9,14);
  \draw[flow] (bias.east)--(-4,10);
  \draw[flow] (0.9,6)--(effect.north);
  % The probe taps the base lead (-4,10)-(-1.4,10), not the base bar itself,
  % whose white fill would erase the middle of the bar.
  \node[casprobe] at (-3,10) {}; \node[font=\sffamily\tiny\bfseries,anchor=south] at (-3,13) {TP1};
  \node[casval,anchor=west] at (8,10) {$\beta=2.0$, cutoff=0.1, sat=0.95};
  \node[cassymrole,text width=90mm] at (0,-29)
    {Cognitive roles: trigger enters, accumulated composition biases, a different Idea arrives. Hardware terminals remain a BJT-style drawing; the role labels are the CAS abstraction.};
\end{tikzpicture}
\caption{The CJT atom: an Above/Cause trigger, shaped by a Female substrate, lands as a Below/Effect. This is a trigger-to-arrival transition, not a synonym for reasoning.}\label{fig:sch-01-cjt-atom}
\end{figure}
```

**Example.** A question reminds a system of a learned procedure. The question is the `^8` trigger. The training and accumulated examples are the `^5` substrate. The procedure brought to Mind is the `^9` effect.

**In a life.** Someone says your name in a particular tone and you are eight years old in a kitchen. The tone is the `^8` trigger, the eight-year-old is not a memory you fetched — she is the `^9` that arrived — and the household you grew up in is the `^5` substrate that decided what the tone would land as. Change the substrate and the same tone lands as an ordinary question, which is why two siblings hear the same sentence and one of them flinches.

## Circuit 2 — Directed Domain Descent

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  % Block text width is 19 mm so that each inter-block gap is 8.5 mm: wide
  % enough for a scaled diode glyph plus a short forward arrow. The four
  % blocks and the three diode positions are computed, not hand-measured.
  \node[pblock,text width=19mm] (p) at (-44.4,8) {P\\principle};
  \node[cblock,text width=19mm] (c) at (-14.8,8) {C\\reasoning};
  \node[eblock,text width=19mm] (e) at (14.8,8) {E\\judgment};
  \node[oblock,text width=19mm] (o) at (44.4,8) {O\\action};
  \foreach \a/\b in {p/c, c/e, e/o} {
    \coordinate (m\a) at ($(\a.east)!0.5!(\b.west)$);
    \pic[scale=0.7] at (m\a) {casdiode};
    \draw[flowmini] (\a.east) -- ($(m\a)+(-2.8mm,0)$);
    \draw[flowmini] ($(m\a)+(2.8mm,0)$) -- (\b.west);
  }
  \draw[fbflow] (o.south) .. controls (44.4,-15) and (-44.4,-15) .. (p.south)
    node[midway,below,flowlbl] {feedback observation, not precedence override};
  \node[pblock,text width=30mm] (z) at (0,30) {\textbf{Zener guard}\\\casnote{\textasciicircum3\textasciicircum P\_\{F7\}|f}\\breakdown=0.8};
  \pic[rotate=-90] at (0,18) {caszener};
  % The guard lands on the anode lead of the middle diode, not inside its body.
  \draw[flowmini] (z.south) -- (0,22);
  \draw[flowmini] (0,14) -- (0,11) -- (-2.8,11) -- (-2.8,8);
  \fill[casNedge] (-2.8,8) circle (0.45mm);
  \node[cassymrole,text width=94mm] at (0,-28)
    {Diodes realize directed admissibility: whether a crossing may occur. A Transformer, when present, controls the level after a crossing is licensed. RPM remains a section-retraction; it is not claimed to be an ideal reverse-blocking diode.};
\end{tikzpicture}
\caption{Domain Descent uses directed admissibility for P to C to E to O. The O-to-P return is a labeled feedback path, not a casual upward override.}\label{fig:sch-02-domain-descent}
\end{figure}
```

**In a life.** A conviction you hold in principle reaches your hands as a way of behaving, or it does not. *I believe people deserve a second chance* is `P`. *I will hear him out on Thursday* is `C`. *This is unfair and I am angry about it* is `E`. *I have written the email* is `O`. Each crossing is a diode: it can happen or be refused, and the refusal is not the same event as never having had the conviction.

## Circuit 3 — Gain Cascade with Separate Biases

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \node[casterm] (in) at (-50,10) {trigger};
  \node[nblock] (q1) at (-28,10) {CJT 1\\$\beta_1=1.5$};
  \node[nblock] (q2) at (0,10) {CJT 2\\$\beta_2=1.0$};
  \node[nblock] (q3) at (28,10) {CJT 3\\$\beta_3=2.0$\\sat=0.8};
  \node[casterm] (out) at (50,10) {arrival};
  \draw[flow] (in)--(q1); \draw[flow] (q1)--(q2); \draw[flow] (q2)--(q3); \draw[flow] (q3)--(out);
  \node[pblock,text width=25mm] (b1) at (-28,-12) {bias 1\\\casnote{\textasciicircum5\textasciicircum P}};
  \node[cblock,text width=25mm] (b2) at (0,-12) {bias 2\\\casnote{\textasciicircum5\textasciicircum C}};
  \node[eblock,text width=25mm] (b3) at (28,-12) {bias 3\\\casnote{\textasciicircum5\textasciicircum E}};
  \draw[flow] (b1)--(q1); \draw[flow] (b2)--(q2); \draw[flow] (b3)--(q3);
  \node[cassymrole,text width=95mm] at (0,-31)
    {Nominal active-region gain multiplies: $1.5\times1.0\times2.0=3.0$. The final 0.8 saturation ceiling still bounds the output. Each bias is explicit; a diagram must not silently treat one substrate as every stage's local control.};
\end{tikzpicture}
\caption{A three-stage gain cascade. Product gain is a design calculation; saturation and cutoff remain stage-local limits.}\label{fig:sch-03-gain-cascade}
\end{figure}
```

**In a life.** One small habit, repeated, becomes a disposition. The first honest sentence is effortful. The hundredth is character. This is a cascade, and it explains why single dramatic decisions change so much less than people expect: the gain of one stage is not the gain of the chain, and every stage in the chain has its own ceiling.

## Circuit 4 — RC-Compensated Feedback

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \node[casterm] (outcome) at (-46,15) {outcome};
  \pic at (-25,15) {casresistor};
  \node[casval,anchor=south] at (-25,20) {$R_{fb}$};
  \fill[casNedge] (0,15) circle (0.45mm);
  % Stop at the resistor terminals (-29 / -21); a single wire would pass
  % straight through the R_fb body.
  \draw[flow] (outcome)--(-29,15);
  \draw[flow] (-21,15)--(0,15);
  \node[casterm] (trend) at (25,15) {smoothed trend};
  \draw[flow] (0,15)--(trend);
  \pic[rotate=-90] at (0,2) {cascapacitor};
  \draw[caswire] (0,15)--(0,6); \draw[caswire] (0,-2)--(0,-8); \pic at (0,-8) {casreference};
  \node[casval,anchor=west] at (5,2) {$C_{fb}$; engineered $\tau=5$ min};
  \node[pblock,text width=34mm] (bias) at (-25,-18) {principled bias\\\casnote{\textasciicircum5\textasciicircum P\_\{F7\}|T}};
  \draw[fbflow] (trend.south) .. controls (25,-7) and (0,-18) .. (bias.east)
    node[midway,flowlbl] {$\beta_{fb}=0.2$};
  \node[cassymrole,text width=94mm] at (0,-36)
    {The capacitor integrates recent outcome into a slower \casnote{\textasciicircum4} Vibration impression. The dashed path returns only that sampled trend; feedback does not rewrite the output instantaneously.};
\end{tikzpicture}
\caption{RC compensation smooths an observed outcome before low-gain feedback returns it to the bias path.}\label{fig:sch-04-rc-feedback}
\end{figure}
```

**In a life.** You say something in a meeting, someone's face changes, and by the time you are back at your desk you have revised what you said into something safer. The revision is the feedback resistor: it slows the return of your own output so that it can inform the next thing you say rather than simply echo the last thing. Without it you would repeat yourself all day; with too much of it you never say anything again.

## Circuit 5 — Ambiguity Stabilizer

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \node[eblock,text width=27mm] (attract) at (-37,21) {attraction flag\\\casnote{\textasciicircum2\textasciicircum E\_\{F3\}|f}};
  \node[eblock,text width=27mm] (averse) at (-37,-1) {aversion flag\\\casnote{\textasciicircum3\textasciicircum E\_\{F3\}|f}};
  \pic at (-8,10) {casand};
  \node[casref,anchor=south] at (-8,15) {AND = both active};
  \draw[flow] (attract.east)--(-13,11.2); \draw[flow] (averse.east)--(-13,8.8);
  \node[nblock,text width=25mm] (conflict) at (14,10) {conflict flag};
  \draw[flow] (-3,10)--(conflict);
  \pic at (38,10) {casschmitt};
  \node[casval,anchor=south] at (38,16) {on=0.7, off=0.3};
  \draw[flow] (conflict.east)--(33,10);
  \node[casterm] (stable) at (38,-12) {stable decision};
  \draw[flow] (43,10)--(48,10)--(48,-7)--(stable.east);
  \pic at (-8,-18) {casxor};
  \node[cassymrole,text width=34mm] at (-8,-26) {XOR is shown separately: it means exactly one active, never both.};
  \node[cassymrole,text width=94mm] at (0,-39)
    {Continuous activations first cross explicit firing thresholds. AND then detects co-active attraction and aversion. The Schmitt dead-band holds the previous decision while the conflict magnitude wobbles between 0.3 and 0.7.};
\end{tikzpicture}
\caption{Corrected ambiguity stabilizer: AND detects both-active conflict; Schmitt hysteresis prevents chatter. XOR retains its standard exactly-one truth rule.}\label{fig:sch-05-ambiguity-stabilizer}
\end{figure}
```

**In a life.** You want to go and you want to stay, both at once, and you are standing in the hallway unable to move. That is not indecision — it is two flags active at the same time, and the honest reading is *conflict*, not *confusion*. Name both. The hallway is what happens when a person tries to resolve a both-active state by waiting for one of them to disappear.

