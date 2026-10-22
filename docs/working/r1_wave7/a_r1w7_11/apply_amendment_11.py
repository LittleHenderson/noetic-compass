"""apply_amendment_11.py <package_root> [--plants-only] -- apply A-R1W7-11 to a wave-7 package source tree
(HELM_R1_W7_20261020/, a FRESH copy; never the sealed build tree). DESIGN_V73_A11.md section 3.5 and T2.

  1. r1w7/honest_ask_w7.py              (new; the honesty test and the K4 recount)
  2. tests_r1w7/test_honest_ask_w7.py   (new; T2: the real frozen functions on the author's own items)
  3. r1w7/score_w7.py                   (one import, one keyword, one call right after the frozen wave-6 score_real)
  4. r1w7/merge_r1w7.py                 (READER v3; reads SAMPLE_REAL_X7.json beside the keys; passes the raw lines;
                                         K4 reads the strict count after the exemption, only when the recount is consistent)
  5. tests_r1w7/fixture_run.py          (five reader-level plants + a synthetic SAMPLE_REAL_X7.json)
  6. tests_r1w7/run_tests.py            (+ tests_r1w7.test_honest_ask_w7)
  7. PREREGISTRATION_R1W7.md            (section 23 appended; sections 1-22 are not edited)

--plants-only applies change 5 alone (the design's step 2: the plants run against the UNMODIFIED reader first).

Every anchor must occur exactly once and the amendment must not be present yet; every check runs BEFORE any write, so a
refusal writes nothing. Content checks (fix round 2026-10-21, reviewer G-8): each of the five target files must hash to its
v9 member pin (V9_TARGET_SHA256, copied from the sealed v9 PACKAGE_FREEZE.json, sha256 ce9495fa...) AND to the member pin
in the tree's own PACKAGE_FREEZE.json; each new file's source beside this tool must hash to NEW_FILE_SHA256 (the values
AMENDMENT_A_R1W7_11.md section 7 lists); section 22 must be the LAST "## " section of the preregistration, so appending
section 23 at the end puts it right after section 22. Writes are two-phase: every changed file is first written as
<name>.partial, then each is renamed into place (os.replace), so a refusal or a crash while writing leaves no half-written
file. Prints the sha256 of every file it wrote or changed. Standard library only.
Usage: python -X utf8 -B -I apply_amendment_11.py C:\\path\\to\\HELM_R1_W7_20261020 [--plants-only]
"""
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEW_FILES = {"r1w7/honest_ask_w7.py": "honest_ask_w7.py", "tests_r1w7/test_honest_ask_w7.py": "test_honest_ask_w7.py"}
#: the sources beside this tool must be exactly these bytes (AMENDMENT_A_R1W7_11.md section 7)
NEW_FILE_SHA256 = {
    "honest_ask_w7.py": "a4dd7926e93885c271a1c3696cac0883b7c875c334cf611b595a1fb061b66e40",
    "test_honest_ask_w7.py": "cf8fe611d97f9869f2977d26495507551bdb4c0d15ea7032967fb865fb5658e4",
}
#: the five target files as sealed in v9 (PACKAGE_FREEZE.json members of the v9 zip ad3fb98c...)
V9_TARGET_SHA256 = {
    "r1w7/score_w7.py": "01fef9272e1d9d0dc5055de7b8b7779c53cc7703803d81134e1f3cb1a0a06af9",
    "r1w7/merge_r1w7.py": "3dcb07fa25fa6627049df68391536f8fad55aae3be02178e5ce25a2885f1744a",
    "tests_r1w7/fixture_run.py": "b351fe951a570721ba2f67610235fe91e3fd7a3f6cad4e0fc74cb8599eb9cfd6",
    "tests_r1w7/run_tests.py": "194669a94d81e925bc1e205f437f824e8ba79335119908562f66d6de0ff9cf56",
    "PREREGISTRATION_R1W7.md": "5d04b3ab1e8f2ef52df7797f9aa7c688ae4e2b27e8b5b6ae4824278e3bd1d379",
}

