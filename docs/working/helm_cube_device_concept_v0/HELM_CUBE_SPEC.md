# HELM Cube — device concept spec v0.1 (design only, nothing built)

**Date:** 2026-10-21. **v0.1** applies the owner's two rulings of the same day (Section 0). v0 put the light in a band around the middle and left the charging face without full sensors; both are changed here.
**Status:** Design only. Nothing has been built, bought, measured or run, and nothing was spent (0 USD). Every capability below is a proposal. None of it is tested.

**Number tags:**
- **[M]** means MEASURED-BY-SOURCE. The number comes from a datasheet, a standard or a maker page. If it is marked "(secondary)", it comes from a retailer, press, forum or patent page, and should be checked against the primary document.
- **[E]** means ESTIMATE. It is our own arithmetic or design judgment, and it needs a prototype to confirm.
- **S-numbers** point to the source list in Section 14.

**HELM terms used here:**
- **HELM:** a small reasoning system that works with recipes. It does exact fraction arithmetic and has few parameters. There is no large language model inside it.
- **RPM gate:** the check that every needed input is present before HELM answers. If one is missing, HELM stops and marks the answer `UNDETERMINED`. It never guesses. Code: `C:\Users\wakil\OneDrive\Desktop\tksCAS\helm_brain_22x40.py`, lines 117-136.
- **Unity Eye:** a watcher that writes reports. It never acts.

---

## 0 Owner rulings that govern this spec (2026-10-21, verbatim)

1. **"FOR THE ISSUE OF THE BOTTOM AND CHARGING MAGNETIC PULL AND HAPTIC FEEDBACK SHOULD TAKE CARE OF KNOWING WHICH SIDE TO CHARGE"**
2. **"YES BECAUSE THE MAIN THING IS THAT IT SHOULD LOOK THE SAME ON ALL SIDES LIKE A PLAIN BLACK BOX"** (the "yes" accepts: while the cube is docked, the charging face's camera, mic and speaker rest, and the other five faces listen, watch and speak.)
3. **"WITH GYRATOR WHEN IT'S BEEN MOVE TURNED AND DIRECTION FOR MAPPING IT'S ENVIROMENT GEOLOCATION AND USE WIFI TO DRAW ITSELF AN INTERNAL SCHEMATIC OF IT'S ENVIROMENT AND OR USE LIDAR"** ("gyrator" = gyroscope; see Section 8a.)
4. **"ALL OF WHICH FEEDS BACK TO HELM WHO WILL HAVE ANY NECESSARY CONTROLS OVER"**
5. **"THE ENTIRE OUTSIDE MADE OUT OF GORILLA GLASS THAT IS BLACK BUT CAN TURN ON AND SHOW SCREENS IMAGES VIDEOS ETC THIS COULD BE ANOTHER VERSION YES THIS IS JUST ANOTHER VERSION NOT THE MAIN VERSION"** (a second version; see Section 15. The main version stays the edge-light cube.)

**What these rulings decide:**
- **The governing rule: when it is off, the cube is a plain black box, identical on all six faces.** No face, edge or band may look different from another when unlit. Any design choice that breaks this is wrong for this product.
- **One charge face, found by feel.** One face carries the Qi2 magnet ring and the charging coil. Nothing marks it. Bring the cube near the charger and that face pulls itself into place; a short haptic pulse (a tiny vibration motor, a linear resonant actuator or LRA) confirms that charging started. A Hall-effect sensor (a chip that feels a magnet) knows the cube is docked.
- **Every face has a camera, a mic and a sound port, the charge face included.** While docked, the charge face's sensors rest and the other five work.
- **The light is dead-front and symmetric.** "Dead-front" means invisible until lit. It runs along all twelve edges, so every face is framed the same way. There is no band around the middle (that would mark a top and a bottom).
- **Roles follow orientation, not markings.** "The face pointing up" is whichever face is up; the motion sensor knows which.
- **HELM is in charge (ruling 4).** Every sensor reading (motion, turning, location, the room map, sound, pictures) feeds HELM, and HELM holds the controls: which sensors run, when the cube maps, what the light shows, which home devices it controls. Every such action goes through HELM's RPM gate and leaves a receipt; a missing fact stays `UNDETERMINED` and HELM asks. **Two hardware lines stay outside all software, HELM included** (operator's proposal, kept unless the owner overrules): the camera-on light is wired to each camera's power, and the hard mute is a physical switch. HELM can turn any camera or mic on or off; it cannot hide that it did (Section 9).

## 1 Said plainly first

1. The HELM Cube is a small black cube. It listens, talks, sees, and controls other devices in the home.
2. The target size is 64 mm on each side, about as wide as a tennis ball. The smallest honest size is 55 mm, which costs magnetic charging and on-cube speech.
3. It has no buttons. You shake it to wake it and tap it to give commands. The number of taps picks the action, and the face you tap picks the target.
4. When off it is a plain black box, the same on all six faces. When on, light glows along all twelve edges to show what it is doing, and it pulses in time with HELM's speech.
5. It charges only on a Qi wireless pad. Nothing marks the charging face: magnets pull it onto the charger and a short buzz confirms charging. Heat, not the charging standard, limits how fast it can charge.
6. Three parts of the brief do not fit cleanly as written: six separate speakers, six cameras running at once, and "visible nowhere" (a printed regulatory mark). The law expects a printed regulatory label. No law we found requires a recording light, but a hidden camera with no visible on-light will be read as spying. Section 12 gives the trade-offs.
7. Every number is either taken from a cited source or marked as our estimate.

## 2 What the owner asked for

Verbatim brief:

> "I WANT TO CREATE A HARDWARE DEVICE FOR THE EVENTUAL FINAL FORM FACTOR OF HELM LIKE A BLACK CUBE WITH A GLOWING, PULSATING LIGHT STRIP TO DENOTE SPEECH CADENCE, LISTENING AND VARIOUS OTHER LIKELY MODES ETC. CONNECTS TO WIFI W/ BLUETOOTH OF COURSE NO BUTTONS JUST A SHAKE TO WAKE AND TAPS TO CONNECT, CONTROL OTHER DEVICES(DIFFERENT NUMBERS OF TAPS FOR VARIOUS FUNCTIONS), QI SUPERCHARGING ONLY, HAS A COMPANION APP OF COURSE THE SMALLER THE CUBE THE BETTER ACCEPTABLE SIZES ARE ANYWHERE FROM PALM SIZE TO TENNIS BALL SIZE CAMERAS SPEAKERS AND MICROPHONES ON ALL SIX SIDES BUT VISIBLE NOWHERE"

## 3 The form

A **Qi pad** is a standard wireless charging pad. **Qi2** is the newer version, which uses a ring of magnets to snap the device into the right place.

| | **Target: 64 mm "tennis-ball" cube** | **Stretch: 55 mm "palm" cube** |
|---|---|---|
| Outside volume | 262 cc [E] | 166 cc [E] |
| Inside volume (2 mm walls) | 216 cc [E] | 133 cc [E] |
| Compared with a tennis ball (6.54–6.86 cm across [M, S69]; about 157 cc at 6.7 cm [E]) | Slightly narrower face to face (64 mm vs 65.4–68.6 mm), but 90.5 mm across a face diagonal and 110.9 mm corner to corner [E]; about 1.7× the volume [E] | About the same volume [E]; narrower |
| Weight | About 230 g with a plastic shell, 290 g glass, 460 g zirconia ceramic [E]. A tennis ball weighs 56.0–59.4 g [M, S69] | About 150–330 g [E] |
| Compared with HomePod mini (about 478 cc [E], from 84.3 × 97.9 mm [M, S16]) | About 55% of its volume [E] | About 35% [E] |
| Qi2 magnet ring (54–56 mm across [M, secondary, S37, S42]) | Fits inside 60 mm with 2–3 mm to spare per side [E] | Does not fit inside 51 mm [E] |
| Charging | Qi2 or Qi2 25W pad. About 14 W at first, likely falling to 7–10 W within about half an hour as the cube warms [E] | Plain Qi, no magnets. Qi v2.0 allows the Extended Power Profile (EPP) at up to 15 W without magnets, under the plain Qi logo [M, secondary, S40]. Heat limits it to about 5–8 W sustained [E] |
| Usable battery | About 13.5 Wh [E] | About 7.8 Wh [E] |
| Battery life on a typical day | About 10 days [E] | About 5.7 days [E] |
| Main brain | Linux-class processor (NXP i.MX 93) | Microcontroller (Infineon PSoC Edge E84 or Espressif ESP32-C6). HELM's core must be ported to C or Rust [E] |
| Speech | On the cube by default; phone as backup | On the phone |
| Cameras | 6 positions, one live at a time (Section 8) [E] | 1–2 low-power presence sensors [E] |
| Sound | 1 driver + 2 passive radiators | 1 smaller driver; voice quality only [E] |
| Heat it can shed while on the pad (5 faces) | About 3.7 W [E] | About 2.7 W [E] |

**Why 64 mm is the target:**
- It is the smallest size where the Qi2 magnet ring, a Linux-class board, a 17–21 Wh battery and a real speaker box all fit [E].
- It is close to a tennis ball's width face to face [M, S69].

**Why 55 mm is the smallest honest size:**
- At 55 mm the cube holds about a tennis ball's volume [E].
- Below that, the battery drops under about 10 Wh, the speaker's air box shrinks to almost nothing, and the charging coil fills the base [E].
- At 55 mm the owner gives up magnetic Qi2 charging, on-cube speech and most of the cameras.

