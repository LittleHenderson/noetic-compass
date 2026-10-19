"""Build helm_ui/demo/index.html: one self-contained page that replays a REAL local HELM session with no server.

Every reply, record, self-check and plan in the page comes from running the real modules right now, through the same
HelmBridge the server uses (tools off). Nothing is typed in by hand. Run again to refresh:

    python helm_ui/make_demo.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(UI_DIR))
import server  # noqa: E402

SCRIPT = [
    "Hello",
    "We have 12 cups of flour and 9 cups of water.",
    "How much bread can we make?",
    "We made 5 loaves from 10 flour and 8 water and ran out of flour.",
    "How much bread can we make now?",
    "My grandfather kept bees.",
    "What do you know about me so far?",
    "Who will win the football game next year?",
]
PLANS = [
    "Write the code for auth.py, verify the tests pass, then commit it to git.",
    "Before you commit to git, verify the tests pass. Before you verify the tests, write the code for auth.py.",
    "Ω_a needs Ω_b first. Ω_b needs Ω_a first.",
]


def build() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        bridge = server.HelmBridge(session_dir=tmp, allow_tools=False)
        if bridge.session is None:
            raise SystemExit("HELM chat did not load: " + bridge.wiring.get("chat", ""))
        initial = bridge.state()
        turns = []
        for text in SCRIPT:
            resp = bridge.turn(text)
            if resp.get("record"):
                resp["record"]["session_file"] = "demo-session.jsonl"
            turns.append({"you_said": text, "response": resp})
        eye = {"clean": server.run_eye_scan("clean"), "fault": server.run_eye_scan("fault")}
        plans = [server.run_plan(p) for p in PLANS]
    return {"recorded_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime()),
            "note": "Recorded from a real local HELM session by helm_ui/make_demo.py; tools were off.",
            "state_initial": initial, "turns": turns, "eye": eye, "plans": plans}


def write(data: dict) -> Path:
    static = UI_DIR / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    css = (static / "styles.css").read_text(encoding="utf-8")
    js = (static / "app.js").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=True).replace("</", "<\\/")
    html = html.replace('<link rel="stylesheet" href="/static/styles.css">', "<style>\n" + css + "\n</style>")
    html = html.replace("<!--HELM_DEMO_DATA-->", "<script>window.HELM_DEMO = " + payload + ";</script>")
    html = html.replace('<script src="/static/app.js"></script>', "<script>\n" + js.replace("</", "<\\/") + "\n</script>")
    html = html.replace("<title>HELM</title>", "<title>HELM Demo</title>")
    out = UI_DIR / "demo" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    return out


if __name__ == "__main__":
    data = build()
    path = write(data)
    words = [t["response"].get("record", {}).get("status_word") for t in data["turns"]]
    print(f"wrote {path} ({path.stat().st_size} bytes); turns: {words}")
