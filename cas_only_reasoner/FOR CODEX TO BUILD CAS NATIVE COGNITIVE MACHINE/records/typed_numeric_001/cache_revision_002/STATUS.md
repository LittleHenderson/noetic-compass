# Performance correction for a fresh full-course attempt

The first GPU job reached a full 564-row initial prediction seal, then began
teaching. It had 30 verified optimizer updates at 02:37:32 UTC and was still
running. Its original source and 1,800-second child limit are unchanged.

The proposed next revision removes redundant pure slot compilation with a
bounded cache. Complete public packet bytes and current profile bytes identify
an entry; malformed JSON types are rejected before lookup, outputs are copied,
and changed inputs or source profiles cannot reuse the old plan. It retains
the original uncached compiler for exact comparison. The account is 1,024
entries and at most 256 MiB of serialized retained content, not a heap-RSS bound.

85 pure tests passed, including exact cached/uncached plans for all 564 packets.
No tensors, private checker or provider execution was performed by those checks.
The independent review caught and corrected an overly narrow string limit in
the uninstalled prototype; valid long excerpts remain accepted.

The future numeric child limit is 3,300 seconds, with a 4,200-second whole
bootstrap limit. The existing 6,900-second boot watchdog, 7,200-second instance
envelope, one instance, zero automatic retries and $7 reservation are unchanged.
The learner admits at most 3,600 seconds, so 3,300 is within its bound. At the
$2.52/hour rate ceiling, two hours of compute plus the existing $1.48 ancillary
allowance total $6.52; $7 remains the reservation, not an invoice guarantee.
57 launcher and worker-contract pure tests passed after this limit change.
After the progress and partial-checkpoint changes, the combined worker,
launcher and worker-contract suite passed all 88 checks in 24.86 seconds.

This is a new source revision requiring a new archive, rehearsal, authority and
reservation. It does not revise the first job's records. The intended numerical
work remains 160 main updates plus two replay updates. No complete course or
learning advantage is established by these pure checks.
