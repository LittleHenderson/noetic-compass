# HELM Cube: interaction, light, companion app, and safety

Scope: this is research and a design proposal only. Nothing was built and no money was spent. Every number is tagged:
- **[SRC]** means MEASURED-BY-SOURCE: it comes from a datasheet, a rule, a standard, or the cited page.
- **[EST]** means ESTIMATE: it is my own design guess.

Where a source is only secondary (a forum, a blog, a distributor listing, or a patent), the note says so. Part numbers appear only where a source names them.

## 0. HELM states the cube must show (from the repo, read-only)

I read these states in the code. The light and the gestures below map to them.
- **`UNDETERMINED`**, with gate code `G-ABSENT`. The RPM gate (the check that every needed input is present) stops the run. It names the missing input as `limiting_reagent`. It sets `invented_facts: 0`.
  - File: `C:\Users\wakil\OneDrive\Desktop\tksCAS\helm_brain_22x40.py`, lines 112-136.
  - A comment there says the system "refuses to guess".
- **`CLARIFY_REFUSAL`**, **`STORE_CLARIFY`**, **`STORE_REFUSAL`**, **`READ_COMPLETED`** and **`INVENTORY_RECORDED`**. Each turn also gets a `receipt_hash`.
  - File: `C:\Users\wakil\OneDrive\Desktop\tksCAS\helm_end_to_end_loop.py`, lines 286-354.
- **`STUDY_REFUSAL`** and **`GATE_REFUSE`**.
  - File: `C:\Users\wakil\OneDrive\Desktop\tksCAS\helm_chat.py`, lines 388-397.

**Design rule taken from these states:** a gesture or a light can never supply a missing fact.
- Taps can only say yes, no, repeat, skip, or stop.
- A question that is skipped stays `UNDETERMINED`.
- An unclear tap sequence is not counted. The cube does not guess what you meant.

## 1. Shake to wake and taps: the motion sensor (IMU)

### Real parts that can do it

| Part | What the source says | Numbers |
|---|---|---|
| Analog Devices ADXL367 (accelerometer only) | Wakes on motion; single- and double-tap detection | 180 nA in motion-wake mode; 0.89 µA at 100 Hz; 40 nA standby; tap detection adds 35 nA; 512-sample buffer; 2.2 × 2.3 × 0.87 mm [SRC, from a Rev. 0 datasheet copy, so check the current revision] |
| Bosch BMI323 (accelerometer + gyroscope) | Single, double **and triple** tap on the chip; motion and orientation detection | 790 µA in high-performance mode with both sensors on; 2.5 × 3.0 × 0.83 mm; 1.71-3.63 V [SRC] |
| ST LSM6DSV16X (accelerometer + gyroscope) | Free-fall, wake-up, 6D/4D orientation, single and double tap ("click"); Qvar charge sensing | 0.65 mA in high-performance mode [SRC, distributor listing; the datasheet fetch timed out] |

- A Bosch support engineer warns that tap interrupts can fire on vibration or on the device rubbing against a surface [SRC, qualitative].
- In ST's tap register, the sensor reports **which axis was struck (X, Y or Z) and the sign** (the TAP_SIGN bit) [SRC, ST forum thread].
  - Combine that with the gravity direction (which face is down) and the cube knows which face was tapped.
  - Resting on a table, 5 faces can be tapped. Held in the hand, all 6 can [EST].
- Four or five taps are not built into any of these chips. The microcontroller counts single taps instead. An ST moderator confirms that tap types must be told apart in the microcontroller [SRC].

**Proposed setup [EST]:**
- An ADXL367 stays on all the time as the "sentry". It catches the shake at nano-amp current.
- A 6-axis IMU (BMI323 or LSM6DSV16X) powers up only when the cube is awake. It reads tap direction and rotation.
- Do not use a magnetometer (compass sensor) to tell faces apart. A Qi2 magnet ring would distort it [EST].

### Timing (starting values, to tune on real hardware)

- One ST forum example ran at 416 Hz and ±2 g. It used a tap threshold of 562.5 mg, a 38.5 ms shock window and a 9.6 ms quiet window [SRC, forum example, not official guidance].
- My starting values [EST]:
  - Each tap's impulse lasts 40 ms or less.
  - The gap between taps is 100-450 ms.
  - The sequence ends after 600 ms of quiet.
  - The "attention window" after a shake is 8 s.

