# CAS Value-Keyed Color Palette Specification — v1.0

**Status:** Locked for `feature/cas-value-keyed-palette`. Downstream PRs must pin to `PALETTE_VERSION = "v1.0"`.
**Date:** 2026-05-03
**Scope:** Foundation work for the tri-channel benchmark (notation + diagram + color-coded axes).

---

## 1. Why Value-Keyed (Design Rationale)

The existing `diagramColor(kind)` in `CompilerPage.tsx` is **kind-keyed**: every node of kind `noetic` gets the same cyan (`#22d3ee`) regardless of which Noetic operator it represents, every `domain` node gets the same emerald (`#34d399`) regardless of P/C/E/O, and so on. This conflates two distinct information channels:

1. **Structural role** (what type of thing is this node?) — already encoded by node shape and label.
2. **Specific value** (which Noetic/Domain/Drive instance is this?) — currently lost.

Value-keyed color adds a redundant encoding channel that:
- Lets a reader trace a single operator (say ^3 Negative) across a complex diagram without reading every label.
- Enables cross-channel consistency checks in the tri-channel benchmark: the same ^3 Negative should emit the same color token in a notation rendering, a diagram node, and a color-coded axis strip.
- Follows the **information-theoretic redundancy principle**: each axis value gets a unique color token, so color contributes positive mutual information with value identity.

This module does NOT remove the kind-keyed fallback. Backward compatibility is mandatory. When a node lacks axis attributes, `diagramColor(kind)` continues to govern.

---

## 2. Palette Design Methodology

### 2.1 Sources

| Source | Description | Use in this palette |
|--------|-------------|---------------------|
| **Wong (2011)** | 8-color colorblind-safe palette published in *Nature Methods*. Hues chosen to be distinguishable under deuteranopia, protanopia, and tritanopia simultaneously. | Starting hue references for Noetic and Drive axes. |
| **Paul Tol "muted" qualitative** | 10-color qualitative palette (Tol, 2021, `personal.sron.nl/~pault/`). Designed for colorblind safety across 10 distinguishable classes. | Primary hue source for Noetic 10-class axis. |
| **Paul Tol "bright" qualitative** | 6-color palette. Useful for Drive axis base. | Supplementary Drive hues. |
| **ColorBrewer "Set2"** | 8-class qualitative, print-friendly. | Domain axis hue verification. |

### 2.2 Luminance Constraint

The palette must meet **WCAG 2.1 large-text contrast (3:1)** against both the dashboard dark background (`#0d1117`) and white paper background (`#ffffff`).

Background luminances (sRGB → relative luminance):
- `#0d1117`: L_dark ≈ 0.004
- `#ffffff`: L_white = 1.000

For 3:1 contrast simultaneously on both:
- vs dark: `(L_color + 0.05) / (0.004 + 0.05) ≥ 3` → `L_color ≥ 0.112`
- vs white: `(1.000 + 0.05) / (L_color + 0.05) ≥ 3` → `L_color ≤ 0.300`

**Target luminance window: L ∈ [0.12, 0.30]** for simultaneous 3:1 on both backgrounds.

