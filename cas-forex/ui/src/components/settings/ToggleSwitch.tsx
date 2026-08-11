/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 3). */



export function ToggleSwitch({
  on,
  busy,
  onClick,
  label,
}: {
  on: boolean;
  busy: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className="go-live-switch"
      data-on={on}
      disabled={busy}
      aria-pressed={on}
      aria-label={`${label} — ${on ? "on" : "off"}`}
      onClick={onClick}
    >
      <span className="knob" />
    </button>
  );
}

