"""helm_faces_in.py -- a small, deterministic English reader for the three FACES of an ingredient (HELM-R1 wave 3).

WHAT IT DOES (plain words)
--------------------------
A person may say how things stand with an ingredient, not just how much of it there is:

    "We have 12 cups of flour but I barely know how to use it."   -> Flour: Wisdom is Rising
    "The yeast is getting old."                                    -> Yeast: Power is Waning
    "There's no reason to bake bread today."                       -> Bread (the recipe): Purpose is Absent

This reader finds those statements and nothing else. Each face goes on the owner's ONE scale (Rising 1/4, Peak 1,
Waning 1/2, Absent 0). It returns the faces it read and the rest of the text (the stock part), which goes on to
HELM's stock reader (helm_english_in) exactly as before.

HOW (the whole rule)
--------------------
* Every face comes from one row of the frozen lexicon `helm_faces_lexicon.json` (each row carries its source).
  Nothing else can make a face. No guessing, no learned weights, no similarity score.
* A sentence is split into clauses at "but", "and", ";" and ",". A question clause is never read as a face.
* "it" / "them" / "this" / "that" stands for the ONE ingredient named in the same input. None or two named: ask.
* A clause that holds a face cue word (the lexicon's `cue_words`, e.g. "rusty", "old", "dead") and names an
  ingredient, a product or a pronoun, but matches no row, is NOT guessed: the reader asks (FACE_UNREAD).
* A clause with "not" / "n't" / "never" that matches a row not marked `negation_ok` is not taken: it asks
  (FACE_NEGATED).
* When it asks, it returns no faces and no remainder: the turn writes nothing.

WHAT IT IS NOT
--------------
It does not write anything. It does not hold the faces (helm_triad.TriadTable does, with receipts). It does not
lower a Wisdom face on its own: rule C (owner ruling 2026-10-18) is enforced by TriadTable.set_face, not here.
It understands no English beyond its lexicon rows.

CLAIM STATUS: ENGINEERED-NOT-VALIDATED. SYNTHETIC_ONLY. Zero learned parameters.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
LEXICON_PATH = os.path.join(HERE, "helm_faces_lexicon.json")
READER_VERSION = "helm_faces_in v1 (2026-10-19)"
CLAIM_STATUS = "ENGINEERED-NOT-VALIDATED"

with open(LEXICON_PATH, "rb") as _h:
    _LEX_BYTES = _h.read()
LEXICON: Dict[str, Any] = json.loads(_LEX_BYTES.decode("utf-8"))
LEXICON_SHA256 = hashlib.sha256(_LEX_BYTES).hexdigest()

#: The same OUR_CONVENTION everyday names as helm_english_in (copied, so this module imports nothing of HELM's).
EVERYDAY_INGREDIENTS: Dict[str, str] = {
    "flour": "Flour", "water": "Water", "sugar": "Sugar", "butter": "Butter", "milk": "Milk",
    "egg": "Egg", "eggs": "Egg", "yeast": "Yeast", "salt": "Salt",
}
EVERYDAY_PRODUCTS: Dict[str, str] = {
    "bread": "Bread", "breads": "Bread", "loaf": "Bread", "loaves": "Bread",
    "frosting": "Frosting", "starter": "Starter", "starters": "Starter",
    "meringue": "Meringue", "meringues": "Meringue",
}
PRONOUNS = ("it", "them", "this", "that", "they")
NEGATION_RX = re.compile(r"\bnot\b|n't\b|\bnever\b")
CLAUSE_SPLIT_RX = re.compile(r"\s*;\s*|\s*,\s*|\s+but\s+|\s+and\s+")
SENTENCE_SPLIT_RX = re.compile(r"(?<=[.!?])\s+")
Q_START = {"can", "could", "how", "what", "do", "does", "did", "is", "are", "will", "would", "should", "shall",
           "which", "who", "when", "where", "why"}

STATUS_NONE, STATUS_FACES, STATUS_CLARIFY = "NONE", "FACES", "CLARIFY"


def normalize(text: str) -> str:
    t = (text or "").replace("’", "'").replace("‘", "'").lower()
    return re.sub(r"[ \t]+", " ", t).strip()


def _alt(words: Sequence[str]) -> str:
    return "|".join(sorted((re.escape(w) for w in words), key=len, reverse=True))


def _compile_rows(ingredients: Sequence[str], products: Sequence[str]) -> List[Tuple[Dict[str, Any], "re.Pattern"]]:
    ing_words = [w for w, n in EVERYDAY_INGREDIENTS.items() if n in ingredients]
    prod_words = [w for w, n in EVERYDAY_PRODUCTS.items() if n in products]
    ing = _alt(ing_words)
    obj = r"(?P<obj>(?:the |our |my )?(?:%s)|%s)" % (ing, _alt(PRONOUNS))
    subj = r"(?P<subj>(?:the |our |my )?(?:%s|it|they))" % ing
    prod = r"(?P<prod>%s)" % _alt(prod_words)
    out = []
    for row in LEXICON["rows"]:
        pat = row["pattern"].replace("{OBJ}", obj).replace("{SUBJ}", subj).replace("{PROD}", prod)
        out.append((row, re.compile(r"(?<![a-z'])" + pat + r"(?![a-z'])")))
    return out


def _named_ingredients(text_norm: str, ingredients: Sequence[str]) -> List[str]:
    found = []
    for w, n in EVERYDAY_INGREDIENTS.items():
        if n in ingredients and re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(w), text_norm) and n not in found:
            found.append(n)
    return found


def _ref_word(fragment: str) -> Optional[str]:
    """'the flour' -> 'flour'; 'it' -> 'it'."""
    w = re.sub(r"^(?:the|our|my) ", "", fragment.strip())
    return w


def _is_question(clause: str, sentence: str) -> bool:
    words = re.findall(r"[a-z']+", clause)
    return sentence.rstrip().endswith("?") or (bool(words) and words[0] in Q_START)


def _mentions(clause: str, ingredients: Sequence[str], products: Sequence[str]) -> bool:
    names = [w for w, n in EVERYDAY_INGREDIENTS.items() if n in ingredients] + \
            [w for w, n in EVERYDAY_PRODUCTS.items() if n in products] + list(PRONOUNS)
    return re.search(r"(?<![a-z'])(?:%s)(?![a-z'])" % _alt(names), clause) is not None


def read(text: str, ingredients: Sequence[str], products: Sequence[str]) -> Dict[str, Any]:
    """Read face statements. Returns {status, faces, remainder, clarify, rows, lexicon, reader}.

    status NONE: no face statement (remainder = the text unchanged).
    status FACES: faces read; remainder = the text without the face clauses ('' if nothing is left).
    status CLARIFY: the reader will not guess; faces [] and remainder '' (the turn writes nothing)."""
    base = {"reader": READER_VERSION, "lexicon": {"sha256": LEXICON_SHA256, "rows": len(LEXICON["rows"])},
            "claim_status": CLAIM_STATUS}
    norm = normalize(text)
    rows = _compile_rows(ingredients, products)
    cues = set(LEXICON["cue_words"])
    named = _named_ingredients(norm, ingredients)
    faces: List[Dict[str, Any]] = []
    kept_sentences: List[str] = []
    for sentence in SENTENCE_SPLIT_RX.split(norm):
        if not sentence.strip():
            continue
        body = sentence.rstrip(".!;").strip()
        if body.endswith("?") or _is_question(body, sentence):
            kept_sentences.append(sentence)
            continue
        clauses = [c.strip() for c in CLAUSE_SPLIT_RX.split(body) if c.strip()]
        keep: List[str] = []
        for clause in clauses:
            hit = None
            for row, rx in rows:
                m = rx.search(clause)
                if m:
                    hit = (row, m)
                    break
            if hit is None and NEGATION_RX.search(clause):
                plain = re.sub(r"\b(?:not|never) |n't\b", "", clause)
                negated = [row["id"] for row, rx in rows if not row["negation_ok"] and rx.search(plain)]
                if negated:
                    return dict(base, status=STATUS_CLARIFY, faces=[], remainder="",
                                clarify={"code": "FACE_NEGATED", "slots": {"clause": clause}}, rows=negated[:1])
            if hit is None:
                words = set(re.findall(r"[a-z]+", clause))
                if words & cues and _mentions(clause, ingredients, products):
                    return dict(base, status=STATUS_CLARIFY, faces=[], remainder="",
                                clarify={"code": "FACE_UNREAD", "slots": {"clause": clause}}, rows=[])
                keep.append(clause)
                continue
            row, m = hit
            if NEGATION_RX.search(clause) and not row["negation_ok"]:
                return dict(base, status=STATUS_CLARIFY, faces=[], remainder="",
                            clarify={"code": "FACE_NEGATED", "slots": {"clause": clause}}, rows=[row["id"]])
            if row["scope"] == "recipe":
                name = EVERYDAY_PRODUCTS[m.group("prod")]
            else:
                ref = m.groupdict().get("obj") or m.groupdict().get("subj")
                word = _ref_word(ref or "")
                if word in PRONOUNS:
                    if len(named) != 1:
                        return dict(base, status=STATUS_CLARIFY, faces=[], remainder="",
                                    clarify={"code": "FACE_WHICH_INGREDIENT", "slots": {"clause": clause,
                                                                                         "named": named}},
                                    rows=[row["id"]])
                    name = named[0]
                else:
                    name = EVERYDAY_INGREDIENTS[word]
            faces.append({"scope": row["scope"], "name": name, "face": row["face"], "stage": row["stage"],
                          "row": row["id"], "source": row["source"], "phrase": m.group(0)})
        if keep:
            kept_sentences.append(" and ".join(keep) + ".")
    if not faces:
        return dict(base, status=STATUS_NONE, faces=[], remainder=text, clarify=None, rows=[])
    remainder = " ".join(kept_sentences).strip()
    return dict(base, status=STATUS_FACES, faces=faces, remainder=remainder, clarify=None,
                rows=[f["row"] for f in faces])


def evidence_digest(text: str) -> str:
    """The evidence a stored face carries: sha256 of the user's exact sentence (UTF-8)."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def say_face(face: Dict[str, Any]) -> str:
    """Everyday English for a face the reader took (no CAS words)."""
    n = face["name"].lower()
    s, f = face["stage"], face["face"]
    if face["scope"] == "recipe":
        return {"ABSENT": f"Noted: there's no reason to make {n} right now.",
                "RISING": f"Noted: {n} is only a maybe for now.",
                "WANING": f"Noted: {n} matters less right now.",
                "PEAK": f"Noted: {n} is wanted."}[s]
    if f == "WISDOM":
        return {"RISING": f"Noted: you're still getting the hang of the {n}.",
                "WANING": f"Noted: you're a bit out of practice with the {n}.",
                "PEAK": f"Noted: you know the {n} well.",
                "ABSENT": f"Noted: you don't know how to use the {n} yet."}[s]
    if f == "POWER":
        return {"RISING": f"Noted: the {n} is only just getting going.",
                "WANING": f"Noted: the {n} has lost some of its strength.",
                "PEAK": f"Noted: the {n} is in good shape.",
                "ABSENT": f"Noted: the {n} won't do its job."}[s]
    return {"ABSENT": f"Noted: the {n} isn't meant for this.",
            "RISING": f"Noted: the {n} might be used for this.",
            "WANING": f"Noted: the {n} is less meant for this now.",
            "PEAK": f"Noted: the {n} is meant for this."}[s]


if __name__ == "__main__":
    ings = list(dict.fromkeys(EVERYDAY_INGREDIENTS.values()))
    prods = list(dict.fromkeys(EVERYDAY_PRODUCTS.values()))
    for t in ("We have 12 cups of flour but I barely know how to use it.", "The yeast is getting old.",
              "There's no reason to bake bread today.", "How much bread can we make?"):
        r = read(t, ings, prods)
        print(json.dumps({"text": t, "status": r["status"], "faces": r["faces"], "remainder": r["remainder"]}))
