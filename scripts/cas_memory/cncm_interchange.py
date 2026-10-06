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


# ===========================================================================
# the reverse direction: CNCM → CAS-RPU
# ===========================================================================
#
# Plan and gate answer: `docs/working/helm_cooperation_reverse_direction_plan_2026_10_06.md`
# (worked example A of the fixtures draft, §3.3). CNCM is the holder of givens
# here: every change it holds is committed by a run of the pinned kernel on the
# component packet of the changed pair, and the run id is the provenance the
# envelope carries. CAS-RPU is the receiver: a `Stream` whose single writer
# (`Stream.commit`) is the only way an imported event reaches the organism.
# The receiver keeps every accepted envelope verbatim in a ledger beside the
# history document so an answer's support can be followed back by id to the
# CNCM run it came from.
#
#     CNCM commits                   envelope          CAS-RPU accepted event
#     leads_to(s,o) asserted         FACT, +           events.fact(s,o)
#     leads_to(s,o) polarity false   FACT, -           events.negation(s,o)
#     r(s,o) asserted (foreign r)    FACT, relation r  events.fact(s,o,r)
#     a given dropped by a later run RETRACT, +        events.retract(s,o)   (refused if not a GIVEN here)
#     {retracts, asserts} pair       CORRECTION        retract then fact, atomically (both or neither)
#     a CONCLUDED conclusion         DERIVED           rejected E-IX-DERIVED: re-derived here, never imported
#     a value-bearing statement      (value field)     rejected E-IX-VALUE
#     a proposal / guess             PROPOSED          rejected E-IX-PROPOSED
#     another context's scope        context_id ≠      rejected E-IX-CONTEXT
#     a hop naming this stream       cycle             rejected E-IX-CYCLE

import json as _json

REVERSE_SOURCE = "cncm"
REVERSE_TARGET = "cas_rpu"
LEDGER = "imports.jsonl"
_HYPOTHESIS_NOTE = "a guess is CAS-RPU's own and never a CNCM commit; told directly, not imported"


