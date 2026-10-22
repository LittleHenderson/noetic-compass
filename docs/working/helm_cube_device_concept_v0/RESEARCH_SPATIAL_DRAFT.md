## 8a Knowing where it is: motion, heading, location and a map of the room

**Owner ruling 3 (verbatim):** "WITH GYRATOR WHEN IT'S BEEN MOVE TURNED AND DIRECTION FOR MAPPING IT'S ENVIROMENT GEOLOCATION AND USE WIFI TO DRAW ITSELF AN INTERNAL SCHEMATIC OF IT'S ENVIROMENT AND OR USE LIDAR". "Gyrator" means gyroscope. Ruling 4 puts HELM in charge of all of it.

**Said plainly first:**
1. The gyroscope already on board tells the cube how it was turned. For a turn lasting a few seconds, it is accurate to about 1° [E]. It cannot tell how far the cube was carried: that estimate is wrong within a second or two [E].
2. There is no compass, so the cube has no "north". It keeps its own heading, which slowly drifts. It corrects the drift by recognising the room with its depth sensors and cameras [E].
3. GPS does not suit a sealed cube that lives indoors. If the user allows it, the cube gets its town-level location from the phone app [E].
4. Wi-Fi can tell roughly how far the cube is from the router, and whether something is moving nearby. Drawing walls and furniture from Wi-Fi alone is still research [M, S116, S118].
5. The room drawing comes from tiny "lidar" depth sensors, one behind each face, plus the cameras. Each sensor gives 64 distances (an 8 × 8 grid) out to about 3.5–4 m [M, S120, S122]. Turning and moving the cube fills in the gaps.
6. The result is a coarse 3D sketch of rooms, walls, doorways and large objects. Across a room it shows detail of about 0.3–0.4 m [E]. Space the cube has not measured stays blank and is marked `UNDETERMINED`. HELM never draws in a wall it has not measured.
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

**Verdict: turning works today. Distance carried does not.**