### Stopping false triggers from bumps [all EST]

1. **Taps count only after a shake.** The one exception is the privacy gesture, because it only ever makes the cube safer.
2. **Reject bumps that come up through the table.** A resting cube cannot be tapped on its bottom face. So any impulse that comes from below is a table knock, not a tap.
3. **Free-fall or a large rotation means "dropped or lifted".** Tap counting pauses for 1 s.
4. **Pocket guard.** Shake-to-wake opens the microphones only after the shake is followed by 300 ms of stillness. If the cube keeps moving (walking, in a bag), it stays asleep.
5. **Optional sound check.** When the microphones are already live, a tap must also make a matching knock sound within a few milliseconds.
6. **Unclear sequences are not counted.** Example: one gap sits right on the timing limit. The cube flashes "not counted" and logs it in the app. It never guesses whether you meant 2 or 3.
7. **Feedback on every tap.** Each counted tap lights a brief tick on the face that was struck, so the user sees what was counted.

### Tap grammar

**Main rule:** the number of taps is the verb, and the face is the target. The top face means HELM itself. The side faces mean devices you bind in the app.

| Gesture | Face | When it works | Normal action | When HELM is asking a question |
|---|---|---|---|---|
| Shake (2 bursts within ~1 s [EST], then still) | any | asleep or awake | Wake and listen | Drop the question; it stays `UNDETERMINED` |
| 1 tap | top | awake | Stop / hush (stop talking, cancel) | **Yes** (yes/no questions only) |
| 2 taps | top | awake | Repeat the last answer | **No** |
| 2 taps | side face bound to a device | awake | Toggle that device (on/off) | not accepted |
| 3 taps | top | awake | Run a favourite scene | **Repeat the question** |
| 3 taps | bound side face | awake | Next step for that device (brightness, next track, next scene) | not accepted |
| 4 taps | top | awake, then confirm by voice or in the app | Open the pairing window (Bluetooth + Matter setup). The light shows a countdown. | not accepted |
| 5 taps | any | **always, even asleep** | Privacy ON (soft: firmware turns cameras and microphones off) | Privacy ON |
| Shake, then 5 taps | any | awake | Privacy OFF, after a 3 s countdown that 1 tap cancels | — |
| Set it upside down on its top face (charging face up, like a phone face-down) | — | always | **HARD privacy** (section 4) | Hard privacy |
| Phone held against the cube | — | during setup | NFC "tap to connect": Matter 1.4.1 NFC setup [SRC: feature exists] | — |

**Safety rule:** taps can never unlock doors, disarm alarms, or open garage doors or gates. Matter 1.5 adds garage doors and gates to its device types [SRC]. Those actions need voice plus confirmation in the app.

## 2. The light strip

### Where to put it on the cube

| Option | Good | Bad |
|---|---|---|
| Light along all 12 edges (a glowing wireframe) | Dramatic | Corners are hard to light evenly; bottom edges are hidden; about 3× the LEDs [EST] |
| **A belt around the middle, built into the seam where the two shell halves meet (recommended)** | One band can be seen from every side; the manufacturing seam becomes the light, so there is no extra visible line; the Qi coil face is the natural base, so the belt sits level | When the cube is set on a side face, part of the belt is hidden |
| A ring on the top face only | Simple | Cannot be seen from the side at table height |

**Light pipe and diffuser:**
- Use "hidden-until-lit" translucent black plastic. It looks black when off and glows when lit.
- A patent for a portable voice assistant claims a translucent black light bar about 1 mm thick, with 35-75% light transmission. It has raised diffuser bumps lined up with each LED and a reflector behind [SRC: US 10620913, a patent, not a confirmed shipping product].
- One related patent notes that diffuser features on clear material stay visible when unlit. That is the reason to use the tinted outer skin [SRC].

**LEDs:**
- SK6805-E-J addressable RGB LED (one that takes colour commands over a data line). Package is 1.5 × 1.5 mm, about 18 mA constant current per channel [SRC: Adafruit listing].
- Inolux IN-PI15TAT5R5G5B, also 1.5 × 1.5 mm [SRC: DigiKey listing].

