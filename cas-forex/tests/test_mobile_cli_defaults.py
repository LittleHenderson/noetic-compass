"""Tests for owner-facing mobile CLI defaults."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

from cas_forex.mobile_web_base import default_mobile_web_base, quick_start_url


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_mobile_web_base_prefers_configured_lan_host(monkeypatch) -> None:
    monkeypatch.setenv("CAS_FOREX_LAN_HOST", "10.9.8.7")

    assert default_mobile_web_base() == "http://10.9.8.7:4173"
    assert quick_start_url(None) == "http://10.9.8.7:4173/?page=quick-start"


def test_mobile_readiness_cli_defaults_to_owner_lan_base(monkeypatch, capsys) -> None:
    module = _load_script("run_mobile_release_readiness_cli", "scripts/run_mobile_release_readiness.py")
    captured: dict[str, object] = {}

    monkeypatch.setenv("CAS_FOREX_LAN_HOST", "10.9.8.7")

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(module, "run_mobile_release_readiness", fake_runner)
    monkeypatch.setattr(module, "readiness_to_dict", lambda report: {"web_base": captured.get("web_base")})

    assert module.main(["--json", "--skip-docker", "--skip-device-probe"]) == 0
    assert captured["web_base"] == "http://10.9.8.7:4173"
    assert '"web_base": "http://10.9.8.7:4173"' in capsys.readouterr().out


def test_release_bundle_cli_defaults_to_owner_lan_base(monkeypatch, capsys) -> None:
    module = _load_script("build_web_phone_release_bundle_cli", "scripts/build_web_phone_release_bundle.py")
    captured: dict[str, object] = {}

    monkeypatch.setenv("CAS_FOREX_LAN_HOST", "10.9.8.7")

    def fake_builder(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(ready_for_phone_install=True)

    monkeypatch.setattr(module, "build_phone_release_bundle", fake_builder)
    monkeypatch.setattr(module, "bundle_to_dict", lambda bundle: {"tested_web_base": captured.get("web_base")})

    assert module.main(["--json"]) == 0
    assert captured["web_base"] == "http://10.9.8.7:4173"
    assert '"tested_web_base": "http://10.9.8.7:4173"' in capsys.readouterr().out


def test_mobile_cli_explicit_web_base_still_wins(monkeypatch) -> None:
    module = _load_script("run_mobile_release_readiness_cli_override", "scripts/run_mobile_release_readiness.py")
    captured: dict[str, object] = {}

    monkeypatch.setenv("CAS_FOREX_LAN_HOST", "10.9.8.7")
    monkeypatch.setattr(
        module,
        "run_mobile_release_readiness",
        lambda **kwargs: captured.update(kwargs) or SimpleNamespace(),
    )
    monkeypatch.setattr(module, "readiness_to_dict", lambda report: {})

    assert module.main(["--json", "--web-base", "https://phone.example.test"]) == 0
    assert captured["web_base"] == "https://phone.example.test"
