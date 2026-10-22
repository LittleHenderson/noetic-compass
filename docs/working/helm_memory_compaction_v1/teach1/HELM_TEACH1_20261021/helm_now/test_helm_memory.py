"""test_helm_memory.py -- where HELM's chat session log goes, and when its folder is made.

Defect found by HELM UI v0 (2026-10-19): starting a chat session created an empty `sessions/` folder at the
repo root. Now the log goes to the given folder, else $HELM_SESSION_DIR, else helm_ui/sessions (git-ignored),
and the folder is made only on the first logged turn.
Run:  python -m pytest test_helm_memory.py -q
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import helm_memory  # noqa: E402
from helm_memory import HELMConversationalMemory  # noqa: E402


def _one_turn(mem):
    mem.record_turn("Check status.", "Check status.", "GIT_CONTROL", {}, "Done.")


def test_folder_is_made_on_first_write_only(tmp_path):
    target = tmp_path / "logs" / "nested"
    mem = HELMConversationalMemory(session_id="t-lazy", storage_dir=str(target))
    assert not target.exists()                     # starting a session makes no folder
    _one_turn(mem)
    assert (target / "t-lazy.jsonl").is_file()     # the first write makes it


def test_default_folder_is_helm_ui_sessions_not_repo_root(monkeypatch):
    monkeypatch.delenv("HELM_SESSION_DIR", raising=False)
    mem = HELMConversationalMemory(session_id="t-default")
    assert os.path.abspath(mem.storage_dir) == os.path.join(HERE, "helm_ui", "sessions")
    assert os.path.abspath(mem.storage_dir) != os.path.join(HERE, "sessions")


def test_env_var_sets_the_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("HELM_SESSION_DIR", str(tmp_path / "from_env"))
    mem = HELMConversationalMemory(session_id="t-env")
    assert mem.storage_dir == str(tmp_path / "from_env")
    _one_turn(mem)
    assert (tmp_path / "from_env" / "t-env.jsonl").is_file()


def test_starting_a_chat_session_makes_no_root_sessions_folder(monkeypatch, tmp_path):
    root_sessions = os.path.join(HERE, "sessions")
    existed = os.path.isdir(root_sessions)
    monkeypatch.setenv("HELM_SESSION_DIR", str(tmp_path / "chat"))
    import helm_chat
    helm_chat.HELMConversationalSession(mode="everyday", session_id="t-chat-start")
    assert not (tmp_path / "chat").exists()
    if not existed:
        assert not os.path.isdir(root_sessions)
    assert helm_memory.DEFAULT_SESSION_DIR == os.path.join(HERE, "helm_ui", "sessions")


def test_user_facts_keeps_the_last_twenty():
    """The cap keeps the LAST 20 facts. Before 2026-10-21 the code read `[:20]` and kept the FIRST 20, silently
    discarding every later fact from working memory (found by the memory-compaction census, SPEC 7.115)."""
    ctx = helm_memory.WorkingMemoryContext(context_id="t-facts-cap")
    for i in range(1, 26):
        ctx.add_user_fact(f"fact number {i}", turn_index=i)
    assert len(ctx.user_facts) == 20
    assert ctx.user_facts[0] == "fact number 6"
    assert ctx.user_facts[-1] == "fact number 25"
    assert "fact number 1" not in ctx.user_facts
