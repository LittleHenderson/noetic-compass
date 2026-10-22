1. MAJOR. Section 8a, "Said plainly" point 5. The range claim is too high. ST's own VL53L7CX datasheet (DS13865 Rev 6) gives 3.5 m only for the coarse 4 × 4 grid, in the dark, on a white target, with no cover glass. In the 8 × 8 grid it gives 2.0 m. On a 17% grey target it gives 0.8 m. At 5 klux it gives 0.5 m.
Replace: "5. The room drawing comes from tiny "lidar" depth sensors, one behind each face, plus the cameras. Each sensor gives 64 distances (an 8 × 8 grid) out to about 3.5–4 m [M, S120, S122]. Turning and moving the cube fills in the gaps."
With: "5. The room drawing comes from tiny "lidar" depth sensors, one behind each face, plus the cameras. In its finer mode each sensor gives 64 distances (an 8 × 8 grid). For the first-pick sensor, ST gives about 2 m on a white wall in the dark, about 0.8 m on a dark grey surface, and about 0.5 m in bright daylight. All three figures are without cover glass [M, S127]. The 3.5 m figure holds only for the coarser 4 × 4 grid (16 distances), in the dark, on a white wall [M, S127]. Turning the cube fills the gaps around the horizon. Some directions stay unmeasured (8a.4)."

2. MAJOR. "Said plainly" point 6. The level of detail and the reach are overstated.
Replace: "6. The result is a coarse 3D sketch of rooms, walls, doorways and large objects. Across a room it shows detail of about 0.3–0.4 m [E]."
With: "6. The result is a coarse 3D sketch of the nearer part of a room: walls, doorways and large objects within about 2 m. At 2 m, one reading covers about 0.26 m [E]. Farther out, only the coarse grid reaches, at about 0.8 m per reading at 3 m [E]."
Keep the rest of point 6 as it is.

3. MAJOR. 8a.4 sensor table, VL53L7CX column. Replace these cells:
- Zones: "8 × 8 (64) at up to 15 Hz, or 4 × 4 at up to 60 Hz [M, S127; S120 gives the same limits for the VL53L8CX]"
- Range: "4 × 4 in the dark: 3.5 m on a white (88%) target, 1.4 m on dark grey (17%). 8 × 8 in the dark: 2.0 m white, 0.8 m dark grey. At 5 klux (bright daylight at 940 nm): 0.5–0.65 m. All typical, without cover glass; minimum 2 cm [M, S127]"
- Size: "6.4 × 3.0 × 1.6 mm [M, S127]"
- Power: "Continuous ranging: 216 mW (2.8 V analog, 1.8 V I/O) to 313 mW (3.3 V both) [M, S127]. Autonomous mode, 20 ms per frame: 5.4 mW at 4 × 4 and 1 Hz; 19 mW at 8 × 8 and 1 Hz; 88 mW at 8 × 8 and 5 Hz [M, S127]. Pololu's carrier: about 100 mA typical, peaks 150 mA [M, distributor, S122]"
- Width of one zone: "8 × 8 at 2 m: 7.5°, about 0.26 m. 4 × 4 at 3 m: 15°, about 0.79 m [E]"
- Share of directions: "About 40% from one still pose with five usable faces [E]"

Replace these cells in the VL53L8CX column:
- Range: "Up to 400 cm by ST's headline figure; better in bright light [M, S120, S121]. For the VL53L7CX the headline figure is the 4 × 4, dark, white-target case; the 8 × 8 figures for this part are not checked [check DS14161]"
- Width of one zone: "8 × 8 at 2 m: 5.6°, about 0.20 m. 4 × 4 at 3 m: 11.25°, about 0.59 m [E]"
- Share of directions: "About 23% [E]"

