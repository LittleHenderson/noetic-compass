# PROVENANCE — `language_v2`: what was copied in, from where, and what its bytes are

Built 2026-10-16 in `C:\Users\wakil\Documents\Codex\2026-10-16\language_v2\`.

This folder is the **merged copy** of `..\language\`. The original is untouched and still passes
(`python -B test_all.py` in `..\language\`: `30 of 30 cases passed.`). One mechanism that already
existed in this project was wired in here:

  * **RESTART_FALLBACK** — RB-C4's seeded alternative fit starts, ported from
    `2026-10-14\rb_c4\fitg.py` into `restart.py` and called by the tap's wording choice.

The Unity Eye is **not** in this build: it lives in `..\faculties_v2\eye\`, and it watches this
package (`language_v2`) as one of its measured health signals. Nothing here imports it.

Nothing in `rb_c4`, `rb_i1`, `u1b_unity_eye` or their neighbours was modified. Nothing outside
this folder was written. Every hash below was checked on 2026-10-16 with PowerShell
`Get-FileHash -Algorithm SHA256`.

## Byte-identical copies from `..\language\`

`the_copies_are_byte_identical_to_their_sources` re-hashes both sides on every run.

| copy | sha256 (source and copy, equal) |
| --- | --- |
| `cas_validator.py` | `2dff2868097e28baef1bdaa0ded1a519c7358c73ba1ccf01910318640d3b50bf` |
| `cce_parse.py` | `67bb0193709a0c6df0cdbadfbe2efc385ffc3210179120738bfc8d33740c2ea6` |
| `cce_render.py` | `ae6c6df18e541f801edecfdac0cf8c93ed74c184a1c574dce0244921bc778ce8` |
| `content.py` | `b46a39d7094554f1fa1692a93fc368e9367a3ce193396117bdd23f75274f5078` |
| `demo.py` | `364023729d1efe76fdee67166fef728a0f5b65c318a9eb47f9e31134fa9bb748` |
| `inject.py` | `a1580aa0e4152515e495fd537b437a05f83750d86601b804487d6be44bbc240e` |
| `lexicon.py` | `615a93710b4073d9b61b70bd002362c18f84e69b17cf41c42cb8b15e903c3f7b` |
| `numbers.py` | `bb1de8f3692c40180cfee3fc62a632ecdc32f289aec6c8e20e98a449cd922175` |
| `roundtrip.py` | `28582227311a4517b5037770309aa2ad6b6c5c429e6e913975b3d0f5da6984c4` |
| `DEMO_OUTPUT.txt` | `4ffe1b1f75f99f814918c50380d6d5f0a2c4c7b2185a3a174fee8c0fc7dc8172` |
| `TEST_OUTPUT.txt` | `a2eb080aeba19f342779d3e4765ad4bcdd29133fd14e79fc347710ea15dff420` |

## Copies that this merge changed, and why

| file | source sha256 | what changed |
| --- | --- | --- |
| `tap.py` | `c3b0c57d8fdd7fe92d0f41be36b263ca2a51c36fb6cb48c804599c107a00c7d2` | `tap_all` takes an optional `restart=` chooser. With no chooser the behaviour is exactly as before; with one, the restart fallback picks which lossless wording each speakable station is said in, and the round-trip receipt still refuses any sentence that does not read back. |
| `test_all.py` | `e296fe82efc9828e8ad6e534bd7797935484715cf2432b3efa6bb370591346a0` | the original 30 cases are kept word for word; five are added: the restart ledger, the tap wiring, the "a restart cannot say an unverified sentence" wall, the UNDECIDED IN SOURCES drift check and the byte-identical copies check. |
| `README.md` | `64f820ca3c90f35193986160be1ba003bbae295a6ed569a403fa970c93a00a41` | a section on the restart fallback and the UNDECIDED IN SOURCES list. |

## New in this merge

| file | what it is | sha256 at build time |
| --- | --- | --- |
| `restart.py` | the RESTART_FALLBACK port for this host: a content is a row, a wording is a route, start 0 is the fixed twin, the seeded starts draw other wordings, and every start records its seed, its start, the contents it explained and whether it was kept | `2c9a2ae51b4cbc9a92a1d0bf3c05a6519ba0fc97d964dc0f7833f0a6e8b34d02` |

## Sources read for the mechanism and NOT copied as files

| source | sha256 | what it was read for |
| --- | --- | --- |
| `2026-10-14\rb_c4\fitg.py` | `62951b1d53359313b19515e131d8cecc590c946a330ab451e0fa2f007b653a19` | `fit_routes` (150-179), `route_fit_once` (96-147), `MAX_ITER` (52), `CLEAR` (51), the seed rule (109), the fire rule (169-171) |
| `2026-10-14\rb_c4\RESULTS.md` | `01a00e5fe2daae571a1f9b0d85bef9d92632631a682fbec996f1c0e1cdc9b53e` | the measured precedent: 8,828 firings, 7,823 alternative starts kept; "a FIT-START win, not a proposal win" |
| `2026-10-15\helm_rb_i_faculties_design_v1\FACULTIES.md` | `2afe438e232f0b0dad9466e0396e37b6637452fa58881538432e08164349a555` | pondering's card (2.3), which names the re-fit's fallback |

## How to re-check all of it

```
cd C:\Users\wakil\Documents\Codex\2026-10-16\language_v2
python -B test_all.py
```

The run prints the lexicon digest first, every case by name, and `N of M cases passed.` last.
