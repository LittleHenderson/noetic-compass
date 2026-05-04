/**
 * Tests for casColorPalette.ts — CAS value-keyed color palette (TypeScript).
 * Mirrors tests/test_color_palette.py exactly in structure and intent.
 */

import { describe, it, expect } from "vitest";
import {
  PALETTE_VERSION,
  noeticColor,
  domainColor,
  driveColor,
  registerTreatment,
  axisColorForNode,
} from "../casColorPalette";

const HEX_RE = /^#[0-9A-Fa-f]{6}$/;
const isHex = (s: string) => HEX_RE.test(s);

// ---------------------------------------------------------------------------
// PALETTE_VERSION
// ---------------------------------------------------------------------------

describe("PALETTE_VERSION", () => {
  it("is set to v1.0", () => {
    expect(PALETTE_VERSION).toBe("v1.0");
  });

  it("is a string", () => {
    expect(typeof PALETTE_VERSION).toBe("string");
  });
});

// ---------------------------------------------------------------------------
// noeticColor
// ---------------------------------------------------------------------------

describe("noeticColor", () => {
  it("returns a valid hex for all indices 0-9", () => {
    for (let n = 0; n <= 9; n++) {
      expect(isHex(noeticColor(n))).toBe(true);
    }
  });

  it("throws for -1", () => {
    expect(() => noeticColor(-1)).toThrow();
  });

  it("throws for 10", () => {
    expect(() => noeticColor(10)).toThrow();
  });

  it("throws for non-integer (float)", () => {
    expect(() => noeticColor(3.5)).toThrow();
  });

  it("all 10 Noetic colors are distinct", () => {
    const colors = Array.from({ length: 10 }, (_, n) => noeticColor(n));
    expect(new Set(colors).size).toBe(10);
  });

  it("is deterministic", () => {
    for (let n = 0; n <= 9; n++) {
      expect(noeticColor(n)).toBe(noeticColor(n));
    }
  });

  it("^0 Idea is #3388BB", () => {
    expect(noeticColor(0)).toBe("#3388BB");
  });

  it("^3 Negative is #CC6677", () => {
    expect(noeticColor(3)).toBe("#CC6677");
  });

  it("hex values match Python palette exactly", () => {
    // Spot-check all 10 to guard against accidental drift
    const expected = [
      "#3388BB", "#117733", "#CC7700", "#CC6677", "#2E7A6E",
      "#CC3388", "#5B55C0", "#7A7A25", "#AA4499", "#6B778C",
    ];
    for (let n = 0; n < 10; n++) {
      expect(noeticColor(n)).toBe(expected[n]);
    }
  });
});

// ---------------------------------------------------------------------------
// domainColor
// ---------------------------------------------------------------------------

describe("domainColor", () => {
  const domains = ["P", "C", "E", "O"] as const;

  it("returns a valid hex for all valid domains", () => {
    for (const d of domains) {
      expect(isHex(domainColor(d))).toBe(true);
    }
  });

  it("throws for invalid domain 'X'", () => {
    expect(() => domainColor("X" as any)).toThrow();
  });

  it("throws for lowercase 'p'", () => {
    expect(() => domainColor("p" as any)).toThrow();
  });

  it("all 4 Domain colors are distinct", () => {
    const colors = domains.map(domainColor);
    expect(new Set(colors).size).toBe(4);
  });

  it("is deterministic", () => {
    for (const d of domains) {
      expect(domainColor(d)).toBe(domainColor(d));
    }
  });

  it("P (Principled) is #7B7EC4", () => {
    expect(domainColor("P")).toBe("#7B7EC4");
  });

  it("O (Operational) is #C0883C", () => {
    expect(domainColor("O")).toBe("#C0883C");
  });

  it("hex values match Python palette exactly", () => {
    expect(domainColor("P")).toBe("#7B7EC4");
    expect(domainColor("C")).toBe("#4490B0");
    expect(domainColor("E")).toBe("#4A9068");
    expect(domainColor("O")).toBe("#C0883C");
  });
});

// ---------------------------------------------------------------------------
// driveColor
// ---------------------------------------------------------------------------

describe("driveColor", () => {
  it("returns a valid hex for all drives F1-F7", () => {
    for (let k = 1; k <= 7; k++) {
      expect(isHex(driveColor(k))).toBe(true);
    }
  });

  it("throws for 0", () => {
    expect(() => driveColor(0)).toThrow();
  });

  it("throws for 8", () => {
    expect(() => driveColor(8)).toThrow();
  });

  it("throws for negative", () => {
    expect(() => driveColor(-1)).toThrow();
  });

  it("throws for float", () => {
    expect(() => driveColor(2.5)).toThrow();
  });

  it("all 7 Drive colors are distinct", () => {
    const colors = Array.from({ length: 7 }, (_, i) => driveColor(i + 1));
    expect(new Set(colors).size).toBe(7);
  });

  it("is deterministic", () => {
    for (let k = 1; k <= 7; k++) {
      expect(driveColor(k)).toBe(driveColor(k));
    }
  });

  it("F1 Unity is #4477AA", () => {
    expect(driveColor(1)).toBe("#4477AA");
  });

  it("F7 Purpose is #446688", () => {
    expect(driveColor(7)).toBe("#446688");
  });

  it("hex values match Python palette exactly", () => {
    const expected = [
      "#4477AA", "#7755CC", "#228866", "#997700", "#BB4488", "#BB6699", "#446688",
    ];
    for (let k = 1; k <= 7; k++) {
      expect(driveColor(k)).toBe(expected[k - 1]);
    }
  });
});

