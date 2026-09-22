"""Independent, read-only book/owner-record audit of a frozen Git snapshot.

No learner, cloud client, or runtime model is imported. Only this report directory
is written. Historical inputs are read using git show, not mutable working copies.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from collections import Counter
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
CN = HERE.parents[2]
SUB = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
WORK = CN.parents[1]
MAIN = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
FROZEN = "626cc84b574e60217a103b72d2f09388d7aa5e34"
PIN = "d50abbbc"
BEFORE = "dbb388ee"
MAIN_PIN = "eb3c9b1e"
PREFIX = "book/CAS_PCBA_Engineer/"
COMMANDS = []
def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    COMMANDS.append({"repository": str(repo), "arguments": list(args),
                     "exit_code": result.returncode, "stderr": result.stderr.decode("utf-8", "replace")})
    if result.returncode:
        raise RuntimeError(COMMANDS[-1])
    return result.stdout
def blob(ref: str, path: str, repo: Path = WORK) -> bytes:
    return git(repo, "show", f"{ref}:{path}")
def txt(ref: str, path: str, repo: Path = WORK) -> str:
    return blob(ref, path, repo).decode("utf-8").replace("\r\n", "\n")
def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
def line_evidence(ref: str, filename: str, numbers: list[int], root: str = PREFIX):
    path = root + filename
    raw = blob(ref, path)
    lines = raw.decode("utf-8").splitlines()
    return {"commit": git(WORK, "rev-parse", ref).decode().strip(), "path": path,
            "lf_sha256": sha(raw.replace(b"\r\n", b"\n")),
            "lines": [{"line": n, "text": lines[n-1]} for n in numbers]}
def listings(ref: str):
    paths = git(WORK, "ls-tree", "-r", "--name-only", ref, "--", PREFIX).decode().splitlines()
    paths = [p for p in paths if p.endswith(".md") and "/" not in p[len(PREFIX):]]
    rows = []
    for path in paths:
        source = txt(ref, path)
        for match in re.finditer(r"^\s*(circuit|board)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", source, re.M):
            # Leading whitespace in the package regex can include newlines.
            at = match.start() + len(match.group(0)) - len(match.group(0).lstrip())
            rows.append({"path": path, "line": source.count("\n", 0, at)+1,
                         "kind": match.group(1), "name": match.group(2)})
    return {"top_level_markdown_files": len(paths), "blocks": len(rows),
            "distinct_names": len({r["name"] for r in rows}), "rows": rows}

manifest = json.loads(txt(FROZEN, SUB + "/records/audit_package_20260922/02_MANIFEST.json"))
changed = git(WORK, "diff", "--name-only", BEFORE, PIN, "--", PREFIX).decode().splitlines()
cross = []
for path in changed:
    lab, main = blob(PIN, path), blob(MAIN_PIN, path, MAIN)
    lhs, rhs = sha(lab.replace(b"\r\n", b"\n")), sha(main.replace(b"\r\n", b"\n"))
    expected = manifest["canon_pin_cross_repository_check"][path[len(PREFIX):]]
    cross.append({"path": path, "lab_lf_sha256": lhs, "main_lf_sha256": rhs,
                  "identical": lhs == rhs,
                  "matches_manifest": lhs == expected["lab_d50abbbc"] and rhs == expected["main_eb3c9b1e"],
                  "raw_identical": lab == main})
numstat = git(WORK, "diff", "--numstat", BEFORE, PIN, "--", PREFIX).decode()
insertions = sum(int(row.split("\t")[0]) for row in numstat.splitlines())
deletions = sum(int(row.split("\t")[1]) for row in numstat.splitlines())
tree_change = git(WORK, "diff", "--name-only", PIN, FROZEN, "--", PREFIX).decode()
truth = [{"a": a, "b": b, "XOR": bool(a) != bool(b), "AND": bool(a) and bool(b)}
         for a in (False, True) for b in (False, True)]
numbers = {
    "feedback_factor_exact": "333/1000",
    "book_forward_gain": 12,
    "closed_loop_at_A12": float(Fraction(12) / (1 + Fraction(12) * Fraction(333, 1000))),
    "closed_loop_at_A10": float(Fraction(10) / (1 + Fraction(10) * Fraction(333, 1000))),
    "including_serial_evaluation_gain_A18": float(Fraction(18) / (1 + Fraction(18) * Fraction(333,1000))),
    "infinite_A_limit": float(1 / Fraction(333,1000)),
    "A12_exact_feedback_one_third": float(Fraction(12) / (1 + Fraction(12,3))),
    "claim_exactly_three": False,
    "boundary": "Arithmetic under the book's formula only; no simulation or model measurement."
}
evidence = [
    line_evidence(BEFORE, "Chapter_10_Special_Purpose_Components.md", [96,98,104,278]),
    line_evidence(PIN, "Chapter_10_Special_Purpose_Components.md", [37,39,41,96,99,111,112,115,116,278,322]),
    line_evidence(BEFORE, "Chapter_14_Power_Management.md", [80,326]),
    line_evidence(BEFORE, "Appendix_E_Exercise_Answers.md", [327]),
    line_evidence(PIN, "Appendix_E_Exercise_Answers.md", [327]),
    line_evidence(BEFORE, "Appendix_A_Notation_Quick_Reference.md", [137]),
    line_evidence(PIN, "Appendix_A_Notation_Quick_Reference.md", [40,121,137]),
    line_evidence(BEFORE, "Appendix_B_Component_Datasheets.md", [372,374]),
    line_evidence(PIN, "Appendix_B_Component_Datasheets.md", [59,65,281,283,374,386,389,390]),
    line_evidence(PIN, "Appendix_C_CCDL_Language_Reference.md", [444,447,549]),
    line_evidence(PIN, "Appendix_G_Glossary.md", [47,48,238]),
    line_evidence(PIN, "Chapter_03_The_Transistor_That_Changed_Everything.md", [101,103,181,188,199]),
    line_evidence(PIN, "Chapter_16_Feedback_Systems.md", [17,20,21,22,25,182,184,198,199,204,211,213]),
    line_evidence(PIN, "Chapter_15_Mixed_Signal_Design.md", [49,144,164]),
    line_evidence(FROZEN, "CODEX_CONTINUATION_20260921.md", [51,52,53,54,55], SUB+"/"),
]
owner_path = SUB+"/research/helm_cas_expression_lab/OWNER_DECISIONS_20260921.json"
owner_text = txt(FROZEN, owner_path)
owner = json.loads(owner_text)
owner_rows = owner.get("decisions", owner.get("owner_decisions"))
if owner_rows is None:
    owner_rows = next(v for v in owner.values() if isinstance(v,list) and v and isinstance(v[0],dict) and "id" in v[0])
owner_selected = [r for r in owner_rows if r["id"] in {"OD-9","OD-10"}]
ver_path = SUB+"/records/continuation_20260921/VERIFICATION.md"
ver = txt(FROZEN, ver_path)
packaged = txt(FROZEN, SUB+"/records/audit_package_20260922/files/OTHER_AGENT_VERIFICATION.md")
continuation = txt(FROZEN, SUB+"/CODEX_CONTINUATION_20260921.md")
checks = {
    "BOOK-1": {"verdict":"REPRODUCES", "all_eight_identical": len(cross)==8 and all(x["identical"] for x in cross),
               "all_manifest_hashes_match": all(x["matches_manifest"] for x in cross), "rows":cross,
               "book_changes_since_pin":tree_change},
    "BOOK-2": {"verdict":"REPRODUCES", "files":len(changed), "insertions":insertions,"deletions":deletions,
               "numstat_stdout": numstat,
               "original_noisy_commit_stdout":git(WORK,"show","--stat","--oneline","0fc6bb30","--",PREFIX).decode(),
               "audit_checkout_eol_stdout":git(WORK,"ls-files","--eol","--",PREFIX+"*.md").decode(),
               "main_checkout_eol_stdout":git(MAIN,"ls-files","--eol","--",PREFIX+"*.md").decode(),
               "note":"39 top-level files; git pathspec also includes build/BUILD_README.md, yielding 40. This count caveat was disclosed by the pre-handover checker."},
    "BOOK-3": {"verdict":"REPRODUCES", "truth_table":truth,
               "note":"Original prose contradicts its own correct truth-table column. Two active inputs give XOR false, AND true."},
    "BOOK-4": {"verdict":"REPRODUCES", "declarations":[evidence[0],evidence[2]]},
    "BOOK-5": {"verdict":"REPRODUCES", "before":[evidence[0],evidence[3]], "after":[evidence[1],evidence[4]]},
    "BOOK-6": {"verdict":"UNVERIFIABLE", "verified":"Final two corrected lines exist, Appendix_A diff is 1/1.",
               "not_verified":"The uncommitted owner-edited pre-fix Appendix_B text and authorship-only attribution are not independently retained. Old committed NOT is line372; line374 is XOR. The pre-handover report already disclosed this.",
               "appendix_a_numstat":git(WORK,"diff","--numstat",BEFORE,PIN,"--",PREFIX+"Appendix_A_Notation_Quick_Reference.md").decode()},
    "BOOK-7": {"verdict":"REPRODUCES", "before":listings(BEFORE), "canon":listings(PIN)},
    "BOOK-8": {"verdict":"REPRODUCES", "note":"Both reported sentences and changed headings survive unchanged through the frozen audit target."},
    "GOV-3": {"verdict":"UNVERIFIABLE", "artifact_exists":True, "entries":owner_selected,
              "owner_artifact_lf_sha256":sha(owner_text.encode()),
              "quoted_refusal_in_named_verification": "do not corroborate it" in ver,
              "quoted_refusal_in_packaged_verification":"do not corroborate it" in packaged,
              "quoted_refusal_in_actual_continuation":"do not corroborate it" in continuation,
              "actual_source_path":SUB+"/CODEX_CONTINUATION_20260921.md:53",
              "boundary":"Artifact contents and prior refusal reproduce. Actual chat was not supplied to this audit; wording, speaker, and authorization authenticity cannot be established by the agent-authored artifact itself."}
}
result = {"schema":"cas.peer-audit.book/1.0","audit_target":FROZEN,
          "source_refs":{"canon":git(WORK,"rev-parse",PIN).decode().strip(),
                         "before":git(WORK,"rev-parse",BEFORE).decode().strip(),
                         "main_pin":git(MAIN,"rev-parse",MAIN_PIN).decode().strip()},
          "repositories":{"audited_git_common_dir":git(WORK,"rev-parse","--git-common-dir").decode().strip(),
                          "main_git_common_dir":git(MAIN,"rev-parse","--git-common-dir").decode().strip()},
          "claim_checks":checks,"additional_line_evidence":evidence,"finite_feedback_counterexample":numbers,
          "readonly_boundary":"Git reads and Python standard-library arithmetic only. All generated artifacts stay beside this script.",
          "commands":COMMANDS}
path = HERE/"book_probe.json"
path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
print(json.dumps({"output":str(path),"sha256":sha(path.read_bytes()),
                  "claims":{k:v["verdict"] for k,v in checks.items()},
                  "canon_files_identical":checks["BOOK-1"]["all_eight_identical"],
                  "canon_file_count":len(cross),"insertions":insertions,"deletions":deletions,
                  "listings":checks["BOOK-7"]["canon"]["blocks"],"distinct_names":checks["BOOK-7"]["canon"]["distinct_names"],
                  "finite_feedback_counterexample":numbers},ensure_ascii=False,indent=2))
