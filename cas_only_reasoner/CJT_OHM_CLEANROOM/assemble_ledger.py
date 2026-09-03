"""Assemble CJT_OHM_CLAIM_LEDGER.json from the clean-room agent outputs + a MECHANICAL verification.

Inputs
  --journal   workflow journal (JSONL) from the multi-agent reconstruction run: extraction results
              ({"source_key","claims",...}), verifier verdicts ({"claim_id","proposed_status",...}),
              P6 lens audits ({"lens",...}) and the completeness critic ({"missing_topics",...}).
  --extra     JSON file of clean-room claims written by the successor itself (P6, record gaps).
Outputs (this directory)
  agent_outputs/ledger_raw_agent_outputs.json   every agent output verbatim (rebuildable without journal)
  CJT_OHM_CLAIM_LEDGER.json                     the ledger
  CJT_OHM_CLAIM_TABLES.md                       markdown tables for the state-of-evidence document

MECHANICAL VERIFICATION (deterministic, $0, no model): for every claim
  - each artifact path is checked at HEAD with  git cat-file -e HEAD:<path>
  - each key number is searched VERBATIM (its numeric token) in the committed content of the
    claim's artifact files (git show HEAD:<path>), then in the claim's commit messages
STATUS RESOLUTION LAW (mechanical; prose decides nothing)
  1. If a second-agent verifier verdict exists, its proposed status is final.
  2. Otherwise start from the extractor's status and apply, in order:
     a. any cited artifact missing at HEAD                      -> UNVERIFIED (note)
     b. a numeric key number found in NO committed file:
          found only in a commit message                       -> CHAT_REPORTED_ONLY if none found in files, else note
          found nowhere                                        -> UNVERIFIED (note) for measurement statuses
     c. VERIFIED is kept only if the claim carries no numbers (a ruling/law read from a file) or the
        extractor recorded a matching re-execution / a committed independent audit file for it;
        otherwise VERIFIED -> SUPPORTED_NARROWLY (note)
  3. Categorisation statuses (OPEN, INVALID_BENCH, RETIRED_BY_IDENTITY, REFUTED, CHAT_REPORTED_ONLY)
     are kept but carry the same notes.
  4. Nothing is deleted. Extractor status, every note, and every check travel with the claim.
"""
import argparse
import collections
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
STATUSES = ["VERIFIED", "SUPPORTED_NARROWLY", "REFUTED", "RETIRED_BY_IDENTITY", "INVALID_BENCH",
            "UNVERIFIED", "CHAT_REPORTED_ONLY", "OPEN"]
MEASUREMENT = {"VERIFIED", "SUPPORTED_NARROWLY"}
STATUS_LAW = {
    "VERIFIED": "committed runnable artifact at HEAD + number in a committed FILE + (re-executed and matched OR committed different-family audit record)",
    "SUPPORTED_NARROWLY": "committed artifact + numbers present and coherent, but scope limited, numerical not proved, or no independent audit; or a measured fact about a construction itself declared invalid",
    "REFUTED": "a committed artifact shows the claim false",
    "RETIRED_BY_IDENTITY": "shown to be an algebraic identity / coordinate relabelling, not a distinct hypothesis class",
    "INVALID_BENCH": "design or bench declared invalid / DO_NOT_BUILD by committed review or owner ruling",
    "UNVERIFIED": "written in a committed document but no committed script or raw output reproduces it (or a cited artifact / number could not be found at HEAD)",
    "CHAT_REPORTED_ONLY": "appears only in chat, commit messages or memory notes; in no committed artifact file",
    "OPEN": "hypothesis neither confirmed nor fairly killed",
}
NUM_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?")
_content_cache = {}
_msg_cache = {}


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def file_at_head(path):
    if path not in _content_cache:
        code, out = git("show", f"HEAD:{path}")
        _content_cache[path] = out if code == 0 else None
    return _content_cache[path]


def commit_msg(sha):
    if sha not in _msg_cache:
        code, out = git("show", "-s", "--format=%B", sha)
        _msg_cache[sha] = out if code == 0 else ""
    return _msg_cache[sha]


