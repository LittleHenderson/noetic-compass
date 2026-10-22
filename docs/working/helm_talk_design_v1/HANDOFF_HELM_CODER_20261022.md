# HANDOFF — "helm coder" (Claude Managed Agent) — HELM talking like a person, 2026-10-22

Written by the laptop Claude Code session for the owner's new cloud agent. Read this whole file first, then the
"read first" list. Everything here is checkable in the repo; numbers are exact.

## 0. Who and what

- **Owner:** Little Henderson (Wakil). Writes nothing: his clicks and words are his approvals; you record them verbatim.
- **Repo:** `github.com/LittleHenderson/noetic-compass`. **Branch:** `claude/helm-talk-build-20261022`.
  **PR #459** targets `claude/project-thread-pmbzd6` (NOT `master`; master has no spec sheet).
- **Project:** HELM, a chat system whose own translator, the **CTT** (CAS-token transformer, 9,585,566 parameters,
  shared English + CAS vocabulary), should talk like a person. The **ear** reads English into CAS; the **mouth** writes
  English from CAS. CAS = the Cognitive Architecture System (10 Noetics × 4 domains = 40 states; see CLAUDE.md).

## 1. Read first (in this order)

1. `CLAUDE.md` (repo root) — project rules, canonical Noetic definitions (verbatim, never paraphrase).
2. `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` — before any CAS wording.
3. `docs/CAS_HARNESS_SPEC_SHEET.md` §7.126, §7.127, §7.128 and the top of §11 CHANGE LOG — the living record.
4. `CHANGELOG.md` top entries (2026-10-22).
5. `docs/working/helm_talk_design_v1/`: amendments `AMENDMENT_A_TALK_1.md` … `AMENDMENT_A_TALK_11.md` (append-only,
   each fingerprinted in a `.sha256`), `PLAN_MOUTH_V2.md`.

## 2. Where things stand (claim status words from the spec sheet legend)

| Piece | State | Where |
|---|---|---|
| Talk layer v1 (templates, OFF by default) | `ENGINEERED-NOT-VALIDATED` | spec §7.127; `helm_talk.py` |
| Mouth v1 (job c59, 1.29 USD) | 🟥 `MOUTH_HARMED` (1 DEV line glued "40 40" → "4040"); fallback 41/1,076, round trip 512/761, VARIED 59/100 missed; ear gates ✅; SOUNDS-HUMAN 682/989 ✅ (facts win ~9/10, chat loses) | `mouth_v1/run_c59/RUN_RECORD_MOUTH_TRAIN_C59_20261022.md` |
| Mouth v2 | data BUILT, 95 % writable gate ✅ in every situation; laptop smoke running at hand-over; NOT sealed, NOT trained | `mouth_v2/` |
| Accepted CTT | c57 (CUBE TRAIN) finals; c59 weights are a rejected side branch | spec §7.125 / §7.128 |

### Mouth v2 in numbers (all from `mouth_v2/package_source/data/DATA_MANIFEST_MOUTH.json` and `llm/MOUTH_LESSONS_RECORD_V2.json`)
- Corpus (owner's request, A-TALK-7 H4): 37 vocabulary lists (3 reading levels ~700 words, 3 larger level lists
  1,202 / 1,315 / 1,916, 30 professions × 25, 188 irregular forms), each written by one AI family and kept by another.
  10 styles (plain, warm, formal, casual, barbershop, intimate, curious, jovial, storyteller, professional), 3 levels
  (grade5, grade10, college), story form. 4,725 lesson inputs; 453 held-out exam person lines.
- Replies by anthropic (Claude helper agents, file mode), openai (Codex CLI), deepseek (API); every kept reply passed
  the rule check and two other-family checks with none failing. **12,418 AI-written lessons kept** (v1: 3,029).
- Train 11,530 · DEV 2,097 · dropped (lock cannot write) 170 · exam 1,517 · ear lessons 5,306.
- Writable under the lock: ANSWER 0.9949, SAYBACK 0.9984, ASK 0.9918, OFF 0.9795, SMALL 0.9969, SELF 0.9864,
  WORLD 0.9957 (gate ≥ 0.95).
