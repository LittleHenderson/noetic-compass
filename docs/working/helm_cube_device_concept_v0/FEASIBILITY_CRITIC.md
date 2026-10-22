1. §8 job table, row "Shake and tap detection", and §6 "Always on". The draft says the M33 core can count taps for under 1 mW, which is wrong. In NXP AN13917, Rev. 4.0, the 7.6 mW deep-sleep figure has "The CM33 ... in reset hold". "Linux Suspend + M33 in WFI" measured 122.4 mW. At that sleep power, typical life drops from about 10 days to about 3.3 days.
   Replace the row with: "| Shake and tap detection | ADXL367 alone while asleep. It wakes the i.MX 93 by interrupt and keeps the raw motion in its FIFO until the processor is up | Well under 0.01 mW asleep [M, S74]. Do not keep the M33 awake for this job. NXP measured 'Linux Suspend + M33 in WFI' at 122.4 mW, against 7.6 mW in deep sleep with the M33 held in reset [M, S57]. If a processor must count taps while the cube sleeps, use a separate tiny microcontroller, such as the nRF54L15 [S82] [E]. |"

2. §6 Sensors, ADXL367 bullet, and the 5-tap row. The ADXL367 detects single and double taps on only one axis, chosen in its TAP_AXIS register. It does not report which face was struck. Its datasheet also says tilting can fire a tap below a 1 g threshold.
   Replace the bullet with: "Always on: Analog Devices ADXL367 accelerometer. It draws 180 nA in motion-wake mode and 40 nA in standby. It detects single and double taps for 35 nA more, but only along one axis chosen in its TAP_AXIS setting, and it does not report which face was struck. Below a 1 g tap threshold, tilting can also register as a tap [M, Rev. 0 datasheet copy, S74]."
   Replace the 5-tap row with: "| 5 taps | Top face while asleep (the always-on sensor watches the up-down axis only); any face while awake | Always | Soft privacy ON | Soft privacy ON |"
   In "Finding which face was tapped", append: "This register is on the ST LSM6DSV16X only. With the Bosch BMI323, the face must be read from the raw motion data [E]."

3. §8 "Camera input limit", §11 and §12 item 1. The camera chain has no image processor. The OV02C10 outputs only "8-bit or 10-bit RGB RAW" (S6). The i.MX 93 has no hardware ISP. That comes from an NXP community reply; the NXP product page lists none. The i.MX 93 also has a parallel camera input that the draft omits.
   Replace with: "The i.MX 93 has one 2-lane MIPI CSI-2 input rated for 1080p60, plus one 8-bit parallel YUV/RGB input [M, S56]. It has no hardware ISP. An ISP (image signal processor) is the block that turns raw sensor data into a normal picture [M, secondary, NXP community reply; S56 lists none]. The OV02C10 sends raw data only [M, S6]. So the cube needs one of three things: sensors with a built-in ISP and YUV output, an external ISP chip (for example onsemi AP1302), or a slow software ISP running on the A55 cores. This choice must be made before the board is laid out [E]."
   Also in §8: "1–2× A55" exists. Specify the dual-core part number.

4. §4 Cameras, Coverage and Stock lenses. A 16:9 sensor needs a much wider lens than 109.5°, and the stock module is narrower than stated.
   Replace with: "Coverage. To see everything around the cube, each camera must cover the whole view from its face: 90° across, 90° up-down, and 109.5° corner to corner on a square image [E, geometry]. The OV02C10 is 16:9 (1920 × 1080). A plain (rectilinear) lens that gives it 90° up-down needs about 121° across and 128° corner to corner [E]. The cameras sit on the faces, not at the centre, so add 10–20° of overlap to avoid blind gaps near the edges [E]. Stock lenses are too narrow. A stock 5 × 5 × 3.2 mm module sees 68° corner to corner, 61° across and only 36° up-down [M, S7]."

5. §3 table row "Charging", and §7 "64 mm cube", heat and time to 80%. "14 W steady" overclaims. The draft's own budget leaves no room for heat soaking up from the pad, for a warm room, or for uneven surface temperature.
   - Charging cell: "Qi2 or Qi2 25W pad. About 14 W at first, likely falling to 7–10 W within about half an hour as the cube warms [E]."
   - Heat bullet: "About 14 W reaching the battery costs roughly 2.5–3 W of heat inside the cube, from the receiver coil, rectifier, charger chip and battery [E]. The pad's own coil also warms the bottom face. In a 25 °C room that uses most of the 3.7 W budget before HELM does anything. In a 30 °C room the budget falls to about 2.7 W [E]. The 3.7 W figure assumes an evenly warm surface. Real cubes have hot spots, so treat it as an upper limit [E]."
   - Time bullet: "Time to 80% at 64 mm: about 80–110 min [E]."

