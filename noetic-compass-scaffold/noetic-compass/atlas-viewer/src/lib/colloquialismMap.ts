/**
 * Atlas Viewer — CAS-to-English colloquialism map.
 *
 * Authoritative source: CLAUDE.md "Canonical colloquialism map" under
 * "Colloquialism Test" / Clarification 6 of CAS_FOUNDATIONAL_CLARIFICATIONS.md.
 * Phrases are verbatim from the Tootra Math Handbook. Do not paraphrase,
 * substitute, or extend. New phrases require an authoritative-source update.
 */

export type NoeticOperator =
  | "^0"
  | "^1"
  | "^2"
  | "^3"
  | "^4"
  | "^5"
  | "^6"
  | "^7"
  | "^8"
  | "^9";

export type Domain = "P" | "C" | "E" | "O";

export type Drive = "F1" | "F2" | "F3" | "F4" | "F5" | "F6" | "F7";

export const NOETIC_OPERATORS: readonly NoeticOperator[] = [
  "^0",
  "^1",
  "^2",
  "^3",
  "^4",
  "^5",
  "^6",
  "^7",
  "^8",
  "^9",
] as const;

export const DOMAINS: readonly Domain[] = ["P", "C", "E", "O"] as const;

export const DRIVES: readonly Drive[] = [
  "F1",
  "F2",
  "F3",
  "F4",
  "F5",
  "F6",
  "F7",
] as const;

export const NOETIC_NAMES: Record<NoeticOperator, string> = {
  "^0": "Idea",
  "^1": "Mind",
  "^2": "Positive",
  "^3": "Negative",
  "^4": "Vibration",
  "^5": "Female",
  "^6": "Male",
  "^7": "Rhythm",
  "^8": "Above/Cause",
  "^9": "Below/Effect",
};

export const DOMAIN_NAMES: Record<Domain, string> = {
  P: "Principled",
  C: "Cognitive",
  E: "Evaluative",
  O: "Operational",
};

export const DRIVE_NAMES: Record<Drive, string> = {
  F1: "Unity",
  F2: "Wisdom",
  F3: "Vitality",
  F4: "Connection",
  F5: "Agency",
  F6: "Structure",
  F7: "Purpose",
};

/**
 * Verbatim canonical colloquialisms — one entry per Noetic operator.
 *
 * Source: CLAUDE.md "Canonical colloquialism map" (Clarification 6).
 * Phrases must remain verbatim. Drift-watch annotations live on ^3 and ^8.
 */
export const COLLOQUIALISMS_BY_NOETIC: Record<NoeticOperator, string[]> = {
  "^0": ["It's all in your head."],
  "^1": [
    "Paying attention.",
    "Making up your mind.",
    "Using your head.",
  ],
  "^2": [
    "Drawn to it like a moth to a flame.",
    "Speaks to me.",
    "Can't resist.",
  ],
  /**
   * Anti-drift: ^3 Negative is VISCERAL, not analytical. The colloquialisms
   * "Can't stomach it." / "Rubs me the wrong way." / "Wouldn't touch it with
   * a ten-foot pole." describe aversion/repulsion, not analytical critique.
   * If a phrase reaches for audit/scrutinize/find-flaws vocabulary, the
   * correct operator is ^6 Male (compositional decomposition-and-test),
   * not ^3. (CLAUDE.md anti-drift annotation.)
   */
  "^3": [
    "Can't stomach it.",
    "Rubs me the wrong way.",
    "Wouldn't touch it with a ten-foot pole.",
  ],
  "^4": [
    "Hit me hard.",
    "Struck a chord.",
    "Resonated.",
    "Made an impression.",
  ],
  "^5": [
    "We are the sum of our experiences.",
    "It's who I am.",
    "Part of what makes me me.",
  ],
  "^6": [
    "Unpacking an idea.",
    "Breaking it down.",
    "Looking at what's underneath.",
    "Pulling apart the argument.",
  ],
  "^7": [
    "Practice makes perfect.",
    "You are what you repeatedly do.",
    "Getting into a groove.",
    "Muscle memory.",
  ],
  /**
   * Anti-drift: ^8 Above/Cause is associative TRIGGERING, not deductive
   * reasoning. The colloquialisms "That reminds me..." / "One thing leads
   * to another." / "Triggered a memory." / "Made me think of..." describe
   * associative surfacing of Ideas, not deductive inference. Deductive
   * causal analysis is a compound of ^6 Male (decomposition) and ^9
   * Below/Effect (landing), not ^8. (CLAUDE.md anti-drift annotation.)
   */
  "^8": [
    "That reminds me...",
    "One thing leads to another.",
    "Triggered a memory.",
    "Made me think of...",
  ],
  "^9": [
    "It just popped into my head.",
    "Out of nowhere I thought of...",
    "The thought came to me.",
    "It just clicked.",
  ],
};

const NOETIC_PATTERN = /\^([0-9])/;

function extractNoetic(casState: string): NoeticOperator | null {
  const match = casState.match(NOETIC_PATTERN);
  if (!match) return null;
  const candidate = `^${match[1]}` as NoeticOperator;
  return NOETIC_OPERATORS.includes(candidate) ? candidate : null;
}

/**
 * Pick the first colloquialism for the Noetic operator embedded in a CAS
 * state string. Accepts forms like "^1^C_{F1|A}", "^3^P", or "^8".
 * Returns "" when no recognizable Noetic operator is present.
 */
export function toEnglish(casState: string): string {
  const op = extractNoetic(casState);
  if (!op) return "";
  const phrases = COLLOQUIALISMS_BY_NOETIC[op];
  return phrases.length > 0 ? phrases[0] : "";
}

/**
 * Compose a single tooltip-ready phrase from a Noetic operator and optional
 * Domain / Drive coordinates. Domain and Drive currently inflect the phrase
 * by appending the first colloquialism of paired operators where canonical
 * pairings exist; otherwise they are surfaced as a parenthetical name tag.
 *
 * Wave-1 default behavior: return the first Noetic colloquialism; suffix a
 * compact name tag for Domain and/or Drive when supplied.
 */
export function tooltipForCoord(
  noetic: NoeticOperator,
  domain?: Domain,
  drive?: Drive,
): string {
  const base = COLLOQUIALISMS_BY_NOETIC[noetic][0] ?? "";
  const tags: string[] = [];
  if (domain) tags.push(DOMAIN_NAMES[domain]);
  if (drive) tags.push(DRIVE_NAMES[drive]);
  if (tags.length === 0) return base;
  return `${base} (${tags.join(" / ")})`;
}
