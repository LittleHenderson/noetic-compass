"""Smoke test: chat.py B-4 native-generator wiring is connected.

The B-4 wiring routes user typed text through K=9 → generate_reply when
``/native on`` is toggled. Codex's audit caught four wiring bugs in the
initial draft. These tests pin the fixes so future edits don't regress:

1. The typed-text ``_predict_and_show`` call must pass ``native_generator``
   (otherwise ``/native on`` has no effect on what users type into the REPL).
2. ``_show_menu`` and ``_show_random_demo`` must accept ``native_generator``
   (otherwise ``/menu`` and ``/sample`` crash with TypeError when the toggle
   is on).
3. Register extraction must fall back safely when K=9 returns an empty
   ``registers`` list (otherwise IndexError silently kills Stage 2).
4. ``use_cas_prefix=False`` is set explicitly to match the trainer/B-3.5
   eval default (PAD-leakage guard until head exposes cas_prefix_mask).

These tests source-grep the chat.py contents — the same approach the
belief-wiring test uses — because the full REPL needs a multi-GB
checkpoint that's out of scope for unit tests.
"""

from __future__ import annotations

from pathlib import Path


def _chat_source() -> str:
    repo_root = Path(__file__).resolve().parents[3]
    chat_path = repo_root / "cas-native" / "inference" / "chat.py"
    assert chat_path.exists(), f"chat.py not found at {chat_path}"
    return chat_path.read_text(encoding="utf-8")


def test_show_menu_accepts_native_generator():
    src = _chat_source()
    # The signature line must declare native_generator as a kwarg.
    assert "def _show_menu(" in src
    # Find the function and verify the param exists in its signature
    fn_start = src.index("def _show_menu(")
    fn_body = src[fn_start: fn_start + 2000]
    assert "native_generator" in fn_body, (
        "_show_menu must accept a native_generator kwarg or /menu crashes "
        "when /native is on"
    )


def test_show_random_demo_accepts_native_generator():
    src = _chat_source()
    assert "def _show_random_demo(" in src
    fn_start = src.index("def _show_random_demo(")
    fn_body = src[fn_start: fn_start + 1500]
    assert "native_generator" in fn_body, (
        "_show_random_demo must accept a native_generator kwarg or /sample "
        "crashes when /native is on"
    )


def test_typed_input_path_passes_native_generator():
    """Codex audit finding #1: the main REPL path that users actually
    type into must route through native_generator when use_native is on,
    otherwise /native is a dead toggle for typed input."""
    src = _chat_source()
    # The typed-input _predict_and_show invocation must pass
    # native_generator=native_gen_loaded if use_native else None.
    # Search for the pattern that indicates the routing exists.
    assert "native_generator=native_gen_loaded if use_native else None" in src, (
        "typed-input _predict_and_show must pass native_generator based "
        "on use_native toggle"
    )


def test_register_extraction_handles_empty_registers_list():
    """Codex audit finding #4: K=9 may return registers as an empty list;
    blind indexing crashes Stage 2. Must fall back to "T"."""
    src = _chat_source()
    # The fix uses an "or [] / if registers_list else 'T'" pattern.
    assert "registers_list = prediction.get(\"registers\") or []" in src
    # The actual code wraps in str(...) for safety; test for the
    # ternary fallback structure regardless of the str() wrapper.
    assert "if registers_list else \"T\"" in src
    assert "registers_list[0]" in src


def test_native_generation_uses_cas_prefix_off():
    """Codex audit finding #3: use_cas_prefix must be False to match the
    trainer default and the B-3.5 evaluation. The head doesn't yet expose
    a cas_prefix_mask so a padded prefix would leak PAD into conditioning."""
    src = _chat_source()
    # Find the generate_reply call inside _predict_and_show
    assert "use_cas_prefix=False" in src, (
        "B-4 generate_reply call must set use_cas_prefix=False explicitly"
    )


def test_native_command_token_defined():
    """The /native toggle command itself must exist in the REPL command
    handling block."""
    src = _chat_source()
    assert "/native" in src, "REPL must define a /native command for B-4 toggle"


def test_no_trailing_whitespace_in_b4_block():
    """Trailing whitespace at the BPE-load block was caught by git diff
    --check during the audit; pin it so future edits don't reintroduce."""
    src = _chat_source()
    for i, line in enumerate(src.splitlines(), start=1):
        if line and line != line.rstrip():
            # Allow trailing whitespace ONLY inside string literals (rare).
            # The audit-flagged line was 1031 (BPE composition block).
            # If anything is flagged in the production-code area, raise.
            stripped_left = line.lstrip()
            if stripped_left.startswith(("#", '"', "'")):
                continue  # comment or docstring — usually fine
            raise AssertionError(
                f"trailing whitespace at line {i}: {line!r}"
            )