**Size of the belt [EST]:**
- About 24 LEDs on a 50 mm cube, or 32 on a 65 mm cube (one LED every 8 mm).
- Limit brightness to 5-10%, which gives about 30-130 mA. Full white would draw over 1 A.
- Addressable LEDs draw some current even when dark. Cut their power with a switch while the cube sleeps [EST].

**Camera-on dots are separate from the belt.** Each face gets a tiny hidden-until-lit dot. The dot is powered by that face's camera power line, not by a software-controlled pin (section 4).

### Light modes

Each mode must be readable by its motion alone, so colour-blind users can tell them apart. Each also gets a short sound. All colours and timings are [EST] design choices. The Amazon Echo already uses blue for listening, red for mic off, and orange for setup [SRC, secondary guides]. Reusing those learned meanings helps users.

| Mode | HELM state | Colour | Motion |
|---|---|---|---|
| Asleep / idle | — | off (fully dark) | none. An optional "presence glow" of one segment at 2% can be turned on in the app. |
| Awake | after a shake | soft white | one sweep around the belt, then dim |
| Listening | microphones live | cool white / cyan | an arc that **points toward the person speaking** (six microphones can tell the direction) |
| Thinking | parsing, RPM gate checking, waiting on cloud speech | gold | two dots orbit. Shown only if it takes over 300 ms. |
| Speaking | voice output | warm white | brightness follows the speech loudness: 30-50 ms rise, 100-150 ms fall, which pulses at the syllable rate (about 4-5 per second) |
| Asking a question | `CLARIFY`, `STORE_CLARIFY` | violet | "question rhythm": short, short, long, every 2 s; then listening opens |
| **UNDETERMINED** | `UNDETERMINED` (`G-ABSENT` / `G-LIMIT`) | amber ring with **one dark segment** | The dark gap slowly pulses. The ring is the recipe; the dark gap is the missing input. HELM says which input is missing. The light holds until the input is given or the question is skipped. |
| Declined | `*_REFUSAL`, `GATE_REFUSE` | dim amber | the belt shrinks to one segment and fades. Not red, because red means privacy. |
| Privacy, soft | 5-tap mute (firmware) | red | slow breathing |
| Privacy, hard | gravity switch open | solid red | steady. Powered through the hardware switch, not firmware. |
| Charging | on the Qi pad | green | the arc length shows the charge level for 5 s after you set it down, then goes dark |
| Low battery | 15% or less / 5% or less | amber / orange | one blink every 10 s / two blinks every 10 s |
| Pairing | setup window open | blue | a chase around the belt; the arc shrinks as the window runs out |
| Device acknowledged | tap on a bound side face | that device's colour | a brief flash on the struck face |
| Error | the machine failed (no network, speech service down) | orange | two blinks, then dim steady. Kept separate from `UNDETERMINED`, which means missing information, not a failure. |
| Eye report | Unity Eye filed a report | teal | one small blip. It means "a report is in the app" and never implies the Eye acted. |
| Updating | firmware update | white | slow chase |

## 3. Controlling other devices

- **Matter.** The phone usually acts as the "commissioner" that adds a device. A "controller" then runs the device day to day [SRC: SmartThings, NXP].
  - Matter 1.4.1 (May 2025) adds NFC tap setup and one QR code that sets up several devices [SRC].
  - Matter 1.5 (November 2025) adds cameras (WebRTC video, privacy zones), closures (shades, gates, garage doors) and energy features [SRC].
  - **Recommendation [EST]:** the cube joins the home system the user already has (Apple Home, Google Home, SmartThings, Alexa) as one more administrator, using Matter multi-admin. It does not replace those systems.
- **Thread.** Thread devices need a Thread Border Router (a box that bridges Thread to Wi-Fi) [SRC].
  - Apple TV, Nest, some Echo models and IKEA DIRIGERA already include one [SRC, forum].
  - Version 1 can rely on the user's existing border router [EST].
- **Radio chips:**
  - ESP32-C6: Wi-Fi 6, Bluetooth 5 LE and 802.15.4 (Thread/Zigbee). Espressif says a border router is the C6 paired with a second chip [SRC].
  - Nordic nRF54L15: Bluetooth LE with Bluetooth 6.0 Channel Sounding, plus 802.15.4 for Thread, Matter and Zigbee. Wi-Fi needs an nRF70 companion chip [SRC].
