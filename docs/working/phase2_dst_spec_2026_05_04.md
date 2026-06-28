# Phase 2 — Dialogue State Tracker Specification

**Date:** 2026-05-04
**Status:** scaffold landed; full implementation tracked separately
**Phase:** Version B Phase 2 (Dialogue State Tracker + NL Generation Head)
**Sequencing:** Lands AFTER Phase 3 (free-form English) and AFTER vocab14 + Lever 3 retrain. Phase 2 is not "ready" until ~6-8 weeks from today.

---

## 1. Motivation — why DST > naive prompt-stitching

Single-turn structured prediction (the K=9 baseline at 93.2% canonical) is an *encoder* problem. It maps one user utterance to one CAS expression. A chat model is a *state* problem: every turn writes into and reads from a running representation that survives across turns. Naive prompt-stitching ("concatenate the dialog so far, ask for next CAS expression") ducks the state problem and inherits four failure modes:

1. **Repair amnesia.** "No wait, that's not right" must roll the prior CAS commitment back. Stitching has no notion of which commitment is being repaired.
2. **Move-type drift.** A model trained on `OPEN -> ANSWER` does not know when MIRROR (echo and confirm) is the right move; stitching can't gate move type because there's nothing in the stitched prompt that distinguishes "the model committed" from "the model paraphrased."
3. **Admissibility violations.** The K=9 architecture has no notion of which next move is *legal*. Without a grammar, the model can produce degenerate transitions (PLAN before ANSWER, ANSWER before MIRROR, etc.).
4. **Coherence loss.** The CAS expression at turn N must agree with turn N-1 up to a refinement; a stitched prompt has no mechanism to enforce this beyond what the LM happens to learn.

The Dialogue State Tracker (DST) solves all four with explicit machinery: a typed `DialogState`, a typed `Turn`, a 11-move grammar with admissibility relations gating every transition, and a repair strategy hierarchy that walks back the CAS state when the user vetoes.

The architectural framing matches the framework's mathematical posture (Correction 1: admissibility relations gate every operator transition; Correction 2: RPM is section-retraction, so walk-back is value restoration not inverse computation). DST is the conversational realization of those structural commitments.

---

## 2. The 11 turn types

| Turn type | Role | Carries CAS? | Mutates state? | Description |
|---|---|---|---|---|
| `OPEN` | user | no | no | User opens the conversation or pivots mid-stream |
| `ACK` | assistant | no | no | Short acknowledgement, no CAS commitment |
| `MIRROR` | assistant | yes | yes | Echoes the structural reading; invites confirmation |
| `CLARIFY` | assistant | no | no | Asks for refinement before committing |
| `EMPATHIZE` | assistant | no | no | Holds space, no CAS proposal |
| `ANSWER` | assistant | yes | yes | Commits to a CAS prediction |
| `PLAN` | assistant | yes | no | Proposes RPM-style pathway over current state |
| `REFUSE` | assistant | no | no | Declines due to admissibility / safety constraint |
| `REFUSE_CLAIM` | assistant | yes | yes | Rejects user CAS claim and proposes alternative |
| `REPAIR` | user | no | yes | User corrects prior assistant CAS reading |
| `CLOSE` | either | no | no | End-of-conversation marker |

Examples (each line is one turn; CAS state in parentheses for CAS-load-bearing turns):

- `OPEN`: "I can't stand it when people interrupt me."
- `ACK`: "Got it."
- `MIRROR`: "If I'm hearing you, the structural reading is ^3^E|f. Does that fit?" (`^3^E|f`)
- `CLARIFY`: "Walk it back — what's closer to your felt sense?"
- `EMPATHIZE`: "That sounds like a lot."
- `ANSWER`: "The reading I'd stand behind is ^3^E|f." (`^3^E|f`)
- `PLAN`: "Given ^3^E|f, the next step on the pathway would be to strengthen the prerequisite that's currently weakest." (`^3^E|f`, no mutation)
- `REFUSE`: "I can't take that turn — it would break the admissibility of the dialog."
- `REFUSE_CLAIM`: "I don't think the structure you're proposing fits. The closer reading I'd stand behind is ^4^E|f." (`^4^E|f`)
- `REPAIR`: "No wait, actually it's closer to grief than aversion."
- `CLOSE`: "Thanks, that's it."

The split between `REFUSE` and `REFUSE_CLAIM` is load-bearing: `REFUSE` declines the *request* (typically because admissibility is violated by the proposed transition); `REFUSE_CLAIM` accepts the request but rejects the user's *CAS claim* and counter-proposes. Conflating them breaks downstream metrics — refusal rate vs. counter-proposal rate are independent signals.

---

## 3. Admissibility graph

