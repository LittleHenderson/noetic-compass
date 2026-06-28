"""Smoke tests for the Phase 2 Dialogue State Tracker scaffold.

These tests exercise plumbing only. They assert:

  - dialog grammar admissibility correctness
  - admissibility graph connectivity
  - DialogState evolution preserves invariants
  - repair detection fires on canonical correction language
  - repair strategy selection picks reasonable strategies
  - repair application mutates state correctly
  - ConversationEngine smoke: a 5-turn synthetic conversation produces
    a valid state at every turn
  - the conversation generator emits a record with a valid dialog path
  - all stubs return correctly-typed values

Constraints: stdlib only; <30 s total runtime; no torch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from cas_native.dst import (
    ADMISSIBILITY,
    CAS_LOAD_BEARING,
    CAS_MUTATING,
    CAS_NEUTRAL,
    ConversationEngine,
    DefaultStubPredictor,
    DialogState,
    EngineStep,
    GenerationRequest,
    GenerationResult,
    RepairStrategy,
    Turn,
    TurnType,
    TURN_SEMANTICS,
    admissibility_graph_is_connected,
    admissible_next,
    apply_repair,
    apply_turn,
    carries_cas,
    compress_history,
    derive_followup_turn_type,
    detect_repair,
    expected_role,
    generate,
    initial_state,
    is_admissible,
    make_turn,
    mutates_cas_state,
    reachable_from,
    select_repair_strategy,
)


# ---------------------------------------------------------------------------
# Dialog grammar tests
# ---------------------------------------------------------------------------

class TestDialogGrammar:
    """Admissibility relation + per-turn semantics."""

    def test_open_to_answer_is_admissible(self):
        # OPEN -> ANSWER is allowed for short well-anchored prompts.
        assert is_admissible(TurnType.OPEN, TurnType.ANSWER) is True

    def test_open_to_repair_is_not_admissible(self):
        # REPAIR cannot follow OPEN -- there is nothing to repair yet.
        assert is_admissible(TurnType.OPEN, TurnType.REPAIR) is False

    def test_mirror_to_answer_is_admissible(self):
        assert is_admissible(TurnType.MIRROR, TurnType.ANSWER) is True

    def test_answer_to_repair_is_admissible(self):
        # The user's correction can follow the assistant's commitment.
        assert is_admissible(TurnType.ANSWER, TurnType.REPAIR) is True

    def test_close_admits_nothing(self):
        # CLOSE is terminal.
        assert ADMISSIBILITY[TurnType.CLOSE] == frozenset()
        for tt in TurnType:
            assert is_admissible(TurnType.CLOSE, tt) is False

    def test_admissibility_keys_total(self):
        # Every TurnType must appear as a key in ADMISSIBILITY.
        assert set(ADMISSIBILITY.keys()) == set(TurnType)

    def test_admissibility_values_typecheck(self):
        # Every value in the relation is a TurnType.
        for prev, nexts in ADMISSIBILITY.items():
            assert isinstance(nexts, frozenset)
            for nxt in nexts:
                assert isinstance(nxt, TurnType)

    def test_admissibility_graph_connectivity(self):
        # Every TurnType reachable from OPEN.
        assert admissibility_graph_is_connected() is True

    def test_admissibility_graph_full_reach_from_open(self):
        reach = reachable_from(TurnType.OPEN)
        assert reach == set(TurnType)

    def test_admissible_next_with_no_prev_returns_open(self):
        nexts = admissible_next(None)
        assert nexts == frozenset({TurnType.OPEN})

    def test_carries_cas_load_bearing_set(self):
        for tt in TurnType:
            assert carries_cas(tt) == (tt in CAS_LOAD_BEARING)

    def test_mutates_state_set(self):
        for tt in TurnType:
            assert mutates_cas_state(tt) == (tt in CAS_MUTATING)

    def test_cas_load_bearing_and_neutral_are_disjoint(self):
        assert CAS_LOAD_BEARING.isdisjoint(CAS_NEUTRAL)

    def test_cas_load_bearing_plus_neutral_covers_all_types(self):
        # Every turn type is either load-bearing or neutral.
        union = set(CAS_LOAD_BEARING) | set(CAS_NEUTRAL)
        assert union == set(TurnType)

    def test_expected_role_total(self):
        for tt in TurnType:
            role = expected_role(tt)
            assert role in {"user", "assistant", "either"}

    def test_turn_semantics_total(self):
        # TURN_SEMANTICS describes every turn type.
        assert set(TURN_SEMANTICS.keys()) == set(TurnType)


# ---------------------------------------------------------------------------
# State tracker tests
# ---------------------------------------------------------------------------

class TestStateTracker:
    """DialogState + apply_turn + compress_history + detect_repair."""

    def test_initial_state_is_empty(self):
        s = initial_state()
        assert s.num_turns == 0
        assert s.current_cas_state == ""
        assert s.cas_state_history == ()
        assert s.admissible_next_moves == frozenset({TurnType.OPEN})
        assert s.repair_count == 0

    def test_apply_open_appends_turn(self):
        s = initial_state()
        t = make_turn(role="user", text="hi", turn_type=TurnType.OPEN)
        s2 = apply_turn(s, t)
        assert s2.num_turns == 1
        assert s2.last_turn is t
        assert s2.last_turn_type == TurnType.OPEN
        # OPEN does not mutate CAS state.
        assert s2.current_cas_state == ""
        assert s2.admissible_next_moves == ADMISSIBILITY[TurnType.OPEN]

    def test_apply_answer_writes_cas_state(self):
        s = initial_state()
        s = apply_turn(s, make_turn("user", "hi", TurnType.OPEN))
        s = apply_turn(
            s,
            make_turn(
                "assistant", "got it",
                TurnType.ANSWER,
                cas_state_after="^3^E|f",
                cas_transition="visceral aversion",
            ),
        )
        assert s.current_cas_state == "^3^E|f"
        # Walk-back stack got the previous (empty) state.
        assert s.cas_state_history == ("",)

    def test_apply_violates_admissibility_raises(self):
        s = initial_state()
        s = apply_turn(s, make_turn("user", "hi", TurnType.OPEN))
        bad = make_turn("user", "no wait", TurnType.REPAIR)
        # REPAIR after OPEN is illegal (nothing to repair yet).
        with pytest.raises(ValueError):
            apply_turn(s, bad)

    def test_apply_disable_admissibility_check(self):
        s = initial_state()
        s = apply_turn(s, make_turn("user", "hi", TurnType.OPEN))
        # With enforce_admissibility=False, the same illegal turn lands
        # without raising. (Tests of low-level data model only.)
        bad = make_turn("user", "no wait", TurnType.REPAIR)
        s2 = apply_turn(s, bad, enforce_admissibility=False)
        assert s2.last_turn_type == TurnType.REPAIR

    def test_repair_increments_counter_and_decays_satisfaction(self):
        s = initial_state()
        s = apply_turn(s, make_turn("user", "hi", TurnType.OPEN))
        s = apply_turn(
            s,
            make_turn(
                "assistant", "got it", TurnType.ANSWER,
                cas_state_after="^3^E|f",
            ),
        )
        s = apply_turn(s, make_turn("user", "no wait that's not right", TurnType.REPAIR))
        assert s.repair_count == 1
        assert s.user_satisfaction_estimate < 1.0

    def test_compress_history_drops_oldest(self):
        s = initial_state()
        # Build a long alternating thread (within admissibility) using the
        # disable flag to keep the test simple; admissibility itself is
        # tested elsewhere.
        for i in range(20):
            t = make_turn("user", f"msg {i}", TurnType.OPEN)
            s = apply_turn(s, t, enforce_admissibility=False)
        before = s.num_turns
        s = compress_history(s, max_turns=5)
        assert s.num_turns == 5
        assert s.metadata["compressed_count"] == before - 5

    def test_detect_repair_requires_prior_cas_turn(self):
        # No prior assistant CAS turn -> not a repair, even if trigger fires.
        s = initial_state()
        s = apply_turn(s, make_turn("user", "hi", TurnType.OPEN))
        assert detect_repair(s, "no wait actually") is False

    def test_detect_repair_fires_after_answer(self):
        s = initial_state()
        s = apply_turn(s, make_turn("user", "hi", TurnType.OPEN))
        s = apply_turn(
            s,
            make_turn(
                "assistant", "got it", TurnType.ANSWER,
                cas_state_after="^3^E|f",
            ),
        )
        assert detect_repair(s, "no wait, that's not right") is True
        assert detect_repair(s, "actually, I meant something else") is True
        assert detect_repair(s, "thanks, that's helpful") is False

    def test_turn_to_dict_roundtrip_keys(self):
        t = make_turn("user", "hi", TurnType.OPEN)
        d = t.to_dict()
        for key in ("role", "text", "turn_type", "cas_state_after", "cas_transition", "timestamp_ms"):
            assert key in d
        # Turn-type should be the string value, not the enum.
        assert d["turn_type"] == "OPEN"

    def test_dialog_state_to_dict_serialisable(self):
        s = initial_state()
        s = apply_turn(s, make_turn("user", "hi", TurnType.OPEN))
        d = s.to_dict()
        # Verify it's actually JSON-serialisable.
        json.dumps(d)


# ---------------------------------------------------------------------------
# Repair strategy tests
# ---------------------------------------------------------------------------

class TestRepairStrategies:
    """select_repair_strategy + apply_repair + derive_followup_turn_type."""

    def _post_answer_state(self) -> DialogState:
        s = initial_state()
        s = apply_turn(s, make_turn("user", "hi", TurnType.OPEN))
        s = apply_turn(
            s,
            make_turn(
                "assistant", "got it", TurnType.ANSWER,
                cas_state_after="^3^E|f",
            ),
        )
        return s

    def test_walk_back_when_history_present_and_trigger(self):
        s = self._post_answer_state()
        # Add a second answer so the walk-back stack has content beyond
        # the initial empty state.
        s = apply_turn(s, make_turn("user", "no wait, actually", TurnType.REPAIR))
        s = apply_turn(
            s,
            make_turn(
                "assistant", "okay revised", TurnType.ANSWER,
                cas_state_after="^2^E|f",
            ),
        )
        # Now history has [^3^E|f, ""] in the walk-back stack.
        assert "^3^E|f" in s.cas_state_history
        strategy = select_repair_strategy(s, "go back to the earlier reading")
        assert strategy == RepairStrategy.WALK_BACK

    def test_clarify_when_user_unsure(self):
        s = self._post_answer_state()
        strategy = select_repair_strategy(s, "I don't know, either way I guess")
        assert strategy == RepairStrategy.CLARIFY

    def test_refine_when_user_corrects(self):
        s = self._post_answer_state()
        strategy = select_repair_strategy(s, "actually it's closer to grief than aversion")
        assert strategy == RepairStrategy.REFINE

    def test_reset_after_repeated_repairs(self):
        s = self._post_answer_state()
        # Force the repair count up to one less than the threshold; the
        # next repair must escalate.
        from dataclasses import replace
        s = replace(s, repair_count=2)  # next repair makes 3 -> RESET
        strategy = select_repair_strategy(s, "no, that's not right")
        assert strategy == RepairStrategy.RESET

    def test_apply_walk_back_restores_previous(self):
        s = self._post_answer_state()
        s = apply_turn(s, make_turn("user", "no wait", TurnType.REPAIR))
        s = apply_turn(
            s,
            make_turn(
                "assistant", "revised", TurnType.ANSWER,
                cas_state_after="^2^E|f",
            ),
        )
        # current = ^2^E|f, history = [^3^E|f, ""]
        assert s.current_cas_state == "^2^E|f"
        s2 = apply_repair(s, RepairStrategy.WALK_BACK, "go back")
        assert s2.current_cas_state == "^3^E|f"

    def test_apply_reset_clears_state(self):
        s = self._post_answer_state()
        s2 = apply_repair(s, RepairStrategy.RESET, "no, totally off")
        assert s2.current_cas_state == ""
        assert s2.cas_state_history == ()
        assert s2.metadata["reset_count"] == 1

    def test_walk_back_with_empty_history_falls_through_to_refine(self):
        # If the user asks to walk back but the stack is empty, we fall
        # through to REFINE so we never lose ground.
        s = self._post_answer_state()
        # cas_state_history at this point is ('',), which is non-empty
        # but only contains the initial empty state. Empty stack case:
        from dataclasses import replace
        s_empty = replace(s, cas_state_history=())
        s2 = apply_repair(s_empty, RepairStrategy.WALK_BACK, "go back")
        # State should not have a popped restoration; current_cas_state
        # remains as it was, and the metadata records refine fallback.
        assert s2.current_cas_state == s_empty.current_cas_state
        assert s2.metadata.get("last_repair_strategy") == RepairStrategy.REFINE.value

    def test_followup_turn_types(self):
        assert derive_followup_turn_type(RepairStrategy.WALK_BACK) == TurnType.MIRROR
        assert derive_followup_turn_type(RepairStrategy.REFINE) == TurnType.ANSWER
        assert derive_followup_turn_type(RepairStrategy.CLARIFY) == TurnType.CLARIFY
        assert derive_followup_turn_type(RepairStrategy.RESET) == TurnType.CLARIFY


# ---------------------------------------------------------------------------
# NL generation head tests
# ---------------------------------------------------------------------------

class TestNLGenerationHead:
    """generate() returns sensibly typed results for every turn type."""

    @pytest.mark.parametrize("tt", list(TurnType))
    def test_generate_returns_typed_result(self, tt):
        # Build a request with a fake CAS state so CAS-load-bearing
        # turns have something to render.
        req = GenerationRequest(turn_type=tt, cas_state="^3^E|f", user_text="hi")
        result = generate(req)
        assert isinstance(result, GenerationResult)
        assert isinstance(result.text, str)
        assert result.text.strip() != ""
        assert isinstance(result.template_used, str)
        assert result.template_used.strip() != ""

    def test_generate_answer_grounds_in_cas_state(self):
        req = GenerationRequest(turn_type=TurnType.ANSWER, cas_state="^3^E|f")
        result = generate(req)
        # In the inline-fallback rendering the CAS expression appears in
        # the text.
        assert "^3^E|f" in result.text or result.template_used == "cas_renderer"

    def test_generate_clarify_uses_canned(self):
        req = GenerationRequest(turn_type=TurnType.CLARIFY)
        result = generate(req)
        assert result.template_used == "canned_clarify"


# ---------------------------------------------------------------------------
# ConversationEngine smoke tests
# ---------------------------------------------------------------------------

class TestConversationEngineSmoke:
    """5-turn synthetic conversation produces valid state at every turn."""

    def test_engine_constructs_with_defaults(self):
        engine = ConversationEngine()
        assert engine.predictor is not None
        assert engine.nl_head is not None

    def test_single_turn_open_then_answer(self):
        engine = ConversationEngine()
        step = engine.respond("I can't stand it when people interrupt me")
        assert isinstance(step, EngineStep)
        assert step.user_turn.role == "user"
        assert step.user_turn.turn_type == TurnType.OPEN
        assert step.assistant_turn.role == "assistant"
        # The stub predictor sees "can't stand" and returns ^3^E|f with
        # confidence 0.85 > confidence_floor=0.7, so the engine commits
        # via ANSWER.
        assert step.assistant_turn.turn_type in (TurnType.ANSWER, TurnType.MIRROR)
        assert step.state.num_turns == 2
        assert step.elapsed_ms >= 0.0

    def test_five_turn_synthetic_conversation(self):
        """Walks a realistic 5-turn synthetic exchange and asserts state
        invariants at every turn."""
        engine = ConversationEngine()
        state = None
        utterances = [
            "I can't stand it when people interrupt me",
            "no wait, actually it's closer to grief than aversion",
            "what about when it reminds me of my dad",
            "thanks, that's helpful",
            "bye for now",
        ]
        for i, text in enumerate(utterances):
            step = engine.respond(text, state)
            state = step.state
            # Invariants at every turn:
            assert state.num_turns == 2 * (i + 1), (
                f"turn {i}: expected {2 * (i + 1)} turns, got {state.num_turns}"
            )
            # admissible_next_moves matches the most recent turn type's
            # admissibility set.
            assert state.admissible_next_moves == ADMISSIBILITY[state.last_turn_type]
            # CAS state evolves only via CAS-load-bearing assistant turns.
            if step.assistant_turn.turn_type in CAS_LOAD_BEARING:
                assert step.assistant_turn.cas_state_after is not None
                assert state.current_cas_state == step.assistant_turn.cas_state_after
            # Walk-back stack length never exceeds the cap.
            assert len(state.cas_state_history) <= 32

    def test_repair_handling_in_engine(self):
        """REPAIR after an ANSWER produces a follow-up assistant turn."""
        engine = ConversationEngine()
        step1 = engine.respond("I can't stand interruptions")
        # First turn must be ANSWER or MIRROR (CAS-load-bearing).
        assert step1.assistant_turn.turn_type in CAS_LOAD_BEARING
        step2 = engine.respond("no wait, that's not right -- it's closer to grief", step1.state)
        # User turn classified as REPAIR.
        assert step2.user_turn.turn_type == TurnType.REPAIR
        assert step2.repair_strategy is not None
        # Assistant follow-up is one of the admissible-after-REPAIR types.
        assert step2.assistant_turn.turn_type in ADMISSIBILITY[TurnType.REPAIR]

    def test_engine_passes_state_through(self):
        """Calling respond with an explicit state preserves identity."""
        engine = ConversationEngine()
        step1 = engine.respond("hello")
        # The returned state contains both turns.
        assert step1.state.num_turns == 2
        # Continuing from that state appends, not replaces.
        step2 = engine.respond("more text", step1.state)
        assert step2.state.num_turns == 4
        # Earliest turn's text is preserved in history.
        assert step2.state.turn_history[0].text == "hello"


# ---------------------------------------------------------------------------
# Conversation generator tests (multi-turn synthetic corpus)
# ---------------------------------------------------------------------------

class TestConversationGenerator:
    """The synthetic multi-turn corpus producer."""

    def test_import(self):
        # Importing the generator module should not require torch.
        import importlib
        mod = importlib.import_module("cas_synthetic.generator.multi_turn.conversation_generator")
        assert hasattr(mod, "generate_conversation")
        assert hasattr(mod, "generate_dialog_path")

    def test_generate_dialog_path_is_admissible(self):
        from cas_synthetic.generator.multi_turn.conversation_generator import (
            generate_dialog_path,
        )
        path = generate_dialog_path(seed=0, target_turns=6)
        assert isinstance(path, list)
        assert len(path) >= 2
        # First turn must be OPEN.
        assert path[0] == TurnType.OPEN
        # Every consecutive pair must be admissible.
        for prev, nxt in zip(path, path[1:]):
            assert is_admissible(prev, nxt), f"{prev} -> {nxt} not admissible"

    def test_generate_conversation_record_shape(self):
        from cas_synthetic.generator.multi_turn.conversation_generator import (
            generate_conversation,
        )
        record = generate_conversation(seed=42, target_turns=6)
        assert isinstance(record, dict)
        for key in ("id", "turns", "final_cas_state", "dialog_path", "buckets_visited", "num_repairs"):
            assert key in record
        assert isinstance(record["turns"], list)
        assert len(record["turns"]) >= 2
        assert isinstance(record["final_cas_state"], str)
        assert isinstance(record["num_repairs"], int)
        assert record["num_repairs"] >= 0

    def test_generate_conversation_is_deterministic(self):
        from cas_synthetic.generator.multi_turn.conversation_generator import (
            generate_conversation,
        )
        a = generate_conversation(seed=99, target_turns=6)
        b = generate_conversation(seed=99, target_turns=6)
        assert a["dialog_path"] == b["dialog_path"]
        assert a["final_cas_state"] == b["final_cas_state"]

    def test_generate_conversation_supports_target_buckets(self):
        from cas_synthetic.generator.multi_turn.conversation_generator import (
            generate_conversation,
        )
        record = generate_conversation(
            seed=7,
            target_turns=4,
            target_buckets=["v74_baseline"],
        )
        assert "v74_baseline" in record["buckets_visited"]
