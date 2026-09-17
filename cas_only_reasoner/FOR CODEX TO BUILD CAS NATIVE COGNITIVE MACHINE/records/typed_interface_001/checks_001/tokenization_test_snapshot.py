"""Lossless pure frame tokens; retained inputs are training-only public packets."""
import builtins
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from cas_meta2.typed_teaching import input_frames as frames, source, tokenization as tok


ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "records/typed_course_001/checks_002/public_packet_examples.json"
EXAMPLES_SHA = "9def7698d985661cb0f288376e006a9a39bfc73873c265cb3903a47eb0a9c6e4"
DENIED = {"torch", "numpy", "tensorflow", "jax", "jaxlib", "cas_cjt", "casformer",
          "boto3", "botocore", "requests", "httpx", "openai", "anthropic", "transformers"}


@pytest.fixture(autouse=True)
def no_numeric_or_legacy_teacher(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("FORBIDDEN_TOKENIZER_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


@pytest.fixture(scope="module")
def public_frames():
    # Load this pinned public training projection once. No private/final targets.
    raw = EXAMPLES.read_bytes()
    assert sha256(raw).hexdigest() == EXAMPLES_SHA
    packets = json.loads(raw)
    assert set(packets) == {"definition", "context", "analogy", "correspondence",
                           "parts", "reach", "edge_account", "role_set"}
    return tuple(frames.compile_packet(packets[kind]) for kind in sorted(packets))


@pytest.fixture(scope="module")
def trained(public_frames):
    cap = max(tok.training_token_count(frame) for frame in public_frames)
    return tok.fit_train(list(public_frames), max_tokens=cap)


def text_only_tokenizer(*, max_tokens=4096):
    """Synthetic lexical seam, not evidence of an admitted training corpus."""
    words = tuple(tok._word(unit) for unit in sorted(("Known", " ", "\n")))
    synthetic = sha256(b"synthetic text-only fixture metadata").hexdigest()
    return tok.FrameTokenizer(tok.FIXED + words, (synthetic,), max_tokens, tok.profile())


@pytest.mark.parametrize("index", range(8))
def test_every_answer_kind_has_exact_full_frame_roundtrip(public_frames, trained, index):
    frame = public_frames[index]
    before = deepcopy(frame)
    sequence = trained.encode_frame(frame)
    assert sequence["ids"][0] == tok.START and sequence["ids"][-1] == tok.END
    assert len(sequence["ids"]) == tok.training_token_count(frame)
    assert trained.decode_text(sequence["ids"][1:-1]) == frame["text"]
    assert trained.validate_sequence(frame, sequence) is True
    assert frames.restore_packet(frame) == frames.restore_packet(before)
    assert frame == before
    assert sequence["frame_digest"] == source.digest(frame)
    assert sequence["tokenizer_digest"] == trained.digest
    assert trained.to_dict()["numeric_compatibility"] is False


def test_fit_order_is_irrelevant_but_training_membership_is_bound(public_frames):
    items = list(public_frames[:2])
    cap = max(tok.training_token_count(item) for item in items)
    forward = tok.fit_train(items, max_tokens=cap)
    reverse = tok.fit_train(list(reversed(items)), max_tokens=cap)
    subset = tok.fit_train(items[:1], max_tokens=cap)
    assert forward.to_dict() == reverse.to_dict() and forward.digest == reverse.digest
    assert forward.training_frame_digests == tuple(sorted(source.digest(x) for x in items))
    assert forward.digest != subset.digest
    assert source.digest(items[1]) not in subset.training_frame_digests
    before = forward.to_dict()
    assert forward.decode_text(forward.encode_text("unseen_\u03bb\U0001f642")) == "unseen_\u03bb\U0001f642"
    assert forward.to_dict() == before  # Encoding never grows or refits the vocabulary.


@pytest.mark.parametrize("text", ["Known Known\n", "\t\r\n  ", "\u03bb\U0001f642\u4e2d",
                                  "e\u0301", "\u00e9", "[FRAME] [END] @{W0/N0}",
                                  '"quoted"\\escaped\nline', "\x00\x01\x7f"])
def test_case_whitespace_unicode_punctuation_and_control_bytes_roundtrip(text):
    tokenizer = text_only_tokenizer()
    ids = tokenizer.encode_text(text)
    assert tokenizer.decode_text(ids) == text
    assert tok.START not in ids and tok.END not in ids


def test_complete_utf8_fallback_has_no_unknown_or_normalization():
    tokenizer = text_only_tokenizer()
    text = "\u03bb\U0001f642\u4e2d"
    assert tokenizer.encode_text(text) == [tok.BYTE_START + x for x in text.encode("utf-8")]
    assert tokenizer.encode_text("\u00e9") != tokenizer.encode_text("e\u0301")
    assert tokenizer.encode_text("Known") != tokenizer.encode_text("known")


@pytest.mark.parametrize("ids", [[tok.START], [tok.END], [-1], [True], [2.0],
                                 [1000000], [tok.BYTE_START + 0xc3], [tok.BYTE_START + 0xff]])
def test_text_decoder_rejects_special_type_range_and_broken_utf8(ids):
    with pytest.raises(ValueError):
        text_only_tokenizer().decode_text(ids)


@pytest.mark.parametrize("text", ["", None, 1, b"text", "\ud800"])
def test_invalid_text_is_rejected(text):
    with pytest.raises(ValueError):
        text_only_tokenizer().encode_text(text)


def test_overflow_refuses_whole_text_and_counts_both_frame_markers():
    tokenizer = text_only_tokenizer(max_tokens=3)
    assert len(tokenizer.encode_text("Known")) + 2 == 3
    for text in ("KnownKnown", "Known Known", "\U0001f642"):
        with pytest.raises(ValueError, match="OVERFLOW_NO_TRUNCATION"):
            tokenizer.encode_text(text)
    assert text_only_tokenizer(max_tokens=6).decode_text(
        text_only_tokenizer(max_tokens=6).encode_text("\U0001f642")) == "\U0001f642"
    with pytest.raises(ValueError, match="OVERFLOW_NO_TRUNCATION"):
        text_only_tokenizer(max_tokens=5).encode_text("\U0001f642")


def test_exact_training_frame_cap_passes_and_one_less_refuses(public_frames):
    frame = public_frames[0]
    count = tok.training_token_count(frame)
    exact = tok.fit_train([frame], max_tokens=count)
    assert len(exact.encode_frame(frame)["ids"]) == count
    with pytest.raises(ValueError, match="OVERFLOW_NO_TRUNCATION"):
        tok.fit_train([frame], max_tokens=count - 1)


@pytest.mark.parametrize("value", [True, 3.0, "3", None, 1, tok.HARD_MAX_TOKENS + 1])
def test_cap_requires_exact_bounded_integer(value):
    with pytest.raises(ValueError, match="TOKEN_CAP"):
        text_only_tokenizer(max_tokens=value)


@pytest.mark.parametrize("mutation", ["extra", "schema", "algorithm", "unit_rule", "fit_scope",
                                     "numeric_zero", "numeric_true", "vocabulary_tuple", "digests_tuple"])
def test_serialized_metadata_is_closed_and_exact(mutation):
    data = text_only_tokenizer().to_dict()
    if mutation == "extra": data["private_target"] = "not permitted"
    elif mutation == "numeric_zero": data["numeric_compatibility"] = 0
    elif mutation == "numeric_true": data["numeric_compatibility"] = True
    elif mutation == "vocabulary_tuple": data["vocabulary"] = tuple(data["vocabulary"])
    elif mutation == "digests_tuple": data["training_frame_digests"] = tuple(data["training_frame_digests"])
    else: data[mutation] = "altered"
    with pytest.raises(ValueError):
        tok.FrameTokenizer.from_dict(data)


@pytest.mark.parametrize("mutation", ["fixed", "duplicate", "reordered", "uppercase_hex", "invalid_utf8",
                                     "empty_unit", "multiple_units", "unit_too_long", "word_type"])
def test_vocabulary_is_canonical_bounded_and_lossless(mutation):
    data = text_only_tokenizer().to_dict()
    if mutation == "fixed": data["vocabulary"][0] = "[WRONG]"
    elif mutation == "duplicate": data["vocabulary"].append(data["vocabulary"][-1])
    elif mutation == "reordered": data["vocabulary"][tok.WORD_START:] = reversed(data["vocabulary"][tok.WORD_START:])
    else:
        replacement = {"uppercase_hex": "[UNIT:4A]", "invalid_utf8": "[UNIT:ff]",
                       "empty_unit": "[UNIT:]", "multiple_units": "[UNIT:612062]",
                       "unit_too_long": "[UNIT:" + "61" * (tok.MAX_UNIT_BYTES + 1) + "]",
                       "word_type": 7}[mutation]
        data["vocabulary"][-1] = replacement
    with pytest.raises(ValueError):
        tok.FrameTokenizer.from_dict(data)


@pytest.mark.parametrize("identities", [[], ["bad"], ["A" * 64], [True], ["0" * 64, "0" * 64],
                                        ["f" * 64, "0" * 64]])
def test_fit_digest_metadata_is_exact_sorted_unique(identities):
    data = text_only_tokenizer().to_dict()
    data["training_frame_digests"] = identities
    with pytest.raises(ValueError, match="FIT_IDENTITIES"):
        tok.FrameTokenizer.from_dict(data)


def test_constructor_requires_immutable_vocabulary_and_fit_digest_tuples():
    item = text_only_tokenizer()
    with pytest.raises(ValueError, match="FIXED_VOCABULARY"):
        tok.FrameTokenizer(list(item.vocabulary), item.training_frame_digests, item.max_tokens, item.source_profile)
    with pytest.raises(ValueError, match="FIT_IDENTITIES"):
        tok.FrameTokenizer(item.vocabulary, list(item.training_frame_digests), item.max_tokens, item.source_profile)


def test_source_profile_and_serialization_do_not_alias_caller_metadata():
    original = text_only_tokenizer()
    data = original.to_dict()
    restored = tok.FrameTokenizer.from_dict(data)
    expected = restored.to_dict()
    data["source_profile"]["numeric_encoder_compatibility"] = True
    data["vocabulary"][0] = "corrupted"
    assert restored.to_dict() == expected == original.to_dict()
    output = restored.to_dict()
    output["source_profile"]["file"]["sha256"] = "0" * 64
    assert restored.to_dict() == expected
    # Dataclass freezing is shallow: explicit profile mutation must fail closed.
    restored.source_profile["numeric_encoder_compatibility"] = True
    with pytest.raises(ValueError, match="SOURCE_PROFILE"):
        restored.to_dict()


def test_resealed_source_profile_tampering_refuses():
    data = text_only_tokenizer().to_dict()
    data["source_profile"]["file"]["sha256"] = "0" * 64
    data["source_profile"]["profile_digest"] = source.digest({
        k: v for k, v in data["source_profile"].items() if k != "profile_digest"})
    with pytest.raises(ValueError, match="SOURCE_PROFILE"):
        tok.FrameTokenizer.from_dict(data)


@pytest.mark.parametrize("mutation", ["tuple", "float", "cycle"])
def test_source_profile_requires_closed_json_types(mutation):
    data = text_only_tokenizer().to_dict()
    if mutation == "tuple":
        data["source_profile"]["frame_profile"]["files"] = tuple(data["source_profile"]["frame_profile"]["files"])
    elif mutation == "float":
        data["source_profile"]["file"]["bytes"] = float(data["source_profile"]["file"]["bytes"])
    else:
        data["source_profile"]["cycle"] = data["source_profile"]
    with pytest.raises(ValueError):
        tok.FrameTokenizer.from_dict(data)


def test_stale_current_source_profile_refuses_serialization_and_bound_encoding(public_frames, trained, monkeypatch):
    changed = tok.profile()
    changed["file"]["sha256"] = "0" * 64
    changed["profile_digest"] = source.digest({k: v for k, v in changed.items() if k != "profile_digest"})
    monkeypatch.setattr(tok, "profile", lambda: deepcopy(changed))
    with pytest.raises(ValueError, match="SOURCE_PROFILE"):
        trained.to_dict()
    with pytest.raises(ValueError, match="SOURCE_PROFILE"):
        trained.encode_frame(public_frames[0])


@pytest.mark.parametrize("mutation", ["schema", "frame_digest", "tokenizer_digest", "ids", "ids_tuple", "extra"])
def test_resealed_sequence_tampering_refuses(public_frames, trained, mutation):
    frame = public_frames[0]
    sequence = trained.encode_frame(frame)
    if mutation == "ids": sequence["ids"][1] = tok.START
    elif mutation == "ids_tuple": sequence["ids"] = tuple(sequence["ids"])
    elif mutation == "extra": sequence["target"] = "private"
    else: sequence[mutation] = "0" * 64
    sequence["sequence_digest"] = source.digest({k: v for k, v in sequence.items() if k != "sequence_digest"})
    with pytest.raises(ValueError):
        trained.validate_sequence(frame, sequence)


def test_sequence_cannot_be_borrowed_by_another_frame_or_tokenizer(public_frames, trained):
    sequence = trained.encode_frame(public_frames[0])
    with pytest.raises(ValueError, match="SEQUENCE_BINDING"):
        trained.validate_sequence(public_frames[1], sequence)
    another = tok.fit_train([public_frames[0]], max_tokens=trained.max_tokens)
    with pytest.raises(ValueError, match="SEQUENCE_BINDING"):
        another.validate_sequence(public_frames[0], sequence)


def test_invalid_resealed_frame_is_refused_before_tokenizing(public_frames, trained):
    frame = deepcopy(public_frames[0])
    frame["text"] += "\nUNDECLARED EXTRA STRUCTURE"
    frame["frame_digest"] = source.digest({k: v for k, v in frame.items() if k != "frame_digest"})
    with pytest.raises(ValueError):
        trained.encode_frame(frame)


def test_fitter_rejects_duplicate_or_nonlist_training_inputs(public_frames):
    frame = public_frames[0]
    cap = tok.training_token_count(frame)
    for value in ([], tuple([frame]), None):
        with pytest.raises(ValueError, match="FIT_LIST"):
            tok.fit_train(value, max_tokens=cap)
    with pytest.raises(ValueError, match="DUPLICATE_FIT_FRAME"):
        tok.fit_train([frame, deepcopy(frame)], max_tokens=cap)
    with pytest.raises(ValueError, match="FIT_LIST"):
        tok.fit_train([frame] * (tok.MAX_FIT_FRAMES + 1), max_tokens=cap)


def test_fit_and_encode_do_not_consult_private_semantics(public_frames, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("TOKENIZER_CONSULTED_SOURCE_CONSTRUCTOR_OR_TEACHER")
    for name in ("training_families", "freeze_bank", "compile_source"):
        monkeypatch.setattr(source, name, forbidden)
    checker = sys.modules.get("cas_meta2.typed_teaching.checker")
    if checker is not None:
        monkeypatch.setattr(checker, "derive_target", forbidden)
    frame = public_frames[0]
    fitted = tok.fit_train([frame], max_tokens=tok.training_token_count(frame))
    assert fitted.validate_sequence(frame, fitted.encode_frame(frame))
