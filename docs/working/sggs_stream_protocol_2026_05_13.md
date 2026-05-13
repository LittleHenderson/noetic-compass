# SGGS Stream Protocol — Wire Format Spec (v0)

**Date**: 2026-05-13
**Status**: skeleton — producer + client implemented, server endpoint not yet wired
**Schema version**: `sggs_stream_v0`
**Authoritative implementations**:
- Python producer: `cas-native/inference/sggs_stream.py`
- TypeScript client: `dashboard/src/lib/sggs_stream.ts`

---

## 1. Purpose

Deliver head-level structural commits from the CAS-Native inference server to the SGGS 3D viewer so the dashboard can animate structural assembly in real time. Pairs with the saved `traceability_v0` trace: live stream gives "what the model is doing right now," saved trace gives "what it did, available for rewind / slow-motion."

This is Phase 2 of the SGGS product backlog (`sggs_v2_v3_product_feature_backlog_2026_05_06.md` lines 91-108).

## 2. Transport

**Server-Sent Events** over HTTP, framed per the WHATWG / W3C HTML SSE spec.

Why SSE and not WebSocket:
- The channel is one-way (server → client). WebSocket's bidirectional capability is unused.
- SSE travels cleanly through HTTP proxies without upgrade negotiation.
- `EventSource` provides automatic reconnect + `Last-Event-ID` resume — exactly the semantics we want.
- Implementation cost is lower on both producer (any HTTP framework can stream lines) and consumer (browser-native API, no library).

## 3. Granularity

**Head-level, not token-level.**

Per spec line 105-106:

> **Streaming granularity**: target head-level (12 updates per turn) not token-level (hundreds per turn). Token-level gets jittery; head-level is readable.

And spec line 146:

> Real-time streaming requires either WebSocket or SSE. If latency too high, "real-time" property breaks. If updates too granular, viz gets jittery. **Sweet spot is probably head-level granularity (12 updates per turn).**

One commit corresponds to either:
- one structural-prediction head firing (noetic / domain / drive / register / cas_expression / slot_pattern / model_generation / confidence_marker / identifier_attempt), or
- one edge materializing between two previously-emitted nodes.

A typical turn emits ~12 `head_commit` events, ~6 `edge_commit` events, plus the `turn_start` and `turn_end` bookends. Total: ~20 SSE blocks over ~2-3 seconds at 6Hz.

## 4. SSE block format

Each event is a sequence of `field: value` lines terminated by a blank line:

```
event: head_commit
id: 9c3a7b1e0d4f5028
data: {"kind":"head_commit","schema_version":"sggs_stream_v0","turn_id":"t-001","head_index":3,"head_name":"register","node_id":"n7","node_kind":"identifier_attempt","node_label":"^3^P|A","parent_node_id":"n4","axis_attrs":{"register":"A","drive":"F2"}}

```

The blank `\n\n` terminator is load-bearing — the EventSource parser only dispatches an event when it sees it. Tests on both sides pin this.

The `id:` line carries a per-event unique identifier (16-hex-char UUID4 prefix in the reference producer). It is what enables resume semantics in Section 6.

## 5. Event kinds

### `turn_start`
Beginning of a model turn. Always exactly one per turn, first event.

```json
{
  "kind": "turn_start",
  "schema_version": "sggs_stream_v0",
  "turn_id": "t-001",
  "user_text": "show me how an AI refuses a harmful request",
  "created_at": "2026-05-13T20:00:00Z"
}
```

### `head_commit`
One structural-prediction-head has produced a node.

```json
{
  "kind": "head_commit",
  "schema_version": "sggs_stream_v0",
  "turn_id": "t-001",
  "head_index": 3,
  "head_name": "register",
  "node_id": "n7",
  "node_kind": "identifier_attempt",
  "node_label": "^3^P|A",
  "parent_node_id": "n4",
  "axis_attrs": {"register": "A", "drive": "F2"}
}
```

Field discipline:
- `head_index` is 0-based and stable across the turn so a client can reorder out-of-band commits.
- `head_name` names the head producing the commit (`noetic`, `domain`, `drive`, `register`, `cas_expression`, `slot_pattern`, `model_generation`, `confidence_marker`, `identifier_attempt`, `emergent`, `nl_bridge`, `user_prompt`).
- `node_id`, `node_kind`, `node_label` mirror the `traceability_v0.thought_tree` node shape so SGGS commits and saved Atlas traces speak the same vocabulary.
- `parent_node_id` is nullable; the root user-prompt node (implicit at `n0`) is delivered via `turn_start`.
- `axis_attrs` is an arbitrary key-value bag specific to the head (Noetic id, domain letter, drive id, register letter, coefficient, confidence, etc.).

### `edge_commit`
A structural edge between two previously-emitted nodes.

```json
{
  "kind": "edge_commit",
  "schema_version": "sggs_stream_v0",
  "turn_id": "t-001",
  "edge_id": "e0",
  "source_node_id": "n0",
  "target_node_id": "n1",
  "edge_kind": "parent_child"
}
```

`edge_kind` defaults to `parent_child`. Other values (`cross_register_fusion`, `recipe_prerequisite`, `inversion_replay`, etc.) are reserved for later use; the client treats unknown values as opaque labels.

### `turn_end`
Turn complete. Carries `final_trace_id` resolving to a `traceability_v0` trace for replay.

