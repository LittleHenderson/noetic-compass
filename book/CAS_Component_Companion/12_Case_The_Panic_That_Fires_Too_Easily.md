# The Panic That Fires Too Easily

*Chapter 11. Case study 3 of 8 — the Schmitt trigger, the threshold, and the missing dead-band.*

Priya is thirty-four. She has panic attacks, and the thing that frightens her most is not the attacks. It is that she never knows whether the next fast heartbeat is a panic attack or a staircase. She has started avoiding stairs.

Her doctor has ruled out the heart. What is left is a circuit sitting exactly on its own threshold, with noise on top of it.

## The circuit

**The Schmitt trigger** is the whole story, and this is one of the most directly useful mappings in the library. A comparator with a single threshold, sitting with its input near that threshold, will chatter: the output flips on every scrap of noise. The fix is not a better threshold or more willpower. The fix is **hysteresis** — one level at which the alarm turns on, a *lower* one at which it turns off, and a gap in between where the previous answer holds.

Priya's alarm has one threshold, set low, and no gap. So a flight of stairs can turn it on, and a rest at the top does not turn it off, because turning off requires dropping below a level that the aftermath — the adrenaline, the fear of the fear — keeps her above for twenty minutes.

**The positive feedback** is what turns an alarm into an attack. Fast heartbeat is read as danger; danger produces adrenaline; adrenaline produces a fast heartbeat. The output has become the input. This is the same oscillator structure as Chapter 10, and it is why the attack has a life of its own once it starts.

**The reference** explains part of why the threshold is where it is. Priya grew up in a house where a fast heartbeat meant something was about to happen. Her body's calibration for *a normal level of arousal* is low, because a low level was never safe.

**The rail** is the part that gets forgotten. Attacks cost enormous amounts of supply, and a person running three a week for a year is running a board with a chronically low F3 rail — which lowers every threshold on the board and produces more attacks. The loop is not only inside the attack.

## The same moment, in all four registers

- `|A` **Mental** — *"This is the fourth time today. My heart rate is up, I have not eaten since eight, and I have a meeting at two."* She can name every variable accurately. Accurate naming does not stop it, and telling her to be rational about it is telling her to use an instrument that was never broken.
- `|f` **Emotional** — *"I am frightened of being frightened."* The second-order fear is the fuel, and it is why the state rises after the first adrenaline arrives rather than settling.
- `|E` **Physical** — *"My chest is tight, my hands are cold, and I have stopped breathing out properly."* This is the register that starts the loop and the only one that can be interrupted fast, because the body is the part that responds in seconds.
- `|T` **Spiritual** — *"What is the point of a life I cannot walk up a flight of stairs in?"* This is not melodrama and it is not depression; it is the accurate report of a person whose horizon has narrowed until it contains nothing she is living *toward* — which is itself a maintenance condition, because a `|T` rail with nothing on it gives the threat system nothing to weigh against.

## What actually helps, in circuit terms

**Widen the dead-band.** The single most useful move. Decide in advance, in a calm hour, on two numbers: the level at which you will treat a fast heartbeat as an alarm, and a clearly lower level at which you will stand down. Then hold the previous answer in between. Written down, the gap does real work — it is the difference between deciding once and deciding sixty times an hour.

**Break the feedback path.** The loop runs through the interpretation. Slowing the out-breath for ninety seconds does not talk the state down; it removes the input the state is using to sustain itself. Breathe out longer than in, and the loop loses gain.

**Raise the rail.** Sleep, food at regular hours, movement, and human contact. Unglamorous, upstream of everything, and the most reliable lever there is.

**Give `|T` something to weigh.** Not a slogan. Something she is actually living toward, specific enough to be measured in a week. A threat system with nothing on the other side of the scales will win every argument it is in.

## Where the analogy stops

A Schmitt trigger has fixed thresholds and no history. Priya's thresholds move with sleep, with blood sugar, and with the memory of the last attack — and, importantly, they can be moved deliberately over months, which no comparator can do for itself. Read the component as the **shape** of the problem and the **reason** a dead-band helps. Its numbers are not her numbers.

As with every case in this part: this is a description of a pattern, not a diagnosis and not a treatment. Panic, in particular, is worth taking to somebody qualified.

## What to take from it

- A single threshold with no gap will chatter. The fix is a dead-band, not more certainty.
- The second-order fear is the fuel; treating it as the patient rather than the symptom is where the leverage is.
- The body is the only register that can be interrupted in seconds, which makes it the right first move.
- A life with nothing on the `|T` rail has nothing to weigh against a threat. That is a design fault, not a mood.