# ------------------------------------------------------------------------------------------------ score_w7.py
SCORE_EDITS = [
    ("from . import common_w7 as C\n",
     "from . import common_w7 as C\n"
     "from . import honest_ask_w7 as HA       # A-R1W7-11 (owner's word 2026-10-21: \"Exempt from K4 only\")\n"),
    ("def score_real(ns, HV, keys: List[dict], inputs: List[dict], doc: Dict[str, Any], plainness_scored: bool) -> Dict[str, Any]:\n"
     "    out = ns.SC6.score_real(ns, keys, inputs, doc)\n",
     "def score_real(ns, HV, keys: List[dict], inputs: List[dict], doc: Dict[str, Any], plainness_scored: bool,\n"
     "               raw_by_id: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:\n"
     "    out = ns.SC6.score_real(ns, keys, inputs, doc)\n"
     "    HA.apply(ns, out, keys, inputs, doc, raw_by_id)      # A-R1W7-11: K4's MULTI_QTY honest-ask recount (no raw lines -> no exemption)\n"),
]

# ------------------------------------------------------------------------------------------------ merge_r1w7.py
MERGE_EDITS = [
    ('READER = "r1w7.merge_r1w7 v2 (2026-10-20, A-R1W7-4: HG5 names the units missing helm_now_files_changed)"\n',
     'READER = ("r1w7.merge_r1w7 v3 (2026-10-21, A-R1W7-11: K4 reads the strict count after the MULTI_QTY honest-ask '
     'exemption; reads SAMPLE_REAL_X7.json for the tagged lines)")\n'),
    ('        self.inputs_noise = json.loads((ex / "INPUTS_NOISE_X7.json").read_text(encoding="utf-8"))\n',
     '        self.inputs_noise = json.loads((ex / "INPUTS_NOISE_X7.json").read_text(encoding="utf-8"))\n'
     '        # A-R1W7-11: the real items\' raw lines (laptop only, beside the keys) for the tagged-line check; never raises;\n'
     '        # absent or unreadable -> {} and None, and then nothing is exempted\n'
     '        self.raw_real: Dict[str, Any] = {}\n'
     '        self.sample_real_sha256: Optional[str] = None\n'
     '        try:\n'
     '            sp = ex / "SAMPLE_REAL_X7.json"\n'
     '            if sp.is_file():\n'
     '                sha = C.sha256_file(sp)\n'
     '                raw = {}\n'
     '                for it in json.loads(sp.read_text(encoding="utf-8")).get("items") or []:\n'
     '                    if isinstance(it, dict) and isinstance(it.get("id"), str) and isinstance(it.get("raw_lines"), list):\n'
     '                        raw[it["id"]] = [str(x) for x in it["raw_lines"]]\n'
     '                self.raw_real, self.sample_real_sha256 = raw, sha\n'
     '        except Exception:                                   # A-R1W7-11: never raises; no lines -> no exemption\n'
     '            self.raw_real, self.sample_real_sha256 = {}, None\n'),
    ('            sm["real"] = SC.score_real(self.ns, self.HV, self.keys_real, self.inputs_real, d, plain_scored)\n',
     '            sm["real"] = SC.score_real(self.ns, self.HV, self.keys_real, self.inputs_real, d, plain_scored,\n'
     '                                       raw_by_id=self.raw_real)                     # A-R1W7-11\n'),
    ('    mk["K4_HONEST"] = {"value": bool(t) and t.get("unexplained_asks_strict") == 0,\n'
     '                       "unexplained_asks_strict": t.get("unexplained_asks_strict"),\n'
     '                       "unexplained_asks_w6_rule_reported": t.get("unexplained_asks"),\n'
     '                       "unsettled_ask_fired": t.get("unsettled_ask_fired"),\n'
     '                       "not_routed_scored_turns": t.get("not_routed_scored_turns"), "deviation": "D-W7-9"}\n',
     '    # A-R1W7-11 (owner\'s word 2026-10-21 "Exempt from K4 only"; a fresh draw only): K4 reads the frozen strict count\n'
     '    # minus the honest asks on MULTI_QTY-tagged ANSWER keys (r1w7/honest_ask_w7.py), and only when the recount of the\n'
     '    # frozen rule equals the frozen strict count; the strict count is still reported; exempted items are listed as\n'
     '    # FLAG_FOR_HUMAN_REVIEW (reported, not a gate)\n'
     '    real_on = R.get("X7_REAL", "CHAT_ON").get("real") or {}\n'
     '    a11_rows = {row.get("id"): row for row in (real_on.get("a11_checks") or []) if isinstance(row, dict)}\n'
     '    a11_ids = list(real_on.get("a11_exempted_ids") or [])\n'
     '    mk["K4_HONEST"] = {"value": bool(t) and t.get("a11_consistent") is True and t.get("unexplained_asks_strict_after_a11") == 0,\n'
     '                       "unexplained_asks_strict": t.get("unexplained_asks_strict"),\n'
     '                       "unexplained_asks_strict_after_a11": t.get("unexplained_asks_strict_after_a11"),\n'
     '                       "a11_strict_recount": t.get("a11_strict_recount"), "a11_consistent": t.get("a11_consistent"),\n'
     '                       "a11_exempted_ids": a11_ids, "sample_real_sha256": R.sample_real_sha256,\n'
     '                       "a11_flag_for_human_review": [{"id": i, "tagged_lines": (a11_rows.get(i) or {}).get("tagged_lines"),\n'
     '                                                      "unlearned": (a11_rows.get(i) or {}).get("unlearned"),\n'
     '                                                      "allowed_tail_heads": (a11_rows.get(i) or {}).get("allowed_tail_heads"),\n'
     '                                                      "status": "FLAG_FOR_HUMAN_REVIEW"} for i in a11_ids],\n'
     '                       "unexplained_asks_w6_rule_reported": t.get("unexplained_asks"),\n'
     '                       "unsettled_ask_fired": t.get("unsettled_ask_fired"),\n'
     '                       "not_routed_scored_turns": t.get("not_routed_scored_turns"), "deviation": "D-W7-9",\n'
     '                       "amendment": "A-R1W7-11"}\n'),
]

