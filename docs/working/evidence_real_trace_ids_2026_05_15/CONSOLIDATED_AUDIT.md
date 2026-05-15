# Evidence Packet → real trace_ids — consolidated audit (2026-05-15)

Master checkpoint: commit `63d68be` (v1 Evidence Packet, Codex audit "Pass Clean").
Branch in flight: `codex/evidence-real-trace-ids` — head `6621dc2`.

This document consolidates the findings of four parallel audits run before
shipping the real-trace_id wiring. It exists so any follow-up agent (or
Codex re-audit) can pick up the surface without re-walking the codebase.

---

## 1. MVP wiring (shipped on this branch)

**Commit `6621dc2` on `codex/evidence-real-trace-ids`.**

- `dashboard/src/components/idea-atlas/Mode7LiveShell.tsx` — passes
  `selectedTraceId={stream.state.finalTraceId ?? undefined}` to CASBrainMap.
- `dashboard/src/components/idea-atlas/CASBrainMap.tsx` — accepts
  `selectedTraceId?: string | null`; conditional button label
  ("Open Evidence" vs "Open Example Evidence"); honest title / aria-label
  swap; `data-testid="cas-brain-open-evidence"` preserved; `useEffect`
  mirrors the prop into the internal `evidenceTraceId` state.
- `dashboard/src/components/idea-atlas/CASBrainMap.test.tsx` — new, 126 LOC,
  2/2 pass: button text "Open Example Evidence" without prop, "Open
  Evidence" (no "Example") with a real `selectedTraceId`.

Verification: `tsc -b --noEmit` clean, 2/2 new vitest, 26/26 evidence
vitest unchanged. Pushed to origin.

**Status:** wired and works at the UI layer. WILL 404 today on a real
trace_id click — see §2.

---

## 2. Mode 7 trace persistence — the blocker

**Verdict: (C) — no real trace JSONs are persisted anywhere on disk.**

`api/routes/evidence.py:_candidate_trace_paths()` (lines 195–210) searches
five locations:
1. `dashboard/public/traces/{trace_id}.json` (canonical)
2. `cas-native/trace/captures/{trace_id}.json`
3. `.tmp/traces/{trace_id}.json`
4. `cas-synthetic/data/traces/{trace_id}.json`
5. `cas-native/trace/{trace_id}.json`

Repo-wide grep for writes to any of these paths: **none from production
code paths.** Only the dev fixture exists.

The four candidate writers all serialize to dict / JSON-string but never
write to disk:
- `cas_native/trace/generation_trace.py:to_dict()` (L193, L604) — pure.
- `cas_native/trace/live_capture.py:to_dict()` (L123) — pure.
- `cas_native/inference/traceability_v0.py:trace_to_json()` (L327) —
  returns string, no `open()`.
- `api/routes/mode7.py` — builds `report["traceability_v0"]` at L1087,
  extracts `trace_id` at L1277, emits over SSE at L1347 — never writes.

**Minimum fix (~15 LOC, backend-only):** add a JSON write to
`api/routes/mode7.py` inside the live stream handler (around L1370,
after `report` is built, before the stream returns). Target path
`.tmp/traces/{trace_id}.json` so it lands in candidate #3.

Sketch (do not copy without re-audit):

```python
trace_json = report.get("traceability_v0") or {}
trace_id_val = trace_json.get("trace_id")
if trace_id_val:
    trace_dir = _scaffold_root() / ".tmp" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    with (trace_dir / f"{trace_id_val}.json").open("w", encoding="utf-8") as fh:
        json.dump(trace_json, fh, indent=2, default=str)
```

This is a **separate commit** on the same branch; backend, not dashboard.

---

## 3. Chat REPL — bigger gap

**Headline: chat REPL is CLI-only. No web surface, no trace persistence,
no chat API. trace_ids cannot flow until that's built.**

- Chat REPL lives at `cas-native/inference/chat.py`. CLI script.
- It captures `LiveTrace` objects from Mode 7 hooks (chat.py L408–430)
  but never persists them.
- No FastAPI route under `api/routes/` matches `/chat`, `/converse`,
  `/native`, `/dialogue`. There is no chat HTTP endpoint today.
- No dashboard chat surface exists yet.

**Minimum change set to make chat REPL feed real trace_ids into Evidence
Packet:**
1. Generate UUID per chat turn (chat.py).
2. Write `LiveTrace` JSON to a `_candidate_trace_paths` location.
3. Build a new chat API route (none exists).
4. Build a dashboard chat surface that mounts an Open Evidence button.

**Scope:** weeks, not days. This is a follow-on project, not a small fix.
Recommend deferring until at least one of {chat API, dashboard chat UI}
is on the roadmap independently.

---

## 4. Idea Atlas — middle-sized gap

**Headline: ~5 files, ~300 LOC; also blocked on §2 persistence.**

- `Idea` interface at `dashboard/src/pages/IdeaAtlasPage.tsx:29–38` has
  no `trace_id` field.
- Ideas come from `POST /idea_atlas/ideas` (`api/routes/idea_atlas.py`
  L466–493) — casivenization endpoint that returns an `IdeaRecord`
  (schema at L67–75, also no `trace_id`).
- DB table `api/models_db.py:17–50` also lacks `trace_id`.
- The TRACE tab loads a separate trace JSON file (`IdeaAtlasPage.tsx`
  L903–961, `loadedTrace.trace_id` at L956) but it's not linked to any
  node selection.

**Minimum change set:**
- Add `trace_id` column to `Idea` DB table (+migration).
- Add `trace_id` to `IdeaRecord` response schema.
- Add `trace_id` to TS `Idea` interface.
- Either new `POST /idea_atlas/ideas_from_trace` route, OR augment
  existing casivenization route to persist + return trace_id.
- Mount an Evidence Packet trigger on `NodeDetailPanel.tsx`.

**Scope:** ~300 LOC, requires schema migration. Smaller than chat REPL,
bigger than Mode 7 persistence. Still blocked on §2 until production
trace persistence exists.

---

## 5. Recommended sequence

1. **Land the MVP commit `6621dc2`** as already-pushed on
   `codex/evidence-real-trace-ids`. It's correct in isolation; it just
   doesn't reach a live packet until §2 lands.
2. **Add Mode 7 persistence (~15 LOC backend commit)** to the same
   branch. After this, a Mode 7 stream completion → click "Open Evidence"
   → drawer loads a real packet end-to-end.
3. **Audit + merge to master** as one atomic Evidence-Packet-real-traces
   feature.
4. **Defer chat REPL and Atlas** to their own scoped branches once
   1–3 are stable and at least one of {chat API, schema migration} is
   roadmap-prioritized independently.

**Reserved language discipline (per SPEC §2 / Codex audits):** the
Evidence Packet is "tamper-evident, reproducible, independently
inspectable." Never "irrefutable." This rule still applies once real
trace_ids flow.
