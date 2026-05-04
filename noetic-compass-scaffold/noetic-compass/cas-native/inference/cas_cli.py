"""Top-level ``cas`` dispatcher CLI.

Unified entry point for the Noetic Compass command surface. Thin glue: parses
the first positional ("subcommand") and delegates to the existing module that
already implements that subcommand. Does not re-implement REPLs, predictors,
or compilers.

Subcommands:

    cas chat              Launch the interactive REPL (cas_native.inference.chat)
    cas notation [...]    Compile a CAS expression (api.notation.cli)
    cas predict TEXT      One-shot prediction on a single text input
    cas demo              Show the curated 21 starter prompts (demo_prompts)
    cas version           Print version + checkpoint + metric info
    cas help              Print the dispatcher banner

Run as ``python -m cas_native.inference.cas_cli ...`` from the repo root, or
via the ``cas.bat`` shim at the repo root.
"""

from __future__ import annotations

import argparse
import sys
import types
from datetime import date
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Package indirection — mirrors chat.py / predict_cas.py / generate_samples.py
# so this module can be invoked from anywhere without the cas_native package
# being installed via pip.
# ---------------------------------------------------------------------------
REPO_ROOT = Path("/root/workspace/noetic-compass-scaffold/noetic-compass")
if not REPO_ROOT.exists():
    REPO_ROOT = Path(__file__).resolve().parents[2]
if "cas_native" not in sys.modules:
    pkg = types.ModuleType("cas_native")
    pkg.__path__ = [str(REPO_ROOT / "cas-native")]
    sys.modules["cas_native"] = pkg
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Static metadata. Resolved lazily so importing this module is cheap and does
# not pull torch.
# ---------------------------------------------------------------------------
PROJECT_VERSION_DEFAULT = "0.1.0-dev"
CHECKPOINT_NAME = "structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045"
CHECKPOINT_LABEL = "K=9 baseline"
TRAINING_TIME_CANONICAL_EXACT = "93.2%"
BUILD_DATE = date(2026, 5, 4).isoformat()


def _resolve_project_version() -> str:
    """Read the project version from pyproject.toml when available."""
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return PROJECT_VERSION_DEFAULT
    try:
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("version"):
                # version = "0.1.0"
                _, _, value = stripped.partition("=")
                value = value.strip().strip('"').strip("'")
                if value:
                    return value
    except Exception:
        pass
    return PROJECT_VERSION_DEFAULT


def _try_rich() -> Any:
    """Return the rich.console.Console class, or None if rich is unavailable."""
    try:
        from rich.console import Console  # type: ignore

        return Console
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Subcommand: help / banner
# ---------------------------------------------------------------------------
def _banner_lines(version: str) -> list[str]:
    return [
        "NOETIC COMPASS — CAS CLI",
        f"v{version} | {CHECKPOINT_LABEL} | {TRAINING_TIME_CANONICAL_EXACT} canonical exact",
        "",
        "Commands:",
        "  cas chat              Launch the interactive REPL (CAS-Native predictions)",
        "  cas notation EXPR     Compile a CAS expression to JSON / lex / parse / check",
        "  cas predict TEXT      One-shot prediction on a text input",
        "  cas demo              Show 21 curated starter prompts",
        "  cas version           Show version and metric info",
        "  cas help              Show this banner",
        "",
        "Examples:",
        "  cas chat",
        '  cas predict "I keep practicing the same scale every day"',
        '  cas notation "^3^E_{F2}|A"',
        "  cas notation --repl",
        "  cas demo",
        "",
        "Repo: https://github.com/LittleHenderson/noetic-compass",
    ]


def _cmd_help(_argv: list[str]) -> int:
    version = _resolve_project_version()
    Console = _try_rich()
    if Console is None:
        for line in _banner_lines(version):
            print(line)
        return 0
    try:
        from rich.panel import Panel  # type: ignore
        from rich.text import Text  # type: ignore

        body = Text("\n".join(_banner_lines(version)[2:]))
        title = Text(_banner_lines(version)[0], style="bold")
        subtitle = Text(_banner_lines(version)[1], style="dim")
        Console().print(Panel(body, title=title, subtitle=subtitle, border_style="cyan"))
        return 0
    except Exception:
        for line in _banner_lines(version):
            print(line)
        return 0


# ---------------------------------------------------------------------------
# Subcommand: version
# ---------------------------------------------------------------------------
def _cmd_version(_argv: list[str]) -> int:
    version = _resolve_project_version()
    print(f"project_version: {version}")
    print(f"checkpoint:      {CHECKPOINT_NAME}")
    print(f"checkpoint_tag:  {CHECKPOINT_LABEL}")
    print(f"canonical_exact: {TRAINING_TIME_CANONICAL_EXACT}  (training-time, held-out 1K)")
    print(f"build_date:      {BUILD_DATE}")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: demo
