"""Run the single-owner CAS Forex API with an explicit Windows loop policy."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _windows_selector_loop_factory(
    use_subprocess: bool = False,
) -> asyncio.AbstractEventLoop:
    """Give Uvicorn a selector loop instead of its Windows Proactor default."""

    _ = use_subprocess
    return asyncio.SelectorEventLoop()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CAS Forex FastAPI server.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host.")
    parser.add_argument("--port", type=int, default=8765, help="Bind port.")
    parser.add_argument("--log-level", default="info", help="Uvicorn log level.")
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("CAS_FOREX_API_WORKERS", "1")),
        help=(
            "Stateful API worker count. CAS currently requires exactly 1; LAN and "
            "phone clients share that single autonomous runtime owner."
        ),
    )
    parser.add_argument(
        "--windows-event-loop",
        choices=("proactor", "selector"),
        default=os.environ.get("CAS_FOREX_WINDOWS_EVENT_LOOP", "proactor").lower(),
        help=(
            "Windows asyncio policy. Proactor is the default because it remains "
            "responsive when machine-wide port-proxy listeners exhaust selector "
            "socket buffers; use selector only as an explicit compatibility fallback."
        ),
    )
    return parser.parse_args(argv)


def _uvicorn_loop_spec(mode: str, *, platform_name: str | None = None) -> str:
    platform = platform_name or os.name
    if platform != "nt":
        return "asyncio"
    if str(mode).strip().lower() == "selector":
        return "scripts.run_api_server:_windows_selector_loop_factory"
    return "asyncio"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    from cas_forex.runtime_topology import RuntimeTopologyError, validate_api_worker_count

    try:
        workers = validate_api_worker_count(args.workers)
    except RuntimeTopologyError as exc:
        print(f"CAS Forex API refused unsafe process topology: {exc}", file=sys.stderr)
        return 2
    os.environ["CAS_FOREX_API_EFFECTIVE_WORKERS"] = str(workers)
    os.environ["CAS_FOREX_API_HOST"] = str(args.host)
    os.environ["CAS_FOREX_API_PORT"] = str(args.port)
    loop_spec = _uvicorn_loop_spec(args.windows_event_loop)
    os.environ["CAS_FOREX_API_EVENT_LOOP"] = (
        str(args.windows_event_loop).upper() if os.name == "nt" else "ASYNCIO"
    )

    import uvicorn

    uvicorn.run(
        "api.server:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        workers=workers,
        loop=loop_spec,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
