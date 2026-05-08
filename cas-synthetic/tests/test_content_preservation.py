"""Tests for `cas_synthetic.scoring.content_preservation`.

Layout follows the existing cas-synthetic test convention (single
`tests/` directory, `cas_synthetic.<subpackage>` import path registered
by `conftest.py`).

The scenarios cover:

1.  Each check's pass case.
2.  Each check's fail case.
3.  The four audit-known-bad records cited in the deliverable spec
    (recipe coefficient drop, fractal k-as-count, domain swap,
    invalid_to_corrected unrelated) — handcrafted records that mimic
    their structure so the test is deterministic without depending on
    the live corpus.
4.  Verbatim-copy detection on every english_to_cas record (covered by
    the synthesised english_to_cas case).
"""

from __future__ import annotations

import json

import pytest

from cas_synthetic.scoring.content_preservation import score_corpus, score_record


# ---------------------------------------------------------------------------
# Helpers — synthesise records that match the live-corpus shape exactly.
# ---------------------------------------------------------------------------


def _cas_to_english_record(
    *,
    sample_id: str,
    category: str,
    cas_expression: str,
    raw_response: str,
) -> dict:
    prompt = (
        "<<SYSTEM>>\nYou are a translator …\n<<USER>>\n"
        f"CAS expression (grammar category: {category}):\n\n"
        f"    {cas_expression}\n\n"
        "Write a concise, plain-English description …"
    )
    return {
        "sample_id": sample_id,
        "slot": "cas_to_english",
        "source_id": "test_seed",
        "source_grammar_category_or_error_class": category,
        "prompt_to_model": prompt,
        "raw_response": raw_response,
        "generated_cas": None,
        "compiler_validated": None,
        "leakage_in_reply": False,
    }


def _english_to_cas_record(
    *,
    sample_id: str,
    reference_cas: str,
    generated_cas: str,
) -> dict:
    prompt = (
        "<<SYSTEM>>\nYou are a translator …\n<<USER>>\n"
        "English description (grammar category: binary_composition):\n\n"
        f"    Express the following (binary_composition grammar slot) as compiler-valid CAS: | reference target (for guidance only — do not paste verbatim, render afresh): {reference_cas} | Noetic operators used: [0]\n\n"
        "Produce a valid CAS expression …"
    )
    return {
        "sample_id": sample_id,
        "slot": "english_to_cas",
        "source_id": "test_seed",
        "source_grammar_category_or_error_class": "binary_composition",
        "prompt_to_model": prompt,
        "raw_response": generated_cas,
        "generated_cas": generated_cas,
        "compiler_validated": True,
        "leakage_in_reply": False,
    }


def _invalid_to_corrected_record(
    *,
    sample_id: str,
    error_class: str,
    invalid_cas: str,
    corrected_cas: str,
    raw_response: str,
) -> dict:
    prompt = (
        "<<SYSTEM>>\nYou are a CAS repair assistant …\n<<USER>>\n"
        f"Invalid CAS expression (error class: {error_class}):\n\n"
        f"    {invalid_cas}\n\n"
        f"Corrected expression (the valid form):\n\n"
        f"    {corrected_cas}\n\n"
        "Compiler error on the invalid form:\n\n"
        "    typecheck: example error\n\n"
        "Describe the repair …"
    )
    return {
        "sample_id": sample_id,
        "slot": "invalid_to_corrected",
        "source_id": "test_seed",
        "source_grammar_category_or_error_class": error_class,
        "prompt_to_model": prompt,
        "raw_response": raw_response,
        "generated_cas": None,
        "compiler_validated": None,
        "leakage_in_reply": False,
    }


