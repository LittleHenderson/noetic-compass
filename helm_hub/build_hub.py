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
    "wave": (r"(?<!pair )(?<!PAIR )\bwaves?\b", re.I, "one sealed test round in the HELM-R1 series, with each part on its own switch"),
    "wide brain": (r"\bwide (?:recipe )?brains?\b", re.I, "the recipe brain with its ingredient list opened up (any ingredient name, up to 10 per recipe, exact fractions, 20 units), behind a switch; HELM's canonical-brain candidate, not yet canonical"),
    "pair wave": (r"\bpair[ _-]?wave\b", re.I, "wave 6: the wide brain run together with HELM's other parts to read how each pair behaves"),
    "chat wave": (r"\b[Cc]hat[ _-]?wave\b", 0, "wave 7: HELM's chat window typed to line by line, with the wide brain on, scored on three fresh exams the builder never sees"),
    "spent exam": (r"\bspent exams?\b", re.I, "an exam that has already been scored; its item ids go on the exclusion list, so no later exam can reuse them and showing its lines tunes nothing"),
    "CTT": (r"\bCTT(?:-[0-9A-Z]+)?\b", 0, "the CAS-token transformer, HELM's optional 'ear': a small translator that proposes a reading only when HELM's own reader would ask, and never writes"),
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


def words_box(body_html: str, open_: bool = True) -> str:
    """For generated pages: a box that explains every listed term used on the page, placed first."""
    text = re.sub(r"<[^>]+>", " ", body_html)
    text = html.unescape(text)
    used = [k for k in TERMS if TERM_RES[k].search(text)]
    if not used:
        return ""
    items = "".join(
        f'<div class="w"><dt><dfn data-term="{esc(k)}" title="{esc(TERMS[k][2])}">{esc(k)}</dfn></dt>'
        f'<dd class="gloss">{esc(TERMS[k][2])}</dd></div>' for k in used)
    return (f'<details class="words"{" open" if open_ else ""}><summary>Words used on this page, in plain English</summary>'
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
    "7.125": ("packet", "partial", "Cubes and memory, designed and built behind a switch that is OFF by default. NEWEST (follow-up 9, 2026-10-22): when a question finds nothing on the device and HELM is online, the Eye now also searches the folded rows stored in the cloud, checking each one, and keeps nothing it read. On the test chat, old lines found exactly by their own words went from 1 of 30 to 30 of 30. The cost is time: about 9 cloud reads per question, estimated at about 10 seconds on the real bucket (an estimate from the earlier live test, not a measurement). Offline, those rare words still cannot be found. 467 HELM tests pass. Before that (follow-up 8): each memory capsule now keeps the clue words of every line it holds, not only its first lines, so any old line can be found by its own words. At the owner's 53,370-byte limit, an 8,000-line chat stays under the limit (48,743 bytes) and 30 of 30 sampled old lines came back exact (before: 1 of 30). The cost: bigger rows push small limits (4,000 bytes) over, and once the folded rows are in the cloud, rare words past each row's 48-word cap cannot be found (HELM then says it does not know, never a wrong line). 462 HELM tests pass. Before that (follow-up 7): the Eye now folds old index rows together, 8 into 1, and then 8 of those into 1, level upon level, each folded row keeping at most 48 clue words; the folded rows themselves go to the device's folder (then the cloud), and a question that misses the kept words searches the folder. An 8,000-line chat stays under the owner's 53,370-byte limit (it would be 100,721 bytes without folding; it ends at 52,429), and old memories still come back exact (20 of 20 sampled). The floor grows by about 3,500 bytes per level and each level covers 8 times more, so 53,370 bytes holds for about 14 levels; a small 4,000-byte limit is below the floor once two levels exist. 453 HELM tests pass. Before that (follow-up 6): when memory is still too full, the Eye now moves the oldest capsules out of working memory to the device's folder (and later to the cloud), keeping only a small index row of clue words; a question that matches the index fetches that one capsule back and checks it against its receipt before answering. A 300-line chat now fits a 3,000-byte limit (7,145 down to 2,830 bytes), but a 600-line chat at 4,000 still goes over (26,034 down to 10,870 bytes), because the index also grows with the chat. 440 HELM tests pass. Before that (follow-up 5): the Eye now runs the memory capsules. It stores only what cannot be rebuilt (the clue words, the CAS digits, the fingerprint of the original, the bound cubes, the weight and the receipt), rebuilds everything else every time a capsule is used, and refuses to use a capsule whose rebuild does not match its receipt. One capsule went from 812 to 281 bytes; working memory now stays under the limit for 200 lines at a 4,000-byte limit (3,955 bytes) and for 2,000 lines at the owner's 53,370 bytes (48,745 bytes), but a 600-line chat at 4,000 still goes over (26,126 bytes), because capsules still pile up. 429 HELM tests pass. Before that (follow-up 4): HELM now keeps every line word for word until its working memory reaches 53,370 bytes (the owner's number), then folds the oldest lines into one CAS capsule per batch, and when the device's own folder of original lines passes 50 MB the oldest originals move to a private, encrypted, versioned storage folder on Amazon's cloud that nothing deletes (helm-cold-memory-807562639912-usw2). With Wi-Fi, HELM fetches them back and checks their fingerprint before calling a memory exact; without it HELM says its full notes are stored away and never claims exact. A live test moved 7 made-up originals and fetched them back. Measured, and not hidden: the capsules stay in working memory and are nearly as big as the lines they replace, so memory still grows past the limit (11,165 bytes against a 4,000 limit after 200 lines); keeping under the limit needs the owner's next design choice. 414 HELM tests pass. A fact the person teaches is kept only when two readers agree twice in at most three rounds: HELM's trained translator between English and CAS symbols proposes a reading, and the brain side checks it and says it back. If they never agree, HELM keeps the person's words and asks. The first build made its own kind of cube and its own reader; the owner pointed out that a cube system already existed. The work was redone on it, the Cube Node Schema v0.1: every named thing is a cube with six sides (what it is, its context, an analogy or metaphor, a mapping, its parts, how the parts fit), and a fact is an edge between two cubes that records what the two have in common. Answers go through the schema's three questions: what does it hold, what do two things share, how are two things related. A side nobody taught stays marked unknown and is never invented. 41 tests; all 395 HELM tests pass. Measured: fading old memories into CAS records costs space on short sentences instead of saving it (53,370 bytes against 2,450 for keeping every line). LESSON FOR WHOEVER COMES NEXT: before any cube or node work, read Cube_Node_Schema_v0.1 and the code where HELM keeps its facts as cubes; never build a second parser or a second kind of cube.", "Nothing licensed; built, not validated. Tests use a stand-in reader, not the trained translator, which still needs retraining on this kind of fact (owner line CUBE TRAIN at 3 USD, not yet typed)."),
    "7.121": ("scored", "null", "The memory-compaction exam (TEACH-1) ran once on the laptop: 16 made-up worlds (hive yards and bus lines), 512 teaching lines written by three AI companies and checked by the other two, seven ways of remembering. Every honesty and integrity check held: 4,029 memory answers were labelled correctly and nothing was invented. The word is INCONCLUSIVE, because the never-forget arm gave 7 answers the frozen scorer counts wrong: in each, HELM quoted the person's own correction (\"eight; I said seventeen before\") and the scorer read the old number as a wrong value. Compaction recalled 148 more answers than today's memory and lost none against never forgetting on clean notes, but tied a plain text note. The taught facts never became cubes.", "INCONCLUSIVE; nothing licensed. The scoring of quoted corrections is the owner's ruling before any rerun."),
    "7.115": ("packet", "null", "Memory compaction, from design to a sealed exam: when HELM's working memory fills, old turns are packed into small CAS capsules with clue words, a pointer to a safe copy and a receipt; a question fetches the original first and asks a refresh question only when the copy is gone; a rebuilt memory is never called exact. Built behind a switch that is OFF by default; the exam TEACH-1 was built, sealed and later run (7.121).", "Built, not validated; nothing licensed."),
    "7.122": ("scored", "partial", "The Unity Eye acting inside the live HELM loop, behind a switch that is OFF by default, took its sealed exam (200 made-up worlds, 7 ways of running, seeded by the owner's own line). Every safety check held. Acting beat holding: on 320 damaged questions the concert Eye gave 240 right answers, asked on 80 where nothing could be rebuilt, and was never wrong, while HELM with no Eye was wrong on all 320. A rule that keeps backup copies was fooled 80 times by a bad lesson the Eye caught. But a plain rule with no Eye, rebuild from the user's words before every answer, did exactly as well as the Eye on every answer.", "EYE_ACT_EARNED_KEEP and CONCERT_ACT_EARNED_KEEP for this test only, on made-up worlds; built, not validated. The Eye's acting stays NOT LICENSED and the switch stays OFF until the owner rules."),
    "7.120": ("packet", "null", "Two design answers to the owner, nothing built or run. First: who should decide when HELM looks deeper into a problem? An exact arithmetic rule at the gate, not the Eye; the owner's own decoupling stop already does this and earned its keep on made-up worlds (7.69). The Eye's right job is to check that rule from outside, and later, with a new ruling, to ask for more depth but never less. In today's live chat there is no depth choice to make, so a decider there would measure nothing. Second: the HELM Cube, a concept for HELM's final home: a 64 mm black cube that looks the same on all six faces when off, light along all twelve edges, a magnetic charge face found by feel, hidden cameras, microphones and depth sensors on every face, and everything feeding HELM.", "Nothing; designs only. The Eye's acting stays NOT LICENSED; the cube is a concept with no part bought or measured."),
    "7.119": ("scored", "failed", "Wave 7 ran a sixth time (job c56) with the reader fix of 7.117 in and a fresh exam. Every instrument check and every must-hold check held, though the instrument's code does not do what its written rule says (see below). This time the chat got every one of the 64 dialogues right, with none wrong and none left unsure (the fifth round got 2 wrong), and the copy with small talk mixed in read the same. On the real recipes it got 93 right and none wrong, and asked on 15. But two marks failed. On one recipe the book line ended with a loose 'or', so the reader tied a 'ran out' sentence to the next line and the brain stored a wrong amount; a wrong stored amount fails the safety mark. On another recipe one book line held two amounts, the lessons never taught the second, and HELM asked; the ask was honest, but the frozen rule does not accept it, so the honesty mark failed. Both faults happen the same way without the chat layer, so they belong to the reader and brain, not the chat. The instrument's own written rule says that second recipe's question should have been left unscored, but its code scores it. That rule was written by this project's operator, and its code never did what the text said: the mistake is the builder's. The conflict is left for the owner to decide, and this round is not re-scored. By the frozen words this reads HARMED. 0.02 USD.", "Nothing. A recorded failure of the safety mark and the honesty mark with every instrument check and hard gate held; the chat stays NOT LICENSED. Every dialogue right is a fact about this one draw, not a license. The next fix, proposed only: a line ending in a loose 'or' is one ingredient with an alternative, and a 'ran out' sentence that could fit two lines must ask, never guess."),
    "7.118": ("packet", "null", "Wave 7, the sixth round's packet, frozen and fingerprinted again as v9 with exactly three changes on v8: HELM is cut at the merged reader fix of 7.117 (a sentence shaped like a stated fact about an ingredient HELM does not hold now makes it ask and hold its answer; plural and spelling forms of a held name are found; a measure phrase such as \"a dash of pepper\" after a comma is its own line), the ids of the fifth round's exam can never be drawn again, and the number ranges for the exam draw are fresh; the line the owner would sign, CHAT WAVE 6 at 1 USD, is proposed only. The machine's own test list of 12 files was run from the frozen copy (280 tests, OK). On the builder's practice dialogues the chat gets 63 of 64 right with 0 wrong and asks on 1, exactly as v8 did, because none of the practice dialogues has the shapes the fifth round got wrong; the loop driven directly 59 right, 0 wrong; real recipes unchanged; every mark true. Not launched.", "No claim from the packet itself; the practice numbers are facts about practice data, not a result, and they cannot show the fix works."),
    "7.114": ("packet", "null", "Wave 7, the fifth round's packet, frozen and fingerprinted again as v8 with exactly two changes on v7: HELM is cut at the merged reader fix of 7.113 (a stock sentence's clause that names the held ingredient by a longer or hyphenated phrase is now read, and a clause the reader cannot read makes the next question ask instead of answering), and the number ranges for the exam draw are fresh; the owner line CHAT WAVE 5 at 1 USD is kept, since it was never bound to v7. The machine's own test list of 12 files was run from the frozen copy (273 tests, OK). On the builder's practice dialogues, the same ones v7 got 4 wrong, the chat now gets 63 of 64 right with 0 wrong and asks on 1; the loop driven directly 59 right, 0 wrong; real recipes unchanged; every mark true. Not launched.", "No claim from the packet itself; the practice numbers are facts about practice data, not a result."),
    "7.117": ("packet", "null", "The reader fix after c55, tests first. Three general rules: a sentence shaped like a stated fact about an ingredient HELM does not hold now makes it ask and hold its answer instead of treating the sentence as small talk; plural and spelling forms of a held name are found; and a measure phrase such as \"a dash of pepper\" after a comma is its own line, so its running-out can never be charged to the ingredient before it (the cause of c55's one wrong lesson). Seven new tests, five of which fail on the old reader; all 280 HELM tests pass. Replaying c55's three faults by program now gives two asks and one refusal. 0 USD.", "Nothing; a build. The chat stays NOT LICENSED until a fresh sealed draw on the owner's own line reads every mark true."),
    "7.116": ("scored", "failed", "Wave 7 ran a fifth time (job c55) with the reader fix in and a fresh exam. The instrument was clean again, and the asking mark that failed twice before now holds: every one of the chat's 13 asks on real recipes had an accepted reason. On the dialogues the chat went from 44 right and 20 unscored to 62 right of 64, reading the stated faces and purposes. But it answered twice where it should have applied a stated fact or asked, because the sentence named the ingredient by a word the brain had not learned, and one lesson on the real recipes was wrong. A wrong answer fails the safety mark, so by the frozen words this reads HARMED. 0.02 USD.", "Nothing. A recorded failure of the safety mark with a clean instrument; the chat stays NOT LICENSED. The next fix: a face-shaped sentence about a thing the brain does not hold must ask, never be treated as small talk."),
    "7.110": ("packet", "null", "The talk packet, a design only: how HELM would hold a normal conversation. Three layers: the transformer ear, retrained so it can say \"nothing to save\" on purpose and asked only where HELM's own reader cannot read a line, with its three copies voting and a question before anything is used; the recipe brain, untouched; and the voice guarding every reply (no notation, no recipe words on a greeting, exact amounts, an honest \"I don't know\"). The exam was first designed to be typed by four named people; on the owner's word of 2026-10-21 (amendment A-TALK-1) the owner writes no turns and reviews only, every exam turn is written by AI models of at least three families and keyed by a different family, and a pass could only ever say \"AI-written turns\", never \"human-written\" (ceiling LLM_WRITTEN_ONLY). Off-topic turns get a rule: react in one line, keep what was said, ask about what HELM knows, never an opinion or an untold fact. Part M adds a trained mouth (the same translator run CAS to English) that may choose words, never facts, scored against today's templated voice. A 30-line keyword rule is the cheap rival the ear must beat. Two owner lines on record, TALK TRAIN at 3 USD and TALK EXAM at 1 USD, each bound to a package not yet built. Nothing built, nothing trained, nothing run.", "Nothing; a design. Every part keeps its standing; the ear's earlier words (no gain on real sentences; harmed on machine-written ones) stand."),
    "7.107": ("packet", "null", "Wave 7, round 4: the one test that failed on job c53's machine was traced by program to a stored fingerprint of the loop's records that carried the licensed brain's folder path; reporting the machine's path on the laptop reproduces the machine's value exactly, so HELM's answers never differed. A second builder made the test pins machine-neutral (the folder and the two receipts that depend on it are cut out before hashing; a hygiene test guards the class); the first attempt was shown insufficient by diff and replaced. The chat wave packet v6 is frozen and fingerprinted on that code, and its freeze step now runs exactly the machine's own test list with the machine's own command (245 tests, OK); not launched; waits for the owner's line CHAT WAVE 4 at 1 USD. Practice numbers equal v5's exactly.", "No claim from the packet itself; the test fix is built and checked on the laptop, not yet on a machine."),
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
    "7.35": ("scored", "null", "Language carried station by station through the brain. The reader frozen before that run read INCONCLUSIVE because of two defects of its own (digits inside outcome names counted as values; the twin's eye events counted without their rows); a reader corrected after the run read better, but a post-run change cannot count. Settled by the clean rerun in 7.100.", "Nothing from this run itself; see 7.100."),
    "7.100": ("scored", "strong", "The same language exam run again on the owner's word, with the run code byte-identical and the two reader defects fixed and frozen before any part ran. 8 of 8 parts completed; every number equals the first run's (64,756 of 64,756 sentences round-tripped, 106,400 of 106,400 digests unchanged, 240 of 240 planted utterances routed, 0 of 240 shuffled ones); all 14 must-pass checks held and the reader printed its four words. One mark still fails: 80 of 106,400 provenance keys were written wrong by the run code, a defect the owner's order did not cover, so it stays a failure.", "LICENSED for the reader's own sentence only: on made-up worlds, the brain's thought was read in checked English at every station with a receipt and no answer changed; speech started the right faculty at the right station; earlier, not better. No claim about an RPA (the owner ruled RPA means the Atlas), no meaning claim, no HELM claim."),
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
    "7.91": ("packet", "null", "Wave 6, the pair wave: the wide brain run alongside HELM's other parts, switched off together with each one, to read how each pair behaves; the step that decides whether the wide brain can become HELM's main brain. Practice runs found reading defects, fixed first in RB-W1 v4 (commit cb3db850). It then ran as job c48 (see §7.93).", "No claim from the packet itself."),
    "7.93": ("scored", "weak", "Wave 6, the pair wave, ran. With every other part on, the wide brain did no harm (0 items lost on every exam), fully learned 97 of 101 real recipes with 96 right and 0 wrong, and the Eyes stayed quiet. But it asked once, without a reason, on a recipe it had fully learned; the frozen mark allows 0 such asks, so the word is WIDE_WAVE_NO_GAIN. No move: the wide brain stays a candidate and the licensed brain stays canonical.", "Nothing new. Negative kept: one unexplained ask (mark K4 missed)."),
    "7.90": ("scored", "failed", "The transformer ear trained fully. No gain on real sentences (106 / 106 / 105 against the reader's 107). On LLM-written kitchen English it lifted right answers, but broke the cap on confident wrong proposals: FAILURE, EARS_HARMED.", "A narrow negative sentence only. Not 'the ears help'."),
    "7.92": ("packet", "null", "The ear's agreement-rule test, sealed: the ear's three trained copies must all give the identical checked reading before HELM offers it, and then only as a question the user confirms. No retraining. It then ran as job c49 (see 7.95).", "No claim from the packet itself."),
    "7.96": ("scored", "win", "The pair wave re-run (job c50), after the reader defect was fixed. With every other part on, the wide brain did no harm where the marks look (0 items lost on English-64, Faces-64 and the three made-up-world families; 1 of 64 conversation items lost, limit 2), fully learned 93 of 94 real recipes with 94 right, 0 wrong and 0 unexplained asks, answered 0 of 13 same-name recipes, and the Eyes stayed quiet. Four pair words read ADDITIVE. The wide brain became HELM's canonical-brain candidate across the switches, and on the owner's word of 2026-10-20 (\"YES TO WIDE BRAIN\") it is now HELM's canonical brain.", "VALIDATED for one sentence only (named corpora for real recipes; made-up worlds for the rest). Canonical by the owner's ruling, not by this result; the claim status did not change. Negatives kept: one conversation item wrong; 16 answerable recipes still asked."),
    "7.108": ("scored", "weak", "Wave 7 ran a fourth time (job c54) with every known instrument fault fixed and a fresh exam. This time nothing in the instrument failed: every data check and every must-hold check held, and HELM's own tests passed on the machine. The chat got 91 of 94 scorable real recipes right with 0 wrong, 44 of 64 dialogues right with 0 wrong, lost nothing to small talk and ran no shell command. It missed one mark: on two real recipes it asked without an accepted reason, and the loop driven directly asked the same, so the cause is the brain's reading of those recipe lines, not the chat window. By the frozen words that reads NO_GAIN. 0.02 USD.", "Nothing; a recorded mixed result with a clean instrument. The chat stays NOT LICENSED; what remains is the reader's reading of real recipe lines."),
    "7.106": ("scored", "null", "Wave 7 ran a third time (job c53) with the one asking fault fixed and a fresh exam. The chat got 99 of 101 scorable real recipes right with 0 wrong and asked without reason 0 times, 43 of 64 dialogues right with 0 wrong, lost nothing to small talk, and every must-hold check held. But HELM's own unit tests, which must pass on the machine before the run counts, failed one test there: a stored fingerprint of the loop's records that matches on the laptop and not on the machine. So the run reads INCONCLUSIVE, and its numbers are facts, not a result. 0.02 USD.", "Nothing; a recorded null. The chat stays NOT LICENSED; the fault is a test fingerprint tied to the machine, not HELM's answers."),
    "7.105": ("packet", "null", "Wave 7, round 3: the one real recipe job c52 asked about without an accepted reason was found by program. A temperature written after an ingredient line was read by the wide brain's reader as a fifth ingredient, so it waited for a batch where that \"ingredient\" ran out and asked. Fixed as one general rule (a temperature, a time or a head count is a note, never an ingredient), with a test that fails on the old code and passes on the fix. The chat wave packet v5 is frozen and fingerprinted on the fixed code with the used exam's ids excluded and fresh number ranges; not launched; waits for the owner's line CHAT WAVE 3 at 1 USD. Practice numbers equal v4's exactly.", "No claim from the packet itself; the fix is built, not yet validated on a fresh exam."),
    "7.104": ("scored", "weak", "Wave 7 ran again (job c52) on the repaired package with a fresh exam. Every must-hold check held this time, including the one that failed job c51, so that failure is confirmed as the reader's and not HELM's. The chat got 91 of 94 scorable real recipes right with 0 wrong, 44 of 64 dialogues right with 0 wrong, lost nothing to small talk and ran no shell command. It missed one mark: on one real recipe it asked without an accepted reason, and the loop driven directly asked the same, so the cause is in the brain, not the chat window. By the frozen words that reads NO_GAIN. 0.01 USD.", "Nothing; a recorded mixed result. The chat stays NOT LICENSED; the repaired instrument held on one real run."),
    "7.103": ("packet", "null", "The chat wave packet, v4: the scoring program and the recorder unit repaired (the unit now writes the sandbox row the same way the other 13 do, and the program names and refuses any unit that does not), the plan's empty folder list fixed and guarded, the used exam's ids excluded from both pools, fresh number ranges for the exam draw and a new owner line. HELM under test is byte-identical to v3. Frozen and fingerprinted, not launched; waits for the owner's line CHAT WAVE 2 at 1 USD.", "No claim from the packet itself."),
    "7.102": ("scored", "strong", "The same language exam a third time, with the one run-code defect behind the last failing mark fixed first: the untaught control brain asks questions nobody answers, and the run code had stamped those crossings as if they would be. One line changed, one test added that fails on the old code and passes on the new, the package frozen and fingerprinted before any part ran, the reader unchanged. 8 of 8 parts completed; the provenance mark now reads 106,400 of 106,400; every other number equals the second run's; all 14 must-pass checks held and the reader printed its four words. The first of the three runs with no failing mark.", "LICENSED for the reader's own sentence, as before, plus one bookkeeping fact: at every crossing the key the run code wrote agrees with what the crossing became. Nothing about continuity of thought as meaning, nothing about an RPA or the Atlas, no HELM claim, made-up worlds only."),
    "7.101": ("scored", "failed", "Wave 7, the chat wave, ran (job c51). HELM's chat window, typed to line by line with the wide brain on, got 96 of 128 real recipes right with 0 wrong, 44 of 64 dialogues right with 0 wrong, lost nothing to small talk, and never ran a shell command; every mark held. But one of the ten must-hold safety checks read false, so the run is a failure and the word is INCONCLUSIVE. That check failed because the reader itself demands a record from a helper unit that never writes it, a defect in the reader, not in HELM; a failed must-hold check is still a failure, and the rules forbid re-reading the same data with a repaired reader. The first of two machine tries died before any test on a plan-format rule; the retry ran clean. 0.02 USD.", "Nothing; a recorded failure. The chat stays NOT LICENSED."),
    "7.98": ("packet", "null", "Wave 7, the chat wave: HELM's chat window typed to line by line with the wide brain on, scored on three fresh exams the builder never sees. Sealed; ran as job c51 (see 7.101). On practice the chat as shipped would have failed; five defects were fixed in HELM first, and on the same practice draw every mark then held.", "No claim from the packet itself."),
    "7.95": ("scored", "null", "The ear's agreement-rule test ran (job c49). The real-sentence half (Part R) could not be exercised: the census found 7 stock-stating sentences the reader gives up on, against a floor of 24, so by the pre-registered rule the word is INCONCLUSIVE and nothing moves. The AI-written half (Part K) is reported only: with the agreement rule the ear read 79 of 128 singles right against the reader's 63 and 40 of 60 dialogue turns against 27, with 0 confident wrong proposals; the reader itself saved 3 wrong readings there.", "Nothing. The Part K line EARS_EARNED_KEEP is reported, never the word. Negatives kept: Part R not exercisable; reader v1.1 wrong 5 times on AI-written singles."),
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
    ("chat.html", "Talking to HELM"),
    ("architecture.html", "Architecture"),
    ("build.html", "The build, animated"),
    ("data.html", "Data lineage"),
    ("compute.html", "Compute and cost"),
    ("results.html", "Results scorecard"),
    ("model-card.html", "Model card"),
    ("safety.html", "Safety and honesty"),
    ("roadmap.html", "Roadmap"),
    ("device.html", "The HELM Cube"),
    ("glossary.html", "Glossary"),
    ("changelog.html", "Changelog"),
    ("run.html", "How to run HELM"),
    ("files.html", "Files and paths"),
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
.chat{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:14px 16px;margin:14px 0}
.chat .meta{font-size:12.5px;color:var(--ink-3);margin-bottom:8px;overflow-wrap:anywhere}
.chat .meta code{font-size:11.5px}
.msg{display:flex;flex-direction:column;max-width:88%;margin:6px 0}
.msg.you{align-self:flex-end;align-items:flex-end;margin-left:auto}
.msg.helm{align-self:flex-start;align-items:flex-start}
.msg .who{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-3);margin:0 6px 2px}
.msg .bubble{border-radius:14px;padding:8px 12px;font-size:14px;line-height:1.5;overflow-wrap:anywhere}
.msg.you .bubble{background:var(--accent-soft);border:1px solid var(--line);border-bottom-right-radius:4px}
.msg.helm .bubble{background:var(--surface-2);border:1px solid var(--line);border-bottom-left-radius:4px}
.msg.noise .bubble{border-style:dashed}
.msg .st{font:11px/1.4 var(--mono);color:var(--ink-3);margin:2px 6px 0}
.chat .thread{display:flex;flex-direction:column}
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
         description: str = "", words_open: bool = True) -> str:
    navs = "".join(
        f'<li><a href="{s}"{" aria-current=\"page\"" if s == slug else ""}>{esc(n)}</a></li>' for s, n in NAV)
    box = words_box(lede_html + body, words_open) if words else ""
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
    need(S, "7.95", "INCONCLUSIVE", "NOT_EXERCISED", "EARS_EARNED_KEEP", "79")
    need(S, "7.71", "NOT LICENSED", "nine runs")
    need(S, "7.65", "INCONCLUSIVE")
    need(S, "7.93", "WIDE_WAVE_NO_GAIN", "stays canonical", "97 of 101")
    need(S, "7.96", "WIDE_WAVE_EARNED_KEEP", "93 of 94", "owner's decision")
    need(S, "7.56", "YES TO WIDE BRAIN", "canonical brain is the WIDE recipe brain")
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
        pill("strong", "The licensed reference brain", "Beat the old transformer brain on a sealed made-up exam. Canonical until 2026-10-20; keeps its license.", ["LICENSED", "SYNTHETIC_ONLY"], "7.47"),
        pill("win", "The wide brain (candidate)", "Learned real cookbook recipes on a sealed test, 0 wrong answers.", ["VALIDATED (one sentence)", "NAMED_CORPORA_ONLY"], "7.89"),
        pill("win", "The pair wave re-run (wave 6 v3)", "With every part on: no harm where the marks look, 93 of 94 real recipes learned, 0 wrong, 0 unexplained asks. On the owner's word of 2026-10-20 the wide brain is now HELM's canonical brain.", ["PASS", "WIDE_WAVE_EARNED_KEEP", "NAMED_CORPORA_ONLY"], "7.96"),
        pill("weak", "The first pair wave (wave 6)", "With every part on: no harm and 0 wrong, but one unexplained ask (a reader defect, since fixed). No move from that run.", ["PASS", "WIDE_WAVE_NO_GAIN", "SYNTHETIC_ONLY"], "7.93"),
        pill("partial", "The English reader", "Safe on fresh real sentences after a fix; not yet useful.", ["ENGINEERED-NOT-VALIDATED", "S_SAFE_NOT_USEFUL"], "7.87"),
        pill("failed", "The reader before the fix", "Wrote 8 wrong facts on 128 real sentences.", ["S_UNSAFE_ON_REAL"], "7.81"),
        pill("partial", "The Unity Eye", "Found planted faults and paired jobs well, on made-up worlds.", ["EYE_SCAN_EARNED_KEEP", "EYE_PAIRING_EARNED_KEEP", "ENGINEERED-NOT-VALIDATED"], "7.78"),
        pill("failed", "The transformer ear", "No gain on real sentences; too many confident wrong guesses on a second exam.", ["EARS_NO_GAIN", "EARS_HARMED", "FAILURE"], "7.90"),
        pill("null", "The ear under an agreement rule", "Its real-sentence half could not be run (7 usable sentences, floor 24), so the word is INCONCLUSIVE. On AI-written kitchen turns only, reported: 79 vs 63 right, 0 confident wrong.", ["INSTRUMENT_ERROR", "INCONCLUSIVE", "ENGINEERED-NOT-VALIDATED"], "7.95"),
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
(9,585,566 parameters) exists only as an optional "ear" that may propose a reading; it never writes ({slink('7.82')}). A second brain, the {T('wide brain')}, reads any ingredient name; after two {T('sealed')} tests and the {T('pair wave')} it is HELM's
canonical-brain candidate across the switches ({slink('7.96')}), and on the owner's word of 2026-10-20 it is now HELM's canonical brain ({slink('7.56')}). Since 2026-10-20 the live loop and the chat run it by default; setting <code>HELM_WIDE_BRAIN=0</code> runs the licensed reference brain alone.</p>
</div>

