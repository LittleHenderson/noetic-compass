**HELM Cube: sensing and hiding research (cameras, mics, speakers, privacy, law)**

Tag legend: [M] means MEASURED-BY-SOURCE, a number taken from a datasheet, standard or maker page. [E] means ESTIMATE, my own arithmetic or judgment. Source numbers like [S7] point to the list at the end. Where a source is only a retailer, a press release or a secondary site, I say so.

## 1. Bottom line

1. **Cameras.** Small cameras fit easily. A 2 MP module is about 5 × 5 × 3.2 mm [M][S8]. The real limit is the lens angle. To see everything from four side faces, each camera needs at least 90° across and 90° up-down. A cube face spans exactly 90° from the center, and about 109.5° corner to corner [E]. The off-the-shelf 5 mm module sees only 68° corner to corner [M][S8], which leaves gaps. A custom wide lens is needed, and it makes the module bigger: one 120° lens housing is 6.5 × 6.5 mm [M][S14].
2. **Microphones.** They are tiny and easy to hide. Use a 68 dB-SNR part with a built-in "wake on sound" mode. SNR (signal-to-noise ratio) measures how much louder the voice is than the mic's own hiss. One such part is the TDK T5838: 3.5 × 2.65 × 0.98 mm, SNR 68 dB, wake-on-sound at about 20 µA [M][S1][S2]. Hide each mic behind a pinhole in a seam between faces, with a waterproof membrane behind it.
3. **Six speakers is the wrong choice for this size.** The cube is smaller than the sound waves below about 1.6–2.0 kHz [E]. So it already sends sound evenly in every direction there [S20]. Six drivers would split a tiny air volume six ways and give almost no bass. A better plan is the HomePod mini pattern: one active driver plus two opposed passive radiators [M][S18]. A passive radiator is a weighted cone with no motor; the air inside drives it, and it adds bass. Sound leaves through hidden slots at the edges, so it comes out of every side without six drivers.
4. **Bottom face.** The charging coil and alignment magnets take most of the bottom face. Put no camera and no speaker there. If you want magnetic Qi2 alignment, its magnet ring is reported at about 56 mm across. That is a secondary, unverified figure [S40], and it would not fit a 55 mm cube [E].
5. **Privacy.** Wire the camera-on light to the camera's power line, so the camera cannot get power without the light. Add a mute that cuts mic and camera power in hardware. The "no buttons" rule conflicts with a true hardware mute. This needs your decision (section 7).
6. **Law.** I found no law that requires a recording light on a home assistant. That is limited to this search. Duties do exist: all-party consent for recording in about 11 US states, Illinois rules on face scans, EU data-protection law when a camera sees beyond the home, and the EU AI Act rule to tell people they are talking to an AI (section 8).

## 2. Space budget [E]

Walls are taken as 2 mm.

| Cube side | Outside volume | Inside volume |
|---|---|---|
| 55 mm | 166 cc | 133 cc |
| 60 mm | 216 cc | 176 cc |
| 65 mm | 275 cc | 227 cc |
| 70 mm | 343 cc | 287 cc |

For comparison:
- HomePod mini is 84.3 mm tall and 97.9 mm wide [M][S18], about 478 cc [E].
- Echo Dot (5th gen) is about 100 × 100 × 89 mm with a 44 mm speaker driver [M, retailer][S19], about 514 cc [E].
- A 60 mm cube is about 42–45% of those volumes [E], so expect less bass than either.

## 3. Per-face layout (recommended)

Face names: T = top, B = bottom (on the charger), F = front, K = back, L = left, R = right.

| Face | Camera | Mic | Sound | Notes |
|---|---|---|---|---|
| T | Optional wide camera, for the ceiling and hand gestures from above | Yes, port in a top edge seam | Main driver fires up into a small cone. Sound leaves through a hairline slot around the top edges [E design] | The light strip can share the top seam |
| F | Wide camera, at least 100° across [E] | Yes, port in an edge seam | None on the face. The internal passive radiators vent through edge slots | Behind the same dark glass as the rest of the face |
| K | Same as F | Yes | Same as F | |
| L | Same as F | Yes | Internal passive radiator 1 sits behind this face, facing radiator 2 so their shaking cancels [S21] | The face stays solid glass. The radiator vents through a slot |
| R | Same as F | Yes | Internal passive radiator 2 | |
| B | None. It would only see the charger | Optional. It is half-blocked when docked; port it at the bottom edge if kept | None | Qi coil, ferrite and magnets |

