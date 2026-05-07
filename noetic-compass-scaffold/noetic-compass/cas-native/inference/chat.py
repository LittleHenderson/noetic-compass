"""CAS-Native v0 conversational REPL — polished demo build.

Wires the K=9 structured-token baseline checkpoint to:

* the rule-based rewrite shim (free-form English -> training-surface),
* the curated DEMO_PROMPTS catalogue (21 entries, all canonical-exact),
* the natural-language CAS renderer.

The aesthetic is rich-driven (panels, tables, soft cyan/amber/green palette).
Run interactively with ``python chat.py`` or smoke-test with ``python chat.py
--smoke`` (predicts the first three DEMO_PROMPTS without entering the loop).
"""

from __future__ import annotations

import random
import sys
import types
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

# Mirror the cas_native package indirection used elsewhere in cas-native/inference/
REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
if not REPO_ROOT.exists():
    REPO_ROOT = Path(__file__).resolve().parents[2]
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(REPO_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))

from cas_native.belief import BeliefStore  # noqa: E402
from cas_native.inference.cas_renderer import render_cas_prediction  # noqa: E402
from cas_native.inference.demo_prompts import DEMO_PROMPTS  # noqa: E402
from cas_native.inference.native_nl_generate import generate_reply  # noqa: E402
from cas_native.inference.predict_cas import load_predictor  # noqa: E402
from cas_native.inference.rewrite_shim import (  # noqa: E402
    detect_cas_signal,
    rewrite_to_training_surface,
)
from cas_native.training.tokenizer import HybridCASTokenizer  # noqa: E402
from cas_native.trace.live_capture import LiveTrace  # noqa: E402

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.text import Text
    _HAVE_RICH = True
except ImportError:  # pragma: no cover - documented fallback
    _HAVE_RICH = False


CHECKPOINT_RUN_DIR = (
    Path(__file__).resolve().parents[1]
    / "training"
    / "runs"
    / "structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045"
)

NATIVE_GEN_RUN_DIR = (
    Path(__file__).resolve().parents[1]
    / "training"
    / "runs"
    / "b3_full_50k_prodshape_20260507"
)

CHECKPOINT_METRIC = "K=9 baseline | 93.2% canonical exact on held-out 1K"
NATIVE_GEN_METRIC = "B-3 127M | CAS-grounded native generation (experimental)"

# Paul Tol-muted palette aliases (project standard from cas_diagram_and_clusters)
COLOR_BANNER = "cyan"
COLOR_PROMPT = "dim cyan"
COLOR_INPUT = "white"
COLOR_SIGNAL = "yellow"
COLOR_REWRITE = "yellow"
COLOR_PRED = "green"
COLOR_ENGLISH = "green"
COLOR_RAW = "grey50"
COLOR_ERROR = "red"
COLOR_MUTED = "grey62"
COLOR_BELIEF_LOCKED = "bold green"
COLOR_BELIEF_OPEN = "yellow"
COLOR_TRACE = "magenta"

CHEVRON = "›"  # U+203A ›


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------


def _make_console() -> "Console | None":
    if not _HAVE_RICH:
        return None
    return Console(highlight=False, soft_wrap=True)


