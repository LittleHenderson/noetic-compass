"""Stage 3 CAS conversation shell — Step 5 of the post-Stage-3 ordering.

The first real CAS conversation surface. Plain English Mode by default;
technical layers behind slash commands; CAS self-explanation folded in
for "what is CAS?" / "go deeper" / "simpler" questions. Free-form
natural-language chat politely declines for now — that's Step 5B
(Minimal NL Front Door).

Per `decisions.md` 2026-05-13T16:30Z and Codex chat ratification.

Three input classes:
1. CAS expression (starts with "let ", contains "^N^D" pattern, or
   contains "stage<X>_<digits>_<digits>"): route through the cas
   explain pipeline and produce Plain Mode output.
2. Question about CAS itself ("what is CAS?", "why?", "show me an
   example", etc.): route through cas_self_explainer with the current
   session depth level.
3. Free-form natural-language input: polite refusal pointing user to
   one of the two supported paths.

Slash commands:
- /plain: switch the last reply to plain mode (already default; no-op
  when current display is plain)
- /technical or /details: re-display the last reply at technical level
- /all: show both plain + technical layers
- /trace: dump the last trace dict as JSON
- /raw: dump the full last report as JSON
- /deeper: step up one depth level on the last "what is CAS" answer
- /simpler: step down one depth level
- /help: show available commands
- /clear: forget session history
- /quit or /exit: leave the REPL

Bounded scope (per `decisions.md` 2026-05-13T16:30Z):
- Existing `cas chat` (B-4 era) is UNTOUCHED.
- No Mode 7 visualization. No Living Thought Atlas wiring.
- No NL→CAS bridging (Step 5B authorized in principle, separate entry).

Run via:
    python -m cas_native.inference.stage3_chat_repl
    or
    cas chat-stage3
"""
from __future__ import annotations

