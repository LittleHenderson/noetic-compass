# CAS Forex Legal Review Checklist

Status: owner/legal intake checklist. This is not legal advice, not counsel
approval, and not public-launch authorization.

Use this checklist before public launch, hosted use, paid access, multi-user
access, live-money marketing, or advising others for compensation.

## Counsel Scope

- Identify qualified counsel or compliance reviewer.
- Confirm the reviewed product scope, including web app, phone access,
  assistant chat, Operator automation, MT4/MT5 bridge, Hugo's Way or other
  broker connectivity, money movement, notifications, and audit exports.
- Record the reviewed jurisdictions and user classes.
- Confirm whether any commodity trading advisor, investment adviser, broker,
  introducing broker, signal provider, or money transmitter analysis is needed.
- Confirm whether retail forex, CFDs, indices, metals, crypto, or similar
  instruments require additional registration, disclosure, or launch limits.

## Required Document Review

- Terms of Service.
- Privacy Policy.
- Risk Disclosure.
- Automated Trading Disclosure.
- AI Limitations Disclosure.
- Broker Connectivity Disclosure.
- Paper/demo/live separation disclosure.
- No profit guarantee and no guaranteed balance growth language.
- Support, contact, dispute, refund, and billing terms if public or paid.
- Data retention, data deletion, export, incident, and account closure process.
- Autonomous execution correction / product-authority summary describing
  owner-armed AI trading and configured money movement.

## Trading And Broker Review

- Confirm automated trading language accurately describes owner controls,
  risk gates, live authorization, emergency controls, and broker-state
  reconciliation.
- Confirm autonomous execution language accurately describes standing
  owner-delegated authority, including that per-order or per-transfer human
  confirmation is not the normal operating mode once the owner has armed
  authority.
- Confirm broker execution boundary language is clear: pricing, spreads,
  swaps, margin, leverage, fills, withdrawals, account terms, and custody are
  controlled by the broker or provider.
- Confirm configured money-movement language is clear: provider rails,
  allowlisted destinations, transfer caps, receipts, event hashes, and
  emergency-stop / master-kill behavior.
- Confirm retail forex risk disclosure is understandable and visible before
  live-money use.
- Confirm the app does not state or imply guaranteed profits, guaranteed
  withdrawals, guaranteed execution quality, or guaranteed loss avoidance.

## Privacy And Security Review

- Confirm the app never exposes broker credentials, API secrets, webhook
  secrets, card data, bank credentials, or raw payment credentials to browser
  JavaScript.
- Confirm the Privacy Policy covers trade evidence, owner settings, diagnostic
  logs, notification destinations, retention, export, deletion, and incident
  handling.
- Confirm support workflows do not require users to disclose secrets in chat,
  screenshots, tickets, or logs.

## Public Launch Gate

Public launch remains blocked until counsel completes a separate review record.
Draft documents and this checklist are only preparation evidence.

Counsel review record file:

```text
docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md
```

Minimum accepted record markers:

```text
counsel_review_status: accepted
reviewed_by: <qualified reviewer or firm>
review_date: <YYYY-MM-DD>
scope: Terms, risk disclosure, privacy, automated trading, AI limitations, autonomous execution, broker connectivity, money movement, retail forex, public launch
```

Only a qualified reviewer should complete the accepted record.
