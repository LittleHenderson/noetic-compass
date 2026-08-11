"""Bounded reverse readers for append-only JSONL runtime evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def read_jsonl_tail(
    path: Path | str,
    *,
    limit: int,
    chunk_size: int = 64 * 1024,
) -> list[dict[str, Any]]:
    """Return the newest valid JSON objects without reading the whole file.

    Runtime audit logs can reach hundreds of megabytes. Reading backward keeps
    request memory and disk work proportional to the requested evidence tail.
    Results are returned in chronological order.
    """

    target = Path(path)
    wanted = max(1, int(limit))
    block_size = max(4096, int(chunk_size))
    if not target.exists():
        return []

    records: list[dict[str, Any]] = []
    try:
        with target.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell()
            remainder = b""
            while position > 0 and len(records) < wanted:
                read_size = min(block_size, position)
                position -= read_size
                handle.seek(position)
                block = handle.read(read_size) + remainder
                parts = block.split(b"\n")
                remainder = parts[0]
                for raw_line in reversed(parts[1:]):
                    payload = _parse_mapping(raw_line)
                    if payload is not None:
                        records.append(payload)
                        if len(records) >= wanted:
                            break
            if position == 0 and len(records) < wanted:
                payload = _parse_mapping(remainder)
                if payload is not None:
                    records.append(payload)
    except (OSError, MemoryError):
        return []
    return list(reversed(records[:wanted]))


def _parse_mapping(raw_line: bytes) -> dict[str, Any] | None:
    line = raw_line.strip()
    if not line:
        return None
    try:
        payload = json.loads(line.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return dict(payload) if isinstance(payload, Mapping) else None
