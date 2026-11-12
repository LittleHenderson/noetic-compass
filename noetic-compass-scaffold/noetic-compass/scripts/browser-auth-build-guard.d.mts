export function assertSafeBrowserModule(code: string, label?: string): void;
export function assertSafeBrowserEnvironment(env: Record<string, string | undefined>, requireAccounts?: boolean): void;
export function browserAuthBuildGuard(): {
  name: string;
  enforce: 'pre';
  configResolved(config: { env: Record<string, string>; mode: string }): void;
  transform(code: string, id: string): null;
  generateBundle(options: unknown, bundle: Record<string, { type: string; code?: string; source?: string | Uint8Array }>): void;
};