- **Bluetooth Channel Sounding** could later let you point the cube at a device. Reported accuracy varies by source, from about 10-50 cm to 0.5 m [SRC, secondary, they conflict].
- **The companion app as hub:** it adds devices, binds them to faces, and defines scenes. The cube runs the actions.

## 4. Privacy with six hidden cameras

**The social fact:** Airbnb banned all indoor security cameras from 30 April 2024. The ban applies even if they are disclosed [SRC]. Cameras nobody can see will be read as covert surveillance. **Hide the lenses, never hide whether they are on.**

1. **Microphones are off while asleep.** Shake-to-wake removes the need for an always-listening wake word, which is a privacy selling point. A wake word could be an opt-in extra, processed only on the device [EST].
2. **Cameras are off by default and turn on only when asked** ("look at this"). Every power-on is logged in the app from a hardware status line [EST].
3. **A hardware-wired indicator for each face.** Each camera's power line feeds its own face dot directly.
   - Researchers showed that older Mac camera lights could be bypassed because firmware controlled the link [SRC: Johns Hopkins work, as reported].
   - Apple's hardware microphone cut on laptops is described as resistant even to root-level software [SRC].
4. **Hard privacy:** turn the cube upside down. A mechanical gravity (ball-tilt) switch opens the camera and microphone power lines, so no software can override it [EST]. The tilt switch needs vibration testing.
   - Soft privacy (5 taps) is firmware only. The app and the light label it honestly as "soft".
5. **No face recognition by default.**
   - Illinois BIPA requires consent from anyone the cameras might identify [SRC, vendor guidance].
   - Google disables Nest face recognition in Illinois [SRC, secondary].
   - A suit over Arlo camera face scanning survived a motion to dismiss [SRC].
6. **GDPR.** The household exemption is lost if a camera captures any public space, for example through a window. This comes from the EU court case Ryneš, C-212/13, 2014 [SRC].
7. **Never expose the cameras to Matter** (as Matter 1.5 cameras) by default [EST].

## 5. Certifications and rules

| Area | Requirement | Status |
|---|---|---|
| US radio | FCC Part 15 Subpart C certification through a TCB (a private lab the FCC authorises to grant approvals). Pre-certified modules help, but the finished product still needs combined testing (KDB 996369). | [SRC: grant documents] |
| US RF exposure (radio energy absorbed by the body) | Module grants often assume 20 cm separation. A handheld product needs a Class II permissive change or a new application, plus a SAR/MPE evaluation. | [SRC] |
| Qi pad | The FCC exclusion for wireless chargers (KDB 680106) needs, among other things, 15 W or less per coil, under 1 MHz, and contact use. A **25 W** pad exceeds the power condition, so it needs a full evaluation. | [SRC: lab filing citing v03; the 25 W conclusion is my inference] |
| FCC label | The FCC ID must be on the device. Only if it is too small for 4-point type may it go in the manual plus the packaging or a removable label (47 CFR 2.925). E-labels (2.935) are only for devices with a display or used only with one, which this cube likely is not [EST]. **So "visible nowhere" needs a tiny etched regulatory line on the base.** | [SRC] |
| EU radio + cybersecurity | CE under the Radio Equipment Directive. Cybersecurity rules (Regulation 2022/30) have been mandatory since **1 August 2025**, via EN 18031-1, -2 and -3 (2024). Cameras and microphones mean -2 (data and privacy) applies. | [SRC] |
| EU Cyber Resilience Act | Vulnerability and incident reporting has applied since **11 September 2026**. Full application is **11 December 2027**. | [SRC] |
| **EU battery removability** | From **18 February 2027**, users must be able to remove and replace portable batteries (Regulation 2023/1542, Art. 11). The new exemption act adopted 14 July 2026 covers six other product types, and it was not yet in force when the source was written. **A sealed cube conflicts with this rule.** It needs a user-openable base. | [SRC; that it applies to this cube is my inference] |
| EU USB-C rule | The Commission says its rules cover wired charging and that wireless rules are "premature". A Qi-only device appears to be outside the rule. The 30 June 2026 report proposed more product types. | [SRC] |
| EU disposal mark | Crossed-out bin symbol at least 7 mm (EN 50419), or on the packaging if the product is too small. The 5 mm CE-mark minimum is from memory and not confirmed. | [SRC / not verified] |
| Safety | Device: IEC/UL 62368-1. Battery: IEC/UL 62133-2 and UL 2054. Shipping: UN 38.3 (Apple lists the same set). Touch-temperature limits under 62368-1 matter because Qi charging heats a small sealed cube held in the hand; I could not confirm the exact limit. | [SRC] |
| Qi logo | Requires WPC membership, testing at an authorised lab, and a database listing. Using the "Qi2" name requires magnets. Qi2 25W certification began around mid-2025. "Supercharging" is not a WPC term, so call it "Qi2 25W". Membership is about USD 15-25k per year (secondary source, may be dated). | [SRC] |
| Matter logo | CSA certification at an authorised test lab, then listing on the Distributed Compliance Ledger. | [SRC] |
| Bluetooth logo | SIG qualification and a declaration (QPRD v4, 21 July 2025), even when using a pre-certified module. | [SRC] |
| US Cyber Trust Mark | Voluntary. UL withdrew as administrator effective 19 December 2025. The FCC picked ioXt on 13 April 2026. | [SRC] |
| Charging heat | Pause charging if the cell is outside about 0-45 °C | [EST] |