4. MAJOR. 8a.4 "Far walls" bullet.
Replace it with: "- **Far walls.** In the 8 × 8 mode, readings stop at about 2 m on a white wall in the dark, and at about 0.8 m on a dark one. In the 4 × 4 mode they stop at about 3.5 m [M, S127]. The cover window shortens this further. ST asks for over 87% transmission, so at most about 76% of the light survives the round trip, which cuts these ranges by roughly an eighth [E]. In bright daylight (5 klux) every mode falls to about 0.5–0.65 m [M, S127]. So mapping works best under LED lamps or with the curtains drawn, because LED room light carries little 940 nm light [E]. In any larger room, far walls stay `UNDETERMINED` until the cube is moved closer [E]."

5. MAJOR. 8a.4 "Coverage" bullet. Two problems. A resting cube has at most five usable faces. Turning the cube cannot fill the band between level and straight up.
Replace it with: "- **Coverage.** Six faces see in every direction only if each face covers 90° × 90° [E]. A resting cube uses at most five faces, because the bottom face sees the table or sits on the charger. From one still pose, five VL53L7CX views cover about 40% of all directions, and five VL53L8CX views about 23% [E]. Turning the cube about the vertical by about 45° fills the gaps around the horizon [E]. Turning cannot fill a band about 30°–51° above and below the horizon (about 22°–60° for the VL53L8CX). Every resting pose of a cube points its faces level or straight up, so no amount of turning on a table reaches that band. It is about a quarter of all directions [E]. The band holds the upper walls and the corners where walls meet the ceiling, so these stay `UNDETERMINED`. Readings taken while the cube is carried cannot fill them either, because the cube's position is `UNDETERMINED` while it moves (8a.1, 8a.5)."

6. MAJOR. 8a.6 power rows and the "While asleep" paragraph. The 9.6 mW figure is wrong: ST's datasheet gives 5.4 mW per sensor in the slowest mode.
- Row "ToF, one face, continuous": "216–313 mW, depending on supply voltages [M, S127]"
- Row "ToF, one face, slow (1 Hz)": "VL53L7CX, autonomous mode: 5.4 mW at 4 × 4, 19 mW at 8 × 8 [M, S127]. VL53L8CX: 1.6 mW by ST's figure, about 68 mW as measured by one user [M, secondary and forum, S121]. Budget 10–70 mW [E]"
- Row "ToF, all six faces continuous": "1.3–1.9 W [E, 6 × S127]: a third to half of the 3.7 W heat budget (Section 7)"
- "While asleep" paragraph: "**While asleep:** only the ADXL367 runs. ToF, cameras, gyroscope, Wi-Fi ranging and Wi-Fi sensing are all off. Even the slowest ToF setting would not fit: six VL53L7CX sensors at 4 × 4 and 1 Hz would add about 32–50 mW [E, 6 × S127]. That is more than the whole 11–25 mW asleep budget. Keeping them in low-power idle, only to skip the firmware reload, would add about 0.8 mW typical and up to about 6 mW worst case [E, from S127: 45 µA typical and 300 µA maximum each]. So they are switched off."

7. OVERCLAIM. 8a.1, LSM6DSV16X, "15 µA". The source does not say the gyroscope is running at that figure.
Replace: "It runs on as little as 15 µA [M, secondary, S102]."
With: "A press article says it can track "while drawing as little as 15µA" [M, secondary, S102]. The article does not say the gyroscope is on at that figure. With the gyroscope on, budget the part's 0.65 mA high-performance figure [M, S72] until ST's low-power figures are checked [check]."
In the 8a.6 table, replace "its fusion block from 15 µA [M, secondary, S102]" with "the 15 µA press figure is not tied to tracking with the gyroscope on [M, secondary, S102]".

8. OVERCLAIM. 8a.4 "A denser sensor to watch", VL53L9CX.
Replace: "Mass production started in July 2026 [M, secondary, S124]."
With: "ST said mass production would start in early July 2026 [M, secondary, S124]. We did not confirm that it started."
Add after "It may suit one face in a later version.": "It also streams a 2D infrared image alongside depth [M, secondary, S124]. An infrared image is a picture that works in the dark. So this sensor would fall under the camera rules, including the hardware camera-on dot (Section 9) [E]. ST has a cover-glass note for it, AN6346 [S131]."

