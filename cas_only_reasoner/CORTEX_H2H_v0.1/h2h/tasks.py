"""The head-to-head task battery: identical for both routes.

Gold meanings use CCB-L1's own packet schema so ONE grader and ONE
kernel judge both routes. The few-shot examples used to prompt Route B
are DISJOINT from every scored item (held-out discipline for both
routes: Route A's 'training' is its seed lexicon; Route B's 'training'
is its prompt; neither training item is scored).
"""

from __future__ import annotations

from typing import Dict, List

# ---------------------------------------------------------------------
# Dimension 1: in-fragment parsing (Route A's home ground).
IN_FRAGMENT_PARSE: List[Dict] = [
    {"task_id": "p1", "sentence": "the cat is gray.",
     "gold": {"pred": "property", "args": ["cat", "gray"]}},
    {"task_id": "p2", "sentence": "the dog is brown.",
     "gold": {"pred": "property", "args": ["dog", "brown"]}},
    {"task_id": "p3", "sentence": "the dog is not gray.",
     "gold": {"pred": "negation",
              "args": [{"pred": "property", "args": ["dog", "gray"]}]}},
    {"task_id": "p4", "sentence": "the cat chases the dog.",
     "gold": {"pred": "relation", "args": ["chase", "cat", "dog"]}},
    {"task_id": "p5", "sentence": "the cat is not quiet.",
     "gold": {"pred": "negation",
              "args": [{"pred": "property", "args": ["cat", "quiet"]}]}},
    {"task_id": "p6", "sentence": "the dog chases the cat.",
     "gold": {"pred": "relation", "args": ["chase", "dog", "cat"]}},
]

# ---------------------------------------------------------------------
# Dimension 2: question answering - the SAME kernel judges both routes'
# meaning packets; gold is the kernel status plus the decoded answer.
QUESTION_ANSWERING: List[Dict] = [
    {"task_id": "q1", "sentence": "is the cat gray?",
     "gold_status": "CONCLUDED", "gold_answer": "yes, the cat is gray."},
    {"task_id": "q2", "sentence": "is the dog brown?",
     "gold_status": "CONCLUDED", "gold_answer": "yes, the dog is brown."},
    {"task_id": "q3", "sentence": "is the dog quiet?",
     "gold_status": "NEEDS_INFORMATION",
     "gold_answer": "i do not know whether the dog is quiet."},
    {"task_id": "q4", "sentence": "is the cat brown?",
     "gold_status": "NEEDS_INFORMATION",
     "gold_answer": "i do not know whether the cat is brown."},
]

# ---------------------------------------------------------------------
# Dimension 3: unknown-word honesty - the machine must SIGNAL the
# unknown, never fabricate a packet around it.
UNKNOWN_HONESTY: List[Dict] = [
    {"task_id": "u1", "sentence": "the zog is gray.", "unknown_word": "zog"},
    {"task_id": "u2", "sentence": "the cat is flurmous.",
     "unknown_word": "flurmous"},
    {"task_id": "u3", "sentence": "is the blicket gray?",
     "unknown_word": "blicket"},
    {"task_id": "u4", "sentence": "the dog snarfles the cat.",
     "unknown_word": "snarfles"},
]

# ---------------------------------------------------------------------
# Dimension 4: out-of-fragment breadth (Route B's home ground). Gold is
# a flat slot dict; scoring is exact slot matches / gold slots. Route A
# is EXPECTED to refuse with a typed error (honest CANNOT, breadth 0).
BREADTH: List[Dict] = [
    {"task_id": "b1", "sentence": "alice gave the book to maria.",
     "gold": {"event": "give", "agent": "alice", "object": "book",
              "recipient": "maria", "tense": "past"}},
    {"task_id": "b2", "sentence": "the boy ate the red apple.",
     "gold": {"event": "eat", "agent": "boy", "object": "apple",
              "object_property": "red", "tense": "past"}},
    {"task_id": "b3", "sentence": "maria will visit the museum.",
     "gold": {"event": "visit", "agent": "maria", "object": "museum",
              "tense": "future"}},
    {"task_id": "b4", "sentence": "the cup is on the table.",
     "gold": {"relation": "on", "figure": "cup", "ground": "table"}},
    {"task_id": "b5", "sentence": "bob believes the story.",
     "gold": {"event": "believe", "agent": "bob", "object": "story",
              "tense": "present"}},
    {"task_id": "b6", "sentence": "the teacher praised the student.",
     "gold": {"event": "praise", "agent": "teacher", "object": "student",
              "tense": "past"}},
]

# ---------------------------------------------------------------------
# Route B's few-shot prompt examples - DISJOINT from all scored items.
FEWSHOT_FRAGMENT: List[Dict] = [
    {"sentence": "the sky is blue.",
     "packet": {"pred": "property", "args": ["sky", "blue"]}},
    {"sentence": "the bird is not small.",
     "packet": {"pred": "negation",
                "args": [{"pred": "property", "args": ["bird", "small"]}]}},
    {"sentence": "the fox chases the hen.",
     "packet": {"pred": "relation", "args": ["chase", "fox", "hen"]}},
    {"sentence": "is the sun hot?",
     "packet": {"pred": "question",
                "args": [{"pred": "property", "args": ["sun", "hot"]}]}},
    {"sentence": "the wug is tall.",
     "packet": {"error": "unknown word", "word": "wug"}},
]

FEWSHOT_BREADTH: List[Dict] = [
    {"sentence": "tom sent the letter to anna.",
     "packet": {"event": "send", "agent": "tom", "object": "letter",
                "recipient": "anna", "tense": "past"}},
    {"sentence": "the girl will read the long novel.",
     "packet": {"event": "read", "agent": "girl", "object": "novel",
                "object_property": "long", "tense": "future"}},
]

# Words Route B may treat as KNOWN vocabulary for the honesty dimension
# (everything in the seed lexicon plus scored-entity nouns).
KNOWN_WORDS = sorted({
    "the", "is", "not", "it", "cat", "dog", "gray", "brown", "quiet",
    "chases",
})


def all_scored_sentences() -> List[str]:
    battery = (IN_FRAGMENT_PARSE + QUESTION_ANSWERING + UNKNOWN_HONESTY
               + BREADTH)
    return [t["sentence"] for t in battery]


def fewshot_sentences() -> List[str]:
    return [e["sentence"] for e in FEWSHOT_FRAGMENT + FEWSHOT_BREADTH]
