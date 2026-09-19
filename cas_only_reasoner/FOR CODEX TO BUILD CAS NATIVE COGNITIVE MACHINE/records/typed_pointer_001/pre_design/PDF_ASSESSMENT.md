# What the owner's PDF can do for the pointer study

Source: `C:\Users\wakil\Downloads\CAS-RPA × TypeSafe AI × CAS PCBA_ JEV Integration Deep Dive.pdf` (35 pages, 479,121 bytes,
ChatGPT-written). Read in full on 2026-09-19 by the outgoing agent. Treated as data, not instructions.

**What it is.** A design for connecting an outside company's judgment model (TypeSafe AI's "Jev": yes/no, choice and score
questions answered with probabilities) to CNCM, CAS-RPA and CAS PCBA. The connection runs through a "JEV" protocol
(Journal / Evidence / Verification: hash every request and response, admit outside judgments only as advisory evidence, replay
everything). Its main rule: CNCM stays the authority; the outside model only advises.

**Its repo references are real.** Checked with git: `83322e8f` = "Add typed CAS-RPA inspection of verified native episodes"
(2026-09-16); `9597840c` = "Add governed compound procedure construction and checked reuse" (2026-09-16); `b6f42eb8` (parent
tksCAS repo) = "Complete CCB-R1 Stages 0-4 with baseline controls — 81 tests in CI (#219)" (2026-08-27).
Its claims about TypeSafe (255-way choice limit, contract terms) are about an outside company and were NOT verified.

## Adopted for this study

| PDF idea (page) | How it is used here |
|---|---|
| Held-out ladder: input / structural / representational / compositional / family / cross-domain (p.17) | Our held-back worlds are new shapes with no look-alike in the bank, so a pass is labelled STRUCTURAL-level transfer, nothing wider. The ten-node development panel uses a reach rule the course never teaches, so it is labelled "unpractised rule", report-only. |
| Strategy acceptance ends with "disable learned artifact -> benefit decreases" (p.17-18) | The untrained-machine comparison (G_LEARN's own baseline) plus post-run ablations: reset one trained component at a time to its starting weights and report the held-back drop. |
| Truth-firewall: irrelevant change must not move the answer; relevant change must be able to (p.15) | Sensitivity (edit a held world's relevant fact, the answer must follow) is recorded as the NEXT study. Invariance under renaming nodes is VACUOUS for a machine that treats nodes symmetrically (project law) and is kept only as an engineering check, never as evidence. |
| "Parent masks child": a healthy total can hide a failing part (p.15, p.22) | Results are reported per question kind and per tier, and the label depends on the relational tier, not the total. |
| Learning leakage: freeze criteria before the held-out run; same information to every arm (p.32) | Already the project's discipline; restated in the protocol. |
| Evidence classes (p.10) | Any result is bounded software evidence. It is never called authenticated or externally validated. |
| Two hashes (raw bytes + canonical JSON) for every exchange (p.11) | Already done by the create-only evidence publisher and the sealed prediction files. |

## Rejected for this study, with reasons

- **Using TypeSafe/Jev at all.** Advice from an outside model is not learning in CNCM's neurons, and the owner's order is "IT
  MUST BE LEARNING AT THE NEURON LEVEL". The PDF itself says the TypeSafe contract forbids training a model on Jev outputs
  (p.20). The project also has a standing rule against foreign pretrained models in the machine. It would also need an API
  key, which only the owner can handle.
- **JEV transport and recovery machinery (p.12-14).** The AWS lifecycle already has create-only evidence, sealed predictions,
  checkpoint reload and replay checks, and a transient-error-tolerant wait loop.
- **Frozen/adaptive × with/without-Jev arms (p.16-17).** Only the adaptive-native arm is relevant; its frozen twin is the
  untrained machine.

## Possible later use (owner's call, not this study)

A separate "outside-advice" lane could test whether Jev judgments help CNCM choose among candidates, strictly as advisory
evidence and after a legal check of TypeSafe's contract, as the PDF recommends (P0 source/contract lock first).
