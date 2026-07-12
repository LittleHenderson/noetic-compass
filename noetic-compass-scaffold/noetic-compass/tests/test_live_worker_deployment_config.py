from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]


def _assert_dashboard_managed_worker_pair(blueprint: str) -> None:
    assert "6bmmab3vbf1yij-8888.proxy.runpod.net" not in blueprint
    assert "- key: ATLAS_LIVE_WORKER_URL\n        sync: false" in blueprint
    assert "- key: ATLAS_LIVE_WORKER_TOKEN\n        sync: false" in blueprint


def test_render_blueprints_do_not_ship_a_stale_or_tokenless_worker_target():
    root_blueprint = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    legacy_blueprint = (PROJECT_ROOT / "infra" / "render.yaml").read_text(
        encoding="utf-8"
    )

    _assert_dashboard_managed_worker_pair(root_blueprint)
    _assert_dashboard_managed_worker_pair(legacy_blueprint)


def test_environment_example_documents_no_ssh_8080_token_contract():
    example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "https://<pod-id>-8080.proxy.runpod.net" in example
    assert "ATLAS_LIVE_WORKER_URL=" in example
    assert "ATLAS_LIVE_WORKER_TOKEN=" in example
    assert "must not depend on an SSH tunnel or laptop" in example
    assert "Every non-loopback URL is" in example
    assert "fail-closed" in example
