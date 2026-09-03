# P6 RESOLUTION -- Phase B of the clean-room reset (2026-09-02)

**Question the owner asked this phase to close:**

> Does the specific P > C > E > O order have evidence of value, or does only generic sequencing help?

**Answer, in one line:** P6 provides evidence for **neither**. Its reported numbers are training-fit
accuracies; on genuinely held-out data the experiment fails its own positive control and its own
status law returns `CONTROLS_FAILED_NO_VERDICT`. The specific-order question is **OPEN**, not
answered in either direction, and nothing in this arc supports a value for P > C > E > O.

Everything below is checkable from files in this directory and from git. No number here is
retyped from chat; each is copied from a raw stdout receipt named next to it.

---

## 1. What the record contained before this phase

| item | state found |
|---|---|
| script | `cas_only_reasoner/CJT_PREC_CLOSURE/p6_order_test.py`, committed once, in `1e58d725` (2026-09-02 21:29:49 -0700); git blob `779cc239b51579f88e8f74b349e970619585a7c8`; sha256 (LF) `07e824e242968c11440c4cc3d256bb518cf5579416fc4d848bf3004cc8baa8dd` |
| result numbers | **commit message of `1e58d725` only.** No raw stdout, receipt, result JSON, findings section, spec-sheet row or CHANGELOG row |
| preregistration | the "registered prediction" is inside the script, committed in the **same** commit as the results. No earlier commit exists. "Written before running" is not verifiable from git |
| orders tested | 3 fixed orders (`(0,1,2,3)` CAS, `(3,2,1,0)` reversed, `(2,0,3,1)` one non-CAS) plus a mechanism-free bag. **Not all 24** |
| independent audit | **none** for P6. The DeepSeek R1 audit in the same commit covered the visibility law and the generic non-absorption claim, not P6 |
| spec sheet / CHANGELOG | not updated in `1e58d725`, `61a3576d` or `4825a37d` (the sheet's own rule requires same-commit rows) |

Handoff status on entry: `CHAT_REPORTED_ONLY`.

## 2. Reproduction of the committed script, as committed

Receipt: `p6_committed_repro_stdout.txt` (raw), `p6_committed_repro_time.txt`, `p6_committed_repro_env.txt`
(python 3.14.0, numpy 2.3.5), `p6_order_test.sha256`. Wall time 55.995 s, local CPU, numpy only, `$0`.

All sixteen means reproduce the commit-message numbers to four decimals:

```
(a) world = CAS order      CAS 0.9689  reversed 0.9272  random-fixed 0.9471  bag 0.8181
(c) world = reversed       CAS 0.9312  reversed 0.9448  random-fixed 0.9203  bag 0.8212
(b) world = random/item    CAS 0.7245  reversed 0.7247  random-fixed 0.7307  bag 0.5689
(neg) no order structure   CAS 0.9856  reversed 0.9921  random-fixed 0.9683  bag 0.9960
controls PASS/PASS; (a) +0.0219 HELD; (b) -0.0061 HELD; (c) -0.0136 FAILED
```

So the numbers are real outputs of the committed script. That is the only thing this step shows.

## 3. The defect: the "held-out" set is the training set

`run_condition()` (committed lines 160-162) draws the training world with
`np.random.default_rng(1000 + sd)` and then the "held-out" set with a fresh
`np.random.default_rng(1000 + sd)` -- the same seed. Every world function draws its parameters and
then its evidence from that single stream, and `NTR == NTE == 1500`, so the two draws are
byte-identical. Checked directly before any correction was written:
`np.array_equal(Etr, Ete) and np.array_equal(ytr, yte)` is `True` for all 5 seeds in all three world
functions (15 of 15). Every accuracy the committed script prints is a training-fit accuracy. The
comment `# same world, fresh draw` (line 162) and the banner `1500 train / 1500 held out` (line 173)
are false.

## 4. The correction, and what it shows

`p6_heldout_repro.py` (append-only; the committed script is untouched) loads the committed
definitions digest-pinned, rebuilds the same training sets and asserts them element-wise equal to
the committed draw, draws a fresh held-out set from the same world parameters with seed stream
`500000 + sd`, trains the same four arms with the same init seeds, steps, learning rate and
optimiser, and applies the committed controls and thresholds to the held-out numbers. Its positive
control is that the train-fit numbers must reproduce the committed numbers exactly. Receipt:
`p6_heldout_repro_stdout.txt`, wall time 1 m 11.120 s, `$0`.

```
                              train-fit  committed  match   HELD-OUT  +/- seed sd
(a) world = CAS order
  CAS  P>C>E>O                   0.9689     0.9689   yes     0.6868   0.0298
  reversed                       0.9272     0.9272   yes     0.6148   0.0279
  random fixed                   0.9471     0.9471   yes     0.6384   0.0222
  BAG mechanism-free             0.8181     0.8181   yes     0.6875   0.0210
(c) world = reversed
  CAS                            0.9312     0.9312   yes     0.6209   0.0329
  reversed                       0.9448     0.9448   yes     0.6739   0.0219
  random fixed                   0.9203     0.9203   yes     0.6261   0.0260
  BAG                            0.8212     0.8212   yes     0.6857   0.0235
(b) world = random per item
  CAS                            0.7245     0.7245   yes     0.3743   0.0177
  reversed                       0.7247     0.7247   yes     0.3675   0.0198
  random fixed                   0.7307     0.7307   yes     0.3775   0.0208
  BAG                            0.5689     0.5689   yes     0.4219   0.0337
(neg) no order structure
  CAS                            0.9856     0.9856   yes     0.7167   0.0183
  reversed                       0.9921     0.9921   yes     0.7108   0.0242
  random fixed                   0.9683     0.9683   yes     0.7161   0.0121
  BAG                            0.9960     0.9960   yes     0.8548   0.0242

POSITIVE CONTROL OF THIS SCRIPT (train-fit reproduces committed numbers)   PASS  (16/16)
CONTROL CHECK on held-out:  POSITIVE FAIL  (a) CAS 0.6868 vs bag 0.6875 | (c) reversed 0.6739 vs bag 0.6857
                            NEGATIVE PASS  spread 0.0059
STATUS: CONTROLS_FAILED_NO_VERDICT
```

Plain reading:

- Every arm overfits. Train-fit above 0.92 on the ordered worlds becomes 0.61 to 0.69 held out.
- The mechanism-free bag ties or **beats** every chain arm in every world once the data are held
  out. The committed headline "bag loses by 0.13-0.15 everywhere ordered" was a training-fit
  artefact.
- The order-matching arm does not beat the bag, so the harness cannot detect order-matching at
  all. By the script's own law, no verdict may be stated about (a), (b) or (c).

### 4.1 A mechanism-free linear rule beats every trained arm held out

Registered after a lens review reported it; re-measured with `p6_linear_rule_check.py` (receipt
`p6_linear_rule_check_stdout.txt`, 0.841 s). Ordinary least squares on the flattened 20-number
evidence plus a bias -- 84 parameters, no hidden layer, no sequencing, no training loop -- on the
same training draws (asserted equal to the committed ones) and the same fresh held-out draws:

```
condition                    OLS train   OLS held   majority-class held   best trained arm held
(a) world = CAS order           0.7252     0.7108          0.3744            0.6875 (bag)
(c) world = REVERSED            0.7208     0.7092          0.3592            0.6857 (bag)
(b) world = RANDOM per item     0.4903     0.4536          0.3632            0.4219 (bag)
(neg) NO order structure        0.7892     0.7755          0.3084            0.8548 (bag)
```

In every ordered world the linear rule beats every chain arm and the bag. Two consequences:
the "chance = 0.25" banner understates the trivial floor (majority class is 0.36-0.37, labels
are imbalanced), and the experiment's arms never rose above the cheapest method without the
mechanism. By the standing rule (a win by mechanism M is uninterpretable until it beats the
cheapest method without M), P6 could not have licensed an order claim even with a valid held-out
set.

## 5. Independent audit (different model family, via AWS Bedrock; teacher-language use only)

Package: `P6_AUDIT_PACKAGE.md`, assembled by `build_p6_audit_package.py` from the files above
(script verbatim, raw outputs verbatim, questions; no verdict of ours included). Dispatcher:
`dispatch_p6_audit.py`. Reports and token receipt under `audits/`.

| auditor | verdict line | one-word answers |
|---|---|---|
| DeepSeek R1 (`us.deepseek.r1-v1:0`), 11,241 in / 1,384 out tokens, est. USD 0.0226 | `P6_AUDIT_FAIL: The corrected run's POSITIVE control failed (CAS ≤ bag in (a)), invalidating all claims. The experiment cannot distinguish order effects from capacity differences or seed noise.` | `SPECIFIC_CAS_ORDER_HAS_EVIDENCE_OF_VALUE: NO` · `GENERIC_SEQUENCING_HELPS_IN_THIS_WORLD: CANNOT_SAY` |
| Llama 3.3 70B (`us.meta.llama3-3-70b-instruct-v1:0`), 10,872 in / 571 out tokens, est. USD 0.0082 | `P6_AUDIT_FAIL:the experiment's design and analysis are flawed, and the results do not provide strong evidence for any specific sequencing strategy, including the specific order P > C > E > O.` | `SPECIFIC_CAS_ORDER_HAS_EVIDENCE_OF_VALUE: NO` · `GENERIC_SEQUENCING_HELPS_IN_THIS_WORLD: CANNOT_SAY` |

Two families, two `FAIL` verdicts, the same two one-word answers. Token receipt:
`audits/DISPATCH_RECEIPT.json` (estimated total USD 0.0308 from published on-demand rates; reconcile
with the AWS bill). One point of disagreement between the auditors is recorded and not resolved
here: DeepSeek R1 reads the world generator as an answer key for the order-matching arm (A4);
Llama 3.3 does not (Q4). Both agree the bag arm's `U = 0` is a capacity confound.

DeepSeek R1 also answered: the same-seed finding is correct (A1); the correction changes nothing
but the held-out draw (A2); the bag arm's `U = 0` is a capacity confound for any "order matters"
reading (A4, A9); the script's verdict logic could never have concluded that the specific CAS order
has value (A5); the reported differences are within seed noise at 5 seeds (A6); 3 of 24 orders
limits any statement about fixed orders (A7); the original run has no evidentiary credibility and
the correction is a valid instrument whose controls failed (A8).

## 6. Statuses after this phase (handoff vocabulary)

| claim | status | why |
|---|---|---|
| The committed P6 numbers are outputs of the committed script | `VERIFIED` (as training-fit values) | reproduced 16/16 to four decimals, receipt in this directory |
| The P6 numbers are held-out accuracies | `REFUTED` | held-out set was the training set, 15/15 identical |
| Ordered chain beats the mechanism-free bag ("order matters") | `REFUTED` on held-out; the committed evidence for it was training-fit | bag ties or wins in all four worlds held out |
| The CAS order P > C > E > O has value beyond other fixed orders | `OPEN` -- never fairly tested; **no** evidence for it anywhere in this arc | P6 cannot test it (positive control fails; only 3 of 24 orders; verdict logic has no branch that could find it) |
| Generic sequencing helps on ordered worlds | `OPEN` | P6 cannot say; the only mechanism-free baseline beats the chains held out |
| P6 as a bench for either question | `INVALID_BENCH` | controls fail under the implemented held-out draw; capacity confound between chain and bag arms |
| Handoff line "ordered chain vs orderless bag: sequencing appears useful in reported P6 screen" | **withdrawn** | it rested on training-fit numbers |

## 7. Record defects added by this phase (append-only; nothing rewritten)

| id | defect | where |
|---|---|---|
| CR-01 | "held-out" set identical to training set, all seeds, all worlds | `p6_order_test.py` lines 160-162 |
| CR-02 | false comment and banner ("fresh draw", "1500 held out") | lines 162, 173 |
| CR-03 | result numbers exist only in a commit message; no raw output or receipt committed | commit `1e58d725` |
| CR-04 | "registered prediction" committed in the same commit as the results; no prior registration | commit `1e58d725` |
| CR-05 | three lane commits shipped without the same-commit spec-sheet row the sheet mandates | `4825a37d`, `61a3576d`, `1e58d725` |
| CR-06 | the DeepSeek R1 theorem audit in `1e58d725` did not cover P6, but the commit title reads as if one audit covered all three items | commit `1e58d725` |
| CR-07 | **status written by prose, not by the program.** The commit message states `=> order matters, CAS ordering does not. CAS_PRECEDENCE_VALUE_NOT_ESTABLISHED.` The script prints that status only in its all-three-predictions-hold branch (lines 240-247). Prediction (c) FAILED, so the program took the `else` branch and printed `THE PREDICTION DID NOT HOLD AS REGISTERED ... do NOT substitute a new hypothesis for the registered one` (lines 251-253; see `p6_committed_repro_stdout.txt`, last three lines). The commit message substituted a conclusion the program refused to print. Found independently by all three internal lens reviews. | commit `1e58d725` vs receipt |

## 8. Internal review of the correction itself (Claude-family agent -- NOT an independent audit)

A separate agent was asked to break `p6_heldout_repro.py`. Verdict: `CORRECTION_SOUND`, no
BLOCKING or MAJOR finding. Recorded here so its minor notes are not lost; the audited script is left
byte-identical to what the two external auditors received (sha256 in `P6_AUDIT_PACKAGE.md`).

- Draw order, arithmetic, seeds, arms, thresholds and controls match the committed protocol line
  for line; the three seed streams (`1000+sd`, `7000+sd`, `500000+sd`) share no values and show
  no correlation (100,000-draw check); `train()` mutates only its own parameters.
- The reviewer reproduced the correction's four held-out means for world (a) exactly (`0.6868`,
  `0.6148`, `0.6384`, `0.6875`) from its own reconstruction, and got `0.6788 / 0.6219 / 0.6361 /
  0.6891` on 20,000 fresh items -- the same picture.
