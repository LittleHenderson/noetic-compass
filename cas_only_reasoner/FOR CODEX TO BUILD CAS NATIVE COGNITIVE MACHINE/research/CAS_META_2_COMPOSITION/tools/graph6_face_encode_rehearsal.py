"""The second half of the encoder path, rehearsed locally — still no torch.

The first attempt died at the tokenizer fit. The next call in the same path is
`encode_problem`, which needs structural segments and three encoded observation
slots. Both are pure text, so both are checkable here: the tokenizer is fitted
exactly as `build_encoder` fits it, and then every fitting record and a sample of
scheduled episodes is walked through the encoder's own segmentation rule.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2.features_v2 import LosslessPublicTokenizer, _word_token  # noqa: E402
from cas_meta2.graph_teaching import (face_corpus as corpus,  # noqa: E402
                                      face_evaluation as evaluation,
                                      face_roles as roles,
                                      face_schedule as schedule,
                                      face_worker as worker)

MAX_LENGTH = 64 * 1024


def main():
    built = corpus.families()
    panel = evaluation.panel(built)
    conditions = [(entry["condition"], entry["organization"], entry["cue"])
                  for entry in schedule.comparison_conditions()]
    bundle = worker.public_corpus(built, panel, conditions)
    tokenizer = LosslessPublicTokenizer.fit_train(list(bundle["publics"]),
                                                  max_length=MAX_LENGTH)
    vocabulary = tuple(tokenizer.vocabulary)
    node_id = vocabulary.index(_word_token("node"))
    rel_id = vocabulary.index(_word_token("rel"))
    newline_id = vocabulary.index(_word_token("\n"))

    def check(public, label):
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
        assert segments, "PROBLEM_STRUCTURAL_SEGMENTS_REQUIRED:" + label
        assert slots == {0, 1, 2}, "PUBLIC_SLOT_ENCODING_INCOMPLETE:%s:%s" % (label, slots)
        return segments

    fewest, checked = 10 ** 9, 0
    for index, public in enumerate(bundle["publics"]):
        fewest = min(fewest, check(public, "fitting:%d" % index))
        checked += 1
    print("fitting records   :", checked, "| fewest structural segments:", fewest)

    sampled = 0
    for name, organization, cue in conditions:
        for event in schedule.condition_events(name, organization, cue,
                                               built=built)[:200]:
            episode = worker.experiment.compile_event(event, built=built)
            check(episode["public"], "%s:%s" % (name, event.get("family_id")))
            sampled += 1
    print("scheduled sampled :", sampled)
    for item in panel:
        entry = (evaluation.diagnostic_item(item, built=built)
                 if item["kind"] in evaluation.DIAGNOSTIC_KINDS
                 else evaluation.compile_panel_item(item, built=built))
        check(entry["episode"]["public"], "panel:%s" % item["item_id"])
    print("panel items       :", len(panel))
    print("ENCODE PROBLEM PATH OK — segments and three slots are present everywhere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
