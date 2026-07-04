import { apiGet, apiPostJson } from "./apiCore";

export interface CommandPreview {
  command: string;
  params: Record<string, unknown>;
  title: string;
  current?: unknown;
  proposed?: unknown;
  effects?: string[];
  blockers?: string[];
  ready?: boolean;
  confirm_phrase?: string;
}

export interface ProposedCommand {
  command: string;
  params: Record<string, unknown>;
}

export interface CommandExecuteResult {
  ok: boolean;
  applied: boolean;
  receipt?: Record<string, unknown>;
  result?: Record<string, unknown>;
  reason?: string;
  need_confirmation?: string;
  preview?: CommandPreview;
}

export interface CommandCatalogEntry {
  name: string;
  summary: string;
  params: Array<{ name: string; type: string; help: string }>;
}

export async function commandCatalog(): Promise<CommandCatalogEntry[]> {
  try {
    const d = await apiGet<{ commands: CommandCatalogEntry[] }>("/owner-command/catalog", 6000);
    return d.commands || [];
  } catch {
    return [];
  }
}

export async function previewCommand(command: string, params: Record<string, unknown>): Promise<CommandPreview> {
  return apiPostJson<CommandPreview, { command: string; params: Record<string, unknown> }>(
    "/owner-command/preview",
    { command, params },
  );
}

export async function executeCommand(
  command: string,
  params: Record<string, unknown>,
  confirm: string,
): Promise<CommandExecuteResult> {
  return apiPostJson<CommandExecuteResult, { command: string; params: Record<string, unknown>; confirm: string }>(
    "/owner-command/execute",
    { command, params, confirm },
  );
}

export async function commandReceipts(limit = 15): Promise<Array<Record<string, unknown>>> {
  try {
    const d = await apiGet<{ receipts: Array<Record<string, unknown>> }>(`/owner-command/receipts?limit=${limit}`, 6000);
    return d.receipts || [];
  } catch {
    return [];
  }
}
