"""Step 1 of job helm-claude-xreal-20261019-c42 (HELM-R1 X-REAL): verify the sealed X-REAL zip (a9b4c954) and its
freeze (67b48541; every member re-hashed), the 299 pinned public source files (SOURCES_PINNED.json 24cfb0d1, on the
laptop only; none ship), the owner's pre-approval line (121 UTF-8 bytes, sha256 2a8a6f86) as quoted in
APPROVAL_RECORD_XREAL.md and in the custodian's OWNER_LINE_XREAL.txt, the custodian handoff
XREAL_SEALED_20261019T235639Z.json (manifest 1e535511, pins 4cb97a82, inputs 37312a31, receiver all_pass) by hash only,
and write OWNER_APPROVAL_XREAL_<utc>.json in the house shape of OWNER_APPROVAL_R1W5_20261019T193227Z.json with the
fields the frozen reader xreal/merge_xreal.py rows I9/I10 read. Prints hashes and booleans only; never opens an exam
file (KEYS, SAMPLE_RECORD, INPUTS, MANIFEST are hashed as bytes, never parsed)."""
import datetime
import hashlib
import json
import zipfile
from pathlib import Path

X = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19\x_real")
OP = Path(r"C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation")
ZIP = X / "HELM_XREAL_20261019_SOURCE_XREAL.zip"
ZIP_SHA = "a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249"
FREEZE_SHA = "67b485415078ca11c5c3d984cd3f82a6a1ab1f111efc9ce2a619d3c136c8006d"
SOURCES_PINNED_SHA = "24cfb0d17c0cea0602a907e5b4537fbace8fd01e4d1ebddbb4530b5da659fbdd"
LINE_SHA = "2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00"
RECORD = X / "APPROVAL_RECORD_XREAL.md"
LINE_FILE = X / "xr_custody" / "work" / "OWNER_LINE_XREAL.txt"
HANDOFF = X / "xr_custody" / "XREAL_SEALED_20261019T235639Z.json"
EXAM = X / "xr_custody" / "exam"
CARRIER = X / "xr_custody" / "carrier" / "xr"
MANIFEST_SHA = "1e535511a6e802a727a9a49cf6b4a317037f46fadd7b92271aac4376604a541e"
INPUTS_SHA = "37312a31c9024e3f40c88118822218f28af1942a08ab13f2bfb40ed3f289bbe2"
PINS_SHA = "4cb97a82f2fa816b2715eea454f1aec48afdd11bcc0aaf1c380e36bad7304999"
PKG = "HELM_XREAL_20261019"
JOB = "helm-claude-xreal-20261019-c42"
VOID_ZIP_PREFIX = "c275daed"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


assert sha(ZIP) == ZIP_SHA, "ZIP"
assert not ZIP_SHA.startswith(VOID_ZIP_PREFIX)
assert sha(X / "PACKAGE_FREEZE_XREAL.json") == FREEZE_SHA, "FREEZE_SIDE_COPY"
z = zipfile.ZipFile(ZIP)
assert z.testzip() is None
assert hashlib.sha256(z.read(PKG + "/PACKAGE_FREEZE.json")).hexdigest() == FREEZE_SHA
fr = json.loads(z.read(PKG + "/PACKAGE_FREEZE.json"))
names = [n for n in z.namelist() if not n.endswith("/")]
mem = fr["members"]
assert set(n[len(PKG) + 1:] for n in names if n != PKG + "/PACKAGE_FREEZE.json") == set(mem)
for m, v in mem.items():
    raw = z.read(PKG + "/" + m)
    assert hashlib.sha256(raw).hexdigest() == v["sha256"] and len(raw) == v["bytes"], m
sp_raw = z.read(PKG + "/SOURCES_PINNED.json")
assert hashlib.sha256(sp_raw).hexdigest() == SOURCES_PINNED_SHA
sp = json.loads(sp_raw)
src_bad = []
for f in sp["files"]:
    p = X / "sources" / f["file"]
    if not p.is_file() or p.stat().st_size != f["bytes"] or sha(p) != f["sha256"]:
        src_bad.append(f["file"])
assert len(sp["files"]) == 299 and not src_bad, ("SOURCES", len(sp["files"]), src_bad[:5])

