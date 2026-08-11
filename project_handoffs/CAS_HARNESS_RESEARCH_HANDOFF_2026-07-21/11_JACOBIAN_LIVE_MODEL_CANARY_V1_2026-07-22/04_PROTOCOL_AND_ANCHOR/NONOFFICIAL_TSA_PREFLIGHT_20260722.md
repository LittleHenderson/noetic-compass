# Nonofficial DigiCert RFC3161 preflight

Date: 2026-07-22 PDT

Status: `PREFLIGHT_ONLY / NOT_THE_V1_PROTOCOL_ANCHOR / NOT_LICENSED`

Before submitting the official V1 anchor payload, a disposable query over the
preflight implementation manifest was sent to DigiCert's documented RFC3161
endpoint:

`http://timestamp.digicert.com`

The response:

- verified successfully against the retained DigiCert Trusted Root G4;
- used the requested policy OID `2.16.840.1.114412.7.1`;
- identified exactly one CMS signer;
- identified signer serial
  `0A80EF184B8DF10582D1C476A7957468`;
- identified signer SHA-256 fingerprint
  `4AA03FA22CD75C84C55C938F828E676B9CAECAB33FE36D269AA334F146110A33`;
- exposed the critical, time-stamping-only extended key usage; and
- contained a normal three-certificate chain.

The three-certificate live response revealed that the preflight verifier's
then-current requirement for exactly one embedded certificate was too strict.
That implementation checkpoint must not be used for the official anchor. The
replacement verifier must allow a bounded certificate chain while proving
that the one actual CMS signer—not merely an included certificate—is the
pinned responder.

The disposable query/response files live under `C:\tmp` and are deliberately
excluded from the official run evidence. The official protocol, anchor
payload, timestamp query, and timestamp response had not been created or
submitted when this note was written.