**Shell:**
- The faces should be matte black glass, ceramic or plastic. Metal blocks both Qi charging and the radios [E].
- A matte black surface also sheds heat well by radiation, at an emissivity (how well a surface gives off heat) of about 0.9 [E].
- Corners should get a small radius, about 3 mm, for comfort in the hand and to reduce chipping when dropped. Glass and ceramic corners still chip on hard floors, so drop-test before choosing the shell [E].

## 4 Six faces

Face names: **C** = the charge face (one face, found by magnetic pull; nothing marks it), **O** = the face opposite it, and four side faces **S1-S4**. These names are for the builder only. From outside all six faces look the same, and in use "top" means whichever face points up.

| Face | Camera | Mic | Sound | What hides it |
|---|---|---|---|---|
| O | Yes, wide-angle | Yes, pinhole in an edge seam | The main driver sits behind this face and fires into a small cone. Sound leaves through hairline slots along the edges of every face [E] | Dark glass face. A black tube around the lens traps stray light. The slots read as the same shadow line on every edge |
| S1 | Yes, needs at least 90° across and 90° up-down | Yes, edge-seam pinhole | Sound port: the shared edge slots | Same dark glass. Black print with a small coated window over the lens |
| S2 | Same as S1 | Yes | Same as S1 | Same as S1 |
| S3 | Yes | Yes | Passive radiator 1 sits behind this face. It vents through the edge slots | Same as S1 |
| S4 | Yes | Yes | Passive radiator 2 faces radiator 1, so their shaking cancels [S19] | Same as S1 |
| C | **Yes** (owner ruling). Mounted in a corner beside the magnet ring; rests while docked [E] | **Yes**, edge-seam pinhole; rests while docked | Sound port: the shared edge slots (covered on one side while docked) | Same dark glass as every face. Inside: Qi coil, ferrite shield and magnet ring in the centre, the Hall-effect dock sensor, and the haptic motor nearby. The regulatory mark is an open choice (Section 12, item 6) |

**Cameras:**
- **Coverage.** To see everything around the cube, each camera must cover the whole view from its face: 90° across, 90° up-down, and 109.5° corner to corner on a square image [E, geometry]. The OV02C10 is 16:9 (1920 × 1080). A plain (rectilinear) lens that gives it 90° up-down needs about 121° across and 128° corner to corner [E]. The cameras sit on the faces, not at the centre, so add 10–20° of overlap to avoid blind gaps near the edges [E].
- **Stock lenses are too narrow.** A stock 5 × 5 × 3.2 mm module sees 68° corner to corner, 61° across and only 36° up-down [M, S7].
- **Custom lenses are needed.** A 120° lens housing measures 6.5 × 6.5 mm [M, S12]. We expect wide modules of about 6.5–8.5 mm [E].
- **Sensor.** OmniVision OV02C10: 1920 × 1080, 60 fps, with an always-on presence-sensing mode [M, S6]. It sends raw data only, so it needs an image processor (Section 8) [M, S6].

**Microphones:**
- **Part.** TDK T5838 is 3.5 × 2.65 × 0.98 mm. Its SNR is 68 dB [M, S1]. SNR (signal-to-noise ratio) measures how much louder a voice is than the mic's own hiss. It has a wake-on-sound mode at about 20 µA [M, S1, S2].
- **Ports.** Each mic sits behind a 0.5–1.0 mm pinhole [E], with a Gore waterproof membrane behind it. The membrane loses under 2 dB at 1 kHz with a 1.6 mm opening [M, S21]. Our pinholes are 0.5–1.0 mm, so the loss at that size is unmeasured. The T5838 is bottom-port, so each mic needs a through-board sound channel to its seam pinhole [M, S1]. The S21 datasheet link now returns 404.
- **Spacing.** On a 64 mm cube, mics on neighbouring faces sit about 45 mm apart, and mics on opposite faces 64 mm apart [E].
- **Steering limit.** An array of mics steers cleanly only below c/(2d), where c is the speed of sound and d is the spacing [S20]. Here that is about 3.8 kHz and 2.7 kHz [E]. That covers most of the telephone voice band (300–3,400 Hz); the close pair is needed above that [E].
- **Optional close pair.** One extra pair 15 mm apart extends steering to about 11.4 kHz [E].

**Speakers (why not six):**
- **The cube is small next to low notes.** Below about 1.7 kHz, a 64 mm cube is small compared with the sound wave. One source then spreads sound evenly in all directions anyway [E, from the ka < 1 rule in S18].
- **Six drivers would starve each other.** They would split a tiny air volume six ways. A micro speaker in a 1 cc box makes almost nothing below its 800 Hz resonance [M, S13].
- **What we recommend instead.** One driver of about 28–32 mm. Dayton CE32A-4 shows the size class: 32 mm square, 15.5 mm deep, resonance 262.1 Hz [M, S14]. Add two custom passive radiators of about 25–35 mm [E]. A **passive radiator** is a weighted cone with no motor: the air inside drives it, and it adds bass. The smallest stock radiator found is 2.2 in (about 56 mm) square and 1.5 in (about 38 mm) deep, which is too big [M, S15].
- **How the sound gets out.** It leaves through hidden edge slots on every side. Expect voice-class sound. The CE32A-4 reference has Xmax 0.5 mm and Vas 0.15 L [M, S14]. In the roughly 60–100 cc of free air left after the parts [E], a sealed box would put the bass roll-off near 410–490 Hz [E]. The radiators can lower that, but not to HomePod mini levels. The whole inside of the cube becomes the speaker's air box, so the mics, the battery pouch and any vents must be sealed off from it [E].

**Charge face and charger (owner ruling 1):**
- The Qi coil, ferrite and magnet ring take the centre of the charge face. Its camera and mic sit in corners beside the ring [E].
- **Finding it:** nothing on the outside marks it. Held near the charger, the magnet ring pulls that face down onto the puck.
- **Confirming it:** a linear resonant actuator (LRA), the small vibration motor phones use, gives one short pulse when charging starts. The edges show the charging pattern (Section 5). The same motor gives a tiny tick for each counted tap (Section 6) [E].
- **Knowing it:** a Hall-effect sensor feels the charger's magnets, so the cube knows it is docked without any contact [E]. The motion sensor knows which face points down.
- **While docked:** the charge face's camera and mic rest; the other five faces listen, watch and speak (owner ruling 2).
- The charger is a low puck under the cube (see the Drawing brief).

## 5 The light

**Where it sits (owner ruling 2: identical on all sides when off):**
- The light runs along **all twelve edges**. Each rounded edge (about 3 mm radius) is a strip of translucent black material over a light pipe. When off it matches the dark faces, so the cube reads as a plain black box; when lit, every face is framed the same way [E].
- This is a **dead-front** finish: the light cannot be seen until it is lit. A patent shows a translucent black bar about 1 mm thick that lets through 35–75% of light, with diffuser bumps over each LED [M, patent, S75]. A patent is not a shipping product; matching the edge strip's look to the face glass when off must be proven on a sample [E].
- **v0 used a band around the middle. That is withdrawn**, because a band marks a top and a bottom and breaks the plain-black-box rule.
- Each edge's light pipe needs a black baffle on its inner side so no light leaks into a camera behind a neighbouring face [E]. Mic pinholes and sound slots in the edges are routed around the light pipes [E].

**LEDs:**
- About 48 addressable RGB LEDs, four per edge, one about every 16 mm along 12 × 64 mm = 768 mm of edge [E]. More LEDs per edge give smoother motion at more power and cost.
- Example part: SK6805-E-J, 1.5 × 1.5 mm, about 18 mA per colour channel [M, secondary, S76].
- Full white on all 48 would draw about 2.6 A [E], so brightness is capped.
- Normal modes use 50–300 mW [E].
- LED power is cut by a switch while the cube sleeps, because these LEDs draw roughly 0.5–1 mA each even when dark. For 48 LEDs that is about 90–180 mW, several times the whole asleep budget [E]. Check their minimum supply voltage against a 3.0–4.2 V cell.

**Camera-on dots:**
- Each face has its own tiny dead-front dot at its centre, the same on all six faces and invisible when off, so the plain-black-box rule holds [E].
- **Green is reserved for "camera on" and is used nowhere else.**
- The camera's own power line drives the dot (Section 9).

**Mode table:** colours and timings are all [E] design choices. Each mode can be told apart by its motion alone, which helps colour-blind users.

| Mode | HELM state | Colour | Motion |
|---|---|---|---|
| Asleep | — | Off | None. An optional 2% "presence glow" can be set in the app |
| Awake | After a shake | Soft white | One sweep along all twelve edges, then dim |
| Listening | Mics live | Cyan | The edges nearest the person speaking glow brighter, using mic direction. They ripple faintly with the speaker's voice level |
| Thinking | Parsing, RPM gate check | Gold | Two points of light travel along the edges. Shown only if thinking takes over 300 ms |
| **Speaking (speech cadence)** | Voice output | Warm white | Brightness follows the loudness of HELM's voice: 30–50 ms rise, 100–150 ms fall. So it pulses with each syllable, about 4–5 per second in normal speech [E] |
| Asking a question | `CLARIFY_REFUSAL`, `STORE_CLARIFY` | Violet | Short, short, long, every 2 s; then listening opens |
| **Missing input** | `UNDETERMINED` (`G-ABSENT`, `G-LIMIT`) | Amber on every edge but one | The one dark edge pulses slowly. The lit frame is the recipe; the dark edge is the missing input. HELM says aloud which input is missing |
| Declined | `*_REFUSAL`, `GATE_REFUSE` | Dim amber | The lit edges shrink to one edge and fade. It is not red, because red means privacy |
| Privacy, soft | 5-tap mute (firmware) | Red | Slow breathing |
| Privacy, hard | Gravity switch open | Red | Steady. Powered through the hardware switch itself |
| Camera on | Any camera powered | Green dot on that face | Steady. Hardware-wired |
| Charging | On the Qi pad | Soft white | One haptic pulse on snap-on (owner ruling 1). The number of lit edges shows the charge level (each edge about 1/12) for 5 s, then goes dark |
| Low battery | 15% or less / 5% or less | Orange | 1 blink / 2 blinks every 10 s |
| Pairing | Setup window open | Blue | A chase along the edges; fewer edges stay lit as the window runs out |
| Device acknowledged | Tap on a bound face | That device's colour (never green or red) | A brief flash on the face that was tapped |
| Error | No network, or speech service down | Orange | Two blinks, then dim steady. Kept separate from `UNDETERMINED`, which means missing information, not a failure |
| Eye report | Unity Eye filed a report | Teal | One small blip. It means "a report is in the app". It never implies the Eye acted |
| Updating | Firmware update | White | Slow chase along the edges |

