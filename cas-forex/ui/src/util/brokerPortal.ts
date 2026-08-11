export interface BrokerPortalInfo {
  label: string;
  url: string;
}

const BROKER_PORTALS: Record<string, BrokerPortalInfo> = {
  risenfx: { label: "RisenFX", url: "https://secure.risenfx.com/" },
  hugosway: { label: "Hugo'sWay", url: "https://app.hugosway.com/" },
};

export function brokerPortalInfo(
  brokerId?: string | null,
  brokerDisplayName?: string | null,
  brokerWebsite?: string | null,
): BrokerPortalInfo {
  const normalized = String(brokerId || "risenfx").trim().toLowerCase();
  return BROKER_PORTALS[normalized] ?? {
    label: brokerDisplayName?.trim() || normalized || "Broker",
    url: brokerWebsite?.trim() || BROKER_PORTALS.risenfx.url,
  };
}
