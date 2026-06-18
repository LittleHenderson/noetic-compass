# Live-Worker Pre-Speech W0 Integration — Design + Gates

Date: 2026-06-18
Status: **DESIGN ONLY — OPEN / NOT LICENSED.** No detector is wired live.

## Why this is design-only right now

The next gate was "wire the scoped detector into the hosted/live worker so it
reads W0 before the first generated token." That presupposed a *validated*
detector. The 2026-06-18 re-audit **withdrew** the `internal_w0_prompt_injection_detection`
license: a character-level surface text control (0.93) beats the hidden-state
readout (0.897), so the readout is not demonstrably internal. See
`hidden_prompt_injection_w0_license_withdrawn_20260618.md`.

Wiring a surface-confounded readout into a live worker as a "detector" would be
shipping on sand. So this document specifies the path and the gates instead, and
wires only the honest, shadow-only pieces.

## What MAY be wired now (shadow-only, OPEN)

1. **Pre-speech W0 capture hook.** Capture prompt-stage hidden states at the
   target layer BEFORE the first generated token. This is legitimate research
   infrastructure (it is also required for the causal gate). It emits nothing
   that affects output; it only records activations to the Evidence Packet.
2. **Character-level surface screen.** The honest near-term signal for encoded-
   injection *presence* is a surface char-n-gram classifier (~0.93), which uses
   NO model internals. If wired, it must be labeled a SURFACE screen, route only
   to `FLAG_FOR_HUMAN_REVIEW`, and carry `verdict_effect: none_shadow_only`.

### BUILT 2026-06-18 (shadow-only)

A shadow `w0_prespeech_screen` event is now emitted by the live worker AFTER the
manifest and BEFORE the first generated token, in both `stream_fake_trace` and
`stream_real_trace` (`app/runtime/event_stream.py`). It is produced by
`app/runtime/w0_prespeech_screen.py`:

- It reads the prompt pre-speech and emits a TRANSPARENT surface indicator
  (encoded-text density), routing to `FLAG_FOR_HUMAN_REVIEW` above threshold.
- In the real path it records `w0_capture_enabled=True` (prompt-stage activations
  are captured), but it does NOT use hidden states for a verdict — internal
  detection is `NOT LICENSED`.
- `verdict_effect` is always `none_shadow_only`; `claim_ceiling` is always
  `NOT LICENSED`. It never alters or intercepts output.
- Tests: `tests/test_w0_prespeech_screen.py` proves the surface indicator, the
  shadow boundary, and that the event is emitted after the manifest and strictly
  before the first token.

This is the honest version of "wire it so it reads W0 before the first generated
token": the wiring exists and is pre-speech, but the only signal exposed is
surface, and licensing of internal detection stays OPEN.

## What MUST NOT be claimed or done

- No "internal W0 detection" claim from the current readout.
- No live interception / prevention / enforcement (`live_pre_speech_interception`
  stays `NOT LICENSED`).
- No conversion of any screen output to `ACCEPT` or automatic suppression.

## Gates to license `live_pre_speech_interception` (unchanged + strengthened)

1. A **re-licensed** internal W0 detector — i.e. one that passes the NEW 15-gate
   battery including `char_text_margin_pass` on a **surface-indistinguishable**
   dataset (see the withdrawal doc). Until that exists, there is nothing internal
   to intercept with.
2. Hosted/live worker receipt with prompt-stage activations captured before the
   first generated token.
3. Audit packet proving the live path read the W0 signal before output.
4. WORM/verifier evidence that the path has `verdict_effect` control boundaries.

## Integration points (when gate 1 is met)

- `live-trace-worker/app/runtime/probe_runner.py` — `capture_probes` already
  captures pre-generation activations; add a layer-18 readout summary.
- `live-trace-worker/app/runtime/model_loader.py` — loaded-model hook.
- Emit a shadow `w0_prespeech_screen` event on the existing event stream with
  both the surface-screen result and (once licensed) the hidden readout, each
  tagged with its claim ceiling.

## Bottom line

The pre-speech W0 *capture* is buildable now as shadow infra; the *detector* it
would feed is OPEN until it passes the surface-indistinguishable, char-controlled
battery. Live interception remains `NOT LICENSED`.
