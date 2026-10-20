# COUNT REPORT C1 — StackExchange Cooking, the free counts-only check (USE-1, real_stock_source_design_v1)

Written 2026-10-19 (Pacific; records in UTC). Owner word: "FETCH STACKEXCHANGE". 0 USD. Laptop only.
Counts only. No sentence text appears in this report. The custodian draws blind.

## Verdict: **SHORT**

The dump holds far too few first-person stock statements for the USE-1 draw.
SE gives **15**. The owner's floor (4 x the 64 stock cells) is **256**.
Even with the X-REAL frame added (at most 16 more), the design's own STOP rules trip
(stock items 31 < 32; reader-gives-up 11 < 12).
So no package was built, no seed exists, and no sign request was written.

## 1. The pinned dump (full record: `SOURCES_PINNED_C1.json`, sha256 `b8f6659e303aac2d0a1356195b2350d9e7fb3ae8f150559a10d4d2b3e6f14048`)

| Thing | Value |
|---|---|
| URL | `https://archive.org/download/stackexchange/cooking.stackexchange.com.7z` (served from `dn720201.ca.archive.org`) |
| Fetch time (UTC) | 2026-10-20T05:26:17Z |
| Size | 87,555,311 bytes |
| sha256 | `de98b85f9807a23dfc8c91006f8b59b2149089e94ea9d54676d215ea156a9ac6` |
| sha1 (ours = publisher's, from `stackexchange_files.xml`) | `c9f780daa9a58cc81a698ce8ae9402e964670d22` — MATCH |
| Dump date (publisher mtime) | 2024-04-06 |
| `Posts.xml` sha256 | `ce28c9240a878ea0d77d8dc832ded68a4e63f629205313498dbfbbeba8ec7a76` (102,222,077 bytes) |
| `Comments.xml` sha256 | `43af4a9bc3ed16407ec4c6cca8267689bcd39c3b0fa2124b614c360eb6cfa1d4` (44,408,160 bytes) |
| `Users.xml` sha256 (attribution only) | `8735062ff44746b942c0babf1e46418a43b7725687f59b8f373894a3ee6ea6f0` |
| Licence | CC BY-SA 4.0 from 2018-05-02; CC BY-SA 3.0 from 2011-04-08; CC BY-SA 2.5 before (per item date); attribution = author name + item link + site name + licence + "changed" note; share-alike |
| User-Agent | `HELM-USE1-fetch/1 (one-time research download)` — no '@' (`test_fetch_no_email.py` PASS) |
| Network | only the 2 URLs SOURCES.md row 5 names |

`x_real/SOURCES_PINNED.json` did not exist at the x_real root. It is now a NEW file
(sha256 `9e86981cf38d198a8bd99b71d24bd4d9b920049ae703c250267fb784ed9fba2c`). It points to the sealed package's pins
unchanged (`HELM_XREAL_20261019/SOURCES_PINNED.json`) and appends one group, `C1_stackexchange_cooking`.
No existing pin was altered.

## 2. How it was counted

- Units: 27,325 questions, 64,239 answers, 142,919 comments.
- Text: HTML stripped; `<pre>`, `<code>`, `<blockquote>` dropped. Split with the frozen splitter (`measure_yield.py`
  `SENT_RX`, 3-60 words).
- Keys: X-REAL K-S, key A + key B (`s_key_pair`), imported from the **unpacked sealed zip**
  (`HELM_XREAL_20261019_SOURCE_XREAL.zip`, sha256 `a9b4c954…`). `xr_custody\exam\` was never opened.
- Reader: `helm_english_in v1.1` (sha256 `31c8a078…`); "gives up" = CLARIFY, or NOT_MINE on a sentence it claims.
- Stock statement (owner picks): K-S FACTS **and** first-person stock shape (`stock_shape.py` `9925debf…`)
  **and** not recipe talk **and** not an instruction.
- Excluded: the designer slice (Id mod 25 = 0: 35,597 sentences), X-REAL's personal-data filter, duplicate text,
  and CTT's leakage rule against c45 `train.jsonl` (227,497 rows).
- Not applied here (custodian steps, only at a draw): spent draws, the forbidden list, the Part K pool overlap,
  the SE precision check (DESIGN 3.1).
- Laptop: 16 census processes + 1 merge, one at a time. Longest 8.5 s. Highest memory 75 MiB.

## 3. The counts (frame = all sentences outside the designer slice: 863,598)

| Count | Number | Per 10,000 sentences |
|---|---|---|
| Sentences, all | 899,195 | — |
| Sentences with a food word (frame) | 143,151 | 1,657.6 |
| K-S FACTS, any kind (two keys agree) | 56 | 0.648 |
| **First-person stock statements (K-S FACTS + shape, no recipe talk, no instruction)** | **15** | **0.174** |
| — of these, reader v1.1 gives up (CLARIFY / NOTHING_TO_SAVE side) | 9 | 0.104 |
| — of these, reader v1.1 reads | 6 | 0.069 |
| "I/we made / baked / cooked / bought" + a food word — **REPORTED only, no batch key** | 1,139 | 13.189 |
| — K-S keys them: UNDETERMINED 962, EMPTY 176, ASK 1 | | |
| Two-key agreement on food sentences | 99.54% | (I2 needs at least 90%: met) |

After exclusions (all eligible for a draw, before the custodian's steps):

| Stratum | Eligible | Cells | Owner floor (4 x cells) | Result |
|---|---|---|---|---|
| U1 + U2 stock statements | **15** | 64 | 256 | **SHORT** |
| U2 stock, reader gives up | **9** | 24 | 96 | **SHORT** |
| U3 say-ask | 268 | 32 | 128 | enough |
| U4a instruction trap | 864 | 16 | 64 | enough |
| U4b fact-from-nothing | 103,430 | 16 | 64 | enough |
| made / baked (not drawable) | 946 | — | — | reported only |

Stock items by licence: 12 under CC BY-SA 3.0, 2 under 4.0, 1 under 2.5. By kind: 9 questions, 2 answers, 4 comments.

**With the X-REAL frame added** (SOURCES.md section 1, before spent-draw removal): Tatoeba 15 + Taskmaster 1.
Upper bound: **31** stock items, **11** where the reader gives up.
The design's STOP rules need 32 and 12. Both trip: `NOT_EXERCISED`.

## 4. Ten example stock statements, by hash id only

| Item id | sha256 of the sentence | Reader v1.1 |
|---|---|---|
| `se:cooking:post:97458:3` | `0768b4d51c51a62afbbad99b20482d709fb0b023105369e581377a097774de20` | reads |
| `se:cooking:post:88174:3` | `1b50490d66eb8cabb31b86f1142054e12583ad35ed73ed187c5932623d396b0f` | gives up |
| `se:cooking:post:53419:0` | `2eaa990ca8f282ae45a81e93caaa7bd45a216d43eb7a7596bc81d3eddd720a63` | reads |
| `se:cooking:post:58591:0` | `3235ad2f475dcaf3a63f0ffc176f585a712cc7bde14dd7909ec9550531760321` | gives up |
| `se:cooking:comment:69670:4` | `34d442a8a0f546cdcc19dce16937244489073faffd96ebefe8c8a5c98d01b80b` | gives up |
| `se:cooking:comment:24483:1` | `3a7cd37b52b35cb60b24e22d9065e4c97fbc7ad4108ef901e30c36f484c708ba` | gives up |
| `se:cooking:comment:191037:0` | `48451c62a2b534bb2a5c27be6bd0a93c36a63d601269848fe0c04ed6e9172741` | gives up |
| `se:cooking:comment:117235:2` | `5a4f32c88d8ad181ef1f5be842c2e312882f3216c57cced33d6d28d1097e4185` | gives up |
| `se:cooking:post:78189:2` | `697e5dac6ffc65487324596d3148ddcb165329a7739dc526bb6ef3b6cf43c4db` | gives up |
| `se:cooking:post:44543:0` | `6de155fd7d9fa7b611f6f8199f451cfa7231b61e7cfa3e78cc9384b660931523` | reads |

## 5. What this means

- The designer guessed 1-3 stock statements per 10,000 after the shape rule. The measured rate is **0.174**.
  That is the same band as Tatoeba and Taskmaster (0.1-0.3). People on a cooking site talk about recipes and
  methods. They rarely state what is in their own kitchen.
- "Made / baked" sentences are 76 times more common (1,139). They cannot be scored: frozen K-S keys them
  UNDETERMINED, and the owner said no batch key now.
- Nothing was loosened. The key, the shape rule and the reader are the frozen ones.

## 6. Recommended next step

Stop USE-1 here, at 0 USD. Per the owner's accepted picks (OPEN_QUESTIONS Q5 / Q6):
no WildChat (it is not needed to prove SHORT, and the gap is about 8 x); **route the stock stratum to
human-written sentences (K-H: people type stock statements in their own words)**, never a looser K-S key.
That needs its own design and an owner word.

## 7. Files

| File | sha256 |
|---|---|
| `use1/census_c1_custody/CENSUS_C1.json` (counts + ids, no text) | `88aee61f6048956b62f9fe86fb21ddfcbae308d84192492d2d105ba31b1ef930` |
| `use1/census_c1_custody/rows_*.jsonl` (candidate rows WITH text: custodian folder, never printed) | 16 files |
| scripts: `fetch_c1.py`, `test_fetch_no_email.py`, `census_c1.py`, `merge_c1.py`, `selftest_census.py`, `write_pins_c1.py`, `run_one.ps1` | see `BACKUP_MANIFEST_USE1_C1.json` |
