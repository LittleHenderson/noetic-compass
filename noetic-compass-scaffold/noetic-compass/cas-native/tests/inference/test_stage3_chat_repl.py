"""Tests for the Stage 3 conversation shell.

Lightweight tests (no archive needed) drive handle_turn directly with
the _DummyExplainer. Heavy test (skipped if real archive absent)
spot-checks the production explainer wire-up.

Discipline pinned:
- Plain mode is the default reply layer for CAS-expression turns.
- Slash commands dispatch correctly.
- Input classifier separates CAS expressions from CAS questions from
  free-form NL.
- Free-form NL gets a polite refusal, not a model call.
- /deeper and /simpler move the self-explain level correctly.
"""
from __future__ import annotations

import json
import pytest

from cas_native.inference import stage3_chat_repl as repl
from cas_native.inference.stage3_chat_repl import (
    ReplResponse,
    SessionState,
    _DummyExplainer,
    classify_input,
    handle_turn,
)
from cas_native.inference.stage3_local_loader import DEFAULT_ARCHIVE_ROOT


# ---------------------------------------------------------------------------
# Input classifier
# ---------------------------------------------------------------------------

def test_classify_cas_expression_with_noetic_operator():
    assert classify_input("^3^P|A") == "cas_expression"
    assert classify_input("let stageA0_4_857 = ^7^P_{F5}") == "cas_expression"


def test_classify_cas_expression_with_stage_identifier():
    assert classify_input(
        "stageA0_4_857 -> stageD3_4_857"
    ) == "cas_expression"


def test_classify_cas_question_what_is_cas():
    assert classify_input("what is CAS?") == "cas_question"
    assert classify_input("What is CAS?!") == "cas_question"
    assert classify_input("WHAT IS CAS") == "cas_question"


def test_classify_cas_question_examples():
    assert classify_input("give me an example") == "cas_question"
    assert classify_input("show me an example") == "cas_question"


def test_classify_cas_question_explain():
    assert classify_input("explain CAS") == "cas_question"
    assert classify_input("explain yourself") == "cas_question"
    assert classify_input("who are you?") == "cas_question"


def test_classify_freeform():
    assert classify_input("tell me a joke") == "freeform"
    assert classify_input("what is the weather in Paris") == "freeform"
    assert classify_input(
        "I'd like to discuss philosophy with you"
    ) == "freeform"


def test_classify_does_not_false_positive_on_F1_racing():
    """REGRESSION PIN (Codex audit fdd8a92): the classifier must not
    treat "F1 racing" as CAS just because F1 looks like a Drive
    marker. Drive markers fire only inside CAS curly-brace context."""
    assert classify_input("F1 racing is exciting") == "freeform"
    assert classify_input("the F4 tornado") == "freeform"
    assert classify_input("press F5 to reload") == "freeform"


def test_classify_does_not_false_positive_on_other_English():
    """A handful of English phrases that previously could trip patterns:
    bare letters that match Domain/Register tokens but lack CAS context."""
    # Word ending in "P" / "C" / "E" / "O" without caret prefix
    assert classify_input("the cup is full") == "freeform"
    # Bare T/A/f/E without pipe prefix
    assert classify_input("type A personality") == "freeform"
    # The bare letter "F" plus a number outside CAS braces
    assert classify_input("Apollo 11 mission") == "freeform"
    # A normal sentence that mentions "stage" but not the stageX_N_N pattern
    assert classify_input("the stage was set") == "freeform"


def test_classify_drive_marker_inside_braces_still_cas():
    """The Drive-marker pattern must still match its CAS context — `_{F5}`
    inside a compound expression."""
    assert classify_input("^7^P_{F5}") == "cas_expression"
    assert classify_input("let x = ^7^P_{F5}") == "cas_expression"


# ---------------------------------------------------------------------------
# Step 5B Minimal NL Front Door (heuristic bridge)
# ---------------------------------------------------------------------------

def test_nl_bridge_match_routes_through_explainer():
    """REGRESSION PIN: when the NL bridge matches a pattern, the REPL
    runs the inferred CAS through the explainer and the response
    surfaces BOTH the inferred CAS expression AND the Plain Mode
    explanation. Counts as a bridge-match kind, not a refusal."""
    state = SessionState()
    explainer = _DummyExplainer()
    response = handle_turn(
        "explain a thought becoming action", state, explainer,
    )
    assert response.kind == "nl_bridge_match"
    # The bridge surfaces the inferred CAS so the user sees what was matched
    assert "^9^O" in response.text
    # And it surfaces the matched pattern description
    assert "thought becoming action" in response.text.lower()


