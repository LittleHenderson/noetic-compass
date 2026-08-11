from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from api import server as api_server
from api.routes import settings as settings_route
from cas_forex.economic_calendar_feed import build_economic_calendar_feed_report
from ui_contract import assert_panel_wired


def _cfg(tmp_path: Path, **overrides):
    base = {
        "economic_calendar_feed_url": None,
        "economic_calendar_feed_path": None,
        "economic_calendar_cache_path": str(tmp_path / "calendar-cache.json"),
        "economic_calendar_ttl_seconds": 900,
        "economic_calendar_timeout_seconds": 1.5,
        "economic_calendar_fail_closed": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_economic_calendar_feed_reports_unconfigured_without_events(tmp_path):
    report = build_economic_calendar_feed_report(config=_cfg(tmp_path), root=tmp_path)

    assert report["report_kind"] == "cas_forex_economic_calendar_feed"
    assert report["status"] == "UNCONFIGURED"
    assert report["configured"] is False
    assert report["event_count"] == 0
    assert "does not place orders" in report["claim_boundary"]


def test_economic_calendar_feed_loads_json_file_and_normalizes_events(tmp_path):
    feed_path = tmp_path / "calendar.json"
    feed_path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "id": "nfp-1",
                        "event": "Non Farm Payrolls",
                        "currency": "USD",
                        "impact": "high",
                        "scheduled_at_utc": "2026-07-08T12:30:00Z",
                    },
                    {"event": "missing time", "impact": "HIGH"},
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_economic_calendar_feed_report(
        config=_cfg(tmp_path, economic_calendar_feed_path=str(feed_path)),
        root=tmp_path,
    )

    assert report["status"] == "LOADED"
    assert report["configured"] is True
    assert report["event_count"] == 1
    assert report["raw_event_count"] == 2
    assert report["unusable_event_count"] == 1
    event = report["events"][0]
    assert event["event_id"] == "nfp-1"
    assert event["event_type"] == "NFP"
    assert event["impact"] == "HIGH"
    assert event["scheduled_at_utc"] == "2026-07-08T12:30:00+00:00"


def test_economic_calendar_feed_uses_fresh_cache_without_refetch(tmp_path):
    feed_path = tmp_path / "calendar.json"
    feed_path.write_text(
        json.dumps(
            [
                {
                    "event": "CPI",
                    "currency": "USD",
                    "impact": "HIGH",
                    "scheduled_at_utc": "2026-07-08T12:30:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )
    cfg = _cfg(tmp_path, economic_calendar_feed_path=str(feed_path))
    first = build_economic_calendar_feed_report(config=cfg, root=tmp_path)
    feed_path.write_text("not valid json now", encoding="utf-8")

    second = build_economic_calendar_feed_report(config=cfg, root=tmp_path)

    assert first["status"] == "LOADED"
    assert second["status"] == "CACHE_FRESH"
    assert second["event_count"] == 1
    assert second["events"][0]["event_type"] == "CPI"


def test_economic_calendar_feed_uses_stale_cache_when_refresh_fails(tmp_path):
    feed_path = tmp_path / "calendar.json"
    feed_path.write_text(
        json.dumps(
            [
                {
                    "event": "FOMC Rate Decision",
                    "currency": "USD",
                    "impact": "HIGH",
                    "scheduled_at_utc": "2026-07-08T18:00:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )
    cfg = _cfg(tmp_path, economic_calendar_feed_path=str(feed_path), economic_calendar_ttl_seconds=1)
    first = build_economic_calendar_feed_report(config=cfg, root=tmp_path)
    cache_path = Path(first["cache_path"])
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    cached["written_at_epoch"] = 1
    cache_path.write_text(json.dumps(cached), encoding="utf-8")
    feed_path.write_text("{broken", encoding="utf-8")

    second = build_economic_calendar_feed_report(config=cfg, root=tmp_path, refresh=True)

    assert second["status"] == "CACHE_STALE"
    assert second["cache_stale"] is True
    assert second["event_count"] == 1
    assert "Feed refresh failed" in second["detail"]


def test_economic_calendar_feed_supports_injected_http_transport(tmp_path):
    payload = json.dumps(
        {
            "data": [
                {
                    "title": "US CPI",
                    "currency": "USD",
                    "importance": "high",
                    "scheduled_at": "2026-07-08T12:30:00+00:00",
                }
            ]
        }
    )
    calls: list[tuple[str, float]] = []

    def transport(url: str, timeout: float) -> str:
        calls.append((url, timeout))
        return payload

    report = build_economic_calendar_feed_report(
        config=_cfg(tmp_path, economic_calendar_feed_url="https://calendar.example.test/feed.json"),
        root=tmp_path,
        transport=transport,
    )

    assert report["status"] == "LOADED"
    assert report["source"] == "https://calendar.example.test/feed.json"
    assert report["event_count"] == 1
    assert report["events"][0]["event_type"] == "CPI"
    assert calls == [("https://calendar.example.test/feed.json", 1.5)]


def test_economic_calendar_settings_route_is_cache_first_and_read_only(monkeypatch):
    captured: dict[str, object] = {}

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

    body = asyncio.run(settings_route.get_economic_calendar())

    assert captured == {
        "key": "settings_economic_calendar",
        "builder_callable": True,
        "ttl_seconds": 30.0,
        "block_on_cold": False,
    }
    assert body["report_kind"] == "cas_forex_economic_calendar_feed"
    assert body["status"] == "WARMING"
    assert "does not place orders" in body["claim_boundary"]
    assert api_server._should_trace_request("GET", "/api/forex/settings/economic-calendar") is False


def test_economic_calendar_settings_ui_and_api_client_are_wired():
    settings_page = (Path(__file__).resolve().parents[1] / "ui" / "src" / "pages" / "SettingsPage.tsx").read_text(encoding="utf-8")
    api_client = (Path(__file__).resolve().parents[1] / "ui" / "src" / "data" / "api.ts").read_text(encoding="utf-8")

    assert_panel_wired("EconomicCalendarPanel")
    # Moved to components/settings/OpsPanels.tsx in the settings decomposition (slice 2).
    extracted_opspanels = (Path(__file__).resolve().parents[1] / "ui" / "src" / "components" / "settings" / "OpsPanels.tsx").read_text(encoding="utf-8")
    assert "Economic Calendar Feed" in extracted_opspanels
    assert "fetchEconomicCalendarFeed" in extracted_opspanels
    assert "EconomicCalendarFeedReport" in api_client
    assert '"/settings/economic-calendar"' in api_client
