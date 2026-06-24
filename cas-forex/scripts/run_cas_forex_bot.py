"""Run the CAS Forex Bot — structured conversational agent for all CAS Forex operations.

Usage:
    py -3.12 scripts/run_cas_forex_bot.py
    py -3.12 scripts/run_cas_forex_bot.py --api http://127.0.0.1:8765
    py -3.12 scripts/run_cas_forex_bot.py --mt5 "C:\\Program Files\\Hugosway\\Hugosway PRO5 Terminal\\terminal64.exe"

The bot presents:
- A current status summary on startup
- 7 action groups (status, workflow, mt5, proof, strategy, owner, system)
- Numbered/key-prefixed commands within each group
- Confirmation gates for MT5 demo orders
- Shows the underlying commands so you learn the system
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

from cas_forex.cas_forex_bot import BotState, run_bot_cli


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8765", help="API base URL")
    parser.add_argument(
        "--mt5",
        default=r"C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe",
        help="MT5 terminal64.exe path",
    )
    args = parser.parse_args()

    # Set up state before running
    import cas_forex.cas_forex_bot as bot_module

    # Override defaults
    bot_module.BotState.mt5_path = args.mt5
    bot_module.BotState.api_base = args.api

    print("CAS Forex Bot — type 'h' for all commands, 'q' to quit")
    print(f"API: {args.api}")
    print(f"MT5: {args.mt5}")
    print()

    run_bot_cli()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
