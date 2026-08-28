"""The workbench conformance plan: real data, real panes, determinism."""

import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from workbench.generate import build_bundle, render_html

PANE_IDS = [
    "pane-dialogue", "pane-goal", "pane-board", "pane-branch",
    "pane-rpm", "pane-memory", "pane-truth", "pane-trace",
    "pane-learning", "pane-evolution", "pane-organs",
]


def _bundle():
    return build_bundle()


def test_all_panes_present_and_nonempty():
    bundle = _bundle()
    for pane_id in ("dialogue", "goal_map", "live_board", "branch_tree",
                    "rpm_stack", "memory", "truth", "trace", "learning",
                    "evolution"):
        assert pane_id in bundle["panes"], pane_id
        assert bundle["panes"][pane_id], pane_id


def test_trace_hashes_chain():
    rows = _bundle()["panes"]["trace"]["rows"]
    assert len(rows) >= 3
    for prev, nxt in zip(rows, rows[1:]):
        assert prev["post_state_hash"] == nxt["pre_state_hash"]
        assert prev["pre_state_hash"], "empty pre hash"
        assert prev["post_state_hash"], "empty post hash"


def test_branch_tree_has_candidates_and_winner_proof():
    tree = _bundle()["panes"]["branch_tree"]
    assert len(tree["candidates"]) >= 2
    winner = tree["winner"]
    assert winner is not None
    winner_cand = [c for c in tree["candidates"]
                   if c["inference"].get("conclusion") == winner]
    assert winner_cand, "winner candidate missing from tree"
    assert winner_cand[0]["inference"]["success"] is True
    assert winner_cand[0]["inference"]["rules_used"]


def test_rpm_pane_shows_push_and_return():
    transitions = _bundle()["panes"]["rpm_stack"]["transitions"]
    kinds = [t["kind"] for t in transitions]
    assert "push_rpm" in kinds and "return_rpm" in kinds


def test_truth_pane_has_verified_and_rejected():
    truth = _bundle()["panes"]["truth"]
    statuses = [c["truth"] for c in truth["semantic_claims"]]
    assert "VERIFIED" in statuses
    assert truth["math"]["attempt"]["verdict"] == "REJECTED"
    assert truth["math"]["corrected_verdict"] == "VERIFIED"


def test_evolution_has_promoted_and_rejected():
    strategies = _bundle()["panes"]["evolution"]["strategies"]
    verdicts = [s["verdict"] for s in strategies]
    assert "PROMOTED" in verdicts and "REJECTED" in verdicts
    assert _bundle()["panes"]["evolution"]["promoted_strategy"]


def test_memory_pane_has_records_and_lacunae():
    memory = _bundle()["panes"]["memory"]
    assert memory["records"], "no memory records"
    assert memory["lacunae"], "no typed lacunae"


def test_dialogue_pane_has_kernel_statuses():
    questions = _bundle()["panes"]["dialogue"]["questions"]
    assert questions
    statuses = {q["kernel_status"] for q in questions}
    assert "CONCLUDED" in statuses
    assert "NEEDS_INFORMATION" in statuses


def test_bundle_is_deterministic():
    a = _bundle()
    b = _bundle()
    assert a["digest"] == b["digest"]
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_organ_summary_totals():
    bundle = _bundle()
    assert sum(o["tests"] for o in bundle["organs"]) == bundle["program_tests"]
    assert bundle["program_tests"] == 158


def test_html_contains_all_panes_and_inline_data():
    html = render_html(_bundle())
    for pane_id in PANE_IDS:
        assert pane_id in html
    assert "const WORKBENCH_DATA" in html
    assert "{{" not in html
    assert html.count("</script>") >= 2


def test_app_js_passes_node_syntax_check(tmp_path):
    app_js = os.path.join(ROOT, "workbench", "app.js")
    result = subprocess.run(["node", "--check", app_js],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


def test_generate_main_writes_bundle(tmp_path):
    from workbench.generate import main
    main(out_dir=str(tmp_path))
    data_path = tmp_path / "workbench_data.json"
    html_path = tmp_path / "glass_brain.html"
    assert data_path.exists() and html_path.exists()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    assert data["digest"] == _bundle()["digest"]
    digest = hashlib.sha256(html_path.read_bytes()).hexdigest()[:16]
    assert digest, "html bundle produced"
