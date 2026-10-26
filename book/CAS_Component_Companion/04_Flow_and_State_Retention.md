# Flow and State Retention

*Plate S1.*

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  % Row backgrounds
  \foreach \y in {0,-18,-36,-54,-72} {
    \draw[rounded corners=1.5pt,fill=casNfill!35,draw=casNedge!45,line width=0.4pt]
      (-53,\y-7) rectangle (53,\y+7);
  }
  % Column guides
  \node[font=\sffamily\tiny\bfseries,text=casNedge,anchor=south] at (-42,9) {SYMBOL};
  \node[font=\sffamily\tiny\bfseries,text=casNedge,anchor=south] at (-22,9) {PART / ROLE};
  \node[font=\sffamily\tiny\bfseries,text=casNedge,anchor=south] at (28,9) {MEMORY LINE};

  % R
  \pic at (-42,0) {casresistor};
  \node[cassymname,anchor=west] at (-31,2) {R1  Resistor};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-2.5) {Activation-current limiter};
  \node[cassymrole,anchor=west,text width=47mm] at (2,2.5) {Electrical: limits current.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-1.5) {Cognitive: limits activation flow.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-4.8) {ENG};

  % C
  \pic at (-42,-18) {cascapacitor};
  \node[cassymname,anchor=west] at (-31,-16) {C1  Capacitor};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-20.5) {State-retention element};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-15.5) {Electrical: charge accumulates.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-19.5) {Cognitive: composition persists.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-22.8) {ENG};

  % L
  \pic at (-42,-36) {casinductor};
  \node[cassymname,anchor=west] at (-31,-34) {L1  Inductor};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-38.5) {Pattern-inertia element};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-33.5) {Electrical: opposes current change.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-37.5) {Cognitive: opposes rhythm change.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-40.8) {ENG};

  % Varactor
  \pic at (-42,-54) {casvaractor};
  \node[cassymname,anchor=west] at (-31,-52) {CV1  Varactor};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-56.5) {Tunable retention};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-51.5) {Electrical: control tunes capacitance.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-55.5) {Cognitive: control tunes retention.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-58.8) {ENG};

  % LC tank
  \pic[rotate=90] at (-45,-72) {casinductor};
  \pic[rotate=90] at (-39,-72) {cascapacitor};
  \draw[caswire] (-45,-68) -- (-39,-68);
  \draw[caswire] (-45,-76) -- (-39,-76);
  \node[cassymname,anchor=west] at (-31,-70) {Z1  LC tank};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-74.5) {Resonant state exchange};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-69.5) {Electrical: L and C exchange energy.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-73.5) {Cognitive: one rate resonates strongest.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-76.8) {ENG};
