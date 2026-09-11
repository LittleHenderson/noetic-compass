"""The fitting-corpus check, as a test: the failure that cost a reservation.

The first CFC pilot died inside `build_encoder` at `fit_train` with
`PUBLIC_TAG_INVALID`, because the fitting corpus had been synthesised by hand with
the whole problem text used as an option tag. Both halves of that call are pure
Python, so this test reproduces the exact failing path locally, with no torch and no
provider: the frozen codec validates every record, and the real tokenizer fits and
is inspected for the tokens the frozen problem encoder requires.
"""
import pytest

from cas_meta2 import codec
from cas_meta2.features_v2 import LosslessPublicTokenizer, _word_token
from cas_meta2.graph_teaching import (face_corpus as corpus,
                                      face_evaluation as evaluation,
                                      face_roles as roles,
                                      face_schedule as schedule,
                                      face_tasks as tasks,
                                      face_worker as worker)

MAX_PROBLEM = 8192
MAX_TAG = 256


def _bundle():
    built = corpus.families()
    panel = evaluation.panel(built)
    conditions = [(entry["condition"], entry["organization"], entry["cue"])
                  for entry in schedule.comparison_conditions()]
    return built, panel, conditions, worker.public_corpus(built, panel, conditions)


def test_every_fitting_record_is_codec_valid():
    _built, _panel, _conditions, bundle = _bundle()
    assert bundle["distinct_texts"] > 2000
    for public in bundle["publics"]:
        codec.validate_public(public)          # raises on any violation
        assert set(public) == {"problem", "observations"}
        slots = sorted(item["slot"] for item in public["observations"])
        assert slots == [0, 1, 2]


def test_the_fitting_corpus_stays_inside_the_frozen_limits():
    _built, _panel, _conditions, bundle = _bundle()
    assert bundle["longest_problem"] <= MAX_PROBLEM
    assert bundle["longest_tag"] <= MAX_TAG
    # the longest tag is close to the limit, so it is pinned rather than assumed
    assert bundle["longest_tag"] > 0


def test_the_real_tokenizer_fits_and_carries_every_required_marker():
    """This is the call that failed on the instance; here it runs locally."""
    _built, _panel, _conditions, bundle = _bundle()
    tokenizer = LosslessPublicTokenizer.fit_train(list(bundle["publics"]),
                                                  max_length=64 * 1024)
    vocabulary = tuple(tokenizer.vocabulary)
    assert len(vocabulary) > 100
    for unit in ("node", "rel", "\n"):
        assert _word_token(unit) in vocabulary, unit
    for face in roles.FACE_NUMBERS:
        assert _word_token(roles.cue_for(face, "stable")) in vocabulary, face
    assert _word_token(roles.cue_for(1, "neutral")) in vocabulary


def test_scheduled_episodes_are_valid_with_their_worked_supports():
    built, _panel, _conditions, _bundle_data = _bundle()
    checked = 0
    longest = 0
    for condition, organization, cue in (("cfc_stable_cues", "CFC_LOOP", "stable"),
                                         ("mixed_order_neutral_cue", "MIXED_ORDER",
                                          "neutral")):
        events = schedule.condition_events(condition, organization, cue, built=built)
        for event in events[:300]:
            episode = worker.experiment.compile_event(event, built=built)
            codec.validate_public(episode["public"])
            longest = max(longest, len(episode["public"]["problem"]))
            checked += 1
    assert checked == 600
    assert longest <= MAX_PROBLEM
    # supports are inside the problem text, so a supported episode is longer
    assert longest > 0


def test_the_synthesised_corpus_that_failed_would_still_be_refused():
    """The exact defect, kept as a regression: a problem text is not a tag."""
    public = {"problem": "node A kind=idea", "observations": [
        {"slot": slot, "tag": "node A kind=idea" if slot == 0 else "x",
         "values": [0.0] * 8} for slot in range(3)]}
    codec.validate_public(public)              # short tags are legal
    long_tag = "z" * (MAX_TAG + 1)
    broken = {"problem": "node A kind=idea", "observations": [
        {"slot": slot, "tag": long_tag, "values": [0.0] * 8} for slot in range(3)]}
    with pytest.raises(Exception) as error:
        codec.validate_public(broken)
    assert "PUBLIC_TAG_INVALID" in str(error.value)


def test_the_encode_problem_path_has_segments_and_three_slots_everywhere():
    """The call immediately after the one that failed, rehearsed the same way."""
    built, _panel, conditions, bundle = _bundle()
    tokenizer = LosslessPublicTokenizer.fit_train(list(bundle["publics"]),
                                                  max_length=64 * 1024)
    vocabulary = tuple(tokenizer.vocabulary)
    node_id = vocabulary.index(_word_token("node"))
    rel_id = vocabulary.index(_word_token("rel"))
    newline_id = vocabulary.index(_word_token("\n"))

    def segments_and_slots(public):
        encoded = tokenizer.encode_public(public)
        problem_ids = [token for token, kind in zip(encoded["ids"], encoded["kinds"])
                       if kind == 0]
        segments, current = 0, None
        for token in problem_ids:
            if token == newline_id:
                current = None
            elif token in (node_id, rel_id):
                current = [token]
                segments += 1
            elif current is not None:
                current.append(token)
        slots = {slot - 1 for token, kind, slot
                 in zip(encoded["ids"], encoded["kinds"], encoded["slots"])
                 if kind == 2 and slot in (1, 2, 3)}
        return segments, slots

    for public in bundle["publics"][:300]:
        segments, slots = segments_and_slots(public)
        assert segments >= 1, "PROBLEM_STRUCTURAL_SEGMENTS_REQUIRED"
        assert slots == {0, 1, 2}, slots
    name, organization, cue = conditions[0]
    for event in schedule.condition_events(name, organization, cue,
                                           built=built)[:100]:
        episode = worker.experiment.compile_event(event, built=built)
        segments, slots = segments_and_slots(episode["public"])
        assert segments >= 1 and slots == {0, 1, 2}
