"""Pure text/data tests. No neural execution or learned capability is claimed."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import ast
import sys

import pytest

from cas_meta2 import features_v2 as f
from cas_meta2.codec import PolicyContractError


def public(problem="Alpha beta.", tags=("copper", "amber", "jade")):
    return {"problem": problem, "observations": [
        {"slot": slot, "tag": tag, "values": [slot + value / 10 for value in range(8)]}
        for slot, tag in enumerate(tags)]}


def tokenizer(**kwargs):
    return f.LosslessPublicTokenizer.fit_train([public()], **kwargs)


@pytest.mark.parametrize("text", [
    "Alpha alpha ALPHA", " \tAlpha\r\n  beta.\n", "p3 p4 p999 v15 v999",
    "Καλημέρα 世界 🚀", "e\u0301 é", "A\u00a0B\u2003C\u200bD", "[]{}:;?!,.\\/", "literal\x00text",
])
def test_unknown_text_round_trips_exact_case_whitespace_and_unicode(text):
    encoder = tokenizer()
    value = public(text, ("[PAD]", "Ω tag\t", "a\r\nb"))
    before = deepcopy(value)
    result = encoder.decode_public_text(encoder.encode_public(value))
    assert result == {"problem": text, "observations": [
        {"slot": row["slot"], "tag": row["tag"]} for row in value["observations"]]}
    assert encoder.check_round_trip(value) is True and value == before


def test_unknown_procedure_names_no_longer_collapse():
    encoder = tokenizer()
    left, right = public("p3"), public("p4")
    encoded_left, encoded_right = encoder.encode_public(left), encoder.encode_public(right)
    assert encoded_left["ids"] != encoded_right["ids"]
    assert encoder.decode_public_text(encoded_left)["problem"] == "p3"
    assert encoder.decode_public_text(encoded_right)["problem"] == "p4"
    assert "[UNK]" not in encoder.vocabulary


def test_byte_namespace_is_fixed_and_not_fitted_on_evaluation():
    first = tokenizer()
    second = f.LosslessPublicTokenizer.fit_train([public("Different train words!")])
    assert first.vocabulary[:f.WORD_START] == second.vocabulary[:f.WORD_START] == f.FIXED_VOCABULARY
    assert f.PAD_ID == 0 and f.BYTE_START == 5 and f.WORD_START == 261
    assert len(f.BYTE_VOCABULARY) == 256 and len(set(f.FIXED_VOCABULARY)) == 261
    before, checksum = first.to_dict(), first.digest
    first.encode_public(public("Entirely_unseen_p999 🧪", ("new1", "new2", "new3")))
    assert first.to_dict() == before and first.digest == checksum


def test_unknown_unicode_uses_full_utf8_bytes():
    encoder = tokenizer()
    result = encoder.encode_public(public("🚀"))
    sep = result["ids"].index(f.SEP_ID)
    ids = result["ids"][1:sep]
    assert ids == [f.BYTE_START + byte for byte in "🚀".encode("utf-8")]
    assert encoder.decode_text(ids) == "🚀"


def test_reserved_literal_strings_cannot_create_markers_even_when_trained():
    value = public("[PAD] [CLS] [SEP] [OBS] [VALUES] [BYTE:41] [WORD:41] [UNK]")
    encoder = f.LosslessPublicTokenizer.fit_train([value])
    ids = encoder.encode_public(value)["ids"]
    assert 0 not in ids and ids.count(f.CLS_ID) == 1 and ids.count(f.SEP_ID) == 1
    assert ids.count(f.OBS_ID) == 3 and ids.count(f.VALUES_ID) == 3
    assert encoder.check_round_trip(value)
    assert all(token.startswith("[WORD:") for token in encoder.vocabulary[f.WORD_START:])


def test_training_lexical_units_include_exact_whitespace_and_case():
    encoder = f.LosslessPublicTokenizer.fit_train([public("A a\t  a\n")])
    units = [f._word_value(token) for token in encoder.vocabulary[f.WORD_START:]]
    assert {"A", "a", "\t  ", "\n"} <= set(units)
    assert "A" != "a" and f._word_token("A") != f._word_token("a")


def test_kind_slot_and_numeric_layout_match_existing_contract():
    value = public("new token")
    value["observations"] = [value["observations"][2], value["observations"][0], value["observations"][1]]
    encoded = tokenizer().encode_public(value)
    assert set(encoded) == {"ids", "kinds", "slots", "values"}
    assert len({len(rows) for rows in encoded.values()}) == 1
    assert encoded["ids"][0] == f.CLS_ID and encoded["kinds"][0] == encoded["slots"][0] == 0
    numeric = [(slot, row) for kind, slot, row in zip(encoded["kinds"], encoded["slots"], encoded["values"]) if kind == 3]
    assert numeric == [(item["slot"] + 1, [float(v) for v in item["values"]])
                       for item in sorted(value["observations"], key=lambda item: item["slot"])]
    assert [slot for slot, _ in numeric] == [1, 2, 3]
    assert all(len(row) == 8 for row in encoded["values"])


def test_text_round_trip_does_not_claim_numeric_float_precision():
    value = public("Exact text")
    value["observations"][0]["values"][0] = 2**53 + 1
    encoder = tokenizer()
    encoded = encoder.encode_public(value)
    numeric = [values for kind, values in zip(encoded["kinds"], encoded["values"]) if kind == 3]
    assert numeric[0][0] == float(2**53 + 1) and numeric[0][0] != 2**53 + 1
    assert encoder.check_round_trip(value)
    assert "numeric tensors" in encoder.to_dict()["numeric_boundary"]


def test_serialized_round_trip_and_digest_are_deterministic():
    first = tokenizer()
    stored = json.loads(json.dumps(first.to_dict()))
    second = f.LosslessPublicTokenizer.from_dict(stored)
    assert second == first and second.digest == first.digest
    assert second.encode_public(public("Unseen P3\n")) == first.encode_public(public("Unseen P3\n"))
    stored["vocabulary"].append("caller copy mutation")
    assert second.vocabulary == first.vocabulary


@pytest.mark.parametrize("field,replacement", [
    ("max_length", True), ("max_length", 15), ("max_length", 65537), ("max_length", "1024"),
    ("fitted_examples", True), ("fitted_examples", 0), ("fitted_examples", 1.0),
    ("fitted_public_sha256", "0" * 63), ("fitted_public_sha256", "G" * 64),
    ("vocabulary", list(f.FIXED_VOCABULARY)), ("vocabulary", f.FIXED_VOCABULARY),
])
def test_manual_constructor_cannot_bypass_type_and_vocabulary_checks(field, replacement):
    with pytest.raises(PolicyContractError):
        replace(tokenizer(), **{field: replacement})


@pytest.mark.parametrize("change", ["fixed_marker", "missing_byte", "duplicate_word", "reordered_words", "invalid_utf8", "multiple_units", "word_integer"])
def test_malformed_vocabulary_is_rejected(change):
    value = tokenizer().to_dict()
    if change == "fixed_marker":value["vocabulary"][0] = "[UNK]"
    elif change == "missing_byte":del value["vocabulary"][100]
    elif change == "duplicate_word":value["vocabulary"].append(value["vocabulary"][-1])
    elif change == "reordered_words":value["vocabulary"][f.WORD_START:] = reversed(value["vocabulary"][f.WORD_START:])
    elif change == "invalid_utf8":value["vocabulary"][-1] = "[WORD:ff]"
    elif change == "multiple_units":value["vocabulary"][-1] = f._word_token("two words")
    else:value["vocabulary"][-1] = 123
    with pytest.raises(PolicyContractError):f.LosslessPublicTokenizer.from_dict(value)


@pytest.mark.parametrize("change", ["extra", "missing", "wrong_schema", "tuple_vocab", "string_vocab", "wrong_fit_split"])
def test_deserializer_has_closed_fields(change):
    value = tokenizer().to_dict()
    if change == "extra":value["gold"] = {}
    elif change == "missing":del value["numeric_boundary"]
    elif change == "wrong_schema":value["schema"] = "older"
    elif change == "tuple_vocab":value["vocabulary"] = tuple(value["vocabulary"])
    elif change == "string_vocab":value["vocabulary"] = "vocabulary"
    else:value["fit_split"] = "test"
    with pytest.raises(PolicyContractError):f.LosslessPublicTokenizer.from_dict(value)


@pytest.mark.parametrize("text", ["\ud800", "\udfff", "\ud83d\ude80"])
@pytest.mark.parametrize("location", ["problem", "tag"])
def test_invalid_unicode_is_rejected_in_training_and_encoding(text, location):
    value = public()
    if location == "problem":value["problem"] = text
    else:value["observations"][0]["tag"] = text
    with pytest.raises(PolicyContractError, match="INVALID_UNICODE"):
        tokenizer().encode_public(value)
    with pytest.raises(PolicyContractError, match="INVALID_UNICODE"):
        f.LosslessPublicTokenizer.fit_train([value])


def test_sequence_bound_rejects_without_truncation_at_exact_boundary():
    value = public("A B C")
    encoder = f.LosslessPublicTokenizer.fit_train([value], max_length=16)
    assert len(encoder.encode_public(value)["ids"]) == 16
    with pytest.raises(PolicyContractError, match="NO_SILENT_TRUNCATION"):
        encoder.encode_public(public("A B C "))
    with pytest.raises(PolicyContractError, match="NO_SILENT_TRUNCATION"):
        encoder.encode_public(public("X" * 100))
    with pytest.raises(PolicyContractError, match="NO_SILENT_TRUNCATION"):
        f.LosslessPublicTokenizer.fit_train([public("." * 100)], max_length=16)


@pytest.mark.parametrize("field", ["target", "gold", "task_id", "provenance", "program", "evaluator"])
def test_public_encoding_never_accepts_private_fields(field):
    value = public();value[field] = "not permitted"
    for action in (lambda:tokenizer().encode_public(value), lambda:tokenizer().check_round_trip(value),
                   lambda:f.LosslessPublicTokenizer.fit_train([value])):
        with pytest.raises(PolicyContractError, match="PUBLIC_INPUT_FIELDS_INVALID"):action()


@pytest.mark.parametrize("ids", [[True], [-1], [0], [1], [4], [999999], [1.0], [f.BYTE_START + 255], [f.BYTE_START + 195]])
def test_text_decoder_rejects_markers_bad_ids_and_broken_utf8(ids):
    with pytest.raises(PolicyContractError):tokenizer().decode_text(ids)


@pytest.mark.parametrize("change", ["extra", "unequal_lengths", "bool_kind", "wrong_slot", "bad_marker", "missing_end", "float_id", "numeric_shape", "nan", "text_values", "trailing"])
def test_public_decoder_rejects_malformed_feature_rows(change):
    encoder = tokenizer();encoded = encoder.encode_public(public())
    if change == "extra":encoded["gold"] = []
    elif change == "unequal_lengths":encoded["ids"].pop()
    elif change == "bool_kind":encoded["kinds"][0] = False
    elif change == "wrong_slot":encoded["slots"][1] = 3
    elif change == "bad_marker":encoded["ids"][0] = f.OBS_ID
    elif change == "missing_end":
        for rows in encoded.values():rows.pop()
    elif change == "float_id":encoded["ids"][1] = float(encoded["ids"][1])
    elif change == "numeric_shape":encoded["values"][-1] = [1.0]
    elif change == "nan":encoded["values"][-1][0] = float("nan")
    elif change == "text_values":encoded["values"][0][0] = 1.0
    else:
        for rows in encoded.values():rows.append(deepcopy(rows[0]))
    with pytest.raises(PolicyContractError):encoder.decode_public_text(encoded)


def test_missing_problem_and_invalid_numeric_values_are_typed_errors():
    value = public();del value["problem"]
    with pytest.raises(PolicyContractError):tokenizer().check_round_trip(value)
    value = public();value["observations"][0]["values"][0] = 10**1000
    with pytest.raises(PolicyContractError):tokenizer().encode_public(value)


def test_module_imports_no_model_parser_or_evaluator():
    source = ast.parse(Path(f.__file__).read_text(encoding="utf-8"))
    modules = {node.module for node in ast.walk(source) if isinstance(node, ast.ImportFrom)}
    modules |= {item.name for node in ast.walk(source) if isinstance(node, ast.Import) for item in node.names}
    assert modules <= {"__future__", "dataclasses", "hashlib", "json", "math", "re", "codec"}
    assert "torch" not in sys.modules and "numpy" not in sys.modules
