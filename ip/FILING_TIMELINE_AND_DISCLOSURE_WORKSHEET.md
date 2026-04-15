# Filing Timeline and Public-Disclosure Worksheet

Prepared from the current workspace on 2026-04-12. This is an engineering/IP triage worksheet, not legal advice.

## Purpose

Use this document to brief patent counsel quickly on:

- what appears to be patentable in the implemented system
- where the earliest public disclosures may already exist
- which filing family is most defensible
- what still needs human confirmation before any filing

## Working Assumption

Treat the following as likely disclosure sources until counsel confirms otherwise:

- public website / hosted demo
- public GitHub remote
- published manuscripts and PDFs
- validation artifacts and benchmark summaries
- any public pitch deck, email, or demo shared without NDA

## Known Public Anchors

| Anchor | Concrete artifact / URL / path | Why it matters |
|---|---|---|
| Public website | `https://noetic-compass.vercel.app/` | Likely public disclosure channel for the Noetic Compass product and scoring UI |
| GitHub remote | `https://github.com/LittleHenderson/noetic-compass.git` | If public, the repo may disclose implementation details and dates |
| Public playground / demo | `https://predeploy-9fd3caf1-tks-overview-vgf9urqt.manus.space/playground` | Confirm whether it is still live and when it first became public |
| Main manuscript set | `TKS_v7_4_FULL_CORRECTED.pdf`, `TKS_v7_4_REFEREE_DEFENSIBLE (1).pdf` | Public or shareable PDFs may start disclosure clocks |
| Formal manual set | `TKS_FORMAL_MATHEMATICAL_MANUAL_v6.1_COMPLETE.pdf`, `TKS_FORMAL_MATHEMATICAL_MANUAL_v6.1_COMPLETE_FIXED.pdf` | Confirms formalization of the language / system |
| Cognitive framework | `TKS_FULL_Cognitive_Framework.tex`, `TKS_FULL_Cognitive_Framework_REFEREE_SAFE.pdf` | May contain broader theory claims that should be separated from patent claims |
| Validation artifacts | `noetic-compass-scaffold/noetic-compass/validation/` | Benchmark studies, evidence log, calibration sessions, protocol docs |

## Earliest Known Public Disclosures

Use this as a confirmation worksheet. Do not guess dates.

| Disclosure | Channel | Concrete artifact / URL / path | Likely date to confirm | Notes for counsel |
|---|---|---|---|---|
| Noetic Compass production site | Vercel public deployment | `https://noetic-compass.vercel.app/` | First live deploy date, first public index date, first demo date | If the site exposed scoring behavior, that may be a substantive disclosure |
| GitHub repository | Public repo if visible | `https://github.com/LittleHenderson/noetic-compass.git` | First public visibility / first push date | Confirm whether repo was ever private, forked, or mirrored |
| Public demo playground | Hosted playground | `https://predeploy-9fd3caf1-tks-overview-vgf9urqt.manus.space/playground` | First public availability date | Confirm whether it displayed compiler / notation behavior |
| TKS manuscript PDF | File distribution | `TKS_v7_4_FULL_CORRECTED.pdf` | First share date, first upload date, first public posting date | If shared outside NDA, may count as public disclosure |
| Referee manuscript PDF | File distribution | `TKS_v7_4_REFEREE_DEFENSIBLE (1).pdf` | First share date | Important because it is closer to the formal claim set |
| Formal manual PDF | File distribution | `TKS_FORMAL_MATHEMATICAL_MANUAL_v6.1_COMPLETE_FIXED.pdf` | First share date | Includes language/compiler claims and formalization language |
| Validation reports | Internal or shared artifacts | `validation/LATEST_PROVIDER_BENCHMARK_SUMMARY.md`, `validation/evidence_log.json`, `validation/studies/*.json` | First time shared externally | If shared publicly, they may be disclosures of operational details |

### Placeholder prompts for counsel to confirm

- What is the earliest date the public site could be accessed by someone outside the team?
- What is the earliest date the GitHub repo became visible outside the team?
- What is the earliest date any manuscript or PDF was emailed, uploaded, or posted without NDA?
- What is the earliest date a demo, screenshot, or benchmark result was shown to an outside party?
- Were any of the validation artifacts shared externally before filing consideration?

## Disclosure Channels To Inventory

Capture each channel separately. A single public artifact can be enough to start a clock.

- Public website and hosted app
- Public GitHub repository
- Public issue tracker / PR discussion
- PDF manuscripts, slide decks, docs, and exported reports
- Demo videos, screenshots, social posts, newsletters
- Email threads with no NDA
- Stakeholder meetings or investor pitches without confidentiality terms
- Conference talks, webinars, livestreams, or podcasts

## Artifact Inventory

Preserve a clean snapshot package for counsel:

