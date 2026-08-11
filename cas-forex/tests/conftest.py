"""Make tests/ importable as a flat namespace.

Test modules import shared helpers from sibling files (e.g. ``from ui_contract
import assert_panel_wired``). pytest's rootdir insertion covers the repo root
but not tests/ itself on all invocation styles, so pin it explicitly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TESTS_DIR = str(Path(__file__).resolve().parent)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)


@pytest.fixture(autouse=True)
def _reset_mt5_connect_cooldown():
    """Keep the process-global MT5 connect cooldown from leaking across tests.

    mt5_connect_guard remembers "the terminal was unreachable at T" for 30s so
    production callers fail fast. In the suite, any test that triggers a real
    connect attempt (e.g. building the full readiness report) would arm the
    cooldown and starve later tests that drive connect() against FAKE MT5
    modules - their fakes are never reached and they fail on ordering alone.
    """
    from cas_forex import mt5_connect_guard

    mt5_connect_guard.reset()
    yield
    mt5_connect_guard.reset()
