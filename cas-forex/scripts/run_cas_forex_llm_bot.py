"""Run the CAS Forex LLM Bot — natural-language operator interface.

The LLM-first bot routes every operator turn through a frontier model and lets
it call the 31 deterministic CAS Forex capabilities as tools. The deterministic
menu is still reachable by typing `menu`.

Providers:
    anthropic-direct  Direct Anthropic Messages API (DEFAULT).
                      Requires ANTHROPIC_API_KEY. Default model
                      `claude-sonnet-4-6`.
    vercel-gateway    Multi-provider routing via Vercel AI Gateway.
                      Requires AI_GATEWAY_API_KEY. Model strings are
                      `provider/model`, e.g. `anthropic/claude-sonnet-4-6`.

Usage:
    py -3.12 scripts/run_cas_forex_llm_bot.py
    py -3.12 scripts/run_cas_forex_llm_bot.py --provider vercel-gateway
    py -3.12 scripts/run_cas_forex_llm_bot.py --model claude-haiku-4-5-20251001
    py -3.12 scripts/run_cas_forex_llm_bot.py --api http://127.0.0.1:8765
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    _reconfigure = getattr(_stream, "reconfigure", None) if _stream is not None else None
    if callable(_reconfigure):
        try:
            _reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.cas_forex_llm_bot import (
    PROVIDER_ANTHROPIC_DIRECT,
    PROVIDER_VERCEL_GATEWAY,
    SUPPORTED_PROVIDERS,
    run_dry_run_cli,
    run_llm_bot_cli,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default=None,
        help=(
            "Which LLM provider path to use. "
            f"Defaults to {PROVIDER_ANTHROPIC_DIRECT} (direct Anthropic Claude Sonnet 4.6). "
            f"Use {PROVIDER_VERCEL_GATEWAY} for multi-provider routing via Vercel AI Gateway."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model identifier. For anthropic-direct use the Anthropic model "
            "name (default: claude-sonnet-4-6). For vercel-gateway use "
            "`provider/model` (e.g. anthropic/claude-sonnet-4-6)."
        ),
    )
    parser.add_argument("--api", default="http://127.0.0.1:8765", help="CAS Forex API base URL")
    parser.add_argument(
        "--mt5",
        default=r"C:\\Program Files\\Hugosway\\Hugosway PRO5 Terminal\\terminal64.exe",
        help="MT5 terminal64.exe path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Trace the full Stage 1->7 pipeline WITHOUT calling the LLM. "
            "Operator types `<key>` or `<key> <hint>`; the bot prints what each "
            "stage would do. No ANTHROPIC_API_KEY required."
        ),
    )
    parser.add_argument(
        "--actually-execute",
        action="store_true",
        help=(
            "Only meaningful with --dry-run. When set, Stage 4 dispatches "
            "deterministically via execute_capability and Stage 5 prompts for "
            "real operator confirmation. Default: trace-only (no execution)."
        ),
    )
    args = parser.parse_args()

    if args.dry_run:
        run_dry_run_cli(
            api_base=args.api,
            mt5_path=args.mt5,
            actually_execute=args.actually_execute,
        )
        return 0

    if args.actually_execute:
        parser.error("--actually-execute is only valid with --dry-run")

    run_llm_bot_cli(
        provider=args.provider,
        model=args.model,
        api_base=args.api,
        mt5_path=args.mt5,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