def _sha(obj) -> str:
    return hashlib.sha256(_json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class CncmSource:
    """CNCM as the holder of givens. `tell(event)` changes what it holds and
    commits the change by one run of the pinned kernel on the component packet
    of the changed pair, with that pair as the query; the envelope returned
    carries the run id as provenance and the run's terminal status as the
    source representation. Guesses are not held (CNCM has no proposal) and
    raise `E-IX-PROPOSED`. Nothing here touches CAS-RPU."""

    def __init__(self, cncm, *, context_id: str, scope: str = "component") -> None:
        self.cncm = cncm
        self.context_id = context_id
        self.scope = scope
        self.state = CncmState()
        self.runs: list[dict] = []
        self.seq = 0

    def _commit(self, pair: tuple[str, str], label: str):
        problem_id = f"c{len(self.runs)}_{label}"
        result = self.cncm.run(self.state.packet(self.cncm, pair, True, problem_id, scope=self.scope))
        fs = result.final_state
        run = {"run_id": fs.run_id, "problem_id": problem_id, "terminal_status": result.terminal_status.value,
               "state_hash": fs.state_hash, "runtime_version": fs.runtime_version,
               "problem_packet_hash": result.problem.input_hash, "ticks": fs.logical_tick}
        self.runs.append(run)
        return result, run

    def _envelope(self, event_type: str, prop: dict, run: dict) -> dict:
        self.seq += 1
        body = {
            "schema_version": ENVELOPE_SCHEMA,
            "source": {"engine": REVERSE_SOURCE, "engine_version": run["runtime_version"], "schema_version": "cncm.problem/0.1",
                       "pinned_commit": CNCM_COMMIT, "stream_id": self.context_id},
            "target": {"engine": REVERSE_TARGET, "schema_version": "revision_streams_contract_2026_10_06", "stream_id": self.context_id},
            "identity": {"context_id": self.context_id, "world_mode": "open"},
            "sequence": {"source_seq": self.seq},
            "event_type": event_type, "status": "accepted",
            "proposition": prop,
            "provenance": {"origin": {"hops": [{"engine": REVERSE_SOURCE, "stream_id": self.context_id, "event_id": run["run_id"]}]},
                           "evidence_ids": [run["run_id"]], "dependency_ids": [], "source_state_digest": run["state_hash"]},
            "source_representation": {"problem_id": run["problem_id"], "terminal_status": run["terminal_status"],
                                      "problem_packet_hash": run["problem_packet_hash"], "scope": self.context_id},
        }
        return {"event_id": "ix-" + _sha(body)[:24], **body}

    def tell(self, event) -> list[dict]:
        """Hold `event` on the CNCM side, commit it by a run, and return the envelopes to send."""
        from events import EventKind
        s, o, rel = _ident(event.subject), _ident(event.obj), event.relation
        if event.kind is EventKind.HYPOTHESIS:
            raise InterchangeError("E-IX-PROPOSED", _HYPOTHESIS_NOTE)
        if event.kind is EventKind.ASK:
            raise InterchangeError("E-IX-KIND", "a question is asked of the receiver, not held by the source")
        if rel == ASSOCIATIVE_RELATION:
            raise InterchangeError("E-IX-RELATION", "CNCM has no associative relation (F13)")
        if rel == LESSON_RELATION:
            raise InterchangeError("E-IX-RULE-UNSUPPORTED", "rules do not cross in this direction yet (plan §2)")
        rel = _ident(rel)
        if event.kind is EventKind.FACT:
            self.state.positive[(rel, s, o)] = f"told-{self.seq + 1}"
            _, run = self._commit((s, o), "fact")
            return [self._envelope("FACT", {"predicate": rel, "arguments": [s, o], "polarity": True}, run)]
        if event.kind is EventKind.NEGATION:
            if rel != DEFAULT_RELATION:
                raise InterchangeError("E-IX-RELATION", "a denial is defined for leads_to only")
            self.state.negative[(s, o)] = f"told-{self.seq + 1}"
            _, run = self._commit((s, o), "negation")
            return [self._envelope("FACT", {"predicate": rel, "arguments": [s, o], "polarity": False}, run)]
        if event.kind is EventKind.RETRACT:
            # CNCM has no retraction: the later run simply does not carry the given.
            # Whether this stream ever held it is the receiver's to decide (F08).
            self.state.positive.pop((rel, s, o), None)
            _, run = self._commit((s, o), "retract")
            return [self._envelope("RETRACT", {"predicate": rel, "arguments": [s, o], "polarity": True}, run)]
        raise InterchangeError("E-IX-KIND", f"unknown kind {event.kind}")

    def conclusion(self, pair: tuple[str, str]) -> dict | None:
        """A CONCLUDED run's conclusion as a DERIVED envelope: what a receiver must refuse."""
        result, run = self._commit(pair, "conclusion")
        if result.terminal_status.value != "CONCLUDED":
            return None
        c = result.final_state.commitment_state.conclusion
        prop = {"predicate": c.predicate, "arguments": list(c.arguments), "polarity": c.polarity, "evidence_status": "derived"}
        return self._envelope("DERIVED", prop, run)

    def correction(self, old: tuple[str, str], new: tuple[str, str]) -> dict:
        """An atomic `{retracts, asserts}` pair, as the semantic layer's ASSERT with
        `previous_digest` would be carried (F07). One run commits both halves."""
        self.state.positive.pop((DEFAULT_RELATION, *old), None)
        self.state.positive[(DEFAULT_RELATION, *new)] = f"told-{self.seq + 1}"
        _, run = self._commit(new, "correction")
        env = self._envelope("CORRECTION", {"predicate": DEFAULT_RELATION, "arguments": list(new), "polarity": True}, run)
        env["retracts"] = {"predicate": DEFAULT_RELATION, "arguments": list(old), "polarity": True}
        env["asserts"] = env.pop("proposition")
        env["provenance"]["dependency_ids"] = ["previous:" + _sha({"pair": list(old)})[:16]]
        return env


@dataclass(frozen=True)
class ImportResult:
    envelope_id: str
    accepted: bool
    code: str | None
    note: str
    own_event_ids: tuple[str, ...] = ()
    verdicts: tuple[str | None, ...] = ()
    withdrawn: tuple[str, ...] = ()
    round_trip: bool | None = None


def _retract_admissible(organism, key: str) -> bool:
    """The organism's own rule (`Organism._retract`): a given still in `pos`."""
    from workspace import Status
    prop = organism.ws.props.get(key)
    if prop is None:
        return False
    if prop.status is Status.FACT:
        return True
    return prop.status is Status.CONTRADICTED and not prop.support


class Receiver:
    """The CAS-RPU stream owner for one context. Every import goes through
    `Stream.commit` (the single writer) with `source="cncm:<envelope id>"`, and
    every accepted envelope is appended verbatim to `imports.jsonl` beside the
    history document, with the stream's own event ids. `open` reads the ledger
    back after a restore so duplicates are still recognised in a new process."""

    def __init__(self, stream, ledger: list[dict] | None = None) -> None:
        self.stream = stream
        self.ledger: list[dict] = list(ledger or [])
        self.results: dict[str, ImportResult] = {}
        self.rejected: list[dict] = []
        for entry in self.ledger:
            self.results[entry["envelope"]["event_id"]] = ImportResult(entry["envelope"]["event_id"], True, None, "from ledger",
                                                                       tuple(entry["own_event_ids"]), round_trip=entry.get("round_trip"))

    @classmethod
    def open(cls, stream) -> "Receiver":
        path = Path(stream.directory) / LEDGER
        entries = []
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                entries = [_json.loads(line) for line in fh if line.strip()]
        return cls(stream, entries)

    @property
    def stream_id(self) -> str:
        return self.stream.identity.stream_id

    # -- validation ----------------------------------------------------------

    def _check(self, env: dict) -> None:
        if env.get("schema_version") != ENVELOPE_SCHEMA:
            raise InterchangeError("E-IX-SCHEMA", f"not a {ENVELOPE_SCHEMA} envelope")
        if env.get("target", {}).get("engine") != REVERSE_TARGET:
            raise InterchangeError("E-IX-TARGET", "this envelope is not addressed to cas_rpu")
        ident = env.get("identity", {})
        if ident.get("context_id") != self.stream.identity.context_id:
            raise InterchangeError("E-IX-CONTEXT", f"context {ident.get('context_id')!r} is not this stream's {self.stream.identity.context_id!r} (F12)")
        if ident.get("world_mode") != self.stream.identity.world_mode:
            raise InterchangeError("E-IX-WORLD", f"world mode {ident.get('world_mode')!r} is not this stream's {self.stream.identity.world_mode!r}")
        hops = env.get("provenance", {}).get("origin", {}).get("hops", [])
        if not hops:
            raise InterchangeError("E-IX-PROVENANCE", "an envelope without an origin hop carries no provenance")
        for hop in hops:
            if hop.get("engine") == REVERSE_TARGET and hop.get("stream_id") == self.stream_id:
                raise InterchangeError("E-IX-CYCLE", "this stream is already in the hop list; an event must not return to its origin")
        t = env.get("event_type")
        if t in ("DERIVED",):
            raise InterchangeError("E-IX-DERIVED", "a conclusion is re-derived by the receiver from its givens, never imported as a given")
        if t in ("PROPOSED", "HYPOTHESIS"):
            raise InterchangeError("E-IX-PROPOSED", "a proposal is not evidence (F10)")
        if t in ("LESSON", "RETRACT_LESSON", "RULE"):
            raise InterchangeError("E-IX-RULE-UNSUPPORTED", "rules do not cross in this direction yet (plan §2)")
        if t not in ("FACT", "RETRACT", "CORRECTION"):
            raise InterchangeError("E-IX-KIND", f"unknown event_type {t!r}")
        ev = env.get("sequence", {}).get("expected_version")
        if ev is not None and ev != self.stream.last_committed_seq:
            raise InterchangeError("E-IX-VERSION", f"expected version {ev} but the stream is at {self.stream.last_committed_seq}")
        for prop in ([env.get("proposition")] if t != "CORRECTION" else [env.get("retracts"), env.get("asserts")]):
            if not isinstance(prop, dict):
                raise InterchangeError("E-IX-PROPOSITION", "a proposition is required")
            if "value" in prop or "value" in env:
                raise InterchangeError("E-IX-VALUE", "CAS-RPU has no value slot; a value-bearing statement is refused, never truncated (F13)")
            if "polarity" not in prop:
                raise InterchangeError("E-IX-POLARITY", "polarity is required; nothing is defaulted")
            if len(prop.get("arguments", [])) != 2:
                raise InterchangeError("E-IX-ARITY", "CAS-RPU holds binary relations only")
            rel = prop.get("predicate")
            if rel == ASSOCIATIVE_RELATION:
                raise InterchangeError("E-IX-RELATION", "an association is never imported as a given (F13)")
            if rel == LESSON_RELATION:
                raise InterchangeError("E-IX-RULE-UNSUPPORTED", "a lesson is not a fact between tokens")
            if not prop["polarity"] and rel != DEFAULT_RELATION:
                raise InterchangeError("E-IX-RELATION", "a denial is defined for leads_to only")

    @staticmethod
    def _event(kind: str, prop: dict):
        from events import Event, EventKind
        s, o = prop["arguments"]
        return Event(EventKind(kind), s, o, prop["predicate"])

    def _plan(self, env: dict):
        """The CAS-RPU events an envelope maps to, in order, or the refusal."""
        t = env["event_type"]
        if t == "FACT":
            p = env["proposition"]
            return [self._event("fact" if p["polarity"] else "negation", p)]
        if t == "RETRACT":
            p = env["proposition"]
            if not p["polarity"]:
                raise InterchangeError("E-IX-NEG-RETRACT", "the grammar has no negative retract (F13)")
            ev = self._event("retract", p)
            if not _retract_admissible(self.stream.organism, ev.key):
                raise InterchangeError("E-IX-RETRACT-REFUSED", f"{ev.key} is not a given in this stream (E-ORG-001/002); nothing to withdraw")
            return [ev]
        r, a = env["retracts"], env["asserts"]
        if not r["polarity"]:
            raise InterchangeError("E-IX-NEG-RETRACT", "the grammar has no negative retract (F13)")
        rev, aev = self._event("retract", r), self._event("fact" if a["polarity"] else "negation", a)
        if not _retract_admissible(self.stream.organism, rev.key):
            raise InterchangeError("E-IX-CORRECTION-REFUSED", f"the correction's retract of {rev.key} would be refused; nothing is half-applied (F07)")
        return [rev, aev]

    # -- the import ------------------------------------------------------------

    def import_envelope(self, env: dict) -> ImportResult:
        eid = env.get("event_id", "")
        if eid in self.results:
            return self.results[eid]                      # exactly once; the earlier result stands
        try:
            self._check(env)
            events = self._plan(env)
        except InterchangeError as exc:
            res = ImportResult(eid, False, exc.code, str(exc))
            self.rejected.append({"event_id": eid, "code": exc.code, "reason": str(exc)})
            self.results[eid] = res
            return res
        own, verdicts, withdrawn = [], [], []
        for ev in events:
            r = self.stream.commit(ev, source=f"cncm:{eid}")
            own.append(self.stream.rows[-1]["event_id"])
            verdicts.append(r.verdict)
            withdrawn.extend(r.withdrawn)
            if not r.accepted:
                # Only a RETRACT/CORRECTION can be refused and both were pre-checked; a refusal
                # here is recorded in the history (REFUSED row) and reported, never hidden.
                res = ImportResult(eid, False, "E-IX-REFUSED:" + str(r.code), r.note, tuple(own), tuple(verdicts), tuple(withdrawn))
                self.results[eid] = res
                return res
        rt = self._round_trip(env, events[-1])
        entry = {"envelope": env, "own_event_ids": own, "seq": self.stream.last_committed_seq, "round_trip": rt}
        self._append(entry)
        res = ImportResult(eid, True, None, "imported", tuple(own), tuple(verdicts), tuple(withdrawn), rt)
        self.results[eid] = res
        return res

    def _round_trip(self, env: dict, last) -> bool:
        """Re-encode what the workspace now holds for the key and compare it with what was sent."""
        from events import EventKind
        from workspace import Status
        prop = env["asserts"] if env["event_type"] == "CORRECTION" else env["proposition"]
        if last.kind is EventKind.RETRACT:
            held = self.stream.organism.ws.props.get(last.key)
            return held is None or held.status is Status.RETRACTED
        pid = ("~" if not prop["polarity"] else "") + last.key
        held = self.stream.organism.ws.props.get(pid)
        if held is None:
            return False
        back = {"predicate": held.relation, "arguments": [held.subject, held.obj], "polarity": not held.negated}
        return back == {"predicate": prop["predicate"], "arguments": list(prop["arguments"]), "polarity": prop["polarity"]}

    def _append(self, entry: dict) -> None:
        self.ledger.append(entry)
        path = Path(self.stream.directory) / LEDGER
        with path.open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(entry, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    # -- following an answer back ------------------------------------------------

    def provenance_of(self, response) -> dict:
        """For a YES answer: the given keys it rests on, and for each the envelope
        and CNCM run that put it there (the most recent accepted import of that key)."""
        ep = response.episode
        if ep is None or ep.conclusion is None:
            return {"roots": [], "envelopes": {}, "runs": {}}
        roots = list(self.stream.organism.ws.roots(ep.conclusion.pid)) or [ep.conclusion.pid]
        by_own = {}
        for entry in self.ledger:
            for own in entry["own_event_ids"]:
                by_own[own] = entry
        envelopes, runs = {}, {}
        for row in self.stream.rows:
            if row["commit_status"] != "ACCEPTED" or row["type"] not in ("FACT", "NEGATION"):
                continue
            p = row["payload"]
            key = ("~" if row["type"] == "NEGATION" else "") + f"{p['subject']}|{p['relation']}|{p['obj']}"
            if key in roots and row["event_id"] in by_own:
                env = by_own[row["event_id"]]["envelope"]
                envelopes[key] = env["event_id"]
                runs[key] = env["provenance"]["origin"]["hops"][0]["event_id"]
        return {"roots": sorted(roots), "envelopes": envelopes, "runs": runs}


# ---------------------------------------------------------------------------
# the comparison over a whole stream, with restarts between sessions
# ---------------------------------------------------------------------------

#: Run in a fresh operating-system process: restore the stream and its ledger,
#: apply one session's items (imports and the stream's own asks and guesses),
#: print one JSON line of outcomes.
_CHILD = r"""
import json, sys
sys.path.insert(0, {cas!r}); sys.path.insert(0, {ccb!r}); sys.path.insert(0, {mem!r})
for banned in ("torch", "openai", "anthropic", "requests"):
    assert banned not in sys.modules
from history import Stream
from controls import ctl_recompute
from events import Event, EventKind
import cncm_interchange as ix
stream = Stream.restore({path!r}, reference=ctl_recompute)
rx = ix.Receiver.open(stream)
items = json.load(open({items!r}))
out = []
for item in items:
    if item["op"] == "import":
        r = rx.import_envelope(item["envelope"])
        out.append({{"op": "import", "accepted": r.accepted, "code": r.code, "verdicts": list(r.verdicts), "withdrawn": list(r.withdrawn), "round_trip": r.round_trip}})
    else:
        e = item["event"]
        r = stream.commit(Event(EventKind(e["kind"]), e["subject"], e["obj"], e["relation"]))
        out.append({{"op": item["op"], "accepted": r.accepted, "code": r.code, "verdict": r.verdict, "withdrawn": list(r.withdrawn), "route": r.route}})
print(json.dumps({{"out": out, "rows": len(stream.rows), "recovered_from": stream.recovered_from}}))
"""


@dataclass
class ImportComparison:
    probes: int = 0
    agree: int = 0
    disagree: list[dict] = field(default_factory=list)
    designed_probes: int = 0                 # cross-session designed probes of the stream (the import probes)
    designed_agree: int = 0
    by_mechanism: dict[str, list[int]] = field(default_factory=dict)   # letter -> [probes, agree]
    imports: int = 0
    imports_accepted: int = 0
    rejected: dict[str, int] = field(default_factory=dict)
    refused_expected: int = 0                # retracts the stream itself designs as refused
    refused_matched: int = 0
    guesses_told: int = 0
    associations_told: int = 0
    withdrawn_total: int = 0
    round_trip_failures: int = 0
    restarts: int = 0
    cncm_runs: int = 0
    cncm_terminal: dict[str, int] = field(default_factory=dict)

    def summary(self) -> dict:
        return {
            "probes": self.probes, "agree": self.agree, "disagree": len(self.disagree),
            "designed_probes": self.designed_probes, "designed_agree": self.designed_agree,
            "by_mechanism": {k: {"probes": v[0], "agree": v[1]} for k, v in sorted(self.by_mechanism.items())},
            "imports": self.imports, "imports_accepted": self.imports_accepted, "rejected": dict(sorted(self.rejected.items())),
            "refused_expected": self.refused_expected, "refused_matched": self.refused_matched,
            "guesses_told": self.guesses_told, "associations_told": self.associations_told, "withdrawn": self.withdrawn_total, "round_trip_failures": self.round_trip_failures,
            "restarts": self.restarts, "cncm_runs": self.cncm_runs, "cncm_terminal": dict(sorted(self.cncm_terminal.items())),
        }


def compare_import_stream(cncm, seed_stream, root, *, restart: str = "in-process", scope: str = "component") -> ImportComparison:
    """CNCM holds and commits every given of `seed_stream`; CAS-RPU receives them
    only through the envelope and answers the stream's asks; verdicts are scored
    against the stream's own oracle. Guesses (HYPOTHESIS) are CAS-RPU's own and
    are told directly. Between sessions the receiver stream is restored:
    `"in-process"` replays the history in this process, `"process"` restores it
    in a fresh operating-system process per session, `None` never restarts.
    Every restore replays against `ctl_recompute` (the control) on every ASK."""
    import subprocess
    sys.path.insert(0, str(REPO / "scripts" / "cas_rpu")); sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))
    from controls import ctl_recompute
    from events import EventKind
    from history import Stream

    root = Path(root)
    sdir = root / f"{seed_stream.context_id}_{'twin' if seed_stream.twin_of is not None else 'primary'}"
    cmp = ImportComparison()
    source = CncmSource(cncm, context_id=seed_stream.context_id, scope=scope)
    stream = Stream.genesis(sdir, organism_id="rx", context_id=seed_stream.context_id, closed_world=seed_stream.closed_world)
    rx = Receiver(stream)
    by_index = {x.event_index: x for x in seed_stream.expectations}
    designed = {ep.designed_probe_index: ep for ep in seed_stream.episodes if ep.cross_session}
    refused = set(seed_stream.refused)

    def score(i, verdict, accepted, code):
        ev = seed_stream.events[i]
        if ev.kind is EventKind.ASK:
            x = by_index[i]
            ok = verdict == x.verdict.value
            cmp.probes += 1; cmp.agree += int(ok)
            if i in designed:
                cmp.designed_probes += 1; cmp.designed_agree += int(ok)
                m = cmp.by_mechanism.setdefault(designed[i].mechanism, [0, 0]); m[0] += 1; m[1] += int(ok)
            if not ok:
                cmp.disagree.append({"index": i, "pair": ev.pair, "expected": x.verdict.value, "got": verdict, "variant": designed[i].variant if i in designed else None})
        elif i in refused:
            cmp.refused_expected += 1
            cmp.refused_matched += int(not accepted)

    for k in range(seed_stream.sessions):
        lo, hi = seed_stream.session_range(k)
        if k > 0 and restart:
            cmp.restarts += 1
        items = []
        for i in range(lo, hi):
            ev = seed_stream.events[i]
            if ev.kind is EventKind.ASK:
                items.append({"op": "ask", "index": i, "event": ev.canonical()})
            elif ev.kind is EventKind.HYPOTHESIS:
                cmp.guesses_told += 1
                items.append({"op": "guess", "index": i, "event": ev.canonical()})
            elif ev.relation == ASSOCIATIVE_RELATION:
                # An association is CAS-RPU's own (`^8` follows it, `^6` rejects it) and
                # CNCM has no counterpart (F13): told directly, never imported.
                cmp.associations_told += 1
                items.append({"op": "associate", "index": i, "event": ev.canonical()})
            else:
                for env in source.tell(ev):
                    cmp.imports += 1
                    items.append({"op": "import", "index": i, "envelope": env})
        cmp.cncm_runs = len(source.runs)
        if restart == "process" and k > 0:
            items_path = sdir / f"session{k}.json"
            items_path.write_text(_json.dumps(items), encoding="utf-8")
            script = _CHILD.format(cas=str(REPO / "scripts" / "cas_rpu"), ccb=str(REPO / "scripts" / "ccb_r1"),
                                   mem=str(REPO / "scripts" / "cas_memory"), path=str(sdir), items=str(items_path))
            proc = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=900)
            if proc.returncode != 0:
                raise RuntimeError(f"child failed in session {k}:\n{proc.stderr[-4000:]}")
            outs = _json.loads(proc.stdout.strip().splitlines()[-1])["out"]
            for item, o in zip(items, outs):
                if item["op"] == "import":
                    cmp.imports_accepted += int(o["accepted"])
                    if not o["accepted"]:
                        cmp.rejected[o["code"]] = cmp.rejected.get(o["code"], 0) + 1
                    cmp.withdrawn_total += len(o["withdrawn"])
                    cmp.round_trip_failures += int(o["accepted"] and not o["round_trip"])
                    score(item["index"], None, o["accepted"], o["code"])
                else:
                    cmp.withdrawn_total += len(o["withdrawn"])
                    score(item["index"], o["verdict"], o["accepted"], o["code"])
            stream = Stream.restore(sdir, reference=ctl_recompute)      # the parent re-reads what the child committed
            rx = Receiver.open(stream)
            continue
        if restart == "in-process" and k > 0:
            stream = Stream.restore(sdir, reference=ctl_recompute)
            rx = Receiver.open(stream)
        for item in items:
            if item["op"] == "import":
                r = rx.import_envelope(item["envelope"])
                cmp.imports_accepted += int(r.accepted)
                if not r.accepted:
                    cmp.rejected[r.code] = cmp.rejected.get(r.code, 0) + 1
                cmp.withdrawn_total += len(r.withdrawn)
                cmp.round_trip_failures += int(r.accepted and not r.round_trip)
                score(item["index"], None, r.accepted, r.code)
            else:
                e = item["event"]
                from events import Event
                r = stream.commit(Event(EventKind(e["kind"]), e["subject"], e["obj"], e["relation"]))
                cmp.withdrawn_total += len(r.withdrawn)
                score(item["index"], r.verdict, r.accepted, r.code)
    for run in source.runs:
        cmp.cncm_terminal[run["terminal_status"]] = cmp.cncm_terminal.get(run["terminal_status"], 0) + 1
    return cmp


