
## Amendment A-TEACH2-14 (2026-10-22 PDT) — a direct cloud client for HELM: standard library only, signs its own requests, keeps one connection open; written before the code

Status: appended after A-TEACH2-13 (`9c8e3daa…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "Yes: build a direct cloud client for HELM (standard library only, signs its own requests, keeps one connection open) so cloud calls stop starting a new program each time. Amendment first, test-first; time it live with a tiny test."

**Before (A-TEACH2-13 record, live):** a cloud question makes 3 calls through the AWS command-line tool, about 0.85 s each, median **2.66 s**; building the 200-line test chat took **73.8 s**.

**K1. The client** (`helm_cold_cloud.S3DirectCloud`): the same four operations as `S3Cloud` (`available`, `put`, `get`, `get_many`), and no delete. Standard library only: `http.client` over HTTPS to `<bucket>.s3.<region>.amazonaws.com`, AWS Signature Version 4 computed with `hashlib` and `hmac`, `xml.etree` for the object list.

**K2. One connection.** One HTTPS connection is opened on first use and kept for every later call; if the bucket closes it, the client opens a new one and retries that call once.

**K3. Signing.** Every request is signed with AWS Signature Version 4 (the canonical request, the string to sign, the date/region/service signing key). The signer is tested against AWS's published Signature Version 4 examples for S3 before it is used.

**K4. Keys.** Read the way the AWS tools read them: the environment (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`) first, else the `[default]` section of `~/.aws/credentials`. Keys are never printed, logged, written to a record or put in a URL; the client's text form shows no key.

**K5. Same safety as before.** Uploads carry `x-amz-server-side-encryption: AES256` and the sha256 of the body; never an ACL. A missing object (404) is "not there" (None); any other error or a network failure is "cannot be reached" (`CloudUnavailable`), which the callers already treat as away (never EXACT; a remembered yes is forgotten, A-TEACH2-13 R2). `get_many` lists the prefix (following continuation pages) and fetches the matching objects over the same connection.

**K6. The command-line client stays.** `S3Cloud` is kept unchanged as a fallback; nothing switches the live HELM to the cloud (the live switch still attaches no cloud, A-TEACH2-5 gaps).

**K7. The live timing test (owner-approved, tiny):** the same bucket, new prefixes under `smoke/`, made-up lines only, the same 200-line chat (limit 2,000, device limit 1,000) built once with `S3Cloud` and once with `S3DirectCloud`, the same 8 questions; plus a cross-check that an object written by one client is read back byte for byte by the other. Expected cost well under 0.01 USD; recorded per CLAUDE.md; nothing deleted by code.

**K8. Measured and reported:** seconds per cloud question and seconds to build the chat, before (command-line) and after (direct). `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).
