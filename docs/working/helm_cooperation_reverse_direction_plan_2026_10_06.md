# Cooperation, reverse direction — a fact and a retraction held by the Codex CNCM kernel, carried into CAS-RPU, changing its later answer (PLAN, not yet run)

**Serves:** `docs/HELM_VISION_AND_ROADMAP.md` ability 7 (built together), roadmap step 6; the cooperation outcome type of §2. Item 2 of the "Next" list in `docs/working/helm_cooperation_cncm_interchange_2026_10_06.md` (PR #249). Executes worked example A of `docs/working/helm_interchange_and_fixtures_draft_2026_10_06.md` §3.3 and fixtures F01, F07, F08, F11, F12, F13 in the CNCM → CAS-RPU direction.
**Status:** plan. Written before any code or run. Nothing here grants merge, push, run or credential authority. Preparation items are labelled preparation.
**Why this step now:** every other open roadmap item waits on something outside this repository (an independent custodian for the frozen retention run, a valid key for level (b), the R8B custody answer and AWS access for neural learning, a verified lead for DeepSeek). The pinned CNCM commit `eb99855` is in this repository and CI mounts it, so this behavior can be shown and tested here.

## 1. Gate answer (vision §3), written before the run

**Ability.** 7, with 3 as the restart condition (F11). Not 2, 4, 5 or 6.

**Behavior, before/after on a named input.** Before: a CAS-RPU organism given `AA -[leads_to]-> BB` and asked `AA → CC` answers GAP (open world). A CNCM run has committed `leads_to(BB,CC)` as an asserted fact with CNCM's own provenance (run id, source statement digest). After: that fact, exported from the CNCM run as a `helm.interchange/0.1` envelope whose `provenance.origin.hops` names the CNCM run, and imported by the CAS-RPU stream owner as its own accepted event with the envelope stored verbatim, makes the same ask answer YES with support `(AA|leads_to|BB, BB|leads_to|CC)` and an answer record whose dependency ids reach the CNCM event through the import. The untaught twin (the envelope replaced by an unrelated CNCM fact) stays GAP. Then a CNCM-side withdrawal of `leads_to(BB,CC)` (a later CNCM commit without it, or a semantic `RETRACT` statement with `previous_digest`) is exported as RETRACT, imported, and withdraws `AA|leads_to|CC` in CAS-RPU; after a fresh operating-system process restores the stream from its history, the withdrawal still holds and nothing is served stale.

**Control that lacks the mechanism.** Fresh recompute from CAS-RPU's accepted event history (`controls.ctl_recompute`), which has no import path and no CNCM state; and the untaught twin stream.

**Pass criterion and denominator.** On every probe of every stream (denominator: probes per stream, open world), the organism holding imported events agrees with the recompute oracle run over the same accepted history; on every designed import probe (denominator: import probes), the primary answers YES and the twin GAP; after the imported retraction (denominator: retraction probes) every dependent is withdrawn before and after restart, 0 stale record hits; 0 envelopes accepted that lack polarity, whose `context_id` does not match the stream, whose `expected_version` is not the last committed version, or whose hop list already names this stream (cycle). Envelopes with scalar values, negative retracts or associations are rejected with their E-IX code, never coerced (denominator: rejected envelopes, counted).

**What it will not show.** DeepSeek's engine; CNCM's own persistence beyond what the run and its semantic statements expose; closed-world verdicts or lacunae; any neural change (**neural change: none**); a custodian result (same builder).

## 2. What crosses, and how the receiver interprets it

| CNCM source | envelope | CAS-RPU accepted event | fixture |
|---|---|---|---|
| committed packet fact `leads_to(s,o)` polarity true, `evidence_status: asserted` | FACT, polarity true, hops = [cncm run] | `events.fact(s,o)` | F01 |
| committed packet fact `leads_to(s,o)` polarity false | FACT, polarity false | `events.negation(s,o)` | F02 |
| foreign predicate `r(s,o)` asserted | FACT, relation r | `events.fact(s,o,r)` | F09 (no rule crosses this way yet) |
| CONCLUDED conclusion `leads_to(s,o)` (derived in CNCM) | **not exported** as a FACT; exported as `DERIVED` with `evidence_status: derived` and rejected by the receiver (`E-IX-DERIVED`): a conclusion is re-derived by the receiver from its givens, never imported as a given | F10 analogue |
| fact present in run k, absent in run k+1 (RRK), or semantic `RETRACT` with `previous_digest` | RETRACT, polarity true | `events.retract(s,o)`; refused if the target is not a GIVEN in this stream (E-ORG-001/002 → `E-IX-RETRACT-REFUSED`) | F07, F08 |
| semantic `ASSERT` with `previous_digest` (correction) | CORRECTION `{retracts, asserts}`, atomic | `retract` then `fact`; the whole pair rejected if the retract is refused | F07 |
| any statement with a rational value | rejected `E-IX-VALUE` | none | F13 |
| CNCM `scope` ≠ stream `context_id` | rejected `E-IX-CONTEXT` | none | F12 |

Receiver steps are exactly worked example A steps 1–5: validate, duplicate and cycle check, append own accepted event with the hop list extended, `Organism.consume`, round-trip re-encode check. The envelope is stored verbatim beside the history row so the dependency chain can be followed back by id.

## 3. Measurement design

- **Hand-built stream (development):** worked example A, then F07 correction, F08 retraction with dependent, F11 restart, F12 same name different context, F13 rejections. Expected answers written in the test before the first run.
- **Generated streams:** for each lesson-free stream of `generate_session_set` (seeds 0–2 development, 3000–3002 first-look, open world), the CNCM side is a packet run per segment whose committed facts are exported; CAS-RPU consumes only imported envelopes plus the stream's asks; score against the oracle over the resulting accepted history. Twin streams substitute an unrelated fact for each designed import.
- **Restart:** the receiver stream is saved and restored in a fresh process (`history.Stream.save` / `restore_from`) between the retraction and its post-restart probe, as the multi-session harness already does.
- **Reported, never claimed:** import counts, rejections by code, record hits, and the F06 divergence if any packet conflict appears in this direction.

## 4. Preparation already done (not behavior)

- Branch `claude/helm-next-step-0tupzc` started from PR #249's head `d08026f`.
- The pinned commit `eb99855` mounted read-only at the path the adapter expects; the 12 existing interchange tests pass against it in this environment (12/12, 1.2 s).
- The mount carries the semantic and derived journals (`semantic_engine.py`, `derived_*`, `*_recovery.py`), so CNCM-side provenance with `previous_digest` is available for F07 without touching the mount.

## 5. Decisions taken at coding time (recorded here, not in the gate answer)

1. F06 meaning: card posted to the owner 2026-10-06; until answered the adapter keeps reporting it. No F06 case arose in this direction (CAS-RPU, the receiver, has route-local conflict semantics; CNCM's refusal status is carried in `source_representation` and not interpreted).
2. The import path lives in `scripts/cas_memory/cncm_interchange.py` beside the export path (one pin, one module); its tests are `scripts/tests/test_cncm_import.py`.
3. The work is stacked on PR #249's branch head `d08026f` as a separate draft PR.
4. What the CNCM side is: a `CncmSource` that holds the givens and commits every change by one run of the pinned kernel on the component packet of the changed pair (the run id is the provenance); guesses and associations are CAS-RPU's own and are told to the receiver directly, never imported (CNCM has neither). Rules do not cross in this direction yet.
5. Restart: the receiver's history document and the import ledger (`imports.jsonl`, envelopes verbatim with the stream's own event ids) are restored together; every restore replays against `ctl_recompute` on every recorded ask.

## Amendment log

- 2026-10-06 — created, before any code or run.
- 2026-10-06 — §5 rewritten from open questions to the decisions taken; §1 unchanged. Results: `docs/working/helm_cooperation_cncm_import_2026_10_06.md`.