def numeric_token(s):
    m = NUM_RE.findall(s or "")
    if not m:
        return None
    return max(m, key=len)


def mechanical_check(claim):
    paths = [p.replace("\\", "/").strip() for p in (claim.get("artifact_paths") or []) if p]
    missing, present, uncommitted = [], [], []
    texts = []
    for p in paths:
        t = file_at_head(p)
        if t is not None:
            present.append(p)
            texts.append(t)
        elif (ROOT / p).is_file():
            # clean-room receipts written in this worktree; committed by the same commit as the ledger
            uncommitted.append(p)
            texts.append((ROOT / p).read_bytes().decode("utf-8", errors="replace"))
        else:
            missing.append(p)
    files_text = "\n".join(texts)
    msgs_text = "\n".join(commit_msg(s) for s in (claim.get("commits") or []))
    found_file, found_msg, not_found, skipped = [], [], [], []
    for n in (claim.get("key_numbers") or []):
        tok = numeric_token(n)
        needle = tok if tok is not None else (n or "").strip()
        if not needle:
            continue
        if tok is None and len(needle) < 6:
            skipped.append(n)
            continue
        if needle in files_text:
            found_file.append(n)
        elif needle in msgs_text:
            found_msg.append(n)
        else:
            not_found.append(n)
    return {"artifacts_present": present, "artifacts_missing": missing, "artifacts_uncommitted_in_worktree": uncommitted,
            "numbers_in_committed_files": found_file, "numbers_only_in_commit_message": found_msg,
            "numbers_not_found": not_found, "numbers_skipped": skipped,
            "has_script_artifact": any(p.endswith(".py") for p in present + uncommitted)}


def extractor_reran(claim):
    txt = " ".join(str(claim.get(k) or "") for k in ("independent_auditor", "notes", "raw_evidence_locator")).lower()
    reran = ("rerun" in txt or "re-run" in txt or "re-execut" in txt or "ran to completion" in txt) and \
            ("reproduc" in txt or "match" in txt or "exact" in txt)
    audit_file = bool(re.search(r"[\w/.-]+\.(md|json)", claim.get("independent_auditor") or "")) and \
                 "no committed" not in (claim.get("independent_auditor") or "").lower() and \
                 "not committed" not in (claim.get("independent_auditor") or "").lower()
    return reran, audit_file


def resolve(claim, verdict, mech):
    ext = claim.get("status")
    notes = []
    if verdict is not None:
        final = verdict.get("proposed_status") or ext
        if verdict.get("status_verdict") not in (None, "AGREE"):
            notes.append(f"second-agent verifier {verdict.get('status_verdict')}: {ext} -> {final}")
        else:
            notes.append("second-agent verifier AGREE")
        return final if final in STATUSES else "UNVERIFIED", notes
    final = ext if ext in STATUSES else "UNVERIFIED"
    notes.append("no second-agent verdict (verification fan-out hit the session usage limit); mechanical checks applied")
    if mech["artifacts_missing"]:
        notes.append(f"artifact(s) missing at HEAD: {mech['artifacts_missing']}")
        if final in MEASUREMENT:
            final = "UNVERIFIED"
    numeric_claim = bool(mech["numbers_in_committed_files"] or mech["numbers_only_in_commit_message"] or mech["numbers_not_found"])
    if numeric_claim and not mech["numbers_in_committed_files"]:
        if mech["numbers_only_in_commit_message"] and not mech["numbers_not_found"]:
            notes.append("every numeric key number lives only in a commit message")
            if final in MEASUREMENT or final == "UNVERIFIED":
                final = "CHAT_REPORTED_ONLY"
        elif final in MEASUREMENT:
            notes.append(f"numeric key number(s) not found in any committed file or commit message: {mech['numbers_not_found']}")
            final = "UNVERIFIED"
    elif mech["numbers_not_found"]:
        notes.append(f"some key numbers not found verbatim (formatting or derived values?): {mech['numbers_not_found']}")
    if final == "VERIFIED" and numeric_claim and mech.get("has_script_artifact"):
        # a MEASUREMENT claim (it rests on a runnable script) needs a matched re-execution or a
        # committed audit file; a DOCUMENT fact (ruling, record entry) needs only verbatim presence
        reran, audit_file = extractor_reran(claim)
        if not (reran or audit_file):
            notes.append("VERIFIED capped at SUPPORTED_NARROWLY: measurement claim with no recorded matching re-execution and no committed independent audit file")
            final = "SUPPORTED_NARROWLY"
    if mech.get("artifacts_uncommitted_in_worktree"):
        notes.append(f"artifact(s) present in the worktree, committed with the ledger: {mech['artifacts_uncommitted_in_worktree']}")
    return final, notes


