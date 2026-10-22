# HELM Hub

A living spec sheet for HELM: a static website, rebuilt by a script from the project's own records.
Plain English first; every technical word is explained where it first appears on each page.

**Confidential, internal.** Do not host it publicly. Public hosting is an owner and IP-attorney decision
(`CLAUDE.md`: much of this work is new matter not covered by the provisional filing).

## Rebuild

```
python helm_hub/build_hub.py
```

Standard library only, no network. It writes `helm_hub/site/` and then runs its checks. On the laptop:
about 8-12 s (most of it is the files inventory walk), peak about 65 MiB. Tests: `python -m unittest helm_hub/test_build_hub.py -v` (21 tests, about 10 s).

## Pages

| File | Page |
|---|---|
| `index.html` | Home: what HELM is in one screen, today's status strip, the record in numbers |
| `thinking.html` | How HELM thinks: recipes, the limiting ingredient, asking, receipts, the round trip, the Eye; canonical Noetic definitions |
| `architecture.html` | Every part with its learned-parameter count; what HELM is not; language coverage |
| `build.html` | The build, animated: one turn as wired today and as intended next (SVG + CSS + a small inline script; still picture without scripts or with reduced motion) |
| `data.html` | Generators, custody, pinned public sources with licences and hashes, the outside-material rule |
| `compute.html` | Budget totals, every paid run with its charge, laptop and GPU rules |
| `results.html` | Every HELM record from spec sheet §7.24 on, negatives included; the claim-status legend |
| `model-card.html` | Intended use, out of scope, licensed sentences quoted, known defects; what this hub does not have, and why |
| `safety.html` | Hard gates, the Eye never writes, read-back, refusal, write audit, plain findings, owner-decision headings |
| `roadmap.html` | Intended domains with honest status; "can I chat with it?"; the corrected milestone table |
| `glossary.html` | All dictionary entries, searchable in the page |
| `changelog.html` | HELM entries of `CHANGELOG.md` since 2026-10-01 |
| `run.html` | How to run the HELM UI; local endpoints; rebuilding the hub |
| `files.html` | Files and paths for the next agent: start-here rules, repo map, off-repo evidence, backups, machines, key paths (names only), memory paths; each path checked on disk, sizes and sha256 for files under 50 MB; sealed exam folders listed by name only, never entered |
| `demo.html` | A copy of `helm_ui/demo/index.html` |

## Sources it reads

In the repo: `docs/CAS_HARNESS_SPEC_SHEET.md` (§3 legend, §7.24 onward), `docs/reference/CAS_HELM_DICTIONARY.md`,
`docs/working/HELM_CAPABILITIES_ROADMAP_AND_DEVELOPMENTAL_STAGES.md` and its 2026-10-18 status correction, `CHANGELOG.md`,
`helm_ui/README.md`, `helm_ui/demo/index.html`, `docs/working/xreal/SOURCES_PINNED.json` and `PREREGISTRATION_X_REAL.md`.

Off the repo (folder set by `HELM_HUB_CODEX`, default `C:\Users\wakil\Documents\Codex`): `AWS_COMBINED_ALLOCATION_CURRENT.json`
(totals only), `2026-10-18\OWNER_APPROVALS_20261018.md` (section headings only), the `RUN_RESULT_*.md` run records under
`2026-10-18` and `2026-10-19`, and `2026-10-19\language_map_coverage_v1\COVERAGE.md`. If one is missing, the page says so and the build goes on. The files page also walks `D:\tksCAS-archive`; display paths come from `HELM_HUB_REPO_DISPLAY`, `HELM_HUB_HOME` and `HELM_HUB_ARCHIVE`.

## What the build checks (it exits 1 if any fails)

- **Jargon lint.** `TERMS` in `build_hub.py` lists the words that must be explained on first use (Noetic, Drive, recipe brain,
  limiting reagent, RPM Gate, custodian, status word, claim ceiling, Unity Eye, round trip, receipt, synthetic world, CTT, wave, pair wave and 34 more).
  On every page except the glossary, the first time a listed word appears it must sit inside a `<dfn>` with a plain explanation.
  Hand-written pages explain words inline (`T()` adds the explanation in brackets). Pages made mostly of copied records
  (results, compute, roadmap, model card, changelog) open with a "Words used on this page" box. The text of the explanations
  themselves and the quoted "Precise definition" boxes are not linted; they point to the glossary.
- **Living citations.** `need()` stops the build if a status word or number the hub cites no longer appears in the cited spec section.
- **Links.** Every internal link and anchor must resolve; no external links except Google Fonts.
- **Secrets.** No e-mail address, AWS key id, secret-key name, private key, GitHub, OpenAI, Anthropic, Google or Slack token.
  E-mail addresses are also scrubbed from every source on read.
- **Page contract.** `<!doctype html>`, charset, viewport, a 2-4 word title, dark-mode tokens on `:root` (both the media query and
  `data-theme`), an explicit body background, no external scripts, no emoji.
- **Prohibited words** of spec sheet §3 in the hub's own text (quoted record text is exempt and marked `verbatim`).

## Editing

Plain meanings and colors for each scorecard row are the hub editor's reading, in the `CUR` table of `build_hub.py`; the record governs.
A new spec-sheet section appears on the scorecard automatically; until a `CUR` row is added it shows "See the record"
(or the sealed-packet text, if its heading says NOT LAUNCHED). Colors are the owner's scale and never a claim status.
