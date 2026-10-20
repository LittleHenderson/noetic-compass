"""Census 2 (TEST_PLAN step 1): apply the DRAFT stage-1 tag rules (DESIGN 1.2) to every receipt-like record in the
wave-6 c50 host output and the RB-I3 run, and count the 28-cell histogram. COUNTS ONLY: no text field is read into
the report; only status / reason / kind words and Foundation labels are looked at. Floor (TEST_PLAN): at least 20 of 28
cells with 8 or more items. The rules here are the DRAFT table; UNTAGGED is reported, never guessed.
Usage: python -I -B -X utf8 census_tags_28_cells.py <out dir>"""
import collections, hashlib, json, re, sys, time
from pathlib import Path

OUT = Path(sys.argv[1]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
C = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19")
ROOTS = {"c50_host": C / "r1_wave6" / "run_c50_r1w6v3_20261020" / "deliverable_unpacked_a1" / "results" / "r1w6_host_run" / "out" / "r1w6_out",
         "rb_i3_runs": C / "rb_i3" / "runs"}
FOUND_RX = re.compile(r"^F[1-7]$")
# ---- DRAFT rule DOM-1 / DOM-2: a status or reason word -> Domain. First match wins; else UNTAGGED. ----
DOM_RULES = [  # (regex over the word, Domain, rule id)
    (r"REFUSED|GUARD|CUT_|CLAMPED|ALWAYS_ASK|LEARNING_DISABLED|VIOLAT", "P", "DOM-1a rules, caps, refusals, guards"),
    (r"ADMITTED|SUCCESS_EVALUATED|UNDETERMINED|PLAN|LEARNED|READ$|REPLAY", "C", "DOM-1b readings, lessons, answers, plans"),
    (r"COMPLETE|EXITED|SKIPPED|CHECK|VERIF|FINDING|WHISPER|REPORT|PASS|FAIL|ADMIT$", "E", "DOM-1c verdicts, receipts, Eye findings"),
    (r"INVENTORY_RECORDED|STOCK_RECORDED|WITNESS|RECORDED|TOOL|FILE", "O", "DOM-1d stock, batches, tools, files"),
    (r"^CLARIFY_|^ASK|QUESTION", "C", "DOM-1e a question = a reading that stopped"),
]
def domain_of(word):
    for rx, dom, rid in DOM_RULES:
        if re.search(rx, word): return dom, rid
    return "UNTAGGED", None

items = collections.Counter(); cells = collections.Counter(); fonly = collections.Counter(); donly = collections.Counter(); how = collections.Counter(); untagged_words = collections.Counter()
per_root = {}
t0 = time.time()
for root_name, root in ROOTS.items():
    rc = collections.Counter(); rcells = collections.Counter(); nfiles = 0
    for f in sorted(root.rglob("*.json")):
        nfiles += 1
        try:
            d = json.loads(f.read_bytes())
        except Exception:
            rc["unreadable_files"] += 1; continue
        def walk(o, found):
            if isinstance(o, dict):
                # Foundation inherited from any ancestor field naming one
                for k in ("foundation", "well", "F", "desire", "home", "filed_at", "category"):
                    v = o.get(k)
                    if isinstance(v, str) and FOUND_RX.match(v): found = v
                word = None
                for k in ("status", "reason", "code", "verdict", "outcome"):
                    v = o.get(k)
                    if isinstance(v, str) and v and v != "None": word = v; break
                if word is not None:
                    dom, rid = domain_of(word)
                    rc["items"] += 1; items[root_name] += 1
                    how[rid or "UNTAGGED"] += 1
                    if dom == "UNTAGGED": untagged_words[word[:40]] += 1
                    cell = f"{found}{dom}" if (found and dom != "UNTAGGED") else ("UNTAGGED_FOUNDATION" if dom != "UNTAGGED" else "UNTAGGED_DOMAIN")
                    if found and dom == "UNTAGGED": cell = "UNTAGGED_DOMAIN"
                    rcells[cell] += 1; cells[cell] += 1
                    if found and dom == "UNTAGGED": fonly[found] += 1
                    if (not found) and dom != "UNTAGGED": donly[dom] += 1
                for v in o.values(): walk(v, found)
            elif isinstance(o, list):
                for v in o: walk(v, found)
        walk(d, None)
    per_root[root_name] = {"files": nfiles, "counts": dict(rc), "cells": dict(rcells.most_common())}
grid = {f"F{i}{d}": cells.get(f"F{i}{d}", 0) for i in range(1, 8) for d in "PCEO"}
filled = sum(1 for v in grid.values() if v >= 8)
report = {"schema": "helm.census.tags_28_cells/1", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
          "rules": [{"regex": rx, "domain": dom, "rule": rid} for rx, dom, rid in DOM_RULES], "roots": {k: str(v) for k, v in ROOTS.items()},
          "per_root": per_root, "items_total": sum(items.values()), "how": dict(how.most_common()),
          "untagged_domain_words_top": dict(untagged_words.most_common(30)), "grid_28": grid,
          "foundation_only_by_F": dict(sorted(fonly.items())), "domain_only_by_D": dict(sorted(donly.items())),
          "untagged": {"foundation_missing": cells.get("UNTAGGED_FOUNDATION", 0), "domain_missing": cells.get("UNTAGGED_DOMAIN", 0)},
          "floor": {"cells_with_8_or_more_required": 20, "cells_with_8_or_more_found": filled,
                    "result": "PASS_FLOOR" if filled >= 20 else "STOP_NOT_EXERCISED"},
          "seconds": round(time.time() - t0, 1)}
p = OUT / "CENSUS_TAGS_28_CELLS.json"
p.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps({"items_total": report["items_total"], "grid_28": grid, "untagged": report["untagged"], "foundation_only_by_F": report["foundation_only_by_F"], "domain_only_by_D": report["domain_only_by_D"], "floor": report["floor"],
                  "how": report["how"], "untagged_words_top": dict(untagged_words.most_common(12)), "per_root_files": {k: v["files"] for k, v in per_root.items()},
                  "seconds": report["seconds"], "file_sha256": hashlib.sha256(p.read_bytes()).hexdigest()}, indent=1))
