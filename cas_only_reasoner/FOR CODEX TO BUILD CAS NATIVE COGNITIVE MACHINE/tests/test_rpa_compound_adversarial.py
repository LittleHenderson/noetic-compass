"""Independent read-only compound atlas attacks and equal-information traversal.

Actual-source acceptance fixtures are replayed once per selected view. Cheap
navigation/page mutations reuse those views. Forged journal tests still invoke
the real recovery boundary. These tests assert no human/performance advantage.
"""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from cncm.canonical import canonical_json, digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_kernel import compound_intent
from cncm.compound_model import CompoundIntentType as C, CompoundProblem, create_problem
from cncm.compound_profile import load_compound_profile
from cncm.model import ContractError, TerminalStatus
from cncm.procedural_substrate import make_candidate
from cncm.rpa_model import AtlasSnapshot, LinkType, NodeStatus
from cncm.rpa_compound_adapter import (compound_atlas_from_journal, candidate_page,
                                      record_body_from_catalog, validate_evidence_catalog)
from cncm.semantic_model import MemoryRef


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE = ROOT / "records/compound_procedure_001/acceptance_001"
PROFILE_DIGEST = "3a7c6f620782ce820145d5e119d8f64c2050008378a9fbfdf94adbd1a9dcfed5"


def read(name):
    return json.loads((ACCEPTANCE / name).read_text(encoding="utf-8"))


def reseal(journal):
    journal["journal_digest"] = digest({key: value for key, value in journal.items() if key != "journal_digest"})
    return journal


@pytest.fixture(scope="module")
def source_context():
    profile = load_compound_profile()
    assert profile.profile_digest == PROFILE_DIGEST == read("receipt.json")["source_profile_digest"]
    ingress = read("external_ingress.json")
    old_rpa = json.loads((ROOT / "records/rpa_001/demo2/receipt.json").read_text())
    pinned = {row["path"]: row["sha256"] for row in old_rpa["sources"]}
    pinned.update({name: checksum for name, _, checksum in profile.source_files})
    yield {
        "profile": profile,
        "genesis": CompoundProblem.from_dict(read("genesis.json")),
        "ingress": tuple(ingress["initial_statement_digests"]),
        "extensions": tuple(tuple(row) for row in ingress["extensions"]),
    }
    assert all(sha256((ROOT / name).read_bytes()).hexdigest() == checksum for name, checksum in pinned.items()), (
        "an old RPA or accepted runtime source changed")


def project(journal, context, *, genesis=None, ingress=None, extensions=(), anchor=None, profile=None):
    return compound_atlas_from_journal(journal,
        trusted_genesis=context["genesis"] if genesis is None else genesis,
        trusted_ingress=context["ingress"] if ingress is None else ingress,
        expected_journal_digest=journal["journal_digest"] if anchor is None else anchor,
        trusted_ingress_extensions=extensions,
        profile=context["profile"] if profile is None else profile)


@pytest.fixture(scope="module")
def views(source_context):
    cache = {}

    def get(stem):
        if stem not in cache:
            journal = read(stem + "_journal.json")
            is_main = stem in {"baseline", "correction", "reuse", "rollback_compound", "rollback_primitive"}
            packet = source_context["genesis"] if is_main else CompoundProblem.from_dict(journal["episodes"][0]["problem"])
            ingress = source_context["ingress"] if is_main else ()
            extensions = source_context["extensions"] if is_main and stem != "baseline" else ()
            before = canonical_json(journal)
            view = project(journal, source_context, genesis=packet, ingress=ingress, extensions=extensions)
            assert canonical_json(journal) == before, "projection mutated its caller's source journal"
            cache[stem] = (journal, view)
        return cache[stem]

    return get


def atlas(view):
    return AtlasSnapshot.from_dict(view["atlas"])


