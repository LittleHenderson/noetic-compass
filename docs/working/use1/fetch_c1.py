"""USE-1 C1 fetch: one exact URL per call, resumable, deadline-capped. Stdlib only. Run with python -I.
Usage: python -I fetch_c1.py <which> [--max-seconds 270]
  which = files_xml | dump7z   (the only two URLs SOURCES.md row 5 names)
Writes into x_real/sources/C1_stackexchange_cooking/ (untrusted data; never executed).
Appends one JSON line per call to use1/fetch_log_c1.jsonl."""
import hashlib, json, os, sys, time, urllib.request
from pathlib import Path

DAY = Path(r"C:\Users\wakil\Documents\Codex\2026-10-19")
DST = DAY / "x_real" / "sources" / "C1_stackexchange_cooking"
LOG = DAY / "use1" / "fetch_log_c1.jsonl"
URLS = {
    "files_xml": ("https://archive.org/download/stackexchange/stackexchange_files.xml", "stackexchange_files.xml"),
    "dump7z": ("https://archive.org/download/stackexchange/cooking.stackexchange.com.7z", "cooking.stackexchange.com.7z"),
}
UA = "HELM-USE1-fetch/1 (one-time research download)"


def main():
    which = sys.argv[1]
    maxs = float(sys.argv[sys.argv.index("--max-seconds") + 1]) if "--max-seconds" in sys.argv else 270.0
    url, name = URLS[which]
    part = DST / (name + ".partial")
    final = DST / name
    if final.exists():
        print("already complete:", final)
        return
    have = part.stat().st_size if part.exists() else 0
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if have:
        req.add_header("Range", "bytes=%d-" % have)
    t0 = time.time()
    rec = {"url": url, "file": "C1_stackexchange_cooking/" + name, "start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "resume_from": have, "user_agent": UA}
    done = False
    with urllib.request.urlopen(req, timeout=60) as r:
        rec["http"] = r.status
        rec["final_url"] = r.geturl()
        rec["content_length"] = r.headers.get("Content-Length")
        rec["content_range"] = r.headers.get("Content-Range")
        rec["last_modified"] = r.headers.get("Last-Modified")
        if have and r.status != 206:
            raise SystemExit("server ignored Range; refusing to append")
        with open(part, "ab") as fh:
            while True:
                b = r.read(1 << 20)
                if not b:
                    done = True
                    break
                fh.write(b)
                if time.time() - t0 > maxs:
                    break
    rec["bytes_now"] = part.stat().st_size
    rec["seconds"] = round(time.time() - t0, 1)
    rec["complete"] = done
    if done:
        h = hashlib.sha256(); s = hashlib.sha1()
        with open(part, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b); s.update(b)
        os.replace(part, final)
        rec["sha256"] = h.hexdigest(); rec["sha1"] = s.hexdigest()
        rec["fetch_utc_complete"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