// ---------------------------------------------------------------------------
// registerTreatment
// ---------------------------------------------------------------------------

const VALID_REGISTERS = ["T", "A", "f", "E"] as const;
const VALID_BORDER_STYLES = new Set(["solid", "dashed", "dotted", "double"]);

describe("registerTreatment", () => {
  it("returns an object for all valid registers", () => {
    for (const r of VALID_REGISTERS) {
      expect(typeof registerTreatment(r)).toBe("object");
    }
  });

  it("returned object has borderStyle and color keys", () => {
    for (const r of VALID_REGISTERS) {
      const t = registerTreatment(r);
      expect(t).toHaveProperty("borderStyle");
      expect(t).toHaveProperty("color");
    }
  });

  it("borderStyle is one of solid/dashed/dotted/double", () => {
    for (const r of VALID_REGISTERS) {
      expect(VALID_BORDER_STYLES.has(registerTreatment(r).borderStyle)).toBe(true);
    }
  });

  it("color is a valid hex", () => {
    for (const r of VALID_REGISTERS) {
      expect(isHex(registerTreatment(r).color)).toBe(true);
    }
  });

  it("throws for invalid register 'X'", () => {
    expect(() => registerTreatment("X" as any)).toThrow();
  });

  it("throws for lowercase 't'", () => {
    expect(() => registerTreatment("t" as any)).toThrow();
  });

  it("returns a copy — mutations do not affect internal palette", () => {
    const t1 = registerTreatment("T");
    t1.color = "#000000";
    const t2 = registerTreatment("T");
    expect(t2.color).not.toBe("#000000");
  });

  it("all 4 border styles are distinct", () => {
    const styles = VALID_REGISTERS.map((r) => registerTreatment(r).borderStyle);
    expect(new Set(styles).size).toBe(4);
  });
});

// ---------------------------------------------------------------------------
// axisColorForNode
// ---------------------------------------------------------------------------

describe("axisColorForNode", () => {
  it("Noetic takes precedence over Domain", () => {
    expect(axisColorForNode({ noetic: 3, domain: "P" })).toBe(noeticColor(3));
  });

  it("Noetic takes precedence over Drive", () => {
    expect(axisColorForNode({ noetic: 0, drive: 5 })).toBe(noeticColor(0));
  });

  it("Noetic takes precedence over all", () => {
    expect(axisColorForNode({ noetic: 7, domain: "C", drive: 2 })).toBe(noeticColor(7));
  });

  it("Domain takes precedence over Drive", () => {
    expect(axisColorForNode({ domain: "E", drive: 4 })).toBe(domainColor("E"));
  });

  it("Drive is used when only drive is present", () => {
    expect(axisColorForNode({ drive: 6 })).toBe(driveColor(6));
  });

  it("returns null for empty node", () => {
    expect(axisColorForNode({})).toBeNull();
  });

  it("returns null when all values are null", () => {
    expect(axisColorForNode({ noetic: null, domain: null, drive: null })).toBeNull();
  });

  it("returns a valid hex string for noetic nodes", () => {
    for (let n = 0; n <= 9; n++) {
      expect(isHex(axisColorForNode({ noetic: n }) as string)).toBe(true);
    }
  });

  it("throws for out-of-range noetic in node", () => {
    expect(() => axisColorForNode({ noetic: 10 })).toThrow();
  });
});

// ---------------------------------------------------------------------------
// Cross-axis distinctness
// ---------------------------------------------------------------------------

describe("Cross-axis distinctness", () => {
  it("Noetic colors are distinct from Domain colors", () => {
    const noeticSet = new Set(Array.from({ length: 10 }, (_, n) => noeticColor(n)));
    const domainSet = new Set(["P", "C", "E", "O"].map(domainColor as any));
    for (const c of domainSet) {
      expect(noeticSet.has(c as string)).toBe(false);
    }
  });

  it("Noetic colors are distinct from Drive colors", () => {
    const noeticSet = new Set(Array.from({ length: 10 }, (_, n) => noeticColor(n)));
    const driveSet = new Set(Array.from({ length: 7 }, (_, i) => driveColor(i + 1)));
    for (const c of driveSet) {
      expect(noeticSet.has(c)).toBe(false);
    }
  });

  it("Domain colors are distinct from Drive colors", () => {
    const domainSet = new Set(["P", "C", "E", "O"].map(domainColor as any));
    const driveSet = new Set(Array.from({ length: 7 }, (_, i) => driveColor(i + 1)));
    for (const c of driveSet) {
      expect(domainSet.has(c)).toBe(false);
    }
  });
});
