/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 2). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { ControlField } from "../../components/settings/ControlField";
import { SecurityPosture, fetchSecurityPosture } from "../../data/api";
import { formatYesNo } from "./formatters";
import { useEffect, useState } from "react";

export function SecurityPosturePanel() {
  const [posture, setPosture] = useState<SecurityPosture | null>(null);

  useEffect(() => {
    void fetchSecurityPosture().then((s) => { if (s) setPosture(s); });
  }, []);

  const owner = posture?.owner_auth;
  const ignore = posture?.ignore_coverage ?? {};
  const secrets = posture?.server_secret_inventory ?? [];
  const attention = posture?.attention_items ?? [];
  const browserPolicy = posture?.browser_exposure?.frontend_secret_policy ?? "Loading security posture.";
  const managedStore = posture?.managed_secret_store;
  const roleModel = posture?.role_permission_model;
  const liveSecondFactor = roleModel?.live_action_second_factor;
  const routePolicy = roleModel?.route_permission_policy;
  const defaultMutationCount = routePolicy?.default_mutation_route_count ?? 0;
  const sensitiveRouteRules = (routePolicy?.route_rules ?? [])
    .filter((rule) => rule.money_or_live_sensitive)
    .slice(0, 6);
  const roles = roleModel?.roles ?? [];

  return (
    <GlassPanel title="Security Posture" subtitle="Owner auth, browser exposure, and local secret inventory">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={posture?.status ?? "SYNCING"}
          variant={posture?.status === "OK" ? "success" : posture?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={owner?.lan_mode_enabled ? "LAN ON" : "LAN OFF"}
          variant={owner?.lan_mode_enabled ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={owner?.owner_token_present ? "OWNER TOKEN SET" : "NO OWNER TOKEN"}
          variant={owner?.owner_token_present ? "success" : "warning"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField label="Owner Token" value={owner?.owner_token_present ? (owner.owner_token_hint || "SET") : "NOT SET"} mono description="Only masked token hints are shown outside the loopback-only pairing route." />
        <ControlField label="Cloud Mode" value={owner?.cloud_mode ? "TOKEN REQUIRED" : "LOCAL LOOPBACK TRUSTED"} description={owner?.cloud_mode ? "Cloud deployments require an owner token for all API calls." : "The local PC can use the API without a token; off-box devices need LAN mode plus token."} />
        <ControlField label=".env Git Ignore" value={ignore.env_ignored_by_git ? "COVERED" : "MISSING"} danger={!ignore.env_ignored_by_git} />
        <ControlField label="runtime/ Git Ignore" value={ignore.runtime_ignored_by_git ? "COVERED" : "MISSING"} danger={!ignore.runtime_ignored_by_git} />
        <ControlField label="runtime/ Docker Ignore" value={ignore.runtime_ignored_by_docker ? "COVERED" : "MISSING"} danger={!ignore.runtime_ignored_by_docker} />
        <ControlField label="Browser Secret Policy" value="OWNER TOKEN ONLY" description={browserPolicy} />
      </div>
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Managed Secret Store</h4>
        <div className="control-grid">
          <ControlField
            label="Backend"
            value={managedStore?.backend_status ?? "SYNCING"}
            mono
            danger={managedStore?.status === "ATTENTION"}
            description={managedStore?.detail ?? "Managed secret-store status is loading."}
          />
          <ControlField
            label="Active Provider"
            value={managedStore?.active_backend || "none"}
            mono
            description={`requested: ${managedStore?.requested_backend ?? "auto"}`}
          />
          <ControlField
            label="External Manager"
            value={managedStore?.external_secret_manager?.configured ? (managedStore.external_secret_manager.provider || "CONFIGURED") : "NOT CONFIGURED"}
            danger={managedStore?.cloud_mode && !managedStore?.external_secret_manager?.configured}
            description={managedStore?.cloud_mode ? "Cloud/public mode should use an external managed secret manager." : "Local desktop can use current-user OS protection."}
          />
          <ControlField
            label="Raw Secret Return"
            value={managedStore?.raw_secret_returned ? "YES" : "NO"}
            danger={managedStore?.raw_secret_returned === true}
            description={managedStore?.claim_boundary ?? "Managed-store posture is read-only."}
          />
        </div>
      </div>
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Server-Side Secrets</h4>
        <div className="control-grid">
          {secrets.slice(0, 8).map((secret) => (
            <ControlField
              key={secret.key}
              label={secret.label}
              value={secret.configured ? `SET ${secret.masked_hint || ""}` : "NOT SET"}
              mono={Boolean(secret.masked_hint)}
              danger={Boolean(secret.browser_exposed && secret.key !== "owner_token")}
              description={`${secret.storage ?? "server-side"}; browser exposed: ${secret.browser_exposed ? "yes" : "no"}${secret.runtime_override_set ? `; runtime override encrypted: ${secret.runtime_override_encrypted_at_rest ? "yes" : "no"}` : ""}${secret.runtime_secret_store_set ? `; runtime secret store encrypted: ${secret.runtime_secret_store_encrypted_at_rest ? "yes" : "no"}` : ""}${secret.plaintext_config_source_present ? "; plaintext config fallback present" : ""}.`}
            />
          ))}
        </div>
      </div>
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Role Permission Model</h4>
        <div className="control-grid" style={{ marginBottom: 10 }}>
          <ControlField
            label="Authorization Model"
            value={roleModel?.authorization_model ?? "SYNCING"}
            description={roleModel?.claim_boundary ?? "Role permission model is read-only."}
          />
          <ControlField
            label="MFA Status"
            value={roleModel?.mfa_status ?? "SYNCING"}
            danger={roleModel?.mfa_status === "NOT_IMPLEMENTED"}
            description={roleModel?.mfa_detail ?? "Loading MFA posture."}
          />
          <ControlField
            label="Live Action 2nd Factor"
            value={liveSecondFactor?.status ?? "SYNCING"}
            description={[
              ...(liveSecondFactor?.factors ?? []),
              ...(liveSecondFactor?.not_implemented ?? []).map((item) => `not implemented: ${item}`),
              ...(roleModel?.mfa_hardening_backlog ?? []),
            ].join(" ")}
            danger={!liveSecondFactor?.status}
          />
          <ControlField
            label="Permission Gaps"
            value={`${roleModel?.gaps?.length ?? 0}`}
            mono
            danger={(roleModel?.gaps?.length ?? 0) > 0}
          />
          <ControlField
            label="Route Permission Policy"
            value={routePolicy?.status ?? "SYNCING"}
            danger={routePolicy?.status === "ATTENTION"}
            description={routePolicy?.claim_boundary ?? "Route permission policy is loading."}
          />
          <ControlField
            label="Policy Enforcement"
            value={routePolicy?.enforcement ?? "SYNCING"}
            mono
            description={`default read: ${routePolicy?.default_read_permission ?? "n/a"}; default mutation: ${routePolicy?.default_mutation_permission ?? "n/a"}`}
          />
          <ControlField
            label="Route Rules"
            value={`${routePolicy?.route_rule_count ?? 0}`}
            mono
            description={`${routePolicy?.money_or_live_sensitive_rule_count ?? 0} live/money-sensitive; ${routePolicy?.loopback_only_rule_count ?? 0} loopback-only.`}
          />
          <ControlField
            label="Default Mutations"
            value={`${defaultMutationCount}`}
            mono
            danger={defaultMutationCount > 0}
            description={`coverage: ${routePolicy?.coverage_status ?? "SYNCING"}; inventory: ${routePolicy?.route_inventory_available ? `${routePolicy.route_inventory_count ?? 0} method routes` : "not available"}`}
          />
        </div>
        {(routePolicy?.default_mutation_routes?.length ?? 0) > 0 && (
          <div className="control-field-desc" style={{ marginBottom: 10, color: "var(--warning)" }}>
            Default mutation routes need explicit policy: {routePolicy?.default_mutation_routes?.slice(0, 4).map((route) => `${route.method} ${route.path}`).join("; ")}
          </div>
        )}
        <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginBottom: 10 }}>
          <table className="data-table ai-dial-table">
            <thead>
              <tr>
                <th>Route Category</th>
                <th>Path</th>
                <th>Permission</th>
                <th>Extra Gate</th>
              </tr>
            </thead>
            <tbody>
              {sensitiveRouteRules.map((rule) => (
                <tr key={`${rule.category ?? "route"}-${rule.path ?? rule.prefix}`}>
                  <td className="ai-dial-detail">{rule.category ?? "route"}</td>
                  <td className="ai-dial-detail mono">{rule.path ?? rule.prefix ?? "n/a"}</td>
                  <td className="ai-dial-detail mono">{rule.permission ?? "n/a"}</td>
                  <td className="ai-dial-detail">
                    typed confirm {formatYesNo(rule.typed_confirmation_required)}
                    {" | "}loopback only {formatYesNo(rule.loopback_only)}
                  </td>
                </tr>
              ))}
              {sensitiveRouteRules.length === 0 && (
                <tr>
                  <td colSpan={4}>Route permission policy is warming.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="positions-table-wrap ai-dial-table-wrap">
          <table className="data-table ai-dial-table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Auth</th>
                <th>Controls</th>
                <th>Live / Broker</th>
                <th>Secrets / Money</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr key={role.role_key ?? role.label}>
                  <td>
                    <div className="ai-dial-name">{role.label ?? role.role_key}</div>
                    <div className="ai-dial-key mono">{role.principal_type ?? "unknown"}</div>
                  </td>
                  <td className="ai-dial-detail">{role.authentication ?? "unknown"}</td>
                  <td className="ai-dial-detail">
                    dashboard {formatYesNo(role.can_view_dashboard)}
                    {" | "}owner {formatYesNo(role.can_change_owner_controls)}
                    {" | "}dials {formatYesNo(role.can_change_ai_dials)}
                  </td>
                  <td className="ai-dial-detail">
                    arm {formatYesNo(role.can_arm_live_authority)}
                    {" | "}order {formatYesNo(role.can_submit_live_order)}
                    {" | "}emergency {formatYesNo(role.can_run_broker_emergency)}
                  </td>
                  <td className="ai-dial-detail">
                    money {formatYesNo(role.can_move_money)}
                    {" | "}raw secrets {formatYesNo(role.can_read_raw_secrets)}
                    {" | "}typed confirm {formatYesNo(role.requires_typed_confirmation_for_money_or_live)}
                  </td>
                </tr>
              ))}
              {roles.length === 0 && (
                <tr>
                  <td colSpan={5}>Role permission model is warming.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {attention.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 12, color: "var(--warning)" }}>
          {attention.slice(0, 4).join(" ")}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {posture?.claim_boundary ?? "Security posture is read-only and never returns raw secrets."}
      </div>
    </GlassPanel>
  );
}