9. OVERCLAIM. "Said plainly" point 1, and the 8a.1 "Moves while asleep" bullets. The claim of about 1° holds only if the gyroscope was already running.
Point 1, with: "1. The gyroscope already on board tells the cube how it was turned, if the gyroscope was running when the turn began. For a turn lasting a few seconds, it is accurate to about 1° [E]. If the cube was asleep, the start of the turn is missed, and the new heading is `UNDETERMINED` until the cube recognises the room (point 2). The gyroscope cannot tell how far the cube was carried: that estimate is wrong within a second or two [E]."
Replace the bullet "The 6-axis IMU runs only while awake, so the first part of a pick-up may be missed [E]. The gyroscope's start-up time has not been checked [check]."
With: "- The 6-axis IMU runs only while awake. The BMI323 starts in about 2.5 ms in its fast-start mode [M, S70, read through a search summary]. The longer delay is the i.MX 93 waking from deep sleep and starting the IMU, which is not measured [check]. So the first part of a pick-up is missed [E].
- Option, off by default: the LSM6DSV16X's fusion block could keep running through sleep and hold its results in the sensor's own memory (FIFO) for the processor to read on waking. At 0.65 mA that is about 1.2–2.3 mW [E, from S72], which fits the asleep budget. FIFO size not checked [check]."

10. ACCURACY. 8a.1, "Heading without a compass". The cube relocalises at rest; it does not track on the move.
Replace: "- Fusing a camera with an IMU this way is an established method, called visual-inertial odometry. VINS-Mono is one published example [M, S105]."
With: "- The cube matches the room only while it rests. That is relocalising, not tracking on the move. Tracking on the move with a camera and an IMU together is an established method called visual-inertial odometry; VINS-Mono is one published example [M, S105]. The cube does not do this by default. It would need a camera running while the cube is carried (green dot on, about 1 W, Section 7), and only one camera runs at a time (Section 8) [E]."

11. PHYSICAL FLAW. 8a.1, true north from the phone. The cube's Qi2 magnet ring would distort a phone compass held against it.
Replace: "If the owner wants true north, the phone's compass could supply it once at setup, while the phone is held to the cube [E, untested]."
With: "If the owner wants true north, the phone's compass could supply it once at setup [E, untested]. The phone must not touch the cube, because the Qi2 magnet ring that rules out a compass in the cube would also bend the phone's reading. The app lights one face. The user lays the phone on the table in line with that face, at least about 50 cm away [E, untested]. Expect a few degrees of error at best indoors [E]."

12. OVERCLAIM and missing limits. Wi-Fi ranging.
- "Said plainly" point 4, with: "4. If the home's router answers Wi-Fi ranging requests (many do not), Wi-Fi can tell roughly how far the cube is from it. It works best with a clear line of sight [M, S111]. Wi-Fi can also tell whether something moved nearby. Drawing walls and furniture from Wi-Fi alone is still research [M, S116, S118]."
- 8a.2, after the bullet "In that note, a client device like the cube can start ranging…", add: "  - NXP validated trigger-based 802.11az ranging only with its own in-house access point. The note itself covers only non-trigger-based ranging [M, S111]."
- Replace "The i.MX 93 can run the NXP Linux driver this note uses [E]." with: "The ranging tool, mlanwls, is preinstalled in i.MX Linux board packages based on kernel 6.18.2 and later. Its configuration file and README were not yet in the "lf-6.18.2_1.0.0" release [M, S111]."
- Under "Limits", add: "- NXP says the station and the access point must be in line of sight for an accurate and stable reading [M, S111]. Through a wall, the range is only a rough hint."
- Under "Limits", add: "- The IW612 can also answer ranging requests itself (802.11mc and 802.11az non-trigger-based) [M, S111]. So an Android phone with Wi-Fi RTT could measure its distance to the cube, with no new part [E, untested]."
- In 8a.6, after "a 128 ms burst every 500 ms [M, S111]", add: "(802.11mc). For 802.11az NXP recommends 5 exchanges a second, 10 measurements each [M, S111]".

