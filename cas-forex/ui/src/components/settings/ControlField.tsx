/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 1). */



export function ControlField({ label, value, mono, danger, description }: { label: string; value: string; mono?: boolean; danger?: boolean; description?: string }) {
  return (
    <div className="control-field">
      <div className="control-field-header">
        <span className="field-label">{label}</span>
        <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : undefined, fontWeight: 600 }}>{value}</span>
      </div>
      {description && <div className="control-field-desc">{description}</div>}
    </div>
  );
}

