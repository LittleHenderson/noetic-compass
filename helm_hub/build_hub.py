#!/usr/bin/env python3
"""HELM Hub builder: a living, static info hub for HELM, generated from the sources of truth.

Run:  python helm_hub/build_hub.py            (writes helm_hub/site/)
      python helm_hub/build_hub.py --check    (build, then run the jargon lint, link check and secret scan)

Standard library only. No network. Reads the spec sheet, the dictionary, the roadmap and its status
correction, CHANGELOG.md, the HELM UI README and demo, the X-REAL source pins (all in the repo), plus
off-repo records under the Codex folder (the AWS ledger totals, the run records, the owner-approval
headings, the language-map coverage report). Set HELM_HUB_CODEX to point at another Codex folder.
Missing off-repo files never stop the build: the page says the source was not available.

The build fails (exit 1) when the jargon lint, the link check or the secret scan fails.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    _PACIFIC = ZoneInfo("America/Los_Angeles")
except Exception:  # pragma: no cover - fallback when tz data is missing
    _PACIFIC = None

HUB = Path(__file__).resolve().parent
REPO = HUB.parent
SITE = HUB / "site"
CODEX = Path(os.environ.get("HELM_HUB_CODEX", r"C:\Users\wakil\Documents\Codex"))

SPEC = REPO / "docs" / "CAS_HARNESS_SPEC_SHEET.md"
DICT = REPO / "docs" / "reference" / "CAS_HELM_DICTIONARY.md"
ROAD = REPO / "docs" / "working" / "HELM_CAPABILITIES_ROADMAP_AND_DEVELOPMENTAL_STAGES.md"
CORR = REPO / "docs" / "working" / "HELM_CAPABILITIES_ROADMAP_STATUS_CORRECTION_20261018.md"
CHLOG = REPO / "CHANGELOG.md"
UI_README = REPO / "helm_ui" / "README.md"
UI_DEMO = REPO / "helm_ui" / "demo" / "index.html"
XR_SOURCES = REPO / "docs" / "working" / "xreal" / "SOURCES_PINNED.json"
XR_PREREG = REPO / "docs" / "working" / "xreal" / "PREREGISTRATION_X_REAL.md"
LEDGER = CODEX / "AWS_COMBINED_ALLOCATION_CURRENT.json"
APPROVALS = CODEX / "2026-10-18" / "OWNER_APPROVALS_20261018.md"
COVERAGE = CODEX / "2026-10-19" / "language_map_coverage_v1" / "COVERAGE.md"
RUN_DIRS = [CODEX / "2026-10-19", CODEX / "2026-10-18"]

FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500"
         "&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap")

# --------------------------------------------------------------------------------------------
# Reading sources (scrubbed: e-mail addresses never reach the output)
# --------------------------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")
MISSING: list[str] = []


def rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(p)


def read(p: Path) -> str:
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        MISSING.append(rel(p))
        return ""
    return EMAIL_RE.sub("[e-mail removed]", t)


def sha256_file(p: Path) -> str:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return "unavailable"


def noemoji(s: str) -> str:
    return re.sub(r"\s{2,}", " ", EMOJI_RE.sub("", s)).strip()


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def md(s: str) -> str:
    """Inline markdown (code, bold, italic, links) to HTML; everything escaped first."""
    s = noemoji(s)
    parts = re.split(r"(`[^`]*`)", s)
    out = []
    for part in parts:
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            out.append("<code>" + esc(part[1:-1]) + "</code>")
            continue
        t = esc(part)
        t = re.sub(r"\[([^\]]+)\]\([^)]+\)", lambda m: m.group(1), t)
        t = re.sub(r"\*\*(.+?)\*\*", lambda m: "<strong>" + m.group(1) + "</strong>", t)
        t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", lambda m: "<em>" + m.group(1) + "</em>", t)
        out.append(t)
    return "".join(out)


def md_table(text: str, after: str) -> list[list[str]]:
    """Rows (header first) of the first markdown table after the line that starts with `after`."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(after)), None)
    if start is None:
        return []
    rows: list[list[str]] = []
    for ln in lines[start + 1:]:
        if ln.startswith("|"):
            body = ln.strip().strip("|").replace("\\|", "\x00")
            cells = [c.strip().replace("\x00", "|") for c in body.split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            rows.append(cells)
        elif rows:
            break
    return rows


def html_table(rows: list[list[str]], cls: str = "", verbatim: bool = True) -> str:
    if not rows:
        return '<p class="muted">Source table not available.</p>'
    head, body = rows[0], rows[1:]
    v = " verbatim" if verbatim else ""
    t = [f'<div class="tablewrap{v}"><table class="{cls}"><thead><tr>']
    t += [f"<th>{md(c)}</th>" for c in head]
    t.append("</tr></thead><tbody>")
    for r in body:
        t.append("<tr>" + "".join(f"<td>{md(c)}</td>" for c in r) + "</tr>")
    t.append("</tbody></table></div>")
    return "".join(t)


# --------------------------------------------------------------------------------------------
# Spec sheet
# --------------------------------------------------------------------------------------------
def spec_sections(text: str) -> dict[str, dict]:
    secs: dict[str, dict] = {}
    cur = None
    for line in text.splitlines():
        m = re.match(r"^### (7\.\d+) (.*)$", line)
        if m:
            cur = m.group(1)
            secs[cur] = {"title": m.group(2).strip(), "body": []}
            continue
        if re.match(r"^#{1,3} ", line):
            cur = None
            continue
        if cur:
            secs[cur]["body"].append(line)
    for v in secs.values():
        v["text"] = "\n".join(v["body"])
    return secs


def spec_legend(text: str) -> tuple[list[tuple[str, str, str]], str]:
    rows = []
    block = text.split("## 3. CLAIM-STATUS LEGEND", 1)[-1].split("\n---", 1)[0]
    for ln in block.splitlines():
        m = re.match(r"^\| \*\*(.+?)\*\* \| (.*?) \| (.*?) \|\s*$", ln)
        if m:
            rows.append((m.group(1), m.group(2), m.group(3)))
    m = re.search(r"^\*\*Prohibited words in every surface, always:\*\*(.*)$", block, re.M)
    return rows, (m.group(1).strip() if m else "")


def sec_num(k: str) -> int:
    return int(k.split(".")[1])


def sec_line(sec: dict, label_re: str) -> str:
    """Text after a bold label on one line inside a section body, e.g. NOT LICENSED."""
    m = re.search(r"^\s*(?:- )?\*\*" + label_re + r"[^*]*\*\*:?\s*(.*)$", sec.get("text", ""), re.M)
    return m.group(1).strip() if m else ""


def sec_quote(sec: dict, marker: str) -> str:
    t = sec.get("text", "")
    i = t.find(marker)
    if i < 0:
        return ""
    m = re.search(r'"([^"]{40,}?)"', t[i:])
    return m.group(1) if m else ""


# --------------------------------------------------------------------------------------------
# Dictionary
# --------------------------------------------------------------------------------------------
ENTRY_RE = re.compile(r"^\*\*(.+?)\*\*(.*?) — \[(.+?)\]\s*$")


def dict_entries(text: str) -> list[dict]:
    part = text.split("## A–Z entries", 1)[-1].split("## Terms with no written definition", 1)[0]
    out: list[dict] = []
    cur = None
    for ln in part.splitlines():
        m = ENTRY_RE.match(ln)
        if m:
            cur = {"term": m.group(1).strip(), "alias": m.group(2).strip(), "cat": m.group(3).strip(), "lines": []}
            out.append(cur)
            continue
        if cur is None:
            continue
        if ln.startswith("- "):
            mm = re.match(r"^- \*(.+?):\*\s*(.*)$", ln)
            if mm:
                cur["lines"].append((mm.group(1), mm.group(2)))
            else:
                cur["lines"].append(("", ln[2:]))
        elif ln.strip() and not ln.startswith("#") and not ln.startswith("**"):
            if cur["lines"]:
                lab, t = cur["lines"][-1]
                cur["lines"][-1] = (lab, t + " " + ln.strip())
            else:
                cur["lines"].append(("", ln.strip()))
    return out


def dict_find(entries: list[dict], term: str) -> dict | None:
    t = term.lower().strip("`")
    for e in entries:
        if e["term"].lower().strip("`") == t:
            return e
    return None


def dict_line(entries: list[dict], term: str, label_start: str) -> str:
    e = dict_find(entries, term)
    if not e:
        return ""
    for lab, t in e["lines"]:
        if lab.lower().startswith(label_start.lower()):
            return t
    return ""


def canonical_quote(entries: list[dict], term: str) -> str:
    t = dict_line(entries, term, "Definition (canonical")
    m = re.match(r'^"(.+?)"\s*—', t)
    return m.group(1) if m else ""


# --------------------------------------------------------------------------------------------
# Off-repo records
# --------------------------------------------------------------------------------------------
def ledger_totals() -> dict:
    t = read(LEDGER)
    if not t:
        return {}
    try:
        d = json.loads(t)
    except ValueError:
        return {}
    keep = ("ceiling_usd", "combined_allocation_usd", "unreserved_usd", "utc", "last_jobs")
    return {k: d.get(k) for k in keep}


def run_records() -> list[dict]:
    out = []
    files = []
    for d in RUN_DIRS:
        if d.exists():
            files += sorted(d.rglob("RUN_RESULT_*.md"))
        else:
            MISSING.append(str(d))
    for f in files:
        t = read(f)
        if not t:
            continue
        first = t.splitlines()[0].lstrip("# ").strip() if t else f.name
        job = re.search(r"\bjob (c\d+[a-z0-9-]*)", first) or re.search(r"_(C\d+)\.md$", f.name)
        jid = job.group(1).lower() if job else "unavailable"
        m = re.search(r"(?:Charge|Cost)\b.{0,320}?\*\*([0-9]+\.[0-9]+) USD\*\*", t, re.S)
        inst = re.search(r"\b((?:m6i|t3|g5|g4dn)\.[0-9a-z]+)\b", t)
        date = re.search(r"(2026-\d\d-\d\d)", first) or re.search(r"(2026-\d\d-\d\d)", t)
        out.append({
            "file": f, "title": noemoji(first), "job": jid,
            "charge": m.group(1) if m else "unavailable",
            "instance": inst.group(1) if inst else "unavailable",
            "date": date.group(1) if date else "unavailable",
        })
    out.sort(key=lambda r: (r["date"], r["job"]))
    return out


def approval_headings() -> list[tuple[str, str]]:
    t = read(APPROVALS)
    out = []
    for ln in t.splitlines():
        if ln.startswith("## "):
            h = noemoji(ln[3:].strip())
            m = re.search(r"\((2026-\d\d-\d\d[^)]*)\)", h)
            when = m.group(1) if m else "2026-10-18"
            if len(h) > 170:
                h = h[:167].rstrip() + "..."
            out.append((when, h))
    return out


# --------------------------------------------------------------------------------------------
# Jargon: every term below must be explained on first use on every page (except the glossary)
# --------------------------------------------------------------------------------------------
TERMS: dict[str, tuple[str, int, str]] = {
    # key: (regex, flags, plain explanation)
    "CAS": (r"\bCAS\b", 0, "the Cognitive Architecture System, the project's framework for describing how any mind works"),
    "Noetic": (r"\bNoetics?\b", 0, "one of ten basic moves a mind makes with Ideas, written ^0 to ^9"),
    "Drive": (r"\bDrives?\b(?![- ]loop)", 0, "one of seven core motivations, F1 Unity to F7 Purpose"),
    "Domain": (r"\bDomains?\b", 0, "one of four levels a thought works at: Principled, Cognitive, Evaluative, Operational"),
    "Register": (r"\bRegisters?\b", 0, "the tone of an operation: Transcendent, Analytical, Affective or Embodied"),
    "recipe": (r"\brecipes?\b", re.I, "a written rule saying how much of each ingredient one unit of an outcome needs"),
    "recipe brain": (r"\brecipe brains?\b", re.I, "HELM's brain made of written recipes and exact arithmetic instead of a neural network"),
    "limiting reagent": (r"\blimiting (?:reagent|ingredient)s?\b", re.I, "the ingredient that runs out first and so caps how much can be made"),
    "RPM Gate": (r"\bRPM[ _]gate\b", re.I, "HELM's one gate: it lets a step go ahead, sends it to repair, or refuses, and lets the brain say it cannot tell"),
    "UNDETERMINED": (r"\bUNDETERMINED\b", 0, "HELM's honest 'I cannot tell', used when something it needs is missing"),
    "CLARIFY": (r"\bCLARIFY\b", 0, "HELM asking a question instead of guessing, with nothing saved"),
    "receipt": (r"\breceipt(?:s|ed)?\b", re.I, "the record a saved fact leaves behind, with a fingerprint, so it can be checked later"),
    "round trip": (r"\bround[- ]trips?\b", re.I, "turning a checked statement into English and back; the result must equal the start"),
    "CCE": (r"\bCCE\b", 0, "Controlled Core English, a strict small form of English that converts to CAS and back exactly"),
    "Unity Eye": (r"\bUnity Eye\b|\bthe Eye\b|\bEYE_(?:SCAN|PAIRING)\b", 0, "a small watcher that looks over HELM, reports and whispers, and never writes"),
    "whisper": (r"\bwhisper(?:s|ed|ing)?\b", re.I, "a typed nudge from the Eye that HELM may ignore; it never changes a stored fact"),
    "custodian": (r"\bcustodians?\b", re.I, "a separate session that builds and seals each exam so the builder never sees it"),
    "sealed": (r"\bseal(?:ed|s|ing)?\b", re.I, "frozen and fingerprinted before the run, so nothing can be changed after the fact"),
    "frozen reader": (r"\bfrozen readers?\b", re.I, "the scoring program, sealed before the run, that alone writes the verdict"),
    "hard gate": (r"\bhard gates?\b|\bHARD_GATES_PASS\b", re.I, "a must-hold check; if one fails, the whole run counts as a failure"),
    "status word": (r"\bstatus words?\b", re.I, "the frozen reader's one-word verdict for a part, such as EARNED_KEEP"),
    "EARNED_KEEP": (r"EARNED_KEEP", 0, "a status word meaning that switching the part off made results worse, so it stays"),
    "claim status": (r"\bclaim status(?:es)?\b", re.I, "what may be said about a result, using only the words of the spec sheet's legend"),
    "claim ceiling": (r"\bclaim ceilings?\b", re.I, "the widest world a claim covers; nothing outside it is claimed"),
    "SYNTHETIC_ONLY": (r"SYNTHETIC_ONLY", 0, "a claim ceiling: the result holds on made-up test worlds only"),
    "NAMED_CORPORA_ONLY": (r"NAMED_CORPORA_ONLY", 0, "a claim ceiling: the result holds on the named public text collections only"),
    "synthetic world": (r"\bsynthetic worlds?\b", re.I, "a made-up test world built by a program, with known right answers"),
    "LICENSED": (r"\bLICENSED\b", 0, "a claim-status word: this exact sentence may be said, nothing wider (NOT LICENSED: it may not be said)"),
    "VALIDATED": (r"(?<!NOT-)\bVALIDATED\b", 0, "a claim-status word: it passed its own pre-set test against controls, on the data it was measured on"),
    "ENGINEERED-NOT-VALIDATED": (r"ENGINEERED-NOT-VALIDATED", 0, "a claim-status word: built and working, with no validated result yet"),
    "transformer": (r"\btransformers?\b", re.I, "the kind of neural network behind most modern AI chat assistants"),
    "parameter": (r"\bparameters?\b", re.I, "an adjustable number a model learns"),
    "LLM": (r"\bLLMs?\b", 0, "large language model, a big pretrained text-predicting neural network like those behind chat assistants"),
    "GB3": (r"\bGB3\b", 0, "the small transformer that used to be HELM's brain and is the bar to beat"),
    "AWS": (r"\bAWS\b", 0, "Amazon Web Services, the rented cloud computers used for heavy runs"),
    "GPU": (r"\bGPUs?\b", 0, "a graphics chip used to train neural networks quickly"),
    "seed": (r"\bseeds?\b", re.I, "a starting number that fixes which random choices a program makes"),
    "hash": (r"\bsha256\b|\bhash(?:es)?\b", re.I, "a fingerprint of a file; change one byte and the fingerprint changes"),
    "SDG": (r"\bSDG\b", 0, "the CAS Synthetic Data Generator, the project's program for making practice English"),
    "lacuna": (r"\blacuna(?:e|s)?\b|\bLACUNA", re.I, "something HELM could know but was never taught"),
    "restart fallback": (r"\brestart fallback\b|RESTART_FALLBACK", re.I, "if the exact first try leaves something unexplained, a few saved random restarts are tried and the checker decides"),
    "cube store": (r"\bcube store\b|CUBE_STORE", re.I, "where HELM keeps facts; an unknown side stays marked unknown and is never filled in"),
    "triad": (r"\btriad\b", re.I, "three stages on each ingredient: Purpose, Wisdom and Power"),
    "cascade": (r"\bcascade\b", re.I, "going down into sub-problems, with a stop rule and a depth limit"),
    "drive loop": (r"\bdrive[- ]loop\b|DRIVE_LOOP", re.I, "HELM's idle attention moving among the seven Drives toward unfinished work"),
    "faculty": (r"\bfacult(?:y|ies)\b", re.I, "a mental job HELM can run on an open item, such as asking or verifying"),
}
TERM_RES = {k: re.compile(v[0], v[1]) for k, v in TERMS.items()}


def T(key: str, shown: str | None = None, gloss: str | None = None, also: tuple[str, ...] = ()) -> str:
    """A term on first use: a <dfn> plus an inline plain-English gloss."""
    if key not in TERMS:
        raise KeyError(key)
    plain = gloss or TERMS[key][2]
    keys = "|".join((key,) + tuple(also))
    return (f'<dfn data-term="{esc(keys)}" title="{esc(plain)}">{esc(shown or key)}</dfn>'
            f'<span class="gloss"> ({esc(plain)})</span>')


def words_box(body_html: str) -> str:
    """For generated pages: a box that explains every listed term used on the page, placed first."""
    text = re.sub(r"<[^>]+>", " ", body_html)
    text = html.unescape(text)
    used = [k for k in TERMS if TERM_RES[k].search(text)]
    if not used:
        return ""
    items = "".join(
        f'<div class="w"><dt><dfn data-term="{esc(k)}" title="{esc(TERMS[k][2])}">{esc(k)}</dfn></dt>'
        f'<dd class="gloss">{esc(TERMS[k][2])}</dd></div>' for k in used)
    return (f'<details class="words" open><summary>Words used on this page, in plain English</summary>'
            f'<dl>{items}</dl></details>')


# --------------------------------------------------------------------------------------------
# Colors (the owner's scale, as a reading aid only; never a claim status)
# --------------------------------------------------------------------------------------------
COLORS = {
    "win": "Confirmed win",
    "strong": "Strong",
    "partial": "Partial",
    "weak": "Weak or mixed",
    "failed": "Failed or withdrawn",
    "null": "Null, inconclusive or not run",
    "method": "Method or process win",
    "blocked": "Blocked on owner",
    "rule": "Rule, not a result",
}
COLOR_BAR = {
    "win": "passed with a floor that cannot be faked, survived checking, licensed wording",
    "strong": "real and survived its controls, with a named caveat",
    "partial": "real but bounded",
    "weak": "barely above chance, or mixed",
    "failed": "killed by a control or retracted; kept in the record",
    "null": "no signal, or never executed; distinct from a failure",
    "method": "an instrument, gate, tool or discipline improvement; not a science result",
    "blocked": "needs the owner's sign line, money or authorization; not a result",
    "rule": "a decision or a pointer that binds now; not evidence",
}


def dot(c: str) -> str:
    return f'<span class="dot c-{c}" aria-hidden="true"></span><span class="clabel">{esc(COLORS[c])}</span>'


# --------------------------------------------------------------------------------------------
# Curated plain-English row notes for the scorecard (editor's reading; the record governs)
# kind: scored | packet | rule | audit ; color: key of COLORS
# --------------------------------------------------------------------------------------------
CUR: dict[str, tuple[str, str, str, str]] = {
    "7.24": ("scored", "partial", "The first recipe brain, put in the transformer's slot, passed the transformer's own 16-world exam and beat it by one world. A plain lookup table tied it, so the recipe arithmetic got no credit.", "PASS on that exam. Not that recipe math earned its keep."),
    "7.25": ("scored", "weak", "Harder exams. Task A passed, but the transformer passed too. Task B tripped the reader's own instrument rule, so the overall reading is NOT_PASS.", "Nothing new may be said."),
    "7.26": ("scored", "strong", "Clean rerun of Task B: only the recipe mechanism passed. The first exam where composing recipes earned credit.", "Composition credit on these made-up worlds. Not learned composition."),
    "7.27": ("scored", "partial", "Rules for when to add parameters: the limiting-ingredient rule of scaling held on 6 of 7 families; the blend law held only up to about 12 corners; smooth and noisy laws need an ordinary head.", "Recorded rules. No HELM claim."),
    "7.28": ("scored", "strong", "The old transformer, as built and widened, was taught and tested on Task B. Both stayed near chance; the recipe brain beat them by 25 and 22.5 of 32.", "The recipe brain beat the transformer on Task B, on made-up worlds."),
    "7.29": ("scored", "strong", "The same, with the transformer given the same hints the recipe brain gets. Still near chance. The hints were not the reason.", "Margins 24 and 23 of 32, on made-up worlds."),
    "7.30": ("scored", "failed", "Three self-growth runs. The brain grew the right kind of capacity, but never reached the pre-sized brain, and its trigger fired on a control world.", "Growth stays NOT LICENSED."),
    "7.31": ("scored", "partial", "The language line: a checked English skin with exact round trips (576 of 576) and nested Noetics; free English read 233 of 439; taught random coordinates were not calibrated and were stopped.", "Form only. Not reading open English."),
    "7.32": ("scored", "failed", "Fourth growth run: every scored number equals the third. The gap is in how results are read, not in the fit.", "Growth stays NOT LICENSED."),
    "7.33": ("scored", "failed", "Without an answer key, the checker separated 1 of 25 ambiguous sentences; 24 ended as questions. A coin would have added more wrong than right.", "Nothing; a recorded negative."),
    "7.34": ("scored", "failed", "Faculties and the seven-Drive loop on the recipe brain. A hard gate failed (one empty fit receipt), so the run is a failure. Read as if it had passed, no faculty earned its keep.", "Nothing; a recorded negative."),
    "7.35": ("scored", "null", "Language carried station by station through the brain. The sealed reader read INCONCLUSIVE; a corrected reader reads better, but that amendment waits for the owner's judgment.", "Nothing until the owner judges the amendment."),
    "7.36": ("scored", "failed", "Fifth growth run: the smooth family reached the pre-sized brain for the first time, but a unit grew on the control world.", "Growth stays NOT LICENSED."),
    "7.37": ("scored", "null", "The clean rerun of the faculties test stopped itself at its first stage: two data sets rebuilt on Linux did not match their fingerprints.", "No science reading exists."),
    "7.38": ("scored", "null", "The Unity Eye acting on the brain: inconclusive both ways. A random-whisper control broke the clean-dialogue gate.", "No keep word and no harm word."),
    "7.39": ("scored", "failed", "Sixth growth run, with a compactness check. It grew the wrong kind on both world sets, although the check refused every useless unit on noise.", "Growth stays NOT LICENSED."),
    "7.40": ("scored", "win", "Retest on fresh made-up worlds: the Eye fixed 148 of 148 planted faults with far fewer interventions than a blind checklist, and made no keyed answer worse.", "EYE_EARNED_KEEP and CONCERT_EARNED_KEEP for this test, on made-up worlds only."),
    "7.41": ("scored", "weak", "Language map, test 6: all 16 hard gates passed and five words were earned, but the cascade never went below depth 0, and the early-stop arm found 269 of 800 deep faults.", "The five words, for the tested form only."),
    "7.42": ("scored", "failed", "Trimming and pruning the brain with the Eye: mixed evidence, overall FAIL.", "Nothing; a recorded negative."),
    "7.43": ("scored", "failed", "Layered memory run: hard gate H8 failed.", "Nothing; a recorded negative."),
    "7.44": ("audit", "method", "The fresh exam for wave 1 was built and sealed by a custodian and handed to the builder as fingerprints only. Nothing was scored.", "No claim."),
    "7.45": ("scored", "method", "Follow-up that explains the 15 H8 memory violations: a healthy second copy returned the exact original after a fault touched the first copy.", "The explanation; the H8 rule is unchanged."),
    "7.46": ("rule", "rule", "The owner moved the memory question to 'is the fault classified', and a bounded repair search was frozen. Nothing scored.", "No claim."),
    "7.47": ("scored", "strong", "Wave 1. On a freshly sealed made-up exam the recipe brain, in the transformer's slot, scored 32 against GB3's 9 (17/2 widened), with all seven hard gates and all eight instrument rows holding. This is HELM's licensed brain. The job supervisor's own markup read FAIL because it looked for outputs one folder too high; that markup is kept as recorded.", "One exact sentence, on made-up worlds (see the model card). Not real data, not inside HELM's runtime at the time, not general superiority."),
    "7.48": ("audit", "null", "Nine thinking-loop packages built, with 308 tests written. Only a few outputs were recorded on disk; none ran inside HELM at the time.", "Built, not validated."),
    "7.49": ("audit", "weak", "Audit of the end-to-end pipeline and chat layer: the round-trip result was ignored, missing amounts were filled with an invented 10, and the gate was skipped. Fixes C and D rewired it on 2026-10-18 (CHANGELOG).", "Built, not validated."),
    "7.50": ("audit", "failed", "The valve's learned weights were trained on the laptop, not on AWS as the roadmap said. The owner ruled that a written rule replaces them.", "Built, not validated; the roadmap claim is false."),
    "7.51": ("audit", "null", "Two demonstration brains (22 baking ingredients, 40 parameters). Stand-ins, not the licensed brain; no score.", "Built, not validated."),
    "7.52": ("scored", "weak", "A substitution head for smooth families: it helped on fresh worlds, was no better on the original ones, and its calibration sweep failed.", "NOT LICENSED. The 87.5% against 60.74% figures belong here, not to the 22x40 brain."),
    "7.53": ("audit", "failed", "Two GPU jobs ran on a side branch with no ledger line and no owner sign line; one left no artifact at all. Flagged for human review; the owner later accepted the cost after the fact.", "Nothing; a governance negative kept on the record."),
    "7.54": ("audit", "partial", "197 sentences HELM could not read were split into 98 sealed and 99 for development, with fingerprints. One baseline line of the tabulation was typed in, not computed.", "The split is REAL; the typed line is flagged."),
    "7.55": ("rule", "rule", "Who decided what, 2026-10-16 to 18: depth horizon 12, recipe brain canonical, no more GPU for now, a plain-rule valve, fixes A to G.", "Rules, not results."),
    "7.56": ("rule", "rule", "Pointer: HELM has one licensed brain, the wave-1 recipe brain. Everything else is a candidate or a stand-in.", "A pointer, not a result."),
    "7.57": ("scored", "partial", "A bigger written dictionary: the sealed 98 sentences went from 0 read to 34 (32 right, 2 wrong); the 439-sentence headline went from 233 to 304 matches.", "These counts only."),
    "7.58": ("scored", "partial", "Purpose / Wisdom / Power per ingredient can be wired in and read back. The answer keys use the same rules, so this shows wiring, not that real ingredients carry a triad.", "Built, not validated; made-up worlds only."),
    "7.59": ("rule", "rule", "Owner rulings: 'Desire is Purpose' becomes HELM canon; one stage scale for all three faces; a stopped 300 GB machine deleted; 2.06 USD accepted after the fact.", "Rules, not results."),
    "7.60": ("audit", "null", "The everyday-English reader: plain stock and recipe sentences are restated in the checked form and run like checked turns. Built and tested; not scored on a sealed exam.", "Built, not validated."),
    "7.61": ("scored", "partial", "Does Wisdom only rise? Rule C (it drops only through a named event with evidence) caught every tampered record. Planted worlds only.", "Built, not validated; made-up worlds only."),
    "7.62": ("audit", "null", "The triad adapter around the licensed brain: 0 learned parameters, off by default, a receipt on every write.", "Built, not validated."),
    "7.64": ("scored", "strong", "Wave 2: parts switched off one at a time. Six earned their keep; the language skin changed nothing, by design; no exam used the triad.", "One word per part, in the reader's own sentence, made-up worlds only."),
    "7.65": ("scored", "null", "The faculties retest ran clean (every hard gate held) and still earned no faculty word and no drive-loop word. A clean negative.", "Nothing new; INCONCLUSIVE by its frozen rule."),
    "7.67": ("scored", "failed", "Growth at the point of curiosity: it named the right gap 85 of 85 times, but grew once on the control world.", "Growth stays NOT LICENSED."),
    "7.68": ("scored", "failed", "The same run with only the job check fixed: no false growth, but curiosity beat both simple rivals on one family only.", "Growth stays NOT LICENSED."),
    "7.69": ("scored", "strong", "Wave 3: 11 parts earned their keep; the owner's decoupling stop beat the old fixed cap (203 descents against 609, no fuse blown); no pair worked better together than apart. Erratum: one rival arm had a hidden lookup table.", "The reader's own words, made-up worlds only."),
    "7.71": ("scored", "null", "A harder growth world: even the pre-sized brain could not fit it, so no world was valid and the comparison is VACUOUS.", "Growth stays NOT LICENSED."),
    "7.72": ("scored", "strong", "Wave 3b, with roomier exams: the English reader and the voice work together (SYNERGY); three other pairs guard the same items (INTERFERENCE).", "The four pair words, made-up worlds only."),
    "7.73": ("scored", "partial", "The Eye's read-only self-scan found all 176 planted faults in 368 copies, with 0 false alarms. The faults were planted knowing what the scan checks.", "Built, not validated; made-up worlds only."),
    "7.74": ("scored", "partial", "The Eye learned which faculty fits which Drive: 77.28% of items resolved against 37.33% for random pairing. The world was built so pairing matters.", "Built, not validated; no creativity claim."),
    "7.77": ("scored", "partial", "Wave 4: the Eye's self-scan on the real brain found 88 of 88 planted faults and held back all 88 answers that would have used them, at no cost on other exams.", "Built, not validated; made-up worlds only."),
    "7.78": ("scored", "partial", "Wave 5: the Eye-paired idle loop cleared 70.18% of a sealed backlog, against 35.32% for random pairing. The gain comes from learning.", "Built, not validated; made-up worlds only."),
    "7.80": ("scored", "failed", "The old small English model on the sealed 98: 0 exact. 21 confident answers passed the round-trip check and all 21 were wrong. A round trip proves form, not truth.", "Nothing; stays built, not validated."),
    "7.81": ("scored", "failed", "X-REAL, the first real-text exam: HELM's English reader wrote 8 wrong stock facts on 128 real sentences (limit 2). On real recipes it never answered wrong but answered only 3 of 64. The Eye's scan caught nothing a plain checksum missed.", "The negative words, on the named corpora only."),
    "7.83": ("audit", "null", "The wide recipe brain, built beside the licensed one behind an off-by-default switch. Unit-tested only at this point.", "Built, not validated."),
    "7.85": ("scored", "null", "The transformer ear's first GPU run stopped itself: a file-write watcher saw writes made by the PyTorch library. Nothing trained at scale.", "Nothing scored."),
    "7.87": ("scored", "partial", "The fixed English reader on 128 fresh real sentences wrote 0 wrong facts (the old reader wrote 11). Safe, not yet useful: right 115 times against always-ask's 114.", "Safety half only, on the named corpora."),
    "7.88": ("scored", "weak", "The wide brain's first sealed test on real recipes: 0 wrong answers, but it fully learned 90 of 110 (bar 99).", "A recorded negative on learning."),
    "7.89": ("scored", "win", "The wide brain v3, second sealed test on 128 fresh real recipes: fully learned 92 of 96 (bar 87), 93 right, 0 wrong. Now HELM's canonical-brain candidate.", "VALIDATED for one sentence only, named corpora only. Not canonical yet."),
    "7.90": ("scored", "failed", "The transformer ear trained fully. No gain on real sentences (106 / 106 / 105 against the reader's 107). On LLM-written kitchen English it lifted right answers, but broke the cap on confident wrong proposals: FAILURE, EARS_HARMED.", "A narrow negative sentence only. Not 'the ears help'."),
}


def classify(k: str, title: str) -> tuple[str, str, str, str]:
    if k in CUR:
        return CUR[k]
    t = title.upper()
    if "NOT LAUNCHED" in t or "NOTHING SCORED" in t:
        return ("packet", "null", "A test packet built and sealed before any run. Nothing has run on it; it makes no claim.", "No claim.")
    return ("scored", "null", "See the record.", "See the record.")


def section_words(title: str) -> list[str]:
    t = noemoji(title)
    toks = re.findall(r"`([^`]+)`", t)
    toks += re.findall(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", t)
    for w in ("PASS", "FAIL", "FAILURE", "INCONCLUSIVE", "NOT LAUNCHED", "NOT LICENSED", "ENGINEERED-NOT-VALIDATED",
              "LICENSED", "VALIDATED", "REAL", "IN FORCE"):
        if re.search(r"(?<![A-Z_-])" + re.escape(w) + r"(?![A-Z_-])", t):
            toks.append(w)
    seen, out = set(), []
    for x in toks:
        x = x.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9 _-]*[A-Z0-9]", x):
            continue
        if x in ("AWS", "GPU", "USD", "PDT", "MSI", "CCE", "HELM", "LLM", "RB", "UTC"):
            continue
        if any(x != y and x in y for y in toks if re.fullmatch(r"[A-Z0-9 _-]+", y)):
            continue
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out[:7]


def section_cost(title: str) -> str:
    m = re.findall(r"(\d+\.\d+) USD", title)
    if m:
        return m[-1] + " USD"
    if re.search(r"\$0\b|\b0 USD\b", title):
        return "0 USD"
    if "unavailable" in title:
        return "unavailable"
    return "not stated"


def section_date(title: str, body: str = "") -> str:
    m = re.findall(r"(2026-\d\d-\d\d(?:/\d\d)?)", title)
    if m:
        return m[-1]
    b = re.search(r"(2026-\d\d-\d\d)", body)
    return (b.group(1) + " (from the text)") if b else "not stated"


def section_job(title: str) -> str:
    m = re.search(r"\bjobs? (c\d+[a-z0-9-]*|m1h8v5)", title)
    return m.group(1) if m else ""


# --------------------------------------------------------------------------------------------
# Page frame
# --------------------------------------------------------------------------------------------
NAV = [
    ("index.html", "Home"),
    ("thinking.html", "How HELM thinks"),
    ("architecture.html", "Architecture"),
    ("data.html", "Data lineage"),
    ("compute.html", "Compute and cost"),
    ("results.html", "Results scorecard"),
    ("model-card.html", "Model card"),
    ("safety.html", "Safety and honesty"),
    ("roadmap.html", "Roadmap"),
    ("glossary.html", "Glossary"),
    ("changelog.html", "Changelog"),
    ("run.html", "How to run HELM"),
]

CSS = r"""
:root{
  --bg:#f5f3ee; --bg-glow:#ece7dc; --surface:#fffefb; --surface-2:#f8f5ef;
  --line:rgba(24,27,33,.09); --line-strong:rgba(24,27,33,.18);
  --ink:#16191f; --ink-2:#4a505a; --ink-3:#6f7580;
  --accent:#7d5f22; --accent-soft:rgba(125,95,34,.10);
  --c-win:#23784a; --c-strong:#3f9a6e; --c-partial:#b58a12; --c-weak:#c4651f; --c-failed:#b23a3a;
  --c-null:#8b9099; --c-method:#2a78d6; --c-blocked:#7a5bb5; --c-rule:#d9d4c9;
  --shadow:0 1px 2px rgba(20,22,28,.04),0 8px 28px rgba(20,22,28,.05);
  --radius:14px;
  --serif:"Newsreader","Iowan Old Style",Georgia,serif;
  --sans:"Inter",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"Cascadia Mono",Consolas,monospace;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0d1015; --bg-glow:#141a23; --surface:#141920; --surface-2:#1a2029;
    --line:rgba(232,230,225,.08); --line-strong:rgba(232,230,225,.16);
    --ink:#e9e7e2; --ink-2:#b4b9c2; --ink-3:#8a919c;
    --accent:#d2b06e; --accent-soft:rgba(210,176,110,.12);
    --c-win:#4cc07f; --c-strong:#6cc79a; --c-partial:#e0b84a; --c-weak:#ec9150; --c-failed:#ec6d6d;
    --c-null:#8f96a1; --c-method:#5598e7; --c-blocked:#a98ae0; --c-rule:#3a404a;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.25);
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --bg:#0d1015; --bg-glow:#141a23; --surface:#141920; --surface-2:#1a2029;
  --line:rgba(232,230,225,.08); --line-strong:rgba(232,230,225,.16);
  --ink:#e9e7e2; --ink-2:#b4b9c2; --ink-3:#8a919c;
  --accent:#d2b06e; --accent-soft:rgba(210,176,110,.12);
  --c-win:#4cc07f; --c-strong:#6cc79a; --c-partial:#e0b84a; --c-weak:#ec9150; --c-failed:#ec6d6d;
  --c-null:#8f96a1; --c-method:#5598e7; --c-blocked:#a98ae0; --c-rule:#3a404a;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.25);
  color-scheme:dark;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);background-image:radial-gradient(1200px 500px at 10% -10%,var(--bg-glow),transparent 60%);
  color:var(--ink);font:15.5px/1.6 var(--sans);-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:var(--ink);text-decoration:underline;text-decoration-color:var(--line-strong);text-underline-offset:3px}
a:hover{text-decoration-color:var(--accent)}
code{font:12.5px/1.5 var(--mono);background:var(--surface-2);border:1px solid var(--line);border-radius:6px;padding:1px 5px;overflow-wrap:anywhere}
pre{font:12px/1.55 var(--mono);background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:12px 14px;overflow-x:auto;white-space:pre-wrap;overflow-wrap:anywhere}
.wrap{max-width:1080px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}
header.top{border-bottom:1px solid var(--line);background:color-mix(in srgb,var(--surface) 70%,transparent);backdrop-filter:blur(6px)}
.bar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 0 12px}
.wordmark{font:500 22px/1 var(--serif);letter-spacing:.16em;text-decoration:none}
.tagline{font-size:12.5px;color:var(--ink-3);margin-top:5px}
.tools{display:flex;gap:8px;align-items:center}
.btn{font:inherit;font-size:12.5px;color:var(--ink-2);background:transparent;border:1px solid var(--line-strong);border-radius:999px;padding:6px 12px;cursor:pointer}
.btn:hover{color:var(--ink);border-color:var(--accent)}
nav.pages ul{list-style:none;margin:0;padding:0 0 12px;display:flex;flex-wrap:wrap;gap:4px 6px}
nav.pages a{display:inline-block;font-size:13px;color:var(--ink-2);text-decoration:none;padding:5px 10px;border-radius:999px;border:1px solid transparent}
nav.pages a:hover{border-color:var(--line-strong);color:var(--ink)}
nav.pages a[aria-current="page"]{background:var(--accent-soft);color:var(--ink);border-color:var(--line-strong)}
#menu-btn{display:none}
@media (max-width:760px){
  #menu-btn{display:inline-block}
  html.js nav.pages{display:none}
  html.js nav.pages.open{display:block}
  nav.pages ul{flex-direction:column}
}
.conf{font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
main{padding:28px 0 40px}
h1{font:400 clamp(28px,4.4vw,40px)/1.15 var(--serif);margin:6px 0 12px;letter-spacing:-.01em}
h2{font:500 clamp(21px,2.6vw,26px)/1.25 var(--serif);margin:36px 0 10px}
h3{font:600 15.5px/1.35 var(--sans);margin:22px 0 6px}
p{margin:0 0 12px}
.lede{font:400 clamp(17px,2.1vw,20px)/1.55 var(--serif);color:var(--ink-2);max-width:62ch}
.muted{color:var(--ink-3)}
.small{font-size:13px}
dfn{font-style:normal;font-weight:600;border-bottom:1px dotted var(--accent);cursor:help}
.gloss{color:var(--ink-2)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:18px 20px;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:14px}
.grid .card{margin:0}
.strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:10px;margin:16px 0}
.pill{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px;font-size:13.5px}
.pill .what{font-weight:600;display:block;margin-bottom:3px}
.word{font:11.5px/1.4 var(--mono);padding:1px 6px;border-radius:6px;background:var(--surface-2);border:1px solid var(--line);color:var(--ink-2);display:inline-block;margin:2px 3px 2px 0;overflow-wrap:anywhere}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:baseline;border:1px solid var(--line-strong)}
.clabel{font-size:12.5px;color:var(--ink-2)}
.c-win{background:var(--c-win)} .c-strong{background:var(--c-strong)} .c-partial{background:var(--c-partial)}
.c-weak{background:var(--c-weak)} .c-failed{background:var(--c-failed)} .c-null{background:var(--c-null)}
.c-method{background:var(--c-method)} .c-blocked{background:var(--c-blocked)} .c-rule{background:var(--c-rule)}
.tablewrap{width:100%;overflow-x:auto;margin:12px 0;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;vertical-align:top;padding:9px 11px;border-bottom:1px solid var(--line)}
th{font-weight:600;color:var(--ink-2);background:var(--surface-2);font-size:12.5px}
tr:last-child td{border-bottom:0}
td{overflow-wrap:anywhere}
.verbatim{border-left:3px solid var(--line-strong)}
blockquote{margin:12px 0;padding:10px 16px;border-left:3px solid var(--accent);background:var(--surface-2);border-radius:0 10px 10px 0;font:400 16px/1.55 var(--serif)}
details{margin:8px 0}
details>summary{cursor:pointer;color:var(--ink-2);font-size:13.5px}
details.precise{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:8px 12px}
details.precise[open]>summary{margin-bottom:6px}
details.words{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:16px 0}
details.words dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:6px 18px;margin:10px 0 0}
details.words dt{font-size:13px} details.words dd{margin:0 0 6px;font-size:13px}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.filters .btn[aria-pressed="true"]{background:var(--accent-soft);color:var(--ink);border-color:var(--accent)}
.search{width:100%;font:inherit;font-size:15px;padding:10px 14px;border-radius:12px;border:1px solid var(--line-strong);background:var(--surface);color:var(--ink)}
article.entry{border-bottom:1px solid var(--line);padding:12px 0}
article.entry h3{margin:0 0 4px;font-size:15px}
.cat{font-size:11.5px;color:var(--ink-3);margin-left:6px}
.entry .line{font-size:13.5px;margin:3px 0}
.entry .lab{font-weight:600;color:var(--ink-2)}
footer.sources{border-top:1px solid var(--line);padding:22px 0 40px;font-size:12.5px;color:var(--ink-3)}
footer.sources ul{margin:6px 0 10px;padding-left:18px}
footer.sources li{overflow-wrap:anywhere}
.kv{display:grid;grid-template-columns:minmax(120px,max-content) 1fr;gap:4px 14px;font-size:14px}
.kv dt{color:var(--ink-3)} .kv dd{margin:0}
ul.tight li{margin:3px 0}
@media (max-width:760px){
  table.cards thead{display:none}
  table.cards,table.cards tbody,table.cards tr,table.cards td{display:block;width:100%}
  table.cards tr{border-bottom:1px solid var(--line);padding:8px 0}
  table.cards tr[hidden]{display:none}
  table.cards td{border:0;padding:3px 12px}
  table.cards td[data-label]::before{content:attr(data-label);display:block;font-size:10.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3);margin-bottom:1px}
}
.note{border:1px dashed var(--line-strong);border-radius:12px;padding:12px 14px;background:var(--surface-2);font-size:14px}
"""

JS = r"""
(function(){
  var d=document.documentElement; d.classList.add('js');
  function get(){try{return localStorage.getItem('helmhub-theme')||'auto'}catch(e){return 'auto'}}
  function set(v){try{localStorage.setItem('helmhub-theme',v)}catch(e){}}
  function apply(v){if(v==='auto'){d.removeAttribute('data-theme')}else{d.setAttribute('data-theme',v)}
    var b=document.getElementById('theme-btn'); if(b){b.textContent='Theme: '+v}}
  apply(get());
  document.addEventListener('DOMContentLoaded',function(){
    apply(get());
    var b=document.getElementById('theme-btn');
    if(b){b.addEventListener('click',function(){var o=['auto','light','dark'];var v=o[(o.indexOf(get())+1)%3];set(v);apply(v)})}
    var m=document.getElementById('menu-btn'), n=document.getElementById('pages');
    if(m&&n){m.addEventListener('click',function(){var o=n.classList.toggle('open');m.setAttribute('aria-expanded',o?'true':'false')})}
    var q=document.getElementById('gsearch');
    if(q){var items=[].slice.call(document.querySelectorAll('article.entry')), c=document.getElementById('gcount');
      q.addEventListener('input',function(){var s=q.value.trim().toLowerCase(), k=0;
        items.forEach(function(a){var on=!s||a.textContent.toLowerCase().indexOf(s)>=0; a.hidden=!on; if(on)k++});
        if(c){c.textContent=k+' of '+items.length+' entries shown'}})}
    var fb=[].slice.call(document.querySelectorAll('[data-filter]'));
    fb.forEach(function(btn){btn.addEventListener('click',function(){
      var f=btn.getAttribute('data-filter');
      fb.forEach(function(x){x.setAttribute('aria-pressed',x===btn?'true':'false')});
      [].slice.call(document.querySelectorAll('tr[data-kind]')).forEach(function(r){
        var on=f==='all'||r.getAttribute('data-kind')===f||r.getAttribute('data-color')===f||(f==='neg'&&r.getAttribute('data-neg')==='1');
        r.hidden=!on})})});
  });
})();
"""


def pacific_now() -> str:
    now = _dt.datetime.now(_dt.timezone.utc)
    if _PACIFIC is not None:
        return now.astimezone(_PACIFIC).strftime("%Y-%m-%d %H:%M %Z (Pacific)")
    return now.strftime("%Y-%m-%d %H:%M UTC (Pacific time zone data unavailable)")


def git_head() -> str:
    try:
        r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short=8", "HEAD"], capture_output=True,
                           text=True, timeout=20)
        return r.stdout.strip() or "unavailable"
    except Exception:
        return "unavailable"