Amazon Echo uses blue for listening, red for mic off, orange for setup and yellow for notifications [M, secondary, S78]. Our red for privacy matches Echo. Our blue for pairing and orange for errors do not: an Echo owner will read blue as "listening" and orange as "setting up". Either move pairing to orange and errors to another colour, or drop the claim that we follow Echo. Sources also report Echo purple for Do Not Disturb or a Wi-Fi failure, which overlaps our violet [E].

## 6 Touch without buttons

**Sensors:**
- An **IMU** is a motion sensor that measures movement and tilt.
- **Always on: Analog Devices ADXL367 accelerometer.** It draws 180 nA in motion-wake mode and 40 nA in standby. It detects single and double taps for 35 nA more, but only along one axis chosen in its TAP_AXIS setting, and it does not report which face was struck. Below a 1 g tap threshold, tilting can also register as a tap [M, Rev. 0 datasheet copy, S74].
- **Only while awake: a 6-axis IMU.** Option one is the Bosch BMI323, which has single, double and triple tap built in and is 2.5 × 3.0 × 0.83 mm [M, S70]. Option two is the ST LSM6DSV16X [M, secondary, S72].
- **Finding which face was tapped.** ST's tap register reports the axis and the sign of the blow [M, secondary, S73]. Combined with gravity (which face is down), that gives the face [E]. This register is on the ST LSM6DSV16X only. With the Bosch BMI323, the face must be read from the raw motion data [E].
- **Counting taps.** Four or five taps are counted in software, not by the sensor [M, secondary, S73]. While the cube sleeps, the ADXL367 wakes the processor and holds the raw motion in its FIFO until counting can start (Section 8) [E].
- **No compass sensor.** Qi2 magnets would distort it [E].

**Timing, as starting values to tune [E]:**
- Each tap's impulse lasts 40 ms or less.
- The gap between taps is 100–450 ms.
- A sequence ends after 600 ms of quiet.
- A shake opens an 8 s attention window.

**Tap grammar.** The number of taps is the verb. The face is the target. "Top" means whichever face points up at that moment (the motion sensor knows); it means HELM itself. The side faces mean devices bound in the app, counted around from the charge face, so a binding stays with the same physical face however the cube is set down [E]. A counted tap gets a tiny haptic tick.

| Gesture | Face | When | Normal action | While HELM is asking a question |
|---|---|---|---|---|
| Shake (2 bursts within about 1 s, then still) | Any | Always | Wake and listen | Drop the question. It stays `UNDETERMINED` |
| 1 tap | Top | Awake | Stop / hush | Yes |
| 2 taps | Top | Awake | Repeat the last answer | No |
| 2 taps | Bound side face | Awake | Toggle that device on or off | Not accepted |
| 3 taps | Top | Awake | Run a favourite scene | Repeat the question |
| 3 taps | Bound side face | Awake | Next step for that device (brightness, track, scene) | Not accepted |
| 4 taps | Top | Awake, then confirm by voice or in the app | **Tap to connect:** open the Bluetooth and Matter pairing window | Not accepted |
| 5 taps | Top face while asleep (the always-on sensor watches the up-down axis only); any face while awake | Always | Soft privacy ON | Soft privacy ON |
| Shake, then 5 taps | Any | Awake | Soft privacy OFF after a 3 s countdown (1 tap cancels) | — |
| Set it down with the charge face pointing up (lift it off the charger and flip it) | — | Always | Hard privacy (Section 9) | Hard privacy |
| Phone held to the cube | — | Setup | NFC setup, a feature of Matter 1.4.1 [M, S79] | — |

**Rules:**
- **Taps never supply a missing fact.** They can only say yes, no, repeat, skip or stop. A skipped question stays `UNDETERMINED`.
- **Taps never unlock doors, disarm alarms, or open garages or gates.** Matter 1.5 adds gates and garage doors as device types [M, S79]. Those actions need voice plus confirmation in the app.

**How false taps are rejected [E]:**
1. Taps count only inside the attention window after a shake. The privacy gesture is the one exception, because it only makes the cube safer.
2. A cube resting on a table cannot be tapped on its bottom face. So a blow coming up from below is a table knock, not a tap.
3. A free fall or a large rotation means the cube was dropped or lifted. Tap counting pauses for 1 s.
4. **Pocket guard.** A shake wakes the mics only if 300 ms of stillness follows it. If the cube keeps moving, as in a bag, it stays asleep.
5. When the mics are live, a tap must also make a matching knock sound.
6. An unclear sequence, such as a gap right on the timing limit, is **not counted**. The cube flashes "not counted", logs it in the app, and never guesses whether you meant 2 or 3.
7. Each counted tap shows a brief tick on the face that was struck.
8. The two passive radiators face each other, so their shaking cancels. The main driver is not balanced. It shakes the cube along the up-down axis, the same axis as a tap on the top face. While HELM speaks, a top-face tap must be checked against the known speaker signal, or "1 tap = stop" will be missed or fire by mistake [E].

A Bosch engineer warns that tap signals can fire on vibration or on the device rubbing a surface [M, qualitative, S71]. Rules 2–5 address that.

## 7 Power and heat

**The Qi standard:**
- **Qi2** charges at 15 W, and **Qi2 25W** at 25 W [M, S39]. The Qi2 25W release calls it "nearly 70% more" power than Qi2 [M, S38].
- The Qi2 logo requires built-in magnets. The "Qi2 Ready" label, introduced in January 2025, covers devices that get their magnets from a case [M, secondary, S40].
- "Supercharging" is not a WPC (Wireless Power Consortium) term. The correct name is "Qi2 25W".
- The magnet ring's exact size is in IEC 63563-10:2025, a paid standard [M, S41]. Check it before the size is fixed.
- IEC 63563-10:2025 is "Qi Specification version 2.0 – Part 10: MPP System Specification". The spare MagSafe ring assembly includes a separate alignment magnet [S42]. If the standard requires one, place it in a corner of the bottom face [E].
- **64 mm cube:** Qi2 magnetic profile. About 14 W at first, likely falling to 7–10 W within about half an hour as the cube warms [E]. 25 W only as a short burst when the battery is empty, then heat forces it lower [E].
- **55 mm cube:** Plain Qi, no magnets. Qi v2.0 allows the Extended Power Profile (EPP) at up to 15 W without magnets, under the plain Qi logo, not Qi2 [M, secondary, S40]. Heat, not the standard, sets the limit: about 5–8 W sustained at 55 mm [E]. The 29 × 29 mm Würth coil (7.9 µH, 1.7 A, 330 mΩ max DC resistance [M, secondary, S44]) would itself turn about 1 W into heat at its rated current [E]. A shallow square dish helps alignment [E]. No magnetic snap and no Qi2 logo.

**Coil examples** (secondary, from distributor listings):
- Würth 760308102213: 29 × 29 mm square, 7.9 µH, 1.7 A, 330 mΩ max DC resistance. Listings disagree on thickness: 0.62 mm or 0.9 mm [M, secondary, S44].
- Würth 760308103305: 44 × 45 × 0.72 mm, 8.8 µH, 5 A [M, secondary, S44]. It is listed as no longer stocked at one distributor.

**Battery [E]:**
- Pouch cells hold 600–750 Wh/L. Phone-class cells reach about 835 Wh/L [M, secondary, S45]. Enovix AI-1 reaches 935 Wh/L [M, vendor test, S45].
- Usable energy is taken as 80% of the low end of the range.

| Cube | Pouch | Energy | Usable |
|---|---|---|---|
| 64 mm | 53 × 53 × 10 mm (28.1 cc) | 16.9–21.1 Wh | About 13.5 Wh |
| 55 mm | 45 × 45 × 8 mm (16.2 cc) | 9.7–12.2 Wh | About 7.8 Wh |

**Power by state:**

