"""Pure feature tests; no model, tensor, target parsing or provider calls."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import random

import pytest

from cas_meta2.codec import (ACTION_TO_ID, CJT_NAMES, PROCEDURE_NAMES, VARIABLE_NAMES,
                             PolicyContractError)
from cas_meta2.features_v2 import LosslessPublicTokenizer, WORD_START
from cas_meta2.features_v3 import COPY_SYMBOLS, encode_public_with_spans, symbol_occurrences


def public(problem="main p0 arg v0 A"):
    return {"problem": problem, "observations": [
        {"slot": slot, "tag": tag, "values": [0.125 * (slot + 1)] * 8}
        for slot, tag in enumerate(("amber", "blue", "green"))]}


def test_frozen_tokenizer_bytes_are_unchanged():
    path = Path(__file__).parents[1] / "cas_meta2" / "features_v2.py"
    assert sha256(path.read_bytes()).hexdigest() == "79dd26ad6183cde7e586dda2cd1b65d812e601e793d5c60e0658ad886c09b4dc"


def test_exact_full_codec_symbol_vocabulary_without_control_tokens():
    assert COPY_SYMBOLS == PROCEDURE_NAMES + VARIABLE_NAMES + CJT_NAMES
    assert len(COPY_SYMBOLS) == 54 and len(set(COPY_SYMBOLS)) == 54
    assert "v31" in COPY_SYMBOLS and "R" in COPY_SYMBOLS
    assert not {"RUN", "CALL", "RETURN", "BIND0", "[EOS]"}.intersection(COPY_SYMBOLS)


@pytest.mark.parametrize("fitted", [True, False])
def test_every_symbol_round_trips_at_its_exact_encoded_and_character_span(fitted):
    item = public("\t" + "\n(".join(COPY_SYMBOLS) + ")\r\n")
    tokenizer = LosslessPublicTokenizer.fit_train([item if fitted else public("unrelated words")], max_length=1024)
    before = deepcopy(item)
    actual = encode_public_with_spans(item, tokenizer)
    assert actual["encoded"] == tokenizer.encode_public(item)
    assert item == before and tokenizer.check_round_trip(item)
    assert [row["symbol"] for row in actual["occurrences"]] == list(COPY_SYMBOLS)
    for row in actual["occurrences"]:
        ids = actual["encoded"]["ids"][row["token_start"]:row["token_end"]]
        assert tokenizer.decode_text(ids) == row["symbol"]
        assert item["problem"][row["char_start"]:row["char_end"]] == row["symbol"]
        assert row["action_id"] == ACTION_TO_ID[row["symbol"]]
        assert all(actual["encoded"]["kinds"][index] == actual["encoded"]["slots"][index] == 0
                   for index in range(row["token_start"], row["token_end"]))
        if fitted:
            assert len(ids) == 1 and ids[0] >= WORD_START
        else:
            assert len(ids) == len(row["symbol"].encode("utf-8"))
            assert all(token_id < WORD_START for token_id in ids)


@pytest.mark.parametrize("text", ["p16 v32", "p01 v001", "p0_extra xp0 p0x", "P0 V0 Main ARG a b c r",
                                  "é_p0 p0é", "p١ v１", "mainly argument", "[WORD:7030]"])
def test_unknown_identifiers_never_create_silent_partial_matches(text):
    item = public(text)
    tokenizer = LosslessPublicTokenizer.fit_train([public("unrelated words")])
    assert symbol_occurrences(item, tokenizer) == []
    assert tokenizer.check_round_trip(item)


def test_spans_ignore_symbol_spellings_in_observations_and_numeric_rows():
    item = public("No symbolic identifiers here.")
    for row in item["observations"]:
        row["tag"] = "main p0 v31 A R"
    tokenizer = LosslessPublicTokenizer.fit_train([item])
    actual = encode_public_with_spans(item, tokenizer)
    assert actual["occurrences"] == []
    assert actual["encoded"] == tokenizer.encode_public(item)


def test_repeated_symbols_are_distinct_occurrences_with_one_destination_id():
    item = public("p0 p1 p0 p10 p0")
    tokenizer = LosslessPublicTokenizer.fit_train([public("p1 p10")])
    rows = symbol_occurrences(item, tokenizer)
    assert [row["symbol"] for row in rows] == ["p0", "p1", "p0", "p10", "p0"]
    assert len({row["token_start"] for row in rows}) == 5
    assert len({row["action_id"] for row in rows if row["symbol"] == "p0"}) == 1


def test_reordered_observations_leave_problem_occurrences_unchanged():
    item = public("main -> p15: v31 = R(arg).")
    tokenizer = LosslessPublicTokenizer.fit_train([item])
    reordered = deepcopy(item)
    reordered["observations"].reverse()
    assert encode_public_with_spans(reordered, tokenizer) == encode_public_with_spans(item, tokenizer)


def test_no_instruction_parser_or_semantic_acceptance_is_hidden_in_spans():
    # Nonsense text is still accepted as text; these are not program claims.
    item = public("RETURN v31 before v0? p0 p0 RUN R CALL main ALLOW C.")
    tokenizer = LosslessPublicTokenizer.fit_train([item])
    assert [row["symbol"] for row in symbol_occurrences(item, tokenizer)] == ["v31", "v0", "p0", "p0", "R", "main", "C"]


def test_private_fields_are_rejected_before_feature_creation():
    item = public()
    tokenizer = LosslessPublicTokenizer.fit_train([item])
    for field in ("target", "task_id", "expected_graph", "answer", "binding"):
        with pytest.raises(PolicyContractError, match="PUBLIC_INPUT_FIELDS_INVALID"):
            encode_public_with_spans({**item, field: "forbidden"}, tokenizer)


def test_other_tokenizer_types_are_rejected():
    with pytest.raises(PolicyContractError, match="FROZEN_LOSSLESS_TOKENIZER"):
        encode_public_with_spans(public(), object())


def test_invalid_unicode_and_oversized_input_are_not_truncated():
    tokenizer = LosslessPublicTokenizer.fit_train([public("short")], max_length=64)
    with pytest.raises(PolicyContractError, match="INVALID_UNICODE"):
        encode_public_with_spans(public("p0 \ud800"), tokenizer)
    with pytest.raises(PolicyContractError, match="NO_SILENT_TRUNCATION"):
        encode_public_with_spans(public("p15 " * 100), tokenizer)


def test_synthetic_mixed_fitted_and_utf8_unit_offsets():
    rng = random.Random(60231)
    tokenizer = LosslessPublicTokenizer.fit_train([public("main p0 v0 A known word")], max_length=4096)
    alphabet = list(COPY_SYMBOLS) + ["p16", "v32", "Café", "🧠", "p0_extra"]
    separators = [" ", "\t", "\r\n", ";", " -> ", "(", ")"]
    for _ in range(40):
        units = [rng.choice(alphabet) for _ in range(30)]
        item = public("".join(unit + rng.choice(separators) for unit in units))
        result = encode_public_with_spans(item, tokenizer)
        assert result["encoded"] == tokenizer.encode_public(item)
        assert [row["symbol"] for row in result["occurrences"]] == [unit for unit in units if unit in COPY_SYMBOLS]
        for row in result["occurrences"]:
            assert tokenizer.decode_text(result["encoded"]["ids"][row["token_start"]:row["token_end"]]) == row["symbol"]
