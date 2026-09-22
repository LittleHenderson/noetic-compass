# Inspect genuine saved Helm answers

The existing offline workbench now displays one retained correct answer and one
retained wrong answer from Helm 2.0-experimental. Open
`records/rpa_recorded_helm_20260922/workbench/index.html`, then select **Open the
saved question and answer**. Select the wrong task in the item selector to
inspect its original error. Expand each source record for exact saved JSON.

| Saved development task | Original prediction | Original checker |
|---|---|---|
| How is Dev1Node1 reached from Dev1Node7? | VIA via Dev1Node2 | Correct |
| Which nodes does Dev1Node7 directly contain? | (no nodes) | Wrong |

The wrong answer remains unchanged. The separately labeled deterministic checker
replay yields Dev1Node2. It is a reference answer, not a new learned prediction.
The two cases were selected after the historical run to illustrate inspection;
they do not form a performance estimate or a new evaluation.

The saved question, full public input packet, development focus-world structure,
original prediction, original checker result, independent checker replay and
model identity appear together. The full input includes the retained public
training-bank worlds; protected final evaluation targets are not exported.
The organization of these records is not an internal thought sequence.

Every item keeps its exact address, snapshot and saved version. The saved present
stays fixed when inspection, nested navigation, reference, layout or zoom changes.
A saved view can be restored only against its matching recorded document. Native
runtime, compound runtime, declared design and retained Helm families keep their
own schemas, source identities and evidence meanings.

## Missing evidence stays missing

All items in this retained Helm document have unassigned forty-part profiles and
no recorded Ohm measurement. Selecting a coordinate reference does not create
coordinates. The page explicitly reports:

```text
CAS profile: Not assigned
CAS-Ohm measurement: Not available
Original prediction: Available
Checker result: Available
Internal thought trace: Not recorded
```

The opening page links the previously completed declared-design atlas separately.
Its 12/4=3 and 12/6=2 examples are not measurements of either Helm prediction.
No model is loaded or called when generating or opening this workbench.

## Saved source identity

The selected job is `cas-meta2-tpntr-20260920210258-20208c92-m-20260917`,
source commit `20208c923d41c24614504d4ecc2b289ecb66eda8`, saved revision 1470.
The retained weights SHA-256 is
`c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb`.
The source run remains **NOT_CERTIFIED / NO_TRANSFER_TO_NEW_WORLDS**.
No release status changes.

The selection is bound by independent code-pinned source hashes. The adapter
replays the saved pure checker against source-bound inputs and rejects altered
task/model/checker joins, including modifications followed by a replacement
outer hash. This demonstrates faithful inspection of retained local evidence;
it is not independent authentication of the historical worker or a new inference.
Exact retained file identities are in
`records/rpa_recorded_helm_20260922/SOURCE_IDENTITIES.md`.

## Reproduce the viewer

From this CNCM directory, using the installed Python 3.12 interpreter:

```powershell
python tools/reproduce_recorded_helm_view.py
```

This rebuilds only the new retained-answer workbench and checks exact addresses,
source stability, navigation, missing values and original checker outcomes.
The existing compiler, PCBA reader and original design artifacts are preserved.
The existing renderer also accepts the generated document directly:

```powershell
python tools/render_rpa_view.py records/rpa_recorded_helm_20260922/workbench/helm.json records/rpa_recorded_helm_20260922/workbench/rendered_again.html
```

## Q4 learning remains a separate gate

The deterministic preparation uses the intended CUDA interpreter, current Q3
v0.7 data, explicit source pins and a separately pinned authorization-library
copy. The refreshed plan is not a run receipt. Actual CUDA runtime availability,
neural predictions and V25–V27 learning checks remain unproven until execution.
See `records/rpa_recorded_helm_20260922/q4_preparation/STATUS.md` for the exact
prepared job, current resource observations, failures and next command.

The September 22 continuation attachment explicitly withholds resource permission
and requires a currently authorized machine, workload, time/cost limit and retry
policy. Historical CPU rescoring permission and account balances do not establish
permission for this GPU job. No authorization or signature is fabricated.

Current test results, negative attempts and acceptance mapping are recorded in
`records/rpa_recorded_helm_20260922/VERIFICATION.md`.
