# Rhythm and Register Conversion

*Plate S4.*

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

  \pic at (-42,0) {casoscillator};
  \node[cassymname,anchor=west] at (-31,2) {OSC1  Oscillator};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-2.5) {Self-sustained cycle};
  \node[cassymrole,anchor=west,text width=47mm] at (2,2.5) {Electrical: repeats without a repeating input.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-1.5) {Cognitive: a \texttt{Phi<...>} cycle keeps recurring.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-4.8) {ENG};

  \pic at (-42,-18) {cascrystal};
  \node[cassymname,anchor=west] at (-31,-16) {Y1  Crystal};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-20.5) {Low-drift timing reference};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-15.5) {Electrical: holds one frequency precisely.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-19.5) {Cognitive: stabilizes an entrenched cadence.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-22.8) {ENG};

  \pic at (-42,-36) {caspll};
  \node[cassymname,anchor=west] at (-31,-34) {U2  PLL};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-38.5) {External entrainment loop};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-33.5) {Electrical: locks a cycle to a reference.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-37.5) {Cognitive: exposure entrains internal rhythm.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-40.8) {ISO};

  \pic at (-42,-54) {casadc};
  \node[cassymname,anchor=west] at (-31,-52) {U3  ADC};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-56.5) {Continuous-to-discrete translation};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-51.5) {Electrical: samples and quantizes.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-55.5) {Cognitive: $|f$ becomes $|A$ with loss.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-58.8) {ISO};

  \pic at (-42,-72) {casdac};
  \node[cassymname,anchor=west] at (-31,-70) {U4  DAC};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-74.5) {Discrete-to-continuous translation};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-69.5) {Electrical: reconstructs a smooth signal.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-73.5) {Cognitive: $|A$ becomes $|E$, same state axis.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-76.8) {ISO};