- `PATENT_READINESS_MEMO.md`
- `ip/FILING_TIMELINE_AND_DISCLOSURE_WORKSHEET.md`
- `peer_review/README.md`
- `peer_review/SUBMISSION_CHECKLIST.md`
- `peer_review/TKS_v7_4_REFEREE_DEFENSIBLE_PEER_REVIEW.md`
- `peer_review/TKS_v7_4_FULL_CORRECTED_PEER_REVIEW_TRIAGE.md`
- `peer_review/VERIFICATION_NOTES.md`
- `pdf_review/TKS_FORMAL_MATHEMATICAL_MANUAL_v6.1_COMPLETE_FIXED.tex`
- `pdf_review/TKS_FORMAL_MATHEMATICAL_MANUAL_v6.1_COMPLETE_FIXED.pdf`
- `pdf_review/TKS_FULL_Cognitive_Framework_REFEREE_SAFE.tex`
- `pdf_review/TKS_FULL_Cognitive_Framework_REFEREE_SAFE.pdf`
- `noetic-compass-scaffold/noetic-compass/validation/VALIDATION_PROTOCOL.md`
- `noetic-compass-scaffold/noetic-compass/validation/LATEST_PROVIDER_BENCHMARK_SUMMARY.md`
- `noetic-compass-scaffold/noetic-compass/validation/evidence_log.json`
- `noetic-compass-scaffold/noetic-compass/validation/human_labels.json`
- `noetic-compass-scaffold/noetic-compass/validation/calibration_sessions.json`
- `noetic-compass-scaffold/noetic-compass/validation/studies/*.json`

## Filing-Family Decision Table

| Option | What it covers | Best use case | Risks / notes | Recommendation |
|---|---|---|---|---|
| Provisional patent | Early priority date, broad technical description | Fastest way to preserve rights while refining claims | Needs enough detail to support later non-provisional claims | Recommended first step |
| Non-provisional utility application | Formal claims and examination | When claim scope is stable and counsel is ready | Higher cost, narrower drafting tolerance | Second step after provisional unless already ready |
| PCT application | Preserves international filing options | If you expect foreign filing and need time | Costs more and does not itself grant rights | Consider if global commercialization is likely |
| Continuation / CIP | Extends claim strategy from a parent filing | If the system evolves after the first filing | Must be aligned with earlier disclosure and support | Consider only after the first filing family exists |
| Trade secret only | Keep implementation confidential | If a component is hard to reverse engineer | Does not protect against independent development | Use for select internal heuristics or operational details only |

### Practical recommendation

File first around the implemented technical system, not the theory:

1. Noetic Compass assessment / wrap pipeline
2. CAS-native architecture
3. CAS executable language / compiler toolchain

## Jurisdiction Risk Checklist

Counsel should confirm the exact filing posture for each jurisdiction you care about.

- United States: assess whether any public disclosure has already started the one-year grace clock
- Europe / EPO: assume no useful grace period unless counsel confirms a narrow exception
- United Kingdom: assume early public disclosure can be fatal for novelty
- Canada: confirm whether any grace-period exception applies and from what date
- China: treat pre-filing public disclosure as high risk
- Japan: confirm grace-period rules and documentary proof requirements
- Korea: confirm grace-period scope and timing
- PCT: useful for preserving optionality, but not a substitute for an early first filing

## Inventorship Checklist

Inventorship must be tied to the claims, not to who used the most AI tools.

- Identify every human who contributed to conception of each patentable feature
- Separate conception from implementation labor
- Exclude AI-generated text from inventorship unless a human made the inventive decision
- For each invention candidate, write down:
  - who conceived the core idea
  - who reduced it to practice
  - who selected the specific architecture or data flow
  - who chose the claim-critical parameters
- Confirm whether any coauthors, contractors, or advisors should be named
- Keep a dated invention log with versioned notes and screenshots

## Confidentiality / NDA Checklist

Before any further disclosure:

- mark counsel-facing drafts confidential
- use NDA or attorney-client privileged channels for outside review
- do not email full manuscripts to non-counsel recipients without checking terms
- keep access logs for shared drives, docs, and demo links
- verify whether any public website or repository exposes source, claims, or screenshots
- if a demo is needed, use a controlled access link with logging
- preserve evidence of who saw what and when

## Pre-Filing Do-Not-Do List

- do not publish new claim details on the public website
- do not post new manuscripts or PDFs without a disclosure review
- do not push additional invention-critical code to public repos until counsel reviews timing
- do not call the system "patent pending" until something has actually been filed
- do not assume a private belief about novelty is enough
- do not merge theory claims with patent claims in the same document
- do not rely on AI output as the sole source of legal drafting
- do not change inventor names retroactively without documentation

## Counsel Questions

Give counsel these questions up front:

1. Which filing family should be first: provisional, non-provisional, or PCT?
2. What is the earliest likely public disclosure date for each channel listed above?
3. Which technical subsystem is the strongest patent core:
   - Noetic Compass pipeline
   - CAS-native architecture
   - CAS compiler/toolchain
4. Which parts should be treated as trade secrets instead of disclosed in the filing?
5. Which claims are vulnerable to abstract-idea or mathematical-framework rejections?
6. What evidence should be preserved now to support enablement and reduction to practice?
7. What foreign filing deadlines are triggered by any known disclosure date?
8. Who are the proper inventors for each claim family?
9. Should the first filing be narrow and conservative, or broader with more fallback embodiments?
10. What exact public-disclosure cleanup should happen before any further stakeholder demos?

## Fast Counsel Packet

If you need to hand counsel one folder, include:

- this worksheet
- `PATENT_READINESS_MEMO.md`
- the best 1-2 product screenshots
- a short architecture diagram for Noetic Compass
- the latest validation summary
- one representative manuscript PDF
- a list of known public URLs and repo remotes

## Immediate Next Step

Confirm the earliest public dates for:

- `https://noetic-compass.vercel.app/`
- `https://github.com/LittleHenderson/noetic-compass.git`
- `https://predeploy-9fd3caf1-tks-overview-vgf9urqt.manus.space/playground`
- the first externally shared PDF or manuscript

Then have counsel decide whether to file a provisional first or to clean up disclosures before any additional public release.
