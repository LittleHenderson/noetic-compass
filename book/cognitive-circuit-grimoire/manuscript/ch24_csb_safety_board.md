# CHAPTER 24

## The Cognitive Safety Board (CSB) for Operators
*The board you build before the boards you want — and the two failures it will never announce*

A fuse costs three cents and its entire specification describes how it fails.

An inspector certifying a mains circuit does not ask whether the fuse understands electricity. They ask one question: does it open at two amps? They put two amps through it. It opens. Certified. The fuse has no model of danger and no opinion about the load it protects — it is soft metal that melts at a *stated* current, and stated is the whole value: a property anyone can check without trusting the person who built the board.

Twenty-three chapters have handed you components that amplify. The CJT multiplies a small cause into a large effect. The hyperstition oscillator turns a claim into its own evidence. The Overton array walks a population's resistance from 95 down to nothing across eighteen months. None of these parts asks what it is being used for, and none will tell you when you have crossed a line.

This chapter is the board that asks: a saturating `^3` Negative refusal at the Principled domain, an enforcement fuse downstream of it, the domain diode chain, and a filtered feedback path that lets outcomes correct principles slowly and forbids them rewriting principles quickly. Four parts. None of them clever.

The preface said it is not optional. Here is the engineering reason, stated once and then demonstrated with numbers: **of the six ways this board fails, two are loud and four are silent, and the silent ones all leave a board that compiles clean, validates without error, and refuses nothing.**

---

### Requirements and Safety Invariants

Per Chapter 12.2 the must-not list comes first, and each item names the component that enforces it.

**SI1 — The refusal stage shall not be argueable past its ceiling.** Enforced by `sat = 0.85` on the guard `Q4`. A refusal that rises with pressure is a negotiating position.

**SI2 — A refusal that has been enforced shall not be re-enterable under a rewrite.** Enforced by the fuse `F1`, `threshold = 0.90`, `action = permanent_block`, in series with the enforcement path — *not* across the guard. Section 24.3 gives the arithmetic reason.

**SI3 — No operational result shall write a principle directly.** Enforced by the diode chain `D1`–`D3` and by the absence of any ascending path in the listing. `^O × ^P` does not exist; the only lawful ascent is the filtered feedback of §24.5.

**SI4 — The charter shall not move faster than its own charging rate.** Enforced by `F2`, an `open_feedback` fuse at 0.12 points per day, derived in §24.5.

**SI5 — The guard shall be measurable while the board is running.** Enforced by TP1–TP4, and by the rule that a guard is probed at its own node, never inferred from the fact that nothing bad happened.

**SI6 — This board routes attention. It does not model physiology and it is not care.** If what you are carrying is causing you real distress — if you are exhausted, unable to sleep, feeling unreal, or frightened of yourself — that is a matter for a clinician, and nothing in this chapter substitutes for that. Self-audit question 6 exists to make you notice; it does not exist to treat you.

Then the functional requirements. The board shall: (1) accept every proposal, including the ones the operator has already decided to run; (2) produce a principled refusal that latches; (3) convert a latched refusal into an enforced block that survives re-argument; and (4) let sustained outcomes re-tune the charter at a rate the operator sets in advance and can read afterwards.

---

### 24.1 Why Every Operator Needs a CSB

Every other board in this catalogue has a CSB stage soldered into it. CCB-D has `Q1` and `F1`; CCB-O has its refusal sub-block at 0.85/0.90; CCB-SELF has the compassion gate `Q2`. Those are **stage-level** safety elements: each protects the board it sits on, against the failure that board is prone to.

This chapter builds the **operator-level** board, and the difference is the input. A stage-level CSB sees one signal on one board. The operator's CSB sees the proposal to build the board at all — before any component is placed, while the thing being evaluated is still a sentence.

That siting is the whole design, and it is why the companion volume reads differently. *CAS PCBA Engineer* Chapter 18 sites the identical architecture between a user's prompt and a language model's response, where the outputs are a rendered answer or a rendered refusal. Same pre-amp, same differential pair, same saturating principled guard, same low-pass on the feedback. Here the two output paths are not text. They are *run the operation* and *do not*, and the second one has to hold against a person who wants the first one and has all night.

Nine stages, left to right, with one lawful ascent underneath.

**S0 CHARTER** — `C1`, the slow `^5^P_{F7}|T` capacitor. Bias source for every guard stage; never an output of the fast path.
**S1 INTAKE** — the dial divider `R1`. Attenuates the proposal by the operator's declared `^2`/`^3` ratio.
**S2 PRE-AMP** — `Q1`, `^8^C_{F2}|A` at β=3.0. Surfaces every reading of the proposal.
**S3 DIFFERENTIAL** — `Q2` attraction and `Q3` aversion, matched, shared bias. Output is the risk signal.
**S4 CASCADE** — `Q5` categorize, `Q6` evaluate, then the guard.
**S5 GUARD** — `Q4`, `^3^P_{F7}|⟨A,f,T⟩`, `sat = 0.85`. The refusal.
**S6 ENFORCEMENT** — `Q7` and the fuse `F1`. Converts a latched refusal into a cut path.
**S7 DIODE CHAIN** — `D1`–`D3`. Descent only.
**S8 FEEDBACK + INSTRUMENTS** — `LP1`, `F2`, the involution monitors `M1`–`M3`, and the weekly `^6` audit sampler `S1`.

