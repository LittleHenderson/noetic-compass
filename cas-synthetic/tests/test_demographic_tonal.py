"""Tests for the demographic + tonal SDG extension (Task #68).

Coverage:

1. Spec well-formedness: all 8 profiles + 5 tones present and fully
   specified.
2. Stratified sampling: deterministic given seed, covers profile space
   first, no duplicates.
3. Label preservation: every sacred field is byte-identical between
   canonical and variant.
4. Surface variation: different (profile, tone) pairs produce visibly
   different prompts.
5. End-to-end expansion: K=4 over a 10-record sample yields 40
   variants with no duplicates.
"""

from __future__ import annotations

import json
from pathlib import Path

from cas_synthetic.generator.demographic_tonal_axes import (
    ALL_PROFILE_TONE_PAIRS,
    PROFILES,
    PROFILE_BY_CODE,
    TONES,
    TONE_BY_CODE,
    profile_for,
    stratified_sample,
    tone_for,
)
from cas_synthetic.generator.demographic_tonal_rewrite import (
    SACRED_FIELDS,
    rewrite_record,
    rewrite_user_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _canonical_record(seed_idx: int = 0) -> dict:
    """Return a canonical Level 3 record mirroring the production schema."""
    return {
        "id": f"l3conv-test-{seed_idx:06d}",
        "source_level2_id": f"level2-{seed_idx:06d}",
        "bucket": "v75_register",
        "cas_expression": "^2^O_{F3}|T",
        "user_prompt": (
            "I am learning CAS. The target structure is families: "
            "state expression; states: Noetic ^2; domain O (operational); "
            "drive F3; register |T (meaning-level). What is the precise "
            "notation?"
        ),
        "natural_language_mapping": (
            "Recoverable mapping: the user prompt states families: state "
            "expression; states: Noetic ^2; domain O (operational); drive "
            "F3; register |T (meaning-level)."
        ),
        "assistant_response": (
            "Use ^2^O_{F3}|T. The notation preserves registers T."
        ),
        "follow_up_question": (
            "Would you like the same structure rewritten as a less formal "
            "user prompt?"
        ),
        "soft_operator_targets": [
            0.009091, 0.009091, 0.918182, 0.009091, 0.009091,
            0.009091, 0.009091, 0.009091, 0.009091, 0.00909,
        ],
        "soft_domain_targets": [0.009615, 0.009615, 0.009615, 0.971155],
        "tags": [
            "level3", "conversational", "v75_register",
            "recoverable_translation", "has_register",
        ],
        "provenance": {
            "level3_spec_version": "0.1.0",
            "generation_method": "deterministic_template",
            "seed": 42,
            "source_index": seed_idx,
            "source_level2_id": f"level2-{seed_idx:06d}",
        },
        # v77 schema additions
        "turn_type": "single",
        "expression_family": "state_expression",
        "transition_kind": "none",
        "noetic": "2",
        "domain": "O",
        "drive": "F3",
        "register_mode": "single",
        "registers": ["T"],
        "authority": "canonical",
        "has_omega": False,
        "has_meta_logic": False,
        "meta_relations": [],
        "prior_cas_state": None,
    }


# ---------------------------------------------------------------------------
# 1. Spec well-formedness
# ---------------------------------------------------------------------------


def test_eight_profiles_present_and_fully_specified():
    assert len(PROFILES) == 8
    expected_codes = {f"P{i}" for i in range(1, 9)}
    assert {p.code for p in PROFILES} == expected_codes
    for p in PROFILES:
        assert p.name and p.name.islower(), p
        assert p.description and len(p.description) > 20, p
        assert isinstance(p.speech_traits, tuple) and p.speech_traits
        assert isinstance(p.typical_lexicon, tuple) and len(p.typical_lexicon) >= 5
        assert isinstance(p.avoid_lexicon, tuple) and len(p.avoid_lexicon) >= 1
        assert isinstance(p.cultural_markers, tuple) and p.cultural_markers


def test_five_tones_present_and_fully_specified():
    assert len(TONES) == 5
    expected_codes = {f"T{i}" for i in range(1, 6)}
    assert {t.code for t in TONES} == expected_codes
    for t in TONES:
        assert t.name and t.name.islower(), t
        assert t.description and len(t.description) > 10, t
        assert isinstance(t.sentence_starters, tuple)
        assert isinstance(t.sentence_enders, tuple)
        assert 0.0 <= t.hedge_density <= 1.0
        assert t.energy_level in {"low", "medium", "high"}
        assert t.sentence_length_bias in {"short", "medium", "long"}


def test_profile_and_tone_lookups_round_trip():
    for p in PROFILES:
        assert profile_for(p.code) is p
        assert PROFILE_BY_CODE[p.code] is p
    for t in TONES:
        assert tone_for(t.code) is t
        assert TONE_BY_CODE[t.code] is t


def test_full_pair_pool_has_forty_unique_combinations():
    assert len(ALL_PROFILE_TONE_PAIRS) == 8 * 5
    assert len(set(ALL_PROFILE_TONE_PAIRS)) == 40


# ---------------------------------------------------------------------------
# 2. Stratified sampling
# ---------------------------------------------------------------------------


def test_stratified_sample_is_deterministic_under_same_seed():
    a = stratified_sample(k=4, seed=12345)
    b = stratified_sample(k=4, seed=12345)
    assert a == b


def test_stratified_sample_varies_with_seed():
    a = stratified_sample(k=4, seed=1)
    b = stratified_sample(k=4, seed=2)
    assert a != b


def test_stratified_sample_returns_no_duplicates_and_correct_size():
    for seed in range(0, 20):
        s = stratified_sample(k=4, seed=seed)
        assert len(s) == 4
        assert len(set(s)) == 4


def test_stratified_sample_k4_covers_four_distinct_profiles():
    """K=4 should hit 4 distinct profiles every time (Phase 1 covers space)."""
    for seed in range(0, 20):
        s = stratified_sample(k=4, seed=seed)
        profiles = {pair[0] for pair in s}
        assert len(profiles) == 4, (seed, s)


def test_stratified_sample_rejects_invalid_k():
    import pytest

    with pytest.raises(ValueError):
        stratified_sample(k=0, seed=1)
    with pytest.raises(ValueError):
        stratified_sample(k=41, seed=1)


# ---------------------------------------------------------------------------
# 3. Label preservation
# ---------------------------------------------------------------------------


def test_rewrite_preserves_every_sacred_field():
    canonical = _canonical_record(seed_idx=0)
    variant = rewrite_record(
        canonical, profile_code="P5", tone_code="T3"
    )

    # The id is regenerated by the driver script, but rewrite_record
    # itself preserves it.
    for field in SACRED_FIELDS:
        if field in canonical:
            assert variant[field] == canonical[field], (
                f"sacred field {field!r} was modified: "
                f"{canonical[field]!r} -> {variant[field]!r}"
            )
    # ``tags`` is intentionally NOT sacred (the rewriter appends
    # demographic-tonal sub-tags) but every original tag must survive.
    for tag in canonical.get("tags", []):
        assert tag in variant["tags"], (
            f"original tag {tag!r} was lost from variant['tags']"
        )


def test_rewrite_only_touches_user_prompt_and_metadata():
    canonical = _canonical_record(seed_idx=1)
    variant = rewrite_record(
        canonical, profile_code="P2", tone_code="T5"
    )
    diff_keys = {
        k for k in set(canonical) | set(variant)
        if canonical.get(k) != variant.get(k)
    }
    # user_prompt always changes; demographic_profile / tonal_register /
    # expansion_method are added; provenance gets demographic_tonal injected.
    expected_changes = {
        "user_prompt",
        "demographic_profile",
        "tonal_register",
        "expansion_method",
        "provenance",
        "tags",  # we add demographic-tonal tags
    }
    assert diff_keys.issubset(expected_changes), diff_keys


def test_metadata_fields_added():
    canonical = _canonical_record()
    variant = rewrite_record(
        canonical, profile_code="P3", tone_code="T4"
    )
    assert variant["demographic_profile"] == "P3"
    assert variant["tonal_register"] == "T4"
    assert variant["expansion_method"] == "rule_based_v1"
    prov = variant["provenance"]["demographic_tonal"]
    assert prov["profile_code"] == "P3"
    assert prov["tone_code"] == "T4"
    assert prov["expansion_method"] == "rule_based_v1"
    assert isinstance(prov["seed"], int)


def test_rewrite_returns_a_new_object_not_mutating_canonical():
    canonical = _canonical_record()
    snapshot = json.loads(json.dumps(canonical))
    rewrite_record(canonical, profile_code="P1", tone_code="T1")
    # Canonical record is unchanged.
    assert canonical == snapshot


def test_rewrite_is_deterministic_across_calls():
    canonical = _canonical_record()
    a = rewrite_record(canonical, profile_code="P5", tone_code="T3")
    b = rewrite_record(canonical, profile_code="P5", tone_code="T3")
    assert a["user_prompt"] == b["user_prompt"]
    assert a["provenance"]["demographic_tonal"]["seed"] == (
        b["provenance"]["demographic_tonal"]["seed"]
    )


# ---------------------------------------------------------------------------
# 4. Surface variation
# ---------------------------------------------------------------------------


def test_different_profiles_produce_different_prompts():
    canonical = _canonical_record()
    a = rewrite_record(canonical, profile_code="P1", tone_code="T1")
    b = rewrite_record(canonical, profile_code="P2", tone_code="T1")
    c = rewrite_record(canonical, profile_code="P5", tone_code="T1")
    d = rewrite_record(canonical, profile_code="P8", tone_code="T1")
    prompts = [a["user_prompt"], b["user_prompt"], c["user_prompt"], d["user_prompt"]]
    assert len(set(prompts)) == 4, prompts


def test_different_tones_produce_different_prompts():
    canonical = _canonical_record()
    prompts = []
    for tone in ("T1", "T2", "T3", "T4", "T5"):
        v = rewrite_record(canonical, profile_code="P5", tone_code=tone)
        prompts.append(v["user_prompt"])
    assert len(set(prompts)) == 5, prompts


def test_rewrite_preserves_slot_block_in_prompt():
    """The recoverable 'families: ...' anchor must appear in the rewrite.

    This is the structural payload the model trains on; the wrapper
    can change voice but the slot description must survive.
    """
    canonical = _canonical_record()
    variant = rewrite_record(
        canonical, profile_code="P5", tone_code="T3"
    )
    new_prompt = variant["user_prompt"]
    assert "families:" in new_prompt
    assert "Noetic ^2" in new_prompt
    assert "domain O" in new_prompt
    assert "drive F3" in new_prompt
    assert "register |T" in new_prompt


def test_rewrite_user_prompt_string_helper():
    base = (
        "I am learning CAS. The target structure is families: state "
        "expression; states: Noetic ^2. What is the notation?"
    )
    a = rewrite_user_prompt(base, profile_code="P1", tone_code="T1", seed=0)
    b = rewrite_user_prompt(base, profile_code="P5", tone_code="T3", seed=0)
    assert a != b
    assert "Noetic ^2" in a
    assert "Noetic ^2" in b


# ---------------------------------------------------------------------------
# 5. End-to-end K=4 expansion of a 10-record sample
# ---------------------------------------------------------------------------


def test_k4_expansion_of_ten_records_yields_forty_unique_variants(tmp_path: Path):
    """K=4 over a 10-record sample produces exactly 40 records, no
    (source_id, profile, tone) duplicates."""
    from cas_synthetic.generator.demographic_tonal_axes import stratified_sample
    from cas_synthetic.generator.demographic_tonal_rewrite import rewrite_record

    canonicals = [_canonical_record(seed_idx=i) for i in range(10)]

    seen: set[tuple[str, str, str]] = set()
    variants: list[dict] = []
    for record in canonicals:
        record_id = record["id"]
        # Match the driver's per-record seed derivation.
        import hashlib

        seed = int(
            hashlib.sha1(f"42|{record_id}".encode("utf-8")).hexdigest()[:12],
            16,
        )
        pairs = stratified_sample(k=4, seed=seed)
        for profile_code, tone_code in pairs:
            v = rewrite_record(
                record, profile_code=profile_code, tone_code=tone_code
            )
            key = (record_id, profile_code, tone_code)
            assert key not in seen, key
            seen.add(key)
            variants.append(v)

    assert len(variants) == 40
    # All user_prompts are non-trivial.
    for v in variants:
        assert isinstance(v["user_prompt"], str) and len(v["user_prompt"]) > 20


def test_driver_script_dry_run_against_inline_jsonl(tmp_path: Path):
    """The driver script reads JSONL and counts variants correctly."""
    import subprocess
    import sys as _sys

    repo_root = Path(__file__).resolve().parents[2]
    script = (
        repo_root / "cas-synthetic" / "scripts"
        / "expand_jsonl_demographic_tonal.py"
    )

    input_path = tmp_path / "in.jsonl"
    output_path = tmp_path / "out.jsonl"
    canonicals = [_canonical_record(seed_idx=i) for i in range(5)]
    with open(input_path, "w", encoding="utf-8") as f:
        for r in canonicals:
            f.write(json.dumps(r) + "\n")

    result = subprocess.run(
        [
            _sys.executable,
            str(script),
            "--input", str(input_path),
            "--output", str(output_path),
            "--variants-per-canonical", "4",
            "--seed", "42",
            "--progress-every", "0",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "demographic-tonal expansion complete" in result.stdout
    # 5 canonicals * K=4 = 20 variants.
    with open(output_path, encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]
    assert len(lines) == 20
    # Every variant has the metadata fields.
    parsed = [json.loads(line) for line in lines]
    for v in parsed:
        assert v["demographic_profile"] in {f"P{i}" for i in range(1, 9)}
        assert v["tonal_register"] in {f"T{i}" for i in range(1, 6)}
        assert v["expansion_method"] == "rule_based_v1"