\end{tikzpicture}
\caption{Flow and state-retention symbols. The short memory line states the preserved functional role; ENG marks a stipulated cognitive quantity.}\label{fig:sym-s1-flow-retention}
\end{figure}
```

### Resistor — the part that limits how fast something gets through

**The experience.** Your brother says something designed to wound you at a family lunch. You feel the whole answer arrive — fully formed, accurate, and lethal — and you say, "Pass the salt." Nothing about the anger changed. The rate at which it reached your mouth did.

**The same thing, in all four registers.**

- `|A` **Mental** — counting to ten before you answer; the argument you build and then decline to make
- `|f` **Emotional** — not letting someone see how much they have just hurt you
- `|E` **Physical** — the slow breath; the hand that stops halfway to the phone
- `|T` **Spiritual** — restraint kept because of who you intend to be, when nobody would ever know


**What is happening.** The activation is real and undiminished. What has been added is a limit on flow: the same pressure, delivered slowly enough that the decision about what to do with it happens somewhere other than mid-sentence. In CAS terms this is restraint on propagation. It lives mostly in `|E` — the deliberate half-second of breath — while the judgment it buys is spent in `|A`.

**The part that matches.** A resistor does not reduce the voltage. It limits current for a given voltage, and it dissipates what it limits as heat. The correspondence is exact at the level of roles: pressure unchanged, rate constrained, cost paid. The cost is real in both cases — the swallowed answer goes somewhere, and it is not free.

**Where it breaks.** A resistor is linear and passive: it limits everything that passes, always, without judgment. Human restraint is selective and expensive. Someone who limits *every* answer is not well-regulated, they are shut down, and the map stops describing them.

### Capacitor — the part that keeps what arrived

**The experience.** Twenty years after she died, you can still hear the exact way your mother said your name when she was pleased. You did not rehearse it. You did not choose to keep it. It stayed.

**The same thing, in all four registers.**

- `|A` **Mental** — a fact you can still recall on demand
- `|f` **Emotional** — warmth that colours a room twenty years later
- `|E` **Physical** — the softening in your shoulders at the sound of a voice
- `|T` **Spiritual** — part of what you would name if asked who you are


**What is happening.** Something arrived once and has persisted, and the persistence is itself doing work — it shapes how you hear praise today. This is `^5` Female: the Mind **is composed of** accumulated Ideas. Note the register: in `|A` it is a fact you can recall on demand; in `|f` it is a warmth that still colours a room; in `|E` it is a particular softening in your shoulders; in `|T` it is part of what you would name if asked who you are.

**The part that matches.** A capacitor holds charge across time and resists a change in the voltage across it. Accumulated composition persists and can decay. That is the whole of it, and the role-match is exact.

**Where it breaks — and this one matters.** A capacitor is a **container**. `^5` Female is not. The Mind does not hold experiences the way a bucket holds water; the Mind is made of them. The moment you write "the Mind contains her memory," you have imported a picture the framework explicitly rejects — a self standing behind its own contents. Write "the Mind is composed of it." The distinction is not pedantry: a container can be emptied and still be a container, and a person cannot.

**The leak is real too.** Capacitance leaks. Good retention is not perfect retention, and the leak rate is a parameter, not a moral failure. Someone who remembers everything at equal vividness is not healthier than someone whose grief has softened a few percent a year.

### Inductor — the part that will not change speed

**The experience.** You have cracked your knuckles the same way since you were nine. You decide, at forty, to stop. Nothing about the decision is difficult. The hand does it anyway — three times before you catch it — and catching it feels like interrupting a sentence.

**The same thing, in all four registers.**

- `|A` **Mental** — the reasoning that keeps arriving back at the old conclusion
- `|f` **Emotional** — loyalty to a person or an idea you have already outgrown
- `|E` **Physical** — the hand that cracks a knuckle before you notice
- `|T` **Spiritual** — a faith or a vocation that will not be hurried into changing


**What is happening.** An established pattern is resisting a *change in its rate*. Not the pattern itself — the change. Inductance opposes any change in current, and it pushes back in proportion to how fast you are asking for the change. This is why habit advice that says "just stop" fails: it requests the highest possible rate of change, and therefore meets the largest possible opposition.

**The part that matches.** An inductor stores energy in a magnetic field and fights a change in current, and it keeps the current flowing when you open the switch — which is why an inductive circuit arcs. That is not a quirk of the analogy; it is the same statement. Abruptly interrupting an established pattern releases the stored energy somewhere, and if you have not provided a path, it will find one.

**Where it breaks.** An inductor's opposition is symmetric and instant. Human inertia is neither: it is weaker for a pattern being *increased* than for one being cut, and it has a refractory period. And unlike a coil, a person can change their own inductance over months — practice reshapes the pattern rather than merely pushing back on its rate.

### Varactor — the part whose retention can be tuned

**The experience.** The smell of a particular brand of cigarettes used to put you straight back in your father's car, and it hurt. Ten years on, the same smell arrives and you think: *him* — and there is more affection in it than pain.

**The same thing, in all four registers.**

- `|A` **Mental** — reframing: the same fact, carrying less weight
- `|f` **Emotional** — a hurt that softens from agony into tenderness
- `|E` **Physical** — a flinch that becomes a pause
- `|T` **Spiritual** — a loss that slowly becomes a source of meaning rather than a wound


**What is happening.** Nothing was deleted. This is the register people miss when they ask how to *forget* something: the memory's **retention was retuned by a control input**, not erased. Therapy, time, and a changed relationship to the memory act as that control. The composition is the same; how strongly it holds, and how sharply it swings when it discharges, has changed.

**The part that matches.** A varactor is a diode whose junction capacitance is set by a reverse-bias voltage. It is not a different component — it is the same junction, tuned by a control signal. That is exactly the human case: same retained content, externally tunable persistence.

**Where it breaks.** A varactor's control is monotonic, reversible, and smooth over its range. Humans are none of those. The same intervention that softens a memory can harden it, the change can be irreversible in one direction, and the curve is not smooth. Read the varactor as *"retention is controllable"* — never as *"turn the dial to reduce pain."*

### LC tank — the part that selects one frequency

**The experience.** You and your partner can discuss money, in-laws, your careers, and the children without difficulty. There is one subject — who was going to move, twenty years ago — that ends the same way every time. Not a similar way. The same way.

**The same thing, in all four registers.**

- `|A` **Mental** — the argument you could have in your sleep — the same three points
- `|f` **Emotional** — the subject that always ends the same way
- `|E` **Physical** — the room, the hour, the particular tone that sets it off
- `|T` **Spiritual** — the unresolved question about what it all meant, re-asked every time


**What is happening.** Coupled retention and inertia, exchanging energy, are picking out one repeating rate and favouring it. The capacitance holds the accumulated charge of the old grievance; the inductance is the established pattern of how the two of you move through it. Together they resonate, and a resonant circuit responds to one frequency far more strongly than to any other. That is why the argument can be set off by almost nothing: a resonant tank barely needs input at the right rate.

**The part that matches.** An LC tank stores energy, swapping it between the capacitor's electric field and the inductor's magnetic field, and it does this most readily at one frequency set by `f₀ = 1/(2π√(LC))`. The role-match to "one recurring fight, one recurring rhythm" is exact, and it predicts something useful: to change the frequency you must change `L` or `C` — the retained charge or the established pattern — not merely resolve to argue better.

**Where it breaks.** A tank is passive and its Q is fixed by its components. A couple can raise or lower their own Q by learning to notice the moment the tank starts ringing. And unlike a circuit, the human version usually has *more than one* tank, and the interesting behaviour is in how they couple.