This gives 5 cameras, 5–6 mics and 1 active driver.

Why 5 cameras and not 6:
- A likely processor, the Qualcomm QCS6490, handles at most 5 cameras at once [M][S39].
- A sixth camera needs a stream-merging chip or time-sharing [E].
- The bottom camera is the obvious one to drop.

Mic spacing [E]:
- Mics on neighboring faces of a 60 mm cube sit about 42 mm apart. Mics on opposite faces sit 60 mm apart.
- An array of mics can only steer cleanly below the frequency c/(2d), where c is the speed of sound and d is the spacing [S22]. Here that is about 4.0 kHz for neighboring faces and about 2.9 kHz for opposite faces.
- That covers the main voice band. Add one close pair of mics (about 15 mm apart, good to 11.4 kHz [M][S22]) if you need steering higher up.

## 4. Parts table

| Role | Part (maker) | Size | Key numbers | Fit for HELM | Source |
|---|---|---|---|---|---|
| Mic, first pick | T5838 (TDK InvenSense), bottom port, digital (PDM) output | 3.5 × 2.65 × 0.98 mm [M] | SNR 68 dB, overload limit 133 dB [M]. Wake-on-sound about 20 µA [M]; low-power mode 130 µA [M]; full-quality mode 310 or 330 µA [M, sources differ] | Built-in wake-on-sound suits always-listening | S1, S2 |
| Mic, alternative | IM69D130 (Infineon), order code IM69D130V01XTSA1 | 4 × 3 × 1.2 mm [M] | SNR 69 dB(A); 1.3 mA [M, distributor] | Quieter mic, but draws more power | S3 |
| Mic, smallest | CMM-2718AB-3815NC-TR (Same Sky), bottom port | 2.75 × 1.85 × 0.90 mm [M] | SNR 62 or 64 dBA (the source gives both values for the family) [M] | Smallest, but noisier. Not for far-field voice | S4 |
| Mic, reference | SPH0655LM4H-1-8 (Knowles) | 3.50 × 2.65 × 1.08 mm [M, distributor] | SNR 66 dB [M, distributor] | Acceptable | S5 |
| Camera sensor | OV02C10 (OmniVision), 1/7.25-inch, 1920 × 1080 | Supports a 4 × 3.5 × 2 mm module [M] | 60 fps; has an always-on presence-sensing mode [M] | Best fit. One part can both watch for presence and capture video | S7 |
| Camera module, example | AE-CCM-OV02C10-C-61 (Appleye) | 5 × 5 × 3.2 mm [M] | 68° corner to corner, 61° across, 36° up-down; fixed focus; MIPI [M] | Too narrow. Needs a wide lens; I estimate about 6.5–8.5 mm module size [E] | S8 |
| Thinner camera sensor | OV01A10 (OmniVision), 720p | Module about 2.5 mm in one direction, under 2 mm thick [M] | 1/11-inch | Lower resolution, very thin | S9 |
| Always-on vision sensor | HM0360 (Himax), 640 × 480 (VGA), 1/6-inch | Sensor diagonal 2.88 mm [M] | About 140 µA at 2 frames per second, small frames [M, retailer citing Himax] | Optional low-power presence watcher | S10 |
| Global-shutter sensor | VD55G1 (ST) | 2.73 × 2.16 mm sensor die [M] | 800 × 700 [M] | For motion and gestures. Sensor only, not a full module | S11 |
| Development stand-in only | Raspberry Pi Camera Module 3 Wide | 25 × 24 × 12.4 mm [M] | 102° across, 67° up-down, f/2.2 [M] | For lab tests only. Too big for the product | S12 |
| Not suitable | OVM6948 (OmniVision) | 0.65 × 0.65 × 1.158 mm [M] | Medical endoscope camera | Too low-resolution | S13 |
| Micro speaker, if you keep "speakers on every face" | AS01508AO-3-SC-R (PUI Audio) | 15 × 11 mm; family thickness 3.5–4.42 mm [M] | Resonance 800 Hz in a 1 cc box. 91 dB at 0.7 W and 10 cm in a 1 cc box. 0.7 W rated [M] | Nearly nothing below about 800 Hz | S15 |
| Main driver, size reference | CE32A-4 (Dayton Audio) | 32 mm square, 15.5 mm deep [M] | Resonance 262.1 Hz; Vas 0.15 L (the air volume equal to its suspension stiffness); cone area 3.917 cm²; travel ±0.5 mm; 78 dB at 1 W and 1 m; 2 W [M] | Shows the size class. A custom driver of about 28–32 mm is likely [E] | S16 |
| Passive radiator | Smallest stock part found: DMA58-PR (Dayton) | About 58 mm across [M] | Dayton advises radiator air movement of at least twice the active driver's [M] | Too big. Needs custom radiators, about 25–35 mm [E] | S17 |
| Mic membrane vent | GAW334 (Gore) | 1.6 mm inner diameter | Under 2 dB loss at 1 kHz [M]. Smaller 1.0 mm vents lose about 2.6–6.6 dB [M, press release] | Waterproofs the hidden mic ports | S23 |
| Camera window glass | Gorilla Glass DX / DX+ (Corning) | — | 98% of light passes; plain covers pass 92–95% [M, maker claim, 2021] | Clear window option | S26 |