<h2>Today's status</h2>
<p>Each card shows a color, the exact words from the record, and the {T('claim ceiling')}. Tests run in numbered {T('wave', 'waves')}; the latest, the {T('pair wave')}, read WIDE_WAVE_NO_GAIN, so the wide brain stays a candidate and the licensed brain stays HELM's main brain. Most results come from {T('sealed')} exams.
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
<div class="card"><a href="chat.html">Talking to HELM: the chat test</a><br><span class="muted small">Latest scored run c56 (package v9): PASS / CHAT_WAVE_HARMED, 93 real recipes right, 0 wrong, 1 ask without an accepted reason, 1 wrong stored lesson, 64 of 64 dialogues right, 0 lost to small talk, 0.02 USD. Before it, c55: 93 right, 0 wrong, 0 unexplained asks, 62 of 64 dialogues right and 2 wrong, also HARMED. Scores for every run, and real exchanges word for word. Claim status NOT LICENSED.</span></div>
</div>

<h2>Where to go next</h2>
<div class="grid">
<div class="card"><a href="thinking.html">How HELM thinks</a><br><span class="muted small">Recipes, asking, receipts and the Eye, with the precise definitions.</span></div>
<div class="card"><a href="files.html#start">Next agent: start here</a><br><span class="muted small">Every file and folder with its full path, and the rules to read first. Then read the owner's <a href="roadmap.html#intent">statement of intent for whoever comes after</a> (2026-10-21): the transformer mouth trained on the 40 elements; intended, nothing built.</span></div>
<div class="card"><a href="build.html">The build, animated</a><br><span class="muted small">One turn as wired today, and the intended next wiring.</span></div>
<div class="card"><a href="architecture.html">Architecture</a><br><span class="muted small">Every part, its parameter count, and what HELM is not.</span></div>
<div class="card"><a href="results.html">Results scorecard</a><br><span class="muted small">Every result, negatives included.</span></div>
<div class="card"><a href="roadmap.html">Roadmap</a><br><span class="muted small">What is real, what is planned, and "can I chat with it?"</span></div>
<div class="card"><a href="device.html">The HELM Cube (concept)</a><br><span class="muted small">HELM's intended final home: a small black cube with no buttons. Design only.</span></div>
<div class="card"><a href="demo.html">Try the demo page</a><br><span class="muted small">A recorded HELM session you can open without a server.</span></div>
<div class="card"><a href="model-card.html#not-here">What this hub does not have, and why</a><br><span class="muted small">The usual chatbot sections that do not apply to HELM.</span></div>
</div>
"""
    return page("index.html", "HELM Hub", "HELM, in one screen", lede, body, [
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.24, §7.47, §7.56, §7.65, §7.71, §7.77, §7.78, §7.81, §7.82, §7.87, §7.89, §7.90 (section counts computed from §7.24 onward)",
        f"`{rel(LEDGER)}` (totals only)",
        "Owner's color scale: `docs/reference/CAS_HELM_DICTIONARY.md`, 'Color marks used in owner reports'",
    ], description="What HELM is, in one screen, with today's status.")


CHAT_SAMPLES = HUB / "chat_samples_c53.json"
C54_RESULT = CODEX / "2026-10-20" / "r1_wave7" / "run_c54_r1w7v6_20261021" / "RUN_RESULT_R1W7V6_C54.md"

# HELM's internal status words seen in the c53 transcripts, in plain English (the legend on the chat page)
CHAT_STATUS = {
    "WITNESS_ADMITTED": "the lesson was accepted and one amount was saved",
    "STOCK_RECORDED": "what you have was written down",
    "INVENTORY_RECORDED": "a stock list was written down",
    "SUCCESS_EVALUATED": "HELM worked out an answer",
    "UNDETERMINED_CLARIFY": "HELM could not tell, said so, and asked; nothing was saved",
    "BRAIN_UNDETERMINED": "the brain itself could not tell; nothing was saved",
    "CLARIFY_ENGLISH_UNKNOWN_PRODUCT": "HELM has no recipe by that name yet; nothing was saved",
    "CLARIFY_ENGLISH_UNKNOWN_INGREDIENT": "a word in that line was not read as an ingredient; nothing was saved",
    "CLARIFY_ENGLISH_NO_INGREDIENT_NAMED": "an amount came with no ingredient name; nothing was saved",
    "CLARIFY_ENGLISH_NO_STOCK_FRAME": "the line did not read as a stock statement; nothing was saved",
    "TEACH_REFUSED_REFUSED_RAN_OUT_NOT_IN_BATCH": "the thing said to run out was not in that batch, so the lesson was refused",
    "none": "the chat window answered by itself (small talk or a closing remark); the brain was not called and nothing was saved",
}


def chat_samples() -> dict:
    t = read(CHAT_SAMPLES)
    try:
        return json.loads(t) if t else {}
    except ValueError:
        return {}


def chat_block(tr: dict, label: str, plain: str = "") -> str:
    """One transcript as a two-voice chat: You on the right, HELM on the left, HELM's status word small under each reply."""
    msgs = []
    for t in tr["turns"]:
        noise = t.get("kind") == "noise"
        who = "You (small talk)" if noise else "You"
        ncls = " noise" if noise else ""
        st = t.get("status") or "none"
        msgs.append(f'<div class="msg you{ncls}"><span class="who">{esc(who)}</span><div class="bubble">{esc(t["you"])}</div></div>')
        msgs.append(f'<div class="msg helm{ncls}"><span class="who">HELM</span><div class="bubble">{esc(t["helm"])}</div>'
                    f'<span class="st">inside: {esc(st)}</span></div>')
    arm = {"CHAT_ON": "wide brain on", "CHAT_OFF": "wide brain off (licensed reference brain alone)", "NOISE_CHAT_ON": "wide brain on, small talk mixed in"}.get(tr.get("arm"), tr.get("arm", ""))
    fam = tr.get("family", "")
    famtxt = "" if fam == "REAL" else f'; family <code>{esc(fam)}</code>'
    return (f'<div class="chat"><div class="meta"><strong>{esc(label)}</strong> &middot; item <code>{esc(tr["id"])}</code>{famtxt} &middot; '
            f'job c53, spent exam &middot; {esc(arm)} &middot; scored turn read <code>{esc(tr.get("scored_status", ""))}</code></div>'
            f'{("<p class=small>" + plain + "</p>") if plain else ""}<div class="thread">{"".join(msgs)}</div></div>')


