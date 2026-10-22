# HELM Cube device spec v1 (concept) and the RPM depth governor

**Status: INTENDED. CONCEPT ONLY. NOTHING BUILT, NOTHING LICENSED, NO MONEY.**

Written 2026-10-22 on the laptop, 0 USD. No HELM code changed. This file is a plain-English concept. It is not a result and it moves no claim.

**How this file relates to earlier records.** The owner asked much the same two questions on 2026-10-21, and a forked session answered them in spec section 7.120 (design only). That work lives in `docs/working/helm_cube_device_concept_v0/HELM_CUBE_SPEC.md` (v0.1) and `docs/working/helm_rpm_depth_decider_design_v1/DESIGN.md`. This v1 file restates the device brief from the owner's 2026-10-22 words and adds the depth governor as a rule. **Where this file and the owner's earlier rulings in v0.1 disagree, the owner's rulings win.** One known conflict: on 2026-10-21 the owner withdrew a light band around the middle, because a band marks a top and a bottom, and moved the light to all twelve edges (7.120). This file still lists the band as one option because the 2026-10-22 brief asked for both options. The band is NOT the owner's choice of record. The concept drawing `helm_cube_concept.svg` beside this file shows the band; it is a drawing of the option, not of the ruling.

---

## (a) The owner's words, verbatim, dated

The owner, 2026-10-22, recorded in `C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md` as a STATEMENT OF INTENT, not an approval:

> "WHAT IF WE LET THE EYE OR SOME OTHER REASONING PART DETERMINE IF MORE RPM DEPTH WAS NEEDED/NECESSARY ON A GIVEN MATTER? HOW WOULD THAT WORK AND COULD THAT WORK? ALSO I WANT TO CREATE A HARDWARE DEVICE FOR THE EVENTUAL FINAL FORM FACTOR OF HELM LIKE A BLACK CUBE WITH A GLOWING, PULSATING LIGHT STRIP TO DENOTE SPEECH CADENCE, LISTENING AND VARIOUS OTHER LIKELY MODES ETC. CONNECTS TO WIFI W/ BLUETOOTH OF COURSE NO BUTTONS JUST A SHAKE TO WAKE AND TAPS TO CONNECT, CONTROL OTHER DEVICES(DIFFERENT NUMBERS OF TAPS FOR VARIOUS FUNCTIONS), QI SUPERCHARGING ONLY, HAS A COMPANION APP OF COURSE THE SMALLER THE CUBE THE BETTER ACCEPTABLE SIZES ARE ANYWHERE FROM PALM SIZE TO TENNIS BALL SIZE CAMERAS SPEAKERS AND MICROPHONES ON ALL SIX SIDES BUT VISIBLE NOWHERE ONCE WRITTEN UP OF COURSE ADD TO HELM HUB GET CLAUDE DESIGN TO DRAW IT UP."

This approves no money, no order, no build and no claim.

---

## (b) Form

- **Shape:** a black cube with rounded edges and a soft-touch matte shell.
- **Size:** edge 55 mm to 67 mm. A tennis ball is about 67 mm across. So a 55 mm cube fits in the palm, and a 60 mm cube matches a tennis ball's bulk. (A 60 mm cube holds 216 cubic cm; a 67 mm ball holds about 157 cubic cm, so by volume 60 mm is already a little bigger.) Smaller is better, as the owner said; 55 mm is the floor for fitting the parts honestly (see (k)).
- **No buttons. No visible holes.**
- **One continuous light strip.** Two options:

| Option | What it looks like | Good | Bad |
|---|---|---|---|
| Equator band | a thin ring around the middle of four faces | one simple light guide; easy to read from any side at table height | marks a top and a bottom, so the faces are no longer all the same; **withdrawn by the owner on 2026-10-21 (7.120)** |
| Edges | light along the cube's edges (the four vertical edges, or all twelve as the owner ruled) | keeps every face the same; invisible when off | more light-guide parts; harder to seal; corners are drop points |

---

## (c) Light language

