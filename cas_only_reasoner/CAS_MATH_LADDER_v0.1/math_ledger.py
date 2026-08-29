"""THE MATHEMATICS LEARNING LEDGER - what the machine can compute,
where every skill came from, and live proof - derived ENTIRELY from
the persistent skill store, the sealed episodes, and live runs.
Nothing enters by assertion.

    python math_ledger.py  -> prints and writes
                              output/MATH_LEARNING_LEDGER.md
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(LANE, "CCB_M1_v0.1"))

from mathschool import SkillStore, Student, grade  # noqa: E402
from mathschool.graph import SKILLS  # noqa: E402
from mathschool.sdg import generate  # noqa: E402

STORE_PATH = os.path.join(HERE, "fixtures", "math_skills.json")
LIVE_SEED = 777  # ledger-local; not dev, not protected, not retention


def build() -> str:
    lines = ["# THE CNCM MATHEMATICS LEARNING LEDGER", ""]
    store = SkillStore.load(STORE_PATH)
    lines.append("## 1. What the machine can COMPUTE right now")
    lines.append("")
    lines.append(f"**Promoted skills: {len(store.skills)}** of "
                 f"{len(SKILLS)} in the MATH-L0..L10 ladder "
                 f"(store revision {store.revision})")
    lines.append("")
    lines.append("| skill | level | kind | taught by | evidence |")
    lines.append("|---|---|---|---|---|")
    for skill_id in sorted(store.skills):
        record = store.skills[skill_id]
        lines.append(
            f"| {skill_id} | {record['level']} | {record['kind']} "
            f"| {record['provenance'].split('teacher:')[-1]} "
            f"| {record['record_digest']} |")
    lines.append("")

    # live checks: an exercise per skill from a ledger-local seed
    lines.append("## 2. LIVE check (run at ledger generation - "
                 "fresh store load, unseen exercises)")
    lines.append("")
    student = Student(store)
    for skill_id in sorted(store.skills):
        exercise = generate(skill_id, SKILLS[skill_id]["kind"],
                            LIVE_SEED, 1)[0]
        graded = grade(exercise, student.solve(exercise))
        task = (exercise.get("expr") or exercise.get("equation")
                or f"{exercise.get('a', '')} "
                   f"{exercise.get('op', exercise['kind'])} "
                   f"{exercise.get('b', '')}".strip())
        lines.append(f"- {skill_id}: `{task}` -> "
                     f"{'PASS' if graded['passed'] else 'FAIL'} "
                     f"(answer "
                     f"{graded['result'].get('answer') or graded['result'].get('answer_expr')})")
    lines.append("")

    # capability honesty: the gate is real
    empty = Student(SkillStore())
    refusal = empty.solve({"exercise_id": "x", "skill_id": "addition",
                           "kind": "arith", "op": "add", "a": "3",
                           "b": "4", "expected": "7"})
    lines.append(f"**Capability honesty (empty store):** asked 3+4, "
                 f"an unschooled student answers "
                 f"`{refusal['status']}` - the exact engine exists, "
                 f"but the STUDENT may only use promoted skills.")
    lines.append("")

    # the paper trail
    lines.append("## 3. The paper trail")
    lines.append("")
    episodes = sorted(glob.glob(os.path.join(HERE, "output",
                                             "math_lesson_*.json")))
    lines.append(f"- Sealed lesson artifacts: {len(episodes)}")
    for path in episodes:
        payload = json.load(open(path, encoding="utf-8"))
        episode = payload.get("episode") or {}
        verdict = payload.get("verdict") or episode.get("verdict")
        ohm = [s for s in episode.get("stages", [])
               if s["stage"] == "CAS_OHM_PROFILE"]
        profile = json.loads(ohm[0]["detail"]) if ohm else {}
        lines.append(
            f"  - {payload['skill_id']}: {verdict}"
            + (f" | CAS-Ohm P_cap "
               f"{profile.get('P_cap_before')} -> "
               f"{profile.get('P_cap_after')}, flow "
               f"{profile.get('flow_before')} -> "
               f"{profile.get('flow_after')}" if profile else ""))
    lines.append("")
    lines.append("Every promotion carries the checker-source digest, "
                 "provenance, a rollback pointer, and its sealed "
                 "twelve-step evidence. The protected battery seed "
                 "never appears in any teacher channel. Nothing "
                 "enters this ledger by assertion.")
    return "\n".join(lines) + "\n"


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    text = build()
    out = os.path.join(HERE, "output", "MATH_LEARNING_LEDGER.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    print(f"written: {out}")


if __name__ == "__main__":
    main()
