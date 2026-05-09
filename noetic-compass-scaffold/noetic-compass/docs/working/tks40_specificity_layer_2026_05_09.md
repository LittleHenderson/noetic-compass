# TKS40 Specificity Layer for CAS-SDG Memory Compression

Status: paraphrased specificity bridge added for old TKS memory compression.

## Mapping

Original TKS used four planes and ten elements:

- A = Spiritual -> current CAS `P` / principled
- B = Mental -> current CAS `C` / cognitive
- C = Emotional -> current CAS `E` / evaluative
- D = Physical -> current CAS `O` / operational

Element numbers map to current Noetics:

- 1 -> `^1` Mind
- 2 -> `^2` Positive
- 3 -> `^3` Negative
- 4 -> `^4` Vibration
- 5 -> `^5` Female
- 6 -> `^6` Male
- 7 -> `^7` Rhythm
- 8 -> `^8` Above
- 9 -> `^9` Below
- 10 -> `^0` Idea

So `A1` becomes `^1^P`, `B10` becomes `^0^C`, and `D7` becomes `^7^O`.

## Why It Exists

Old memories often have more specificity than the modern compact CAS labels.
The TKS40 layer gives CAS-SDG short prompt hints when compressing old memory
text into CABS records.

Example:

`^7^O` can carry the extra hint:

`movement routine, music, time, dance, exercise, repeated action`

That lets a memory compressor distinguish operational rhythm from generic
"practice" without inserting long source prose into context.

## Guardrail

The implementation stores paraphrased hints, not long source passages. This
keeps the layer compact and makes it a compression aid rather than a raw text
dump.

## Code Surface

- `cas_native.belief.tks40_specificity.TKS40_ELEMENTS`
- `lookup_tks40("A1")`
- `lookup_cas_state("^1^P")`
- `compression_hint_for_cas("^7^O")`
- `compression_prompt_fragment("^4^C")`
