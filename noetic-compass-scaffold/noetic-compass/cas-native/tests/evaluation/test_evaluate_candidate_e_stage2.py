"""Tests for the Candidate E Stage 2 evaluator scoring helpers (2026-05-12).

The model-loading + decode path is not exercised here (requires a real
checkpoint + GPU); the helpers under test are the per-record recovery
scoring and the pair cross-emission counter — the metrics that define
the E2b gate semantics.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


_THIS_FILE = Path(__file__).resolve()
_EVAL_SCRIPT = (
    _THIS_FILE.parents[2]
    / "evaluation" / "evaluate_candidate_e_stage2.py"
)


@pytest.fixture(scope="module")
def evaluator_module():
    """Load the evaluator script as a module so we can call its helpers
    without invoking the CLI entrypoint."""
    spec = importlib.util.spec_from_file_location(
        "evaluate_candidate_e_stage2", str(_EVAL_SCRIPT),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _rec(rec_id: str, bodies: list[str], pair_id: str, variant_idx: int,
         middle: int = 5) -> dict:
    canon = [f"stageA0_{middle}_{bodies[0]}",
             f"stageD3_{middle}_{bodies[0]}",
             f"stageW2_{middle}_{bodies[0]}",
             f"stageP4_{middle}_{bodies[0]}"]
    return {
        "id": rec_id,
        "eval_meta": {
            "canonical_identifiers": canon,
            "body": bodies[0],
            "source_swap_pair_id": pair_id,
            "counterfactual_variant_idx": variant_idx,
        },
    }


def test_per_record_recovery_full(evaluator_module):
    """All four canonicals present in correct order → recovery_rate = 1.0."""
    rec = _rec("a", ["111"], "p1", 0)
    gen = ("Let stageA0_5_111 name X, stageD3_5_111 name Y, "
           "stageW2_5_111 name Z, stageP4_5_111 name W.")
    r = evaluator_module.per_record_recovery(rec, gen)
    assert r["applicable"]
    assert r["n_target"] == 4
    assert r["n_recovered"] == 4
    assert r["recovery_rate"] == 1.0


def test_per_record_recovery_memorization_signature(evaluator_module):
    """Member emits OTHER pair member's bodies — recovery=0,
    cross_emission=4. This is the A/B/C/D failure pattern we are hunting."""
    rec_a = _rec("a", ["111"], "p1", 0)
    rec_b = _rec("b", ["222"], "p1", 1)
    gen_a = ("Let stageA0_5_222 name X, stageD3_5_222 name Y, "
             "stageW2_5_222 name Z, stageP4_5_222 name W.")
    r = evaluator_module.per_record_recovery(rec_a, gen_a)
    ce = evaluator_module.pair_cross_emission(rec_a, rec_b, gen_a)
    assert r["recovery_rate"] == 0.0
    assert ce == 4


def test_per_record_recovery_wrong_order(evaluator_module):
    """Right bodies, wrong positions — positional match catches only the
    two that are at their canonical position."""
    rec = _rec("a", ["111"], "p1", 0)
    gen = ("Let stageD3_5_111 name X, stageA0_5_111 name Y, "
           "stageW2_5_111 name Z, stageP4_5_111 name W.")
    r = evaluator_module.per_record_recovery(rec, gen)
    assert r["n_recovered"] == 2, f"expected 2, got {r['n_recovered']}"


def test_per_record_recovery_partial(evaluator_module):
    """Only first canonical emitted; rest missing → 1/4, zero cross."""
    rec_a = _rec("a", ["111"], "p1", 0)
    rec_b = _rec("b", ["222"], "p1", 1)
    gen_a = "Let stageA0_5_111 name X. The rest is missing."
    r = evaluator_module.per_record_recovery(rec_a, gen_a)
    ce = evaluator_module.pair_cross_emission(rec_a, rec_b, gen_a)
    assert r["n_recovered"] == 1
    assert ce == 0


def test_pair_cross_emission_zero_when_other_bodies_absent(evaluator_module):
    """Pair cross-emission must not flag the SHARED distractor — only
    the other-member's CANONICAL bodies count."""
    rec_a = _rec("a", ["111"], "p1", 0)
    rec_b = _rec("b", ["222"], "p1", 1)
    # member A's output contains a shared distractor (body 845) but no
    # member-B canonical bodies → cross-emission should be 0
    gen_a = "Let stageA0_5_111 name X, distractor stageW3_5_845 elsewhere."
    ce = evaluator_module.pair_cross_emission(rec_a, rec_b, gen_a)
    assert ce == 0


def test_per_record_recovery_non_applicable(evaluator_module):
    """A record without canonical_identifiers (e.g. a non-rpm category) is
    not applicable for recovery scoring."""
    rec = {"id": "nr", "eval_meta": {}}
    r = evaluator_module.per_record_recovery(rec, "Some text.")
    assert r["applicable"] is False
    assert r["n_target"] == 0
    assert r["recovery_rate"] is None