## 6. Companion app: main screens [EST]

1. **Now:** awake or asleep, battery and charging, privacy state (HARD / SOFT / OFF) read from hardware status lines, the last answer and its `receipt_hash`.
2. **Conversation and receipts:** each turn with its HELM status (`EVALUATED` / `UNDETERMINED` / `CLARIFY` / `*_REFUSAL`), the gate code, the limiting input, and the receipt.
3. **Open Questions:** every pending `UNDETERMINED` question, answered by typing. Nothing is ever filled in automatically.
4. **Gestures:** a 3D face map, an editor for counts × faces, a live practice mode, a sensitivity setting, and an honest list of rejected bumps.
5. **Devices and scenes:** add devices by Matter QR or NFC, multi-admin sharing, binding devices to faces. Locks and gates are blocked from taps.
6. **Light:** the mode legend, brightness, night dimming, the presence glow, patterns for colour-blind users.
7. **Privacy and data:** per-face camera and microphone switches, a log of every camera and microphone power-on, retention, delete, on-device vs cloud speech, face recognition off (opt-in needs written consent).
8. **Unity Eye reports:** the list is labelled "the Eye reports; it does not act".
9. **Setup, updates and regulatory info:** this is in addition to the label on the device, not a replacement for it.

## Sources

- https://www.mouser.com/datasheet/3/1046/1/bst_bmi323_ds000.pdf
- https://www.bosch-sensortec.com/products/motion-sensors/imus/bmi323/
- https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/Reliability-for-TAP-detection-on-BMI270-and-Inquiry-on-TAP/m-p/101069
- https://www.digikey.com/en/product-highlight/s/stmicroelectronics/lsm6dsv16x-inemo-3-axis-accelerometer-and-gyroscope
- https://community.st.com/t5/mems-sensors/how-to-calibrate-tap-sensing-lsm6dsm/td-p/203243
- https://community.st.com/t5/mems-sensors/single-and-double-tap-on-lsm6dsl/m-p/584105
- https://community.st.com/t5/mems-sensors/lsm6dsox-int1-int2-both-interrupt/m-p/74668
- https://cdn.sparkfun.com/assets/2/e/1/8/6/adxl367.pdf
- https://analog.com/en/products/adxl367.html
- https://support.apple.com/111772
- https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10620913
- https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11346523
- https://patents.justia.com/patent/11485281
- https://www.adafruit.com/product/4492
- https://www.digikey.es/en/products/detail/inolux/IN-PI15TAT5R5G5B/14555725
- https://www.androidcentral.com/what-all-color-rings-mean-your-amazon-echo
- https://gizmodo.com/amazon-echo-colors-meaning-1848775533
- https://digprjsurvey.amazon.com/csad/help/node/GKA25FVYEV5PY8C9
- https://gigazine.net/gsc_news/en/20250319-amazon-echo-mute
- https://csa-iot.org/newsroom/matter-1-5-introduces-cameras-closures-and-enhanced-energy-management-capabilities/
- https://homekitnews.com/2025/05/07/csa-offers-user-friendly-features-with-matter-1-4-1/
- https://www.nxp.com/company/about-nxp/smarter-world-blog/BL-MATTER-TERMINOLOGY
- https://support.smartthings.com/hc/en-us/articles/11219700390804
- https://community.openhab.org/t/ikea-launches-matter-devices-2026-will-we-need-a-hub/167105
- https://www.espressif.com/en/products/socs/esp32-C6
- https://www.nordicsemi.com/Products/nRF54L15
- https://www.ezurio.com/channel-sounding
- https://hubble.com/community/guides/bluetooth-channel-sounding-explained-how-ble-now-measures-distance/
- https://www.schneier.com/blog/archives/2026/03/apples-came=
- https://support.apple.com/bg-bg/guide/security/secbbd20b00b/web
- https://abc7news.com/airbnb-indoor-security-cameras-host-changes-doorbell-cams/14514564/
- https://www.rhombus.com/blog/staying-in-compliance-with-ccpa-and-bipa-for-video-security
- https://news.bloomberglaw.com/litigation/class-action-privacy-suit-over-person-detection-ai-moves-ahead
- https://www.hunton.com/privacy-and-cybersecurity-law-blog/cjeu-adopts-strict-approach-use-cctv
- https://fccid.io/2AJVQMWH566B
- https://www.espressif.com/sites/default/files/ESP32-C3-WROOM-02%20FCC%20Certification.pdf
- https://speag.com/assets/downloads/products/dasy/application-notes/WPT/DASY8_Module_WPT_Application_Note_Compatibility_with_KDB_680106V2.pdf
- https://www.law.cornell.edu/cfr/text/47/2.925
- https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-2/subpart-J/subject-group-ECFRd5ad3b739dbf27a/section-2.935
- https://www.element.com/resources/articles/cybersecurity-and-the-red
- https://digital.gob.es/content/dam/portal-mtdfp/avance-digital/telecomunicacion-e-infraestructuras-digitales/areas_interes/equipos-telecomunicacion/documents/Guia-aplicacion-EN-18031.pdf
- https://www.traverssmith.com/knowledge/knowledge-container/the-eu-cyber-resilience-acts-vulnerability-and-incident-reporting-requirements-are-now-live/
- https://finitestate.io/blog/cyber-resilience-act-timeline-2026-2027
- https://en.reach24h.com/news/industry-news/sustainability/eu-portable-battery-removability-exemptions-2026
- https://www.compliancegate.com/removable-and-replaceable-battery-requirements-european-union/
- https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/radio-equipment-directive-red/one-common-charging-solution-all_en
- https://productip.com/kb/productipedia/compliance-resources/crossed-out-wheeled-bin
- https://support.apple.com/en-au/103766
- https://www.element.com/resources/articles/lithium-ion-battery-certification
- https://japan.ul.com/wp-content/uploads/sites/27/2014/06/1_techbrief_touchtemp.pdf
- https://wirelesspowerconsortium.com/knowledge-base/testing-and-certification/authorized-test-labs
- https://www.wirelesspowerconsortium.com/media/iyfpemdt/wpc-logo-guidelines-revised-23oct2025.pdf
- https://www.androidcentral.com/phones/qi2-does-not-require-magnets
- https://www.belkin.com/company/blog/25w-wireless-charging-guide/
- https://www.podfeet.com/blog/2026/05/ces-2026-wireless-power-consortium/
- https://www.avnet.com/wps/portal/us/resources/article/how-to-get-your-qi-project-certified-by-the-wireless-power-consortium
- https://wiki.st.com/stm32mcu/wiki/Connectivity:Matter_certification_process
- https://docs.silabs.com/matter/2.2.2/matter-certification
- https://www.bluetooth.com/download/qprd-document
- https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrf/protocols/bt/bt_qualification/index.html
- https://broadbandbreakfast.com/fcc-picks-ioxt-alliance-to-head-cyber-trust-mark-program/
- https://www.ioxtalliance.org/news-events-blog/ul-solutions-withdraws-as-lead-administrator-for-fccs-cyber-trust-mark-program

**Not verified in this pass:**
- The full LSM6DSV16X datasheet (the fetch timed out). Its state-machine and machine-learning features are not claimed here.
- The exact TS1 touch-temperature limit under IEC 62368-1.
- The 5 mm CE-mark minimum.
- The Matter setup-window maximum time.
- Whether the July 2026 battery exemption act has been published.