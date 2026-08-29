"""TALK TO THE MACHINE - the CONV v0.1 terminal.

    python chat.py            one session; ctrl+c or 'quit' to leave
    python chat.py --trace    also print route/status/source per turn

Every reply comes from the native runtime (no model anywhere at
runtime). What you assert is remembered WITH its source and answered
back only as "based on what you told me"; verified facts say so;
unknowns are honest; conflicts are surfaced, never resolved silently.
The session ends when you leave - session assertions are
session-scoped by design.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
for path in (HERE, os.path.join(LANE, "CAS_CORTEX_v0.1"),
             os.path.join(LANE, "CCB_L1_v0.1")):
    if path not in sys.path:
        sys.path.insert(0, path)

from cortex.router import HybridRouter  # noqa: E402

# example sentences that are KNOWN to parse (each covers one taught
# family). These are canonical probes, not free text.
EXAMPLES = [
    ("greet", "hello."),
    ("tell a fact", "the cat chases the dog."),
    ("ask about it", "does the cat chase the dog?"),
    ("wh-question", "what does the cat chase?"),
    ("negation", "the cat does not chase the dog."),
    ("adjectives", "the gray cat chases the brown dog."),
    ("a question", "is the cat gray?"),
    ("arithmetic", "what is three plus four?"),
    ("comparison", "is three greater than four?"),
    ("solve", "solve x plus three equals seven."),
    ("class rule", "every cat is an animal."),
    ("membership", "milo is a cat."),
    ("derive", "is milo an animal?"),
    ("correct", "actually, the cat chases the fox."),
    ("retract", "forget what i said about the cat."),
    ("thank / bye", "thank you."),
]


def print_help(router) -> None:
    from collections import defaultdict
    lexicon = router.seed["lexicon"]
    by_pos = defaultdict(list)
    for word, entry in sorted(lexicon.items()):
        by_pos[entry["pos"]].append(word)
    print("machine> i only understand the words and sentence shapes "
          "i was taught. here they are.")
    print("\n  WORDS I KNOW (everything else i will refuse, not "
          "guess):")
    labels = {"noun": "nouns", "verb": "verbs", "adj": "adjectives",
              "number": "numbers", "quant": "quantifiers",
              "mathop": "math words", "pronoun": "pronouns",
              "adv": "time words", "article": "articles",
              "copula": "copula", "negation": "negation"}
    for pos in ("noun", "verb", "adj", "number", "quant", "mathop",
                "pronoun", "adv"):
        if by_pos.get(pos):
            print(f"    {labels[pos]:12}: "
                  f"{', '.join(by_pos[pos])}")
    print("\n  SENTENCES THAT WORK (copy one, or swap in a known "
          "word):")
    for label, sentence in EXAMPLES:
        print(f"    [{label:12}] {sentence}")
    print("\n  lowercase, end with . or ?  -  'quit' to leave, "
          "'help' to see this again.")


def main() -> None:
    show_trace = "--trace" in sys.argv
    router = HybridRouter(mode="NATIVE_ONLY")
    print("CONV v0.1 - the CNCM dialogue terminal. type 'help' to "
          "see the words and sentences i know. lowercase, end with "
          ". or ?  ('quit' to leave)")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("quit", "exit"):
            break
        if line.lower() in ("help", "words", "?"):
            print_help(router)
            continue
        trace = router.turn(line)
        answer = trace["answer"]
        reply = (answer.get("text") or answer.get("acknowledgment")
                 or answer.get("detail") or answer.get("status"))
        print(f"machine> {reply}")
        if answer.get("status") == "UNSUPPORTED_LANGUAGE":
            print("machine> (that used a word or shape i was not "
                  "taught - type 'help' to see what i know.)")
        if show_trace:
            print(f"    [route={trace.get('route')} "
                  f"status={answer.get('status')} "
                  f"source={answer.get('source_class')}]")
    active = router.dialogue.store.active()
    if active:
        print("\nsession assertions on the record at exit "
              "(session-scoped, not persisted):")
        for record in router.dialogue.store.records:
            print(f"  {record['assertion_id']} "
                  f"{record['lifecycle_status']:10} "
                  f"{record['clause']}")


if __name__ == "__main__":
    main()
