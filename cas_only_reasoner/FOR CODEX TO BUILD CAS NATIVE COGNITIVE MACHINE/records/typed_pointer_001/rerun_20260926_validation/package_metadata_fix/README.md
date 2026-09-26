# Prospective package metadata correction

**Prepared only; not authorized or executed.** AST syntax passed. No corrected package has been built on AWS.

The focused AWS run passed 41 cases and 6 subtests. Its count wrapper stopped before packaging. The subsequent package-only job failed when the exact-source packager queried whole Git directories: omitted unrelated blobs in the public partial checkout have size `BAD`.

`build_exact_package.py` narrows only that packaging process's metadata query to the complete declared input list. It uses real Git output and keeps the original source, Git objects, package members, object-ID/size/SHA checks, 128 required artifacts and pass-10 checkpoint requirements.

The proposed AWS command is:

    python3 -B build_exact_package.py --project-root <exact-public-a5fc-checkout> --output <fresh-package-directory> --payload-manifest <public-payload-manifest> --payload-manifest-sha256 <frozen-hash> --source-sha a5fcf527b5f2c47a3a9b1f170977c55371845af0

A fresh job and payload must be frozen after new owner authorization. The failed identities and reservations remain unchanged. This phase would run no tests or training.

The proposed single build is capped at $0.10 and 600 seconds. Preserved validation/package reservations ($0.60/$0.10), planned training reservation ($19.20), and other allowance ($0.10) bring the revised conservative total to **$20.10**. This exceeds the current $20 authorization. Measured training runtime itself still fits its existing envelope.

No new paid attempt, source.zip, training admission or training instance has been created.