def test_nl_bridge_pushes_explain_to_history():
    """The bridge runs through the explainer; the resulting report
    goes into history so /trace and /tree work afterwards."""
    state = SessionState()
    handle_turn("turn anger into CAS", state, _DummyExplainer())
    assert len(state.history) == 1
    assert state.history[0]["kind"] == "explain"
    # The report carries the nl_bridge tag with the user's text
    report = state.history[0]["report"]
    assert "nl_bridge" in report
    assert report["nl_bridge"]["user_text"] == "turn anger into CAS"
    assert report["nl_bridge"]["cas_expression"] == "^3^E|f"


def test_nl_bridge_no_match_still_falls_through_to_refusal():
    """Unmatched NL input still gets the bridge-to-Step-5B refusal,
    BUT the refusal now lists supported patterns (heuristic v0)."""
    state = SessionState()
    response = handle_turn(
        "tell me about your weekend", state, _DummyExplainer(),
    )
    assert response.kind == "freeform_refusal"
    # New: lists supported patterns so the user learns what works
    assert "heuristic" in response.text.lower() or \
           "pattern" in response.text.lower()
    # Still mentions both supported input paths
    assert "CAS expression" in response.text
    assert "what is CAS" in response.text.lower() or \
           "what is cas" in response.text.lower()


def test_nl_bridge_followed_by_slash_trace_works():
    """After an NL bridge match, /trace should dump the full v0 trace
    just like a direct CAS expression."""
    state = SessionState()
    handle_turn("explain a thought becoming action", state, _DummyExplainer())
    response = handle_turn("/trace", state, _DummyExplainer())
    import json
    parsed = json.loads(response.text)
    assert parsed["schema_version"] == "traceability_v0"
    # Inferred CAS appears in the trace input
    assert parsed["input"]["cas_expression"] == "^9^O"


def test_classify_empty():
    assert classify_input("") == "empty"
    assert classify_input("   ") == "empty"
    assert classify_input("\n") == "empty"


# ---------------------------------------------------------------------------
# CAS expression turn → plain mode by default
# ---------------------------------------------------------------------------

def test_cas_expression_turn_returns_plain_mode():
    """REGRESSION PIN: a CAS-expression turn returns the plain-mode
    rendering, not the technical layer."""
    state = SessionState()
    expl = _DummyExplainer()
    response = handle_turn("^3^P|A", state, expl)
    assert response.kind == "explain"
    # Plain mode includes the synthetic dummy plain answer
    assert "plain answer" in response.text.lower() or \
           "plain meaning" in response.text.lower()
    # Technical-layer-only labels must NOT appear in the default reply
    assert "slot trace" not in response.text.lower()
    assert "STAGE_VAR" not in response.text


def test_cas_expression_turn_pushes_to_history():
    state = SessionState()
    expl = _DummyExplainer()
    handle_turn("^3^P|A", state, expl)
    assert len(state.history) == 1
    assert state.history[0]["kind"] == "explain"


# ---------------------------------------------------------------------------
# CAS question turn → self-explainer
# ---------------------------------------------------------------------------

def test_cas_question_turn_returns_self_explain():
    state = SessionState()
    response = handle_turn("what is CAS?", state, _DummyExplainer())
    assert response.kind == "self_explain"
    # Default level is simple, default topic is what
    assert state.self_explain_level == "simple"
    assert state.self_explain_topic == "what"
    assert state.history[-1]["kind"] == "self_explain"


def test_cas_question_with_example_keyword_sets_topic():
    state = SessionState()
    handle_turn("give me an example", state, _DummyExplainer())
    assert state.self_explain_topic == "example"


def test_cas_question_with_why_keyword_sets_topic():
    state = SessionState()
    handle_turn("why does CAS exist?", state, _DummyExplainer())
    assert state.self_explain_topic == "why"


# ---------------------------------------------------------------------------
# Free-form NL → polite refusal
# ---------------------------------------------------------------------------