lb = LINE_FILE.read_bytes()
line = lb.decode("utf-8")
assert len(lb) == 121 and hashlib.sha256(lb).hexdigest() == LINE_SHA and not line.endswith("\n")
text = RECORD.read_bytes().decode("utf-8")
assert ("> " + line + "\n") in text and LINE_SHA in text and ZIP_SHA in text and FREEZE_SHA in text
seed_input = hashlib.sha256((line + ":" + ZIP_SHA).encode("utf-8")).hexdigest()

handoff = json.loads(HANDOFF.read_bytes())
assert handoff["schema"] == "helm.xreal.sealed-handoff/1" and handoff["receiver_check_all_pass"] is True
assert handoff["package_zip_sha256"] == ZIP_SHA and handoff["owner_line_sha256"] == LINE_SHA
assert handoff["manifest_sha256"] == MANIFEST_SHA == sha(EXAM / "MANIFEST_XREAL.json")
assert handoff["pins_sha256"] == PINS_SHA
for n, e in handoff["files"].items():
    assert sha(EXAM / n) == e["sha256"] and (EXAM / n).stat().st_size == e["bytes"], ("EXAM_FILE_NOT_SEALED_ONE", n)
assert sorted(p.name for p in CARRIER.iterdir()) == ["INPUTS_XREAL.json", "XREAL_PINS.json"]
for n, e in handoff["carrier_xr"].items():
    assert sha(CARRIER / n) == e["sha256"] and (CARRIER / n).stat().st_size == e["bytes"], ("CARRIER", n)
assert handoff["carrier_xr"]["INPUTS_XREAL.json"]["sha256"] == INPUTS_SHA
assert handoff["carrier_xr"]["XREAL_PINS.json"]["sha256"] == PINS_SHA

