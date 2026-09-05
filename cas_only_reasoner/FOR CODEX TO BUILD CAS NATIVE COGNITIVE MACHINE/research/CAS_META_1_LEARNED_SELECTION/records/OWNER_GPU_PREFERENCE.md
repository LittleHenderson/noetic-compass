# Owner GPU direction

On 2026-09-05, the owner asked whether an H100 would be faster and directed:
"if so please don't use this slow ass shit again."

The builder committed to no further T4 use for this task. The owner then said
"go". Continue within the existing $100 AWS task cap, using a faster available
GPU for profiling and completing evaluation. Do not retrain or change the
already-sealed predictions after held-out answers were opened.

The first T4 job trained both candidates successfully, but native evaluation
hit its time ceiling. Its failure evidence and candidate checkpoints must be
preserved. H100 availability and whole-pipeline speedup are not yet established.
