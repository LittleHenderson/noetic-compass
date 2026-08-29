"""THE FIRST LIVE TEACHER LESSON.

Qwen2.5-1.5B-Instruct (local snapshot, offline, greedy) is asked - as
a TEACHER - to author a LanguageLessonPacket for the English negation
construction. The student (CCB-L1's Apprentice) grades the lesson on
its own ten-stage acceptance ladder, with held-out generalization
cases from OUR protected channel (the teacher never sees them).

Either verdict is a valid first result: a promoted lesson is the
first model-taught grammar; a rejected lesson is the acceptance law
doing its job on live teacher output. The sealed episode records
which - honestly.
"""

import glob
import json
import os
import re
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(LANE, "CCB_L1_v0.1"))

from apprentice.board import ApprenticeshipBoard  # noqa: E402
from lang.apprentice import Apprentice  # noqa: E402
from lang.constructions import GrammarStore, MorphTable  # noqa: E402
from lang.lexicon import Lexicon  # noqa: E402

TEACHER_MODEL = os.environ.get("CAS_TEACHER_MODEL",
                               "Qwen/Qwen2.5-1.5B-Instruct")
_SLUG = TEACHER_MODEL.split("/")[-1].lower().replace(".", "_")

TEACHING_LEX = {
    "the": {"pos": "article", "sense": "the"},
    "cat": {"pos": "noun", "sense": "cat"},
    "dog": {"pos": "noun", "sense": "dog"},
    "bird": {"pos": "noun", "sense": "bird"},
    "fox": {"pos": "noun", "sense": "fox"},
    "hen": {"pos": "noun", "sense": "hen"},
}

# The worked example the teacher learns the packet format from
# (the already-promoted passive lesson, abridged).
FORMAT_EXAMPLE = {
    "lesson_id": "EXAMPLE_passive_past",
    "construction": {
        "construction_id": "passive_past",
        "surface_pattern": ["NP:patient", "was",
                            "VERB:pred:participle", "by", "NP:agent"],
        "semantics": {"frame": "event", "predicate": "@pred",
                      "agent": "@agent", "patient": "@patient",
                      "tense": "past", "polarity": "positive"},
        "surface_meta": {"voice": "passive"},
    },
    "positive_examples": [
        {"sentence": "the dog was chased by the cat.",
         "expected_core": {"frame": "event", "predicate": "chase",
                           "agent": "cat", "patient": "dog",
                           "tense": "past", "polarity": "positive"}}],
    "minimal_pairs": [
        {"sentence_a": "the dog was chased by the cat.",
         "sentence_b": "the cat was chased by the dog.",
         "relation": "different_meaning"}],
    "counterexamples": [{"sentence": "the dog was chased the cat."}],
    "ambiguity_cases": [{"sentence": "the dog was chased by the cat.",
                         "expect": "parsed"}],
    "morphology": [{"surface": "chased", "lemma": "chase",
                    "form": "past_or_participle"}],
}

PROMPT = (
    "You are a grammar TEACHER for a symbolic language-learning "
    "machine. The machine learns CONSTRUCTIONS: a surface pattern of "
    "slots and fixed words, plus a semantic mapping. Slots: "
    "'NP:name' matches 'the NOUN'; 'VERB:name:form' matches a verb "
    "in that form (forms: past, participle, base). Semantics use "
    "'@name' to reference slots and must include tense and polarity.\n"
    "Here is a complete example lesson packet (JSON):\n"
    + json.dumps(FORMAT_EXAMPLE, indent=1) +
    "\n\nNow author a NEW lesson packet, in EXACTLY the same JSON "
    "format, for the English NEGATED PRESENT construction:\n"
    "  pattern: 'the X does not VERB the Y'  (verb in BASE form)\n"
    "  meaning: an event with predicate=verb, agent=X, patient=Y, "
    "tense 'present', polarity 'negative'.\n"
    "Use ONLY these nouns: cat, dog, bird, fox, hen. Use ONLY the "
    "verb chase (base form 'chase' - include it in morphology with "
    "form 'base'). Give 2 positive_examples, 2 minimal_pairs (the "
    "negated sentence vs its positive counterpart must be "
    "different_meaning, and role reversal must be different_meaning), "
    "2 counterexamples (malformed negation), 1 ambiguity_case with "
    "expect 'parsed', lesson_id 'LIVE_L001_negation_present', and "
    "construction_id 'negated_present_transitive'.\n"
    "Output ONLY the JSON object."
)

