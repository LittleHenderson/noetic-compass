/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 3). */

import { ControlField } from "../../components/settings/ControlField";
import { OwnerAuthorityModel } from "../../data/api";

export function AuthorityModelStrip({ model }: { model?: OwnerAuthorityModel }) {
  const controls = model?.authority_controls?.join(" + ") || "owner switches + Owner ACCEPT buttons";
  const checks = model?.action_time_requirements?.slice(0, 3).join("; ")
    || "broker/provider, edge, and risk checks";
  const delegated = (model?.ai_autonomous_execution_authority ?? "").includes("OWNER_DELEGATED");
  const perOrder = model?.per_order_confirmation_required ?? false;
  return (
    <div className="control-grid" style={{ marginBottom: 14 }}>
      <ControlField
        label="Authority"
        value={model?.authority || "OWNER"}
        description={`${controls} are the capability authority path.`}
      />
      <ControlField
        label="AI Autonomy"
        value={delegated ? "DELEGATED" : "GATED"}
        description={
          delegated
            ? `AI may act inside armed owner limits; per-order confirmation ${perOrder ? "required" : "not required"}.`
            : "Owner setup and action-time gates control whether AI automation can act."
        }
      />
      <ControlField
        label="Action-Time Checks"
        value={model?.technical_action_time_checks_still_required === false ? "OFF" : "REQUIRED"}
        danger={model?.technical_action_time_checks_still_required === false}
        description={checks}
      />
    </div>
  );
}

