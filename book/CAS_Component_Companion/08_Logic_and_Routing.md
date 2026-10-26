# Logic and Routing

*Plate S5.*

```{=latex}
\begin{figure}[H]
\centering
\begin{tikzpicture}[x=1mm,y=1mm]
  \foreach \x/\name/\picname in {-44/AND/casand,-22/OR/casor,0/NOT/casnot,22/NAND/casnand,44/NOR/casnor} {
    \pic at (\x,22) {\picname}; \node[cassymname,anchor=north] at (\x,16) {\name};
  }
  \foreach \x/\name/\picname in {-44/XOR/casxor,-22/XNOR/casxnor,0/MUX/casmux,22/DEMUX/casdemux,44/RELAY/casrelay} {
    \pic at (\x,0) {\picname}; \node[cassymname,anchor=north] at (\x,-6) {\name};
  }
  \pic at (0,-25) {casschmitt};
  \node[cassymname,anchor=north] at (0,-31) {Schmitt trigger};
  \node[cassymrole,text width=95mm] at (0,-42)
    {Gates act on explicitly thresholded firing flags. AND detects both-active conflict; XOR detects exactly-one; XNOR detects equality and includes both-inactive. MUX/DEMUX route by a stated select signal. Relay control and switched path remain isolated.};
  \node[font=\sffamily\tiny\bfseries] at (46,-42) {ENG};
\end{tikzpicture}
\caption{Logic and routing symbols. Boolean truth rules apply only after continuous CAS activations have been converted into explicit firing flags.}\label{fig:sym-s5-logic-routing}
\end{figure}
```

Gates act on **explicitly thresholded flags** — a continuous state has first been converted into a yes or a no by a stated rule. That preliminary step is where nearly all the argument about these components belongs, because the gate itself is trivial and the threshold is not.

### AND — the part that needs every condition at once

**The experience.** You will lend your brother money if he has a plan **and** he has stopped drinking. Either one alone is not enough, and you know from experience that treating either one alone as enough is how the last two loans went.

**The same thing, in all four registers.**

- `|A` **Mental** — two conditions that must both hold before you act
- `|f` **Emotional** — love and trust as separate flags; either one alone is not enough
- `|E` **Physical** — calm body **and** willing mind — both, or you will not sleep
- `|T` **Spiritual** — conviction together with practice


**What is happening.** A decision is being held behind two conditions that must both be active. The useful discipline is that you named them in advance, in the calm, rather than negotiating them in the moment when one of them is failing.

**The part that matches.** An AND gate is true only when every input is true. Threshold each condition first, and the gate does the rest.

**Where it breaks.** A well-formed promise may pull you toward helping *and* away from it at the same time. If both flags are genuinely active, the correct reading is not that one of them is fake — it is that you have a **conflict**, and the component for that is AND reporting both-active, not a choice made by shouting louder. Route the conflict to somewhere it can be deliberated. Do not suppress it.

### OR — the part where any one thing is enough

**The experience.** There are three signs that mean you should leave the party: your chest tightening, the third drink, and the moment you start rehearsing what you will say in the car. Any one of them is enough. You do not need all three, and waiting for all three is how you end up staying until two in the morning.

**The same thing, in all four registers.**

- `|A` **Mental** — any one of three reasons is enough to stop
- `|f` **Emotional** — any one of several feelings means leave
- `|E` **Physical** — any one physical warning sign
- `|T` **Spiritual** — any one thing that breaks a commitment


**What is happening.** Several flagged conditions are being combined so that any one of them can trigger the exit. This is the structure of a well-designed personal rule: it fires early, it is unambiguous, and it does not require you to argue with yourself.

**The part that matches.** An OR gate is true when at least one input is true. The role-match is exact.

**Where it breaks.** OR preserves alternatives; it does not integrate them. Three warning signs do not add up to a fourth, worse thing — they are three separate routes to the same flag. If you want them combined into a severity, that is an arithmetic sum, not a gate, and you should say so.

### NOT — the part that flips one flag

**The experience.** Someone asks whether you are angry. You say no. You are not lying and you are not angry — but you are also not *not* angry in the ordinary sense, and both of you can hear it.

**The same thing, in all four registers.**

- `|A` **Mental** — “I'm not angry” as a threshold statement, not a fact
- `|f` **Emotional** — equanimity misread by others as coldness
- `|E` **Physical** — stillness that is not calm
- `|T` **Spiritual** — doubt that is not disbelief


**What is happening.** A flag has been complemented inside a stated frame. The frame is what matters: "not angry" means *below the threshold I am using for angry*, and your threshold and theirs may differ. Naming the frame is what turns a confusing exchange into a clear one.