def reference_bfs(wire, *, root, depth_limit, node_limit, relations):
    """Ordinary graph walk over wire IDs, independently of AtlasSnapshot.expand."""
    by_id = {row["node_id"]: row for row in wire["nodes"]}
    edges = {key: [] for key in by_id}
    for edge in sorted(wire["links"], key=lambda row: row["link_id"]):
        if edge["relation"] in relations:
            edges[edge["source_id"]].append(edge)
    frontier = [(root, 0)]
    visited, seen, traversed, revisited, deferred = [root], {root}, [], [], []
    offset = 0
    while offset < len(frontier):
        source, depth = frontier[offset]
        offset += 1
        pending_generator = by_id[source]["expansion_ref"]
        if pending_generator is not None:
            deferred.append(dict(source_id=source, link_id=None, target_id=None,
                                 reason="generator_not_expanded", expansion_ref=pending_generator))
        for edge in edges[source]:
            target, edge_id = edge["target_id"], edge["link_id"]
            if target in seen:
                traversed.append(edge_id)
                revisited.append(edge_id)
            elif depth == depth_limit or len(visited) == node_limit:
                deferred.append(dict(source_id=source, link_id=edge_id, target_id=target,
                                     reason="max_depth" if depth == depth_limit else "max_nodes", expansion_ref=None))
            else:
                seen.add(target)
                visited.append(target)
                traversed.append(edge_id)
                frontier.append((target, depth + 1))
    return visited, traversed, revisited, deferred


@pytest.mark.parametrize("depth,node_limit", [(0, 1), (1, 2), (2, 7), (3, 20), (8, 100), (32, 512)])
@pytest.mark.parametrize("relations", [tuple(LinkType), (LinkType.CONTAINS_PART,), (LinkType.REACHABLE_VIA,)])
def test_flat_graph_and_typed_atlas_traversal_match_independent_bfs(views, depth, node_limit, relations):
    _, view = views("baseline")
    snapshot = atlas(view)
    wire = snapshot.flat_graph()
    assert wire == snapshot.to_dict() == view["atlas"]
    expected = reference_bfs(wire, root=snapshot.focus_node_id, depth_limit=depth, node_limit=node_limit,
                             relations={value.value for value in relations})
    result = snapshot.expand(max_depth=depth, max_nodes=node_limit, relations=relations).to_dict()
    assert (result["visited_node_ids"], result["traversed_link_ids"], result["revisited_link_ids"], result["deferred"]) == expected
    assert result["nodes_used"] <= node_limit and result["visited_node_ids"][0] == snapshot.focus_node_id


def test_focus_and_hypothesis_only_change_view_handles(views):
    source, view = views("baseline")
    original_source, original_view = canonical_json(source), canonical_json(view)
    snapshot = atlas(view)
    source_hash, present = source["episodes"][-1]["final_state"]["state_hash"], snapshot.current_state_id
    for selected in snapshot.nodes[:10]:
        moved = snapshot.focus(selected.node_id).with_hypothesis(None)
        assert moved.nodes == snapshot.nodes and moved.links == snapshot.links
        assert moved.current_state_id == present
        assert view["native"]["current_state_hash"] == source_hash
    assert canonical_json(view) == original_view and canonical_json(source) == original_source
    assert all(node.profile40 is None and node.profile_basis is None for node in snapshot.nodes)
    assert all(action["authority"] == "PROPOSAL_ONLY" for action in view["next_actions"])


@pytest.mark.parametrize("attack", ["external_anchor", "genesis", "initial_ingress", "source_profile", "journal_profile", "truncation"])
def test_external_replay_anchors_cannot_be_supplied_by_untrusted_journal(source_context, attack):
    journal = read("baseline_journal.json")
    kw = {}
    if attack == "external_anchor": kw["anchor"] = "0" * 64
    elif attack == "genesis":
        genesis = source_context["genesis"]
        kw["genesis"] = replace(genesis, reasoning=replace(genesis.reasoning, problem_id="foreign-genesis"))
    elif attack == "initial_ingress": kw["ingress"] = ()
    elif attack == "source_profile":
        profile = source_context["profile"]
        rows = list(profile.source_files)
        rows[0] = (rows[0][0], rows[0][1], "0" * 64)
        kw["profile"] = replace(profile, source_files=tuple(rows))
    elif attack == "journal_profile":
        journal["source_profile"]["source_files"][0]["sha256"] = "0" * 64
        reseal(journal)
    else:
        journal["episodes"][0]["trace"].pop()
        journal["episodes"][0]["proposal_batches"].pop()
        # Keep the independently supplied complete anchor, despite resealing.
        kw["anchor"] = journal["journal_digest"]
        reseal(journal)
    with pytest.raises(ContractError):
        project(journal, source_context, **kw)


def test_final_ingress_union_does_not_replace_external_chronology(source_context):
    journal = read("correction_journal.json")
    final = source_context["ingress"] + source_context["extensions"][0]
    with pytest.raises(ContractError):
        project(journal, source_context, ingress=final)
    with pytest.raises(ContractError):
        project(journal, source_context, extensions=())


