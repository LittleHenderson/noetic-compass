# Lessons — the first run on ability 2 (a told rule, retained, applied to unfamiliar instances)

**Serves:** `docs/HELM_VISION_AND_ROADMAP.md` ability 2 (learns), roadmap step 5; ability 3 (the lesson survives restart); contract `docs/working/revision_streams_contract_2026_10_06.md` §13; plan `docs/working/helm_eval_plan_draft_2026_10_06.md` §4.6a.
**Code:** `scripts/cas_rpu/events.py` (`lesson`, `unlesson`), `revision.py` (oracle views), `controls.py`, `organism.py` (`_entail`), `sessions.py` (`lessons=True`, class L), `session_harness.py` (`--lessons`). Tests: `test_cas_rpu_lessons.py` (9), `test_cas_rpu_sessions.py` (42).
**Label:** a development demonstration and a first-look run on seeds the builder had not generated before. Not the frozen result. **Neural change: none** — the organism is symbolic; a lesson is one FACT row in the history document and no parameter exists to change.

## Gate answer (written before the runs; contract §13)

Ability 2. Before: a chain whose only route runs through an edge of a foreign relation (`s -[rel_a]-> u -[leads_to]-> t`) answers UNKNOWN and names `s|leads_to|u` as the gap. After the lesson "`rel_a` entails `leads_to`" is accepted, the same ask answers YES; in a later fresh process, on tokens never seen when the lesson was taught, the same lesson yields YES; the untaught twin (identical stream, the lesson replaced by an unrelated fact) stays UNKNOWN / NO. Control: fresh recompute from the log under §13. Criterion: zero verdict disagreements on every L probe in both worlds; untaught twins 100% GAP; zero stale record hits; withdrawn exact when the lesson or an entailed edge is retracted. Not shown: a lesson induced from examples (it is told), lessons in open English, any neural change.

## What a lesson is here, and what it is not

A lesson is a given: `FACT entails (r, leads_to)`. While it is held, the organism lands `s|leads_to|o` as a DERIVED record for every `s -[r]-> o` edge, with support `(s|r|o, r|entails|leads_to)`. Everything after that is the machinery that already existed: `^8` walks, `^6` finds the link present, the conclusion carries the lesson among its roots, `Workspace.retract` cascades when the edge or the lesson goes, a denial of the twin's pair makes a contradiction, `RETRACT leads_to` of the twin is refused as derived (E-ORG-001), and the record-first dependency check walks to the lesson. It is told, retractable, specific to its relation, and it survives restart because it is a row in the stream. It is not induced from examples, not expressed in English, and not a weight.

## What was run

| run | seeds | sessions | paths | worlds | twins | faults | shape per seed |
|---|---|---|---|---|---|---|---|
| **first-look** | 3000–3019 (never generated before the run) | 5 | recompute, walk, record_dep, record_rpa | open, closed | yes | none | 34 episodes, 501 events, 110 probes; 7 L episodes |
| faults with lessons | 0–9 | 5 | walk, record_dep | open, closed | no | one per seed | same |

Registered lesson fingerprints (seeds 0–19, twins on): open `4ba1ddd5003f5f85f884ac46bd9b16b6d56bf1bfe67a22da8abf3154ec6f6acf`, closed `e66b92c93c27ed02f99d06009a58c66c5b44f11fd9188857120f4598eb7bf455`. The lesson-free fingerprints (`9e0d35b0…`, `deae82a0…`) are unchanged: `lessons=True` is opt-in and draws the L episodes after every other episode.

The seven L variants and their designed sequences (GAP = UNKNOWN open / NO closed; `*` the designed probe): L-before [GAP, GAP, YES*, YES] — ask, boundary, ask, lesson, ask, boundary, ask; L-apply [YES, GAP, YES*, GAP] — lesson and one taught instance, then a fresh instance two sessions later; L-compose [YES, GAP, YES*, GAP] — two foreign edges in one chain, a plain edge appended later; L-retract [YES, GAP*, YES, GAP] — unlesson across a boundary, withdrawn required; L-revive [YES, GAP, YES*, YES, GAP]; L-specific [YES, GAP*, YES] — a lesson for `r1` does nothing for `r2`; L-edge [YES, GAP, GAP*, YES] — the edge retracted, the twin's retract refused, the lesson still applying elsewhere.

## Results — first-look run, seeds 3000–3019