- Owner rulings built in: Q1 (a) the ear learns the mouth's own sentences; Q2 ASK scored on thing/value/month;
  A-TALK-8 the corpus chat lines teach the ear "nothing to save"; **A-TALK-11 HELM may hold opinions** (owner: "HELM
  NEED OPINIONS JUST AS IT NEEDS FACTS"); still blocked: made-up facts and "you should" advice.
- Guard: whole-word lock (never a name / number / month the input lacks; numbers are single locked units), sense
  check layer 1 (no word twice in a row, no content word 3+ times) and layer 2 (the mouth's own confidence ≥ −0.607,
  frozen from `mouth_v2/SENSE_LAYER2_CENSUS.json`).

## 3. What is left, in order

1. Finish the laptop smoke (laptop only) → seal: `python -X utf8 -B mouth_v2/seal_mouth.py <out>` (needs the c57
   weights in `mouth_v2/package_source/weights/`, which are NOT in git — laptop only).
2. Spec sheet §7.128 + CHANGELOG entry for the v2 seal (same commit), A-TALK-10 / -11 fingerprints are in.
3. AWS job (laptop only; owner click required, cap 3 USD; expected ~1.4 USD): controller made from c59's by checked
   substitution as job `c60`; ledger hold; watchdog; launch; download; three-way cleanup check; ledger closeout.
4. Read the host reading; run the blind raters (`mouth_v2/rate_mouth.py`); record the word with colour marks; never
   delete a negative.
5. **After v2 (owner order):** CAS fully in the CTT — all 10 Noetics, 40 states — used by ear and mouth; HELM's
   opinions grounded in `^2` Positive / `^3` Negative. First hazard: AI label agreement passed only for `^1`
   (2026-10-07 trial), so trustworthy per-Noetic labels come first.
6. Housekeeping: PR #459 is clean against `claude/project-thread-pmbzd6`.

## 4. What a cloud agent can and cannot do here

- **Can:** read and change code and docs on the branch; write tests; review; plan the full-CAS step; design exams;
  write amendments (owner's words verbatim); open PRs.
- **Cannot (lives only on the owner's laptop):** the CTT weights; `C:\Users\wakil\Documents\Codex\...` (AWS
  controllers, the money ledger `AWS_COMBINED_ALLOCATION_CURRENT.json`); `D:/tksCAS-archive` backups; AWS keys
  (`~/.aws`) and AI-company keys (`~/.cas_llm_keys.env`). Never ask for keys in chat; never commit a secret.
- Coordinate with the laptop session through the repo (commit notes / PR comments) — never by editing the same files
  at the same time.

## 5. House rules (non-negotiable)

- **Plain English, always:** meaning first, define jargon on first use, short sentences, exact literals in backticks.
  End every update with `🎉WHAT IS CURRENTLY HAPPENING:` / `🎁FOR WAKIL TO DO:` / `🚀NEXT:` (none blank). Mark
  results ✅🟩🟨🟧🟥⬜🔧🔒 (✅ only with an unfakeable floor).
- **Money:** ask before any spend; the owner's click is the approval; record it verbatim. Heavy/neural work on AWS GPU,
  never on a laptop CPU.
- **Research discipline:** amendment before code; tests before code; a failed hard gate is a FAILURE; Claude is not the
  research governor (no self-approved replacement hypotheses or promotions); never re-read sealed exam content.
- **Record:** update the spec sheet in the same commit as any result; never delete a negative; add a dated change-log
  row; update CHANGELOG.md.
- **HELM content:** HELM may have opinions; never invent facts; canonical Noetic names and definitions verbatim.
- **Git:** commit as `LittleHenderson <wakillorenzo@gmail.com>` with the trailer
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push after every commit; never force-push; docs PRs target
  the thread branch.
- **Do not flag** patent application 64/037,173 as suspect (it is real).
