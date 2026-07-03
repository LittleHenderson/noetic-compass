/* A color-coded symbol chip. Drop in anywhere a currency pair / index is shown
   to make it instantly recognizable by its consistent color. */

import { symbolChipStyle } from "../util/symbolColor";

export function SymbolTag({ symbol, size = "md" }: { symbol: string; size?: "sm" | "md" }) {
  if (!symbol) return null;
  const style = symbolChipStyle(symbol);
  return (
    <span
      className={`symbol-tag symbol-tag--${size}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.3em",
        padding: size === "sm" ? "0.05em 0.4em" : "0.12em 0.5em",
        borderRadius: "999px",
        border: `1px solid ${style.borderColor}`,
        background: style.background,
        color: style.color,
        fontSize: size === "sm" ? "0.62rem" : "0.72rem",
        fontWeight: 600,
        letterSpacing: "0.02em",
        whiteSpace: "nowrap",
      }}
    >
      <span
        aria-hidden
        style={{
          width: "0.5em",
          height: "0.5em",
          borderRadius: "50%",
          background: style.borderColor,
        }}
      />
      {symbol}
    </span>
  );
}