\end{tikzpicture}
\caption{Rhythm and conversion parts. Pure ADC/DAC register examples keep Noetic and Domain fixed; a Domain change requires a separate directed crossing or conversion stage.}\label{fig:sym-s4-rhythm-conversion}
\end{figure}
```

### Oscillator — the part that runs on its own

**The experience.** It is 2 a.m. and you are going over it again. Not solving anything — going over it. The same four minutes of last Tuesday, the same sentence, the same imagined reply. You have been awake for an hour and a half and you have not produced one new thought.

**The same thing, in all four registers.**

- `|A` **Mental** — rumination — the loop that produces no new thought
- `|f` **Emotional** — a mood sustaining itself without new cause
- `|E` **Physical** — pacing; the body keeping the loop running
- `|T` **Spiritual** — a question about meaning that returns every night and is never answered


**What is happening.** A loop is sustaining an ordered cycle with no fresh input. That last part is what makes it an oscillator and not a process: it is not waiting for more information, because it does not need any. Positive feedback has taken over, and the output has become the input. This is the structure of rumination, and it explains why it feels like thinking while producing nothing.

**The part that matches.** An oscillator uses positive feedback to sustain a periodic signal with no external drive. The role-match is exact, and it comes with the engineering answer: you stop an oscillator by adding loss, by breaking the feedback path, or by capturing it with something stronger. In human terms: change the environment, interrupt the loop physically, or give it a competing rhythm.

**Where it breaks.** An oscillator's frequency and amplitude are stable and predictable. Rumination is not: it wanders, it escalates, and it is sensitive to everything from blood sugar to who texted you. Treat the oscillator as the *shape* of the loop, not a claim about its timing.

### Crystal — the part that holds a steady beat

**The experience.** There is a man in your village who has walked the same route at the same hour for thirty years. You have never spoken to him. On the two occasions he missed it — a funeral, and the week of the storm — several people noticed and asked after him. His steadiness is load-bearing for people it has never occurred to him he was holding.

**The same thing, in all four registers.**

- `|A` **Mental** — a principle you apply the same way every time
- `|f` **Emotional** — warmth that is the same on a bad day as a good one
- `|E` **Physical** — a daily practice kept at a fixed hour
- `|T` **Spiritual** — integrity — a reference other people set their clocks by


**What is happening.** A high-`Q` reference: low drift and low pullability. The useful property is not that it is precise in the abstract, but that **other things can lock to it**. A person whose behaviour is the same across contexts — who is recognisably himself at work, at home, and under pressure — becomes a reference other people set their clocks by. That is a real function in any group, and it is usually invisible to the person performing it.

**The part that matches.** A crystal resonator has a very high Q: it barely drifts, and it is hard to pull off frequency. It is used as a timing reference precisely because it will not be moved by the rest of the circuit. The correspondence holds — including the cost, which is that a very high-Q reference is also very hard to adjust when it *is* wrong.

**Where it breaks.** A crystal is passive and mindless. Human steadiness is a maintained achievement, it costs something, and it can be exhausted. Someone who has been the reference for everyone for twenty years may be running on no reserve at all — which is the entire subject of Chapter 16.

### PLL — the part that catches someone else's rhythm

**The experience.** You are walking beside someone and, without deciding to, you are in step. A month into a new job, you notice you have started taking breaks when your team takes breaks, at a pace you would not have chosen. A baby's sleep schedule gradually becomes the household's schedule, and then the household's schedule becomes the baby's.

**The same thing, in all four registers.**

- `|A` **Mental** — absorbing a team's way of thinking in a month
- `|f` **Emotional** — moods synchronising with a partner's
- `|E` **Physical** — falling into step; a sleep schedule entraining the household
- `|T` **Spiritual** — taking on a community's sense of what matters


**What is happening.** An internal rhythm has **locked** to an external reference. This is `^7` Rhythm: the rate and pattern a Mind is exposed to, entraining it. Crucially, locking is *gradual* and has a **range** — you can only be captured by a rhythm close enough to the one you already keep.

**The part that matches.** A phase-locked loop compares its own oscillator to a reference, feeds the difference back, and pulls its oscillator into step. It has a **capture range** (how far off the reference can be for lock to be acquired at all), a **lock range** (how far it can drift once locked and stay locked), and a loop time constant. All three have human counterparts, and the prediction they generate is practical: you cannot entrain someone by asking them to change their rhythm to something far from their own. You have to move it in steps that stay inside their capture range.

**Where it breaks.** A PLL locks to whatever its reference does, including a bad reference, and it does so without judging. So does a person — which is why the interesting question is never "can you entrain?" but "entrained to what, and who chose it?"

### ADC — the part where a continuous feeling becomes a name

**The experience.** For three weeks you have known that something is wrong and have not been able to say what. You describe it as tired. Then, in the middle of an unremarkable conversation, you say out loud — *"I think I'm lonely"* — and something shifts. Nothing about your circumstances has changed. Something has become legible.

**The same thing, in all four registers.**

- `|A` **Mental** — finding the word for what you have been feeling for three weeks
- `|f` **Emotional** — the feeling becoming nameable, and therefore bearable
- `|E` **Physical** — noticing the clenched jaw and calling it tension
- `|T` **Spiritual** — naming a nameless longing as a question of meaning


**What is happening.** A continuous `|f` impression has been converted into a discrete `|A` description. This is one of the most valuable operations available to a person: the analytical register can hold, compare, plan, and communicate, and it cannot do any of that with an unquantised feeling. Naming is not a substitute for feeling. It is a translation that makes the feeling usable by the part of you that talks.

**The part that matches.** An ADC samples a continuous signal and quantises it into discrete codes. In a pure register example the Noetic and the Domain stay fixed — `^4^E_{F2}|f -> ^4^E_{F2}|A` — and only the Register changes. The role-match is exact.

**Where it breaks — and this is the part people get wrong.** Quantisation is **lossy**. The code is not the signal, and the word is not the feeling. Someone who has become fluent at naming their states can start living in the names, and a name is a much coarser thing than the state it stands for. There is also a resolution limit: below a certain granularity, "fine" and "good" and "okay" are the same code, and using them will make two different weeks look identical.

### DAC — the part where a decision becomes a way of living

**The experience.** You decide to be honest with your father. That is a sentence, and it takes a second. What follows is four years of small continuous behaviour: the phone calls you make when you would rather not, the questions you ask, the thing you do not say at Christmas. The decision was discrete. The living of it is not.

**The same thing, in all four registers.**

- `|A` **Mental** — a decision becoming a plan
- `|f` **Emotional** — a commitment showing up as daily kindness
- `|E` **Physical** — the decision rendered as habit, posture and routine
- `|T` **Spiritual** — a conversion becoming a life's work


**What is happening.** A discrete `|A` control has been rendered into continuous `|E` execution. This is the step where intentions either become behaviour or stop, and the gap between the two is where most self-improvement fails. Smoothing matters: the code is stepped, and life is continuous, so the rendering has to interpolate. Somebody who renders "be honest" as a rule rather than a way of moving will be brittle at exactly the moments that matter.

**The part that matches.** A DAC takes discrete codes and reconstructs a smoothed continuous signal. In a pure register example the Noetic and Domain stay fixed and only the Register changes: `^9^O_{F5}|A -> ^9^O_{F5}|E`. The role-match is the conversion of a stepped specification into continuous output.

**Where it breaks — and this one is a hard rule.** A DAC is **not** the inverse of an ADC. The ADC is lossy: it quantised a continuous signal into codes and threw away the detail in between. You cannot run the lossy conversion backwards and recover what was lost — no converter can. Anyone who tells you that naming a feeling precisely enough will give them the feeling back has misread the datasheet. The DAC is a separate, forward direction: control in, behaviour out.

