**Answer: power, heat, compute and radios for the HELM cube (research only; nothing was built or run, cost 0 USD)**

Legend: [M] means MEASURED-BY-SOURCE, from a datasheet, standard or vendor document. [M2] means the number comes only from a secondary source. [E] means ESTIMATE, my own figure. I did not invent any part numbers. Every part named below appears in a cited source.

## 1. Bottom line

1. **Qi charging only:**
   - The fastest current standard is **Qi v2.2.1, sold as "Qi2 25W"**. The WPC (Wireless Power Consortium) announced it on 2025-07-23. Its 25 W is "nearly 70% more" than the original 15 W Qi2 [M].
   - Qi2 needs a magnet ring. Only devices with magnets may use the Qi2 name [M].
   - That ring is about **54–56 mm across** [M2: 54.1 mm attributed to Apple's accessory guidelines; aftermarket rings are 54×46 mm and 56×46 mm].
   - **The ring will not fit inside a 55 mm cube.** With 2 mm walls the inside is about 51 mm [E].
   - The ring fits tightly at **60 mm** and comfortably at **62–65 mm** or more [E].
   - At 55 mm the cube can only use plain Qi with a smaller coil. Charging is about 5 W [M: the baseline 5 W level], or a bit more on a flat pad. There is no magnetic snap and no Qi2 logo.
2. **Heat, not the standard, limits charging speed.** A sealed, matte-black cube can shed only about **2.7 W (55 mm) to 4.4 W (70 mm)** of internal heat while it sits on a pad [E]. That is enough for about 10 W of steady charging at 55 mm and about 17 W at 70 mm [E]. Qi2 25W would only be a short burst on an empty battery, then the rate drops.
3. **Battery:** about **10–12 Wh at 55 mm** and **24–30 Wh at 70 mm** [E].
4. **The power design matters most.** If the always-listening state stays at about 20 mW, a typical day lasts about **6 days at 55 mm and about 14 days at 70 mm** [E]. If the main processor is left idling in Linux (199.9 mW [M]), it lasts **39 h at 55 mm** [E]. A smart-speaker design idles at 1.5–3 W [M2, third-party Echo tests], which would give **3–5 h** [E].
5. **Compute:** use two brains.
   - A tiny always-on part runs the wake word and shake/tap detection, at under 1 mW.
   - An NXP i.MX 93-class processor (two Cortex-A55 cores at 1.7 GHz plus a small AI accelerator) wakes only when needed. It runs HELM's recipe brain and, optionally, speech recognition and speech output on the device. NXP measured it at 7.6 mW asleep and 1264.1 mW at full stress [M].
   - At 55 mm, I recommend a microcontroller-only build with speech sent to the phone instead.
6. **Radios:** Wi-Fi 6 with Target Wake Time (TWT, a scheduled-sleep feature), Bluetooth LE with LE Audio, and an 802.15.4 radio for Thread/Matter, which is what lets the cube control other devices.
   - **Wi-Fi 7 is not needed.** Its gains are speed, which a voice cube does not use, and I found no published low-power numbers for Wi-Fi 7 chips.
   - **The shell must not be metal**, at least on the charging face and in front of the antennas [E].
7. **Recommended size: about 65 mm.** It is the smallest size where the Qi2 magnet ring, the Linux board and a 17–22 Wh battery all fit [E]. It matches a tennis ball's width (6.54–6.86 cm [M]). A 54 mm cube has the same *volume* as a 67 mm tennis ball [E, arithmetic].

## 2. What fits at each size [E unless marked]

Assumptions:
- Walls are 2 mm.
- The battery is a flat pouch sitting just above the Qi coil on the bottom face.
- Energy density is 600–750 Wh/L. The best phone cells reach about 835 Wh/L [M2, implied by Enovix's claim] and Enovix's AI-1 cell 935 Wh/L [M, vendor test]. Small custom pouches lose more volume to packaging.
- Usable energy is taken as 80% of the low end of the battery range.

| Cube edge | Inside volume | Qi2 magnet ring (~54.1 mm) | Battery pouch | Battery energy | Heat it can shed (5 faces / 6 faces)* | Steady charge rate | Time to 80% |
|---|---|---|---|---|---|---|---|
| 55 mm | 132.7 cm³ | **Does not fit** (51 mm inside) | 45×45×8 mm = 16.2 cm³ | 9.7–12.2 Wh (≈2.5–3.2 Ah) | 2.7 / 3.3 W | 5 W plain Qi; ≈10 W with a larger coil and alignment | ≈2 h at 5 W; ≈55–60 min at 10 W |
| 60 mm | 175.6 cm³ | Fits, tight (56 mm inside) | 50×50×9 = 22.5 cm³ | 13.5–16.9 Wh | 3.2 / 3.9 W | ≈12–14 W | ≈60–70 min |
| 65 mm | 227.0 cm³ | Fits, comfortable | 54×54×10 = 29.2 cm³ | 17.5–21.9 Wh | 3.8 / 4.6 W | ≈15 W | ≈60–75 min |
| 70 mm | 287.5 cm³ | Fits, comfortable | 58×58×12 = 40.4 cm³ | 24.2–30.3 Wh (≈6.3–7.9 Ah) | 4.4 / 5.3 W | ≈17 W; 25 W only as a burst | ≈75–80 min |

\*How the heat figures were worked out:
- Heat shed = h × area × ΔT.
- h ≈ 10 W/m²K [E]. That is natural air flow of about 4–6 W/m²K plus heat radiation of about 5.9 W/m²K. The radiation figure assumes a matte black surface (emissivity about 0.9) and comes from 4εσT³ at 307 K.
- Sources give natural air-flow values of 1–25 W/m²K for gases [M] and about 7 W/m²K for a heat-sink case [M].
- ΔT = 18 K, from 25 °C room air to 43 °C on the surface.
- While charging, one face sits on the pad, so only 5 faces shed heat, and the pad also warms that face.
- The steady charge rate assumes about 20% of the received power becomes heat inside the cube (coil, rectifier and charger chip) [E].

The thermal limits behind this:
- **Touch temperature:** under IEC 62368-1, a surface touched for more than 1 minute may reach **48 °C for metal and 48 °C for plastic** [M, UL brief of Table 42]. I used 43 °C as the design target for an object people hold or touch for a long time [E]. Check the current edition of the standard, which has stricter rows for long contact.
- **Battery temperature:** JEITA-style chargers cut charge current or voltage above a "warm" point. On TI's BQ25618E that point defaults to **45.5 °C**, with **10 °C** as the "cool" point; it stops charging below 0 °C (T1) and above 60 °C (T5) [M]. In a sealed cube the battery sits only a few degrees above the shell. This 45 °C limit is the one that actually stops charging [E].
- **Color:** black is the right color for cooling, because a matte black surface radiates heat well. A polished metal shell (emissivity about 0.1) would lose roughly half of the cooling and would also block Qi and the radios [E].
- **Charging and talking share one heat budget.** Firmware must lower the charge rate while HELM is talking or using a camera [E].

Qi coil facts:
- Plain Qi receivers can be backward compatible at 5 W [M, Infineon Qi2 reference design].
- Small-device pads on current Qi2 25W stations give earbuds and watches 5 W [M, product listing].
- Example coils that fit 55 mm:
  - Würth 760308102213: 29 mm, 7.9 µH, 1.7 A [M2, distributor listings].
  - Würth 760308103305: 44 × 45 × 0.72 mm, 8.8 µH, 5 A [M2]. RS lists it as no longer stocked.
- At 55 mm, align the cube with a shallow square charging dish instead of magnets [E].
- With no buttons, use the charger chip's "ship mode" for shipping. Placing the cube on a Qi pad wakes it [E].
- The governing document for the magnet profile is IEC 63563-10:2025 (Qi v2.0 MPP), a paid document [M]. **Check the ring size against it before committing to a size.**

## 3. Power budget table

| State | Part (source) | Power | Tag |
|---|---|---|---|
| **A. Asleep but listening (24 h/day)** | 2 mics in low-power mode: IM69D129F, 170 µA each, at about 1.8 V | 0.6 mW | current [M2]; voltage [E] |
| | Wake-word chip: Syntiant NDP120, "under 280 µW" | 0.28 mW | [M, vendor claim] |
| | Shake/tap sensor: Bosch BMA400, tap/double tap under 8 µA | ≈0.015 mW | [M, Bosch flyer] |
| | Wi-Fi 6 staying connected: SiWx917 modules, about 20 µA with TWT and a 60 s keep-alive | ≈0.07 mW best case; **2–10 mW on routers without TWT** | [M, vendor] / [E] |
| | Bluetooth LE idle link to the phone | 0.1–0.5 mW | [E] |
| | Main processor parked: i.MX 93 "System in DSM" (deep sleep), SoC only | 7.6 mW | [M, NXP AN13917] |
| | Memory self-refresh plus power chips and fuel gauge | 2.5–6 mW | [E] |
| | Light strip switched off when dark | 0 mW; dim "breathing" 5–20 mW | [E] |
| | **Total, state A** | **≈11–25 mW**; 3–15 mW if the main processor is fully off | [E] |
| **B. Listening after the wake word, speech recognition on the device** | i.MX 93 at work: Dhrystone 805.9 mW; eIQ AI benchmark 725.5 mW | 700–900 mW | [M] as a stand-in |
| | Memory active | 100–200 mW | [E] |
| | 6 mics in high-performance mode, 450 µA each | ≈5 mW | [M2] |
| | Light strip "listening" glow | 50–150 mW | [E] |
| | **Total, state B** | **≈0.9–1.3 W** | [E] |
| **C. Speaking, with the light pulsing to the speech rhythm** | Processor running speech synthesis | 700–900 mW | [M] as a stand-in |
| | Speaker amplifier MAX98357A: 3.2 W maximum into 4 Ω at 5 V, 92% efficient at 1 W, 2.4 mA idle | 0.2–0.6 W average for speech | [M] spec / [E] average |
| | Light strip pulsing | 100–300 mW | [E] |
| | **Total, state C** | **≈1.1–1.9 W** | [E] |
| **D. Speech sent to the phone instead** | Main processor stays parked. A small chip sends compressed audio over BLE. ESP32-C6 BLE radio peaks: receive 71 mA, transmit at 0 dBm 130 mA; the radio is mostly off | ≈50–150 mW total | peaks [M]; average [E] |
| **E. Camera** | Low-power presence sensor HM0360: VGA at 60 fps 7 mA (≈20 mW at 2.8 V); watch mode 50 µA | ≈20 mW | [M, preliminary datasheet] |
| | Full camera use: i.MX 93 "Machine vision" 780.5 mW plus a sensor at 100–250 mW | ≈0.9–1.1 W | [M] + [E] |
| **Wi-Fi peaks (ESP32-C6, 3.3 V)** | Receive 802.11ax at 20 MHz: 78 mA (≈257 mW). Transmit 802.11ax at 16.5 dBm: 252 mA (≈832 mW) | duty-cycled | [M] |

Runtime per day [E]. Usable energy is 7.8 Wh at 55 mm and 19.4 Wh at 70 mm. Each conversation turn is 15 s at about 1.5 W.

| Usage | Energy per day | 55 mm | 70 mm |
|---|---|---|---|
| Listening only, about 20 mW | 0.48 Wh | ≈16 days | ≈40 days |
| Light: 30 turns, 5 min of camera | ≈0.75 Wh | ≈10 days | ≈26 days |
| Typical: 100 turns, 15 min of camera | ≈1.36 Wh | ≈5.7 days | ≈14 days |
| Heavy: 300 turns of 20 s at 1.6 W, 60 min of camera | ≈4.15 Wh | ≈1.9 days | ≈4.7 days |
| Talking nonstop at 1.5 W | — | ≈5.2 h | ≈12.9 h |
| Mistake: processor left idling in Linux (199.9 mW [M]) | — | ≈39 h | ≈97 h |

One more point: each spoken turn costs about the same energy whether speech is handled on the cube (about 1 W for a few seconds) or sent over Wi-Fi (about 0.26–0.83 W radio peaks) [E]. What decides battery life is how low the always-listening state goes, not where speech is processed.

## 4. Compute options and recommendation

**What has to run where:**
- **HELM's recipe brain is tiny.** It uses exact fractions and has few parameters. Running it costs almost nothing on any chip [E].
  - Today it is written in Python, so it needs Linux, which means an application processor.
  - If it were ported to C or Rust, it could run on a microcontroller [E].
- **Speech recognition and speech output are the heavy parts:**
  - Moonshine Tiny has 27M parameters [M, arXiv 2509.02523]. Its makers report about 5× less compute than Whisper tiny.en for a 10-second clip [M, arXiv 2410.15608]. It is MIT-licensed [M].
  - Kokoro has 82M parameters and an Apache-2.0 license [M].
  - Piper is a "fast and local" voice engine under GPL-3.0. Its development moved to the OHF-Voice/piper1-gpl repository [M]. Note GPL-3.0 if it ships inside a product.
  - At 8-bit precision, Moonshine Tiny's weights are about 27 MB and Kokoro's about 82 MB [E]. Neither fits the 5 MB on-chip memory of a microcontroller [M: PSoC Edge E84 has 5 MB SRAM]. **Speech that understands any words needs a processor with external memory, or offload to the phone.**

**Candidate parts (all real, all cited):**

| Role | Part | Key facts |
|---|---|---|
| Always-on wake word | Syntiant NDP120 | Under 280 µW for wake words [M] |
| Always-on wake word plus a small HELM core | Infineon PSoC Edge E84 | Cortex-M55 at 400 MHz with an Ethos-U55 accelerator (128 MACs) and 5 MB SRAM; Cortex-M33 at 200 MHz; wake word in hardware [M]. I found no power figures; low-power performance is [E] |
| Main processor | NXP i.MX 93 | 1–2 Cortex-A55 at 1.7 GHz, Cortex-M33 at 250 MHz, Ethos-U65 accelerator (0.5 TOPS [M2]), LPDDR4/4X memory, 9×9 mm package option [M]. Measured: DSM 7.6 mW, Linux asleep with M33 waiting 122.4 mW, idle without display 199.9–345.6 mW, audio playback 458.6 mW, Dhrystone 805.9 mW, maximum stress 1264.1 mW (SoC only) [M] |
| Main processor plus radio in one package | NXP i.MX 93W | Two A55 cores, Ethos-U65, Wi-Fi 6 + BLE + 802.15.4 in the same package. **Pre-production**; specs may change [M] |
| Too big or too hot | Qualcomm QCS6490 | 8 cores, 12 TOPS [M]. No power figure published; phone-class [E] |
| Alternative | Synaptics Astra SL2610 | A55 cores plus a Cortex-M52, about 1 TOPS accelerator [M] |

**Recommendation:**
- **65–70 mm build (recommended):**
  - Wake word: NDP120, or the i.MX 93's own M33 core.
  - Shake/taps: BMA400.
  - Main: i.MX 93 with 1–2 GB of memory [E].
  - Radio: NXP IW612. It handles Wi-Fi 6 on 2.4 and 5 GHz, Bluetooth LE 5.4 and 802.15.4 (Thread/Matter), and NXP already pairs it with the i.MX 93 on the FRDM-IMX93 board [M].
  - HELM runs as it is. Speech is on the cube by default, so it works offline and keeps audio private.
  - Speech goes to the phone when the cube is hot or the battery is low.
- **55 mm build:**
  - PSoC Edge E84 with Infineon's AIROC CYW55513 radio (Wi-Fi 6/6E on 2.4, 5 and 6 GHz, TWT, Bluetooth [M]). Infineon's own kits use this pairing [M].
  - Or ESP32-C6, which is cheaper: Wi-Fi 6 on 2.4 GHz only, BLE 5.3, 802.15.4, 160 MHz [M].
  - HELM's core would need to be ported to C or Rust [E].
  - Only the wake word and a short command list run on the cube. Open-ended speech goes to the companion app.
- **What must be measured before choosing:** the real speed and power of Moonshine plus Piper or Kokoro on two A55 cores. I found no published figures. This needs a dev board such as the FRDM-IMX93. Buying one is the owner's call. AWS ARM servers would not be a faithful stand-in [E].

## 5. Radios

- **Wi-Fi 6 with TWT:** yes. TWT is what makes staying connected cheap (about 20 µA vendor claim [M]). Many home routers lack TWT, so plan for 2–10 mW [E].
- **Dual-band Wi-Fi** (IW612, CYW55513) copes better with crowded homes than 2.4 GHz-only (ESP32-C6) [E].
- **Wi-Fi 7:** the Synaptics SYN4390 exists. It offers Wi-Fi 7 on three bands, 2x2 antennas, multi-link, Bluetooth 6.0 with LE Audio and Channel Sounding, and 802.15.4/Matter [M]. Synaptics publishes no power numbers [M], and Wi-Fi 7's extra speed gives a voice cube nothing it needs [E]. **Skip it for version 1.**
- **Bluetooth LE Audio:** useful for sending speech to the phone [E].
- **Bluetooth 6.0 Channel Sounding** measures distance [M]. It could confirm the phone is close when the user taps to connect [E]. The CYW55513 is listed as Bluetooth 5.4 in some places and 6.0 in others [M]; check the datasheet.
- **802.15.4 (Thread):** needed to control Matter-over-Thread devices. The IW612, ESP32-C6, SYN4390 and i.MX 93W have it. **The CYW55513 does not list it** [M].
- **Antennas:** a quarter-wave at 2.4 GHz is about 31 mm, so chip antennas fit even at 55 mm. They need non-metal windows in the shell [E].

## 6. Still open (owner or other teams)

- Confirm the Qi2 magnet ring size against IEC 63563-10 or WPC member documents. This single number decides the 55 mm versus 60+ mm question.
- Measure on-device speech on real A55 hardware.
- Choose the router assumption: whether TWT is available.
- Six-face cameras and the charging face: the Qi coil and ring fill the center of the bottom face, so any camera, microphone or speaker on that face must sit near the corners [E].

## Sources

- WPC Qi2 25W press release (2025-07-23): https://www.wirelesspowerconsortium.com/media/wvsmia32/qi2-25w-news-release-v72.pdf
- WPC Qi page: https://www.wirelesspowerconsortium.com/standards/qi-wireless-charging/
- GSMArena, Qi2 25W official: https://m.gsmarena.com/qi2_25w_is_official_promises_hundreds_of_devices_will_support_it-amp-68741.php
- Qi2 magnets rule: https://9to5google.com/2024/12/20/qi2-magnets/
- Qi2 Ready: https://9to5google.com/2025/01/07/qi2-ready-built-in-magnets/
- IEC 63563-10 listing: https://www.vde-verlag.de/iec-normen/254762/iec-63563-10-2025.html
- Magnet ring size, secondary: https://forum.khadas.com/t/what-is-the-diameter-of-the-magnetic-ring-in-the-tea-amp/15443 and https://medium.com/@duanh148/what-size-is-magsafe-magnet-7b14f5d6c450 and https://totalelement.com/products/54-x-46-x-1-5mm-magsafe-neodymium-rare-earth-magnet-phone-attachment-ring-assembly-with-alignment-magnet-5-pack
- Infineon Qi2 transmitter, 5 W baseline: https://www.infineon.com/cms/en/about-infineon/press/market-news/2023/INFPSS202310-003.html
- Qi2.2 3-in-1 station with 5 W earbud pad: https://www.hotukdeals.com/deals/amazon-basics-25w-qi22-certified-3-in-1-wireless-charging-station-45w-power-brick-15m-cable-4930648
- Würth coils: https://uk.rs-online.com/web/p/wireless-charging-coils/1354633 and https://www.distrelec.ch/en/charging-coil-receiver-9uh-7a-330mohm-wuerth-elektronik-760308102213/p/30121381
- Enovix cell energy density: https://ir.enovix.com/news-releases/news-release-details/independent-testing-confirms-enovix-ai-1tm-achieves-935-whl
- Touch temperature (UL brief on IEC 62368-1): https://japan.ul.com/wp-content/uploads/sites/27/2014/06/1_techbrief_touchtemp.pdf
- Air cooling coefficients: https://www.purdue.edu/freeform/me418/wp-content/uploads/sites/30/2025/09/ME-418-Lec-67-Heat-Transfer.pdf and https://www.comsol.com/paper/heat-transfer-coefficient-for-a-finned-cpu-heat-sink-under-natural-convection-136252
- TI charger temperature limits (BQ25618E): https://ti.com/document-viewer/BQ25619E/datasheet/GUID-8C31B571-FE9C-4DC4-AFEF-0BD1B1196679
- ESP32-C6 datasheet v1.5: https://documentation.espressif.com/esp32-c6_datasheet_en.pdf
- SiWx917 Wi-Fi 6 modules: https://investor.silabs.com/news-releases/news-release-details/silicon-labs-breakthrough-ultra-low-power-wi-fi-6-and-bluetooth
- PSoC Edge E84: https://www.cnx-software.com/2024/04/19/infineon-psoc-edge-e81-e83-e84-cortex-m55-m33-mcu-machine-learning-iot-consumer-industrial-applications/
- CYW55513: https://embeddedcomputing.com/technology/processing/chips-and-socs/product-of-the-week-infineon-technologies-airoc-cyw55513-wi-fi-and-bluetooth-combo-ic and https://documentation.infineon.com/cyw55513/docs/nhu1755169548502
- NXP IW612: https://www.nxp.com/iw612
- NXP i.MX 93W: https://www.nxp.com/products/IMX93W
- FRDM-IMX93 board: https://www.nxp.com/company/about-nxp/smarter-world-blog/BL-FRDM-IMX93-DEVELOPMENT-BOARD-LAUNCHES-ON-BOARD
- i.MX 93 product page: https://www.nxp.com/products/i.MX93
- i.MX 93 power app note AN13917 Rev 4.0: https://www.nxp.com/docs/en/application-note/AN13917.pdf
- Synaptics SYN4390: https://www.synaptics.com/assets/product-brief/syn4390-triple-combo-wi-fi-7-bluetooth-and-802-15-4-soc
- Synaptics SL2610: https://www.synaptics.com/products/embedded-processors/sl2610-product-line
- Qualcomm QCS6490: https://www.qualcomm.com/internet-of-things/products/q6-series/qcs6490
- Syntiant NDP120: https://www.eeworldonline.com/low-power-conversational-ai-chips-support-google-hot-words/ and https://www.eetasia.com/syntiant-leads-tinyml-benchmark-results/
- Bosch BMA400: https://www.bosch-sensortec.com/media/boschsensortec/downloads/product_flyer/bst-bma400-fl000.pdf
- Infineon microphones: https://www.allaboutcircuits.com/news/infineon-debuts-pair-rugged-mems-microphones-harsh-environments/
- HM0360 camera sensor: https://www.welectron.com/mediafiles/productimg/arducam/Datasheet/HM0360-image-sensor-datasheet.pdf
- MAX98357A amplifier: https://www.analog.com/products/MAX98357A
- Moonshine papers: https://arxiv.org/abs/2509.02523 and https://arxiv.org/abs/2410.15608
- Moonshine code and license: https://github.com/moonshine-ai/moonshine
- Kokoro: https://github.com/hexgrad/kokoro
- Piper: https://github.com/OHF-Voice/piper1-gpl
- Echo idle power, third-party tests: https://www.esource.com/printpdf/211344 and https://www.homeandsmart.de/echo-stromverbrauch-738798
- ITF tennis ball size: https://www.itftennis.com/media/4420/2023-technical-booklet.pdf