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

## 8a Knowing where it is: motion, heading, location and a map of the room

**Owner ruling 3 (verbatim):** "WITH GYRATOR WHEN IT'S BEEN MOVE TURNED AND DIRECTION FOR MAPPING IT'S ENVIROMENT GEOLOCATION AND USE WIFI TO DRAW ITSELF AN INTERNAL SCHEMATIC OF IT'S ENVIROMENT AND OR USE LIDAR". "Gyrator" means gyroscope. Ruling 4 puts HELM in charge of all of it.

**Said plainly first:**
1. The gyroscope already on board tells the cube how it was turned, if the gyroscope was running when the turn began. For a turn lasting a few seconds, it is accurate to about 1° [E]. If the cube was asleep, the start of the turn is missed, and the new heading is `UNDETERMINED` until the cube recognises the room (point 2). The gyroscope cannot tell how far the cube was carried: that estimate is wrong within a second or two [E].
2. There is no compass, so the cube has no "north". It keeps its own heading, which slowly drifts. It corrects the drift by recognising the room with its depth sensors and cameras [E].
3. GPS does not suit a sealed cube that lives indoors. If the user allows it, the cube gets its town-level location from the phone app [E].
4. If the home's router answers Wi-Fi ranging requests (many do not), Wi-Fi can tell roughly how far the cube is from it. It works best with a clear line of sight [M, S111]. Wi-Fi can also tell whether something moved nearby. Drawing walls and furniture from Wi-Fi alone is still research [M, S116, S118].
5. The room drawing comes from tiny "lidar" depth sensors, one behind each face, plus the cameras. In its finer mode each sensor gives 64 distances (an 8 × 8 grid). For the first-pick sensor, ST gives about 2 m on a white wall in the dark, about 0.8 m on a dark grey surface, and about 0.5 m in bright daylight. All three figures are without cover glass [M, S127]. The 3.5 m figure holds only for the coarser 4 × 4 grid (16 distances), in the dark, on a white wall [M, S127]. Turning the cube fills the gaps around the horizon. Some directions stay unmeasured (8a.4).
6. The result is a coarse 3D sketch of the nearer part of a room: walls, doorways and large objects within about 2 m. At 2 m, one reading covers about 0.26 m [E]. Farther out, only the coarse grid reaches, at about 0.8 m per reading at 3 m [E]. Space the cube has not measured stays blank and is marked `UNDETERMINED`. HELM never draws in a wall it has not measured.
7. Mapping is off by default. When it is on, it runs only while the cube is awake and shows a light pattern. The map stays on the cube and can be deleted from the app.

**Terms used in this section:**
- **Gyroscope:** measures how fast the cube turns. Adding up (integrating) the turn rate over time gives the angle turned.
- **Accelerometer:** measures pushes and gravity. Gravity tells which face is down (tilt). It cannot tell which way the cube faces around the vertical axis.
- **Heading:** which way a face points around the vertical axis, as a compass would say. **Pose:** position, heading and tilt together.
- **Bias (zero offset):** the small false reading a sensor gives when it should read zero. Adding up a bias over time is what makes estimates drift.
- **Dead reckoning:** estimating where you are by adding up your own motion, with no outside reference.
- **Relocalising:** finding the cube's pose again by matching what it senses now against the stored map.
- **Time of flight (ToF):** measuring distance by timing a pulse of invisible light to a surface and back. A **multizone** ToF sensor does this for a grid of directions at once. It is a tiny lidar with no moving parts.

**8a.1 Motion and turning from the gyroscope already on board**

**Verdict: turning is feasible with the gyroscope already chosen (untested). Distance carried is not.**