# ------------------------------------------------------------------------------------------------ fixture_run.py
FIXTURE_EDITS = [
    ('OFF_STATUS = "CLARIFY_ENGLISH_UNKNOWN_PRODUCT"\n',
     'OFF_STATUS = "CLARIFY_ENGLISH_UNKNOWN_PRODUCT"\n'
     '#: A-R1W7-11 (DESIGN_V73_A11.md T2, reader level): five plants on item 0, the author\'s own synthetic lines\n'
     'A11_PLANTS = ("K4_A11", "K4_A11_CLARIFY", "K4_A11_PHANTOM", "K4_A11_NO_SAMPLE", "K3_A11_WRONG")\n'
     'A11_TAIL_NAME = "juniper berry"                       # the brain\'s name for the second amount\'s head ("berries")\n'),
    ('# ============================================================================================ the run\n',
     '# ============================================================================================ A-R1W7-11 plants\n'
     'def raw_lines_of(i: int, plant: Optional[str] = None) -> List[str]:\n'
     '    """The synthetic book lines of item i (the keys\' heads and amounts). Under an A-R1W7-11 plant, item 0\'s last line\n'
     '    carries a second amount after a separator (A-R1W7-7\'s MULTI_QTY shape)."""\n'
     '    lines = [f"{2 + j} cups {h}" if h != "eggs" else f"{2 + j} {h}" for j, h in enumerate(HEADS)]\n'
     '    if i == 0 and plant in A11_PLANTS:\n'
     '        lines[-1] += ", 6 juniper berries"\n'
     '    return lines\n'
     '\n'
     '\n'
     'def a11_tag_key(key: Dict[str, Any]) -> None:\n'
     '    """A-R1W7-7\'s tag on the key\'s last line (the line raw_lines_of gives a second amount)."""\n'
     '    rep = key["representable"]\n'
     '    rep["why_not"] = list(rep.get("why_not") or []) + ["line2:MULTI_QTY"]\n'
     '    rep["representable"] = False\n'
     '\n'
     '\n'
     'def a11_plant_record(r: Dict[str, Any], plant: str) -> None:\n'
     '    """Record 0 of a CHAT arm: the honest ask (the G1 untaught-requirement sentence naming the tail\'s head), its\n'
     '    CLARIFY or PHANTOM variant, or (K3_A11_WRONG) a wrong number on the tagged key."""\n'
     '    q = [t for t in r["turns"] if t["kind"] == "turn"][-1]\n'
     '    lv = q["loop"]\n'
     '    if plant == "K3_A11_WRONG":\n'
     '        lv["value"] = "1/3"\n'
     '        r["scored_turn"]["value"] = "1/3"\n'
     '        return\n'
     '    noun = r["lesson_records"][0]["product"]\n'
     '    name = "beaten" if plant == "K4_A11_PHANTOM" else A11_TAIL_NAME\n'
     '    status = "CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT" if plant == "K4_A11_CLARIFY" else "UNDETERMINED_CLARIFY"\n'
     '    sentence = (f"I can\'t say yet how much {noun} we can make. I still need one batch where {name} ran out first "\n'
     '                f"while everything else was left over. I didn\'t guess.")\n'
     '    lv.update(status=status, value=None, limiting=None, writes=0, cubes_written=[], receipt_hash="r0",\n'
     '              loop_sentence=sentence)\n'
     '    q.update(reply=sentence, stdout="\\nHELM: " + sentence + "\\n", receipt_hash="r0")\n'
     '    r["scored_turn"].update(status=status, value=None, limiting=None, writes=0, inner_status=status)\n'
     '    r["scored_reply"] = sentence\n'
     '    r["log"][-1].update(status=status, value=None, limiting=None, writes=0)\n'
     '    r["lesson_records"][-1]["status"] = status\n'
     '    r["wide_audit"] = [{"ok": True, "coefficients": 3, "support_slots": 4, "numbers_are_coefficients": True,\n'
     '                        "within_support": True, "factors_pinned": True, "attributes_ok": True, "extra_numbers": 0}]\n'
     '\n'
     '\n'
     '# ============================================================================================ the run\n'),
    ('    if plant == "I14":\n',
     '    if plant in A11_PLANTS:                            # A-R1W7-11: key 0 carries the two-amount tag before the keys are written\n'
     '        a11_tag_key(real_keys[0])\n'
     '    if plant == "I14":\n'),
    ('    C.write_json(exam / "KEYS_CONV_X7.json", {"schema": "helm.r1w7.conv-keys/1", "keys": conv_keys, "synthetic_fixture": True})\n',
     '    C.write_json(exam / "KEYS_CONV_X7.json", {"schema": "helm.r1w7.conv-keys/1", "keys": conv_keys, "synthetic_fixture": True})\n'
     '    if plant != "K4_A11_NO_SAMPLE":                    # A-R1W7-11: a synthetic sample (raw lines; laptop only, beside the keys)\n'
     '        C.write_json(exam / "SAMPLE_REAL_X7.json", {"schema": "helm.r1w7.real-sample/1", "synthetic_fixture": True,\n'
     '                                                    "skips": [], "items": [dict(it, raw_lines=raw_lines_of(i, plant))\n'
     '                                                                           for i, it in enumerate(real_items)]})\n'),
    ('    elif plant == "NEVER_SENT":\n'
     '        on_conv["records"][0]["turns"][0]["text"] = "exit"\n',
     '    elif plant == "NEVER_SENT":\n'
     '        on_conv["records"][0]["turns"][0]["text"] = "exit"\n'
     '    elif plant in A11_PLANTS:                               # A-R1W7-11: record 0, in CHAT_ON, CHAT_ON_REPLAY and CHAT_DIAG alike\n'
     '        for u in real_on:\n'
     '            a11_plant_record(u["records"][0], plant)\n'),
]