13. WORDING. 8a.2 GNSS cell. The datasheet test condition is "every satellite at −130 dBm", not "open sky". Also, 25 mW equals the top of the asleep budget; it is not more than it.
With: "Indoors, satellite signals lose 5–15 dB in houses and 20–30 dB in office buildings [M, S106]. A good small receiver, the u-blox MAX-M10S, specifies its 1.5 m accuracy with every satellite at −130 dBm, static, over 24 hours [M, S107]. It needs −148 dBm for a cold start (no stored satellite data). A cold start takes 27 s with every satellite at −130 dBm, and its sensitivity figures were "demonstrated with a good external LNA", meaning an extra signal amplifier [M, S107]. A fix near a window in a timber house may be possible, but it is not dependable inside a sealed cube with a small antenna [E]. Tracking draws 25 mW [M, S107], about equal to the top of the cube's whole asleep budget of about 11–25 mW (Section 7). The antenna would also sit beside the Qi coil and magnets [E]."

14. OVERCLAIM. 8a.1 verdict. Nothing has been built.
Replace "**Verdict: turning works today. Distance carried does not.**" with "**Verdict: turning is feasible with the gyroscope already chosen (untested). Distance carried is not.**"

15. WORDING. The BMI323 ±0.7% is a best case. The flyer says "down to ± 0.7%".
In 8a.1, replace "A self-calibration step, run while the part is still, trims the gyroscope's scale error after soldering to ±0.7%." with "Bosch says a self-calibration step, run while the part is still, brings the gyroscope's scale error after soldering "down to ± 0.7%" [M, S101]. That is a best case, not a guaranteed limit."
In the "Scale" bullet, write "At ±0.7% (Bosch's best case), …".

16. UPGRADE. LSM6DSV16X gyroscope noise.
Replace "Gyroscope noise is about 2.8 mdps/√Hz (0.0028 °/s/√Hz). That figure is for the sibling LSM6DSV, not the 16X [M, secondary, S103]."
With: "Gyroscope noise is about 0.0028 °/s/√Hz. ST's LSM6DSV16X product page lists this figure (read through a search summary) [M, secondary, S102], and Luxonis gives the same for the sibling LSM6DSV [M, secondary, S103]."

17. WORDING. 8a.4, "Crosstalk".
With: "- **Crosstalk.** Light bouncing inside the cover glass ("crosstalk") is handled by ST's processing beyond 60 cm [M, S120, S127]. Closer than that, it can make targets look nearer than they are, or invent one. ST then advises a crosstalk calibration with the cover in place, using a target at 600 mm or more that fills the whole view. The result can be saved, and one unit's calibration can be reused on others with a safety margin [M, S120]. Spot-check each production cube [E]. A black barrier between the emitter and receiver openings is needed under the glass [E]."

18. MISSING PHYSICAL CHECK. Window size. Add under "Behind dark glass":
"- **Window size.** ST requires the opening in the cover to be at least as wide as the receiver's "exclusion zone", a 74° × 74° cone (105° diagonal) [M, S127]. With the ink on the inside of a 2 mm face glass, that means an opening clear to infrared of roughly 2–4 mm over each of the two lenses (emitter and receiver) [E]. Both fit beside the camera on a 64 mm face. On the charge face they go in a corner outside the magnet ring [E]."

