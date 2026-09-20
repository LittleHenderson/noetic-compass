"""Opt-in pytest 9.0.2 plugin: retain temp files without convenience symlinks.

Load explicitly with -p cas_meta2.pytest_no_aliases_v4. This only replaces
pytest's byte-pinned alias helper, never Path.symlink_to or the collector.
"""
from hashlib import sha256
import inspect

HELPER_SHA256 = 'bf2d8dd60869ad74fa271923837893840d400590f1a9aef5db42e25afd2e21c0'
_original = None
_suppressed = 0


def _no_alias(root, target, link_to):
    global _suppressed
    _suppressed += 1


def pytest_configure(config):
    global _original, _suppressed
    import pytest
    import _pytest.pathlib as paths
    if _original is not None:
        raise RuntimeError('PYTEST_ALIAS_PLUGIN_ALREADY_ACTIVE')
    if (pytest.__version__ != '9.0.2'
            or sha256(inspect.getsource(paths._force_symlink).encode()).hexdigest() != HELPER_SHA256):
        raise RuntimeError('PYTEST_ALIAS_HELPER_IDENTITY_MISMATCH')
    _original, _suppressed = paths._force_symlink, 0
    paths._force_symlink = _no_alias
    config._cas_v4_alias_owner = True


def pytest_report_header(config):
    return 'CAS v4: pytest convenience aliases disabled; real temp directories retained'


def pytest_terminal_summary(terminalreporter):
    terminalreporter.write_line('CAS_PYTEST_ALIAS_SUPPRESSIONS=' + str(_suppressed))


def pytest_unconfigure(config):
    global _original
    if not getattr(config, '_cas_v4_alias_owner', False):
        return
    import _pytest.pathlib as paths
    if paths._force_symlink is not _no_alias or _original is None:
        raise RuntimeError('PYTEST_ALIAS_HELPER_CHANGED_WHILE_ACTIVE')
    paths._force_symlink = _original
    _original = None
    config._cas_v4_alias_owner = False