# ------------------------------------------------------------------------------------------------ run_tests.py
RUN_TESTS_EDITS = [
    ('"tests_r1w7.test_multi_qty_w7"])   # v7: A-R1W7-7\'s seven tests\n',
     '"tests_r1w7.test_multi_qty_w7",\n'
     '                                                          "tests_r1w7.test_honest_ask_w7"])   # v7: A-R1W7-7\'s seven tests; A-R1W7-11\'s T2 tests\n'),
]

# ------------------------------------------------------------------------------------------------ the preregistration
PREREG_ANCHOR = "\n## 22. Amendment A-R1W7-10 "
SECTION_23 = """
## 23. Amendment A-R1W7-11 (owner's word 2026-10-21: "Exempt from K4 only"; a fresh draw only)

K4 HONEST reads `unexplained_asks_strict_after_a11` = the frozen strict count minus the asks exempted here, and is false
unless `a11_consistent` holds (a recount of the frozen rule equals the frozen strict count, and every exempted ask is one
it counts). An ask is exempted only when, checked in order: (a) the key is ANSWER and carries a `line<i>:MULTI_QTY` tag;
(b) RB-W1T's `unexplained_ask` counts it; (c) the question's status is `UNDETERMINED_CLARIFY` on the wide path; (d) the
question's loop sentence is HELM's untaught-requirement sentence, its names count exactly the untaught slots of the one
wide recipe whose learned coefficients equal the key's line count, and its dish is the lessons' dish; (e) each name's head
word is the head of a second-amount tail on a tagged line (read from `SAMPLE_REAL_X7.json` with the frozen grammar), not a
unit, a note word, a participle or a key line's head. These checks are necessary, not sufficient; their limits are listed
in the design (DESIGN_V73_A11.md 3.2). Each exempted item is listed as `FLAG_FOR_HUMAN_REVIEW`. The strict count is still
reported. The question score, K1, K3, NH-CHAT, P, N, every gate and instrument row are unchanged; a wrong number stays
WRONG. No reading of c51–c56 is redone.

### 23.1 Correction to section 19.1

Section 19.1 says a tagged item "then scores `NOT_SCORED` (an undetermined key), exactly as recipes with a range, an
approximate amount, an odd form or a unit outside the top-20 table already do". That premise is false in the frozen code.
`rbw1t.keys_rbw1t.score_question` returns `NOT_SCORED` only when the key's answer word is not ANSWER and never reads
`representable`; `r1w6.score_w6.score_real` reads `representable` only for K1's bar (`rep_answer`, `fully_learned_rep`);
`unexplained_ask` never reads it. So A-R1W7-7 as built changed only K1's denominator: a tagged ANSWER key, like every
not-representable ANSWER key, kept its question score and stayed in K4's strict count. The "would have been `NOT_SCORED`"
statements of 19.4 and 19.5 are `WITHDRAWN` as stated; those items stay scored for their question. The 19.5 counts
themselves (6 of 128 tagged; representable 120 to 114) stand. The error is the builder's (spec §7.119). Readings c51–c56
stand as read.
"""


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_lf(p: Path) -> str:
    return p.read_bytes().decode("utf-8")


