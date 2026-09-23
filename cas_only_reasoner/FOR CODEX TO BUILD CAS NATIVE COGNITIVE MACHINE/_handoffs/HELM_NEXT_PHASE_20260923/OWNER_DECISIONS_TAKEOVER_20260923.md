# Owner decisions during the temporary takeover (2026-09-23)

**The owner's words, in chat, exactly:**

> "4. KEEP IT (G6E.XLARGE) 3. YOU HAVE THE GO AHEAD FOR THE SWITCH ON MODEL 2. GO WITH YOUR RECOMMENDATION 6 AND 7
> NODE 1. FOR RESCORER PICK WHICH EVER ONE MAKES FOR A BETTER MODEL"

**What they answered.** The four owner items in Claude's report of the same day:
1. the rescorer anchor policy;
2. the Stage 1 reach cut;
3. training a switch-ON model;
4. the stopped `g6e.xlarge`.

## How each decision is applied

| # | Decision | Applied as |
|---|---|---|
| 4 | Keep the stopped `g6e.xlarge` `i-0c3028734c8885542` ("cas-bridge-control-20260822") and its 300 GB volume | No action. Nobody touches it |
| 3 | **Go-ahead to train the switch-ON model** | See section 3 |
| 2 | **Stage 1 reach cells at 6 and 7 nodes** (option 1 of `records/helm_eval_design_20260923/hset1a/HSET1A_BUILD_RESULT.md`, Claude's recommendation) | See section 2 |
| 1 | **Rescorer: "whichever makes for a better model"** | See section 1 |

### 3. Training the switch-ON model

This is HELM-ANALOGY-REPAIR-1 acceptance item 2.

- **The approval.** Bounded AWS GPU training of trained switch-ON checkpoints.
- **Order.** Training runs only **after** acceptance item 1 (switch OFF preserved on the T4, amendment A4) has
  passed. If item 1 fails, the training job is not launched.
- **Records written before launch:** the job's source, seeds, starts, limits and cost ceiling. It must also have a
  migration record declaring the ON shapes. Matched starts come from the same seeds as Helm 2.0, with the five
  `analogy_head` tensors seeded separately.
- **The acceptance rule is unchanged.** `PRESENT_GRAPH_AND_DOMAIN` (probe v0.2) is required on every trained ON
  checkpoint whose analogy numbers are read.
- **What it does not cover.** Q4 or the late-reach experiment. Nor does it add budget beyond the ceiling that job
  states.

### 2. Stage 1 reach cells at 6 and 7 nodes

- **The build.** Claude, as custodian, builds HSET-1B: reach cells at 6 and 7 nodes. It uses a new salt and a new
  sealed TEST, and the frozen checker (reach is scored at up to 10 nodes).
- **Kept from HSET-1A:**
  - every node's in-degree and out-degree is at most 4;
  - trained words only;
  - comparators unchanged.
- **Before any model is read,** W and power are printed.
- **The success rule.** It is carried unchanged from `EVALUATION_DESIGN_v0_2.md` section 1.3: a cluster sign test
  against the measured bar, with the floor of 10 applied to W. It is frozen in design v0.3 before any model is read.
  The owner chose the 6- and 7-node cut, and this rule was part of the recommendation the owner accepted.

### 1. The rescorer anchor policy: the fail-closed option

**Why.** The anchor policy does not change what a model learns. It changes how safely every model is graded. The
stricter option protects every future model's grading from a wrong recorded rule, so it is the better choice for
the models.

**The two options:**
- Codex's tool 0.3 accepts the old 0.2 anchors and only **reports** that their recorded rule carries the wrong
  zero-loss veto.
- The fail-closed option **refuses** any anchor whose recorded rule disagrees with the historical rule, before any
  checker call.

**Applied as:**
- New 0.3 anchors are written with the correct rule. They were never delivered: "new anchors, new readings" was an
  open builder deliverable.
- The old 0.2 anchors and readings stay in the repository unchanged, as history.
- The tool refuses any anchor with a wrong rule.
- One AWS CPU job then produces the never-completed full 564-record reading and the 9 slow tests.

This is a builder change to Codex's tool, made by the temporary Claude builder and reviewed by a fresh reviewer.
Codex reviews it on return.

**Order of jobs.** One runner per job, and they are not all launched at once:
1. T4 item 1 (running next);
2. the ON training, after item 1 passes;
3. the HSET-1B build;
4. the rescorer reading.

The two CPU jobs may run while no GPU job is running.

## Addendum: the spending limit for switch-ON training (2026-09-23)

**The question put to the owner in chat, exactly:**

> "Switch-ON training must run on the same AWS g7.2xlarge Helm 2.0 used (the training code refuses any other GPU).
> Expected real cost is about $24 total: a ~$1.50 short test run, then 3 seeds of about 3 hours each (~$7.50 each),
> one at a time. The code books a fixed $15 per job, so up to $60 is reserved. What spending limit do you approve?"

**The owner's answer: "Up to $60 (Recommended)".** The option's text read: "Short test run + 3 seeds, one at a time.
Expected ~$24. Stops if the test run or any seed fails, and I stop and report if spend passes $30 before the third
seed."

**Applied as:**
- **Ceiling:** $60.00, for one reduced-schedule test run plus 3 seed jobs on g7.2xlarge, us-west-2. Each job books
  the code's fixed $15.00 reservation.
- **One machine at a time.** No automatic retries.
- **Stops:**
  - if the test run fails, no seed is launched;
  - if any seed ends other than delivered, the next seed is not launched;
  - if actual spend passes $30 before the third seed, stop and report.
- **Still first:** acceptance item 1 must pass on the T4, and the preparation must be reviewed.
