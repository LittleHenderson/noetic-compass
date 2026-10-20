"""Write SOURCES_PINNED_C1.json (use1/ and the source folder) and create x_real/SOURCES_PINNED.json as a NEW file that
references the sealed package's pins unchanged and appends one new group C1. Run: python -B -I -X utf8 write_pins_c1.py"""
import hashlib
import json
from pathlib import Path

DAY = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19")
SRC = DAY / "x_real" / "sources" / "C1_stackexchange_cooking"
USE1 = DAY / "use1"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


log = [json.loads(x) for x in (USE1 / "fetch_log_c1.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
by = {r["file"]: r for r in log if r.get("complete")}
files = []
for name, role in [("stackexchange_files.xml", "publisher checksum list (archive.org item 'stackexchange')"),
                   ("cooking.stackexchange.com.7z", "C1 dump archive (Stack Exchange data dump, cooking.stackexchange.com)")]:
    r = by["C1_stackexchange_cooking/" + name]
    p = SRC / name
    assert sha(p) == r["sha256"]
    files.append({"file": r["file"], "url": r["url"], "served_from": r["final_url"], "fetch_utc": r["fetch_utc_complete"],
                  "http": r["http"], "bytes": p.stat().st_size, "sha256": r["sha256"], "sha1": r["sha1"],
                  "last_modified_header": r["last_modified"], "user_agent": r["user_agent"], "role": role})
pub = {"name": "cooking.stackexchange.com.7z", "size": 87555311, "md5": "f6ffe54c3783c8faebc33b30f8ff61d1",
       "crc32": "cc994830", "sha1": "c9f780daa9a58cc81a698ce8ae9402e964670d22", "mtime_unix": 1712443098,
       "mtime_utc": "2024-04-06T22:38:18Z"}
assert files[1]["sha1"] == pub["sha1"] and files[1]["bytes"] == pub["size"]
for name in ("Posts.xml", "Comments.xml", "Users.xml"):
    p = SRC / "extracted" / name
    files.append({"file": "C1_stackexchange_cooking/extracted/" + name, "extracted_from": "cooking.stackexchange.com.7z",
                  "extractor": "C:/Windows/System32/tar.exe (bsdtar 3.8.9, libarchive 3.8.9, liblzma 5.8.3)",
                  "bytes": p.stat().st_size, "sha256": sha(p),
                  "role": {"Posts.xml": "frame U-SE units (questions PostTypeId 1, answers PostTypeId 2)",
                           "Comments.xml": "frame U-SE units (comments)",
                           "Users.xml": "attribution (author display names), never a frame unit"}[name]})
licence = {
    "licence": "CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/) for posts and comments created on or "
               "after 2018-05-02; CC BY-SA 3.0 for 2011-04-08 to 2018-05-01; CC BY-SA 2.5 before 2011-04-08 "
               "(licence chosen per item by its CreationDate, as SOURCES.md row 5 says)",
    "attribution_requirements": [
        "name the author (display name) of each item used",
        "link to the item on cooking.stackexchange.com (question / answer: /q/<PostId> or /a/<PostId>; comment: the post link)",
        "name the source: Seasoned Advice (cooking.stackexchange.com), Stack Exchange network",
        "state the licence (CC BY-SA, version by item date) and indicate changes (sentence split, HTML stripped)",
        "share-alike: any derivative text published carries the same licence"],
    "kept_per_item": "id, post id, author user id / display name, creation date (licence version); files stay internal",
    "note": "archive.org also holds license.txt in the same item; not fetched (not a URL SOURCES.md names)",
}
doc = {"schema": "use1.sources-pinned-c1/1", "group": "C1_stackexchange_cooking",
       "design": "real_stock_source_design_v1/SOURCES.md row 5", "files": files, "publisher_checksum": pub,
       "publisher_checksum_match": "sha1 and size equal", "licence": licence,
       "network_rule": "only the two URLs SOURCES.md row 5 names; neutral User-Agent, no '@' (test_fetch_no_email.py PASS)",
       "untrusted": "never executed; read only by use1 scripts with python -I"}
txt = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
(USE1 / "SOURCES_PINNED_C1.json").write_text(txt, encoding="utf-8")
(SRC / "SOURCES_PINNED_C1.json").write_text(txt, encoding="utf-8")

xr = DAY / "x_real" / "SOURCES_PINNED.json"
base = DAY / "x_real" / "HELM_XREAL_20261019" / "SOURCES_PINNED.json"
assert not xr.exists(), "x_real/SOURCES_PINNED.json already exists: append by hand, never overwrite"
top = {"schema": "x_real.sources-pinned-index/1",
       "note": "x_real had no SOURCES_PINNED.json at its root; the existing pins live in the sealed package copy below "
               "and are NOT altered or copied here. New groups are appended below only.",
       "existing_pins_unchanged": {"file": "HELM_XREAL_20261019/SOURCES_PINNED.json", "sha256": sha(base),
                                   "sealed_zip": "HELM_XREAL_20261019_SOURCE_XREAL.zip",
                                   "sealed_zip_sha256": "a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249"},
       "appended_groups": [{"group": "C1_stackexchange_cooking", "added_utc": files[1]["fetch_utc"],
                            "by": "USE-1 census (owner word 'FETCH STACKEXCHANGE')", "pins": doc}]}
xr.write_text(json.dumps(top, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print("SOURCES_PINNED_C1.json", sha(USE1 / "SOURCES_PINNED_C1.json"))
print("x_real/SOURCES_PINNED.json", sha(xr))