def test_freeform_turn_returns_polite_refusal():
    """Codex 2026-05-13 reframe: freeform isn't a refusal, it's a bridge
    to Step 5B. Asserts the response surfaces what works now AND points
    at NL generation as the active next experiment."""
    state = SessionState()
    response = handle_turn(
        "tell me about your weekend",
        state, _DummyExplainer(),
    )
    assert response.kind == "freeform_refusal"
    # Bridges to Step 5B (active next experiment, not future-distant)
    assert "next experiment" in response.text.lower() or \
           "coming after" in response.text.lower() or \
           "coming next" in response.text.lower()
    # Tells the user what IS supported
    assert "CAS expression" in response.text
    assert "what is CAS" in response.text.lower() or "what is cas" in response.text.lower()
    # Concrete examples of supported input
    assert "example" in response.text.lower()


def test_freeform_turn_does_not_call_explainer():
    """REGRESSION PIN: free-form NL must not invoke the model. Detect
    via a counting explainer."""
    state = SessionState()

    class _CountingExplainer:
        def __init__(self):
            self.calls = 0

        def __call__(self, _expr: str):
            self.calls += 1
            return _DummyExplainer()(_expr)

    counter = _CountingExplainer()
    handle_turn("hello, how are you", state, counter)
    assert counter.calls == 0, (
        "free-form NL must not invoke the explainer"
    )


# ---------------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------------

def test_slash_help():
    state = SessionState()
    response = handle_turn("/help", state, _DummyExplainer())
    assert response.kind == "command"
    assert "/plain" in response.text
    assert "/technical" in response.text
    assert "/deeper" in response.text
    # Per Codex audit 95fcecf: /trace dumps full trace; /tree dumps
    # only the Thought Tree. Both must be in help.
    assert "/trace" in response.text
    assert "/tree" in response.text


def test_slash_quit():
    state = SessionState()
    response = handle_turn("/quit", state, _DummyExplainer())
    assert response.should_quit is True


def test_slash_exit():
    state = SessionState()
    response = handle_turn("/exit", state, _DummyExplainer())
    assert response.should_quit is True


def test_slash_clear_resets_history_and_level():
    state = SessionState()
    handle_turn("^3^P|A", state, _DummyExplainer())
    handle_turn("/deeper", state, _DummyExplainer())
    assert state.history  # something there
    assert state.self_explain_level != "simple"
    response = handle_turn("/clear", state, _DummyExplainer())
    assert response.kind == "command"
    assert state.history == []
    assert state.self_explain_level == "simple"


def test_slash_technical_after_cas_explain():
    """/technical on a CAS-explain reply shows the technical layer."""
    state = SessionState()
    handle_turn("^3^P|A", state, _DummyExplainer())
    response = handle_turn("/technical", state, _DummyExplainer())
    assert response.kind == "command"
    # Technical layer mentions slot trace, identifiers, gates
    text = response.text
    assert "slot trace" in text or "identifiers" in text or "gates" in text


def test_slash_details_is_alias_for_technical():
    state = SessionState()
    handle_turn("^3^P|A", state, _DummyExplainer())
    response = handle_turn("/details", state, _DummyExplainer())
    text = response.text
    assert "slot trace" in text or "identifiers" in text or "gates" in text


def test_slash_all_shows_both_layers():
    state = SessionState()
    handle_turn("^3^P|A", state, _DummyExplainer())
    response = handle_turn("/all", state, _DummyExplainer())
    text = response.text
    # Plain content
    assert "plain answer" in text.lower() or "plain meaning" in text.lower()
    # Technical content
    assert "slot trace" in text or "identifiers" in text


def test_slash_trace_dumps_full_v0_trace_as_json():
    """REGRESSION PIN (Codex 95fcecf): /trace dumps the full
    Traceability v0 trace object, not just the slot summary subset."""
    state = SessionState()
    handle_turn("^3^P|A", state, _DummyExplainer())
    response = handle_turn("/trace", state, _DummyExplainer())
    parsed = json.loads(response.text)
    # Full v0 trace has these top-level keys
    assert parsed.get("schema_version") == "traceability_v0"
    assert "input" in parsed
    assert "output" in parsed
    assert "copy" in parsed
    assert "slot_trace" in parsed
    assert "confidence" in parsed
    assert "thought_tree" in parsed
    assert "trace_id" in parsed


def test_slash_tree_dumps_only_thought_tree():
    """REGRESSION PIN (Codex 95fcecf): /tree dumps ONLY the Thought
    Tree sub-object, not the full trace. Useful when the user wants
    the node-edge graph without metadata."""
    state = SessionState()
    handle_turn("^3^P|A", state, _DummyExplainer())
    response = handle_turn("/tree", state, _DummyExplainer())
    parsed = json.loads(response.text)
    # Thought-tree-only payload has these keys, no schema_version
    assert "root" in parsed
    assert "nodes" in parsed
    assert "edges" in parsed
    assert "node_count" in parsed
    # No full-trace top-level keys
    assert "schema_version" not in parsed
    assert "input" not in parsed
    assert "confidence" not in parsed