def test_decode_records_tf_redirects_to_teacher_forced_eval(evaluator_module):
    """decode_records is the free-decode path. When called with tf_mode=True
    it must raise pointing the caller at teacher_forced_eval — the proper
    TF entrypoint per user audit 2026-05-12. Old test
    (test_tf_mode_raises_until_wired) renamed to reflect that TF is now
    actually implemented, just in a different function."""
    try:
        evaluator_module.decode_records(
            model=None, records=[], collator=None, tokenizer=None,
            device=None, max_new_tokens=8, tf_mode=True,
        )
    except NotImplementedError as exc:
        msg = str(exc).lower()
        assert "teacher_forced_eval" in msg, (
            f"raise must point at teacher_forced_eval; got: {msg!r}"
        )
        return
    raise AssertionError("decode_records(tf_mode=True) should have raised")


# ---------------------------------------------------------------------------
# Slot-trace helpers (Codex audit 2026-05-12 finding 1)
# ---------------------------------------------------------------------------

def test_longest_stage_var_run_basic(evaluator_module):
    """Longest contiguous STAGE_VAR (id=2) run in the trace."""
    # SLOT_CONNECTIVE=0, SLOT_OMEGA=1, SLOT_STAGE_VAR=2
    trace = [0, 2, 2, 2, 0, 2, 2, 0, 2, 2, 2, 2, 0]
    assert evaluator_module.longest_stage_var_run(trace) == 4


def test_longest_stage_var_run_all_other_slots(evaluator_module):
    """No STAGE_VAR positions → 0."""
    trace = [0, 1, 3, 4, 5, 6, 7, 0]
    assert evaluator_module.longest_stage_var_run(trace) == 0


def test_longest_stage_var_run_empty_trace(evaluator_module):
    """Empty trace → 0."""
    assert evaluator_module.longest_stage_var_run([]) == 0


def test_stage_var_token_count(evaluator_module):
    """Total STAGE_VAR positions across all spans."""
    trace = [0, 2, 2, 0, 2, 0, 2, 2, 2]
    assert evaluator_module.stage_var_token_count(trace) == 6


def test_stage_var_token_count_zero(evaluator_module):
    """No STAGE_VAR positions → 0."""
    assert evaluator_module.stage_var_token_count([0, 1, 0, 1]) == 0


# ---------------------------------------------------------------------------
# CLI gate behavior — e2b is blocked
# ---------------------------------------------------------------------------

def test_stage_e2b_now_supported_at_cli(evaluator_module):
    """--stage e2b is no longer blocked. The evaluator's argparse must
    accept it without raising. Actual model loading is exercised at the
    integration level (CPU smoke); this test just confirms the CLI
    surface is unblocked."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # Confirm the old raise is gone
    assert "--stage e2b is blocked" not in src
    # Confirm the new gate args are present
    assert "--gate-recovery" in src
    assert "--gate-swap" in src
    # Confirm fail-exit logic is present for e2b
    assert "return 2" in src
    assert "e2b_overall_pass" in src


def test_e2b_gate_is_tf_identifier_recovery(evaluator_module):
    """Per user audit 2026-05-12: E2b primary gate MUST be teacher-forced
    identifier-level recovery, NOT free-decode full_recovery_rate.

    Source-level checks (regression pins):
    - teacher_forced_eval helper exists and computes identifier_recovery_rate
    - The gate variable name in main() is tf_recovery_value (not the old
      free-decode recovery_value).
    - tf_dev_summary is the section the gate reads from.
    """
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    assert "def teacher_forced_eval(" in src, "TF eval helper missing"
    assert "tf_dev_summary" in src, "TF dev summary missing in main"
    assert "tf_recovery_value" in src, "TF recovery gate variable missing"
    assert 'tf_dev_summary.get("identifier_recovery_rate")' in src, (
        "Gate metric is not identifier_recovery_rate"
    )
    # The OLD gate variable name was `recovery_value` (read from free-decode
    # dev_summary). The NEW gate variable is `tf_recovery_value` (read from
    # TF dev summary). Lock the rename so a refactor doesn't silently
    # reintroduce the wrong gate.
    assert "tf_recovery_value = tf_dev_summary.get" in src, (
        "TF recovery gate must read from tf_dev_summary, not free-decode dev_summary"
    )
    # The old fail-exit used `recovery_gate_pass`; new uses `tf_recovery_gate_pass`.
    assert "tf_recovery_gate_pass" in src
    assert "overall_pass = tf_recovery_gate_pass" in src


def test_teacher_forced_eval_returns_identifier_level_metric(evaluator_module):
    """Smoke: teacher_forced_eval signature has the right shape — takes
    model + records + collator + device, returns per-record dicts with
    identifier_recovery_rate / per_token_accuracy keys.

    Real model execution is covered at integration level; here we just
    verify the function's contract by inspecting its source / globals."""
    assert hasattr(evaluator_module, "teacher_forced_eval")
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # Confirm the metric is identifier-level, not record-level
    assert "identifier_recovery_rate" in src
    assert "per_token_correct" in src
    assert "per_token_accuracy" in src
    # Confirm STAGE_VAR span scoring is present (gold src == argmax check)
    assert "argmax_src" in src
    assert "gold_src" in src or "typed_slot_source" in src


def test_identifier_level_recovery_distinct_from_full_recovery(evaluator_module):
    """Per user audit 2026-05-12: full_recovery_rate is record-level
    (all-or-nothing), identifier_recovery_rate is identifier-level (each
    ID counted independently). The TF summary must surface both.
    """
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # Both keys present in tf_dev_summary
    assert '"identifier_recovery_rate"' in src
    assert '"full_recovery_rate"' in src
    assert '"per_token_accuracy"' in src