19. MISSING PHYSICAL CHECK. Wiring six sensors. Add after the "Data" bullet:
"- **Wiring six sensors.** Every sensor starts at the same bus address, 0x52, and loses any new address when powered off [M, S120, S127]. Each needs its own enable line (LPn) so HELM can give it an address at each start-up [M, S120]. The VL53L7CX talks only I2C, at up to 1 MHz [M, S127]. Loading its firmware (about 84 KB for the VL53L8CX [M, S120]; the VL53L7CX figure is not checked [check]) takes roughly 0.7–1 s per sensor, so about 4–6 s for six at the start of each session [E]. The VL53L8CX also offers SPI at up to 20 MHz [M, S120], which cuts this to well under a second [E]."
In 8a.7, change "The new parts are six ToF sensors and six infrared windows [E]." to "The new parts are six ToF sensors, six infrared windows, one enable line per sensor, and a flex harness to each face [E]."

20. TAG FIX. 8a.4, "Hard surfaces".
With: "- **Hard surfaces.** Dark surfaces cut the range sharply: a 17% grey surface reads only to about 0.8 m in the 8 × 8 mode, in the dark [M, S127]. Glass and mirrors can give no reading or a false one [E]. ST also warns that indoors the sensor may see several light paths and report false targets [M, S120]. The two-pose rule in 8a.5 guards against this."

21. WORDING. 8a.3 table, Comcast. Replace "Comcast announced WiFi Motion on 18 August 2026." with "BleepingComputer reported on 18 August 2026 that Comcast offers WiFi Motion."

22. PRIVACY GAP. Raw Wi-Fi records carry other devices' addresses. Add to 8a.8 item 6:
"Raw CSI records carry the hardware (MAC) addresses of the sender and receiver of every packet the radio hears [M, S112]. HELM computes the motion measure on the cube, keeps only "motion yes/no, time", and drops each raw record at once. It never stores or sends those addresses [E]. Capture is filtered to packets from the home's own access point; NXP's firmware supports filtering [M, S112]."

23. PRIVACY GAP. Router addresses are location data. Add a new 8a.8 item:
"**Access-point lists are location data.** A router's hardware address (BSSID) can be looked up to a street location. Researchers pulled the locations of over 2 billion of them from Apple's public positioning service [M, S129]. So any access-point address the cube stores, for ranging or room hints, is treated like precise location: kept on the cube, encrypted, never sent out by default, and deleted with the map [E]."

24. PRIVACY OVERCLAIM. 8a.8 item 7.
With: "7. **Camera mapping keeps points, not pictures, but points are not harmless.** Researchers rebuilt recognisable images of scenes from stored 3D points and their feature descriptors alone [M, S128]. By default HELM keeps only each point's 3D position and drops the descriptors at the end of the session, so relocalising in later sessions uses depth only. If the owner chooses to keep descriptors for faster relocalising, they are treated as camera data under Section 9 [E, owner choice]. The hardware green dot lights while any camera is powered (Section 9)."
In 8a.5, change "(no pictures are kept)" to "(no pictures are kept; 8a.8 item 7 says what is kept)".

25. PRIVACY GAP. 8a.8 item 9. Hard mute cannot stop Wi-Fi sensing. Add:
"Hard mute cannot cut Wi-Fi sensing or Wi-Fi ranging, because the radio stays on for the network. Under hard mute, firmware turns both off. The app labels this part as software-only, like soft mute [E]."

26. PRIVACY GAP. Deletion from flash. In 8a.8 item 3, replace "Deleting from flash memory must really erase the data, not just unlink the file [E]."
With: "Flash memory moves data around as it wears, so overwriting a file does not reliably erase it [M, secondary, S130]. So the map, the pose history and the location fact are encrypted from their very first write, with the key held in the i.MX 93's secure enclave [E, check]. Deleting destroys the key ("cryptographic erase"). NIST counts this as a full purge only if nothing was ever stored unencrypted before the key existed [M, S130]."

27. PRIVACY GAP. No retention limit. Add a new 8a.8 item:
"**Retention.** Pose history and the motion log keep 7 days by default. The owner can change this in the app [E, owner choice]. Map cells keep their dates and age out of decisions (8a.5)."

