# Regulation, Protection, and Annotations

*Plate S6.*

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \foreach \x/\name/\picname in {-42/REG/casregulator,-14/FUSE/casfuse,14/BREAKER/casbreaker,42/SWITCH/casswitch} {
    \pic at (\x,18) {\picname}; \node[cassymname,anchor=north] at (\x,12) {\name};
  }
  \foreach \x/\name/\picname in {-42/RAIL/casrail,-14/REFERENCE/casreference,14/METER/casmeter} {
    \pic at (\x,-4) {\picname}; \node[cassymname,anchor=north] at (\x,-10) {\name};
  }
  \draw[caswire] (34,-4)--(50,-4); \node[casprobe] at (42,-4) {};
  \node[font=\sffamily\tiny\bfseries,anchor=south] at (42,-1) {TP};
  \node[cassymname,anchor=north] at (42,-10) {PROBE};
  \node[cassymrole,text width=100mm] at (0,-27)
    {Regulator restores a setpoint. Fuse opens once. Breaker trips and resets. Rail supplies Drive potential. Reference fixes zero. Probe observes without changing the path. Meter states the measurement mode.};
  \draw[flow] (-37,-42)--(-5,-42) node[midway,flowlbl] {solid forward};
  \draw[fbflow] (5,-42)--(37,-42) node[midway,flowlbl] {dashed feedback};
