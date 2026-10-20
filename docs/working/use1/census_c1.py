"""USE-1 census U0, StackExchange Cooking part (DESIGN.md sections 2.1-2.3 and 3.2). Counts only are published.

Run (laptop, one shard per process, each under 300 s / 300 MiB):
    python -B -I -X utf8 census_c1.py <posts|comments> <shard> <of> [--max-seconds 270]
A unit belongs to shard (Id mod <of>). Output: census_c1_custody/shard_<file>_<shard>of<of>.json (counters) and
census_c1_custody/rows_<file>_<shard>of<of>.jsonl (candidate rows WITH text: custodian folder, never printed).

Source files are untrusted data (x_real/sources/C1_stackexchange_cooking/extracted/): parsed as XML text only,
never executed. Keys = X-REAL K-S two-key pair imported from the UNPACKED SEALED ZIP (use1/xreal_unpacked, zip
sha256 a9b4c954...). Reader = helm_english_in v1.1 (sha256 31c8a078...). Frame rules = the designer's pinned
measure_yield.py (a6195cc2...) and stock_shape.py (9925debf...)."""
from __future__ import annotations

import hashlib
import html.parser
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

DAY = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19")
USE1 = DAY / "use1"
XR_UNPACKED = USE1 / "xreal_unpacked" / "HELM_XREAL_20261019"
DESIGN = DAY / "real_stock_source_design_v1"
READER = DAY / "rtr1" / "dry" / "overlay" / "helm"
SE = DAY / "x_real" / "sources" / "C1_stackexchange_cooking" / "extracted"
OUT = USE1 / "census_c1_custody"

