from __future__ import annotations

import subprocess

from api.routes import evidence
from api.services import cas_harness_api_endpoint_runner as api_runner
from api.services import cas_harness_live_worker_runner as live_runner


def _unexpected_git(*_args, **_kwargs):
    raise AssertionError("provider-bound runtime provenance must not invoke git")


def test_render_commit_is_authoritative_when_production_image_has_no_git(
    monkeypatch,
) -> None:
    deployed_sha = "a" * 40
    monkeypatch.setenv("RENDER_GIT_COMMIT", deployed_sha)
    monkeypatch.setattr(subprocess, "run", _unexpected_git)

    assert live_runner._code_commit_sha() == deployed_sha
    assert api_runner._code_commit_sha() == deployed_sha
    assert evidence._git_head_sha() == deployed_sha


def test_malformed_render_commit_fails_closed_without_git_fallback(monkeypatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "not-a-canonical-commit")
    monkeypatch.setattr(subprocess, "run", _unexpected_git)

    assert live_runner._code_commit_sha() == "unknown"
    assert api_runner._code_commit_sha() == "unknown"
    assert evidence._git_head_sha() is None
