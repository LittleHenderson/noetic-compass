"""Project all retained compound acceptance cuts into an offline evidence view.

This is symbolic replay and display verification, not training or a benchmark of
reasoning improvement. Inputs remain authored, externally anchored fixtures.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
FORBIDDEN = frozenset({"torch", "transformers", "boto3", "botocore", "requests", "httpx", "openai"})


class DenyModelsAndProviders:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise AssertionError("forbidden model/provider import: " + fullname)


sys.meta_path.insert(0, DenyModelsAndProviders())
from cncm.canonical import canonical_json, digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundProblem
from cncm.compound_profile import SOURCE_FILES, load_compound_profile
from cncm.compound_recovery import _decode_proposal_batch
from cncm.rpa_compound_adapter import compound_atlas_from_journal, candidate_page, record_body_from_catalog
from cncm.rpa_model import AtlasSnapshot
from render_compound_rpa_view import render_compound_rpa_view, validate_document

# Fixed independently retained acceptance receipt, not an anchor read from a journal.
PRIOR_RECEIPT_SHA256 = "3f3ca9e9f3016df527ddbf218f7c0d26a41cc7d9baf01ca99f8d7632f6fcf66b"
PRIOR_RPA_RECEIPT_SHA256 = "dcd8e3c99fdf0edd45f0e6ea56a6d9336fabac9761ac3056d29b223bf6339f62"
COMPOUND_PROFILE = "3a7c6f620782ce820145d5e119d8f64c2050008378a9fbfdf94adbd1a9dcfed5"
SOURCE = ROOT / "records/compound_procedure_001/acceptance_001"
VIEW_SOURCES = (
    "cncm/rpa_model.py", "cncm/rpa_compound_adapter.py", "tools/render_rpa_view.py",
    "tools/render_compound_rpa_view.py", "tools/reproduce_compound_rpa.py",
    "docs/CAS_RPA_PROJECT_FIT.md", "docs/CAS_RPA_MATHEMATICAL_REVIEW.md",
    "docs/CAS_RPA_COMPOUND_EXTENSION_v0.1.md", "docs/CAS_RPA_COMPOUND_IMPLEMENTATION_v0.1.md",
    "records/rpa_001/source_identity.json",
)


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    raw = value.encode("utf-8") if type(value) is str else (canonical_json(value) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(raw)


def identity(path, base):
    raw = path.read_bytes()
    return {"path": path.relative_to(base).as_posix(), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def verify_previous_inputs():
    assert sha256((SOURCE / "receipt.json").read_bytes()).hexdigest() == PRIOR_RECEIPT_SHA256
    receipt = read(SOURCE / "receipt.json")
    assert len(receipt["files"]) == 48 and receipt["fresh_process_cuts"] == 75
    for row in receipt["files"]:
        path = (SOURCE / row["path"]).resolve()
        assert path.is_relative_to(SOURCE.resolve()) and identity(path, SOURCE) == row
    old_path = ROOT / "records/rpa_001/demo2/receipt.json"
    assert sha256(old_path.read_bytes()).hexdigest() == PRIOR_RPA_RECEIPT_SHA256
    old_rpa = read(old_path)
    assert len(old_rpa["sources"]) == 7
    for row in old_rpa["sources"]:
        assert identity(ROOT / row["path"], ROOT) == row
    profile = load_compound_profile()
    assert profile.profile_digest == COMPOUND_PROFILE and len(profile.source_files) == 87
    return profile, receipt, old_rpa["sources"]


def project(journal, genesis, ingress, anchor, extensions, profile):
    before = canonical_json(journal)
    view = compound_atlas_from_journal(journal, trusted_genesis=genesis, trusted_ingress=ingress,
        expected_journal_digest=anchor, trusted_ingress_extensions=extensions, profile=profile)
    state = journal["episodes"][-1]["final_state"]
    native = view["native"]
    assert native["runtime_version"] == "0.5.0" and native["authority"] == "DISPLAY_ONLY"
    assert native["current_state_hash"] == state["state_hash"]
    assert native["source_profile_digest"] == profile.profile_digest and native["journal_digest"] == anchor
    assert native["ingress_digest"] == state["ingress_digest"] == journal["ingress_digest"]
    assert native["current_call"] == state["compound_call"] and native["frames"] == state["rpm_stack"]
    from cncm.compound_program import CallProgram
    expected_program = next((p for p in state["compound_artifacts"]
        if CallProgram.from_dict(p).program_digest == state["compound_head"]), None)
    assert native["current_program"] == expected_program
    assert native["parameters"] == journal["episodes"][-1]["problem"]["parameters"]
    assert native["source_bindings"] == state["memory_bindings"]
    assert native["budget"]["remaining"] == state["native_budget"]
    assert native["terminal_status"] == state["halt_status"]
    assert native["conditional_output"] == (state["compound_call"]["output"] if state["compound_call"] else None)
    expected_events = [(i, event, batch) for i, ep in enumerate(journal["episodes"])
        for event, batch in zip(ep["trace"], ep["proposal_batches"], strict=True)]
    assert len(expected_events) == len(view["timeline"])
    for row, (index, event, batch) in zip(view["timeline"], expected_events, strict=True):
        assert row["episode_index"] == index and row["event"] == event and row["proposal_batch"] == batch
    for index, episode in enumerate(journal["episodes"]):
        rows = [row for row in view["timeline"] if row["episode_index"] == index]
        charged = [key for row in rows for key in row["work_record_digests"]]
        assert len(charged) == len(set(charged)), "work record charged more than once"
        for allocation, limit in (("instructions_allocated", "instructions_remaining"),
                                  ("checker_calls_allocated", "checker_calls_remaining")):
            expected = episode["problem"]["budget"][limit] - episode["final_state"]["native_budget"][limit]
            assert sum(row["work"][allocation] for row in rows) == expected
    snapshot = AtlasSnapshot.from_dict(view["atlas"])
    assert snapshot.current_state_id == "state-" + state["state_hash"]
    assert snapshot.flat_graph() == view["atlas"]
    focused = snapshot.focus("current-call")
    assert focused.current_state_id == snapshot.current_state_id
    assert focused.nodes == snapshot.nodes and focused.links == snapshot.links
    original = snapshot.snapshot_digest
    expansion = snapshot.expand(max_depth=3, max_nodes=12)
    assert len(expansion.visited_node_ids) <= 12 and snapshot.snapshot_digest == original
    assert validate_document(view) == canonical_json(view)
    assert canonical_json(journal) == before, "projection changed input history"
    return view


def save_view(output, name, view, examples):
    snapshot = AtlasSnapshot.from_dict(view["atlas"])
    native = view["native"]
    write(output / (name + ".json"), view)
    write(output / (name + ".html"), render_compound_rpa_view(view))
    write(output / (name + "_expansion.json"), snapshot.expand(max_depth=3, max_nodes=12).to_dict())
    examples.append({"name": name, "view_digest": digest(view), "journal_digest": native["journal_digest"],
        "current_state_hash": native["current_state_hash"], "terminal_status": native["terminal_status"],
        "conditional_output": native["conditional_output"], "frames": [row["kind"] for row in native["frames"]],
        "dispatch": native["dispatch"], "budget": native["budget"], "nodes": len(snapshot.nodes), "links": len(snapshot.links),
        "focus_preserves_current": True, "identical_graph_and_flower_data": True})
    print(canonical_json({"saved": name, "status": native["terminal_status"], "nodes": len(snapshot.nodes)}), flush=True)


def verify_pages(output, name, view):
    pages = []
    for report in view["native"]["candidate_reports"]:
        record_digest = report["record_digests"][0]
        original = record_body_from_catalog(view["native"]["evidence_catalog"], record_digest)["report"]
        page = candidate_page(view, record_digest)
        joined = []
        while True:
            assert page["start"] == len(joined)
            joined.extend(item["candidate"] for item in page["items"])
            assert page["deferred"] == {"before": [0, page["start"]], "after": [len(joined), page["total"]]}
            pages.append(page)
            if page["next_cursor"] is None:
                break
            page = candidate_page(view, record_digest, cursor=page["next_cursor"])
        assert joined == original["candidates"] and len(joined) == report["total"]
    write(output / (name + "_candidate_pages.json"), {"pages": pages, "all_candidates_exact": True})
    return len(pages)


def render_index(examples):
    descriptions = {
        "missing_primitive": "The outer task and primitive acquisition both have saved return points.",
        "constructed_not_installed": "Construction found a candidate; installation has not happened.",
        "installed_waiting_return": "The program is installed; the saved caller still awaits its return.",
        "checked_solution": "The original sourced equation concludes with a checked answer of 3.",
        "source_correction": "The admitted fixture correction changes the checked answer to 2.",
        "corrected_reuse": "A later task recalls the correction and reuses the program, returning 3.",
        "compound_rollback": "Removing the active compound head prevents future dispatch.",
        "primitive_rollback": "The compound artifact remains; its required primitive is no longer authorized.",
        "search_exhausted": "A bounded search ends without a solution; this does not prove impossibility.",
        "budget_exhausted": "The next required work cannot fit the remaining allocation.",
    }
    cards = ''.join('<a class="card" href="' + escape(row['name']) + '.html"><strong>'
        + escape(row['name'].replace('_', ' ').capitalize()) + '</strong><p>'
        + escape(descriptions[row['name']]) + '</p><small>' + escape(row['terminal_status'])
        + ' · ' + str(row['nodes']) + ' evidence nodes</small></a>' for row in examples)
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>CAS-RPA · Compound evidence workbench</title><style>
*{box-sizing:border-box}body{margin:0;background:#101827;color:#e8edf5;font:16px/1.55 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:48px 24px}h1{font-size:clamp(30px,5vw,48px);line-height:1.15;margin:12px 0 20px}
.eyebrow{color:#75ddcc;letter-spacing:.08em;font-size:13px}p{max-width:820px;color:#b6c6d9}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:16px;margin:32px 0}
.card{display:block;padding:22px;border:1px solid #36506d;border-radius:12px;background:#17253a;color:inherit;text-decoration:none}
.card:hover,.card:focus{border-color:#75ddcc;background:#1d3048}.card strong{font-size:19px}.card p{margin:12px 0}small{color:#8de0d1}
footer{border-top:1px solid #36506d;padding-top:20px;color:#b6c6d9;font-size:14px}a{color:#8de0d1}</style>
<main><div class="eyebrow">CAS-RPA / COMPOUND RUNTIME 0.5</div><h1>Inspect what actually happened.</h1>
<p>Ten saved views show one real symbolic procedure lifecycle. All 75 retained pause points pass semantic replay and projection checks. Open a view to inspect the same evidence as a graph or flower, expand dependencies, and page through construction candidates.</p>
<p>These offline views preserve the recorded state. Navigation does not run the machine. Source statements remain engineering fixtures; checked arithmetic is conditional on those statements.</p><div class="grid">''' + cards + '''</div>
<footer>Bounded evidence presentation; no measured reasoning or learning advantage. The complete CNCM charter remains open. <a href="receipt.json">Exact source and artifact receipt</a></footer></main></html>'''


def reproduce(output):
    output.mkdir(parents=True, exist_ok=False)
    profile, prior, old_sources = verify_previous_inputs()
    sources = [identity(ROOT / name, ROOT) for name in dict.fromkeys((*SOURCE_FILES, *VIEW_SOURCES))]
    genesis = CompoundProblem.from_dict(read(SOURCE / "genesis.json"))
    custody = read(SOURCE / "external_ingress.json")
    ingress = tuple(custody["initial_statement_digests"])
    extensions = tuple(tuple(row) for row in custody["extensions"])
    complete = read(SOURCE / "correction_journal.json")
    retained_cuts = {(r["episode"], r["cut"]): r for r in read(SOURCE / "all_cut_replay.json")["cuts"]}
    replay = CompoundMachine(profile, trusted_ingress=ingress)
    rows, examples, saved = [], [], set()
    for episode_index, episode in enumerate(complete["episodes"]):
        replay.start(CompoundProblem.from_dict(episode["problem"]),
            additional_trusted_ingress=() if episode_index == 0 else extensions[episode_index - 1])
        for cut in range(len(episode["trace"]) + 1):
            if cut:
                event = episode["trace"][cut - 1]
                outcome = replay.coordinator.execute(enabled_components=event["enabled_components"],
                    scheduled_components=event["scheduled_components"],
                    intents=_decode_proposal_batch(episode["proposal_batches"][cut - 1]))
                assert outcome.trace_event.to_dict() == event
            prefix = replay.journal()
            retained = retained_cuts[(episode_index, cut)]
            assert prefix["journal_digest"] == retained["prefix_digest"] and replay.state.state_hash == retained["state_hash"]
            view = project(prefix, genesis, ingress, retained["prefix_digest"], extensions[:episode_index], profile)
            rows.append({"episode": episode_index, "cut": cut, "prefix_digest": retained["prefix_digest"],
                "view_digest": digest(view), "current_state_hash": replay.state.state_hash,
                "frames": [f.kind for f in replay.state.rpm_stack], "remaining_policy_budget": replay.state.native_budget.to_dict()})
            name = None
            if episode_index == 0:
                if len(replay.state.rpm_stack) == 2 and not replay.state.procedure_heads:
                    name = "missing_primitive"
                elif replay.state.compound_head is None and any(r.kind == "CONSTRUCTION" for r in replay.state.compound_records):
                    name = "constructed_not_installed"
                elif replay.state.compound_head and replay.state.rpm_stack:
                    name = "installed_waiting_return"
                elif cut == len(episode["trace"]):
                    name = "checked_solution"
            elif cut == len(episode["trace"]):
                name = "source_correction"
            if name and name not in saved:
                save_view(output, name, view, examples)
                saved.add(name)
                if name == "checked_solution":
                    assert view["native"]["conditional_output"] == "3"
                    assert verify_pages(output, name, view) == 21
        print(canonical_json({"projected_episode": episode_index, "cuts_so_far": len(rows)}), flush=True)
    assert len(rows) == 34
    write(output / "all_cut_projection.json", {"cuts": rows, "all_retained_cuts_exact": True})
    failure_rows = []
    retained_failures = {(r["case"], r["cut"]): r for r in read(SOURCE / "failure_cut_replay.json")["cuts"]}
    for case, spec in read(SOURCE / "failure_inputs.json").items():
        packet = CompoundProblem.from_dict(spec["problem"])
        journal = read(SOURCE / (case + "_journal.json"))
        replay = CompoundMachine(profile, trusted_ingress=())
        replay.start(packet)
        episode = journal["episodes"][0]
        for cut in range(len(episode["trace"]) + 1):
            if cut:
                event = episode["trace"][cut - 1]
                outcome = replay.coordinator.execute(enabled_components=event["enabled_components"],
                    scheduled_components=event["scheduled_components"],
                    intents=_decode_proposal_batch(episode["proposal_batches"][cut - 1]))
                assert outcome.trace_event.to_dict() == event
            prefix = replay.journal()
            anchor = retained_failures[(case, cut)]["prefix_digest"]
            assert prefix["journal_digest"] == anchor
            view = project(prefix, packet, (), anchor, (), profile)
            failure_rows.append({"case": case, "cut": cut, "prefix_digest": anchor, "view_digest": digest(view),
                "current_state_hash": replay.state.state_hash, "remaining_policy_budget": replay.state.native_budget.to_dict()})
        assert replay.journal() == journal and view["native"]["current_call"]["failure"] == spec["failure"]
        if case in ("budget", "prefix"):
            name = "budget_exhausted" if case == "budget" else "search_exhausted"
            save_view(output, name, view, examples)
            if case == "prefix": verify_pages(output, name, view)
        print(canonical_json({"projected_failure": case, "cuts_so_far": len(failure_rows)}), flush=True)
    assert len(failure_rows) == 41
    write(output / "failure_cut_projection.json", {"cuts": failure_rows, "all_retained_cuts_exact": True})
    for stem, name, expected in (("reuse", "corrected_reuse", "3"),
                                  ("rollback_compound", "compound_rollback", None),
                                  ("rollback_primitive", "primitive_rollback", None)):
        journal = read(SOURCE / (stem + "_journal.json"))
        anchor = read(SOURCE / (stem + "_anchor.json"))["journal_digest"]
        view = project(journal, genesis, ingress, anchor, extensions, profile)
        assert view["native"]["conditional_output"] == expected
        if "rollback" in stem: assert not view["native"]["dispatch"]["eligible"]
        save_view(output, name, view, examples)
    assert len(examples) == 10
    assert {row["name"]: row["conditional_output"] for row in examples}["source_correction"] == "2"
    assert load_compound_profile().profile_digest == COMPOUND_PROFILE
    assert sources == [identity(ROOT / row["path"], ROOT) for row in sources], "sources changed during acceptance"
    verify_previous_inputs()
    write(output / "index.html", render_index(examples))
    files = [identity(path, output) for path in sorted(output.iterdir()) if path.is_file()]
    receipt = {"schema_version": "cncm.rpa-compound-receipt/0.1", "status": "REAL_COMPOUND_EVIDENCE_PROJECTED",
        "pid": os.getpid(), "runtime_source_profile_digest": COMPOUND_PROFILE,
        "prior_acceptance_receipt_sha256": PRIOR_RECEIPT_SHA256, "prior_manifest_files_verified": len(prior["files"]),
        "prior_rpa_receipt_sha256": PRIOR_RPA_RECEIPT_SHA256,
        "prior_rpa_sources_unchanged": old_sources, "sources": sources, "files": files, "examples": examples,
        "primary_cuts": len(rows), "failure_cuts": len(failure_rows), "all_retained_cuts": len(rows) + len(failure_rows),
        "kernel_state_writes_by_viewer": 0, "model_or_provider_work": False, "measured_performance_advantage": False,
        "full_goal_complete": False, "scope": "Replay-bound offline inspection of authored symbolic fixtures; no general learning or full CNCM acceptance."}
    write(output / "receipt.json", receipt)
    print(canonical_json({"status": receipt["status"], "cuts": 75, "examples": len(examples), "sources": len(sources)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    target = parser.parse_args().output.resolve()
    if not target.is_relative_to((ROOT / "records/rpa_compound_001").resolve()):
        raise SystemExit("output must stay in this homebase's rpa_compound_001 records")
    try:
        reproduce(target)
    except Exception:
        if target.is_dir() and not (target / "failure.txt").exists():
            write(target / "failure.txt", traceback.format_exc())
        raise