def p_chat(S: dict) -> str:
    # Living checks: every number on this page must still be in the cited record
    need(S, "7.98", "128 real recipes", "64 dialogues", "the same 64 with small talk", "five chat defects", "NOT LAUNCHED")
    need(S, "7.101", "FAILURE", "INCONCLUSIVE", "HG5", "95 of 97", "RIGHT 96 / WRONG 0",
         "CONV 64: 44 / 0", "0.02 USD", "K4 0 unexplained asks")
    need(S, "7.104", "PASS", "CHAT_WAVE_NO_GAIN", "91 of 94", "1 unexplained ask", "CONV 64: 44 / 0", "0.01 USD", "a temperature note after an ingredient line")
    need(S, "7.106", "INSTRUMENT_ERROR", "INCONCLUSIVE", "99 of 101 real recipes right, 0 wrong", "100 of 101", "K4 0 unexplained", "CONV 64: 43 / 0", "0.02 USD",
         "21 of 64 dialogues UNDETERMINED (S1 6, S2 6, S7 4, S6 2, R4 2, R3 1)", "fails only on the Ubuntu / Python 3.12 host")
    need(S, "7.98", "Or chicken bouillon")
    need(S, "7.116", "CHAT_WAVE_HARMED", "62 right / 2 wrong / 0 undetermined")
    need(S, "7.119", "CHAT_WAVE_HARMED", "64 right / 0 wrong / 0 undetermined", "Builder's error")
    secs = S["secs"]
    c54_in_spec = "7.108" in secs
    if c54_in_spec:
        need(S, "7.108", "CHAT_WAVE_NO_GAIN", "PASS", "91 of 94")
    c54_file = read(C54_RESULT)
    c54_src = "`" + str(C54_RESULT) + "`" + (" and spec sheet §7.108" if c54_in_spec else " (spec sheet §7.108 is on PR #431, not yet on this branch; the next rebuild after it lands checks the row against it)")
    c54_note = "" if c54_file else " That file was not available on this machine when the page was built; the row carries the coordinator's verified facts of 2026-10-21."

    D = chat_samples()
    SM = D.get("samples", {})
    CN = D.get("counts", {})
    n_tr = sum(len(v) for v in SM.values())

    def row(color, job, pkg, verdict, word, rw, learned, asks, conv, noise, cost, wrong, src):
        words = f'<span class="word">{esc(verdict)}</span> <span class="word">{esc(word)}</span>'
        return (f'<tr><td>{dot(color)}<br><strong>{esc(job)}</strong></td><td>{esc(pkg)}</td><td>{words}</td><td>{esc(rw)}</td><td>{esc(learned)}</td>'
                f'<td>{esc(asks)}</td><td>{esc(conv)}</td><td>{esc(noise)}</td><td>{esc(cost)}</td><td>{wrong}</td><td class="small">{src}</td></tr>')

    rows = "".join([
        row("null", "c51", "v3", "FAILURE", "INCONCLUSIVE", "96 right / 0 wrong", "95 of 97 (bar 88)", "0", "44 right / 0 wrong", "0", "0.02 USD",
            "The scoring program demanded a record from a helper unit that never writes one. A defect in the reader, not in HELM; but a failed must-hold check is a failure, so the marks count as facts only.", slink("7.101")),
        row("weak", "c52", "v4", "PASS", "CHAT_WAVE_NO_GAIN", "91 right / 0 wrong", "91 of 94 (bar 85)", "1", "44 right / 0 wrong", "0", "0.01 USD",
            "Nothing in the instrument. The one miss was in the brain: a temperature note written after an ingredient line was read as a fifth ingredient, so HELM asked once without a reason. Found afterward and fixed as one general rule.", slink("7.104") + ", " + slink("7.105")),
        row("null", "c53", "v5", "INSTRUMENT_ERROR", "INCONCLUSIVE", "99 right / 0 wrong", "100 of 101 (bar 91)", "0", "43 right / 0 wrong", "0", "0.02 USD",
            "One of HELM's own unit tests pinned a fingerprint that matches on the laptop and not on the cloud machine, so the test failed there. A test tied to one machine, not HELM's answers; fixed afterward with a machine-neutral pin. Every mark held, including 0 unexplained asks.", slink("7.106")),
        row("weak", "c54", "v6", "PASS", "CHAT_WAVE_NO_GAIN", "91 right / 0 wrong", "91 of 94 (bar 85)", "2", "44 right / 0 wrong", "0", "0.02 USD",
            "Nothing in the instrument this time: every instrument row (8 of 8) and every must-hold check (10 of 10) held, and HELM's test suite ran clean on the cloud machine (245 tests OK), so the pin fix held. Two real recipe lines of a shape the wide reader does not read yet made HELM ask without an accepted reason; the loop driven directly made the same two asks, so the cause is in the brain. By the frozen words that reads NO_GAIN." + esc(c54_note), md(c54_src)),
        row("failed", "c55", "v8", "PASS", "CHAT_WAVE_HARMED", "93 right / 0 wrong", "92 of 94 (bar 85)", "0", "62 right / 2 wrong", "0", "0.02 USD",
            "Every instrument row and must-hold check held, and the asking mark held for the first time since c51: no ask without an accepted reason. The dialogues went from 44 right and 20 unscored to 62 right, but 2 were answered where HELM should have applied a stated fact or asked, because the sentence named the ingredient by a word the brain had not learned; and one lesson stored a wrong amount. A wrong answer fails the safety mark, so by the frozen words that reads HARMED. The reader fix that followed is " + slink("7.117") + ".", slink("7.116")),
        row("failed", "c56", "v9", "PASS", "CHAT_WAVE_HARMED", "93 right / 0 wrong", "91 of 91 (bar 82)", "1", "64 right / 0 wrong", "0", "0.02 USD",
            "Every instrument row and must-hold check held, and every dialogue was right (64 of 64), the copy with small talk the same. Two marks failed on two real recipes, the same way with no chat layer: a book line ending in a loose \"or\" made the reader tie a \"ran out\" sentence to the next line, so one lesson stored a wrong amount; and a line holding two amounts left one ingredient untaught, so HELM asked honestly, which the frozen rule counts as unexplained. The written rule meant to leave that recipe's question unscored was never built to do so: the builder's error, left for the owner to decide. By the frozen words that reads HARMED.", slink("7.119")),
    ])

    legend = "".join(f'<div class="w"><dt><code>{esc(k)}</code></dt><dd class="small">{esc(v)}</dd></div>' for k, v in CHAT_STATUS.items())

    def section(key, title, intro, labels):
        items = SM.get(key, [])
        if not items:
            return f"<h3>{esc(title)}</h3><p class=\"muted\">No transcripts in the samples file for this part.</p>"
        out = [f"<h3>{esc(title)}</h3><p>{intro}</p>"]
        for i, tr in enumerate(items):
            lab, plain = labels[i] if i < len(labels) else (f"{title} {i + 1}", "")
            out.append(chat_block(tr, lab, plain))
        return "".join(out)

    real_right = section("real_right", "Three real cookbook recipes, taught by typing, then answered",
        "Each one goes the same way: a lesson per ingredient (what was made, from what, and what ran out first), then a line about what you have, then the question. HELM had never seen any of these recipes. Every reply below is exactly what it said.",
        [("Real recipe 1 (juice)", ""), ("Real recipe 2 (dumplings)", "Note the untidy source text (stray full stops, 'heaping tablespoonfuls'); HELM still reads the amounts and names."),
         ("Real recipe 3 (sherbet)", "")])
    real_off = section("real_off_same", "The same first recipe with the wide brain switched off",
        "This is the comparison arm. The licensed reference brain alone knows only eight ingredient names and four products, so it cannot take these lessons; it asks on every line and saves nothing. On this exam it answered 0 real recipes. That is why the wide brain is on by default.",
        [("Real recipe 1 again, wide brain off", "")])
    real_ask = section("real_ask", "Two real recipes where HELM asked instead of answering",
        "On job c53 every ask on a real recipe had a reason the frozen reader accepts. HELM says what it cannot do and saves nothing; it never guesses.",
        [("Ask 1: no recipe by that name", "Plainly: the recipe is for 'veal', and HELM's ask wrongly lists only the old brain's four products. The wide brain could have learned it; the reader did not pass the line through because the first ingredient line read as the product name. The wording of the ask is a known rough edge."),
         ("Ask 2: one lesson refused, so one amount missing", "Plainly: the first lesson said the batch 'ran out of of' (a typo in the cookbook line), so HELM refused that lesson. With one ingredient's amount still unknown it could not answer and said exactly which batch it still needs.")])
    conv_right = section("conv_right", "Three made-up kitchen dialogues answered",
        "These are built dialogues from the exam generator: lessons, a closing remark, a stock line, a question, sometimes phrased differently. The closing remarks ('Okay, that's all of it for now') are answered by the chat window itself, without the brain; its stock phrase there is a known rough edge.",
        [("Dialogue 1: stock, then ask", ""), ("Dialogue 2: a different question form", "The question is 'How much eggs do we have the makings of?', not the plain form; HELM still answers."),
         ("Dialogue 3: a new session", "One turn in this item was recorded with no text (the exam's session break); HELM gave no reply there, which is right.")])
    conv_open = section("conv_open", "Three dialogues HELM could not settle (the known gap)",
        "In these, the stock line carries a feeling or purpose clause ('but I'm new to using rice water', 'and the eggs is getting old') or is paraphrased in the past tense. The wide reader does not read those shapes yet, so the stock is not saved, and HELM then says plainly that it does not know how much is on hand and asks. It never guesses and never saves a wrong fact. Reading those clauses is the next job. Note also that the 'ingredients I know' list in these asks is the old brain's list of eight, a wording defect on the record.",
        [("Gap 1: a feeling clause on the stock line", ""), ("Gap 2: a feeling clause on the stock line", ""), ("Gap 3: a clause that is not an ingredient", "")])
    noise_right = section("noise_right", "Two dialogues with small talk mixed in",
        "Two small-talk lines are dropped into each dialogue. HELM must answer them as a person would, keep the kitchen facts, and still get the question right. The dashed bubbles are the small talk. One reply below ('Glad you're feeling great today' to 'I live in Oakland') is off; it cost nothing in the kitchen but is on the record.",
        [("Small talk 1", ""), ("Small talk 2", "")])

    gap_list = "S1 6, S2 6, S7 4, S6 2, R4 2, R3 1 by the reader's count"
    lede = (f"HELM has a chat window. You type to it line by line in everyday English; it learns {T('recipe', 'recipes')} it has never seen, "
            f"writes down what you have, works out how much you can make, and asks when it cannot tell. This page shows how that was tested, "
            f"the exact scores, and real exchanges, word for word, from a {T('spent exam')}.")
    body = f"""
<div class="card">
<h2 style="margin-top:4px">What the chat test is, in one screen</h2>
<p>The test is called the {T('chat wave', also=('wave',))}. A program types to HELM's chat window exactly as a person would, one line at a time,
with the {T('wide brain')} on. HELM must do four things from typing alone: learn a recipe it has never seen (one lesson per ingredient:
"we made 1 juice from 5 lbs grapes and 2 quarts water and ran out of grapes"), record what you have ("we have 7 1/2 lbs grapes and 1/3 quart water"),
answer how much you can make ("1/3 juice; water runs out first"), and ask instead of guessing when something is missing.</p>
<p>Each run sits three fresh exams: <strong>128 real cookbook recipes</strong> from old public cookbooks, <strong>64 made-up kitchen dialogues</strong>
built by a generator in thirteen shapes (30 of the 64 are built so that the right answer is to ask), and <strong>the same 64 with small talk mixed in</strong>
(two unrelated lines dropped into each one, 128 in all). A {T('custodian')} draws every exam blind and seals it; the builder never sees an exam before the run;
nothing in HELM is tuned to it. After a run the exam is spent: its item ids go on the exclusion list, which is why its lines can be shown here.</p>
<p>A {T('frozen reader')}, sealed before the run, alone writes the verdict and the {T('status word')}. It first checks the instrument (did every part run, did HELM's own tests pass
on the cloud machine) and ten must-hold checks (a {T('hard gate')} each: for example, HELM touched no file outside its sandbox and ran no shell command). Only then does it count the marks:
recipes learned against a bar, 0 wrong answers, asks only with an accepted reason, nothing lost against the loop driven directly, plain replies, nothing lost to small talk.
Four runs so far cost 0.07 USD in all.</p>
</div>

<h2 id="scores">The scores, run by run</h2>
<p>Exact words and numbers from the record. "Fully learned" counts recipes whose every ingredient amount was learned, against the frozen bar for that draw.
"Asks without an accepted reason" is the honesty mark: HELM may ask, but only for a reason the reader accepts. The colour dot is the owner's reading aid
(grey for INCONCLUSIVE, orange for NO_GAIN); it is not a {T('claim status')}. <strong>The chat's claim status is NOT LICENSED</strong> ({T('LICENSED')}):
no reader word has been earned yet, so "the chat works" may not be said. The numbers are facts on the record.</p>
<div class="tablewrap"><table>
<thead><tr><th>Run</th><th>Package</th><th>Verdict and status word</th><th>Real recipes right / wrong</th><th>Fully learned (bar)</th><th>Asks without an accepted reason</th>
<th>Dialogues right / wrong</th><th>Lost to small talk</th><th>Cost</th><th>What went wrong in the instrument</th><th>Record</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="small muted">Four draws, four words; facts, not a trend. The licensed reference brain alone (wide brain off) answered 0 real recipes on every draw.
The one word that would license the chat is CHAT_WAVE_EARNED_KEEP, which needs every mark true on a clean instrument; no run has it yet.</p>

<h2 id="exchanges">Read real exchanges</h2>
<p>Every transcript below is from job c53 (package v5, exam X7v5, now spent). "You" is what the test typed; "HELM" is the reply, word for word.
Under each reply, in small type, is HELM's own internal status for that turn, so you can see the machinery agreeing with the words. {n_tr} transcripts.</p>
<details class="words" open><summary>The status words under the replies, in plain English</summary><dl>{legend}</dl></details>
{real_right}
{real_off}
{real_ask}
{conv_right}
{conv_open}
{noise_right}

<h2 id="cannot">What it cannot do yet</h2>
<ul class="tight">
<li><strong>Stock lines with a feeling or purpose clause, and past-tense paraphrases.</strong> On c53, 21 of the 64 dialogues were left {T('UNDETERMINED')} ({gap_list}; the dialogue shapes S1 to S7 are the ones with a stated purpose, feeling or second meaning). By HELM's own status words {esc(str(CN.get('conv_items', 64) - CN.get('conv_answered_by_status', 0)))} of 64 items ended in an ask, but 30 of the 64 are built so that asking is the right answer, and only the reader, with the key, tells those apart. HELM asks instead of guessing, which is the safe side; reading those clauses is the next job. Since the reader-gap build ({slink('7.111')} to {slink('7.117')}), c55 read 62 of the 64 dialogues right with 2 wrong, and c56 read all 64 right: facts about two draws, not a license.</li>
<li><strong>The wording of some asks names the wrong brain.</strong> "I can work with flour, water, sugar, butter, milk, eggs, yeast, and salt" is the licensed brain's list of eight; with the wide brain on it is misleading. A wording defect, on the record.</li>
<li><strong>An "X or Y" ingredient is spoken oddly.</strong> On the practice draw of the first packet, a line like "chicken stock or chicken bouillon" made HELM say "Or chicken bouillon runs out first": right by the key, odd to a person ({slink('7.98')}).</li>
<li><strong>A few real recipe lines of a shape the wide reader does not read.</strong> One unexplained ask on c52 (a temperature note, since fixed), two on c54, and one on c56 (a line with two amounts, one ingredient never taught). On c56 a line ending in a loose "or" also made the reader store one wrong amount ({slink('7.119')}). Each one costs the run its word.</li>
<li><strong>The licensed reader alone answers 0 real recipes.</strong> Without the wide brain, HELM's chat cannot learn a real cookbook recipe at all.</li>
<li><strong>Nothing is licensed.</strong> The chat has no reader word yet. Nothing on this page may be read as "HELM's chat works".</li>
</ul>
"""
    return page("chat.html", "Talking to HELM", "Talking to HELM: the chat test, its scores, and real exchanges", lede, body, [
        f"Transcripts: `helm_hub/chat_samples_c53.json`, written by `helm_hub/make_chat_samples.py` from the job c53 unit files "
        f"`W7_X7_REAL_CHAT_ON.json`, `W7_X7_REAL_CHAT_OFF.json`, `W7_X7_CONV_CHAT_ON.json`, `W7_X7_NOISE_CHAT_ON.json`, `W7_X7_REAL_LOOP_ON.json` under `{D.get('units_dir', 'the c53 deliverable')}`",
        "Readable copy of more exchanges: `docs/working/r1_wave7/CHAT_SAMPLES_C53_20261021.md`",
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.98 (the packet), §7.101 (c51), §7.103 (v4), §7.104 (c52), §7.105 (round 3), §7.106 (c53)",
        f"c54: {c54_src}",
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.116 (c55), §7.117 (reader v7.2), §7.118 (v9), §7.119 (c56)",
    ], words=True, words_open=False, description="HELM's chat test: what it is, the exact scores of every run, and real exchanges word for word.")


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
<li>The {T('Unity Eye')} watches, reports and {T('whisper', 'whispers')}, and never writes. An acting mode that may put back what the user's own words re-derive is built behind the switch <code>HELM_EYE_ACT</code>, OFF by default and not licensed ({slink('7.122')}).</li>
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
Every saved fact leaves a {T('receipt')}; every sentence it says must pass the {T('round trip')}. Scored tests use {T('sealed')} exams and run in numbered {T('wave', 'waves')}.
The one place chance is allowed uses saved {T('seed', 'seeds')}.</p>
<p>A {T('parameter')} is an adjustable number a model learns. Big AI chat assistants have billions. HELM's licensed brain has dozens.
Each part below sits behind a switch, so tests can turn one part off and see what is lost. A part that loses something when switched off earns the
{T('status word')} {T('EARNED_KEEP')}. Tests run on {T('synthetic world', 'synthetic worlds')} unless they say otherwise.</p>
<div class="tablewrap"><table><thead><tr><th>Part</th><th>What it does, plainly</th><th>Learned parameters (exact, from the record)</th><th>Standing</th></tr></thead><tbody>
<tr><td><strong>Licensed {T('recipe brain')}</strong><br><code>helm_brain_canonical.py</code></td><td>Holds recipes; answers by exact yield; names the limiting ingredient. The way recipes combine is programmed; only the requirement amounts are learned.</td>
<td>Run log: "RB-B 32 learned slots" ({slink('7.47')}). The first recipe brain had "68 learned values (requirements 32, ceilings 32, bindings 4)" ({slink('7.24')}). For comparison, the {T('GB3')} {T('transformer')} it replaced: 97; widened: 385.</td>
<td>{T('LICENSED')}, one sentence, {T('SYNTHETIC_ONLY')} ({slink('7.56')}). Wired into HELM's live loop by fixes C and D on 2026-10-18.</td></tr>
<tr><td><strong>{T('wide brain', 'Wide recipe brain')}</strong> (RB-W1, reader v5)<br><code>helm_brain_wide.py</code></td><td>The same learning and answering rules, for real recipes: open ingredient names, exact fractions, up to 10 ingredients, 20 kitchen units.</td>
<td>One requirement coefficient per (recipe, ingredient), learned from one witnessed batch each. Survey estimate, not a measurement: "49,493 coefficients for 9,495 recipes". 9 unit factors are programmed, not learned ({slink('7.83')}).</td>
<td>Canonical-brain candidate, {T('VALIDATED')} for one sentence, {T('NAMED_CORPORA_ONLY')} ({slink('7.89')}). With every part on it first read WIDE_WAVE_NO_GAIN ({slink('7.93')}); after the reader fix the re-run read WIDE_WAVE_EARNED_KEEP ({slink('7.96')}). <strong>HELM's canonical brain since 2026-10-20</strong>, on the owner's word ({slink('7.56')}); on by default in the live loop and the chat since 2026-10-20 (<code>HELM_WIDE_BRAIN=0</code> runs the licensed reference brain alone).</td></tr>
<tr><td><strong>{T('RPM Gate')}</strong></td><td>Lets a step go ahead, sends it to repair, or refuses; lets the brain answer {T('UNDETERMINED')}.</td><td>0 (a written rule)</td><td>EARNED_KEEP in waves 1, 2 and 3. Switched off in wave 1, wrong answers rose from 32 to 768 ({slink('7.47')}).</td></tr>
<tr><td><strong>{T('lacuna', 'Lacuna')} cadence</strong></td><td>Keeps track of what HELM could know but was never taught, and when to look again.</td><td>0 (a written rule)</td><td>EARNED_KEEP in waves 2 and 3 ({slink('7.64')}, {slink('7.69')}).</td></tr>
<tr><td><strong>{T('restart fallback', 'Restart fallback')}</strong></td><td>The one place chance is allowed: a few saved random restarts, and the checker decides.</td><td>0 (seeds are saved, not learned)</td><td>EARNED_KEEP in waves 2 and 3.</td></tr>
<tr><td><strong>English reader</strong><br><code>helm_english_in.py</code></td><td>Restates plain kitchen sentences in the checked form, or asks.</td><td>0 (a written program with word lists)</td><td>{T('ENGINEERED-NOT-VALIDATED')}. On fresh real sentences: 0 wrong facts after the fix, but not yet useful ({slink('7.87')}).</td></tr>
<tr><td><strong>Voice</strong><br><code>helm_voice.py</code></td><td>Turns the brain's receipt into one to three plain sentences, then reads its own numbers back.</td><td>0</td><td>EARNED_KEEP; works together with the reader (SYNERGY) ({slink('7.72')}).</td></tr>
<tr><td><strong>{T('CCE')} skin</strong></td><td>The strict English form that converts to CAS and back exactly.</td><td>0 (deterministic parser and renderer)</td><td>NEUTRAL by construction: switching it off changes no answer.</td></tr>
<tr><td><strong>{T('cube store', 'Cube store')}</strong></td><td>Where facts live, built on the Cube Node Schema v0.1: every thing is a cube with six sides (what it is, its context, an analogy or metaphor, a mapping, its parts, how the parts fit), and an edge between two cubes records what the two have in common. Three questions run over it: what does it hold, what do two things share, how are two things related. An unknown side is reported unknown, never filled. Taught conversation facts land here as cubes and edges only behind the OFF-by-default switch HELM_CUBE_OSC ({slink('7.125')}).</td><td>0</td><td>EARNED_KEEP in wave 3.</td></tr>
<tr><td><strong>{T('triad', 'Triad')}</strong><br><code>helm_triad.py</code></td><td>Purpose, Wisdom and Power on each ingredient; the weakest face sets how much counts.</td><td>"0 learned parameters"; stored values ceiling 28 ({slink('7.62')})</td><td>Built, default off; EARNED_KEEP in wave 3.</td></tr>
<tr><td><strong>{T('cascade', 'Cascade')}</strong></td><td>Goes down into sub-problems. The owner's decoupling stop decides when to stop; a fuse at depth 12 is the hard limit.</td><td>0</td><td>DECOUPLING_EARNED: 203 descents against 609 for the old fixed cap ({slink('7.69')}).</td></tr>
<tr><td><strong>{T('Unity Eye')}: scan</strong></td><td>Read-only self-check of memory and records; holds back an answer that would use a damaged record.</td><td>0</td><td>EYE_SCAN_EARNED_KEEP, built not validated ({slink('7.77')}).</td></tr>
<tr><td><strong>Unity Eye: pairing</strong></td><td>Counts which mental job works for which motive, and {T('whisper', 'whispers')} the best pair.</td><td>A 7 x 7 table of counts of checked tries; counts, not trained weights</td><td>EYE_PAIRING_EARNED_KEEP, built not validated ({slink('7.78')}).</td></tr>
<tr><td><strong>{T('drive loop', 'Drive loop')}</strong></td><td>Where idle attention goes among the seven {T('Drive', 'Drives')}; paused during conversation.</td><td>0</td><td>NEUTRAL alone in wave 3; with the Eye's pairing, earned its keep in wave 5.</td></tr>
<tr><td><strong>{T('faculty', 'Faculties')}</strong></td><td>Mental jobs such as asking, verifying, pondering, curiosity.</td><td>0</td><td>No faculty word earned on the brain itself ({slink('7.65')}).</td></tr>
<tr><td><strong>Transformer ear</strong> ({T('CTT', 'CTT-1')})</td><td>A from-scratch translator, called only when the reader would ask. It may point at your own words and numbers; HELM's own checks decide.</td>
<td>9,585,566 (width 256, 4 + 4 layers); twin 2,482,718; vocabulary 8,349 = 8 specials + 341 CAS tokens + 8,000 English word pieces learned from scratch ({slink('7.82')})</td>
<td>ENGINEERED-NOT-VALIDATED. EARS_NO_GAIN; second exam FAILURE, EARS_HARMED ({slink('7.90')}).</td></tr>
</tbody></table></div>

