from api import route_cache
from api.route_cache import _CACHES, cache_first_payload, cached_payload_snapshot, invalidate_cache
from api import live_money_cache


def test_cache_first_payload_can_block_on_cold(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    _CACHES.pop("unit-block-on-cold", None)
    calls: list[str] = []

    def builder():
        calls.append("build")
        return {"report_kind": "unit_report", "value": 42}

    def fallback():
        return {"report_kind": "unit_report", "value": "fallback"}

    payload = cache_first_payload(
        "unit-block-on-cold",
        builder=builder,
        fallback=fallback,
        ttl_seconds=60.0,
        block_on_cold=True,
    )

    assert payload["value"] == 42
    assert payload["cache_status"] == "fresh"
    assert calls == ["build"]


def test_invalidate_cache_drops_named_keys_only():
    _CACHES.clear()
    _CACHES["keep"] = {"payload": {"value": "keep"}}
    _CACHES["drop"] = {"payload": {"value": "drop"}}

    invalidate_cache("drop", "missing")

    assert "drop" not in _CACHES
    assert _CACHES["keep"]["payload"]["value"] == "keep"


def test_invalidate_cache_without_keys_clears_all():
    _CACHES.clear()
    _CACHES["one"] = {"payload": {"value": 1}}
    _CACHES["two"] = {"payload": {"value": 2}}

    invalidate_cache()

    assert _CACHES == {}


def test_cached_payload_snapshot_returns_copy_without_starting_refresh():
    _CACHES.clear()
    _CACHES["snapshot"] = {
        "payload": {"value": 7},
        "built_at": 100.0,
        "building": False,
        "error": None,
        "refresh_started_at": 0.0,
    }

    packet = cached_payload_snapshot("snapshot", ttl_seconds=60.0)

    assert packet is not None
    assert packet["value"] == 7
    assert packet["cache_status"] in {"fresh", "stale"}
    packet["value"] = "changed"
    assert _CACHES["snapshot"]["payload"]["value"] == 7


def test_start_cache_refresh_builds_packet_through_background_timer(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    _CACHES.pop("unit-prewarm", None)
    intervals: list[float] = []

    class ImmediateTimer:
        name = ""
        daemon = False

        def __init__(self, interval, target, args=()):
            intervals.append(interval)
            self._target = target
            self._args = args

        def start(self):
            self._target(*self._args)

    monkeypatch.setattr(route_cache.threading, "Timer", ImmediateTimer)

    started = route_cache.start_cache_refresh("unit-prewarm", lambda: {"value": 99})

    assert started is True
    assert intervals == [0.2]
    assert _CACHES["unit-prewarm"]["payload"]["value"] == 99
    assert _CACHES["unit-prewarm"]["building"] is False


def test_start_cache_refresh_accepts_custom_delay(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    _CACHES.pop("unit-delayed-prewarm", None)
    intervals: list[float] = []

    class CapturingTimer:
        name = ""
        daemon = False

        def __init__(self, interval, target, args=()):
            intervals.append(interval)
            self._target = target
            self._args = args

        def start(self):
            return None

    monkeypatch.setattr(route_cache.threading, "Timer", CapturingTimer)

    started = route_cache.start_cache_refresh(
        "unit-delayed-prewarm",
        lambda: {"value": "delayed"},
        delay_seconds=1.0,
    )

    assert started is True
    assert intervals == [1.0]
    assert _CACHES["unit-delayed-prewarm"]["building"] is True
    assert _CACHES["unit-delayed-prewarm"]["payload"] is None


def test_start_cache_refresh_skips_key_already_building():
    _CACHES["unit-busy"] = {
        "payload": None,
        "built_at": 0.0,
        "building": True,
        "error": None,
        "refresh_started_at": 1.0,
    }

    started = route_cache.start_cache_refresh("unit-busy", lambda: {"value": "ignored"})

    assert started is False
    assert _CACHES["unit-busy"]["payload"] is None


def test_live_money_gate_invalidation_clears_route_and_authorization_caches(monkeypatch):
    captured: dict[str, object] = {}

    def fake_invalidate_cache(*keys: str) -> None:
        captured["keys"] = keys

    def fake_invalidate_live_enable_report_cache() -> None:
        captured["live_enable"] = True

    monkeypatch.setattr(live_money_cache, "invalidate_cache", fake_invalidate_cache)
    from cas_forex import live_enable_control

    monkeypatch.setattr(
        live_enable_control,
        "invalidate_live_enable_report_cache",
        fake_invalidate_live_enable_report_cache,
    )

    live_money_cache.invalidate_live_money_gate_caches("extra_key")

    keys = set(captured["keys"])
    assert "live_money_progression_packet" in keys
    assert "live_money_progression_packet_fast" in keys
    assert "settings_authority_boundary" in keys
    assert "settings_runtime_gates" in keys
    assert "live_order_dry_run_review" in keys
    assert "live_readiness:False" in keys
    assert "extra_key" in keys
    assert captured["live_enable"] is True