GEN_AT = pacific_now()
HEAD = git_head()


def cardify(body: str) -> str:
    """Give every table class 'cards' and label each cell with its column name, so phones show stacked cards."""
    def one(m: re.Match) -> str:
        t = m.group(0)
        heads = [html.unescape(re.sub(r"<[^>]+>", "", h)).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", t, re.S)]
        t = re.sub(r"<table(?: class=\"([^\"]*)\")?", lambda mm: f'<table class="cards {mm.group(1) or ""}"'.replace(' "', '"'), t, count=1)
        if not heads or "<tbody>" not in t:
            return t
        head, _, rest = t.partition("<tbody>")
        rows = rest.split("<tr")
        out = [rows[0]]
        for r in rows[1:]:
            i = [0]

            def lab(mm: re.Match) -> str:
                k = i[0]
                i[0] += 1
                return f'<td data-label="{esc(heads[k])}"' if k < len(heads) else "<td"
            out.append(re.sub(r"<td(?=[ >])", lab, r))
        return head + "<tbody>" + "<tr".join(out)
    return re.sub(r"<table.*?</table>", one, body, flags=re.S)


def page(slug: str, title: str, h1: str, lede_html: str, body: str, sources: list[str], words: bool = False,
         description: str = "") -> str:
    navs = "".join(
        f'<li><a href="{s}"{" aria-current=\"page\"" if s == slug else ""}>{esc(n)}</a></li>' for s, n in NAV)
    box = words_box(lede_html + body) if words else ""
    body = cardify(body)
    src = "".join(f"<li>{md(s)}</li>" for s in sources)
    desc = esc(description or f"HELM Hub: {h1}")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex, nofollow">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<style>{CSS}</style>
<script>{JS}</script>
</head>
<body>
<header class="top"><div class="wrap">
<div class="bar"><div><a class="wordmark" href="index.html">HELM HUB</a>
<div class="tagline">A living spec sheet for HELM, rebuilt from the project's own records</div></div>
<div class="tools"><button class="btn" id="menu-btn" type="button" aria-controls="pages" aria-expanded="false">Pages</button>
<button class="btn" id="theme-btn" type="button">Theme: auto</button></div></div>
<nav class="pages" id="pages" aria-label="Hub pages"><ul>{navs}</ul></nav>
</div></header>
<main class="wrap">
<div class="conf">Confidential, internal. Not for public posting.</div>
<h1>{esc(h1)}</h1>
<div class="lede">{lede_html}</div>
{box}
{body}
</main>
<footer class="sources"><div class="wrap">
<strong>Sources for this page</strong>
<ul>{src}</ul>
<div>Generated {esc(GEN_AT)} by <code>helm_hub/build_hub.py</code> from repo commit <code>{esc(HEAD)}</code>.
Rebuild with <code>python helm_hub/build_hub.py</code>. Where this page and a source disagree, the source wins.</div>
</div></footer>
</body>
</html>
"""


# --------------------------------------------------------------------------------------------
# Load everything once
# --------------------------------------------------------------------------------------------
def load() -> dict:
    spec_t = read(SPEC)
    secs = spec_sections(spec_t)
    legend, prohibited = spec_legend(spec_t)
    dict_t = read(DICT)
    entries = dict_entries(dict_t)
    return {
        "spec": spec_t, "secs": secs, "legend": legend, "prohibited": prohibited,
        "dict": dict_t, "entries": entries,
        "road": read(ROAD), "corr": read(CORR), "chlog": read(CHLOG),
        "ui_readme": read(UI_README), "ledger": ledger_totals(), "runs": run_records(),
        "approvals": approval_headings(), "coverage": read(COVERAGE),
        "xr_prereg": read(XR_PREREG), "xr_sources": read(XR_SOURCES),
    }


def need(S: dict, sec: str, *words: str) -> None:
    """Living check: a word this hub cites must still be in the cited spec section."""
    s = S["secs"].get(sec)
    if s is None:
        raise SystemExit(f"BUILD STOP: spec section {sec} not found")
    blob = s["title"] + "\n" + s["text"]
    for w in words:
        if w not in blob:
            raise SystemExit(f"BUILD STOP: '{w}' no longer appears in spec section {sec}; update the hub")


def slink(sec: str) -> str:
    return f'<a href="results.html#s{sec.replace(".", "-")}">§{sec}</a>'


# --------------------------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------------------------
def p_home(S: dict) -> str:
    need(S, "7.56", "LICENSED", "SYNTHETIC_ONLY")
    need(S, "7.89", "WIDE_BRAIN_EARNED_KEEP", "VALIDATED", "NAMED_CORPORA_ONLY")
    need(S, "7.87", "S_SAFE_NOT_USEFUL", "ENGINEERED-NOT-VALIDATED")
    need(S, "7.77", "EYE_SCAN_EARNED_KEEP", "ENGINEERED-NOT-VALIDATED")
    need(S, "7.78", "EYE_PAIRING_EARNED_KEEP")
    need(S, "7.90", "EARS_NO_GAIN", "EARS_HARMED", "FAILURE")
    need(S, "7.71", "NOT LICENSED", "nine runs")
    need(S, "7.65", "INCONCLUSIVE")
    need(S, "7.81", "S_UNSAFE_ON_REAL")
    L = S["ledger"]
    ledger = (f"{L.get('combined_allocation_usd')} of {L.get('ceiling_usd')} USD allocated; "
              f"{L.get('unreserved_usd')} USD unreserved (ledger stamp {L.get('utc')})") if L else "ledger not available on this machine"
    secs = S["secs"]
    helm_secs = [k for k in secs if sec_num(k) >= 24]
    scored = [k for k in helm_secs if classify(k, secs[k]["title"])[0] == "scored"]
    neg = [k for k in helm_secs if classify(k, secs[k]["title"])[1] in ("failed", "weak")]
    latest = max(helm_secs, key=sec_num) if helm_secs else ""

    def pill(color, what, plain, words, sec):
        ws = "".join(f'<span class="word">{esc(w)}</span>' for w in words)
        return (f'<div class="pill"><span class="what">{dot(color)} {esc(what)}</span>{plain}'
                f'<div>{ws}</div><div class="small muted">Record: {slink(sec)}</div></div>')

    strip = "".join([
        pill("strong", "The licensed brain", "Beat the old transformer brain on a sealed made-up exam.", ["LICENSED", "SYNTHETIC_ONLY"], "7.47"),
        pill("win", "The wide brain (candidate)", "Learned real cookbook recipes on a sealed test, 0 wrong answers.", ["VALIDATED (one sentence)", "NAMED_CORPORA_ONLY"], "7.89"),
        pill("partial", "The English reader", "Safe on fresh real sentences after a fix; not yet useful.", ["ENGINEERED-NOT-VALIDATED", "S_SAFE_NOT_USEFUL"], "7.87"),
        pill("failed", "The reader before the fix", "Wrote 8 wrong facts on 128 real sentences.", ["S_UNSAFE_ON_REAL"], "7.81"),
        pill("partial", "The Unity Eye", "Found planted faults and paired jobs well, on made-up worlds.", ["EYE_SCAN_EARNED_KEEP", "EYE_PAIRING_EARNED_KEEP", "ENGINEERED-NOT-VALIDATED"], "7.78"),
        pill("failed", "The transformer ear", "No gain on real sentences; too many confident wrong guesses on a second exam.", ["EARS_NO_GAIN", "EARS_HARMED", "FAILURE"], "7.90"),
        pill("failed", "Self-growth", "Growing its own capacity has not earned a claim.", ["NOT LICENSED"], "7.71"),
        pill("null", "Faculties", "The mental jobs earned no word on the brain itself.", ["INCONCLUSIVE"], "7.65"),
    ])
    lede = (f"HELM is a small thinking machine you can check line by line. Its brain is a set of written "
            f"{T('recipe', 'recipes')}, worked with exact arithmetic. When something is missing, it asks instead of guessing.")
    body = f"""
<div class="card">
<p>HELM is built on {T('CAS')}. Its brain is a {T('recipe brain')}. For each outcome, such as a loaf of bread,
it keeps how much of each ingredient one unit needs. It learns those amounts from things it has watched happen
("we made 5 loaves from 10 flour and 8 water and ran out of flour"). It answers by dividing what is on hand by what each
unit needs. The smallest result wins, because the {T('limiting reagent')} runs out first.</p>
<p>When an amount it needs is missing, its {T('RPM Gate')} lets it answer {T('UNDETERMINED')} instead of guessing.
Every fact it saves is read back first and leaves a {T('receipt')}. A watcher, the {T('Unity Eye')}, looks over the whole
system; it reports and {T('whisper', 'whispers')}, and it never writes.</p>
<p><strong>HELM is not a chatbot built on a large language model.</strong> No {T('LLM')} sits inside it. The first recipe brain had
68 learned values ({T('parameter', 'parameters')}): 32 requirements, 32 ceilings and 4 bindings ({slink('7.24')}). The licensed brain's run log
printed 32 learned slots, against 97 for the {T('transformer')} it replaced ({slink('7.47')}). A separate small transformer
(9,585,566 parameters) exists only as an optional "ear" that may propose a reading; it never writes ({slink('7.82')}).</p>
</div>

<h2>Today's status</h2>
<p>Each card shows a color, the exact words from the record, and the {T('claim ceiling')}. Most results come from {T('sealed')} exams.
Words ending in {T('EARNED_KEEP')} are the good outcome for a part; a {T('faculty')} is one of HELM's mental jobs. The colors are the owner's scale and
are a reading aid only. The words in grey boxes are the record's own words. {T('SYNTHETIC_ONLY')} and {T('NAMED_CORPORA_ONLY')} are the two ceilings in use today.
{T('LICENSED')}, {T('VALIDATED')} and {T('ENGINEERED-NOT-VALIDATED')} are {T('claim status')} words; the others are {T('status word', 'status words')}.</p>
<div class="strip">{strip}</div>
<p class="small muted">Money: {esc(ledger)}. See <a href="compute.html">Compute and cost</a>.</p>

<h2>The record in numbers</h2>
<div class="grid">
<div class="card"><strong>{len(helm_secs)}</strong> HELM records in the spec sheet (§7.24 to §{esc(latest)}).<br>
<strong>{len(scored)}</strong> of them are runs that produced a reading.<br>
<strong>{len(neg)}</strong> are failures, weak or mixed results, kept on purpose. <a href="results.html">See every one</a>.</div>
<div class="card">Latest record: {slink(latest)} {md(classify(latest, secs[latest]['title'])[2]) if latest else ''}</div>
<div class="card">The one rule that keeps this honest: a failed {T('hard gate')} is a failure, never "a pass with caveats".
<a href="safety.html">Safety and honesty</a>.</div>
</div>

<h2>Where to go next</h2>
<div class="grid">
<div class="card"><a href="thinking.html">How HELM thinks</a><br><span class="muted small">Recipes, asking, receipts and the Eye, with the precise definitions.</span></div>
<div class="card"><a href="architecture.html">Architecture</a><br><span class="muted small">Every part, its parameter count, and what HELM is not.</span></div>
<div class="card"><a href="results.html">Results scorecard</a><br><span class="muted small">Every result, negatives included.</span></div>
<div class="card"><a href="roadmap.html">Roadmap</a><br><span class="muted small">What is real, what is planned, and "can I chat with it?"</span></div>
<div class="card"><a href="demo.html">Try the demo page</a><br><span class="muted small">A recorded HELM session you can open without a server.</span></div>
<div class="card"><a href="model-card.html#not-here">What this hub does not have, and why</a><br><span class="muted small">The usual chatbot sections that do not apply to HELM.</span></div>
</div>
"""
    return page("index.html", "HELM Hub", "HELM, in one screen", lede, body, [
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.24, §7.47, §7.56, §7.65, §7.71, §7.77, §7.78, §7.81, §7.82, §7.87, §7.89, §7.90 (section counts computed from §7.24 onward)",
        f"`{rel(LEDGER)}` (totals only)",
        "Owner's color scale: `docs/reference/CAS_HELM_DICTIONARY.md`, 'Color marks used in owner reports'",
    ], description="What HELM is, in one screen, with today's status.")


def precise(S: dict, term: str, label: str = "Definition") -> str:
    e = dict_find(S["entries"], term)
    if not e:
        return f'<p class="muted small">No dictionary entry named {esc(term)}.</p>'
    lines = "".join(
        f'<div class="line"><span class="lab">{esc(lab or "Note")}:</span> {md(t)}</div>'
        for lab, t in e["lines"] if lab.lower().startswith(("definition", "status", "in helm", "rule", "anti")))
    return (f'<details class="precise"><summary>Precise definition: {esc(e["term"])} '
            f'(dictionary entry, quoted)</summary><div class="verbatim" style="padding-left:10px">{lines}</div></details>')


def p_thinking(S: dict) -> str:
    E = S["entries"]
    noetics = ["Idea", "Mind", "Positive", "Negative", "Vibration", "Female", "Male", "Rhythm", "Above/Cause", "Below/Effect"]
    rows = []
    for i, n in enumerate(noetics):
        q = canonical_quote(E, n)
        if not q:
            raise SystemExit(f"BUILD STOP: canonical definition for {n} not found in the dictionary")
        plain = dict_line(E, n, "Plain")
        rows.append(f"<tr><td><code>^{i}</code></td><td>{esc(n)}</td><td class=\"verbatim\">\u201c{esc(q)}\u201d</td><td>{md(plain)}</td></tr>")
    ntable = ('<div class="tablewrap"><table><thead><tr><th>Mark</th><th>Name</th><th>Canonical definition (verbatim)</th>'
              '<th>In plain words (dictionary)</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")
    need(S, "7.83", "a := stock / amount made", "yield = min x_i / a_i")
    need(S, "7.60", "we made 5 loaves from 10 flour and 8 water and ran out of flour")
    lede = "Six ideas explain almost everything HELM does. Each has a plain explanation, then a box with the exact wording from the project's dictionary."
    body = f"""
<div class="card"><strong>The six ideas, one line each</strong>
<ul class="tight">
<li>A {T('recipe')} is what HELM's {T('recipe brain')} is made of.</li>
<li>The {T('limiting reagent')} decides how much can be made.</li>
<li>When something is missing, the {T('RPM Gate')} lets HELM say it cannot tell, instead of guessing.</li>
<li>Every saved fact leaves a {T('receipt')}.</li>
<li>Every sentence HELM says must survive the {T('round trip')}.</li>
<li>The {T('Unity Eye')} watches, reports and {T('whisper', 'whispers')}, and never writes.</li>
</ul>
<p class="small muted">Each "Precise definition" box quotes the project's dictionary word for word; it may use further project terms, which the <a href="glossary.html">glossary</a> explains.</p></div>
<h2>1. Recipes</h2>
<p>HELM's brain is built from the vocabulary of {T('CAS')}. Its core unit is the recipe. A recipe for bread might say:
one loaf needs 2 flour and 1 water. CAS writes this as <code>Θ(Ω) = a₁·X₁ + a₂·X₂ + ... → Ω</code>, where Ω (omega) is the outcome,
each X is an ingredient, and each a is how much of it one unit needs.</p>
<p>HELM learns those amounts by watching. Tell it "we made 5 loaves from 10 flour and 8 water and ran out of flour", and it learns that
one loaf needs 10 ÷ 5 = 2 flour, because flour is the one that ran out. The record writes this rule as
<code>a := stock / amount made</code> ({slink('7.83')}). Nothing is guessed; the arithmetic is exact fractions.</p>
{precise(S, 'Recipe (Θ)') if dict_find(E, 'Recipe (Θ)') else precise(S, 'Recipe')}
{precise(S, 'Recipe brain')}

<h2>2. The limiting ingredient</h2>
<p>To answer "how much bread can we make?", HELM divides what is on hand by what one unit needs, for every ingredient, and takes the
smallest result: <code>yield = min x_i / a_i</code>. The ingredient with the smallest result is the limiting reagent.
With 12 flour and 20 water: 12 ÷ 2 = 6 and 20 ÷ 1 = 20, so 6 loaves, and flour is the limiting ingredient.</p>
{precise(S, 'Limiting Reagent')}

<h2>3. Asking instead of guessing</h2>
<p>If an amount HELM needs is missing, it does not fill in a number. Its RPM Gate lets the brain answer
{T('UNDETERMINED')}, and HELM asks a plain question. When it cannot read what you said, it answers with {T('CLARIFY')}: one question, nothing saved.
An earlier version of HELM's pipeline filled missing amounts with an invented 10; that was found and removed ({slink('7.49')}).</p>
{precise(S, 'RPM Gate')}
{precise(S, '`UNDETERMINED`')}
{precise(S, '`CLARIFY`')}

<h2>4. Receipts: read back before writing</h2>
<p>Before HELM saves a fact, it reads the fact back and checks it. Every saved fact leaves a receipt with a
{T('hash')}, so anyone can check later that nothing changed. A write that fails its read-back is refused, and nothing is saved.</p>
{precise(S, 'Receipt')}

<h2>5. The round trip: saying it the same way both directions</h2>
<p>Inside, HELM works in exact CAS statements. Outside, it talks in English. The bridge is {T('CCE')}. Any statement HELM
says must pass the round trip: turn it into English, read the English back, and get exactly the same statement
(<code>parse(render(C)) == C</code>). A round trip proves the form is right, not that the content is true: an old English model
gave 21 confident answers that passed the round trip and were all wrong ({slink('7.80')}).</p>
{precise(S, 'Round trip')}
{precise(S, 'CCE')}

<h2>6. The Eye</h2>
<p>The Unity Eye is a small watcher whose only motive is unity, the first of the seven core motivations. It scans
HELM's memory and records for damage, and it helps choose which mental job to try on unfinished work. It may report and
whisper. It never writes: in the scored runs it made 0 writes ({slink('7.77')}, {slink('7.78')}).</p>
{precise(S, 'Unity Eye')}
{precise(S, 'Whisper')}

<h2>The CAS words underneath</h2>
<p>CAS describes any mind, human or machine, with a small fixed vocabulary. The ten {T('Noetic', 'Noetics', also=('Noetic',))} are the basic moves.
Their names and definitions are canonical and are quoted below word for word. HELM also uses the seven {T('Drive', 'Drives')}
(F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose), the four {T('Domain', 'Domains')}
and, in some tests, the four {T('Register', 'Registers')}.</p>
{ntable}
<p class="small muted">The ^ marks are the project's notation for the Noetics. Definitions are copied from the dictionary, which quotes
<code>docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md</code> Clarification 1 verbatim. Where a colloquialism and a definition seem to disagree, the definition governs.</p>
"""
    return page("thinking.html", "How HELM Thinks", "How HELM thinks", lede, body, [
        "`docs/reference/CAS_HELM_DICTIONARY.md` (entries quoted in the 'Precise definition' boxes; Noetic definitions marked canonical, verbatim)",
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.24, §7.49, §7.60, §7.77, §7.78, §7.80, §7.83",
        "`CLAUDE.md` (the ten Noetics and the seven Drives)",
    ], description="Recipes, the limiting ingredient, asking, receipts, the round trip and the Eye.")


def p_architecture(S: dict) -> str:
    need(S, "7.47", "RB-B 32 learned slots", "T 97", "T+ 385")
    need(S, "7.24", "68 learned values")
    need(S, "7.82", "9,585,566", "2,482,718", "8,349")
    need(S, "7.83", "49,493 coefficients", "MAX_INGREDIENTS = 10")
    need(S, "7.62", "0 learned parameters")
    need(S, "7.69", "DECOUPLING_EARNED", "203")
    need(S, "7.51", "40")
    need(S, "7.50", "five weights")
    cov = S["coverage"]
    rows_html = html_table(md_table(cov, "| Place | Ten frames")) if cov else '<p class="muted">Coverage report not available on this machine.</p>'
    lede = "HELM is a set of small parts, each on its own switch, around one brain that does exact arithmetic. Here is every part, how many learned numbers it has, and what each one is for."
    body = f"""
<h2>The parts</h2>
<p>HELM is built on {T('CAS')}. Its brain holds {T('recipe', 'recipes')}, answers with exact arithmetic, and names the {T('limiting reagent')}.
Every saved fact leaves a {T('receipt')}; every sentence it says must pass the {T('round trip')}. Scored tests use {T('sealed')} exams.
The one place chance is allowed uses saved {T('seed', 'seeds')}.</p>
<p>A {T('parameter')} is an adjustable number a model learns. Big AI chat assistants have billions. HELM's licensed brain has dozens.
Each part below sits behind a switch, so tests can turn one part off and see what is lost. A part that loses something when switched off earns the
{T('status word')} {T('EARNED_KEEP')}. Tests run on {T('synthetic world', 'synthetic worlds')} unless they say otherwise.</p>
<div class="tablewrap"><table><thead><tr><th>Part</th><th>What it does, plainly</th><th>Learned parameters (exact, from the record)</th><th>Standing</th></tr></thead><tbody>
<tr><td><strong>Licensed {T('recipe brain')}</strong><br><code>helm_brain_canonical.py</code></td><td>Holds recipes; answers by exact yield; names the limiting ingredient. The way recipes combine is programmed; only the requirement amounts are learned.</td>
<td>Run log: "RB-B 32 learned slots" ({slink('7.47')}). The first recipe brain had "68 learned values (requirements 32, ceilings 32, bindings 4)" ({slink('7.24')}). For comparison, the {T('GB3')} {T('transformer')} it replaced: 97; widened: 385.</td>
<td>{T('LICENSED')}, one sentence, {T('SYNTHETIC_ONLY')} ({slink('7.56')}). Wired into HELM's live loop by fixes C and D on 2026-10-18.</td></tr>
<tr><td><strong>Wide recipe brain</strong> (RB-W1 v3)<br><code>helm_brain_wide.py</code></td><td>The same learning and answering rules, for real recipes: open ingredient names, exact fractions, up to 10 ingredients, 20 kitchen units.</td>
<td>One requirement coefficient per (recipe, ingredient), learned from one witnessed batch each. Survey estimate, not a measurement: "49,493 coefficients for 9,495 recipes". 9 unit factors are programmed, not learned ({slink('7.83')}).</td>
<td>Canonical-brain candidate, {T('VALIDATED')} for one sentence, {T('NAMED_CORPORA_ONLY')} ({slink('7.89')}). Switch off by default.</td></tr>
<tr><td><strong>{T('RPM Gate')}</strong></td><td>Lets a step go ahead, sends it to repair, or refuses; lets the brain answer {T('UNDETERMINED')}.</td><td>0 (a written rule)</td><td>EARNED_KEEP in waves 1, 2 and 3. Switched off in wave 1, wrong answers rose from 32 to 768 ({slink('7.47')}).</td></tr>
<tr><td><strong>{T('lacuna', 'Lacuna')} cadence</strong></td><td>Keeps track of what HELM could know but was never taught, and when to look again.</td><td>0 (a written rule)</td><td>EARNED_KEEP in waves 2 and 3 ({slink('7.64')}, {slink('7.69')}).</td></tr>
<tr><td><strong>{T('restart fallback', 'Restart fallback')}</strong></td><td>The one place chance is allowed: a few saved random restarts, and the checker decides.</td><td>0 (seeds are saved, not learned)</td><td>EARNED_KEEP in waves 2 and 3.</td></tr>
<tr><td><strong>English reader</strong><br><code>helm_english_in.py</code></td><td>Restates plain kitchen sentences in the checked form, or asks.</td><td>0 (a written program with word lists)</td><td>{T('ENGINEERED-NOT-VALIDATED')}. On fresh real sentences: 0 wrong facts after the fix, but not yet useful ({slink('7.87')}).</td></tr>
<tr><td><strong>Voice</strong><br><code>helm_voice.py</code></td><td>Turns the brain's receipt into one to three plain sentences, then reads its own numbers back.</td><td>0</td><td>EARNED_KEEP; works together with the reader (SYNERGY) ({slink('7.72')}).</td></tr>
<tr><td><strong>{T('CCE')} skin</strong></td><td>The strict English form that converts to CAS and back exactly.</td><td>0 (deterministic parser and renderer)</td><td>NEUTRAL by construction: switching it off changes no answer.</td></tr>
<tr><td><strong>{T('cube store', 'Cube store')}</strong></td><td>Where facts live; an unknown side is reported unknown, never filled.</td><td>0</td><td>EARNED_KEEP in wave 3.</td></tr>
<tr><td><strong>{T('triad', 'Triad')}</strong><br><code>helm_triad.py</code></td><td>Purpose, Wisdom and Power on each ingredient; the weakest face sets how much counts.</td><td>"0 learned parameters"; stored values ceiling 28 ({slink('7.62')})</td><td>Built, default off; EARNED_KEEP in wave 3.</td></tr>
<tr><td><strong>{T('cascade', 'Cascade')}</strong></td><td>Goes down into sub-problems. The owner's decoupling stop decides when to stop; a fuse at depth 12 is the hard limit.</td><td>0</td><td>DECOUPLING_EARNED: 203 descents against 609 for the old fixed cap ({slink('7.69')}).</td></tr>
<tr><td><strong>{T('Unity Eye')}: scan</strong></td><td>Read-only self-check of memory and records; holds back an answer that would use a damaged record.</td><td>0</td><td>EYE_SCAN_EARNED_KEEP, built not validated ({slink('7.77')}).</td></tr>
<tr><td><strong>Unity Eye: pairing</strong></td><td>Counts which mental job works for which motive, and {T('whisper', 'whispers')} the best pair.</td><td>A 7 x 7 table of counts of checked tries; counts, not trained weights</td><td>EYE_PAIRING_EARNED_KEEP, built not validated ({slink('7.78')}).</td></tr>
<tr><td><strong>{T('drive loop', 'Drive loop')}</strong></td><td>Where idle attention goes among the seven {T('Drive', 'Drives')}; paused during conversation.</td><td>0</td><td>NEUTRAL alone in wave 3; with the Eye's pairing, earned its keep in wave 5.</td></tr>
<tr><td><strong>{T('faculty', 'Faculties')}</strong></td><td>Mental jobs such as asking, verifying, pondering, curiosity.</td><td>0</td><td>No faculty word earned on the brain itself ({slink('7.65')}).</td></tr>
<tr><td><strong>Transformer ear</strong> (CTT-1)</td><td>A from-scratch translator, called only when the reader would ask. It may point at your own words and numbers; HELM's own checks decide.</td>
<td>9,585,566 (width 256, 4 + 4 layers); twin 2,482,718; vocabulary 8,349 = 8 specials + 341 CAS tokens + 8,000 English word pieces learned from scratch ({slink('7.82')})</td>
<td>ENGINEERED-NOT-VALIDATED. EARS_NO_GAIN; second exam FAILURE, EARS_HARMED ({slink('7.90')}).</td></tr>
</tbody></table></div>

<h2>Retired and stand-in parts</h2>
<ul class="tight">
<li><code>helm_brain_22x40.py</code>: a demonstration brain. "22" is 22 baking ingredients and "40" is a parameter count, not CAS's 22 pathways or 40 states. No score ({slink('7.51')}).</li>
<li>The old valve: a learned rule with five weights and one bias, trained on the laptop. The owner ruled it be replaced by a plain written rule ({slink('7.50')}).</li>
<li>Scribe L4, an old small English model: 0 of 98 exact on the sealed set ({slink('7.80')}).</li>
</ul>

<h2>What HELM is not</h2>
<ul class="tight">
<li><strong>No foreign pretrained model.</strong> Nothing in HELM was downloaded already trained. The transformer ear was trained from scratch; its run checked "0 pretrained files" ({slink('7.90')}).</li>
<li><strong>The transformer never writes.</strong> It runs in its own process and shares nothing with the brain. It never writes a number or a name; HELM's name table, exact-number rule and round trip decide, and anything saved is read back first ({slink('7.82')}).</li>
<li><strong>Not a general chatbot.</strong> Its world is a kitchen, by design, as a test bed. See the <a href="roadmap.html#chat">chat question</a>.</li>
<li><strong>Not a large language model,</strong> and not trained by preference tuning. See <a href="model-card.html#not-here">what this hub does not have</a>.</li>
</ul>

<h2>How far the language reaches today</h2>
<p>An analyst report measured where each piece of the CAS language map really exists. "Ten frames" are the sentence shapes of the ten
{T('Noetic', 'Noetics')}; "23 fundamentals" are jobs language does, such as saying how much or saying no. The ledger cells cross each fundamental
with each Noetic, {T('Domain')} and {T('Register')}. "CTT" is the transformer ear; "D4" rows come from the {T('SDG')}. The table is copied from the report.</p>
{rows_html}
"""
    return page("architecture.html", "HELM Architecture", "Architecture", lede, body, [
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.24, §7.47, §7.50, §7.51, §7.56, §7.62, §7.64, §7.65, §7.69, §7.72, §7.77, §7.78, §7.80, §7.82, §7.83, §7.87, §7.89, §7.90",
        "`docs/reference/CAS_HELM_DICTIONARY.md` (Cube store, Cascade, Voice, Drive loop, Triad, CCE, Restart fallback)",
        "`CHANGELOG.md` entry '2026-10-18 PDT - FIXES C AND D'",
        f"`{rel(COVERAGE)}` section 1, 'Headline numbers' (copied)",
    ], description="Every HELM part, its learned parameter count, and what HELM is not.")


def p_data(S: dict) -> str:
    need(S, "7.79", "Project Gutenberg", "Tatoeba", "Taskmaster", "Wikibooks")
    need(S, "7.82", "200,000 A-world rows")
    need(S, "7.44", "custodian")
    try:
        xs = json.loads(S["xr_sources"]) if S["xr_sources"] else {}
    except ValueError:
        xs = {}
    groups: dict[str, list] = {}
    for f in xs.get("files", []):
        groups.setdefault(f["file"].split("/")[0], []).append(f)
    names = {"A0_pg_robots": "Project Gutenberg robots file (procedure only)", "A1_pg_catalog": "Project Gutenberg catalog",
             "A1_pg_ebooks": "Project Gutenberg cookery eBooks", "A2_wikibooks": "English Wikibooks dump 20261001",
             "B1_tatoeba": "Tatoeba English sentences", "B2_taskmaster": "Google Taskmaster dialogues"}
    srows = []
    for g, fs in groups.items():
        lic = sorted({f.get("licence", "") for f in fs})
        big = max(fs, key=lambda f: f.get("bytes", 0))
        srows.append(f"<tr><td>{esc(names.get(g, g))}</td><td>{len(fs)}</td><td>{sum(f.get('bytes', 0) for f in fs):,}</td>"
                     f"<td>{'<br>'.join(esc(x) for x in lic)}</td><td><code>{esc(big['file'])}</code><br><code>{esc(big['sha256'])}</code></td></tr>")
    skipped = "".join(f"<li><code>{esc(k)}</code>: {esc(v)}</li>" for k, v in xs.get("skipped", {}).items())
    pin = sha256_file(XR_SOURCES)
    prereg_rows = md_table(S["xr_prereg"], "| ID | Source | State |") if S["xr_prereg"] else []
    lede = "Where every piece of HELM's practice and test material comes from, who was allowed to see it, and which outside text is allowed in."
    body = f"""
<h2>Made-up worlds first</h2>
<p>Almost every HELM result so far was earned on {T('synthetic world', 'synthetic worlds')}: test worlds written by programs, where the right answers are
known. That is why most results carry the {T('claim ceiling')} {T('SYNTHETIC_ONLY')}. The main generators:</p>
<ul class="tight">
<li><strong>The {T('SDG')}</strong> (<code>cas-synthetic/</code>): practice English written from {T('CAS')} statements; 5,802 {T('seed', 'seeds', gloss='starting statements the generator writes English from; elsewhere on this page, a seed is a starting number for random choices')} in <code>cas-synthetic/data/path_d/seeds.jsonl</code> (language-map coverage report).</li>
<li><strong>The kitchen world generator</strong> used to train the {T('transformer')} ear: "200,000 A-world rows" ({slink('7.82')}).</li>
<li><strong>Exam builders</strong> for each test wave: fresh worlds X0 to X5, each built for one run and then spent ({slink('7.44')}, {slink('7.77')}, {slink('7.78')}).</li>
</ul>

<h2>Custody: who may see an exam</h2>
<p>Every scored exam is built by a {T('custodian')}. The builder of the part under test never sees the exam, only its fingerprints
({T('hash', 'hashes')}). The scoring program is {T('sealed')} before the run. In the record's words, the operator "never opened, printed or parsed" an exam file (wave 5 run record).</p>
<ul class="tight">
<li><strong>Seeds from owner lines.</strong> The random draw for an exam is fixed by a fingerprint of the owner's own approval line joined with the sealed package's fingerprint. "No seed could be known before the package bytes were final" ({slink('7.79')}).</li>
<li><strong>Bands.</strong> Each exam draws its seeds from its own range of numbers, so no two exams can share a draw. Example: the transformer ear's exams used bands "CW 1,920,000,001–1,921,000,000 and CD 1,922,000,001–1,923,000,000" ({slink('7.82')}).</li>
<li><strong>Two answer keys.</strong> For the real-text exam, key A was written by the builder and key B by a separate session that read only the written rule. Items where they disagree are not scored; agreement had to be at least 90% ({slink('7.79')}).</li>
</ul>

<h2>Real text: the pinned public sources</h2>
<p>The X-REAL exam (and later tests drawn from the same frames) uses text other people wrote. Every file was downloaded once,
fingerprinted, and pinned. Pin file <code>docs/working/xreal/SOURCES_PINNED.json</code>, sha256 <code>{esc(pin)}</code>.
Results on this material carry the ceiling {T('NAMED_CORPORA_ONLY')}.</p>
<div class="tablewrap verbatim"><table><thead><tr><th>Source</th><th>Files</th><th>Bytes</th><th>Licence (as recorded)</th><th>Largest file and its sha256</th></tr></thead><tbody>{''.join(srows) or '<tr><td colspan="5">Pin file not available.</td></tr>'}</tbody></table></div>
<p class="small">Skipped, with the recorded reason:</p><ul class="small tight">{skipped}</ul>
<h3>The source list as preregistered</h3>
{html_table(prereg_rows)}
<p class="small muted">One recorded slip: the first download request carried the owner's e-mail address in its browser identification string. Every later request used a neutral one ({slink('7.79')}).</p>

<h2>"Foreign questions OK, answers never"</h2>
<p>This is the project's rule for outside material. Text written outside the project, by people or by other AI models, may be used as
<em>questions</em>: the sentences HELM is asked to read. The <em>answers</em> HELM is scored against must never come from an outside model;
they come from HELM's own written rules. Example: the transformer ear's second exam used kitchen sentences written by two outside {T('LLM', 'LLMs')},
labelled LLM_WRITTEN, while its answer keys came from the frozen rules (owner question and coordinator answer, 2026-10-19, in the owner-approvals record; {slink('7.90')}).</p>
<p>No user data is collected for training. HELM UI session logs stay on the local machine in a folder git ignores (<code>helm_ui/README.md</code>).</p>
"""
    return page("data.html", "HELM Data Lineage", "Data lineage", lede, body, [
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.44, §7.77, §7.78, §7.79, §7.82, §7.90",
        "`docs/working/xreal/SOURCES_PINNED.json` (groups, licences, hashes computed by the build)",
        "`docs/working/xreal/PREREGISTRATION_X_REAL.md` section 1 (table copied)",
        f"`{rel(COVERAGE)}` (SDG seed count)",
        f"`{rel(CODEX / '2026-10-19' / 'r1_wave5' / 'run_c40_r1w5_20261019' / 'RUN_RESULT_R1W5_C40.md')}` (operator never opened the exam)",
        f"`{rel(APPROVALS)}` (heading 'Owner question (2026-10-19)'; headings only)",
        "`helm_ui/README.md` (session logs)",
    ], description="Generators, pinned public sources, custody and the outside-material rule.")


def p_compute(S: dict) -> str:
    L = S["ledger"]
    runs = S["runs"]
    rrows = "".join(
        f"<tr><td>{esc(r['date'])}</td><td><code>{esc(r['job'])}</code></td><td>{esc(r['instance'])}</td>"
        f"<td>{esc(r['charge'])}{' USD' if r['charge'] != 'unavailable' else ''}</td><td>{md(r['title'])}</td>"
        f"<td><code>{esc(rel(r['file']))}</code></td></tr>" for r in runs)
    total = sum(float(r["charge"]) for r in runs if r["charge"] != "unavailable")
    secs = S["secs"]
    srows = []
    for k in sorted(secs, key=sec_num):
        if sec_num(k) < 24:
            continue
        t = secs[k]["title"]
        job = section_job(t)
        cost = section_cost(t)
        if classify(k, t)[0] == "rule" or (not job and cost in ("not stated", "0 USD")):
            continue
        srows.append(f"<tr><td>{slink(k)}</td><td>{esc(section_date(t, secs[k]['text']))}</td><td><code>{esc(job or '-')}</code></td><td>{esc(cost)}</td>"
                     f"<td>{md(classify(k, t)[2])}</td></tr>")
    ltxt = (f"<dl class=\"kv\"><dt>Ceiling</dt><dd>{L.get('ceiling_usd')} USD (owner ruling 2026-10-14)</dd>"
            f"<dt>Allocated so far</dt><dd>{L.get('combined_allocation_usd')} USD</dd>"
            f"<dt>Unreserved</dt><dd>{L.get('unreserved_usd')} USD</dd>"
            f"<dt>Ledger stamp</dt><dd><code>{esc(str(L.get('utc')))}</code></dd>"
            f"<dt>Last job in the ledger</dt><dd><code>{esc(', '.join(L.get('last_jobs') or []))}</code></dd></dl>") if L else "<p>Ledger not available on this machine.</p>"
    lede = "What HELM's tests have cost, where they ran, and the rules for which computer does what."
    body = f"""
<h2>The budget</h2>
<div class="card">{ltxt}
<p class="small muted">"Allocated" is the ledger's own total of holds and charges, written as the ledger writes it. It is not a bill.
Charges below are list prices worked out from how long each rented machine ran, rounded up to the cent; the record says "the bill is not posted".
The account's cost report gives daily totals only, so one run's charge cannot be separated from other machines on the same day ({slink('7.47')}).</p></div>

<h2>Paid runs on 2026-10-18 to 2026-10-20 (from the run records)</h2>
<p>Each row is read from a run record file. Instance names are {T('AWS')} machine types: "m6i" and "t3" are ordinary processors; "g5" carries a {T('GPU')}.</p>
<div class="tablewrap"><table><thead><tr><th>Date</th><th>Job</th><th>Machine</th><th>Charge</th><th>Run record title</th><th>File</th></tr></thead><tbody>{rrows or '<tr><td colspan="6">No run records found on this machine.</td></tr>'}</tbody></table></div>
<p class="small">Sum of the charges listed above: <strong>{total:.2f} USD</strong> (computed by this build from the rows; the ledger total above is the authority).</p>

<h2>Every HELM record in the spec sheet with a job or a cost</h2>
<div class="tablewrap"><table><thead><tr><th>Record</th><th>Date</th><th>Job</th><th>Cost as written</th><th>Plain meaning</th></tr></thead><tbody>{''.join(srows)}</tbody></table></div>
<p class="small muted">"Cost as written" is the last amount in the record's heading. Wave 1 (job c34-g) took seven attempts; its run cost is shown in the record only as arithmetic at a named rate, not as a bill ({slink('7.47')}).</p>

<h2>Rules for which computer does what</h2>
<ul>
<li><strong>The laptop is for light work.</strong> The owner, 2026-09-23: "use aws as there is only 354 mb of 16 gbs locally". The 354 MB is the owner's reported snapshot, not a live measurement. Tests, builds and long runs go to rented cloud machines; the laptop edits, launches and downloads (<code>CLAUDE.md</code>).</li>
<li><strong>Quick runs may stay local.</strong> The owner's standing words: "Run it locally as long as it Quick if long use aws" ({slink('7.67')}). Local runs are signed as one process with a time cap, for example "LOCAL_CPU_ONCE on MSI, 300 s cap, no spend".</li>
<li><strong>GPU first for neural work.</strong> No neural network runs on a laptop processor; the local graphics card is for smoke tests only; every claim-bearing neural run goes to a cloud GPU (<code>CLAUDE.md</code>). On 2026-10-18 the owner said "no more GPU for now"; on 2026-10-19 he lifted that for the transformer ear ({slink('7.55')}, {slink('7.82')}).</li>
<li><strong>Every cloud job is recorded:</strong> source, purpose, machine, time and money limits, the owner's sign line, and a cleanup check. Two jobs that skipped this were flagged and kept on the record ({slink('7.53')}).</li>
</ul>
"""
    return page("compute.html", "HELM Compute Costs", "Compute and cost", lede, body, [
        f"`{rel(LEDGER)}` (totals only: ceiling, allocation, unreserved, stamp, last job)",
        "Run records: " + ", ".join(f"`{rel(r['file'])}`" for r in runs),
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.24 to the latest section (headings: job ids and costs), §7.47, §7.53, §7.55, §7.67, §7.82",
        "`CLAUDE.md` (compute escalation ladder; GPU-first rule)",
    ], words=True, description="Budget, cost per run, and the laptop and GPU rules.")


def p_results(S: dict) -> str:
    secs = S["secs"]
    legend, prohibited = S["legend"], S["prohibited"]
    rows = []
    for k in sorted(secs, key=sec_num):
        if sec_num(k) < 24:
            continue
        t = secs[k]["title"]
        kind, color, meaning, lic = classify(k, t)
        words = section_words(t)
        ws = "".join(f'<span class="word">{esc(w)}</span>' for w in words)
        notlic = sec_line(secs[k], r"`?NOT LICENSED`?")
        notshow = sec_line(secs[k], r"What this does not show")
        extra = ""
        if notlic:
            extra += f'<div class="line"><span class="lab">NOT LICENSED (record):</span> {md(notlic)}</div>'
        if notshow:
            extra += f'<div class="line"><span class="lab">What this does not show (record):</span> {md(notshow)}</div>'
        neg = "1" if color in ("failed", "weak") else "0"
        rows.append(
            f'<tr id="s{k.replace(".", "-")}" data-kind="{kind}" data-color="{color}" data-neg="{neg}">'
            f"<td><strong>§{k}</strong></td><td>{esc(section_date(t, secs[k]['text']))}</td><td>{esc(kind)}</td><td>{dot(color)}</td>"
            f"<td>{ws}</td><td>{esc('-' if kind == 'rule' else section_cost(t))}</td><td>{md(meaning)}"
            f'<details><summary>From the record</summary><div class="verbatim" style="padding-left:10px">'
            f'<div class="line"><span class="lab">Heading:</span> {md(t)}</div>{extra}</div></details></td>'
            f"<td>{md(lic)}{' <strong>Negative, kept on purpose.</strong>' if neg == '1' else ''}</td></tr>")
    leg = "".join(f"<tr><td><code>{md(w)}</code></td><td>{md(a)}</td><td>{md(b)}</td></tr>" for w, a, b in legend)
    cl = "".join(f"<tr><td>{dot(c)}</td><td>{esc(COLOR_BAR[c])}</td></tr>" for c in COLORS)
    filters = "".join(
        f'<button class="btn" type="button" data-filter="{f}" aria-pressed="{"true" if f == "all" else "false"}">{esc(n)}</button>'
        for f, n in [("all", "All"), ("scored", "Runs with a reading"), ("neg", "Negatives"), ("packet", "Sealed, not run"),
                     ("rule", "Rules"), ("audit", "Audits of built code")])
    lede = "Every HELM record in the spec sheet, from the first brain test onward. Failures and weak results stay in the table on purpose: they are what keeps every other claim honest."
    body = f"""
<h2>How to read a row</h2>
<p>Each row reads in four layers. Did the run itself hold up (the verdict)? What one word did the scoring program give the part
(the status word)? What may be said (the claim status, using only the legend words below)? And how wide is the claim (the ceiling)?
The color is the owner's scale and is only a reading aid; this hub's editor chose each row's color from the record, and where the record
marks a color itself, the hub uses that one. The "Plain meaning" column is the hub's summary; the record governs.</p>
<div class="filters">{filters}</div>
<div class="tablewrap"><table><thead><tr><th>Record</th><th>Date</th><th>Kind</th><th>Color</th><th>Words from the record</th><th>Cost</th><th>Plain meaning</th><th>What it allows us to say</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>

<h2>The claim-status legend</h2>
<p>These are the only words allowed for what may be said. One word, one meaning, everywhere. Copied from the spec sheet's §3.</p>
<div class="tablewrap verbatim"><table><thead><tr><th>Word</th><th>Means</th><th>Does NOT mean</th></tr></thead><tbody>{leg}</tbody></table></div>
<p class="small">Prohibited on every surface, always (spec sheet §3): <span class="verbatim">{md(prohibited)}</span></p>
<p class="small">No ACCEPT verdict stands anywhere in the project record (spec sheet §1).</p>

<h2>The color scale</h2>
<div class="tablewrap"><table><thead><tr><th>Color</th><th>The bar it must clear</th></tr></thead><tbody>{cl}</tbody></table></div>
"""
    return page("results.html", "HELM Results Scorecard", "Results scorecard", lede, body, [
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §3 (legend and prohibited words, copied), §7.24 onward (headings, dates, costs, 'NOT LICENSED' and 'What this does not show' lines extracted by the build)",
        "Plain meanings and colors: the hub's editor, in `helm_hub/build_hub.py` (table `CUR`); the record governs",
        "`docs/reference/CAS_HELM_DICTIONARY.md` ('How to read a HELM result'; 'Color marks used in owner reports')",
    ], words=True, description="Every HELM result with its status words, cost and meaning, negatives included.")


def p_model_card(S: dict) -> str:
    secs = S["secs"]
    lic1 = sec_quote(secs.get("7.56", {}), "The licensed sentence, verbatim")
    lic2 = sec_quote(secs.get("7.89", {}), "for this sentence only")
    lic3 = sec_line(secs.get("7.90", {}), r"Licensed \(negative, narrow\)")
    nl1 = sec_line(secs.get("7.56", {}), r"Not licensed")
    nl2 = sec_line(secs.get("7.89", {}), r"`?NOT LICENSED`?")
    for q, s in ((lic1, "7.56"), (lic2, "7.89"), (lic3, "7.90")):
        if not q:
            raise SystemExit(f"BUILD STOP: licensed sentence not found in spec section {s}")
    need(S, "7.47", "8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b")
    lede = "The standard facts sheet for a model, adapted to what HELM is: a small brain of written rules, with checks around it."
    body = f"""
<h2>Model details</h2>
<dl class="kv">
<dt>Name</dt><dd>HELM (its licensed brain: the HELM-R1 wave-1 {T('recipe brain')})</dd>
<dt>Package</dt><dd><code>HELM_R1_W1_20261015_v3</code>, freeze sha256 <code>8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b</code> ({slink('7.56')})</dd>
<dt>Type</dt><dd>Written recipes plus exact arithmetic; learned requirement values; no neural network in the brain. Built on {T('CAS')}.</dd>
<dt>Size</dt><dd>Run log: 32 learned slots. The {T('transformer')} it replaced ({T('GB3')}): 97 {T('parameter', 'parameters')} ({slink('7.47')}).</dd>
<dt>Candidate</dt><dd>The wide recipe brain RB-W1 v3 ({slink('7.89')}); the licensed brain stays canonical until a later wave says otherwise.</dd>
<dt>Owner</dt><dd>Little Henderson (Wakil). Confidential.</dd>
</dl>

<h2>What may be said, word for word</h2>
<p>Each sentence below is {T('LICENSED')}: it may be said exactly as written, and nothing wider. Widening the sentence voids it.</p>
<h3>The licensed brain ({T('SYNTHETIC_ONLY')})</h3><blockquote class="verbatim">{esc(lic1)}</blockquote>
<p class="small"><strong>Not licensed (record):</strong> {md(nl1)}</p>
<h3>The wide brain candidate ({T('VALIDATED')} for this sentence only, {T('NAMED_CORPORA_ONLY')})</h3><blockquote class="verbatim">{esc(lic2)}</blockquote>
<p class="small"><strong>Not licensed (record):</strong> {md(nl2)}</p>
<h3>The transformer ear (a narrow negative)</h3><blockquote class="verbatim">{md(lic3)}</blockquote>

<h2>Intended use</h2>
<ul class="tight">
<li>A research instrument: showing that a brain made of recipes can be checked line by line, refuse when unsure, and beat a small transformer on its own exams.</li>
<li>A kitchen test world: stock on hand, recipes, how much can be made, and what runs out first.</li>
<li>Local demonstration through the HELM UI on one machine (<a href="run.html">How to run HELM</a>).</li>
</ul>
<h2>Out of scope</h2>
<ul class="tight">
<li>Real kitchens, real cooks, food safety, nutrition, allergies.</li>
<li>Medical, legal, financial or safety-critical advice of any kind.</li>
<li>General conversation, general knowledge, open-ended English (the reader is kitchen-only; see <a href="roadmap.html#chat">the chat question</a>).</li>
<li>Controlling machines or running tools. In the UI, tool actions are switched off by default.</li>
</ul>

<h2>Claim ceilings</h2>
<p>A {T('claim ceiling')} is the widest world a claim covers. Today there are two. {T('synthetic world', 'Synthetic worlds')} only, for most results;
the named public text collections only, for the real-text tests (listed on <a href="data.html">Data lineage</a>). No HELM claim covers real users.</p>

<h2>Known defects, and what was done</h2>
<div class="tablewrap"><table><thead><tr><th>Defect</th><th>What happened next</th><th>Record</th></tr></thead><tbody>
<tr><td>The pipeline ignored its own {T('round trip')} result, filled missing amounts with an invented 10, and skipped the gate.</td><td>Fixes C and D rewired the licensed brain into the live loop through the gate, with read-back before every write (2026-10-18). Built, not validated.</td><td>{slink('7.49')}</td></tr>
<tr><td>The English reader wrote 8 wrong stock facts on 128 real sentences.</td><td>Reader v1.1 added a stock-frame rule: 0 wrong of 115 scored on a fresh draw. Safe, not yet useful.</td><td>{slink('7.81')}, {slink('7.87')}</td></tr>
<tr><td>The wide brain did not recognise 22 dish names and refused their lessons.</td><td>v3 fixed names, line splitting, ran-out binding and ties; the second sealed test passed (92 of 96 fully learned).</td><td>{slink('7.88')}, {slink('7.89')}</td></tr>
<tr><td>The transformer ear's first run stopped: its write watcher caught library writes.</td><td>The audit rule was fixed and the package resealed; the second run trained and scored (no gain; a failed gate on the second exam).</td><td>{slink('7.85')}, {slink('7.90')}</td></tr>
<tr><td>Wave 1's job supervisor marked a clean run FAIL (it looked for outputs one folder too high).</td><td>Recorded as an instrument defect; kept as recorded, not overwritten.</td><td>{slink('7.47')}</td></tr>
<tr><td>A wave-3 rival arm called "round-robin" also had a lookup table.</td><td>Erratum published; true round-robin scored 31; no word changed.</td><td>{slink('7.69')}</td></tr>
<tr><td>The roadmap said the valve was trained on AWS; it was trained on the laptop.</td><td>Marked a false claim; the valve is now a written rule.</td><td>{slink('7.50')}</td></tr>
<tr><td>Two GPU jobs ran without a ledger line or an owner sign line.</td><td>Flagged for human review; the owner accepted the 2.06 USD after the fact.</td><td>{slink('7.53')}, {slink('7.59')}</td></tr>
</tbody></table></div>

<h2 id="not-here">What this hub does not have, and why</h2>
<p>The usual documents for a large AI language model include sections that do not apply to HELM. They are left out on purpose:</p>
<ul>
<li><strong>Fine-tuning and preference training</strong> (SFT, RLHF, DPO: ways of training a big model on example answers or on people's preferences). HELM's brain learns amounts from witnessed batches by exact arithmetic, with no gradients; there is nothing of this kind to report.</li>
<li><strong>Standard benchmark tables</strong> (such as MMLU or GSM8K, general-knowledge and math-word-problem tests for big models). HELM does not answer general questions. Its scores come from sealed exams built for each part; they are all on the <a href="results.html">Results scorecard</a>.</li>
<li><strong>Compression and serving</strong> (quantization, vLLM: ways to run a huge model cheaply). The brain is tiny and the transformer ear has 9,585,566 parameters; nothing is served to the public.</li>
<li><strong>Training-log dashboards.</strong> The brain has no training curve. The ear's training runs are summarised in their run records (<a href="compute.html">Compute and cost</a>).</li>
<li><strong>A data flywheel</strong> (collecting users' conversations to train on). HELM collects none; session logs stay on the local machine.</li>
<li><strong>A public deployment or API.</strong> There is a local page and local endpoints only (<a href="run.html">How to run HELM</a>). Public hosting is an owner and IP-attorney decision; much of this work is new matter not covered by the provisional patent filing.</li>
</ul>
"""
    return page("model-card.html", "HELM Model Card", "Model card", lede, body, [
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.47, §7.49, §7.50, §7.53, §7.56 (licensed sentence, quoted by the build), §7.59, §7.69, §7.81, §7.85, §7.87, §7.88, §7.89 (§12 sentence, quoted), §7.90 (narrow negative, quoted)",
        "`CHANGELOG.md` entry '2026-10-18 PDT - FIXES C AND D'",
        "`CLAUDE.md` (Confidential; patent filing status and new-matter caveat)",
        "`helm_ui/README.md` (tools off; local only)",
    ], words=True, description="Intended use, limits, claim ceilings, licensed sentences and known defects.")


def p_safety(S: dict) -> str:
    need(S, "7.81", "S_UNSAFE_ON_REAL")
    need(S, "7.90", "H-CWFW")
    need(S, "7.34", "H1")
    need(S, "7.43", "H8")
    need(S, "7.47", "H1_receipts") if "H1_receipts" in S["secs"]["7.47"]["text"] else None
    appr = S["approvals"]
    arows = "".join(f"<tr><td>{esc(w)}</td><td>{md(h)}</td></tr>" for w, h in appr)
    lede = "The rules that stop HELM, and the people building it, from fooling themselves, and the findings where those rules caught a real problem."
    body = f"""
<h2>The rules</h2>
<div class="grid">
<div class="card"><h3>A failed must-hold check is a failure</h3><p>A {T('hard gate')} is a must-hold check written before the run: every write has a {T('receipt')},
nothing is invented, a replay gives the same answer, the controls behave. If one fails, the run is a FAILURE, never "a pass with caveats".
Examples: the {T('faculty', 'faculties')} run failed on gate H1 ({slink('7.34')}); the memory run failed on gate H8 ({slink('7.43')}); the {T('transformer')} ear failed gate H-CWFW ({slink('7.90')}).</p></div>
<div class="card"><h3>Read back before writing</h3><p>Every fact is read back and checked before it counts as saved. A write that fails the read-back is refused and nothing is saved.
Each saved fact leaves a fingerprinted receipt.</p></div>
<div class="card"><h3>The Eye never writes</h3><p>The {T('Unity Eye')} may report a problem and {T('whisper', 'whisper')} a suggestion.
HELM may ignore the whisper. In waves 4 and 5 the Eye made 0 writes ({slink('7.77')}, {slink('7.78')}).</p></div>
<div class="card"><h3>Refuse rather than guess</h3><p>Missing information gives {T('UNDETERMINED')}; unreadable English gives {T('CLARIFY')}; a step that should not run gets REFUSE
from the {T('RPM Gate')}. In each case nothing is saved.</p></div>
<div class="card"><h3>Write audit on the ear</h3><p>The transformer ear runs in its own process, watched by a file-write audit that allows only its own log.
The first run stopped itself when the watcher saw writes made by a library ({slink('7.85')}).</p></div>
<div class="card"><h3>No one marks their own homework</h3><p>A {T('custodian')} builds and {T('sealed', 'seals')} each exam; a {T('frozen reader')} writes the verdict;
an AI model is not the research governor; only the owner's signed line starts a paid run or moves a claim (<code>CLAUDE.md</code>).</p></div>
</div>

<h2>Findings, stated plainly</h2>
<p>These are the tests that found real problems. Each one is kept on the record on purpose.</p>
<ul>
<li><strong>HELM's English reader was not safe on real sentences.</strong> On 128 sentences other people wrote, it saved 8 stock facts the sentences did not say, for example "no water on hand" for a sentence about someone pulled out of the water (a practice example). The limit was 2. The fix brought it to 0 wrong on a fresh draw, but it is not yet useful ({slink('7.79')}, {slink('7.81')}, {slink('7.87')}).</li>
<li><strong>The transformer ear made confident wrong proposals.</strong> On kitchen English written by outside {T('LLM', 'LLMs')}, two of three trained copies proposed more confident, well-formed, wrong readings than the cap of 2 allowed (2 / 5 / 3). Nothing wrong was saved, because HELM's own checks decide, but the gate failed: FAILURE, EARS_HARMED ({slink('7.90')}).</li>
<li><strong>Passing the check proves form, not truth.</strong> An old English model gave 21 confident answers that passed the {T('round trip')} and were all wrong ({slink('7.80')}).</li>
<li><strong>The Eye's scan found nothing a plain checksum missed</strong> on real kinds of file damage; the checksum caught more kinds ({slink('7.81')}).</li>
<li><strong>Process failures.</strong> Two {T('GPU')} jobs ran with no ledger line and no owner sign line ({slink('7.53')}). A roadmap claimed a cloud-trained valve that was trained on the laptop ({slink('7.50')}). A download carried the owner's e-mail address in a request header once ({slink('7.79')}). Each is recorded, not hidden.</li>
<li><strong>Growth has failed or been inconclusive in every run so far</strong>, so HELM growing its own capacity stays NOT {T('LICENSED')} ({slink('7.71')}).</li>
</ul>

<h2>Who decides: the owner's words on record</h2>
<p>Every paid run and every ruling traces to the owner's own words. This table lists the headings of the owner-approvals record
for 2026-10-18 to 2026-10-19 (headings only; dates are Pacific). They name parts of {T('CAS')}, the {T('SDG')} and the idle {T('drive loop')}.</p>
<div class="tablewrap verbatim"><table><thead><tr><th>When</th><th>Heading</th></tr></thead><tbody>{arows or '<tr><td colspan="2">Owner-approvals record not available on this machine.</td></tr>'}</tbody></table></div>
"""
    return page("safety.html", "HELM Safety Record", "Safety and honesty", lede, body, [
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.34, §7.43, §7.47, §7.50, §7.53, §7.71, §7.77, §7.78, §7.79, §7.80, §7.81, §7.85, §7.87, §7.90",
        f"`{rel(APPROVALS)}` (section headings only; no addresses or keys)",
        "`CLAUDE.md` (research governance: a failed hard gate is a FAILURE; Claude is not the research governor)",
        "`docs/reference/CAS_HELM_DICTIONARY.md` (Hard gate)",
    ], description="Hard gates, the never-writes rule, refusal, the write audit, and plain findings.")


def p_roadmap(S: dict) -> str:
    corr_rows = md_table(S["corr"], "| Version | Codename") if S["corr"] else []
    need(S, "7.83", "1 of 13,686")
    need(S, "7.87", "115")
    lede = "Where HELM is meant to go, with an honest status on every line. Kitchen first, as a test world; everything after it is a plan until a test says otherwise."
    domains = [
        ("Kitchen (the test world)", "strong", "Real today, inside limits. The licensed brain is LICENSED on made-up worlds; the wide brain is a candidate, VALIDATED for one sentence on real cookbook recipes. The licensed brain's fixed shapes fit 1 of 13,686 real recipes, which is why the wide brain exists.", "§7.56, §7.83, §7.89"),
        ("Software work", "null", "Authored only. A tool-planning file exists with no recorded output; in the UI, tools are switched off by default.", "Roadmap §2.5 and §2.7; status correction row v0.6"),
        ("Everyday planning", "null", "Partly backed. A prerequisite planner orders steps and refuses loops; one worked plan is recorded; not scored on a sealed exam.", "§7.48; status correction row v0.7"),
        ("Research governance", "rule", "In force as a way of working (custodians, sealed exams, frozen readers, owner sign lines), not as something HELM does by itself.", "§7.55, §9.9 of the spec sheet"),
        ("Safety as a recipe", "partial", "The pieces exist and earned their keep on made-up worlds (the gate, the Eye's scan, refusal). Treating safety itself as a recipe HELM reasons about is not built.", "§7.64, §7.69, §7.77"),
        ("Physical systems (simulated flight, drones, robots)", "null", "Not built. Plans only.", "Roadmap §2.8, §2.9; status correction rows v1.1 to v2.0"),
        ("Science", "null", "Not built. No test exists.", "Roadmap §2.4 (frontier plans)"),
        ("Outputs with checkable receipts", "partial", "Every write in the scored waves is receipted and the receipts held as hard gates; a product that hands receipts to outside users is not built.", "§7.47, §7.64"),
    ]
    drows = "".join(f"<tr><td><strong>{esc(n)}</strong></td><td>{dot(c)}</td><td>{md(t)}</td><td>{md(r)}</td></tr>" for n, c, t, r in domains)
    body = f"""
<h2>The intended domains</h2>
<p>The colors are the owner's scale, as a reading aid; the words are this hub's summary of the records named on the right.
Anything marked "not built" is a plan, and a plan is not a capability.</p>
<div class="tablewrap"><table><thead><tr><th>Domain</th><th>Color</th><th>Honest status</th><th>Records</th></tr></thead><tbody>{drows}</tbody></table></div>

<h2 id="chat">"Can I chat with it?"</h2>
<div class="card">
<p><strong>Yes, on one computer, about a kitchen, and it will often ask you questions back.</strong> The HELM UI is a local page where you type
everyday sentences ("we have 50 flour and 30 sugar", "how much bread can we make?") and every reply opens to the record it rests on
(<a href="run.html">How to run HELM</a>). It is not a general chatbot. Three gaps stand between HELM and one (this hub's summary of the records):</p>
<ol>
<li><strong>Reading.</strong> Its English reader is safe on fresh real sentences but not yet useful: right 115 times against 114 for a reader that always asks ({slink('7.87')}). It reads kitchen sentences only, and none of the ten sentence shapes of the CAS language map (<a href="architecture.html">Architecture</a>).</li>
<li><strong>Knowing.</strong> Its brain knows recipes and nothing else. The licensed brain's shapes fit 1 of 13,686 real recipes; the wide candidate learns real recipes, one witnessed batch per ingredient ({slink('7.83')}, {slink('7.89')}).</li>
<li><strong>Hearing more.</strong> The transformer ear that might widen what it can read gave no gain on real sentences and failed a safety gate on a second exam ({slink('7.90')}). The Eye and the idle {T('drive loop')} are not wired to the live chat window (<code>helm_ui/README.md</code>).</li>
</ol></div>

<h2>The roadmap's milestone table, with an honest status column</h2>
<p>The project's roadmap lists version milestones with its own status words. Those words are not spec-sheet words and carry no evidential weight.
The status correction of 2026-10-18 added an honest column, copied here.</p>
{html_table(corr_rows)}
"""
    return page("roadmap.html", "HELM Roadmap", "Roadmap", lede, body, [
        "`docs/working/HELM_CAPABILITIES_ROADMAP_STATUS_CORRECTION_20261018.md` (milestone table, copied)",
        "`docs/working/HELM_CAPABILITIES_ROADMAP_AND_DEVELOPMENTAL_STAGES.md` §2.4, §2.5, §2.7, §2.8, §2.9 (plans)",
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.47, §7.48, §7.55, §7.56, §7.64, §7.69, §7.77, §7.83, §7.87, §7.89, §7.90, §9.9",
        "`helm_ui/README.md` ('Wired vs not wired')",
        "Domain list: the owner's brief for this hub (2026-10-19), statuses from the records above",
    ], words=True, description="Intended domains with honest status, and the chat question answered plainly.")


def p_glossary(S: dict) -> str:
    entries = S["entries"]
    arts = []
    for e in entries:
        slug = re.sub(r"[^a-z0-9]+", "-", e["term"].lower().strip("`")).strip("-") or "entry"
        lines = "".join(f'<div class="line">{"<span class=lab>" + esc(lab) + ":</span> " if lab else ""}{md(t)}</div>' for lab, t in e["lines"])
        arts.append(f'<article class="entry" id="g-{slug}"><h3><dfn>{md(e["term"])}</dfn> <span class="muted small">{md(e["alias"])}</span>'
                    f'<span class="cat">{esc(e["cat"])}</span></h3><div class="verbatim" style="padding-left:10px">{lines}</div></article>')
    sym = md_table(S["dict"], "| symbol | plain meaning")
    missing_terms = [k for k in TERMS if not any(TERM_RES[k].search(e["term"] + " " + e["alias"]) for e in entries)]
    extra = "".join(f'<article class="entry" id="h-{re.sub(r"[^a-z0-9]+", "-", k.lower())}"><h3><dfn>{esc(k)}</dfn><span class="cat">hub word list</span></h3>'
                    f'<div class="line">{esc(TERMS[k][2])}</div></article>' for k in missing_terms)
    lede = (f"Every entry of the project's CAS and HELM dictionary ({len(entries)} entries), searchable. Each gives the plain meaning first, "
            f"then the precise definition with its source. Canonical text is quoted word for word.")
    body = f"""
<input class="search" id="gsearch" type="search" placeholder="Search the glossary, for example: limiting, custodian, ^4" aria-label="Search the glossary">
<p class="small muted" id="gcount">{len(entries) + len(missing_terms)} entries shown</p>
<details><summary>Symbols and notation (table from the dictionary)</summary>{html_table(sym)}</details>
<section>{''.join(arts)}</section>
<h2>Hub words not in the dictionary as their own entry</h2>
<p class="small muted">These are the plain explanations this hub uses on every page.</p>
<section>{extra or '<p class="muted">None.</p>'}</section>
"""
    return page("glossary.html", "HELM Glossary", "Glossary", lede, body, [
        "`docs/reference/CAS_HELM_DICTIONARY.md` (all A-Z entries and the symbols table, rendered by the build)",
        "Hub word list: `TERMS` in `helm_hub/build_hub.py`",
    ], description="Every CAS and HELM term, searchable, plain meaning first.")


HELM_CL = re.compile(r"HELM|\bRB[- ]?[A-Z0-9]|CTT|RTR-1|X-REAL|Scribe|Unity Eye|\bU1|\bU3|lexicon|English reader|dictionary|"
                     r"helm_|DWP|triad|LM-T|recipe brain|\bGB\d|wave \d|Gate B", re.I)


def p_changelog(S: dict) -> str:
    text = S["chlog"]
    ents = []
    cur = None
    for ln in text.splitlines():
        m = re.match(r"^## (\d{4}-\d\d-\d\d)\b\s*(?:PDT|PST|UTC)?\s*[-:]?\s*(.*)$", ln)
        if m:
            cur = {"date": m.group(1), "title": m.group(2).strip(), "body": []}
            ents.append(cur)
            continue
        if ln.startswith("## ") or ln.startswith("# "):
            cur = None
            continue
        if cur is not None:
            cur["body"].append(ln)
    keep = [e for e in ents if e["date"] >= "2026-10-01" and HELM_CL.search(e["title"])]
    items = []
    for e in keep:
        lis, paras = [], []
        for ln in e["body"]:
            if ln.startswith("- "):
                lis.append(ln[2:])
            elif ln.startswith("  ") and lis:
                lis[-1] += " " + ln.strip()
            elif ln.strip():
                paras.append(ln.strip())
        inner = "".join(f"<p>{md(p)}</p>" for p in paras) + ("<ul>" + "".join(f"<li>{md(x)}</li>" for x in lis) + "</ul>" if lis else "")
        items.append(f'<article class="entry"><h3 class="verbatim" style="padding-left:10px">{esc(e["date"])}: {md(e["title"])}</h3>'
                     f'<details><summary>Details as written</summary><div class="verbatim small" style="padding-left:10px">{inner}</div></details></article>')
    lede = (f"HELM's own entries from the project changelog since 2026-10-01, newest first ({len(keep)} entries). Titles and details are copied as written.")
    body = "<section>" + "".join(items) + "</section>"
    return page("changelog.html", "HELM Changelog", "Changelog", lede, body, [
        "`CHANGELOG.md` (entries dated 2026-10-01 or later whose title names a HELM part, test or record; filter `HELM_CL` in `helm_hub/build_hub.py`)",
    ], words=True, description="HELM entries from the project changelog, newest first.")


def p_run(S: dict) -> str:
    ui = S["ui_readme"]
    endpoints = md_table(ui, "| Method | Path")
    wired = ""
    m = re.search(r"## Wired vs not wired \(honest list\)\n(.*?)(?:\n## )", ui, re.S)
    if m:
        wired = "<ul class=\"verbatim\">" + "".join(f"<li>{md(x[2:])}</li>" for x in m.group(1).splitlines() if x.startswith("- ")) + "</ul>"
    lede = "HELM runs on one computer, in a calm local page. Here is how to start it, what you will see, and the rules for which computer does what."
    body = f"""
<h2>Try it without installing anything</h2>
<p>The <a href="demo.html">demo page</a> is a recorded HELM session. It needs no server: open it and read each reply's record.</p>

<h2>Run the live page</h2>
<pre>python helm_ui/server.py</pre>
<p>Then open <code>http://127.0.0.1:8765</code>. The server listens on this computer only. It needs FastAPI and uvicorn.
Tests: <code>python -m pytest helm_ui/tests -q</code>. Page options: <code>?theme=dark|light</code>, <code>?records=1</code>.</p>
<p>Type everyday kitchen sentences. HELM's reply comes with a plain status and a "Show the record" link that opens what was saved,
the gate's verdict, and the {T('receipt')}. If HELM cannot read a sentence, it asks one question and saves nothing.</p>

<h2>What is wired and what is not</h2>
<p>The list below is copied from the UI's own notes. It mentions the {T('Unity Eye')}, which may {T('whisper')} suggestions; the idle {T('drive loop')},
which moves attention among the seven {T('Drive', 'Drives')}; and test copies built from a fixed {T('seed')}.</p>
{wired or '<p class="muted">UI README not available.</p>'}

<h2>Local endpoints</h2>
<p>For developers: the page talks to these addresses on the same computer. Only <code>POST /turn</code> can change HELM's state.</p>
{html_table(endpoints)}

<h2>Rebuild this hub</h2>
<pre>python helm_hub/build_hub.py</pre>
<p>The build reads the spec sheet, the dictionary, the roadmap and its correction, the changelog, the run records and the ledger totals,
then writes <code>helm_hub/site/</code>. It checks every page for unexplained jargon, broken links, and anything that looks like a secret or an
e-mail address, and fails if it finds one. It runs on the laptop in seconds.</p>

<h2>Laptop rules</h2>
<ul class="tight">
<li>Heavy work goes to rented {T('AWS')} machines; the laptop is for light editing, launching and downloading (owner, 2026-09-23).</li>
<li>Local runs stay small: one process, a time cap such as 300 s, and no spend.</li>
<li>Neural network training never runs on the laptop's processor; it goes to a cloud {T('GPU')}.</li>
</ul>
<p>Details and costs: <a href="compute.html">Compute and cost</a>.</p>
"""
    return page("run.html", "Running HELM", "How to run HELM", lede, body, [
        "`helm_ui/README.md` (run command, options, endpoints table copied, 'Wired vs not wired' copied)",
        "`helm_ui/demo/index.html` (copied to `demo.html`)",
        "`CLAUDE.md` (compute rules)",
    ], description="Start the HELM UI, open the demo, and rebuild the hub.")


# --------------------------------------------------------------------------------------------
# Checks: jargon lint, links, secrets, page contract
# --------------------------------------------------------------------------------------------
class _Lint(HTMLParser):
    SKIP = {"head", "script", "style", "nav", "footer", "title"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str, bool]] = []  # (tag, dfn-keys, skip)
        self.first: dict[str, tuple[bool, str]] = {}
        self.bad_dfn: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("meta", "link", "br", "input", "img", "hr"):
            return
        cls = (a.get("class") or "").split()
        skip = tag in self.SKIP or "gloss" in cls or "precise" in cls
        keys = a.get("data-term", "") if tag == "dfn" else ""
        if tag == "dfn" and keys and len((a.get("title") or "").strip()) < 12:
            self.bad_dfn.append(keys)
        self.stack.append((tag, keys, skip))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if any(s for _, _, s in self.stack):
            return
        open_keys = set()
        for _, k, _ in self.stack:
            if k:
                open_keys.update(k.split("|"))
        for key, rx in TERM_RES.items():
            if key in self.first:
                continue
            m = rx.search(data)
            if m:
                self.first[key] = (key in open_keys, data[max(0, m.start() - 40):m.end() + 40].strip())


def lint_page(path: Path) -> list[str]:
    p = _Lint()
    p.feed(path.read_text(encoding="utf-8"))
    errs = [f"{path.name}: term '{k}' first used unexplained: ...{ctx}..." for k, (ok, ctx) in p.first.items() if not ok]
    errs += [f"{path.name}: <dfn data-term={k}> has no plain explanation" for k in p.bad_dfn]
    return errs


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.ids: set[str] = set()
        self.scripts: list[str] = []
        self.styles: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(("a", a["href"]))
        if tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        if tag == "link" and a.get("href"):
            self.styles.append(a["href"])
        if tag in ("img", "iframe") and a.get("src"):
            self.links.append((tag, a["src"]))


SECRET_RES = [
    ("e-mail address", EMAIL_RE),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("AWS secret key name", re.compile(r"aws_secret_access_key|aws_session_token", re.I)),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b|github_pat_[A-Za-z0-9_]{20,}")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("password assignment", re.compile(r"\bpassword\s*[:=]\s*\S{4,}", re.I)),
]
PROHIBITED_RE = re.compile(r"\bcertified\b|\bguaranteed\b|100%|\bworld-first\b|court-admissible|regulator-grade by construction", re.I)


class _Prohib(HTMLParser):
    """Prohibited words in the hub's own text (quoted record text inside .verbatim is exempt)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []
        self.hits: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("meta", "link", "br", "input", "img", "hr"):
            return
        a = dict(attrs)
        ex = tag in ("script", "style", "head") or "verbatim" in (a.get("class") or "").split()
        self.stack.append((tag, ex))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if any(e for _, e in self.stack):
            return
        for m in PROHIBITED_RE.finditer(data):
            self.hits.append(data[max(0, m.start() - 30):m.end() + 30])


def check_site(site: Path = SITE) -> dict:
    pages = sorted(site.glob("*.html"))
    report = {"pages": len(pages), "lint": [], "links": [], "secrets": [], "contract": [], "prohibited": [], "emoji": []}
    ids: dict[str, set[str]] = {}
    parsed: dict[str, _Links] = {}
    for p in pages:
        t = p.read_text(encoding="utf-8")
        lp = _Links()
        lp.feed(t)
        ids[p.name] = lp.ids
        parsed[p.name] = lp
        for name, rx in SECRET_RES:
            for m in rx.finditer(t):
                report["secrets"].append(f"{p.name}: {name}: {m.group(0)[:12]}...")
        if p.name == "demo.html":
            continue
        head = t[:600].lower()
        for need_s in ("<!doctype html>", '<meta charset="utf-8">', 'name="viewport"'):
            if need_s not in head:
                report["contract"].append(f"{p.name}: missing {need_s}")
        mt = re.search(r"<title>(.*?)</title>", t)
        if not mt or not (2 <= len(mt.group(1).split()) <= 4):
            report["contract"].append(f"{p.name}: title must be 2-4 words")
        for s in lp.scripts:
            report["contract"].append(f"{p.name}: external script {s}")
        for s in lp.styles:
            if s.startswith("http") and not s.startswith(("https://fonts.googleapis.com", "https://fonts.gstatic.com")):
                report["contract"].append(f"{p.name}: external stylesheet {s}")
        for need_s in (':root:not([data-theme="light"])', ':root[data-theme="dark"]', "prefers-color-scheme: dark", "body{margin:0;background:"):
            if need_s not in t:
                report["contract"].append(f"{p.name}: style contract missing {need_s}")
        c1 = re.search("[\x80-\x9f]", t)
        if c1:
            report["contract"].append(f"{p.name}: C1 control character U+{ord(c1.group(0)):04X} (a lost backslash escape?) near {t[max(0, c1.start() - 30):c1.start()]!r}")
        if EMOJI_RE.search(re.sub(r"<script>.*?</script>", "", t, flags=re.S)):
            report["emoji"].append(p.name)
        if p.name != "glossary.html":
            report["lint"] += lint_page(p)
        pr = _Prohib()
        pr.feed(t)
        report["prohibited"] += [f"{p.name}: ...{h}..." for h in pr.hits]
    for name, lp in parsed.items():
        for kind, href in lp.links:
            if href.startswith(("http://", "https://", "mailto:")):
                if name != "demo.html":
                    report["links"].append(f"{name}: external link {href}")
                continue
            target, _, anchor = href.partition("#")
            target = target or name
            if target not in ids:
                report["links"].append(f"{name}: broken link {href}")
            elif anchor and anchor not in ids[target]:
                report["links"].append(f"{name}: missing anchor {href}")
    return report


# --------------------------------------------------------------------------------------------
def build() -> dict:
    t0 = time.perf_counter()
    S = load()
    if SITE.exists():
        for f in SITE.glob("*.html"):
            f.unlink()
    SITE.mkdir(parents=True, exist_ok=True)
    pages = {
        "index.html": p_home(S), "thinking.html": p_thinking(S), "architecture.html": p_architecture(S),
        "data.html": p_data(S), "compute.html": p_compute(S), "results.html": p_results(S),
        "model-card.html": p_model_card(S), "safety.html": p_safety(S), "roadmap.html": p_roadmap(S),
        "glossary.html": p_glossary(S), "changelog.html": p_changelog(S), "run.html": p_run(S),
    }
    for name, content in pages.items():
        content = EMAIL_RE.sub("[e-mail removed]", content)
        (SITE / name).write_text(content, encoding="utf-8", newline="\n")
    if UI_DEMO.exists():
        demo = read(UI_DEMO)
        (SITE / "demo.html").write_text(demo, encoding="utf-8", newline="\n")
    else:
        MISSING.append(rel(UI_DEMO))
    sizes = {f.name: f.stat().st_size for f in sorted(SITE.glob("*.html"))}
    return {"seconds": round(time.perf_counter() - t0, 3), "sizes": sizes, "missing": sorted(set(MISSING))}


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    info = build()
    rep = check_site()
    total = sum(info["sizes"].values())
    print(f"HELM Hub built in {info['seconds']} s -> {rel(SITE)} ({len(info['sizes'])} pages, {total:,} bytes)")
    for n, s in info["sizes"].items():
        print(f"  {n:<20} {s:>9,} bytes")
    if info["missing"]:
        print("Sources not available on this machine: " + "; ".join(info["missing"]))
    ok = True
    for key in ("lint", "links", "secrets", "contract", "prohibited", "emoji"):
        items = rep[key]
        print(f"{key:<11} {'PASS' if not items else 'FAIL (' + str(len(items)) + ')'}")
        for it in items[:40]:
            print("   - " + it)
        ok = ok and not items
    print("Generated at", GEN_AT)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