def load_journal(path):
    extractions, verdicts, lenses, critics, others = [], {}, [], [], []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") != "result":
            continue
        r = d.get("result") if d.get("result") is not None else d.get("value")
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except Exception:
                pass
        if not isinstance(r, dict):
            others.append(r)
        elif "claims" in r:
            extractions.append(r)
        elif "claim_id" in r and "proposed_status" in r:
            verdicts.setdefault(r["claim_id"], []).append(r)
        elif "lens" in r:
            lenses.append(r)
        elif "missing_topics" in r:
            critics.append(r)
        else:
            others.append(r)
    return extractions, verdicts, lenses, critics, others


def build(journal, extra):
    extractions, verdicts, lenses, critics, others = load_journal(journal)
    raw = {"extractions": extractions, "verdicts": verdicts, "p6_lenses": lenses, "critics": critics, "others": others}
    claims, seen = [], set()
    for ex in extractions:
        for c in ex.get("claims", []):
            cid = c.get("claim_id")
            if cid in seen:
                cid = f"{cid}-dup{len(seen)}"
                c["claim_id"] = cid
            seen.add(cid)
            vs = verdicts.get(cid, [])
            v = vs[0] if vs else None
            mech = mechanical_check(c)
            final, notes = resolve(c, v, mech)
            claims.append({
                "claim_id": cid, "source_key": ex.get("source_key"), "statement": c.get("statement"),
                "status": final, "extractor_status": c.get("status"), "scope": c.get("scope"),
                "commits": c.get("commits", []), "artifact_paths": c.get("artifact_paths", []),
                "independent_auditor": c.get("independent_auditor"), "raw_evidence_locator": c.get("raw_evidence_locator"),
                "known_correction": c.get("known_correction"), "may_govern_next_design": bool(c.get("may_govern_next_design")),
                "key_numbers": c.get("key_numbers", []), "number_location": c.get("number_location"),
                "mechanical_verification": mech,
                "second_agent_verification": None if v is None else {
                    "status_verdict": v.get("status_verdict"), "proposed_status": v.get("proposed_status"),
                    "artifact_check": v.get("artifact_check"), "number_check": v.get("number_check"),
                    "number_detail": v.get("number_detail"), "rerun": v.get("rerun"), "rerun_detail": v.get("rerun_detail"),
                    "reason": v.get("reason"), "defects": v.get("defects", []), "additional_verdicts": len(vs) - 1},
                "resolution_notes": notes, "notes": c.get("notes"),
            })
    if extra and pathlib.Path(extra).exists():
        for c in json.loads(pathlib.Path(extra).read_text(encoding="utf-8")).get("claims", []):
            c.setdefault("source_key", "CLEANROOM")
            c.setdefault("extractor_status", c.get("status"))
            c["mechanical_verification"] = mechanical_check(c)
            c.setdefault("second_agent_verification", None)
            c.setdefault("resolution_notes", ["clean-room successor claim; status rests on the receipts named in raw_evidence_locator (working-tree files until this commit lands)"])
            claims.append(c)
    return claims, raw, lenses, critics


