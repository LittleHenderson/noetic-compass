/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 3). */

import { LiveEnableKey } from "../../data/api";

export const GO_LIVE_GROUPS: { title: string; keys: LiveEnableKey[] }[] = [
  { title: "Account acknowledgments", keys: ["personal_account_ack", "no_pooled_capital_ack"] },
  { title: "Live broker mode", keys: ["live_mode", "prefer_mt5"] },
  { title: "Owner enable", keys: ["owner_enable_live_trading", "live_trading_licensed"] },
];


export const REAL_MONEY_ARM_CONFIRM_PHRASE = "ARM REAL MONEY";

export const PAYMENT_PROVIDER_LIVE_CONFIRM_PHRASE = "ARM PAYMENT PROVIDER LIVE";

export const ARM_CONFIRM_KEYS = new Set<string>([
  "personal_account_ack",
  "no_pooled_capital_ack",
  "live_mode",
  "prefer_mt5",
  "owner_enable_live_trading",
  "live_trading_licensed",
  "owner_enable_broker_accept",
  "owner_enable_auto_deposit",
  "owner_enable_bank_card_movement",
  "owner_enable_payout_automation",
  "payout_destination_allowlisted",
]);


export const BROKER_REALITY_CHECKS = [
  ["broker_entity_reviewed", "Broker entity reviewed"],
  ["withdrawal_minimum_reviewed", "Withdrawal minimum reviewed"],
  ["withdrawal_timing_reviewed", "Withdrawal timing reviewed"],
  ["kyc_requirements_reviewed", "KYC requirements reviewed"],
  ["withdrawal_fees_reviewed", "Withdrawal fees reviewed"],
  ["currency_conversion_reviewed", "Currency conversion reviewed"],
  ["automation_tos_reviewed", "Automation terms reviewed"],
  ["owner_accepts_broker_terms", "Owner accepts broker terms"],
] as const;


export const BROKER_REALITY_TEXT_FIELDS = [
  ["broker_entity", "Broker entity / jurisdiction"],
  ["withdrawal_minimum", "Withdrawal minimum"],
  ["withdrawal_timing", "Withdrawal timing"],
  ["kyc_requirements", "KYC requirements"],
  ["withdrawal_fees", "Withdrawal fees"],
  ["currency_conversion", "Currency conversion"],
  ["automation_tos", "Automation terms"],
  ["notes", "Owner notes"],
] as const;


export const LIVE_PILOT_CHECKS = [
  ["owner_understands_real_money_risk", "Owner understands real-money risk"],
  ["owner_confirms_risk_denominated_sizing", "Lot size follows stop risk, margin, and exposure"],
  ["owner_confirms_autonomous_scaling_within_envelope", "Operator may scale autonomously inside the envelope"],
  ["owner_confirms_emergency_stop_ready", "Emergency stop is ready"],
] as const;


export const LIVE_PILOT_RISK_FIELDS = [
  ["max_trade_risk_pct_equity", "Max stop risk per trade (% equity)"],
  ["max_daily_loss_usd", "Max daily realized loss USD"],
  ["max_total_loss_usd", "Max authority loss USD"],
] as const;


export const LIVE_PILOT_LEGACY_FIELDS = [
  ["max_trade_lots", "Legacy max trade lots"],
  ["max_open_live_lots", "Legacy max open lots"],
  ["max_live_trade_count", "Legacy max live trades"],
  ["max_pilot_days", "Legacy max pilot days"],
] as const;


export const LIVE_PILOT_NUMBER_FIELDS = [...LIVE_PILOT_RISK_FIELDS, ...LIVE_PILOT_LEGACY_FIELDS] as const;


export function armConfirmationForPatch(patch: Record<string, unknown>): string | null {
  if (["live", "production"].includes(String(patch.payment_provider_environment ?? "").trim().toLowerCase())) {
    return PAYMENT_PROVIDER_LIVE_CONFIRM_PHRASE;
  }
  const enabling = Object.entries(patch)
    .filter(([key, value]) => ARM_CONFIRM_KEYS.has(key) && value === true)
    .map(([key]) => key)
    .sort();
  if (enabling.length === 0) return null;
  if (enabling.length === 1) return `ARM ${enabling[0]}`;
  return REAL_MONEY_ARM_CONFIRM_PHRASE;
}


export function requestArmConfirmation(phrase: string): string | null {
  return window.prompt(`Type exactly "${phrase}" to arm this live/money authority switch.`, "");
}


export function confirmRequiredMessage(payload: { need_confirmation?: string | null }): string {
  return `Type exactly "${payload.need_confirmation ?? REAL_MONEY_ARM_CONFIRM_PHRASE}" to arm this live/money authority switch.`;
}

