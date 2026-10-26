# Active and Comparative Parts

*Plate S3.*

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

  \pic at (-42,0) {cascjt};
  \node[cassymname,anchor=west] at (-31,2) {Q1  CJT};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-2.5) {Controlled trigger-to-arrival stage};
  \node[cassymrole,anchor=west,text width=47mm] at (2,2.5) {Electrical: a control governs a larger path.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-1.5) {Cognitive: bias shapes trigger into arrival.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-4.8) {ENG};

  \pic at (-42,-18) {casopamp};
  \node[cassymname,anchor=west] at (-31,-16) {U1  Op-amp};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-20.5) {Differential gain with feedback};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-15.5) {Electrical: amplifies one input minus another.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-19.5) {Cognitive: compares commensurable activations.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-22.8) {ENG};

  \pic at (-42,-36) {casdiffpair};
  \node[cassymname,anchor=west] at (-31,-34) {Q2/Q3  Differential pair};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-38.5) {Matched comparison stage};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-33.5) {Electrical: rejects what both inputs share.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-37.5) {Cognitive: preserves only the difference.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-40.8) {ENG};

  \pic at (-42,-54) {casmirror};
  \node[cassymname,anchor=west] at (-31,-52) {Q4/Q5  Current mirror};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-56.5) {Replicated bias};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-51.5) {Electrical: copies one branch current.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-55.5) {Cognitive: gives both paths one bias.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-58.8) {ENG};

  \pic at (-42,-72) {casactiveload};
  \node[cassymname,anchor=west] at (-31,-70) {Q6  Active load};
  \node[cassymrole,anchor=west,text width=29mm] at (-31,-74.5) {Difference-to-output conversion};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-69.5) {Electrical: turns branch difference into signal.};
  \node[cassymrole,anchor=west,text width=47mm] at (2,-73.5) {Cognitive: lands decomposition as output.};
  \node[font=\sffamily\tiny\bfseries,anchor=west] at (45,-76.8) {ENG};
