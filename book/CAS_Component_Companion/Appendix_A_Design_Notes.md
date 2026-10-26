# Design Notes and Frozen Inventory

*Appendix A.*

**Working title:** Illustrated Electrical Symbols and Cognitive Schematics  
**Status:** maintenance inventory. Part of this guide, and the place to start if you are extending it.  
**Scope:** one functional-role map per symbol. Component symbols are conventional circuit notation adapted to the book's visual grammar; they are not a new CAS ontology and do not imply one component = one Noetic.

## Mapping labels used on the plates

- **ISO — exact structural isomorphism:** one-to-one at the level of functional roles; the relation has the same form.
- **ENG — engineered analog:** the role correspondence is explicit, but a cognitive quantity, control input, or conservation rule is stipulated by the design.
- **PED — pedagogical analogy:** the resemblance teaches only; no quantitative transfer.

## Symbol plates

### S0 — Signal and annotation legend

- Terminal / port node — named source or destination boundary (`PORT`)
- Domain color key — P amber, C blue, E red, O green; labels and shapes remain authoritative in grayscale
- Items 36, 37, and 40–42 below are demonstrated here and remain numbered under S6 for deck traceability.
- This guide's printable card deck keeps 56 total cards by folding five narrow or derived entries into their parent cards: Varactor into Capacitor/LC, Current mirror into Differential Pair, and NAND/NOR/XNOR into the AND/OR/NOT/XOR logic family. The chapter plates and this inventory still preserve all 42 individual entries.
- **Deck numbers and inventory numbers agree only from deck card 28 onward.** Cards 6–27 were numbered consecutively across the five folded entries, so deck 9 is inventory 5 (LC tank; Varactor skipped) and deck 18 is inventory 15 (Active load; Current mirror skipped). Never read a deck number below 28 as an inventory index.

### S1 — Flow and state retention

1. Resistor — activation-current limiter (`R`)
2. Capacitor — state retention / accumulated composition (`C`)
3. Inductor — pattern inertia (`L`)
4. Varactor — tunable state retention (`D` / `CV`)
5. LC tank — resonant state exchange (`Z` / composite)

### S2 — Direction, threshold, and sensing

6. Diode — directed admissibility guard (`D`)
7. Zener diode — threshold conduction and clamp (`ZD`)
8. Transformer — domain impedance matching (`T`)
9. Photodiode — stimulus intake transducer (`PD`)
10. Bridge rectifier — polarity normalization only (`BR`); **PED**, never a `^3` Negative-to-`^2` Positive converter

### S3 — Active and comparative parts

11. Cognitive Junction Transistor — controlled trigger-to-arrival transition (`Q1` / `CJT`)
12. Op-amp — high-gain differential stage with feedback (`U1`)
13. Differential pair — matched comparison stage (`Q2`, `Q3`; composite)
14. Current mirror — replicated bias (`Q4`, `Q5`; composite)
15. Active load — current-to-difference conversion (`Q6` / composite)

### S4 — Rhythm and register conversion

16. Oscillator — sustained `Phi` cycle (`OSC`)
17. Crystal — low-drift timing reference (`Y`)
18. Phase-locked loop — entrainment to an external reference (`U2` / `PLL`; composite)
19. ADC — register translation with quantization (`U`)
20. DAC — register translation with smoothing (`U`)

### S5 — Logic and routing

21. AND
22. OR
23. NOT
24. NAND
25. NOR
26. XOR
27. XNOR / equivalence detector
28. MUX
29. DEMUX
30. Relay
31. Schmitt trigger

**Logic correction:** standard XOR is true when exactly one input is true. A both-active conflict detector is AND. XNOR reports equal inputs, including both-active and both-inactive; it needs an OR/activity qualifier if used to isolate both-active conflict.

### S6 — Regulation, protection, and annotations

32. Voltage regulator
33. Fuse
34. Circuit breaker
35. Drive rail
36. Reference / rest node
37. Probe / test point
38. Switch / enable
39. Meter / CAS-Ohm mode marker
40. Net label (typed CAS state on a wire)
41. Solid forward path
42. Dashed feedback path

## Schematic plates

1. **CJT atom** — `^8` Above/Cause trigger + `^5` Female substrate → `^9` Below/Effect arrival.
2. **Domain descent** — directed admissibility across `P → C → E → O`, plus explicit `O → P` feedback path.
3. **Gain cascade** — multi-stage CJTs; stage gain and bias separation.
4. **RC feedback** — sampled output returned through a low-pass compensation path.
5. **Ambiguity stabilizer** — AND conflict detector + Schmitt hysteresis; standard XOR shown separately as exclusivity detector.
6. **CSB red path** — clamped refusal stage, reachable fuse threshold, and output-path polarity.
7. **CDAB differential pair** — commensurable input axes, shared bias, matched gain, difference output.
8. **COB rhythm circuit** — LC tank + PLL + crystal reference.
9. **CMB retention cell** — capacitor, leakage, charge/discharge, refresh, and lacunarity probe.
10. **CPMB supply** — seven Drive rails, regulators, `P → C → E → O` sequencer, brownout hysteresis, and silent emergency cutoff.

