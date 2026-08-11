"""Visual baseline manifest and diff checks for CAS Forex UI screenshots."""

from __future__ import annotations

import json
import struct
import time
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_ui_visual_baseline_diff"
BASELINE_KIND = "cas_forex_ui_visual_baseline_manifest"
DEFAULT_BASELINE_PATH = REPO_ROOT / "ui" / "visual_baselines" / "cas_forex_ui_browser_zoom_baseline.json"
CLAIM_BOUNDARY = (
    "UI visual baseline diff compares local browser screenshots against a "
    "source-controlled visual fingerprint manifest. It is observational only: "
    "it does not call trading actions, place orders, close positions, move "
    "money, change settings, authorize live trading, or promise returns."
)
GRID_WIDTH = 24
GRID_HEIGHT = 16
DEFAULT_MAX_MEAN_DELTA = 28.0


@dataclass(frozen=True)
class VisualEntry:
    key: str
    page: str
    profile: str
    width: int
    height: int
    bytes: int
    sha256: str
    visual_grid: tuple[int, ...]
    screenshot_path: str


@dataclass(frozen=True)
class VisualDiffRow:
    key: str
    status: str
    detail: str
    mean_delta: float | None = None
    baseline_width: int | None = None
    baseline_height: int | None = None
    current_width: int | None = None
    current_height: int | None = None
    baseline_bytes: int | None = None
    current_bytes: int | None = None