6. §3 and §7, 55 mm charging. "5 W baseline" understates the standard. Qi v2.0 EPP allows 15 W without magnets, under the plain Qi logo.
   Replace with: "Plain Qi, no magnets. Qi v2.0 allows the Extended Power Profile (EPP) at up to 15 W without magnets, under the plain Qi logo, not Qi2 [M, secondary, S40]. Heat, not the standard, sets the limit: about 5–8 W sustained at 55 mm [E]. The 29 × 29 mm Würth coil (7.9 µH, 1.7 A, 330 mΩ max DC resistance [M, secondary, S44]) would itself turn about 1 W into heat at its rated current [E]."
   Replace "Using the Qi2 name requires the magnet ring" with: "The Qi2 logo requires built-in magnets. The 'Qi2 Ready' label, introduced in January 2025, covers devices that get their magnets from a case [M, secondary, S40]."

7. §7 battery-life table, row "Heavy". The arithmetic is wrong. The stated model gives 1.875 + 1.0 + 0.48 = 3.355 Wh.
   Replace with: "| Heavy: 300 turns, 60 min of camera | About 3.36 Wh | About 4.0 days | About 2.3 days |"

8. §1 item 6 contradicts §9 item 8, which found no law requiring a recording light.
   Replace with: "6. Three parts of the brief do not fit as written: six speakers, six cameras running at once, and 'visible nowhere'. The law expects a printed regulatory label. No law we found requires a recording light, but a hidden camera with no visible on-light will be read as spying. Section 12 gives the trade-offs."

9. §5, the sentence after the mode table. The claim that the cube follows Echo's colours is false. On Echo, blue means listening and orange means setup.
   Replace with: "Amazon Echo uses blue for listening, red for mic off, orange for setup and yellow for notifications [M, secondary, S78]. Our red for privacy matches Echo. Our blue for pairing and orange for errors do not: an Echo owner will read blue as 'listening' and orange as 'setting up'. Either move pairing to orange and errors to another colour, or drop the claim that we follow Echo. Sources also report Echo purple for Do Not Disturb or a Wi-Fi failure, which overlaps our violet [E]."

10. §6 rule 8 overclaims.
    Replace with: "8. The two passive radiators face each other, so their shaking cancels. The main driver is not balanced. It shakes the cube along the up-down axis, the same axis as a tap on the top face. While HELM speaks, a top-face tap must be checked against the known speaker signal, or '1 tap = stop' will be missed or fire by mistake [E]."

11. §9 item 3, light-sensor sub-bullet. The draft's own source shows this kind of check can be beaten.
    Replace with: "A tiny light sensor beside each dot cuts that camera's power if the dot looks covered [E]. This makes covering harder, not impossible: a sticker beat a similar check on Meta's glasses [M, S31]. The circuit should also sense the dot's own current and cut the camera if the LED fails [E]."

12. §4 and §5 layout, and the Drawing brief. A band at mid-height collides with centred side cameras and with the 25–35 mm radiators.
    Add to §5: "The band sits at mid-height, where a centred side camera and the radiators would also sit. Put each side camera in the upper half of its face, above the band. Keep the radiators' rims clear of the shell seam [E]."
    Add to the Drawing brief: "Side-face cameras sit in the upper half of each face, above the band."

13. §4 Speakers, and §11 radiator row. The bass is overstated and the radiator size is wrong.
    - Replace "Expect less bass than HomePod mini." with: "Expect voice-class sound. The CE32A-4 reference has Xmax 0.5 mm and Vas 0.15 L [M, S14]. In the roughly 60–100 cc of free air left after the parts [E], a sealed box would put the bass roll-off near 410–490 Hz [E]. The radiators can lower that, but not to HomePod mini levels. The whole inside of the cube becomes the speaker's air box, so the mics, the battery pouch and any vents must be sealed off from it [E]."
    - DMA58-PR: replace "About 58 mm across" with "2.2 in (about 56 mm) square, 1.5 in (about 38 mm) deep [M, S15]".

14. §7 "Power by state", row A, Wi-Fi term. The 20 µA figure belongs to a different chip.
    Replace with: "Wi-Fi 6 keep-alive: Silicon Labs claims as low as 20 µA for its SiWx917 modules, with TWT and a 60 s keep-alive [M, vendor, S50]. That is not the IW612. NXP publishes no power figure for the IW612 [M, S53], so budget 2–10 mW until measured [E]. A 60 s keep-alive also means the app may wait up to a minute to reach a sleeping cube [E]."

