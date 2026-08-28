"""The capability ladder: criterion execution tests."""

from cas_rr.benchmark import report_text, run_ladder, tier_of
from tasks.levels import LADDER


def test_core_levels_all_pass():
    results = run_ladder([s for s in LADDER if s["level"] != "L6"])
    assert len(results) == 9
    assert all(r.passed for r in results), [r.name for r in results if not r.passed]


def test_frontier_refusals_are_honest():
    results = run_ladder([s for s in LADDER if s["level"] == "L6"])
    refusals = [r for r in results if r.status == "NEEDS_INFORMATION"]
    assert len(refusals) == 4
    # A refusal is the CORRECT behavior here - graded as pass.
    assert all(r.passed for r in results)
    supported = [r for r in results
                 if r.name == "arithmetic (comparison as data)"]
    assert supported and supported[0].output == "taller(ada,bo)"


def test_tier_is_r3_not_r4():
    # L6 refusals are honesty, not attained capability: tier must be R3.
    results = run_ladder(LADDER)
    assert tier_of(results) == "R3"


def test_report_text_contains_tier_and_counts():
    text = report_text(run_ladder(LADDER))
    assert "capability tier: R3" in text
    assert "core levels:     9/9 passed" in text
    assert "refused honestly" in text


def test_depth2_recursion_in_ladder():
    results = run_ladder([s for s in LADDER
                          if s["name"] == "recursive planning (depth 2)"])
    assert results[0].passed
    assert results[0].ticks == 7


def test_cli_report(capsys):
    from run import main
    assert main(["report"]) == 0
    out = capsys.readouterr().out
    assert "capability tier: R3" in out
