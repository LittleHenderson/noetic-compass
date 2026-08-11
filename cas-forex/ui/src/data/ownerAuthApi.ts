import {
  apiGet,
  apiPostJson,
  consumeOwnerPairingFromUrl,
  consumeOwnerTokenFromLocation,
  getOwnerToken,
  setOwnerToken,
} from "./apiCore";

export interface OwnerAuthState {
  token_present?: boolean;
  token_hint?: string;
  lan_mode_enabled?: boolean;
}

export interface OwnerPairing {
  owner_token?: string;
  token_hint?: string;
  lan_mode_enabled?: boolean;
  header_name?: string;
  pairing_hash_key?: string;
  api_base_hash_key?: string;
  pairing_urls?: string[];
  native_pairing_urls?: string[];
  pairing_api_bases?: string[];
  direct_api_bases?: string[];
  how_to_pair?: string;
}

export async function fetchOwnerAuthState(): Promise<OwnerAuthState | null> {
  try {
    return await apiGet<OwnerAuthState>("/owner-auth/state", 6000);
  } catch {
    return null;
  }
}

/** Loopback-only on the server; returns the full token so the desktop can pair a phone. */
export async function fetchOwnerPairing(): Promise<OwnerPairing | null> {
  try {
    return await apiGet<OwnerPairing>("/owner-auth/pairing", 6000);
  } catch {
    return null;
  }
}

export async function setLanMode(enabled: boolean): Promise<{ lan_mode_enabled?: boolean }> {
  return apiPostJson<{ lan_mode_enabled?: boolean }, { enabled: boolean }>(
    "/owner-auth/lan-mode",
    { enabled },
  );
}

export async function rotateOwnerToken(): Promise<{ token_hint?: string }> {
  return apiPostJson<{ token_hint?: string }, Record<string, never>>("/owner-auth/rotate", {});
}

export function isLoopbackHost(): boolean {
  if (typeof window === "undefined") return true;
  const host = window.location.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  return host === "localhost" || host === "::1" || host.startsWith("127.");
}

export { consumeOwnerPairingFromUrl, consumeOwnerTokenFromLocation, getOwnerToken, setOwnerToken };
