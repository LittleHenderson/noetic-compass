"""Canonical display names must keep CAS targets and distinguish revised rows."""

import hashlib
import json

import pytest

from cas_synthetic.generator.conversational import Level3ConversationalGenerator


NAMES = [
    "Idea", "Mind", "Positive", "Negative", "Vibration", "Female", "Male",
    "Rhythm", "Above/Cause", "Below/Effect",
]


def _record(noetic=6, *, response_suffix=""):
    generator = Level3ConversationalGenerator(seed=11, variants_per_source=1)
    # Fixed templates expose both revised naming slots and isolate content
    # identity from random template selection.
    generator.styles = [{
        "id": "canonical_names_fixture",
        "user_prompt_templates": ["Read {cas_expression}."],
        "natural_language_mapping_templates": ["{focus_summary}"],
        "assistant_response_templates": ["{cas_reading}" + response_suffix],
        "follow_up_question_templates": ["Explain its domain."],
    }]
    source = {
        "id": "canonical-source",
        "cas_expression": f"^{noetic}^C_{{F2}}|A",
        "_meta": {"bucket": "v75_register", "is_valid": True},
    }
    return next(generator.iter_source_record(source, source_index=0)).to_dict()


@pytest.mark.parametrize("noetic,name", enumerate(NAMES))
def test_canonical_name_slots_preserve_expression_and_numeric_targets(noetic, name):
    record = _record(noetic)
    assert record["cas_expression"] == f"^{noetic}^C_{{F2}}|A"
    assert f"^{noetic} ({name})" in record["natural_language_mapping"]
    assert f"^{noetic} {name} as the main noetic signal" in record["assistant_response"]
    # Frozen v1 outputs include its six-decimal rounding and final-bin repair.
    expected_operators = [0.009091] * 10
    expected_operators[noetic] = 0.918182
    expected_operators[-1] = 0.918181 if noetic == 9 else 0.009090
    assert record["soft_operator_targets"] == expected_operators
    assert record["soft_domain_targets"] == [0.009615, 0.971154, 0.009615, 0.009616]


def test_revised_records_are_deterministic_and_do_not_reuse_v1_identity():
    record = _record()
    assert record == _record()
    legacy_input = "11|canonical-source|0|canonical_names_fixture|^6^C_{F2}|A"
    legacy_id = "l3conv-" + hashlib.sha1(legacy_input.encode("utf-8")).hexdigest()[:12]
    assert record["id"] != legacy_id
    assert record["id"].startswith("l3conv-v2-")
    provenance = record["provenance"]
    assert provenance["generator_version"] == "level3_conversational_v2_canonical_names"
    assert provenance["record_identity_version"] == "2"
    assert provenance["conversation_id"] == record["id"]
    content = {key: value for key, value in record.items() if key not in {"id", "provenance"}}
    content_sha256 = hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert provenance["content_sha256"] == content_sha256


def test_changed_rendered_content_has_a_distinct_identity_with_the_same_source():
    first = _record()
    revised = _record(response_suffix=" Revised wording.")
    assert first["cas_expression"] == revised["cas_expression"]
    assert first["soft_operator_targets"] == revised["soft_operator_targets"]
    assert first["id"] != revised["id"]
    assert first["provenance"]["content_sha256"] != revised["provenance"]["content_sha256"]