The light is driven only from HELM's own receipt states (a receipt is the record HELM writes for each step). So the light never claims more than HELM did. Example: the "asking" light fires only when HELM's turn ended with a `CLARIFY_` status; the "I don't know" light fires only when HELM recorded `UNDETERMINED`.

| Mode | Colour | Motion | Driven by |
|---|---|---|---|
| Listening | soft white | slow breathe (about 4 s per breath) | microphones open and the reader waiting |
| Thinking | white | a pulse that travels along the strip | the RPM gate or the brain running |
| Speaking | white | brightness follows HELM's speech envelope syllable by syllable (the "speech cadence") | the voice output's loudness, frame by frame |
| Asking a question | blue | a rising sweep | a `CLARIFY_` status in the turn's receipt |
| "I don't know" / needs input | amber | steady hold | an `UNDETERMINED` or refusal receipt |
| Privacy (mics and cameras cut) | red | solid red on one edge, or fully dark (owner to choose) | the hardware cut line itself, not software |
| Charging | dim white | slow fill from the bottom up | the charger chip's state |
| Pairing | blue | a chase around the strip | pairing mode open |
| Error | red | double blink, then off | a failed self-check or a failed step receipt |

---

## (d) Input: shake and taps

- **Shake to wake:** an accelerometer (a motion sensor). It wakes only on at least two strong shakes within about 1 s (the threshold is set by test, starting near 2.5 g). After a wake there is a cooldown of a few seconds. A single bump in a bag does not wake it.
- **Taps:** the same sensor tells how many taps and which face was tapped.

| Gesture | Default action |
|---|---|
| 1 tap (any face) | wake, or stop talking |
| 2 taps | pause / resume |
| 3 taps | repeat the last answer |
| Long press (hold a face about 2 s) | privacy toggle: cut mics and cameras |
| Double-tap on the top face | connect / pairing mode |
| Tap pattern on a named face | a device command from the tap grammar |

- **Tap grammar for other devices** (set in the companion app): the face picks the device ("the face toward the lamp is the lamp"); the tap count picks the action (for example 1 = on/off, 2 = brighter, 3 = dimmer). Each command goes through the RPM gate and leaves a receipt, like any other HELM action. A tap HELM cannot map is not guessed: the light shows amber.

---

## (e) Senses

- **Microphones on all six faces**, used together as a beamforming array (several mics combined to listen in one direction). They sit behind acoustically transparent micro-perforations under the coating, about 0.1 mm across, invisible at arm's length.
- **Six cameras**, one per face, each behind a dark glass panel flush with the shell that passes visible and infrared light. Said honestly: a camera needs a window. "Invisible" here means behind dark glass that reads as solid black, not truly absent.
- **Speaker:** one full-range driver plus a passive radiator, using the whole body as the sound box, firing through the same perforations.

## (f) Radios

Wi-Fi 6/6E and Bluetooth LE 5.x.

## (g) Power

- **Qi2 magnetic wireless charging only. No ports.**
- "Supercharging" in standard terms means Qi2 at 15 W today, with 25 W under Qi2.2.
- A small cube has a small battery: roughly 1,500 to 2,500 mAh at 55 to 67 mm. Expect hours of active talk and about a day on standby. These are estimates, not measurements.
- Heat is the limit: a sealed cube with no vents cannot shed much heat while it charges fast and talks at the same time.

## (h) Compute: what runs where

- **On the cube:** HELM's recipe brain and the hand-written reader are tiny. They run on a microcontroller-class chip or a small application processor.
- **The CTT** (the transformer ear, 9,585,566 parameters) fits an edge NPU (a small chip for neural networks).
- **Anything larger** runs on the paired phone or a home hub.
- **The rule:** HELM's checks and receipts stay on the cube, whatever else runs elsewhere.

## (i) Privacy as hardware

- The long press cuts mic and camera power in hardware. The light reads the cut line itself, so it shows the truth.
- Local-first processing. No cloud by default.

## (j) Companion app

Pairing; tap grammar editor; device control list; memory viewer with receipts; privacy log (every cut and every reopen, with times); light preview (play every mode before choosing).