| Previous turn | Admissible next turns | Rationale |
|---|---|---|
| `OPEN` | `ACK`, `MIRROR`, `EMPATHIZE`, `CLARIFY`, `ANSWER`, `REFUSE`, `REFUSE_CLAIM` | After a user opens, the assistant can ack, mirror, empathise, clarify, or commit (if confidence is high enough). Direct `ANSWER` is allowed for short well-anchored prompts. Refusal paths exist for inadmissible requests. |
| `ACK` | `MIRROR`, `CLARIFY`, `ANSWER`, `EMPATHIZE` | After an ack, the assistant continues with the substantive move. |
| `MIRROR` | `ANSWER`, `CLARIFY`, `REPAIR`, `PLAN`, `OPEN`, `CLOSE` | The mirror is a confirmation point. The user can accept (leading to `ANSWER` / `PLAN`), correct (`REPAIR`), pivot (`OPEN`), or close. The assistant can ask for further clarification. |
| `CLARIFY` | `ANSWER`, `REPAIR`, `OPEN` | After a clarifying question, the user answers (next assistant turn can be `ANSWER`), corrects, or pivots. |
| `EMPATHIZE` | `MIRROR`, `CLARIFY`, `ANSWER`, `CLOSE` | Empathic pause leads naturally to mirroring or committing. |
| `ANSWER` | `REPAIR`, `PLAN`, `CLOSE`, `OPEN` | Post-answer, the user accepts (-> `PLAN` or `CLOSE`), corrects (`REPAIR`), or pivots (`OPEN`). |
| `PLAN` | `CLOSE`, `REPAIR`, `OPEN` | Post-plan, the user closes, corrects the plan, or pivots. |
| `REFUSE` | `CLOSE`, `REPAIR`, `OPEN` | Post-refusal, the user closes, corrects (re-asking with admissible framing), or pivots. |
| `REFUSE_CLAIM` | `CLOSE`, `REPAIR`, `CLARIFY`, `OPEN` | Same as `REFUSE` plus `CLARIFY` (the assistant can ask the user to defend the rejected claim). |
| `REPAIR` | `MIRROR`, `ANSWER`, `CLARIFY`, `REFUSE_CLAIM` | After a user repair, the assistant re-mirrors, re-answers, asks for clarification, or rejects the correction (`REFUSE_CLAIM`). |
| `CLOSE` | (empty) | Terminal. |

Rationale for inclusion of `OPEN` in many follow-on sets: real users pivot mid-conversation. Treating `OPEN` strictly as "the first turn only" produces a brittle grammar that can't handle "what about when it reminds me of my dad" coming after an `ANSWER`. The cost is a slightly larger grammar; the benefit is much higher coverage.

The graph is connected from `OPEN` (every TurnType is reachable via the transitive closure). Verified by `admissibility_graph_is_connected()` in the smoke tests.

---

## 4. DialogState data model

```python
@dataclass(frozen=True)
class DialogState:
    turn_history: tuple[Turn, ...]
    current_cas_state: str
    cas_state_history: tuple[str, ...]      # walk-back stack, newest first
    admissible_next_moves: frozenset[TurnType]
    repair_count: int
    user_satisfaction_estimate: float       # [0, 1]
    metadata: dict[str, Any]
```

Frozen + immutable. Every update returns a new `DialogState`; we never mutate in place. The walk-back stack is a *cache*, not an inverse computation — this matches Correction 2 (RPM is section-retraction; re-applying inverse may lose information).

Updates are functional:

- `apply_turn(state, turn)` — appends, updates CAS state if the turn is mutating, recomputes admissibility, updates repair counter and satisfaction estimate.
- `compress_history(state, max_turns=10)` — drops oldest turns when history grows beyond `max_turns`. CAS state history is preserved in full (walk-back depth is independent of the user-visible context window).
- `detect_repair(state, user_text)` — heuristic returning True iff the user utterance is a correction *and* the most recent assistant turn was CAS-load-bearing.

The `repair_count` is monotonic; the satisfaction estimate decays by 0.2 on each `REPAIR` and recovers by 0.05 on each successful CAS turn (`ANSWER` / `MIRROR` / `PLAN`). This is a Phase-2 stub — the follow-on session can swap in a learned estimator.

---

## 5. Repair strategy hierarchy

When the user emits `REPAIR`, the engine runs `select_repair_strategy(state, user_correction)` and picks one of:

