# First committed bundle: check-process startup failure

The package was built from commit4cb8dfe7933ffb7d630417385561c7e90fbdb216.
Its17-member inventory, hashes and extraction passed. The wrapper then failed
while starting its clean child with the extracted directory as cwd:

```text
NotADirectoryError: [WinError 267] The directory name is invalid
```

This exception was observed in the interactive command output. No child receipt
was produced by that wrapper invocation. The extracted directory existed. A
separate direct Python -I -B invocation of the same --child check, using the exact
manifest pin, returned CLEAN_EXTRACTED_PURE_ADMISSION_PASSED. Thus this finding
concerns the Windows check-process working directory, not a failed worker import
or model execution.

The subsequent fix uses the Python executable's directory as the clean process
cwd, explicitly records it, and retains startup/timeout failures. Isolation and
the verified extracted module paths remain required. The next bundle directory
retains a complete fresh wrapper result. No files in this attempt were deleted
or overwritten; no neural or AWS execution occurred.
