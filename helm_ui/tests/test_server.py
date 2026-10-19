"""HELM UI v0 server tests: endpoints answer, the turn path round-trips a stock statement, and nothing writes to
HELM's state except the turn path. Run:  python -m pytest helm_ui/tests -q"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

UI_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(UI_DIR))
import server  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

STOCK = "We have 12 cups of flour and 9 cups of water."
CYCLE = "Ω_a needs Ω_b first. Ω_b needs Ω_a first."


@pytest.fixture()
def rig(tmp_path):
    bridge = server.HelmBridge(session_dir=str(tmp_path / "sessions"), allow_tools=False)
    if bridge.session is None:
        pytest.skip("HELM chat did not load here: " + bridge.wiring.get("chat", ""))
    return bridge, TestClient(server.create_app(bridge)), tmp_path


def snapshot(bridge):
    s = bridge.session
    brain = s.loop.brain
    return json.dumps({
        "turns": len(s.memory.turns),
        "store_writes": len(s.loop.cube_store.write_history) if s.loop.cube_store is not None else None,
        "stock": {k: str(v) for k, v in s.loop.stock.items()},
        "absent": sorted(s.loop.declared_absent),
        "recipes": {p: brain.requirements(p) for p in brain.products},
        "facts": list(s.memory.context.user_facts),
        "trace": len(s.loop.trace),
        "turn_count": s.turn_count,
    }, sort_keys=True, default=str)


def test_index_and_static_answer(rig):
    _, c, _ = rig
    assert c.get("/").status_code == 200
    for f in ("app.js", "styles.css"):
        assert c.get(f"/static/{f}").status_code == 200


def test_state_answers_and_is_honest(rig):
    _, c, _ = rig
    st = c.get("/state").json()
    assert st["wiring"]["chat"] == "wired"
    assert st["wiring"]["tools"] == "off in this window"
    assert st["wiring"]["eye_live_session"].startswith("not wired")
    assert st["knows"]["stock"] == [] and st["knows"]["your_facts"] == []
    assert {r["product"] for r in st["knows"]["recipes"]} >= {"Bread"}
    marks = {c_["mark"] for c_ in st["claims"]}
    assert marks <= set(server.MARK.values())
    assert "✅" not in marks          # nothing on screen has earned a confirmed-win marker
    assert any(c_["word"] == "NOT WIRED" for c_ in st["claims"])


def test_turn_round_trips_one_stock_statement(rig):
    bridge, c, tmp = rig
    r = c.post("/turn", json={"text": STOCK}).json()
    assert r["ok"] and r["recorded"]
    rec = r["record"]
    assert rec["status_word"] == "INVENTORY_RECORDED"
    assert rec["status_plain"] == "Stock noted"
    assert "item_flour" in rec["cubes_written"] and "item_water" in rec["cubes_written"]
    assert rec["loop"]["checked_form"] == "There is 12 of Ω_Flour. There is 9 of Ω_Water."
    assert rec["loop"]["receipt_hash"] == rec["receipt_hash"]
    assert rec["loop"]["rpm_gate"]["code"] == "NOTHING_BLOCKED"
    assert "12 cups of flour" in r["reply"]
    stock = {s["name"]: s for s in c.get("/state").json()["knows"]["stock"]}
    assert stock["Flour"]["amount"] == "12" and stock["Water"]["amount"] == "9"
    assert stock["Flour"]["unit"] == "cups"
    hist = c.get("/history").json()
    assert len(hist) == 1 and hist[0]["you_said"] == STOCK and hist[0]["record"]["receipt_hash"] == rec["receipt_hash"]
    logs = list((tmp / "sessions").glob("*.jsonl"))       # the session log went to the given folder only
    assert len(logs) == 1 and STOCK in logs[0].read_text(encoding="utf-8")


def test_no_write_outside_the_turn_path(rig):
    bridge, c, _ = rig
    c.post("/turn", json={"text": STOCK})
    before = snapshot(bridge)
    assert c.get("/state").status_code == 200
    assert c.get("/history").status_code == 200
    assert c.get("/dials").status_code == 200
    assert c.post("/dials", json={"preset": "EXPLORATORY"}).json()["mode"] == "EXPLORATORY"
    assert c.post("/dials", json={"K": 12}).json()["values"]["K"] == 12
    assert c.post("/plan", json={"text": "Write the code for auth.py, verify the tests pass, then commit it to git."}).status_code == 200
    c.get("/eye/scan", params={"world": "clean"})
    for cmd in ("exit", "mode", "help", "history", "dials"):
        r = c.post("/turn", json={"text": cmd}).json()
        assert r["recorded"] is False
    assert snapshot(bridge) == before


def test_tool_actions_stay_off(rig):
    bridge, c, _ = rig
    target = server.REPO / "helm_ui_probe_should_not_exist.py"
    assert not target.exists()
    r = c.post("/turn", json={"text": "Write a python helper helm_ui_probe_should_not_exist.py and check git status."}).json()
    assert r["recorded"]
    assert r["record"]["route"] == "AGENTIC_GOAL" and r["record"]["tools_off"] is True
    assert r["record"]["gate"] == "GATE_CLAMPED"
    assert not target.exists()


def test_dials_reject_out_of_range(rig):
    _, c, _ = rig
    before = c.get("/dials").json()["values"]
    r = c.post("/dials", json={"R": 3})
    assert r.status_code == 422 and "R must be" in r.json()["error"]
    assert c.get("/dials").json()["values"] == before
    assert c.post("/dials", json={"preset": "nope"}).status_code == 422


def test_planner_orders_and_refuses_a_cycle(rig):
    _, c, _ = rig
    ok = c.post("/plan", json={"text": "Write the code for auth.py, verify the tests pass, then commit it to git."}).json()
    assert ok["ok"] and ok["refused"] is False
    assert ok["plan"]["order"] == ["synthesize", "verify", "git"]
    assert all(s["gate_verdict"] == "PROCEED" for s in ok["dry_run"]["steps"])
    assert all(e["source"] for e in ok["plan"]["edges"])
    cyc = c.post("/plan", json={"text": CYCLE}).json()
    assert cyc["refused"] is True and cyc["code"] == "PLAN_CYCLE" and cyc["stage"] == "plan"


def test_eye_scan_reads_only(rig):
    _, c, _ = rig
    if not (server.U3_DIR / "eye_scan.py").is_file():
        pytest.skip("U3 scanner folder not on this machine")
    rep = c.get("/eye/scan", params={"world": "fault"}).json()
    assert rep["ok"] and rep["eye_writes_to_brain"] == 0 and rep["whisper_writes"] == 0
    assert rep["findings"] and rep["salt"] == "dev"
    assert any(s["kind"] == "FINDING" for s in rep["plain"])
    assert c.get("/state").json()["eye_last"]["world_id"] == rep["world_id"]
    assert c.get("/eye/scan", params={"world": "other"}).json()["ok"] is False


def test_missing_parts_fail_soft(rig, monkeypatch, tmp_path):
    _, c, _ = rig
    monkeypatch.setattr(server, "U3_DIR", tmp_path / "nowhere")
    monkeypatch.setattr(server, "RB_I3_READING", tmp_path / "nowhere" / "READING.json")
    assert c.get("/eye/scan").json() == {"ok": False, "wired": False,
                                         "reason": f"not wired: {tmp_path / 'nowhere'} not found"}
    p = c.get("/state").json()["pairing"]
    assert p["wired"] is False and p["reason"].startswith("not wired")


def test_demo_page_is_self_contained():
    page = (UI_DIR / "demo" / "index.html").read_text(encoding="utf-8")
    assert "window.HELM_DEMO = " in page and "/static/" not in page
    data = json.loads(re.search(r"window\.HELM_DEMO = (.*?);</script>", page, re.S).group(1).replace("<\\/", "</"))
    assert data["turns"] and all(t["response"]["recorded"] for t in data["turns"])
    words = [t["response"]["record"]["status_word"] for t in data["turns"]]
    assert "INVENTORY_RECORDED" in words
    assert data["eye"]["clean"]["ok"] and data["plans"][-1]["code"] == "PLAN_CYCLE"