def _main(argv=None) -> int:
    import argparse
    import tempfile
    p = argparse.ArgumentParser(description="CNCM → CAS-RPU import comparison over generated session streams")
    p.add_argument("--seeds", default="0-2", help="e.g. 0-2 or 3000,3001")
    p.add_argument("--restart", default="process", choices=["process", "in-process", "none"])
    p.add_argument("--no-twins", action="store_true")
    p.add_argument("--root", default=None, help="directory for the receiver stores (default: a temporary one)")
    args = p.parse_args(argv)
    sys.path.insert(0, str(REPO / "scripts" / "cas_rpu")); sys.path.insert(0, str(REPO / "scripts" / "ccb_r1"))
    from sessions import generate_session_set
    seeds = []
    for part in args.seeds.split(","):
        if "-" in part:
            a, b = part.split("-"); seeds.extend(range(int(a), int(b) + 1))
        else:
            seeds.append(int(part))
    cncm = load_cncm()
    sset = generate_session_set(seeds, closed_world=False, twins=not args.no_twins)
    restart = None if args.restart == "none" else args.restart
    tmp = tempfile.TemporaryDirectory() if args.root is None else None
    root = Path(args.root) if args.root else Path(tmp.name)
    print(f"# CNCM → CAS-RPU import comparison; kernel {CNCM_COMMIT[:9]} pinned {loaded_version()['matches_pin']}; seeds {seeds}; restart={args.restart}; open world")
    totals = {}
    for label, streams in (("primary", sset.streams), ("twin", sset.twins)):
        for s in streams:
            cmp = compare_import_stream(cncm, s, root, restart=restart)
            sm = cmp.summary()
            print(f"{label} seed {s.seed}: probes {sm['agree']}/{sm['probes']}; designed {sm['designed_agree']}/{sm['designed_probes']} "
                  f"{sm['by_mechanism']}; imports {sm['imports_accepted']}/{sm['imports']} rejected {sm['rejected']}; "
                  f"refused-as-designed {sm['refused_matched']}/{sm['refused_expected']}; guesses told {sm['guesses_told']}; associations told {sm['associations_told']}; "
                  f"withdrawn {sm['withdrawn']}; round-trip failures {sm['round_trip_failures']}; restarts {sm['restarts']}; "
                  f"cncm runs {sm['cncm_runs']} {sm['cncm_terminal']}")
            for d in cmp.disagree:
                print(f"    DISAGREE {d}")
            t = totals.setdefault(label, {"probes": 0, "agree": 0, "designed_probes": 0, "designed_agree": 0, "imports": 0, "imports_accepted": 0, "restarts": 0, "round_trip_failures": 0, "streams": 0})
            for key in ("probes", "agree", "designed_probes", "designed_agree", "imports", "imports_accepted", "restarts", "round_trip_failures"):
                t[key] += sm[key]
            t["streams"] += 1
    for label, t in totals.items():
        print(f"TOTAL {label}: streams {t['streams']}; probes {t['agree']}/{t['probes']}; designed {t['designed_agree']}/{t['designed_probes']}; "
              f"imports {t['imports_accepted']}/{t['imports']}; restarts {t['restarts']}; round-trip failures {t['round_trip_failures']}")
    if tmp is not None:
        tmp.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
