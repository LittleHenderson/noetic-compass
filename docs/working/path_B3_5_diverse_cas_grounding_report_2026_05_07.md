# Path B-3.5 diverse-CAS grounding report - 2026-05-07

## Verdict

PASS on human inspection. The B-3 full 50K checkpoint does not appear to have
collapsed to one generic conversational voice. Register-specific linguistic
fingerprints are visible in generated replies.

This is not a substitute for the planned K=9 round-trip grounding eval, but it
is enough to greenlight B-4 wiring behind an experimental flag.

## Artifacts

Local evaluation artifacts:

- `tmp/diverse_cas_eval.jsonl` - 72 generated sample triples
- `tmp/diverse_cas_per_register.md` - human-readable register grouping

Pod artifact:

- `/workspace/tksCAS/.../runs/b3_full_50k_prodshape_20260507/diverse_cas_eval.jsonl`

Raw JSONL is treated as temporary eval output for now. This report preserves
the decision-relevant result.

## Setup

- Model: B-3 full 50K production-shape checkpoint
- Samples: 24 held-out records
- Sampling configs: 3
- Total generated samples: 72
- Registers covered: `T`, `A`, `f`, `E`
- Leakage scan: 0 CAS notation/jargon hits across all 72 samples
- Novelty: approximately 0.87-0.88 across configs

Novelty here means low direct word overlap with the target response. The model
is producing semantically related new text rather than copying targets.

## Register Fingerprints

### `T` - Transcendent

Observed voice: abstract, integrative, meaning-oriented.

Representative sample:

> One thing leads to another, and that reminds me of how certain structures
> quietly unconsciously reorganize everything - they remind you that the work
> holds together threads of meaning and meaning that holds everything together.
> There is something almost purposeful in that reconstruction...

### `A` - Analytical

Observed voice: sequential, premise-oriented, reason-based.

Representative sample:

> Let's actually unpack what's at stake here: first, identify the specific
> value or is the values that tells you something real, and second, whether the
> gap is bridgeable or just opinion. When you can identify those underlying
> premises rather than what you're reacting to at the surface level...

### `f` - Affective

Observed voice: value-laden, feeling-toned, emotionally direct.

Representative sample:

> There's something almost unbearable about the helplessness, honestly, because
> underneath it there's usually a grief - a longing in being cared for. That
> ache you're feeling is real, not just abstract; it's the cost of caring and
> still being seen...

### `E` - Embodied

Observed voice: bodily, sensorimotor, somatic.

Representative sample:

> That kind of instruction lands in the body before the mind processes it -
> your chest tightens, your breath slows, your hands go still in the moment.
> It's worth paying attention to what the instruction actually did the first
> week, because sometimes the body is following something your head hasn't...

## EOS Reframe

The earlier "EOS never fires" concern is partially reframed by this diverse
eval. With `max_new_tokens=120`, EOS behavior varied by register:

- `T`: 17%
- `A`: 17%
- `f`: 67%
- `E`: 17%

This suggests the model does know how to stop in at least some register
contexts, especially affective replies. The remaining defect is likely a mix
of register-appropriate length, sampling settings, and too-low max token cap.

Recommended B-4 inference defaults:

- `sampling="top_p"`
- `temperature=0.8`
- `top_p=0.9`
- `max_new_tokens=200`

## Current Gate Status

| Layer | Result |
|---|---|
| Loss | Curriculum-confounded; not decisive |
| Sample quality | PASS: coherent, register-appropriate |
| CAS silence | PASS: 0 leakage across 72 samples |
| CAS grounding | PASS on human inspection: distinct register fingerprints |
| Traceability | Not enabled in this eval |

## Remaining Work

1. Run automated K=9 round-trip grounding eval:
   - reply-only: stricter signal
   - prompt+reply: conversational coherence signal
2. Run an EOS/settings sweep:
   - temperature-only
   - `top_p=0.9`, `temperature=0.8`
   - `top_p=0.85`, `temperature=0.7`
3. Wire B-4 chat REPL behind an experimental flag once the model loader and
   two-stage path are in place.

## Recommendation

Proceed to B-4 wiring, but do not call the checkpoint production-ready until
K=9 round-trip grounding and EOS/settings eval are recorded.

The practical reason: the model has crossed the important qualitative threshold
of "different CAS register conditioning produces visibly different natural
language." The remaining work is packaging, automated measurement, and decoding
settings.