28. PRIVACY GAP. Other people in the home. Add a new 8a.8 item:
"**Other people in the home.** The consent flag belongs to the account holder. Others in the home, and guests, are mapped and sensed without giving their own consent. The Mapping light is their notice. The app offers a guest mode that pauses mapping and Wi-Fi sensing [E]."

29. PRIVACY GAP. HELM waking itself to map. Add to 8a.8 item 1:
"HELM does not wake the cube on its own to map. A session runs only inside an awake window that a person started (shake, tap, voice or app), unless the owner turns on scheduled mapping [E, owner choice]."

30. PRIVACY and SECURITY GAP. Ranging to other people's routers. Add to 8a.8 item 5:
"HELM ranges only to the home's own access points, while connected to them. 802.11mc ranging frames are not encrypted. 802.11az can encrypt them when the cube is connected with WPA3 protected management frames [M, S111]. So prefer 802.11az over WPA3. Never range unconnected to a neighbour's access point, which would show it the cube's hardware address [E]."

31. MODE CLASH. 8a.8 item 8. A light travelling around the edges matches Thinking, Pairing and Updating (Section 5). Pale magenta sits next to violet ("Asking a question").
Replace the "The pattern" and "Colour rules" bullets with:
"- **The pattern:** the four edges around the top face glow steady and dim, and the other eight edges stay free for other modes [E]. No other mode in Section 5 lights only the top ring and holds it still, so the shape alone tells it apart, for colour-blind users too [E].
- **Colour rules:** pale magenta, used for nothing else. On RGB LEDs behind dark material it can look like violet ("Asking a question"), so test the two side by side on a sample [E]."

32. COMPLIANCE NOTE. Add to the 8a.4 "Light source" row or the parts row:
"ST lists EN 50689:2021 compliance except its clause 5 on child-appealing products. If the cube could count as child-appealing, ST asks to be contacted [M, S127]."

33. PARTS ROWS. Replacement "Key numbers" cells, plus tag and source.
- VL53L7CX: "8 × 8 at up to 15 Hz or 4 × 4 at up to 60 Hz; 60° × 60° (90° diagonal); range 4 × 4 dark white 3.5 m, 8 × 8 dark white 2.0 m, 8 × 8 dark grey 0.8 m, 5 klux 0.5–0.65 m, all without cover glass; minimum 2 cm; 940 nm Class 1; 6.4 × 3.0 × 1.6 mm; continuous 216–313 mW; autonomous 1 Hz 5.4 mW (4 × 4) or 19 mW (8 × 8); I2C only, 1 MHz, address 0x52; receive window ≥ 74° × 74°". Tag "[M]". Fit "Good within about 2 m; needs an infrared window; six needed". Source "S127, S122".
- VL53L8CX: add "I2C (1 MHz) or SPI (20 MHz); address 0x52, one LPn line per sensor; 8 × 8 range not checked [check DS14161]".
- VL53L9CX: replace "mass production from July 2026" with "ST said mass production would start in early July 2026 (not confirmed); also streams a 2D infrared image (camera-class); cover-glass note AN6346". Sources "S124, S131".
- ToF window: add "ST's VL53L7 note asks for over 87% at 940 nm [S123]; opening ≥ the 74° × 74° receive cone [M, S127]". Sources "S25, S123, S127".
- IW612: add "also an FTM responder (802.11mc, 802.11az non-trigger-based); trigger-based ranging validated only with an NXP in-house access point; line of sight needed for stable readings; mlanwls in board packages from kernel 6.18.2". Sources unchanged.
- BMI323: change to "scale error after self-calibration down to ±0.7% (best case); fast start 2.5 ms". Sources "S101, S70".
- LSM6DSV16X SFLP: replace "from 15 µA" with "15 µA press figure not tied to tracking with the gyroscope on; budget 0.65 mA with the gyroscope on"; noise "0.0028 °/s/√Hz (ST product page, via search summary)". Sources "S102, S72, S103".
- MAX-M10S: change "cold start 27 s (default constellations)" to "cold start 27 s with every satellite at −130 dBm (default constellations); sensitivity shown with a good external LNA".