## (k) The honest hard parts

1. Six cameras, six mics, a speaker, a battery, radios and an NPU in a 55 to 67 mm cube is dense and hot.
2. "Invisible" cameras need dark glass windows. They are hidden, not absent.
3. Qi-only means no wired recovery port. Proposal: a hidden pogo-pin service pad under the base, for factory and repair use only.
4. Sound leaks between faces inside a small box. The mic array must reject the cube's own speaker.
5. Drop durability: a dense cube lands on a corner. Corners and the light guide take the hit.

## (l) What would come first

A 3D-printed shell with a dev board inside (for example an ESP32-S3, or a small Linux board) running HELM's chat, to test the light language and the tap grammar before any custom electronics. Nothing is ordered without the owner's money line.

---

## Thinking deeper on demand: who decides the RPM depth

**The question (owner, 2026-10-22):** could the Eye, or some other reasoning part, decide when a matter needs more RPM depth? How would it work, and could it work?

**Plain answer: yes, as a written rule with receipts. Not by the Eye.**

### What the record says about depth limits

The sources disagree (spec §7.35's tail and the 2026-10-15 change-log row list them):

| Source | Depth limit |
|---|---|
| The published book (canon) and the Rust engine | 5 |
| rc0 / CNCM | 4 |
| HELM Gate A, the TKS rails, the Atlas expansion default | 3 |
| The Builder's Manual | log2(resources) + 3 |
| **In force for HELM:** the owner's depth ruling (commit `0e48ec2f`, PR #329; §7.48, §7.55) | **`HORIZON = 12`**, with canon's 5 kept on the record |

The D/W/P engine and the repair performer are in §7.48 (`ENGINEERED-NOT-VALIDATED`). Today the live loop starts at depth 0, and a REPAIR opens one child per gap at depth 1 (§7.120).

### The proposal: a depth governor inside the RPM gate

The **depth governor** is a rule inside the RPM gate. It decides; the Eye does not.

1. **Go one level deeper only** when the gate returns `REPAIR` or `UNDETERMINED` for a reason a child repair can address: a missing prerequisite, an unread clause, an untaught line.
2. **Never go deeper** when the reason is "the user did not say". Then HELM asks.
3. **Hard ceiling:** the depth ruling of record (`HORIZON = 12`).
4. **Per-turn budget:** a fixed number of descents per turn, written down before any test.
5. **No-progress stop:** stop when a level adds no new checked fact. (The owner's decoupling stop, §7.69, is a scored rule of this kind, on made-up worlds only.)
6. **Receipts:** every descent leaves a receipt saying why it went deeper and what it found.

### The Eye's role: advisor only

The Eye is report-only. It may whisper "this looks worth going deeper" or "this is looping". The governor may count a whisper as one input among its written reasons. **The Eye never sets depth.**

Eye acting stays `NOT LICENSED` (§7.38). EYE-ACT-1 (§7.122) was built behind the switch `HELM_EYE_ACT` (default OFF) and scored on the owner's line: all 10 hard gates held; words `EYE_ACT_EARNED_KEEP`, `CONCERT_ACT_EARNED_KEEP`, `EYE_ACT_BEATS_CHECKSUM_COPY`, `TIES_REBUILD_ALWAYS`; labels `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY`; acting stays `NOT LICENSED`, switch OFF. That test was about the Eye acting on faulted memory items, not about depth.

### How to test it

A sealed exam (items the builder never sees) with items that need depth 1, 2 or 3 and items that need no descent at all. Three cheap baselines to beat:

- always depth 1;
- always the maximum depth;
- depth = the number of missing prerequisites.

Scored on: right answers; wrong answers (must be 0); wasted descents (descents that added no checked fact); asks.

### Could it work?

Yes, as a rule with receipts: each step down has a written, checkable reason, and the no-progress stop and the ceiling bound the cost.

### What it cannot do

It cannot decide depth from "importance" or "interest" without a written, checkable reason. A feeling that a matter matters is not a reason the gate can check.
