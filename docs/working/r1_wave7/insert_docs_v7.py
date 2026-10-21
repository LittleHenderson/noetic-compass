"""Builder tool (NOT sealed): insert the v7 docs into the repo worktree: spec section 7.112 before "## 8. THE TWO CLAIMS", one
follow-up line at the end of 7.108 and of 7.111, the section 11 row at the top of the change log, the CHANGELOG entry at the top,
and a curated hub row for 7.112 in helm_hub/build_hub.py. Every edit is an exact once-only replacement.

    python -X utf8 -B -I insert_docs_v7.py <repo worktree>
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


body = (B / "SPEC_7_112_BODY.md").read_text(encoding="utf-8")
row = (B / "SPEC_11_ROW_V7.md").read_text(encoding="utf-8")
entry = (B / "CHANGELOG_ENTRY_V7.md").read_text(encoding="utf-8")
t = SPEC.read_text(encoding="utf-8")
if "### 7.112 " in t:
    raise SystemExit("7.112 already present")
# 7.112 before the two claims
once(SPEC, "\n## 8. THE TWO CLAIMS", "\n" + body.rstrip("\n") + "\n\n## 8. THE TWO CLAIMS")
# follow-up at the end of 7.111 (its last bullet ends the section; the new 7.112 heading follows after a blank line)
once(SPEC, "no-cue paraphrases (\"has seen better days\") are ignored as not a face — the wave-3 lexicon's own limit, unchanged.\n",
     "no-cue paraphrases (\"has seen better days\") are ignored as not a face — the wave-3 lexicon's own limit, unchanged.\n"
     "- **Follow-up (2026-10-21, §7.112):** this cut was sealed as wave 7 v7 (zip `42c044a9…`, 167 files, the host's list 12 names "
     "`Ran 271, OK`); on the builder's practice dialogues limit (a) showed as 4 WRONG answers where the v6 reader asked (all "
     "`S1_WISDOM_STATED`, face ingredient an everyday name) beside 16 asks turned RIGHT; K3 missed on practice; `FLAG_FOR_HUMAN_REVIEW`; "
     "real recipes unchanged.\n")
# follow-up at the end of 7.108
once(SPEC, "`x7v6_custody/`, `approval_v6/`, `make_c54_kit.py`, `C54_VALUES.json`; repo copies `docs/working/r1_wave7/`.\n",
     "`x7v6_custody/`, `approval_v6/`, `make_c54_kit.py`, `C54_VALUES.json`; repo copies `docs/working/r1_wave7/`.\n"
     "- **Follow-up (2026-10-21, §7.112):** v6 is `VOID_SUPERSEDED_BY_V7` for any further run (this record stands); the two asks' "
     "instrument fix (A-R1W7-7) and the reader-gap build (§7.111) are sealed in v7 (zip `42c044a9…`, line `CHAT WAVE 5 at 1 USD`), "
     "NOT LAUNCHED; v7's practice run missed K3 on 4 dialogues (a negative kept in §7.112).\n")
# section 11 row at the top
once(SPEC, "## 11. CHANGE LOG\n\n| Date | Change | Commit / artifact |\n|---|---|---|\n",
     "## 11. CHANGE LOG\n\n| Date | Change | Commit / artifact |\n|---|---|---|\n" + row.rstrip("\n") + "\n")
# changelog entry at the top (after the intro paragraph)
once(CL, "This file records cross-cutting campaign milestones.\n\n", "This file records cross-cutting campaign milestones.\n\n" + entry.rstrip("\n") + "\n\n")
# hub row
hub_row = ('    "7.112": ("packet", "null", "Wave 7, the fifth round\'s packet: v6 resealed as v7 with exactly four changes. HELM is cut at '
           'the merged reader-gap build (the wide brain\'s reader now reads the clause of a stock sentence and applies a stated face at the '
           'question); the machine\'s own test list grew to 12 files and was run from the seal (271 tests, OK); the custodian\'s two-amount '
           'rule is applied (6 of 128 practice recipes are set aside as not scorable); the last exam\'s ids are excluded, fresh number ranges, '
           'a new owner line CHAT WAVE 5 at 1 USD. Not launched. One practice finding is kept on record: on the builder\'s practice dialogues the '
           'new reader turned 16 earlier questions into right answers and 4 into wrong ones (a stated weakness of an everyday ingredient such as '
           'flour was not counted), so the safety mark was missed on practice; real recipes did not move. The owner decides whether to fix that '
           'first.", "No claim from the packet itself; the practice finding is flagged for the owner, not a result."),\n')
once(HUB, '    "7.110": ("packet", "null",', hub_row + '    "7.110": ("packet", "null",')
for p in (SPEC, CL, HUB):
    raw = p.read_bytes()
    if b"\x08" in raw:
        raise SystemExit("stray backspace byte in " + p.name)
print("inserted")
