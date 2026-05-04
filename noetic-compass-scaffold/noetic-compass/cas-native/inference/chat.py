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

from cas_native.inference.cas_renderer import render_cas_prediction  # noqa: E402
from cas_native.inference.demo_prompts import DEMO_PROMPTS  # noqa: E402
from cas_native.inference.predict_cas import load_predictor  # noqa: E402
from cas_native.inference.rewrite_shim import (  # noqa: E402
    detect_cas_signal,
    rewrite_to_training_surface,
)

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

CHECKPOINT_METRIC = "K=9 baseline | 93.2% canonical exact on held-out 1K"

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
    title = f"CAS-Native v0 {CHEVRON} conversational REPL"
    subtitle = f"checkpoint: {CHECKPOINT_METRIC}"
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
    body.append("  /menu  ", style=COLOR_BANNER)
    body.append("browse the 21 curated demo prompts\n", style=COLOR_MUTED)
    body.append("  /sample", style=COLOR_BANNER)
    body.append("  random demo prompt\n", style=COLOR_MUTED)
    body.append("  /raw   ", style=COLOR_BANNER)
    body.append("toggle raw prediction dict (default OFF)\n", style=COLOR_MUTED)
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
    table.add_row(
        Text("ENGLISH", style=f"bold {COLOR_ENGLISH}"),
        Text(english, style=COLOR_ENGLISH),
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
) -> None:
    if console is None:
        _print_plain("")
        _print_plain(f"INPUT: {user_text}")
        if signal is not None:
            _print_plain(f"DETECTED SIGNAL: {_format_signal_line(signal)}")
        if rewritten is not None and rewritten != user_text:
            _print_plain(f"REWRITTEN: {rewritten}")
        _print_plain(f"CAS PREDICTION: {expression}")
        _print_plain(f"ENGLISH: {english}")
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
    predictor: Callable[[str], dict[str, Any]],
    text: str,
    *,
    console: "Console | None",
    show_raw: bool,
    apply_rewrite: bool,
    extra_notes: list[str] | None = None,
) -> None:
    """Run detection + (optional) rewrite + prediction, render the turn."""
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

    try:
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
        return

    expression = _expression_from_prediction(prediction)
    english = render_cas_prediction(prediction)

    _render_turn(
        console,
        user_text=text,
        signal=signal,
        rewritten=rewritten,
        expression=expression,
        english=english,
        raw_prediction=prediction if show_raw else None,
        notes=notes,
    )


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
    predictor: Callable[[str], dict[str, Any]],
    *,
    console: "Console | None",
    show_raw: bool,
    read_line: Callable[[str], str],
) -> None:
    if console is not None:
        console.print(_build_menu_table())
    else:
        for i, entry in enumerate(DEMO_PROMPTS, start=1):
            _print_plain(f"{i:>3}. [{entry['bucket']}] {entry['feature']}")

    try:
        choice = read_line("Pick a number (1-21), or anything else to cancel: ").strip()
    except (EOFError, KeyboardInterrupt):
        _print_plain("")
        return

    if not choice.isdigit():
        return
    pick = int(choice)
    if not 1 <= pick <= len(DEMO_PROMPTS):
        return

    entry = DEMO_PROMPTS[pick - 1]
    note = (
        f"demo entry {pick}/{len(DEMO_PROMPTS)} | bucket={entry['bucket']} | "
        f"ground_truth={entry['ground_truth']}"
    )
    _predict_and_show(
        predictor,
        entry["prompt"],
        console=console,
        show_raw=show_raw,
        apply_rewrite=False,  # already in training-surface format
        extra_notes=[note],
    )


def _show_random_demo(
    predictor: Callable[[str], dict[str, Any]],
    *,
    console: "Console | None",
    show_raw: bool,
) -> None:
    entry = random.choice(DEMO_PROMPTS)
    note = (
        f"random demo | bucket={entry['bucket']} | feature={entry['feature']} | "
        f"ground_truth={entry['ground_truth']}"
    )
    _predict_and_show(
        predictor,
        entry["prompt"],
        console=console,
        show_raw=show_raw,
        apply_rewrite=False,
        extra_notes=[note],
    )


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

    if console is not None:
        console.print(
            Text(f"Ready. {len(DEMO_PROMPTS)} curated demo prompts loaded.\n", style=COLOR_MUTED)
        )
    else:
        _print_plain(f"Ready. {len(DEMO_PROMPTS)} curated demo prompts loaded.\n")

    show_raw = False
    line_reader = _read_line(console)

    while True:
        try:
            text = _read_prompt(console)
        except (EOFError, KeyboardInterrupt):
            _print_plain("")
            break

        if not text:
            continue

        cmd = text.lower()
        if cmd in ("/exit", "/quit", "/q"):
            break
        if cmd in ("/help", "/h"):
            _emit_banner(console)
            continue
        if cmd in ("/menu", "/m"):
            _show_menu(predictor, console=console, show_raw=show_raw, read_line=line_reader)
            continue
        if cmd in ("/sample", "/s"):
            _show_random_demo(predictor, console=console, show_raw=show_raw)
            continue
        if cmd == "/raw":
            show_raw = not show_raw
            state = "ON" if show_raw else "OFF"
            msg = f"raw prediction dump now {state}"
            if console is not None:
                console.print(Text(msg, style=COLOR_MUTED))
            else:
                _print_plain(msg)
            continue
        if text.startswith("/"):
            msg = f"(unknown command: {text} - try /help)"
            if console is not None:
                console.print(Text(msg, style=COLOR_ERROR))
            else:
                _print_plain(msg)
            continue

        _predict_and_show(
            predictor,
            text,
            console=console,
            show_raw=show_raw,
            apply_rewrite=True,
        )

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

    if console is not None:
        console.print(
            Text(f"--smoke: predicting first 3 of {len(DEMO_PROMPTS)} demo prompts\n",
                 style=COLOR_MUTED)
        )
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