@pytest.mark.parametrize("attack", ["fake_terminal", "fake_output", "wrong_budget", "fake_proof", "wrong_proposal"])
def test_resealed_false_journal_still_fails_actual_semantic_replay(source_context, attack):
    # A small real domain-refusal journal tests semantics without repeating420.
    journal = read("domain_journal.json")
    genesis = CompoundProblem.from_dict(journal["episodes"][0]["problem"])
    episode = journal["episodes"][0]
    state = episode["final_state"]
    if attack == "fake_terminal": state["halt_status"] = "CONCLUDED"
    elif attack == "fake_output": state["compound_call"]["output"] = "3"
    elif attack == "wrong_budget": state["native_budget"]["instructions_remaining"] += 1
    elif attack == "fake_proof": state["branch_table"][0]["proof_steps"] = [{"operation": "NATIVE_PROCEDURE_CHECKED"}]
    else: episode["proposal_batches"][0][0]["intent"]["issuer_subsystem"] = "untrusted-viewer"
    if attack != "wrong_proposal":
        # Reseal the state and final event as well as the outer journal. A
        # self-consistent hash chain still cannot replace semantic execution.
        state["state_hash"] = digest({key: value for key, value in state.items() if key not in {"state_hash", "trace_head"}})
        last = episode["trace"][-1]
        last["post_state_hash"] = state["state_hash"]
        last["terminal_status"] = state["halt_status"]
        last["event_hash"] = digest({key: value for key, value in last.items() if key != "event_hash"})
        state["trace_head"] = last["event_hash"]
    reseal(journal)
    with pytest.raises(ContractError):
        project(journal, source_context, genesis=genesis, ingress=())


def send(machine, proposal, *, repeats=1):
    return machine.coordinator.execute(enabled_components=(proposal.issuer_subsystem,),
        scheduled_components=(proposal.issuer_subsystem,), intents=(proposal,) * repeats)


def primitive_stage(context, name):
    packet = create_problem(dict(a="2", b="3", c="5", d="7", e="35"), problem_id=name)
    machine = CompoundMachine(context["profile"], trusted_ingress=())
    machine.start(packet)
    for _ in range(12):
        proposal = machine.coordinator.next_intent()
        if proposal is not None and proposal.intent_type is C.SELECT_PRIMITIVE:
            return machine, packet, proposal
        machine.advance()
    pytest.fail("primitive acquisition stage not reached")


@pytest.fixture(scope="module")
def duplicate_view(source_context):
    machine, packet, proposal = primitive_stage(source_context, "duplicate-work-atlas")
    first = send(machine, proposal)
    assert not first.rejected_intents
    budget = machine.state.native_budget
    second = send(machine, proposal, repeats=2)
    assert second.rejected_intents and machine.state.native_budget == budget
    journal = machine.journal()
    view = project(journal, source_context, genesis=packet, ingress=())
    return machine, journal, view, first.trace_event.event_hash, second.trace_event.event_hash


def test_stale_duplicate_proposal_does_not_reuse_previous_work_charge(duplicate_view):
    machine, journal, view, accepted_hash, duplicate_hash = duplicate_view
    timeline = {row["event"]["event_hash"]: row for row in view["timeline"]}
    assert timeline[accepted_hash]["work"]["instructions_allocated"] == 144
    assert timeline[accepted_hash]["work"]["checker_calls_allocated"] == 24
    assert timeline[duplicate_hash]["work"]["instructions_allocated"] == 0
    assert timeline[duplicate_hash]["work"]["checker_calls_allocated"] == 0
    assert timeline[duplicate_hash]["event"]["rejected_intents"]
    assert len(journal["episodes"][0]["proposal_batches"][-1]) == 2
    assert view["native"]["current_state_hash"] == machine.state.state_hash


def test_semantically_rejected_install_retains_its_one_real_charge(source_context):
    machine, packet, _ = primitive_stage(source_context, "charged-refusal-atlas")
    before = machine.state.native_budget
    proposal = compound_intent(machine.coordinator, C.INSTALL_PRIMITIVE,
        dict(call_id=machine.state.compound_call.call_id, artifact=make_candidate().to_dict(), qualification_digest=None))
    outcome = send(machine, proposal)
    assert outcome.rejected_intents
    assert before.instructions_remaining - machine.state.native_budget.instructions_remaining == 60
    assert before.checker_calls_remaining - machine.state.native_budget.checker_calls_remaining == 10
    view = project(machine.journal(), source_context, genesis=packet, ingress=())
    event = next(row for row in view["timeline"] if row["event"]["event_hash"] == outcome.trace_event.event_hash)
    assert event["event"]["rejected_intents"] and not event["event"]["authorized_intent_ids"]
    assert event["work"]["instructions_allocated"] == 60 and event["work"]["checker_calls_allocated"] == 10