# OUR protected held-out channel - the teacher never sees these.
HELD_OUT = [
    {"sentence": "the fox does not chase the hen.",
     "expected_core": {"frame": "event", "predicate": "chase",
                       "agent": "fox", "patient": "hen",
                       "tense": "present", "polarity": "negative"}},
    {"sentence": "the bird does not chase the cat.",
     "expected_core": {"frame": "event", "predicate": "chase",
                       "agent": "bird", "patient": "cat",
                       "tense": "present", "polarity": "negative"}},
    {"sentence": "the does not chase fox hen.", "expect": "no_parse"},
]


def find_snapshot(model_name: str) -> str:
    base = os.path.expanduser(
        "~/.cache/huggingface/hub/models--"
        + model_name.replace("/", "--") + "/snapshots")
    snapshots = sorted(glob.glob(os.path.join(base, "*")))
    if not snapshots:
        raise SystemExit(f"no local snapshot for {model_name}")
    return snapshots[-1]


def extract_json(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # STANDING OWNER ORDER (2026-08-28): never CPU for model
    # inference - GPU, RunPod, or AWS only.
    if not torch.cuda.is_available():
        raise SystemExit(
            "REFUSING to run on CPU (standing owner order). Run this "
            "under the CUDA venv (~/venvs/cas-gpu) or on RunPod/AWS.")

    snapshot = find_snapshot(TEACHER_MODEL)
    print(f"loading teacher {TEACHER_MODEL} on "
          f"{torch.cuda.get_device_name(0)}")
    print(f"  snapshot: {os.path.basename(snapshot)}")
    start = time.time()
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    model = AutoModelForCausalLM.from_pretrained(
        snapshot, dtype=torch.float16, device_map="cuda")
    model.eval()
    print(f"  loaded in {time.time() - start:.0f}s")

    def generate(messages):
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to("cuda")
        start = time.time()
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=1200,
                                 do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
        reply = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:],
                                 skip_special_tokens=True).strip()
        print(f"  generated in {time.time() - start:.0f}s "
              f"({len(reply)} chars)")
        return reply

    messages = [{"role": "user", "content": PROMPT}]
    raw = generate(messages)

    # CHECKPOINT the expensive part immediately - a session restart
    # must never orphan the generation again
    ckpt = os.path.join(HERE, "output", f"live_teacher_raw_{_SLUG}.json")
    os.makedirs(os.path.dirname(ckpt), exist_ok=True)
    with open(ckpt, "w", encoding="utf-8") as fh:
        json.dump({"teacher": TEACHER_MODEL,
                   "snapshot": os.path.basename(snapshot),
                   "device": torch.cuda.get_device_name(0),
                   "raw_teacher_output": raw}, fh, indent=1)

    lesson_packet = extract_json(raw)
    board = ApprenticeshipBoard()

    if lesson_packet is None:
        outcome = {"verdict": "REJECTED_MALFORMED_LESSON",
                   "evidence": "teacher output was not parseable JSON"}
        episode = board._seal(
            {"lesson_id": "LIVE_L001_negation_present",
             "domain": "language_grammar",
             "target": "grammar_store",
             "teacher_model": TEACHER_MODEL,
             "teacher_revision": os.path.basename(snapshot),
             "teacher_role": "lecturer",
             "examiner_identity": "ccb_l1_acceptance_ladder",
             "provenance": "first_live_teacher_lesson"},
            outcome, None, None)
    else:
        # complete the packet's required administrative fields (the
        # teacher authored the CONTENT; identity comes from the run)
        lesson_packet.setdefault("lesson_id",
                                 "LIVE_L001_negation_present")
        lesson_packet["lesson_type"] = "grammar_construction"
        lesson_packet["teacher_model"] = TEACHER_MODEL
        lesson_packet["teacher_revision"] = os.path.basename(snapshot)
        lesson_packet["teacher_confidence"] = None
        lesson_packet["provenance"] = "first_live_teacher_lesson"
        lesson_packet.setdefault("morphology", [])

        student = Apprentice(Lexicon(TEACHING_LEX), MorphTable(),
                             GrammarStore())

        def ladder_channel(meta):
            ladder = student.learn(lesson_packet,
                                   held_out_cases=HELD_OUT)
            return {"verdict": ladder["verdict"],
                    "evidence": ladder["stages"],
                    "episode_digest": ladder["episode_digest"]}

        episode = board.teach(
            {"lesson_id": lesson_packet["lesson_id"],
             "domain": "language_grammar",
             "target": "grammar_store",
             "teacher_model": TEACHER_MODEL,
             "teacher_revision": os.path.basename(snapshot),
             "teacher_role": "lecturer",
             "examiner_identity": "ccb_l1_acceptance_ladder",
             "provenance": "first_live_teacher_lesson"},
            ladder_channel)

        # THE SOCRATIC RETRY (faculty doctrine: the ladder's typed
        # defects go back to the teacher ONCE; the examiner is
        # unchanged; attempt 2 is graded on the same law)
        attempts = [{"attempt": 1, "raw": raw, "episode": episode}]
        if str(episode["outcome"]["verdict"]).startswith("REJECTED"):
            defects = json.dumps(episode["outcome"]["evidence"],
                                 indent=1, default=str)[:1500]
            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content":
                             "Your lesson was REJECTED by the "
                             "student's acceptance ladder. The typed "
                             "defects were: " + defects +
                             " ... Author a CORRECTED lesson packet in "
                             "the exact same JSON format. Remember: "
                             "every VERB slot needs BOTH a name and a "
                             "form, like 'VERB:pred:base', and every "
                             "'@name' in semantics must reference a "
                             "declared slot name. Output ONLY the "
                             "JSON object."})
            raw2 = generate(messages)
            packet2 = extract_json(raw2)
            if packet2 is not None:
                packet2.setdefault("lesson_id",
                                   "LIVE_L001_negation_present_r2")
                packet2["lesson_type"] = "grammar_construction"
                packet2["teacher_model"] = TEACHER_MODEL
                packet2["teacher_revision"] = os.path.basename(snapshot)
                packet2["teacher_confidence"] = None
                packet2["provenance"] = "live_teacher_socratic_retry"
                packet2.setdefault("morphology", [])
                student2 = Apprentice(Lexicon(TEACHING_LEX),
                                      MorphTable(), GrammarStore())

                def ladder2(meta):
                    ladder = student2.learn(packet2,
                                            held_out_cases=HELD_OUT)
                    return {"verdict": ladder["verdict"],
                            "evidence": ladder["stages"],
                            "episode_digest": ladder["episode_digest"]}

                episode = board.teach(
                    {"lesson_id": packet2["lesson_id"],
                     "domain": "language_grammar",
                     "target": "grammar_store",
                     "teacher_model": TEACHER_MODEL,
                     "teacher_revision": os.path.basename(snapshot),
                     "teacher_role": "lecturer",
                     "examiner_identity": "ccb_l1_acceptance_ladder",
                     "provenance": "live_teacher_socratic_retry"},
                    ladder2)
                lesson_packet = packet2
                raw = raw2
            attempts.append({"attempt": 2, "raw": raw2,
                             "episode": episode})

    artifact = {
        "event": "FIRST_LIVE_TEACHER_LESSON",
        "attempts": [{"attempt": a["attempt"],
                      "verdict": a["episode"]["outcome"]["verdict"]}
                     for a in attempts] if lesson_packet else [],
        "teacher": TEACHER_MODEL,
        "teacher_snapshot": os.path.basename(snapshot),
        "raw_teacher_output": raw,
        "parsed_lesson": lesson_packet,
        "episode": episode,
        "held_out_channel": "protected (authored by the student's "
                            "side, never shown to the teacher)",
    }
    out_path = os.path.join(HERE, "output",
                            f"live_teacher_episode_{_SLUG}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=1, sort_keys=True)

    print(f"\nVERDICT: {episode['outcome']['verdict']}")
    if lesson_packet is not None and "evidence" in episode["outcome"] \
            and isinstance(episode["outcome"]["evidence"], list):
        for stage in episode["outcome"]["evidence"]:
            flag = "PASS" if stage["passed"] else "FAIL"
            print(f"  [{flag}] {stage['stage']}: "
                  f"{stage['detail'][:70]}")
    print(f"sealed: {out_path}")


if __name__ == "__main__":
    main()