## 5. Hiding: methods and what each costs

**Cameras**
- **Dark tinted face (whole face one even tint).**
  - Gray acrylic passes about 27% (Plexiglas 2064) or 12% (2074) of visible light [M][S25]. A second page from the same seller shows different numbers, so check the official datasheet.
  - Light loss: about 1.9 f-stops at 27% and about 3.1 stops at 12% [E]. Each stop halves the light.
  - Result: noisier video in dim rooms, a risk of color tint, and ghost images from reflections. Anti-reflection coatings reduce ghosts but do not remove them [S26].
  - To make the lens disappear, put a black light-trap tube around it and anti-reflection coating on the inside face [E].
- **Clear coated window inside a black-printed face.** It loses only about 2% of light [M][S26]. The lens can be seen up close, so it is not fully hidden.
- **Black plastic that passes only infrared** (ACRYLITE IRT; Phillips NIR-85N passes from about 810 nm) [M][S27]. A normal color camera cannot see through it. Use it only for infrared night views with infrared lights behind it.
- **Camera under a display.** This is the worst option. Samsung itself warns of lower quality, flare, blur and haze [S28].
- **Precedent:** Apple Vision Pro keeps 8 of its 12 cameras behind its front glass [M][S29].

**Microphones**
- Use a 0.5–1.0 mm pinhole in an edge seam with a Gore-type membrane behind it [E for hole size]. The added loss is under 2 dB at a 1.6 mm opening [M][S23].
- A small port can add a high-pitched peak (a resonance). Handle it in tuning [E].

**Speakers**
- **Perforated metal.** Typical open area is 30–65%. Less open area raises distortion [S24]. The hole pattern is visible.
- **Fabric.** HomePod mini uses acoustically transparent fabric [S18]. Fabric clashes with a glossy black glass cube.
- **Hidden edge slot** (my recommendation) [E]. Costs: some treble loss and possible air-rush noise at high volume. It needs measurement.

## 6. Six speakers or fewer drivers?