\end{tikzpicture}
\caption{Active and comparative parts. Cause, Bias, and Effect are cognitive terminal roles on the CJT; they are not claims that a standard BJT's collector, base, and emitter have those signal roles in every configuration.}\label{fig:sym-s3-active-comparative}
\end{figure}
```

### CJT — the part where what arrived depends on what you are made of

**The experience.** Two people hear the identical sentence — *"we should probably talk about your mother"* — in the same kitchen, at the same volume. One of them feels a small administrative irritation: *fine, let's get it over with.* The other's stomach drops and they are nine years old again. Same input. Different output. Nothing is wrong with either of them.

**The same thing, in all four registers.**

- `|A` **Mental** — one sentence, two people, two entirely different conclusions
- `|f` **Emotional** — the same remark landing as mild irritation in one and a wound in the other
- `|E` **Physical** — the stomach dropping before any thought has formed
- `|T` **Spiritual** — a sentence that lands as calling, because of the life it meets


**What is happening.** This is the central component of the whole system, and it is worth slowing down for. An `^8` Above/Cause — an Idea that triggers a *different* Idea than itself to come to Mind — meets a `^5` Female substrate, the accumulated composition that the Mind is made of, and what lands is an `^9` Below/Effect. The trigger does not contain the response. The substrate supplies it. That is why the same sentence produces grief in one person and logistics in another, and why telling someone to "be reasonable" about it does not work: you are asking them to change their substrate by an act of will, in the middle of the moment it is doing its job.

**The part that matches.** A transistor is the same device everywhere it appears, and its behaviour is set by its bias. Change the bias and the identical input produces an entirely different output — cutoff, or amplification, or saturation. The role correspondence is exact: Cause enters, Bias shapes, Effect lands.

**Where it breaks, and this is the anti-drift rule for the whole book.** `^8` Above/Cause is **associative triggering**, not reasoning. Its colloquialisms are "that reminds me," "one thing leads to another," "it triggered a memory." If you find yourself describing someone as *analysing* the situation, or *reasoning* their way to a conclusion, you are no longer describing `^8` — you are describing a compound of `^6` Male (decomposition) and `^9` (the landing). Getting this wrong is the single most common error in this framework, and it produces advice that sounds sophisticated and helps nobody.

### Op-amp — the part that amplifies a difference between two things

**The experience.** Your partner says "nothing's wrong" in a voice that is a quarter-tone flatter than usual. By the time you have finished washing up, you have constructed an entire theory of the last three weeks from that quarter-tone. You were not wrong that something was different. You were wrong about how much.

**The same thing, in all four registers.**

- `|A` **Mental** — building a three-week theory out of one flat tone of voice
- `|f` **Emotional** — one cool goodbye, and a certainty that you are not loved
- `|E` **Physical** — hearing a quarter-tone in a voice before you know you heard it
- `|T` **Spiritual** — reading a small event as a verdict on your whole direction — usually a gain error


**What is happening.** A small difference between two quantities was amplified enormously because there was no feedback path holding the gain down. In CAS terms, a tiny difference in `|E` — a voice, a posture — was taken up and run through `|A` until it became a certainty. The input was real. The magnitude was manufactured.

**The part that matches.** An op-amp takes the difference between two inputs and multiplies it by an open-loop gain so large that the output is meaningless without feedback. The minus input is exactly that: **arithmetic subtraction of two commensurable quantities.** And the discipline this predicts is real — you must close the loop with feedback (ask the person directly) or the output will be driven to a rail by noise.

**Where it breaks — an important precision.** An op-amp's inverting input is arithmetic subtraction. It is **not** a Noetic involution. Involution is defined only for `^2↔^3`, `^5↔^6`, and `^8↔^9`; the self-duals `^0`, `^1`, `^4` and `^7` remain themselves. Writing "the op-amp inverts the state" and meaning "turns Positive into Negative" is a category error. Inverting an *arithmetic* difference around a reference is ordinary engineering and has nothing to do with the involution structure.

### Differential pair — the part that ignores what both sides share

**The experience.** You and a colleague are made redundant on the same morning, from the same meeting, with the same words. Eighteen months later you are both working again and both broadly all right. But you notice something: your colleague was angry for a fortnight and then fine, and you were calm for a fortnight and then fell apart in the third. Same event. The difference between you is the part that was actually about you.

**The same thing, in all four registers.**

- `|A` **Mental** — two people given identical news, reaching different conclusions; the difference is them
- `|f` **Emotional** — the same bereavement, two different depths of grief
- `|E` **Physical** — the same cold room, and only one of you shivers
- `|T` **Spiritual** — the same loss, and one person's faith holds while another's does not


**What is happening.** The shared circumstance is **common-mode**, and a well-built comparison cancels it. What remains is the difference — the part that is not explained by the event, and therefore has to be explained by the person. This is uncomfortable precisely because it is informative: it removes the excuse and leaves the signal.

**The part that matches.** A differential pair with good common-mode rejection amplifies only the difference between its two inputs. Matched devices and a shared bias are what make the rejection work. Unmatched inputs — two things that are not actually comparable — produce garbage, which is the technical statement of "you can't compare those two situations."

**Where it breaks.** A differential pair needs **matched** devices. Comparing your reaction to a redundancy with your reaction to a bereavement is an unmatched comparison, and it will output noise that you will then mistake for insight. State the axis before you compare anything.

### Current mirror — the part that copies one condition onto another branch

**The experience.** You are forty-five and you catch yourself doing the exact thing your father did when a bill arrived: not opening it, moving it to the side of the desk, feeling vaguely sick. You have never once decided to do this. And you are doing it to a piece of paper in your own house, thirty years after leaving his.

**The same thing, in all four registers.**

- `|A` **Mental** — an inherited way of reasoning you never chose and never noticed
- `|f` **Emotional** — your mother's dread arriving in your chest at an airport
- `|E` **Physical** — a gesture, a posture, a way of holding a cup
- `|T` **Spiritual** — an inherited faith, or an inherited cynicism


**What is happening.** A control condition was **copied**, not chosen. This is one of the most useful things the library can describe, because it explains behaviour that has no decision behind it and therefore cannot be fixed by deciding differently. The bias was replicated onto your branch; the branch itself is your own.

**The part that matches.** A current mirror replicates the current in one branch into another by tying the two control terminals together. The second branch did not compute anything; it received the same bias. The role-match is clean and — importantly — it comes with the fix: you can change the copied current only by changing the **reference** branch, which in human terms means working on the pattern where it lives, not on your own symptoms.

**Where it breaks.** A mirror copies continuously and exactly. Human transmission is partial, shaped by temperament, and interrupted by everything that happened to you that did not happen to them. You are not a copy of your father with a wire attached. You are a branch that shares one control node with him, and the rest of the circuit is yours.

### Active load — the part that turns a difference into an actual decision

**The experience.** You have felt vaguely off at this party for an hour. Nothing is wrong, exactly. Then someone makes a small remark, and you think: *I'm leaving.* The feeling was there the whole time. What changed was that it became an output.

**The same thing, in all four registers.**

- `|A` **Mental** — the moment a vague suspicion becomes a decision
- `|f` **Emotional** — unease turning into resolve
- `|E` **Physical** — standing up and reaching for your coat
- `|T` **Spiritual** — a long-felt sense that something is wrong becoming a commitment to change a life


**What is happening.** A branch difference that was sitting as a difference has been converted into a single-ended output with enough drive to do something. This is the stage that turns a sensed difference into an action, and it is a **composite** — a combination of parts doing a job — not a new primitive. In register terms, `|E` produced the difference and the conversion is what allowed `|O` — operational, the domain of action — to take it up.

**The part that matches.** An active load replaces a passive resistor with an active device, which raises gain and allows a differential stage to produce a usable single-ended output. The role-match is that this is a conversion stage: difference in, drive out.

**Where it breaks.** Do not reify it. An active load is not a faculty, a module, or a homunculus that decides things. It is two transistors arranged so that a difference arrives somewhere it can be used. The moment you give it agency you have invented a little person inside the person, which is exactly the move this library exists to prevent.

