# Agent instructions

## AWS execution preference — owner instruction, 2026-09-23

The owner said: "use aws as there is only 354 mb of 16 gbs locally" and asked
that all future agents be told. Use AWS for tests, builds, benchmarks, model
execution, training, and other memory-intensive or sustained compute. Keep
this laptop to lightweight editing, inspection, orchestration, and result download.
Do not silently fall back to local heavy execution if AWS is unavailable.
The 354 MB free out of 16 GB is the owner's reported snapshot, not a live measurement.
Record each cloud job's source, purpose, instance, resource/time/cost limits,
and cleanup. This instruction selects AWS for the current work; preserve
historical job records and their original device identities.

Read the project-specific AGENTS.md before changing project files.