import json
import re
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# Package indirection — mirrors stage3_local_smoke.py + cas_cli.py so
# this module runs as a plain script via `python <path>` or
# `python -m cas_native.inference.stage3_chat_repl`.
_SCRIPT_DIR = Path(__file__).resolve()
_NOETIC_COMPASS_ROOT = _SCRIPT_DIR.parents[2]
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(_NOETIC_COMPASS_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
if str(_NOETIC_COMPASS_ROOT) not in sys.path:
    sys.path.insert(0, str(_NOETIC_COMPASS_ROOT))


# ---------------------------------------------------------------------------
# Input classification
# ---------------------------------------------------------------------------

# Patterns to detect CAS expression input. Each pattern must require a
# CAS-shaped context, not a bare letter-number match — otherwise "F1
# racing" or "PEOPLE" or "EAT" get misread as CAS.
#
# Per Codex audit `fdd8a92` 2026-05-13: the classifier must not
# false-positive on normal English phrases. Each pattern below is
# scoped so it only fires on CAS-shaped syntax.
_CAS_PATTERNS = [
    # ^0..^9 Noetic operator. Bare carets don't appear in normal English.
    re.compile(r"\^\d"),
    # stageA0_4_857 style identifier — the most CAS-specific signal.
    re.compile(r"\bstage[A-Z]\d_\d+_\d+\b"),
    # `let stage<X>_... = ...` — RPM-chain prefix.
    re.compile(r"^let\s+stage", re.IGNORECASE),
    # Domain marker ^P / ^C / ^E / ^O — caret-prefixed, not bare letter.
    re.compile(r"\^[PCEO]\b"),
    # Register marker |T / |A / |f / |E — pipe-prefixed, not bare letter.
    re.compile(r"\|[TAfE]\b"),
    # Drive marker — only fires inside CAS curly-brace context (e.g.
    # `_{F5}`, `{F1,F2}`) so plain English like "F1 racing" doesn't
    # trigger.
    re.compile(r"\{F[1-7]\b"),
    # The `^N^D_{F_k}|R` compound shape — full CAS state vector tail.
    re.compile(r"\^\d\^[PCEO]_\{F[1-7]\}"),
]

# Phrases that signal "the user is asking about CAS itself."
_CAS_SELF_QUESTION_PATTERNS = [
    re.compile(r"\bwhat\s+is\s+cas\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+(is\s+)?this\b", re.IGNORECASE),
    re.compile(r"\bwhy\s+(does\s+)?(cas|this)\b", re.IGNORECASE),
    re.compile(r"\bexplain\s+(cas|yourself|this\s+system)", re.IGNORECASE),
    re.compile(r"\bwho\s+are\s+you\b", re.IGNORECASE),
    re.compile(r"\bgive\s+me\s+an?\s+example\b", re.IGNORECASE),
    re.compile(r"\bshow\s+me\s+(an?\s+)?example\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+do\s+(you|these)\s+(do|mean)", re.IGNORECASE),
    re.compile(r"\bhow\s+does\s+(cas|this)\s+work\b", re.IGNORECASE),
]


def classify_input(text: str) -> str:
    """Classify a user turn as 'cas_expression', 'cas_question', or
    'freeform'. Conservative: when a turn could be a CAS expression, it
    IS treated as one (the decoder will produce something or fail; the
    REPL surfaces the error cleanly).

    Returns one of: 'cas_expression', 'cas_question', 'freeform', 'empty'.
    """
    if not text or not text.strip():
        return "empty"

    # CAS expression takes priority. If we see Noetic operators, slot
    # identifiers, or `let stage...`, treat it as CAS.
    for pattern in _CAS_PATTERNS:
        if pattern.search(text):
            return "cas_expression"

    # Otherwise, look for CAS-self-question phrases.
    for pattern in _CAS_SELF_QUESTION_PATTERNS:
        if pattern.search(text):
            return "cas_question"

    return "freeform"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

@dataclass
class SessionState:
    """Holds the REPL's running state across turns."""
    # The Stage 3 bundle is held by the REPL itself; only the report
    # history and the current self-explainer depth level live here.
    history: list[dict[str, Any]] = field(default_factory=list)
    self_explain_level: str = "simple"
    self_explain_topic: str = "what"

    def push_explain(self, report: dict[str, Any]) -> None:
        """Record a cas-explain report."""
        self.history.append({"kind": "explain", "report": report})

    def push_self_explain(self, entry: dict[str, Any]) -> None:
        """Record a self-explainer entry."""
        self.history.append({"kind": "self_explain", "entry": entry})

    @property
    def last(self) -> Optional[dict[str, Any]]:
        return self.history[-1] if self.history else None


# ---------------------------------------------------------------------------
# Display helpers (Plain English Mode is the default)
# ---------------------------------------------------------------------------

def _render_explain_plain(report: dict[str, Any]) -> str:
    """Render a cas-explain report in plain mode."""
    plain = report.get("plain_english", {}) or {}
    lines = []
    short = plain.get("short_answer", "")
    meaning = plain.get("plain_meaning", "")
    generated = report.get("generated_english", "")
    caveat = plain.get("confidence_caveat")
    if short:
        lines.append(short)
    if meaning and meaning != short:
        lines.append("")
        lines.append(meaning)
    if generated:
        lines.append("")
        lines.append(f"The model said: {generated}")
    if caveat:
        lines.append("")
        lines.append(f"Note: {caveat}")
    return "\n".join(lines)


def _render_explain_technical(report: dict[str, Any]) -> str:
    """Render the technical layer of a cas-explain report."""
    lines = []
    model = report.get("model", {})
    lines.append(
        f"model: ablation={model.get('manifest_ablation_mode')} "
        f"load={model.get('load_seconds')}s "
        f"decode={model.get('decode_seconds')}s "
        f"max_cas_prefix_len={model.get('max_cas_prefix_len')}"
    )
    lines.append("")
    idents = report.get("identifiers", {})
    expected = idents.get("expected", []) or []
    emitted = idents.get("emitted", []) or []
    copied = set(idents.get("copied", []) or [])
    cov = idents.get("coverage")
    cov_str = f"{cov:.3f}" if isinstance(cov, float) else str(cov)
    lines.append(f"identifiers: {len(expected)} expected, {len(emitted)} emitted")
    for i, ident in enumerate(expected):
        marker = "OK  " if ident in copied else "MISS"
        lines.append(f"  [{marker}] {i}: {ident}")
    lines.append(f"coverage: {cov_str}")
    slot = report.get("slot_summary", {})
    lines.append(
        f"slot trace: length={slot.get('length')} "
        f"longest_STAGE_VAR_run={slot.get('longest_stage_var_run')} "
        f"counts={slot.get('counts')}"
    )
    gates = report.get("gates") or {}
    lines.append(f"gates: {gates}")
    return "\n".join(lines)


def _render_self_explain(entry: dict[str, Any]) -> str:
    """Render a self-explainer entry."""
    lines = []
    text = entry.get("text", "")
    metaphor = entry.get("metaphor")
    example = entry.get("example")
    deeper = entry.get("deeper")
    simpler = entry.get("simpler")
    if text:
        lines.append(text)
    if metaphor:
        lines.append("")
        lines.append(f"Picture it like: {metaphor}")
    if example:
        lines.append("")
        lines.append(f"Example: {example}")
    nav = []
    if deeper:
        nav.append(f"/deeper → {deeper}")
    if simpler:
        nav.append(f"/simpler → {simpler}")
    if nav:
        lines.append("")
        lines.append(f"({' · '.join(nav)})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------------

_HELP_TEXT = """
Available commands:
  /plain       Show the last reply in plain English (default mode)
  /technical   Show the last reply's technical details
  /details     Alias for /technical
  /all         Show both plain and technical for the last reply
  /trace       Dump the full Traceability v0 trace as JSON
  /tree        Dump only the Thought Tree (node-edge graph) as JSON
  /raw         Dump the full last reply report as JSON
  /deeper      Go one level deeper on the last "what is CAS?" answer
  /simpler     Go one level simpler on the last "what is CAS?" answer
  /help        Show this help
  /clear       Forget conversation history
  /quit /exit  Leave the REPL

You can type:
  - A CAS expression (e.g. "let stageA0_4_857 = ^7^P_{F5}; ...")
    → The model explains it in plain English.
  - A question about CAS itself
    ("what is CAS?", "why?", "give me an example", "who are you")
    → CAS explains itself at the current depth level.
  - Anything else
    → CAS politely says open-ended chat is not ready yet.
""".strip()


# ---------------------------------------------------------------------------
# REPL core (factored for testability)
# ---------------------------------------------------------------------------

@dataclass
class ReplResponse:
    """A single REPL response. Used so tests can inspect what the REPL
    would have printed without driving a real interactive loop."""
    text: str
    kind: str  # 'explain' | 'self_explain' | 'freeform_refusal' | 'command' | 'error'
    should_quit: bool = False


class _DummyExplainer:
    """Stand-in for the real cas-explain pipeline. Used by tests so the
    REPL classifier + display logic can be exercised without loading
    the 664 MB checkpoint. Returns a synthetic report that the renderer
    accepts."""

    def __call__(self, expression: str) -> dict[str, Any]:
        return {
            "command": "cas explain",
            "version": 1,
            "input_cas_expression": expression,
            "model": {
                "manifest_ablation_mode": "e3",
                "load_seconds": 0.0,
                "decode_seconds": 0.0,
                "max_cas_prefix_len": 192,
            },
            "generated_english": "(stub) the model said something here",
            "n_tokens_generated": 10,
            "identifiers": {
                "expected": [], "emitted": [], "copied": [], "missing": [],
                "coverage": None,
            },
            "slot_summary": {"length": 0, "counts": {},
                             "longest_stage_var_run": 0},
            "gates": {"no_crash": True, "generated_non_empty": True,
                      "ge_one_identifier_copied": False},
            "plain_english": {
                "short_answer": "(stub) plain answer",
                "plain_meaning": "(stub) plain meaning",
                "qualitative_coverage": "unknown",
                "qualitative_slot_quality": "unknown structure",
                "confidence_caveat": None,
            },
        }


def handle_turn(
    user_text: str,
    state: SessionState,
    explainer: Any,
) -> ReplResponse:
    """Pure-function REPL turn handler. Reads the user text, mutates
    state, returns the response that should be printed.

    Args:
        user_text: the line the user typed (without trailing newline).
        state: the session state. Mutated in place.
        explainer: a callable that takes a CAS expression and returns
            a cas-explain report dict. In production this wraps
            `cas_native.inference.cas_cli._cmd_explain` minus the CLI
            shell; in tests a `_DummyExplainer` instance is fine.

    Returns:
        A `ReplResponse` indicating what to print and whether to exit.
    """
    from cas_native.inference.cas_self_explainer import (
        explain_cas, step_deeper, step_simpler,
    )

    text = user_text.strip()
    if not text:
        return ReplResponse(text="", kind="command")

    # Slash commands first
    if text.startswith("/"):
        cmd, _, _arg = text[1:].partition(" ")
        cmd = cmd.lower()
        if cmd in ("quit", "exit"):
            return ReplResponse(text="Goodbye.", kind="command",
                                should_quit=True)
        if cmd == "help":
            return ReplResponse(text=_HELP_TEXT, kind="command")
        if cmd == "clear":
            state.history.clear()
            state.self_explain_level = "simple"
            state.self_explain_topic = "what"
            return ReplResponse(text="(history cleared)", kind="command")

        last = state.last
        if cmd == "plain":
            if last is None:
                return ReplResponse(text="(no previous reply)", kind="command")
            if last["kind"] == "explain":
                return ReplResponse(text=_render_explain_plain(last["report"]),
                                    kind="command")
            return ReplResponse(text=_render_self_explain(last["entry"]),
                                kind="command")
        if cmd in ("technical", "details"):
            if last is None:
                return ReplResponse(text="(no previous reply)", kind="command")
            if last["kind"] == "explain":
                return ReplResponse(text=_render_explain_technical(last["report"]),
                                    kind="command")
            # Self-explain has no "technical layer" — show the same content.
            return ReplResponse(text=_render_self_explain(last["entry"]),
                                kind="command")
        if cmd == "all":
            if last is None:
                return ReplResponse(text="(no previous reply)", kind="command")
            if last["kind"] == "explain":
                body = (
                    _render_explain_plain(last["report"])
                    + "\n\n" + "=" * 60 + "\n\n"
                    + _render_explain_technical(last["report"])
                )
                return ReplResponse(text=body, kind="command")
            return ReplResponse(text=_render_self_explain(last["entry"]),
                                kind="command")
        if cmd == "trace":
            # Per Codex audit `95fcecf` 2026-05-13: /trace dumps the
            # full clean Traceability v0 trace object. /tree dumps
            # only the Thought Tree sub-object.
            if last is None or last["kind"] != "explain":
                return ReplResponse(text="(no trace from last reply)",
                                    kind="command")
            from cas_native.inference.traceability_v0 import (
                build_v0_trace, trace_to_json,
            )
            v0 = last["report"].get("traceability_v0")
            if v0 is None:
                v0 = build_v0_trace(last["report"])
            return ReplResponse(text=trace_to_json(v0), kind="command")
        if cmd == "tree":
            # /tree shows ONLY the Thought Tree portion of the trace.
            # Useful when the user wants the node-edge graph without
            # the full trace metadata.
            if last is None or last["kind"] != "explain":
                return ReplResponse(text="(no thought tree from last reply)",
                                    kind="command")
            from cas_native.inference.traceability_v0 import build_v0_trace
            v0 = last["report"].get("traceability_v0")
            if v0 is None:
                v0 = build_v0_trace(last["report"])
            tree = v0.get("thought_tree", {})
            return ReplResponse(text=json.dumps(tree, indent=2,
                                                default=str),
                                kind="command")
        if cmd == "raw":
            if last is None:
                return ReplResponse(text="(no previous reply)", kind="command")
            payload = last.get("report") or last.get("entry") or {}
            return ReplResponse(text=json.dumps(payload, indent=2,
                                                default=str),
                                kind="command")
        if cmd == "deeper":
            new_level = step_deeper(state.self_explain_level)
            state.self_explain_level = new_level
            entry = explain_cas(level=new_level, topic=state.self_explain_topic)
            state.push_self_explain(entry)
            return ReplResponse(text=_render_self_explain(entry),
                                kind="self_explain")
        if cmd == "simpler":
            new_level = step_simpler(state.self_explain_level)
            state.self_explain_level = new_level
            entry = explain_cas(level=new_level, topic=state.self_explain_topic)
            state.push_self_explain(entry)
            return ReplResponse(text=_render_self_explain(entry),
                                kind="self_explain")
        return ReplResponse(text=f"(unknown command: /{cmd}; try /help)",
                            kind="command")

    # Not a slash command. Classify the input.
    kind = classify_input(text)
    if kind == "cas_expression":
        try:
            report = explainer(text)
        except Exception as exc:
            return ReplResponse(
                text=f"(could not process that CAS expression: {exc!r})",
                kind="error",
            )
        state.push_explain(report)
        return ReplResponse(text=_render_explain_plain(report),
                            kind="explain")

    if kind == "cas_question":
        # Stay at the current depth level on a fresh "what is CAS?"
        # question. The user navigates with /deeper and /simpler.
        # Update topic if the question hints at a specific facet.
        text_l = text.lower()
        if "example" in text_l:
            state.self_explain_topic = "example"
        elif "metaphor" in text_l or "like" in text_l:
            state.self_explain_topic = "metaphor"
        elif "why" in text_l:
            state.self_explain_topic = "why"
        elif "who" in text_l and "you" in text_l:
            state.self_explain_topic = "what"
        elif "symbol" in text_l:
            state.self_explain_topic = "symbol-legend"
        else:
            state.self_explain_topic = "what"
        entry = explain_cas(level=state.self_explain_level,
                            topic=state.self_explain_topic)
        state.push_self_explain(entry)
        return ReplResponse(text=_render_self_explain(entry),
                            kind="self_explain")

    # Step 5B Minimal NL Front Door: try the heuristic NL → CAS bridge
    # before falling through to the refusal. Per `decisions.md`
    # 2026-05-13T18:25Z. Rule-based, deterministic, no model call.
    # The matched pattern carries the inferred CAS expression which
    # we then run through the existing cas-explain pipeline so
    # Plain Mode + trace + Thought Tree all attach normally.
    from cas_native.inference.nl_to_cas_v0 import (
        match_nl_to_cas, list_supported_patterns,
    )
    nl_match = match_nl_to_cas(text)
    if nl_match is not None:
        try:
            report = explainer(nl_match.cas_expression)
        except Exception as exc:
            return ReplResponse(
                text=(
                    f"I read that as: `{nl_match.cas_expression}` "
                    f"({nl_match.matched_pattern}), but the model "
                    f"failed to explain it: {exc!r}"
                ),
                kind="error",
            )
        # Tag the report so /trace / /raw show this came via the NL
        # bridge — preserves traceability end-to-end.
        report["nl_bridge"] = {
            "user_text": text,
            "matched_pattern": nl_match.matched_pattern,
            "cas_expression": nl_match.cas_expression,
            "rationale": nl_match.rationale,
            "confidence": nl_match.confidence,
        }
        state.push_explain(report)
        # User-facing text: show the inferred CAS + rationale + then
        # the model's Plain Mode explanation. The user always sees
        # both — the bridge never hides what it inferred.
        head = (
            f"I read that as: `{nl_match.cas_expression}` "
            f"(matched pattern: {nl_match.matched_pattern}, "
            f"confidence {nl_match.confidence:.2f})\n"
            f"\n{nl_match.rationale}\n\n"
            f"--- model explanation ---\n"
        )
        return ReplResponse(
            text=head + _render_explain_plain(report),
            kind="nl_bridge_match",
        )

    # No NL pattern matched — keep the existing bridge-to-Step-5B text
    # but list supported patterns so the user learns what works.
    supported_examples = list_supported_patterns()
    examples_text = "\n".join(
        f"  - {p}" for p in supported_examples[:6]
    )
    return ReplResponse(
        text=(
            "I can answer CAS questions, explain CAS expressions, and "
            "translate a handful of constrained English patterns into "
            "CAS. Trained natural-language-to-CAS generation is the "
            "next experiment.\n\n"
            "Patterns I currently understand (heuristic v0). "
            "Try one of these as an example phrasing:\n"
            f"{examples_text}\n\n"
            "Other things you can try:\n"
            "  - Ask a CAS question: 'what is CAS?' or 'go deeper'\n"
            "  - Paste a CAS expression (example: "
            "'let stageA0_4_857 = ^7^P_{F5}; stageA0_4_857 -> "
            "stageA0_4_857')\n"
            "  - Type /help for the full command list."
        ),
        kind="freeform_refusal",
    )


# ---------------------------------------------------------------------------
# Interactive loop entry point
# ---------------------------------------------------------------------------

_BANNER = """
CAS Native — Stage 3 conversation shell (v0)
Type /help for commands. /quit to exit.
Plain English by default; technical details on demand.
""".strip()


def _build_production_explainer() -> Any:
    """Build the production explainer — wraps the cas-explain pipeline
    so the REPL can call it as `explainer(expression) -> report_dict`.
    Deferred import so the REPL module itself stays importable in
    test environments without torch."""
    from cas_native.inference.stage3_local_loader import load_stage3_local
    from cas_native.training.datasets.simplex_collator import SimplexCollator
    from cas_native.evaluation.sample_decoder import decode_canary_pack
    from cas_native.evaluation.evaluate_candidate_e_stage2 import (
        per_record_recovery, extract_identifiers_in_order,
    )
    from cas_native.inference.plain_english import translate_explain
    import torch as _torch
    import time as _time

    print("Loading Stage 3 checkpoint from local archive...")
    bundle = load_stage3_local(device="cpu")
    print("Ready.")

    cap = int(
        bundle.manifest.get("config", {}).get("max_cas_prefix_len", 192)
    )
    collator = SimplexCollator(
        bundle.tokenizer, enable_simplex_aux=True,
        max_cas_prefix_len=cap,
    )
    device = _torch.device("cpu")

    def _explain(expression: str) -> dict[str, Any]:
        prompt = (
            "Explain this rpm chain expression."
            if "->" in expression
            else "Explain this expression."
        )
        synthetic = {
            "id": "chat_repl_turn",
            "prompt_text": prompt,
            "reply_text": ".",
            "cas_expression": expression,
            "v1mix_task_type": "cas_to_english",
            "v1mix_grammar_category_or_error_class": "rpm_chain",
            "eval_meta": {"canonical_identifiers": []},
        }
        t0 = _time.time()
        decoded = decode_canary_pack(
            bundle.model, [synthetic], collator, bundle.tokenizer,
            device=device, max_new_tokens=192,
            hard_typed_emission=False, copy_confidence_threshold=0.5,
            truncate_traces=False,
        )
        decode_secs = _time.time() - t0
        entry = decoded[0]
        generated = entry.get("generated_text", "") or ""
        expected = extract_identifiers_in_order(expression)
        emitted = extract_identifiers_in_order(generated)
        copied = [i for i in expected if i in emitted]
        missing = [i for i in expected if i not in emitted]
        coverage = (len(copied) / len(expected)) if expected else None
        slot_trace = entry.get("slot_type_trace", []) or []
        from collections import Counter
        counts = Counter(slot_trace) if slot_trace else {}
        longest = 0
        cur_run = 0
        for sid in slot_trace:
            if sid == 2:
                cur_run += 1
                longest = max(longest, cur_run)
            else:
                cur_run = 0
        slot_summary = {
            "length": len(slot_trace),
            "counts": {str(k): int(v) for k, v in sorted(counts.items())},
            "longest_stage_var_run": int(longest),
        }
        report = {
            "command": "cas chat-stage3 (turn)",
            "version": 1,
            "input_cas_expression": expression,
            "model": {
                "manifest_ablation_mode": bundle.manifest.get("ablation_mode"),
                "load_seconds": 0.0,
                "decode_seconds": round(decode_secs, 3),
                "max_cas_prefix_len": cap,
            },
            "generated_english": generated,
            "n_tokens_generated": entry.get("n_tokens_generated"),
            "identifiers": {
                "expected": list(expected), "emitted": list(emitted),
                "copied": copied, "missing": missing, "coverage": coverage,
            },
            "slot_summary": slot_summary,
            "gates": {
                "no_crash": True,
                "generated_non_empty": bool(generated),
                "ge_one_identifier_copied": bool(copied),
            },
        }
        report["plain_english"] = translate_explain(report)
        # Embed Traceability v0 so /trace and /tree have it ready and
        # saved reports contain the UI-consumable trace. Per Codex
        # `8e0ae2d` (build trace before NL bridge).
        from cas_native.inference.traceability_v0 import build_v0_trace
        report["traceability_v0"] = build_v0_trace(report)
        return report

    return _explain


def main(argv: Optional[list[str]] = None) -> int:
    """Interactive REPL entry point."""
    print(_BANNER)
    state = SessionState()
    explainer = _build_production_explainer()
    try:
        while True:
            try:
                user_text = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            response = handle_turn(user_text, state, explainer)
            if response.text:
                print()
                print(response.text)
            if response.should_quit:
                break
    finally:
        print("\nSession ended.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