Seeds 3000–3019, never generated before the run (a first attempt stopped in its last path when the container's disk filled with finished stores — E-MEM-051, reported in commit `c89f37a` — and the run was repeated in full after the harness was made to delete each finished store; the seeds were not inspected between the attempts). Fingerprints: open `9f248425f6203ce2…`, closed `7cd0a5c28622e715…`. 40 streams per world (20 primaries + 20 untaught twins), 110 probes per stream, 4400 probes per path per world; 200 fresh processes per path per world, **1200 process launches in all**, plus the in-process recompute control. Both worlds gave identical counts in every column. Text report: `docs/working/evidence/helm_lessons_firstlook_seeds3000-3019_2026_10_06.txt`; the full JSON (scratchpad only) has SHA-256 `18079ada73ac58382e1238cf33bf1050668e86f4ebb6a7e3532f352fcef02ef4`.

| path | verdict | contested | named (open) | withdrawn | **lesson probes (class L designed)** | lesson probes from the record | retention probes (all cross-session) | stale hits | untaught twins, all designed | **untaught twins, L designed** |
|---|---|---|---|---|---|---|---|---|---|---|
| recompute (P0) | 4400/4400 | 200/200 | 2360/2360 | 960/960 | 140/140 | 0 | 320/320 | 0 | 680/680 GAP | 140/140 GAP |
| walk (P1) | 4400/4400 | 200/200 | 2360/2360 | 960/960 | 140/140 | 0 | 320/320 | 0 | 680/680 GAP | 140/140 GAP |
| **record_dep (P2)** | 4400/4400 | 200/200 | 2360/2360 | 960/960 | **140/140** | 0 | 320/320, 40 from the record | **0** | 680/680 GAP | **140/140 GAP** |
| record_rpa (P3) | 4400/4400 | 200/200 | 2360/2360 | 960/960 | 140/140 | 0 | 320/320, 40 from the record | 0 | 680/680 GAP | 140/140 GAP |

Per variant, every path: L-before 20/20, L-apply 20/20, L-compose 20/20, L-retract 20/20, L-revive 20/20, L-specific 20/20, L-edge 20/20; the same seven at 20/20 GAP in the twins. T-compose 20/20 by reasoning (0 record hits), T-exact 20/20 from the record (20 hits) as before.

In the directive's words: **what did it learn** — the told rule, applied where it could not answer before (L-before: GAP then YES on the same ask); **did it keep it after restarting** — yes, in fresh processes two sessions later on tokens it had never seen when taught (L-apply 20/20), and a retracted lesson stayed retracted across restarts (L-retract 20/20, withdrawn exact 960/960); **can it use it when the example changes** — yes within the narrow sense the family defines: new instances and compositions of the same rule (L-apply, L-compose), not a different rule; a lesson for one relation did nothing for another (L-specific 20/20) and the untaught twin never gained the ability (140/140 GAP). No lesson probe was served from the record on any path: each is a first ask of a fresh instance or a re-ask after a mutation, so a record hit would have been a stale hit, and there were none. Neural change: none.

Costs (open world): commit p50 10.8 ms, p95 18.9 ms (the stream is 501 events, so the document rewritten per commit is larger than before); restore p50 72 / 68 / 151 ms (walk / record_dep / record_rpa), max 153 / 173 / 760 ms; process start p50 52 / 49 / 231 ms; session wall p50 1.37 / 1.37 / 1.83 s; max RSS 74 / 117 / 159 MB; largest store 55 MB with retained copies. The RPA path again changed no answer and cost the most restore time.

## Results — fault schedule with lessons, seeds 0–9

Seeds 0–9 (development), `lessons=True`, one fault per seed (kinds rotating: the four commit-boundary kills, kill-during-restore, redeliver, redeliver-after-restart, swap, torn-current, corrupt-current), walk and record_dep, both worlds, no twins. Both worlds gave identical counts.

| path | verdict | contested | named (open) | withdrawn | lesson probes (L designed) | retention probes | stale hits | fault checks |
|---|---|---|---|---|---|---|---|---|
| walk | 1100/1100 | 50/50 | 450/450 | 240/240 | 70/70 (10/10 on each of the 7 variants) | 160/160 | 0 | recovery 4/4; redeliver, redeliver-restart, swap, torn-current, corrupt-current 1/1 each |
| record_dep | 1100/1100 | 50/50 | 450/450 | 240/240 | 70/70, 0 from the record | 160/160, 20 from the record | 0 | same |

Every recovery restored exactly the acknowledged prefix (or one ahead with the retry recognised), with lesson-derived records replayed identically (the restore compares every recorded outcome; none differed). No L designed probe was served from the record in either path: the lesson probes are first asks of fresh instances or re-asks after a mutation, so a record hit would be a stale hit, and there were none.

## What this does and does not show

- **Shown (bounded by the control that lacks the mechanism):** on this family the organism with a held lesson agrees with fresh recompute on every probe; the lesson changes answers it could not give before; it is retained across fresh processes and applied to instances and compositions never seen when it was taught; its retraction withdraws exactly what rested on it, before and after restart; the untaught twin never gains the ability. Relative to the organism without the lesson (the twin), the lesson is the difference; "necessary" and "superior" are not said.
- **Not shown:** induction (the lesson is told); any lesson other than "`r` entails `leads_to`"; open English; independence from the builder (same generator, same builder, first-look not custody); level (b) survival; any neural outcome — **neural change is zero, measured as not applicable**, and no claim of neural growth is made.

## Next

1. A second lesson kind that is not a relation entailment (a composition rule or a recipe coefficient) to show the mechanism is not one special case — only if the owner wants ability 2 widened before ability 3's level (b).
2. The owner-side items unchanged: storage verification, replacement-machine run, custodian.
