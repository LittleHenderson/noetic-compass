# F2 report — saved development answers by label class

The saved development gains mostly come from positive paths, not the majority ABSENT class. This contradicts a blanket account that apparent success on this panel comes mainly from predicting no path. Results remain mixed: five runs improve exact positive-path answers, while Helm 2.0 seed 20260917 loses one. All six final runs perform poorly on ABSENT. No causal training mechanism is established.

## Preregistered scope

F2 was preregistered in FOLLOWUP_PLAN.md at integration commit `259ed0be`, then selected unchanged after the conference at `5c128a33`. Its three alternatives were: aggregate correctness mainly follows ABSENT; exact DIRECT/VIA improvement contributes; or results differ across versions/seeds. This report executes only that comparison. No second round is proposed because no discrepancy appeared.

Subjects are Helm 1.0 source `af0970cfa6d54a85aeb16e5a99a84d791ace59c0` and Helm 2.0-experimental source `20208c923d41c24614504d4ecc2b289ecb66eda8`, each at seeds 20260917, 20260918 and 20260919. Endpoint files are the original `development_p00_predictions.json` and `development_p10_predictions.json`; saved scoring is used only to check the independently derived correctness.

## Exact correctness, initial → final

Each column has a fixed denominator. VIA is correct only when both the state and required via node match; it is not a state-only score.

| Version / seed | ABSENT /42 | DIRECT /8 | VIA /3 | Parts /6 | All /59 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Helm 1.0 / 20260917 | 0 → 0 | 0 → 3 | 0 → 3 | 0 → 1 | 0 → 7 |
| Helm 1.0 / 20260918 | 0 → 1 | 0 → 5 | 0 → 2 | 0 → 1 | 0 → 9 |
| Helm 1.0 / 20260919 | 0 → 0 | 0 → 2 | 0 → 3 | 0 → 1 | 0 → 6 |
| Helm 2.0 / 20260917 | 0 → 0 | 0 → 0 | 3 → 2 | 0 → 0 | 3 → 2 |
| Helm 2.0 / 20260918 | 10 → 2 | 0 → 7 | 0 → 3 | 0 → 0 | 10 → 12 |
| Helm 2.0 / 20260919 | 0 → 2 | 0 → 0 | 0 → 3 | 0 → 1 | 0 → 6 |

Exact positive-path totals (DIRECT + VIA) are Helm 1.0: 0→6/11, 0→7/11, 0→5/11; Helm 2.0: 3→2/11, 0→10/11, 0→3/11. Seed 20260918 illustrates why total accuracy is insufficient: Helm 2.0 gains ten exact positive-path answers while losing eight ABSENT answers, yielding only two more correct answers overall.

These results support the preregistered positive-path contribution and mixed-outcome alternatives. They reject the blanket majority-ABSENT success account for the recorded final results. The class imbalance still matters in a different way: the largely missed ABSENT class dominates the denominator and hides some positive-path gains. The constant ABSENT answer matches 42/53 reach targets; final Helm reach totals are only 6, 8, 5, 2, 12 and 5 out of 53, respectively. This comparison concerns independently derived target agreement, not a new official benchmark run.

## Evidence and method

`F2_RESULTS.json` preserves every target, its graph/query identity, all 708 saved endpoint answers and independently computed correctness, per-class counts, gains/losses, and full consumed-file SHA256 values. All six source ZIPs, twelve prediction files and twelve scoring files match the common manifest. All six ZIPs contain the same compact development bytes: SHA256 `5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4`.

`f2_development_classes.py` imports only standard-library modules. Its independent graph routine implements direct-edge precedence, sorted-neighbor search, and the required first constituent or immediate predecessor. Parts answers are the complete sorted outgoing-neighbor set. Source semantics are preserved with original checker.py lines 129–199 and SHA256 `57ac0a9f78c46999fac444fc974d3c1b718435b583cbc48701be74c56efa971e`. The historical checker was not imported or executed. All 708 independently computed correctness values agree with saved scoring; no failed assertion or recovery occurred.

The shared data have 59 packets and 59 unique query IDs over six focus worlds: five ten-node graphs and one nine-node graph, previously established by A3. There are 53 reach questions (42 ABSENT, eight DIRECT, three VIA) and six parts questions. These are previously examined development questions, not fresh hidden evaluation. Results do not prove a general graph algorithm, memorization, a particular optimization cause, or the cause of the frozen held-panel gate outcome.

## Execution record

One substantive execution, zero repeats, zero formal test functions; six run subjects × two endpoints × 59 packets = 708 saved prediction instances, comprising 636 reach and 72 parts checks. Those are repeated observations of 59 shared inputs, not 708 independent experiments. An earlier read inspected file keys only; it did not calculate F2 results.

Command: `C:/Python314/python.exe -B cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A3/f2_development_classes.py`. It ran in the assigned A3 worktree using PowerShell 7, login disabled, `PYTHONDONTWRITEBYTECODE=1`, and `PYTHONIOENCODING=utf-8`; tool chunk `b450d4`, exit 0, internal time `0.3133488000021316` seconds, 115-second watchdog. Plan/schema inspection was chunk `c50067`, exit 0. `F2_EXECUTION_RECEIPT.json` binds the script/output hashes and exact environment; stdout is saved separately.

No new predictions, model initialization, Torch import, checkpoint load, training, GPU, cloud, paid API, installation, or allowance expansion occurred. The original FIRST_REPORT.md remains byte-identical.