- Minor notes on the correction: the docstring says "15 of 15" (three world functions x five
  seeds, which is what was checked first); over the four conditions it is 20 of 20, verified by the
  reviewer. The exit code is `0` for every status branch, so a receipt reading only exit codes
  cannot tell "no verdict" from "verdict"; the printed `STATUS:` line is the authority. The
  "held-out identical to train: [False x5]" line is a sanity print, not a control.
- Notes on the committed design, untouched by the correction: labels are imbalanced (majority
  class 0.36-0.40 per seed), so the banner's `chance=0.25` understates the trivial baseline, and
  in world (b) the chain arms' held-out 0.37-0.38 sit at that baseline. The bag has 224 trainable
  parameters against 480 for each chain arm.
- Robustness sweep (reviewer's own run, world (a), 20,000 fresh items, 5-seed means): at
  25 / 50 / 100 / 200 / 400 / 700 steps CAS = `0.7241 / 0.7269 / 0.7105 / 0.6927 / 0.6823 / 0.6783`,
  bag = `0.7060 / 0.7126 / 0.7107 / 0.7010 / 0.6924 / 0.6895`. The largest CAS-over-bag margin is
  `+0.0181` at 25 steps, below the `+0.02` positive-control margin, so `CONTROLS_FAILED_NO_VERDICT`
  holds at every step count tested. Early stopping does not rescue the instrument.

## 9. What was NOT done, deliberately

- No run of all 24 orders, no new arms, no re-tuning, no GPU, no AWS compute. The owner's
  instruction was not to invent another CAS-order experiment; a repaired instrument that fails
  its own positive control is the end of P6, not the start of P7.
- No number in the original record was altered. The committed script and commit message stand as
  they are; this directory sits beside them.

Cost of this phase: local CPU numpy, under 2 minutes total; Bedrock audit tokens as receipted.
