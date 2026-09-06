"""Real directory creation with instrumented alias calls; no GPU execution."""
from pathlib import Path
from types import SimpleNamespace
import pytest
import _pytest.pathlib as paths
from cas_meta2 import pytest_no_aliases_v4 as plugin

pytestmark = pytest.mark.not_gpu


def test_real_temp_directories_and_files_survive_without_alias_call(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(Path, 'symlink_to', lambda self, target, **kwargs: calls.append((self, target)))
    paths.make_numbered_dir(tmp_path, 'before-')
    assert len(calls) == 1
    calls.clear()
    original = paths._force_symlink
    config = SimpleNamespace()
    plugin.pytest_configure(config)
    try:
        first = paths.make_numbered_dir(tmp_path, 'retained-')
        second = paths.make_numbered_dir(tmp_path, 'retained-')
        (first / 'evidence.json').write_text('{}')
        assert first != second and first.is_dir() and second.is_dir()
        assert (first / 'evidence.json').read_text() == '{}'
        assert calls == [] and plugin._suppressed == 2
        # Explicit links are NOT disabled. The collector still has to refuse them.
        (tmp_path / 'explicit-link').symlink_to(first)
        assert len(calls) == 1
    finally:
        plugin.pytest_unconfigure(config)
    assert paths._force_symlink is original


def test_unrecognized_pytest_version_fails_closed(monkeypatch):
    monkeypatch.setattr(pytest, '__version__', 'unknown')
    with pytest.raises(RuntimeError, match='PYTEST_ALIAS_HELPER_IDENTITY_MISMATCH'):
        plugin.pytest_configure(SimpleNamespace())
    assert plugin._original is None


def test_changed_helper_fails_closed(monkeypatch):
    monkeypatch.setattr(paths, '_force_symlink', plugin._no_alias)
    with pytest.raises(RuntimeError, match='PYTEST_ALIAS_HELPER_IDENTITY_MISMATCH'):
        plugin.pytest_configure(SimpleNamespace())
    assert plugin._original is None


def test_plugin_does_not_replace_an_overlapping_owner():
    config = SimpleNamespace()
    plugin.pytest_configure(config)
    try:
        with pytest.raises(RuntimeError, match='ALREADY_ACTIVE'):
            plugin.pytest_configure(SimpleNamespace())
    finally:
        plugin.pytest_unconfigure(config)