**The part that matches.** NOT is the Boolean complement of one input. It is the simplest and most easily abused component in the library.

**Where it breaks — hard rule.** NOT maps to a Noetic involution only for a licensed pair: `^2↔^3`, `^5↔^6`, `^8↔^9`. The self-duals `^0`, `^1`, `^4` and `^7` are unchanged by it. A Boolean complement of a flag is not the involution of a state, and treating "not attracted" as "repelled" is a category error that will produce bad advice at speed.

### NAND — the part that stops when everything lines up

**The experience.** A safety rule at work: the machine runs unless *both* the guard is open and the operator is clear — at which point it stops. It is the inversion of an all-required condition, and it is written that way because "stop unless it is obviously fine" is a safer default than "go if it looks all right."

**The same thing, in all four registers.**

- `|A` **Mental** — the one combination that must never both be true
- `|f` **Emotional** — exhaustion plus resentment: stop
- `|E` **Physical** — pain plus pushing through
- `|T` **Spiritual** — a compromise that would defeat the entire point


**What is happening.** The negation of an AND. Where AND asks *have all conditions been met?*, NAND asks *is this the one combination I must never allow?*

**The part that matches.** NAND is false only when every input is true. It is the standard building block of fail-safe logic, and its human use is the same: a small number of conditions whose simultaneous presence is unacceptable.

**Where it breaks.** NAND needs the same explicit thresholds as AND, and it inherits AND's blind spot: it is silent about every combination except the one it forbids.

### NOR — the part that acts only when nothing is wrong

**The experience.** You will have the difficult conversation tonight if nobody is drunk, nobody has just been criticised, and the children are asleep. Not if one of those is fine — if *all* of them are quiet. The rule is deliberately restrictive, and it means some nights the conversation does not happen.

**The same thing, in all four registers.**

- `|A` **Mental** — act only when every condition is quiet
- `|f` **Emotional** — have the conversation only when nobody is raw
- `|E` **Physical** — only when rested, fed and well
- `|T` **Spiritual** — only when the motive is clean


**What is happening.** A permissive condition that requires **every** input to be inactive. This is the fail-closed pattern, and its cost is real: it will refuse to act on nights when acting would have been fine.

**The part that matches.** NOR is true only when every input is false. Use it when the cost of a bad attempt is much higher than the cost of waiting.

**Where it breaks.** A NOR gate can be starved into permanent silence by one input that never goes false — one person who is never sober, one issue that is never calm. If a NOR condition has been unmet for months, that is not patience; it is a circuit that will never fire, and the remedy is upstream.

### XOR — the part where exactly one can pass

**The experience.** Two people have each told you something in confidence, and you have discovered that telling either one what the other said would hurt them both. You can honour one confidence or the other. You cannot honour both, and choosing both is the same as choosing neither.

**The same thing, in all four registers.**

- `|A` **Mental** — two conclusions, only one of which can be acted on
- `|f` **Emotional** — two loyalties, one choice
- `|E` **Physical** — two commitments at the same hour
- `|T` **Spiritual** — two callings; you cannot serve both


**What is happening.** Exactly one of two mutually exclusive paths may be taken. This is a real and common human structure — loyalty conflicts, mutually exclusive commitments, two jobs — and naming it as *exactly one* is often the thing that ends a week of agonising.

**The part that matches.** XOR is true when exactly one input is true. Standard, unambiguous, and often misremembered.

**Where it breaks — and this is the most common error in the whole library.** XOR is **not** a both-active conflict detector. When both attraction and aversion are firing, XOR is **false** — it says nothing useful. That situation is AND's job. If you find a diagram using XOR to "detect ambivalence," the diagram is wrong and will mislead you at exactly the moment you need it.

### XNOR — the part that reports agreement

**The experience.** You and your partner both do not want to go to the wedding. Neither of you has said so. When one of you finally does, the relief is instantaneous, because the flags agreed.

**The same thing, in all four registers.**

- `|A` **Mental** — agreement — both think it, or neither does
- `|f` **Emotional** — mutual indifference mistaken for peace
- `|E` **Physical** — two bodies relaxing at the same moment
- `|T` **Spiritual** — shared conviction


**What is happening.** Equality between two flags is being reported. Note what that includes: **both-inactive counts as agreement.** Two people who both do not care are in agreement, and a detector that reported only both-active agreement would miss the more common case.

**The part that matches.** XNOR is true when its inputs are equal.

**Where it breaks.** Because both-inactive reads as agreement, XNOR alone cannot tell you whether anything is happening. Add an activity qualifier when you need to separate "we agree to do this" from "neither of us cares."

### MUX — the part that chooses which response reaches the output