- Below about 1.6–2.0 kHz the cube is small compared with the sound wave. A single source then sends sound evenly in all directions, and the rule for this is ka < 1 [S20].
- So drivers on six faces only add direction at high frequencies [E].
- Six drivers split the air inside about six ways. Each micro speaker in a 1 cc box makes almost nothing below about 800 Hz [M][S15].
- One 32 mm-class driver in a sealed 30 cc box would start rolling off below about 640 Hz [E, from S16's numbers]. Passive radiators can push the bass lower.
- Two opposed radiators cancel each other's shaking [S21]. That also helps the shake and tap sensor avoid false triggers from the speaker [E].
- Recommendation: 1 driver plus 2 internal opposed passive radiators, venting through hidden slots. If you insist on six speakers, expect a voice-only sound with no bass.

## 7. Privacy signal and hardware mute

- **What others do:**
  - Google Nest Hub Max has a hardware switch that turns off the camera and mics together and shows an orange light. A solid green light means the camera is streaming [S30].
  - Amazon Echo has a mic button that disconnects the mics and shows a red light [S31].
  - Apple's old webcam light was meant to be wired to the camera, but in 2013 researchers turned it off by reprogramming the camera's chip [S32].
  - Meta's glasses stop recording when their light is covered, but tests show a sticker can still beat this [S33].
- **For HELM [E]:**
  - Reserve one light color that no other mode may use. Power it from the camera power line itself, not from a signal the software controls.
  - Add a light sensor next to it that cuts camera power if the light is covered.
- **Hardware mute without a button.** These are design ideas, not tested [E]:
  - (a) A hidden magnetic switch, worked by a magnetic "privacy puck" or a privacy spot on the dock.
  - (b) A tilt switch: set the cube on its "privacy face" (off the charger) and mic and camera power is cut.
  - (c) A tap pattern read by a tiny separate chip. This is software, so it is the weakest of the three.

## 8. Legal duty to show recording

This is not legal advice. Have a lawyer review it.

- **United States:**
  - The federal rule is one-party consent. California, Delaware, Florida, Illinois, Maryland, Massachusetts, Michigan, Montana, New Hampshire, Pennsylvania and Washington mainly require consent from everyone recorded [S34]. Guests count.
  - California allows civil damages of $5,000 per violation [M, secondary][S34].
  - A light gives notice. It is not consent.
  - Illinois BIPA (the Biometric Information Privacy Act) requires notice and written consent before scanning faces. An Arlo camera lawsuit survived a motion to dismiss [S35].
- **European Union:**
  - The home-use exemption ends when a camera sees public space. The EU court held this in Ryneš [S36]. Ireland's regulator also bars capturing neighbors' homes, gardens or driveways [S36].
  - AI Act Article 50(1): people must be told they are interacting with an AI. Article 50(3): anyone exposed to emotion recognition must be informed [S37].
  - Secondary sources say these apply from 2 August 2026. One part, 50(2) machine-readable marking, is delayed to 2 December 2026 for systems already on sale [S37].
- **Korea and Japan:** Korea has a government-backed shutter-sound rule for phones. In Japan the rule comes from mobile carriers [S38]. Neither is directly a rule for home devices, but they show what buyers there expect.
- **Not found:** in this search, no law requiring a recording light on a home assistant.

## 9. Open decisions for the owner

1. Five cameras or six. The processor limit points to five [S39].
2. Speaker plan: the recommended 1 driver + 2 radiators, or literal speakers on every face.
3. Mute method: (a), (b) or (c) from section 7.
4. Minimum cube size: at least about 60 mm if Qi2 magnets are wanted [S40, unverified].

## Sources

- S1 https://invensense.tdk.com/products/digital/t5838/
- S2 https://audioxpress.com/news/tdk-introduces-lowest-pulse-density-modulation-multi-mode-mems-microphone-with-acoustic-activity-detect
- S3 https://www.infineon.cn/content/dam/infineon/row/public/documents/24/49/infineon-im69d130-datasheet-en.pdf (returned 404 when fetched directly) ; https://digikey.dk/en/products/detail/infineon-technologies/IM69D130V01XTSA1/IM69D130V01XTSA1CT-ND/8030734
- S4 https://www.sameskydevices.com/news/press-releases/new-mems-microphones-carry-wide-operating-frequency-ranges ; https://audioxpress.com/news/cui-devices-offers-new-mems-microphones-for-active-noise-canceling-applications
- S5 https://www.digikey.cn/en/products/detail/knowles/SPH0655LM4H-1/11506911
- S7 https://www.ovt.com/products/ov02c/
- S8 https://appleye.co.il/?p=430
- S9 https://www.ovt.com/products/ov01a/ ; https://www.ovt.com/wp-content/uploads/2022/01/OV01A10-PB-v1.1-WEB.pdf
- S10 https://www.welectron.com/mediafiles/productimg/arducam/Datasheet/HM0360-image-sensor-datasheet.pdf ; https://thepihut.com/collections/raspberry-pi-camera/products/vga-camera-module-for-raspberry-pi-pico-hm0360
- S11 https://www.st.com/resource/en/data_brief/vd55g1.pdf
- S12 https://www.raspberrypi.com/documentation/accessories/camera.html
- S13 https://www.eenewseurope.com/en/wafer-level-camera-module-measures-only-0-65-x-0-65-x-1-158mm/
- S14 https://www.waveshare.com/product/raspberry-pi/cameras/pi5-imx219.htm
- S15 https://api.puiaudio.com/file/005fec80-3413-4365-af79-f80803bcda9b.pdf ; https://www.mouser.fr/new/pui-audio/pui-slim-line-micro-speakers
- S16 https://daytonaudio.com/product/1138/ce32a-4-1-1-4-mini-speaker-driver-4-ohm
- S17 https://www.daytonaudio.com/product/1625/dma58-pr-2-dma-series-passive-radiator
- S18 https://www.apple.com/homepod-mini/specs/
- S19 https://www.pbtech.com/product/SPKAMZ51011/reg ; https://www.johnlewis.com/amazon-echo-dot-smart-speaker-with-alexa-early-access-voice-recognition-control-5th-generation-2022/glacier-white/p6375096
- S20 https://www.ioa.org.uk/system/files/proceedings/nt_shade_sound_goes_round_the_quest_for_omnidirectional_radiation.pdf
- S21 https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5850460 ; https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10075787 ; https://www.postbulletin.com/news/bose-speakers-offer-high-end-desktop-sound
- S22 https://www.cee.elektro.dtu.dk/-/media/c6c495f0f1d743f684b985e494364b6f.pdf
- S23 https://www.gore.com/sites/g/files/ypyipe116/files/2017-01/GORE-Acoustic-Vent-GAW334-Datasheet-en.pdf ; https://www.gore.com/node/17776
- S24 https://patents.justia.com/patent/9014411 ; https://www.prosoundtraining.com/?p=9962
- S25 https://www.eplastics.com/ACRY20640-375PM48X72 ; https://www.eplastics.com/plexiglass/acrylic-sheets/bronze-gray (gives conflicting numbers)
- S26 https://www.bgr.com/tech/new-gorilla-glass-for-camera-lenses-will-improve-smartphone-photography/
- S27 https://www.acplasticsinc.com/media/documents/UACI_150033_Infrared_Transmitting_Extruding_Acrylic_Product_Data_HR.PDF ; https://www.phillips-safety.com/shop/optical-filters/polymer-filters/acrylic-nir-near-infrared-filters/
- S28 https://www.samsung.com/za/support/mobile-devices/what-is-the-udc-under-display-camera-of-the-galaxy-z-fold4 ; https://news.samsung.com/in/interview-making-your-screen-seamless-experts-explain-the-engineering-behind-galaxy-z-fold4s-udc
- S29 https://www.uploadvr.com/apple-vision-pro-specs/ ; https://apple.com/apple-vision-pro/
- S30 https://support.google.com/googlenest/answer/9449280
- S31 https://digprjsurvey.amazon.com/csad/help/node/GKA25FVYEV5PY8C9
- S32 https://support.apple.com/en-ph/guide/security/mac-on-screen-camera-indicator-light-sec75a2d237d/1/web/1 ; https://news.hitb.org/content/researchers-find-way-activate-isight-cameras-without-alerting-users
- S33 https://ipvm.com/reports/meta-ray-ban-led-bypass-fix-tested
- S34 https://www.rcfp.org/reporters-recording-guide/ ; https://www.rcfp.org/reporters-recording-guide/california/
- S35 https://news.bloomberglaw.com/litigation/class-action-privacy-suit-over-person-detection-ai-moves-ahead
- S36 https://curia.europa.eu/jcms/jcms/P_152318 ; https://www.dataprotection.ie/sites/default/files/uploads/2026-05/Domestic_CCTV_A5_ENG_Final.pdf
- S37 https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50 ; https://www.mondaq.com/uk/compliance/1826042/not-delayed-not-deferred-eu-ai-act-transparency-obligations-are-now-in-force ; https://www.mccannfitzgerald.com/knowledge/technology-and-innovation/one-month-to-go-eu-ai-act-transparency-compliance
- S38 https://petapixel.com/2023/11/06/korean-smartphones-have-mandatory-shutter-sounds-8-in-10-want-it-muted ; https://www.engadget.com/2016-09-30-japans-noisy-iphone-problem.html
- S39 https://docs.qualcomm.com/doc/87-28733-1/87-28733-1_REV_F_QUALCOMM_QCS6490_QCM6490_Processors_Product_Brief.pdf
- S40 https://jisaku.com/glossary/wireless-charger-qi2 (secondary source; check against the WPC Qi2 specification)

No files were written or committed.