15. §8 Thread bullet. Leaving the cube's Thread radio on would break the sleep budget.
    Append: "The cube reaches Thread devices through that border router over Wi-Fi, so its own 802.15.4 radio can stay off while on battery. Joining Thread directly as a router would keep a receiver on all the time and break the asleep power budget [E]."

16. §7 row B. The two numbers are stand-ins from other tasks.
    Replace "i.MX 93 at work, 725.5–805.9 mW [M, S57]" with: "i.MX 93 stand-ins from NXP's EVK tests (processor rails only; memory measured separately): eIQ benchmark 725.5 mW, Dhrystone 805.9 mW, audio playback 458.6 mW, NXP 'Smart doorbell' case 772.1 mW [M, S57]. None of these is speech recognition [E]."

17. §8 Text-to-speech row, and Moonshine licence.
    - TTS: "Kokoro's code and weights are Apache-2.0, but it uses espeak-ng for English words outside its dictionary [M, S66]. espeak-ng is GPL-3.0 [check]. Piper is GPL-3.0 [M, S67]. Both need a licence review before shipping. Kokoro (82M) is likely slower than real time on two A55 cores [E]. Plan a Piper-class voice for on-cube speech until FRDM-IMX93 measurements exist."
    - Moonshine: "MIT for code and models, except the legacy non-streaming non-English models, which use the non-commercial Moonshine Community License [M, S65]."

18. §7 battery limit, and §11 charger row. The cited datasheet covers two parts, and the chip is too small for 14 W.
    Replace with: "A typical charger chip, TI BQ25618E/BQ25619E (one datasheet covers both [S48]), reduces charging above a 45.5 °C warm point by default. That point is programmable from 40 to 54.5 °C. It has a 10 °C cool point [M, S48]. It is a 1.5 A charger, about 6 W into one cell, so it is a temperature reference only. The real charger must handle about 3.5–4 A for 14 W [E]."

19. §7 coil bullet, and §11. Replace "29 mm" with: "29 × 29 mm square, 7.9 µH, 1.7 A, 330 mΩ max DC resistance. Listings disagree on thickness: 0.62 mm or 0.9 mm [M, secondary, S44]".

20. §11, missing part. Add the row: "| NFC setup tag | NFC tag holding the Matter onboarding data (part not chosen) | Needed for 'phone held to the cube' setup; Matter 1.4.1 adds 'Onboarding Info in NFC Tag' [M, S79] | [E] | Keep its antenna away from the Qi coil and magnets | S79 |"

21. §3 table, missing weight and size reality. Add the row: "| Weight | About 230 g with a plastic shell, 290 g glass, 460 g zirconia ceramic [E]. A tennis ball weighs 56.0–59.4 g [M, S69] | About 150–330 g [E] |"
    Change "Same width" to: "Slightly narrower face to face (64 mm vs 65.4–68.6 mm), but 90.5 mm across a face diagonal and 110.9 mm corner to corner [E]"

22. §3 Shell, corners. Replace "to survive drops" with: "to reduce chipping when dropped. Glass and ceramic corners still chip on hard floors, so drop-test before choosing the shell [E]."

23. §7 row A+. Replace "Adds about 1 mW [E]" with: "Adds about 1 mW in a quiet room [E]. In a noisy home it costs more, because every false trigger wakes the main processor for a second or more at about 1 W [E]."

24. §9 item 8, AI Act. Replace the date sentence with: "It has applied since 2 August 2026 [M, secondary, S35]."

25. §12 item 6, EU bin mark. The cited page does not state the 7 mm figure.
    Replace with: "The EU crossed-out-bin mark goes on the device. Where size or function prevents that, it goes on the packaging, the instructions and the warranty (WEEE Directive 2012/19/EU, Art. 14(4)) [check]. The 7 mm minimum height (EN 50419) is unconfirmed; the page cited as S94 does not state it."
    FCC: add "47 CFR 2.925(f)". The fallback to the user manual plus the packaging or a removable label applies only below 4-point type with no display. A 64 mm cube must carry the FCC ID.