def _print_plain(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def _emit_banner(console: "Console | None") -> None:
    title = f"CAS-Native v0 {CHEVRON} conversational REPL (B-4 Experimental)"
    subtitle = f"K=9 baseline: {CHECKPOINT_METRIC}\nB-3 native: {NATIVE_GEN_METRIC}"
    if console is None:
        _print_plain("=" * 60)
        _print_plain(title)
        _print_plain(subtitle)
        _print_plain("=" * 60)
        return
    body = Text()
    body.append(subtitle, style=COLOR_MUTED)
    body.append("\n\n")
    body.append("Type free-form English to predict, or use a command:\n", style=COLOR_MUTED)
    body.append("  /native", style=COLOR_BANNER)
    body.append(" toggle B-3 native generation (default OFF)\n", style=COLOR_MUTED)
    body.append("  /menu  ", style=COLOR_BANNER)
    body.append("browse the 21 curated demo prompts\n", style=COLOR_MUTED)
    body.append("  /sample", style=COLOR_BANNER)
    body.append("  random demo prompt\n", style=COLOR_MUTED)
    body.append("  /raw   ", style=COLOR_BANNER)
    body.append("toggle raw prediction dict (default OFF)\n", style=COLOR_MUTED)
    body.append("  /beliefs", style=COLOR_BANNER)
    body.append(" list locked beliefs (CABS)\n", style=COLOR_MUTED)
    body.append("  /why <claim>  ", style=COLOR_BANNER)
    body.append("explain belief gates for a claim\n", style=COLOR_MUTED)
    body.append("  /forget <claim>", style=COLOR_BANNER)
    body.append(" record a contradiction\n", style=COLOR_MUTED)
    body.append("  /trace ", style=COLOR_BANNER)
    body.append("show Mode 7 mechanistic trace of last prediction (--raw for JSON)\n", style=COLOR_MUTED)
    body.append("  /help  ", style=COLOR_BANNER)
    body.append("show this banner\n", style=COLOR_MUTED)
    body.append("  /exit  ", style=COLOR_BANNER)
    body.append("leave", style=COLOR_MUTED)
    panel = Panel(
        body,
        title=Text(title, style=f"bold {COLOR_BANNER}"),
        border_style=COLOR_BANNER,
        padding=(1, 2),
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Pretty printing of a single turn
# ---------------------------------------------------------------------------


def _build_turn_table(
    *,
    user_text: str,
    signal: dict[str, Any] | None,
    rewritten: str | None,
    expression: str,
    english: str,
    raw_prediction: dict[str, Any] | None,
    notes: list[str] | None = None,
    belief_status: str | None = None,
    belief_locked: bool = False,
    is_native: bool = False,
) -> "Table":
    """Build a rich Table with one row per logical section."""
    table = Table(
        show_header=False,
        show_lines=False,
        box=None,
        pad_edge=False,
        padding=(0, 1),
        expand=True,
    )
    table.add_column("label", style="bold", no_wrap=True, width=18)
    table.add_column("value", overflow="fold")

    table.add_row(Text("INPUT", style=f"bold {COLOR_BANNER}"), Text(user_text, style=COLOR_INPUT))

    if signal is not None:
        sig_line = _format_signal_line(signal)
        table.add_row(
            Text("DETECTED SIGNAL", style=f"bold {COLOR_SIGNAL}"),
            Text(sig_line, style=COLOR_SIGNAL),
        )

    if rewritten is not None and rewritten != user_text:
        table.add_row(
            Text("REWRITTEN", style=f"bold {COLOR_REWRITE}"),
            Text(rewritten, style=f"italic {COLOR_REWRITE}"),
        )

    table.add_row(
        Text("CAS PREDICTION", style=f"bold {COLOR_PRED}"),
        Text(expression, style=f"bold {COLOR_PRED}"),
    )

    english_label = "NATIVE ENGLISH" if is_native else "ENGLISH"
    table.add_row(
        Text(english_label, style=f"bold {COLOR_ENGLISH}"),
        Text(english, style=COLOR_ENGLISH),
    )

    if belief_status is not None:
        belief_color = (
            COLOR_BELIEF_LOCKED if belief_locked else COLOR_BELIEF_OPEN
        )
        table.add_row(
            Text("BELIEF STATUS", style=f"bold {belief_color}"),
            Text(belief_status, style=belief_color),
        )

    if notes:
        for note in notes:
            table.add_row(
                Text("NOTE", style=f"bold {COLOR_MUTED}"),
                Text(note, style=COLOR_MUTED),
            )

    if raw_prediction is not None:
        table.add_row(
            Text("RAW", style=f"bold {COLOR_RAW}"),
            Text(_format_raw_prediction(raw_prediction), style=COLOR_RAW),
        )

    return table


def _format_signal_line(signal: dict[str, Any]) -> str:
    parts: list[str] = []
    if signal.get("noetic") is not None:
        parts.append(
            f"Noetic ^{signal['noetic']} ({signal.get('noetic_confidence', 0):.2f})"
        )
    if signal.get("domain"):
        parts.append(
            f"domain {signal['domain']} ({signal.get('domain_confidence', 0):.2f})"
        )
    if signal.get("drive"):
        parts.append(
            f"drive {signal['drive']} ({signal.get('drive_confidence', 0):.2f})"
        )
    if signal.get("register"):
        parts.append(
            f"register |{signal['register']} ({signal.get('register_confidence', 0):.2f})"
        )
    return ", ".join(parts) if parts else "(no axes detected)"


def _format_raw_prediction(prediction: dict[str, Any]) -> str:
    keys_order = (
        "turn_type",
        "expression_family",
        "transition_kind",
        "noetic",
        "domain",
        "drive",
        "register_mode",
        "registers",
        "authority",
        "has_omega",
        "has_meta_logic",
        "meta_relations",
    )
    pieces: list[str] = []
    for key in keys_order:
        if key in prediction:
            pieces.append(f"{key}={prediction[key]!r}")
    extras = [k for k in prediction if k not in keys_order]
    for key in extras:
        pieces.append(f"{key}={prediction[key]!r}")
    return ", ".join(pieces)


def _render_turn(
    console: "Console | None",
    *,
    user_text: str,
    signal: dict[str, Any] | None,
    rewritten: str | None,
    expression: str,
    english: str,
    raw_prediction: dict[str, Any] | None,
    notes: list[str] | None = None,
    belief_status: str | None = None,
    belief_locked: bool = False,
    is_native: bool = False,
) -> None:
    if console is None:
        _print_plain("")
        _print_plain(f"INPUT: {user_text}")
        if signal is not None:
            _print_plain(f"DETECTED SIGNAL: {_format_signal_line(signal)}")
        if rewritten is not None and rewritten != user_text:
            _print_plain(f"REWRITTEN: {rewritten}")
        _print_plain(f"CAS PREDICTION: {expression}")
        english_label = "NATIVE ENGLISH" if is_native else "ENGLISH"
        _print_plain(f"{english_label}: {english}")
        if belief_status is not None:
            _print_plain(f"BELIEF STATUS  {belief_status}")
        for note in notes or []:
            _print_plain(f"NOTE: {note}")
        if raw_prediction is not None:
            _print_plain(f"RAW: {_format_raw_prediction(raw_prediction)}")
        _print_plain("")
        return

    table = _build_turn_table(
        user_text=user_text,
        signal=signal,
        rewritten=rewritten,
        expression=expression,
        english=english,
        raw_prediction=raw_prediction,
        notes=notes,
        belief_status=belief_status,
        belief_locked=belief_locked,
        is_native=is_native,
    )
    panel = Panel(
        table,
        border_style=COLOR_BANNER,
        padding=(0, 1),
        expand=True,
    )
    console.print(panel)


# ---------------------------------------------------------------------------
# Core prediction flow
# ---------------------------------------------------------------------------


def _expression_from_prediction(prediction: dict[str, Any]) -> str:
    """Pull the canonical expression string out of the renderer's lead sentence.

    The renderer wraps the expression in backticks; we extract it for the
    dedicated CAS PREDICTION row. If extraction fails we fall back to the full
    rendered string.
    """
    rendered = render_cas_prediction(prediction)
    if "`" in rendered:
        first = rendered.split("`", 1)[1]
        if "`" in first:
            return first.split("`", 1)[0]
    return rendered


def _predict_and_show(
    predictor: Callable[..., Any],
    text: str,
    *,
    console: "Console | None",
    show_raw: bool,
    apply_rewrite: bool,
    extra_notes: list[str] | None = None,
    belief_store: BeliefStore | None = None,
    capture_trace: bool = False,
    native_generator: dict[str, Any] | None = None,
) -> LiveTrace | None:
    """Run detection + (optional) rewrite + prediction, render the turn.

    When ``native_generator`` is provided, runs the two-stage inference loop:
    Stage 1 (K=9) -> Stage 2 (B-3 native generation).
    """
    signal: dict[str, Any] | None = None
    rewritten: str | None = None
    notes = list(extra_notes or [])
    target_text = text

    if apply_rewrite:
        signal = detect_cas_signal(text)
        if signal.get("has_signal"):
            rewritten = rewrite_to_training_surface(text)
            target_text = rewritten
        else:
            signal = None
            notes.append(
                "no CAS signal detected in free-form input; predicting on the "
                "raw text. The K=9 baseline tends to collapse to its prior on "
                "out-of-distribution colloquial English (documented modality "
                "limitation)."
            )

    trace: LiveTrace | None = None
    try:
        if capture_trace:
            try:
                result = predictor(target_text, with_trace=True)
                if isinstance(result, tuple) and len(result) == 2:
                    prediction, trace = result
                else:
                    prediction = result  # type: ignore[assignment]
            except TypeError:
                # Predictor signature does not support with_trace yet.
                prediction = predictor(target_text)
        else:
            prediction = predictor(target_text)
    except Exception as exc:  # pragma: no cover - defensive
        if console is not None:
            console.print(
                Panel(
                    Text(f"prediction failed: {exc}", style=COLOR_ERROR),
                    title=Text("ERROR", style=f"bold {COLOR_ERROR}"),
                    border_style=COLOR_ERROR,
                )
            )
        else:
            _print_plain(f"ERROR: prediction failed: {exc}")
        return None

    expression = _expression_from_prediction(prediction)
    is_native = False

    if native_generator is not None:
        try:
            # Stage 2: Native generation
            # Extract first register label (e.g. "T") from predicted list.
            # Defensive: K=9 may return [] for registers; fall back to "T".
            registers_list = prediction.get("registers") or []
            register = str(registers_list[0]) if registers_list else "T"
            # use_cas_prefix=False matches the trainer default and how
            # the diverse-CAS B-3.5 evaluation was measured. Conditioning
            # is via register + bottleneck-z + prompt encoder pass; CAS
            # expression is recorded as metadata but does not enter the
            # head's discrete-prefix path until the head exposes a
            # cas_prefix_mask (B-4 followup).
            gen_out = generate_reply(
                model=native_generator["model"],
                tokenizer=native_generator["tokenizer"],
                prompt_text=text,
                cas_expression=expression,
                register=register,
                max_new_tokens=200,
                sampling="top_p",
                temperature=0.8,
                top_p=0.9,
                use_cas_prefix=False,
                device=native_generator["device"],
            )
            english = gen_out["reply_text"]
            is_native = True
            notes.append(
                f"Stage 2 (B-3): generated {gen_out['n_steps']} tokens "
                f"with top-p=0.9, temp=0.8."
            )
        except Exception as exc:
            notes.append(f"Stage 2 (native generation) failed: {exc}. Falling back to rule-based English.")
            english = render_cas_prediction(prediction)
    else:
        english = render_cas_prediction(prediction)

    belief_status: str | None = None
    belief_locked = False
    if belief_store is not None:
        try:
            belief = belief_store.record_observation(
                text,
                expression,
                evidence_strength=0.5,
                source="chat-session",
            )
            belief_status = belief.short_status()
            belief_locked = belief.locked
        except Exception as exc:  # pragma: no cover - belief substrate is best-effort
            notes.append(f"belief substrate recording failed: {exc}")

    _render_turn(
        console,
        user_text=text,
        signal=signal,
        rewritten=rewritten,
        expression=expression,
        english=english,
        raw_prediction=prediction if show_raw else None,
        notes=notes,
        belief_status=belief_status,
        belief_locked=belief_locked,
        is_native=is_native,
    )
    return trace


# ---------------------------------------------------------------------------
# /menu rendering
# ---------------------------------------------------------------------------


def _build_menu_table() -> "Table":
    table = Table(
        title=Text("Curated demo prompts (21)", style=f"bold {COLOR_BANNER}"),
        title_justify="left",
        border_style=COLOR_BANNER,
        header_style=f"bold {COLOR_BANNER}",
        show_lines=False,
        expand=True,
    )
    table.add_column("#", style=COLOR_PROMPT, width=4, justify="right")
    table.add_column("Bucket", style=COLOR_MUTED, no_wrap=True)
    table.add_column("Feature", style=COLOR_MUTED, no_wrap=True)
    table.add_column("Prompt", overflow="fold", style=COLOR_INPUT)

    grouped: "OrderedDict[str, list[tuple[int, dict[str, str]]]]" = OrderedDict()
    for i, entry in enumerate(DEMO_PROMPTS, start=1):
        grouped.setdefault(entry["bucket"], []).append((i, entry))

    first_bucket = True
    for bucket, items in grouped.items():
        if not first_bucket:
            table.add_section()
        first_bucket = False
        table.add_row(
            "",
            Text(bucket, style=f"bold {COLOR_BANNER}"),
            "",
            "",
        )
        for idx, entry in items:
            prompt_preview = entry["prompt"]
            if len(prompt_preview) > 90:
                prompt_preview = prompt_preview[:87] + "..."
            table.add_row(
                str(idx),
                "",
                entry["feature"],
                prompt_preview,
            )
    return table


def _show_menu(
    predictor: Callable[..., Any],
    *,
    console: "Console | None",
    show_raw: bool,
    read_line: Callable[[str], str],
    belief_store: BeliefStore | None = None,
    capture_trace: bool = False,
    native_generator: dict | None = None,
) -> LiveTrace | None:
    if console is not None:
        console.print(_build_menu_table())
    else:
        for i, entry in enumerate(DEMO_PROMPTS, start=1):
            _print_plain(f"{i:>3}. [{entry['bucket']}] {entry['feature']}")

    try:
        choice = read_line("Pick a number (1-21), or anything else to cancel: ").strip()
    except (EOFError, KeyboardInterrupt):
        _print_plain("")
        return None

    if not choice.isdigit():
        return None
    pick = int(choice)
    if not 1 <= pick <= len(DEMO_PROMPTS):
        return None

    entry = DEMO_PROMPTS[pick - 1]
    note = (
        f"demo entry {pick}/{len(DEMO_PROMPTS)} | bucket={entry['bucket']} | "
        f"ground_truth={entry['ground_truth']}"
    )
    return _predict_and_show(
        predictor,
        entry["prompt"],
        console=console,
        show_raw=show_raw,
        apply_rewrite=False,  # already in training-surface format
        extra_notes=[note],
        belief_store=belief_store,
        capture_trace=capture_trace,
        native_generator=native_generator,
    )


def _show_random_demo(
    predictor: Callable[..., Any],
    *,
    console: "Console | None",
    show_raw: bool,
    belief_store: BeliefStore | None = None,
    capture_trace: bool = False,
    native_generator: dict | None = None,
) -> LiveTrace | None:
    entry = random.choice(DEMO_PROMPTS)
    note = (
        f"random demo | bucket={entry['bucket']} | feature={entry['feature']} | "
        f"ground_truth={entry['ground_truth']}"
    )
    return _predict_and_show(
        predictor,
        entry["prompt"],
        console=console,
        show_raw=show_raw,
        apply_rewrite=False,
        extra_notes=[note],
        belief_store=belief_store,
        capture_trace=capture_trace,
        native_generator=native_generator,
    )


# ---------------------------------------------------------------------------
# CABS belief commands
# ---------------------------------------------------------------------------


def _show_beliefs(
    belief_store: BeliefStore,
    *,
    console: "Console | None",
) -> None:
    """Render the /beliefs command — locked beliefs, sorted by vibration desc."""
    locked = belief_store.list_locked()
    if not locked:
        msg = "(no locked beliefs yet — record more observations)"
        if console is not None:
            console.print(Text(msg, style=COLOR_MUTED))
        else:
            _print_plain(msg)
        return

    if console is None:
        _print_plain(f"Locked beliefs ({len(locked)}):")
        for b in locked:
            _print_plain(
                f"  ^4={b.vibration:.2f}  ^7={b.rhythm_count}  "
                f"{b.cas_expression}  {b.claim_text!r}"
            )
        return

    table = Table(
        title=Text(
            f"Locked beliefs ({len(locked)})",
            style=f"bold {COLOR_BELIEF_LOCKED}",
        ),
        title_justify="left",
        border_style=COLOR_BELIEF_LOCKED,
        header_style=f"bold {COLOR_BELIEF_LOCKED}",
        expand=True,
    )
    table.add_column("^4", justify="right", style=COLOR_BELIEF_LOCKED, width=6)
    table.add_column("^7", justify="right", style=COLOR_MUTED, width=4)
    table.add_column("CAS", style=COLOR_PRED, no_wrap=True)
    table.add_column("Claim", overflow="fold", style=COLOR_INPUT)
    for b in locked:
        table.add_row(
            f"{b.vibration:.2f}",
            str(b.rhythm_count),
            b.cas_expression,
            b.claim_text,
        )
    console.print(table)


def _show_why(
    belief_store: BeliefStore,
    claim_arg: str,
    *,
    console: "Console | None",
) -> None:
    """Render the /why <claim> command.

    Strategy: search for any belief whose claim_text matches the argument
    (case-insensitive, whitespace-collapsed). If none found, error.
    """
    if not claim_arg.strip():
        msg = "(usage: /why <claim text>)"
        if console is not None:
            console.print(Text(msg, style=COLOR_ERROR))
        else:
            _print_plain(msg)
        return

    candidates = belief_store.find_by_claim(claim_arg)
    if not candidates:
        # Try by claim_key prefix as a fallback.
        for b in belief_store.list_all():
            if b.claim_key.startswith(claim_arg.strip()):
                candidates.append(b)
                break
    if not candidates:
        msg = f"(no belief recorded for {claim_arg!r})"
        if console is not None:
            console.print(Text(msg, style=COLOR_ERROR))
        else:
            _print_plain(msg)
        return

    for belief in candidates:
        explanation = belief_store.explain(belief.claim_key)
        if explanation is None:
            continue
        _render_explanation(console, belief, explanation)


def _render_explanation(
    console: "Console | None",
    belief: Any,
    explanation: dict[str, Any],
) -> None:
    head = (
        f"{belief.claim_text!r}  expr={belief.cas_expression}  "
        f"key={belief.claim_key}"
    )
    lock_rule = explanation["lock_rule"]
    rule_summary = (
        f"locked={lock_rule['locked']} | "
        f"rpm={lock_rule['rpm']} | "
        f"^4>{lock_rule['vibration_threshold']:.2f}={lock_rule['vibration_above']} | "
        f"inv={lock_rule['inversion']} | "
        f"^7>={lock_rule['min_rhythm']}={lock_rule['rhythm']}"
    )

    rpm_status = explanation["rpm"]
    inv_axes = explanation["inversion"]
    obs = explanation["observations"]
    contradictions = explanation["contradictions"]

    if console is None:
        _print_plain("")
        _print_plain(f"WHY  {head}")
        _print_plain(f"  status: {belief.short_status()}")
        _print_plain(f"  rule: {rule_summary}")
        _print_plain("  RPM stages:")
        for stage_name, info in rpm_status.get("stages", {}).items():
            mark = "✓" if info.get("passed") else "✗"
            _print_plain(f"    {mark} {stage_name}: {info.get('reason', '')}")
        _print_plain("  Inversion axes:")
        for axis, info in inv_axes.items():
            mark = "✓" if info.get("clean") else "✗"
            placeholder = " (placeholder)" if info.get("placeholder") else ""
            _print_plain(
                f"    {mark} {axis}{placeholder}: {info.get('reason', '')}"
            )
        _print_plain(f"  Observations ({len(obs)}):")
        for o in obs:
            _print_plain(
                f"    {o.timestamp.isoformat()}  strength={o.evidence_strength:.2f}"
            )
        if contradictions:
            _print_plain(f"  Contradictions ({len(contradictions)}):")
            for c in contradictions:
                _print_plain(
                    f"    {c['timestamp'].isoformat()}  {c['reason']!r}"
                )
        _print_plain("")
        return

    body = Text()
    body.append(head + "\n", style=COLOR_INPUT)
    body.append(f"status: {belief.short_status()}\n", style=COLOR_BANNER)
    body.append(f"rule:   {rule_summary}\n\n", style=COLOR_MUTED)

    body.append("RPM stages:\n", style=f"bold {COLOR_BANNER}")
    for stage_name, info in rpm_status.get("stages", {}).items():
        mark = "✓" if info.get("passed") else "✗"
        color = COLOR_PRED if info.get("passed") else COLOR_ERROR
        body.append(f"  {mark} {stage_name}: ", style=color)
        body.append(f"{info.get('reason', '')}\n", style=COLOR_MUTED)

    body.append("\nInversion axes:\n", style=f"bold {COLOR_BANNER}")
    for axis, info in inv_axes.items():
        mark = "✓" if info.get("clean") else "✗"
        color = COLOR_PRED if info.get("clean") else COLOR_ERROR
        placeholder = " (placeholder)" if info.get("placeholder") else ""
        body.append(f"  {mark} {axis}{placeholder}: ", style=color)
        body.append(f"{info.get('reason', '')}\n", style=COLOR_MUTED)

    body.append(f"\nObservations ({len(obs)}):\n", style=f"bold {COLOR_BANNER}")
    for o in obs:
        body.append(
            f"  {o.timestamp.isoformat()}  strength={o.evidence_strength:.2f}\n",
            style=COLOR_MUTED,
        )
    if contradictions:
        body.append(
            f"\nContradictions ({len(contradictions)}):\n",
            style=f"bold {COLOR_ERROR}",
        )
        for c in contradictions:
            body.append(
                f"  {c['timestamp'].isoformat()}  {c['reason']!r}\n",
                style=COLOR_ERROR,
            )

    panel = Panel(
        body,
        title=Text("/why", style=f"bold {COLOR_BANNER}"),
        border_style=COLOR_BANNER,
        padding=(1, 2),
    )
    console.print(panel)


def _do_forget(
    belief_store: BeliefStore,
    claim_arg: str,
    *,
    console: "Console | None",
) -> None:
    """Add a contradiction for every belief matching ``claim_arg``."""
    if not claim_arg.strip():
        msg = "(usage: /forget <claim text>)"
        if console is not None:
            console.print(Text(msg, style=COLOR_ERROR))
        else:
            _print_plain(msg)
        return
    matches = belief_store.find_by_claim(claim_arg)
    if not matches:
        msg = f"(no belief matching {claim_arg!r})"
        if console is not None:
            console.print(Text(msg, style=COLOR_ERROR))
        else:
            _print_plain(msg)
        return
    for belief in matches:
        belief_store.add_contradiction(
            belief.claim_text,
            belief.cas_expression,
            reason=f"/forget command issued by user",
        )
    summary = (
        f"recorded {len(matches)} contradiction(s) for {claim_arg!r}; "
        "affected beliefs unlocked"
    )
    if console is not None:
        console.print(Text(summary, style=COLOR_BELIEF_OPEN))
    else:
        _print_plain(summary)


# ---------------------------------------------------------------------------
# Mode 7 trace commands
# ---------------------------------------------------------------------------


def _show_trace(
    trace: LiveTrace | None,
    *,
    console: "Console | None",
    raw: bool = False,
) -> None:
    """Render Mode 7 mechanistic trace summary or raw JSON.

    When ``raw=True``, dumps the full trace as JSON to stdout. Otherwise
    renders a compact human-readable summary: per-head argmax + confidence,
    top-3 bottleneck attribution dims per head, last-block (embedding) live
    activation magnitudes, attention/gate entropy summary.
    """
    if trace is None:
        msg = "(no trace available — predict something first)"
        if console is not None:
            console.print(Text(msg, style=COLOR_MUTED))
        else:
            _print_plain(msg)
        return

    if raw:
        _do_trace_raw(trace, console=console)
        return

    if console is None:
        _print_plain("")
        _print_plain(f"TRACE  input={trace.input_text!r}")
        _print_plain(f"  schema: {trace.schema_version}")
        timing = trace.timing or {}
        _print_plain(
            f"  timing: forward={timing.get('forward_ms', 0):.2f}ms "
            f"attribution={timing.get('attribution_ms', 0):.2f}ms"
        )
        _print_plain("  Live activations per layer:")
        for la in trace.layer_activations:
            _print_plain(
                f"    {la.name:<28} shape={la.shape} "
                f"L2={la.l2_norm:.3f} mean|.|={la.mean_abs:.3f}"
            )
        ent = trace.attention_entropy_summary or {}
        _print_plain(
            "  Attention/gate entropy: "
            f"mean={ent.get('mean', 0):.3f} "
            f"H={ent.get('entropy', 0):.3f} "
            f"tokens={int(ent.get('token_count', 0))}"
        )
        _print_plain("  Per-head argmax + top-3 bottleneck attribution:")
        for h in trace.heads:
            attr = ", ".join(
                f"d{d}={s:+.3f}" for d, s in h.top_k_attribution
            ) or "(no attribution)"
            label = (
                h.argmax_label if h.argmax_label is not None
                else str(h.argmax_index)
            )
            _print_plain(
                f"    {h.name:<18} argmax={label!r:<14} conf={h.confidence:.3f}  "
                f"top3=[{attr}]"
            )
        if trace.diagnostics:
            _print_plain(f"  Diagnostics: {trace.diagnostics}")
        _print_plain("")
        return

    body = Text()
    body.append(f"input={trace.input_text!r}\n", style=COLOR_INPUT)
    body.append(f"schema: {trace.schema_version}\n", style=COLOR_MUTED)
    timing = trace.timing or {}
    body.append(
        f"timing: forward={timing.get('forward_ms', 0):.2f}ms "
        f"attribution={timing.get('attribution_ms', 0):.2f}ms\n\n",
        style=COLOR_MUTED,
    )

    body.append("Live activations per layer:\n", style=f"bold {COLOR_TRACE}")
    for la in trace.layer_activations:
        body.append(
            f"  {la.name:<28} shape={la.shape} "
            f"L2={la.l2_norm:.3f} mean|.|={la.mean_abs:.3f}\n",
            style=COLOR_MUTED,
        )

    ent = trace.attention_entropy_summary or {}
    body.append(
        "\nAttention/gate entropy: ",
        style=f"bold {COLOR_TRACE}",
    )
    body.append(
        f"mean={ent.get('mean', 0):.3f}  "
        f"H={ent.get('entropy', 0):.3f}  "
        f"tokens={int(ent.get('token_count', 0))}\n",
        style=COLOR_MUTED,
    )

    panel = Panel(
        body,
        title=Text("Mode 7 trace", style=f"bold {COLOR_TRACE}"),
        border_style=COLOR_TRACE,
        padding=(1, 2),
    )
    console.print(panel)

    table = Table(
        title=Text(
            "Per-head argmax + top-3 bottleneck attribution",
            style=f"bold {COLOR_TRACE}",
        ),
        title_justify="left",
        border_style=COLOR_TRACE,
        header_style=f"bold {COLOR_TRACE}",
        show_lines=False,
        expand=True,
    )
    table.add_column("head", style=COLOR_PRED, no_wrap=True, width=18)
    table.add_column("argmax", style=COLOR_INPUT, no_wrap=True)
    table.add_column("conf", style=COLOR_INPUT, justify="right", width=6)
    table.add_column("top-3 attribution dims", style=COLOR_MUTED)
    for h in trace.heads:
        label = (
            h.argmax_label if h.argmax_label is not None
            else str(h.argmax_index)
        )
        attr = ", ".join(
            f"d{d}={s:+.3f}" for d, s in h.top_k_attribution
        )
        table.add_row(
            h.name,
            label,
            f"{h.confidence:.3f}",
            attr or "(none)",
        )
    console.print(table)

    if trace.diagnostics:
        console.print(
            Text(f"diagnostics: {trace.diagnostics}", style=COLOR_MUTED)
        )


def _do_trace_raw(trace: LiveTrace, *, console: "Console | None") -> None:
    """Dump the full trace as JSON to stdout."""
    import json as _json

    payload = _json.dumps(trace.to_dict(), indent=2)
    if console is None:
        _print_plain(payload)
    else:
        # Rich's Console.print on a long JSON string keeps it as-is.
        console.print(payload, soft_wrap=True)


# ---------------------------------------------------------------------------
# Loading + REPL
# ---------------------------------------------------------------------------


def _load_with_spinner(console: "Console | None") -> Any:
    if not CHECKPOINT_RUN_DIR.exists():
        raise FileNotFoundError(f"checkpoint run dir missing: {CHECKPOINT_RUN_DIR}")

    if console is None or not _HAVE_RICH:
        _print_plain("Loading K=9 baseline checkpoint...")
        return load_predictor(CHECKPOINT_RUN_DIR)

    with Progress(
        SpinnerColumn(style=COLOR_BANNER),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Loading K=9 baseline checkpoint...", total=None)
        predictor = load_predictor(CHECKPOINT_RUN_DIR)
        progress.update(task, completed=1)
    return predictor


def _load_native_generator(console: "Console | None", device: str = "cpu") -> dict[str, Any] | None:
    if not NATIVE_GEN_RUN_DIR.exists():
        return None

    import torch
    from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
    from cas_native.model.nl_generation_head import NLGenerationHead, NLGenerationHeadConfig

    if console is None or not _HAVE_RICH:
        _print_plain("Loading B-3 native generator...")
    else:
        progress = Progress(
            SpinnerColumn(style=COLOR_BANNER),
            TextColumn("[bold cyan]{task.description}[/bold cyan]"),
            console=console,
            transient=True,
        )
        progress.start()
        task = progress.add_task("Loading B-3 native generator...", total=None)

    try:
        tokenizer_path = NATIVE_GEN_RUN_DIR / "tokenizer.json"
        bpe_path = NATIVE_GEN_RUN_DIR / "english_bpe.json"
        tokenizer = HybridCASTokenizer.load(tokenizer_path)
        if bpe_path.exists():
            tokenizer = tokenizer.with_english_bpe(bpe_path)

        vocab_size = int(tokenizer.vocab_size)
        torch_device = torch.device(device)

        # Build model + head (hardcoded B-3 prodshape params for now)
        enc_cfg = CASNativeConfig(d_model=512, n_layers=6, n_heads=8, vocab_size=vocab_size)
        model = CASNativeModel(enc_cfg).to(torch_device)
        head_cfg = NLGenerationHeadConfig(vocab_size=vocab_size, d_model=512, n_heads=8, n_layers=6)
        head = NLGenerationHead(head_cfg).to(torch_device)
        model.attach_nl_gen_head(head)

        ckpt_path = NATIVE_GEN_RUN_DIR / "model_final.pt"
        state = torch.load(ckpt_path, map_location=torch_device)
        model.load_state_dict(state["model"])
        model.eval()

        if console is not None and _HAVE_RICH:
            progress.update(task, completed=1)
            progress.stop()

        return {"model": model, "tokenizer": tokenizer, "device": torch_device}
    except Exception as exc:
        if console is not None and _HAVE_RICH:
            progress.stop()
        _print_plain(f"Warning: failed to load native generator: {exc}")
        return None


def _read_prompt(console: "Console | None") -> str:
    if console is None:
        return input(f"cas-native {CHEVRON} ").strip()
    console.print(
        Text(f"cas-native {CHEVRON} ", style=f"bold {COLOR_PROMPT}"),
        end="",
    )
    return input().strip()


def _read_line(console: "Console | None") -> Callable[[str], str]:
    """Return a function that prints a styled prompt then reads a line."""
    def _fn(message: str) -> str:
        if console is None:
            return input(message)
        console.print(Text(message, style=COLOR_MUTED), end="")
        return input()
    return _fn


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    console = _make_console()
    _emit_banner(console)

    try:
        predictor = _load_with_spinner(console)
    except Exception as exc:
        if console is not None:
            console.print(
                Panel(
                    Text(str(exc), style=COLOR_ERROR),
                    title=Text("FATAL", style=f"bold {COLOR_ERROR}"),
                    border_style=COLOR_ERROR,
                )
            )
        else:
            _print_plain(f"FATAL: {exc}")
        return 2

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    native_gen_loaded = _load_native_generator(console, device=device)
    use_native = False

    belief_store = BeliefStore()

    if console is not None:
        ready_msg = f"Ready. {len(DEMO_PROMPTS)} curated demo prompts loaded. "
        if native_gen_loaded:
            ready_msg += "B-3 native generator AVAILABLE (/native to toggle). "
        else:
            ready_msg += "B-3 native generator not found. "
        ready_msg += f"Belief substrate: {len(belief_store.list_all())} known, {len(belief_store.list_locked())} locked.\n"
        console.print(Text(ready_msg, style=COLOR_MUTED))
    else:
        status = "AVAILABLE" if native_gen_loaded else "NOT FOUND"
        _print_plain(
            f"Ready. {len(DEMO_PROMPTS)} curated demo prompts loaded. "
            f"B-3 native generator {status}. "
            f"Belief substrate: {len(belief_store.list_all())} known, "
            f"{len(belief_store.list_locked())} locked.\n"
        )

    show_raw = False
    last_trace: LiveTrace | None = None
    line_reader = _read_line(console)

    try:
        while True:
            try:
                text = _read_prompt(console)
            except (EOFError, KeyboardInterrupt):
                _print_plain("")
                break

            if not text:
                continue

            cmd_token = text.split(None, 1)[0].lower()
            cmd_arg = text[len(cmd_token):].strip() if " " in text else ""
            if cmd_token in ("/exit", "/quit", "/q"):
                break
            if cmd_token in ("/help", "/h"):
                _emit_banner(console)
                continue
            if cmd_token == "/native":
                if not native_gen_loaded:
                    msg = "Error: B-3 native generator not loaded (check NATIVE_GEN_RUN_DIR)."
                else:
                    use_native = not use_native
                    state = "ON" if use_native else "OFF"
                    msg = f"B-3 native generation now {state}"
                if console is not None:
                    console.print(Text(msg, style=COLOR_MUTED))
                else:
                    _print_plain(msg)
                continue
            if cmd_token in ("/menu", "/m"):
                trace = _show_menu(
                    predictor,
                    console=console,
                    show_raw=show_raw,
                    read_line=line_reader,
                    belief_store=belief_store,
                    capture_trace=True,
                    native_generator=native_gen_loaded if use_native else None,
                )
                if trace is not None:
                    last_trace = trace
                continue
            if cmd_token in ("/sample", "/s"):
                trace = _show_random_demo(
                    predictor,
                    console=console,
                    show_raw=show_raw,
                    belief_store=belief_store,
                    capture_trace=True,
                    native_generator=native_gen_loaded if use_native else None,
                )
                if trace is not None:
                    last_trace = trace
                continue
            if cmd_token == "/raw":
                show_raw = not show_raw
                state = "ON" if show_raw else "OFF"
                msg = f"raw prediction dump now {state}"
                if console is not None:
                    console.print(Text(msg, style=COLOR_MUTED))
                else:
                    _print_plain(msg)
                continue
            if cmd_token == "/beliefs":
                _show_beliefs(belief_store, console=console)
                continue
            if cmd_token == "/why":
                _show_why(belief_store, cmd_arg, console=console)
                continue
            if cmd_token == "/forget":
                _do_forget(belief_store, cmd_arg, console=console)
                continue
            if cmd_token == "/trace":
                raw_flag = "--raw" in cmd_arg.split()
                _show_trace(last_trace, console=console, raw=raw_flag)
                continue
            if text.startswith("/"):
                msg = f"(unknown command: {text} - try /help)"
                if console is not None:
                    console.print(Text(msg, style=COLOR_ERROR))
                else:
                    _print_plain(msg)
                continue

            trace = _predict_and_show(
                predictor,
                text,
                console=console,
                show_raw=show_raw,
                apply_rewrite=True,
                belief_store=belief_store,
                capture_trace=True,
                native_generator=native_gen_loaded if use_native else None,
            )
            if trace is not None:
                last_trace = trace
    finally:
        belief_store.close()

    if console is not None:
        console.print(Text("Goodbye.", style=COLOR_BANNER))
    else:
        _print_plain("Goodbye.")
    return 0


# ---------------------------------------------------------------------------
# Smoke test (--smoke)
# ---------------------------------------------------------------------------


def _smoke() -> int:
    """Predict the first 3 DEMO_PROMPTS without entering the REPL."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    console = _make_console()
    _emit_banner(console)

    try:
        predictor = _load_with_spinner(console)
    except Exception as exc:
        if console is not None:
            console.print(
                Panel(
                    Text(str(exc), style=COLOR_ERROR),
                    title=Text("FATAL", style=f"bold {COLOR_ERROR}"),
                    border_style=COLOR_ERROR,
                )
            )
        else:
            _print_plain(f"FATAL: {exc}")
        return 2

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    native_gen = _load_native_generator(console, device=device)

    if console is not None:
        msg = f"--smoke: predicting first 3 of {len(DEMO_PROMPTS)} demo prompts"
        if native_gen:
            msg += " (NATIVE MODE ENABLED)"
        console.print(Text(msg + "\n", style=COLOR_MUTED))
    else:
        _print_plain(f"--smoke: predicting first 3 of {len(DEMO_PROMPTS)} demo prompts\n")

    for idx, entry in enumerate(DEMO_PROMPTS[:3], start=1):
        note = (
            f"smoke {idx}/3 | bucket={entry['bucket']} | feature={entry['feature']} | "
            f"ground_truth={entry['ground_truth']}"
        )
        _predict_and_show(
            predictor,
            entry["prompt"],
            console=console,
            show_raw=False,
            apply_rewrite=False,
            extra_notes=[note],
            native_generator=native_gen,
        )

    if console is not None:
        console.print(Text("smoke complete.", style=COLOR_BANNER))
    else:
        _print_plain("smoke complete.")
    return 0


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        sys.exit(_smoke())
    raise SystemExit(main())
