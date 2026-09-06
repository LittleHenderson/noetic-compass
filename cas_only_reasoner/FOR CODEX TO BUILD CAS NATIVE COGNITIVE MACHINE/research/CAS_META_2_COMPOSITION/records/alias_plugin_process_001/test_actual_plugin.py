"""Actual plugin loading and pure pytest directory behavior."""
from pathlib import Path
import _pytest.pathlib as paths
from cas_meta2 import pytest_no_aliases_v4 as plugin


def test_actual_plugin(tmp_path):
    assert paths._force_symlink is plugin._no_alias
    first = paths.make_numbered_dir(tmp_path, 'kept-')
    second = paths.make_numbered_dir(tmp_path, 'kept-')
    (first / 'data.json').write_text('{}')
    assert first != second and second.is_dir()
    assert (first / 'data.json').read_text() == '{}'
    assert plugin._suppressed >= 3
    assert not any(p.is_symlink() for p in tmp_path.parent.rglob('*'))
