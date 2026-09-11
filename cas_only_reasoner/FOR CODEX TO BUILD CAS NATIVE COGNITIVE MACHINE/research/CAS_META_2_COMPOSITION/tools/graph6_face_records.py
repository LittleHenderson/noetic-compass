"""Write the CUBE_FACE_GROUNDING_001 preparation records.

Read-only over the code: it compiles the corpus manifest, the coverage report, the
task bindings, the schedule arithmetic, the panel manifest, and one readable
cross-cube teaching episode per face with its exact learner input and target. It
trains nothing and launches nothing.

Usage: python tools/graph6_face_records.py <record-directory>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2.graph_teaching import (face_corpus as corpus,  # noqa: E402
                                      face_evaluation as evaluation,
                                      face_roles as roles,
                                      face_schedule as schedule,
                                      face_tasks as tasks)


def write(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True,
                               ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", path.name, path.stat().st_size, "bytes")


def episode_text(family, face, built, supports):
    episode = tasks.compile_episode(family, face, roles.FACE_APPLY, arm="stable",
                                    supports=supports, built=built)
    recognition = tasks.compile_episode(family, face, roles.ROLE_FROM_CONTENT,
                                        offset=face, built=built)
    return {
        "face": face, "role": roles.role_for(face)["role"],
        "family_id": family["family_id"], "domain": family["domain"],
        "archetype": family["archetype"],
        "support_families": [support["family_id"] for support in supports],
        "learner_input": episode["public"]["problem"],
        "delivered_choices": episode["encoded_options"],
        "encoded_correct_index": episode["encoded_correct_index"],
        "teacher_target": episode["teacher_target"],
        "public_record_id": episode["public_record"]["record_id"],
        "recognition_input": recognition["public"]["problem"],
        "recognition_choices": recognition["encoded_options"],
        "recognition_correct_index": recognition["encoded_correct_index"],
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit("usage: graph6_face_records.py <record-directory>")
    directory = Path(argv[0])
    directory.mkdir(parents=True, exist_ok=True)
    built = corpus.families()
    training = corpus.by_split(corpus.TRAINING, built)

    write(directory / "FAMILY_MANIFEST.json", corpus.family_manifest(built))
    write(directory / "COVERAGE_REPORT.json", corpus.coverage_report(built))
    write(directory / "ROLE_REGISTRY.json", roles.registry_report())
    write(directory / "TASK_BINDINGS_FACE.json", tasks.task_bindings())
    write(directory / "AMBIGUITY_REPORT.json", tasks.ambiguity_report(built))
    write(directory / "SCHEDULE.json", schedule.schedule_report(built))
    write(directory / "EVALUATION_PANEL.json", evaluation.panel_manifest(built))

    episodes = []
    for family in training[:6]:
        for face in roles.FACE_NUMBERS:
            supports = tasks.choose_supports(family, face, offset=face, built=built)
            episodes.append(episode_text(family, face, built, supports))
    write(directory / "WORKED_EPISODES.json",
          {"schema": "cas.cube-face-episodes/0.1",
           "note": ("one cross-cube teaching episode per face, on the first six "
                    "training families, with the exact learner input, the "
                    "delivered choice order and the separate teacher target"),
           "episodes": episodes})

    excerpt = directory / "WORKED_EPISODES.md"
    lines = ["# One cross-cube teaching episode per face", "",
             "Compiled from the declared corpus; the input shown is what the",
             "numerical path receives.", ""]
    for episode in episodes[:6]:
        lines += ["## Face %d - %s (family %s, %s/%s)"
                  % (episode["face"], episode["role"], episode["family_id"],
                     episode["domain"], episode["archetype"]), "",
                  "Worked supports from: " + ", ".join(episode["support_families"]),
                  "", "```", episode["learner_input"].rstrip(), "```", "",
                  "Delivered choices (public order): `%s`; correct slot %d."
                  % (json.dumps(episode["delivered_choices"]),
                     episode["encoded_correct_index"]), "",
                  "Unlabelled recognition excerpt:", "", "```",
                  episode["recognition_input"].rstrip(), "```", "",
                  "Recognition choices: `%s`; correct slot %d."
                  % (json.dumps(episode["recognition_choices"]),
                     episode["recognition_correct_index"]), ""]
    excerpt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", excerpt.name, excerpt.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
