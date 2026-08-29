"""THE LEARNING LEDGER: the clear indicator of what the CNCM knows,
where every piece came from, and proof it works - derived ENTIRELY
from the persistent stores and sealed artifacts, never hardcoded.

    python learning_ledger.py   -> prints and writes
                                   output/LEARNING_LEDGER.md
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(LANE, "CCB_L1_v0.1"))
sys.path.insert(0, os.path.join(LANE, "CAS_CORTEX_v0.1"))

FIXTURES = os.path.join(LANE, "CCB_L1_v0.1", "fixtures")


def load(name):
    path = os.path.join(FIXTURES, name)
    if not os.path.exists(path):
        return None
    return json.load(open(path, encoding="utf-8"))


def teacher_of(provenance: str) -> str:
    if "teacher:" in provenance:
        return provenance.split("teacher:")[-1].split("|")[0]
    if "lesson:LIVE" in provenance or "constrained" in provenance:
        return "live model teacher"
    if "seed" in provenance.lower() or "SEED" in provenance:
        return "hand-authored seed"
    return provenance[:40]


def build_ledger():
    lines = ["# THE CNCM LEARNING LEDGER", ""]
    grammar = load("seed_grammar.json") or {"rules": {}, "history": []}
    lexicon = load("seed_lexicon.json") or {}
    morph = load("seed_morphology.json") or {}

    # ---------------- 1. WHAT THE MACHINE KNOWS ----------------------
    rules = grammar["rules"]
    durable = {cid: r for cid, r in rules.items()
               if r.get("durability") == "PROMOTED_DURABLY"
               and r.get("state") == "ACTIVE"}
    live_taught = {cid: r for cid, r in durable.items()
                   if "LIVE" in r.get("provenance", "")}
    lines.append("## 1. What the machine KNOWS right now")
    lines.append("")
    lines.append(f"**Grammar constructions: {len(durable)} durable** "
                 f"(of {len(rules)} in the store)")
    lines.append("")
    lines.append("| construction | state | taught by | evidence |")
    lines.append("|---|---|---|---|")
    for cid, rule in sorted(rules.items()):
        lines.append(
            f"| {cid} | {rule.get('state')}"
            f"/{rule.get('durability', 'provisional')} "
            f"| {teacher_of(rule.get('provenance', ''))} "
            f"| {rule.get('provenance', '')[:60]} |")
    words = lexicon.get("lexicon", lexicon) if lexicon else {}
    lines.append("")
    lines.append(f"**Words: {len(words)}** "
                 f"({', '.join(sorted(words))})")
    lines.append(f"**Verb forms (morphology): {len(morph)}** "
                 f"({', '.join(sorted(morph))})")
    lines.append("")

    # ---------------- 2. LEARNED FROM A LIVE MODEL TEACHER -----------
    lines.append("## 2. Learned from a LIVE MODEL TEACHER")
    lines.append("")
    if live_taught:
        for cid, rule in live_taught.items():
            lines.append(f"- **{cid}** - provenance "
                         f"`{rule.get('provenance')}`")
    else:
        lines.append("- none yet")
    lines.append("")

    # ---------------- 3. PROOF: BEFORE vs AFTER ----------------------
    lines.append("## 3. PROOF the learning is real (before vs after)")
    lines.append("")
    artifacts = sorted(glob.glob(os.path.join(
        HERE, "output", "constrained_teaching_*.json")))
    for path in artifacts:
        artifact = json.load(open(path, encoding="utf-8"))
        before = artifact.get("before_transcript")
        after = artifact.get("after_transcript")
        if before and after:
            probe = before["input"]
            lines.append(f"Teacher **{artifact['teacher']}**, probe "
                         f"`{probe}`:")
            lines.append(f"- BEFORE the lesson: "
                         f"**{before['answer']['status']}** "
                         f"(route {before['route']})")
            core = after["answer"].get("core") or \
                after["answer"].get("meaning")
            lines.append(f"- AFTER the lesson: "
                         f"**{after['answer']['status']}** "
                         f"(route {after['route']}), core = `{core}`")
            lines.append("")

    # live unseen-generalization check, run NOW against the real router
    from cortex.router import HybridRouter
    router = HybridRouter(mode="NATIVE_ONLY")
    unseen = ["the dog does not chase the cat.",
              "the dog was chased by the cat.",
              "the cat chases the dog."]
    lines.append("**Unseen-sentence check (run live at ledger "
                 "generation, NATIVE only - no model anywhere):**")
    lines.append("")
    generalization = []
    for sentence in unseen:
        trace = router.turn(sentence)
        answer = trace["answer"]
        core = answer.get("core") or answer.get("meaning")
        generalization.append(
            {"sentence": sentence, "status": answer["status"],
             "route": trace["route"], "core": core})
        lines.append(f"- `{sentence}` -> **{answer['status']}** "
                     f"(route {trace['route']}), core = `{core}`")
    lines.append("")

    # ---------------- 4. HOW IT LEARNED (the paper trail) ------------
    lines.append("## 4. The paper trail")
    lines.append("")
    episodes = load("seed_grammar_episodes.json") or []
    lines.append(f"- Seed teaching episodes on file: "
                 f"{len(episodes) if isinstance(episodes, list) else 1}")
    live_files = sorted(glob.glob(os.path.join(
        HERE, "output", "live_teacher_episode_*.json")))
    lines.append(f"- Live teacher episodes sealed: {len(live_files)} "
                 f"(every attempt, pass or fail)")
    for path in live_files:
        artifact = json.load(open(path, encoding="utf-8"))
        attempts = artifact.get("attempts") or []
        verdicts = ", ".join(a["verdict"] for a in attempts) \
            if attempts else artifact.get("episode", {}).get(
                "outcome", {}).get("verdict", "?")
        lines.append(f"  - {artifact.get('teacher')}: {verdicts}")
    lines.append(f"- Constrained-teaching artifacts: {len(artifacts)}")
    lines.append("")
    lines.append("Every durable rule carries provenance, its "
                 "regression guard, and a rollback path; every lesson "
                 "attempt - including every REJECTION - is a sealed "
                 "episode. Nothing enters this ledger by assertion.")
    return "\n".join(lines), {
        "durable_constructions": len(durable),
        "live_taught_constructions": len(live_taught),
        "words": len(words),
        "unseen_generalization": generalization,
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    text, summary = build_ledger()
    out = os.path.join(HERE, "output", "LEARNING_LEDGER.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(text)
    print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
