"""RPA narrowing over the organism's held records — the "record-first with RPA" path.

Memory contract M5 and M8.6. The Recursive Possibility Atlas is a read-only
map of states and alternatives. Here it is built as a projection of ONE
organism's workspace — every proposition a node with the atlas's own status
vocabulary, every standing conclusion a VERIFIED state reachable from the
present with its supports as evidence, every told guess HYPOTHETICAL — and
then asked one question per record-first lookup: is this candidate a VERIFIED
record whose evidence is all OBSERVED? It may only REMOVE candidates (the
organism refuses anything else, E-ORG-007), so a measured difference between
the two record-first paths is attributable to the atlas alone.

The atlas code is reused, never copied (owner decision 2; contract M12a item
3): it is imported from the RPA checkout at commit `eb99855` of branch
`codex/helm-rpa-recorded-run-20260922`, mounted read-only at the path in
`CAS_RPA_ROOT` or the session's default. When that checkout is not mounted
this module raises `RpaUnavailable`, and the experiment reports the RPA path
as not run rather than inventing one.

This module lives outside the reasoning package: the organism never imports
an atlas; the narrower is injected (`Organism(record_narrow=...)`).

Honest expectation, written before the run (directive §5, "if RPA adds no
measured value, say so"): with one candidate per key, narrowing can only
confirm or remove what the dependency check already decides. The expected
measured difference in verdicts and hits is zero.
"""

from __future__ import annotations