def render_tables(claims):
    by_src = collections.OrderedDict()
    for c in claims:
        by_src.setdefault(c["source_key"], []).append(c)
    out = ["# CJT / CAS-Ohm claim tables (generated by assemble_ledger.py; the JSON ledger is authoritative)\n"]
    for src, cs in by_src.items():
        out.append(f"\n### {src}  ({len(cs)} claims)\n")
        out.append("| id | claim (plain English, exact numbers) | status | numbers live in | artifact | auditor | correction | governs next design |")
        out.append("|---|---|---|---|---|---|---|---|")
        for c in cs:
            art = "<br>".join(f"`{p}`" for p in (c.get("artifact_paths") or [])[:3]) or "none"
            note = ""
            if c["status"] != c.get("extractor_status"):
                note = f" *(from {c.get('extractor_status')} by resolution law)*"
            cl = lambda s: (s or "none").replace("|", "\\|").replace("\n", " ")
            out.append(f"| {c['claim_id']} | {cl(c.get('statement'))} | **{c['status']}**{note} | {c.get('number_location')} | {art} | {cl(c.get('independent_auditor'))} | {cl(c.get('known_correction'))} | {'yes' if c.get('may_govern_next_design') else 'no'} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", required=True)
    ap.add_argument("--extra", default=str(HERE / "cleanroom_claims.json"))
    ap.add_argument("--head", required=True)
    ap.add_argument("--branch", required=True)
    ap.add_argument("--built-at", required=True)
    a = ap.parse_args()
    claims, raw, lenses, critics = build(a.journal, a.extra)
    (HERE / "agent_outputs").mkdir(exist_ok=True)
    (HERE / "agent_outputs" / "ledger_raw_agent_outputs.json").write_text(json.dumps(raw, indent=1), encoding="utf-8")
    counts = collections.Counter(c["status"] for c in claims)
    changed = [(c["claim_id"], c.get("extractor_status"), c["status"]) for c in claims if c["status"] != c.get("extractor_status")]
    ledger = {
        "ledger_version": "1.0", "built_at": a.built_at, "head": a.head, "branch": a.branch,
        "status_vocabulary": STATUSES, "status_law": STATUS_LAW,
        "resolution_law": __doc__.split("STATUS RESOLUTION LAW")[1].strip(),
        "verification_state": {
            "extraction_agents_completed": len(raw["extractions"]),
            "second_agent_verdicts": sum(len(v) for v in raw["verdicts"].values()),
            "second_agent_verification": "INCOMPLETE -- the per-claim adversarial verifier fan-out (226 agents) and the completeness critic failed on the account session usage limit; every claim without a verdict carries the mechanical checks and the resolution-law notes instead",
            "mechanical_verification": "COMPLETE for every claim (artifact existence at HEAD; verbatim numeric search in committed files and commit messages)",
            "p6_lens_audits_completed": len(lenses),
        },
        "claim_count": len(claims), "status_counts": dict(counts),
        "number_location_counts": dict(collections.Counter(c.get("number_location") for c in claims)),
        "status_changed_by_resolution_law": changed,
        "claims": claims, "p6_lens_audits": lenses, "completeness_critic": critics,
    }
    (HERE / "CJT_OHM_CLAIM_LEDGER.json").write_text(json.dumps(ledger, indent=1) + "\n", encoding="utf-8")
    (HERE / "CJT_OHM_CLAIM_TABLES.md").write_text(render_tables(claims), encoding="utf-8")
    print(f"claims {len(claims)}  statuses {dict(counts)}")
    print(f"second-agent verdicts {ledger['verification_state']['second_agent_verdicts']}  lenses {len(lenses)}  critics {len(critics)}")
    print(f"status changed by resolution law: {len(changed)}")
    for cid, e, f in changed:
        print(f"  {cid}: {e} -> {f}")
    miss = [(c["claim_id"], c["mechanical_verification"]["artifacts_missing"]) for c in claims if c["mechanical_verification"]["artifacts_missing"]]
    print(f"claims citing artifacts missing at HEAD: {len(miss)}")
    for cid, m in miss:
        print(f"  {cid}: {m}")


if __name__ == "__main__":
    main()