| State | Main contributors | Power |
|---|---|---|
| A. Asleep (mics off by default, motion sensor on, Wi-Fi kept connected) | i.MX 93 deep sleep 7.6 mW [M, S57]; memory, power chips and fuel gauge 2.5–6 mW [E]; Wi-Fi 6 keep-alive: Silicon Labs claims as low as 20 µA for its SiWx917 modules, with TWT and a 60 s keep-alive [M, vendor, S50]. That is not the IW612. NXP publishes no power figure for the IW612 [M, S53], so budget 2–10 mW until measured [E]. A 60 s keep-alive also means the app may wait up to a minute to reach a sleeping cube [E]; BLE idle link 0.1–0.5 mW [E] | **About 11–25 mW [E]** |
| A+. Optional voice wake word | Syntiant NDP120 under 280 µW [M, S61]; 2 mics in low-power mode | Adds about 1 mW in a quiet room [E]. In a noisy home it costs more, because every false trigger wakes the main processor for a second or more at about 1 W [E] |
| B. Listening, speech recognised on the cube | i.MX 93 stand-ins from NXP's EVK tests (processor rails only; memory measured separately): eIQ benchmark 725.5 mW, Dhrystone 805.9 mW, audio playback 458.6 mW, NXP "Smart doorbell" case 772.1 mW [M, S57]. None of these is speech recognition [E]; memory 100–200 mW [E]; light 50–150 mW [E] | **About 0.9–1.3 W [E]** |
| C. Speaking, light pulsing | Processor 700–900 mW [M stand-in, S57]; amplifier MAX98357A (3.2 W max into 4 Ω at 5 V [M, S64]) averaging 0.2–0.6 W [E]; light 100–300 mW [E] | **About 1.1–1.9 W [E]** |
| D. Speech sent to the phone instead | Main processor parked; audio sent over BLE | About 50–150 mW [E] |
| E. Camera in use | i.MX 93 "machine vision" 780.5 mW [M, S57] plus a sensor at 100–250 mW [E] | **About 0.9–1.1 W [E]** |
| Mistake to avoid | Linux left idling, 199.9 mW [M, S57] | — |
| Mistake to avoid | M33 kept awake while Linux sleeps: "Linux Suspend + M33 in WFI" 122.4 mW [M, S57]. Typical life would drop from about 10 days to about 3.3 days [E] | — |

TWT (Target Wake Time) is a Wi-Fi 6 feature that lets the cube sleep between scheduled check-ins.

**Battery life [E].** Usage model: each turn is 15 s at 1.5 W; the camera runs at about 1 W; asleep is about 20 mW.

| Usage | Energy per day | 64 mm | 55 mm |
|---|---|---|---|
| Asleep and connected only | 0.48 Wh | About 28 days | About 16 days |
| Light: 30 turns, 5 min of camera | About 0.75 Wh | About 18 days | About 10 days |
| Typical: 100 turns, 15 min of camera | About 1.36 Wh | About 10 days | About 5.7 days |
| Heavy: 300 turns, 60 min of camera | About 3.36 Wh | About 4.0 days | About 2.3 days |
| Talking nonstop at 1.5 W | — | About 9 h | About 5.2 h |
| Linux left idling | — | About 67 h | About 39 h |

Battery life depends mostly on how low the asleep state goes, not on where speech is processed [E].

**Heat while charging:**
- **How much heat it can shed.** Heat shed = h × area × ΔT, with h about 10 W/m²K [E]. Sources give 1–25 W/m²K for still air [M, S47]. ΔT is 18 K, from 25 °C room air to a 43 °C surface [E]. With one face on the pad, 5 faces shed heat: about **3.7 W at 64 mm** and **2.7 W at 55 mm** [E].
- **Touch limit.** A UL brief on IEC 62368-1 gives 48 °C for plastic or metal touched for more than 1 minute [M, S46]. We design to 43 °C, because people hold this cube [E]. Check the current edition of the standard (the UL brief is based on the 2010 first edition, Table 42).
- **Battery limit.** A typical charger chip, TI BQ25618E/BQ25619E (one datasheet covers both [S48]), reduces charging above a 45.5 °C warm point by default. That point is programmable from 40 to 54.5 °C. It has a 10 °C cool point [M, S48]. It stops charging below 0 °C and above 60 °C [M, S48]. It is a 1.5 A charger, about 6 W into one cell, so it is a temperature reference only. The real charger must handle about 3.5–4 A for 14 W [E]. Inside a sealed cube, this battery limit is the one that actually stops charging [E].
- **Charging and talking share one heat budget.** About 14 W reaching the battery costs roughly 2.5–3 W of heat inside the cube, from the receiver coil, rectifier, charger chip and battery [E]. The pad's own coil also warms the bottom face. In a 25 °C room that uses most of the 3.7 W budget before HELM does anything. In a 30 °C room the budget falls to about 2.7 W [E]. The 3.7 W figure assumes an evenly warm surface. Real cubes have hot spots, so treat it as an upper limit [E]. Add talking at 1.5 W and the total exceeds the budget. Firmware must therefore cut the charge rate while HELM talks or a camera runs [E].
- **Time to 80%** at 64 mm: about 80–110 min [E].
- **Shipping.** The charger chip's "ship mode" keeps the cube off in the box. Setting it on a Qi pad wakes it [E].

## 8 Brains and radios

**Two brains [E]:**
- A tiny always-on part watches for a shake or a tap.
- The main processor wakes only when needed.

| Job | Where | Notes |
|---|---|---|
| Shake and tap detection | ADXL367 alone while asleep. It wakes the i.MX 93 by interrupt and keeps the raw motion in its FIFO until the processor is up | Well under 0.01 mW asleep [M, S74]. Do not keep the M33 awake for this job. NXP measured "Linux Suspend + M33 in WFI" at 122.4 mW, against 7.6 mW in deep sleep with the M33 held in reset [M, S57]. If a processor must count taps while the cube sleeps, use a separate tiny microcontroller, such as the nRF54L15 [S82] [E]. |
| Optional voice wake word | NDP120 or the M33 | Off by default (Section 9) |
| HELM recipe brain: fractions, RPM gate, Unity Eye reports | Main processor, Linux | Tiny compute [E]. Python today, so it needs Linux |
| Speech to text | On the cube: Moonshine Tiny, 27M parameters [M, S65] | Licence: MIT for code and models, except the legacy non-streaming non-English models, which use the non-commercial Moonshine Community License [M, S65]. Speed on these cores is **not measured** anywhere we found |
| Text to speech | On the cube: Kokoro, 82M parameters [M, S66]; or Piper [M, S67] | Kokoro's code and weights are Apache-2.0, but it uses espeak-ng for English words outside its dictionary [M, S66]. espeak-ng is GPL-3.0 [check]. Piper is GPL-3.0 [M, S67]. Both need a licence review before shipping. Kokoro (82M) is likely slower than real time on two A55 cores [E]. Plan a Piper-class voice for on-cube speech until FRDM-IMX93 measurements exist. |
| Light and speech cadence | M33 core | Driven by the speech loudness |
| Device control | Cube radio over Matter or Thread | Section 6 safety rules apply |
| Setup, device binding, receipts, open questions | Phone app | Section 10 |
| Speech fallback | Phone | When the cube is hot or the battery is low |
| Cloud | Nothing required | Firmware updates; opt-in backup only [E] |

**Chip class (64 mm):**
- NXP i.MX 93, dual-core part i.MX 9352 [check]: two Cortex-A55 cores at 1.7 GHz, a Cortex-M33 at 250 MHz, and an Ethos-U65 AI accelerator, with a 9 × 9 mm package option [M, S56]. The accelerator is rated 0.5 TOPS [M, secondary, S56]. Single-core family members exist, so the part number must be named on the order.
- Measured: 7.6 mW in deep sleep, 1264.1 mW at full stress, processor chip only [M, S57].
- Memory: 1–2 GB [E].
- At 8-bit precision the speech models take about 27 MB and 82 MB [E]. Neither fits the 5 MB of on-chip memory in a microcontroller [M, PSoC Edge E84, S51]. That is why the 55 mm cube sends speech to the phone.

**Camera input limit (important):**
- The i.MX 93 has one 2-lane MIPI CSI-2 input rated for 1080p60, plus one 8-bit parallel YUV/RGB input [M, S56]. It has no hardware ISP. An ISP (image signal processor) is the block that turns raw sensor data into a normal picture [M, secondary, NXP community reply; S56 lists none]. The OV02C10 sends raw data only [M, S6]. So the cube needs one of three things: sensors with a built-in ISP and YUV output, an external ISP chip (for example onsemi AP1302), or a slow software ISP running on the A55 cores. This choice must be made before the board is laid out [E].
- MIPI CSI-2 is the standard wire link between a camera and a processor.
- So six cameras must **take turns** through a switch [E]. The cube would pick the face where the voice came from, or where motion was seen.
- Running five cameras at once needs a phone-class chip such as the Qualcomm QCS6490 (at most 5 at once [M, S36]). That chip runs hotter and has no published power figure. Section 12 covers this choice.
- **55 mm presence sensors.** The ESP32-C6 has no dedicated camera port [check datasheet]. A camera interface on the PSoC Edge E84 is unconfirmed; S51 lists only a display interface. The HM0360 sends 1-, 4- or 8-bit parallel or 1-lane MIPI data [M, S9]. Confirm the chosen chip can take one of these.

**Radios:**
- **64 mm:** NXP IW612. Wi-Fi 6 on 2.4 and 5 GHz, Bluetooth LE 5.4 and 802.15.4 for Thread and Matter. NXP already pairs it with the i.MX 93 on the FRDM-IMX93 board [M, S53, S55].
- **55 mm:** ESP32-C6. Wi-Fi 6 on 2.4 GHz only, BLE 5.3 and 802.15.4 [M, S49]. Another option is the Infineon CYW55513, which does not list 802.15.4 [M, S52].
- **Wi-Fi 7 is skipped for version 1.** A voice cube does not need the speed, and the one Wi-Fi 7 combo chip found (Synaptics SYN4390) has no published power numbers [M, S59].
- **Matter** is the shared standard for smart-home devices. The cube joins the user's existing home system (Apple Home, Google Home, SmartThings or Alexa) as one more controller, using Matter "multi-admin" [E, S80].
- **Thread** is a low-power mesh radio used by many Matter devices. It needs a **border router**, a box that bridges Thread to Wi-Fi. Apple TV, Nest, some Echo models and IKEA DIRIGERA already include one [M, secondary, S81]. Version 1 relies on the user's existing border router [E]. The cube reaches Thread devices through that border router over Wi-Fi, so its own 802.15.4 radio can stay off while on battery. Joining Thread directly as a router would keep a receiver on all the time and break the asleep power budget [E].
- **Antennas.** A quarter-wave antenna at 2.4 GHz is about 31 mm long, so chip antennas fit. They need non-metal windows in the shell [E].