import hashlib
import importlib
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = (
    REPO / ".claude" / "worktrees" / "rpa-readonly" / "cas_only_reasoner"
    / "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
RPA_COMMIT = "eb9985566bd11a89f485d627186ef0efa7177f02"
RPA_BRANCH = "codex/helm-rpa-recorded-run-20260922"
#: SHA-256 of the two files actually imported, as committed at RPA_COMMIT. The
#: loader refuses any other content: "the RPA at eb99855" must mean exactly that.
RPA_FILE_SHA256 = {
    "cncm/rpa_model.py": "323a53b951644a93603cd2f56204fd5a038a3161f4778e28777e650a4f966f01",
    "cncm/canonical.py": "424323335452fecd26cd6659136475c0fd19bda695ab07811d34d1734564877a",
}
MODEL_VERSION = "cas_rpu.organism-atlas/0.1"


class RpaUnavailable(RuntimeError):
    pass


def rpa_root() -> Path:
    return Path(os.environ.get("CAS_RPA_ROOT", str(DEFAULT_ROOT)))


def loaded_version(root: Path | None = None) -> dict:
    """What is actually mounted: file digests, and the checkout's HEAD when git can say."""
    root = root or rpa_root()
    out = {"root": str(root), "pinned_commit": RPA_COMMIT, "files": {}}
    for rel in RPA_FILE_SHA256:
        path = root / rel
        out["files"][rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    try:
        head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        out["head"] = head.stdout.strip() if head.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        out["head"] = None
    out["matches_pin"] = out["files"] == RPA_FILE_SHA256
    return out


def load_rpa():
    """Import `cncm.rpa_model` from the mounted checkout, or raise RpaUnavailable.

    Refuses a checkout whose imported files differ from those committed at
    RPA_COMMIT, so a result labelled "RPA at eb99855" was produced by that code
    and no other.
    """
    root = rpa_root()
    if not (root / "cncm" / "rpa_model.py").exists():
        raise RpaUnavailable(
            f"RPA checkout not mounted at {root} (commit {RPA_COMMIT[:9]}, branch {RPA_BRANCH}); "
            "set CAS_RPA_ROOT or mount it read-only"
        )
    version = loaded_version(root)
    if not version["matches_pin"]:
        raise RpaUnavailable(
            f"the RPA files at {root} are not those committed at {RPA_COMMIT[:9]}: "
            f"{version['files']} (HEAD {version['head']}); refusing to load an unpinned version"
        )
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    model = importlib.import_module("cncm.rpa_model")
    canonical = importlib.import_module("cncm.canonical")
    model.content_id = canonical.content_id   # the native adapter's own id helper, exposed alongside
    return model


def node_id_for(pid: str) -> str:
    """A workspace pid as an atlas identifier: `~A|leads_to|B` -> `rec-not.A.leads_to.B`."""
    body = pid[1:] if pid.startswith("~") else pid
    return "rec-" + ("not." if pid.startswith("~") else "") + body.replace("|", ".")


def idea_id_for(key: str) -> str:
    return "idea-" + key.replace("|", ".")


def organism_atlas(organism, stream_id: str = "stream", rpa=None):
    """Project one organism's workspace into an `AtlasSnapshot`.

    Status vocabulary (atlas <- workspace): OBSERVED <- a given (FACT or
    ASSUMPTION) or a derived record that is not standing; VERIFIED <- a
    standing conclusion (CONCLUDED YES, still assertive); HYPOTHETICAL <- a
    told guess; UNKNOWN <- a contradicted record; REJECTED <- a retracted one.
    The present is one STATE node; every record is a part of it; every
    standing conclusion is reachable from it by the action "derive" with its
    supports as evidence.
    """
    rpa = rpa or load_rpa()
    from workspace import Status  # the reasoning package's own vocabulary

    ctx = rpa.AtlasContext(
        context_id=stream_id.replace("|", "."),
        model_version=MODEL_VERSION,
        observation_id=f"clock-{organism.clock}",
        observation_time=f"logical-clock:{organism.clock}",
        record_version=organism.clock,
    )
    status_of = {
        Status.FACT: rpa.NodeStatus.OBSERVED,
        Status.ASSUMPTION: rpa.NodeStatus.OBSERVED,
        Status.DERIVED: rpa.NodeStatus.OBSERVED,
        Status.HYPOTHESIS: rpa.NodeStatus.HYPOTHETICAL,
        Status.CONTRADICTED: rpa.NodeStatus.UNKNOWN,
        Status.RETRACTED: rpa.NodeStatus.REJECTED,
    }
    nodes = {}
    links = []
    present = "present"
    nodes[present] = rpa.AtlasNode(
        node_id=present, idea_id=present, label="Current held state", context=ctx,
        status=rpa.NodeStatus.OBSERVED, kind=rpa.NodeKind.STATE,
        fields=(("clock", str(organism.clock)), ("standing", str(len(organism.standing)))),
    )
    hypothesis = None
    for prop in sorted(organism.ws.props.values(), key=lambda p: p.pid):
        nid = node_id_for(prop.pid)
        status = status_of[prop.status]
        kind = rpa.NodeKind.EVIDENCE
        if prop.status is Status.DERIVED:
            kind = rpa.NodeKind.STATE
            if prop.pid in organism.standing:
                status = rpa.NodeStatus.VERIFIED
        elif prop.status is Status.HYPOTHESIS:
            kind = rpa.NodeKind.STATE
        evidence = tuple(sorted(node_id_for(s) for s in prop.support))
        nodes[nid] = rpa.AtlasNode(
            node_id=nid, idea_id=idea_id_for(prop.key), label=str(prop), context=ctx,
            status=status, kind=kind,
            fields=(("pid", prop.pid), ("stage", prop.stage), ("status", prop.status.value)),
            evidence_refs=evidence,
        )
        links.append(rpa.AtlasLink(
            link_id=rpa.content_id("part", {"present": present, "record": nid}),
            source_id=present, target_id=nid, relation=rpa.LinkType.CONTAINS_PART,
            projection="workspace.props",
        ))
        if status is rpa.NodeStatus.VERIFIED and evidence:
            links.append(rpa.AtlasLink(
                link_id=rpa.content_id("derive", {"present": present, "record": nid}),
                source_id=present, target_id=nid, relation=rpa.LinkType.REACHABLE_VIA,
                action_id="derive", evidence_refs=evidence, transition_status="observed",
            ))
        if status is rpa.NodeStatus.HYPOTHETICAL and hypothesis is None:
            hypothesis = nid
    return rpa.AtlasSnapshot(
        nodes=tuple(nodes.values()), links=tuple(links),
        current_state_id=present, focus_node_id=present, hypothesis_branch_id=hypothesis,
    )


class RpaNarrower:
    """`(key, candidates) -> candidates'`, injected into `Organism(record_narrow=...)`.

    Rebuilds the atlas from the organism when the clock has moved (an atlas is
    a read-only index: rebuilt, never mutated), then keeps a candidate only if
    its node is VERIFIED and every evidence node is OBSERVED or VERIFIED. If
    the atlas cannot be built (a bound exceeded), narrowing abstains — returns
    the candidates unchanged — and counts the failure, so an index failure can
    never remove a valid record or admit an invalid one.
    """

    def __init__(self, organism, stream_id: str = "stream", rpa=None) -> None:
        self.organism = organism
        self.stream_id = stream_id
        self.rpa = rpa or load_rpa()
        self._atlas = None
        self._clock = -1
        self.stats = {"rebuilds": 0, "lookups": 0, "removed": 0, "abstained": 0}

    def atlas(self):
        if self._atlas is None or self._clock != self.organism.clock:
            self._atlas = organism_atlas(self.organism, self.stream_id, self.rpa)
            self._clock = self.organism.clock
            self.stats["rebuilds"] += 1
        return self._atlas

    def __call__(self, key: str, candidates) -> tuple[str, ...]:
        self.stats["lookups"] += 1
        candidates = tuple(candidates)
        try:
            nodes = self.atlas().node_map()
        except Exception:
            self.stats["abstained"] += 1
            return candidates
        ok = (self.rpa.NodeStatus.OBSERVED, self.rpa.NodeStatus.VERIFIED)
        kept = []
        for c in candidates:
            node = nodes.get(node_id_for(c))
            if node is not None and node.status is self.rpa.NodeStatus.VERIFIED and all(
                nodes[e].status in ok for e in node.evidence_refs if e in nodes
            ):
                kept.append(c)
        self.stats["removed"] += len(candidates) - len(kept)
        return tuple(kept)


def available() -> bool:
    try:
        load_rpa()
        return True
    except RpaUnavailable:
        return False