def write_visual_baseline_manifest(
    *,
    source_report_path: Path | str,
    baseline_path: Path | str = DEFAULT_BASELINE_PATH,
    root: Path | str | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    source_path = _resolve_path(source_report_path, base)
    baseline = build_visual_baseline_manifest(source_report_path=source_path, root=base)
    target = Path(baseline_path)
    if not target.is_absolute():
        target = base / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return baseline | {"baseline_path": str(target)}


def build_visual_baseline_manifest(
    *,
    source_report_path: Path | str,
    root: Path | str | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    source_path = _resolve_path(source_report_path, base)
    source_report = _read_json(source_path)
    entries = _entries_from_smoke_report(source_report, source_path=source_path, root=base)
    return {
        "report_kind": BASELINE_KIND,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_report_path": _display_path(source_path, base),
        "grid_width": GRID_WIDTH,
        "grid_height": GRID_HEIGHT,
        "screenshot_count": len(entries),
        "entries": [asdict(entry) for entry in entries],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def compare_visual_baseline(
    *,
    source_report_path: Path | str,
    baseline_path: Path | str = DEFAULT_BASELINE_PATH,
    root: Path | str | None = None,
    max_mean_delta: float = DEFAULT_MAX_MEAN_DELTA,
) -> dict[str, Any]:
    started = time.perf_counter()
    base = Path(root) if root is not None else REPO_ROOT
    source_path = _resolve_path(source_report_path, base)
    baseline_resolved = _resolve_path(baseline_path, base)
    baseline = _read_json(baseline_resolved)
    current_manifest = build_visual_baseline_manifest(source_report_path=source_path, root=base)
    baseline_entries = {_entry_key(row): row for row in _rows(baseline.get("entries"))}
    current_entries = {_entry_key(row): row for row in _rows(current_manifest.get("entries"))}

    diff_rows: list[VisualDiffRow] = []
    for key, baseline_entry in sorted(baseline_entries.items()):
        current_entry = current_entries.get(key)
        if current_entry is None:
            diff_rows.append(VisualDiffRow(key=key, status="MISSING_CURRENT", detail="Current screenshot is missing."))
            continue
        dimension_mismatch = (
            baseline_entry.get("width") != current_entry.get("width")
            or baseline_entry.get("height") != current_entry.get("height")
        )
        mean_delta = _mean_abs_delta(
            _int_list(baseline_entry.get("visual_grid")),
            _int_list(current_entry.get("visual_grid")),
        )
        if dimension_mismatch:
            status = "DIMENSION_MISMATCH"
            detail = "Screenshot dimensions changed."
        elif mean_delta is None:
            status = "GRID_MISMATCH"
            detail = "Visual fingerprint grids are incompatible."
        elif mean_delta > max_mean_delta:
            status = "VISUAL_DRIFT"
            detail = f"Mean visual delta {mean_delta:.2f} exceeds threshold {max_mean_delta:.2f}."
        else:
            status = "OK"
            detail = "Within visual baseline threshold."
        diff_rows.append(
            VisualDiffRow(
                key=key,
                status=status,
                detail=detail,
                mean_delta=round(mean_delta, 4) if mean_delta is not None else None,
                baseline_width=_int_or_none(baseline_entry.get("width")),
                baseline_height=_int_or_none(baseline_entry.get("height")),
                current_width=_int_or_none(current_entry.get("width")),
                current_height=_int_or_none(current_entry.get("height")),
                baseline_bytes=_int_or_none(baseline_entry.get("bytes")),
                current_bytes=_int_or_none(current_entry.get("bytes")),
            )
        )

    for key in sorted(set(current_entries) - set(baseline_entries)):
        current_entry = current_entries[key]
        diff_rows.append(
            VisualDiffRow(
                key=key,
                status="MISSING_BASELINE",
                detail="Current screenshot has no baseline entry.",
                current_width=_int_or_none(current_entry.get("width")),
                current_height=_int_or_none(current_entry.get("height")),
                current_bytes=_int_or_none(current_entry.get("bytes")),
            )
        )

    failures = [row for row in diff_rows if row.status != "OK"]
    return {
        "report_kind": REPORT_KIND,
        "status": "OK" if not failures else "ATTENTION",
        "baseline_path": str(baseline_resolved),
        "source_report_path": str(source_path),
        "baseline_count": len(baseline_entries),
        "current_count": len(current_entries),
        "ok_count": len(diff_rows) - len(failures),
        "attention_count": len(failures),
        "max_mean_delta": max_mean_delta,
        "elapsed_ms": (time.perf_counter() - started) * 1000.0,
        "diffs": [asdict(row) for row in diff_rows],
        "top_attention_items": [f"{row.key}: {row.detail}" for row in failures[:8]],
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _entries_from_smoke_report(
    source_report: Mapping[str, Any],
    *,
    source_path: Path,
    root: Path,
) -> tuple[VisualEntry, ...]:
    entries: list[VisualEntry] = []
    for row in _rows(source_report.get("screenshots")):
        if not row.get("success"):
            continue
        screenshot_path = _resolve_screenshot_path(row.get("screenshot_path"), source_path=source_path, root=root)
        if not screenshot_path.exists():
            continue
        signature = _image_signature(screenshot_path)
        page = str(row.get("page") or "")
        profile = str(row.get("profile") or "")
        key = _make_key(page, profile)
        entries.append(
            VisualEntry(
                key=key,
                page=page,
                profile=profile,
                width=signature["width"],
                height=signature["height"],
                bytes=signature["bytes"],
                sha256=signature["sha256"],
                visual_grid=tuple(signature["visual_grid"]),
                screenshot_path=_display_path(screenshot_path, root),
            )
        )
    return tuple(sorted(entries, key=lambda item: item.key))


def _image_signature(path: Path) -> dict[str, Any]:
    width, height, rows, channels, color_type = _read_png_rows(path)
    grid: list[int] = []
    for gy in range(GRID_HEIGHT):
        y = min(height - 1, int((gy + 0.5) * height / GRID_HEIGHT))
        row = rows[y]
        for gx in range(GRID_WIDTH):
            x = min(width - 1, int((gx + 0.5) * width / GRID_WIDTH))
            grid.append(_luma(row, x, channels=channels, color_type=color_type))
    data = path.read_bytes()
    return {
        "width": width,
        "height": height,
        "bytes": len(data),
        "sha256": sha256(data).hexdigest(),
        "visual_grid": grid,
    }


def _read_png_rows(path: Path) -> tuple[int, int, list[bytes], int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")
    offset = 8
    width = height = bit_depth = color_type = None
    idat_parts: list[bytes] = []
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk[:10])
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk)
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or bit_depth != 8 or color_type not in {0, 2, 4, 6}:
        raise ValueError(f"{path} has unsupported PNG format")
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    bpp = channels
    stride = width * channels
    raw = zlib.decompress(b"".join(idat_parts))
    rows: list[bytes] = []
    previous = bytearray(stride)
    pos = 0
    for _ in range(height):
        filter_type = raw[pos]
        pos += 1
        scanline = bytearray(raw[pos : pos + stride])
        pos += stride
        _unfilter_scanline(scanline, previous, filter_type=filter_type, bpp=bpp)
        rows.append(bytes(scanline))
        previous = scanline
    return width, height, rows, channels, color_type


def _unfilter_scanline(scanline: bytearray, previous: bytearray, *, filter_type: int, bpp: int) -> None:
    for index, value in enumerate(scanline):
        left = scanline[index - bpp] if index >= bpp else 0
        up = previous[index]
        upper_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 0:
            recon = value
        elif filter_type == 1:
            recon = value + left
        elif filter_type == 2:
            recon = value + up
        elif filter_type == 3:
            recon = value + ((left + up) // 2)
        elif filter_type == 4:
            recon = value + _paeth(left, up, upper_left)
        else:
            raise ValueError(f"Unsupported PNG filter {filter_type}")
        scanline[index] = recon & 0xFF


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _luma(row: bytes, x: int, *, channels: int, color_type: int) -> int:
    i = x * channels
    if color_type == 0:
        r = g = b = row[i]
    elif color_type == 2:
        r, g, b = row[i], row[i + 1], row[i + 2]
    elif color_type == 4:
        r = g = b = row[i]
    else:
        r, g, b = row[i], row[i + 1], row[i + 2]
    return int((0.2126 * r) + (0.7152 * g) + (0.0722 * b))


def _resolve_screenshot_path(value: Any, *, source_path: Path, root: Path) -> Path:
    raw = Path(str(value or ""))
    if raw.is_absolute():
        return raw
    candidate = source_path.parent / raw
    if candidate.exists():
        return candidate
    return root / raw


def _resolve_path(path: Path | str, root: Path) -> Path:
    raw = Path(path)
    return raw if raw.is_absolute() else root / raw


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []


def _entry_key(row: Mapping[str, Any]) -> str:
    key = row.get("key")
    if isinstance(key, str) and key:
        return key
    return _make_key(str(row.get("page") or ""), str(row.get("profile") or ""))


def _make_key(page: str, profile: str) -> str:
    return f"{page}::{profile}"


def _int_list(value: Any) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [int(item) for item in value]


def _mean_abs_delta(left: Sequence[int], right: Sequence[int]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    return sum(abs(int(a) - int(b)) for a, b in zip(left, right)) / len(left)


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None