<p>See every part move through one conversation turn on <a href="build.html">The build, animated</a>.</p>

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
<li><strong>Exam builders</strong> for each test {T('wave')}: fresh worlds X0 to X5, each built for one run and then spent ({slink('7.44')}, {slink('7.77')}, {slink('7.78')}).</li>
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
<dt>Canonical brain</dt><dd>The wide recipe brain RB-W1 (reader v5), on the owner's word of 2026-10-20 after {slink('7.89')} and {slink('7.96')}; the wave-1 brain keeps its license as the reference brain ({slink('7.56')}).</dd>
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
Each saved fact leaves a receipt carrying a {T('hash')}.</p></div>
<div class="card"><h3>The Eye never writes</h3><p>The {T('Unity Eye')} may report a problem and {T('whisper', 'whisper')} a suggestion.
HELM may ignore the whisper. In {T('wave', 'waves')} 4 and 5 the Eye made 0 writes ({slink('7.77')}, {slink('7.78')}).
An acting mode is now built behind the switch <code>HELM_EYE_ACT</code>, OFF by default and not {T('LICENSED', 'licensed')}: when it is on, the Eye
may put back only what the user's own words re-derive, through HELM's own routines, each change recorded with its
reason; it never adds a fact or a number, and where nothing supports a value HELM asks ({slink('7.122')}).</p></div>
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
for 2026-10-18 to 2026-10-21 (headings only; dates are Pacific). They name parts of {T('CAS')}, the {T('SDG')}, the {T('CTT')}, the {T('pair wave')}, the {T('wide brain')} and the idle {T('drive loop')}; a confirmation quotes a package's {T('hash')}.</p>
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
        ("Kitchen (the test world)", "strong", "Real today, inside limits. The licensed brain is LICENSED on made-up worlds; the wide brain is a candidate, VALIDATED for one sentence on real cookbook recipes; the pair wave first read WIDE_WAVE_NO_GAIN (one unexplained ask, a reader defect since fixed) and its re-run read WIDE_WAVE_EARNED_KEEP, so the wide brain became the candidate across the switches, and on the owner's word of 2026-10-20 it is HELM's canonical brain; the wave-1 brain keeps its license as the reference brain. The licensed brain's fixed shapes fit 1 of 13,686 real recipes, which is why the wide brain exists.", "§7.56, §7.83, §7.89, §7.91, §7.93, §7.96"),
        ("Software work", "null", "Authored only. A tool-planning file exists with no recorded output; in the UI, tools are switched off by default.", "Roadmap §2.5 and §2.7; status correction row v0.6"),
        ("Everyday planning", "null", "Partly backed. A prerequisite planner orders steps and refuses loops; one worked plan is recorded; not scored on a sealed exam.", "§7.48; status correction row v0.7"),
        ("Research governance", "rule", "In force as a way of working (custodians, sealed exams, frozen readers, owner sign lines), not as something HELM does by itself.", "§7.55, §9.9 of the spec sheet"),
        ("Safety as a recipe", "partial", "The pieces exist and earned their keep on made-up worlds (the gate, the Eye's scan, refusal). Treating safety itself as a recipe HELM reasons about is not built.", "§7.64, §7.69, §7.77"),
        ("Physical systems (simulated flight, drones, robots)", "null", "Not built. Plans only.", "Roadmap §2.8, §2.9; status correction rows v1.1 to v2.0"),
        ("Science", "null", "Not built. No test exists.", "Roadmap §2.4 (frontier plans)"),
        ("Outputs with checkable receipts", "partial", "Every write in the scored waves is receipted and the receipts held as hard gates; a product that hands receipts to outside users is not built.", "§7.47, §7.64"),
    ]
    drows = "".join(f"<tr><td><strong>{esc(n)}</strong></td><td>{dot(c)}</td><td>{md(t)}</td><td>{md(r)}</td></tr>" for n, c, t, r in domains)
    need(S, "7.110", "A-TALK-1", "LLM_WRITTEN_ONLY", "TALK TRAIN at 3 USD", "TALK EXAM at 1 USD", "`C0`–`C9`", "NOT A PRESENT CAPABILITY")
    need(S, "7.111", "ENGINEERED-NOT-VALIDATED", "26 new tests")
    need(S, "7.49", "ENGINEERED-NOT-VALIDATED")
    need(S, "7.38", "INCONCLUSIVE", "NOT LICENSED")
    need(S, "7.31", "round trip 576/576")
    need(S, "7.48", "cube store", "ENGINEERED-NOT-VALIDATED")
    need(S, "7.77", "EYE_SCAN_EARNED_KEEP", "0 Eye writes")
    need(S, "7.78", "EYE_PAIRING_EARNED_KEEP", "0 Eye writes")
    need(S, "7.98", "session log")
    need(S, "7.24", "recipe")
    need(S, "7.56", "CANONICAL BRAIN POINTER")
    need(S, "7.60", "ENGINEERED-NOT-VALIDATED")
    # (meaning, what exists today, what would have to be built and tested)
    talk = [
        ("Ordinary phrasing understood",
         "HELM reads a sentence the way people actually type it (a purpose clause, a feeling, past tense, a hedge, a typo) and gets the fact out of it.",
         "A hand-written reader for kitchen sentences; its clause and face-name gaps were fixed on the laptop and pass 26 new tests, but no sealed exam has scored the fix ({s7111}, {s7109}). The transformer ear that would read what the hand-written reader cannot is designed to be retrained, not retrained ({s7110}); its last scored words were no gain on real sentences and harmed on machine-written ones ({s7090}).",
         "Retrain the ear so it can say \"nothing to save\" on purpose; score reader and ear on a fresh exam of conversational turns the builder never sees."),
        ("\"Nothing to save\" small talk",
         "On \"hi\", \"thanks\", \"how are you\", HELM says something short and saves nothing: no stock row, no fact.",
         "The chat already drops small talk without saving on the scored runs (0 lost to small talk in c54, {s7108}), but on templates, not on sentences people wrote. The ear has no \"nothing\" output yet ({s7110}).",
         "The new \"nothing to save\" output in the ear; a hard check that nothing was saved on such turns (the packet's HG12); the mark U3, at least 46 of 48."),
        ("The mouth",
         "No recipe talk on a turn that is not about recipes; every amount exact; \"I don't know\" said when HELM does not know; what was saved said back.",
         "The voice guards recipe replies today (exact amounts, honest-unknown markers; {s7060}); the no-recipe-speak rule on other turns and the said-back rule for corrections are designed, not built ({s7110}, rules M1 to M9).",
         "Extend the guard to every reply; a published list of recipe words that may not appear on a non-recipe turn; marks S1 to S4."),
        ("Off-topic talk, answered like a person who does not know the subject",
         "When the person talks about something outside the kitchen, HELM reacts in one line, keeps what was said word for word, and asks one question about it. It never makes up an opinion, and never states a fact it was not told.",
         "Nothing. Today an off-topic line is dropped without a save and the reply is reported, not scored ({s7110}). The owner ruled on 2026-10-21 that HELM may comment like a normal person would; the coordinator's reading, accepted: like a person who does NOT know the subject. The rule is written as amendment A-TALK-1 (mouth rule M10).",
         "Build the react / keep / ask templates; marks O1 (0 invented facts), O2 (0 opinions), O3 (a question back on at least 14 of 16), scored by a key written by a different model family than the turn's writer."),
        ("HELM asks about what it does know",
         "Whatever the person brings up, HELM asks a question about the part it already holds something on: a fact saved earlier, an ingredient it has a recipe for, a thing said earlier in the session.",
         "HELM asks today only when a recipe step is missing something (its CLARIFY asks; {s7087}). Asking about a person's subject from what HELM holds is not built.",
         "A rule that looks up the person's words against the stored records and builds one question from them, using only the person's own words and HELM's stored names; scored as part of O3 first, then as its own mark."),
        ("HELM remembers the answers and reasons over them",
         "What the person answers is kept, and the next turn can use it: the memory holds it, the brain can count with it.",
         "The chat layer keeps this session's turns, up to 20 of the person's own sentences word for word (user_facts), and the stock the brain saved with a receipt in the cube store ({s7049}, {s7108}). It does not yet draw a conclusion from a kept sentence; only saved stock enters the arithmetic.",
         "A path from a kept sentence into a checked fact the brain can use (through HELM's own checker, never a guess); a sealed exam where a later turn depends on an earlier answer."),
        ("The reply's emotional tone, chosen from the Cognitive-domain states",
         "The tone of each reply would be picked by a written rule from the ten Cognitive-domain states of the 40 (C0 to C9: the ten {noetic} at the Cognitive {domain}), and the record would carry that choice with the {register} mark |f (Affective) as its own tone label, as CLAUDE.md and Clarification 8 of the foundational clarifications define it.",
         "Nothing. No part of HELM reads or writes a tone today, and no tone claim exists ({s7110}, amendment A-TALK-1 section 5). The owner's words: \"USE IT'S C-WORLD OF THE 40 ELEMENTS TO DENOTE THE CORRECT EMOTIONALITY IN IT'S RESPONSE.\"",
         "Named as the next design after the talk exam: a written rule (not a learned one) that picks one of C0 to C9 per reply, templates per state, a switch (default off), and a sealed exam against a reply with no tone rule at all."),
        ("Conversing about anything human-like",
         "The owner's standing vision: HELM talks with a person about anything, growing as it is taught, piece by piece.",
         "Nothing beyond the kitchen. HELM has no knowledge it was not taught or told, and no large language model inside; the rule against foreign pretrained models stands. Everything above is a step toward this, and each step is unlicensed until its own exam says otherwise.",
         "Each piece above, in turn, by the same four steps (below). The limit stays honest: HELM will only ever know what it was taught or told."),
        ("A transformer mouth trained on the 40 elements, for tone",
         "The same small translator that is HELM's ear (CAS symbols on one side, English on the other) trained the other way round: it takes the brain's checked receipt (the facts, amounts and names HELM actually recorded) plus the CAS tags already stamped on the record (which of the 40 states, which Register) and writes the English reply, so HELM need not depend on fixed templated sentences. It may choose words, never facts.",
         "Nothing. The ear has only ever been trained English to CAS. The design is Part M of amendment A-TALK-1 ({s7110}): every number and name must be copied from the receipt; the existing voice guard rejects any sentence that names a fact the receipt does not hold and the template answers instead; 0 invented facts is a must-hold check. The owner's words: \"SEE THIS IS WHY I WANT A TRANSFORMER TRAINED ON THE 40 ELEMENTS BECAUSE THAT CAN CONTRIBUTE TO THE NUANCE HUMAN LIKE TONE ... HELM DOESN'T HAVE TO DEPEND ON DETERMINISTIC TEMPLATED PHRASES\".",
         "Train it on (receipt + tags to English) pairs, rule-made and AI-written from several model families; score it against today's templated voice on the same turns: same records exactly, no fewer plain replies, varied wording on repeated receipts, and a tone that matches the key's state label at least 8 of 64 turns more often; about 2.6 USD together with the ear's retraining, inside TALK TRAIN at 3 USD if the sealed count fits, else a separate line."),
        # Items 10 to 13: the owner's statement of intent of 2026-10-21, 09:42 PDT (quoted below the first quote)
        ("Teaching HELM a new subject by ordinary question-and-answer conversation, until it understands",
         "A person teaches HELM something it does not know the way one person teaches another: by talking, asking and answering, in ordinary sentences, until HELM gets it. It should sound natural throughout. \"Understood\" would be shown by a test, not by HELM saying so.",
         "Lessons by typed sentences only, one fact per line, kitchen only: the chat rounds taught stock and recipe lines one at a time ({s7098} to {s7108}); the talk packet designs the three layers that would carry a normal conversation ({s7110}). No lesson arrives as a back-and-forth conversation today, and no test of \"it understood\" exists.",
         "A written test for \"understood\" first (the subject asked back in fresh words, in the right amounts, with HELM's own checker as the judge, never a feeling of understanding); then a teaching path where each turn of the conversation can add, correct or withdraw a fact through the same checker; a fresh exam of taught subjects the builder never sees, scored against the cheapest trick (lessons typed as plain lines)."),
        ("Memory compacted into CAS, with clues to its subject, as space fills",
         "When HELM's memory runs short, old memories are not thrown away: each is folded into a short CAS statement (HELM's exact inner language) that keeps a clue to what the memory was about, so it takes less room and can be rebuilt later.",
         "A bounded memory of this session's turns and the person's own sentences, kept word for word, with a session log on disk ({s7049}, {s7098}); the CAS compiler and the controlled CAS English {roundtrip} that turn a checked statement into English and back exactly, 576 of 576 ({s7031}); every saved fact leaves a {receipt} in the {cubestore} ({s7048}). Nothing compacts today: when the memory is full, the oldest sentences are dropped.",
         "A compaction rule (which memories, when, into which CAS statement, with which clue) written down before any code; a rebuild rule that turns the statement back into the facts; a check that a rebuilt memory equals the saved one or is marked lossy; an exam where HELM answers from compacted memory as well as from full memory, against the cheapest trick (drop the oldest). The owner named the parts (09:50 PDT, quoted below): the CTT (CAS symbols on one side, English on the other) and the CAS compiler as the compaction and rebuild machinery, the statement checked by the compiler and the round trip as the equality check; the CAS SDG, the synthetic data generator, to make the training and test pairs (memory to CAS statement and back); and compaction that works over the cube store and over the recipe brain's coefficients, so a compacted memory can still be used by the brain. All of this is INTENDED; nothing is built; nothing is licensed.",
         """<p><strong>The owner's second statement on this item, verbatim (2026-10-21 09:50 PDT, operator session; recorded in <code>Documents\\Codex\\2026-10-18\\OWNER_APPROVALS_20261018.md</code> under the heading "Owner words (2026-10-21 09:50 PDT, operator session, verbatim; a STATEMENT OF INTENT plus an ORDER to record it on the HELM Hub)"):</strong></p><blockquote class="verbatim"><p>"REMEMBER IF CTT AND CAS SDG AND CAS COMPILER ALREADY EXIST AND WORK WHY NOT EMPLOY THEM IN COMPACTING MEMORIES AS WELL AND CAN WORK WITH CUBES AND RECIPE COEFFICIENTS ALSO MAKE SURE TO PUT THIS IN HELM HUB FOR POSTERITY'S SAKE THE LLMs  MODELS THAT WILL TAKE YOUR PLACE ONCE WE RUN OUT TOKENS"</p></blockquote><p class="small">The parts it names and what each is today: the CTT, the transformer ear, trained English to CAS only ({s7110}); the CAS SDG, the generator of practice English from CAS statements; the CAS compiler and its controlled CAS English round trip, 576 of 576 ({s7031}); the cube store, where saved facts and their receipts live ({s7048}); the recipe brain and its coefficients ({s7024}, the canonical wide brain at {s7056}). None of them compacts a memory today. INTENDED / NOT A PRESENT CAPABILITY / NOTHING LICENSED.</p>"""),
        ("\"Refresh my memory\" questions, with a fit check and strengthening",
         "When HELM needs a memory it no longer holds in full, it asks the person a \"refresh my memory\" question, reasons whether the answer fits in with the rest of the context it rebuilt, and if it fits, strengthens that memory so it is recalled better next time.",
         "The person's own sentences are recalled word for word on \"what do you know about me so far?\" ({s7049}); the loop asks by default when a reading is unsure ({s7108}). There is no fit check: an answer is kept or dropped, never tested against the rest of the context. Nothing is strengthened: every kept sentence has the same weight.",
         "A written fit rule (what \"fits logically with the rest\" means, decided by HELM's own checker, never a guess); a strengthening rule that changes how a memory is kept, with a record of each change; an exam with planted wrong answers to refresh questions, scored on 0 wrong answers accepted and on recall of strengthened memories against unstrengthened ones."),
        ("The Unity Eye applied in these situations, correctly",
         "The small watcher that looks over HELM would also watch teaching, compaction and refresh: it reports what it sees and whispers a hint, and it never writes a memory, a fact or a reply itself.",
         "The {eye} scan and pairing earned keep words on made-up worlds only: found 88 of 88 planted faults with 0 Eye writes ({s7077}), and the Eye-paired idle work resolved 70.18% of a backlog with 0 Eye writes ({s7078}). The Eye acting on the recipe brain read INCONCLUSIVE in both readings, and Eye acting stays NOT LICENSED ({s7038}). The Eye is not wired to the live chat.",
         "First a written rule for what \"correctly applied\" means here (report and whisper only; 0 Eye writes as a must-hold check); then the Eye wired to the teaching, compaction and refresh paths behind a switch, default off; an exam against the same paths with the Eye off, scored on items lost, wrong memories accepted, and 0 Eye writes."),
    ]
    intent_path = REPO / "docs/working/helm_talk_design_v1/INTENT_MOUTH_TRANSFORMER_20261021.md"
    if not intent_path.exists():
        raise SystemExit("BUILD STOP: the statement of intent file is missing: " + rel(intent_path))
    intent_raw = intent_path.read_bytes()
    INTENT_SHA = hashlib.sha256(intent_raw).hexdigest()
    intent_parts = []
    for para in re.split(r"\n\s*\n", intent_raw.decode("utf-8").replace("\r\n", "\n").strip()):
        para = para.strip()
        if para == "---":
            intent_parts.append("<hr>")
        elif para.startswith("# "):
            intent_parts.append(f"<p><strong>{esc(para[2:])}</strong></p>")
        else:
            intent_parts.append(f"<p>{md(para)}</p>")
    intent_html = "".join(intent_parts)
    S_ = {"s7049": slink("7.49"), "s7060": slink("7.60"), "s7087": slink("7.87"), "s7090": slink("7.90"), "s7108": slink("7.108"),
          "s7109": slink("7.109"), "s7110": slink("7.110"), "s7111": slink("7.111"),
          "s7031": slink("7.31"), "s7038": slink("7.38"), "s7048": slink("7.48"), "s7077": slink("7.77"), "s7078": slink("7.78"),
          "s7098": slink("7.98"), "s7024": slink("7.24"), "s7056": slink("7.56"),
          "noetic": T("Noetic", "Noetics"), "domain": T("Domain", "level"), "register": T("Register"),
          "roundtrip": T("round trip"), "receipt": T("receipt"), "cubestore": T("cube store"), "eye": T("Unity Eye")}
    trows = "".join(
        f"<tr><td><strong>{esc(t[0])}</strong><br><span class=\"small\">INTENDED / NOT A PRESENT CAPABILITY / NOTHING LICENSED</span></td>"
        f"<td>{esc(t[1])}</td><td>{t[2].format(**S_) if '{' in t[2] else esc(t[2])}</td><td>{esc(t[3])}</td></tr>"
        + (f"<tr><td colspan=\"4\">{t[4].format(**S_)}</td></tr>" if len(t) > 4 else "")
        for t in talk)
    body = f"""
<h2>The intended domains</h2>
<p>The colors are the owner's scale, as a reading aid; the words are this hub's summary of the records named on the right.
Anything marked "not built" is a plan, and a plan is not a capability.</p>
<div class="tablewrap"><table><thead><tr><th>Domain</th><th>Color</th><th>Honest status</th><th>Records</th></tr></thead><tbody>{drows}</tbody></table></div>

<h2 id="talk">Intended: talking like a person</h2>
<p>Every line in this table is <strong>INTENDED / NOT A PRESENT CAPABILITY / NOTHING LICENSED</strong>. It is the owner's standing
vision for HELM, recorded on 2026-10-21 so each piece can be taught and tested in turn. HELM is a recipe brain with a hand-written
reader and a templated voice; it has no large language model inside (an {T('LLM')}), and nothing here changes that.
The owner's words, verbatim, with the date:</p>
<blockquote class="verbatim"><p>"ADD ALL OF THAT SHIT TO The intended domains OF HELM HUB SO EACH CAN EVENTUALLY BE ADDED TO THE MODEL TAUGHT TO
THE MODEL SO IT WILL EVENTUALLY "comment like a normal person would." ... HELM SHOULD ASK QUESTIONS CONCERNING WHAT IT DOES KNOW ABOUT
WHAT THE PERSON IS TALKING ABOUT AND REMEMBER AND REASON OVER THE ANSWERS GIVEN AND USE IT'S C-WORLD OF THE 40 ELEMENTS TO DENOTE THE
CORRECT EMOTIONALITY IN IT'S RESPONSE. NO THERE WILL ONLY BE LLMs LIKE YOURSELF WHO WILL [write the] typed turns ... I WILL ONLY REVIEW
... Yes THE RULE STANDS; Q 4 YES; Q 5 YES; Q6 YES ... REMEMBER THE EVENTUAL VISION AND INTENTIONS WE HAVE FOR HELM TO CONVERSE ABOUT
ANYTHING HUMAN LIKE EVEN THOUGH THAT MAY NOT BE A CAPABILITY PRESENT NOW WE ARE WORKING TOWARD THAT AND MORE."</p>
<p class="small">The owner, 2026-10-21 (afternoon, Pacific); recorded in <code>Documents\\Codex\\2026-10-18\\OWNER_APPROVALS_20261018.md</code>.
Earlier the same day the owner ruled that HELM may comment on an off-topic subject like a normal person would; the accepted reading is
"as a person who does not know the subject would".</p></blockquote>
<p>Items 10 to 13 of the table come from a second statement the owner typed the same morning. It is a <strong>statement of intent,
not an approval</strong> and not a launch order: it approves no package, no spend and no claim. It names the {T('CTT')}, the {T('SDG')}
and the CAS compiler (the program that checks and converts CAS statements), and the Eye. The owner's words, verbatim:</p>
<blockquote class="verbatim"><p>"YEAH BECAUSE SINCE WE HAVE THE CTT AND CAS SDG AND CAS COMPILER AS IT LEARNS VIA CONVERSATIONS (IN FACT WE SHOULD TEST
TEACH HELM NEW SUBJECT VIA REGULAR NORMAL Q AND A HUMAN LIKE CONVERSATIONS UNTIL IT GETS IT AND UNDERSTANDS AND IT SHOULD ALL SOUND VERY
NATURAL LIKE) AS SPACE GET TAKEN UP MEMORIES CAN BE COMPACTED INTO CAS W/CLUES TO THERE SUBJECT MATTER AND HELM IF NEED TO CAN ASK REFRESH
MY MEMORY QUESTIONS AND REASON IT OUT TO SEE IF IT FITS LOGICALLY IN WITH THE REST OF THE CONTEXT IT REBUILT AND IF SO STRENGTHEN THAT
PARTICULARS OF THAT MEMORY FOR BETTER RECALL NEXT TIME ALSO USE THE EYE IN THESE SITUATIONS, CORRECTLY APPLIED."</p>
<p class="small">The owner, 2026-10-21 09:42 PDT, typed in the operator session; recorded in
<code>Documents\\Codex\\2026-10-18\\OWNER_APPROVALS_20261018.md</code> under the heading "Owner words (2026-10-21 09:42 PDT, operator session,
verbatim; a STATEMENT OF INTENT, not an approval and not a launch order)". Nothing in it is built; nothing is licensed; the Eye's acting
stays NOT LICENSED ({slink('7.38')}).</p></blockquote>
<div class="tablewrap"><table><thead><tr><th>Piece</th><th>Plain meaning</th><th>What exists today</th><th>What would have to be built and tested</th></tr></thead><tbody>{trows}</tbody></table></div>
<p><strong>How each piece gets added, in order.</strong> <em>Taught:</em> a labelled data stratum (today's exam turns are written by AI models
of at least three families, labelled LLM_WRITTEN, never by the owner, who reviews only; amendment A-TALK-1, {slink('7.110')}).
<em>Built:</em> behind a switch, default off. <em>Tested:</em> a {T('sealed', 'sealed exam')} the builder never sees, against a mechanism-free
baseline (the cheapest trick that does the same job without the new piece). <em>Licensed:</em> only by the {T('frozen reader', 'frozen reader')}'s
own word, with a {T('claim ceiling')} (for the talk exam: LLM_WRITTEN_ONLY, never "human-written" or "real people"). The two owner lines on record,
TALK TRAIN at 3 USD and TALK EXAM at 1 USD, each bind to a future sealed package that does not exist yet; nothing has been spent.</p>

<h2 id="intent">Statement of intent for whoever comes after (2026-10-21)</h2>
<p><strong>INTENDED / NOTHING BUILT / NOTHING LICENSED.</strong> The owner ordered this statement kept on the hub for the instances and
models that take over this build after the ones writing today. It is the file
<code>docs/working/helm_talk_design_v1/INTENT_MOUTH_TRANSFORMER_20261021.md</code> (sha256 <code>{INTENT_SHA}</code>), rendered in full
and word for word below; nothing in it is a result. It names the {T('CTT')} and the {T('receipt', 'receipt')} tags; the one safety rule it
sets is that the mouth may choose words, never facts.</p>
<blockquote class="verbatim">{intent_html}</blockquote>

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
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.31, §7.38, §7.47, §7.48, §7.49, §7.55, §7.56, §7.64, §7.69, §7.77, §7.78, §7.83, §7.87, §7.89, §7.90, §7.98, §7.108, §7.110, §9.9",
        "`helm_ui/README.md` ('Wired vs not wired')",
        "Items 10 to 13: the owner's statements of intent of 2026-10-21 09:42 and 09:50 PDT in `Documents\\Codex\\2026-10-18\\OWNER_APPROVALS_20261018.md`",
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
# The build, animated (pure SVG + CSS + a small inline script; static without JS or with reduced motion)
# --------------------------------------------------------------------------------------------
STATUS_KEYS = [
    ("lic", "Licensed", "may be said in one exact sentence, on made-up worlds only"),
    ("val", "Validated, one sentence", "passed its own sealed test on named real texts; a candidate only"),
    ("keep", "Earned its keep", "switching it off made results worse (status word EARNED_KEEP), on made-up worlds"),
    ("env", "Engineered, not validated", "built and working; no validated result yet"),
    ("fail", "Failed, kept on record", "its latest scored test failed a must-hold check; the result stays on the record"),
    ("plan", "Planned / partly backed", "a plan, or only partly backed by recorded output; not a capability"),
    ("plain", "Plain step", "input or output; no claim"),
]


def _wrap_svg_text(x: float, y: float, lines: list[str], size: int = 15, weight: str = "", cls: str = "") -> str:
    out = []
    for i, ln in enumerate(lines):
        w = ' font-weight="600"' if (weight and i == 0) else ""
        out.append(f'<text x="{x}" y="{y + i * (size + 4)}" font-size="{size if i == 0 else size - 2}"{w} class="{cls}" text-anchor="middle">{esc(ln)}</text>')
    return "".join(out)


def _box(bid: str, x: int, y: int, w: int, h: int, status: str, lines: list[str], extra: str = "") -> str:
    ty = y + h / 2 - (len(lines) - 1) * 9 + 5
    return (f'<g class="part s-{status}" id="{bid}" data-cx="{x + w / 2}" data-cy="{y + h / 2}">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10"{extra}/>'
            + _wrap_svg_text(x + w / 2, ty, lines, 15, "b") + "</g>")


def _arrow(d: str, cls: str = "flow", label: str = "", lx: float = 0, ly: float = 0, anchor: str = "middle") -> str:
    lab = f'<text x="{lx}" y="{ly}" font-size="12" class="alabel" text-anchor="{anchor}">{esc(label)}</text>' if label else ""
    return f'<path d="{d}" class="{cls}" marker-end="url(#ah)"/>' + lab


def _simplex(cx: int, cy: int, r: int, pid: str, label: str) -> str:
    import math
    pts = [(cx + r * math.sin(2 * math.pi * k / 7), cy - r * math.cos(2 * math.pi * k / 7)) for k in range(7)]
    spokes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{px:.1f}" y2="{py:.1f}" class="spoke"/>' for px, py in pts)
    poly = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    labs = "".join(f'<text x="{cx + (r + 13) * math.sin(2 * math.pi * k / 7):.1f}" y="{cy - (r + 13) * math.cos(2 * math.pi * k / 7) + 4:.1f}" '
                   f'font-size="11" text-anchor="middle" class="alabel">F{k + 1}</text>' for k in range(7))
    return (f'<g class="part s-env" id="{pid}-g" data-cx="{cx}" data-cy="{cy}"><polygon points="{poly}" class="simplex"/>{spokes}{labs}'
            f'<circle id="{pid}" cx="{cx}" cy="{cy}" r="7" class="attn" data-cx="{cx}" data-cy="{cy}" data-r="{r}"/>'
            f'<text x="{cx}" y="{cy + r + 32}" font-size="13" text-anchor="middle" class="alabel" id="{pid}-lab">{esc(label)}</text></g>')


def _scene_today() -> str:
    P = []
    P.append(_box("t-eye", 210, 18, 240, 56, "env", ["Unity Eye", "scan + pairing"]))
    # crossed-out write arrow
    P.append('<g class="nowrite"><path d="M330 76 L330 118" class="flow wr" marker-end="url(#ah)"/>'
             '<line x1="316" y1="88" x2="344" y2="108" class="xmark"/><line x1="344" y1="88" x2="316" y2="108" class="xmark"/>'
             '<text x="352" y="104" font-size="12" class="alabel" text-anchor="start">write: never</text></g>')
    P.append('<path d="M212 50 L182 50 L182 662 L208 662" class="whisper" marker-end="url(#ah)"/>'
             '<text x="174" y="300" font-size="12" class="alabel" text-anchor="middle" transform="rotate(-90 174 300)">report + whisper (never a write)</text>')
    P.append(_simplex(655, 82, 46, "t-attn", "idle drive loop"))
    P.append(_box("t-in", 210, 128, 240, 42, "plain", ["English in"]))
    P.append(_box("t-reader", 210, 198, 240, 56, "keep", ["Hand-written reader", "stock-frame rule"]))
    P.append(_box("t-rt", 210, 282, 240, 50, "env", ["Round-trip check", "English -> CAS -> English"]))
    P.append('<path d="M450 296 C 488 296, 488 322, 452 322" class="flow loop" marker-end="url(#ah)"/>'
             '<text x="492" y="313" font-size="12" class="alabel" text-anchor="start">must match</text>')
    P.append(_box("t-gate", 210, 360, 240, 56, "keep", ["RPM Gate", "go / repair / ask"]))
    P.append(_box("t-ask", 476, 360, 122, 56, "keep", ["Ask", "nothing saved"]))
    P.append(_box("t-brain", 210, 452, 240, 72, "lic", ["Licensed recipe brain", "8 ingredients, 4 shapes", "32 learned slots"]))
    P.append(_box("t-wide", 476, 452, 122, 72, "val", ["Wide brain", "candidate", "switch OFF"]))
    P.append('<g class="switch"><rect x="452" y="482" width="22" height="12" rx="6" class="sw"/><circle x="0" cx="458" cy="488" r="4" class="swk"/></g>')
    P.append(_box("t-cube", 22, 452, 146, 40, "keep", ["Cube store"]))
    P.append(_box("t-triad", 22, 500, 146, 40, "keep", ["Triad"]))
    P.append(_box("t-casc", 22, 548, 146, 40, "keep", ["Cascade"]))
    P.append('<path d="M168 472 L208 480" class="rail"/><path d="M168 520 L208 494" class="rail"/><path d="M168 568 L208 510" class="rail"/>')
    P.append(_box("t-rcpt", 210, 556, 240, 52, "lic", ["Receipt", "read back, then saved"]))
    P.append(_box("t-voice", 210, 636, 240, 52, "keep", ["Voice", "reads its own numbers back"]))
    P.append(_box("t-out", 210, 716, 240, 42, "plain", ["English out"]))
    # main flow arrows
    for y1, y2 in ((170, 196), (254, 280), (332, 358), (416, 450), (524, 554), (608, 634), (688, 714)):
        P.append(_arrow(f"M330 {y1} L330 {y2}"))
    P.append(_arrow("M450 380 L474 380", label="ask", lx=462, ly=374))
    P.append(_arrow("M210 400 C 196 400, 196 226, 208 226", cls="flow loop", label="repair", lx=214, ly=348, anchor="start"))
    P.append(_arrow("M537 416 L537 430 L604 430 L604 737 L452 737", cls="flow", label="a question", lx=560, ly=600, anchor="end"))
    P.append('<text x="335" y="442" font-size="12" class="alabel" text-anchor="start">go</text>')
    # boundary and the ear
    P.append('<line x1="614" y1="170" x2="614" y2="770" class="boundary"/>'
             '<text x="623" y="520" font-size="12" class="alabel" transform="rotate(90 623 520)" text-anchor="middle">shares nothing with the brain</text>')
    P.append(_box("t-ear", 636, 330, 118, 84, "fail", ["CTT ear", "9,585,566", "parameters"]))
    P.append(_arrow("M636 388 L600 388", cls="flow ear", label="proposes", lx=630, ly=430, anchor="end"))
    return P


def _scene_intended() -> str:
    P = []
    P.append(_box("i-eye", 210, 18, 240, 56, "plan", ["Unity Eye", "wired to the live chat"]))
    P.append('<g class="nowrite"><path d="M330 76 L330 118" class="flow wr" marker-end="url(#ah)"/>'
             '<line x1="316" y1="88" x2="344" y2="108" class="xmark"/><line x1="344" y1="88" x2="316" y2="108" class="xmark"/>'
             '<text x="352" y="104" font-size="12" class="alabel" text-anchor="start">write: never</text></g>')
    P.append('<path d="M212 50 L182 50 L182 662 L208 662" class="whisper live" marker-end="url(#ah)"/>'
             '<text x="174" y="300" font-size="12" class="alabel" text-anchor="middle" transform="rotate(-90 174 300)">report + whisper, live (never a write)</text>')
    P.append(_simplex(655, 82, 46, "i-attn", "drive loop, live"))
    P.append(_box("i-in", 210, 128, 240, 42, "plain", ["English in"]))
    P.append(_box("i-reader", 210, 198, 240, 56, "keep", ["Hand-written reader", "first, as today"]))
    P.append(_box("i-rt", 210, 282, 240, 50, "env", ["Round-trip check"]))
    P.append(_box("i-gate", 210, 360, 240, 56, "keep", ["RPM Gate", "go / repair / ask"]))
    P.append(_box("i-ask", 476, 360, 122, 56, "keep", ["Ask", "read-back question"]))
    P.append(_box("i-brain", 210, 452, 240, 72, "plan", ["Wide recipe brain", "canonical since 2026-10-20", "on by default in the loop"]))
    P.append(_box("i-ref", 476, 452, 122, 72, "lic", ["Licensed brain", "kept as the", "reference"]))
    P.append(_box("i-cube", 22, 452, 146, 40, "keep", ["Cube store"]))
    P.append(_box("i-triad", 22, 500, 146, 40, "keep", ["Triad"]))
    P.append(_box("i-casc", 22, 548, 146, 40, "keep", ["Cascade"]))
    P.append('<path d="M168 472 L208 480" class="rail"/><path d="M168 520 L208 494" class="rail"/><path d="M168 568 L208 510" class="rail"/>')
    P.append(_box("i-rcpt", 210, 556, 240, 52, "lic", ["Receipt", "read back, then saved"]))
    P.append(_box("i-voice", 210, 636, 240, 52, "keep", ["Voice"]))
    P.append(_box("i-out", 210, 716, 240, 42, "plain", ["English out"]))
    for y1, y2 in ((170, 196), (254, 280), (332, 358), (416, 450), (524, 554), (608, 634), (688, 714)):
        P.append(_arrow(f"M330 {y1} L330 {y2}"))
    P.append(_arrow("M450 380 L474 380", label="ask", lx=462, ly=374))
    P.append(_arrow("M537 416 L537 430 L604 430 L604 737 L452 737", cls="flow", label="a question", lx=560, ly=600, anchor="end"))
    P.append('<line x1="614" y1="170" x2="614" y2="770" class="boundary"/>'
             '<text x="623" y="560" font-size="12" class="alabel" transform="rotate(90 623 560)" text-anchor="middle">shares nothing with the brain</text>')
    P.append(_box("i-ear", 636, 250, 118, 64, "plan", ["CTT ear", "proposes"]))
    P.append(_box("i-agree", 636, 340, 118, 64, "plan", ["3 seeds", "must agree"]))
    P.append(_arrow("M695 314 L695 338", cls="flow ear"))
    P.append(_arrow("M636 384 L600 384", cls="flow ear", label="admitted", lx=632, ly=420, anchor="end"))
    P.append(_box("i-human", 636, 452, 118, 96, "plan", ["Exam written", "by people", "(E-HUMAN-W)"]))
    P.append('<text x="695" y="566" font-size="12" class="alabel" text-anchor="middle">route to any claim</text>'
             '<text x="695" y="581" font-size="12" class="alabel" text-anchor="middle">about people</text>')
    # domain ring
    import math
    doms = [("Kitchen", "now, test world", "keep"), ("Software work", "planned", "plan"), ("Everyday planning", "partly backed", "plan"),
            ("Research governance", "planned", "plan"), ("Safety as a recipe", "planned", "plan"), ("Physical systems", "planned", "plan"),
            ("Science", "planned", "plan"), ("Receipts for outputs", "partly backed", "plan")]
    cx, cy, rx, ry = 380, 905, 300, 82
    P.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" class="ring" id="i-ring"/>'
             f'<text x="{cx}" y="{cy + 5}" font-size="14" text-anchor="middle" class="alabel">domains widen, one sealed test at a time</text>')
    for k, (n, st, c) in enumerate(doms):
        a = -math.pi / 2 + 2 * math.pi * k / len(doms)
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        P.append(f'<g class="part s-{c} dom" id="i-dom{k}" data-cx="{x:.0f}" data-cy="{y:.0f}"><rect x="{x - 78:.0f}" y="{y - 21:.0f}" width="156" height="42" rx="21"/>'
                 + _wrap_svg_text(round(x), round(y) - 3, [n, st], 13, "b") + "</g>")
    P.append(_arrow("M330 758 L330 815", cls="flow"))
    return P


def _svg(scene_id: str, parts: list[str], h: int, title: str) -> str:
    return (f'<svg viewBox="0 0 760 {h}" class="buildsvg" role="img" aria-labelledby="{scene_id}-t" id="{scene_id}-svg">'
            f'<title id="{scene_id}-t">{esc(title)}</title>'
            '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M0 0 L10 5 L0 10 z" class="ahead"/></marker></defs>'
            + "".join(parts) + f'<circle r="8" class="token" id="{scene_id}-token" cx="-50" cy="-50"/></svg>')


BUILD_CSS = r"""
.scenes{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}
.figwrap{overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:var(--surface);padding:8px}
.buildsvg{display:block;width:100%;min-width:600px;height:auto;font-family:var(--sans)}
.buildsvg text{fill:var(--ink)}
.buildsvg .alabel{fill:var(--ink-2)}
.part rect,.part polygon{stroke-width:2}
.s-lic rect{fill:color-mix(in srgb,var(--c-strong) 20%,var(--surface));stroke:var(--c-strong)}
.s-val rect{fill:color-mix(in srgb,#1f8a8a 20%,var(--surface));stroke:#1f8a8a}
.s-keep rect{fill:color-mix(in srgb,var(--c-method) 16%,var(--surface));stroke:var(--c-method)}
.s-env rect{fill:color-mix(in srgb,var(--c-null) 16%,var(--surface));stroke:var(--c-null)}
.s-env polygon{fill:color-mix(in srgb,var(--c-null) 10%,var(--surface));stroke:var(--c-null)}
.s-fail rect{fill:color-mix(in srgb,var(--c-failed) 16%,var(--surface));stroke:var(--c-failed)}
.s-plan rect{fill:var(--surface);stroke:var(--accent);stroke-dasharray:6 4}
.s-plain rect{fill:var(--surface-2);stroke:var(--line-strong)}
.part.on rect,.part.on polygon{stroke-width:4;filter:drop-shadow(0 0 6px color-mix(in srgb,var(--accent) 55%,transparent))}
.flow{fill:none;stroke:var(--ink-3);stroke-width:2}
.flow.ear{stroke:var(--c-failed)}
.flow.wr{stroke:var(--c-failed);stroke-dasharray:3 3}
.xmark{stroke:var(--c-failed);stroke-width:3}
.whisper{fill:none;stroke:var(--accent);stroke-width:2;stroke-dasharray:7 5}
.whisper.live{stroke-dasharray:none}
.rail{stroke:var(--ink-3);stroke-width:1.5;stroke-dasharray:2 3;fill:none}
.boundary{stroke:var(--ink);stroke-width:3}
.ahead{fill:var(--ink-3)}
.spoke{stroke:var(--line-strong);stroke-width:1.2}
.simplex{stroke-width:1.5}
.attn{fill:var(--accent)}
.ring{fill:none;stroke:var(--line-strong);stroke-width:2;stroke-dasharray:4 6}
.sw{fill:var(--surface-2);stroke:var(--ink-3)} .swk{fill:var(--ink-3)}
.token{fill:var(--accent);opacity:0}
html.js .token{opacity:.95}
.dom rect{stroke-width:1.5}
ol.steps{padding-left:22px} ol.steps li{margin:6px 0;padding:4px 8px;border-radius:8px}
ol.steps li.on{background:var(--accent-soft)}
.legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr));gap:8px;margin:12px 0}
.legend div{display:flex;gap:8px;align-items:flex-start;font-size:13px}
.legend svg{flex:none}
html.js .scene[hidden]{display:none}
@media (prefers-reduced-motion: reduce){.token{display:none}.part.on rect{filter:none}}
"""

BUILD_JS = r"""
(function(){
  var d=document.documentElement;
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var scenes=[].slice.call(document.querySelectorAll('.scene'));
  var btns=[].slice.call(document.querySelectorAll('[data-scene]'));
  var cur='today';
  function show(id){cur=id;scenes.forEach(function(s){s.hidden=(s.id!=='scene-'+id)});
    btns.forEach(function(b){b.setAttribute('aria-pressed',b.getAttribute('data-scene')===id?'true':'false')});restart()}
  btns.forEach(function(b){b.addEventListener('click',function(){show(b.getAttribute('data-scene'))})});
  var bar=document.getElementById('scene-toggle'); if(bar){bar.hidden=false}
  var mb=document.getElementById('motion-note'); if(mb&&reduce){mb.textContent='Reduced motion is on: the picture is shown still, with every step listed below.'}
  var timer=null, raf=null;
  function el(id){return document.getElementById(id)}
  function center(id){var g=el(id);return g?[+g.getAttribute('data-cx'),+g.getAttribute('data-cy')]:null}
  function clear(scope){[].slice.call(scope.querySelectorAll('.on')).forEach(function(x){x.classList.remove('on')})}
  function restart(){if(timer)clearTimeout(timer);if(raf)cancelAnimationFrame(raf);
    var sc=el('scene-'+cur); if(!sc)return; clear(sc); if(reduce)return;
    var steps=[].slice.call(sc.querySelectorAll('ol.steps li'));
    var tok=el(cur+'-token'), attn=el(cur==='today'?'t-attn':'i-attn'), lab=el((cur==='today'?'t-attn':'i-attn')+'-lab');
    var i=0, pos=null, phase=0;
    function moveAttn(t){if(!attn)return;var cx=+attn.getAttribute('data-cx'),cy=+attn.getAttribute('data-cy'),r=+attn.getAttribute('data-r');
      var a=t/900, k=Math.floor(a)%7, f=a-Math.floor(a), a1=2*Math.PI*k/7, a2=2*Math.PI*((k+3)%7)/7, rr=r*0.75;
      var x1=cx+rr*Math.sin(a1),y1=cy-rr*Math.cos(a1),x2=cx+rr*Math.sin(a2),y2=cy-rr*Math.cos(a2);
      attn.setAttribute('cx',x1+(x2-x1)*f);attn.setAttribute('cy',y1+(y2-y1)*f)}
    var t0=performance.now(), frozen=false;
    function loop(t){if(!frozen)moveAttn(t-t0);raf=requestAnimationFrame(loop)}
    raf=requestAnimationFrame(loop);
    function step(){clear(sc);
      if(i>=steps.length){i=0;frozen=false;if(lab)lab.textContent=cur==='today'?'idle drive loop: moving':'drive loop, live: moving';
        if(tok)tok.setAttribute('cx',-50);timer=setTimeout(step,2600);return}
      var li=steps[i];li.classList.add('on');
      var ids=(li.getAttribute('data-parts')||'').split(' ').filter(Boolean);
      var turn=li.getAttribute('data-turn')==='1'; frozen=turn;
      if(lab)lab.textContent=turn?'paused: a conversation turn is passing':(cur==='today'?'idle drive loop: moving':'drive loop, live: moving');
      ids.forEach(function(id){var g=el(id);if(g)g.classList.add('on')});
      var c=ids.length?center(ids[0]):null;
      if(tok&&c){var from=pos||c,s0=performance.now();
        (function glide(t){var f=Math.min(1,(t-s0)/600);tok.setAttribute('cx',from[0]+(c[0]-from[0])*f);tok.setAttribute('cy',from[1]+(c[1]-from[1])*f);if(f<1)requestAnimationFrame(glide)})(s0);
        pos=c}
      i++;timer=setTimeout(step,1900)}
    step()}
  document.addEventListener('DOMContentLoaded',function(){show('today')});
  if(document.readyState!=='loading'){show('today')}
})();
"""


def p_build(S: dict) -> str:
    need(S, "7.47", "RB-B 32 learned slots")
    need(S, "7.82", "9,585,566", "shares nothing with the recipe brain")
    need(S, "7.89", "WIDE_BRAIN_EARNED_KEEP", "candidate")
    need(S, "7.90", "EARS_HARMED", "EARS_NO_GAIN")
    need(S, "7.91", "NOT LAUNCHED")
    need(S, "7.93", "WIDE_WAVE_NO_GAIN", "no move")
    need(S, "7.95", "INCONCLUSIVE")
    need(S, "7.96", "WIDE_WAVE_EARNED_KEEP", "owner's decision")
    legend = "".join(
        f'<div><svg width="34" height="20" viewBox="0 0 34 20" aria-hidden="true"><g class="s-{k}"><rect x="1" y="1" width="32" height="18" rx="5" style="stroke-width:2"/></g></svg>'
        f'<span><strong>{esc(n)}</strong>: {esc(t)}</span></div>' for k, n, t in STATUS_KEYS)
    today_steps = [
        ("t-in", 1, "English in: you type an everyday sentence, such as 'we have 12 flour and 20 water'."),
        ("t-reader", 1, "The hand-written reader restates it in HELM's checked form. Its stock-frame rule saves a stock fact only when the sentence really states one (earned its keep; on fresh real sentences safe but not yet useful, §7.87)."),
        ("t-rt", 1, "The round-trip check turns the checked form back into English and reads it again; it must come back identical. It proves the form, not the truth."),
        ("t-gate", 1, "The RPM Gate is HELM's one gate. It picks one of three exits: go ahead, repair (back to the reader), or ask."),
        ("t-brain t-wide", 1, "Go: the licensed recipe brain divides what is on hand by what one unit needs and names the ingredient that runs out first. It knows 8 ingredients and 4 recipe shapes, with 32 learned slots. Beside it, the wide brain waits behind a switch that is OFF: a candidate, validated for one sentence on real recipes; the first pair wave (§7.93) left it a candidate and the re-run (§7.96) made it the candidate across the switches; the owner's word of 2026-10-20 made it canonical (§7.56), and the live loop now runs it by default."),
        ("t-cube t-triad t-casc", 1, "Side rails: the cube store keeps facts and never fills in an unknown; the triad weighs Purpose, Wisdom and Power on each ingredient; the cascade breaks a problem into smaller ones, with a stop rule and a depth limit."),
        ("t-rcpt", 1, "Receipt: nothing is saved until it is read back and checked; then it leaves a receipt, a fingerprinted record anyone can check later."),
        ("t-voice", 1, "Voice: HELM writes one to three plain sentences and reads its own numbers and names back against the receipt."),
        ("t-out", 1, "English out: you get the answer in everyday words."),
        ("t-ask", 1, "Ask: if HELM cannot read the sentence or cannot tell, the ask exit sends one question and saves nothing."),
        ("t-ear", 1, "Outside the solid line, the CTT ear (a small translator, 9,585,566 parameters) may propose a reading, but only on the ask path, and only as a question you confirm. It shares nothing with the brain. On record: no gain on real sentences (EARS_NO_GAIN) and a failed safety check on AI-written ones (EARS_HARMED), §7.90. A follow-up that lets it speak only when its three copies agree could not read its real-sentence half (INCONCLUSIVE, §7.95); its AI-written half is reported only."),
        ("t-eye", 0, "Above it all, the Unity Eye scans HELM's records for damage and whispers suggestions. The crossed-out arrow is the rule: it never writes. Today it is not wired to the live chat window."),
        ("t-attn-g", 0, "Between turns, the idle drive loop moves HELM's attention among the seven Drives (F1 to F7) toward unfinished work. It freezes while a conversation turn passes."),
    ]
    intended_steps = [
        ("i-in i-reader i-rt i-gate", 1, "Same turn, same checks: the reader goes first, then the round-trip check, then the RPM Gate."),
        ("i-brain", 1, "The main slot is where the wide recipe brain is meant to go. The pair wave (HELM's sixth test wave) ran twice: the first run (§7.93) read WIDE_WAVE_NO_GAIN on one unexplained ask, a reader defect that was then fixed; the re-run (§7.96) read WIDE_WAVE_EARNED_KEEP: no harm where the marks look, 93 of 94 real recipes learned, 0 wrong, 0 unexplained asks. The wide brain became the candidate across the switches, and on the owner's word of 2026-10-20 it is HELM's canonical brain (§7.56). The live loop and the chat now run it by default (HELM_WIDE_BRAIN=0 runs the licensed reference brain alone)."),
        ("i-ref", 1, "The licensed brain stays beside it as the reference; its one licensed sentence does not change."),
        ("i-ear i-agree", 1, "The CTT ear is admitted only through a stricter rule: all three trained copies must agree exactly, and HELM asks by default (CTT-2R, preregistered, nothing scored). Planned."),
        ("i-ask", 1, "Anything the ear proposes is still read back to you as a question before it counts; nothing is saved without your yes."),
        ("i-rcpt i-voice i-out", 1, "Receipt, voice and English out work as today."),
        ("i-eye", 0, "The Unity Eye's scan and pairing are wired to the live chat. It still only reports and whispers, and never writes. Planned."),
        ("i-attn-g", 0, "The idle drive loop runs live between turns, and still pauses during a conversation turn. Planned."),
        ("i-ring i-dom0 i-dom1 i-dom2 i-dom3 i-dom4 i-dom5 i-dom6 i-dom7", 0, "The domain ring widens beyond the kitchen, one sealed test at a time: software work (planned), everyday planning (partly backed), research governance (planned), safety as a recipe (planned), physical systems (planned), science (planned), receipts for outputs (partly backed)."),
        ("i-human", 0, "Any claim about real people typing to HELM must come from an exam that people write (E-HUMAN-W). None has run. Planned."),
    ]

    def steps_html(steps):
        return '<ol class="steps">' + "".join(
            f'<li data-parts="{esc(p)}" data-turn="{t}">{esc(c)}</li>' for p, t, c in steps) + "</ol>"

    lede = "One HELM turn, drawn as it is wired today and as it is meant to be wired next. Every part is colored by its status in the records."
    body = f"""