## 9 Privacy

**Principle:** hide the lenses, but never hide whether they are on. Airbnb banned all indoor cameras from 30 April 2024, even disclosed ones [M, S85]. Hidden cameras will be read as spying unless their on-state is plain.

1. **Mics are off while asleep.** Shake to wake means no always-listening is needed. A voice wake word is opt-in and processed on the cube only [E].
2. **Cameras are off by default.** They turn on only when asked ("look at this"). Every power-on is logged in the app from a hardware status line [E].
3. **The camera light is wired in hardware.** Each camera's power line drives its own green face dot. Software cannot power the camera without lighting the dot [E].
   - Why: older Mac camera lights were turned off by reprogramming the camera's chip [M, S30].
   - A tiny light sensor beside each dot cuts that camera's power if the dot looks covered [E]. This makes covering harder, not impossible: a sticker beat a similar check on Meta's glasses [M, S31]. The circuit should also sense the dot's own current and cut the camera if the LED fails [E].
4. **Hard mute without a button. Pick one [E, untested]:**
   - (a) **Gravity switch.** Set the cube down with its charge face pointing up (the face that snaps to the charger), and a tilt switch opens the mic and camera power lines. Nothing on the outside shows which face that is, so the user learns it from the charger. It needs vibration testing.
   - (b) **Magnetic privacy puck.** A hidden magnetic switch cuts power when a puck touches the cube. It must sit away from the Qi2 magnet ring so the ring cannot trigger it.
   - In both, the steady red privacy light is powered through the switch itself.
5. **Soft mute** (5 taps) is firmware only. The app and the light label it honestly as "soft".
6. **No face recognition by default.** Illinois BIPA (Biometric Information Privacy Act) requires written consent first. A lawsuit over Arlo person detection survived a motion to dismiss [M, S33].
7. **Cameras are never shared with other Matter devices by default** [E].
8. **Law (not legal advice; have a lawyer review it):**
   - About 11 US states require everyone recorded to consent [M, S32]. A light gives notice. It is not consent.
   - In the EU, the household exemption ends when a camera sees public space (Ryneš, C-212/13) [M, S34].
   - The EU AI Act, Article 50(1), requires telling people they are talking to an AI [M, S35]. It has applied since 2 August 2026 [M, secondary, S35].
   - Our search found no law requiring a recording light on a home assistant. That finding is only as wide as the search.

## 10 Companion app

1. **Now:** awake or asleep, battery and charging, and privacy state (HARD / SOFT / OFF) read from hardware status lines. Also the last answer and its `receipt_hash`.
2. **Conversation and receipts:** each turn with its HELM status (`EVALUATED`, `UNDETERMINED`, `CLARIFY_REFUSAL`, `*_REFUSAL`), its gate code, the missing input and the receipt.
3. **Open questions:** every pending `UNDETERMINED` item, answered by typing. Nothing is ever filled in automatically.
4. **Gestures:** a 3D face map, a tap-count × face editor, a practice mode, a sensitivity setting, and a list of rejected bumps.
5. **Devices and scenes:** add devices by Matter QR code or NFC, bind devices to faces. Locks, alarms and gates are blocked from taps.
6. **Light:** the mode legend, brightness, night dimming, the presence glow, and patterns for colour-blind users.
7. **Privacy and data:** per-face camera and mic switches, a log of every power-on, retention and delete controls, on-cube vs phone speech, and face recognition (off; opt-in needs written consent).
8. **Unity Eye reports:** labelled "The Eye reports; it does not act."
9. **Setup, updates and regulatory info:** this adds to the label on the cube. It does not replace it.

## 11 Parts table with sources

| Role | Part (maker) | Key numbers | Tag | Fit | Source |
|---|---|---|---|---|---|
| Mic, first pick | T5838 (TDK InvenSense) | 3.5 × 2.65 × 0.98 mm; SNR 68 dB; overload limit 133 dB; wake-on-sound about 20 µA; bottom port | [M] | Good | S1, S2 |
| Mic, alternative | IM69D130 (Infineon), order code IM69D130V01XTSA1 | 4 × 3 × 1.2 mm; SNR 69 dB(A); 1.3 mA | [M, distributor] | Quieter, more power | S3 |
| Mic, low-power | IM69D129F (Infineon) | 170 µA in low-power mode; 450 µA in high-performance mode | [M, secondary] | Good | S63 |
| Mic, reference | SPH0655LM4H-1 (Knowles) | 3.50 × 2.65 × 1.08 mm; SNR 66 dB | [M, distributor] | Acceptable | S5 |
| Camera sensor | OV02C10 (OmniVision) | 1920 × 1080, 60 fps; presence-sensing mode; 8-bit or 10-bit RGB RAW output only, so it needs an ISP | [M] | Best fit, if an ISP is added | S6 |
| Camera module, example | AE-CCM-OV02C10-C-61 (Appleye) | 5 × 5 × 3.2 mm; 68° corner to corner, 61° across, 36° up-down | [M] | Too narrow | S7 |
| Presence sensor | HM0360 (Himax) | 640 × 480; 7 mA at 60 fps; 50 µA watch mode; 1-, 4- or 8-bit parallel or 1-lane MIPI output | [M, preliminary datasheet] | 55 mm cube | S9 |
| Wide lens, reference | 120° housing (Waveshare listing) | 6.5 × 6.5 mm | [M] | Size reference | S12 |
| Main driver, size reference | CE32A-4 (Dayton Audio) | 32 mm square, 15.5 mm deep; resonance 262.1 Hz; 2 W; Xmax 0.5 mm; Vas 0.15 L | [M] | Custom 28–32 mm likely [E] | S14 |
| Passive radiator | DMA58-PR (Dayton) | 2.2 in (about 56 mm) square, 1.5 in (about 38 mm) deep | [M] | Too big; custom 25–35 mm [E] | S15 |
| Micro speaker | AS01508AO-3-SC-R (PUI Audio) | 15 × 11 mm; resonance 800 Hz in a 1 cc box | [M] | Only if "six speakers" is kept | S13 |
| Amplifier | MAX98357A (Analog Devices) | 3.2 W into 4 Ω at 5 V; 92% efficient at 1 W. From a 3.7 V cell with no boost converter, about 1.7–1.8 W [E, scaled by V²] | [M] | Good | S64 |
| Mic vent | GAW334 (Gore) | Under 2 dB loss at 1 kHz; 1.6 mm opening (loss at 0.5–1.0 mm unmeasured) | [M] | Good | S21 |
| Shake sentry | ADXL367 (Analog Devices) | 180 nA motion wake; single and double tap on one chosen axis only; 2.2 × 2.3 × 0.87 mm | [M, Rev. 0 copy] | Good | S74 |
| Tap and orientation IMU | BMI323 (Bosch) | Single, double and triple tap; 790 µA; 2.5 × 3.0 × 0.83 mm | [M] | Good | S70 |
| Tap and orientation IMU, alternative | LSM6DSV16X (ST) | 0.65 mA | [M, distributor] | Good | S72 |
| Low-power accelerometer, alternative | BMA400 (Bosch) | Tap detection under 8 µA | [M] | Good | S62 |
| Sleep-time tap counter, option | nRF54L15 (Nordic) | Separate tiny microcontroller, only if taps must be counted while the cube sleeps | [E] | Option | S82 |
| Wake word | NDP120 (Syntiant) | Under 280 µW | [M, vendor] | Optional | S61 |
| Main processor | i.MX 93 (NXP), dual-core part i.MX 9352 [check] | 2× A55 at 1.7 GHz; M33; Ethos-U65; deep sleep 7.6 mW; maximum 1264.1 mW; 1 two-lane MIPI CSI-2 input (1080p60) plus 1 8-bit parallel YUV/RGB input; no hardware ISP | [M] | 64 mm cube | S56, S57, S58 |
| Processor + radio in one package | i.MX 93W (NXP) | Wi-Fi 6, BLE, 802.15.4 in the package; pre-production | [M] | Watch | S54 |
| Microcontroller | PSoC Edge E84 (Infineon) | M55 at 400 MHz + Ethos-U55; 5 MB SRAM; camera interface unconfirmed | [M] | 55 mm cube | S51 |
| Radio | IW612 (NXP) | Wi-Fi 6 dual-band, BLE 5.4, 802.15.4; no published power figure | [M] | 64 mm cube | S53 |
| Radio, small | ESP32-C6 (Espressif) | Wi-Fi 6 at 2.4 GHz; 802.11ax receive 78 mA, transmit 252 mA | [M] | 55 mm cube | S49 |
| Phone-class processor | QCS6490 (Qualcomm) | 12 TOPS; at most 5 cameras at once | [M] | Only if cameras must run at once | S36 |
| Edge LED | SK6805-E-J | 1.5 × 1.5 mm; about 18 mA per channel | [M, secondary] | Good | S76 |
| Edge LED, alternative | IN-PI15TAT5R5G5B (Inolux) | 1.5 × 1.5 mm | [M, distributor] | Good | S77 |
| Haptic motor (owner ruling 1) | A small linear resonant actuator (LRA); part not chosen | Phone-class size; one pulse on snap-on, a tick per counted tap | [E] | Needs a part pick and a check that its buzz does not register as a tap | — |
| Dock sensor (owner ruling 1) | A Hall-effect magnetic switch; part not chosen | Feels the charger's magnets; must not be tripped by the cube's own Qi2 ring or the speaker magnet | [E] | Placement test needed | — |
| Qi coil | 760308102213 (Würth) | 29 × 29 mm square, 7.9 µH, 1.7 A, 330 mΩ max DC resistance. Listings disagree on thickness: 0.62 mm or 0.9 mm | [M, secondary] | 55 mm cube | S44 |
| Charger chip, temperature reference | BQ25618E/BQ25619E (TI) | Warm point 45.5 °C by default, programmable 40–54.5 °C; cool point 10 °C; 1.5 A charger (about 6 W) | [M] | Temperature reference only; the real charger must handle about 3.5–4 A for 14 W [E] | S48 |
| Camera cover glass | Gorilla Glass DX (Corning) | 98% of light passes | [M, maker claim, 2021] | Window option | S24 |
| NFC setup tag | NFC tag holding the Matter onboarding data (part not chosen) | Needed for "phone held to the cube" setup; Matter 1.4.1 adds "Onboarding Info in NFC Tag" [M, S79] | [E] | Keep its antenna away from the Qi coil and magnets | S79 |

