# Stage 27J Output-Side Component Attribution

**Status:** `PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION`

## Contracts

- Stage 7 prefix source: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- Stage 27I source: `NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED`
- Learn/eval disjoint: `True`

## Learned Covers

- Carrier cover: `L10MLP`, `L8MLP`, `L9H7`, `L9MLP`, `L8H11`, `L8H10`
- Eraser cover: `L11MLP`, `L9H3`, `L11H11`, `L10H6`, `L11H9`, `L10H3`
- Carrier random-control exact layer/kind: `False`
- Eraser random-control exact layer/kind: `False`

## Held-Out Evaluation

- Carrier drop mean: `0.320940`
- Random carrier drop mean: `-0.780190`
- Carrier drop > random: `39 / 56` (share `0.6964`, p `0.00228077`, mean delta `1.101130`)
- Eraser lift mean: `0.822302`
- Random eraser lift mean: `-0.072137`
- Eraser lift > random: `39 / 56` (share `0.6964`, p `0.00228077`, mean delta `0.894439`)

## Top Learned Carrier Components

- `L10MLP` mean_drop `0.192630` positive_share `0.6250`
- `L8MLP` mean_drop `0.058109` positive_share `0.6071`
- `L9H7` mean_drop `0.043651` positive_share `0.6786`
- `L9MLP` mean_drop `0.042285` positive_share `0.5179`
- `L8H11` mean_drop `0.041832` positive_share `0.5893`
- `L8H10` mean_drop `0.033794` positive_share `0.6607`
- `L8H8` mean_drop `0.031859` positive_share `0.5893`
- `L10H1` mean_drop `0.028603` positive_share `0.6429`
- `L9H9` mean_drop `0.027447` positive_share `0.5536`
- `L8H7` mean_drop `0.027126` positive_share `0.5714`

## Top Learned Eraser Components

- `L11MLP` mean_lift `0.736830`
- `L9H3` mean_lift `0.020213`
- `L11H11` mean_lift `0.008355`
- `L10H6` mean_lift `0.007670`
- `L11H9` mean_lift `0.006635`
- `L10H3` mean_lift `0.003688`
- `L11H0` mean_lift `0.000363`
- `L11H1` mean_lift `-0.001930`
- `L10H4` mean_lift `-0.003195`
- `L9H10` mean_lift `-0.003251`

## Boundary

Stage 27J is bounded late-layer output-side component attribution for Pythia-160M semantic likelihood margins. It is not complete circuit discovery, not model-wide control, not weight editing, and not visible free-form generation control.
