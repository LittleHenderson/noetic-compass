"""CAS-RPU → Codex CNCM interchange: a lesson told to the organism, carried in the
envelope, used by the independent CNCM kernel.

HELM ability 7 (built together), roadmap step 6; interchange draft
`docs/working/helm_interchange_and_fixtures_draft_2026_10_06.md` §3 (envelope
`helm.interchange/0.1`) and §2 (fixtures F01–F13). The CNCM kernel is the
frozen Codex reference implementation at `eb99855`, mounted read-only (the same
checkout the RPA adapter pins); it is imported, never copied, and its modules
are pinned by content (`CNCM_MODULES_SHA256`). Nothing here writes into that
checkout, and nothing in `scripts/cas_rpu` imports this module (the sever law).

What crosses the boundary, and how:

    CAS-RPU accepted event        envelope event_type   CNCM packet element
    FACT  s -[leads_to]-> o       FACT, polarity true   fact leads_to(s,o) asserted
    NEGATION s -[leads_to]-> o    FACT, polarity false  fact leads_to(s,o) polarity false
    FACT  s -[r]-> o  (foreign)   FACT, relation r      fact r(s,o) asserted
    FACT  r entails leads_to      LESSON                rule INFER_MODUS_PONENS r(?x,?y) -> leads_to(?x,?y)
    RETRACT (accepted)            RETRACT               the given is dropped from the packet state
    HYPOTHESIS                    PROPOSED (not sent)   never a fact (F10: a guess is not evidence)
    FACT  s -[co_occurs]-> o      REJECTED E-IX-RELATION (CNCM has no association; F13)
    transitivity of leads_to      (built into CAS-RPU)  rule INFER_TRANSITIVE, always added

The packet is stateless: for each question the current accepted state is
re-sent, which makes CNCM a second, independently written recompute solver
over the same history. Its verdicts are mapped back by two runs per question
(the positive query, then the negative one):

    CONCLUDED on P                              -> YES
    CONFLICT_UNRESOLVED on P                    -> INADMISSIBLE
    otherwise, CONCLUDED on not-P               -> NO
    otherwise                                   -> UNKNOWN

Known divergence, measured and reported, never mapped away (fixture F06): CNCM
refuses every question while ANY contradiction exists in the packet, whereas
the Revision Streams oracle refuses only when a disputed link lies on a route.
The adapter marks each answer with `conflict_elsewhere` so the comparison can
count that case separately. CNCM has no closed world and names no lacunae, so
only open-world verdicts are compared.
"""

from __future__ import annotations

