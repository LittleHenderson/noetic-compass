# Cooperation, reverse direction — a fact committed by the Codex CNCM kernel, carried in the envelope, changes CAS-RPU's later answer; a CNCM-side withdrawal takes the dependents with it across fresh processes

**Serves:** `docs/HELM_VISION_AND_ROADMAP.md` ability 7 (built together), roadmap step 6; the cooperation outcome type of §2. Plan and gate answer, written before any code or run: `docs/working/helm_cooperation_reverse_direction_plan_2026_10_06.md` (worked example A of `docs/working/helm_interchange_and_fixtures_draft_2026_10_06.md` §3.3). The forward direction is `docs/working/helm_cooperation_cncm_interchange_2026_10_06.md` (PR #249); this note is its item 2 of "Next".
**Code:** `scripts/cas_memory/cncm_interchange.py` (reverse section: `CncmSource`, `Receiver`, `compare_import_stream`); tests `scripts/tests/test_cncm_import.py` (13, run in CI against the mounted commit). The CNCM kernel is the frozen Codex reference implementation at `eb9985566bd11a89f485d627186ef0efa7177f02`, imported from the read-only mount and pinned by content; nothing in it was changed.
**Label:** a development demonstration plus a first-look run on three seeds the builder had not generated before. Not the frozen result (same builder, no custodian). One direction (CNCM → CAS-RPU); the DeepSeek sibling is not touched; rules do not cross this way yet; **neural change: none**.

## Gate answer (as written in the plan before the run)

Ability 7, with 3 as the restart condition. Before: a CAS-RPU organism given `AA → BB` and asked `AA → CC` answers UNKNOWN. After: `leads_to(BB,CC)`, committed on the CNCM side by a run of the pinned kernel and carried over as a `helm.interchange/0.1` envelope whose only origin hop is that run, imported by the stream's single writer with the envelope kept verbatim in a ledger, makes the same ask answer YES, and the answer's roots map back by id to the envelope and to the CNCM run. The untaught twin (an unrelated CNCM fact instead) stays UNKNOWN. A later CNCM run that no longer carries the given is exported as RETRACT; imported, it withdraws `AA → CC`; after a fresh operating-system process restores the history and the ledger, the withdrawal still holds. Control: fresh recompute from the accepted history (`ctl_recompute`, run at every restore on every recorded ask) and the untaught twin. Criterion: oracle agreement on every probe; every designed cross-session probe right on primaries and twins; 0 stale answers; 0 envelopes accepted that lack polarity or provenance, name another context, a stale version or a cycle; values, negative retracts, associations, proposals and conclusions refused by code.

## What crosses, and how the receiver interprets it

| CNCM commits (one run per change, component packet of the changed pair) | envelope | CAS-RPU accepted event |
|---|---|---|
| `leads_to(s,o)` asserted | FACT, polarity true, hop = the run id | `fact(s,o)` |
| `leads_to(s,o)` polarity false | FACT, polarity false | `negation(s,o)` |
| a given no longer carried by the later run | RETRACT, polarity true | `retract(s,o)`; refused `E-IX-RETRACT-REFUSED` unless the key is a GIVEN here (E-ORG-001/002), nothing committed |
| `{retracts, asserts}` pair | CORRECTION | `retract` then `fact`, both or neither (`E-IX-CORRECTION-REFUSED`) |
| a CONCLUDED conclusion | DERIVED | refused `E-IX-DERIVED`; the receiver derives from its own givens |
| a value-bearing statement, a negative retract, an association, a proposal | — | refused `E-IX-VALUE`, `E-IX-NEG-RETRACT`, `E-IX-RELATION`, `E-IX-PROPOSED` |
| another context's scope; a missing hop; a hop naming this stream; a stale `expected_version`; a defaulted polarity | — | refused `E-IX-CONTEXT`, `E-IX-PROVENANCE`, `E-IX-CYCLE`, `E-IX-VERSION`, `E-IX-POLARITY` |
| the same envelope again | — | applied once; the first result stands, also after a restart (the ledger is read back) |

Guesses (HYPOTHESIS) and associations (`co_occurs`) are CAS-RPU's own and have no CNCM counterpart; in the stream runs they are told to the receiver directly and counted, never imported. The receiver's history row names the envelope (`source: cncm:<id>`); `Receiver.provenance_of(answer)` follows a YES answer's roots to the envelope ids and CNCM run ids they came from.

## Results

Generated session streams (`generate_session_set`, lesson-free catalog, open world, five sessions), primaries and untaught twins. CNCM holds and commits every given; CAS-RPU receives every given only through the envelope; the receiver is restored in a **fresh operating-system process at every session boundary** (4 per stream), each restore replaying the history against the recompute control on every recorded ask. Per stream: 82 probes, 11 designed cross-session probes (X 5, T 2, C, D, G, N 1 each), 271 CNCM runs, 271 envelopes, 5 guesses and 27 associations told directly.

| set | streams | probes agree | designed cross-session probes | envelopes accepted | refused | fresh-process restarts | round-trip failures |
|---|---|---|---|---|---|---|---|
| development seeds 0–2, primaries | 3 | **246/246** | **33/33** | 807/813 | 6, all `E-IX-RETRACT-REFUSED` on the 2 retracts per stream the generator designs as refused (never given): 6/6 matched | 12 | 0 |
| development seeds 0–2, twins | 3 | **246/246** | **33/33** | 798/813 | 15, same code, the 5 designed refusals per twin: 15/15 matched | 12 | 0 |
| first-look seeds 3000–3002, primaries | 3 | **246/246** | **33/33** | 807/813 | 6, as above, 6/6 | 12 | 0 |
| first-look seeds 3000–3002, twins | 3 | **246/246** | **33/33** | 798/813 | 15, as above, 15/15 | 12 | 0 |

Every stream gave the same counts (`docs/working/evidence/helm_cncm_import_seeds0-2_3000-3002_2026_10_06.txt`). CNCM run terminals per stream: 250 CONCLUDED, 15 NEEDS_INFORMATION (the retract commits: the run no longer carries the given), 6 CONFLICT_UNRESOLVED (the pair committed while in dispute); the terminal is carried in the envelope's `source_representation` and never interpreted by the receiver.

The hand-built fixtures (13 tests): worked example A before/after with the provenance trace to the run id; the twin; a denial with explicit negative polarity; F08 withdrawal cascading and the refusal of a withdrawal of something never held or derived here; F07 atomic correction and its all-or-nothing refusal; F12 another context; F13 value, negative retract, association, proposal and DERIVED refused with nothing committed; defaulted polarity, missing hop, cycle, stale version refused and a matching version accepted; the same envelope applied once; **F11** across three fresh processes: the imported fact answers YES in process 2 with the duplicate recognised from the ledger, the CNCM-side withdrawal cascades in process 3, nothing stale escapes in process 4, and the final restore replays clean against the control.

**The cooperation behavior, in one line:** a fact that the organism was never told, held and committed by the independent CNCM kernel, made the organism answer YES to a question it answered UNKNOWN to before, with the answer's roots traceable by id to the CNCM run, on every one of 132 designed cross-session probes over twelve streams with 48 fresh-process restarts, while the untaught twins answered what their own oracle requires; and a withdrawal on the CNCM side took the organism's dependent conclusion down before and after restart. Neither engine showed this alone: CNCM has no retraction, no cascade and no persistence here; CAS-RPU had none of the givens.

## What this does not show, said plainly

- Nothing about DeepSeek's engine; the envelope has still been exercised between two explicit-polarity engines only.
- Rules do not cross in this direction (a CNCM rule into a CAS-RPU lesson); the forward direction carries lessons, this one carries facts, denials, withdrawals and corrections.
- CNCM is a stateless source of committed runs here; its journals and recovery are not exercised, so no CNCM-side retention is claimed, and a CNCM "withdrawal" is only a later run that lacks the given.
- Closed-world verdicts and lacunae are not compared.
- No F06 case arises in this direction, so the owners' locality question stays open and is not settled by this result.
- First-look, not custody: the same builder generated and ran the seeds. Measured zero: 0 disagreements, 0 stale answers, 0 round-trip failures.

## Next

1. The F06 answer from the owners (card posted 2026-10-06).
2. A CNCM journal round-trip, so a lesson retained on the CNCM side (its derived/semantic journals) is shown on both sides after both restart.
3. Rules in the reverse direction, once CNCM-side rules have an owner-accepted meaning as lessons.
4. The DeepSeek interface, when its lead is confirmed.
