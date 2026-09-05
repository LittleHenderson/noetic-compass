from copy import deepcopy
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.not_gpu

from cas_meta2.codec import (
    ACTION_VOCABULARY, PolicyContractError, PublicTokenizer, action_to_ids,
    action_to_tokens, ids_to_action, tokens_to_action, validate_action,
    validate_public,
)


def public():
    return {"problem": "Apply A to the amber record, then call a child that runs B.",
            "observations": [{"slot": i, "tag": tag, "values": [float(i)] * 8}
                             for i, tag in enumerate(("amber", "blue", "green"))]}


def action():
    return {"binding": 0, "program": {
        "schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
            "main": {"input": "arg", "allowed_cjts": ["A", "B"],
                     "steps": [{"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
                               {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"}],
                     "return": "v1"},
            "p0": {"input": "arg", "allowed_cjts": ["B"],
                   "steps": [{"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}],
                   "return": "v0"},
        }}}


@pytest.mark.parametrize("binding", [0, 1, 2])
def test_program_roundtrip_tokens_and_ids(binding):
    expected = action()
    expected["binding"] = binding
    tokens = action_to_tokens(expected)
    assert tokens_to_action(tokens) == expected
    assert ids_to_action(action_to_ids(expected)) == expected
    assert "CALL" in tokens and "RUN" in tokens
    assert all(token in ACTION_VOCABULARY for token in tokens)


def test_codec_import_is_torch_free():
    root = str(Path(__file__).resolve().parents[1])
    script = ("import sys;sys.path.insert(0," + repr(root)
              + ");import cas_meta2.codec;assert 'torch' not in sys.modules")
    subprocess.run([sys.executable, "-B", "-c", script], check=True)


def test_vocabulary_contains_no_whole_program_id():
    assert len(ACTION_VOCABULARY) == len(set(ACTION_VOCABULARY))
    assert "RUN" in ACTION_VOCABULARY and "CALL" in ACTION_VOCABULARY
    assert not any(token.startswith(("graph_", "program_", "template_")) for token in ACTION_VOCABULARY)


def test_serialization_ignores_dict_insertion_order():
    expected = action()
    reordered = deepcopy(expected)
    reordered["program"]["procedures"] = dict(reversed(list(expected["program"]["procedures"].items())))
    assert action_to_tokens(expected) == action_to_tokens(reordered)
    assert tokens_to_action(action_to_tokens(reordered)) == expected


@pytest.mark.parametrize("mutation", [
    lambda a: a.update({"gold": 1}),
    lambda a: a.update({"binding": True}),
    lambda a: a.update({"binding": 3}),
    lambda a: a["program"].update({"schema": "foreign/1"}),
    lambda a: a["program"].update({"entry": "p0"}),
    lambda a: a["program"]["procedures"]["main"].update({"input": "other"}),
    lambda a: a["program"]["procedures"]["main"].update({"return": "v31"}),
    lambda a: a["program"]["procedures"]["main"].update({"steps": []}),
    lambda a: a["program"]["procedures"]["main"].update({"allowed_cjts": ["A", "A"]}),
    lambda a: a["program"]["procedures"]["main"].update({"allowed_cjts": ["A"]}),
    lambda a: a["program"]["procedures"]["main"]["steps"][0].update({"cjt_id": "R"}),
    lambda a: a["program"]["procedures"]["main"]["steps"][0].update({"input": "v0"}),
    lambda a: a["program"]["procedures"]["main"]["steps"][1].update({"output": "v0"}),
    lambda a: a["program"]["procedures"]["main"]["steps"][1].update({"procedure": "p15"}),
    lambda a: a["program"]["procedures"]["main"]["steps"][1].update({"procedure": "main"}),
    lambda a: a["program"]["procedures"]["main"]["steps"][0].update({"extra": "hidden"}),
])
def test_invalid_programs_fail_closed(mutation):
    value = action()
    mutation(value)
    with pytest.raises(PolicyContractError):
        action_to_tokens(value)


@pytest.mark.parametrize("mutation", [
    lambda t: t[:-1],
    lambda t: t + ["[EOS]"],
    lambda t: ["[PAD]"] + t[1:],
    lambda t: t[:1] + ["BIND3"] + t[2:],
    lambda t: t[:6] + ["[UNK]"] + t[7:],
    lambda t: t[:4] + ["RETURN"] + t[5:],
])
def test_corrupt_tokens_are_not_repaired(mutation):
    with pytest.raises(PolicyContractError):
        tokens_to_action(mutation(action_to_tokens(action())))


def test_exact_length_boundary():
    expected = action()
    tokens = action_to_tokens(expected)
    assert action_to_tokens(expected, max_length=len(tokens)) == tokens
    assert tokens_to_action(tokens, max_length=len(tokens)) == expected
    with pytest.raises(PolicyContractError, match="NO_SILENT_TRUNCATION"):
        action_to_tokens(expected, max_length=len(tokens) - 1)
    with pytest.raises(PolicyContractError):
        tokens_to_action(tokens, max_length=len(tokens) - 1)


def test_curriculum_roundtrips_without_public_or_action_truncation():
    from cas_meta2.curriculum import generate_dataset
    dataset = generate_dataset()
    tokenizer = PublicTokenizer.fit_train([task["public"] for task in dataset["splits"]["train"]])
    for tasks in dataset["splits"].values():
        for task in tasks:
            assert tokens_to_action(action_to_tokens(task["target"], max_length=256)) == task["target"]
            assert len(tokenizer.encode_public(task["public"])["ids"]) <= 512


@pytest.mark.parametrize("ids", [[True], [-1], [999], [1.0], ["RUN"], None])
def test_corrupt_ids_rejected(ids):
    with pytest.raises(PolicyContractError):
        ids_to_action(ids)


@pytest.mark.parametrize("field", ["target", "program", "binding", "id", "provenance", "expected"])
def test_public_input_rejects_gold_or_metadata(field):
    value = public()
    value[field] = action()
    with pytest.raises(PolicyContractError, match="PUBLIC_INPUT_FIELDS_INVALID"):
        validate_public(value)


def test_public_slot_order_does_not_change_encoding():
    value = public()
    tokenizer = PublicTokenizer.fit_train([value])
    reversed_value = deepcopy(value)
    reversed_value["observations"].reverse()
    assert tokenizer.encode_public(value) == tokenizer.encode_public(reversed_value)


def test_tokenizer_fits_training_only_and_uses_unknown():
    value = public()
    tokenizer = PublicTokenizer.fit_train([value])
    heldout = deepcopy(value)
    heldout["problem"] = "entirelynovelword"
    encoded = tokenizer.encode_public(heldout)
    assert 1 in encoded["ids"]
    assert "entirelynovelword" not in tokenizer.vocabulary
    assert tokenizer.to_dict()["fit_split"] == "train_only"
    assert tokenizer.fitted_examples == 1
    assert len(tokenizer.digest) == 64
    assert json.loads(json.dumps(tokenizer.to_dict()))["vocabulary"][0] == "[PAD]"


def test_public_length_overflow_rejected_at_fit_and_inference():
    value = public()
    tokenizer = PublicTokenizer.fit_train([value], max_length=64)
    value["problem"] = "word " * 100
    with pytest.raises(PolicyContractError, match="NO_SILENT_TRUNCATION"):
        tokenizer.encode_public(value)
    with pytest.raises(PolicyContractError, match="NO_SILENT_TRUNCATION"):
        PublicTokenizer.fit_train([value], max_length=64)


@pytest.mark.parametrize("mutation", [
    lambda p: p["observations"][0].update({"slot": True}),
    lambda p: p["observations"][0].update({"slot": 1}),
    lambda p: p["observations"][0].update({"values": [float("nan")] * 8}),
    lambda p: p["observations"][0].update({"values": [True] * 8}),
    lambda p: p["observations"][0].update({"values": [0.0] * 7}),
    lambda p: p["observations"][0].update({"tag": ""}),
])
def test_invalid_observations_rejected(mutation):
    value = public()
    mutation(value)
    with pytest.raises(PolicyContractError):
        validate_public(value)