26. §12, new item 12. These rules are in the source list but missing from the text.
    Add: "12. Security, safety and certification rules are not yet in the plan. In the EU, the Radio Equipment Directive cybersecurity rules (EN 18031) have applied to internet-connected radios since 1 August 2025. Cyber Resilience Act vulnerability reporting has applied since 11 September 2026 [M, secondary, S90, S91]. In the UK, the PSTI Act bans default passwords and requires a stated update period, since 29 April 2024 [source to add]. The battery needs IEC 62133-2 and UN 38.3 tests [S95]. Budget for Qi (WPC), Matter (CSA) and Bluetooth SIG certification [S96–S98]. If children may talk to it, COPPA covers stored voice recordings. The FTC acted on Alexa recordings in 2023 [source to add]. Set a water target now, for example splash resistance, because the edge slots, the pinholes and the light seam all need sealing [E]."

27. §12 item 9, KDB 680106.
    Append: "The exclusion also needs the device in direct contact with the pad, and it covers mobile (not handheld) exposure only [M, secondary, test reports citing v03]. Version 1 should use an already-certified Qi2 25W puck, not a custom one [E]."

28. §4 Microphones, Ports.
    Append: "Our pinholes are 0.5–1.0 mm, so the loss at that size is unmeasured. The T5838 is bottom-port, so each mic needs a through-board sound channel to its seam pinhole [M, S1]. The S21 datasheet link now returns 404."

29. §7 Qi standard bullets.
    Add: "IEC 63563-10:2025 is 'Qi Specification version 2.0 – Part 10: MPP System Specification'. The spare MagSafe ring assembly includes a separate alignment magnet [S42]. If the standard requires one, place it in a corner of the bottom face [E]."

30. §11 MAX98357A row. Append: "From a 3.7 V cell with no boost converter, about 1.7–1.8 W [E, scaled by V²]."
    §5 LEDs: replace "these LEDs draw current even when dark" with: "these LEDs draw roughly 0.5–1 mA each even when dark. For 32 LEDs that is about 60–120 mW, several times the whole asleep budget [E]. Check their minimum supply voltage against a 3.0–4.2 V cell."

31. §8, 55 mm presence sensors.
    Add: "The ESP32-C6 has no dedicated camera port [check datasheet]. A camera interface on the PSoC Edge E84 is unconfirmed; S51 lists only a display interface. The HM0360 sends 1-, 4- or 8-bit parallel or 1-lane MIPI data [M, S9]. Confirm the chosen chip can take one of these."

32. Front matter, RPM gate pointer. Replace "lines 112-136" with "lines 117-136". The gate code starts at line 117; line 112 is the docstring.

33. §4 steering limit. Replace "That covers the main voice band." with: "That covers most of the telephone voice band (300–3,400 Hz); the close pair is needed above that [E]."
    §7 touch limit: append "(the UL brief is based on the 2010 first edition, Table 42)".

Checked and correct as written: the volumes, the HomePod mini comparison (478 cc, modelled as a truncated sphere), the 5-face heat arithmetic, and the typical, light, idle and nonstop battery rows. These source figures also matched:
- ADXL367: 180 nA, 40 nA, 35 nA, and its size.
- i.MX 93: package options and clock speeds; AN13917's 7.6, 199.9, 780.5 and 1264.1 mW.
- Matter 1.5 closures, released 20 November 2025, and Matter 1.4.1 NFC onboarding.
- IW612: Bluetooth 5.4, 802.15.4 and dual-band Wi-Fi 6.
- CE32A-4: 262.1 Hz, 32 mm, 15.5 mm deep, 2 W.
- BMI323: single, double and triple tap, 790 µA, 2.5 × 3.0 × 0.83 mm.
- QCS6490: 12 TOPS and 5 cameras at once.
- PSoC Edge E84: 5 MB SRAM. HM0360: 7 mA and 50 µA.
- SK6805-E-J: 1.5 × 1.5 mm and about 18 mA.

Sources I could not open:
- S21 (404), S44 at RS (403), S50 (403), S41 (503; the title was confirmed through other standards sellers).
- The S78 article body was cut off; other search results covered it.
- S88 was too large; secondary test reports covered it. S64 and the S70 PDF timed out.

The extracted datasheet text is in `C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS\73b7dfb1-8d04-45a8-8b78-844374ca5ce9\scratchpad\pdf\` (`an13917.txt`, `adxl367.txt`, `ul.txt`, `hm0360.txt`, `qcs.txt`).

VERDICT: A 64 mm cube is plausible as a voice-and-light device with one camera on at a time, voice-quality sound and about 7–10 W of sustained charging. It is not plausible as written: the cameras need an ISP or YUV sensors, the always-on tap job needs the ADXL367 alone or a separate tiny chip, and "14 W steady" and "5 taps on any face while asleep" do not hold up.