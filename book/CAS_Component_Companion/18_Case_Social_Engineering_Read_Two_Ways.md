# Social Engineering, Read Two Ways

*Chapter 18. Case study 9 of 9 — a coercive circuit, drawn and written.*

Everything in this book so far has described a person. This chapter describes somebody working *on* a person, deliberately, using the same components — and it is here because the library is neutral. A bias terminal does not care who is turning it. The same structure that explains how a teacher steadies a frightened student explains how a fraudster empties an account, and the reason to be able to read it is not curiosity.

There is no new machinery in this chapter. Every part in it has already appeared. What is new is the *aim*.

## The situation

A man in his seventies gets a phone call. The caller knows his name, his bank, and the name of a fund he holds. The caller is calm, slightly apologetic, and in a hurry on his behalf: *there has been a flag on the account, we need to move the money to a holding account for forty-eight hours, I am sorry, I know how this sounds, I will stay on the line with you.*

He is on the phone for three hours. He does not tell his daughter. He does not go to the branch. He does not do any of the four things he would have said, that morning, that he would obviously do.

Nothing was hacked. He was not stupid, and he is not confused. A circuit was built around him and driven.

## The circuit, drawn

**An `^8` trigger into a `^5` substrate.** The authority, the correct details, the apologetic urgency — all `^8` Above/Cause. What it lands as is supplied by `^5`: sixty years of being taught that officials are to be cooperated with, that being difficult is shameful, and that a man who cannot handle his own affairs has lost something. The caller did not create that substrate. The caller *aimed at* it.

**A relay.** A small control signal — one sentence at a time — switching an enormous, isolated path: an entire life's savings. The isolation is the point. The man's ordinary judgement, which is intact, is on the other side of the coil. It never gets to touch the switch.

**A current mirror.** The caller copies his own calm onto the call. Tone is contagious, and a professional fraudster is a professional at remaining unhurried while a person's alarm is rising. The man is being *supplied* with a steady bias by somebody else, and the steady bias is what keeps his own alarm from becoming an action.

**An RC low-pass on the return path.** The three hours are not an accident. Every delay makes the next delay easier, because the man is now invested in the story he has been telling himself for two hours. The feedback that would have reached him in the first ten minutes — *why am I doing this* — has been smoothed out of the loop.

**A regulator with the setpoint moved.** He is not panicking. He is *calm*, and the calm is the operation. What has been moved is the reference: an hour ago his zero was *nothing about this is real*; now it is *something has gone wrong and I am handling it*. Everything he does from that point is measured against the new zero, and measured against it, he is behaving sensibly.

**A fuse that cannot fire.** Here is the part that matters most, and it is the reachability rule from Chapter 9. The man has a rule: *I do not move money on the phone.* For that rule to fire, the situation has to be *recognisable* as a phone-money situation. The whole construction of the call is designed so that it is classified as an *account-security emergency* instead — and a rule attached to one classification cannot fire inside another. **A boundary whose trigger condition has been renamed is a boundary that will never trip.** This is not a failure of willpower. It is a fuse with the wrong label on it.

## The same three hours, in all four registers

- `|A` **Mental** — *"He knows the fund name. He has a reference number. He is being helpful."* Every individual inference is sound and every premise was supplied. Manipulation rarely requires you to believe something false; it requires you to reason correctly from what you have been handed.
- `|f` **Emotional** — *"I felt reassured, and slightly ashamed that I had doubted him."* The shame is doing work: it discourages him from asking his daughter, because asking would mean admitting he had been rattled.
- `|E` **Physical** — *"I was standing up. I don't remember standing up."* Three hours without sitting down, without eating, without a glass of water. A body kept slightly off-balance makes fewer good decisions, and the caller kept him off-balance on purpose.
- `|T` **Spiritual** — *"I did not want to be the man who could not manage his own affairs."* This is the lever, and it is the one he never names. The whole call is aimed at his sense of what kind of man he is. Attacks of this sort are almost never aimed at your reasoning. They are aimed at what you are unwilling to be.

## The circuit, written

```
^8^C_{F5}|A    (an authority claim, cognitive domain, Agency, analytical intake)
   +  ^5^P_{F7}|T   (sixty years of composition: deference, Purpose, transcendent)
   -> ^9^E_{F3}|f   (an arrival: evaluative, Vitality, affective — the alarm, mis-scored)
```

Read the substrate line. The defence is not in the trigger. It is in `^5` — and `^5` is exactly the thing that cannot be changed quickly. What *can* change quickly is the **classification**, and that is where the notation earns its keep: it forces the words *"an authority claim"* onto the page. Written plainly, the sentence is *"an authority claim landed on sixty years of deference."* Drawn as one transistor, it is a stranger turning a bias terminal that was installed long before he arrived.

**Now the enforcement, in the other direction.** The notation can state the expression. It cannot state the *ordering* — and the ordering is the whole defence. The drawing says it at once: the alarm is generated and *then* routed past the decision stage. Put a probe between them and the operation fails. That is a topological fact, and topology is what schematics are for.

Neither language catches this alone. The expression names the substrate the attack is using; the drawing names the wire the defence has to be inserted into. **You need both, and this is the clearest case in the book of why.**

## What actually works, in circuit terms

Not "be more careful", which is an instruction to try harder with the same circuit.

**Name the classification out loud, at the start.** The single most effective defence is a rule attached to a *perception* rather than a *situation*: not *"I do not move money on the phone"* but *"if anyone asks me to move money, for any reason, I hang up and call the number on my card."* That rule is triggered by the request itself, so it cannot be renamed out from under you. **Attach the fuse to what you can see, not to what you have been told it is.**

**Put a person in the loop.** Isolation is a component of the attack, not a side effect. Anybody who needs you alone and hurried needs those two things for a reason; a single call to a daughter in the middle of the three hours ends it, because the register changes the moment the story has to be told to a second person.

**Break the smoothing.** The three hours work because delay compounds commitment. A short circuit — *I will call you back* — is a hard break in the feedback path, and it costs nothing if the caller is genuine.

**Answer the `|T` lever directly.** *"I did not want to be the man who could not manage his own affairs"* is a real fear and it can be met honestly: needing help with a fraud is not the same as being unable to manage. The lever only works while it is unnamed.

## Where the analogy stops

The circuit describes the *mechanism* of the manipulation. It says nothing about the caller, who is a person with reasons, and nothing about the man, whose sixty years are not a defect to be corrected. And there is a boundary worth stating plainly: this chapter describes a structure so it can be recognised. It is not a script, and the parts it names are exactly the parts a competent fraudster already knows.

## What to take from it

- The library is neutral. The same components describe a teacher and a thief, and recognising the shape is the whole defence.
- Attacks are aimed at what you are unwilling to be, not at what you believe.
- A boundary whose trigger has been renamed will never fire. Attach it to what you can see.
- Isolation and hurry are load-bearing parts of the attack, not incidental. Remove either and it weakens.
- The notation names the substrate; the drawing names the wire to cut. Neither alone is enough.
