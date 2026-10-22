"""Builder tool (NOT sealed): insert the v9 docs into the repo worktree: spec section 7.118 before "## 8. THE TWO CLAIMS", one
follow-up line at the end of 7.117, the section 11 row at the top of the change log, the CHANGELOG entry at the top, and a curated
hub row for 7.118 in helm_hub/build_hub.py. Every edit is an exact once-only replacement.

    python -X utf8 -B -I insert_docs_v9.py <repo worktree>
"""
import sys
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
B = Path(__file__).resolve().parent
SPEC = REPO / "docs" / "CAS_HARNESS_SPEC_SHEET.md"
CL = REPO / "CHANGELOG.md"
HUB = REPO / "helm_hub" / "build_hub.py"


def once(p, old, new):
    t = p.read_bytes().decode("utf-8")
    if t.count(old) != 1:
        raise SystemExit(f"{p.name}: anchor not found exactly once: {old[:80]!r}")
    p.write_bytes(t.replace(old, new).encode("utf-8"))


body = (B / "SPEC_7_118_BODY.md").read_text(encoding="utf-8")
row = (B / "SPEC_11_ROW_V9.md").read_text(encoding="utf-8")
entry = (B / "CHANGELOG_ENTRY_V9.md").read_text(encoding="utf-8")
t = SPEC.read_text(encoding="utf-8")
if "### 7.118 " in t:
    raise SystemExit("7.118 already present")
if "### 7.117 " not in t:
    raise SystemExit("7.117 is missing: not the thread head")
# the follow-up at the end of 7.117 (its last bullet), then 7.118, then the two claims
once(SPEC, "(`CUSTODIAN_SHAPE_FACTS_C55*.json`, `…_MECHANISM.json`).\n\n## 8. THE TWO CLAIMS",
     "(`CUSTODIAN_SHAPE_FACTS_C55*.json`, `…_MECHANISM.json`).\n"
     "- **Follow-up (2026-10-21, §7.118):** the v9 reseal on this fix is done (zip `ad3fb98c…`, cut `55cda1e2`, the host's 12 names "
     "`Ran 280, OK (skipped=1)`, exclusion block `X7v8_c55`, bands 2,036 / 2,038 / 2,040 M); its practice run from the seal reads 0 WRONG "
     "in every dialogue family (CONV `CHAT_ON` 63 / 0 / 1), every mark true, and not one number moved against v8's run10 (the practice "
     "dialogues do not contain c55's shapes); v8 `VOID_SUPERSEDED_BY_V9`; NOT LAUNCHED; the line `CHAT WAVE 6 at 1 USD` is proposed, "
     "not approved.\n\n"
     + body.rstrip("\n") + "\n\n## 8. THE TWO CLAIMS")
# section 11 row at the top
once(SPEC, "## 11. CHANGE LOG\n\n| Date | Change | Commit / artifact |\n|---|---|---|\n",
     "## 11. CHANGE LOG\n\n| Date | Change | Commit / artifact |\n|---|---|---|\n" + row.rstrip("\n") + "\n")
# changelog entry at the top (after the intro paragraph)
once(CL, "This file records cross-cutting campaign milestones.\n\n", "This file records cross-cutting campaign milestones.\n\n" + entry.rstrip("\n") + "\n\n")
# hub row (plain words only; no banned terms; same shape as the 7.114 row)
hub_row = ('    "7.118": ("packet", "null", "Wave 7, the sixth round\'s packet, frozen and fingerprinted again as v9 with exactly three '
           'changes on v8: HELM is cut at the merged reader fix of 7.117 (a sentence shaped like a stated fact about an ingredient HELM '
           'does not hold now makes it ask and hold its answer; plural and spelling forms of a held name are found; a measure phrase such '
           'as \\"a dash of pepper\\" after a comma is its own line), the ids of the fifth round\'s exam can never be drawn again, and the '
           'number ranges for the exam draw are fresh; the line the owner would sign, CHAT WAVE 6 at 1 USD, is proposed only. The '
           'machine\'s own test list of 12 files was run from the frozen copy (280 tests, OK). On the builder\'s practice dialogues the chat '
           'gets 63 of 64 right with 0 wrong and asks on 1, exactly as v8 did, because none of the practice dialogues has the shapes the '
           'fifth round got wrong; the loop driven directly 59 right, 0 wrong; real recipes unchanged; every mark true. Not launched.", '
           '"No claim from the packet itself; the practice numbers are facts about practice data, not a result, and they cannot show the '
           'fix works."),\n')
once(HUB, '    "7.114": ("packet", "null",', hub_row + '    "7.114": ("packet", "null",')
for p in (SPEC, CL, HUB):
    raw = p.read_bytes()
    if b"\x08" in raw:
        raise SystemExit("stray backspace byte in " + p.name)
print("inserted")
