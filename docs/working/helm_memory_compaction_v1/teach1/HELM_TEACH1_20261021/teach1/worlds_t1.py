"""The SDG keyed worlds of TEACH-1 (pre-code 4.1), the three quizzes (4.3) and the teaching plan (4.2). Pure, seeded.

A WORLD is one small made-up subject with a key: 24 facts (names, places, counts, months, one-step relations), 4 of them
marked unknown-to-the-person. Two frozen subject templates: HIVE_YEAR (a made-up family's hive yards over a year) and
BUS_LINES (a made-up town's bus lines). Every name is drawn from the frozen pools below, which `check_disjoint` proves
disjoint by exact match from every ingredient, recipe and product name the brain's tables hold, from every cube core name
in the shipped store, and from wave 7's twelve small-talk sentences (contract/DISJOINT_CHECK_TEACH1.json).

The generator is the CAS SDG's job in this packet (DESIGN 3.5): rule-based, seedable, keyed. It writes the canonical
statement and question of every fact; the sealed exam's TEACHING TURNS are written by AI models from these facts
(contract/WRITER_BRIEF_TEACH1.md), never by this file. The practice turns (turns_t1.practice_turns) are rule-written and
are never the exam.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from . import common_t1 as C

# ---- frozen pools: made-up names, letters only, at least four letters (the compactor's clue rule) ----
PERSONS = ("Orrin", "Vexley", "Halden", "Ysolde", "Branwen", "Corvan", "Delmar", "Elowen", "Fenwick", "Garron",
           "Hollis", "Isbeth", "Jorvan", "Kestrel", "Larkin", "Maudry", "Nessa", "Oswin", "Perrin", "Quilla",
           "Rowena", "Sabra", "Tamsin", "Ulric", "Varden", "Wendel", "Yorath", "Zelma", "Ambrin", "Bryony",
           "Caddock", "Dorran")
PLACES = ("Saltwick", "Dunmere", "Fennick", "Pellstone", "Marrow", "Ashcombe", "Brindle", "Carrow", "Dovecote",
          "Elmbrook", "Foxley", "Glenhollow", "Harrowby", "Ivybridge", "Kelsmere", "Lindhurst", "Moorcroft",
          "Nethercote", "Oakridge", "Pennyford", "Quarrybank", "Ravensby", "Stonewick", "Thornfield", "Umberley",
          "Vellmoor", "Wexcombe", "Yarrowdale", "Ashby", "Bramlow", "Cresswell", "Dunholm", "Eastwold", "Fallowmere",
          "Greystoke", "Hazelby", "Longmoor", "Millbrook", "Northgate", "Oxley")
NUMBERS = tuple(C.NUMBER_WORDS)           # two .. nineteen
MONTHS = C.MONTHS                          # no "may"
TEMPLATES = ("HIVE_YEAR", "BUS_LINES")
SLOTS = ("count", "person", "place")

#: wave 7's twelve frozen small-talk sentences (PREREGISTRATION_R1W7 4.3); subject words must not appear in them
WAVE7_NOISE = ("Hello there!", "My grandfather kept bees in the south of France.", "Remember that I prefer short answers.",
               "I'm feeling tired today.", "Tell me a joke.", "What do you know about me so far?", "What did we just do?",
               "I live in Oakland and I like hiking.", "Thanks, that's helpful.", "How are you?",
               "Do you remember what I said about my answers?", "I love this recipe book.")

# ---- the two templates: (kind, statement, question, unknown statement). {Y} the yard / line, {P} person, {X} place,
#      {N} count word, {M} month. Each kind's question covers the statement's clue words and no other fact's.
HIVE_YEAR = {
    "unit": "yard",
    "count": ("The {Y} yard had {N} colonies in {M}.", "What did I say about the colonies at {Y} in {M}?",
              "I don't remember how many colonies the {Y} yard had in {M}."),
    "person": ("{P} looked after the {Y} yard.", "What did I say about who looked after the {Y} yard?",
               "I don't remember who looked after the {Y} yard."),
    "market": ("The honey from the {Y} yard went to the {X} market.", "What did I say about where the honey from the {Y} yard went?",
               "I don't remember where the honey from the {Y} yard went."),
    "move": ("The {Y} yard was moved to {X} in {M}.", "What did I say about where the {Y} yard was moved in {M}?",
             "I don't remember where the {Y} yard was moved in {M}."),
    "origin": ("The queens for the {Y} yard came from {X}.", "What did I say about where the queens for the {Y} yard came from?",
               "I don't remember where the queens for the {Y} yard came from."),
    "fix": "Correction: the {Y} yard had {N} colonies in {M}, not {OLD}.",
}
BUS_LINES = {
    "unit": "line",
    "count": ("The {Y} line ran {N} buses in {M}.", "What did I say about the buses on the {Y} line in {M}?",
              "I don't remember how many buses the {Y} line ran in {M}."),
    "person": ("{P} drove the {Y} line.", "What did I say about who drove the {Y} line?",
               "I don't remember who drove the {Y} line."),
    "market": ("The {Y} line ended at {X}.", "What did I say about where the {Y} line ended?",
               "I don't remember where the {Y} line ended."),
    "move": ("The {Y} line was rerouted through {X} in {M}.", "What did I say about where the {Y} line was rerouted in {M}?",
             "I don't remember where the {Y} line was rerouted in {M}."),
    "origin": ("The depot for the {Y} line was at {X}.", "What did I say about where the depot for the {Y} line was?",
               "I don't remember where the depot for the {Y} line was."),
    "fix": "Correction: the {Y} line ran {N} buses in {M}, not {OLD}.",
}
TEMPLATE_TEXT = {"HIVE_YEAR": HIVE_YEAR, "BUS_LINES": BUS_LINES}
KIND_SLOT = {"count": "count", "person": "person", "market": "place", "move": "place", "origin": "place"}
KINDS_PER_WORLD = (("count", 8), ("person", 4), ("market", 4), ("move", 4), ("origin", 4))   # = 24


_CW = {}


def content_words(text: str) -> List[str]:
    """The cut's own clue rule (helm_now/helm_memory_compact.content_words), loaded by path, standard library only.
    The quiz question's content words are the fact's ANCHOR WORDS: every keyed turn must carry them (D-TEACH1-3)."""
    if "f" not in _CW:
        import importlib.util
        path = C.helm_now_dir() / "helm_memory_compact.py"
        spec = importlib.util.spec_from_file_location("teach1_cut_hmc", str(path))
        import sys
        mod = importlib.util.module_from_spec(spec)
        sys.modules["teach1_cut_hmc"] = mod
        spec.loader.exec_module(mod)   # type: ignore[union-attr]
        _CW["f"] = mod.content_words
    return _CW["f"](text)


def world_rng(seed, index: int) -> random.Random:
    """One stream per world, derived from the band seed (or the practice text) and the world index."""
    return random.Random(f"{seed}:world:{index}")


def _fill(text: str, **kw) -> str:
    for k, v in kw.items():
        text = text.replace("{" + k + "}", v.capitalize() if k == "M" else v)
    return text


def build_world(seed, index: int, template: str) -> Dict[str, Any]:
    """One keyed world. `seed` is the WORLD band seed (int) or a practice text; `index` 0..15."""
    rng = world_rng(seed, index)
    T = TEMPLATE_TEXT[template]
    places = list(PLACES)
    persons = list(PERSONS)
    rng.shuffle(places)
    rng.shuffle(persons)
    units = places[:4]                      # the 4 yards / lines
    others = places[4:20]                   # 16 places for market / move / origin values + never-taught
    keepers = persons[:4]
    never_place, never_person = places[20], persons[4]
    numbers = list(NUMBERS)
    rng.shuffle(numbers)
    months = list(MONTHS)
    rng.shuffle(months)
    facts: List[Dict[str, Any]] = []
    # 8 count facts: every unit twice, in distinct months, distinct numbers
    count_months = months[:8]
    for i in range(8):
        y, m, n = units[i % 4], count_months[i], numbers[i]
        facts.append({"id": f"C{i + 1}", "kind": "count", "slot": "count", "unit": y, "month": m, "value": n,
                      "statement": _fill(T["count"][0], Y=y, N=n, M=m), "question": _fill(T["count"][1], Y=y, M=m),
                      "unknown_statement": _fill(T["count"][2], Y=y, M=m)})
    for i in range(4):
        y, p = units[i], keepers[i]
        facts.append({"id": f"K{i + 1}", "kind": "person", "slot": "person", "unit": y, "value": p,
                      "statement": _fill(T["person"][0], P=p, Y=y), "question": _fill(T["person"][1], Y=y),
                      "unknown_statement": _fill(T["person"][2], Y=y)})
    for i in range(4):
        y, x = units[i], others[i]
        facts.append({"id": f"H{i + 1}", "kind": "market", "slot": "place", "unit": y, "value": x,
                      "statement": _fill(T["market"][0], Y=y, X=x), "question": _fill(T["market"][1], Y=y),
                      "unknown_statement": _fill(T["market"][2], Y=y)})
    move_months = months[8:11] + [months[0]]      # 4 months, the last one shared with a count fact of another unit
    for i in range(4):
        y, x, m = units[i], others[4 + i], move_months[i]
        facts.append({"id": f"V{i + 1}", "kind": "move", "slot": "place", "unit": y, "month": m, "value": x,
                      "statement": _fill(T["move"][0], Y=y, X=x, M=m), "question": _fill(T["move"][1], Y=y, M=m),
                      "unknown_statement": _fill(T["move"][2], Y=y, M=m)})
    for i in range(4):
        y, x = units[i], others[8 + i]
        facts.append({"id": f"O{i + 1}", "kind": "origin", "slot": "place", "unit": y, "value": x,
                      "statement": _fill(T["origin"][0], Y=y, X=x), "question": _fill(T["origin"][1], Y=y),
                      "unknown_statement": _fill(T["origin"][2], Y=y)})
    assert len(facts) == C.FACTS_PER_WORLD
    for f in facts:
        f["anchor_words"] = content_words(f["question"])
    # 4 unknown-to-the-person facts (one per non-count kind would be too regular; drawn at random, at most 2 count facts)
    ids = [f["id"] for f in facts]
    unknown: List[str] = []
    pool = ids[:]
    rng.shuffle(pool)
    for fid in pool:
        if len(unknown) >= C.UNKNOWN_PER_WORLD:
            break
        if fid.startswith("C") and sum(1 for u in unknown if u.startswith("C")) >= 2:
            continue
        unknown.append(fid)
    for f in facts:
        f["unknown"] = f["id"] in unknown
        if f["unknown"]:
            f["taught_value"] = None
    # 2 corrections (FIX): two known COUNT facts whose first statement carries a wrong value, corrected later
    known_counts = [f for f in facts if f["kind"] == "count" and not f["unknown"]]
    fixes = rng.sample(known_counts, C.FLOOR_FIX_TURNS)
    spare = [n for n in numbers if n not in {f["value"] for f in facts if f["kind"] == "count"}]
    for i, f in enumerate(fixes):
        old = spare[i]
        f["fix"] = {"first_value": old, "first_statement": _fill(T["count"][0], Y=f["unit"], N=old, M=f["month"]),
                    "correction": _fill(T["fix"], Y=f["unit"], N=f["value"], M=f["month"], OLD=old)}
    # never-taught questions (2): a place and a person that appear nowhere in this world
    never = [{"id": "N1", "kind": "count", "slot": "count", "value": None, "never_taught": True,
              "question": _fill(T["count"][1], Y=never_place, M=months[3])},
             {"id": "N2", "kind": "person", "slot": "person", "value": None, "never_taught": True,
              "question": _fill(T["person"][1], Y=others[12])}]
    never[1]["note"] = f"{others[12]} is a place never used by any fact of this world; the person {never_person} is never named"
    names = {"units": units, "persons": keepers, "places": others[:12], "never": [never_place, others[12], never_person]}
    values = {"count": sorted({f["value"] for f in facts if f["slot"] == "count"} | {f["fix"]["first_value"] for f in fixes}),
              "person": sorted(keepers), "place": sorted(others[:12]), "month": sorted(set(count_months + move_months))}
    return {"schema": "helm.teach1.world/1", "world_id": f"W{index + 1:02d}", "index": index, "template": template,
            "unit_word": T["unit"], "names": names, "values": values, "facts": facts, "never_taught": never,
            "unknown_ids": sorted(unknown), "fix_ids": sorted(f["id"] for f in fixes)}


def teaching_plan(world: Dict[str, Any], seed) -> List[Dict[str, Any]]:
    """The 32 slots of the teaching turns (4.2): 24 statements (20 known, 4 'I don't remember'), 2 corrections,
    4 small talk, 2 restatements; a correction or restatement always after its fact's first statement."""
    rng = random.Random(f"{seed}:plan:{world['world_id']}")
    slots: List[Dict[str, Any]] = []
    for f in world["facts"]:
        if f["unknown"]:
            slots.append({"kind": "UNKNOWN", "fact_id": f["id"], "text": f["unknown_statement"], "value": None})
        elif f.get("fix"):
            slots.append({"kind": "FACT", "fact_id": f["id"], "text": f["fix"]["first_statement"], "value": f["fix"]["first_value"]})
        else:
            slots.append({"kind": "FACT", "fact_id": f["id"], "text": f["statement"], "value": f["value"]})
    for fid in world["fix_ids"]:
        f = next(x for x in world["facts"] if x["id"] == fid)
        slots.append({"kind": "FIX", "fact_id": fid, "text": f["fix"]["correction"], "value": f["value"],
                      "not_value": f["fix"]["first_value"]})
    restate = rng.sample([f for f in world["facts"] if not f["unknown"] and not f.get("fix")], 2)
    for f in restate:
        slots.append({"kind": "RESTATE", "fact_id": f["id"], "text": f["statement"], "value": f["value"]})
    for i in range(C.FLOOR_SMALL_TURNS):
        slots.append({"kind": "SMALL", "fact_id": None, "text": None, "value": None, "small_index": i})
    assert len(slots) == C.TEACHING_TURNS
    rng.shuffle(slots)
    pos = {s["fact_id"]: i for i, s in enumerate(slots) if s["kind"] in ("FACT", "UNKNOWN")}
    for i, s in enumerate(slots):
        if s["kind"] in ("FIX", "RESTATE") and i < pos[s["fact_id"]]:
            j = pos[s["fact_id"]]
            slots[i], slots[j] = slots[j], slots[i]
            pos[s["fact_id"]] = i
    for i, s in enumerate(slots):
        s["turn_index"] = i + 1
    return slots


def quiz_items(world: Dict[str, Any], seed) -> List[Dict[str, Any]]:
    """The 16 keyed questions (4.3): 12 taught, 2 unknown-to-the-person, 2 never taught. Drawn at the QUIZ seed."""
    rng = random.Random(f"{seed}:quiz:{world['world_id']}")
    known = [f for f in world["facts"] if not f["unknown"]]
    unknown = [f for f in world["facts"] if f["unknown"]]
    items = []
    for f in rng.sample(known, C.QUIZ_TAUGHT):
        items.append({"fact_id": f["id"], "kind": "TAUGHT", "slot": f["slot"], "question": f["question"], "value": f["value"],
                      "not_value": (f.get("fix") or {}).get("first_value")})
    for f in rng.sample(unknown, C.QUIZ_UNKNOWN):
        items.append({"fact_id": f["id"], "kind": "UNKNOWN", "slot": f["slot"], "question": f["question"], "value": None})
    for n in world["never_taught"][:C.QUIZ_NEVER]:
        items.append({"fact_id": n["id"], "kind": "NEVER", "slot": n["slot"], "question": n["question"], "value": None})
    assert len(items) == C.QUIZ_QUESTIONS
    return items


def quiz_orders(world: Dict[str, Any], seed) -> Dict[str, List[int]]:
    """Three fresh orders of the same 16 (indices into quiz_items)."""
    rng = random.Random(f"{seed}:order:{world['world_id']}")
    out = {}
    for q in C.QUIZZES:
        order = list(range(C.QUIZ_QUESTIONS))
        rng.shuffle(order)
        out[q] = order
    return out


def damage_plan(world: Dict[str, Any], items: List[Dict[str, Any]], seed) -> List[Dict[str, Any]]:
    """Which cold copies are damaged between Q-TAUGHT and Q-SQUEEZED (Q10 b): two TAUGHT quiz facts, one copy deleted,
    one corrupted. Drawn from the WORLD stream so every compacting arm plants the same damage."""
    rng = random.Random(f"{seed}:damage:{world['world_id']}")
    taught = [it for it in items if it["kind"] == "TAUGHT" and not it.get("not_value")]
    picked = rng.sample(taught, C.PLANTED_DAMAGE_PER_WORLD)
    return [{"fact_id": picked[0]["fact_id"], "damage": "DELETE"}, {"fact_id": picked[1]["fact_id"], "damage": "CORRUPT"}]


def build_all(seed, count: int = C.WORLDS) -> List[Dict[str, Any]]:
    """`count` worlds, eight of each template, template order drawn from the seed."""
    rng = random.Random(f"{seed}:templates")
    order = [TEMPLATES[i % 2] for i in range(count)]
    rng.shuffle(order)
    return [build_world(seed, i, order[i]) for i in range(count)]


def world_words(world: Dict[str, Any]) -> List[str]:
    """Every subject word this world uses (lower case): units, persons, places, never-taught names."""
    n = world["names"]
    return sorted({w.lower() for w in n["units"] + n["persons"] + n["places"] + n["never"]})


def subject_pool_words() -> List[str]:
    return sorted({w.lower() for w in PERSONS + PLACES})


def check_disjoint(brain_names: List[str], cube_names: List[str]) -> Dict[str, Any]:
    """Exact-match disjointness of the subject pools from the brain's tables, the shipped cube names and wave 7's noise."""
    pool = set(subject_pool_words())
    noise = set()
    for s in WAVE7_NOISE:
        noise.update(C.words_of(s))
    brain = {str(x).lower() for x in brain_names}
    brain_parts = set()
    for x in brain:
        brain_parts.update(C.words_of(x.replace("_", " ")))
    cubes = {str(x).lower() for x in cube_names}
    cube_parts = set()
    for x in cubes:
        cube_parts.update(C.words_of(x))
    template_words = set()
    for T in TEMPLATE_TEXT.values():
        for k, v in T.items():
            if isinstance(v, tuple):
                for s in v:
                    template_words.update(C.words_of(s))
    hits = {"brain": sorted(pool & (brain | brain_parts)), "cubes": sorted(pool & (cubes | cube_parts)),
            "wave7_noise": sorted(pool & noise), "numbers_or_months": sorted(pool & (set(NUMBERS) | set(MONTHS))),
            "template_words_in_brain": sorted(template_words & (brain | brain_parts)),
            "short_or_nonletter": sorted(w for w in pool if len(w) < 4 or not w.isalpha())}
    return {"schema": "helm.teach1.disjoint/1", "pool_size": len(pool), "brain_names": len(brain), "cube_names": len(cubes),
            "hits": hits, "ok": not any(hits.values())}