@pytest.mark.parametrize("stem", ["baseline", "reuse", "rollback_primitive", "prefix"])
def test_timeline_work_equals_unique_physical_reservations_and_each_episode_budget(views, stem):
    journal, view = views(stem)
    reservations = {}
    for episode in journal["episodes"]:
        state = episode["final_state"]
        for field in ("native_records", "semantic_records", "compound_records"):
            for record in state[field]:
                if record["kind"] == "WORK_RESERVATION":
                    reservations[record["record_digest"]] = json.loads(record["body_json"])
    timeline = {row["event"]["event_hash"]: row for row in view["timeline"]}
    assert len(timeline) == sum(len(episode["trace"]) for episode in journal["episodes"])
    for episode in journal["episodes"]:
        spent_instructions = spent_checks = 0
        for event in episode["trace"]:
            proposed_ids = {row["intent_id"] for row in event["proposed_intents"]}
            matches = [body for body in reservations.values()
                       if body["run_id"] == event["run_id"]
                       and body["tick"] + 1 == event["logical_tick"]
                       and body["intent_id"] in proposed_ids]
            instructions = sum(row["instructions_allocated"] for row in matches)
            checks = sum(row["checker_calls_allocated"] for row in matches)
            shown = timeline[event["event_hash"]]
            assert shown["work"]["instructions_allocated"] == instructions
            assert shown["work"]["checker_calls_allocated"] == checks
            assert shown["event"]["authorized_intent_ids"] == event["authorized_intent_ids"]
            assert shown["event"]["rejected_intents"] == event["rejected_intents"]
            spent_instructions += instructions
            spent_checks += checks
        initial, final = episode["problem"]["budget"], episode["final_state"]["native_budget"]
        assert spent_instructions == initial["instructions_remaining"] - final["instructions_remaining"]
        assert spent_checks == initial["checker_calls_remaining"] - final["checker_calls_remaining"]


def construction_record(view):
    report = view["native"]["candidate_reports"][0]
    return report["record_digests"][0]


def test_catalog_reconstructs_every_complete_retained_record_without_copy_loss(views):
    journal, view = views("baseline")
    catalog = view["native"]["evidence_catalog"]
    state = journal["episodes"][-1]["final_state"]
    physical = {row["record_digest"]: row for field in ("native_records", "semantic_records", "compound_records")
                for row in state[field]}
    assert {row["record_digest"] for row in catalog["records"]} == set(physical)
    for key, row in physical.items():
        assert record_body_from_catalog(catalog, key) == json.loads(row["body_json"])
    report_ids = [row["report_digest"] for row in catalog["reports"]]
    assert len(report_ids) == len(set(report_ids))
    construction = view["native"]["candidate_reports"][0]
    assert len(construction["record_digests"]) >= 2, "reservation and construction share one sealed report"
    assert report_ids.count(construction["report_digest"]) == 1


def test_all420_candidate_pages_preserve_exact_programs_checks_indices_and_deferred_ranges(views):
    _, view = views("baseline")
    key = construction_record(view)
    original = canonical_json(view)
    expected = read("construction_report.json")["candidates"]
    page = candidate_page(view, key)
    observed = []
    while True:
        assert page["total"] == 420 and page["count"] == 20 and page["returned"] <= 20
        assert page["deferred"] == {"before": [0, page["start"]], "after": [page["start"] + page["returned"], 420]}
        assert page["journal_digest"] == view["native"]["journal_digest"]
        for item in page["items"]:
            assert item["candidate"] == expected[item["index"]]
            observed.append(item["index"])
        if page["next_cursor"] is None:
            break
        page = candidate_page(view, key, cursor=page["next_cursor"])
    assert observed == list(range(420))
    end = candidate_page(view, key, start=420)
    assert end["items"] == [] and end["returned"] == 0 and end["next_cursor"] is None
    assert canonical_json(view) == original


@pytest.mark.parametrize("options", [dict(start=-1), dict(start=421), dict(start=True), dict(start=False),
    dict(start=20.0), dict(count=0), dict(count=21), dict(count=True), dict(count=1.0), dict(start="0")])
