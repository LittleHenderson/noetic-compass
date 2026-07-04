import { apiGet, apiPostJson, getOwnerToken, setOwnerToken } from "./apiCore";

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
  return ["127.0.0.1", "localhost", "::1"].includes(window.location.hostname);
}

export { getOwnerToken, setOwnerToken };