## 12 What is hard or may not fit

1. **Six cameras running at once, and raw-only sensors.** The i.MX 93 has one 2-lane MIPI CSI-2 input rated for 1080p60, plus one 8-bit parallel YUV/RGB input [M, S56]. It has no hardware ISP. An ISP (image signal processor) is the block that turns raw sensor data into a normal picture [M, secondary, NXP community reply; S56 lists none]. The OV02C10 sends raw data only [M, S6]. So the cube needs one of three things: sensors with a built-in ISP and YUV output, an external ISP chip (for example onsemi AP1302), or a slow software ISP running on the A55 cores. This choice must be made before the board is laid out [E].
   - Choice A: cameras take turns. This is cooler and cheaper, but only one face sees at a time.
   - Choice B: a phone-class chip runs 5 at once [M, S36]. It is hotter, has no published power figure, and a sixth camera still needs extra hardware.
2. **Wide lenses.** Full coverage needs about 90° × 90° per face, 109.5° corner to corner on a square image [E]. On the 16:9 OV02C10, a plain lens needs about 121° across and 128° corner to corner, plus 10–20° of overlap [E]. Stock modules are too narrow. Custom lenses grow modules to about 6.5–8.5 mm [E].
3. **Hiding cameras costs light.** Dark acrylic passes 27% or 12% of light [M, S23]. That is 1.9–3.1 f-stops, and each stop halves the light [E], so video gets noisy in dim rooms.
   - A clear coated window loses about 2% [M, S24] but can be seen up close.
   - Under-display cameras are the worst option. Samsung itself notes haze and flare [M, S26].
4. **Six speakers.** Six separate drivers do not fit usefully in this volume [E]. One driver plus two passive radiators, with sound leaving through hidden slots on the edges of all six faces, gives sound in every direction and keeps every face looking the same. Expect voice-class sound, with far less bass than HomePod mini. Six micro speakers remain possible if the owner prefers them (Section 13).
5. **"Qi supercharging".**
   - Qi2 25W exists [M, S38], but heat limits a 64 mm cube to about 14 W at first, likely falling to 7–10 W within about half an hour [E].
   - At 55 mm the magnet ring does not fit, so charging is plain Qi (Qi v2.0 EPP allows up to 15 W without magnets [M, secondary, S40]; heat limits it to about 5–8 W sustained [E]).
   - The ring size (54–56 mm) is only from secondary sources [S37, S42]. It must be checked against IEC 63563-10.
   - Whether a non-phone device can carry the Qi2 25W logo is not confirmed.
6. **"Visible nowhere" against the law.**
   - The FCC ID must be on the device (47 CFR 2.925) [M, S89]. The fallback to the user manual plus the packaging or a removable label (47 CFR 2.925(f)) applies only below 4-point type with no display. A 64 mm cube must carry the FCC ID. The owner's rule is a plain black box, so the best fit is a tone-on-tone laser etch (black on black, about 1 mm text) on the charge face, readable only up close at an angle [E]. Electronic labelling in the app is allowed only for devices with a built-in display, which the cube does not have [E, check 47 CFR 2.935]. This is an owner choice (Section 13).
   - The EU crossed-out-bin mark goes on the device. Where size or function prevents that, it goes on the packaging, the instructions and the warranty (WEEE Directive 2012/19/EU, Art. 14(4)) [check]. The 7 mm minimum height (EN 50419) is unconfirmed; the page cited as S94 does not state it.
   - The camera-on light must be visible (Section 9).
7. **No buttons against a true mute.** A hardware mute needs the gravity switch or a magnetic puck. A tap mute is only "soft".
8. **Sealed cube against EU battery law.** From 18 February 2027, users must be able to remove portable batteries (Regulation 2023/1542, Art. 11) [M, S92]. Applying this to the cube is our inference. An EU version needs a user-openable base.
9. **Radio exposure.** Module approvals often assume 20 cm separation. A handheld cube needs its own SAR/MPE evaluation, which measures radio energy absorbed by the body [M, S87]. A 25 W charger puck exceeds the 15 W limit of the FCC wireless-charger exclusion (KDB 680106) [M, S88]. The conclusion that the puck needs full evaluation is our inference. The exclusion also needs the device in direct contact with the pad, and it covers mobile (not handheld) exposure only [M, secondary, test reports citing v03]. Version 1 should use an already-certified Qi2 25W puck, not a custom one [E].
10. **On-cube speech speed is unmeasured.** No published figures exist for Moonshine plus Kokoro or Piper on two A55 cores. Testing needs a dev board such as the FRDM-IMX93 [S55]. AWS ARM servers are not a faithful stand-in [E].
11. **Heat is shared.** The cube cannot charge fast and talk at the same time [E].
12. Security, safety and certification rules are not yet in the plan. In the EU, the Radio Equipment Directive cybersecurity rules (EN 18031) have applied to internet-connected radios since 1 August 2025. Cyber Resilience Act vulnerability reporting has applied since 11 September 2026 [M, secondary, S90, S91]. In the UK, the PSTI Act bans default passwords and requires a stated update period, since 29 April 2024 [source to add]. The battery needs IEC 62133-2 and UN 38.3 tests [S95]. Budget for Qi (WPC), Matter (CSA) and Bluetooth SIG certification [S96–S98]. If children may talk to it, COPPA covers stored voice recordings. The FTC acted on Alexa recordings in 2023 [source to add]. Set a water target now, for example splash resistance, because the edge slots, the pinholes and the light seam all need sealing [E].

## 13 Open questions for the owner

1. Size: 64 mm with Qi2 magnets, or 55 mm without magnets and with speech on the phone?
2. Cameras: one at a time (cooler chip), or five at once (hotter, phone-class chip)?
3. Sound: 1 driver + 2 passive radiators, or literal speakers on every face (voice only, no bass)?
4. Hard mute: flip so the charge face points up (gravity switch), or a magnetic privacy puck?
5. Wake: shake only, with mics off while asleep, or also an opt-in voice wake word?
6. Speech: on the cube by default (private, works offline), or on the phone by default (cooler)?
7. Sell in the EU in version 1? If yes, the base must open for battery swap.
8. Buy an FRDM-IMX93 dev board to measure on-cube speech?
9. The regulatory mark: a black-on-black etch on the charge face, readable only up close? (It is the one place the plain-black-box rule bends.)
10. Light: all twelve edges (this spec), or a soft glow through all six faces (harder to keep light out of the cameras)?

## 14 Sources

