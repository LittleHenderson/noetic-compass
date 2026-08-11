# Novice Local Start Guide and Docker DNS Fix

This starts the local Noetic Compass/CAS API stack. It does not run the paid GPU diagnostic and does not create a customer-production `ACCEPT`.

The complete runnable checkout is currently:

`C:\Users\wakil\CAS-Harness-Run\noetic-compass-scaffold\noetic-compass`

The files under this handoff's `07_PROTECTED_IMPLEMENTATION_SNAPSHOT_81b5c18b` are an audited snapshot, not the whole application.

## First-time setup

1. Start Docker Desktop and wait until it says the engine is running.
2. Open PowerShell.
3. Go to the application folder:

```powershell
Set-Location C:\Users\wakil\CAS-Harness-Run\noetic-compass-scaffold\noetic-compass
```

4. Create `.env` only if it does not already exist:

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

5. Open it for editing:

```powershell
notepad .env
```

Never paste the contents of `.env` into chat, logs, screenshots, or this handoff.

## Validate and start

```powershell
docker compose config
docker compose pull redis postgres
docker compose up --build
```

Leave that PowerShell window open while the program is running.

Open these addresses in a browser:

- API health: `http://localhost:8000/health`
- Dashboard: `http://localhost:3000`

In a second PowerShell window, check status with:

```powershell
Set-Location C:\Users\wakil\CAS-Harness-Run\noetic-compass-scaffold\noetic-compass
docker compose ps
docker compose logs --tail 100 cas-api
```

To stop the local stack without deleting its named database volumes:

```powershell
docker compose down
```

Do not add `-v` unless you intentionally want to delete the local Redis/Postgres volumes.

## The Docker error previously encountered

The earlier message contained:

`lookup registry-1.docker.io: no such host`

That means Docker Desktop could not resolve Docker Hub's network address. It is a Docker/Windows DNS or proxy problem, not proof that CAS source code failed.

Run these checks:

```powershell
Resolve-DnsName registry-1.docker.io
docker info
docker pull redis:7-alpine
docker pull postgres:16-alpine
```

If `Resolve-DnsName` fails:

1. Confirm ordinary websites load.
2. Disconnect and reconnect the VPN if one is in use.
3. Run `ipconfig /flushdns`.
4. Quit and restart Docker Desktop.
5. Try the four checks again.

If Windows resolves the address but Docker still says it has no HTTPS proxy, open Docker Desktop → Settings → Resources → Proxies. Use the organization's actual proxy settings if the network requires one; do not invent proxy addresses.

Once both image pulls succeed, retry:

```powershell
docker compose up --build
```

## Separate Codex MCP timeout note

The `codex_apps` timeout is not required to run CAS locally. It affects how Codex starts its connector. If needed, open:

```powershell
notepad $env:USERPROFILE\.codex\config.toml
```

Add or update:

```toml
[mcp_servers.codex_apps]
startup_timeout_sec = 120
```

Save the file and restart Codex. Do not place credentials in `config.toml` merely to fix a startup timeout.

