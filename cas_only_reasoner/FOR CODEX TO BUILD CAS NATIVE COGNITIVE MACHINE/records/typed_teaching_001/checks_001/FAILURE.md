# Preserved aggregate reporting failure

The first guarded aggregate run exited with status 1 while JUnit tried to read
the local hostname. The overbroad audit hook refused `socket.gethostname`.
The output reached the 72-test completion dots, but no completed XML report or
acceptance receipt was produced. This directory is not a passing test receipt.

`runner_snapshot.py` preserves the exact failing runner, and
`inputs_before.json` preserves its input pins. The source and answer modules
were not changed for this repair. The next runner exempts only the local
hostname lookup; network operations, subprocesses, tensors, providers and old
all-split constructors remain blocked. It also retains a structured failure
record if pytest reporting fails again.
