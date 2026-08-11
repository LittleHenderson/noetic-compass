from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cas_forex.ui_browser_zoom_smoke import run_ui_browser_zoom_smoke


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ui_browser_zoom_smoke_dry_run_plans_all_pages_and_profiles():
    report = run_ui_browser_zoom_smoke(root=REPO_ROOT, dry_run=True)

    assert report["report_kind"] == "cas_forex_ui_browser_zoom_smoke"
    assert report["status"] == "DRY_RUN"
    assert report["page_count"] >= 20
    assert report["profile_count"] == 3
    assert report["screenshot_count"] == report["page_count"] * report["profile_count"]
    assert report["failed"] == 0
    assert "does not call trading actions" in report["claim_boundary"]

    profiles = {item["profile"] for item in report["screenshots"]}
    assert profiles == {"desktop", "desktop_zoom_150_effective", "phone"}


def test_ui_browser_zoom_smoke_dry_run_can_limit_pages_and_profiles():
    report = run_ui_browser_zoom_smoke(
        root=REPO_ROOT,
        pages=("proof", "settings"),
        profiles=("desktop_zoom_150_effective",),
        dry_run=True,
    )

    assert report["page_count"] == 2
    assert report["profile_count"] == 1
    assert report["screenshot_count"] == 2
    assert [item["page"] for item in report["screenshots"]] == ["proof", "settings"]
    assert {item["profile"] for item in report["screenshots"]} == {"desktop_zoom_150_effective"}


def test_ui_browser_zoom_smoke_cli_dry_run_json_exits_cleanly():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_ui_browser_zoom_smoke.py",
            "--dry-run",
            "--pages",
            "proof,settings",
            "--profiles",
            "desktop,phone",
            "--json",
            "--exit-code-on-failure",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)

    assert payload["report_kind"] == "cas_forex_ui_browser_zoom_smoke"
    assert payload["status"] == "DRY_RUN"
    assert payload["screenshot_count"] == 4