**Sensing and hiding**
- S1 https://invensense.tdk.com/products/digital/t5838/
- S2 https://audioxpress.com/news/tdk-introduces-lowest-pulse-density-modulation-multi-mode-mems-microphone-with-acoustic-activity-detect
- S3 https://www.infineon.cn/content/dam/infineon/row/public/documents/24/49/infineon-im69d130-datasheet-en.pdf (returned 404) ; https://digikey.dk/en/products/detail/infineon-technologies/IM69D130V01XTSA1/IM69D130V01XTSA1CT-ND/8030734
- S4 https://www.sameskydevices.com/news/press-releases/new-mems-microphones-carry-wide-operating-frequency-ranges ; https://audioxpress.com/news/cui-devices-offers-new-mems-microphones-for-active-noise-canceling-applications
- S5 https://www.digikey.cn/en/products/detail/knowles/SPH0655LM4H-1/11506911
- S6 https://www.ovt.com/products/ov02c/
- S7 https://appleye.co.il/?p=430
- S8 https://www.ovt.com/products/ov01a/ ; https://www.ovt.com/wp-content/uploads/2022/01/OV01A10-PB-v1.1-WEB.pdf
- S9 https://www.welectron.com/mediafiles/productimg/arducam/Datasheet/HM0360-image-sensor-datasheet.pdf ; https://thepihut.com/collections/raspberry-pi-camera/products/vga-camera-module-for-raspberry-pi-pico-hm0360
- S10 https://www.st.com/resource/en/data_brief/vd55g1.pdf
- S11 https://www.raspberrypi.com/documentation/accessories/camera.html
- S12 https://www.waveshare.com/product/raspberry-pi/cameras/pi5-imx219.htm
- S13 https://api.puiaudio.com/file/005fec80-3413-4365-af79-f80803bcda9b.pdf ; https://www.mouser.fr/new/pui-audio/pui-slim-line-micro-speakers
- S14 https://daytonaudio.com/product/1138/ce32a-4-1-1-4-mini-speaker-driver-4-ohm
- S15 https://www.daytonaudio.com/product/1625/dma58-pr-2-dma-series-passive-radiator
- S16 https://www.apple.com/homepod-mini/specs/
- S17 https://www.pbtech.com/product/SPKAMZ51011/reg ; https://www.johnlewis.com/amazon-echo-dot-smart-speaker-with-alexa-early-access-voice-recognition-control-5th-generation-2022/glacier-white/p6375096
- S18 https://www.ioa.org.uk/system/files/proceedings/nt_shade_sound_goes_round_the_quest_for_omnidirectional_radiation.pdf
- S19 https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5850460 ; https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10075787 ; https://www.postbulletin.com/news/bose-speakers-offer-high-end-desktop-sound
- S20 https://www.cee.elektro.dtu.dk/-/media/c6c495f0f1d743f684b985e494364b6f.pdf
- S21 https://www.gore.com/sites/g/files/ypyipe116/files/2017-01/GORE-Acoustic-Vent-GAW334-Datasheet-en.pdf ; https://www.gore.com/node/17776
- S22 https://patents.justia.com/patent/9014411 ; https://www.prosoundtraining.com/?p=9962
- S23 https://www.eplastics.com/ACRY20640-375PM48X72 ; https://www.eplastics.com/plexiglass/acrylic-sheets/bronze-gray (the two pages give conflicting numbers)
- S24 https://www.bgr.com/tech/new-gorilla-glass-for-camera-lenses-will-improve-smartphone-photography/
- S25 https://www.acplasticsinc.com/media/documents/UACI_150033_Infrared_Transmitting_Extruding_Acrylic_Product_Data_HR.PDF ; https://www.phillips-safety.com/shop/optical-filters/polymer-filters/acrylic-nir-near-infrared-filters/
- S26 https://www.samsung.com/za/support/mobile-devices/what-is-the-udc-under-display-camera-of-the-galaxy-z-fold4 ; https://news.samsung.com/in/interview-making-your-screen-seamless-experts-explain-the-engineering-behind-galaxy-z-fold4s-udc
- S27 https://www.uploadvr.com/apple-vision-pro-specs/ ; https://apple.com/apple-vision-pro/
- S28 https://support.google.com/googlenest/answer/9449280
- S29 https://digprjsurvey.amazon.com/csad/help/node/GKA25FVYEV5PY8C9
- S30 https://support.apple.com/en-ph/guide/security/mac-on-screen-camera-indicator-light-sec75a2d237d/1/web/1 ; https://news.hitb.org/content/researchers-find-way-activate-isight-cameras-without-alerting-users
- S31 https://ipvm.com/reports/meta-ray-ban-led-bypass-fix-tested
- S32 https://www.rcfp.org/reporters-recording-guide/ ; https://www.rcfp.org/reporters-recording-guide/california/
- S33 https://news.bloomberglaw.com/litigation/class-action-privacy-suit-over-person-detection-ai-moves-ahead
- S34 https://curia.europa.eu/jcms/jcms/P_152318 ; https://www.dataprotection.ie/sites/default/files/uploads/2026-05/Domestic_CCTV_A5_ENG_Final.pdf ; https://www.hunton.com/privacy-and-cybersecurity-law-blog/cjeu-adopts-strict-approach-use-cctv
- S35 https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50 ; https://www.mondaq.com/uk/compliance/1826042/not-delayed-not-deferred-eu-ai-act-transparency-obligations-are-now-in-force ; https://www.mccannfitzgerald.com/knowledge/technology-and-innovation/one-month-to-go-eu-ai-act-transparency-compliance
- S36 https://docs.qualcomm.com/doc/87-28733-1/87-28733-1_REV_F_QUALCOMM_QCS6490_QCM6490_Processors_Product_Brief.pdf ; https://www.qualcomm.com/internet-of-things/products/q6-series/qcs6490
- S37 https://jisaku.com/glossary/wireless-charger-qi2 (secondary, not cited by its author)

**Power, heat, compute, radios**
- S38 https://www.wirelesspowerconsortium.com/media/wvsmia32/qi2-25w-news-release-v72.pdf ; https://m.gsmarena.com/qi2_25w_is_official_promises_hundreds_of_devices_will_support_it-amp-68741.php
- S39 https://www.wirelesspowerconsortium.com/standards/qi-wireless-charging/
- S40 https://9to5google.com/2024/12/20/qi2-magnets/ ; https://9to5google.com/2025/01/07/qi2-ready-built-in-magnets/ ; https://www.androidcentral.com/phones/qi2-does-not-require-magnets
- S41 https://www.vde-verlag.de/iec-normen/254762/iec-63563-10-2025.html
- S42 https://forum.khadas.com/t/what-is-the-diameter-of-the-magnetic-ring-in-the-tea-amp/15443 ; https://medium.com/@duanh148/what-size-is-magsafe-magnet-7b14f5d6c450 ; https://totalelement.com/products/54-x-46-x-1-5mm-magsafe-neodymium-rare-earth-magnet-phone-attachment-ring-assembly-with-alignment-magnet-5-pack
- S43 https://www.infineon.com/cms/en/about-infineon/press/market-news/2023/INFPSS202310-003.html ; https://www.hotukdeals.com/deals/amazon-basics-25w-qi22-certified-3-in-1-wireless-charging-station-45w-power-brick-15m-cable-4930648
- S44 https://uk.rs-online.com/web/p/wireless-charging-coils/1354633 ; https://www.distrelec.ch/en/charging-coil-receiver-9uh-7a-330mohm-wuerth-elektronik-760308102213/p/30121381
- S45 https://ir.enovix.com/news-releases/news-release-details/independent-testing-confirms-enovix-ai-1tm-achieves-935-whl
- S46 https://japan.ul.com/wp-content/uploads/sites/27/2014/06/1_techbrief_touchtemp.pdf
- S47 https://www.purdue.edu/freeform/me418/wp-content/uploads/sites/30/2025/09/ME-418-Lec-67-Heat-Transfer.pdf ; https://www.comsol.com/paper/heat-transfer-coefficient-for-a-finned-cpu-heat-sink-under-natural-convection-136252
- S48 https://ti.com/document-viewer/BQ25619E/datasheet/GUID-8C31B571-FE9C-4DC4-AFEF-0BD1B1196679
- S49 https://documentation.espressif.com/esp32-c6_datasheet_en.pdf ; https://www.espressif.com/en/products/socs/esp32-C6
- S50 https://investor.silabs.com/news-releases/news-release-details/silicon-labs-breakthrough-ultra-low-power-wi-fi-6-and-bluetooth
- S51 https://www.cnx-software.com/2024/04/19/infineon-psoc-edge-e81-e83-e84-cortex-m55-m33-mcu-machine-learning-iot-consumer-industrial-applications/
- S52 https://embeddedcomputing.com/technology/processing/chips-and-socs/product-of-the-week-infineon-technologies-airoc-cyw55513-wi-fi-and-bluetooth-combo-ic ; https://documentation.infineon.com/cyw55513/docs/nhu1755169548502
- S53 https://www.nxp.com/iw612
- S54 https://www.nxp.com/products/IMX93W
- S55 https://www.nxp.com/company/about-nxp/smarter-world-blog/BL-FRDM-IMX93-DEVELOPMENT-BOARD-LAUNCHES-ON-BOARD
- S56 https://www.nxp.com/products/i.MX93
- S57 https://www.nxp.com/docs/en/application-note/AN13917.pdf
- S58 https://mouser.com/pdfDocs/IMX93AEC.pdf ; https://docs.digi.com/resources/documentation/digidocs/embedded/dey/5.0/cc93/bsp-camera_r_93.html ; https://wiki.dave.eu/index.php/AURA_SOM/AURA_Hardware/Peripherals/MIPI (datasheet copy hosted by a distributor, not fetched from NXP directly)
- S59 https://www.synaptics.com/assets/product-brief/syn4390-triple-combo-wi-fi-7-bluetooth-and-802-15-4-soc
- S60 https://www.synaptics.com/products/embedded-processors/sl2610-product-line
- S61 https://www.eeworldonline.com/low-power-conversational-ai-chips-support-google-hot-words/ ; https://www.eetasia.com/syntiant-leads-tinyml-benchmark-results/
- S62 https://www.bosch-sensortec.com/media/boschsensortec/downloads/product_flyer/bst-bma400-fl000.pdf
- S63 https://www.allaboutcircuits.com/news/infineon-debuts-pair-rugged-mems-microphones-harsh-environments/
- S64 https://www.analog.com/products/MAX98357A
- S65 https://arxiv.org/abs/2509.02523 ; https://arxiv.org/abs/2410.15608 ; https://github.com/moonshine-ai/moonshine
- S66 https://github.com/hexgrad/kokoro
- S67 https://github.com/OHF-Voice/piper1-gpl
- S68 https://www.esource.com/printpdf/211344 ; https://www.homeandsmart.de/echo-stromverbrauch-738798
- S69 https://www.itftennis.com/media/4420/2023-technical-booklet.pdf

