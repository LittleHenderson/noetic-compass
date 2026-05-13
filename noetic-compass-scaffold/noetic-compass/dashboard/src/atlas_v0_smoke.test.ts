/**
 * Atlas v0 end-to-end smoke (Codex guardrail 4d3216f #6).
 *
 * Validates the full pipeline: REPL trace -> cas atlas-save -> file
 * on disk -> TraceLoader validator. This test runs only when a saved
 * trace exists in the cas-native tmp directory; skipped otherwise so
 * CI on a fresh checkout doesn't fail.
 *
 * Setup (manual):
 *   1. cd noetic-compass-scaffold/noetic-compass/cas-native
 *   2. printf "explain a thought becoming action\n/trace\n/quit\n" \
 *      | python inference/cas_cli.py chat-stage3 \
 *      | awk '/^{$/,/^}$/' > .tmp_smoke/trace_smoke.json
 *   3. python inference/cas_cli.py atlas-save \
 *      --from .tmp_smoke/trace_smoke.json \
 *      --out-dir .tmp_smoke/atlas_out --validate-strict
 *   4. cd ../dashboard && npx vitest run src/atlas_v0_smoke.test.ts
 */
import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { isAtlasTrace, validateAtlasTrace } from './lib/trace';

const SMOKE_DIR = '../cas-native/.tmp_smoke/atlas_out';

describe('Atlas v0 end-to-end smoke', () => {
  it.runIf(existsSync(SMOKE_DIR))(
    'REPL trace round-trips through atlas-save into TraceLoader validator',
    () => {
      const files = readdirSync(SMOKE_DIR).filter((f) => f.endsWith('.json'));
      expect(files.length).toBeGreaterThan(0);
      const raw = readFileSync(join(SMOKE_DIR, files[0]!), 'utf8');
      const parsed = JSON.parse(raw);
      const result = validateAtlasTrace(parsed);
      expect(result.ok).toBe(true);
      expect(isAtlasTrace(parsed)).toBe(true);
      if (result.ok) {
        expect(result.trace.schema_version).toBe('traceability_v0');
        expect(result.trace.thought_tree.nodes.length).toBeGreaterThan(0);
        expect(result.trace.thought_tree.edges.length).toBeGreaterThan(0);
      }
    },
  );
});
