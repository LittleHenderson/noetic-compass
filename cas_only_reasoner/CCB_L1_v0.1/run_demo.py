"""CCB-L1 v0.1 demonstration: parse, learn, ask, answer."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lang.l1 import CCB_L1

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_fixture(name):
    with open(os.path.join(ROOT, "fixtures", name), "r",
              encoding="utf-8") as fh:
        return json.load(fh)


def main():
    print("CCB-L1 v0.1 - the English acquisition board")
    print("=" * 64)
    l1 = CCB_L1(load_fixture("seed_lexicon.json"))

    print("Round-trip (English -> CAS-Sem -> English):")
    for sentence in ("the cat is gray.", "the dog chases the cat.",
                     "the cat is not brown.", "is the cat gray?"):
        result = l1.roundtrip(sentence) if not sentence.endswith("?") else None
        meaning = l1.parse(sentence)
        surface = l1.generate(meaning)
        stable = l1.parse(surface) == meaning
        mark = "PASS" if stable else "FAIL"
        print(f"  {mark}  {sentence:<28} -> {surface:<28} stable={stable}")

    print()
    print("Grounding (the kernel reasons, CCB-L1 only encodes/decodes):")
    for question in ("is the cat gray?", "is the dog gray?"):
        result = l1.ask(question)
        print(f"  {question:<20} kernel={result['kernel_status']:<20} "
              f"-> {result['answer']}")

    print()
    print("Learning a new word (flurpy):")
    try:
        l1.parse("the cat is flurpy.")
    except Exception as exc:
        print(f"  unknown word detected: {exc.message()}")
    cycle = l1.teach(load_fixture("teach_flurpy.json"))
    for decision in cycle["decisions"]:
        print(f"  {decision['verdict']:<10} sense '{decision['candidate_sense']}'")
    print(f"  promoted: {cycle['promoted_sense']} (verified)")

    correction = l1.correct("flurpy", "black")
    print(f"  corrected to '{correction['new_sense']}' "
          f"(revision {correction['revision']}, history keeps the old sense)")


if __name__ == "__main__":
    main()