PINS = {
    DAY / "x_real" / "HELM_XREAL_20261019_SOURCE_XREAL.zip": "a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249",
    DESIGN / "measure_yield.py": "a6195cc2e35e52ba2b74a3d3b59fc263d21e8c56c62f81745fdb4c581abcd019",
    DESIGN / "stock_shape.py": "9925debf311137ae025be4ff129002031652900ff5e50f2554bf161c1447892a",
    READER / "helm_english_in.py": "31c8a078e8817d39b1272169d8fcdda582db15a4314471eb00cc9bbc2953b33b",
    SE / "Posts.xml": "ce28c9240a878ea0d77d8dc832ded68a4e63f629205313498dbfbbeba8ec7a76",
    SE / "Comments.xml": "43af4a9bc3ed16407ec4c6cca8267689bcd39c3b0fa2124b614c360eb6cfa1d4",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# imports: X-REAL from the unpacked sealed zip FIRST (so measure_yield's own sys.path insert does not win)
sys.path.insert(0, str(XR_UNPACKED))
from xreal import sample_xr as SX  # noqa: E402
from xreal import frames as XF  # noqa: E402
from xreal import forbidden as XFB  # noqa: E402
sys.path.insert(0, str(DESIGN))
import measure_yield as MY  # noqa: E402
from stock_shape import stock_shape  # noqa: E402
assert Path(SX.__file__).resolve().is_relative_to(XR_UNPACKED.resolve()), SX.__file__
assert Path(MY.SX.__file__).resolve() == Path(SX.__file__).resolve()
assert Path(MY.HE.__file__).resolve().is_relative_to(READER.resolve()), MY.HE.__file__

RECIPE_TALK_RX = re.compile(r"(?<![\w'])(?:recipe|calls for|call for|requires|require|asks for|instructions|"
                            r"the directions)(?![\w'])", re.I)
HAVE_READY_RX = re.compile(r"^\s*have\s+ready(?![\w'])", re.I)
NUM_RX = re.compile(r"\d|[½⅓¼⅔¾⅛]|(?<![\w'])(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                    r"dozen|half)(?![\w'])", re.I)
ING_WORDS_RX = re.compile(r"(?<![\w'])(?:%s)(?![\w'])" % "|".join(map(re.escape, sorted(set(MY.G.INGREDIENT_WORDS)))),
                          re.I)


class Strip(html.parser.HTMLParser):
    """Body HTML -> text. <pre>, <code>, <blockquote> contents dropped; block tags become paragraph breaks."""
    DROP = {"pre", "code", "blockquote"}
    BLOCK = {"p", "li", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "ul", "ol", "table", "tr", "td"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag in self.DROP:
            self.depth += 1
        if tag in self.BLOCK:
            self.out.append("\n\n")

    def handle_endtag(self, tag):
        if tag in self.DROP and self.depth:
            self.depth -= 1
        if tag in self.BLOCK:
            self.out.append("\n\n")

    def handle_data(self, data):
        if not self.depth:
            self.out.append(data)


def body_text(h: str) -> str:
    s = Strip()
    s.feed(h or "")
    s.close()
    return "".join(s.out)


def flags(t: str) -> dict:
    return {"STOCK_SHAPE": stock_shape(t), "RECIPE_TALK": bool(RECIPE_TALK_RX.search(t)),
            "INSTRUCTION": bool(MY.IMP_RX.search(t) or HAVE_READY_RX.search(t))}


def main():
    which, shard, of = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    maxs = float(sys.argv[sys.argv.index("--max-seconds") + 1]) if "--max-seconds" in sys.argv else 270.0
    t0 = time.time()
    if shard == 0:
        for p, want in PINS.items():
            got = sha256_file(p)
            assert got == want, "PIN REFUSED %s" % p
    src = SE / ("Posts.xml" if which == "posts" else "Comments.xml")
    c = {}

    def bump(k, n=1):
        c[k] = c.get(k, 0) + n

    OUT.mkdir(exist_ok=True)
    rows_p = OUT / ("rows_%s_%dof%d.jsonl" % (which, shard, of))
    rows = open(rows_p, "w", encoding="utf-8")
    status = "COMPLETE"
    for ev, el in ET.iterparse(str(src), events=("end",)):
        if el.tag != "row":
            continue
        a = el.attrib
        uid = int(a["Id"])
        if uid % of != shard:
            el.clear()
            continue
        if time.time() - t0 > maxs:
            status = "STOPPED_AT_TIME_LIMIT"
            break
        if which == "posts":
            pt = a.get("PostTypeId")
            if pt not in ("1", "2"):
                el.clear()
                continue
            kind = "question" if pt == "1" else "answer"
            text = body_text(a.get("Body", ""))
        else:
            kind = "comment"
            text = a.get("Text", "")
        meta = {"owner_user_id": a.get("OwnerUserId") or a.get("UserId"),
                "owner_display_name": a.get("OwnerDisplayName") or a.get("UserDisplayName"),
                "creation_date": a.get("CreationDate"),
                "post_id": a.get("PostId") if which == "comments" else a.get("Id")}
        el.clear()
        bump("units_" + kind)
        grp = "SLICE" if uid % 25 == 0 else "FRAME"
        for i, s in enumerate(MY.sentences(text)):
            bump(grp + "_sentences")
            bump(grp + "_sentences_" + kind)
            fm = MY.MADE_RX.search(s)
            if fm:
                bump(grp + "_made_any")
            if not MY.FOOD_RX.search(s):
                continue
            bump(grp + "_food")
            fl = flags(s)
            kp = SX.s_key_pair(s)
            k = kp["key"]["key"]
            bump(grp + "_KS_" + k)
            if not kp["agree"]:
                bump(grp + "_KS_disagree")
            if fm:
                bump(grp + "_made_food")
                bump(grp + "_made_food_KS_" + k)
            if fl["STOCK_SHAPE"]:
                bump(grp + "_shape")
                bump(grp + "_shape_KS_" + k)
            stockish = k == "FACTS" and fl["STOCK_SHAPE"] and not fl["RECIPE_TALK"] and not fl["INSTRUCTION"]
            sayask = k == "ASK" and fl["STOCK_SHAPE"] and not fl["RECIPE_TALK"]
            instr_trap = (k == "EMPTY" and fl["INSTRUCTION"] and bool(NUM_RX.search(s))
                          and bool(ING_WORDS_RX.search(s)))
            empty_other = k == "EMPTY" and not fl["INSTRUCTION"]
            need_reader = k == "FACTS" or sayask or instr_trap or empty_other
            wa = MY.would_ask(s) if need_reader else None
            if k == "FACTS":
                bump(grp + "_FACTS_" + ("R1" if wa else "R4"))
            if stockish:
                bump(grp + "_STOCK_FP")
                bump(grp + "_STOCK_FP_" + ("R1_reader_gives_up" if wa else "R4_reader_reads"))
            cls = None
            if stockish:
                cls = "U1"
            elif sayask:
                cls = "U3"
            elif instr_trap and wa:
                cls = "U4a"
            elif empty_other and wa:
                cls = "U4b"
            elif fm:
                cls = "MADE_REPORTED"
            if cls:
                bump(grp + "_cand_" + cls)
                rec = {"id": "se:cooking:%s:%d:%d" % ("comment" if which == "comments" else "post", uid, i),
                       "kind": kind, "group": grp, "cand": cls, "key": k, "agree": kp["agree"],
                       "would_ask": wa, "flags": fl, "personal": XF.personal_data(s),
                       "norm_sha256": hashlib.sha256(XFB.normalize(s).encode()).hexdigest(),
                       "text_sha256": hashlib.sha256(s.encode()).hexdigest(), "n_words": len(s.split()),
                       "made": bool(fm), "meta": meta, "text": s}
                rows.write(json.dumps(rec, ensure_ascii=False) + "\n")
    rows.close()
    out = {"file": which, "shard": shard, "of": of, "status": status, "seconds": round(time.time() - t0, 1),
           "reader": MY.HE.READER_VERSION, "counts": dict(sorted(c.items()))}
    (OUT / ("shard_%s_%dof%d.json" % (which, shard, of))).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("file", "shard", "of", "status", "seconds")}),
          "sentences", c.get("FRAME_sentences", 0) + c.get("SLICE_sentences", 0), "STOCK_FP", c.get("FRAME_STOCK_FP", 0))


if __name__ == "__main__":
    main()
