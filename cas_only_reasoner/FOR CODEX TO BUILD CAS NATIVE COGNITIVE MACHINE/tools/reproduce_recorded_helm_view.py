"""Build the saved Helm workbench without model inference or training."""
from __future__ import annotations

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cncm import rpa_recorded_helm as recorded
from cncm.canonical import canonical_json
from tools.render_rpa_view import render_rpa_view, _within_home

DEFAULT = ROOT / "records/rpa_recorded_helm_20260922/workbench"


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()


def reproduce(output):
    output = _within_home(output)
    if output.exists() and not output.is_dir():
        raise ValueError("output must be a directory")
    document = recorded.build_recorded_atlas()
    original = canonical_json(document)
    assert recorded.load_recorded_atlas(original) == document
    atlas = recorded.validate_recorded_atlas(document)
    payload = recorded.view_payload(document)
    assert payload["profiles"] == {} and payload["calculations"] == {}
    assert all(node.profile40 is None for node in atlas.nodes)
    addresses = {}
    for node in atlas.nodes:
        address = recorded.exact_address(document, node.node_id)
        uri = recorded.address_text(address)
        assert recorded.resolve_address(document, uri) == node
        addresses[node.node_id] = {"address": address, "uri": uri}
    trace = []
    for case in ("correct", "wrong"):
        cursor = recorded.start_navigation(document)
        cursor = recorded.enter_node(document, cursor, "task-" + case)
        cursor = recorded.inspect_node(document, cursor, "prediction-" + case)
        cursor = recorded.select_reference(document, cursor, "model-checkpoint")
        view = recorded.navigation_view(document, cursor)
        assert view["current_state_id"] == recorded.PRESENT
        assert view["profile_status"] == "NOT_ASSIGNED" and view["ohm_status"] == "NOT_RECORDED"
        trace.append({"case": case, "cursor": cursor, "source_unchanged": canonical_json(document) == original})
        assert recorded.return_to(document, cursor, 0)["path"] == [recorded.PRESENT]
    assert [row["saved_check"]["correct"] for row in document["examples"]] == [True, False]
    page = render_rpa_view(document)
    assert canonical_json(document) == original
    saved = {"schema_version": recorded.SAVED_VIEW_SCHEMA, "document_sha256": document["document_sha256"],
             "current_state_id": recorded.PRESENT, "navigation": {
                 **recorded.start_navigation(document), "focus_node_id": "task-correct"},
             "layout": "flower", "zoom": 1, "axes": [25, 33], "compare_node_id": ""}
    bookmark = base64.b64encode(json.dumps(saved, separators=(",", ":")).encode()).decode()
    index = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>CAS-RPA · Saved workbench</title><style>body{font:17px/1.6 system-ui,sans-serif;background:#f3f6f6;color:#163746;max-width:820px;margin:60px auto;padding:24px}h1{line-height:1.2}section{background:white;padding:24px;margin:20px 0;border:1px solid #d6e1e5;border-radius:12px}a{color:#087c83;font-weight:700}code{overflow-wrap:anywhere}small{color:#526979}</style>
<h1>Inspect what Helm actually answered.</h1><p>Original saved outputs, their checker results, and the model that produced them.</p>
<section><h2>Recorded Helm development answers</h2><p>One genuine correct answer and one genuine error from Helm 2.0-experimental. No model runs when you open this file.</p>
<p><a href="helm.html#view=''' + bookmark + '''">Open the saved question and answer</a></p><small>CAS profile: Not assigned. CAS-Ohm measurement: Not available. These selected examples are not a new performance benchmark.</small></section>
<section><h2>Declared CAS-Ohm design example</h2><p>The separate 12/4=3 and 12/6=2 calculations remain declared designs. They are not readings from the Helm answers.</p>
<a href="../../rpa_ohm_atlas_20260922/demo/atlas.html">Open the preserved design atlas</a></section>
<p><small>These files inspect saved records. Native runtime, compound runtime, Helm predictions and declared designs retain their separate source identities.</small></p></html>'''
    verification = {"schema_version": "cas.rpa.recorded-helm-reproduction/0.1",
                    "status": "EXECUTED_RECORD_AND_NAVIGATION_CHECKS_PASS",
                    "document_sha256": document["document_sha256"], "addresses": addresses,
                    "navigation": trace, "source_selection_sha256": recorded.SELECTION_SHA256,
                    "profiles": "NOT_ASSIGNED", "ohm_measurements": "NOT_AVAILABLE",
                    "model_execution": "NOT_RUN", "browser_tests": "SEPARATELY_RECORDED",
                    "examples": [{key: row[key] for key in ("example_id", "question_display", "prediction_display", "saved_check", "checker_replay")}
                                 for row in document["examples"]]}
    files = {"helm.json": encoded(document), "helm.html": page.encode(), "index.html": index.encode(),
             "saved_view.json": encoded(saved), "verification.json": encoded(verification)}
    manifest = {"schema_version": "cas.rpa.recorded-helm-artifacts/0.1", "document_sha256": document["document_sha256"],
                "files": {name: {"bytes": len(body), "sha256": sha256(body).hexdigest()} for name, body in files.items()}}
    files["manifest.json"] = encoded(manifest)
    output.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        path = output / name
        if path.is_symlink() or not _within_home(path).is_relative_to(output):
            raise ValueError("artifact path escaped output")
        path.write_bytes(body)
        assert path.read_bytes() == body
    return {"output": str(output), "document_sha256": document["document_sha256"],
            "files": len(files), "neural_execution": "NOT_RUN"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT)
    args = parser.parse_args(argv)
    print(json.dumps(reproduce(args.out.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