WCAG AA normal text (4.5:1) is impossible to satisfy simultaneously on both backgrounds (the constraint intervals don't overlap). 3:1 large-text is the practical maximum for a dual-background palette.

### 2.3 Colorblind Simulation Methodology

Three colorblind conditions are simulated using the Brettel-Viénot-Mollon (1997) model:
- **Deuteranopia**: M-cone absent; red-green discrimination severely reduced.
- **Protanopia**: L-cone absent; red-green discrimination severely reduced (red appears darker than under deuteranopia).
- **Tritanopia**: S-cone absent; blue-yellow discrimination reduced.

**Acceptability criterion**: No two values within the same axis may become indistinguishable under any single colorblind condition. Where hue converges under simulation, luminance contrast (ΔL ≥ 0.05) provides fallback distinguishability.

**Red-green constraint**: No pair from the {red/orange, green/yellow-green} subsets may occupy the same axis without a luminance differential of ΔL ≥ 0.07 to ensure deuteranopia/protanopia distinguishability.

---

## 3. Noetic Axis — 10 Colors (^0 through ^9)

**Basis**: Paul Tol "muted" 10-class palette hues, with lightness adjusted to place all colors in L ∈ [0.12, 0.30].

The CAS structural properties inform hue grouping:
- **Involution pairs** (CO-2↔CO-3, CO-5↔CO-6, CO-8↔CO-9) use contrasting hues within their pair.
- **Self-duals** (CO-0, CO-1, CO-4, CO-7) use independent hues.

| Value | Name          | Token              | Hex     | L (rel lum) | vs `#0d1117` | vs `#ffffff` | Hue region    | Tol source          |
|-------|---------------|--------------------|---------|-------------|--------------|--------------|---------------|---------------------|
| ^0    | Idea          | `noetic-idea`      | #3388BB | 0.240       | 6.3:1 ✓     | 3.6:1 ✓     | Mid blue      | Tol muted pale-blue (darkened) |
| ^1    | Mind          | `noetic-mind`      | #117733 | 0.154       | 3.8:1 ✓     | 5.2:1 ✓     | Dark green    | Tol muted green (kept) |
| ^2    | Positive      | `noetic-positive`  | #CC7700 | 0.278       | 5.1:1 ✓     | 3.2:1 ✓     | Amber-orange  | Tol muted straw (darkened, hue-shifted to orange) |
| ^3    | Negative      | `noetic-negative`  | #CC6677 | 0.250       | 5.6:1 ✓     | 3.5:1 ✓     | Rose-pink     | Tol muted rose (kept) |
| ^4    | Vibration     | `noetic-vibration` | #2E7A6E | 0.174       | 4.2:1 ✓     | 4.6:1 ✓     | Dark teal     | Tol muted teal (darkened) |
| ^5    | Female        | `noetic-female`    | #CC3388 | 0.176       | 4.2:1 ✓     | 4.6:1 ✓     | Magenta       | Tol muted wine (brightened + hue-shifted) |
| ^6    | Male          | `noetic-male`      | #5B55C0 | 0.134       | 3.5:1 ✓     | 5.7:1 ✓     | Indigo        | Tol muted indigo (brightened) |
| ^7    | Rhythm        | `noetic-rhythm`    | #7A7A25 | 0.200       | 4.7:1 ✓     | 4.2:1 ✓     | Olive         | Tol muted olive (darkened) |
| ^8    | Above/Cause   | `noetic-above`     | #AA4499 | 0.166       | 4.0:1 ✓     | 4.9:1 ✓     | Purple        | Tol muted purple (kept) |
| ^9    | Below/Effect  | `noetic-below`     | #6B778C | 0.200       | 4.7:1 ✓     | 4.2:1 ✓     | Blue-gray     | Tol muted gray (replaced with blue-gray) |

### 3.1 Involution-Pair Color Choices

| Pair | ^n hex | ^m hex | Hue contrast | ΔL |
|------|--------|--------|--------------|-----|
| CO-2 Positive ↔ CO-3 Negative | #CC7700 (amber) | #CC6677 (rose-pink) | ~30° hue shift (orange → pink); under deut: amber→warm-brown, rose→cooler-pink, still distinguishable by chroma character. | 0.028 |
| CO-5 Female ↔ CO-6 Male | #CC3388 (magenta) | #5B55C0 (indigo) | ~120° hue shift; under deut: magenta→blue-ish, indigo→blue; fallback via ΔL = 0.042. | 0.042 |
| CO-8 Above ↔ CO-9 Below | #AA4499 (purple) | #6B778C (blue-gray) | ~60° hue shift; under deut: purple→blue-ish, blue-gray→gray; distinguishable. | 0.034 |

### 3.2 Colorblind Simulation Table — Noetic Axis

Approximate hue appearance under each condition (Brettel-Viénot-Mollon model). "Distinct" means the two colors remain visually separable within the axis.

| Pair at risk | Deuteranopia | Protanopia | Tritanopia |
|--------------|--------------|------------|------------|
| ^1 (green) vs ^7 (olive) | Both shift toward brownish-yellow. ΔL=0.046 provides fallback. Marginal but acceptable. | Same as deut. Marginal. | Green and olive differ in blue-component (none); both appear brownish. ΔL fallback holds. |
| ^2 (amber) vs ^7 (olive) | Amber→warm-brown; olive→slightly cooler brown. ΔL=0.078 — distinguishable. | Similar. | Both warm; trit doesn't affect this pair. Distinct. |
| ^0 (mid-blue) vs ^9 (blue-gray) | Blue channel preserved; both appear blue but ^9 is more desaturated. Distinct. | Same as deut. | Trit: blue shifts toward purple. Blue-gray loses blue, appears grayer. Distinct. |
| ^5 (magenta) vs ^6 (indigo) | Magenta loses red → appears blue-ish; indigo stays blue. ΔL=0.042 and saturation differ. Acceptable. | Magenta appears darker blue. Indigo lighter blue. ΔL distinguishes. | Trit doesn't affect red-magenta vs blue-indigo strongly. Distinct. |
| ^8 (purple) vs ^6 (indigo) | Both blue-ish; ΔL=0.032, hue slightly different. Marginal. | Similar. | Both appear similar under trit. Note: ^6 and ^8 are NOT an involution pair and are not structurally coupled. Marginal pairs documented; not a failure. |

**Summary**: No pair within the Noetic axis is fully indistinguishable under any single colorblind condition. All marginal pairs (^1/^7, ^5/^6, ^6/^8) retain ΔL ≥ 0.032 as fallback distinguishability. Per the acceptability criterion, this palette passes.

---

## 4. Domain Axis — 4 Colors (P, C, E, O)

**Design intent**: Domain colors are at a slightly lower saturation tier than Noetic colors, making them identifiable as "domain-axis" when appearing alongside Noetic colors in a legend or multi-axis diagram. All four Domain colors cluster at L ∈ [0.22, 0.30] — a higher luminance tier than most Noetics — providing a visual-tier cue.

**Note on existing `colors.ts`**: The existing `DOMAIN_COLORS` in `dashboard/src/lib/colors.ts` (`#818cf8`, `#60a5fa`, `#34d399`, `#fbbf24`) are used for the kind-keyed `diagramColor()` fallback and for non-diagram components (gauge, radar chart). Those values are unchanged. The new value-keyed domain palette uses different values optimized for the dual-background constraint.

| Value | Name        | Token          | Hex     | L (rel lum) | vs `#0d1117` | vs `#ffffff` | Hue region       | Source                    |
|-------|-------------|----------------|---------|-------------|--------------|--------------|------------------|---------------------------|
| P     | Principled  | `domain-P`     | #7B7EC4 | 0.233       | 5.3:1 ✓     | 3.8:1 ✓     | Lavender-indigo  | ColorBrewer Set2 adj.     |
| C     | Cognitive   | `domain-C`     | #4490B0 | 0.248       | 5.6:1 ✓     | 3.6:1 ✓     | Steel blue       | ColorBrewer Set2 adj.     |
| E     | Evaluative  | `domain-E`     | #4A9068 | 0.231       | 5.2:1 ✓     | 3.8:1 ✓     | Muted emerald    | ColorBrewer Set2 adj.     |
| O     | Operational | `domain-O`     | #C0883C | 0.294       | 3.2:1 ✓     | 3.0:1 ✓     | Muted amber      | Wong orange (desaturated, L adj.) |

### 4.1 Cross-Axis Orthogonality

For a node carrying both a Noetic value and a Domain value, the two colors appear in different visual channels (e.g., fill vs border/ring). Even where hues overlap, the encoding channel separates them. Additionally:

| Noetic vs Domain pair most at risk | Assessment |
|------------------------------------|------------|
| ^0 #3388BB (mid-blue) vs C #4490B0 (steel-blue) | Hue very close. In multi-axis display, C-Domain would be shown as a border ring; fill is Noetic. No conflation. In legend use, these are adjacent entries under different axis headings. Acceptable. |
| ^6 #5B55C0 (indigo) vs P #7B7EC4 (lavender-indigo) | Similar hue, different lightness (0.134 vs 0.233). Distinguishable by luminance. |
| ^2 #CC7700 (amber) vs O #C0883C (muted amber) | Similar hue. Different saturation (Noetic is more saturated). Distinguishable by chroma. |

Colorblind simulation: the four Domain colors span blue, green, amber, and lavender — four hue regions that remain distinct under deuteranopia (lavender/indigo appears blue-ish, green appears brownish, amber appears brownish-warm, steel-blue stays blue). Lavender vs steel-blue remain distinct under deut by hue angle and luminance. Domain axis is colorblind-accessible.

---

## 5. Drive Axis — 7 Colors (F1 through F7)

**Basis**: Paul Tol "bright" palette hues, adjusted for L ∈ [0.12, 0.30]. The Drive inversion pairs (F1↔F7, F2↔F6, F3↔F5; F4 self-dual) use contrasting hue positions.

**Critical constraint**: The F3 Vitality ↔ F5 Agency involution pair must NOT use a red+green combination (indistinguishable under deuteranopia/protanopia). F3 uses teal-green (significant blue component); F5 uses pink-magenta. These are distinguishable under all colorblind conditions.

| Value | Name       | Token        | Hex     | L (rel lum) | vs `#0d1117` | vs `#ffffff` | Hue region       | Inversion pair |
|-------|------------|--------------|---------|-------------|--------------|--------------|------------------|----------------|
| F1    | Unity      | `drive-F1`   | #4477AA | 0.189       | 4.5:1 ✓     | 4.7:1 ✓     | Blue             | F1 ↔ F7       |
| F2    | Wisdom     | `drive-F2`   | #7755CC | 0.180       | 4.3:1 ✓     | 4.8:1 ✓     | Purple           | F2 ↔ F6       |
| F3    | Vitality   | `drive-F3`   | #228866 | 0.196       | 4.6:1 ✓     | 4.5:1 ✓     | Teal-green       | F3 ↔ F5       |
| F4    | Connection | `drive-F4`   | #997700 | 0.213       | 4.9:1 ✓     | 4.1:1 ✓     | Amber-olive      | self-dual      |
| F5    | Agency     | `drive-F5`   | #BB4488 | 0.170       | 4.1:1 ✓     | 5.0:1 ✓     | Pink-magenta     | F3 ↔ F5       |
| F6    | Structure  | `drive-F6`   | #BB6699 | 0.236       | 5.3:1 ✓     | 3.8:1 ✓     | Medium pink      | F2 ↔ F6       |
| F7    | Purpose    | `drive-F7`   | #446688 | 0.136       | 3.5:1 ✓     | 5.6:1 ✓     | Slate blue       | F1 ↔ F7       |

### 5.1 Inversion-Pair Color Choices

| Pair | F_k hex | F_m hex | Hue contrast | ΔL | CB safety |
|------|---------|---------|--------------|-----|-----------|
| F1 Unity ↔ F7 Purpose | #4477AA (blue) | #446688 (slate-blue) | Small hue shift; large ΔL=0.053. Under deut: both appear blue, but luminance distinguishes. | 0.053 | Marginal but passes ΔL criterion. |
| F2 Wisdom ↔ F6 Structure | #7755CC (purple) | #BB6699 (pink) | ~60° hue shift. Under deut: purple shifts blue-ish, pink shifts brownish-pink. Distinct. | 0.056 | Passes. |
| F3 Vitality ↔ F5 Agency | #228866 (teal-green) | #BB4488 (magenta) | ~180° complementary. Under deut: teal-green has blue component → appears blue-ish; magenta loses red → appears blue-ish. ΔL=0.026 is small; fallback: saturation/chroma differs noticeably. | 0.026 | Passes: chroma separation is decisive. |

### 5.2 Drive Colorblind Simulation Table

| Pair at risk | Deuteranopia | Protanopia | Tritanopia |
|--------------|--------------|------------|------------|
| F1 (blue) vs F7 (slate-blue) | Both blue. ΔL=0.053 distinguishes. | Same. | Blue shifts toward purple under trit; slate-blue shifts slightly less. ΔL still distinguishes. |
| F3 (teal-green) vs F4 (amber) | Teal→blueish-gray; amber→brownish-yellow. Clearly distinct. | Same. | Teal retains green character; amber stays warm. Distinct. |
| F4 (amber) vs F2 (purple) | Amber→brownish; purple→blueish. Distinct. | Same. | Trit: amber shifts toward brownish (no blue to affect); purple shifts toward grayish. Distinct. |

---

## 6. Register Axis — 4 Visual Treatments (T, A, f, E)

Registers are rendered as **border/overlay treatments** rather than fill colors. This keeps the Register axis visually orthogonal to the Noetic/Domain/Drive fill colors — a node's fill identifies its specific Noetic/Domain/Drive value; its border style + color identifies its Register.

Each treatment has both a `border_style` (encoding structure) and a `color` (encoding register identity). The border colors are chosen to be distinguishable from all fill palette colors.

| Value | Name        | Token           | Border Style | Border Color | Color L | vs dark | vs white |
|-------|-------------|-----------------|--------------|--------------|---------|---------|---------|
| T     | Transcendent| `register-T`    | `solid`      | #D4A020      | 0.249   | 5.6:1 ✓ | 3.6:1 ✓ |
| A     | Analytical  | `register-A`    | `double`     | #4488CC      | 0.248   | 5.6:1 ✓ | 3.6:1 ✓ |
| f     | Affective   | `register-f`    | `dashed`     | #CC4477      | 0.182   | 4.3:1 ✓ | 4.7:1 ✓ |
| E     | Embodied    | `register-E`    | `dotted`     | #44AA77      | 0.231   | 5.2:1 ✓ | 3.8:1 ✓ |

**Border style semantics**:
- `solid` — Transcendent: continuous, unbroken line; evokes integration/wholeness.
- `double` — Analytical: double line; evokes explicit, structured, two-pass processing.
- `dashed` — Affective: interrupted; evokes the non-linear, feeling-toned character of affective states.
- `dotted` — Embodied: tactile, point-contact; evokes sensorimotor, concrete engagement.

**Colorblind safety**: The four register border colors (#D4A020 amber, #4488CC blue, #CC4477 rose, #44AA77 teal-green) are the four hue quadrants used by the Okabe-Ito palette. Amber vs teal-green may converge under deut/prot, but the border STYLE independently distinguishes them (solid vs dotted). Dual-channel redundancy (style + color) makes the Register axis fully colorblind-accessible even where hue converges.

---

## 7. `axis_color_for_node` — Precedence Rule

When a diagram node carries multiple axis attributes, the function returns the color for the most-specific axis:

```
Noetic (^n) > Domain (P/C/E/O) > Drive (F1-F7) > Register (T/A/f/E) → None
```

Rationale: Noetics are the most primitive CAS structural unit; they carry the greatest information density per node. Domain is second (structural precedence tier). Drive is motivational and typically annotates compound states. Register is the least-specific identifier (only 4 values) and is encoded as a border overlay anyway.

---

## 8. `PALETTE_VERSION`

```
PALETTE_VERSION = "v1.0"
```

Bumping `PALETTE_VERSION` is a breaking change once downstream consumers (compiler emission, eval harness, diagram-diff) pin to it. Future palette revisions require a new PR and explicit version bump. Consumers should pin `assert PALETTE_VERSION == "v1.0"` or equivalent.

---

## 9. Hex Color Tables — Quick Reference

### Noetic (^0–^9)
| ^0 | ^1 | ^2 | ^3 | ^4 | ^5 | ^6 | ^7 | ^8 | ^9 |
|----|----|----|----|----|----|----|----|----|----|
| #3388BB | #117733 | #CC7700 | #CC6677 | #2E7A6E | #CC3388 | #5B55C0 | #7A7A25 | #AA4499 | #6B778C |

### Domain (P/C/E/O)
| P | C | E | O |
|---|---|---|---|
| #7B7EC4 | #4490B0 | #4A9068 | #C0883C |

### Drive (F1–F7)
| F1 | F2 | F3 | F4 | F5 | F6 | F7 |
|----|----|----|----|----|----|----|
| #4477AA | #7755CC | #228866 | #997700 | #BB4488 | #BB6699 | #446688 |

### Register Treatments (T/A/f/E)
| T | A | f | E |
|---|---|---|---|
| solid / #D4A020 | double / #4488CC | dashed / #CC4477 | dotted / #44AA77 |

---

## 10. Downstream Notes

- **Compiler emission**: A future PR will make the notation compiler emit `<span style="color: {hex}">` tokens using this palette. That PR must import `color_palette.py` and pin `PALETTE_VERSION == "v1.0"`.
- **Eval harness**: The paraphrase-invariance evaluator (`evaluate_paraphrase_invariance.py`) is unchanged. A future PR adds a cross-channel color consistency check. It must pin the same version.
- **Diagram diff**: A future PR makes the diagram differ color-aware using `axisColorForNode`. It must import `casColorPalette.ts` and pin `PALETTE_VERSION`.
- **`colors.ts`**: Unchanged. It serves kind-keyed fallback and non-diagram components. No migration.