def test_display_page_bounds_and_types_are_exact(views, options):
    _, view = views("baseline")
    with pytest.raises(ContractError):
        candidate_page(view, construction_record(view), **options)


@pytest.mark.parametrize("options", [dict(start=20.0), dict(count=20.0)])
def test_explicit_cursor_arguments_cannot_coerce_float_aliases(views, options):
    _, view = views("baseline")
    key = construction_record(view)
    cursor = candidate_page(view, key)["next_cursor"]
    with pytest.raises(ContractError):
        candidate_page(view, key, cursor=cursor, **options)


@pytest.mark.parametrize("field", ["journal_digest", "catalog_digest", "record_digest", "report_digest", "total", "schema_version"])
def test_even_resealed_foreign_cursor_bindings_are_rejected(views, field):
    _, view = views("baseline")
    key = construction_record(view)
    cursor = candidate_page(view, key)["next_cursor"]
    cursor[field] = 419 if field == "total" else "foreign-version" if field == "schema_version" else "0" * 64
    cursor["cursor_digest"] = digest({k: v for k, v in cursor.items() if k != "cursor_digest"})
    with pytest.raises(ContractError):
        candidate_page(view, key, cursor=cursor)


@pytest.mark.parametrize("field", ["start", "count", "total"])
@pytest.mark.parametrize("reseal_cursor", [False, True])
def test_cursor_numeric_fields_reject_equal_float_aliases(views, field, reseal_cursor):
    _, view = views("baseline")
    key = construction_record(view)
    cursor = candidate_page(view, key)["next_cursor"]
    cursor[field] = float(cursor[field])
    if reseal_cursor:
        cursor["cursor_digest"] = digest({k: v for k, v in cursor.items() if k != "cursor_digest"})
    with pytest.raises(ContractError):
        candidate_page(view, key, cursor=cursor)


def test_cursor_for_prior_journal_cannot_be_applied_to_later_retained_same_record(views):
    _, baseline = views("baseline")
    _, later = views("reuse")
    key = construction_record(baseline)
    cursor = candidate_page(baseline, key)["next_cursor"]
    assert any(row["record_digest"] == key for row in later["native"]["evidence_catalog"]["records"])
    with pytest.raises(ContractError): candidate_page(later, key, cursor=cursor)
    with pytest.raises(ContractError): candidate_page(baseline, key, cursor=cursor, start=40)
    with pytest.raises(ContractError): candidate_page(baseline, key, cursor=cursor, count=10)


@pytest.mark.parametrize("attack", ["report_body", "record_body", "duplicate_record", "duplicate_report", "foreign_report_ref", "non_json"])
def test_catalog_resealing_does_not_hide_changed_nested_content(views, attack):
    _, view = views("baseline")
    catalog = deepcopy(view["native"]["evidence_catalog"])
    if attack == "report_body": catalog["reports"][0]["body"]["status"] = "FORGED_SUCCESS"
    elif attack == "record_body": catalog["records"][0]["body"]["tick"] += 1
    elif attack == "duplicate_record": catalog["records"].append(deepcopy(catalog["records"][0]))
    elif attack == "duplicate_report": catalog["reports"].append(deepcopy(catalog["reports"][0]))
    elif attack == "foreign_report_ref":
        row = next(row for row in catalog["records"] if row["report_refs"])
        row["report_refs"][0]["report_digest"] = "0" * 64
    else: catalog["reports"][0]["body"]["numeric_float"] = 1.0
    catalog["catalog_digest"] = digest({k: v for k, v in catalog.items() if k != "catalog_digest"})
    with pytest.raises(ContractError): validate_evidence_catalog(catalog)


def test_catalog_and_page_returned_objects_cannot_write_through_to_source_view(views):
    source, view = views("baseline")
    before_view, before_source = canonical_json(view), canonical_json(source)
    key = construction_record(view)
    page = candidate_page(view, key)
    page["items"][0]["candidate"]["program"]["steps"][0]["a_ref"] = "evil"
    body = record_body_from_catalog(view["native"]["evidence_catalog"], key)
    body["report"]["status"] = "FORGED_SUCCESS"
    copied = validate_evidence_catalog(view["native"]["evidence_catalog"])
    copied["records"][0]["body"]["tick"] = -1
    assert canonical_json(view) == before_view and canonical_json(source) == before_source


