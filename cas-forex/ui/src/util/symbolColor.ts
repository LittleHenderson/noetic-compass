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

/** Normalize so broker format ("GBPAUD") and app format ("GBP/AUD") — and any
    casing/spacing — map to the SAME color. Only letters/digits are kept. */
function normalizeSymbol(symbol: string): string {
  return (symbol || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
}

// Hand-picked, maximally-distinct hues for the known tradable symbols so every
// one is unmistakable at a glance (a hash alone collides). Keyed by normalized
// form so "EUR/USD" and "EURUSD" match.
const SYMBOL_HUES: Record<string, number> = {
  EURUSD: 210, // blue
  GBPUSD: 145, // green
  USDJPY: 30, // orange
  AUDUSD: 55, // yellow
  USDCAD: 0, // red
  AUDCAD: 300, // magenta
  GBPAUD: 178, // teal
  NAS100: 265, // purple
  SPX500: 95, // lime
  US30: 330, // pink
  XAUUSD: 45, // gold
  EURGBP: 195, // cyan-blue
  EURJPY: 15, // red-orange
  GBPJPY: 130, // spring green
  AUDJPY: 70, // chartreuse
  NZDUSD: 285, // violet
  USDCHF: 350, // rose
  EURAUD: 165, // teal-green
  EURCAD: 250, // indigo
};

// Fallback palette for any symbol not in the map — still well separated.
const HUE_PALETTE = [8, 30, 48, 90, 140, 168, 190, 210, 240, 270, 300, 320, 345, 120];

export function symbolHue(symbol: string): number {
  const key = normalizeSymbol(symbol);
  if (key in SYMBOL_HUES) return SYMBOL_HUES[key];
  return HUE_PALETTE[hashString(key) % HUE_PALETTE.length];
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
