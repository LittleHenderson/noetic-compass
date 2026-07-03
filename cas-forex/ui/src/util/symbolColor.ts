/* Deterministic, stable color per trading symbol so every currency pair / index
   is immediately recognizable across the app. Same symbol => same color, every
   render, every page. Colors are spread around the hue wheel with strong
   saturation and a fixed lightness that reads on the dark UI. */

function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function symbolHue(symbol: string): number {
  return hashString((symbol || "").toUpperCase()) % 360;
}

/** Background/border color for a symbol chip. */
export function symbolColor(symbol: string): string {
  const hue = symbolHue(symbol);
  return `hsl(${hue}, 70%, 55%)`;
}

/** A translucent fill + solid text pairing for a chip, keyed off the symbol. */
export function symbolChipStyle(symbol: string): { background: string; borderColor: string; color: string } {
  const hue = symbolHue(symbol);
  return {
    background: `hsla(${hue}, 70%, 55%, 0.18)`,
    borderColor: `hsla(${hue}, 70%, 60%, 0.65)`,
    color: `hsl(${hue}, 85%, 78%)`,
  };
}
