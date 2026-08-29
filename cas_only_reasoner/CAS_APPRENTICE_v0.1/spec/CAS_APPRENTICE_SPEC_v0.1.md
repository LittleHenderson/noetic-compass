# CCB-A1: the Cognitive Apprenticeship and Teaching Board v0.1

**Status:** the domain-general teaching pipeline per
CAS_TEACHING_ARCHITECTURE_v0.1.md. (The directive's "CCB-T1" label
collides with the existing Tool Board; this board is CCB-A1.)

## The law

The teacher may propose knowledge and skill. The CNCM decides what
becomes part of itself. The teacher is a FACULTY, not an oracle.

## What is implemented (v0.1)

- **TeachingEpisode sealing** (apprentice/board.py): every lesson -
  promoted, rejected, or refused - is a sealed episode with teacher
  identity + revision + role, examiner identity, outcome, pre/post
  capability, provenance, rollback pointer, digest.
- **The never-autonomous guard**: nine constitutional targets
  (authority contract, sole-writer rule, proof checker, trace
  verifier, protected benchmarks, constitutional values, deployment
  permissions, rollback machinery, the definition of improvement)
  refuse promotion with a typed error and a sealed refusal episode.
- **The faculty-committee rule**: high-impact domains
  (world_knowledge, research_method, board_design, self_improvement)
  reject lessons whose only examiner is the proposer.
- **The world-knowledge channel** (apprentice/knowledge.py): the
  stricter fact protocol - model facts enter PROPOSED never VERIFIED;
  trusted-source attestation upgrades to VERIFIED, contradiction
  rejects, mixed evidence stores CONTESTED; changing facts demand
  current-retrieval provenance AND a validity window; hard boundaries
  never enter through teaching; typed destinations per knowledge
  type.
- **Teaching metrics**: learning gain, transfer rate, teaching
  efficiency, retention, teacher dependence, false-lesson rate.
- **The live teacher harness** (live_teacher.py): a real local model
  authors a LanguageLessonPacket; the CCB-L1 acceptance ladder is the
  examiner; held-out cases come from the student's protected channel;
  the sealed artifact records the verdict either way.

## Verifier channels by domain (routing)

    language grammar   -> the CCB-L1 ten-stage ladder (exists)
    mathematics        -> the CCB-M1 exact checker + lessons (exists)
    reasoning strategy -> the RLP acceptance law (exists)
    world knowledge    -> the trusted-source protocol (this board)
    tool use           -> CCB-T1 typed intents (channel open)
    board design       -> foundry DRC + fault suites (open)

## Open

Live teacher lessons across the other domains; the critic/adversary
roles live (two-model committee); SDG expansion channel; CAS-Ohm
before/after capability profiles attached to every episode;
retrieval-linked knowledge store beyond the v0.1 dict.