now = datetime.datetime.now(datetime.timezone.utc)
stamp = now.strftime("%Y%m%dT%H%M%SZ")
out = OP / ("OWNER_APPROVAL_XREAL_%s.json" % stamp)
rec = {
    "schema": "helm.xreal.approval/1",
    "house_shape": "helm.owner-standing-authorization/1 (keys of OWNER_APPROVAL_R1W5_20261019T193227Z.json) plus the fields the frozen reader xreal/merge_xreal.py rows I9 and I10 read (MERGE_INPUT approval: owner_line_verbatim, owner_line_sha256, package_zip_sha256, package_freeze_sha256, cap_usd, attempts, superseded_by)",
    "written_utc": now.isoformat(),
    "job": JOB,
    "job_family": "HELM-R1 X-REAL (job helm-claude-xreal-20261019-c42): the first exam built from material outside our own generators (real food sentences, real recipes, real file damage); 23 host units (HELM_XREAL_20261019, label XREAL)",
    "owner_line_verbatim": line,
    "owner_line_utf8_bytes": len(lb),
    "owner_line_sha256": LINE_SHA,
    "owner_line_note": "The owner's pre-approval line names no hash; APPROVAL_RECORD_XREAL.md binds it to this final zip (A-XR-18). It is also the exam seed source: sha256(line + ':' + zip sha256) = " + seed_input + ", so the frozen reader's I9 and I10 both read it.",
    "seed_source_input_sha256": seed_input,
    "package_zip_sha256": ZIP_SHA,
    "package_freeze_sha256": FREEZE_SHA,
    "cap_usd": 1.0,
    "attempts": "one scored + one plumbing retry",
    "attempts_detail": {"scored": 1, "plumbing_retry": 1,
                        "plumbing_retry_rule": "only if no unit of the scored pool started; same zip, same X-REAL pins; any package change is a reseal and a new sign line"},
    "superseded_by": None,
    "package": {
        "archive": str(ZIP), "archive_sha256": ZIP_SHA, "members": len(mem), "members_checked_against_freeze": len(mem),
        "members_bad": 0, "package_freeze": str(X / "PACKAGE_FREEZE_XREAL.json"), "package_freeze_sha256": FREEZE_SHA,
        "void_earlier_seals": "v1 HELM_XREAL_20261019_SOURCE_XREAL c275daed... VOID_SUPERSEDED_BY_V2 (never signed, never shipped)",
        "sources_pinned_sha256": SOURCES_PINNED_SHA, "sources_pinned_files_checked_on_laptop": len(sp["files"]), "sources_pinned_bad": 0,
        "sources_on_host": "none (RUN_LIMITS_XREAL.json sources_on_host: the pinned public sources stay on the laptop)",
        "launch_brief": str(X / "LAUNCH_BRIEF_XREAL_20261019.md"), "launch_brief_sha256": sha(X / "LAUNCH_BRIEF_XREAL_20261019.md"),
        "run_limits_member_sha256": mem["RUN_LIMITS_XREAL.json"]["sha256"],
        "preregistration": str(X / "PREREGISTRATION_X_REAL.md"), "preregistration_sha256": sha(X / "PREREGISTRATION_X_REAL.md"),
        "approval_record": str(RECORD), "approval_record_sha256": sha(RECORD),
        "custodian_owner_line_file": str(LINE_FILE), "custodian_owner_line_file_sha256": LINE_SHA,
        "custody_handoff": str(HANDOFF), "custody_handoff_sha256": sha(HANDOFF), "custody_manifest_sha256": MANIFEST_SHA,
        "frozen_criterion": "FROZEN_XREAL.json; the verdict and the part words come only from the frozen reader xreal/merge_xreal.py (PASS / FAILURE / INSTRUMENT_ERROR; part words per PREREGISTRATION_X_REAL.md section 11). A stage exit code is never the verdict.",
    },
    "authority_basis": [{
        "kind": "owner_words_verbatim_as_recorded", "who": "Wakil",
        "where": "Documents\\Codex\\2026-10-18\\OWNER_APPROVALS_20261018.md as quoted in APPROVAL_RECORD_XREAL.md (sha256 %s) and the custodian's OWNER_LINE_XREAL.txt (121 bytes); also quoted verbatim in the coordinator's launch order to this operator" % sha(RECORD),
        "utc": "2026-10-19 (Pacific), before the X-REAL v2 seal",
        "words": line, "sha256": LINE_SHA, "utf8_bytes": len(lb),
        "note": "The launch operator did not see the owner's message itself; it relies on the approval record, the custodian's line file and the coordinator's order quoting the same 121 bytes. Bytes and sha256 recomputed here.",
    }],
    "scope": {
        "all_services_usd_max": 1.0, "owner_cap_usd": 1.0,
        "wave_cap_note": "The 1.00 USD cap covers the scored attempt and at most one plumbing retry (RUN_LIMITS_XREAL.json). No torch, no GPU.",
        "hosts": 1, "automatic_retry": False,
        "what_runs": "LAUNCH_BRIEF_XREAL_20261019.md step 4: the one supervisor stage xreal_host_run (kit/STAGE_XREAL.json) running kit/run_xreal.py: wave 1, 2, 3, 3b and 4 carried tests, the X-REAL tests, then the X-REAL unit pool (23 units, two at a time). Raw data only (xreal_out/XREAL_HOST.json + .sha256); every mark and word is computed on the laptop by xreal/merge_xreal.py.",
        "operator_side": "RUN_LIMITS_XREAL.json: one m6i.xlarge, us-west-2, image ami-0dddfa1ffa6b87af7, 2-CPU slice, 14 GiB memory slice, XREAL_WORKERS=2, command deadline 2400 s, stage limit 3000 s; ledger hold 1.00 USD before launch; the charge replaces it at closeout.",
        "claims": "Claim ceiling NAMED_CORPORA_ONLY if earned (PREREGISTRATION section 11). Nothing beyond the named public corpora.",
    },
    "limits_of_this_record": "Covers ONE scored attempt plus at most ONE plumbing retry of the sealed X-REAL package (a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249) at a 1.00 USD total cap. Not covered: any reseal or package edit (needs a new owner line), a second scored attempt, a different host, the separate 8 USD transformer-training line, starting or stopping any other instance, any change to AWS account settings or quotas.",
    "recorded_by": "Claude Code sub-agent, AWS launch operator for job c42 (laptop MSI)",
}
with open(out, "x", encoding="ascii", newline="\n") as fh:
    fh.write(json.dumps(rec, indent=2, ensure_ascii=True) + "\n")
print(json.dumps({"record": str(out), "sha256": sha(out), "members": len(mem), "sources_checked": len(sp["files"]),
                  "seed_input_sha256": seed_input, "handoff_files_checked": len(handoff["files"])}, indent=1))
