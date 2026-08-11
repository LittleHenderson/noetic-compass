# CAS Forex Automated Trading Disclosure Draft

Status: draft for owner review and qualified legal/compliance review before any
public, hosted, paid, or multi-user use.

This draft is not legal advice and is not approval for launch or live-money
use.

## Product Intent

CAS Forex is intended to support owner-armed autonomous trading.

If the owner has enabled the relevant authority and the runtime gates pass, CAS
Forex may autonomously place orders, modify pending orders, set or modify stop
losses and take profits, partially close or fully close positions, scale
exposure, and flatten exposure.

## Standing Authority, Not Per-Order Approval

CAS Forex should not be described as requiring per-order human approval when
the owner has already delegated standing authority for live automation. The
owner is responsible for deciding whether to arm that authority and how wide to
set the risk envelope.

## Runtime Gates

Autonomous execution remains subject to gated backend paths, including:

- live-mode and owner-authorization switches;
- fresh broker truth and broker connectivity;
- edge authorization where configured;
- risk caps, margin checks, exposure limits, and drawdown controls;
- recovery and cooldown conditions;
- master kill / emergency-stop controls; and
- durable audit and receipt evidence.

## No Guarantee Of Trading Activity Or Profit

CAS Forex does not guarantee that an autonomous trading system will trade often,
trade continuously, avoid losses, or outperform manual trading. Runtime gates,
market conditions, broker constraints, or poor strategy conditions may block or
stand down automation.
