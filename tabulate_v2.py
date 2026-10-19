"""tabulate_v2.py -- v1 vs v2 alias-wide lexicon, side by side, every number COMPUTED.

Replaces the typed-in literals of tabulate_439_sdg_baseline.py (lines 170-173: 42 / 17 / 25 / 25/42, and lines
209-210: Bridge v2 118 / 321 / 42 and cce 265 / 199 / 17; plus the .get("MISMATCH", 42) default). That old script
is NOT edited and is NOT re-run here, because it also rewrites the two split files.

This script writes NOTHING into cas-synthetic/. It only reads.

Usage (stdlib only, one process):
  python -X utf8 -B tabulate_v2.py                          # 481 / 439 / DEV-99, v1 and v2
  python -X utf8 -B tabulate_v2.py --score-sealed-98-once   # adds the ONE sealed pass (counts only)

The sealed pass refuses to run a second time: it writes a receipt and checks for it first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent
LANG_V3 = REPO / "docs" / "working" / "noetic_council" / "language_v3"
BRIDGE_ROOT = Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011")
LACUNA_ROOT = Path(r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1")
for p in (LANG_V3, BRIDGE_ROOT, LACUNA_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import lexicon_v2  # noqa: E402
import scoring  # noqa: E402
from sdg_bridge_v2.english import check_binding  # noqa: E402

SPLIT = REPO / "cas-synthetic" / "data" / "l4_split"
DEV = SPLIT / "real_dev_unparseables_99.jsonl"
SEALED = SPLIT / "real_heldout_unparseables_98.jsonl"
DEV_SHA = "17cd198321d242bd74ff789a4b7f8032d499a7ff8534e5b07545b6221930fde0"
SEALED_SHA = "e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe"
OUT_JSON = REPO / "docs" / "working" / "SDG_TABULATION_V1_V2_20261018.json"
SEALED_RECEIPT = LANG_V3 / "SEALED_98_SCORE_RECEIPT_LEXICON_V2.json"
VERDICTS = ("MATCH", "UNPARSEABLE_ENGLISH", "MISMATCH")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_line(item):
    """Byte-identical to the line tabulate_439_sdg_baseline.py writes, so the split can be re-derived in memory."""
    return json.dumps({"seed_id": item["seed_id"], "file": item["file"], "line": item["line"],
                       "english": item["english"], "parsed": item["parsed"]}, ensure_ascii=False) + "\n"


def score(rows, version):
    m = lexicon_v2.reader(version)
    verdicts, reasons, second, per = Counter(), Counter(), 0, []
    for r in rows:
        v = m.check(r["parsed"], r["english"])
        verdicts[v["verdict"]] += 1
        for code in v.get("reasons", []):
            reasons[code] += 1
        if v["verdict"] == "MATCH" and v.get("second_number_agrees"):
            second += 1
        per.append(v["verdict"])
    return {"MATCH": verdicts["MATCH"], "UNPARSEABLE": verdicts["UNPARSEABLE_ENGLISH"],
            "MISMATCH": verdicts["MISMATCH"], "second_number_agrees": second,
            "reasons": dict(sorted(reasons.items()))}, per


def bridge(rows):
    c = Counter(check_binding(r["parsed"], r["english"])["verdict"] for r in rows)
    return {"MATCH": c["MATCH"], "UNPARSEABLE": c["UNPARSEABLE_ENGLISH"], "MISMATCH": c["MISMATCH"]}


def transitions(a, b):
    t = Counter((x, y) for x, y in zip(a, b))
    return {"%s->%s" % (x, y): t[(x, y)] for x in VERDICTS for y in VERDICTS if t[(x, y)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score-sealed-98-once", action="store_true")
    args = ap.parse_args()
    t0 = time.perf_counter()

    frozen = json.loads((LANG_V3 / "FROZEN.json").read_text("utf-8"))
    excluded = set(frozen["headline_rows"]["excluded_42_seed_ids"])
    rows, total_lines = scoring.load_english(excluded)
    head = [r for r in rows if not r["excluded"]]

    report = {"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "lexicon_v2_sha256": sha256(LANG_V3 / "lexicon_v2.py"),
              "lexicon_v1_json_sha256": sha256(LANG_V3 / "ALIAS_WIDE_LEXICON_v0_1.json"),
              "frozen_lexicon_v2_sha256": sha256(LANG_V3 / "FROZEN_LEXICON_V2.json"),
              "total_file_lines": total_lines, "accepted_rows": len(rows), "headline_rows": len(head),
              "excluded_rows": len(rows) - len(head)}

    v1_481, p1_481 = score(rows, "v1")
    v2_481, p2_481 = score(rows, "v2")
    v1_439, p1_439 = score(head, "v1")
    v2_439, p2_439 = score(head, "v2")
    b_481, b_439 = bridge(rows), bridge(head)
    report["view_481"] = {"bridge_v2": b_481, "lexicon_v1": v1_481, "lexicon_v2": v2_481,
                          "v1_to_v2_transitions": transitions(p1_481, p2_481)}
    report["view_439"] = {"bridge_v2": b_439, "lexicon_v1": v1_439, "lexicon_v2": v2_439,
                          "v1_to_v2_transitions": transitions(p1_439, p2_439)}
    reduction = b_481["MISMATCH"] - v1_481["MISMATCH"]
    report["computed_replacements_for_old_literals"] = {
        "bridge_v2_481_mismatches (old literal 42)": b_481["MISMATCH"],
        "cce_v1_481_mismatches (old literal 17)": v1_481["MISMATCH"],
        "misread_reduction_v1 (old literal 25)": reduction,
        "error_reduction_pct_v1 (old literal 25/42)":
            round(reduction / b_481["MISMATCH"] * 100, 2) if b_481["MISMATCH"] else None,
        "bridge_v2_481 MATCH/UNPARSEABLE/MISMATCH (old literal 118/321/42)":
            [b_481["MATCH"], b_481["UNPARSEABLE"], b_481["MISMATCH"]],
        "cce_v1_481 MATCH/UNPARSEABLE/MISMATCH (old literal 265/199/17)":
            [v1_481["MATCH"], v1_481["UNPARSEABLE"], v1_481["MISMATCH"]],
        "bridge_v2_439 MISMATCH (old code: .get default 0)": b_439["MISMATCH"],
    }

    # Re-derive the split in memory (no write) and check it reproduces the two files byte for byte.
    unparse_439 = [r for r, v in zip(head, p1_439) if v == "UNPARSEABLE_ENGLISH"]
    shuffled = list(unparse_439)
    random.Random(42).shuffle(shuffled)
    # The old script wrote in Windows text mode, so every line ends CRLF on disk.
    held_bytes = "".join(split_line(x) for x in shuffled[:98]).replace("\n", "\r\n").encode("utf-8")
    dev_bytes = "".join(split_line(x) for x in shuffled[98:]).replace("\n", "\r\n").encode("utf-8")
    report["split_rederivation"] = {
        "v1_unparseable_439": len(unparse_439),
        "dev_rederived_sha256_matches_file": hashlib.sha256(dev_bytes).hexdigest() == DEV_SHA == sha256(DEV),
        "sealed_rederived_sha256_matches_expected": hashlib.sha256(held_bytes).hexdigest() == SEALED_SHA,
        "note": "computed from the v1 verdicts only; no sealed row text is printed or stored"}

    # DEV-99: before (v1) and after (v2).
    assert sha256(DEV) == DEV_SHA, "DEV file changed"
    dev = [json.loads(x) for x in DEV.read_text("utf-8").splitlines() if x.strip()]
    d1, pd1 = score(dev, "v1")
    d2, pd2 = score(dev, "v2")
    report["dev_99"] = {"lexicon_v1": d1, "lexicon_v2": d2, "v1_to_v2_transitions": transitions(pd1, pd2)}

    if args.score_sealed_98_once:
        if SEALED_RECEIPT.exists():
            raise SystemExit("REFUSED: the sealed 98 were already scored once (%s)" % SEALED_RECEIPT)
        before = sha256(SEALED)
        if before != SEALED_SHA:
            raise SystemExit("REFUSED: sealed sha256 is %s, expected %s" % (before, SEALED_SHA))
        sealed = [json.loads(x) for x in SEALED.read_bytes().decode("utf-8").splitlines() if x.strip()]
        s1, _ = score(sealed, "v1")
        s2, _ = score(sealed, "v2")
        after = sha256(SEALED)
        receipt = {"scored_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rows": len(sealed),
                   "sha256_before": before, "sha256_after": after, "unchanged": before == after == SEALED_SHA,
                   "lexicon_v2_sha256": report["lexicon_v2_sha256"],
                   "lexicon_v1": {k: s1[k] for k in ("MATCH", "UNPARSEABLE", "MISMATCH")},
                   "lexicon_v2": {k: s2[k] for k in ("MATCH", "UNPARSEABLE", "MISMATCH")},
                   "policy": "counts only; no row text, seed id or per-row verdict recorded; scored once"}
        SEALED_RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", "utf-8")
        report["sealed_98"] = receipt

    report["runtime_seconds"] = round(time.perf_counter() - t0, 3)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")

    def line(name, d):
        return "| %s | %d | %d | %d |" % (name, d["MATCH"], d["UNPARSEABLE"], d["MISMATCH"])

    for title, key in (("481 accepted rows", "view_481"), ("439 headline rows", "view_439"), ("DEV 99", "dev_99")):
        print("\n### %s\n| reader | MATCH | UNPARSEABLE | MISMATCH |\n|---|---:|---:|---:|" % title)
        if "bridge_v2" in report[key]:
            print(line("bridge v2", report[key]["bridge_v2"]))
        print(line("lexicon v1", report[key]["lexicon_v1"]))
        print(line("lexicon v2", report[key]["lexicon_v2"]))
        print("transitions v1->v2:", report[key]["v1_to_v2_transitions"])
        print("second number agrees (v1, v2):", report[key]["lexicon_v1"]["second_number_agrees"],
              report[key]["lexicon_v2"]["second_number_agrees"])
        print("reasons v1:", report[key]["lexicon_v1"]["reasons"])
        print("reasons v2:", report[key]["lexicon_v2"]["reasons"])
    print("\ncomputed replacements:", json.dumps(report["computed_replacements_for_old_literals"], indent=1))
    print("split re-derivation:", report["split_rederivation"])
    if "sealed_98" in report:
        s = report["sealed_98"]
        print("\nSEALED 98 (once): v1", s["lexicon_v1"], "| v2", s["lexicon_v2"], "| sha unchanged:", s["unchanged"])
    print("\nwrote", OUT_JSON, "in %.2fs" % report["runtime_seconds"])


if __name__ == "__main__":
    main()
