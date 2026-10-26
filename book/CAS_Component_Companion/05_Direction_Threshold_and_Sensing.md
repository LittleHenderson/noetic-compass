# Direction, Threshold, and Sensing

*Plate S2.*

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \foreach \y in {0,-18,-36,-54,-72} {
    \draw[rounded corners=1.5pt,fill=casNfill!35,draw=casNedge!45,line width=0.4pt]
      (-53,\y-7) rectangle (53,\y+7);
  }
  \node[font=\sffamily\tiny\bfseries,text=casNedge,anchor=south] at (-42,9) {SYMBOL};
  \node[font=\sffamily\tiny\bfseries,text=casNedge,anchor=south] at (-22,9) {PART / ROLE};
  \node[font=\sffamily\tiny\bfseries,text=casNedge,anchor=south] at (28,9) {MEMORY LINE};

  \pic at (-42,0) {casdiode};
  \node[cassymname,anchor=west] at (-31,2) {D1  Diode};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-2.5) {Directed admissibility guard};
  \node[cassymrole,anchor=west,text width=47mm] at (2,2.5) {Electrical: conducts one way.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-1.5) {Cognitive: licenses one direction.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-4.8) {ISO};

  \pic at (-42,-18) {caszener};
  \node[cassymname,anchor=west] at (-31,-16) {ZD1  Zener};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-20.5) {Threshold plus clamp};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-15.5) {Electrical: conducts at breakdown.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-19.5) {Cognitive: trips, then limits level.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-22.8) {ENG};

  \pic at (-42,-36) {castransformer};
  \node[cassymname,anchor=west] at (-31,-34) {T1  Transformer};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-38.5) {Domain impedance matching};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-33.5) {Electrical: trades voltage for current.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-37.5) {Cognitive: trades abstraction for actionability.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-40.8) {ENG};

  \pic at (-42,-54) {casphotodiode};
  \node[cassymname,anchor=west] at (-31,-52) {PD1  Photodiode};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-56.5) {Stimulus-intake transducer};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-51.5) {Electrical: light becomes current.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-55.5) {Cognitive: stimulus crosses into intake.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-58.8) {ENG};

  \pic[scale=0.82] at (-42,-72) {casbridge};
  \node[cassymname,anchor=west] at (-31,-70) {BR1  Bridge rectifier};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-74.5) {Scalar polarity normalization};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-69.5) {Electrical: alternating polarity becomes one.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-73.5) {Cognitive: PED only; never erase aversion.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-76.8) {PED};