import hashlib
import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = (
    REPO / ".claude" / "worktrees" / "rpa-readonly" / "cas_only_reasoner"
    / "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
CNCM_COMMIT = "eb9985566bd11a89f485d627186ef0efa7177f02"
CNCM_MODULES = ("__init__.py", "api.py", "engine.py", "kernel.py", "model.py", "semantics.py", "verification.py", "canonical.py")
#: SHA-256 over "name:sha256(file)\n" for each module above, as committed at CNCM_COMMIT.
CNCM_MODULES_SHA256 = "84fadf88cd201d12032b8571a786da638124f756b865fca0a428619ab6cdb95d"
ENVELOPE_SCHEMA = "helm.interchange/0.1"
SOURCE_ENGINE = "cas_rpu"
TARGET_ENGINE = "cncm"
DEFAULT_RELATION = "leads_to"
ASSOCIATIVE_RELATION = "co_occurs"
LESSON_RELATION = "entails"
BUDGETS = {"max_ticks": 512, "max_branches": 8, "max_rpm_depth": 4, "max_inference_steps": 256, "max_memory_queries": 1, "max_repeat_states": 3}


class CncmUnavailable(RuntimeError):
    pass


class InterchangeError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def cncm_root() -> Path:
    return Path(os.environ.get("CAS_CNCM_ROOT", os.environ.get("CAS_RPA_ROOT", str(DEFAULT_ROOT))))


def loaded_version(root: Path | None = None) -> dict:
    root = root or cncm_root()
    h = hashlib.sha256()
    files = {}
    for name in CNCM_MODULES:
        path = root / "cncm" / name
        d = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        files[name] = d
        h.update(f"{name}:{d}\n".encode())
    combined = h.hexdigest()
    return {"root": str(root), "pinned_commit": CNCM_COMMIT, "files": files, "combined": combined, "matches_pin": combined == CNCM_MODULES_SHA256}


def load_cncm():
    """Import the pinned CNCM kernel, or raise CncmUnavailable."""
    root = cncm_root()
    if not (root / "cncm" / "api.py").exists():
        raise CncmUnavailable(f"CNCM checkout not mounted at {root} (commit {CNCM_COMMIT[:9]}); set CAS_CNCM_ROOT")
    v = loaded_version(root)
    if not v["matches_pin"]:
        raise CncmUnavailable(f"the CNCM modules at {root} are not those committed at {CNCM_COMMIT[:9]} ({v['combined'][:16]}…)")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return importlib.import_module("cncm")


def available() -> bool:
    try:
        load_cncm()
        return True
    except CncmUnavailable:
        return False


# ---------------------------------------------------------------------------
# the envelope (export)
# ---------------------------------------------------------------------------

def _ident(token: str) -> str:
    """CNCM identifiers are [A-Za-z_][A-Za-z0-9_]*; CAS-RPU tokens are AA..ZZ and rel_a..; both pass. Anything else is refused."""
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
        raise InterchangeError("E-IX-IDENT", f"{token!r} is not an identifier both engines accept")
    return token


def export_rows(rows, stream_id: str) -> tuple[list[dict], list[dict]]:
    """History rows (`history.Stream.rows`) -> (envelopes, rejected).

    Only ACCEPTED rows are exported; a refused event changed nothing and has
    nothing to carry. Every envelope carries explicit polarity and the source
    event id; nothing is defaulted. Associations and guesses are listed under
    `rejected` with their E-IX code rather than coerced (F13, F10).
    """
    out: list[dict] = []
    rejected: list[dict] = []
    seq = 0
    for row in rows:
        if row["commit_status"] != "ACCEPTED":
            continue
        p = row["payload"]
        kind, s, rel, o = p["kind"], p["subject"], p["relation"], p["obj"]
        base = {
            "schema_version": ENVELOPE_SCHEMA, "event_id": row["event_id"],
            "source": {"engine": SOURCE_ENGINE, "engine_version": row.get("engine_version", ""), "schema_version": "revision_streams_contract_2026_10_06", "stream_id": stream_id},
            "target": {"engine": TARGET_ENGINE, "schema_version": "cncm.problem/0.1"},
            "identity": {"context_id": stream_id, "world_mode": "open"},
            "sequence": seq,
        }
        if kind == "ask":
            continue                                  # questions are asked, not exported
        if kind == "hypothesis":
            rejected.append({"event_id": row["event_id"], "code": "E-IX-PROPOSED", "reason": "a guess is not evidence; never exported as a fact (F10)"})
            continue
        if rel == ASSOCIATIVE_RELATION:
            rejected.append({"event_id": row["event_id"], "code": "E-IX-RELATION", "reason": "CNCM has no associative relation (F13)"})
            continue
        if rel == LESSON_RELATION:
            if kind not in ("fact", "retract"):
                rejected.append({"event_id": row["event_id"], "code": "E-IX-RULE-UNSUPPORTED", "reason": f"{kind} of a lesson has no semantics"})
                continue
            out.append({**base, "event_type": "LESSON" if kind == "fact" else "RETRACT_LESSON",
                        "rule": {"rule_id": f"lesson_{_ident(s)}", "operation": "INFER_MODUS_PONENS",
                                 "antecedents": [{"predicate": _ident(s), "arguments": ["?x", "?y"], "polarity": True}],
                                 "consequent": {"predicate": DEFAULT_RELATION, "arguments": ["?x", "?y"], "polarity": True}},
                        "status": "accepted"})
            seq += 1
            continue
        prop = {"predicate": _ident(rel), "arguments": [_ident(s), _ident(o)], "polarity": kind != "negation", "relation": rel}
        if kind in ("fact", "negation"):
            out.append({**base, "event_type": "FACT", "proposition": prop, "status": "accepted"})
        elif kind == "retract":
            out.append({**base, "event_type": "RETRACT", "proposition": prop, "status": "accepted"})
        else:
            rejected.append({"event_id": row["event_id"], "code": "E-IX-KIND", "reason": f"unknown kind {kind}"})
            continue
        seq += 1
    return out, rejected


# ---------------------------------------------------------------------------
# the state a packet is built from (import side)
# ---------------------------------------------------------------------------

@dataclass
class CncmState:
    """What the receiver holds after folding envelopes in order. Stateless per question."""

    positive: dict[tuple[str, str, str], str] = field(default_factory=dict)   # (rel, s, o) -> source event id
    negative: dict[tuple[str, str], str] = field(default_factory=dict)        # (s, o) -> source event id (leads_to denials)
    lessons: dict[str, str] = field(default_factory=dict)                     # relation -> source event id
    applied: int = 0
    refused: list[dict] = field(default_factory=list)

    def fold(self, env: dict) -> None:
        if env.get("schema_version") != ENVELOPE_SCHEMA:
            raise InterchangeError("E-IX-SCHEMA", f"not a {ENVELOPE_SCHEMA} envelope")
        t = env["event_type"]
        if t == "LESSON":
            self.lessons[env["rule"]["antecedents"][0]["predicate"]] = env["event_id"]
        elif t == "RETRACT_LESSON":
            self.lessons.pop(env["rule"]["antecedents"][0]["predicate"], None)
        elif t == "FACT":
            p = env["proposition"]
            if "polarity" not in p:
                raise InterchangeError("E-IX-POLARITY", "polarity is required; nothing is defaulted")
            s, o = p["arguments"]
            if p["polarity"]:
                self.positive[(p["predicate"], s, o)] = env["event_id"]
            else:
                if p["predicate"] != DEFAULT_RELATION:
                    raise InterchangeError("E-IX-RELATION", "a denial is defined for leads_to only")
                self.negative[(s, o)] = env["event_id"]
        elif t == "RETRACT":
            p = env["proposition"]
            if not p["polarity"]:
                raise InterchangeError("E-IX-NEG-RETRACT", "the grammar has no negative retract (F13)")
            s, o = p["arguments"]
            self.positive.pop((p["predicate"], s, o), None)
        else:
            raise InterchangeError("E-IX-KIND", f"unknown event_type {t}")
        self.applied += 1

    def conflicts(self) -> set[tuple[str, str]]:
        """Pairs given with both polarities under leads_to, or entailed and denied (contract §13 views)."""
        held = {(s, o) for (rel, s, o) in self.positive if rel == DEFAULT_RELATION or rel in self.lessons}
        return held & set(self.negative)

    def component(self, query: tuple[str, str]) -> set[str]:
        """Every token reachable from either end of the query over any held edge,
        ignoring direction and polarity. A fact outside this set cannot lie on any
        route in either engine; sending it would only expose CNCM's global
        conflict rule and spend its budget (see the module docstring)."""
        adj: dict[str, set[str]] = {}
        for (_, s, o) in self.positive:
            adj.setdefault(s, set()).add(o); adj.setdefault(o, set()).add(s)
        for (s, o) in self.negative:
            adj.setdefault(s, set()).add(o); adj.setdefault(o, set()).add(s)
        seen = set(query)
        stack = list(query)
        while stack:
            n = stack.pop()
            for m in adj.get(n, ()):
                if m not in seen:
                    seen.add(m); stack.append(m)
        return seen

    def packet(self, cncm, query: tuple[str, str], polarity: bool, problem_id: str, *, scope: str = "component"):
        if scope == "component":
            keep = self.component(query)
            positive = {k: v for k, v in self.positive.items() if k[1] in keep and k[2] in keep}
            negative = {k: v for k, v in self.negative.items() if k[0] in keep and k[1] in keep}
        elif scope == "whole":
            positive, negative = dict(self.positive), dict(self.negative)
        else:
            raise InterchangeError("E-IX-SCOPE", f"unknown scope {scope!r}")
        entities = sorted({x for (_, s, o) in positive for x in (s, o)} | {x for (s, o) in negative for x in (s, o)} | set(query))
        predicates = sorted({rel for (rel, _, _) in positive} | set(self.lessons) | {DEFAULT_RELATION})
        facts = [
            {"predicate": rel, "arguments": [s, o], "polarity": True, "evidence_status": "asserted",
             "provenance": [{"source_type": SOURCE_ENGINE, "source_id": eid}]}
            for (rel, s, o), eid in sorted(positive.items())
        ] + [
            {"predicate": DEFAULT_RELATION, "arguments": [s, o], "polarity": False, "evidence_status": "asserted",
             "provenance": [{"source_type": SOURCE_ENGINE, "source_id": eid}]}
            for (s, o), eid in sorted(negative.items())
        ]
        rules = [{
            "rule_id": "leads_to_transitive", "operation": "INFER_TRANSITIVE",
            "antecedents": [{"predicate": DEFAULT_RELATION, "arguments": ["?x", "?y"], "polarity": True},
                            {"predicate": DEFAULT_RELATION, "arguments": ["?y", "?z"], "polarity": True}],
            "consequent": {"predicate": DEFAULT_RELATION, "arguments": ["?x", "?z"], "polarity": True},
            "provenance": [{"source_type": SOURCE_ENGINE, "source_id": "transitivity-of-leads_to"}],
        }] + [{
            "rule_id": f"lesson_{rel}", "operation": "INFER_MODUS_PONENS",
            "antecedents": [{"predicate": rel, "arguments": ["?x", "?y"], "polarity": True}],
            "consequent": {"predicate": DEFAULT_RELATION, "arguments": ["?x", "?y"], "polarity": True},
            "provenance": [{"source_type": SOURCE_ENGINE, "source_id": eid}],
        } for rel, eid in sorted(self.lessons.items())]
        return cncm.ProblemPacket.from_dict({
            "schema_version": "cncm.problem/0.1", "problem_id": problem_id, "goal_id": "answer", "seed": 0,
            "entities": [{"entity_id": e, "entity_type": "node"} for e in entities],
            "predicates": [{"predicate_id": p, "argument_types": ["node", "node"], "transitive": p == DEFAULT_RELATION} for p in predicates],
            "facts": facts, "rules": rules,
            "query": {"predicate": DEFAULT_RELATION, "arguments": [query[0], query[1]], "polarity": polarity},
            "budgets": dict(BUDGETS),
        })


@dataclass(frozen=True)
class CncmAnswer:
    verdict: str                 # YES | NO | UNKNOWN | INADMISSIBLE | UNMAPPED
    positive_status: str
    negative_status: str | None
    conflict_elsewhere: bool     # a contradiction exists in the packet but not on the asked pair
    ticks: int
    problem_id: str


def ask_cncm(cncm, state: CncmState, pair: tuple[str, str], *, problem_id: str = "q", scope: str = "component") -> CncmAnswer:
    """Two runs per question; the mapping of the module docstring."""
    pos = cncm.run(state.packet(cncm, pair, True, problem_id, scope=scope))
    ps = pos.terminal_status.value
    conflicts = state.conflicts()
    if scope == "component":
        keep = state.component(pair)
        conflicts = {c for c in conflicts if c[0] in keep and c[1] in keep}
    elsewhere = bool(conflicts) and pair not in conflicts
    if ps == "CONCLUDED":
        return CncmAnswer("YES", ps, None, elsewhere, pos.final_state.logical_tick, problem_id)
    if ps == "CONFLICT_UNRESOLVED":
        return CncmAnswer("INADMISSIBLE", ps, None, elsewhere, pos.final_state.logical_tick, problem_id)
    if ps not in ("NEEDS_INFORMATION",):
        return CncmAnswer("UNMAPPED", ps, None, elsewhere, pos.final_state.logical_tick, problem_id)
    neg = cncm.run(state.packet(cncm, pair, False, problem_id + "_neg", scope=scope))
    ns = neg.terminal_status.value
    if ns == "CONCLUDED":
        return CncmAnswer("NO", ps, ns, elsewhere, pos.final_state.logical_tick + neg.final_state.logical_tick, problem_id)
    if ns == "NEEDS_INFORMATION":
        return CncmAnswer("UNKNOWN", ps, ns, elsewhere, pos.final_state.logical_tick + neg.final_state.logical_tick, problem_id)
    return CncmAnswer("UNMAPPED", ps, ns, elsewhere, pos.final_state.logical_tick + neg.final_state.logical_tick, problem_id)


# ---------------------------------------------------------------------------
# the comparison over a whole stream
# ---------------------------------------------------------------------------

@dataclass
class Comparison:
    probes: int = 0
    agree: int = 0
    disagree: list[dict] = field(default_factory=list)
    unmapped: int = 0
    conflict_elsewhere_total: int = 0
    conflict_elsewhere_disagree: int = 0
    rejected_envelopes: int = 0
    lesson_probes: int = 0
    lesson_agree: int = 0

    def summary(self) -> dict:
        return {
            "probes": self.probes, "agree": self.agree, "disagree": len(self.disagree), "unmapped": self.unmapped,
            "conflict_elsewhere": self.conflict_elsewhere_total, "conflict_elsewhere_disagree": self.conflict_elsewhere_disagree,
            "agree_excluding_conflict_elsewhere": self.agree + self.conflict_elsewhere_disagree,
            "rejected_envelopes": self.rejected_envelopes, "lesson_probes": self.lesson_probes, "lesson_agree": self.lesson_agree,
        }


def compare_stream(cncm, events, expectations, *, stream_id: str = "s", lesson_probe_indices=(), scope: str = "component") -> Comparison:
    """Replay a CAS-RPU event stream through the organism's history rows (so the
    exported envelopes are the accepted ones) and ask CNCM every probe from the
    state folded so far; score against the whole-stream oracle (open world)."""
    sys.path.insert(0, str(REPO / "scripts" / "cas_rpu")); sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))
    from organism import Organism
    from events import EventKind
    org = Organism(closed_world=False)
    by_index = {x.event_index: x for x in expectations}
    state = CncmState()
    cmp = Comparison()
    rows = []
    for i, ev in enumerate(events):
        r = org.consume(ev)
        if ev.kind is EventKind.ASK:
            x = by_index[i]
            ans = ask_cncm(cncm, state, ev.pair, problem_id=f"p{i}", scope=scope)
            cmp.probes += 1
            expected = x.verdict.value
            ok = ans.verdict == expected
            cmp.agree += int(ok)
            cmp.unmapped += int(ans.verdict == "UNMAPPED")
            cmp.conflict_elsewhere_total += int(ans.conflict_elsewhere)
            if i in set(lesson_probe_indices):
                cmp.lesson_probes += 1
                cmp.lesson_agree += int(ok)
            if not ok:
                cmp.conflict_elsewhere_disagree += int(ans.conflict_elsewhere and ans.verdict == "INADMISSIBLE")
                cmp.disagree.append({"index": i, "pair": ev.pair, "expected": expected, "cncm": ans.verdict,
                                     "positive": ans.positive_status, "negative": ans.negative_status, "conflict_elsewhere": ans.conflict_elsewhere})
            continue
        row = {"commit_status": "ACCEPTED" if r.accepted else "REFUSED", "event_id": f"ev{i}", "payload": ev.canonical()}
        rows.append(row)
        envs, rejected = export_rows([row], stream_id)
        cmp.rejected_envelopes += len(rejected)
        for env in envs:
            state.fold(env)
    return cmp
