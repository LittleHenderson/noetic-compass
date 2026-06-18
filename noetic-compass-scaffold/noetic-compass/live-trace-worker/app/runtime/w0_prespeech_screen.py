"""Shadow pre-speech W0 screen for the live worker.

Emitted once after the manifest and BEFORE the first generated token. It reads
the prompt (and flags whether prompt-stage W0 hidden states are being captured)
and routes suspicious prompts to ``FLAG_FOR_HUMAN_REVIEW``.

HONESTY BOUNDARY — this is shadow-only and makes NO internal-detection claim:

- The hidden-state prompt-injection readout was withdrawn on 2026-06-18 because
  a character-level surface control (0.925) beats it (0.897). See
  ``docs/working/hidden_prompt_injection_w0_license_withdrawn_20260618.md``.
- So the only signal here is a TRANSPARENT surface indicator (density of
  encoded-looking text), not an internal detector.
- ``verdict_effect`` is always ``none_shadow_only`` — it never alters, blocks, or
  intercepts output. ``claim_ceiling`` is always
  ``NOT LICENSED AS INTERNAL DETECTION``.

The W0 hidden states the worker captures pre-generation are recorded for future
research (the surface-clean re-license experiment), NOT used to make a verdict.
"""

from __future__ import annotations

import re

from ..schemas.events import W0PrespeechScreenEvent

# Transparent surface heuristic: fraction of the prompt that looks like an
# encoded payload (long base64-ish runs or url-encoded escapes). This is NOT a
# trained detector — it is an explainable "this prompt carries encoded text"
# indicator that a human reviewer can verify by eye.
_B64_RUN = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
_URL_ESC = re.compile(r"(?:%[0-9A-Fa-f]{2}){4,}")

DEFAULT_FLAG_THRESHOLD = 0.15


def encoded_surface_indicator(prompt: str) -> tuple[float, str]:
    """Return (fraction_encoded, signal_label) for a prompt — transparent, untrained."""

    text = prompt or ""
    if not text:
        return 0.0, "none"
    encoded_chars = 0
    signals: list[str] = []
    for match in _B64_RUN.finditer(text):
        encoded_chars += len(match.group(0))
        if "base64" not in signals:
            signals.append("base64")
    for match in _URL_ESC.finditer(text):
        encoded_chars += len(match.group(0))
        if "url_encoded" not in signals:
            signals.append("url_encoded")
    fraction = min(1.0, encoded_chars / max(1, len(text)))
    return fraction, ("+".join(signals) if signals else "none")


def build_w0_prespeech_screen_event(
    prompt: str,
    *,
    target_layer: int,
    w0_capture_enabled: bool,
    flag_threshold: float = DEFAULT_FLAG_THRESHOLD,
) -> W0PrespeechScreenEvent:
    """Build the shadow pre-speech screen event (no internal-detection claim)."""

    indicator, signal = encoded_surface_indicator(prompt)
    flagged = indicator >= flag_threshold
    return W0PrespeechScreenEvent(
        target_layer=max(0, int(target_layer)),
        w0_capture_enabled=bool(w0_capture_enabled),
        surface_indicator=round(indicator, 6),
        surface_signal=signal,
        route="FLAG_FOR_HUMAN_REVIEW" if flagged else "none",
        note=(
            "Shadow surface screen only (encoded-text density). Internal W0 "
            "prompt-injection detection is OPEN / NOT LICENSED; this does not "
            "alter or intercept output."
        ),
    )