\end{tikzpicture}
\caption{Regulation, protection, and annotation symbols. A fuse threshold must be below every upstream clamp or saturation ceiling that feeds it, or the fuse is unreachable.}\label{fig:sym-s6-protection-annotations}
\end{figure}
```

These are the parts that keep a person running, stop a person running, and let a person see what is going on. They are less glamorous than amplifiers and matter considerably more.

### Regulator — the part that restores you to a baseline

**The experience.** You sleep badly for a week and you notice the change in yourself on the fourth day: shorter fuse, less patience, a tendency to read neutral emails as hostile. You sleep properly for two nights and you are back. Not transformed — back.

**The same thing, in all four registers.**

- `|A` **Mental** — attention restored by two nights of sleep
- `|f` **Emotional** — mood returning to baseline
- `|E` **Physical** — sleep, food, movement
- `|T` **Spiritual** — a practice that keeps you oriented


**What is happening.** Something is holding an operating point against disturbance. Sleep, food, movement, and contact with people you like are not rewards for functioning well; they are the regulation itself, and their absence is a disturbance the loop is trying to correct with the wrong tools. A person running on five hours is not a lesser version of themselves; they are the same circuit with the supply out of tolerance.

**The part that matches.** A voltage regulator holds its output near a setpoint despite changes in input and load. The role-match is exact, including the tolerance band — regulation is not perfection, it is bounded drift.

**Where it breaks.** A regulator has a dropout: below a minimum input it stops regulating and simply passes whatever it has. People have that too, and it is why "just push through" fails past a certain point — past dropout there is no regulation left to push with.

### Fuse — the boundary that only fires once

**The experience.** You have one rule that ends things: if he hits you again, you leave, and you do not come back. You have said it out loud to yourself so that it cannot be renegotiated at three in the morning.

**The same thing, in all four registers.**

- `|A` **Mental** — a rule that ends the argument permanently
- `|f` **Emotional** — the last time
- `|E` **Physical** — leaving the building
- `|T` **Spiritual** — a line that cannot be crossed without breaking faith


**What is happening.** A protective element with a **threshold**, an **action**, and **no reset**. Its whole value is that it is not a judgement call in the moment — the decision was made in the calm and the fuse only executes it. This is also why fuse thresholds have to be *reachable*: a boundary set where nothing can ever cross it is decoration.

**The part that matches.** A fuse severs a circuit permanently when its threshold current is exceeded. One shot, for the stated lifetime of the circuit. The role-match is exact, and so is the discipline around it: the threshold must sit below every upstream ceiling on the path, or it will never trip.

**Where it breaks.** A fuse is a poor fit for anything you intend to negotiate, because a fuse you renegotiate is not a fuse — it is a threat, and it will teach everyone around you that your thresholds are not real. If you need something recoverable, use the breaker below.

### Circuit breaker — the boundary you can reset

**The experience.** You have a rule with your teenager: if the shouting starts, you leave the room and come back in twenty minutes. You have done it maybe forty times. It fires often, it resets every time, and it has changed the temperature of the house.

**The same thing, in all four registers.**

- `|A` **Mental** — “we will talk about it tomorrow”
- `|f` **Emotional** — leaving the room for twenty minutes
- `|E` **Physical** — going for a walk mid-argument
- `|T` **Spiritual** — a sabbath — a deliberate stop that can be resumed


**What is happening.** A protective element that trips on a fault and can be **deliberately reset** once the fault has cleared. The reset is the point: it lets you protect a relationship without ending it, and it makes the protection usable on ordinary bad evenings rather than only on catastrophes.

**The part that matches.** A circuit breaker interrupts on fault and can be reclosed. Use it for recoverable faults.

**Where it breaks.** A breaker that resets automatically — or that you reset without addressing the fault — will simply trip again, and everyone involved will learn to ignore it. Reset is a decision, not a formality.

### Switch — the part that opens and closes one path

**The experience.** You decide not to have the conversation tonight. Not never — tonight. You are tired, the topic is live, and you would rather do it on Sunday. That is a switch being opened on purpose, and the fact that it is on purpose is what keeps it from becoming avoidance.

**The same thing, in all four registers.**

- `|A` **Mental** — deciding not to think about it tonight
- `|f` **Emotional** — deciding to let it go, for now
- `|E` **Physical** — putting the phone in the other room
- `|T` **Spiritual** — choosing to stop asking the question for a season


**What is happening.** A route is being enabled or inhibited by an explicit control. The engineering discipline that matters here is stating three things: what open and closed mean, which state is the default, and what happens if the control fails.

**The part that matches.** A switch physically connects or disconnects a path. The role-match is exact and trivial, which is exactly why it is skipped — and why people end up with routes that are neither deliberately open nor deliberately closed.

**Where it breaks.** A switch has no memory and no judgement. If you open the same conversation every night for a year, you do not have a switch; you have a policy, and it is worth admitting which one you built.

### Rail — the part that supplies the motive

**The experience.** You have not seen anyone for eleven days and you cannot work out why you cannot start anything. Nothing is wrong with your discipline. You are running on one supply, and the one marked *contact with people* is at zero.

**The same thing, in all four registers.**

- `|A` **Mental** — curiosity as fuel for thinking
- `|f` **Emotional** — connection as fuel for feeling
- `|E` **Physical** — vitality: sleep and food
- `|T` **Spiritual** — purpose as the supply that makes the rest worth running


**What is happening.** The seven Drives are motive supplies, and different work runs on different ones. When something will not start, the most useful first question is not *why am I lazy* but *which rail is down* — and the answer is usually specific and fixable rather than characterological.

**The part that matches.** A rail distributes supply potential to everything on the board. No rail, no work, regardless of how well the rest of the circuit is designed.

**Where it breaks.** A Drive is not literally a voltage, and the mapping needs a stated normalisation before it means anything quantitative. Keep it operational: name the rail, name how you know it is low, name what raises it. Do not score yourself out of seven.

### Reference — the part you measure everything against

**The experience.** You spend a weekend at a friend's house where nobody raises their voice and nothing is urgently wrong, and you find it unsettling. You keep waiting for the thing that is about to happen. It does not happen, and you cannot settle.

**The same thing, in all four registers.**

- `|A` **Mental** — the assumption you reason from
- `|f` **Emotional** — what you call a normal amount of love
- `|E` **Physical** — what your body calls a normal level of tension
- `|T` **Spiritual** — what you assume a life is for


**What is happening.** Your reference is not calm. You are measuring a normal weekend against a baseline built in a house where the atmosphere had to be monitored, and by that baseline a quiet house reads as *wrong*. Nothing is malfunctioning except the zero point.

**The part that matches.** A reference node sets what the circuit calls zero; every other measurement is relative to it. An engineered baseline is a design decision, not a discovered fact.

**Where it breaks — and this precision matters.** A reference node is **not** `^0` Idea by identity. It is a convention. Calling a cognitive rest state "the ground" is an engineering convenience, and treating that convention as a metaphysical fact is exactly the kind of drift this library is built to prevent. What you can say is: my measurements are relative to this baseline, and here is why I chose it.

### Meter — the part that names what was measured

**The experience.** You tell your doctor the pain is a seven. She asks what a seven means, and you realise you have no idea. You have been using a number that has never been defined, on a scale you invented in the waiting room.

**The same thing, in all four registers.**

- `|A` **Mental** — “I could not concentrate for more than ten minutes”
- `|f` **Emotional** — “the sadness was 6 of 10” — with the scale stated
- `|E` **Physical** — resting heart rate; hours slept
- `|T` **Spiritual** — how often you acted on what you say you value


**What is happening.** A meter reports a quantity, and a quantity without a stated method is not a measurement. "Anxiety 8/10" is not information; "I could not sit still for more than a minute at any point this afternoon" is.

**The part that matches.** A meter reads a declared electrical quantity — voltage, current, resistance — and the declaration is inseparable from the reading.

**Where it breaks.** A meter is passive and indifferent to what it is measuring. Human self-report is not: the act of measuring changes the state, and the state has an interest in the answer. Report the method alongside the number, and treat a number with no method as a feeling wearing a lab coat.

### Probe — the part that lets you look without joining in

**The experience.** You notice you are about to snap at your daughter and you watch it happen — the tightening, the sentence forming — and then you choose a different sentence. You did not stop the feeling. You observed it, and the observation was enough room.

**The same thing, in all four registers.**

- `|A` **Mental** — noticing a thought as a thought
- `|f` **Emotional** — naming the feeling while it is happening
- `|E` **Physical** — noticing the jaw, the breath, the shoulders
- `|T` **Spiritual** — noticing what you are actually living for, without editing it


**What is happening.** A named point is being read without becoming part of the signal. This is the mechanism behind most of what is called mindfulness, described without the mysticism: naming a state in `|A` while it is occurring gives the analytical register a foothold it would not otherwise have.

**The part that matches.** A test point exposes a conductor for measurement and does not alter the circuit.

**Where it breaks.** A probe reading does not define, explain, or fix the state it reads. Noticing that you are angry is not the same as resolving it, and treating observation as a cure is a very common and very expensive mistake.

### Net label — the part that names the whole signal

**The experience.** You have been describing the week to your friend in pieces: the meeting, the phone call, the thing your son said, the fact that you are sleeping badly. She listens and then says, *"so you're frightened."* You had not said that word. Everything you said was true, and none of it was the wire.

**What is happening.** A bundle of separate observations has been recognised as **one signal with one name**. This is the move that turns a list into a thing you can act on, and it is usually performed by somebody else first, because naming your own signal requires standing far enough back to see its shape — which is exactly what you cannot do while carrying it.

**The same thing, in all four registers.**

- `|A` **Mental** — naming the belief
- `|f` **Emotional** — naming the feeling
- `|E` **Physical** — naming the sensation
- `|T` **Spiritual** — naming what you are living for

**The part that matches.** A net label names a whole conductor, so that every point on it is understood to be the same signal. The role-match is exact, and so is the discipline: the label must name **one** thing. A label reading "tired/stressed/annoyed" names nothing, because a wire carries one signal.

**Where it breaks.** A label is a claim, and a wrong one is worse than none — it sends every later intervention to the wrong place. "You're frightened" is a hypothesis offered with its evidence, not a diagnosis announced from above. And a label, once applied, is sticky: people keep reporting the name long after it has stopped fitting, because the name is easier to carry than the state.

### Solid arrow and dashed arrow — forward and return

**The experience.** Two people have the same conversation for the fifth time. Only one of them has noticed that the conversation is not about the topic — that it is the *return path* of something that happened in the spring.

**The same thing, in all four registers.**

- `|A` **Mental** — this belief leads to that conclusion
- `|f` **Emotional** — this fear leads to that withdrawal
- `|E` **Physical** — this tension leads to that headache
- `|T` **Spiritual** — this commitment leads to that way of living


**What is happening.** A solid arrow is the forward path: this causes that. A dashed arrow is the return: a sampled piece of the output comes back and changes the input. Confusing the two is the most common way a person misreads their own behaviour, because the returning signal usually arrives looking like a fresh cause.

**The part that matches.** Solid is forward flow; dashed is feedback. Marking them is not decoration — it is what lets you tell a new problem from an old one coming back around.

**Where it breaks.** Feedback is delayed, sampled, and lossy. The thing that comes back is not the thing you sent out, and the delay is exactly what makes it unrecognisable.

### The one rule that outranks the rest: reachability

Everything above assumes the protective element can actually fire. A fuse whose threshold sits above every ceiling on the path will never trip. A boundary set where nothing can cross it is not protection; it is a decorative component, and a board whose fuse never fires tests *vacuously* safe.

The human version: **name the threshold, then name the highest level the upstream can actually reach.** If the ceiling is lower than the threshold, you have not built a boundary — you have built a sentence you say to yourself. This is the engineering rule that catches more false safety than any other, and it applies identically to a circuit board and to a person.