def test_catalog_size_boundary_refuses_expansion_without_silent_truncation(views, monkeypatch):
    import cncm.rpa_compound_adapter as adapter
    _, view = views("baseline")
    catalog = view["native"]["evidence_catalog"]
    before = canonical_json(catalog)
    assert adapter.MAX_VIEW_BYTES == 32 * 1024 * 1024
    # Exercise the exact size guard with a deliberately smaller test policy;
    # avoid allocating a gratuitous32MiB attack string for every test run.
    monkeypatch.setattr(adapter, "MAX_VIEW_BYTES", 1024)
    with pytest.raises(ContractError, match="limit"):
        validate_evidence_catalog(catalog)
    assert canonical_json(catalog) == before


def test_current_arithmetic_and_memory_evidence_remain_distinct_conditional_claims(views):
    journal, view = views("reuse")
    native = view["native"]
    state = journal["episodes"][-1]["final_state"]
    assert native["conditional_output"] == "3" and native["terminal_status"] == "CONCLUDED"
    assert native["source_bindings"] == state["memory_bindings"]
    assert native["claim_status"] == "CONDITIONAL_ON_RECORDED_SOURCE_BINDINGS"
    assert native["authority"] == "DISPLAY_ONLY"
    assert all(label == "TEST_FIXTURE" for binding in native["source_bindings"] for label in binding["statuses"])
    source_nodes = [node for node in atlas(view).nodes if node.node_id.startswith("source-")]
    assert source_nodes
    for node in source_nodes:
        assert node.status is not NodeStatus.VERIFIED
        assert dict(node.fields)["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED"
    heads = native["source_heads"]
    assert len(heads) == 1 and heads[0]["value"] == "8", "later current head retains corrected source value"


def test_retained_compound_and_primitive_bytes_do_not_grant_dispatch_after_primitive_rollback(views):
    journal, view = views("rollback_primitive")
    state, native = journal["episodes"][-1]["final_state"], view["native"]
    assert state["compound_head"] is not None and state["compound_artifacts"] and state["procedural_artifacts"]
    assert not state["procedure_heads"]
    dispatch = native["dispatch"]
    assert dispatch["program_present"] and dispatch["primitive_present"]
    assert dispatch["compound_head"] == state["compound_head"] and dispatch["primitive_head"] is None
    assert dispatch["eligible"] is False and dispatch["pin_matches_current_head"] is False
    assert "NO_ACTIVE_PRIMITIVE_HEAD" in dispatch["blockers"]
    assert "PINNED_PRIMITIVE_NOT_AUTHORIZED" in dispatch["blockers"]
    assert native["conditional_output"] is None and native["terminal_status"] == "NEEDS_CAPABILITY"


def test_search_prefix_exhaustion_is_not_recast_as_all_candidates_impossible(views):
    _, view = views("prefix")
    key = construction_record(view)
    report = record_body_from_catalog(view["native"]["evidence_catalog"], key)["report"]
    assert report["candidate_limit"] == report["candidate_count"] == 1
    assert report["status"] == "SEARCH_EXHAUSTED" and report["selected_artifact"] is None
    page = candidate_page(view, key)
    assert page["total"] == page["returned"] == 1
    assert view["native"]["conditional_output"] is None


def test_stronger_fact_requirement_remains_unmet_in_the_atlas(source_context):
    statement = source_context["genesis"].updates[0]
    packet = create_problem(dict(a="2", b="3",
        c=MemoryRef(statement.scope, statement.key, "INDEPENDENTLY_VERIFIED"), d="7", e="35"),
        updates=(statement,), problem_id="atlas-stronger-fact-demand")
    machine = CompoundMachine(source_context["profile"], trusted_ingress=(statement.statement_digest,))
    result = machine.run(packet)
    assert machine.state.memory_failure == "INSUFFICIENT_EVIDENCE"
    view = project(machine.journal(), source_context, genesis=packet, ingress=(statement.statement_digest,))
    assert view["native"]["conditional_output"] is None and not view["native"]["source_bindings"]
    assert view["native"]["terminal_status"] != "CONCLUDED"
    receipts = [row["body"] for row in view["native"]["evidence_catalog"]["reports"]]
    refused = [row for row in receipts if row.get("reason") == "INSUFFICIENT_EVIDENCE"]
    assert refused and all(row["factual_status"] == "NOT_INDEPENDENTLY_VERIFIED" for row in refused)