34. SOURCES (Section 14). Add:
- S127 https://www.pololu.com/file/0J1992/vl53l7cx.pdf (ST DS13865 Rev 6, March 2023; Pololu-hosted copy; read in full)
- S128 https://arxiv.org/abs/1904.03303 (Pittaluga, Koppal, Kang, Sinha, "Revealing Scenes by Inverting Structure from Motion Reconstructions", CVPR 2019)
- S129 https://arxiv.org/abs/2405.14975 (Rye and Levin, "Surveilling the Masses with Wi-Fi-Based Positioning Systems", 2024; venue not confirmed)
- S130 https://csrc.nist.gov/pubs/sp/800/88/r2/final ; https://csrc.nist.gov/files/pubs/sp/800/88/r2/final/docs/sp800-88r2-faq.pdf (NIST SP 800-88 Rev. 2, September 2025; read through search summaries)
- S131 https://www.st.com/resource/en/application_note/an6346-guidelines-for-the-cover-glass-of-the-vl53l9cx-timeofflight-2k-zones-stmicroelectronics.pdf (did not load; read through a search summary)

Amend:
- S102: add https://st.com/LSM6DSV16X (product page; noise figure read through a search summary).
- S70: add "BMI323 datasheet rev 1.6, Aug 2025: fast start 2.5 ms (read through a search summary)".
- S25: add "(first link returned 404 on 2026-10-21)".
- S123: add "the >87% wording is confirmed for AN5962 (VL53L7) and AN6346 through search summaries; AN5939's wording is not confirmed".
- S119: say the date is the article date.

These claims were checked against their sources and are correct as drafted:
- BMI323 flyer figures: ±1 °/s, ±0.04 °/s/K, 0.007 °/s/√Hz, ±50 mg, ±0.3 mg/K, 180 µg/√Hz, 790 µA, 1.71–3.63 V, "preliminary".
- The IW612 is 1×1, up to 80 MHz, Bluetooth 5.4 certified, and lists "802.11az accurate ranging".
- AN14044 is Rev. 3.0, 29 April 2026: the IW612 is listed, and the 128 ms burst every 500 ms setting is right.
- AN14011 is Rev. 10.2, 25 June 2026: the IW612 has CSI "Yes" and AMI "Yes", in STA mode; mlancsi v1.1 ships from Linux 6.12.49; CSI is made per received packet.
- Android Wi-Fi RTT targets: 2, 4 and 8 m for 802.11mc; 1 m at 80 MHz for 802.11az with 2×4 antennas.
- Android location: about 3 km² approximate, usually about 50 m precise.
- IEEE 802.11bf-2025: approved 28 May 2025, published 26 September 2025.
- Comcast WiFi Motion: opt-in, off by default, motion only, small pets versus children, advice to lower sensitivity behind shared walls.
- Place Lab median error: 13–40 m.
- S114 (over 180 papers, 4 September 2025), S116 (PerCom 2023), S117 (20 m, record not yet verified by the library) and S118 (Structure from WiFi, ACC 2024) all match.
- RPLIDAR C1: 55.6 × 55.6 × 41.3 mm, 110 g, 1.15 W.
- VL53L8CX: 84 KB firmware, 15 Hz at 8 × 8 and 60 Hz at 4 × 4, crosstalk handled beyond 60 cm (UM3109 Rev 7).
- VL53L9CX: 54 × 42 zones, 55° × 42°, under 5 cm to 8.8 m, 100 Hz, 12.8 × 6.1 × 4.6 mm, I3C or CSI.
- All of the draft's own arithmetic: dead-reckoning errors, gyro drift, the 48% and 28% coverage, 62,500 cells, 230,400 readings, and the battery-day figures.

Spec file checked: C:\tmp\helm-cube-design\docs\working\helm_cube_device_concept_v0\HELM_CUBE_SPEC.md