## Non-negotiable notation rules

1. Every signal wire carries a typed state or explicitly named scalar/control quantity.
2. Solid arrows are forward signal paths. Dashed arrows are feedback paths.
3. Color reinforces Domain but never carries meaning alone.
4. `+` means co-presence. `×` requires a named emergent result. `|⟨…⟩` is register-set specification.
5. `^3` Negative is repulsion, not decomposition. `^6` Male is decomposition.
6. `^8` Above/Cause is associative triggering, not reasoning. A reasoned landing uses `^6` and `^9` as appropriate.
7. ADC/DAC examples hold Noetic and Domain fixed when demonstrating pure Register translation.
8. Parameter values on every plate are design choices, not measured cognitive or model results.

## Resolved guardrails retained for maintenance

- The book's CJT labels Cause/Bias/Effect are a cognitive functional abstraction, not the conventional BJT small-signal input/output terminal convention. Plates must show both labels without claiming transistor terminal identity.
- CAS firing thresholds for Boolean gates are design stipulations; continuous open-simplex activations are not intrinsically binary.
- Standard ground denotes an electrical reference. Calling it a cognitive `^0` rest state is an engineered convention, not a canonical identity; use **Reference / rest node** on the plate.
- The bridge rectifier entry remains pedagogical unless a non-valence scalar polarity is defined. Do not map it as aversion-to-attraction conversion.
- ADC and DAC are separately directed Register translations. Quantization makes ADC lossy, so the DAC is not called its inverse.
- Composite parts with no stable one-line CCDL constructor use a labeled composite schematic or documented call-shaped form rather than invented syntax. Preserve the book's defined `Differential<...>`, `mirror ... replicate(...)`, `active_load ... decompose(...)`, and `LC<...>` forms.

## Card deck accounting

- Cards 1–5: five reading and claim-boundary guides, including the Domain/color/label legend.
- Cards 6–34: 29 individually printed component cards; the five folded roles above are cross-referenced on their parent cards.
- Cards 35–42: eight annotation cards, taught as three families: **Supply & Zero** (#35–36), **Observe & Name** (#37 and #39), and **Route & Grammar** (#38 and #40–42).
- Cards 43–52: ten compact cognitive-state circuit cards.
- Cards 53–56: four study, claim, print, and construction cards.
- Total: **56 cards = 7 US-Letter sheets × 8 cards**.

## Automated checks over this guide

Run from `build/`. All of them must pass before this guide ships.

| Script | What it proves | What it does not prove |
|---|---|---|
| `audit_plate_connectivity.py` | Reviewed source strings — terminal coordinates, typed states, Domain styles, symbol conventions — are still present. | Anything nobody wrote down. It is a regression lock, not a verifier. |
| `audit_plate_geometry.py` | Reads the **compiled** PDF of each schematic and fails on any wire endpoint that lands on no other ink (tolerance 1.25 mm). Intentional free ends are listed with a reviewed reason in `dangling_whitelist.json`; a whitelist entry that becomes connected also fails, so the list cannot rot. | The seven symbol plates, which draw each glyph in isolation by design. |
| `audit_symbol_invariants.py` | Each glyph is electrically itself: bridge diodes point at the node they feed, the current mirror is diode-connected and shares its bias, the Schmitt hysteresis mark stays inside the triangle, the switch is drawn open, and the relay linkage, breaker trip square and Zener bar are attached. | Aesthetics, or conformance to a cited standards document. |
| `test_plate_negative.py` | All three audits above can actually fail: it breaks the library once per historical defect and requires the matching audit to report it. | Nothing further; it exists so the other three cannot pass vacuously. |

`verify_plates.py` compiles all 17 figures standalone; `verify_cards.py` checks the 56-card deck
(numbering, one badge per card, page count, US-Letter size, and every semantic guard);
`test_badge_guard.py` proves the compile-time badge check rejects a hybrid label; and
`verify_deliverables.py` cross-checks the finished guide against the finished deck.

## Open review items

- **DAC trapezoid convention.** The wide parallel side now marks the multi-bit port on both converters, with short parallel stubs on the digital side and the `A/D` / `D/A` text naming the direction. This follows the common databook convention; confirm it against the house standard before changing it again.
- **Bridge rectifier node convention.** Left and right corners are AC, top is DC+ and bottom is DC-. The four diode orientations are now *derived* from that convention by `audit_symbol_invariants.py` rather than frozen as literals.
- **Cover spine for the current page count.** Regenerate the cover wrap whenever the interior page count changes; the paperback spine factor is 0.002252 in per page.

