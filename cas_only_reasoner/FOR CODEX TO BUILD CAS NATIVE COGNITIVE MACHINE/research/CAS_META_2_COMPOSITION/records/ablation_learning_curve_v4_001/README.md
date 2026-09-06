# Late-training curve: improvement was uneven

The script checks the original partial packet hash, reads only its retained
scalar history, confirms all 60 epochs are present, and matches the final
validation record to the preserved selected-checkpoint metadata. It does not
load weights or run a model. Missing free-generation checks are not counted
as zero scores.

| Epoch | CAS joint matches /96 | CAS depth-three /32 | Generic joint matches /96 | Generic depth-three /32 |
| --- | ---: | ---: | ---: | ---: |
| 50 | 39 | 5 | 60 | 18 |
| 55 | 40 | 4 | 68 | 18 |
| 60 | 43 | 4 | 69 | 19 |

CAS's unweighted token loss also rose from 0.0600 at epoch 50 to 0.0696
at epoch 60 while its overall generated joint score improved. Checkpoint
selection prioritized worst-depth and macro-depth generated matches, not the
lowest token loss.

This supports an uneven-progress diagnosis, not a claim that longer training
must fix deeper composition or that more training cannot help. A later
experiment should distinguish training duration, structural curriculum and
decoder effects instead of changing all of them and attributing the result
to one cause.

These are old development measurements from an incompletely audited run.
They are not native task outcomes, fresh held-out results, CAS advantage
or new accepted learning. The currently running decoder comparison is unchanged.
