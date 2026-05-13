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


def test_e2c_gate_only_per_token_load_bearing(evaluator_module):
    """Per user audit 2026-05-12 post-E2c-build: at --stage e2c, ONLY
    tf_per_token_accuracy is load-bearing. Swap pair_pass_rate and
    identifier_recovery_rate are informational diagnostics — a model that
    hits 75% per-token but stays low on swap is E2c PASS.

    Source-level regression pin: the e2c overall_pass computation must
    be exactly `tf_per_token_gate_pass` (no AND with swap_gate_pass).
    """
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # Find ALL lines that assign overall_pass; the e2c branch must produce
    # one whose RHS is exactly tf_per_token_gate_pass.
    op_lines = [
        line.strip() for line in src.splitlines()
        if line.strip().startswith("overall_pass =")
    ]
    # We expect both an e2c-style line and an e2b-style line.
    e2c_lines = [
        l for l in op_lines if l == "overall_pass = tf_per_token_gate_pass"
    ]
    e2b_lines = [
        l for l in op_lines
        if l == "overall_pass = tf_recovery_gate_pass and swap_gate_pass"
    ]
    assert e2c_lines, (
        f"e2c overall_pass must be exactly 'tf_per_token_gate_pass' "
        f"(no AND with swap_gate_pass); found assignments: {op_lines!r}"
    )
    assert e2b_lines, (
        f"e2b overall_pass must AND tf_recovery_gate_pass AND "
        f"swap_gate_pass; found assignments: {op_lines!r}"
    )


def test_e2b_gate_still_requires_both(evaluator_module):
    """Regression: e2b gate semantics unchanged — both TF identifier
    recovery AND swap pair_pass must pass for e2b overall_pass=True."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # Look for the e2b/else branch in the gate-pass logic
    assert "overall_pass = tf_recovery_gate_pass and swap_gate_pass" in src, (
        "e2b gate must AND swap_gate_pass with tf_recovery_gate_pass"
    )


# ---------------------------------------------------------------------------
# Stage 3 evaluator modes — e3-baseline (informational) + e3 (enforced).
# Per Codex audit 2026-05-13T02:36Z (commit ee8dfa4), Order B: implement
# evaluator modes FIRST, add tests, surface for audit, then user "go" on
# the pod baseline measurement. These tests pin the CLI surface and gate
# semantics so a refactor cannot silently change Stage 3 decision logic.
# ---------------------------------------------------------------------------

def test_stage_e3_modes_in_argparse_choices(evaluator_module):
    """--stage must accept both e3-baseline (informational, measures
    free-decode behavior of E2c checkpoint BEFORE training) and e3
    (post-training enforced gate)."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # The argparse choices list must include both modes
    assert '"e3-baseline"' in src, "e3-baseline missing from --stage choices"
    assert '"e3"' in src, "e3 missing from --stage choices"
    # The e2c choice must still be present (no regression)
    assert '"e2c"' in src
    assert '"e2b"' in src


def test_stage_e3_cli_gate_args_present(evaluator_module):
    """--gate-e3-recovery (default 0.50, PRIMARY) and --gate-e3-strong
    (default 0.70, strong-pass annotation) must be declared as CLI args.
    These are separate from --gate-recovery (E2b TF) so an operator
    cannot accidentally collapse the two gates."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    assert "--gate-e3-recovery" in src, (
        "PRIMARY Stage 3 free-decode gate flag missing"
    )
    assert "--gate-e3-strong" in src, (
        "Strong-pass Stage 3 annotation flag missing"
    )
    # Defaults must match the Codex-ratified thresholds
    assert "default=0.50" in src and "--gate-e3-recovery" in src
    assert "default=0.70" in src and "--gate-e3-strong" in src


def test_stage_e3_overall_pass_is_recovery_and_safety(evaluator_module):
    """At --stage e3, overall_pass MUST be:
        free-decode recovery_rate >= gate_e3_recovery
      AND
        swap cross_emission_count == 0  (hard safety)

    Both are load-bearing. A model that meets recovery but emits ANY
    cross-pair body fails. A model with zero cross-emission but
    sub-threshold recovery fails. This pins the AND semantics."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # Find ALL lines that assign overall_pass; the e3 branch must AND
    # the recovery gate and the safety gate.
    op_lines = [
        line.strip() for line in src.splitlines()
        if line.strip().startswith("overall_pass =")
    ]
    e3_lines = [
        l for l in op_lines
        if "e3_recovery_gate_pass" in l and "e3_safety_gate_pass" in l
        and " and " in l
    ]
    assert e3_lines, (
        f"e3 overall_pass must AND e3_recovery_gate_pass AND "
        f"e3_safety_gate_pass; found assignments: {op_lines!r}"
    )