def test_slash_tree_no_history():
    state = SessionState()
    response = handle_turn("/tree", state, _DummyExplainer())
    assert response.kind == "command"
    assert "no thought tree" in response.text.lower()


def test_slash_raw_dumps_full_report_as_json():
    state = SessionState()
    handle_turn("^3^P|A", state, _DummyExplainer())
    response = handle_turn("/raw", state, _DummyExplainer())
    parsed = json.loads(response.text)
    # The full report includes the raw fields
    assert parsed.get("input_cas_expression") == "^3^P|A"
    assert "plain_english" in parsed


def test_slash_deeper_steps_up_a_level():
    state = SessionState()
    assert state.self_explain_level == "simple"
    handle_turn("/deeper", state, _DummyExplainer())
    assert state.self_explain_level == "stakeholder"
    handle_turn("/deeper", state, _DummyExplainer())
    assert state.self_explain_level == "user"


def test_slash_simpler_steps_down_a_level():
    state = SessionState()
    state.self_explain_level = "technical"
    handle_turn("/simpler", state, _DummyExplainer())
    assert state.self_explain_level == "builder"


def test_slash_deeper_at_technical_stays():
    state = SessionState()
    state.self_explain_level = "technical"
    handle_turn("/deeper", state, _DummyExplainer())
    assert state.self_explain_level == "technical"


def test_slash_simpler_at_simple_stays():
    state = SessionState()
    state.self_explain_level = "simple"
    handle_turn("/simpler", state, _DummyExplainer())
    assert state.self_explain_level == "simple"


def test_slash_unknown_command_is_helpful():
    state = SessionState()
    response = handle_turn("/nope", state, _DummyExplainer())
    assert response.kind == "command"
    assert "/help" in response.text


def test_slash_plain_with_no_history():
    """No previous reply — /plain returns the no-history hint, not a crash."""
    state = SessionState()
    response = handle_turn("/plain", state, _DummyExplainer())
    assert response.kind == "command"
    assert "no previous reply" in response.text.lower()


def test_slash_trace_with_no_history():
    state = SessionState()
    response = handle_turn("/trace", state, _DummyExplainer())
    assert response.kind == "command"
    assert "no trace" in response.text.lower()


# ---------------------------------------------------------------------------
# Banner / help mentions the supported input paths (regression pin)
# ---------------------------------------------------------------------------

def test_help_text_mentions_both_supported_paths():
    """REGRESSION PIN: the /help output must mention BOTH supported input
    paths (CAS expression + CAS question) so the user knows what works."""
    state = SessionState()
    response = handle_turn("/help", state, _DummyExplainer())
    text = response.text
    assert "CAS expression" in text
    assert "what is CAS" in text.lower() or "what is cas" in text.lower()


# ---------------------------------------------------------------------------
# Heavy: end-to-end against real archive (skipped if absent)
# ---------------------------------------------------------------------------

_REAL_CKPT = (
    DEFAULT_ARCHIVE_ROOT / "stage_e3_20260513T043823Z" / "ckpt_final.pt"
)


@pytest.mark.skipif(
    not _REAL_CKPT.exists(),
    reason=f"real Stage 3 archive not present at {_REAL_CKPT}; "
           "skip heavy end-to-end REPL test",
)
def test_production_explainer_returns_well_formed_report():
    """Production explainer wires through the real Stage 3 model + Plain
    English Mode. Spot-check that one CAS expression produces a
    structurally valid report."""
    explainer = repl._build_production_explainer()
    report = explainer(
        "let stageA0_4_857 = ^7^P_{F5}; "
        "let stageD3_4_857 = ^6^P_{F2}; "
        "stageA0_4_857 -> stageD3_4_857"
    )
    # Schema-level pin
    assert "plain_english" in report
    assert "short_answer" in report["plain_english"]
    assert "plain_meaning" in report["plain_english"]
    assert "generated_english" in report
    assert report["model"]["max_cas_prefix_len"] == 192
    # Gates structurally valid
    gates = report.get("gates", {})
    assert gates.get("no_crash") is True