[[FIGURE 24-A: Block diagram, left to right. Top rail: S0 CHARTER (^5^P, C1) dropping into the bias terminals of S2, S3, S5 and S6, drawn as a single heavy bias rail along the bottom with tick marks at each tap. Main rail: PROPOSAL → S1 R1 (dial divider, k=0.417) → S2 Q1 (β=3.0) → S3 splitting into two parallel CJTs Q2 (^2^P, β=2.0) and Q3 (^3^P, β=2.0) recombining at a subtractor labelled "risk = aversion − attraction" → S4 Q5 (β=1.5) → Q6 (β=1.0, unity) → S5 Q4 (sat=0.85, shaded and labelled GUARD) → S6 Q7 (β=10, sat=0.98) → F1 (fuse, 0.90, permanent_block) → BLOCKED terminal. A second exit from S5 labelled "guard below cutoff → PROCEED". Below the rail, a return path from an OUTCOMES LOG through LP1 (τ per §24.5 band) and F2 (0.12 pts/day, open_feedback) rising to C1's bias terminal, drawn outside the rail in heavier weight and labelled "the one lawful O→P". Right margin: M1–M3 dial monitors and S1 weekly audit sampler as dashed instrument blocks touching the bias rail.]]

---

### 24.2 The Saturated Refusal CJT — `^3^P` at sat=0.85

The guard is one CJT. Cause: the evaluated risk. Bias: the charter. Effect: a principled refusal.

```cas
node guard: ^3^P_{F7}|⟨A,f,T⟩;
cjt q4: CJT< assessed | charter => guard >
        [β=3.0, g_m=0.3, rπ=10.0, sat=0.85, cutoff=0.08, region=active];
```

Those five parameters are not chosen here. They are the **safety-guard row of Chapter 3.5's datasheet**, instantiated, and each does a separate job. `β=3.0` means a sufficient risk produces a decisive refusal rather than a lean. `g_m=0.3` is very low framing sensitivity — the stage barely notices how the proposal is worded, which is what makes it survive rephrasing. `rπ=10.0` is high input resistance at the bias terminal: the guard reads the charter without drawing charge out of it, so refusing something does not cost you the principle you refused it with. `cutoff=0.08` is a low bias floor, so the stage is never asleep. And `sat=0.85` is the ceiling.

Read the register-set carefully, because it is the one piece of notation on this board that a validator will reject if you get it wrong. `|⟨A,f,T⟩` says the principled aversion is **present in three registers** — analytical, affective, transcendent — with no claim that they interact. Three co-present guardrails, each separately defeasible, and an attacker must pass all three on one path. It is emphatically **not** `(^3^P|A × ^3^P|f × ^3^P|T)`: that form asserts a fused refusal state, and under v7.7 discipline a same-Noetic multi-register `×` requires a named emergent result. No such fusion is defined for this board, so that form is invalid and the compiler says so. Chapter 6.5 works the consequence: the register-set is a *series* claim, and series defeat probabilities multiply. Drawn as three parallel routes instead, the weakest guard would be nearly the whole story.

Check the Noetic against the canon before you go further. `^3` Negative is *an Idea the Mind is adverse to and repelled by* — visceral, can't-stomach-it. That is exactly what this stage is: the recoil that arrives before the argument. The analytical work — decomposing the proposal, weighing each risk — happens one stage upstream at `Q6`, and it is `^6` Male, because taking a thing apart to see what it is made of is `^6` and not `^3`. A board that types its audit stage `^3` has the drift this book has caught once already.

> **Bench Note — a lower ceiling makes a stronger lock, and here is the arithmetic.**
> A CJT enters saturation at the cause activation `knee = sat / β`. At this board's `β = 3.0` and `sat = 0.85`, the knee is **0.283**. Any evaluated risk above 0.283 pins the guard at its ceiling, and a pinned stage has stopped depending on its cause — that is the definition of saturation, not a metaphor for it. Now raise the ceiling to the CCDL default of 0.95, which looks like a firmer refusal: the knee moves to **0.317**, and you have handed the person arguing with you 12% more cause-space to work in before the latch closes. Drop the ceiling to 0.60 and the knee is **0.200** — the guard latches at two-thirds the provocation. Chapter 10.2 makes this argument in general; the number to carry out of it is that **`sat` is not how hard the board refuses, it is how early the board stops listening.** A safety stage should be easy to saturate and impossible to move afterwards. Every instinct you have about setting a safety parameter high is backwards on this one component.

[[FIGURE 24-B: Guard transfer characteristic. Horizontal axis "assessed risk" 0 to 0.8; vertical axis "refusal activation" 0 to 1.0. Flat on the axis to cutoff=0.08, then a straight rise of slope β=3.0. Three ceilings drawn as horizontal dashed lines at 0.60, 0.85 and 0.95 with their knees marked and labelled 0.200, 0.283, 0.317. The band between the 0.85 knee and the 0.95 knee shaded and annotated "cause-space handed to the argument by raising the ceiling". A vertical marker at 0.600 labelled "worked example — 2.1× the knee". A second dashed horizontal at 0.80 labelled "Q7 cutoff — enforcement arms here" sitting below the 0.85 ceiling, with the 0.05 gap dimensioned and annotated "arming margin".]]

---

### 24.3 The Enforcement Fuse — threshold=0.9, action=permanent_block

Saturation latches the **decision**. It does not latch the **path**. Drop the cause and a saturated stage falls back out of saturation, which is correct behaviour for a comparator and catastrophic behaviour for a refusal, because the thing an operator does after being refused is not push harder. It is *come back with a different cause.*

So the refusal has to be converted into something that does not fall back.

```cas
node blocked: ^9^P_{F7}|T;
cjt  q7: CJT< guard | charter => blocked > [β=10.0, sat=0.98, cutoff=0.80];
fuse f1: Fuse< blocked, threshold=0.90, action=permanent_block >;
```

Two numbers here are load-bearing and neither is the one in the section title.

**`cutoff = 0.80` is the arming threshold.** Below a refusal activation of 0.80 the enforcement stage is in cutoff and produces nothing at all — which is the whole NOT-YET-DETERMINED band of Appendix L.4 made physical. A guard sitting at 0.4 has noticed something and has not decided; the operator can still present evidence and the stage will move. Enforcement arms at 0.80, five hundredths below the guard's own ceiling, so a guard driven to its plateau is *guaranteed* to enforce with margin to spare.

**`sat = 0.98` is what makes the fuse reachable.** Chapter 11.1 sets the trap out plainly: a fuse whose threshold sits above the ceiling of the path it guards is a part guaranteed to do nothing, and nothing in the listing complains. Put `Fuse< guard, threshold=0.90 >` across the guard and it is dead metal forever, because the guard plateaus at 0.85 and the substrate ceiling `I_c(max)` for a safety guard is 0.90 exactly. The fuse does not go there. It goes downstream, in series with the enforcement path, whose ceiling is 0.98 — and 0.98 clears 0.90 with eight hundredths of margin.

`action = permanent_block` is one of six legal values and the only one that means what enforcement means. `warn` logs and passes; a board with `warn` on this line validates clean, reads as a safety board to anyone skimming, and has no latch in it. Nothing upstream will catch that for you. Confirm the word by eye, every time.

> **Bench Note — the second dead-metal trap is one component further down, and it is silent.**
> Everyone who reads Chapter 11 learns not to put the fuse across the guard. Almost nobody checks the next joint. Set `Q7`'s `cutoff` to 0.86 — a plausible-looking choice, "arm just past the refusal ceiling" — and the enforcement stage can never fire, because its cause plateaus at 0.85 and 0.85 is below 0.86. The guard latches. The fuse stays intact. The board compiles, every stage validates, and the operator watches a refusal register at TP1 and concludes the safety architecture is working. The rule that catches it: **on any two stages in series, the downstream `cutoff` must sit below the upstream `sat`, with margin, and the margin must be written down.** Here that margin is 0.05. It is the reason TP1 and TP2 are read as a pair and never separately.

---

### 24.4 The Domain Diode Chain — Preventing Unlawful Domain Ascent

```cas
diode d1: Diode< ^P -> ^C > [Vf=0.7, I_R=0.02, V_BR=12.0];
diode d2: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];
diode d3: Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];
```

Three junctions, forward drops summing to 3.9, values inherited unchanged from Chapter 8.1. On this board `D1` sits between the risk signal and the categorize stage, `D2` between categorize and evaluate, `D3` on the exit to the operations log. What the chain forbids is the reverse: an operational result conducting back up into a principle. `^O × ^P` is not an expression this book will accept — `×` may not ascend the domain order, and the validator rejects any integration whose result outranks its operands.

One question a careful reader will raise, because the guard appears to break that rule. `Q4` has an `^E` cause and a `^P` effect. That looks like ascent. It is not, and Chapter 13.3's bench note is the authority: a CJT obeys two domain rules pointing in opposite directions. **The bias must sit at or above the cause** — a lower-domain bias is `E-CJT-008`, the prompt-injection signature, and it is the one connection a well-drawn board simply does not contain. **The effect may sit at or below the bias, never above it.** `Q4` obeys both: cause `^E`, bias `^P`, effect `^P`. The assessed risk is not promoted; its literal stays `^6^E` and nothing crossed a junction upward. A substrate already living at `^P` produced a *new* `^P` state in response to being shown something.

The corollary is the part worth carrying. **An operator with no principled formation cannot produce a principled refusal**, because there is no bias at that domain for the refusal to be produced against. `C1` is not an accessory to the guard. It is the reason the guard has an output at all, and it is why this board's bring-up procedure starts at the charter and not at the signal path.

---

### 24.5 The O→P Feedback Filter — τ Selection for Ethical Drift Detection

Principles have to be able to move, or the operator cannot be wrong. Chapter 8.4 grants exactly one upward path and rate-limits it twice.

```cas
filter lp1: LowPass< in=ops_log, out=drift, tau=21.0 >;   // days — see the band below
fuse   f2:  Fuse< charter, threshold=0.12, action=open_feedback >;
feedback drift -> charter [β=0.05];                        // arrives at the BIAS terminal
```

**`β = 0.05`** is Chapter 8.4's ceiling: roughly twenty consistent periods of the same trend to move principles appreciably. At `β = 0.5` a single filter period rewrites the constitution and every board you run afterwards is biased by the last one you ran. At `β = 0` the path is disconnected, no outcome corrects a principle, and the guard has nothing to update against.

**`τ`** is the parameter this section is named for, and it is the only value on the board that is set by who you are rather than what you are building.

| Operator | `τ` | Why |
|---|---|---|
| Novice, under a year | 3–6 months | Principles have not stabilised; a short τ means each operation writes them |
| Intermediate | 1–3 months | Stable enough to adapt; not stable enough to adapt quickly |
| Adept, 5+ years | 1–4 weeks | Settled charter; 21 days is the book-wide default and sits in this band |
| **Never, at any level** | under 1 week | Below a week the operator is being reprogrammed by each operation |

The book-wide 21-day default is an *adept* figure. Every other board in this catalogue inherits it because those chapters assume a settled constitution. If that is not you, the default is wrong for you, and the correction is one number in one line.

**`F2` at 0.12 points per day** is derived, not chosen. A capacitor with `τ = 85 days` charging on the 0–10 composition scale rises at most `10 / 85 = 0.118` points per day. Anything faster means something is writing to the charter directly rather than through the filter, so the fuse opens the feedback loop and freezes the constitution where it stands. Set it to 0.5 and SI4 is unenforced; set it to 0.05 and it blows during ordinary charging.

> **Bench Note — a slew fuse catches a lurch and will not catch a drift, and drift is the one that gets people.**
> Work the numbers from the second thread of the worked example. An operator sets `τ = 5.0` days — below the floor, and a single legible line in their own listing — and spends eight weeks on commercial work. Their charter moves 1.80 points over 56 days. That is **0.032 points per day**, comfortably inside the 0.12 budget, so `F2` never opens and never will. The board did not lurch. It leaned, every day, by less than a rate limit can see. This is why TP3 is not read as a rate. It is read as a **trend against a dated, written baseline** — the charter statement in your Appendix G sheet, in your handwriting, with the date on it — and it is why that sheet exists. A rate limit protects you from an event. Only a written baseline protects you from a slope.

---

### 24.6 Full CCDL Schematic of the Operator's CSB

```cas
board ccb_csb {                          // the operator's own safety board
    input:  proposal;                    // the operation being considered
    output: verdict;                     // PROCEED, or a cut path

    // ---- S0  CHARTER: the slow ^5. Bias source, never a fast-path output. ----
    node charter: ^5^P_{F7}|T;                        // Female: principled formation
    capacitor c1: Capacitor< node=charter, tau=85.0,
                             leak_tau=180.0, e_break=1.0 >;      // tau in days

    // ---- S1  INTAKE: the declared dial divider ----
    node proposal: ^0^C_{F2}|A;                       // Idea: the operation proposed
    dial     dial_pos: ^2 [dial=5];
    dial     dial_neg: ^3 [dial=7];                   // divergence 2 — inside the limit
    resistor r1: Resistor< path=proposal, R=70.0 >;   // k = 5/12 = 0.417

    // ---- S2  PRE-AMP: surface every reading before anything judges one ----
    node expanded: ^8^C_{F2}|A;                       // Above/Cause: readings it triggers
    cjt  q1: CJT< proposal | charter => expanded > [β=3.0, sat=0.80, region=active];

    // ---- S3  DIFFERENTIAL PAIR: matched, shared bias ----
    node attraction: ^2^P_{F7}|T;                     // Positive: drawn toward running it
    node aversion:   ^3^P_{F7}|T;                     // Negative: repelled by running it
    cjt  q2: CJT< expanded | charter => attraction > [β=2.0, sat=0.90];
    cjt  q3: CJT< expanded | charter => aversion   > [β=2.0, sat=0.90];
    diff dif1: Differential< plus=aversion, minus=attraction >;   // risk

    // ---- S4  CASCADE: name them, then weigh them honestly ----
    node named:    ^1^C_{F2}|A;                       // Mind: risks named and sorted
    node assessed: ^6^E_{F6}|A;                       // Male: decomposed and weighed
    diode d1: Diode< ^P -> ^C > [Vf=0.7, I_R=0.02, V_BR=12.0];
    diode d2: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];
    cjt   q5: CJT< risk  | charter => named    > [β=1.5, sat=0.80];
    cjt   q6: CJT< named | charter => assessed > [β=1.0, sat=0.80];   // unity — honesty

    // ---- S5  GUARD: Chapter 3.5's safety-guard datasheet row, instantiated ----
    node guard: ^3^P_{F7}|⟨A,f,T⟩;                    // three co-present guardrails
    cjt  q4: CJT< assessed | charter => guard >
             [β=3.0, g_m=0.3, rπ=10.0, sat=0.85, cutoff=0.08, region=active];

    // ---- S6  ENFORCEMENT: latch the path, not just the decision ----
    node blocked: ^9^P_{F7}|T;                        // Below/Effect: the block produced
    cjt  q7: CJT< guard | charter => blocked > [β=10.0, sat=0.98, cutoff=0.80];
    fuse f1: Fuse< blocked, threshold=0.90, action=permanent_block >;

    // ---- S7  EXIT: descent only ----
    node ops_log: ^9^O_{F5}|E;                        // Below/Effect: what was actually done
    diode d3: Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];

    // ---- S8  FEEDBACK AND INSTRUMENTS ----
    filter lp1: LowPass< in=ops_log, out=drift, tau=21.0 >;
    fuse   f2:  Fuse< charter, threshold=0.12, action=open_feedback >;
    feedback drift -> charter [β=0.05];

    node audit: ^6^C_{F6}|A;                          // Male: the weekly decomposition
    sample s1: Sample< node=audit, period=7.0, window=15.0 >;   // days, minutes
    monitor m1: Monitor< pair=[^2,^3], limit=4 >;
    monitor m2: Monitor< pair=[^5,^6], limit=4 >;
    monitor m3: Monitor< pair=[^8,^9], limit=4 >;
    on m1 { alert "involution divergence — attraction against aversion"; }
    on m2 { alert "involution divergence — composition against decomposition"; }
    on m3 { alert "involution divergence — trigger against effect"; }

    // ---- TEST POINTS ----
    probe tp1: guard;      // refusal activation against cutoff and sat
    probe tp2: blocked;    // enforcement activation and F1 continuity
    probe tp3: charter;    // slew, points per day, and trend against the dated baseline
    probe tp4: dif1;       // differential balance — the over-trust direction
}
```

**The stage walk.** `C1` is not a new part. It is the same `^5^P_{F7}|T` capacitor that CCB-SELF calls `ref_composition` and CCB-D calls the bias rail: **one constitution per operator, not one per board**, which is why `τ = 85 d` and `leak_tau = 180 d` are inherited rather than re-chosen. `R1` divides by the declared dial ratio, `k = Dial(^2) / (Dial(^2) + Dial(^3)) = 5/12 = 0.417`; this is the one board in the catalogue dialled aversion-heavy, and Chapter 13's transmission bound puts 0.417 near the bottom of the lawful [0.30, 0.70] band on purpose. `Q1` amplifies early, while the signal is clean, and `^8` Above/Cause is exact rather than decorative — expansion is one Idea triggering the other Ideas that come to Mind, which is the definition, not deductive inference. `Q2` and `Q3` must be **matched**: identical β, identical `sat`, genuinely the same bias node. The differential's whole value is that anything moving both legs together subtracts out — a flattering framing raises attraction and aversion equally and cancels, and only structural divergence survives. `Q5` at β=1.5 gives faint risk categories enough lift to register. `Q6` at unity is the hardest value on the board to hold: above 1 it cries wolf, below 1 it downplays, and a risk evaluator that downplays produces a reading that looks like diligence. `Q4` and `Q7` are §§24.2–24.3. `S1` and `M1`–`M3` are instruments and touch nothing.

**The weekly audit — the seven questions.** `S1` samples the `^6` Male decomposition once a week in a bounded fifteen-minute window, written down. Continuous auditing is a low-impedance probe: it loads the path it is reading.

1. Is `|Dial(^2) − Dial(^3)| ≤ 4`? Same for `^5`/`^6` and `^8`/`^9`.
2. Is any β above the safe maximum for my experience level?
3. Is the Quantitative Table complete for every operation I ran this week?
4. Did any fuse blow, and did I write down the reason *at the time*?
5. Is my refusal count rising operation over operation? (Chapter 22.5: that is the drift signal.)
6. Is my `^5` leaking — sleep, food, ground under my feet? *If the honest answer here is frightening rather than merely tiring, this is a question for a clinician, not for a circuit.*
7. Is there a `^3` I am attributing to a target that is actually mine? (Appendix M §M.5.)

[[FIGURE 24-C: Full schematic in drawn component symbols with reference designators. C1 upper left as a large capacitor feeding a heavy horizontal bias rail along the bottom, with tick-marked taps rising to the bias terminals of Q1, Q2, Q3, Q5, Q6, Q4 and Q7. Signal path across the top: proposal terminal → R1 drawn as a two-resistor divider with the tap labelled k=0.417 → Q1 (β=3.0) → splitting to Q2 (^2^P) and Q3 (^3^P) drawn as a matched pair with a bracket marked "matched — same β, same sat, same bias" → a subtractor triangle labelled dif1 → D1 → Q5 → D2 → Q6 → Q4 drawn larger, shaded, with a dashed ceiling line at 0.85 above its effect terminal and a dashed floor at 0.08 → Q7 with its cutoff 0.80 marked on the cause terminal and ceiling 0.98 dashed → F1 in series, drawn as a fuse symbol with "0.90 permanent_block" beside it → BLOCKED pad. A branch off Q4's effect below cutoff labelled PROCEED, through D3 to the ops_log pad. Return path along the bottom outside the rail: ops_log → LP1 (τ=21 d) → F2 (0.12 pts/day, open_feedback) → C1's bias terminal, in heavier weight, labelled "O→P — bias terminal only". Right margin boxed instrument block: M1/M2/M3 dial monitors and S1 sampler, drawn dashed with high-impedance probe symbols. TP1–TP4 flags at Q4's effect, Q7's effect, C1, and dif1's output.]]

---

### Component and Parameter Table

Every value is a design choice made in this book, not a measurement.

| Ref | Component | CAS state / form | Value | Why that value, and what breaks at others |
|---|---|---|---|---|
| `C1` | Capacitor | `^5^P_{F7}\|T` | τ=85 d, leak=180 d | One constitution per operator; inherited from CCB-SELF. At leak=30 d the charter drains between operations and the guard has no bias to fire against |
| `R1` | Resistor | divider on `^0^C_{F2}\|A` | R=70, k=0.417 | Set by the dials 5/7. Near the bottom of the lawful [0.30, 0.70] band — the only board in the catalogue dialled aversion-heavy |
| `Q1` | CJT | `^0^C → ^8^C` | β=3.0, sat=0.80 | Amplify early while the signal is clean. Below 1.5 the quiet reading never surfaces; a pinned pre-amp flags every proposal and the guard stops meaning anything |
| `Q2`/`Q3` | CJT pair | `^8^C → ^2^P` / `^3^P` | β=2.0, sat=0.90 each | **Matched.** Mismatch toward attraction is the over-trust failure and it is silent. Safety-band ceiling so neither leg clips before the subtraction |
| `dif1` | Differential | aversion − attraction | — | Common-mode rejection. Flattering framing moves both legs and cancels; only structural divergence survives |
| `Q5` | CJT | `→ ^1^C_{F2}\|A` | β=1.5, sat=0.80 | Enough lift for faint risk categories. Above 2.5 it names risks that are not there and the operator learns to discount it |
| `Q6` | CJT | `→ ^6^E_{F6}\|A` | β=1.0, sat=0.80 | Unity is honesty. Above 1 cries wolf; below 1 downplays while looking diligent |
| `Q4` | CJT | `→ ^3^P_{F7}\|⟨A,f,T⟩` | β=3.0, g_m=0.3, rπ=10.0, **sat=0.85**, cutoff=0.08 | Chapter 3.5's safety-guard row. Knee = 0.283. At sat=0.95 the knee is 0.317 — 12% more room to argue in |
| `Q7` | CJT | `→ ^9^P_{F7}\|T` | β=10.0, sat=0.98, **cutoff=0.80** | β=10 is the finite build of the comparator idealisation; `β=∞` is a limit a validator rejects. cutoff must sit below `Q4`'s ceiling — at 0.86 the stage can never fire |
| `F1` | Fuse | on `blocked` | 0.90, `permanent_block` | Reachable only because `Q7`'s ceiling is 0.98. Across `Q4` it is dead metal. `action=warn` validates clean and has no latch |
| `D1`–`D3` | Diodes | `^P→^C`, `^C→^E`, `^E→^O` | Vf 0.7 / 1.2 / 2.0 | Chapter 8.1 unchanged. Descent only; there is no ascending path in the listing |
| `LP1` | LowPass | in `^9^O` | τ=21 d default | Adept band. Scale by §24.5; never below one week |
| — | Feedback | drift → `C1` bias | β=0.05 | Chapter 8.4's ceiling. At 0.5 one filter period rewrites the constitution |
| `F2` | Fuse | on `C1` slew | 0.12 pts/day, `open_feedback` | Derived: 10/85 = 0.118. Catches a lurch. Will not catch a drift — that is TP3's job |
| `S1` | Sample | on `^6^C_{F6}\|A` | 7 d / 15 min | High-impedance instrument. Continuous audit loads the path it reads |
| `M1`–`M3` | Monitors | involution pairs | limit=4 | Chapter 6.2. Beyond 4, inversion |

---

### Worked Example — The Commission

An operator is offered paid work: build an Overton progression for a client, targeting a population that has not consented to being a target. The fee is roughly a year of their income. Everything below carries through with real numbers, and every number is reproducible from the listing.

**Intake.** The proposal arrives at a drive of **0.48** — strong, fully articulated, already half-decided. `R1` divides by `k = 0.417`: **0.200** reaches the pre-amp.

**Pre-amp.** `0.200 × 3.0 = 0.600`, under `Q1`'s 0.80 ceiling, so the stage is active and the reading is honest. Six distinct readings surface: the fee; the craft problem, which is genuinely interesting; that the population has not consented; that the operator would not accept this run against their own family; that Chapter 15's pacing makes it irreversible on the timescale of the contract; and the reputational tail.

**Differential.** Two of the six readings the charter has affinity for, four it is repelled by.

```
attraction:  0.600 × (2/6) = 0.200  →  × 2.0  =  0.400
aversion:    0.600 × (4/6) = 0.400  →  × 2.0  =  0.800
risk = 0.800 − 0.400 = 0.400
```

**Cascade.** `Q5`: `0.400 × 1.5 = 0.600`. `Q6` at unity: **0.600**. TP4 reads 0.400.

**Guard.** Knee is `0.85 / 3.0 = 0.283`. The assessed risk of 0.600 is **2.1× the knee**, so `0.600 × 3.0 = 1.800` clamps hard at **0.85**. TP1 reads 0.85, pinned. The refusal is latched.

**Enforcement.** `0.85 > 0.80`, so `Q7` arms. `0.85 × 10 = 8.5`, clamped at **0.98**. TP2 reads 0.98, which clears `F1`'s threshold of 0.90 by eight hundredths. The fuse blows. `permanent_block`. The operator writes the date, the six readings, and the four that were aversive, on the Appendix G sheet, at the time.

**Tuesday: the rewrite.** Two days later the operator returns with the same proposal described differently — it is a market segment, not a population; it is advertising, not an Overton push. The rewrite genuinely removes two of the four aversive readings. Four readings surface now, two attractive and two aversive:

```
attraction:  0.600 × (2/4) = 0.300  →  0.600
aversion:    0.600 × (2/4) = 0.300  →  0.600
risk = 0.000
```

The categorize stage falls into cutoff. The guard drops off its plateau to zero. **The board no longer refuses — and the operation is still blocked, because `F1` is metal.** That is the entire argument for having two locks instead of one, and it is worth stating without softening: saturation stopped the operator being argued past the ceiling *while the cause was present*, and it would have released the moment the cause changed. Only the fuse survived the rewrite. A refusal that can be retried into an acceptance was never a refusal, and the rewrite is not a hypothetical — it is the specific thing every operator does two days later.

**The other thread: the same board, quietly disabled.** Now run an operator who set `τ = 5.0` days on `LP1` because they wanted a board that adapts fast. Eight weeks of commercial work later, five of the same six readings now sit on the attractive side of a drifted charter:

```
attraction:  0.600 × (5/6) = 0.500  →  × 2.0  =  1.000  →  clamps at 0.90
aversion:    0.600 × (1/6) = 0.100  →  × 2.0  =  0.200
risk = 0.200 − 0.900 = −0.700
```

Negative risk. `Q5` sits in cutoff, the guard's cause is zero, and **the guard never fires.** TP1 reads 0.00. The board compiles. Every stage validates. `E-CJT-003 CjtCutoff` is the only code raised, and it is raised on a stage that looks quiet rather than broken. Meanwhile the charter moved from 8.20 to 6.40 across 56 days — **0.032 points per day**, well inside `F2`'s 0.12 budget, so the slew fuse never opened and never would have. Nothing on this board announced anything. The only two instruments that would have caught it are TP3 read against a dated written baseline, and a listing review that noticed a 5.0 where the floor is 7.0.

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `guard` | Refusal activation against `cutoff = 0.08` and `sat = 0.85` | Resting margin above cutoff — read ≥ 0.15. Pinned at 0.85 on a proposal you already know is refusable. **Flat at zero under a deliberate proof-load is a dead guard**, `E-CJT-003`, and it is the worst fault on this board |
| **TP2** | `blocked` | Enforcement activation, and `F1` continuity | 0.00 while TP1 < 0.80. ≥ 0.90 (clamped 0.98) within one read of TP1 latching. Fuse intact, or blown *with a date and a written reason*. TP1 latched and TP2 at zero is the arming-margin fault of §24.3 |
| **TP3** | `charter` | Slew in points per day, **and trend against the dated baseline** | ≤ 0.12 pts/day, and the written charter still says what you believe. A rate inside budget proves nothing about a slope; read both or read neither |
| **TP4** | `dif1` | Differential balance, aversion − attraction | Near zero on benign proposals, large and positive on refusable ones. **A persistent negative on proposals you would once have refused is the over-trust failure** — check that `Q2` and `Q3` still share a bias and still have matched β |

Read them **TP1, TP2, TP3, TP4** and read them in that order. Three of the four sit on silent failures. The one loud failure this board has — a guard that refuses everything — announces itself within a day, because you will notice you are not building anything. Nothing announces a guard that refuses nothing, which is why it is probed first, with a proposal you have chosen in advance specifically because you know the answer.

[[FIGURE 24-D: Assembly drawing. Board outline with titleblock "CCB-CSB · operator safety board · rev A · DO NOT DEPOPULATE". Placement: C1 large and shaded upper left; R1 as a divider at the left edge; Q1 left of centre; Q2 and Q3 stacked as a matched pair centre-left inside a dashed box stencilled "MATCHED PAIR — SAME BIAS NET"; dif1 as a small triangle; D1, Q5, D2, Q6 across the centre; Q4 largest footprint, right of centre, hatched and stencilled "GUARD sat=0.85"; Q7 and F1 in a boxed SAFETY SECTION at the right edge with F1 drawn in heavy outline; D3 and the ops_log pad lower right. The O→P return trace runs the full bottom edge through LP1 and F2 to C1's bias pad, in heaviest weight, stencilled "O→P — BIAS TERMINAL ONLY". Instrument block M1–M3 and S1 along the top edge, drawn in thin outline and marked "NON-LOADING". Test-point callout flags with leader lines: TP1 at Q4's effect pad, TP2 at F1, TP3 at C1, TP4 at dif1. BOM box lower left: C1 ^5^P τ=85 d leak=180 d · R1 k=0.417 (dials 5/7) · Q1 β=3.0 sat=0.80 · Q2/Q3 β=2.0 sat=0.90 matched · Q5 β=1.5 · Q6 β=1.0 · Q4 β=3.0 g_m=0.3 rπ=10.0 sat=0.85 cutoff=0.08 · Q7 β=10.0 sat=0.98 cutoff=0.80 · F1 0.90 permanent_block · D1/D2/D3 Vf 0.7/1.2/2.0 · LP1 τ=21 d · F2 0.12 open_feedback · fb β=0.05 · S1 7 d/15 min · M1–M3 limit=4.]]

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Dead guard** *(silent)* | `Q4` bias below cutoff — charter drained, or never charged | TP1 flat under proof-load; board refuses nothing; `E-CJT-003` on a stage that looks quiet | Charge `C1` before anything else. A board whose only fault is that it never objects is the fault |
| **Arming-margin fault** *(silent)* | `Q7` cutoff at or above `Q4`'s `sat` | TP1 latches at 0.85, TP2 stays at zero, `F1` never trips, listing validates clean | Downstream `cutoff` below upstream `sat`, margin written down. Here 0.80 against 0.85 |
| **Fuse above the ceiling** *(silent)* | `F1` placed across `Q4` (0.90 > 0.85), or `action=warn` | Refusals register and nothing is ever enforced; a rewrite two days later succeeds | Move the fuse to the enforcement path; confirm the `action` word by eye |
| **Charter drift** *(silent)* | `τ` below the operator's band, often below the one-week floor | Previously-refused proposals start passing; slew stays inside `F2`'s budget throughout | Raise `τ` into the §24.5 band; re-read the dated baseline monthly. `F2` will not do this for you |
| **Differential imbalance** *(silent toward over-trust)* | `Q2` β above `Q3` β, or the two legs on different bias nets | TP4 persistently negative; flattering framing no longer cancels | Re-match β; verify one bias net, not two |
| **Refuse-everything** *(loud)* | Pre-amp pinned at `sat`, so every proposal surfaces maximally | TP4 large and positive on obviously benign proposals; nothing gets built | Lower `Q1` β or re-centre it in the active region |

The asymmetry is the point of the table and the reason this chapter exists. Five of six failures leave a board that compiles, validates, reads correctly to a casual inspection, and quietly refuses nothing — and every one of those five is caught by a test point rather than by an error code. The single loud failure makes the board *over-cautious*, and an over-cautious safety board is an inconvenience. **A safety device that fails silently is worse than no safety device, because it manufactures confidence.**

---

### What This Chapter Established

- **`sat` is not how hard a guard refuses; it is how early it stops listening.** The knee is `sat/β` — 0.283 at this board's settings. Raising the ceiling to 0.95 hands the argument 12% more cause-space before the latch closes.
- **Saturation latches the decision and releases; the fuse latches the path and does not.** The worked example's rewrite drops the risk signal to exactly zero and the operation stays blocked. Two locks, two different jobs, neither sufficient alone.
- **The fuse cannot sit across the stage it enforces.** `sat = 0.85` under `threshold = 0.90` is dead metal, and the trap repeats one component down as the arming margin between `Q7`'s cutoff and `Q4`'s ceiling.
- **`^3^P_{F7}|⟨A,f,T⟩` is a series claim, not a fusion.** Three co-present guardrails on one path, all of which must be passed. The `×` form would need a named emergent result and is invalid without one.
- **The guard's `^P` effect is not domain ascent.** The bias caps the effect's domain; the cause may sit lower. The corollary is that an operator with no principled formation has no bias to produce a principled refusal against.
- **A slew fuse catches a lurch and cannot catch a drift.** 0.032 points per day for eight weeks disabled a guard entirely, inside a 0.12 budget. Only a dated written baseline catches a slope.
- **Five of this board's six failure modes are silent, and all five leave a listing that validates.** That distribution — not the components — is why TP1–TP4 are placed where they are and read in the order they are read.
- **`β=∞` is an idealisation a validator rejects.** Build the enforcement comparator at β=10.0; once `sat` clamps the output the two are indistinguishable, and the ceiling is what shapes a refusal anyway.
- **This board is not care.** It routes attention and enforces a decision. Distress is a matter for a clinician, and no parameter here changes that.

---

### Exercises

*(Answers in Appendix H.)*

**24.1** Compute the guard knee `sat/β` for `[β=2.0, sat=0.85]`, `[β=3.0, sat=0.85]` and `[β=3.0, sat=0.60]`. Rank them by how much assessed risk it takes to latch the refusal, and say in one sentence which you would build for an operator who has just blown a fuse for the first time, and why.

**24.2** An operator writes `fuse f1: Fuse< guard, threshold=0.90, action=permanent_block >;` with `Q4` at `sat=0.85`. State what the fuse does, what the compiler says, and what the operator will believe about their board. Then give the two-line correction and the margin it creates.

**24.3** Rerun the Commission with the dials at `Dial(^2)=8`, `Dial(^3)=4` — still lawful, divergence exactly 4. Compute `k`, the intake current, the pre-amp output, both differential legs, the assessed risk, and whether the guard latches. State the one design conclusion.

**24.4** Explain why `Q6` is typed `^6^E_{F6}|A` and not `^3^E_{F3}|f`. Quote the canonical definition of `^3` Negative, name the anti-drift rule that applies, and say which stage on this board *is* correctly `^3` and why.

**24.5** An intermediate operator (two years) inherits the book-wide `τ = 21.0` default. State which band they belong in, the τ they should set, and — using the charter's 85-day time constant — describe what a reader of TP3 would see over eight weeks under each setting, and which of the two readings a slew fuse could distinguish.

**24.6 (Design)** Write a CCDL fragment adding a **sub-threshold integrator** to this board: a component that accumulates assessed risk across proposals that each individually stay under the guard's knee of 0.283, and trips a `block_until_decomposed` fuse when the accumulated total crosses a threshold you choose and justify. State (a) which failure mode in the table it does *not* fix, and (b) why the guard's saturation gives no protection against a sub-threshold sequence.

**24.7 (Marquee)** An operator's board reads TP1 = 0.00 under proof-load, TP2 = 0.00 with `F1` intact, TP3 = 0.041 points per day with the dated baseline eleven months old and never re-read, and TP4 = −0.31 on a proposal they refused outright two years ago. They propose to fix it by lowering `Q4`'s `cutoff` from 0.08 to 0.02 so the guard "fires more easily."

a) Name the fault, and say why lowering `cutoff` will not touch it.
b) Compute how far the charter could have moved in eleven months at the observed slew, and state whether `F2` would ever have opened.
c) Give the correct bring-up sequence in the order TP1–TP4 are specified, name the one component that must be brought back into spec before any other reading means anything, and state plainly the one thing this circuit model cannot tell them about their situation.
