/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 3). */

import { LiveMoneyProgressionPacket } from "../../data/api";

export const LIVE_MONEY_PROGRESS_REFRESH_EVENT = "cas-forex-live-money-refresh";

export function isLiveMoneyProgressionWarming(packet: LiveMoneyProgressionPacket | null | undefined): boolean {
  return packet?.status === "WARMING" || packet?.cache_status === "warming" || packet?.cache_refreshing === true;
}


export function emitLiveMoneyProgressionRefresh() {
  window.dispatchEvent(new Event(LIVE_MONEY_PROGRESS_REFRESH_EVENT));
}

