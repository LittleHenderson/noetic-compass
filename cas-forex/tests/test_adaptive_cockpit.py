from cas_forex.adaptive_cockpit import (
    build_adaptive_cockpit_payload,
    write_adaptive_cockpit_html,
    write_adaptive_cockpit_payload,
)
from cas_forex.adaptive_compounding import append_adaptive_compounding_review, review_adaptive_compounding
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan

from tests.test_adaptive_compounding import _decision, _strong_tally, _winning_position


def test_adaptive_cockpit_writes_read_only_artifacts(tmp_path):
    plan = build_index_tsmom_126_paper_proof_plan()
    review = review_adaptive_compounding(
        plan,
        _decision(),
        active_positions=[_winning_position()],
        condition_tally=_strong_tally(),
    )
    append_adaptive_compounding_review(review, tmp_path)

    payload = build_adaptive_cockpit_payload(plan, tmp_path)
    json_path = write_adaptive_cockpit_payload(payload, tmp_path)
    html_path = write_adaptive_cockpit_html(payload, tmp_path)
    html = html_path.read_text(encoding="utf-8")

    assert json_path.exists()
    assert html_path.exists()
    assert payload["cockpit_status"] == "READ_ONLY_PAPER_RESEARCH"
    assert payload["adaptive_action_counts"] == {"ADD_TO_WINNER": 1}
    assert "ADD_TO_WINNER" in html
    assert "NOT LICENSED" in html

