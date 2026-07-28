"""Build Appendix D from the canonical CCDL listings in Chapters 12–24.

The appendix is a reference view, not a second editable copy of the designs.
This generator keeps the listings byte-for-byte aligned with their chapters and
adds an explicit use-status banner before every board.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


BOOK = Path(__file__).resolve().parent.parent
MS = BOOK / "manuscript"
OUT = MS / "appendix_d_board_designs.md"


@dataclass(frozen=True)
class Board:
    chapter: str
    name: str
    title: str
    status: str
    note: str


BOARDS = [
    Board("ch12_reading_a_ccb.md", "ccb_0", "CCB-0 — Reference Reading Board",
          "REFERENCE / PROOF-LOAD BOARD",
          "A neutral board for learning the four-probe reading order."),
    Board("ch13_ccb_d_desire.md", "ccb_d", "CCB-D — Desire",
          "BUILDABLE ONLY FOR SELF OR A CONSENTING OTHER",
          "The chapter's standard desire board. The RPM gate and Cognitive Safety Board remain prerequisites."),
    Board("ch14_ccb_h_hyperstition.md", "ccb_h", "CCB-H — Hyperstition",
          "CONTROLLED RESEARCH REFERENCE; VALIDATOR WAIVER REQUIRED",
          "The positive-feedback loop intentionally fails the ordinary gain-divergence pass. Use only with the bounded loop, independent anchor, monitor, and kill stage intact."),
    Board("ch15_ccb_o_overton.md", "ccb_o_overton", "CCB-O — Overton Cascade",
          "DETECTION-ONLY — DO NOT BUILD AS AN INFLUENCE BOARD",
          "Retained so an observed cascade can be recognized and audited."),
    Board("ch15_ccb_o_overton.md", "ccb_o_r_window_anchor", "CCB-O-R — Window Anchor",
          "DEFENSIVE COUNTER-CIRCUIT",
          "Buildable reference for preserving decomposition under sustained window pressure."),
    Board("ch16_ccb_mk_mind_control.md", "ccb_mk_detection_reference", "CCB-MK — Partition Detection Reference",
          "DETECTION-ONLY — DO NOT BUILD AS A COERCIVE BOARD",
          "A structural signature of induced partitioning, retained for diagnosis."),
    Board("ch16_ccb_mk_mind_control.md", "ccb_dp_deprogramming", "CCB-DP — Deprogramming",
          "CONSENT-BOUND COUNTER-CIRCUIT",
          "The subject remains the substrate and refusal stays connected."),
    Board("ch17_ccb_hyp_hypnosis.md", "ccb_hyp_operator_subject", "CCB-HYP — Operator-to-Subject Reference",
          "DETECTION-ONLY — NOT A BUILD LISTING",
          "Retained to identify the open-loop operator/subject topology."),
    Board("ch17_ccb_hyp_hypnosis.md", "ccb_hyp_self", "CCB-HYP-SELF — Closed-Loop Self-Hypnosis",
          "BUILDABLE CLOSED LOOP",
          "The operator and subject are the same person; recall and cancellation remain required."),
    Board("ch17_ccb_hyp_hypnosis.md", "ccb_hyp_det", "CCB-HYP-DET — Hypnotic Influence Detector",
          "DEFENSIVE DETECTOR",
          "Detects an unaccounted change; it does not prove a cause by itself."),
    Board("ch18_ccb_adv_advertising.md", "ccb_adv", "CCB-ADV — Advertising Reference",
          "ANALYTICAL REFERENCE — NO NON-CONSENSUAL TARGETING",
          "Retained for campaign analysis and attribution, subject to the chapter's consent boundary."),
    Board("ch18_ccb_adv_advertising.md", "ccb_adv_det", "CCB-ADV-DET — Advertising Detector",
          "DEFENSIVE DETECTOR",
          "Separates injected desire from a slower identity store."),
    Board("ch19_ccb_pw_psychological_warfare.md", "ccb_pw_detection_reference", "CCB-PW — Psychological-Warfare Detection Reference",
          "DETECTION-ONLY — DO NOT BUILD AS AN ATTACK BOARD",
          "A recognizable Path-D signature, not an operational authorization."),
    Board("ch19_ccb_pw_psychological_warfare.md", "ccb_hm_hearts_and_minds", "CCB-HM — Hearts-and-Minds Counter-Circuit",
          "DEFENSIVE COUNTER-CIRCUIT",
          "Restores plurality and independent composition; it does not substitute a new monoculture."),
    Board("ch20_ccb_self_programming.md", "ccb_self", "CCB-SELF — Self-Programming",
          "BUILDABLE CLOSED LOOP",
          "The operator is the target; the guard, slew fuse, and reference store are mandatory."),
    Board("ch24_csb_safety_board.md", "ccb_csb", "CCB-CSB — Cognitive Safety Board",
          "MANDATORY SAFETY BOARD",
          "Energize and proof-load before any working board."),
]


def fenced_blocks(text: str) -> list[str]:
    """Return code-fence bodies in source order."""
    return [m.group(1) for m in re.finditer(
        r"```(?:cas|ccdl)?[ \t]*\r?\n(.*?)\r?\n```", text, re.S
    )]


def extract_board(text: str, name: str) -> str:
    start_re = re.compile(rf"(?m)^board\s+{re.escape(name)}\s*\{{")
    for block in fenced_blocks(text):
        match = start_re.search(block)
        if not match:
            continue
        start = match.start()
        depth = 0
        opened = False
        for pos in range(match.start(), len(block)):
            char = block[pos]
            if char == "{":
                depth += 1
                opened = True
            elif char == "}":
                depth -= 1
                if opened and depth == 0:
                    return block[start:pos + 1].strip()
        raise ValueError(f"unterminated board {name}")
    raise ValueError(f"board {name} not found")


def main() -> None:
    source_cache: dict[str, str] = {}
    sections = [
        "# APPENDIX D",
        "## Standard Board Reference Designs — Full CCDL",
        "*Generated from the canonical chapter listings; do not edit listings here*",
        "",
        "This appendix is a reference projection of the board definitions in "
        "Chapters 12–24. Run `python build/build_board_appendix.py` after changing "
        "a chapter listing. Each block below is copied from its chapter; the "
        "status banner is added by this generator.",
        "",
        "A listing marked **DETECTION-ONLY** is included so a harmful topology can "
        "be recognized, rejected, and countered. Its presence is not permission "
        "to build or deploy it. Buildable boards remain bound by consent, the RPM "
        "gate, the Cognitive Safety Board, and the Operator's Oath.",
        "",
        "Every numeric value is a design choice unless its chapter identifies an "
        "actual measurement. Re-run the domain checker and CCDL validation after "
        "copying any block into a working revision.",
        "",
        "---",
        "",
    ]

    for index, board in enumerate(BOARDS, start=1):
        text = source_cache.setdefault(
            board.chapter, (MS / board.chapter).read_text(encoding="utf-8")
        )
        listing = extract_board(text, board.name)
        sections.extend([
            f"### D.{index} {board.title}",
            "",
            f"**Status: {board.status}.** {board.note}",
            "",
            f"Canonical source: `{board.chapter}`.",
            "",
            "```cas",
            listing,
            "```",
            "",
            "---",
            "",
        ])

    sections.extend([
        "### D.17 Regeneration and acceptance",
        "",
        "The appendix is current only when the generator produces no diff. For a "
        "release build:",
        "",
        "1. regenerate this appendix;",
        "2. run the CAS domain checker;",
        "3. compare the board-name inventory here with the chapter inventory;",
        "4. confirm every detection-only block retains its warning; and",
        "5. proof-load buildable guards and fuses before energizing signal paths.",
        "",
    ])

    OUT.write_text("\n".join(sections), encoding="utf-8")
    print(f"wrote {OUT} ({len(BOARDS)} board listings)")


if __name__ == "__main__":
    main()