```json
{
  "kind": "turn_end",
  "schema_version": "sggs_stream_v0",
  "turn_id": "t-001",
  "final_trace_id": "00000000-0000-4000-8000-00000000c0c0",
  "total_heads": 12,
  "duration_ms": 2400,
  "ended_at": "2026-05-13T20:00:02Z"
}
```

### `warning`
Non-fatal advisory. Stream continues.

```json
{
  "kind": "warning",
  "schema_version": "sggs_stream_v0",
  "turn_id": "t-001",
  "severity": "info",
  "message": "Recipe coefficients are pedagogical defaults."
}
```

`severity` is one of `info` / `warning` / `error`, mirroring `traceability_v0` severity bands. Unknown values pass through verbatim so the producer can add a new band without an upstream code change.

### `error`
Fatal-for-this-turn error. The server may close the stream after emitting this.

```json
{
  "kind": "error",
  "schema_version": "sggs_stream_v0",
  "turn_id": "t-001",
  "code": "decode_crash",
  "message": "Model decode path raised an exception."
}
```

`code` is a stable short identifier suitable for metric labels.

## 6. Reconnect semantics

The browser-native `EventSource` handles reconnect automatically. On a transient disconnect (network blip, proxy timeout, server restart), the browser:

1. Waits a small backoff (default ~3s, server-configurable via the `retry:` SSE field).
2. Reconnects to the same URL with header `Last-Event-ID: <id>` set to the id of the last successfully-dispatched event.

The server is expected to maintain a small replay cache (last N events per turn) and resume the stream from after that id. If the server cannot resume (event expired from cache, or the turn already ended), it should emit a `warning` with severity `info` saying "could not resume, starting fresh" and then a fresh `turn_start`. The client will treat the new turn id as a fresh subscription.

**Resume vs replay-from-zero**: the client always sends `Last-Event-ID`; whether the server resumes or replays-from-zero is a server-side decision. The client hook exposes `lastEventId` in component state so external tooling (status panels, dev consoles) can read it without subscribing twice.

**Parse-error policy**: a single malformed event invokes `onError` but does NOT close the stream. A bad commit does not poison the channel; the next valid event dispatches normally. This matches `traceability_v0`'s discipline that producer helpers never raise mid-decode.

## 7. Demo stream

`cas sggs-stream-demo` writes a fake-but-realistic 20-block sequence to stdout (1 `turn_start` + 12 `head_commit` + 6 `edge_commit` + 1 `turn_end`). The sequence mirrors `dashboard/src/components/idea-atlas/TraceLoader.tsx::DEMO_TRACE_COMPLEX` — the canonical Θ-recipe walkthrough — so a stakeholder demo of the live stream lands on the same Atlas trace they have already seen statically.

Inter-event delay defaults to 150ms (~6.7Hz), matching the spec's head-level cadence. Pass `--no-delay` to emit all blocks immediately (useful for piping into a file or for fast tests).

Pipe through `curl --no-buffer` or an SSE proxy to test the TS client without a running model:

```bash
# write demo to file
cas sggs-stream-demo --no-delay > demo.sse

# serve demo via a one-liner local SSE proxy (Python stdlib)
python -c "
import http.server, sys
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
        with open('demo.sse','rb') as f: self.wfile.write(f.read())
http.server.HTTPServer(('localhost',8080), H).serve_forever()
"
```

Or invoke the standalone Python entry point:

```bash
python -m cas_native.inference.sggs_stream
```

## 8. CLI registration

The `cas sggs-stream-demo` subcommand is registered in `cas_native/inference/cas_cli.py` as a thin wrapper around `sggs_stream.run_demo_stream_cli`. The additive edit is < 10 lines (an import, a handler binding, a dispatcher entry). The same function is also exposed as `python -m cas_native.inference.sggs_stream` so the demo can be invoked without going through `cas_cli`.

## 9. Open questions (for Phase 2 follow-on)

- **Server-side replay cache**: how many events / how many turns to keep? Probably "last completed turn + current turn" is enough for stakeholder demos; production sizing TBD.
- **`retry:` field tuning**: SSE supports a server-sent reconnect-delay hint. Default 3s is fine for a polished demo but a stakeholder Wi-Fi blip might benefit from faster retry.
- **Authentication**: not addressed in v0. When the inference server lands behind auth, the client will need cookie / bearer-token wiring. EventSource supports neither natively — the `fetch`-based EventSource polyfill (Microsoft `eventsource-polyfill`, etc.) will be needed.
- **Backpressure**: an SGGS demo at 6Hz with a slow browser renderer could queue events. Not a v0 concern but worth measuring before scaling beyond 12 events per turn.
- **Branching / Mode 6 alternatives**: spec line 107 calls out that real branching visualization needs either Mode 6 counterfactual exposure or beam-search visualization. v0 emits one commit per head; alternative-consideration commits are Phase 3.

## 10. References

- WHATWG HTML SSE specification: https://html.spec.whatwg.org/multipage/server-sent-events.html
- `dashboard/src/lib/trace.ts` — the saved-trace TS types this stream mirrors
- `cas-native/inference/traceability_v0.py` — the saved-trace Python producer
- `sggs_v2_v3_product_feature_backlog_2026_05_06.md` lines 91-108 — Phase 2 work breakdown
