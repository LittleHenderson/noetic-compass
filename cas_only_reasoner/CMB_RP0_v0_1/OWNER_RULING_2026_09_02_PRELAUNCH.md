# OWNER RULING — CMB-RP0 PRE-LAUNCH STATUS (2026-09-02)

Recorded verbatim in substance. This ruling is **binding** and supersedes the builder's
capability status law wherever the two differ.

---

## 1. Operative state

```
CMB-RP0 implementation        BUILT
Scientific result             NONE YET
One-world development signal  UNFAVORABLE
Shortcut repairs              PROMISING, PENDING AUDIT
AWS launch                    NOT YET AUTHORIZED
Required next event           INDEPENDENT AUDIT OF FINAL COMMIT
After audit passes            ONE AWS GPU DEVELOPMENT RUN, HARD CAP $0.40,
                              NO AUTOMATIC REDESIGN
```

Preserved commits: `62a9977b`, `2c87a5c2`, `a7fde30b`.

**A note on one apparent conflict, recorded rather than resolved silently.** The owner's
message opens *"run it on gpu at $0, 9 worlds"* and then rules *"Do not launch it yet"*,
`AWS launch: NOT YET AUTHORIZED`, and *"After a green independent audit, one remote AWS GPU
run may be authorized"*. The builder is treating the **formal ruling as binding** and has
launched nothing. If the opening line was the intended instruction, the owner can say so and
the run starts immediately — the harness and launcher are frozen and ready.

## 2. Role classification

> *"You are now classified as the BUILDER of CMB-RP0, not its independent auditor."*

```
GLM                      builder of RGM-0.2
Claude                   builder of CMB-RP0
Independent third model  audits CMB-RP0
Owner                    authorizes or refuses AWS execution
```

**Accepted without reservation.** The builder's own checks are labelled BUILDER SELF-CHECK
everywhere and are not offered as the audit. Any subagent the builder runs is still Claude and
is therefore **not** independent — that limitation is stated on every artifact this bench
produces.

## 3. GPU ruling — recorded and wired

> No experimental workload on the owner's local CPU.
> Use one remote AWS GPU.
> All scalable learning tensors run on CUDA.
> Fail closed on silent numerical CPU fallback.
> Remote CPU host: orchestration, file I/O, hashing, JSON, monitoring and shutdown only.

Implemented: `require_cuda()` raises `GPU_REQUIRED` and there is **no CPU fallback branch** —
the harness cannot silently degrade. The launcher additionally fails the run before any
harness work if `torch.cuda.is_available()` is False on the instance.

The owner's own observation is recorded on the artifact: the learner is a ~4,800-parameter MLP,
so the T4 spends most of the rented time on Python and world construction rather than neural
arithmetic. **The GPU here is a governance choice, not a speed necessity**, and the receipt
says so in `compute.scale_note` so no auditor reads GPU usage as evidence of scale.

## 4. Promotion law — BINDING, all eight conditions

> *"No result may promote unless CMB_AUTHORIZED: admits less poison than CMB_RETRIEVED;
> beats RANDOM; beats SEMANTIC_DIVERSE; beats CLASS_BALANCED; beats DEGREE_FILTER; preserves
> old-task performance; still learns the new task; clears the frozen world-level uncertainty
> law."*

Implemented in `summarize()` as a conjunctive `promotion` block that prints PASS/FAIL per
condition and emits `PROMOTABLE` or `NOT_PROMOTABLE`:

| condition | executable predicate |
|---|---|
| admits less poison than `CMB_RETRIEVED` | `two_tier_gap > POISON_MARGIN` (`1.0` forgeries) |
| beats `RANDOM` | paired delta `> MARGIN` and permutation `p < 0.05` |
| beats `SEMANTIC_DIVERSE` | same |
| **beats `CLASS_BALANCED`** | same — **added by this ruling**; the builder had excluded it as a "ceiling" |
| beats `DEGREE_FILTER` | same |
| preserves old-task performance | `acc_T1_end / acc_T1_after_T1 >= PRESERVE_FRAC` (`0.80`) |
| still learns the new task | `acc_Tlast_end >= LEARN_FLOOR` (`0.80`) |
| clears the world-level uncertainty law | `p < 0.05` on all four required comparisons |

`CLASS_BALANCED` was the arm the builder had registered as an oracle. The ruling is that it
uses only labels already stored on the memories, making it a **deployable one-line method**
the mechanism must beat. Accepted; it is in `REQUIRED_BEAT`.

## 5. What the independent auditor must verify

Twelve items, from the ruling:

```
ID_ORDER shortcut closure
independent random draws by world
independent task splits by world
poison-degree control
CLASS_BALANCED construction
CMB_RETRIEVED versus CMB_AUTHORIZED poison gap
TWO_TIER_GATE_EARNS_NOTHING
SEMANTIC_DIVERSE and DEGREE_FILTER controls
deterministic hashing
written-versus-executable status equality
actual $0.40 launcher ceiling
full end-to-end receipt path
```

Plus the seven pre-launch items, of which the first three were the ruling's specific
objection — **the builder had claimed the noise problem was fixed without stating how**:

```
1. the exact new effect threshold
2. the world-level uncertainty calculation
3. that nine worlds are enough for the status the program may emit
4. the authorized tier must reduce poison relative to retrieval
5. CMB must beat CLASS_BALANCED, SEMANTIC_DIVERSE and DEGREE_FILTER, not just random
6. every world gets independent random replay, task splits, IDs, poison placement, query
7. the $0.40 ceiling is enforced by the actual launcher
```

## 6. Standing prohibitions

```
No local experimental CPU workload.
No protected data.
No claim promotion.
No automatic second repair.
```

The last is load-bearing: **after this result, no further repair round may be started
without a new owner authorization.** In this lane a repair has twice manufactured the next
shortcut.

## 7. The owner's own summary of the state, preserved

> *"This report is good news about experimental discipline, not yet good news about the CMB
> replay mechanism."*

And the question the bench now asks, in the owner's words:

> *"Can CMB select a small replay set that preserves old learning better than simple balanced
> replay, while admitting fewer forged memories?"*
