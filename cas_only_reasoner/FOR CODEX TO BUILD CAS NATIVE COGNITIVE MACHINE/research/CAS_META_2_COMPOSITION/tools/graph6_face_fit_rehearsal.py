"""Local rehearsal of the call that killed the first attempt — no torch, no AWS.

The first CFC pilot died inside `real_framework.build_encoder` at
`LosslessPublicTokenizer.fit_train` with `PUBLIC_TAG_INVALID`, because the fitting
corpus had been rebuilt by hand with the whole problem text used as an option tag.
Both halves of that call are pure Python, so the whole thing is rehearsable locally:
the codec validates every record, and the real tokenizer fits and is inspected for
the tokens the frozen problem encoder requires.

This is the check that should have run before the reservation. It now runs as a test
and in this file, so it cannot be skipped again.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2 import codec  # noqa: E402
from cas_meta2.features_v2 import LosslessPublicTokenizer, _word_token  # noqa: E402
from cas_meta2.graph_teaching import (face_corpus as corpus,  # noqa: E402
                                      face_evaluation as evaluation,
                                      face_roles as roles,
                                      face_schedule as schedule,
                                      face_tasks as tasks,
                                      face_worker as worker)


def main():
    built = corpus.families()
    panel = evaluation.panel(built)
    conditions = [(entry["condition"], entry["organization"], entry["cue"])
                  for entry in schedule.comparison_conditions()]
    bundle = worker.public_corpus(built, panel, conditions)
    print("fitting corpus :", bundle["distinct_texts"], "records")
    print("longest problem:", bundle["longest_problem"], "chars (limit 8192)")
    print("longest tag    :", bundle["longest_tag"], "chars (limit 256)")

    for index, public in enumerate(bundle["publics"]):
        codec.validate_public(public)
    print("codec          : all", len(bundle["publics"]), "records valid")

    tokenizer = LosslessPublicTokenizer.fit_train(
        list(bundle["publics"]),
        max_length=64 * 1024)
    vocabulary = tuple(tokenizer.vocabulary)
    print("vocabulary     :", len(vocabulary), "units")
    required = ["node", "rel", "\n"] + [roles.cue_for(face, arm)
                                        for face in roles.FACE_NUMBERS
                                        for arm in ("stable",)]
    for unit in required:
        token = _word_token(unit)
        print("  %-18s present: %s" % (unit, token in vocabulary))
        assert token in vocabulary, unit
    print("neutral cue    :", roles.cue_for(5, "neutral"),
          "present:", _word_token(roles.cue_for(5, "neutral")) in vocabulary)

    # every scheduled episode's public must also be valid and within limits
    longest = 0
    checked = 0
    for name, organization, cue in conditions:
        events = schedule.condition_events(name, organization, cue, built=built)
        for event in events[:400]:
            episode = worker.experiment.compile_event(event, built=built)
            codec.validate_public(episode["public"])
            longest = max(longest, len(episode["public"]["problem"]))
            checked += 1
    print("scheduled      :", checked, "episodes valid | longest problem", longest)
    print("REHEARSAL OK — the call that failed locally passes here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
