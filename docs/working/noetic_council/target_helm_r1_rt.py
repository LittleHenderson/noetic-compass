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
REPO = r"C:\Users\wakil\OneDrive\Desktop\tksCAS"
THREAD_BRANCH = "origin/claude/project-thread-pmbzd6"
DESIGN_DIR = "docs/working/noetic_council"
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


def git_show_prefix(prefix: str) -> Optional[str]:
    """The names under a directory on the live branch, or None if git cannot be reached.

    Reads the RECORD, not a disk path. A design that is committed is on the branch whether or not
    any particular worktree still exists on this machine.
    """
    import subprocess
    if not os.path.isdir(REPO):
        return None
    p = subprocess.run(["git", "show", "%s:%s" % (THREAD_BRANCH, prefix.rstrip("/"))],
                       cwd=REPO, capture_output=True, timeout=180)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", errors="replace")


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
    """An R1-RT design exists: the three names, the acceptance test, the shape recommendation.

    READ FROM THE LIVE BRANCH, not from a disk path. The first version of this reading listed a
    hard-coded worktree directory. Measured by running the council from a fresh folder: the design
    is COMMITTED to `origin/claude/project-thread-pmbzd6`, and the worktree was only where it was
    written. If that worktree is ever removed, the disk version would report "no design" while the
    design sits on the branch — a reading that is wrong about the thing it names, which is the exact
    failure section 12 of the directive forbids.

    So: the branch is the source of truth when git can be reached; the disk is the fallback for
    offline work; and the detail says which was used.

    Part two (arms, machine, window) and appendices A and B (the frozen conversion rules) are part
    of the design. This stays False until the whole design exists, because a half-written design is
    what "not designed" meant.
    """
    src = ("git show %s:%s (the live record), falling back to disk paths"
           % (THREAD_BRANCH, DESIGN_DIR))
    branch_names: List[str] = []
    branch_state = "git could not be read"
    out = git_show_prefix("docs/working/noetic_council/")
    if out is not None:
        branch_names = [os.path.basename(p) for p in out.splitlines() if p.strip()]
        branch_state = "%d file(s) on the branch" % len(branch_names)

    disk_names: List[str] = []
    for d in (R1_RT_DIR, os.path.join(
            r"D:\tksCAS-worktrees\docs-r1w1-wave1-20261016\docs\working\noetic_council")):
        if os.path.isdir(d):
            disk_names += [f for f in os.listdir(d) if f.lower().endswith((".md", ".py"))]

    names = branch_names or disk_names
    source_used = "the live branch" if branch_names else (
        "disk only (%s)" % branch_state)
    low = [n.lower() for n in names]
    has_part1 = any("design_part1" in n for n in low)
    has_part2 = any("design_part2" in n for n in low)
    has_env = any("part3_envelope" in n for n in low)
    has_rules = any("appendix_a" in n for n in low) and any("appendix_b" in n for n in low)
    complete = has_part1 and has_part2 and has_env and has_rules
    return Reading(
        source=src, ok=complete,
        detail=("read from %s (%s). design part one: %s; part two: %s; the envelope: %s; the "
                "frozen conversion rules (appendix A and B): %s"
                % (source_used, branch_state,
                   "present" if has_part1 else "absent",
                   "present" if has_part2 else "absent",
                   "present" if has_env else "absent",
                   "present" if has_rules else "absent")))


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

    # The owner's half: an APPROVAL, not a mention. The first version of this searched the plan
    # folder for the string "R1-RT" and got four hits — all of them documents that merely discuss
    # R1-RT. Seat CO-0 measured that WAVES.md itself contains "R1-RT" and sits in the same folder,
    # so a different filesystem walk order would have flipped this reading to True without a single
    # byte changing. That is a false positive of exactly the kind this project keeps getting bitten
    # by. Approval is now required to be an ADMISSION phrase, and a mere mention is reported as a
    # mention so the reason is visible.
    admission = ("approve r1-rt", "approved r1-rt", "approved, design it", "r1-rt approved",
                 "authorise r1-rt", "authorize r1-rt", "go ahead on r1-rt")
    mentions = _grep(R1_RT_DIR, "R1-RT", limit=6) if os.path.isdir(R1_RT_DIR) else []
    mentions += [p for p in _grep(PLAN_DIR, "R1-RT", limit=8)]
    owner_half = []
    for p in mentions:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                low = fh.read().lower()
        except OSError:
            continue
        if any(a in low for a in admission):
            owner_half.append(p)
    gate_line = [l for l in wave.splitlines() if "R1-RT" in l and "Gate" not in l][:1]

    if not reading_half:
        return Reading(source=src, ok=False,
                       detail="the reading half is NOT met: wave 1's reading is missing or unlicensed")
    if not owner_half:
        return Reading(
            source=src, ok=None,
            detail=("HALF MET, HALF ABSENT. W1's reading exists and is licensed, so that half is "
                    "met. %d document(s) MENTION R1-RT and NONE of them is an approval: %s. A "
                    "mention is not a gate. The owner's word is not an agent's to give, so this "
                    "reading cannot be taken as satisfied and it BLOCKS the gate."
                    % (len(mentions),
                       ", ".join(os.path.basename(p) for p in mentions[:4]))))
    return Reading(source=src, ok=True,
                   detail="both halves found: reading licensed, and an approval record naming "
                          "R1-RT as admitted at %s" % owner_half[:2])


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
                source="WAVES.md's wave table, and the two packages' own task definitions",
                ok=True,
                detail=("WAVES.md's own state for this row is 'not designed'. And the target "
                        "sentence is ambiguous in a way that matters: GB3's task is 16 synthetic "
                        "two-board worlds with labels L0-L3, while the runtime's only task is "
                        "native.route_dependency_audit/1 with eight labels, pinned by content at "
                        "teaching.py:31 and by location at :52-53. 'The same answers' as written "
                        "would compare answers to two different tasks. A design must first name "
                        "which brain, which task and which repair mechanism, with hashes.")),
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
