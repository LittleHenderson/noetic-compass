# CJT Syntax Grammar Spec

Date: 2026-06-17
Status: Draft research grammar, not approved production CAS compiler syntax

## Purpose

This file defines the first local grammar target for `CJT<>` syntax. It is a research/parser target only. It does not enable production compiler authority, live trading, broker `ACCEPT`, compiler-enforced safety claims, prompt-injection prevention claims, or governance/regulatory proof.

## Forms

Inline:

```text
CJT< cause | bias => effect >
```

Named:

```text
let cjt_name = CJT< cause | bias => effect > [beta=2.4, sat=0.95, cutoff=0.1, region=active];
```

Prefix-parameter form:

```text
CJT(beta=2.4)< cause | bias => effect >
```

## Terminals

- `cause`: required non-empty source terminal.
- `bias`: required non-empty modulation terminal.
- `effect`: required non-empty output terminal.

For production CAS compiler integration, terminals must later be formally typed against CAS state literals, symbolic refs, or approved trace refs. The current parser only proves IR shape and round-trip behavior.

## Parameters

- `beta`: finite float, `>= 0`.
- `sat` / `saturation`: finite float, `0..1`.
- `cutoff`: finite float, `0..1`.
- `region`: one of `cutoff`, `active`, `saturation`, `breakdown`, `unknown`.

## Required Separators

- `|` separates cause from bias.
- `=>` separates bias from effect.

## IR Fields

- `name`
- `cause`
- `bias`
- `effect`
- `beta`
- `saturation`
- `cutoff`
- `region`

## Claim Boundary

This grammar is not approved production syntax. It is sufficient for parser/IR tests and evidence sidecars only. Production CAS compiler integration still requires:

- Grammar approval.
- CAS terminal typing.
- IR serialization review.
- Formal semantics review.
- Invalid-form and round-trip tests inside the production compiler package.
- A signed statement that CJT syntax cannot create live broker `ACCEPT`.