<style>{BUILD_CSS}</style>
<p id="motion-note" class="small muted">The picture animates one conversation turn step by step. Without scripts, or with reduced motion switched on, it is shown still, with every step listed under it.</p>
<div class="scenes" id="scene-toggle" role="group" aria-label="Choose a scene" hidden>
<button class="btn" type="button" data-scene="today" aria-pressed="true">Today</button>
<button class="btn" type="button" data-scene="intended" aria-pressed="false">Intended</button></div>
<h2>Legend</h2>
<div class="legend">{legend}</div>
<p class="small"><strong>What this animation does not claim.</strong> It shows how the parts are wired and the recorded status of each.
It does not claim that any part works for real users, that the intended scene will happen, or anything wider than each part's own record.
The moving dot is an illustration, not a measurement.</p>

<section class="scene" id="scene-today">
<h2>Today</h2>
<div class="figwrap">{_svg('today', _scene_today(), 790, 'HELM today: one conversation turn')}</div>
{steps_html(today_steps)}
</section>

<section class="scene" id="scene-intended">
<h2>Intended</h2>
<div class="figwrap">{_svg('intended', _scene_intended(), 1010, 'HELM intended: the next wiring')}</div>
{steps_html(intended_steps)}
</section>
<script>{BUILD_JS}</script>
"""
    return page("build.html", "HELM Build Animated", "The build, animated", lede, body, [
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.47, §7.56, §7.64, §7.69, §7.72, §7.77, §7.78, §7.82, §7.87, §7.89, §7.90, §7.91 (statuses and numbers)",
        "`docs/working/HELM_CAPABILITIES_ROADMAP_STATUS_CORRECTION_20261018.md` (planned / partly backed labels for the domains)",
        f"`{rel(CODEX / '2026-10-19' / 'ctt2_design_v1' / 'ACCEPTANCE_RULE.md')}` and `{rel(CODEX / '2026-10-19' / 'ctt2r' / 'PREREGISTRATION_CTT2R.md')}` (three seeds must agree; ask by default)",
        f"`{rel(CODEX / '2026-10-19' / 'cas_token_transformer_design_v1' / 'ARCHITECTURE.md')}` (the ear and the hard boundary)",
        "`helm_ui/README.md` ('Wired vs not wired': the Eye and the drive loop are not wired to the live chat)",
    ], words=True, description="One HELM turn, animated: today's wiring and the intended next wiring, colored by recorded status.")


# --------------------------------------------------------------------------------------------
# Files and paths: an inventory for the next agent (paths, sizes, hashes; sealed exams never opened)
# --------------------------------------------------------------------------------------------
DISPLAY_REPO = os.environ.get("HELM_HUB_REPO_DISPLAY", r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
HOME = Path(os.environ.get("HELM_HUB_HOME", r"C:\Users\wakil"))
ARCHIVE = Path(os.environ.get("HELM_HUB_ARCHIVE", r"D:\tksCAS-archive"))
SEALED_RE = re.compile(r"custod|^exam$|^sealed|sealed98|sealed_extract", re.I)
HASH_LIMIT = 50 * 1024 * 1024
ARCHIVE_ALIAS = {
    "r1_wave1": ["helm_r1_w1_c34g"], "r1_wave2": ["helm_r1w2_"], "r1_wave3": ["helm_r1w3_"], "r1_wave3b": ["helm_r1w3b_"],
    "rb_i1c": ["helm_rb_i1c_"], "rb_i1b": ["helm_rb_i1b_"], "cas_token_transformer": ["cas_token_transformer_", "ctt1_"],
    "scribe_l4_score": ["scribe_l4_score_"], "noetic_council": ["noetic_council_"],
}


def _dir_stats(p: Path) -> tuple[int, int, int]:
    """(files, bytes, sealed folders skipped). Never enters a sealed or custody folder."""
    files = size = skipped = 0
    for root, dirs, fs in os.walk(p):
        keep = []
        for d in dirs:
            if SEALED_RE.search(d):
                skipped += 1
            else:
                keep.append(d)
        dirs[:] = keep
        for f in fs:
            files += 1
            try:
                size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return files, size, skipped


def _sealed_dirs(p: Path, depth: int = 3) -> list[Path]:
    out = []
    base = len(p.parts)
    for root, dirs, _ in os.walk(p):
        rp = Path(root)
        keep = []
        for d in dirs:
            if SEALED_RE.search(d):
                out.append(rp / d)
            elif len(rp.parts) - base < depth:
                keep.append(d)
        dirs[:] = keep
    return sorted(out)


def _human(n: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def _first_heading(p: Path) -> str:
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            for _ in range(40):
                ln = fh.readline()
                if not ln:
                    break
                if ln.startswith("#"):
                    return noemoji(EMAIL_RE.sub("[e-mail removed]", ln.lstrip("# ").strip()))[:220]
    except OSError:
        pass
    return ""


def _doc_line(p: Path) -> str:
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.search(r'^\s*(?:"""|\'\'\')\s*(.+?)$', t, re.M)
    return noemoji(EMAIL_RE.sub("[e-mail removed]", m.group(1).strip().strip('"')))[:220] if m else ""


