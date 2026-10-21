"""Census 1 (TEST_PLAN step 1): how many real recipe ingredient lines does wide reader v5 refuse, and in how many
recipes? COUNTS ONLY. No recipe text, line text, id or title is printed or written. Laptop, 0 USD, stdlib + HELM's own
reader (import by path from a checkout that holds reader v5). Streams the frames line by line (low memory).
Floor (TEST_PLAN): at least 256 refused lines inside "gap recipes" (>= 1 refused line, every other line read, at most
10 lines). The ANSWER-key rule of RB-W1T is a custodian step and is NOT applied here; the floor is read against the
representable gap recipes, which is an upper bound on what a draw could use.
Usage: python -I -B -X utf8 census_gap_lines.py <HELM checkout with helm_wide_turn.py v5> <out dir>"""
import collections, hashlib, json, sys, time
from pathlib import Path

HELM = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HELM))
import helm_wide_turn as T  # noqa: E402

FRAMES = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19\x_real\frames")
SOURCES = {"PG": FRAMES / "FRAME_R_PG.jsonl", "WB": FRAMES / "FRAME_R_WB.jsonl"}
MAX_LINES = 10
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
t0 = time.time()
report = {"schema": "helm.census.gap_lines/1", "reader_file_sha256": h(HELM / "helm_wide_turn.py"),
          "brain_file_sha256": h(HELM / "helm_brain_wide.py"), "frames": {k: {"path": str(v), "sha256": h(v)} for k, v in SOURCES.items()},
          "max_lines": MAX_LINES, "per_source": {}, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
tot = collections.Counter(); codes_all = collections.Counter(); gap_codes_all = collections.Counter()
for name, path in SOURCES.items():
    c = collections.Counter(); codes = collections.Counter(); gap_codes = collections.Counter()
    gap_by_refused = collections.Counter(); gap_by_lines = collections.Counter()
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            d = json.loads(raw)
            lines = d.get("lines") or []
            c["recipes"] += 1; c["lines"] += len(lines)
            if not lines:
                c["recipes_no_lines"] += 1; continue
            refused = []
            for ln in lines:
                text = ln.get("raw") if isinstance(ln, dict) else str(ln)
                try:
                    parsed, ask = T.parse_lines(text)
                except Exception as exc:  # a crash is a refusal too, counted by exception name
                    parsed, ask = [], {"code": "EXC_" + type(exc).__name__}
                if ask is None and parsed:
                    c["lines_read"] += 1
                else:
                    code = (ask or {}).get("code", "UNKNOWN")
                    c["lines_refused"] += 1; codes[code] += 1; refused.append(code)
            if len(lines) > MAX_LINES:
                c["recipes_over_max_lines"] += 1
            if not refused:
                c["recipes_all_read"] += 1
            elif len(refused) == len(lines):
                c["recipes_none_read"] += 1
            else:
                c["recipes_mixed"] += 1
                if len(lines) <= MAX_LINES:
                    c["gap_recipes"] += 1; c["gap_refused_lines"] += len(refused)
                    gap_by_refused[len(refused)] += 1; gap_by_lines[len(lines)] += 1
                    for code in refused: gap_codes[code] += 1
    report["per_source"][name] = {"counts": dict(c), "refused_codes": dict(codes.most_common()),
                                  "gap_refused_codes": dict(gap_codes.most_common()),
                                  "gap_recipes_by_refused_lines": {str(k): v for k, v in sorted(gap_by_refused.items())},
                                  "gap_recipes_by_n_lines": {str(k): v for k, v in sorted(gap_by_lines.items())}}
    tot.update(c); codes_all.update(codes); gap_codes_all.update(gap_codes)
report["totals"] = dict(tot); report["refused_codes"] = dict(codes_all.most_common()); report["gap_refused_codes"] = dict(gap_codes_all.most_common())
floor = 256
report["floor"] = {"gap_refused_lines_required": floor, "gap_refused_lines_found": tot["gap_refused_lines"],
                   "gap_recipes_found": tot["gap_recipes"], "result": "PASS_FLOOR" if tot["gap_refused_lines"] >= floor else "STOP_NOT_EXERCISED",
                   "note": "answer-key rule and spent-exam exclusions not applied (custodian steps); this is an upper bound"}
report["seconds"] = round(time.time() - t0, 1)
p = OUT / "CENSUS_GAP_LINES.json"
p.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps({"totals": report["totals"], "floor": report["floor"], "top_codes": codes_all.most_common(12),
                  "gap_top_codes": gap_codes_all.most_common(12), "seconds": report["seconds"], "file_sha256": h(p)}, indent=1))
