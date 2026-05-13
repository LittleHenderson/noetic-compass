"""Top-level ``cas`` dispatcher CLI.

Unified entry point for the Noetic Compass command surface. Thin glue: parses
the first positional ("subcommand") and delegates to the existing module that
already implements that subcommand. Does not re-implement REPLs, predictors,
or compilers.

Subcommands:

    cas chat              Launch the interactive REPL (cas_native.inference.chat)
    cas notation [...]    Compile a CAS expression (api.notation.cli)
    cas predict TEXT      One-shot prediction on a single text input
    cas explain EXPR      Generate an English explanation of a CAS expression
                          using the Stage 3 local checkpoint
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
        "  cas explain EXPR      Generate an English explanation of a CAS expression",
        "                        using the Stage 3 local checkpoint",
        "  cas demo              Show 21 curated starter prompts",
        "  cas version           Show version and metric info",
        "  cas help              Show this banner",
        "",
        "Examples:",
        "  cas chat",
        '  cas predict "I keep practicing the same scale every day"',
        '  cas notation "^3^E_{F2}|A"',
        "  cas notation --repl",
        '  cas explain "let stageA0_4_857 = ^7^P_{F5}; stageA0_4_857 -> stageA0_4_857"',
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
# Subcommand: explain
# ---------------------------------------------------------------------------
# Step 4 of the post-Stage-3 build (decisions.md 2026-05-13T09:35Z).
# Takes a CAS expression in, runs it through the local Stage 3 checkpoint,
# returns the model's English explanation plus a small structured summary
# (identifier coverage + slot trace). No chat REPL. No Mode 7 trace.

def _explain_prompt_for_expression(cas_expression: str) -> str:
    """Pick the prompt phrasing the model was trained against.

    The Stage 3 training corpus (`rpm_copy_grounding_v2`) uses
    "Explain this rpm chain expression." for chain-shaped inputs. Other
    shapes get a generic phrasing so we never fabricate a training-prompt
    the model never saw.
    """
    if "->" in cas_expression:
        return "Explain this rpm chain expression."
    return "Explain this expression."


def _explain_slot_trace_summary(trace: list[int]) -> dict[str, Any]:
    """Compress a per-position slot_type trace to length + counts + the
    longest contiguous STAGE_VAR run.

    Mirrors `stage3_local_smoke._slot_trace_summary` so two callers stay
    in lockstep. Kept inline here to avoid importing smoke (which would
    pull torch at module load).
    """
    if not trace:
        return {"length": 0, "counts": {}, "longest_stage_var_run": 0}
    from collections import Counter

    STAGE_VAR_ID = 2
    counts = Counter(trace)
    longest = cur = 0
    for sid in trace:
        if sid == STAGE_VAR_ID:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return {
        "length": len(trace),
        "counts": {str(k): int(v) for k, v in sorted(counts.items())},
        "longest_stage_var_run": int(longest),
    }


def _print_explain_summary(output: dict[str, Any]) -> None:
    """Human-readable single-page summary mirroring the smoke harness."""
    print(f"=== cas explain — {output['timestamp_utc']} ===")
    model_info = output.get("model", {})
    print(
        f"model:           ablation_mode={model_info.get('manifest_ablation_mode')}  "
        f"load={model_info.get('load_seconds')}s  "
        f"decode={model_info.get('decode_seconds')}s"
    )
    print()
    print("--- input CAS expression ---")
    print(output.get("input_cas_expression") or "(empty)")
    print()
    print("--- generated English ---")
    print(output.get("generated_english") or "(empty)")
    print()
    idents = output.get("identifiers", {})
    expected = idents.get("expected", []) or []
    emitted = idents.get("emitted", []) or []
    copied = set(idents.get("copied", []) or [])
    missing = idents.get("missing", []) or []
    print(
        f"--- identifiers ({len(expected)} expected, {len(emitted)} emitted) ---"
    )
    for i, ident in enumerate(expected):
        marker = "OK  " if ident in copied else "MISS"
        print(f"  [{marker}] {i}: {ident}")
    if missing:
        print(f"missing:         {missing}")
    cov = idents.get("coverage")
    cov_str = f"{cov:.3f}" if isinstance(cov, float) else str(cov)
    print(f"coverage:        {idents.get('copied', [])} / {expected} = {cov_str}")
    print()
    slot = output.get("slot_summary", {})
    print(
        f"slot trace:      length={slot.get('length')}  "
        f"longest_STAGE_VAR_run={slot.get('longest_stage_var_run')}  "
        f"counts={slot.get('counts')}"
    )
    print()
    print("--- gates ---")
    for k, v in (output.get("gates") or {}).items():
        marker = "PASS" if v else "FAIL"
        print(f"  [{marker}] {k}")
    rp = output.get("report_path")
    if rp:
        print()
        print(f"full report: {rp}")


def _cmd_explain(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="cas explain",
        description=(
            "Generate an English explanation of a CAS expression using the "
            "local Stage 3 checkpoint. Prints the generated English plus a "
            "small breakdown of which stage identifiers from the input were "
            "copied into the output, and the slot-type trace summary."
        ),
    )
    parser.add_argument(
        "expression",
        nargs="?",
        default=None,
        help="CAS expression to explain (required; quote it on the shell).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw output dict as JSON; suppress human-readable formatting.",
    )
    parser.add_argument(
        "--archive-root",
        type=str,
        default=None,
        help=(
            "Override the local archive root (default: D:\\tksCAS-archive\\). "
            "Used by tests + alternate install locations."
        ),
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=192,
        help="Greedy decode cap; default 192 (Stage 3 post-training eval value).",
    )
    parser.add_argument(
        "--no-save-report",
        action="store_true",
        help="Skip writing .tmp/cas_explain_<ts>.json.",
    )
    args = parser.parse_args(argv)

    if not args.expression or not args.expression.strip():
        print(
            "cas explain: expression required — pass a CAS expression as the "
            "first positional argument.",
            file=sys.stderr,
        )
        print(
            "Example: cas explain \"let stageA0_4_857 = ^7^P_{F5}; "
            "stageA0_4_857 -> stageA0_4_857\"",
            file=sys.stderr,
        )
        return 2

    expression = args.expression.strip()
    archive_root_path = Path(args.archive_root) if args.archive_root else None
    if archive_root_path is not None and not archive_root_path.exists():
        print(
            f"cas explain: archive root not found at {archive_root_path!s}. "
            f"The Stage 3 checkpoint and tokenizer artifacts are expected to "
            f"live there. See docs/working/candidate_e/"
            f"checkpoint_archive_registry.md for the layout.",
            file=sys.stderr,
        )
        return 2

    # Deferred imports — they pull torch + the loader chain.
    import json as _json
    import time as _time

    import torch

    from cas_native.inference.stage3_local_loader import load_stage3_local
    from cas_native.evaluation.evaluate_candidate_e_stage2 import (
        extract_identifiers_in_order,
    )
    from cas_native.evaluation.sample_decoder import decode_canary_pack
    from cas_native.training.datasets.simplex_collator import SimplexCollator

    t0 = _time.time()
    try:
        bundle = load_stage3_local(
            archive_root=archive_root_path, device="cpu",
        )
    except RuntimeError as exc:
        print(f"cas explain: failed to load Stage 3 checkpoint — {exc}", file=sys.stderr)
        return 2
    load_seconds = round(_time.time() - t0, 3)

    # Synthetic record in the shape decode_canary_pack expects. Field
    # names match the dev pack (`rpm_copy_grounding_v2_dev.jsonl`) so the
    # collator builds the cas_prefix exactly the way it did at training
    # time.
    #
    # reply_text is required by NativeNLCollator (line 169: it skips any
    # record where prompt_text or reply_text is empty), so we pass a
    # single-token placeholder. Greedy decode starts from BOS and grows
    # token-by-token regardless — the placeholder only sets up tensor
    # shapes for the collator's aux supervision, which we don't consume
    # at inference. eval_meta is intentionally minimal here — recovery
    # scoring comes from the input itself, not from a pre-baked target.
    synthetic_record = {
        "id": "explain_subcommand_input",
        "cas_expression": expression,
        "prompt_text": _explain_prompt_for_expression(expression),
        "reply_text": ".",
        "v1mix_task_type": "cas_to_english",
        "v1mix_grammar_category_or_error_class": "rpm_chain",
        "eval_meta": {"canonical_identifiers": []},
    }

    # Match the cap the Stage 3 model was TRAINED with (manifest stored
    # max_cas_prefix_len=192). The NativeNLCollator default is 32, which
    # silently truncates ~3+ stage RPM chains and drops later identifiers
    # before the model sees them. Read from manifest for forward
    # compatibility; fall back to 192 if absent. Per Codex re-audit
    # `40d5935` 2026-05-13.
    cas_prefix_cap = int(
        bundle.manifest.get("config", {}).get("max_cas_prefix_len", 192)
    )
    collator = SimplexCollator(
        bundle.tokenizer,
        enable_simplex_aux=True,
        max_cas_prefix_len=cas_prefix_cap,
    )
    device = torch.device("cpu")

    t1 = _time.time()
    try:
        decoded = decode_canary_pack(
            bundle.model, [synthetic_record], collator, bundle.tokenizer,
            device=device, max_new_tokens=args.max_new_tokens,
            hard_typed_emission=False, copy_confidence_threshold=0.5,
            truncate_traces=False,
        )
    except Exception as exc:  # decode errors should not crash the CLI
        print(f"cas explain: decode failed — {exc!r}", file=sys.stderr)
        return 2
    decode_seconds = round(_time.time() - t1, 3)

    entry = decoded[0] if decoded else {}
    generated_text = entry.get("generated_text", "") or ""
    slot_trace = entry.get("slot_type_trace", []) or []

    # Identifier extraction: pull the bounded-regex stage identifiers from
    # both input and output. Copied = intersection in expected order so
    # downstream consumers see a stable list. Missing preserves expected
    # order too.
    expected_idents = extract_identifiers_in_order(expression)
    emitted_idents = extract_identifiers_in_order(generated_text)
    emitted_set = set(emitted_idents)
    copied = [t for t in expected_idents if t in emitted_set]
    missing = [t for t in expected_idents if t not in emitted_set]
    coverage = (len(copied) / len(expected_idents)) if expected_idents else 0.0

    slot_summary = _explain_slot_trace_summary(list(slot_trace))

    timestamp_utc = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    output: dict[str, Any] = {
        "command": "cas explain",
        "version": 1,
        "timestamp_utc": timestamp_utc,
        "input_cas_expression": expression,
        "model": {
            "manifest_ablation_mode": bundle.manifest.get("ablation_mode"),
            "checkpoint_sha256": bundle.hash_report.get("ckpt_final.pt"),
            "load_seconds": load_seconds,
            "decode_seconds": decode_seconds,
        },
        "generated_english": generated_text,
        "n_tokens_generated": entry.get("n_tokens_generated"),
        "identifiers": {
            "expected": list(expected_idents),
            "emitted": list(emitted_idents),
            "copied": copied,
            "missing": missing,
            "coverage": coverage,
        },
        "slot_summary": slot_summary,
        "gates": {
            "no_crash": True,
            "generated_non_empty": bool(generated_text),
            "ge_one_identifier_copied": bool(copied),
        },
    }

    if not args.no_save_report:
        # tksCAS/.tmp/  — same convention as stage3_local_smoke.
        # _SCRIPT_DIR_PARENT structure: inference/ -> cas-native/ ->
        # noetic-compass/ -> noetic-compass-scaffold/ -> tksCAS/.
        repo_root = Path(__file__).resolve().parents[4]
        report_dir = repo_root / ".tmp"
        try:
            report_dir.mkdir(parents=True, exist_ok=True)
            ts = _time.strftime("%Y%m%dT%H%M%SZ", _time.gmtime())
            report_path = report_dir / f"cas_explain_{ts}.json"
            with report_path.open("w", encoding="utf-8") as f:
                _json.dump(output, f, indent=2, default=str)
            output["report_path"] = str(report_path)
        except OSError as exc:
            # Saving the side-report is best-effort — don't fail the CLI
            # over a write error, but surface the reason.
            print(
                f"cas explain: could not save report ({exc!r}); continuing.",
                file=sys.stderr,
            )

    if args.json:
        print(_json.dumps(output, indent=2, default=str))
    else:
        _print_explain_summary(output)

    # Gate: no-crash + non-empty generated text. Identifier copy is
    # informational at the CLI level (the user can see the breakdown);
    # zero-copy is not a CLI failure because the model could still produce
    # useful prose. Empty generation IS a failure — nothing to show.
    if not output["gates"]["generated_non_empty"]:
        return 2
    return 0


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
    "explain": _cmd_explain,
    "demo": _cmd_demo,
    "version": _cmd_version,
    "help": _cmd_help,
    "--help": _cmd_help,
    "-h": _cmd_help,
}

# Public alias — Step 4 spec named the dispatcher `COMMANDS`; the
# historical name in this file is `SUBCOMMANDS`. Bind both so external
# consumers (tests, docs, downstream tooling) can pick either.
COMMANDS = SUBCOMMANDS


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