\end{tikzpicture}
\caption{Direction, threshold, conversion, and sensing symbols. The bridge rectifier is intentionally limited to a scalar-polarity teaching analogy; it does not convert Negative into Positive.}\label{fig:sym-s2-direction-threshold}
\end{figure}
```

### Diode — the part that only lets things through one way

**The experience.** You forgive your brother for what he did with the money. You mean it, and it holds. And you notice, two years later, that you no longer lend him anything — not as a policy, and not as punishment. The knowledge simply will not travel back the way it came.

**The same thing, in all four registers.**

- `|A` **Mental** — knowing something you cannot un-know
- `|f` **Emotional** — forgiveness that is real, and trust that did not come back with it
- `|E` **Physical** — a body that will not relax in that person's presence
- `|T` **Spiritual** — a blessing you can still give, in one direction, to someone you cannot let back in


**What is happening.** An admissibility relation has been licensed in one direction and refused in the other. Forgiving is the forward path. Forgetting-what-you-learned is the reverse path, and the reverse path is not blocked by stubbornness — it is blocked structurally. This is why "you said you forgave me" and "I still don't trust you with money" can both be true and neither is a lie.

**The part that matches.** A diode conducts predominantly one way: forward biased, current flows; reverse biased, it does not. It is a one-way gate, not an obstacle. The roles correspond one-for-one, and this is one of the clearest ISO mappings in the library.

**Where it breaks.** A real diode has a reverse breakdown voltage, and past it the gate conducts — hard, and often destructively. So does a person. There is a pressure past which the thing you swore would never get back through comes through all at once, and it does not come through gently.

### Zener — the part that trips at a level and then holds a ceiling

**The experience.** You can take criticism. You have taken a great deal of it and used it well. Then someone says the one thing — about your parenting, about your father — and something changes: your voice flattens, you become extremely polite, and you say, "That's fair, I'll think about it." Nothing more gets in. You are not angry. You are clamped.

**The same thing, in all four registers.**

- `|A` **Mental** — the smooth, agreeable sentence that arrives once you are past your limit
- `|f` **Emotional** — going flat and warm and unreachable under one specific criticism
- `|E` **Physical** — the face that stops moving; the voice that levels out
- `|T` **Spiritual** — protecting a core commitment instead of arguing about it


**What is happening.** Below the threshold the channel is closed and criticism passes through your ordinary processing. At the threshold, a different path conducts, and its job is to cap the output. The politeness is not a strategy; it is the regulator doing its only job, which is to stop the level rising further. In register terms: `|f` has hit a ceiling, and `|A` takes over and produces smooth, agreeable sentences.

**The part that matches.** A Zener diode blocks in reverse until its breakdown voltage, then conducts and clamps the voltage there. Two distinct behaviours, one component, and the transition is sharp rather than gradual. The correspondence holds, including the sharpness — people do not degrade gracefully into their clamp.

**Where it breaks.** A Zener's breakdown voltage is a stable datasheet number. A person's is not: it moves with sleep, with who is in the room, and with how the last hour went. And a Zener clamps cleanly. A human at the clamp is still doing something underneath, and telling someone they are "being defensive" misses that the clamp is protecting a specific, identifiable thing.

### Transformer — the part that changes level without changing content

**The experience.** You explain the same idea three times in one day: to your eight-year-old at breakfast, to a colleague at eleven, and to your mother on the phone at nine. Same idea, three levels, three vocabularies — and the eight-year-old's version is not a lesser version of the colleague's. It is the same content at a different impedance.

**The same thing, in all four registers.**

- `|A` **Mental** — the same idea expressed at three levels of abstraction
- `|f` **Emotional** — saying a hard thing gently without removing the hardness
- `|E` **Physical** — pitch, pace and posture adjusted to whoever is in the room
- `|T` **Spiritual** — carrying a meaning across a gulf — to a child, a culture, or a generation


**What is happening.** A licensed crossing is happening, and the converter is trading abstraction against actionability without adding or removing what is being said. The design decision is the turns ratio: how much precision you spend to get how much grip.

**The part that matches.** A transformer trades voltage against current by a turns ratio. It changes *level* and *impedance*. It does not change content, and — the part that makes this a real correspondence rather than a rhyme — it provides **isolation**: the two sides are not electrically connected. Explaining something to a child and explaining it to a colleague can genuinely be separate conversations, and neither contaminates the other.

**Where it breaks.** A transformer is lossy and its ratio is fixed at manufacture. A person's ratio is adjustable in the moment and improves with practice, and the failure mode is not loss but distortion — usually by flattering the listener, which adds something the original did not contain. A transformer never flatters.

### Photodiode — the part that lets the world in

**The experience.** You have no particular religious belief and no expectation of anything, and you walk into a cathedral you were only visiting for the architecture — and your eyes fill. Or you are driving and a piece of music starts, and by the second bar you have pulled over.

**The same thing, in all four registers.**

- `|A` **Mental** — a new fact that changes what you thought you knew
- `|f` **Emotional** — being moved by music, a building, or a face
- `|E` **Physical** — the hair lifting; the breath catching
- `|T` **Spiritual** — awe — an encounter with something you did not make


**What is happening.** Content arrived from outside. You did not generate it and you did not choose it. The precise reading matters here: `^0` Idea is the content — everything in and outside the Mind — and `^1` Mind is the operation that intakes it. The photodiode does not contain the light and does not invent it. It transduces an external stimulus into something the circuit can use.

**The part that matches.** A photodiode converts incident light into current. The stimulus is external; the device is a transducer, not a source. The two roles map cleanly: external content in, internal signal out, and the operation belongs to the device while the content belongs to the world.

**Where it breaks.** It is tempting — and wrong — to say the photodiode's output *is* the light, or that a person's response *is* the stimulus. The transducer shapes what it admits: its sensitivity curve, its bias, its angle. Two people in the same cathedral are not receiving the same signal, and neither of them is receiving the building itself. Never write `Photodiode< stimulus -> ^0 >`. The output is a `^1` intake, and the `^0` stays on the far side of the boundary.

### Bridge rectifier — the part that turns a swinging scalar into a magnitude

**The badge is PED here, and the reason is worth reading.**

**The experience.** You wake up in a mood that has no direction. You are not sad and you are not happy; you are activated. Your skin is prickly, your thoughts are fast, and you cannot sit down. Friends ask what is wrong. Nothing is wrong. Something is *up*.

**The same thing, in all four registers.**

- `|A` **Mental** — realising you cannot say whether the day was good or bad, only that it was loud
- `|f` **Emotional** — keyed up with no direction; arousal without valence
- `|E` **Physical** — restlessness, prickling skin, no target
- `|T` **Spiritual** — **no honest reading.** This is why the badge is PED. `|T` cannot be manufactured from raw activation


**What is happening.** A quantity that usually has a sign has been read as a magnitude. This is a real and useful description — arousal without valence is a genuine state, and naming it as a magnitude rather than searching for a missing emotion is often what unsticks someone.

**The part that matches, within limits.** A bridge rectifier turns an alternating input into one direction of output. If — and only if — the input is explicitly defined as a **non-valence scalar**, such as `signed_error -> magnitude`, this is a legitimate engineering structure. The mapping is pedagogical: it teaches the shape of the operation.

**Where it breaks, and this is the hard rule.** A bridge rectifier must **never** be used to turn `^3` Negative into `^2` Positive. These are not two signs of one axis. `^3` is repulsion and `^2` is attraction; they are an involution pair, not a polarity flip, and there is no circuit that converts one into the other. Anyone who offers you a component that turns hatred into love has handed you a category error with a schematic attached. If your diagram needs that conversion, the diagram is wrong.