def _purpose_of_dir(p: Path) -> str:
    pats = ["README*.md", "RESULTS*.md", "RUN_RESULT_*.md", "PREREGISTRATION*.md", "DESIGN*.md", "ARCHITECTURE*.md",
            "SURVEY*.md", "COVERAGE*.md", "*.md"]
    for pat in pats:
        for f in sorted(p.glob(pat)):
            if not SEALED_RE.search(f.name):
                h = _first_heading(f)
                if h:
                    return h + f" (from {f.name})"
    return ""


class Inv:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, sec: str, shown: str, checked: Path | None, what: str, kind: str = "auto", sealed: bool = False,
            paths_only: bool = False, extra: str = ""):
        exists = bool(checked) and checked.exists()
        info, digest = "", ""
        if exists and not sealed and not paths_only:
            if checked.is_dir():
                n, b, sk = _dir_stats(checked)
                info = f"{n:,} files, {_human(b)}" + (f"; {sk} sealed folder(s) not entered" if sk else "")
            else:
                sz = checked.stat().st_size
                info = _human(sz)
                digest = sha256_file(checked) if sz < HASH_LIMIT else "over 50 MB, not hashed"
        elif exists and paths_only:
            info = "present (path only)"
        self.rows.append({"sec": sec, "shown": shown, "checked": str(checked) if checked else "", "what": what,
                          "exists": exists, "info": info, "sha": digest, "sealed": sealed, "extra": extra})


