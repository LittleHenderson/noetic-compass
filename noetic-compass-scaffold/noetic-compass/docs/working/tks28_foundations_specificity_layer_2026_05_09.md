# TKS28 Foundations Specificity Layer

Status: paraphrased Drive x Register specificity bridge added for CAS-SDG
memory compression.

Source inspected:

`C:\Users\wakil\Downloads\Everthing-Tootra-TKS\28 fOUNDATIONS 1.0.pdf`

The source enumerates 28 positions: 7 foundations across 4 worlds.
CAS v7.5 maps that surface to 7 Drives across 4 Registers.

## Mapping

Worlds:

- `a` spiritual -> `|T` Transcendent
- `b` mental -> `|A` Analytical
- `c` emotional -> `|f` Affective
- `d` physical -> `|E` Embodied

Foundations:

- `1` -> `F1` Unity
- `2` -> `F2` Wisdom
- `3` -> `F3` Vitality
- `4` -> `F4` Connection
- `5` -> `F5` Agency
- `6` -> `F6` Structure
- `7` -> `F7` Purpose

Examples:

- `1a -> F1|T`
- `2b -> F2|A`
- `4c -> F4|f`
- `7d -> F7|E`

## Use In CAS-SDG Compression

The layer provides short hints for drive-register memory compression.

Example:

`F4|f` carries the hint:

`affection, intimacy, vulnerability, empathy, emotional bonding`

That can specialize a memory tagged with connection in the affective register
without carrying the long source description into prompt context.

## Guardrail

The source contains metaphysical, magical, and culturally specific claims.
The code stores paraphrased structural hints only. It does not assert the
source's metaphysics; it uses the source to enrich CAS compression vocabulary.

## Code Surface

- `cas_native.belief.tks28_foundations.TKS28_FOUNDATIONS`
- `lookup_tks28("1a")`
- `lookup_drive_register("F1|T")`
- `foundation_hint_for_drive_register("F7|E")`
- `foundation_prompt_fragment("F4|f")`