**The experience.** You have a version of yourself for your mother, a version for your team, and a version for your oldest friend. You do not decide which one to be. Who you are with selects it, and it is selected before you have finished saying hello.

**The same thing, in all four registers.**

- `|A` **Mental** — which argument you reach for depending on who is asking
- `|f` **Emotional** — the version of your warmth that appears for family
- `|E` **Physical** — accent, posture and volume changing with the room
- `|T` **Spiritual** — which self you present in a place of worship and a place of work


**What is happening.** Several prepared responses are available and a **named control signal** chooses which one reaches the output. The control is not hidden: it is whoever is in the room, and naming it is what makes the choice visible and therefore changeable.

**The part that matches.** A multiplexer routes one of several inputs to one output, chosen by a select line. The role-match is exact, and it predicts the failure: if the select line is stuck, only one response will ever appear.

**Where it breaks.** A MUX has a defined behaviour for every select value, including a safe default. Human switching does not — under stress, the select line can float and you get whichever version was most recently used, which is rarely the one you would have chosen.

### DEMUX — the part that sends one thing to one place

**The experience.** You have one real insight about how you avoid conflict — and the question is whether it reaches your marriage, your work, or your relationship with your father. It is one insight. It has to be routed.

**The same thing, in all four registers.**

- `|A` **Mental** — one insight routed to one problem
- `|f` **Emotional** — one feeling allowed into one relationship
- `|E` **Physical** — one habit applied in one setting
- `|T` **Spiritual** — a conviction expressed in one domain of life


**What is happening.** One input is being dispatched to one of several output paths under a stated control. The routing decision is a decision, and it is usually made implicitly and badly.

**The part that matches.** A DEMUX sends one input to one selected output. The role-match is exact, and the discipline it teaches is that only the selected output receives the signal — you cannot half-send an insight to two places and expect it to land in either.

**Where it breaks.** Real life frequently needs the same insight in three places at once, and a DEMUX cannot do that. If you need fan-out, say so and use a different structure — do not pretend the routing was a choice when it was actually a shortage.

### Relay — the part where a small signal switches something enormous

**The experience.** You say one sentence — *"I'm going to hand in my notice"* — and a career, a mortgage, and a set of friendships change state. The sentence was small. What it switched was not. And the two are deliberately kept apart: saying the sentence does not by itself touch the money.

**The same thing, in all four registers.**

- `|A` **Mental** — one sentence that changes a career
- `|f` **Emotional** — “I'm leaving” — and everything changes
- `|E` **Physical** — a small movement with a large consequence
- `|T` **Spiritual** — a vow that reorganises a life


**What is happening.** A low-level `^8` Cause control is gating a separate, high-stakes `^9` Effect path, and the two are **isolated** from each other. That isolation is the whole point. It means the small decision can be made in a calm moment without the large consequence reaching back and interfering with the deciding.

**The part that matches.** A relay uses a small coil current to switch a much larger, electrically separate circuit. The role-match is exact: `Relay< control=^8^E_{F5}|A, switches=^9^O_{F5}|E >`.

**Where it breaks — the direction is not reversible.** Cause controls Effect, never the reverse. If your diagram shows the large path reaching back and moving the control signal, it is not a relay; it is a feedback loop, and it should be drawn as one. Getting this wrong is how people end up believing that circumstances decide for them.

### Schmitt trigger — the part that commits and then holds

**The experience.** You have decided to end the relationship. You decided it on Tuesday and you were certain. On Wednesday you were certain of the opposite. On Thursday you were certain again, and by Friday you had re-decided eleven times and told nobody, because the decision would not hold still for long enough to act on.

**The same thing, in all four registers.**

- `|A` **Mental** — deciding once instead of hourly
- `|f` **Emotional** — holding a decision through a bad night
- `|E` **Physical** — steady hands because the decision is settled
- `|T` **Spiritual** — a commitment that does not wobble with mood


**What is happening.** You are sitting exactly on a threshold with a little noise on top of it, and the output is following the noise. The fix is not more certainty. The fix is a **dead-band**: a higher level at which the decision turns on and a lower level at which it turns off, with everything in between holding the previous answer. Deciding once, deliberately, with a gap wide enough to absorb a bad night, is a different act from deciding continuously.

**The part that matches.** A Schmitt trigger switches on at one threshold and off at a lower one, and the gap — the hysteresis — stops the output chattering when the input sits near the boundary. The role-match is exact, and it is one of the most directly useful mappings in the library.

**Where it breaks.** Hysteresis is a commitment, and commitments can be wrong. A very wide dead-band stops you chattering and also stops you noticing that the situation has genuinely changed. Name both thresholds, and name what evidence would move the lower one.

