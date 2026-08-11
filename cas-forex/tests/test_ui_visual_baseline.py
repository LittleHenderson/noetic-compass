from __future__ import annotations

import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

from cas_forex.ui_visual_baseline import (
    build_visual_baseline_manifest,
    compare_visual_baseline,
    write_visual_baseline_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_visual_baseline_manifest_records_screenshot_fingerprints(tmp_path: Path):
    report_path = _write_smoke_report(tmp_path, color=(20, 80, 140))

    manifest = build_visual_baseline_manifest(source_report_path=report_path, root=tmp_path)

    assert manifest["report_kind"] == "cas_forex_ui_visual_baseline_manifest"
    assert manifest["screenshot_count"] == 1
    assert manifest["grid_width"] == 24
    assert manifest["grid_height"] == 16
    assert "does not call trading actions" in manifest["claim_boundary"]
    entry = manifest["entries"][0]
    assert entry["key"] == "proof::desktop"
    assert entry["width"] == 8
    assert entry["height"] == 6
    assert len(entry["visual_grid"]) == 24 * 16
    assert entry["screenshot_path"] == "screens/proof-desktop.png"


def test_visual_baseline_compare_accepts_matching_current_report(tmp_path: Path):
    report_path = _write_smoke_report(tmp_path, color=(20, 80, 140))
    baseline_path = tmp_path / "baseline.json"
    write_visual_baseline_manifest(
        source_report_path=report_path,
        baseline_path=baseline_path,
        root=tmp_path,
    )

    diff = compare_visual_baseline(
        source_report_path=report_path,
        baseline_path=baseline_path,
        root=tmp_path,
        max_mean_delta=0,
    )

    assert diff["report_kind"] == "cas_forex_ui_visual_baseline_diff"
    assert diff["status"] == "OK"
    assert diff["attention_count"] == 0
    assert diff["diffs"][0]["status"] == "OK"


def test_visual_baseline_compare_flags_visual_drift(tmp_path: Path):
    report_path = _write_smoke_report(tmp_path, color=(20, 80, 140))
    baseline_path = tmp_path / "baseline.json"
    write_visual_baseline_manifest(
        source_report_path=report_path,
        baseline_path=baseline_path,
        root=tmp_path,
    )
    _write_png(tmp_path / "screens" / "proof-desktop.png", width=8, height=6, color=(240, 240, 240))

    diff = compare_visual_baseline(
        source_report_path=report_path,
        baseline_path=baseline_path,
        root=tmp_path,
        max_mean_delta=1,
    )

    assert diff["status"] == "ATTENTION"
    assert diff["attention_count"] == 1
    assert diff["diffs"][0]["status"] == "VISUAL_DRIFT"


def test_visual_baseline_compare_flags_dimension_mismatch(tmp_path: Path):
    report_path = _write_smoke_report(tmp_path, color=(20, 80, 140))
    baseline_path = tmp_path / "baseline.json"
    write_visual_baseline_manifest(
        source_report_path=report_path,
        baseline_path=baseline_path,
        root=tmp_path,
    )
    _write_png(tmp_path / "screens" / "proof-desktop.png", width=10, height=6, color=(20, 80, 140))

    diff = compare_visual_baseline(
        source_report_path=report_path,
        baseline_path=baseline_path,
        root=tmp_path,
    )

    assert diff["status"] == "ATTENTION"
    assert diff["diffs"][0]["status"] == "DIMENSION_MISMATCH"


def test_visual_baseline_cli_writes_and_compares(tmp_path: Path):
    report_path = _write_smoke_report(tmp_path, color=(20, 80, 140))
    baseline_path = tmp_path / "baseline.json"

    write_result = subprocess.run(
        [
            sys.executable,
            "scripts/run_ui_visual_baseline.py",
            "--source-report",
            str(report_path),
            "--baseline",
            str(baseline_path),
            "--write-baseline",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    write_payload = json.loads(write_result.stdout)
    assert write_payload["report_kind"] == "cas_forex_ui_visual_baseline_manifest"
    assert baseline_path.exists()

    compare_result = subprocess.run(
        [
            sys.executable,
            "scripts/run_ui_visual_baseline.py",
            "--source-report",
            str(report_path),
            "--baseline",
            str(baseline_path),
            "--json",
            "--exit-code-on-failure",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    compare_payload = json.loads(compare_result.stdout)
    assert compare_payload["report_kind"] == "cas_forex_ui_visual_baseline_diff"
    assert compare_payload["status"] == "OK"


def _write_smoke_report(tmp_path: Path, *, color: tuple[int, int, int]) -> Path:
    screen_dir = tmp_path / "screens"
    screen_dir.mkdir()
    _write_png(screen_dir / "proof-desktop.png", width=8, height=6, color=color)
    report_path = tmp_path / "ui_browser_zoom_smoke_report.json"
    report_path.write_text(
        json.dumps(
            {
                "report_kind": "cas_forex_ui_browser_zoom_smoke",
                "status": "OK",
                "screenshots": [
                    {
                        "page": "proof",
                        "profile": "desktop",
                        "success": True,
                        "width": 8,
                        "height": 6,
                        "screenshot_path": "screens/proof-desktop.png",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return report_path


def _write_png(path: Path, *, width: int, height: int, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scanline = bytes((*color, 255) * width)
    raw = b"".join(b"\x00" + scanline for _ in range(height))
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(raw))
    png += _chunk(b"IEND", b"")
    path.write_bytes(png)


def _chunk(kind: bytes, data: bytes) -> bytes:
    import zlib as _zlib

    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", _zlib.crc32(kind + data) & 0xFFFFFFFF)
