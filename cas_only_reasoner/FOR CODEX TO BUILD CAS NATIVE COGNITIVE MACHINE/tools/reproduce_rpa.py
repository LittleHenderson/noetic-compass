"""Generate source-bound read-only RPA examples from the native acceptance journal."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from cncm.canonical import canonical_json
from cncm.native_engine import NativeMachine
from cncm.native_model import NativeProblem
from cncm.rpa_model import AtlasSnapshot
from cncm.rpa_native_adapter import native_atlas_from_journal
from render_rpa_view import render_rpa_view


def write(path, content):
    raw = content.encode("utf-8") if isinstance(content, str) else (canonical_json(content)+"\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)


def reproduce(output):
    output.mkdir(parents=True, exist_ok=False)
    source = ROOT / "records/native_procedure_001/acceptance_002"
    genesis = NativeProblem.from_dict(json.loads((source / "genesis.json").read_bytes()))
    acquired = json.loads((source / "acquisition_journal.json").read_bytes())
    acquisition_anchor = json.loads((source / "acquisition_anchor.json").read_bytes())
    final_anchor = json.loads((source / "final_anchor.json").read_bytes())
    partial = NativeMachine()
    partial.start(genesis)
    partial.advance()
    partial.advance()
    journal = partial.journal()
    assert journal["episodes"][0]["trace"] == acquired["episodes"][0]["trace"][:2]
    assert partial.state.native_calls[0].status == "SUSPENDED"
    assert not partial.state.procedure_heads
    write(output / "suspended_journal.json", journal)
    write(output / "suspended_anchor.json", {
        "journal_digest": journal["journal_digest"],
        "source_profile_digest": partial.profile.profile_digest,
        "boundary": "Trusted local prefix reproduced and compared with first two retained native transitions.",
    })
    examples = [
        ("missing_procedure", journal, journal["journal_digest"]),
        ("checked_solution", acquired, acquisition_anchor["journal_digest"]),
        ("recovery_and_rollback", (source / "final_journal.json").read_bytes(), final_anchor["journal_digest"]),
    ]
    rows = []
    for name, evidence, anchor in examples:
        document = native_atlas_from_journal(evidence, trusted_genesis=genesis, expected_journal_digest=anchor)
        snapshot = AtlasSnapshot.from_dict(document["atlas"])
        before = snapshot.current_state_id
        focused = snapshot.focus("bound-call-inputs")
        assert focused.current_state_id == before and focused.nodes == snapshot.nodes and focused.links == snapshot.links
        assert snapshot.flat_graph() == document["atlas"]
        expansion = snapshot.expand(max_depth=3, max_nodes=12)
        write(output / (name+".json"), document)
        write(output / (name+".html"), render_rpa_view(document))
        write(output / (name+"_expansion.json"), expansion.to_dict())
        rows.append({"name": name, "nodes": len(snapshot.nodes), "links": len(snapshot.links),
            "native_state_hash": document["native"]["current_state_hash"],
            "terminal_status": document["native"]["terminal_status"], "output": document["native"]["output"],
            "journal_digest": anchor, "focus_preserves_native_present": True,
            "same_data_for_graph_and_flower": True, "expanded_nodes": len(expansion.visited_node_ids),
            "deferred_count": len(expansion.deferred), "next_actions": document["next_actions"]})
    sources = [
        "cncm/rpa_model.py", "cncm/rpa_native_adapter.py", "tools/render_rpa_view.py",
        "tools/reproduce_rpa.py", "docs/CAS_RPA_PROJECT_FIT.md", "docs/CAS_RPA_MATHEMATICAL_REVIEW.md",
        "records/rpa_001/source_identity.json",
    ]
    files = [{"path": str(path.relative_to(output)), "bytes": path.stat().st_size,
              "sha256": sha256(path.read_bytes()).hexdigest()} for path in sorted(output.iterdir()) if path.is_file()]
    receipt = {"schema_version": "cncm.rpa-prototype-receipt/0.1",
        "status": "REAL_NATIVE_EVIDENCE_PROJECTED", "native_source_profile_digest": partial.profile.profile_digest,
        "sources": [{"path": name, "bytes": (ROOT/name).stat().st_size,
                     "sha256": sha256((ROOT/name).read_bytes()).hexdigest()} for name in sources],
        "examples": rows, "files": files,
        "kernel_state_writes_by_viewer": 0, "model_or_provider_work": False,
        "measured_performance_advantage": False,
        "scope": "Bounded typed records and read-only evidence views, not a live planner or full CNCM acceptance."}
    write(output / "receipt.json", receipt)
    print(canonical_json({"status": receipt["status"], "examples": rows}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    target = parser.parse_args().output.resolve()
    if not target.is_relative_to(ROOT / "records"):
        raise SystemExit("RPA output must stay inside this homebase records directory")
    reproduce(target)

