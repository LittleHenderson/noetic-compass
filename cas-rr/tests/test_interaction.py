"""CLI and reporting layer tests - how a human drives the machine."""

import json

from cas_rr.report import battery_table, determinism_check, summarize, trace_compact
from cas_rr.runtime import CASRuntime
from run import main
from tasks import battery


def _packet(name):
    return CASRuntime(battery.constitution_for(name), battery.BATTERY[name]()).run()


def test_summarize_transitive():
    text = summarize(_packet("transitive"))
    assert "CONCLUDED" in text
    assert "precedes(a,c)" in text
    assert "r_trans" in text


def test_summarize_recursive_plan_tells_the_story():
    text = summarize(_packet("recursive_plan"))
    assert "descend  KNOWLEDGE" in text
    assert "descend  CAPABILITY" in text
    assert "resolve" in text
    assert "cached=False" in text  # parent re-measured after each resolution


def test_trace_compact_shows_every_phase():
    text = trace_compact(_packet("transitive"))
    for kind in ("POWER", "GOAL_ACTIVE", "BUDGET", "RETRIEVED", "GENERATED",
                 "DECOMPOSED", "INFERRED", "TOURNAMENT", "SCAN", "DECISION",
                 "OUTPUT", "DISPOSITION", "CONCLUDED"):
        assert kind in text, kind


def test_battery_table_lists_all_tasks():
    results = {name: _packet(name) for name in battery.BATTERY}
    table = battery_table(results)
    for name in battery.BATTERY:
        assert name in table
    assert len(table.splitlines()) == len(battery.BATTERY) + 1


def test_determinism_check_all_tasks():
    for name in battery.BATTERY:
        ok, detail = determinism_check(battery.BATTERY[name],
                                       battery.constitution_for(name))
        assert ok, f"{name}: {detail}"


def test_cli_list(capsys):
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "transitive" in out and "contradiction" in out


def test_cli_run(capsys):
    assert main(["run", "transitive"]) == 0
    out = capsys.readouterr().out
    assert "CONCLUDED" in out and "precedes(a,c)" in out


def test_cli_run_with_trace(capsys):
    assert main(["run", "fault", "--trace"]) == 0
    out = capsys.readouterr().out
    assert "first_bad(S3)" in out and "--- trace ---" in out


def test_cli_run_writes_json(tmp_path):
    target = tmp_path / "packet.json"
    assert main(["run", "transitive", "--json", str(target)]) == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["terminal_status"] == "CONCLUDED"
    assert data["output"]["conclusion"] == "precedes(a,c)"


def test_cli_demo(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "recursive_plan" in out and "NEEDS_INFORMATION" in out


def test_cli_check(capsys):
    assert main(["check"]) == 0
    out = capsys.readouterr().out
    assert out.count("OK ") == len(battery.BATTERY)


def test_cli_unknown_task_fails_cleanly():
    import pytest
    with pytest.raises(KeyError):
        main(["run", "not_a_task"])
