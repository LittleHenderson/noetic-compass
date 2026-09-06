# H100 quota request — pending at submission

The owner requested faster GPU hardware and approved a $400 total AWS cap.
At 2026-09-06 01:23 UTC, the account's us-west-2 On-Demand P quota was zero,
with no existing requests. EC2 reported that p5.4xlarge has one 80 GiB H100 and
requires 16 vCPUs. A request for exactly 16 P-instance vCPUs was submitted.

- Request ID: `7b94b9c2dd564a999316b4217037c59fd72Ae8fc`
- Quota: `ec2 / L-417A185B`, Running On-Demand P instances
- Region: `us-west-2`
- Provider status at submission: `PENDING`
- Provider request ID: `cccd4874-94c9-4d23-9b21-2150fb3740ae`
- Request receipt SHA-256: `464bef246f0c36ce62538d783356ed506160d51fcd93e410f4ba176044671b2a`

`request_receipt.json` preserves the before-state, request history and actual
provider response. `request_once.py` refuses to resubmit after any recorded
attempt. Resolve an uncertain response by reading history, not by retrying.

No instance was launched, no GPU reservation was added, and the $400 spending
cap did not change. Quota approval is not proof of capacity or a speed advantage
over the current Blackwell instance. Check the request status, actual quota,
current price and availability before any future launch. Do not change or
restart the active frozen v3 campaign to use this request.