# ---------------------------------------------------------------------------
def _cmd_demo(_argv: list[str]) -> int:
    from cas_native.inference.demo_prompts import DEMO_PROMPTS  # noqa: WPS433

    grouped: dict[str, list[dict[str, str]]] = {}
    for entry in DEMO_PROMPTS:
        grouped.setdefault(entry["bucket"], []).append(entry)

    Console = _try_rich()
    if Console is None:
        _print_demo_plain(grouped)
        return 0
    try:
        from rich.table import Table  # type: ignore

        console = Console()
        for bucket, entries in grouped.items():
            table = Table(
                title=f"[bold]{bucket}[/bold] ({len(entries)} prompts)",
                show_lines=False,
                expand=True,
            )
            table.add_column("#", style="dim", width=3)
            table.add_column("feature", style="cyan", overflow="fold")
            table.add_column("ground_truth", style="green", overflow="fold")
            for idx, entry in enumerate(entries, start=1):
                table.add_row(
                    str(idx),
                    entry.get("feature", ""),
                    entry.get("ground_truth", ""),
                )
            console.print(table)
        console.print(
            f"[dim]total: {sum(len(e) for e in grouped.values())} curated prompts "
            "across {n} buckets. Use `cas chat` for the interactive picker.[/dim]".format(
                n=len(grouped)
            )
        )
        return 0
    except Exception:
        _print_demo_plain(grouped)
        return 0


def _print_demo_plain(grouped: dict[str, list[dict[str, str]]]) -> None:
    total = 0
    for bucket, entries in grouped.items():
        print()
        print(f"=== {bucket}  ({len(entries)} prompts) ===")
        for idx, entry in enumerate(entries, start=1):
            total += 1
            feature = entry.get("feature", "")
            truth = entry.get("ground_truth", "")
            print(f"  [{idx}] {feature}")
            print(f"      -> {truth}")
    print()
    print(
        f"total: {total} curated prompts across {len(grouped)} buckets. "
        "Use `cas chat` for the interactive picker."
    )


# ---------------------------------------------------------------------------
# Subcommand: predict
# ---------------------------------------------------------------------------
def _cmd_predict(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="cas predict",
        description="One-shot CAS prediction on a single piece of text.",
    )
    parser.add_argument("text", help="text to predict CAS structure for")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="print the full prediction dict (default: rendered English only)",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="torch device (default: cpu)",
    )
    args = parser.parse_args(argv)

    # Imports deferred — they pull torch.
    from cas_native.inference.cas_renderer import render_cas_prediction
    from cas_native.inference.predict_cas import load_predictor

    run_dir = (
        REPO_ROOT
        / "cas-native"
        / "training"
        / "runs"
        / CHECKPOINT_NAME
    )
    if not run_dir.exists():
        print(f"ERROR: checkpoint run dir missing: {run_dir}", file=sys.stderr)
        return 2

    predictor = load_predictor(run_dir, device=args.device)
    prediction = predictor(args.text)
    if args.raw:
        print(prediction)
    else:
        print(render_cas_prediction(prediction))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: chat
# ---------------------------------------------------------------------------
def _cmd_chat(_argv: list[str]) -> int:
    # Defer — chat.py pulls torch via predict_cas.
    from cas_native.inference.chat import main as chat_main

    return int(chat_main() or 0)


# ---------------------------------------------------------------------------
# Subcommand: notation
# ---------------------------------------------------------------------------
def _cmd_notation(argv: list[str]) -> int:
    from api.notation.cli import main as notation_main

    return int(notation_main(argv) or 0)


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
def _cmd_test(_argv: list[str]) -> int:
    """Smoke-test the dispatcher: version, demo, predict.

    Skips ``chat`` because it would block on stdin.
    """
    print("=== cas --test: version ===")
    rc1 = _cmd_version([])
    print()
    print("=== cas --test: demo ===")
    rc2 = _cmd_demo([])
    print()
    print("=== cas --test: predict ===")
    rc3 = _cmd_predict(["I can't stand it when people interrupt me"])
    print()
    overall = rc1 or rc2 or rc3
    print(f"=== cas --test: done (rc={overall}) ===")
    return overall


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
SUBCOMMANDS: dict[str, Callable[[list[str]], int]] = {
    "chat": _cmd_chat,
    "notation": _cmd_notation,
    "predict": _cmd_predict,
    "demo": _cmd_demo,
    "version": _cmd_version,
    "help": _cmd_help,
    "--help": _cmd_help,
    "-h": _cmd_help,
}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    raw = list(sys.argv[1:] if argv is None else argv)

    # Top-level --test flag, runs the smoke tests and exits.
    if raw and raw[0] == "--test":
        return _cmd_test(raw[1:])

    if not raw:
        return _cmd_help([])

    sub, rest = raw[0], raw[1:]
    handler = SUBCOMMANDS.get(sub)
    if handler is None:
        print(f"cas: unknown subcommand '{sub}'", file=sys.stderr)
        print("Run `cas help` for the list of subcommands.", file=sys.stderr)
        return 2
    return handler(rest)


if __name__ == "__main__":
    raise SystemExit(main())