| Strategy | When | Effect |
|---|---|---|
| `WALK_BACK` | User asks to go back to a prior reading; walk-back stack is non-empty | Pop the most recent CAS state off the stack and restore it as `current_cas_state`. Follow-on assistant move: `MIRROR` (echo restored reading). |
| `REFINE` | User adjusts the reading ("closer to grief than aversion") | Leave `current_cas_state` untouched; mark `pending_refinement=True`; predictor re-runs on the user's correction context. Follow-on assistant move: `ANSWER` (commit to refined reading). |
| `CLARIFY` | User is unsure ("I don't know, either way") | Leave CAS state untouched; mark `pending_clarification=True`. Follow-on assistant move: `CLARIFY` (targeted question). |
| `RESET` | After `RESET_AFTER_REPAIRS` (default 3) failed repairs | Clear `current_cas_state`, clear walk-back stack, reset satisfaction to neutral 0.5. Follow-on assistant move: `CLARIFY`. |

Selection precedence:
1. If `repair_count + 1 >= RESET_AFTER_REPAIRS`, escalate to `RESET`.
2. If walk-back triggers fire and walk-back stack is non-empty, `WALK_BACK`.
3. If clarify triggers fire, `CLARIFY`.
4. If refine triggers fire, `REFINE`.
5. Default, `REFINE` (the most common case in chat data).

Triggers are regex-based in the scaffold; the follow-on session can replace them with a learned classifier.

---

## 6. NL Generation Head — what it must do, what it punts to follow-on

The NL Generation Head (`nl_generation_head.generate`) takes a `GenerationRequest` (turn type + CAS state + user text + metadata) and returns a `GenerationResult` (text + template label + CAS echo). The interface is deliberately narrow so the implementation can be swapped without touching the engine.

**What it must do, and the scaffold does:**

- Dispatch by turn type. For CAS-load-bearing turns (`ANSWER`, `MIRROR`, `REFUSE_CLAIM`, `PLAN`), produce text that mentions the CAS state. For CAS-neutral turns, produce a templated response.
- Soft-import the existing `cas_native.inference.cas_renderer.render_cas_prediction` and use it when the predictor passes a prediction dict via metadata. Fall back to an inline minimal renderer when torch is unavailable (e.g., in CI).
- Be deterministic and idempotent.

**What it punts to follow-on:**

- Variation in templated text (the scaffold uses a single template per CAS-neutral turn type; chat needs a wider repertoire).
- Adapting tone to the user's register (we have `register_bias` machinery in the dialectic scaffolding; integrating it into the NL head is follow-on).
- Bucket-aware phrasing (a v77_omega ANSWER should *sound* different from a v74_baseline ANSWER).
- A learned NL head trained on the multi-turn corpus this scaffold's generator produces.

---

## 7. Multi-turn corpus generation

The synthetic multi-turn corpus generator (`cas-synthetic/generator/multi_turn/conversation_generator.py`) emits records of the form:

```python
{
    "id": "mt-<hash>",
    "turns": [...],
    "final_cas_state": str,
    "dialog_path": ["OPEN", "MIRROR", "REPAIR", "MIRROR", "ANSWER", "CLOSE"],
    "buckets_visited": ["v74_baseline", "v77_omega"],
    "num_repairs": int,
    "metadata": {"seed": 42, "target_turns": 6, "target_buckets": []},
}
```

**Diversity dimensions (current scaffold):**

- Dialog path: drawn from the admissibility graph with weighted sampling. The current weight table biases toward `MIRROR`, `ANSWER`, and `REPAIR` so the generated corpus exercises the repair surface.
- CAS buckets: `v74_baseline`, `v75_register`, `v76_production`, `v77_omega`, `meta_logic`. Each user opening template names a bucket; assistant CAS commitments are drawn from the same pool. The `target_buckets` parameter restricts sampling to a subset.
- User correction language: 4 templates for `REPAIR`, 3 for `CLARIFY` responses, 2 for `CLOSE`.

**Diversity dimensions (follow-on):**

