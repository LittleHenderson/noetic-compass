"""dataset_assembly.py -- builds per-arm training/eval examples from records.

Two laws enforced HERE, at the only place examples are built:

1. NO-GOLD-AT-RUNTIME (audit section 2): an assembled example carries ONLY what
   the arm consumes -- profiles (already resolved per the arm's frozen source),
   candidates, the gold ANSWER index (the supervised target of the task), and
   bookkeeping. The construction-gold CLASS labels (idea_labels) and the formal
   trace (seed_trace) are STRIPPED for every arm, so a corrupted-label arm cannot
   read the gold classes at training runtime.

2. NO-PROTECTED-PATH (audit section 2): assembling a protected record raises
   ProtectedPathError unless the caller is the protected evaluator (which passes
   allow_protected=True exactly once, after all training completes).
"""
from __future__ import annotations

try:
    from exec.labels import profile_vectors
except ImportError:                                   # flat import inside exec/
    from labels import profile_vectors


class ProtectedPathError(RuntimeError):
    pass


ALLOWED_EXAMPLE_KEYS = frozenset(
    ["passage_id", "split", "text", "question", "question_type", "clauses",
     "candidates", "answer_index", "profiles", "n_ideas"])


def assemble_examples(records, arm_id, *, verb_to_class=None, allow_protected=False):
    out = []
    for rec in records:
        if rec["split"] == "protected" and not allow_protected:
            raise ProtectedPathError(
                "PROTECTED_PATH_REFUSED: only the protected evaluator may touch "
                "protected records, exactly once, after all training completes")
        profiles = profile_vectors(arm_id, rec, verb_to_class)
        ex = {"passage_id": rec["passage_id"], "split": rec["split"],
              "text": rec["text"], "question": rec["question"],
              "question_type": rec["question_type"],
              "clauses": [c["text"] for c in rec["clauses"]],
              "candidates": list(rec["candidates"]),
              "answer_index": rec["candidates"].index(rec["answer"]),
              "profiles": profiles, "n_ideas": len(rec["clauses"])}
        # typed raise, not a bare assert (asserts vanish under python -O)
        if not set(ex) <= ALLOWED_EXAMPLE_KEYS or "idea_labels" in ex \
                or "seed_trace" in ex:
            raise ProtectedPathError(
                "GOLD_LEAK_REFUSED: assembled example carries unregistered keys")
        out.append(ex)
    return out
