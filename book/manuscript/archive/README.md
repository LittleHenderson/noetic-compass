# `book/manuscript/archive/` — Preserved manuscript snapshots

This directory contains preserved versions of `FULL_MANUSCRIPT.md` from before major reformation passes. These are kept as easy-reference historical artifacts. Git history also preserves all versions automatically. Use these preservation copies when you want to open or share a pre-reformation version without navigating git commands.

## Standing pattern

**Before any major structural or reformation pass on a load-bearing document, a dated preservation copy goes into an archive folder.** Git preserves history by default, but explicit archive copies are cheaper to reference than `git show` commands, and they survive worktree moves and branch switches without requiring git knowledge from the reader.

The same pattern applies to other load-bearing documents, not just the book manuscript:
- Major revisions to `Noetic_Compass_Technical_Feature_Overview.docx` should preserve a dated pre-revision `.docx` in its own archive folder before the revised version is distributed.
- Other manuscript-class documents (peer-review paper, patent filing packages) that undergo significant structural revision should follow the same preserve-snapshot-before-revision pattern.

## Contents

### `FULL_MANUSCRIPT_pre_noetic_reformation_2026-04-19.md`

- **Snapshot of:** `book/manuscript/FULL_MANUSCRIPT.md`
- **Captured on:** 2026-04-19
- **Captured before:** Phase 2 Noetics Language Reformation (structural-not-emotional language pass per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`)
- **Encoding at snapshot:** UTF-16 LE with BOM (preserved exactly as it was before the reformation pass began; the subsequent reformation work converted the main file to UTF-8 and then applied structural-language revisions in place).
- **Byte size at snapshot:** 1,625,348 bytes
- **Content at snapshot:** 27 chapters + Appendices A–E, ~124,178 words, unchanged from commit `5eae335` (the only commit that touched the file at time of preservation).
- **How to read this file:** most modern editors handle UTF-16 LE transparently. If your tool shows each letter with a space between it (e.g., `T h e`), the tool is misinterpreting the UTF-16 byte sequence as ASCII. Convert to UTF-8 first:
  ```
  iconv -f UTF-16LE -t UTF-8 FULL_MANUSCRIPT_pre_noetic_reformation_2026-04-19.md > /tmp/preview.md
  ```

## Do not edit files in this directory

Preserved snapshots are read-only by policy. Any intended revision work targets the live file at `book/manuscript/FULL_MANUSCRIPT.md`, never these archive copies. If a preservation copy is updated or replaced, the old version is retained — snapshots accumulate; they do not overwrite each other.