def _invalid_to_explanation_record(
    *,
    sample_id: str,
    error_class: str,
    invalid_cas: str,
    raw_response: str,
) -> dict:
    prompt = (
        "<<SYSTEM>>\nYou are an explainer …\n<<USER>>\n"
        f"Invalid CAS expression (error class: {error_class}):\n\n"
        f"    {invalid_cas}\n\n"
        "Compiler error message:\n\n"
        "    parsing@1: example error\n\n"
        "Explain in plain English what is wrong …"
    )
    return {
        "sample_id": sample_id,
        "slot": "invalid_to_explanation",
        "source_id": "test_seed",
        "source_grammar_category_or_error_class": error_class,
        "prompt_to_model": prompt,
        "raw_response": raw_response,
        "generated_cas": None,
        "compiler_validated": None,
        "leakage_in_reply": False,
    }


# ---------------------------------------------------------------------------
# Per-check pass + fail.
# ---------------------------------------------------------------------------


class TestCoefficientPreservation:
    def test_pass_when_all_coeffs_present(self):
        rec = _cas_to_english_record(
            sample_id="cp_pass",
            category="recipe",
            cas_expression="Θ(Ω_x) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_x + 0.05*Λ·Ω_side",
            raw_response=(
                "About 0.7 of close attention combines with 1.5 of careful "
                "reasoning to produce the result, with 0.05 spilling over."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["coefficient_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is True
        assert sorted(c["found"]) == ["0.05", "0.7", "1.5"]

    def test_fail_when_coeffs_dropped_audit_case(self):
        # wave3_resume_continue_cas_to_english_02331 — recipe with
        # coefficients 0.7 / 1.5 / 0.05 silently dropped.
        rec = _cas_to_english_record(
            sample_id="wave3_resume_continue_cas_to_english_02331_synth",
            category="recipe",
            cas_expression="Θ(Ω_reasoning_50) = 0.7*^9^C|A + 1.5*^1^P|A → Ω_reasoning_50 + 0.05*Λ·Ω_rehearsal_side",
            raw_response=(
                "To build up reasoning capacity, combine careful attention to "
                "foundational principles with strong draw toward cognitive "
                "insight. This generates a reasoning state, with a small "
                "amount of mental rehearsal happening alongside."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["coefficient_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert set(c["missing"]) == {"0.7", "1.5"}  # 0.05 maps to "small amount" alias
        assert "coefficient_drop" in r["failure_reasons"]

    def test_not_applicable_when_not_recipe(self):
        rec = _cas_to_english_record(
            sample_id="cp_na",
            category="binary_composition",
            cas_expression="^0^P|A + ^0^P|T",
            raw_response="ignored",
        )
        r = score_record(rec)
        assert r["checks"]["coefficient_preservation"]["applicable"] is False
        assert r["checks"]["coefficient_preservation"]["pass"] is True


class TestDomainRegisterPreservation:
    def test_pass_when_domain_and_register_present(self):
        rec = _cas_to_english_record(
            sample_id="dr_pass",
            category="binary_composition",
            cas_expression="^5^C|T + ^5^C|f",
            raw_response=(
                "Two threads at the cognitive level of who I am: one read in "
                "the deeper meaning of it, the other in the felt sense — both "
                "are part of the sum of one's experiences."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["domain_register_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is True

    def test_fail_audit_case_domain_swap(self):
        # wave3_resume_continue_cas_to_english_00001 — `^5^C|T + ^5^C|f`
        # rendered with one term moved to evaluative domain. The model
        # mentions "evaluative" alongside "cognitive"; the source has only
        # the cognitive domain, but our scorer covers source-side coverage,
        # so the failure mode that gets caught is the missing register
        # alias for `T` (no transcendent / big-picture / meaning words).
        rec = _cas_to_english_record(
            sample_id="wave3_resume_continue_cas_to_english_00001_synth",
            category="binary_composition",
            cas_expression="^5^C|T + ^5^C|f",
            raw_response=(
                "The sum of who you are in the cognitive domain, combined with "
                "the sum of who you are in the evaluative domain — these two "
                "aspects of yourself join together."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["domain_register_preservation"]
        assert c["applicable"] is True
        # Missing T register alias (no "transcendent", "meaning", "big picture", etc).
        assert c["pass"] is False
        assert "R:T" in c["missing"]
        assert "domain_or_register_swap_or_drop" in r["failure_reasons"]


class TestDriveNoeticPreservation:
    def test_pass_when_drive_alias_present(self):
        rec = _cas_to_english_record(
            sample_id="dn_pass",
            category="drive_anchored",
            cas_expression="^2^C_{F4}",
            raw_response="A pull toward connection with someone close.",
        )
        r = score_record(rec)
        c = r["checks"]["drive_noetic_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is True

    def test_fail_when_drive_dropped(self):
        rec = _cas_to_english_record(
            sample_id="dn_fail",
            category="drive_anchored",
            cas_expression="^2^C_{F4}",
            raw_response="An attraction toward something cognitive.",  # no F4 alias
        )
        r = score_record(rec)
        c = r["checks"]["drive_noetic_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert "F4" in c["missing"]


class TestOmegaTargetPreservation:
    def test_pass_when_omega_humanised(self):
        rec = _cas_to_english_record(
            sample_id="om_pass",
            category="recipe",
            cas_expression="Θ(Ω_clarity) = 1*^1^C|A → Ω_clarity",
            raw_response="Pure attention produces a sense of clarity.",
        )
        r = score_record(rec)
        c = r["checks"]["omega_target_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is True

    def test_fail_when_omega_dropped(self):
        rec = _cas_to_english_record(
            sample_id="om_fail",
            category="recipe",
            cas_expression="Θ(Ω_clarity) = 1*^1^C|A → Ω_clarity",
            raw_response="Pure attention produces a particular state.",
        )
        r = score_record(rec)
        c = r["checks"]["omega_target_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert "clarity" in c["missing"]


class TestFractalKIndexPreservation:
    def test_pass_when_k_aliases_present(self):
        rec = _cas_to_english_record(
            sample_id="fr_pass",
            category="fractal_sequence",
            cas_expression="Phi<9:4:7>",
            raw_response=(
                "What surfaced — the thought just arrived — and it struck a "
                "chord, settling into muscle-memory practice."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["fractal_k_index_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is True
        assert c["k_as_count_flag"] is False

    def test_fail_audit_case_k_as_count(self):
        # wave3_resume_cas_to_english_03327 — `Phi<9:4:7>` rendered as
        # "9 domains, 4 operations, 7 pathways".
        rec = _cas_to_english_record(
            sample_id="wave3_resume_cas_to_english_03327_synth",
            category="fractal_sequence",
            cas_expression="Phi<9:4:7>",
            raw_response=(
                "A foundational connection across nine domains, structured "
                "through four distinct cognitive operations, with seven "
                "relational pathways active."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["fractal_k_index_preservation"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert c["k_as_count_flag"] is True
        # The combined failure label should carry the k_as_count suffix.
        assert any(fr.endswith("::k_as_count") for fr in r["failure_reasons"])


class TestInvalidCorrectedPairOverlap:
    """v2 rename: `invalid_corrected_overlap` → `invalid_corrected_pair_overlap`.

    The check measures Jaccard between the SOURCE invalid CAS and the
    SOURCE corrected CAS (both extracted from the prompt). It does NOT
    measure faithfulness of the model's English narration to the actual
    fix. A FAIL indicates the upstream training pair is broken.
    """

    def test_pass_when_minimal_edit(self):
        rec = _invalid_to_corrected_record(
            sample_id="ic_pass",
            error_class="admissibility",
            invalid_cas="^13^E|f + ^1^E|E",
            corrected_cas="^1^E|f + ^1^E|E",
            raw_response="The first part used an out-of-range index. Replacing 13 with 1 makes it valid.",
        )
        r = score_record(rec)
        c = r["checks"]["invalid_corrected_pair_overlap"]
        assert c["applicable"] is True
        # Token sets: {^13^E|f, +, ^1^E|E} vs {^1^E|f, +, ^1^E|E} —
        # 2 shared, 4 union -> 0.5 — suspicious tier, not pass.
        assert c["jaccard"] >= 0.4
        assert c["severity"] in ("ok", "suspicious")

    def test_fail_audit_case_unrelated_pair(self):
        # wave3_resume_continue_invalid_to_corrected_00760 — the
        # underlying training PAIR has unrelated structure (the
        # corrector wrote a fresh expression instead of a minimal
        # edit). This is an upstream corpus defect, not direct
        # evidence about the model's English narration.
        rec = _invalid_to_corrected_record(
            sample_id="wave3_resume_continue_invalid_to_corrected_00760_synth",
            error_class="rpm",
            invalid_cas=(
                "let stageA_4_1204 = ^3^O_{F4}; let stageB_4_1204 = ^3^C_{F4}; "
                "stageA_4_1204 -> stageB_4_1204"
            ),
            corrected_cas="^7^C + ^1^C",
            raw_response="The original tried an illegal transition. The fix swaps to two unrelated states.",
        )
        r = score_record(rec)
        c = r["checks"]["invalid_corrected_pair_overlap"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert c["severity"] == "unrelated"
        assert c["jaccard"] < 0.2
        assert "invalid_corrected_pair_unrelated" in r["failure_reasons"]

    def test_legacy_key_no_longer_present(self):
        # The old `invalid_corrected_overlap` key was renamed in v2.
        # Make sure consumers reading by old name notice the change.
        rec = _invalid_to_corrected_record(
            sample_id="ic_legacy",
            error_class="parse",
            invalid_cas="^0^P + ^0^P",
            corrected_cas="^0^P + ^0^P",
            raw_response="No-op fix.",
        )
        r = score_record(rec)
        assert "invalid_corrected_pair_overlap" in r["checks"]
        assert "invalid_corrected_overlap" not in r["checks"]


class TestInvalidToExplanationLightweightChecks:
    """v2 addition: four LIGHTWEIGHT HEURISTIC checks for the
    `invalid_to_explanation` slot.

    These are HEURISTICS, not equivalent to the cas_to_english structural
    preservation checks. Tests confirm the labels and gate behaviours,
    not faithfulness.
    """

    def test_explanation_length_pass(self):
        rec = _invalid_to_explanation_record(
            sample_id="ex_len_pass",
            error_class="parse",
            invalid_cas="^0^|A + ^0^P|T",
            raw_response=(
                "The expression breaks down at the spot where a subject area "
                "should appear; the format is missing one of its expected pieces."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["explanation_length"]
        assert c["applicable"] is True
        assert c["pass"] is True
        assert 30 <= c["char_len"] <= 500

    def test_explanation_length_fail_too_short(self):
        rec = _invalid_to_explanation_record(
            sample_id="ex_len_short",
            error_class="parse",
            invalid_cas="^0^|A + ^0^P|T",
            raw_response="Bad.",
        )
        r = score_record(rec)
        c = r["checks"]["explanation_length"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert "explanation_length_out_of_range" in r["failure_reasons"]

    def test_explanation_length_fail_too_long(self):
        rec = _invalid_to_explanation_record(
            sample_id="ex_len_long",
            error_class="parse",
            invalid_cas="^0^|A + ^0^P|T",
            raw_response="word " * 200,  # >> 500 chars
        )
        r = score_record(rec)
        c = r["checks"]["explanation_length"]
        assert c["pass"] is False

    def test_explanation_specificity_pass(self):
        # Source contains ^0 (Idea) and ^P domain — reply mentions
        # "ideas" and "principled / fundamental" so it's specific.
        rec = _invalid_to_explanation_record(
            sample_id="ex_spec_pass",
            error_class="parse",
            invalid_cas="^0^P|A + ^0^P|T",
            raw_response=(
                "The expression mixes principled ideas with reasoned analysis "
                "but the format is missing a piece, so the structure breaks down."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["explanation_specificity"]
        assert c["applicable"] is True
        assert c["pass"] is True
        assert any(s.startswith("D:P") or s == "^0" for s in c["matched_signals"])

    def test_explanation_specificity_fail_generic(self):
        # Generic boilerplate that mentions nothing structurally tied to
        # ^4 Vibration or the C domain.
        rec = _invalid_to_explanation_record(
            sample_id="ex_spec_fail",
            error_class="parse",
            invalid_cas="^4^C|A",
            raw_response=(
                "Something appears to be off in the way the parts are arranged, "
                "and the system has flagged it as not acceptable in this form."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["explanation_specificity"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert "explanation_not_specific_to_source" in r["failure_reasons"]

    def test_explanation_anti_jargon_pass(self):
        rec = _invalid_to_explanation_record(
            sample_id="ex_jargon_pass",
            error_class="rpm",
            invalid_cas="let A = ^0^P; A -> B",
            raw_response=(
                "The expression hands something off to a destination that was "
                "never named; the chain has no place to land its result."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["explanation_anti_jargon"]
        assert c["applicable"] is True
        assert c["pass"] is True
        assert c["jargon_hits"] == []

    def test_explanation_anti_jargon_fail_on_leak(self):
        rec = _invalid_to_explanation_record(
            sample_id="ex_jargon_fail",
            error_class="parse",
            invalid_cas="^0^|A + ^0^P|T",
            raw_response=(
                "The Noetic operator at position one is missing its register, "
                "so the parser can't validate the F1 drive subscript."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["explanation_anti_jargon"]
        assert c["applicable"] is True
        assert c["pass"] is False
        # Multiple jargon terms should be caught.
        assert any(h.lower() in ("noetic", "register", "f1") for h in c["jargon_hits"])
        assert "explanation_leaks_cas_jargon" in r["failure_reasons"]

    def test_explanation_error_class_alignment_pass_rpm(self):
        rec = _invalid_to_explanation_record(
            sample_id="ex_align_rpm_pass",
            error_class="rpm",
            invalid_cas="let A = ^0^P; A -> B",
            raw_response=(
                "The chain hands off to a destination that was never defined; "
                "the sequence has no second step to deliver its result to."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["explanation_error_class_alignment"]
        assert c["applicable"] is True
        assert c["pass"] is True
        # "chain", "sequence", "step", "destination" are all RPM terms.
        assert len(c["matched_terms"]) >= 1

    def test_explanation_error_class_alignment_fail_off_class(self):
        # An rpm error explained only with vocabulary unrelated to chains
        # / sequences / steps fails the alignment check.
        rec = _invalid_to_explanation_record(
            sample_id="ex_align_rpm_fail",
            error_class="rpm",
            invalid_cas="let A = ^0^P; A -> B",
            raw_response=(
                "The notation seems wrong somehow. The arrangement of pieces "
                "doesn't pass muster and the system finds it problematic."
            ),
        )
        r = score_record(rec)
        c = r["checks"]["explanation_error_class_alignment"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert "explanation_off_error_class" in r["failure_reasons"]

    def test_explanation_error_class_alignment_unfamiliar_class_not_applicable(self):
        # Unknown error class — check should mark not-applicable rather
        # than fail.
        rec = _invalid_to_explanation_record(
            sample_id="ex_align_unknown",
            error_class="some_new_class_not_in_table",
            invalid_cas="^0^P",
            raw_response="A passable but generic explanation that goes on for enough characters.",
        )
        r = score_record(rec)
        c = r["checks"]["explanation_error_class_alignment"]
        assert c["applicable"] is False
        assert c["pass"] is True


class TestEnglishToCasAntiCopy:
    def test_fail_on_verbatim_copy(self):
        # All english_to_cas records in the audited corpus exhibit this:
        # the prompt embeds the CAS as "reference target", and the model
        # echoes it verbatim.
        rec = _english_to_cas_record(
            sample_id="ec_fail",
            reference_cas="^0^P|A + ^0^P|T",
            generated_cas="^0^P|A + ^0^P|T",
        )
        r = score_record(rec)
        c = r["checks"]["english_to_cas_anti_copy"]
        assert c["applicable"] is True
        assert c["pass"] is False
        assert c["is_verbatim_copy"] is True
        assert "english_to_cas_verbatim_copy" in r["failure_reasons"]

    def test_pass_when_genuine_translation(self):
        rec = _english_to_cas_record(
            sample_id="ec_pass",
            reference_cas="^0^P|A + ^0^P|T",
            generated_cas="^0^P|T + ^0^P|A",
        )
        r = score_record(rec)
        c = r["checks"]["english_to_cas_anti_copy"]
        assert c["applicable"] is True
        assert c["pass"] is True
        assert c["is_verbatim_copy"] is False


# ---------------------------------------------------------------------------
# Corpus-level smoke — score_corpus end-to-end against a small JSONL.
# ---------------------------------------------------------------------------


def test_score_corpus_smoke(tmp_path):
    records = [
        _cas_to_english_record(
            sample_id="smoke1",
            category="binary_composition",
            cas_expression="^2^P|A + ^2^P|T",
            raw_response="A principled draw toward something, both in reasoned form and in deeper meaning.",
        ),
        _english_to_cas_record(
            sample_id="smoke2",
            reference_cas="^0^P|A + ^0^P|T",
            generated_cas="^0^P|A + ^0^P|T",  # verbatim copy = FAIL
        ),
    ]
    src = tmp_path / "tiny.jsonl"
    src.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    out_csv = tmp_path / "scores.csv"
    summary_json = tmp_path / "summary.json"
    summary = score_corpus(src, out_csv, summary_json)
    assert summary["total_records"] == 2
    assert summary["by_slot"]["english_to_cas"]["passes"] == 0
    # The cas_to_english smoke uses ^2^P with both A and T registers —
    # should pass.
    assert summary["by_slot"]["cas_to_english"]["passes"] == 1
    text = out_csv.read_text(encoding="utf-8")
    assert "smoke1" in text and "smoke2" in text
    assert "english_to_cas_verbatim_copy" in text


# ---------------------------------------------------------------------------
# Audit-known-bad records on the live corpus — gated, opt-in.
# ---------------------------------------------------------------------------


# These IDs are cited in the deliverable spec; running them validates
# that the scorer correctly flags them when the actual corpus is on
# disk. Skipped if the corpus isn't present (e.g. CI without the data).
_AUDIT_KNOWN_BAD_IDS = [
    "wave3_resume_continue_cas_to_english_02331",
    "wave3_resume_cas_to_english_03327",
    "wave3_resume_continue_cas_to_english_00001",
    "wave3_resume_continue_invalid_to_corrected_00760",
]


@pytest.mark.parametrize("target_id", _AUDIT_KNOWN_BAD_IDS)
def test_audit_known_bad_records_flagged(target_id):
    from pathlib import Path

    corpus = (
        Path(__file__).resolve().parents[2]
        / "cas-synthetic"
        / "data"
        / "path_d"
        / "wave3_phase1_aggregate_20260508.jsonl"
    )
    if not corpus.exists():
        pytest.skip("live corpus not present — skip audit-known-bad regression check")

    target_record = None
    with corpus.open("r", encoding="utf-8") as f:
        for line in f:
            if f'"sample_id": "{target_id}"' in line:
                target_record = json.loads(line)
                break

    assert target_record is not None, f"could not locate {target_id} in corpus"
    result = score_record(target_record)
    assert result["overall_pass"] is False, (
        f"{target_id} should be flagged as failure but passed: {result}"
    )
