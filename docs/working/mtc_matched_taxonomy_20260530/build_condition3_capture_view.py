"""Adapter: Condition-3 fixture -> capture-schema JSONL for the 20B extractor.

`capture_open_weight_probe_dataset.py` loads prompts via
`probe_dataset_common.load_labeled_scenarios`, which requires each record to carry
  - a prompt under `prompt` / `prompt_text` / `text`,
  - an id under `id` / `scenario_id`,
  - a recognized CAS label, e.g. `expected_cas_axes.element` in `^n|D` form
    (operator starts with '^', domain in {P,C,E,O}).

The Condition-3 fixture instead uses `english` / `sample_id` / `element_label`
(+ `element_cas_noetic` ^0..^9, `element_cas_domain` P/C/E/O). As-is the loader
SKIPS every row. This emitter rewrites the fixture into the schema the extractor
accepts, WITHOUT touching any prompt text, so the GPU forward pass sees identical
prompts and the npz comes out keyed by the real sample_id.

Emitted per row:
  id                 = sample_id           (-> npz scenario_ids; comparator join key)
  prompt             = english             (-> npz prompts; the 20B input, verbatim)
  split              = split               (carried for the comparator)
  expected_cas_axes  = {element: "^n|D", domain: D, noetic: "^n"}  (-> npz labels_element)
  control_semantic   = full block          (self-contained Control B/C reconstruction)

Validates that the emitted file loads back through load_labeled_scenarios with all
rows surviving and exactly 40 element classes.
"""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DATE = "20260531"
_FIX = _HERE / f"mtc_condition3_topical_scenarios_{_DATE}.jsonl"
# NOTE: load_labeled_scenarios reads the whole file with json.loads, so the
# capture view is a JSON ARRAY (.json), not newline-delimited JSONL.
_OUT = _HERE / f"mtc_condition3_capture_view_{_DATE}.json"

# Make the extractor's loader importable for the round-trip validation.
_SCRIPTS = (_HERE.parents[2] / "noetic-compass-scaffold" / "noetic-compass"
            / "live-trace-worker" / "scripts")


def main() -> int:
    rows = [json.loads(l) for l in _FIX.open(encoding="utf-8")]
    out_records = []
    for r in rows:
        noetic = r["element_cas_noetic"]          # "^0".."^9"
        domain = r["element_cas_domain"]          # P/C/E/O
        element = f"{noetic}|{domain}"            # _normalise_element-accepted form
        out_records.append({
            "id": r["sample_id"],
            "prompt": r["english"],
            "split": r["split"],
            "element_label": r["element_label"],   # human-readable A1..D10 (carried, unused by loader)
            "expected_cas_axes": {"element": element, "domain": domain, "noetic": noetic},
            "control_semantic": r["control_semantic"],
        })
    _OUT.write_text(json.dumps(out_records, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {_OUT.name}: {len(out_records)} records (JSON array)")

    # Round-trip validation through the real loader -------------------------
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    from probe_dataset_common import load_labeled_scenarios  # noqa: E402

    scen = load_labeled_scenarios(_OUT)
    n = len(scen)
    elems = Counter(s.labels.get("element", "") for s in scen)
    n_elem_classes = len([k for k in elems if k])
    prompts_ok = all(s.prompt for s in scen)
    ids_match = all(s.scenario_id.startswith("c3_") for s in scen)
    print(f"loader round-trip: scenarios={n}/{len(rows)} "
          f"element_classes={n_elem_classes} prompts_nonempty={prompts_ok} "
          f"ids_are_sample_ids={ids_match}")
    ok = (n == len(rows) == 1440 and n_elem_classes == 40 and prompts_ok and ids_match)
    print("VALIDATION:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