def _repo_shown(relpath: str) -> str:
    return DISPLAY_REPO.rstrip("\\") + "\\" + relpath.replace("/", "\\")


def files_inventory() -> Inv:
    I = Inv()
    R = lambda rp: (_repo_shown(rp), REPO / rp)
    # A. start here
    for shown, chk, what in [
        (_repo_shown("CLAUDE.md"), REPO / "CLAUDE.md", "Project rules. Read first: plain English always, AWS for heavy work, Claude is not the research governor, the spec-sheet rule, the canonical Noetic definitions."),
        (str(HOME / ".claude" / "CLAUDE.md"), HOME / ".claude" / "CLAUDE.md", "The owner's global rules for every agent (AWS execution preference, laptop memory)."),
        (*R("docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md"), "The authoritative CAS definitions; read before writing any CAS description."),
        (*R("docs/CAS_HARNESS_SPEC_SHEET.md"), "The living master record of every result. On branch claude/project-thread-pmbzd6, never master. Update it in the same commit as any result; never delete a negative."),
        (*R("CHANGELOG.md"), "Read at session start; add a line after every unit of work."),
        (*R("docs/reference/CAS_HELM_DICTIONARY.md"), "Every CAS and HELM term, plain meaning first."),
        (str(APPROVALS), APPROVALS, "The owner's words on record: every approval, ruling and sign line, verbatim, with Pacific times."),
        (str(LEDGER), LEDGER, "The AWS money ledger, current totals. Read before any paid run; add each job's hold once."),
        (str(CODEX / "AWS_COMBINED_ALLOCATION_HISTORY.jsonl"), CODEX / "AWS_COMBINED_ALLOCATION_HISTORY.jsonl", "The ledger's history, one line per change."),
    ]:
        I.add("A", shown, chk, what)
    # B. repo map
    for p in sorted(REPO.glob("helm_*.py")):
        I.add("B1", _repo_shown(p.name), p, _doc_line(p) or "HELM module.")
    for p in sorted(list(REPO.glob("test_helm_*.py")) + list(REPO.glob("tks_meta_valve_*"))):
        I.add("B1", _repo_shown(p.name), p, _doc_line(p) or ("Test file." if p.name.startswith("test_") else "Valve file."))
    for rp, what in [("helm_ui", "HELM UI v0: the calm local chat page (python helm_ui/server.py)."),
                     ("helm_hub", "This hub: build_hub.py writes site/."),
                     ("cas-synthetic", "The CAS Synthetic Data Generator and its data (seeds, the L4 split)."),
                     ("noetic-compass-scaffold/noetic-compass/api/notation/compiler.py", "The CAS compiler, repo copy (older)."),
                     ("dist/cas-offline/api/notation/compiler.py", "The CAS compiler, offline bundle copy.")]:
        I.add("B2", *R(rp), what)
    site_comp = CODEX / "2026-10-08" / "task-4" / "cas-online" / "dist" / "compiler" / "api" / "notation" / "compiler.py"
    I.add("B2", str(site_comp), site_comp, "The NEWEST CAS compiler (site bundle; adds fractal nesting analysis and CAS-Ohm). Use it for nesting and meta-logic.")
    nc = REPO / "docs" / "working" / "noetic_council"
    for d in sorted(x for x in nc.iterdir() if x.is_dir()) if nc.exists() else []:
        I.add("B3", _repo_shown(f"docs/working/noetic_council/{d.name}"), d, _purpose_of_dir(d) or "A noetic_council package.")
    wk = REPO / "docs" / "working"
    for d in sorted(x for x in wk.iterdir() if x.is_dir() and x.name != "noetic_council") if wk.exists() else []:
        I.add("B4", _repo_shown(f"docs/working/{d.name}"), d, _purpose_of_dir(d) or "A working folder (often a repo copy of an off-repo packet).")
    bk = REPO / "book"
    for d in sorted(x for x in bk.iterdir() if x.is_dir()) if bk.exists() else []:
        I.add("B5", _repo_shown(f"book/{d.name}"), d, _purpose_of_dir(d) or "A book project.")
    # C. off-repo evidence
    arch = sorted(x.name for x in ARCHIVE.iterdir() if x.is_dir()) if ARCHIVE.exists() else []
    for day in ("2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18", "2026-10-19"):
        dd = CODEX / day
        if not dd.exists():
            I.add("C", str(dd), dd, "Dated evidence folder.")
            continue
        items = sorted(dd.iterdir())
        scratch = [x for x in items if x.name.startswith("_") or x.suffix in (".txt", ".py") and x.is_file()]
        if not items:
            I.add("C", str(dd), dd, "Dated evidence folder (empty).")
        for x in items:
            if x in scratch:
                continue
            if x.is_dir():
                runs = sorted(r for r in x.rglob("RUN_RESULT_*.md") if not any(SEALED_RE.search(part) for part in r.relative_to(x).parts))
                prefixes = ARCHIVE_ALIAS.get(x.name, []) + [x.name + "_"]
                backs = [a for a in arch if any(a.startswith(pf) for pf in prefixes)]
                extra = ""
                if runs:
                    extra += "Run record: " + "; ".join(str(r) for r in runs) + ". "
                if backs:
                    extra += "Backup: " + "; ".join(str(ARCHIVE / b) for b in backs) + "."
                I.add("C", str(x), x, _purpose_of_dir(x) or "Evidence folder.", extra=extra)
                for s in _sealed_dirs(x):
                    I.add("C", str(s), s, "SEALED EXAM: never open; hashes only.", sealed=True)
            else:
                I.add("C", str(x), x, _first_heading(x) if x.suffix == ".md" else "Evidence file.")
        if scratch:
            I.rows.append({"sec": "C", "shown": str(dd), "checked": str(dd), "what": f"{len(scratch)} scratch items (names starting with _ , .txt, .py) not listed one by one.",
                           "exists": True, "info": "", "sha": "", "sealed": False, "extra": ""})
    # D. backups
    for a in arch:
        if re.search(r"202610(1[4-9]|2\d)", a):
            I.add("D", str(ARCHIVE / a), ARCHIVE / a, "Backup of a run or packet. Standing rule: three sha256 passes (source, destination re-read, whole-tree digest); the run record names its manifest.")
    # E. machines and places
    jk = CODEX / "2026-10-01" / "task-2" / "helm_operator_preparation"
    I.add("E", str(jk), jk, "The AWS job kit: controllers, reservations, closeouts, cleanup records for every paid run.", paths_only=True)
    I.add("E", str(HOME / "venvs" / "cas-gpu"), HOME / "venvs" / "cas-gpu", "Local GPU Python environment (RTX 4070; smoke tests only).", paths_only=True)
    # F. keys (paths only)
    I.add("F", str(HOME / ".cas_llm_keys.env"), HOME / ".cas_llm_keys.env", "Model API keys. Never print, never commit, never copy.", paths_only=True)
    I.add("F", str(HOME / ".aws") + "\\", HOME / ".aws", "AWS credentials. Never print, never commit, never copy.", paths_only=True)
    # G. memory (paths only)
    mem = HOME / ".claude" / "projects" / "C--Users-wakil-OneDrive-Desktop-tksCAS" / "memory"
    I.add("G", str(mem) + "\\", mem, "Claude's memory folder for this project.", paths_only=True)
    I.add("G", str(mem / "MEMORY.md"), mem / "MEMORY.md", "The memory index: one line per memory file.", paths_only=True)
    return I


