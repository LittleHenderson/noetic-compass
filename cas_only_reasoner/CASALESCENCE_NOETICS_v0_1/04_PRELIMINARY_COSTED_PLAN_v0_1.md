# 04 — Priced plan for the preliminary stages, version 0.1

> **HOLD on P3 and P4, added 2026-10-04 23:25 PDT.** Reading the pilot package showed that its Cause/Effect label has no bearing on the right answer (`05_FINDING_PILOT_GUIDANCE_COULD_NOT_HELP.md`). Rerunning that design with a fixed scorer would most likely show nothing again. P3 and P4 are not launched and no money is held for them. P1 and P2 are unaffected. The owner chooses option A, B or C in that note.

Owner approval on file: `OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json` ("OK YOU HAVE MY APPROVAL FOR IT ALL"). No dollar figure was named, so every cap below fits inside the money the ledger shows as unreserved. Nothing here releases a hold or raises a ceiling.

## Money available

| Fact | Value | Source |
|---|---:|---|
| Ledger pointer, combined | 87.15 of 100.00 | `C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`, read 2026-10-04 22:18 PDT |
| Unreserved | 12.85 | same |
| Inside the 87.15: hold for the finished op11 GPU job | 8.00 | its estimated real cost is about 3.0; not released (needs your order or the bill) |
| Codex operator ledger | 133.96 of 135.46 | separate book; not used by this plan |

Re-read the pointer before every launch. The other Claude session also adds small charges to it.

## Measured rates used for the estimates

- GPU job of 2026-10-04: 236 model calls took 6,247.3 seconds, so **26.5 seconds per call**. Host price **1.212 USD per hour**.
- The same job kept about 26 MB of raw evidence per call; download costs 0.09 USD per GB.
- Fixed time per GPU job (staging, setup, identity checks, packing, download, shutdown): about 22 minutes.
- Outside label team, first look: 40 passages used 94,108 input and 9,651 output tokens on `deepseek-chat`. I estimate under 10 cents; the provider's bill is the record.

## The stages, in order

| # | Stage | What runs | Where | Expected cost | Cap | Time limit |
|---|---|---|---|---:|---:|---|
| P0 | Label-agreement first look | 40 practice passages, three label teams | sub-agents + DeepSeek | under 0.10 | done | done 2026-10-04 |
| P1 | Scorer check | the 30 known examples against the new scorer, plus the package's software tests | AWS, one m6i.xlarge, no model | about 0.02 | 1.00 | 60 min |
| P2 | Label-agreement verdict | fresh passages by an outside writer; two label teams (one Claude, one DeepSeek); at least 50 passages per Noetic | outside service + sub-agents | under 0.50 | 2.00 | none (no host) |
| P3 (ON HOLD) | Practice run for model B | model B alone on about 120 fresh practice tasks, to keep tasks where it is right 30% to 70% of the time | AWS, one g5.2xlarge | about 1.9 | 4.00 | 2 h |
| P4 (ON HOLD) | Early Cause/Effect help-to-B check, exploratory size | 60 fresh final tasks, five groups (none, CAS, mixed-up CAS, ordinary help, same-length filler), saved reader as it is: about 380 calls | AWS, one g5.2xlarge | about 4.8 | 5.85 | 4 h |
| | **Total of caps** | | | | **12.85** | |

Every AWS job: one host, automatic shutdown at its time limit, a stated cap, a separate watchdog, and an independent cleanup check started at launch so it runs within minutes of shutdown.

## What P4 can and cannot show

Sixty tasks is **exploratory**. It can show whether the yardstick now works (no floor, no ceiling, formatting failures counted apart) and whether any group separates clearly. It cannot support a claim of a 10-point gain; that needs roughly 150 to 250 tasks, about 1,200 calls, about 15 USD, and more than one 4-hour job.

🔴 A.N. (only if P4 looks worth enlarging): the larger run does not fit in the unreserved 12.85. It needs either your order to convert the finished op11 hold (8.00) to its real cost, or the AWS bill for that job.

A cheaper route for the reviewer to consider: the pilot package re-checks the model weights three times in every call, which is most of the 26.5 seconds. Checking once at the start and once at the end of each group would cut the time several-fold. That is a change to the reviewed package, so it needs review; it is not assumed in the prices above.

## Who does what (proposed; correct any line)

| Role | Who | Separation |
|---|---|---|
| Owner | you | approves; receives 🔴 A.N. requests |
| Builder of the new package version (scorer, fresh marked tasks, practice mode) | Claude sub-agent | does not see final tasks' answers after they are sealed |
| Case writer for label passages | outside model (DeepSeek), plain brief with no CAS words | never sees the guide, the labels or a reader. Claude sub-agents cannot be blind here: the project instructions they receive contain the definitions. |
| Label team A | Claude sub-agent | reads the guide and passages only |
| Label team B | DeepSeek (`deepseek-chat`) | one passage per call; sees nothing else |
| Reviewer of plan and package | an outside model (DeepSeek reasoning model) plus one Claude sub-agent for code defects | reviewers do not edit what they review |
| Operator (AWS) | Claude Code, this session | runs only reviewed, frozen versions |
| Grader | the program | statuses come from program output |

Outside services checked on 2026-10-04 22:45 PDT with a one-word test: DeepSeek works. Gemini answers on `gemini-2.5-flash`; `gemini-3.1-pro-preview` says quota exceeded. Zhipu GLM says balance insufficient. Alibaba DashScope says the account is in arrears.

## What is sent outside

To DeepSeek: the labeling guide (which quotes the ten definitions and the sayings table) and the passages. No code, no keys, no results, no model data. If you do not want the definitions sent to an outside service, say so and the non-Claude team becomes Codex by hand-off instead.