**BMI323 (first pick, Section 6), from Bosch's preliminary flyer [M, S101]:**
- Gyroscope: zero offset ±1 °/s (typical over the part's life), temperature drift ±0.04 °/s/K, noise density 0.007 °/s/√Hz.
- Accelerometer: zero offset ±50 mg (typical over the part's life), temperature drift ±0.3 mg/K, noise density 180 µg/√Hz.
- Bosch says a self-calibration step, run while the part is still, brings the gyroscope's scale error after soldering "down to ± 0.7%" [M, S101]. That is a best case, not a guaranteed limit.

**LSM6DSV16X (alternative):**
- An on-chip fusion block called SFLP ("sensor fusion low power") outputs three things [M, secondary, S102]:
  - a "game rotation vector" (an orientation with no north reference);
  - a gravity vector;
  - its own estimate of the gyroscope bias.
- A press article says it can track "while drawing as little as 15µA" [M, secondary, S102]. The article does not say the gyroscope is on at that figure. With the gyroscope on, budget the part's 0.65 mA high-performance figure [M, S72] until ST's low-power figures are checked [check].
- ST staff say it estimates the bias only while the device is still [M, forum, S102].
- Gyroscope noise is about 0.0028 °/s/√Hz. ST's LSM6DSV16X product page lists this figure (read through a search summary) [M, secondary, S102], and Luxonis gives the same for the sibling LSM6DSV [M, secondary, S103]. The 16X's own zero-offset figure has not been checked [check].

**What the gyroscope can do [E, our arithmetic from the numbers above]:**
- **Bias.** Left uncorrected, a 1 °/s bias adds 60° of false turning per minute. So the bias must be re-measured each time the cube sits still. The cube is still most of the day, so this costs almost nothing.
- **Temperature.** After the bias is corrected, temperature becomes the main error. The cube warms when it talks or charges (Section 7). A 5 K rise moves the bias by up to 0.2 °/s, which is 12° per minute if it is not re-measured. So the gyroscope alone gives good heading for seconds to tens of seconds. It does not stay good for many minutes unless the bias is re-measured at each rest and corrected for temperature.
- **Noise.** Small: after 60 s it adds about 0.05° (0.007 × √60).
- **Scale.** At ±0.7% (Bosch's best case), a quarter turn (90°) can be off by up to 0.63°, and a full turn by up to 2.5°.
- **So:** a pick-up, turn and set-down lasting a few seconds is measured to about 1°. That covers the owner's "when it's been moved, turned".

**What dead reckoning of position cannot do [E]:**
- Position error from an accelerometer bias grows with the square of time [M, S104]: error = half × bias × time².
- With the ±50 mg offset: about 0.25 m after 1 s, 1 m after 2 s, and 6 m after 5 s.
- Even after calibrating it down to 5 mg: about 0.6 m after 5 s, and 2.5 m after 10 s.
- A 1° tilt error leaks 17 mg of gravity into the sideways reading. That is a problem of the same size.
- The cube starts and ends each move at rest, with zero speed. That helps a little for a short slide across a table of 1–2 s [E; method in S104]. A carry across a room cannot be measured this way.
- **So:** the gyroscope says *how the cube was turned*. *Where it was put* comes from relocalising against the map (8a.5). Until relocalising succeeds, the cube's position is `UNDETERMINED`.

**Moves while asleep.**
- The always-on ADXL367 (Section 6) wakes the processor when the cube moves.
- The 6-axis IMU runs only while awake. The BMI323 starts in about 2.5 ms in its fast-start mode [M, S70, read through a search summary]. The longer delay is the i.MX 93 waking from deep sleep and starting the IMU, which is not measured [check]. So the first part of a pick-up is missed [E].
- Option, off by default: the LSM6DSV16X's fusion block could keep running through sleep and hold its results in the sensor's own memory (FIFO) for the processor to read on waking. At 0.65 mA that is about 1.2–2.3 mW [E, from S72], which fits the asleep budget. FIFO size not checked [check].
- Rule: after any motion while asleep, the stored pose is marked `UNDETERMINED` until the cube relocalises.
- Gravity still tells which face is down.

**Heading without a compass.** The Qi2 magnet ring rules out a compass (Section 6). So:
- The cube keeps a **relative** heading. Angles are measured against the room's own walls, not against north. A room map does not need north [E].
- The gyroscope carries the heading through a turn. Each time the cube rests, HELM corrects the drift by matching depth readings and camera features against the map [E].
- The cube matches the room only while it rests. That is relocalising, not tracking on the move. Tracking on the move with a camera and an IMU together is an established method called visual-inertial odometry; VINS-Mono is one published example [M, S105]. The cube does not do this by default. It would need a camera running while the cube is carried (green dot on, about 1 W, Section 7), and only one camera runs at a time (Section 8) [E].
- Camera matching works only in a lit room. The hidden cameras lose 1.9–3.1 f-stops behind the dark glass (Section 12). The ToF sensors carry their own light and work in the dark.
- If the owner wants true north, the phone's compass could supply it once at setup [E, untested]. The phone must not touch the cube, because the Qi2 magnet ring that rules out a compass in the cube would also bend the phone's reading. The app lights one face. The user lays the phone on the table in line with that face, at least about 50 cm away [E, untested]. Expect a few degrees of error at best indoors [E].
- Wi-Fi ranging gives distance, not direction (8a.2). It cannot correct heading.

**8a.2 Where in the world: geolocation**

| Method | Verdict | Why |
|---|---|---|
| GPS (GNSS) chip in the cube | **Poor fit; not fitted** | Indoors, satellite signals lose 5–15 dB in houses and 20–30 dB in office buildings [M, S106]. A good small receiver, the u-blox MAX-M10S, specifies its 1.5 m accuracy with every satellite at −130 dBm, static, over 24 hours [M, S107]. It needs −148 dBm for a cold start (no stored satellite data). A cold start takes 27 s with every satellite at −130 dBm, and its sensitivity figures were "demonstrated with a good external LNA", meaning an extra signal amplifier [M, S107]. A fix near a window in a timber house may be possible, but it is not dependable inside a sealed cube with a small antenna [E]. Tracking draws 25 mW [M, S107], about equal to the top of the cube's whole asleep budget of about 11–25 mW (Section 7). The antenna would also sit beside the Qi coil and magnets [E]. |
| The phone's location, through the app | **Works today** | The phone already knows where it is. On Android, "approximate" location is accurate to within about 3 km². "Precise" is usually within about 50 m, and sometimes within a few metres [M, S108]. Town level is enough for time zone, weather and sunrise [E]. Default: approximate, asked once at setup, stored as a dated fact. |
| Wi-Fi positioning from a cloud database | **Works with limits; off by default** | The cube would send the list of nearby access points (hardware addresses and signal strengths) to a service such as Google's Geolocation API. The service returns a position and an accuracy radius [M, S109]. A 2005 city-scale study measured median errors of 13–40 m [M, S109]. It tells a third party about the home's surroundings, and the phone already gives the same answer [E]. |
| Wi-Fi round-trip-time ranging (FTM) | **Works with limits** | See below. It gives distance to an access point inside the home, not a street address. |
| Bluetooth Channel Sounding | **Not on this radio** | Channel Sounding arrived in Bluetooth 6.0 and is claimed to measure distance to 10–50 cm [M, secondary, S83]. The IW612 is Bluetooth 5.4 [M, S53]. Watch for it in version 2 [E]. |

**Wi-Fi round-trip-time ranging (FTM):**
- **What it is.** Fine Timing Measurement (FTM) times a Wi-Fi exchange with an access point and back. Distance = round-trip time ÷ 2 × the speed of light [M, S111]. It was introduced in IEEE 802.11mc and continues in IEEE 802.11az [M, S111]. Android calls it "Wi-Fi RTT" [M, S110].
- **The IW612 supports it.**
    - NXP's AN14044 (Rev. 3.0, 29 April 2026) lists the IW612 [M, S111].
    - In that note, a client device like the cube can start ranging with 802.11mc, 802.11az non-trigger-based ranging, and 802.11az trigger-based ranging [M, S111].
    - NXP validated trigger-based 802.11az ranging only with its own in-house access point. The note itself covers only non-trigger-based ranging [M, S111].
    - NXP's IW612 page lists "802.11az accurate ranging" [M, S53].
    - The ranging tool, mlanwls, is preinstalled in i.MX Linux board packages based on kernel 6.18.2 and later. Its configuration file and README were not yet in the "lf-6.18.2_1.0.0" release [M, S111].
- **Accuracy.**
    - Android's target for 802.11mc, at the 90th percentile, is an error of 2 m at 80 MHz, 4 m at 40 MHz, and 8 m at 20 MHz [M, S110].
    - For 802.11az it is 1 m at 80 MHz. That target assumes a phone with 2 antennas and an access point with 4 [M, S110].
    - The IW612 is a 1×1 radio (one data stream) with channels up to 80 MHz [M, S53]. So expect the 2 m class, not the 1 m class [E].
- **Limits.**
    - The access point must answer. Many home routers use chipsets without FTM. A community list names some that do [M, secondary, S113]. HELM must check, not assume: if no access point answers, the FTM range is `UNDETERMINED`.
    - One access point gives a distance, not a position. A position needs about three access points at known places [E]. Most homes have one to three, at places the cube does not yet know [E].
    - Walls and reflections bias the range. A 2025 survey of over 180 papers covers the accuracy problems and their fixes [M, S114].
    - NXP says the station and the access point must be in line of sight for an accurate and stable reading [M, S111]. Through a wall, the range is only a rough hint.
    - The IW612 can also answer ranging requests itself (802.11mc and 802.11az non-trigger-based) [M, S111]. So an Android phone with Wi-Fi RTT could measure its distance to the cube, with no new part [E, untested].
- **Use in the cube:** a coarse "which part of the home am I in" check. It picks which stored room map to try first when relocalising [E]. It is never used as the drawing itself.

**8a.3 "Use Wi-Fi to draw itself an internal schematic"**

- **Channel state information (CSI)** is the receiver's detailed record of how the radio path changed each Wi-Fi packet: the strength and phase of each subcarrier [M, S112]. People and objects in the path change it. That is the basis of **Wi-Fi sensing**.
- **The IW612 exposes CSI.**
    - NXP's AN14011 (Rev. 10.2, 25 June 2026) marks the IW612 "Yes" for CSI. It also marks "Yes" for an **Ambient Motion Index (AMI)**, a built-in motion measure. Both run on Linux, with the cube acting as a normal Wi-Fi client [M, S112].
    - From Linux 6.12.49 onward, the capture tool (mlancsi) is included in NXP's board package [M, S112].
    - CSI comes only from received packets [M, S112]. So the radio must keep receiving and cannot sleep while sensing [E].
- **The standard.** IEEE 802.11bf-2025, "Enhancements for Wireless LAN Sensing", was approved on 28 May 2025 and published on 26 September 2025 [M, S115]. We found no statement that the IW612 implements 802.11bf. NXP's CSI feature is NXP's own interface [M, S112]. This absence claim is only as wide as our search.

| What Wi-Fi sensing can do | Verdict | Evidence |
|---|---|---|
| Notice motion near the cube | **Works with limits** | The IW612 has AMI [M, S112]. BleepingComputer reported on 18 August 2026 that Comcast offers WiFi Motion. It turns the radio links between a gateway and fixed Wi-Fi devices into motion sensors. It detects motion, not who is moving. It is opt-in, and it cannot reliably tell a small pet from a child [M, secondary, S119]. Results change between rooms and people. One study found that a method which works in any room is still not proven [M, S116]. |
| Say whether a person is present, and roughly where | **Research-grade on one 1×1 radio** | A 2025 thesis reports presence and location up to 20 m, through walls, using low-cost Wi-Fi aimed in one direction [M, S117]. The library has not yet verified the record. The cube has one antenna stream and no direction finding [M, S53]. |
| Draw walls and furniture | **Research-grade** | One 2024 paper maps free space from Wi-Fi signal strength while moving [M, S118]. Nothing we found is ready for a product. |

**Verdict for the owner's words:** Wi-Fi gives the map two dated facts: roughly how far away the router is, and whether something moved. The depth sensors and cameras draw the schematic itself (8a.4). Wi-Fi sensing is off by default (8a.8).

**8a.4 Lidar: a tiny depth sensor behind each face**

**Verdict: works with limits. A spinning lidar does not fit.**
- A small spinning lidar, the RPLIDAR C1, is 55.6 × 55.6 × 41.3 mm, weighs 110 g and draws 1.15 W [M, distributor, S126]. It would fill most of a 64 mm cube. It would also need a window band around the middle, which breaks the plain-black-box rule [E].
- **Multizone ToF sensors fit.** One sits behind each face, beside the camera [E].

| | ST VL53L7CX (first pick, wide) | ST VL53L8CX (alternative) |
|---|---|---|
| Zones | 8 × 8 (64) at up to 15 Hz, or 4 × 4 at up to 60 Hz [M, S127; S120 gives the same limits for the VL53L8CX] | 8 × 8 at up to 15 Hz; 4 × 4 at up to 60 Hz [M, S120] |
| View | 60° × 60° (90° diagonal) [M, S122] | 45° × 45° (65° diagonal) [M, S120] |
| Range | 4 × 4 in the dark: 3.5 m on a white (88%) target, 1.4 m on dark grey (17%). 8 × 8 in the dark: 2.0 m white, 0.8 m dark grey. At 5 klux (bright daylight at 940 nm): 0.5–0.65 m. All typical, without cover glass; minimum 2 cm [M, S127] | Up to 400 cm by ST's headline figure; better in bright light [M, S120, S121]. For the VL53L7CX the headline figure is the 4 × 4, dark, white-target case; the 8 × 8 figures for this part are not checked [check DS14161] |
| Light source | 940 nm invisible, Class 1 eye-safe laser (VCSEL) [M, S122]. ST lists EN 50689:2021 compliance except its clause 5 on child-appealing products. If the cube could count as child-appealing, ST asks to be contacted [M, S127] | The same [M, S120] |
| Size | 6.4 × 3.0 × 1.6 mm [M, S127] | 6.4 × 3.0 × 1.75 mm [M, secondary, S121] |
| Power | Continuous ranging: 216 mW (2.8 V analog, 1.8 V I/O) to 313 mW (3.3 V both) [M, S127]. Autonomous mode, 20 ms per frame: 5.4 mW at 4 × 4 and 1 Hz; 19 mW at 8 × 8 and 1 Hz; 88 mW at 8 × 8 and 5 Hz [M, S127]. Pololu's carrier: about 100 mA typical, peaks 150 mA [M, distributor, S122] | About 215 mW in continuous ranging [M, secondary, S121]. ST quotes 1.6 mW at 4 × 4 and 1 Hz in low-power mode [M, secondary, S121]. One user measured about 68 mW at that setting [M, forum, S121] |
| Width of one zone | 8 × 8 at 2 m: 7.5°, about 0.26 m. 4 × 4 at 3 m: 15°, about 0.79 m [E] | 8 × 8 at 2 m: 5.6°, about 0.20 m. 4 × 4 at 3 m: 11.25°, about 0.59 m [E] |
| Share of all directions seen from one still pose | About 40% from one still pose with five usable faces [E] | About 23% [E] |

- **Coverage.** Six faces see in every direction only if each face covers 90° × 90° [E]. A resting cube uses at most five faces, because the bottom face sees the table or sits on the charger. From one still pose, five VL53L7CX views cover about 40% of all directions, and five VL53L8CX views about 23% [E]. Turning the cube about the vertical by about 45° fills the gaps around the horizon [E]. Turning cannot fill a band about 30°–51° above and below the horizon (about 22°–60° for the VL53L8CX). Every resting pose of a cube points its faces level or straight up, so no amount of turning on a table reaches that band. It is about a quarter of all directions [E]. The band holds the upper walls and the corners where walls meet the ceiling, so these stay `UNDETERMINED`. Readings taken while the cube is carried cannot fill them either, because the cube's position is `UNDETERMINED` while it moves (8a.1, 8a.5).
- **Detail.** In the 8 × 8 mode, one zone is about 0.20–0.26 m wide at 2 m, about as far as that mode reaches. At 3 m only the 4 × 4 mode reaches, at about 0.6–0.8 m per zone [E]. Walls, doorways, sofas, tables and people show up. Chair legs, cables and small objects do not.
- **Far walls.** In the 8 × 8 mode, readings stop at about 2 m on a white wall in the dark, and at about 0.8 m on a dark one. In the 4 × 4 mode they stop at about 3.5 m [M, S127]. The cover window shortens this further. ST asks for over 87% transmission, so at most about 76% of the light survives the round trip, which cuts these ranges by roughly an eighth [E]. In bright daylight (5 klux) every mode falls to about 0.5–0.65 m [M, S127]. So mapping works best under LED lamps or with the curtains drawn, because LED room light carries little 940 nm light [E]. In any larger room, far walls stay `UNDETERMINED` until the cube is moved closer [E].
- **Hard surfaces.** Dark surfaces cut the range sharply: a 17% grey surface reads only to about 0.8 m in the 8 × 8 mode, in the dark [M, S127]. Glass and mirrors can give no reading or a false one [E]. ST also warns that indoors the sensor may see several light paths and report false targets [M, S120]. The two-pose rule in 8a.5 guards against this.
- **Data.** Six sensors read 384 distances per frame (6 × 64) [E]. Each sensor needs about 84 KB of firmware loaded over the bus at start-up [M, S120].
- **Wiring six sensors.** Every sensor starts at the same bus address, 0x52, and loses any new address when powered off [M, S120, S127]. Each needs its own enable line (LPn) so HELM can give it an address at each start-up [M, S120]. The VL53L7CX talks only I2C, at up to 1 MHz [M, S127]. Loading its firmware (about 84 KB for the VL53L8CX [M, S120]; the VL53L7CX figure is not checked [check]) takes roughly 0.7–1 s per sensor, so about 4–6 s for six at the start of each session [E]. The VL53L8CX also offers SPI at up to 20 MHz [M, S120], which cuts this to well under a second [E].
- **A denser sensor to watch.** ST's VL53L9CX gives 2,268 zones (54 × 42) over 55° × 42°. It ranges from under 5 cm to 8.8 m, at up to 100 Hz, in a 12.8 × 6.1 × 4.6 mm module. ST said mass production would start in early July 2026 [M, secondary, S124]. We did not confirm that it started. Its power is not published. It connects by MIPI I3C or CSI, and the i.MX 93's one camera port is already busy (Section 8) [E]. It may suit one face in a later version. It also streams a 2D infrared image alongside depth [M, secondary, S124]. An infrared image is a picture that works in the dark. So this sensor would fall under the camera rules, including the hardware camera-on dot (Section 9) [E]. ST has a cover-glass note for it, AN6346 [S131].

**Behind dark glass (it needs an infrared window):**
- **What ST asks for.** The cover glass must pass more than 87% of the 940 nm light [M, S123]. st.com did not load during this check, so this figure was read through a search summary. The light crosses the glass twice, so 87% one way is about 76% round trip [E].
- **Window size.** ST requires the opening in the cover to be at least as wide as the receiver's "exclusion zone", a 74° × 74° cone (105° diagonal) [M, S127]. With the ink on the inside of a 2 mm face glass, that means an opening clear to infrared of roughly 2–4 mm over each of the two lenses (emitter and receiver) [E]. Both fit beside the camera on a 64 mm face. On the charge face they go in a corner outside the magnet ring [E].
- **Why the camera glass will not do.** The cameras' dark face glass passes only 12–27% of visible light (Section 12, S23). The ToF needs the opposite: black to the eye, but clear at 940 nm.
- **Materials that could work:**
    - Visible-black, infrared-passing plastic filters exist. They are black to the eye and pass near-infrared above a cut-on wavelength of 670–910 nm, in thicknesses of 0.5–5.0 mm [M, S25]. Their transmission at 940 nm is not stated [check].
    - An infrared-passing black ink on the inside of the face glass is the other route [E].
- **Appearance.** When off, the window must look the same as the rest of the face. That needs testing on a sample in daylight and under a phone torch [E].
- **Crosstalk.** Light bouncing inside the cover glass ("crosstalk") is handled by ST's processing beyond 60 cm [M, S120, S127]. Closer than that, it can make targets look nearer than they are, or invent one. ST then advises a crosstalk calibration with the cover in place, using a target at 600 mm or more that fills the whole view. The result can be saved, and one unit's calibration can be reused on others with a safety margin [M, S120]. Spot-check each production cube [E]. A black barrier between the emitter and receiver openings is needed under the glass [E].
- **Cameras.** The face cameras need their usual infrared-cut filters, so the 940 nm light does not show up in pictures [E].

**8a.5 How HELM builds and keeps the map**

**What it combines [E]:**
- gyroscope turns: how the cube moved between rests;
- ToF depth: where surfaces are;
- camera features: corner points that fix heading in a lit room (no pictures are kept; 8a.8 item 7 says what is kept);
- Wi-Fi ranges: which part of the home.

Under ruling 4, HELM decides when to map, which faces and sensors run, and how often. Each mapping session must pass the RPM gate. The gate's inputs are:
- the consent flag is on;
- neither privacy mode is on;
- the battery is at or above 20% [E];
- there is heat headroom (8a.6).

Each session leaves a receipt in the app. The receipt lists the faces and sensors used, the duration, the cells changed, and the `receipt_hash`.

**The map has three layers [E]:**
1. **Cells.** Space is divided into 10 cm cubes. Each cell is `occupied`, `free` or `UNDETERMINED`.
   - Every cell starts as `UNDETERMINED`.
   - A cell becomes free when a ToF beam passes through it, and occupied where a beam stops.
   - The published OctoMap method works the same way, and also keeps unknown space as its own state [M, S125].
2. **Schematic.** Rooms, walls, doorways and large objects, drawn only from measured cells.
   - A wall piece exists only where occupied cells were measured.
   - A gap between two measured wall pieces stays `UNDETERMINED`. It is never joined up by a guessed straight line.
3. **Names.** For example "kitchen", "sofa" or "the lamp on face S2".
   - Names come from the user, by voice or in the app.
   - HELM never guesses a name. If it needs one it does not have, it asks.

**Rules [E]:**
- **Every fact carries where and when.** Each cell stores:
  - when it was last measured;
  - which face and sensor measured it;
  - the cube's pose at that moment;
  - how many readings support it;
  - the session's `receipt_hash`.
- **No pose, no writing.** If the cube's pose is `UNDETERMINED` (it moved while asleep and has not relocalised), new depth readings are held back, not written. Writing them would put walls in the wrong place.
- **Two poses must agree.** A cell is written as occupied or free only when readings from two different poses agree. A single reading is shown as "seen once" and is not used for decisions. This guards against mirrors and glass.
- **Facts age.** Each cell shows its age. After an age limit set by the owner, HELM treats the cell as `UNDETERMINED` for any decision. It still shows the old reading with its date.
- **Answers follow the gate.** "How far is the door?" gets either a number with its measurement date, or `UNDETERMINED` plus where to put the cube to measure it.
- **Relocalising.**
  - At each rest, HELM matches the new ToF readings against the stored cells. It also matches camera features if the room is lit.
  - A clear match sets the pose.
  - No clear match leaves the pose `UNDETERMINED`, and HELM may ask: "Where did you put me?"
- **Docked is a known place.** The charger rarely moves, so docking gives a known position and a known face-down. Heading on the charger still has to be found by matching, because the round magnet ring lets the cube sit at any angle.

**Size [E]:**
- **Cells.** A 5 × 5 × 2.5 m room at 10 cm cells is 62,500 cells. At about 2 bytes per cell, that is about 125 KB.
- **Raw readings** are much larger. A 2-minute session is 230,400 readings (6 faces × 64 zones × 5 Hz × 120 s), about 7.4 MB at 32 bytes each.
- **Folding.** At the end of each session the raw readings are folded into the cells and then deleted. The session receipt stays.

**Where the map lives:** on the cube. The app shows it as a 3D sketch. `UNDETERMINED` space is left blank and never filled in [E].

**8a.6 Power and heat**

| Job | Runs when | Power |
|---|---|---|
| Noticing the cube was moved (ADXL367) | Always | 180 nA in motion-wake mode [M, S74] |
| Gyroscope and accelerometer (6-axis IMU) | While awake, and after any motion | BMI323: 790 µA in high-performance mode [M, S101], about 1.4–2.9 mW at 1.8–3.6 V [E]. LSM6DSV16X: 0.65 mA [M, S72]; the 15 µA press figure is not tied to tracking with the gyroscope on [M, secondary, S102] |
| ToF, one face, continuous | Mapping sessions only | 216–313 mW, depending on supply voltages [M, S127] |
| ToF, one face, slow (1 Hz) | Mapping sessions only | VL53L7CX, autonomous mode: 5.4 mW at 4 × 4, 19 mW at 8 × 8 [M, S127]. VL53L8CX: 1.6 mW by ST's figure, about 68 mW as measured by one user [M, secondary and forum, S121]. Budget 10–70 mW [E] |
| ToF, all six faces continuous | **Not allowed** | 1.3–1.9 W [E, 6 × S127]: a third to half of the 3.7 W heat budget (Section 7) |
| Camera features | Mapping in a lit room | 0.9–1.1 W, the "camera in use" state (Section 7) [E] |
| Wi-Fi FTM ranging | Mapping sessions and "where am I" checks | NXP publishes no IW612 power figure [M, S53]. NXP's recommended setting is a 128 ms burst every 500 ms [M, S111] (802.11mc), so the radio is busy about a quarter of the time [E]. For 802.11az NXP recommends 5 exchanges a second, 10 measurements each [M, S111]. Budget 50–150 mW [E] |
| Wi-Fi CSI sensing | Opt-in; awake only | The radio receives steadily and Linux stays awake: about 0.9 W for the whole cube [E, from the Section 7 states] |
| GNSS | Not fitted | 25 mW while tracking [M, S107] |
| Phone location | At setup, then on request | About zero on the cube [E] |

**A mapping session [E]:**
- **Lit room:** two faces ranging continuously, four at 1 Hz, one camera, the IMU and the processor. About 1.4–2.0 W.
- **Dark room, no camera:** about 1.2–1.7 W. That is about the same as speaking (Section 7, state C: 1.1–1.9 W).
- **Length:** sessions are capped at 2 minutes. One session uses up to about 0.067 Wh.
- **Battery:**
  - One session a day changes typical battery life from about 10 days to about 9.5 days.
  - Ten sessions a day: about 6.7 days.
- **Heat:** mapping shares the heat budget with charging and talking. HELM's gate refuses a session during fast charging. If a session must run on the charger, HELM slows the charging first (Section 7).

**While asleep:** only the ADXL367 runs. ToF, cameras, gyroscope, Wi-Fi ranging and Wi-Fi sensing are all off. Even the slowest ToF setting would not fit: six VL53L7CX sensors at 4 × 4 and 1 Hz would add about 32–50 mW [E, 6 × S127]. That is more than the whole 11–25 mW asleep budget. Keeping them in low-power idle, only to skip the firmware reload, would add about 0.8 mW typical and up to about 6 mW worst case [E, from S127: 45 µA typical and 300 µA maximum each]. So they are switched off.

**8a.7 Parts**

Motion, turning, Wi-Fi ranging and Wi-Fi sensing need no new part. The BMI323 or LSM6DSV16X, the ADXL367, the i.MX 93 and the IW612 are already in Section 11. The new parts are six ToF sensors, six infrared windows, one enable line per sensor, and a flex harness to each face [E]. Rows are listed below for Section 11.

**8a.8 Privacy**

A room map and a location reveal a lot: the layout of the home, where people sleep, and when someone is home. They get the strictest defaults.

1. **Off by default.** Mapping, Wi-Fi sensing and cloud Wi-Fi positioning each stay off until the user turns them on in the app. HELM's RPM gate checks the consent flag before every session. With no flag there is no session, and the refusal is logged. HELM does not wake the cube on its own to map. A session runs only inside an awake window that a person started (shake, tap, voice or app), unless the owner turns on scheduled mapping [E, owner choice].
2. **Kept on the cube.** The map, the pose history and the location fact stay on the cube. The app reads them over the home network or Bluetooth. Cloud backup is opt-in only (Section 8).
3. **Delete control.**
   - The app can delete the whole map, one room, a drawn region, or the location fact.
   - Raw readings are deleted at the end of each session (8a.5).
   - Flash memory moves data around as it wears, so overwriting a file does not reliably erase it [M, secondary, S130]. So the map, the pose history and the location fact are encrypted from their very first write, with the key held in the i.MX 93's secure enclave [E, check]. Deleting destroys the key ("cryptographic erase"). NIST counts this as a full purge only if nothing was ever stored unencrypted before the key existed [M, S130].
4. **Coarse location.** Approximate (town level) is the default [M, S108]. The map uses its own room coordinates, not latitude and longitude. Precise location only if the user chooses it.
5. **No third parties by default.** Cloud Wi-Fi positioning sends the nearby access-point list to an outside service (S109), so it stays off. The map is never shared with Matter devices or other apps by default. HELM ranges only to the home's own access points, while connected to them. 802.11mc ranging frames are not encrypted. 802.11az can encrypt them when the cube is connected with WPA3 protected management frames [M, S111]. So prefer 802.11az over WPA3. Never range unconnected to a neighbour's access point, which would show it the cube's hardware address [E].
6. **Wi-Fi sensing can sense through walls.** It can pick up a neighbour moving. Comcast tells its users in buildings with shared walls to lower the sensitivity [M, secondary, S119]. The cube records motion only, never who moved. It is off by default. Raw CSI records carry the hardware (MAC) addresses of the sender and receiver of every packet the radio hears [M, S112]. HELM computes the motion measure on the cube, keeps only "motion yes/no, time", and drops each raw record at once. It never stores or sends those addresses [E]. Capture is filtered to packets from the home's own access point; NXP's firmware supports filtering [M, S112].
7. **Camera mapping keeps points, not pictures, but points are not harmless.** Researchers rebuilt recognisable images of scenes from stored 3D points and their feature descriptors alone [M, S128]. By default HELM keeps only each point's 3D position and drops the descriptors at the end of the session, so relocalising in later sessions uses depth only. If the owner chooses to keep descriptors for faster relocalising, they are treated as camera data under Section 9 [E, owner choice]. The hardware green dot lights while any camera is powered (Section 9).
8. **The light shows mapping, and only mapping.**
   - **When it shows:** while any ToF sensor, camera mapping, Wi-Fi ranging or Wi-Fi sensing runs.
   - **The pattern:** the four edges around the top face glow steady and dim, and the other eight edges stay free for other modes [E]. No other mode in Section 5 lights only the top ring and holds it still, so the shape alone tells it apart, for colour-blind users too [E].
   - **Colour rules:** pale magenta, used for nothing else. On RGB LEDs behind dark material it can look like violet ("Asking a question"), so test the two side by side on a sample [E].
   - **When it stops:** the cube goes dark and is a plain black box again.
   - Add this as a "Mapping" row to the Section 5 mode table.
9. **Hard mute covers depth sensing too.** The hard-mute switch (Section 9) should also cut power to the ToF sensors [E]. Soft mute stops mapping in firmware. Hard mute cannot cut Wi-Fi sensing or Wi-Fi ranging, because the radio stays on for the network. Under hard mute, firmware turns both off. The app labels this part as software-only, like soft mute [E].
10. **Access-point lists are location data.** A router's hardware address (BSSID) can be looked up to a street location. Researchers pulled the locations of over 2 billion of them from Apple's public positioning service [M, S129]. So any access-point address the cube stores, for ranging or room hints, is treated like precise location: kept on the cube, encrypted, never sent out by default, and deleted with the map [E].
11. **Retention.** Pose history and the motion log keep 7 days by default. The owner can change this in the app [E, owner choice]. Map cells keep their dates and age out of decisions (8a.5).
12. **Other people in the home.** The consent flag belongs to the account holder. Others in the home, and guests, are mapped and sensed without giving their own consent. The Mapping light is their notice. The app offers a guest mode that pauses mapping and Wi-Fi sensing [E].
13. **Open choice for the owner:** should the ToF sensors get a hardware-wired indicator like the cameras, or is the firmware Mapping pattern enough? [E]
14. **Law** (not legal advice): a home map linked to a person is likely personal data in the EU [E]. The rules in Section 9 apply.

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
| Room depth sensor, one per face (first pick) | VL53L7CX (ST) | 8 × 8 at up to 15 Hz or 4 × 4 at up to 60 Hz; 60° × 60° (90° diagonal); range 4 × 4 dark white 3.5 m, 8 × 8 dark white 2.0 m, 8 × 8 dark grey 0.8 m, 5 klux 0.5–0.65 m, all without cover glass; minimum 2 cm; 940 nm Class 1; 6.4 × 3.0 × 1.6 mm; continuous 216–313 mW; autonomous 1 Hz 5.4 mW (4 × 4) or 19 mW (8 × 8); I2C only, 1 MHz, address 0x52; receive window ≥ 74° × 74° | [M] | Good within about 2 m; needs an infrared window; six needed | S127, S122 |
| Room depth sensor, alternative | VL53L8CX (ST) | 8 × 8 at up to 15 Hz, 4 × 4 at up to 60 Hz; 45° × 45° (65° diagonal); up to 400 cm; 940 nm Class 1; cover-glass crosstalk handled beyond 60 cm; about 84 KB firmware loaded at start-up; 6.4 × 3.0 × 1.75 mm; about 215 mW continuous; 1.6 mW at 4 × 4, 1 Hz in low-power mode (one user measured about 68 mW); I2C (1 MHz) or SPI (20 MHz); address 0x52, one LPn line per sensor; 8 × 8 range not checked [check DS14161] | [M; size and power secondary] | Narrower view; better in bright rooms | S120, S121 |
| Dense depth sensor, watch | VL53L9CX (ST) | 2,268 zones (54 × 42); 55° × 42°; under 5 cm to 8.8 m; up to 100 Hz; 12.8 × 6.1 × 4.6 mm; MIPI I3C or CSI; power not published; ST said mass production would start in early July 2026 (not confirmed); also streams a 2D infrared image (camera-class); cover-glass note AN6346 | [M, secondary] | Watch: power unknown; the camera port is already busy | S124, S131 |
| ToF window, one per face | Visible-black, infrared-passing filter or ink (example: Phillips NIR acrylic filters) | Black to the eye; passes near-infrared above a cut-on of 670–910 nm; 0.5–5.0 mm thick; 940 nm transmission not stated [check]. ST's VL53L7 note asks for over 87% at 940 nm [S123]; opening ≥ the 74° × 74° receive cone [M, S127] | [M] / [check] | Needed; matching the face's look must be proven on a sample | S25, S123, S127 |
| Wi-Fi ranging and sensing (existing radio) | IW612 (NXP) | 1×1, channels up to 80 MHz; FTM ranging as a client: 802.11mc, 802.11az non-trigger-based and trigger-based (AN14044 Rev. 3.0, 29 April 2026); also an FTM responder (802.11mc, 802.11az non-trigger-based); trigger-based ranging validated only with an NXP in-house access point; line of sight needed for stable readings; mlanwls in board packages from kernel 6.18.2; CSI and Ambient Motion Index on Linux (AN14011 Rev. 10.2, 25 June 2026); no 802.11bf statement found | [M] | Good; no new part | S53, S111, S112 |
| Gyroscope and accelerometer figures (existing part) | BMI323 (Bosch) | Gyroscope zero offset ±1 °/s, ±0.04 °/s/K, noise 0.007 °/s/√Hz; accelerometer zero offset ±50 mg, ±0.3 mg/K, noise 180 µg/√Hz; scale error after self-calibration down to ±0.7% (best case); fast start 2.5 ms; supply 1.71–3.63 V | [M, preliminary flyer; start-up time via search summary] | Good for turns; not for distance | S101, S70 |
| Orientation fusion (existing part) | LSM6DSV16X (ST), SFLP block | Game rotation vector, gravity vector, gyroscope bias; 15 µA press figure not tied to tracking with the gyroscope on; budget 0.65 mA with the gyroscope on; bias estimated only while still; gyroscope noise 0.0028 °/s/√Hz (ST product page, via search summary) | [M, secondary] | Good; heading still drifts without a compass | S102, S72, S103 |
| GNSS receiver, not fitted | MAX-M10S (u-blox) | 25 mW continuous tracking; 1.5 m CEP with satellites at −130 dBm; cold start 27 s with every satellite at −130 dBm (default constellations); sensitivity shown with a good external LNA; cold-start sensitivity −148 dBm | [M] | Not fitted: indoors, sealed cube, power | S107 |
| Spinning lidar, size reference | RPLIDAR C1 (Slamtec) | 55.6 × 55.6 × 41.3 mm; 110 g; 1.15 W; 360° at about 10 Hz | [M, distributor] | Does not fit | S126 |
| Ranging to the phone, watch | Bluetooth Channel Sounding (Bluetooth 6.0) | Claimed 10–50 cm; the IW612 is Bluetooth 5.4, so it is not available | [M, secondary] | Version 2 only | S83, S53 |

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

**Location, motion and mapping (Section 8a).** st.com pages timed out during this check. ST figures come from ST documents hosted elsewhere (the Pololu copies of UM3109 and of the VL53L7CX datasheet DS13865, ST's China-site flyer), distributor pages, or search summaries, and are tagged that way.
- S101 https://storage.microchipusa.com/musadev/datasheetpdf/BST-BMI323-FL000-00.pdf (Bosch BMI323 flyer BST-BMI323-FL000-00, version 1.0, 09/2022; marked preliminary)
- S102 https://circuitdigest.com/news/new-advanced-6-axis-inertial-measurement-unit-with-embedded-sensor-fusion-and-ai (25 Nov 2022) ; https://st.com/LSM6DSV16X (ST product page; noise figure read through a search summary) ; https://community.st.com/mems-and-sensors-62/how-lsm6dsv16x-enables-sensor-fusion-low-power-sflp-algorithm-120280 ; https://community.st.com/t5/mems-sensors/lsm6dsv16x-gyroscope-bias/td-p/714927 (ST forum; read through a search summary)
- S103 https://docs.luxonis.com/hardware/platform/sensors/imu/lsm6dsv (sibling LSM6DSV, not the 16X)
- S104 https://lcv.fee.unicamp.br/wp-content/images/BTSym-22-Brasil/papers/paper_057.pdf ; https://arxiv.org/pdf/1503.07889 (error growth in dead reckoning; zero-velocity updates)
- S105 https://arxiv.org/abs/1708.03852 (VINS-Mono, monocular visual-inertial estimator)
- S106 https://bme.vgtu.lt/index.php/GAC/article/download/10878/9202 (indoor GNSS attenuation: 5–15 dB houses, 20–30 dB offices; read through a search summary)
- S107 https://content.u-blox.com/sites/default/files/MAX-M10S_DataSheet_UBX-20035208.pdf (UBX-20035208 R08, 30 Jan 2026)
- S108 https://developer.android.com/develop/sensors-and-location/location/permissions
- S109 https://static.usenix.org/events/mobisys05/tech/full_papers/cheng/cheng_html/index.html (Place Lab, MobiSys 2005) ; https://developers.google.com/maps/documentation/geolocation/overview
- S110 https://source.android.com/docs/core/connect/wifi-rtt
- S111 https://www.nxp.jp/docs/en/application-note/AN14044.pdf (NXP AN14044, Rev. 3.0, 29 April 2026)
- S112 https://www.nxp.com/docs/en/application-note/AN14011.pdf (NXP AN14011, Rev. 10.2, 25 June 2026)
- S113 https://people.csail.mit.edu/bkph/FTMRTT_aps (community-maintained list; currency uncertain)
- S114 https://arxiv.org/abs/2509.03901 (FTM survey, 4 Sep 2025)
- S115 https://standards.ieee.org/ieee/802.11bf/11574/ (IEEE 802.11bf-2025)
- S116 https://arxiv.org/abs/2302.00992 (Cominelli, Gringoli, Restuccia, IEEE PerCom 2023)
- S117 https://repositum.tuwien.at/handle/20.500.12708/222429 (Strohmayer, TU Wien dissertation, 2025; record not yet verified by the library)
- S118 https://arxiv.org/abs/2403.02235 (Structure from WiFi, ACC 2024)
- S119 https://www.bleepingcomputer.com/news/security/comcast-turns-your-xfinity-wifi-into-a-home-motion-detector/ (article dated 18 Aug 2026)
- S120 https://www.pololu.com/file/0J2030/um3109-a-guide-for-using-the-vl53l8cx-lowpower-highperformance-timeofflight-multizone-ranging-sensor-stmicroelectronics.pdf (ST UM3109 Rev 7, April 2024; Pololu-hosted copy)
- S121 https://www.st.com.cn/resource/en/flyer/vl53l7cx-vl53l8cx-flyer.pdf ; https://www.st.com/en/imaging-and-photonics-solutions/vl53l8cx.html ; https://wiki.adom.inc/kyle/vl53l8cx (secondary, unreviewed) ; https://community.st.com/imaging-sensors-49/vl53l8cx-power-consumption-is-too-high-139035 (forum) (ST pages read through search summaries)
- S122 https://www.pololu.com/product/3418 ; https://www.pololu.com/category/306/carriers-for-st-time-of-flight-tof-distance-sensors
- S123 https://www.st.com/resource/en/application_note/an5939-guidelines-for-the-cover-glass-of-the-vl53l8-timeofflight-tof-multizone-sensor-family-stmicroelectronics.pdf ; https://www.st.com/resource/en/application_note/an5962-guidelines-for-the-cover-glass-of-the-vl53l7-timeofflight-multizone-sensor-family-stmicroelectronics.pdf (did not load; the >87% at 940 nm figure was read through search summaries; the >87% wording is confirmed for AN5962 (VL53L7) and AN6346 through search summaries; AN5939's wording is not confirmed)
- S124 https://www.cnx-software.com/2026/06/22/st-vl53l9cx-direct-time-of-flight-3d-lidar-supports-5cm-to-9m-range-2-3k-zones-resolution/ ; https://www.st.com/vl53l9cx
- S125 https://www.hrl.uni-bonn.de/papers/hornung13auro-preprint.pdf (Hornung et al., OctoMap, Autonomous Robots 34:189–206, 2013)
- S126 https://www.waveshare.com/rplidar-c1.htm (distributor listing)
- S127 https://www.pololu.com/file/0J1992/vl53l7cx.pdf (ST DS13865 Rev 6, March 2023; Pololu-hosted copy; read in full)
- S128 https://arxiv.org/abs/1904.03303 (Pittaluga, Koppal, Kang, Sinha, "Revealing Scenes by Inverting Structure from Motion Reconstructions", CVPR 2019)
- S129 https://arxiv.org/abs/2405.14975 (Rye and Levin, "Surveilling the Masses with Wi-Fi-Based Positioning Systems", 2024; venue not confirmed)
- S130 https://csrc.nist.gov/pubs/sp/800/88/r2/final ; https://csrc.nist.gov/files/pubs/sp/800/88/r2/final/docs/sp800-88r2-faq.pdf (NIST SP 800-88 Rev. 2, September 2025; read through search summaries)
- S131 https://www.st.com/resource/en/application_note/an6346-guidelines-for-the-cover-glass-of-the-vl53l9cx-timeofflight-2k-zones-stmicroelectronics.pdf (did not load; read through a search summary)

**Amendments to sources listed in earlier sections:**
- S70: add "BMI323 datasheet rev 1.6, Aug 2025: fast start 2.5 ms (read through a search summary)".
- S25: add "(first link returned 404 on 2026-10-21)".

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