def p_device(S: dict) -> str:
    need(S, "7.69", "DECOUPLING_EARNED")
    need(S, "7.38", "NOT LICENSED")
    lede = ("The HELM Cube is a concept for HELM's final home: a small black cube with no buttons that listens, talks, sees and maps its "
            "room. This page is a design only. Nothing has been built, bought or measured, and no money was spent.")
    rulings = [
        "FOR THE ISSUE OF THE BOTTOM AND CHARGING MAGNETIC PULL AND HAPTIC FEEDBACK SHOULD TAKE CARE OF KNOWING WHICH SIDE TO CHARGE",
        "YES BECAUSE THE MAIN THING IS THAT IT SHOULD LOOK THE SAME ON ALL SIDES LIKE A PLAIN BLACK BOX",
        "WITH GYRATOR WHEN IT'S BEEN MOVE TURNED AND DIRECTION FOR MAPPING IT'S ENVIROMENT GEOLOCATION AND USE WIFI TO DRAW ITSELF AN INTERNAL SCHEMATIC OF IT'S ENVIROMENT AND OR USE LIDAR",
        "ALL OF WHICH FEEDS BACK TO HELM WHO WILL HAVE ANY NECESSARY CONTROLS OVER",
        "THE ENTIRE OUTSIDE MADE OUT OF GORILLA GLASS THAT IS BLACK BUT CAN TURN ON AND SHOW SCREENS IMAGES VIDEOS ETC THIS COULD BE ANOTHER VERSION YES THIS IS JUST ANOTHER VERSION NOT THE MAIN VERSION",
    ]
    rq = "".join(f"<blockquote>{esc(r)}</blockquote>" for r in rulings)
    feats = [
        ("Size", "64 mm on each edge, about a tennis ball across; 55 mm is the smallest honest size, at the cost of magnetic charging and on-cube speech.", "estimate"),
        ("Look", "A plain black box. Off, all six faces are identical: no band, port, button or logo singles one out.", "owner ruling"),
        ("Light", "Along all twelve edges, invisible until lit. It pulses with each syllable HELM speaks and shows each mode by its motion.", "design"),
        ("Touch", "No buttons. Shake to wake. Taps to command: the number of taps is the action, the face you tap is the target. A tiny buzz confirms each counted tap.", "design"),
        ("Charging", "Qi2 magnetic wireless charging only. One unmarked face snaps to the charger by magnetic pull, and a short buzz confirms. Heat, not the standard, sets the speed: about 14 W at first, likely 7 to 10 W as it warms.", "owner ruling; speeds are estimates"),
        ("Cameras, microphones, sound", "Behind every face, hidden behind dark glass and edge slots. While docked, the charge face rests and the other five work. Cameras are off by default.", "owner ruling; design"),
        ("Knowing where it is", "A gyroscope feels every turn; small depth sensors on each face measure the walls; Wi-Fi gives distances; the phone can share the location. Together they build a coarse map of the room; space it has not measured stays undetermined. Wi-Fi alone cannot draw walls yet; that is still research.", "design; researched and fact-checked (spec Section 8a)"),
        ("Brains", "HELM's recipe brain runs on the cube. Speech runs on the cube when it is cool enough, otherwise on the phone.", "design"),
        ("Radios", "Wi-Fi 6, Bluetooth, and Thread for Matter smart-home devices, through the home's existing hub.", "design"),
        ("Another version: the display cube", "Not the main version. The whole outside is black Gorilla Glass over square screens that can show pictures, video, answers and the room map. A dark screen gives no light, so off it is still a plain black box. Screens cost power and heat, so one or two faces light at a time; cameras see worse under a screen.", "owner ruling; estimates only"),
    ]
    frows = "".join(f"<tr><td><strong>{esc(a)}</strong></td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in feats)
    hard = [
        "Six cameras running at once needs a hotter, phone-class chip; the plan is one camera at a time, chosen by where the voice came from.",
        "Hiding a camera behind dark glass costs it light, so pictures get noisy in dim rooms.",
        "Six separate speakers do not fit usefully; one driver with two passive radiators sends sound out through slots on every face.",
        "The law expects a regulatory mark on the device; the closest fit to the plain-black-box rule is a black-on-black etch on the charge face.",
        "In the EU, from 18 February 2027, portable batteries must be removable by the user, so an EU version needs an openable face.",
        "It cannot charge fast and talk at the same time: both share one small heat budget.",
    ]
    hrows = "".join(f"<li>{esc(h)}</li>" for h in hard)
    film = ""
    tpath = HUB.parent / "docs" / "working" / "helm_cube_device_concept_v0" / "COMMERCIAL_TREATMENT.md"
    ttext = read(tpath) if tpath.exists() else ""
    trows = md_table(ttext, "| # | Time | Picture") if ttext else []
    if trows:
        shot_rows = "".join(f"<tr><td>{esc(r[0])}</td><td>{esc(r[1])}</td><td>{md(r[2])}</td><td>{md(r[5])}</td><td>{md(r[6])}</td></tr>" for r in trows if len(r) >= 7)
        film = ('<h2 id="film">The concept film: "It Asks First"</h2>'
                '<p><strong>A short teaser is made. The full film is not.</strong> On 2026-10-21 there was no money for video credits, so a '
                '44.5-second teaser was made at no cost from what already existed. Every part carries its status tag burned into the picture.</p>'
                '<video controls preload="metadata" playsinline style="width:100%;max-width:960px;display:block;border-radius:12px;background:#000" '
                'src="media/helm_cube_it_asks_first_teaser_web.mp4" aria-label="It Asks First, a 44.5-second concept teaser for the HELM Cube"></video>'
                '<p class="small">What is real and what is not, in the teaser:</p>'
                '<ul class="tight">'
                '<li><strong>Not real:</strong> the cube. The opening shot is AI video; the table scene is two AI still pictures with a slow push-in; '
                'the phone screens are designed pictures. Nothing was filmed, and the cube is not built.</li>'
                '<li><strong>Real:</strong> one part only, HELM\'s own local page, recorded once on one computer on 2026-10-21. Two lines were typed, '
                'HELM\'s replies are shown word for word, and the record under the last reply is opened. Its tag reads TODAY · REAL HELM SOFTWARE · '
                'TYPED · ONE COMPUTER · TEST KITCHEN.</li>'
                '<li><strong>Voices:</strong> synthetic stock voices. HELM does not hear or speak today.</li>'
                '<li>The end card says the cube is a concept and that the film was made with AI video tools.</li>'
                '</ul>'
                '<p><strong>The full film is planned, not made.</strong> It is a 92-second film, 15 shots plus an end card, and only one shot shows real '
                'HELM software today (typed, on one computer, in a test kitchen). '
                'Most of the film shows what HELM is meant to do beyond recipes: plan a day, learn by conversation and refresh a memory, control a '
                'home by taps, map a room without guessing, refuse to commit failing code, report a failed check as a failure, hold a simulated drone '
                'still when a reading is missing, and let the Eye report without acting. It waits for money for video credits; everything made so '
                'far is kept.</p>'
                '<div class="tablewrap"><table><thead><tr><th>#</th><th>Time</th><th>What you see</th><th>What it shows</th><th>Status</th></tr></thead>'
                f'<tbody>{shot_rows}</tbody></table></div>'
                '<p class="small muted">The full treatment, with every line of dialogue, the end card and one ready-to-paste prompt per shot: '
                '<code>docs/working/helm_cube_device_concept_v0/COMMERCIAL_TREATMENT.md</code>. The teaser, its record of every take and cost, and '
                'the plan to finish the full film: <code>C:\\Users\\wakil\\Documents\\Codex\\2026-10-21\\helm_cube_film\\</code> '
                '(<code>FILM_RECORD.md</code>, <code>RESUME_FULL_FILM.md</code>).</p>')
    figs = read(HUB / "device_figures.html") if (HUB / "device_figures.html").exists() else "<p class=\"small muted\">(The figures file is not on this machine; run helm_hub/make_device_figures.py.)</p>"
    body = f"""
<h2>The owner's words</h2>
<p>The brief, and five rulings given on 2026-10-21, word for word:</p>
{rq}
<p class="small muted">"Gyrator" means gyroscope. The second ruling is the one the owner called the main thing: when it is off, the cube is a plain black box, the same on every face.</p>

<h2>What it is</h2>
<div class="tablewrap"><table><thead><tr><th>Part</th><th>The design</th><th>Status</th></tr></thead><tbody>{frows}</tbody></table></div>

<h2>HELM is in charge</h2>
<p>Every sensor feeds HELM, and HELM holds the controls: which sensors run, when the cube maps, what the light shows, which home devices it controls. Each action goes through the {T('RPM Gate')} and leaves a {T('receipt')}. A fact HELM lacks, such as a corner of the room it never measured, stays {T('UNDETERMINED')}: HELM asks instead of guessing, and never draws a wall it did not measure.</p>
<p><strong>Two lines stay outside all software, HELM included.</strong> The camera-on light is wired to each camera's power, and the hard mute is a physical switch. HELM can turn any camera or microphone on or off; it cannot hide that it did. This keeps six hidden cameras trustworthy. It is the operator's proposal, kept unless the owner overrules it.</p>

<h2 id="drawings">The drawings</h2>
<p>Concept drawings, made on the design canvas and reproduced here, with the lights moving exactly as they do on the canvas. Nothing has been built.</p>
{figs}

{film}

<h2>Who decides when HELM looks deeper?</h2>
<p>The owner also asked whether the {T('Unity Eye')} or another reasoning part could decide when HELM needs to look deeper into a problem. The answer, in short:</p>
<ul class="tight">
<li><strong>An exact arithmetic rule should decide, not the Eye.</strong> The owner's own decoupling stop already does this. On HELM's made-up cascade exam it read DECOUPLING_EARNED: 203 deeper looks instead of 609, with more good answers ({slink('7.69')}).</li>
<li><strong>The Eye checks the rule from outside.</strong> By design it never writes and never gates, and its acting is NOT LICENSED ({slink('7.38')}). With a new ruling it could ask for more depth, never for less, so the worst it could cause is extra work, not a wrong answer.</li>
<li><strong>Today's live chat has no depth choice to make.</strong> Every repair opens one level, so a decider there would measure nothing. Depth becomes a real choice when an ingredient has its own recipe.</li>
</ul>

<h2>What is hard</h2>
<ul class="tight">{hrows}</ul>

<h2>Where the details are</h2>
<ul class="tight">
<li>The full spec, with every number marked as measured by a source or estimated: <code>docs/working/helm_cube_device_concept_v0/HELM_CUBE_SPEC.md</code>.</li>
<li>The depth answer, with the three competing designs and the skeptic's review: <code>docs/working/helm_rpm_depth_decider_design_v1/DESIGN.md</code>.</li>
<li>The drawings are on a private design canvas, <code>https://claude.ai/artifact/LVdbdNcxV5eY1kcz5BwMoy</code>: off and speaking, the light modes, the six faces and what hides behind them, the magnetic charge face, the room map, and the display version.</li>
</ul>
"""
    return page("device.html", "HELM Cube Concept", "The HELM Cube: a concept for HELM's final home", lede, body, [
        "Owner's words: `C:\\Users\\wakil\\.claude\\projects\\...\\memory\\project_helm_cube_device_owner_rulings_20261021.md` and the spec's Section 0",
        "`docs/working/helm_cube_device_concept_v0/HELM_CUBE_SPEC.md` (v0.1)",
        "`docs/working/helm_rpm_depth_decider_design_v1/DESIGN.md`",
        "`docs/CAS_HARNESS_SPEC_SHEET.md` §7.38, §7.69, §7.120",
    ], words=True, words_open=False, description="A concept for HELM's final home: a plain black cube with no buttons. Design only.")


def p_files(S: dict) -> str:
    I = files_inventory()

    def table(sec_prefix: str) -> str:
        rows = [r for r in I.rows if r["sec"].startswith(sec_prefix)]
        tr = []
        for r in rows:
            mark = '<span class="sealed">do not open</span>' if r["sealed"] else ("" if r["exists"] else '<span class="missing">MISSING</span>')
            sha = f'<code>{esc(r["sha"])}</code>' if r["sha"] and len(r["sha"]) == 64 else esc(r["sha"])
            ex = f'<div class="small muted">{esc(r["extra"])}</div>' if r["extra"] else ""
            tr.append(f'<tr data-path="{esc(r["checked"])}" data-exists="{1 if r["exists"] else 0}"><td><code>{esc(r["shown"])}</code> {mark}</td>'
                      f'<td>{esc(r["what"])}{ex}</td><td>{esc(r["info"]) if r["exists"] else "MISSING"}</td><td>{sha}</td></tr>')
        return ('<div class="tablewrap"><table><thead><tr><th>Full path</th><th>What it is</th><th>Size or count</th><th>sha256 (files under 50 MB)</th></tr></thead><tbody>'
                + "".join(tr) + "</tbody></table></div>")

    nmiss = sum(1 for r in I.rows if not r["exists"])
    nseal = sum(1 for r in I.rows if r["sealed"])
    lede = ("Where everything lives, with full addresses, for the next person or agent who picks up this project. "
            "Each path was checked on disk when this page was built.")
    body = f"""
<style>.sealed{{color:var(--c-failed);font-weight:600}} .missing{{color:var(--c-weak);font-weight:600}}</style>
<p class="small">{len(I.rows)} paths listed; {nmiss} marked MISSING; {nseal} sealed exam folders marked "do not open" (listed by name only, never entered).
Repo paths are shown under the main checkout <code>{esc(DISPLAY_REPO)}</code>; they were checked in the checkout that ran this build, on branch
<code>claude/project-thread-pmbzd6</code> at commit <code>{esc(HEAD)}</code>. The main checkout folder may be on another branch; use the thread branch or a worktree from it.</p>

<h2 id="start">A. Start here if you are the next agent</h2>
<ol>
<li>Read the rules: both CLAUDE.md files below. Plain English in every report: meaning first, then the precise term; define every term; keep every number exact.</li>
<li>Read the spec sheet on branch <code>claude/project-thread-pmbzd6</code> (never master) and the CHANGELOG before doing anything.</li>
<li>The owner's word is the approvals record below. Only the owner's own words approve money, irreversible steps and claims. Claude is not the research governor; a failed {T('hard gate')} is a failure.</li>
<li>Commit as the owner's GitHub name, <code>LittleHenderson</code>, with the owner's GitHub e-mail (see the approvals record; it is not printed here). Docs PRs go to <code>claude/project-thread-pmbzd6</code>; on conflict merge the base, never rebase or force-push.</li>
<li>Custody: the builder never opens a {T('sealed')} exam; a {T('custodian')} builds it and only fingerprints cross. One attempt plus one plumbing retry per sealed package. The owner's sign line is the {T('seed')} source.</li>
<li>Update the spec sheet in the same commit as any result. Never delete a negative. Use only the legend's {T('claim status')} words.</li>
<li>Heavy work goes to {T('AWS')}; record each job's source, purpose, machine, limits and cleanup in the ledger and job kit. Back up every run to <code>D:\\tksCAS-archive\\</code> with three hash passes.</li>
<li>End every owner update with the owner's three headings, in order: WHAT IS CURRENTLY HAPPENING, FOR WAKIL TO DO, NEXT (each with the owner's chosen marker; standing format order in the approvals record).</li>
<li>Read the owner's <a href="roadmap.html#intent">statement of intent for whoever comes after</a> (2026-10-21; <code>docs/working/helm_talk_design_v1/INTENT_MOUTH_TRANSFORMER_20261021.md</code>): the transformer mouth trained on the 40 elements, which may choose words, never facts. Intended; nothing built; nothing licensed.</li>
</ol>
{table("A")}

<h2 id="repo">B. Repo map (thread branch)</h2>
<h3>HELM modules, tests and the valve</h3>{table("B1")}
<h3>Tools, data and the CAS compiler</h3>{table("B2")}
<h3>noetic_council packages (<code>docs/working/noetic_council/</code>)</h3>{table("B3")}
<h3>Working folders and packet copies (<code>docs/working/</code>)</h3>{table("B4")}
<h3>Books (<code>book/</code>)</h3>{table("B5")}

<h2 id="evidence">C. Off-repo evidence (<code>{esc(str(CODEX))}</code>, 2026-10-14 to 2026-10-19)</h2>
<p>Designs (<code>*_design_v1</code>), packets and runs, each with its first heading as its purpose, its run record and its backup.
Rows in red are sealed exam folders: do not open them; work with their hashes only.</p>
{table("C")}

<h2 id="backups">D. Backups (<code>{esc(str(ARCHIVE))}</code>, 2026-10-14 onward)</h2>
{table("D")}

<h2 id="machines">E. Machines and places</h2>
<ul class="tight">
<li>AWS region <code>us-west-2</code>. Budget ceiling and spend: the ledger in section A.</li>
<li>Laptop: light editing, launching and downloading only; local runs one process, a time cap such as 300 s, no spend. Neural training never on the laptop processor.</li>
</ul>
{table("E")}

<h2 id="keys">F. Keys and secrets (path names only)</h2>
<p><strong>Never print, never commit, never copy these files.</strong> This page shows only whether each path exists.</p>
{table("F")}

<h2 id="memory">G. Claude's memory (paths only)</h2>
{table("G")}
"""
    return page("files.html", "HELM Files Map", "Files and paths: where everything lives", lede, body, [
        "A walk of the repo checkout, the Codex evidence folders 2026-10-14 to 2026-10-19 and the backup drive, done by `helm_hub/build_hub.py` at build time (sizes and sha256 computed; sealed and custody folders never entered)",
        "`CLAUDE.md` and the owner's global rules (the start-here list)",
        f"`{rel(APPROVALS)}` (standing format order; commit identity)",
    ], words=True, words_open=False, description="Every important file and folder with its full path, size and hash, for the next agent.")


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
        "build.html": p_build(S), "model-card.html": p_model_card(S), "safety.html": p_safety(S), "roadmap.html": p_roadmap(S),
        "glossary.html": p_glossary(S), "changelog.html": p_changelog(S), "run.html": p_run(S), "files.html": p_files(S),
        "chat.html": p_chat(S), "device.html": p_device(S),
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
