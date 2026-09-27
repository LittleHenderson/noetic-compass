# Owner account transfer: supported procedure

Prepared 2026-09-26 after a leaked invitation. Nothing here is executed without the owner.

## The two request bodies, exactly

An earlier handover told the owner to send `invite_code`. **That field does not exist.** The
model is `RedeemRequest` in `api/routes/accounts.py` and the field is **`code`**. Getting this
wrong costs a round trip and, worse, encourages re-pasting credentials into a chat while
debugging. The exact shapes:

```jsonc
// POST /accounts/invite            (role-gated: operator, admin or owner)
{
  "role": "owner",                 // optional; must be a role the caller may grant
  "target_email": "owner@example.com",
  "expires_at": null,              // optional ISO-8601; default 24h, maximum 7 days
  "max_uses": 1                    // 1..10
}
// -> { "code": "...", "role": "owner", "expires_at": "...", "max_uses": 1, "uses": 0, ... }

// POST /accounts/invite/redeem     (public: a new user has no token)
{
  "code": "<the code from the invite>",        // NOT "invite_code"
  "email_or_username": "owner@example.com",
  "api_credential": "casak_<43-128 of [A-Za-z0-9_-]>",
  "display_name": null                          // optional
}
// -> AccountResponse, with api_credential always null
```

`RedeemRequest` deliberately has **no** role, tenant_id or account_id field: the role and tenant
come from the invite record, so a caller cannot escalate its own privilege.

## Why not a rename

The account store has no rename. `POST /accounts/bootstrap` creates the one first owner, and
`recover_bootstrap_owner` re-binds *that same account* to a new credential — it looks the account
up by `email_or_username`, so it cannot change the identifier. There is no supported way to turn
`migration-verification@noeticcompass.com` into the owner's real address. The supported path is
**invite + redeem**.

## Procedure

### 0. Handle anything already exposed first

A leaked invitation is a live bearer credential until it is consumed or expires. It is single
use, addressed to one address, and expires. The fastest way to make it harmless is to **consume
it by redeeming it** — which is also the step that creates the account. If redemption fails with
"already used", someone else consumed it, and the recovery path below applies instead.

### 1. Owner supplies their real address (blocking)

### 2. Confirm the current owner path still works

Log in as `migration-verification@noeticcompass.com` and make one authenticated request. A
failure here must not be confused with a failure of the transfer.

### 3. Service issues an invite, role `owner`, addressed to the owner

Default 24-hour expiry. The code is returned once. It is delivered to the owner directly and is
never written to the repository, a shared log, or a document. It is a bearer credential until
redeemed.

### 4. Owner redeems it with a credential only they hold

Body as above, field `code`. The credential must match `^casak_[A-Za-z0-9_-]{43,128}$`. The
service never stores it in plaintext and never returns it.

### 5. Verify three things before retiring anything

1. **Login** — `POST /auth/token` with `{username, api_credential}` returns a token.
2. **Owner permission** — an owner-only action succeeds. Issuing an invite
   (`POST /accounts/invite`) is role-gated; a member token is refused with 403, so a 200 proves
   the role rather than assuming it.
3. **Recovery** — the owner rotates their own credential
   (`POST /accounts/credential/rotate` with `{api_credential: <new>}`) and signs in with the new
   one. This proves they can regain access unaided.

### 6. Then retire the temporary access

- Reset the temporary account's credential: `POST /accounts/credential/reset/{account_id}`, issued
  from the new owner account. It can no longer be used.
- Do not delete the temporary account while it is the only working owner.
- `NC_ACCOUNT_BOOTSTRAP_SECRET` stays until step 5 passes: it is also the only route back to the
  existing owner account, so removing it early trades a working recovery path for a tidier
  secret list.

## If the account exists but its credential was set by someone else

An operator holding the temporary owner can reset it:
`POST /accounts/credential/reset/{account_id}` with a new credential, delivered to the owner
through a channel that is not this repository and not a chat transcript. The owner then signs in
and rotates immediately (step 5.3), so the operator's value stops being usable.

## Never

- Never paste a credential, invite code, or bootstrap secret into chat, a screenshot, an issue, or
  a source file — not even partially. A prefix is still a leak: it trains the habit that leaks a
  whole one.
- Never delete the account or the bootstrap secret while the owner's access is unverified.
