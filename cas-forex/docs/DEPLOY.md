# CAS Forex — Cloud Deploy (phone works independently of your desktop)

You chose **cloud hosting**: the engine (the "brain") runs 24/7 on a small
always-on server, and your **phone and desktop both connect to it as screens of
the exact same instance**. Your laptop can be off — the engine keeps running.

This is **one brain, many screens** — never two copies syncing (those would
drift apart). Everything below is about *where the one brain runs*.

---

## What ships in the image

A single container serves **both** the API (`/api/forex/*`) and the cockpit UI
from one port `8765`, so there's one URL for phone + desktop. State (ledgers,
operator memory, dials, targets, the owner token) lives in a mounted volume at
`/app/runtime` so it survives restarts — "same instance, continued exactly."

- `Dockerfile` — the image (Python 3.12; MetaTrader5 is **not** installed).
- `docker-compose.yml` — run it as a service with a persistent volume.
- `.dockerignore` — keeps local state/secrets out of the image.

> **Unverified locally:** there is no Docker on the build machine, so the image
> build itself hasn't been run here. The app code, cloud-auth, and single-port
> UI serving ARE tested. Build once in your environment and confirm before
> relying on it.

---

## The one caveat: live MT5 trading

The **paper/operator brain runs fine in the cloud** — it uses non-MT5 market
data (yfinance/OANDA), and `MetaTrader5` is optional (every import is guarded).
So cloud-hosting delivers full independence for the **paper/demo** stage you're
in now.

**Live MT5 execution needs the MetaTrader terminal, which is Windows-only.** When
you go live, we either:
- run the engine on a **Windows** cloud host, or
- keep a **thin MT5 relay on your Windows PC** that the cloud brain talks to.

Not a blocker today (you're on paper/demo). We'll wire the live path when you
flip to real money.

---

## Security (money app on the internet — non-negotiable)

1. **HTTPS only.** The owner token authenticates every request; over plain HTTP
   it travels in cleartext. Terminate TLS at a reverse proxy (Caddy/Traefik/
   Cloudflare Tunnel) or use a host that gives you HTTPS. Never expose `8765`
   raw to the internet.
2. **Owner token required for everything.** In cloud mode
   (`CAS_FOREX_CLOUD_MODE=1`) the app trusts NO request without a valid token —
   loopback is *not* trusted, because a reverse proxy makes every request look
   local. Set the token once at deploy:
   ```
   export CAS_FOREX_OWNER_TOKEN="$(python -c 'import secrets;print(secrets.token_urlsafe(32))')"
   ```
   Every device sends it as `Authorization: Bearer <token>` or
   `X-CAS-Owner-Token` (the cockpit stores it after you paste it once in the
   Owner Access panel).
3. **Real money still gated.** Hosting in the cloud changes nothing about the
   live-money gates — live trading, edge PASS, risk, and pilot checks all still
   run at action time.

---

## Option A — VPS + docker-compose (full control)

Any $5–10/mo Linux VPS (DigitalOcean, Hetzner, Vultr, Lightsail):

```bash
# on the server, in the cas-forex/ directory:
cd ui && npm ci && npm run build && cd ..
export CAS_FOREX_OWNER_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
echo "SAVE THIS TOKEN: $CAS_FOREX_OWNER_TOKEN"
docker compose up -d --build
```

Then put **Caddy** in front for automatic HTTPS (one file):

```
# Caddyfile
your-domain.com {
    reverse_proxy 127.0.0.1:8765
}
```
`caddy run` (or the Caddy service) gives you `https://your-domain.com` with a
free auto-renewing cert. Open that on your phone, paste the token in Owner
Access, done.

## Option B — Fly.io (easiest; built-in HTTPS, cheap)

Container-native, gives HTTPS + a persistent volume out of the box:

```bash
cd ui && npm ci && npm run build && cd ..
fly launch --no-deploy            # creates fly.toml; keep internal_port = 8765
fly volume create cas_runtime -s 1
# mount it at /app/runtime in fly.toml [[mounts]]
fly secrets set CAS_FOREX_OWNER_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
fly deploy
```
Fly serves it at `https://<app>.fly.dev` with HTTPS already on.

---

## What only you can do

Creating the cloud account and paying for it, and running the deploy — an AI
can't create accounts or enter payment. Everything above is copy-paste; when you
pick a host I'll tailor the exact commands and, if you want, add the `fly.toml` /
`Caddyfile` to the repo.

## After it's up

After deploy, run the web/phone smoke check from a machine that can reach the
HTTPS URL:

```bash
python scripts/run_web_phone_smoke.py \
  --web-base https://your-domain.com \
  --expect-cloud-api-auth \
  --owner-token "$CAS_FOREX_OWNER_TOKEN" \
  --skip-apk \
  --exit-code-on-failure
```

That verifies the public app shell/PWA assets load, `/api/forex/health` works
through the same origin, and a protected API route refuses no-token requests
while accepting the owner token. The smoke checker defaults to a 10-second
per-request timeout to allow cold cloud routes to answer; override it with
`--timeout-seconds <seconds>` when needed.

Open the HTTPS URL on your phone → **Owner Access** panel → paste the token →
you're on the same instance as your desktop, and it keeps running when your
laptop is off.
