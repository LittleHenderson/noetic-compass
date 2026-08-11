import { StatusChip } from "./StatusChip";
import type { AuthorizationCapability, AuthorizationState } from "../data/api";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface MoneyMovementSetupStatusProps {
  auth: AuthorizationState | null;
  receiptVerified?: boolean;
  receiptStatusLabel?: string;
  receiptDetail?: string;
}

function findCapability(auth: AuthorizationState | null, capability: string): AuthorizationCapability | null {
  return auth?.capabilities.find((item) => item.capability === capability) ?? null;
}

function prettyStatus(value: string | null | undefined): string {
  return String(value || "UNKNOWN").replace(/_/g, " ");
}

function runtimeTone(status: string | null | undefined): ChipVariant {
  switch (status) {
    case "REAL_PROVIDER_READY":
      return "success";
    case "UNSUPPORTED_PROVIDER":
      return "danger";
    case "SIMULATED_ONLY":
    case "BROKER_PROVIDER_SANDBOX_READY":
      return "info";
    case "CREDENTIALS_MISSING":
    case "NOT_CONFIGURED":
    case "GENERAL_PAYMENT_RAIL_ONLY":
    case "BROKER_PROVIDER_CONFIG_MISSING":
      return "warning";
    default:
      return "muted";
  }
}

function SetupCard({
  label,
  status,
  tone,
  detail,
}: {
  label: string;
  status: string;
  tone: ChipVariant;
  detail: string;
}) {
  return (
    <div className="disabled-control" style={{ borderColor: tone === "danger" ? "var(--danger-dim)" : tone === "success" ? "var(--success)" : "var(--warning-dim)" }}>
      <div className="disabled-control-header">
        <span className="disabled-control-label">{label}</span>
        <StatusChip label={status} variant={tone} size="sm" />
      </div>
      <div className="disabled-control-reason">{detail}</div>
    </div>
  );
}

export function MoneyMovementSetupStatus({
  auth,
  receiptVerified = false,
  receiptStatusLabel,
  receiptDetail,
}: MoneyMovementSetupStatusProps) {
  const provider = auth?.provider;
  const payoutCapability = findCapability(auth, "payout_automation");
  const requestedProvider = provider?.payment_provider.trim() || "none";
  const requestedProviderLabel = requestedProvider === "none" ? "NONE" : requestedProvider.toUpperCase();
  const runtimeProviderLabel = String(provider?.runtime_provider_name || "simulated").toUpperCase();
  const runtimeStatus = prettyStatus(provider?.runtime_status);
  const providerEnvironment = String(provider?.payment_provider_environment || "sandbox").toLowerCase();
  const sandboxEnvironment = providerEnvironment !== "live" && providerEnvironment !== "production";
  const credentialsSet = Boolean(provider?.payment_api_key_set);
  const realMoneyProviderReady = Boolean(provider?.real_money_provider_ready);
  const brokerAccountBound = Boolean(provider?.broker_account_bound);
  const payoutDestinationSet = Boolean(provider?.payout_destination_id);
  const payoutAllowlisted = Boolean(provider?.payout_destination_allowlisted);
  const payoutAuthorized = Boolean(payoutCapability?.authorized);
  const receiptLabel = receiptVerified ? receiptStatusLabel ?? "VERIFIED" : "REQUIRED";
  const conformance = provider?.sandbox_conformance;
  const conformanceAccept = conformance?.status === "ACCEPT";

  return (
    <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
      <div className="not-licensed-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <SetupCard
          label="Provider request"
          status={requestedProviderLabel}
          tone={requestedProvider === "none" ? "warning" : "info"}
          detail={`Runtime status: ${runtimeStatus}. Runtime rail: ${runtimeProviderLabel}.`}
        />
        <SetupCard
          label="Provider environment"
          status={sandboxEnvironment ? "SANDBOX" : "LIVE"}
          tone={sandboxEnvironment ? "info" : "warning"}
          detail={
            sandboxEnvironment
              ? "The HTTP contract may run, but it cannot authorize or claim external money movement."
              : "Live mode was explicitly owner-selected; runtime gates and receipt evidence still apply."
          }
        />
        <SetupCard
          label="Sandbox contract proof"
          status={conformance?.status ?? "unavailable"}
          tone={conformanceAccept ? "success" : conformance?.present ? "warning" : "muted"}
          detail={
            conformance?.detail ||
            "No loopback provider-contract proof has been recorded. This never substitutes for live provider readiness."
          }
        />
        <SetupCard
          label="Provider credentials"
          status={credentialsSet ? "SET" : "REQUIRED"}
          tone={credentialsSet ? "success" : "warning"}
          detail={
            credentialsSet
              ? `Key storage: ${provider?.payment_api_key_storage || "runtime/config fallback"}.`
              : "A provider API key is required before any supported payout rail can run."
          }
        />
        <SetupCard
          label="Real-money rail"
          status={realMoneyProviderReady ? "READY" : "SCAFFOLDED"}
          tone={realMoneyProviderReady ? "success" : runtimeTone(provider?.runtime_status)}
          detail={
            provider?.runtime_detail ||
            "Money movement stays scaffolded until a supported real provider is ready."
          }
        />
        <SetupCard
          label="Broker custody binding"
          status={brokerAccountBound ? "BOUND" : "NOT BOUND"}
          tone={brokerAccountBound ? "success" : "warning"}
          detail={
            brokerAccountBound
              ? `Custody scope: ${provider?.custody_scope || "configured broker account"}.`
              : "The provider is not bound to the MT5/Hugo's Way account. Stripe credentials alone do not create that binding."
          }
        />
        <SetupCard
          label="Destination token"
          status={payoutDestinationSet ? "SET" : "REQUIRED"}
          tone={payoutDestinationSet ? "success" : "warning"}
          detail={
            payoutDestinationSet
              ? "A payout destination token is present."
              : "A payout destination token is required before withdrawals or payouts can run."
          }
        />
        <SetupCard
          label="Destination allowlist"
          status={payoutAllowlisted ? "ALLOWLISTED" : "REQUIRED"}
          tone={payoutAllowlisted ? "success" : "warning"}
          detail={
            payoutAllowlisted
              ? "Owner marked the destination as approved."
              : "Real payouts remain blocked until the destination is explicitly allowlisted."
          }
        />
        <SetupCard
          label="Owner payout gate"
          status={payoutAuthorized ? "AUTHORIZED" : "OWNER PENDING"}
          tone={payoutAuthorized ? "success" : "warning"}
          detail={
            payoutAuthorized
              ? "The owner gate is on, but real money still depends on the runtime rail above."
              : payoutCapability?.missing_requirements.join("; ") || "Owner approval is still required."
          }
        />
        <SetupCard
          label="Receipt evidence"
          status={receiptLabel}
          tone={receiptVerified ? "success" : "warning"}
          detail={
            receiptDetail ||
            (receiptVerified
              ? "Broker receipt evidence is present."
              : "Broker receipt evidence is still required before real payouts should be trusted.")
          }
        />
      </div>
    </div>
  );
}
