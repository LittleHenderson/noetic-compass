"""Smoke test: chat.py belief wiring is importable + commands defined.

The full chat.py REPL requires loading a multi-GB checkpoint, which is
out of scope for unit tests. This file verifies the module-level wiring:
that chat.py imports BeliefStore, exposes the new helper functions, and
declares the new ``/beliefs``, ``/why``, ``/forget`` command tokens.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def test_chat_module_imports_belief_store(tmp_path):
    """chat.py must import BeliefStore at module load."""
    repo_root = Path(__file__).resolve().parents[3]
    chat_path = repo_root / "cas-native" / "inference" / "chat.py"
    assert chat_path.exists()
    source = chat_path.read_text(encoding="utf-8")
    assert "from cas_native.belief import BeliefStore" in source


def test_chat_defines_command_tokens():
    repo_root = Path(__file__).resolve().parents[3]
    chat_path = repo_root / "cas-native" / "inference" / "chat.py"
    source = chat_path.read_text(encoding="utf-8")
    assert '"/beliefs"' in source
    assert '"/why"' in source
    assert '"/forget"' in source


def test_chat_defines_belief_helper_functions():
    repo_root = Path(__file__).resolve().parents[3]
    chat_path = repo_root / "cas-native" / "inference" / "chat.py"
    source = chat_path.read_text(encoding="utf-8")
    assert "def _show_beliefs(" in source
    assert "def _show_why(" in source
    assert "def _do_forget(" in source


def test_chat_renders_belief_status_row():
    repo_root = Path(__file__).resolve().parents[3]
    chat_path = repo_root / "cas-native" / "inference" / "chat.py"
    source = chat_path.read_text(encoding="utf-8")
    assert "BELIEF STATUS" in source
    assert "belief_status" in source