def plan_edits(text: str, edits, label: str, problems: list) -> str:
    """Every anchor exactly once, in order; returns the edited text (nothing is written here)."""
    for old, new in edits:
        n = text.count(old)
        if n != 1:
            problems.append(f"{label}: anchor found {n} times (must be 1): {old.splitlines()[0][:90]!r}")
            continue
        text = text.replace(old, new, 1)
    return text


def main(argv) -> int:
    if not argv or len(argv) > 2 or (len(argv) == 2 and argv[1] != "--plants-only"):
        print(__doc__)
        return 2
    root = Path(argv[0]).resolve()
    plants_only = len(argv) == 2
    paths = {"score": root / "r1w7" / "score_w7.py", "merge": root / "r1w7" / "merge_r1w7.py",
             "fixture": root / "tests_r1w7" / "fixture_run.py", "run_tests": root / "tests_r1w7" / "run_tests.py",
             "prereg": root / "PREREGISTRATION_R1W7.md"}
    if not all(p.is_file() for p in paths.values()) or not (root / "r1w7" / "multi_qty_w7.py").is_file():
        print("REFUSED: not a wave-7 package root carrying A-R1W7-7:", root)
        return 2
    problems: list = []
    # content checks (G-8): the five targets are the v9 bytes, and the tree's own freeze pins say the same
    try:
        freeze = json.loads((root / "PACKAGE_FREEZE.json").read_text(encoding="utf-8")).get("members") or {}
    except Exception as exc:                          # no freeze, or unreadable: refuse
        freeze = {}
        problems.append(f"PACKAGE_FREEZE.json unreadable: {type(exc).__name__}")
    rel_of = {k: p.relative_to(root).as_posix() for k, p in paths.items()}
    for k, rel in rel_of.items():
        got = sha(paths[k])
        if got != V9_TARGET_SHA256[rel]:
            problems.append(f"{rel}: sha256 {got[:12]}... is not the v9 member {V9_TARGET_SHA256[rel][:12]}...")
        if (freeze.get(rel) or {}).get("sha256") != got:
            problems.append(f"{rel}: not equal to the tree's own PACKAGE_FREEZE.json member pin")
    texts = {k: read_lf(p) for k, p in paths.items()}
    for k, t in texts.items():
        if "\r" in t:
            problems.append(f"{k}: CR characters present (the package files are LF)")
    if "A11_PLANTS" in texts["fixture"]:
        problems.append("fixture_run.py already carries the A-R1W7-11 plants")
    new = {"fixture": plan_edits(texts["fixture"], FIXTURE_EDITS, "fixture_run.py", problems)}
    if not plants_only:
        if "honest_ask_w7" in texts["score"] or "A-R1W7-11" in texts["merge"]:
            problems.append("score_w7.py / merge_r1w7.py already carry the amendment")
        for rel in NEW_FILES:
            if (root / rel).exists():
                problems.append(f"{rel} already exists")
        for src in NEW_FILES.values():
            if not (HERE / src).is_file():
                problems.append(f"source file missing beside this tool: {src}")
            elif sha(HERE / src) != NEW_FILE_SHA256[src]:
                problems.append(f"source file beside this tool is not the listed bytes (AMENDMENT section 7): {src}")
        pre = texts["prereg"]
        if pre.count(PREREG_ANCHOR) != 1:
            problems.append(f"PREREGISTRATION_R1W7.md: section 22 heading found {pre.count(PREREG_ANCHOR)} times (must be 1)")
        elif "\n## " in pre[pre.index(PREREG_ANCHOR) + len(PREREG_ANCHOR):]:
            problems.append("PREREGISTRATION_R1W7.md: section 22 is not the last section (section 23 must follow it)")
        if "\n## 23." in pre or "A-R1W7-11" in pre:
            problems.append("PREREGISTRATION_R1W7.md already carries section 23 / A-R1W7-11")
        if not pre.endswith("\n"):
            problems.append("PREREGISTRATION_R1W7.md does not end with a newline")
        new["score"] = plan_edits(texts["score"], SCORE_EDITS, "score_w7.py", problems)
        new["merge"] = plan_edits(texts["merge"], MERGE_EDITS, "merge_r1w7.py", problems)
        new["run_tests"] = plan_edits(texts["run_tests"], RUN_TESTS_EDITS, "run_tests.py", problems)
        new["prereg"] = pre + SECTION_23
    if problems:
        print("REFUSED (nothing written):")
        for p in problems:
            print("  -", p)
        return 4
    plan = []                                         # (final path, bytes)
    if not plants_only:
        for rel, src in NEW_FILES.items():
            plan.append((root / rel, (HERE / src).read_bytes()))
    for k, text in new.items():
        plan.append((paths[k], text.encode("utf-8")))
    parts = []
    for p, data in plan:                              # phase 1: every file as <name>.partial
        part = p.with_name(p.name + ".partial")
        part.write_bytes(data)
        parts.append((part, p))
    written = []
    for part, p in parts:                             # phase 2: rename each into place
        os.replace(part, p)
        written.append(p)
    for p in written:
        print(sha(p), p.relative_to(root).as_posix())
    print("APPLIED:", "plants only (fixture_run.py)" if plants_only else "A-R1W7-11 (7 files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