- Demographic + tonal axes (PR #34's `demographic_tonal_axes`) need to be wired in for register-aware multi-turn variety.
- Coherence across turns: the scaffold has no constraint that the final CAS state be reachable from the opening utterance via valid transitions. The follow-on session adds this constraint.
- Engine-grounded mode: the scaffold builds records from templates directly. The follow-on session adds a mode where the `ConversationEngine` drives generation, producing more naturally-distributed dialog paths.

**Target corpus size (Phase 2 follow-on, not this scaffold):**

- 50,000 conversations × ~6 turns each = ~300,000 turns.
- Distribution: 60% v74_baseline / v75_register, 30% v76_production / v77_omega, 10% meta_logic.
- Repair rate: 25-35% of conversations contain at least one REPAIR (matches Cohen-Skoll dialog corpus repair rates).

---

## 8. Training implications

The existing K=9 architecture needs **little** for inference on multi-turn data: a longer context window so the dialog history fits in. The encoder is unchanged.

**Required changes for the follow-on session:**

1. **Context window extension.** Concatenate the dialog history into the predictor's input prompt. The K=9 baseline at 93.2% canonical was trained on single-utterance prompts; we expect a small drop (~3-5pp) when the same checkpoint sees multi-utterance prompts at inference. Mitigation: brief LoRA adapter trained on the synthetic multi-turn corpus.
2. **Optional DST head.** A new prediction head on top of the encoder that predicts the *next move type* given (history, predicted CAS state). This unlocks engine modes where the assistant doesn't need a fixed move-selection rule. The DST head is a 11-way classifier; trains on the synthetic corpus's `dialog_path` label.
3. **CAS state coherence regulariser (optional).** A loss term penalising large transitions in the CAS state across consecutive turns when the dialog path doesn't justify it (e.g., `MIRROR -> REPAIR -> ANSWER` should produce a *small* CAS state change, not a wholesale swap).

What stays unchanged: the K=9 encoder, the Lever-3 self-conditioning machinery, the `structured_token_adapter`, the existing predictor surface, and the `cas_renderer`.

---

## 9. Risks

- **Dialog drift.** Long conversations may accumulate small misclassifications until the CAS state no longer reflects the user's situation. Mitigation: the walk-back stack lets users restore prior states, and the satisfaction estimator triggers `RESET` after repeated repairs.
- **Repair loops.** A user who keeps correcting can trap the engine in a `REPAIR -> ANSWER -> REPAIR -> ...` cycle. Mitigation: the `RESET_AFTER_REPAIRS` threshold escalates after 3 repairs and the engine emits `CLARIFY` to break the loop.
- **CAS state inconsistency across turns.** Without a coherence regulariser, the predictor may emit `^3^E|f` then `^2^E|f` on adjacent turns with no narrative justification. Mitigation: the multi-turn corpus's coherence constraint (follow-on) trains the predictor to respect adjacency. The scaffold provides the data shape; the constraint is left to the follow-on.
- **Over-eager repair detection.** A user saying "I hate that" might be misclassified as a repair after a prior assistant `^3^E|f`. Mitigation: the scaffold's repair-trigger regexes are correction-language-specific (no, wait, actually, that's not right) and explicitly do NOT match affect language.
- **NL head domain shift.** Templated NL responses sound canned; real chat needs natural variation. Mitigation: this is the primary follow-on work for Phase 2.
- **Predictor confidence is poorly calibrated.** The scaffold's `confidence_floor=0.7` is a guess. Mitigation: calibrate against the K=9 baseline's confidence distribution before turning on the engine in production.

---

## 10. Sequencing

Phase 2 implementation push lands AFTER:
- Phase 3 (free-form English handling, currently in progress per the rewrite_shim)
- vocab14 retrain (per `vocab14_retrain_RUNBOOK_2026_05_04.md`)
- Lever 3 self-conditioning retrain

Phase 2 is "ready" when:
- The K=9 baseline tolerates multi-utterance context windows without regressing canonical exact-match below 90%.
- The multi-turn corpus generator scales to 50k records with coherence guarantees.
- An optional DST head reaches >75% next-move-type accuracy on a held-out split.

Earliest readiness: ~6-8 weeks from today (2026-05-04). The scaffold landing here defines the API surface and the test contract so the follow-on session has nothing to design from scratch — only implementation.

---

## 11. Open questions (deferred to follow-on)

1. **DST head architecture.** Linear probe on the encoder representation? Small transformer on top of the dialog history? Empirical question; defer until the corpus is built.
2. **How to handle multi-turn `^5^P|T` substrate references.** When a user references "who I am" mid-conversation, the resulting CAS state is genuinely compound (current Noetic against an `^5` substrate). The scaffold renders this as a single CAS expression; the follow-on may need an explicit substrate-tracking field on `DialogState`.
3. **Cross-conversation memory.** Out of scope for Phase 2. Tracked separately under the "long-horizon memory" workstream.
4. **Adversarial repair patterns.** A user who systematically corrects toward inversions (`^3 -> ^2 -> ^3 -> ^2`) is doing something interesting and possibly diagnostic. The scaffold treats every repair the same; the follow-on could surface inversion-axis repair signatures as a CAS-Native diagnostic.

---

## 12. References

- Project Identity / canonical Noetic definitions: `noetic-compass-scaffold/noetic-compass/CLAUDE.md`
- Foundational clarifications: `noetic-compass-scaffold/noetic-compass/docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`
- Existing single-instance multi-INSTANCE work (different from multi-TURN): `noetic-compass-scaffold/noetic-compass/cas-native/dialectic/`
- Rewrite shim (NL -> training surface): `noetic-compass-scaffold/noetic-compass/cas-native/inference/rewrite_shim.py`
- Version B plan: memory `project_version_b_conversational_plan.md`
- Single-turn baseline: K=9 structured token prediction, 93.2% canonical
