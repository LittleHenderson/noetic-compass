# Project Coherence Paper Series (2026-08)

Papers drafted from the Project Coherence Gate 1 and Gate 4 source artifacts in
the Codex snapshot
`C:\Users\wakil\Documents\Codex\2026-08-05\referenced-chatgpt-conversation-this-is-an\work\project_coherence_model_smoke`.

## Monographs v0.3 (primary, book-length)

Full `amsbook` monographs, 12--14 chapters plus appendices each, assembled from
per-chapter LaTeX sources under `monograph/<name>/chapters/`. Build with
`monograph/build_all.sh` (three `pdflatex` passes). PDFs in `pdf/`.

| Monograph | Directory | Pages |
|---|---|---:|
| Noetic Topos 2.0 | `monograph/noetic_topos2` | 188 |
| TKS v8.0 | `monograph/tks_v8` | 184 |
| CAS Core 8 | `monograph/cas_core8` | 187 |
| CAS PCBA 8 | `monograph/cas_pcba8` | 188 |
| CAS-Ohm 1.0 | `monograph/cas_ohm1` | 187 |

Total ~934 pages. Each monograph expands its v0.2 research paper with tutorial
preliminaries, full proofs, per-code/per-conflict/per-diagnostic treatment,
implementation documentation, threat analyses, worked examples, exercises, and
reference appendices (glossaries, catalogs, census tables). The shared preamble
(`monograph/shared/preamble.tex`) and bibliography
(`monograph/shared/bibliography.tex`) are the single source of environments,
macros, and citation keys; chapter files are body-only LaTeX validated by
`monograph/sanitize_chapters.py`.

## Research papers v0.2 (primary)

Full-length amsart research papers: preliminaries, complete definitions, full
proofs where the sources contain them, executable-certificate detail,
implementation catalogs, threat analyses, and explicit open obligations.
Sources in `tex/`, builds in `pdf/`.

| Paper | File | Pages |
|---|---|---:|
| TKS v8.0 | `RESEARCH_PAPER_TKS_V8_0_v0.2` | 10 |
| Noetic Topos 2.0 | `RESEARCH_PAPER_NOETIC_TOPOS_2_0_v0.2` | 14 |
| CAS Core 8 | `RESEARCH_PAPER_CAS_CORE_8_v0.2` | 8 |
| CAS PCBA 8 | `RESEARCH_PAPER_CAS_PCBA_8_v0.2` | 9 |
| CAS-Ohm 1.0 | `RESEARCH_PAPER_CAS_OHM_1_0_v0.2` | 9 |

## White papers v0.1 (superseded summaries)

The `WHITEPAPER_*_v0.1` markdown, tex, and pdf files are the earlier short-form
summaries, retained for history. The v0.2 research papers supersede them.

## Shared conventions

- Every paper carries the governing status header
  (`DRAFT / OPEN / Ring 4 / NOT LICENSED`) inherited from its source
  specification; drafting a paper promotes nothing.
- Theorems carry the proof status recorded in the registered theorem ledgers
  (`INFORMAL_PROOF_PRESENT`, `PROOF_REQUIRED`, etc.); conjectures are labeled
  conjectures.
- Source artifacts are cited with exact SHA-256 identities where the sources
  record them; adverse findings keep their page/line anchors.
- Bounded software evidence (test counts, exhaustive-case counts, certificate
  identities) is reported as historical, source-bound receipts — never as
  experiments, empirical validation, or authority.
- Open obligations and admission gates are reproduced, not summarized away.
- CAS v7.5+/v8-era content is new matter relative to USPTO provisional
  64/037,173 and needs its own filing or inclusion in the utility conversion
  (deadline ~2027-04-13).

## Rebuilding

```bash
cd docs/whitepapers/tex
pdflatex -interaction=nonstopmode -output-directory=build RESEARCH_PAPER_<NAME>_v0.2.tex
```

Run three passes for the table of contents and cross-references.
