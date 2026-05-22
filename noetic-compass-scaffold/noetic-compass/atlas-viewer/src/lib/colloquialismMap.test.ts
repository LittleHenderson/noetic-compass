import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import {
  COLLOQUIALISMS_BY_NOETIC,
  DOMAINS,
  DRIVES,
  NOETIC_OPERATORS,
  toEnglish,
  tooltipForCoord,
  type Drive,
  type NoeticOperator,
} from "./colloquialismMap";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SOURCE_PATH = join(__dirname, "colloquialismMap.ts");

describe("COLLOQUIALISMS_BY_NOETIC", () => {
  it("covers every Noetic operator", () => {
    expect(Object.keys(COLLOQUIALISMS_BY_NOETIC).sort()).toEqual(
      [...NOETIC_OPERATORS].sort(),
    );
  });

  it("returns at least 2 colloquialisms for every operator except ^0", () => {
    for (const op of NOETIC_OPERATORS) {
      const phrases = COLLOQUIALISMS_BY_NOETIC[op];
      if (op === "^0") {
        // ^0 Idea has a single authoritative colloquialism in CLAUDE.md.
        expect(phrases.length).toBeGreaterThanOrEqual(1);
      } else {
        expect(phrases.length).toBeGreaterThanOrEqual(2);
      }
    }
  });

  it("preserves verbatim ^3 visceral phrases (anti-drift)", () => {
    expect(COLLOQUIALISMS_BY_NOETIC["^3"]).toEqual([
      "Can't stomach it.",
      "Rubs me the wrong way.",
      "Wouldn't touch it with a ten-foot pole.",
    ]);
  });

  it("preserves verbatim ^8 triggering phrases (anti-drift)", () => {
    expect(COLLOQUIALISMS_BY_NOETIC["^8"]).toEqual([
      "That reminds me...",
      "One thing leads to another.",
      "Triggered a memory.",
      "Made me think of...",
    ]);
  });
});

describe("toEnglish", () => {
  it("returns a non-empty colloquialism for every bare Noetic state", () => {
    for (const op of NOETIC_OPERATORS) {
      const phrase = toEnglish(op);
      expect(phrase.length).toBeGreaterThan(0);
      expect(COLLOQUIALISMS_BY_NOETIC[op][0]).toBe(phrase);
    }
  });

  it("parses compound states like ^1^C_{F1|A}", () => {
    expect(toEnglish("^1^C_{F1|A}")).toBe("Paying attention.");
  });

  it("parses domain-only states like ^3^P", () => {
    expect(toEnglish("^3^P")).toBe("Can't stomach it.");
  });

  it("returns empty string when no Noetic operator is present", () => {
    expect(toEnglish("F1|A")).toBe("");
    expect(toEnglish("")).toBe("");
  });
});

describe("tooltipForCoord", () => {
  it("composes a phrase for Noetic alone", () => {
    expect(tooltipForCoord("^1")).toBe("Paying attention.");
  });

  it("appends a Domain name tag when supplied", () => {
    expect(tooltipForCoord("^1", "C")).toBe("Paying attention. (Cognitive)");
  });

  it("appends Domain and Drive name tags together", () => {
    expect(tooltipForCoord("^1", "C", "F1")).toBe(
      "Paying attention. (Cognitive / Unity)",
    );
  });

  it("composes coherently for every Noetic operator", () => {
    for (const op of NOETIC_OPERATORS) {
      const phrase = tooltipForCoord(op);
      expect(phrase.length).toBeGreaterThan(0);
    }
  });

  it("accepts every Domain and Drive value without error", () => {
    const op: NoeticOperator = "^1";
    for (const d of DOMAINS) {
      for (const f of DRIVES as readonly Drive[]) {
        const phrase = tooltipForCoord(op, d, f);
        expect(phrase.length).toBeGreaterThan(0);
      }
    }
  });
});

describe("anti-drift JSDoc presence", () => {
  const source = readFileSync(SOURCE_PATH, "utf8");

  it("contains a ^3 anti-drift JSDoc block flagging VISCERAL vs analytical", () => {
    expect(source).toMatch(
      /\^3 Negative is VISCERAL,? not analytical/i,
    );
    expect(source).toContain("^6 Male");
  });

  it("contains an ^8 anti-drift JSDoc block flagging TRIGGERING vs deductive reasoning", () => {
    expect(source).toMatch(
      /\^8 Above\/Cause is associative TRIGGERING,?[\s*]+not deductive[\s*]+reasoning/i,
    );
    expect(source).toMatch(/\^6[\s\S]+\^9/);
  });
});