**Interaction, light, app, rules**
- S70 https://www.mouser.com/datasheet/3/1046/1/bst_bmi323_ds000.pdf ; https://www.bosch-sensortec.com/products/motion-sensors/imus/bmi323/
- S71 https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/Reliability-for-TAP-detection-on-BMI270-and-Inquiry-on-TAP/m-p/101069
- S72 https://www.digikey.com/en/product-highlight/s/stmicroelectronics/lsm6dsv16x-inemo-3-axis-accelerometer-and-gyroscope
- S73 https://community.st.com/t5/mems-sensors/how-to-calibrate-tap-sensing-lsm6dsm/td-p/203243 ; https://community.st.com/t5/mems-sensors/single-and-double-tap-on-lsm6dsl/m-p/584105 ; https://community.st.com/t5/mems-sensors/lsm6dsox-int1-int2-both-interrupt/m-p/74668
- S74 https://cdn.sparkfun.com/assets/2/e/1/8/6/adxl367.pdf ; https://analog.com/en/products/adxl367.html
- S75 https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10620913 ; https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11346523 ; https://patents.justia.com/patent/11485281
- S76 https://www.adafruit.com/product/4492
- S77 https://www.digikey.es/en/products/detail/inolux/IN-PI15TAT5R5G5B/14555725
- S78 https://www.androidcentral.com/what-all-color-rings-mean-your-amazon-echo ; https://gizmodo.com/amazon-echo-colors-meaning-1848775533 ; https://gigazine.net/gsc_news/en/20250319-amazon-echo-mute
- S79 https://csa-iot.org/newsroom/matter-1-5-introduces-cameras-closures-and-enhanced-energy-management-capabilities/ ; https://homekitnews.com/2025/05/07/csa-offers-user-friendly-features-with-matter-1-4-1/
- S80 https://www.nxp.com/company/about-nxp/smarter-world-blog/BL-MATTER-TERMINOLOGY ; https://support.smartthings.com/hc/en-us/articles/11219700390804
- S81 https://community.openhab.org/t/ikea-launches-matter-devices-2026-will-we-need-a-hub/167105
- S82 https://www.nordicsemi.com/Products/nRF54L15
- S83 https://www.ezurio.com/channel-sounding ; https://hubble.com/community/guides/bluetooth-channel-sounding-explained-how-ble-now-measures-distance/
- S84 https://support.apple.com/111772 ; https://support.apple.com/bg-bg/guide/security/secbbd20b00b/web ; https://www.schneier.com/blog/archives/2026/03/apples-came= (this URL was reported in this form and looks truncated)
- S85 https://abc7news.com/airbnb-indoor-security-cameras-host-changes-doorbell-cams/14514564/
- S86 https://www.rhombus.com/blog/staying-in-compliance-with-ccpa-and-bipa-for-video-security
- S87 https://fccid.io/2AJVQMWH566B ; https://www.espressif.com/sites/default/files/ESP32-C3-WROOM-02%20FCC%20Certification.pdf
- S88 https://speag.com/assets/downloads/products/dasy/application-notes/WPT/DASY8_Module_WPT_Application_Note_Compatibility_with_KDB_680106V2.pdf
- S89 https://www.law.cornell.edu/cfr/text/47/2.925 ; https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-2/subpart-J/subject-group-ECFRd5ad3b739dbf27a/section-2.935
- S90 https://www.element.com/resources/articles/cybersecurity-and-the-red ; https://digital.gob.es/content/dam/portal-mtdfp/avance-digital/telecomunicacion-e-infraestructuras-digitales/areas_interes/equipos-telecomunicacion/documents/Guia-aplicacion-EN-18031.pdf
- S91 https://www.traverssmith.com/knowledge/knowledge-container/the-eu-cyber-resilience-acts-vulnerability-and-incident-reporting-requirements-are-now-live/ ; https://finitestate.io/blog/cyber-resilience-act-timeline-2026-2027
- S92 https://en.reach24h.com/news/industry-news/sustainability/eu-portable-battery-removability-exemptions-2026 ; https://www.compliancegate.com/removable-and-replaceable-battery-requirements-european-union/
- S93 https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/radio-equipment-directive-red/one-common-charging-solution-all_en
- S94 https://productip.com/kb/productipedia/compliance-resources/crossed-out-wheeled-bin
- S95 https://support.apple.com/en-au/103766 ; https://www.element.com/resources/articles/lithium-ion-battery-certification
- S96 https://wirelesspowerconsortium.com/knowledge-base/testing-and-certification/authorized-test-labs ; https://www.wirelesspowerconsortium.com/media/iyfpemdt/wpc-logo-guidelines-revised-23oct2025.pdf ; https://www.belkin.com/company/blog/25w-wireless-charging-guide/ ; https://www.podfeet.com/blog/2026/05/ces-2026-wireless-power-consortium/ ; https://www.avnet.com/wps/portal/us/resources/article/how-to-get-your-qi-project-certified-by-the-wireless-power-consortium
- S97 https://wiki.st.com/stm32mcu/wiki/Connectivity:Matter_certification_process ; https://docs.silabs.com/matter/2.2.2/matter-certification
- S98 https://www.bluetooth.com/download/qprd-document ; https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrf/protocols/bt/bt_qualification/index.html
- S99 https://broadbandbreakfast.com/fcc-picks-ioxt-alliance-to-head-cyber-trust-mark-program/ ; https://www.ioxtalliance.org/news-events-blog/ul-solutions-withdraws-as-lead-administrator-for-fccs-cyber-trust-mark-program
- S100 https://petapixel.com/2023/11/06/korean-smartphones-have-mandatory-shutter-sounds-8-in-10-want-it-muted ; https://www.engadget.com/2016-09-30-japans-noisy-iphone-problem.html

---

## 15 Another version: the display cube (owner ruling 5; NOT the main version)

**Said plainly.** A second version of the cube whose whole outside is black Gorilla Glass over screens. Off, it is the same plain black box. On, any face can show pictures, video, text, the room map or HELM's receipts. The main version stays the edge-light cube in Sections 3-14. Every number here is an estimate [E] until a researcher checks it; this section was written from the owner's words and the main spec, without new sources.

| Part | The display version | Compared with the main version |
|---|---|---|
| Outside | Six square faces of black Gorilla Glass cover glass, edges mitred so the glass meets at every edge [E] | Same plain black box when off |
| Screens | One square OLED panel behind each face, about 58-60 mm across at the 64 mm size [E]. An OLED pixel that is off gives no light, so an unlit panel is true black and the plain-black-box rule holds [E] | The main version has no screens |
| Light modes | Drawn by the screens themselves (a glowing border, a pulse, a picture); the edge light becomes optional [E] | Edge light only |
| Cameras | Under the screen (under-display camera). Samsung's own notes describe haze and flare with this design [M, S26], so pictures are worse than behind plain dark glass [E] | Behind dark glass; better pictures |
| Sound and microphones | The same hidden edge slots and pinholes; a glass panel could also be driven as a speaker by a small exciter [E, untested] | Edge slots |
| Power and heat | One small OLED at moderate brightness draws a few tenths of a watt [E]. Six faces lit at once could take most or all of the 3.7 W heat budget before HELM runs [E]. So the plan is one or two faces lit at a time, chosen by where the person is | Edge light uses 50-300 mW |
| Battery | Hours, not days, with screens on [E] | About 10 days on a typical day [E] |
| Drive electronics | The i.MX 93 class has limited display outputs; six panels need a display bridge or a stronger chip [E, check] | No displays |
| Charging | Qi2 magnetic charging works through glass, since glass is not metal [E]; the charge face's screen rests while docked | Same |
| Privacy | The camera-on light stays wired in hardware (an LED behind the glass), even though the screens could also show it | Same rule |
| Touch | Taps stay motion-sensor taps (no buttons). A touch layer on the glass is possible but not asked for [E] | Same taps |
| Cost and risk | Six custom square OLED panels and six glass faces cost far more; glass corners can chip in a drop [E] | Cheaper, tougher |

**Open questions for this version only:** how many faces may be lit at once; whether the edge light stays; whether the faces should also take touch.

## DRAWING BRIEF

Draw the HELM Cube as a **64 mm matte black cube** with slightly rounded edges, about 3 mm radius. The finish is soft, bead-blasted dark glass or ceramic. It is not glossy and not metal.

**Views:**
1. Three-quarter hero view, unlit and lit (Speaking mode).
2. Six flat face views.
3. A cutaway or exploded view.
4. A scale view with the cube beside a real tennis ball (about 67 mm across) and resting in an adult's open palm.
5. A smaller 55 mm variant beside it, at the same scale.

**The governing rule (owner, 2026-10-21):** unlit, the cube is a plain black box, identical on all six faces. Draw the unlit hero view with no line, band, dot, port or mark that singles out any face.

**Edge light:**
- Light runs along **all twelve edges** (about 3 mm rounded edges of translucent black).
- When unlit the edges are the same black as the faces. When lit they glow, framing every face the same way. There is no band around the middle.
- Show a row of mode swatches, each a small cube with lit edges: off (plain black); soft-white sweep (Awake); cyan, brightest on the edges nearest a person (Listening); gold points travelling (Thinking); warm-white syllable pulses (Speaking); violet short-short-long (Question); amber on every edge but one dark edge (Missing input / UNDETERMINED); dim amber shrinking to one edge (Declined); red breathing and steady red (Privacy soft and hard); blue chase (Pairing); orange blinks (Low battery and Error); teal blip (Eye report).
- Green appears **only** as a small camera-on dot at the centre of a face, invisible when off.

**Hidden sensors:** show them in a separate "x-ray" view as dashed outlines:
- one camera behind each face;
- each camera centred on its face (the charge face's camera in a corner beside the magnet ring);
- mic pinholes in the edge seams;
- the speaker behind the face opposite the charge face, with hairline slots along the edges;
- two passive radiators behind the left and right faces;
- the Qi coil and magnet ring behind the charge face, with the Hall-effect dock sensor and the small haptic motor beside it.

**Charge face and charger:**
- Nothing marks the charge face. A close-up inset may show the black-on-black regulatory etch, readable only at an angle (an open owner choice).
- The charger is a low round black puck, slightly smaller than the cube's footprint, so the cube appears to float. Show the magnetic snap: the cube pulled down onto the puck, with a small "buzz" mark for the haptic pulse.

No buttons, ports or logos are visible anywhere.