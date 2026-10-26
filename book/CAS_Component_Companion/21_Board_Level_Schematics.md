# Board-Level Cognitive Schematics

*Circuits 6–10.*

## Circuit 6 — CSB Red Path and Reachable Fuse

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \node[pblock,text width=30mm] (decision) at (-45,12) {safety decision\\\casnote{\textasciicircum3\textasciicircum P|<A,f,T>}};
  \node[cblock,text width=29mm,draw=casGreen,line width=1pt] (green) at (-12,24) {\textcolor{casGreen}{\textbf{GREEN CJT}}\\\casnote{\textasciicircum9\textasciicircum C\_\{F2\}|A}\\$\beta=1.0$};
  \node[pblock,text width=29mm,draw=casRed,line width=1pt] (red) at (-12,0) {\textcolor{casRed}{\textbf{RED CJT}}\\\casnote{\textasciicircum9\textasciicircum P\_\{F7\}|T}\\$\beta=10$, sat=0.1};
  \draw[flow] (decision.east)--(green.west); \draw[flow] (decision.east)--(red.west);
  \pic at (17,24) {casfuse}; \node[casval,anchor=south] at (17,29) {cuts GREEN};
  \draw[flow] (green.east)--(13,24); \draw[flow] (21,24)--(37,24);
  \draw[fbflow] (red.east)--(5,0)--(5,24)--(13,24);
  \fill[casNedge] (13,24) circle (0.45mm);
  \node[flowlbl,anchor=west] at (7,13) {sense refusal; threshold=0.05};
  \pic at (43,12) {casmux};
  \draw[flow] (37,24)--(38,13.5); \draw[flow] (red.east)--(38,10.5);
  % The result is taken from the multiplexer OUTPUT lead (48,12), never from
  % its select stub. The select input is driven by the refusal-sense line.
  \node[casterm] (out) at (48,-11) {result}; \draw[flow] (48,12)--(out.north);
  \fill[casNedge] (5,0) circle (0.45mm);
  \draw[fbflow] (5,0)--(5,-19)--(30,-19)--(30,8)--(43,8);
  \node[flowlbl,anchor=west] at (16,-17) {select = refusal sense};
  \node[cassymrole,text width=94mm] at (0,-29)
    {$0.05<0.1$: the refusal can reach the fuse threshold before the red stage's clamp. The sense line trips the latch; the fuse severs the green answer path. The refusal path remains available.};
\end{tikzpicture}
\caption{The corrected CSB red path. A reachable 0.05 fuse threshold sits below the 0.1 refusal clamp and cuts the green path, never the refusal path.}\label{fig:sch-06-csb-red-path}
\end{figure}
```

**In a life.** A small sentence switches something enormous. *I am going to say it tonight* changes a marriage; the sentence itself took a second. The isolation matters: the decision can be made in a calm hour without the consequence reaching back and moving the deciding. Note the direction, always — the large path does not get to steer the small one, however much it feels as though it does.

## Circuit 7 — Differential Comparison

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \node[casterm] (a) at (-43,25) {activation A};
  \node[casterm] (b) at (43,25) {activation B};
  \pic at (0,19) {casdiffpair};
  \draw[flow] (a)--(-4,17.5); \draw[flow] (b)--(4,17.5);
  \node[eblock,text width=32mm] (bias) at (-35,0) {shared bias\\\casnote{\textasciicircum5\textasciicircum E\_\{F4\}|f}};
  \pic at (0,0) {casmirror}; \draw[flow] (bias.east)--(-3.5,0);
  % Tail current: the mirror's right collector drives the pair's shared tail.
  \draw[flow] (2,3.5)--(2,14.6)--(0,14.6);
  \pic at (25,0) {casactiveload};
  \draw[flow] (-2,22)--(-2,26)--(18,26)--(18,1)--(20,1);
  \draw[flow] (2,22)--(2,23)--(16,23)--(16,-1)--(20,-1);
  \node[cblock,text width=30mm] (diff) at (25,-18) {difference landing\\\casnote{\textasciicircum6\textasciicircum C|A $+$ \textasciicircum9\textasciicircum C|A}};
  \draw[flow] (30,0)--(35,0)--(35,-13)--(diff.east);
  \node[cassymrole,text width=94mm] at (-8,-36)
    {Both inputs must be commensurable activations on one axis. Matched gain and one shared bias reject common-mode content. Decomposition is \casnote{\textasciicircum6} Male; the resulting Idea lands as \casnote{\textasciicircum9} Below/Effect.};
\end{tikzpicture}
\caption{Differential comparison rejects what two commensurable inputs share and preserves their difference under one shared bias.}\label{fig:sch-07-differential-comparison}
\end{figure}
```

**In a life.** Two people hear the same criticism. One of them is fine and the other is not, and the difference is not the criticism. Something both of you share — the fact of being criticised, the fact of the week you have both had — is cancelling out, and what is left is the part that is actually about each of you. That is uncomfortable precisely because it is informative.

## Circuit 8 — Rhythm, Resonance, and Entrainment

```{=latex}
\clearpage
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \node[casterm] (internal) at (-48,14) {internal cycle};
  \pic at (-27,14) {casinductor}; \node[casval,anchor=south] at (-27,19) {$L$: pattern inertia};
  \pic at (-8,14) {cascapacitor}; \node[casval,anchor=south] at (-8,19) {$C$: retained state};
  \node[nblock,text width=25mm] (tank) at (13,14) {LC tank\\$f_0$, $Q$};
  \draw[flow] (internal.east)--(-31,14); \draw[flow] (-23,14)--(-12,14); \draw[flow] (-4,14)--(tank.west);
  \node[casterm] (reference) at (-48,-8) {external beat};
  \pic at (-27,-8) {cascrystal};
  \pic at (13,-8) {caspll};
  \draw[flow] (reference.east)--(-31,-8); \draw[flow] (-23,-8)--(7.5,-8);
  \draw[flow] (tank.south)--(13,0)--(13,-5.4);
  \node[oblock,text width=29mm] (rhythm) at (42,3) {entrained rhythm\\\casnote{\textasciicircum7\textasciicircum O|E}};
  \draw[flow] (18.5,-8)--(28,-8)--(rhythm.south); \draw[flow] (tank.east)--(rhythm.north);
  \node[cassymrole,text width=94mm] at (0,-28)
    {The LC tank expresses \casnote{\textasciicircum4} Vibration as resonance: one rate strikes the strongest chord. The PLL expresses \casnote{\textasciicircum7} Rhythm as entrainment: repeated external timing conditions the internal cycle. The crystal is a low-drift reference, not a Noetic by itself.};
\end{tikzpicture}
\caption{The COB separates resonance from entrainment: LC selects the resonant rate; PLL locks the repeating cycle to a reference.}\label{fig:sch-08-rhythm-entrainment}
\end{figure}
```

**In a life.** A practice rhythm and an external rhythm find each other: a new baby's sleep and the household's week; a runner's cadence and a partner's; a team's pace and a new starter's. The lock is gradual and it has a range, which is the practical fact — you cannot drag somebody into a rhythm far from their own, and you can walk them into it in steps.

## Circuit 9 — Retention, Leakage, Refresh, and Lacunarity

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \node[casterm] (exp) at (-48,14) {experience};
  \pic at (-30,14) {casswitch}; \node[casval,anchor=south] at (-30,19) {charge};
  \pic at (-10,14) {cascapacitor}; \node[casval,anchor=south] at (-10,19) {$C=200$};
  \draw[flow] (exp.east)--(-34,14); \draw[flow] (-26,14)--(-14,14);
  \pic[rotate=-90] at (-6,2) {casresistor};
  \draw[caswire] (-6,14)--(-6,6); \draw[caswire] (-6,-2)--(-6,-10); \pic at (-6,-10) {casreference};
  % Three-way junction: capacitor plate, leakage tap, and the flow to discharge.
  \fill[casNedge] (-6,14) circle (0.45mm);
  \node[casval,anchor=west] at (0,2) {leakage=0.001};
  \pic at (12,14) {casswitch}; \node[casval,anchor=south] at (12,19) {discharge};
  \node[casterm] (recall) at (35,14) {recalled state}; \draw[flow] (-6,14)--(8,14); \draw[flow] (16,14)--(recall);
  \pic at (12,-9) {casoscillator}; \node[casval,anchor=west] at (18,-9) {refresh pump: \textasciicircum7\textasciicircum C};
  % The pump returns charge to the retention node, landing on the leakage tap.
  \draw[fbflow] (12,-6)--(12,8)--(-6,8);
  \fill[casNedge] (-6,8) circle (0.45mm);
  \node[nblock,text width=29mm] (scan) at (38,-9) {lacunarity scan\\charge $<0.05$};
  \draw[flow] (recall.south)--(scan.north);
  \node[cassymrole,text width=94mm] at (0,-30)
    {A low reading alone cannot distinguish never-written from leaked-away. Write and refresh history must accompany the charge probe. The capacitor models persistence of composition, not a Mind as a container.};
\end{tikzpicture}
\caption{A CMB cell retains state, leaks, refreshes, and exposes low-charge addresses; provenance separates true lacunae from forgotten contents.}\label{fig:sch-09-memory-cell}
\end{figure}
```

**In a life.** You remember, and you are changed by the remembering, and over years the change softens. This is retention with a leak, refreshed by rehearsal, occasionally showing a gap where none was. The gap is the part people fear most, and it is worth saying plainly: a low reading cannot tell you whether something was never written or has faded since. Only the history can.

## Circuit 10 — Drive Supply, Sequence, Brownout, and Silence

```{=latex}
\clearpage
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \foreach \x/\f/\name in {-45/F1/Unity,-30/F2/Wisdom,-15/F3/Vitality,0/F4/Connection,15/F5/Agency,30/F6/Structure,45/F7/Purpose} {
    \pic at (\x,30) {casrail}; \node[font=\sffamily\tiny\bfseries,anchor=south] at (\x,33) {\f};
    \node[font=\sffamily\tiny,anchor=north] at (\x,27) {\name};
  }
  \node[nblock,text width=95mm] (regs) at (0,15) {per-domain regulators and dial limiters\\dials 3--9; involution-pair divergence $\leq4$};
  \node[pblock,text width=20mm] (p) at (-39,-2) {P\\power-good};
  \node[cblock,text width=20mm] (c) at (-13,-2) {C\\power-good};
  \node[eblock,text width=20mm] (e) at (13,-2) {E\\power-good};
  \node[oblock,text width=20mm] (o) at (39,-2) {O\\enable};
  \draw[flow] (regs.south)--(p.north); \draw[flow] (p.east)--(c.west); \draw[flow] (c.east)--(e.west); \draw[flow] (e.east)--(o.west);
  \node[nblock,text width=32mm] (bo) at (-27,-20) {F3-rail brownout\\trip 4.2; release 5.4};
  \node[nblock,text width=32mm] (thermal) at (12,-20) {thermal monitor\\warning / critical / emergency};
  % Regulator block sits 8.5 mm below the rail taps: an explicit bus closes it.
  \draw[caswire] (-45,27.5)--(45,27.5);
  \draw[caswire] (0,27.5)--(regs.north);
  \foreach \x in {-45,-30,-15,0,15,30,45} { \fill[casNedge] (\x,27.5) circle (0.45mm); }
  \node[casterm] (silent) at (43,-20) {silent cutoff};
  \draw[flow] (-15,27.5)--(-15,22)--(-27,22)--(bo.north); \draw[flow] (bo.east)--(thermal.west); \draw[flow] (thermal.east)--(silent.west);
  \node[cassymrole,text width=100mm] at (0,-38)
    {Operational output enables only after P, C, and E are power-good. Brownout uses hysteresis. Emergency response cuts all CJTs to silence; it does not improvise an output while the supply is invalid.};
\end{tikzpicture}
\caption{The CPMB supplies seven Drive rails, regulates them, enforces P-to-C-to-E-to-O startup, derates on brownout, and fails closed to silence at emergency.}\label{fig:sch-10-cpmb-supply}
\end{figure}
```

**In a life.** The whole board in one picture. Somebody is running on purpose and structure, has not slept properly in four months, and is still delivering — right up until the afternoon when the lights go out. The output was clean the entire time, which is precisely why nobody looked at the supply.