def test_stage_e3_baseline_is_informational_only(evaluator_module):
    """At --stage e3-baseline, overall_pass MUST be True regardless of
    measured metrics. This mode measures the E2c-continuation checkpoint
    on free-decode BEFORE Stage 3 training; its purpose is to decide
    whether Stage 3 training is even needed, not to fail-exit the run.

    Per Codex 2026-05-13: <0.50 → run Stage 3; 0.50-0.70 → confirm and
    decide; >=0.70 → strong pass, skip Stage 3 entirely. None of those
    branches are fail-exits at this stage; they are operator decisions."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # Look for the e3-baseline overall_pass = True line
    assert 'args.stage == "e3-baseline"' in src, (
        "e3-baseline argparse branch missing in main()"
    )
    # The branch body must assign overall_pass = True
    # (informational-only — no fail-exit)
    e3_baseline_block_present = False
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if 'args.stage == "e3-baseline"' in line:
            # Check the next ~5 lines for the True assignment
            for j in range(i, min(i + 8, len(lines))):
                if "overall_pass = True" in lines[j]:
                    e3_baseline_block_present = True
                    break
    assert e3_baseline_block_present, (
        "e3-baseline branch must assign overall_pass = True "
        "(informational-only mode, no fail-exit)"
    )


def test_stage_e3_fail_exit_excludes_e3_baseline(evaluator_module):
    """Fail-exit (return 2) must fire for --stage in {e2b, e2c, e3} when
    overall_pass is False, but NEVER for --stage e3-baseline (which is
    informational, used as decision-point telemetry only).

    This pin protects against a refactor that adds e3-baseline to the
    fail-exit set and turns a measurement command into a CI failure."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # The fail-exit predicate must include e3
    assert 'args.stage in ("e2b", "e2c", "e3")' in src or \
           "args.stage in ('e2b', 'e2c', 'e3')" in src, (
        "Fail-exit predicate must include e3 (and exclude e3-baseline)"
    )
    # And NOT include e3-baseline inside the predicate tuple itself.
    # Comments above/below the predicate may legitimately mention the
    # name (explaining the exclusion); the failure mode this test guards
    # against is the literal "e3-baseline" string appearing inside the
    # tuple passed to `args.stage in (...)` next to a `return 2`.
    forbidden_tuple_forms = [
        'args.stage in ("e2b", "e2c", "e3", "e3-baseline")',
        "args.stage in ('e2b', 'e2c', 'e3', 'e3-baseline')",
        'args.stage in ("e3-baseline"',
        "args.stage in ('e3-baseline'",
    ]
    for forbidden in forbidden_tuple_forms:
        assert forbidden not in src, (
            f"Fail-exit predicate must NOT include 'e3-baseline'; "
            f"found pattern: {forbidden!r}"
        )


def test_stage_e3_safety_gate_reads_swap_cross_emission(evaluator_module):
    """The hard-safety gate at --stage e3 must read swap-set
    cross_emission_count (NOT TF set, NOT individual-record level).
    Free-decode cross-pair body emission on the swap eval is the
    canonical safety signal."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    # Confirm the swap-summary read path for cross-emission
    assert "swap_cross_emission_total" in src, (
        "e3 safety gate variable swap_cross_emission_total missing"
    )
    assert "e3_safety_gate_pass" in src
    # Must compare against 0 (zero tolerance — any cross emission fails)
    # The comparison must use the swap totals, not the TF totals.
    safety_line_found = False
    for line in src.splitlines():
        if "e3_safety_gate_pass" in line and "==" in line and "0" in line:
            safety_line_found = True
            break
    assert safety_line_found, (
        "e3_safety_gate_pass assignment must compare cross_emission_total == 0"
    )


def test_stage_e3_recovery_gate_reads_free_decode_aggregate(evaluator_module):
    """The PRIMARY gate at --stage e3 must read the FREE-DECODE
    aggregate_recovery_rate (from dev_summary, not tf_dev_summary).
    Stage 3's whole point is deployment-distribution behavior (no TF)."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    assert "free_decode_recovery_value" in src, (
        "e3 primary gate variable free_decode_recovery_value missing"
    )
    # Must read from dev_summary (free-decode), NOT tf_dev_summary
    free_decode_read_found = False
    for line in src.splitlines():
        if "free_decode_recovery_value" in line and "dev_summary.get" in line \
                and "tf_dev_summary" not in line:
            free_decode_read_found = True
            break
    assert free_decode_read_found, (
        "free_decode_recovery_value must be read from dev_summary "
        "(free-decode), not tf_dev_summary"
    )


def test_stage_e3_gates_dict_surfaces_both_e3_keys(evaluator_module):
    """The gates dict written to findings.md / report.json must surface
    BOTH e3 gate metrics (recovery PRIMARY + cross-emission HARD SAFETY)
    so operators reading the JSON can see both load-bearing values."""
    src = open(evaluator_module.__file__, encoding="utf-8").read()
    assert '"e3_free_decode_recovery"' in src, (
        "gates dict must surface e3_free_decode_recovery key"
    )
    assert '"e3_cross_emission_safety"' in src, (
        "gates dict must surface e3_cross_emission_safety key"
    )
