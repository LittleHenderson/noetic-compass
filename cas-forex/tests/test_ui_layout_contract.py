from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from api.routes import settings as settings_route
from cas_forex.ui_layout_contract import build_ui_layout_contract
from ui_contract import assert_panel_wired


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ui_layout_contract_covers_zoom_sensitive_shell_and_operator_dropdown():
    report = build_ui_layout_contract(REPO_ROOT)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert report["report_kind"] == "cas_forex_ui_layout_zoom_contract"
    assert report["status"] == "OK"
    assert report["route_count"] >= 20
    assert report["missing_page_routes"] == []
    assert report["css_zoom_violations"] == []
    assert "does not render pages" in report["claim_boundary"]

    assert checks["shell_nav_zoom_collapse"]["status"] == "OK"
    assert "ui/src/components/Shell.tsx" in checks["shell_nav_zoom_collapse"]["evidence"]
    assert checks["operator_dropdown_viewport_guard"]["status"] == "OK"
    assert "ui/src/components/OperatorBadge.css" in checks["operator_dropdown_viewport_guard"]["evidence"]
    assert checks["operator_chat_opens_at_composer"]["status"] == "OK"
    assert "chat composer" in checks["operator_chat_opens_at_composer"]["detail"]
    assert checks["global_viewport_box_model"]["status"] == "OK"
    assert checks["visual_baseline_diff_runner_available"]["status"] == "OK"
    assert "cas_forex/ui_visual_baseline.py" in checks["visual_baseline_diff_runner_available"]["evidence"]


def test_ui_layout_contract_route_is_cache_first_and_read_only(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_cache_first_payload(key, *, builder, fallback, ttl_seconds, block_on_cold):
        captured.update(
            {
                "key": key,
                "builder_callable": callable(builder),
                "ttl_seconds": ttl_seconds,
                "block_on_cold": block_on_cold,
            }
        )
        return fallback()

    monkeypatch.setattr(settings_route, "cache_first_payload", fake_cache_first_payload)

    body = asyncio.run(settings_route.get_ui_layout_contract())

    assert captured == {
        "key": "settings_ui_layout_contract",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_ui_layout_zoom_contract"
    assert body["status"] == "WARMING"
    assert "does not render pages" in body["claim_boundary"]


def test_ui_layout_contract_settings_ui_and_api_client_are_wired():
    settings_page = (REPO_ROOT / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (REPO_ROOT / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("UILayoutContractPanel")
    assert "UI Layout Contract" in settings_page
    assert "browser-zoom regressions" in settings_page
    assert "fetchUILayoutContract" in settings_page
    assert "UILayoutContractReport" in api_client
    assert '"/settings/ui-layout-contract"' in api_client


def test_ui_layout_contract_cli_json_exits_cleanly():
    result = subprocess.run(
        [sys.executable, "scripts/run_ui_layout_contract.py", "--json", "--exit-code-on-attention"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)

    assert payload["report_kind"] == "cas_forex_ui_layout_zoom_contract"
    assert payload["status"] == "OK"
    assert payload["attention_count"] == 0
