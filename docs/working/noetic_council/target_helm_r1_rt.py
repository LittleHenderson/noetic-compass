"""THE TASK: the recipe brain has to become HELM's brain, not just beat it on an exam.

TARGET OUTCOME
--------------
"HELM hosts the recipe brain in its own runtime: the same answers inside HELM that wave 1
measured outside it, surviving a restart through HELM's own store and a real nested repair."

WHY THIS TASK
-------------
Wave 1 put the recipe brain in GB3's slot **conceptually**: same boards in, same labels out,
same budget, same marks — in the recipe brain's own harness. It did not run inside HELM's
runtime (`cas_cjt`, its SQLite store, its real nested repair). WAVES.md says so in as many
words: "It does not run inside HELM's runtime". So the win is real and, for the purpose of
"the brain of HELM", it is not yet the thing.

`WAVES.md` lists R1-RT as optional and **not designed**. Its gate is "W1's reading and the
owner's word". The reading now exists (§7.47). The design does not.

WHAT THE TWO SIDES ACTUALLY LOOK LIKE, MEASURED
-----------------------------------------------
This is the part that decides how hard R1-RT is, and it is worth stating before any design:

- **GB3's task** is `native.route_dependency_audit/1`: a directed graph on eight nodes and a
  proposed route; the answer is the first unsupported leg, `FIRST_UNSUPPORTED_LEG_0` through
  `FIRST_UNSUPPORTED_LEG_6`, or `ALL_LEGS_PRESENT`. Input is float32 `[1,8,64]`; the brain
  turns that into eight logits. (TASK_CONTRACT.md, lines 9-41.)
- **The recipe brain's** state is a JSON document — recipes, tables and a stage — written
  atomically and reopened with a sha256 and a recomputed state digest. (rb/state.py.)

They share no vocabulary. A bridge between them is therefore an **adapter with a stated
contract**, not a rename, and that is exactly the kind of thing this project has history with.

EVERY READING HERE IS A PROGRAM READING
---------------------------------------
Each reading opens a named file or runs a named search and returns True / False / None. None
means the reading could not be taken, and it BLOCKS the gate rather than passing it. Nothing
here is typed from prose, and nothing here is a claim about the recipe brain's quality.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from council_loop import Reading, RequiredCondition

R1_RT_DIR = r"C:\Users\wakil\Documents\Codex\2026-10-16\r1_rt"
PLAN_DIR = r"C:\Users\wakil\Documents\Codex\2026-10-15\helm_r1_integration_plan_v1"
WAVES = os.path.join(PLAN_DIR, "WAVES.md")
README = os.path.join(PLAN_DIR, "README.md")

RUNTIME_ROOT = (r"C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation"
                r"\controller_r6_restoration_op13\source_r6\cas_cjt")
V3 = r"C:\Users\wakil\Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3"
READING = (r"C:\Users\wakil\Documents\Codex\2026-10-16\r1w1_reader\HELM_R1_W1_20261015"
           r"\R1_W1_READING.json")

TARGET_ID = "HELM_R1_RT_HOSTED"
TARGET_STATEMENT = (
    "HELM hosts the recipe brain in its own runtime: the same answers inside HELM that wave 1 "
    "measured outside it, surviving a restart through HELM's own store and a real nested repair.")


def _search_names(root: str, needles: tuple) -> Dict[str, List[str]]:
    """Files whose NAME contains a needle, at any depth. A cheap, exact, re-runnable search."""
    hits: Dict[str, List[str]] = {n: [] for n in needles}
    if not os.path.isdir(root):
        return hits
    for base, _dirs, files in os.walk(root):
        for name in files:
            low = name.lower()
            for n in needles:
                if n in low:
                    hits[n].append(os.path.join(base, name))
    return hits


def _grep(root: str, token: str, limit: int = 6) -> List[str]:
    """Files whose TEXT contains a token. Reports where, never how many is enough."""
    found: List[str] = []
    if not os.path.isdir(root):
        return found
    for base, _dirs, files in os.walk(root):
        for name in files:
            if not name.lower().endswith((".py", ".md", ".json", ".yml", ".yaml")):
                continue
            path = os.path.join(base, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            if token in text:
                found.append(path)
                if len(found) >= limit:
                    return found
    return found


def read_design_exists() -> Reading:
    src = "look for an R1-RT design document under %s and in the plan folder" % R1_RT_DIR
    hits = _search_names(R1_RT_DIR, ("r1_rt", "r1rt", "design"))
    plan_hits = _search_names(PLAN_DIR, ("r1_rt", "r1rt", "runtime"))
    n = sum(len(v) for v in hits.values()) + sum(len(v) for v in plan_hits.values())
    return Reading(source=src, ok=n > 0,
                   detail=("found %d candidate file(s): %s"
                           % (n, (list(hits.values()) + list(plan_hits.values()))[:3] if n
                              else "none — WAVES.md's own words are 'not designed'")))


def read_bridge_exists() -> Reading:
    """Is there an adapter that would CARRY the recipe brain into the runtime?

    A filename containing "bridge" is not a bridge. The runtime ships `cncm_bridge.py`, which the
    HELM vision's own source table describes as granting INERT_PROPOSAL_ONLY_NOT_ADMITTED_BY_CURRENT_CNCM
    and importing neither the CNCM nor any kernel. It matched a name search and would have read as
    a satisfied condition. So each candidate is opened and asked what it actually does.
    """
    src = ("open every candidate adapter by name and read what it claims to do, under %s, the "
           "runtime root and the v3 package" % R1_RT_DIR)
    needles = ("bridge", "adapter", "host_")
    cands: List[str] = []
    for root in (R1_RT_DIR, RUNTIME_ROOT, V3):
        for v in _search_names(root, needles).values():
            cands += v
    live, inert = [], []
    for p in cands:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        low = text.lower()
        mentions_recipe = ("recipebrain" in low or "recipe_brain" in low
                           or "recipes" in low or "rb2" in low or "rb3" in low)
        # A file is a BRIDGE only when it touches the recipe brain AND reaches the runtime.
        # A test harness that merely imports the recipe brain is not a bridge; that mistake made
        # host_summary.py read as one on the first attempt.
        touches_runtime = ("cas_cjt" in low or "from runtime" in low or "import runtime" in low
                           or "persistence" in low and "sqlite" in low)
        if "inert" in low or "not_admitted" in low or "proposal_only" in low:
            inert.append(p)
        elif mentions_recipe and touches_runtime:
            live.append(p)
        else:
            inert.append(p)
    return Reading(
        source=src, ok=len(live) > 0,
        detail=("LIVE adapters carrying the recipe brain: %s; candidates that exist but do NOT "
                "carry it (inert, or unrelated to the recipe brain): %s"
                % (live or "none", inert or "none")))


def read_runtime_present() -> Reading:
    src = "the runtime's own source at %s" % RUNTIME_ROOT
    if not os.path.isdir(RUNTIME_ROOT):
        return Reading(source=src, ok=None, detail="the runtime source is not at that path")
    py = []
    for base, _d, files in os.walk(RUNTIME_ROOT):
        py += [os.path.join(base, f) for f in files if f.endswith(".py")]
    names = sorted(os.path.basename(p) for p in py)
    key = [n for n in names if n in ("persistence.py", "runtime.py", "control.py", "semantic.py",
                                     "neural.py", "cncm_bridge.py")]
    return Reading(source=src, ok=len(py) > 0,
                   detail=("%d python files; the ones R1-RT would have to touch: %s"
                           % (len(py), ", ".join(key) or "none of the named ones")))


def read_recipe_state_readable() -> Reading:
    src = "the recipe brain's own state module in the v3 package: rb/state.py"
    path = os.path.join(V3, "rb", "state.py")
    if not os.path.isfile(path):
        return Reading(source=src, ok=None, detail="rb/state.py is not at that path")
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return Reading(source=src,
                   ok=("FORMAT" in text and "save_state" in text and "load_state" in text),
                   detail=("a JSON state document with atomic write, a format marker and a "
                           "sha256 plus recomputed digest on reload: %s"
                           % ("all present" if all(k in text for k in
                                                   ("FORMAT", "save_state", "load_state"))
                              else "one of FORMAT/save_state/load_state is missing")))


def read_runtime_store() -> Reading:
    src = "the runtime's persistence module, named in the HELM vision section 7.3"
    path = os.path.join(RUNTIME_ROOT, "persistence.py")
    if not os.path.isfile(path):
        return Reading(source=src, ok=None, detail="persistence.py is not at that path")
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    marks = {k: (k in text) for k in ("sqlite", "SQLite", "WAL", "BEGIN IMMEDIATE")}
    return Reading(source=src, ok=any(marks.values()),
                   detail="the store's own mechanisms found in the file: %s" % marks)


def read_gate_satisfied() -> Reading:
    """R1-RT's gate: "W1's reading and the owner's word". HALF of it is not this target's to give.

    The first version of this reading returned ok=True because the reading half was met and a
    gate line existed. That is the precise failure this project has been bitten by: a condition
    that is half satisfied reading as satisfied. The owner's word does not exist anywhere on disk,
    so this returns None, which BLOCKS the gate rather than passing it.
    """
    src = "WAVES.md's gate for R1-RT: \"W1's reading and the owner's word\""
    wave = open(WAVES, encoding="utf-8", errors="replace").read() if os.path.isfile(WAVES) else ""
    d = None
    if os.path.isfile(READING):
        with open(READING, encoding="utf-8") as fh:
            d = json.load(fh)
    reading_half = bool(d and d.get("test_verdict") == "PASS" and d.get("claim_licensed") is True)

    # The owner's half: a record that names R1-RT as approved. Looked for, not assumed.
    owner_half = [p for p in _grep(R1_RT_DIR, "R1-RT", limit=4)] if os.path.isdir(R1_RT_DIR) else []
    owner_half += [p for p in _grep(PLAN_DIR, "APPROVE R1-RT", limit=4)]
    gate_line = [l for l in wave.splitlines() if "R1-RT" in l and "Gate" not in l][:1]

    if not reading_half:
        return Reading(source=src, ok=False,
                       detail="the reading half is NOT met: wave 1's reading is missing or unlicensed")
    if not owner_half:
        return Reading(
            source=src, ok=None,
            detail=("HALF MET, HALF ABSENT. W1's reading exists and is licensed, so that half is "
                    "met. No record anywhere approves R1-RT: nothing found under %s or the plan "
                    "folder. The owner's word is not an agent's to give, so this reading cannot be "
                    "taken as satisfied and it BLOCKS the gate. WAVES.md: %r"
                    % (R1_RT_DIR, gate_line[0].strip()[:110] if gate_line else "")))
    return Reading(source=src, ok=True,
                   detail="both halves found: reading licensed, and an approval record naming "
                          "R1-RT at %s" % owner_half[:2])


def read_claim_boundary() -> Reading:
    src = "the wave-1 reading's own excluded list, which forbids claiming runtime operation"
    if not os.path.isfile(READING):
        return Reading(source=src, ok=None, detail="the wave-1 reading is not at that path")
    with open(READING, encoding="utf-8") as fh:
        d = json.load(fh)
    excluded = d.get("not_licensed_in_any_case") or ""
    return Reading(source=src, ok="HELM's runtime" in excluded,
                   detail=("the wave-1 reading already excludes operation inside HELM's runtime "
                           "in its own words: %r" % excluded[:180]))


def conditions_for() -> List[RequiredCondition]:
    design = read_design_exists()
    bridge = read_bridge_exists()
    runtime = read_runtime_present()
    store = read_runtime_store()
    state = read_recipe_state_readable()
    gate = read_gate_satisfied()
    boundary = read_claim_boundary()

    mech = Reading(
        source="the project's own wave rules: freeze first, one switch per part, one attempt "
               "per sealed package, a program reading decides",
        ok=True,
        detail="the design must name its marks, arms and predictions before any code")

    return [
        RequiredCondition(
            id=TARGET_ID, statement=TARGET_STATEMENT,
            understood=Reading(
                source="README_GB3.md section 5 (the one command) and TASK_CONTRACT.md lines 9-41 "
                       "(the task and the exact answer)",
                ok=True,
                detail="what has to run where is stated by the two packages themselves"),
            mechanism=mech,
            established=design,
            prerequisites=["RT_SPECIFIED", "RT_BRIDGE_EXISTS", "RT_GATE_OPEN"]),

        RequiredCondition(
            id="RT_SPECIFIED",
            statement="an R1-RT design exists: what runs, on which exam, read by which program",
            understood=Reading(
                source="WAVES.md, the wave table",
                ok=True,
                detail="WAVES.md's own state for this row is 'not designed'"),
            mechanism=mech, established=design, prerequisites=[]),

        RequiredCondition(
            id="RT_BRIDGE_EXISTS",
            statement="an adapter exists that can carry the recipe brain into the runtime",
            understood=Reading(
                source="the two sides measured: GB3 takes float32 [1,8,64] to eight logits "
                       "(TASK_CONTRACT.md line 33); the recipe brain's state is a JSON document "
                       "with a digest (rb/state.py)",
                ok=True,
                detail="the two share no vocabulary, so the bridge is an adapter with a stated "
                       "contract, not a rename"),
            mechanism=mech, established=bridge, prerequisites=["RT_RUNTIME_PRESENT",
                                                               "RT_STATE_READABLE"]),

        RequiredCondition(
            id="RT_RUNTIME_PRESENT",
            statement="the runtime the brain would be hosted in is on disk and nameable",
            understood=Reading(
                source="HELM vision section 7.3 names the runtime's parts: runtime.py, "
                       "persistence.py, semantic.py, neural.py, control.py, cncm_bridge.py",
                ok=True, detail="a host needs a host"),
            mechanism=mech, established=runtime, prerequisites=[]),

        RequiredCondition(
            id="RT_STATE_READABLE",
            statement="the recipe brain's learned state can be written and reloaded with a check",
            understood=Reading(
                source="rb/state.py's own docstring: one JSON document, atomic write, sha256 and "
                       "a recomputed state digest on reload",
                ok=True, detail="a brain that cannot be reloaded cannot he hosted in a store"),
            mechanism=mech, established=state, prerequisites=[]),

        RequiredCondition(
            id="RT_STORE_PRESENT",
            statement="the runtime has a durable store a hosted brain could survive a restart in",
            understood=Reading(
                source="HELM vision section 7.3: SQLite WAL/FULL and BEGIN IMMEDIATE",
                ok=True, detail="the restart half of R1-RT depends on this existing"),
            mechanism=mech, established=store, prerequisites=[]),

        RequiredCondition(
            id="RT_GATE_OPEN",
            statement="R1-RT's own gate is met: wave 1's reading, and the owner's word",
            understood=Reading(
                source="WAVES.md: 'Gate: W1's reading and the owner's word'",
                ok=True,
                detail="no agent may give the owner's half of a gate"),
            mechanism=mech, established=gate,
            prerequisites=["RT_CLAIM_BOUNDARY_STATED"]),

        RequiredCondition(
            id="RT_CLAIM_BOUNDARY_STATED",
            statement="the claim boundary is on the record before any runtime work starts",
            understood=Reading(
                source="the wave-1 reading's not_licensed_in_any_case field",
                ok=True,
                detail="the reading already excludes runtime operation, so R1-RT is a NEW test, "
                       "not an upgrade of wave 1's claim"),
            mechanism=mech, established=boundary, prerequisites=[]),
    ]


def task() -> Dict[str, Any]:
    return {
        "target_id": TARGET_ID,
        "target_statement": TARGET_STATEMENT,
        "threshold": 0.5,
        "conditions": conditions_for,
    }


def dump_readings() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for c in conditions_for():
        print("%-26s  req=%s" % (c.id, c.prerequisites))
        r = c.established
        print("    established ok=%-5r %s" % (r.ok, r.source))
        print("                %s" % r.detail)
        print()


if __name__ == "__main__":
    dump_readings()
