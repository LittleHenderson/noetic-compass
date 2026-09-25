# HELM 2x launch record
The single fresh 20-pass job launched on AWS at 2026-09-25 15:22:20 UTC.
Source: b981625fdc9c28a5c80a18453216686a1d5357af.
Instance: i-0adf52b7fa801e08b, g7.2xlarge, us-west-2.
Seed: 20260918. Constant learning rate: 0.003. No best-checkpoint selection.
All 33 focused tests passed. The public preflight checks all 1,470 prefix steps;
H1 and H3 pass. H2 uses the explicitly permitted fresh 20-pass route and does
not claim restoration of R18. Both pass-10 state files are required outputs.

Projected instance duration is 17,795.13 seconds (4.94 hours), expected cost
$13.94. Reservation plus other-services allowance is $19.30 within the $20
all-services cap. Instance limit is 25,200 seconds; the independent guest
shutdown timer was observed armed for 24,900 seconds from boot.
Automatic retries: zero. A global check of all 17 enabled regions found no
other GPU job before launch.

The frozen admission, package and observed launch receipts accompany this note.
The package locator is an identical receipt pointing at the already hashed
archive; it changes no scientific or authority bytes.

Status at this commit: AWS instance launched, results and cleanup pending.
EC2 running status alone does not prove optimizer progress or scientific success.
CAS remains separate and cannot delay this run. Its stopped predecessor is
unaccepted; a new CAS job requires the newly requested source and instance gates.