**BMI323 (first pick, Section 6), from Bosch's preliminary flyer [M, S101]:**
- Gyroscope: zero offset ±1 °/s (typical over the part's life), temperature drift ±0.04 °/s/K, noise density 0.007 °/s/√Hz.
- Accelerometer: zero offset ±50 mg (typical over the part's life), temperature drift ±0.3 mg/K, noise density 180 µg/√Hz.
- A self-calibration step, run while the part is still, trims the gyroscope's scale error after soldering to ±0.7%.

**LSM6DSV16X (alternative):**
- An on-chip fusion block called SFLP ("sensor fusion low power") outputs three things [M, secondary, S102]:
  - a "game rotation vector" (an orientation with no north reference);
  - a gravity vector;
  - its own estimate of the gyroscope bias.
- It runs on as little as 15 µA [M, secondary, S102].
- ST staff say it estimates the bias only while the device is still [M, forum, S102].
- Gyroscope noise is about 2.8 mdps/√Hz (0.0028 °/s/√Hz). That figure is for the sibling LSM6DSV, not the 16X [M, secondary, S103]. The 16X's own zero-offset figure has not been checked [check].

**What the gyroscope can do [E, our arithmetic from the numbers above]:**
- **Bias.** Left uncorrected, a 1 °/s bias adds 60° of false turning per minute. So the bias must be re-measured each time the cube sits still. The cube is still most of the day, so this costs almost nothing.
- **Temperature.** After the bias is corrected, temperature becomes the main error. The cube warms when it talks or charges (Section 7). A 5 K rise moves the bias by up to 0.2 °/s, which is 12° per minute if it is not re-measured. So the gyroscope alone gives good heading for seconds to tens of seconds. It does not stay good for many minutes unless the bias is re-measured at each rest and corrected for temperature.
- **Noise.** Small: after 60 s it adds about 0.05° (0.007 × √60).
- **Scale.** At ±0.7%, a quarter turn (90°) can be off by up to 0.63°, and a full turn by up to 2.5°.
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
- The 6-axis IMU runs only while awake, so the first part of a pick-up may be missed [E]. The gyroscope's start-up time has not been checked [check].
- Rule: after any motion while asleep, the stored pose is marked `UNDETERMINED` until the cube relocalises.
- Gravity still tells which face is down.

**Heading without a compass.** The Qi2 magnet ring rules out a compass (Section 6). So:
- The cube keeps a **relative** heading. Angles are measured against the room's own walls, not against north. A room map does not need north [E].
- The gyroscope carries the heading through a turn. Each time the cube rests, HELM corrects the drift by matching depth readings and camera features against the map [E].
- Fusing a camera with an IMU this way is an established method, called visual-inertial odometry. VINS-Mono is one published example [M, S105].
- Camera matching works only in a lit room. The hidden cameras lose 1.9–3.1 f-stops behind the dark glass (Section 12). The ToF sensors carry their own light and work in the dark.
- If the owner wants true north, the phone's compass could supply it once at setup, while the phone is held to the cube [E, untested].
- Wi-Fi ranging gives distance, not direction (8a.2). It cannot correct heading.

**8a.2 Where in the world: geolocation**

| Method | Verdict | Why |
|---|---|---|
| GPS (GNSS) chip in the cube | **Poor fit; not fitted** | Indoors, satellite signals lose 5–15 dB in houses and 20–30 dB in office buildings [M, S106]. A good small receiver, the u-blox MAX-M10S, has its 1.5 m accuracy specified with satellites at −130 dBm. It needs −148 dBm for a cold start (no stored satellite data), and a cold start takes 27 s in open sky [M, S107]. A fix near a window in a timber house may be possible but is not dependable inside a sealed cube [E]. Tracking draws 25 mW [M, S107], more than the cube's whole asleep budget of about 11–25 mW (Section 7). The antenna would also sit beside the Qi coil and magnets [E]. |
| The phone's location, through the app | **Works today** | The phone already knows where it is. On Android, "approximate" location is accurate to within about 3 km². "Precise" is usually within about 50 m, and sometimes within a few metres [M, S108]. Town level is enough for time zone, weather and sunrise [E]. Default: approximate, asked once at setup, stored as a dated fact. |
| Wi-Fi positioning from a cloud database | **Works with limits; off by default** | The cube would send the list of nearby access points (hardware addresses and signal strengths) to a service such as Google's Geolocation API. The service returns a position and an accuracy radius [M, S109]. A 2005 city-scale study measured median errors of 13–40 m [M, S109]. It tells a third party about the home's surroundings, and the phone already gives the same answer [E]. |
| Wi-Fi round-trip-time ranging (FTM) | **Works with limits** | See below. It gives distance to an access point inside the home, not a street address. |
| Bluetooth Channel Sounding | **Not on this radio** | Channel Sounding arrived in Bluetooth 6.0 and is claimed to measure distance to 10–50 cm [M, secondary, S83]. The IW612 is Bluetooth 5.4 [M, S53]. Watch for it in version 2 [E]. |

**Wi-Fi round-trip-time ranging (FTM):**
- **What it is.** Fine Timing Measurement (FTM) times a Wi-Fi exchange with an access point and back. Distance = round-trip time ÷ 2 × the speed of light [M, S111]. It was introduced in IEEE 802.11mc and continues in IEEE 802.11az [M, S111]. Android calls it "Wi-Fi RTT" [M, S110].
- **The IW612 supports it.**
  - NXP's AN14044 (Rev. 3.0, 29 April 2026) lists the IW612 [M, S111].
  - In that note, a client device like the cube can start ranging with 802.11mc, 802.11az non-trigger-based ranging, and 802.11az trigger-based ranging [M, S111].
  - NXP's IW612 page lists "802.11az accurate ranging" [M, S53].
  - The i.MX 93 can run the NXP Linux driver this note uses [E].
- **Accuracy.**
  - Android's target for 802.11mc, at the 90th percentile, is an error of 2 m at 80 MHz, 4 m at 40 MHz, and 8 m at 20 MHz [M, S110].
  - For 802.11az it is 1 m at 80 MHz. That target assumes a phone with 2 antennas and an access point with 4 [M, S110].
  - The IW612 is a 1×1 radio (one data stream) with channels up to 80 MHz [M, S53]. So expect the 2 m class, not the 1 m class [E].
- **Limits.**
  - The access point must answer. Many home routers use chipsets without FTM. A community list names some that do [M, secondary, S113]. HELM must check, not assume: if no access point answers, the FTM range is `UNDETERMINED`.
  - One access point gives a distance, not a position. A position needs about three access points at known places [E]. Most homes have one to three, at places the cube does not yet know [E].
  - Walls and reflections bias the range. A 2025 survey of over 180 papers covers the accuracy problems and their fixes [M, S114].
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
| Notice motion near the cube | **Works with limits** | The IW612 has AMI [M, S112]. Comcast announced WiFi Motion on 18 August 2026. It turns the radio links between a gateway and fixed Wi-Fi devices into motion sensors. It detects motion, not who is moving. It is opt-in, and it cannot reliably tell a small pet from a child [M, secondary, S119]. Results change between rooms and people. One study found that a method which works in any room is still not proven [M, S116]. |
| Say whether a person is present, and roughly where | **Research-grade on one 1×1 radio** | A 2025 thesis reports presence and location up to 20 m, through walls, using low-cost Wi-Fi aimed in one direction [M, S117]. The library has not yet verified the record. The cube has one antenna stream and no direction finding [M, S53]. |
| Draw walls and furniture | **Research-grade** | One 2024 paper maps free space from Wi-Fi signal strength while moving [M, S118]. Nothing we found is ready for a product. |

**Verdict for the owner's words:** Wi-Fi gives the map two dated facts: roughly how far away the router is, and whether something moved. The depth sensors and cameras draw the schematic itself (8a.4). Wi-Fi sensing is off by default (8a.8).

**8a.4 Lidar: a tiny depth sensor behind each face**

**Verdict: works with limits. A spinning lidar does not fit.**
- A small spinning lidar, the RPLIDAR C1, is 55.6 × 55.6 × 41.3 mm, weighs 110 g and draws 1.15 W [M, distributor, S126]. It would fill most of a 64 mm cube. It would also need a window band around the middle, which breaks the plain-black-box rule [E].
- **Multizone ToF sensors fit.** One sits behind each face, beside the camera [E].

| | ST VL53L7CX (first pick, wide) | ST VL53L8CX (alternative) |
|---|---|---|
| Zones | 8 × 8 (64) or 4 × 4 [M, S122]; frame rate not checked [check] | 8 × 8 at up to 15 Hz; 4 × 4 at up to 60 Hz [M, S120] |
| View | 60° × 60° (90° diagonal) [M, S122] | 45° × 45° (65° diagonal) [M, S120] |
| Range | Up to 350 cm "under favorable conditions"; minimum 20 mm [M, S122] | Up to 400 cm; better in bright ambient light [M, S120, S122] |
| Light source | 940 nm invisible, Class 1 eye-safe laser (VCSEL) [M, S122] | The same [M, S120] |
| Size | Not checked [check] | 6.4 × 3.0 × 1.75 mm [M, secondary, S121] |
| Power | About 100 mA typical while ranging, peaks of 150 mA. Measured on a 3.3 V carrier board, which includes its regulator [M, distributor, S122] | About 215 mW in continuous ranging [M, secondary, S121]. ST quotes 1.6 mW at 4 × 4 and 1 Hz in low-power mode [M, secondary, S121]. One user measured about 68 mW at that setting [M, forum, S121] |
| Width of one zone at 3 m [E] | 7.5°, about 0.39 m | 5.6°, about 0.29 m |
| Share of all directions seen from one still pose, six faces [E] | About 48% | About 28% |

- **Coverage.** Six faces see in every direction only if each face covers 90° × 90° [E]. From one still pose, the VL53L7CX's 60° × 60° covers about 48% of directions, and the VL53L8CX about 28% [E]. Turning the cube by about 45°, or setting it down on another face, fills the gaps [E]. This is the owner's "moved, turned" way of mapping.
- **Detail.** At 3 m, one zone is 0.3–0.4 m wide [E]. Walls, doorways, sofas, tables and people show up. Chair legs, cables and small objects do not.
- **Far walls.** Beyond 3.5–4 m, nothing comes back [M, S120, S122]. In a large room, the far wall stays `UNDETERMINED` until the cube is moved closer [E].
- **Hard surfaces.** Glass, mirrors and very dark surfaces can give no reading or a false one [E]. The two-pose rule in 8a.5 guards against this.
- **Data.** Six sensors read 384 distances per frame (6 × 64) [E]. Each sensor needs about 84 KB of firmware loaded over the bus at start-up [M, S120].
- **A denser sensor to watch.** ST's VL53L9CX gives 2,268 zones (54 × 42) over 55° × 42°. It ranges from under 5 cm to 8.8 m, at up to 100 Hz, in a 12.8 × 6.1 × 4.6 mm module. Mass production started in July 2026 [M, secondary, S124]. Its power is not published. It connects by MIPI I3C or CSI, and the i.MX 93's one camera port is already busy (Section 8) [E]. It may suit one face in a later version.

**Behind dark glass (it needs an infrared window):**
- **What ST asks for.** The cover glass must pass more than 87% of the 940 nm light [M, S123]. st.com did not load during this check, so this figure was read through a search summary. The light crosses the glass twice, so 87% one way is about 76% round trip [E].
- **Why the camera glass will not do.** The cameras' dark face glass passes only 12–27% of visible light (Section 12, S23). The ToF needs the opposite: black to the eye, but clear at 940 nm.
- **Materials that could work:**
  - Visible-black, infrared-passing plastic filters exist. They are black to the eye and pass near-infrared above a cut-on wavelength of 670–910 nm, in thicknesses of 0.5–5.0 mm [M, S25]. Their transmission at 940 nm is not stated [check].
  - An infrared-passing black ink on the inside of the face glass is the other route [E].
- **Appearance.** When off, the window must look the same as the rest of the face. That needs testing on a sample in daylight and under a phone torch [E].
- **Crosstalk.** Light bouncing inside the cover glass ("crosstalk") is handled by ST's processing beyond 60 cm. Closer than that, each sensor must be calibrated with its cover in place [M, S120]. A black barrier between the emitter and receiver openings is needed under the glass [E].
- **Cameras.** The face cameras need their usual infrared-cut filters, so the 940 nm light does not show up in pictures [E].

**8a.5 How HELM builds and keeps the map**

**What it combines [E]:**
- gyroscope turns: how the cube moved between rests;
- ToF depth: where surfaces are;
- camera features: corner points that fix heading in a lit room (no pictures are kept);
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
| Gyroscope and accelerometer (6-axis IMU) | While awake, and after any motion | BMI323: 790 µA in high-performance mode [M, S101], about 1.4–2.9 mW at 1.8–3.6 V [E]. LSM6DSV16X: 0.65 mA [M, S72]; its fusion block from 15 µA [M, secondary, S102] |
| ToF, one face, continuous | Mapping sessions only | About 0.2–0.33 W [E, from S121 and S122] |
| ToF, one face, slow (1 Hz) | Mapping sessions only | 1.6 mW by ST's figure, about 68 mW as measured by one user [M, secondary and forum, S121]. Budget 10–70 mW [E] |
| ToF, all six faces continuous | **Not allowed** | 1.3–2.0 W [E]: a third to over half of the 3.7 W heat budget (Section 7) |
| Camera features | Mapping in a lit room | 0.9–1.1 W, the "camera in use" state (Section 7) [E] |
| Wi-Fi FTM ranging | Mapping sessions and "where am I" checks | NXP publishes no IW612 power figure [M, S53]. NXP's recommended setting is a 128 ms burst every 500 ms [M, S111], so the radio is busy about a quarter of the time [E]. Budget 50–150 mW [E] |
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

**While asleep:** only the ADXL367 runs. ToF, cameras, gyroscope, Wi-Fi ranging and Wi-Fi sensing are all off. Six ToF sensors in their 1.6 mW mode would add about 9.6 mW, close to the low end of the 11–25 mW asleep budget. At the 68 mW one user measured, six would add about 0.4 W [E].

**8a.7 Parts**

Motion, turning, Wi-Fi ranging and Wi-Fi sensing need no new part. The BMI323 or LSM6DSV16X, the ADXL367, the i.MX 93 and the IW612 are already in Section 11. The new parts are six ToF sensors and six infrared windows [E]. Rows are listed below for Section 11.

**8a.8 Privacy**

A room map and a location reveal a lot: the layout of the home, where people sleep, and when someone is home. They get the strictest defaults.

1. **Off by default.** Mapping, Wi-Fi sensing and cloud Wi-Fi positioning each stay off until the user turns them on in the app. HELM's RPM gate checks the consent flag before every session. With no flag there is no session, and the refusal is logged.
2. **Kept on the cube.** The map, the pose history and the location fact stay on the cube. The app reads them over the home network or Bluetooth. Cloud backup is opt-in only (Section 8).
3. **Delete control.**
   - The app can delete the whole map, one room, a drawn region, or the location fact.
   - Raw readings are deleted at the end of each session (8a.5).
   - Deleting from flash memory must really erase the data, not just unlink the file [E].
4. **Coarse location.** Approximate (town level) is the default [M, S108]. The map uses its own room coordinates, not latitude and longitude. Precise location only if the user chooses it.
5. **No third parties by default.** Cloud Wi-Fi positioning sends the nearby access-point list to an outside service (S109), so it stays off. The map is never shared with Matter devices or other apps by default.
6. **Wi-Fi sensing can sense through walls.** It can pick up a neighbour moving. Comcast tells its users in buildings with shared walls to lower the sensitivity [M, secondary, S119]. The cube records motion only, never who moved. It is off by default.
7. **Cameras used for mapping keep corner points, not pictures** [E]. The hardware green dot lights while any camera is powered (Section 9).
8. **The light shows mapping, and only mapping.**
   - **When it shows:** while any ToF sensor, camera mapping, Wi-Fi ranging or Wi-Fi sensing runs.
   - **The pattern:** one pale-magenta segment circles the four edges around the top face, once every 2 s, like a lighthouse [E].
   - **Colour rules:** pale magenta must never be used as a device colour. The pattern is also distinct by its motion, for colour-blind users [E].
   - **When it stops:** the cube goes dark and is a plain black box again.
   - Add this as a "Mapping" row to the Section 5 mode table.
9. **Hard mute covers depth sensing too.** The hard-mute switch (Section 9) should also cut power to the ToF sensors [E]. Soft mute stops mapping in firmware.
10. **Open choice for the owner:** should the ToF sensors get a hardware-wired indicator like the cameras, or is the firmware Mapping pattern enough? [E]
11. **Law** (not legal advice): a home map linked to a person is likely personal data in the EU [E]. The rules in Section 9 apply.

--- PARTS ROWS ---
| Room depth sensor, one per face (first pick) | VL53L7CX (ST) | 8 × 8 or 4 × 4 zones; 60° × 60° (90° diagonal); up to 350 cm "under favorable conditions", minimum 20 mm; 940 nm Class 1 VCSEL; about 100 mA typical while ranging on a 3.3 V carrier board, peaks 150 mA; module size and frame rate not checked | [M, distributor] | Good; needs an infrared window; six needed | S122 |
| Room depth sensor, alternative | VL53L8CX (ST) | 8 × 8 at up to 15 Hz, 4 × 4 at up to 60 Hz; 45° × 45° (65° diagonal); up to 400 cm; 940 nm Class 1; cover-glass crosstalk handled beyond 60 cm; about 84 KB firmware loaded at start-up; 6.4 × 3.0 × 1.75 mm; about 215 mW continuous; 1.6 mW at 4 × 4, 1 Hz in low-power mode (one user measured about 68 mW) | [M; size and power secondary] | Narrower view; better in bright rooms | S120, S121 |
| Dense depth sensor, watch | VL53L9CX (ST) | 2,268 zones (54 × 42); 55° × 42°; under 5 cm to 8.8 m; up to 100 Hz; 12.8 × 6.1 × 4.6 mm; MIPI I3C or CSI; power not published; mass production from July 2026 | [M, secondary] | Watch: power unknown; the camera port is already busy | S124 |
| ToF window, one per face | Visible-black, infrared-passing filter or ink (example: Phillips NIR acrylic filters) | Black to the eye; passes near-infrared above a cut-on of 670–910 nm; 0.5–5.0 mm thick; 940 nm transmission not stated [check]. ST asks for over 87% at 940 nm | [M] / [check] | Needed; matching the face's look must be proven on a sample | S25, S123 |
| Wi-Fi ranging and sensing (existing radio) | IW612 (NXP) | 1×1, channels up to 80 MHz; FTM ranging as a client: 802.11mc, 802.11az non-trigger-based and trigger-based (AN14044 Rev. 3.0, 29 April 2026); CSI and Ambient Motion Index on Linux (AN14011 Rev. 10.2, 25 June 2026); no 802.11bf statement found | [M] | Good; no new part | S53, S111, S112 |
| Gyroscope and accelerometer figures (existing part) | BMI323 (Bosch) | Gyroscope zero offset ±1 °/s, ±0.04 °/s/K, noise 0.007 °/s/√Hz; accelerometer zero offset ±50 mg, ±0.3 mg/K, noise 180 µg/√Hz; scale error after self-calibration ±0.7%; supply 1.71–3.63 V | [M, preliminary flyer] | Good for turns; not for distance | S101 |
| Orientation fusion (existing part) | LSM6DSV16X (ST), SFLP block | Game rotation vector, gravity vector, gyroscope bias; from 15 µA; bias estimated only while still; gyroscope noise about 2.8 mdps/√Hz on the sibling LSM6DSV | [M, secondary] | Good; heading still drifts without a compass | S102, S103 |
| GNSS receiver, not fitted | MAX-M10S (u-blox) | 25 mW continuous tracking; 1.5 m CEP with satellites at −130 dBm; cold start 27 s (default constellations); cold-start sensitivity −148 dBm | [M] | Not fitted: indoors, sealed cube, power | S107 |
| Spinning lidar, size reference | RPLIDAR C1 (Slamtec) | 55.6 × 55.6 × 41.3 mm; 110 g; 1.15 W; 360° at about 10 Hz | [M, distributor] | Does not fit | S126 |
| Ranging to the phone, watch | Bluetooth Channel Sounding (Bluetooth 6.0) | Claimed 10–50 cm; the IW612 is Bluetooth 5.4, so it is not available | [M, secondary] | Version 2 only | S83, S53 |

--- SOURCES ---
**Location, motion and mapping (Section 8a).** st.com pages timed out during this check. ST figures come from ST documents hosted elsewhere (the Pololu copy of UM3109, ST's China-site flyer), distributor pages, or search summaries, and are tagged that way.
- S101 https://storage.microchipusa.com/musadev/datasheetpdf/BST-BMI323-FL000-00.pdf (Bosch BMI323 flyer BST-BMI323-FL000-00, version 1.0, 09/2022; marked preliminary)
- S102 https://circuitdigest.com/news/new-advanced-6-axis-inertial-measurement-unit-with-embedded-sensor-fusion-and-ai (25 Nov 2022) ; https://community.st.com/mems-and-sensors-62/how-lsm6dsv16x-enables-sensor-fusion-low-power-sflp-algorithm-120280 ; https://community.st.com/t5/mems-sensors/lsm6dsv16x-gyroscope-bias/td-p/714927 (ST forum; read through a search summary)
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
- S119 https://www.bleepingcomputer.com/news/security/comcast-turns-your-xfinity-wifi-into-a-home-motion-detector/ (18 Aug 2026)
- S120 https://www.pololu.com/file/0J2030/um3109-a-guide-for-using-the-vl53l8cx-lowpower-highperformance-timeofflight-multizone-ranging-sensor-stmicroelectronics.pdf (ST UM3109 Rev 7, April 2024; Pololu-hosted copy)
- S121 https://www.st.com.cn/resource/en/flyer/vl53l7cx-vl53l8cx-flyer.pdf ; https://www.st.com/en/imaging-and-photonics-solutions/vl53l8cx.html ; https://wiki.adom.inc/kyle/vl53l8cx (secondary, unreviewed) ; https://community.st.com/imaging-sensors-49/vl53l8cx-power-consumption-is-too-high-139035 (forum) (ST pages read through search summaries)
- S122 https://www.pololu.com/product/3418 ; https://www.pololu.com/category/306/carriers-for-st-time-of-flight-tof-distance-sensors
- S123 https://www.st.com/resource/en/application_note/an5939-guidelines-for-the-cover-glass-of-the-vl53l8-timeofflight-tof-multizone-sensor-family-stmicroelectronics.pdf ; https://www.st.com/resource/en/application_note/an5962-guidelines-for-the-cover-glass-of-the-vl53l7-timeofflight-multizone-sensor-family-stmicroelectronics.pdf (did not load; the >87% at 940 nm figure was read through a search summary)
- S124 https://www.cnx-software.com/2026/06/22/st-vl53l9cx-direct-time-of-flight-3d-lidar-supports-5cm-to-9m-range-2-3k-zones-resolution/ ; https://www.st.com/vl53l9cx
- S125 https://www.hrl.uni-bonn.de/papers/hornung13auro-preprint.pdf (Hornung et al., OctoMap, Autonomous Robots 34:189–206, 2013)
- S126 https://www.waveshare.com/rplidar-c1.htm (distributor listing)