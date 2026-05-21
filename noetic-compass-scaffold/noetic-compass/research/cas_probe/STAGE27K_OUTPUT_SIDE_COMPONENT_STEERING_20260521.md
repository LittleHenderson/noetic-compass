# Stage 27K Output-Side Component Steering

**Status:** `GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL`

## Contracts

- Stage 7 prefix source: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`
- Stage 27J source: `PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION`
- Held-out eval only: `True`

## Covers

- Carrier cover: `L10MLP`, `L8MLP`, `L9H7`, `L9MLP`, `L8H11`, `L8H10`
- Eraser cover: `L11MLP`, `L9H3`, `L11H11`, `L10H6`, `L11H9`, `L10H3`
- Carrier scale: `2.0`
- Eraser scale: `0.0`
- Carrier flip scale: `-1.0`

## Held-Out Evaluation

- Combined increment mean: `0.557552`
- Random combined increment mean: `-0.292661`
- Combined > random: `30 / 56` (share `0.5357`, p `0.34444`, mean delta `0.850213`)
- Carrier amplification increment mean: `0.092256`
- Eraser suppression increment mean: `0.822302`
- Carrier flip reduction mean: `0.736053`
- Random carrier flip reduction mean: `0.198312`
- Carrier flip > random: `28 / 56` (share `0.5000`, p `0.553073`, mean delta `0.537741`)

## Boundary

Stage 27K is bounded late-layer intervention steering over Pythia-160M CPL2 likelihood margins. It is not complete circuit discovery, not weight editing, not model-wide control, not cross-model control, and not visible free-form generation control.
