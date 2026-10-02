# Installation

## Requirements

- Linux or macOS with **Docker** and the **compose plugin** (`docker compose version`), `git`, `curl`.
- About 1 GB of disk for the image, 512 MB of RAM.
- On Linux the app runs as uid 1000 inside the container: `data/` must be writable by it
  (the installer fixes it when run as root, otherwise it prints the `chown` to run).

A small VM or a Linux container (Proxmox LXC with nesting) works well.

## Install

```bash
git clone https://github.com/nigifabio/swiss-job-agent.git
cd swiss-job-agent
./install.sh            # or ./install.sh --yes to accept every default
```

The installer:

1. checks Docker, compose, git and curl;
2. creates `.env` from [`.env.example`](../.env.example) (mode 600) and asks:
   - **setup wizard** (default): import your CV / LinkedIn in the browser and let it build the search,
     or answer the search questions here instead (titles, region, languages, skills, sources);
   - **port** (8080) and **listen address** (`127.0.0.1` = this machine only);
3. builds the image and starts two containers: `web` (the interface) and `scheduler` (scans
   every 12 hours);
4. waits for `/healthz` and prints the address.

An existing `.env` is never overwritten; re-run `./install.sh` any time to rebuild and restart.
Day-to-day commands (scan, logs, backup, discover…) are in the [`jobagent` wrapper](docker.md#jobagent-commands).

Prefer not to clone and build? Use the [prebuilt Docker image](docker.md#run-the-prebuilt-image).

## First steps

1. Open http://127.0.0.1:8080 and follow the wizard (or fill `data/profile.json`, see
   [profiles, CVs and letters](profiles-cv-letters.md); an example is in
   [`examples/profile.example.json`](../examples/profile.example.json)).
2. Press **Scan now** on the homepage. The first scan takes a few minutes.
3. Open a job, mark skills you have, generate a CV and letter, apply, track.

## Upgrade

```bash
./install.sh upgrade
```

Takes a backup, `git pull --ff-only`, rebuilds, restarts and checks health. If the new version
isn't healthy it checks out the previous commit and starts it again. Database changes are applied
automatically at start-up. It refuses to run if you changed tracked files (commit or stash first).

## Backup and restore

```bash
./install.sh backup      # -> backups/YYYYMMDD-HHMMSS.tar.gz (mode 600)
```

The archive holds all of `data/`: the database (a consistent copy taken from the running app),
`profile*.json`, `settings.json`, the watchlist and generated PDFs. Your `.env` is not included:
keep a copy of it somewhere safe, it may hold API keys.

Restore: stop (`docker compose down`), unpack the archive in the repo folder (it recreates
`data/`), rename `data/jobs.backup.db` to `data/jobs.db` if present, then `./install.sh`.

## Reaching it from other devices

The app has **no login of its own**. By default it only listens on `127.0.0.1`. To use it from your
phone or another computer, choose one of:

- **VPN** (Tailscale, WireGuard): set `BIND_ADDR` to the machine's VPN address, so only devices on
  your VPN can reach it. Or keep `127.0.0.1` and use an SSH tunnel (`ssh -L 8080:127.0.0.1:8080 host`).
- **Cloudflare Tunnel + Cloudflare Access** (recommended for the internet): create an Access
  application for your hostname, then set in `.env`:
  ```
  CF_TEAM_DOMAIN=your-team.cloudflareaccess.com
  CF_ACCESS_AUD=<the application's Audience (AUD) tag>
  ALLOWED_EMAILS=you@example.com
  ```
  The app then verifies the Access token on every request itself, so even someone on your LAN
  gets 403 without a valid login.
- **Reverse proxy on another machine** (nginx, Caddy, NPM): set `BIND_ADDR=0.0.0.0` and make sure
  the proxy authenticates (Access, OAuth proxy, basic auth). Never expose port 8080 directly.

After changing `.env`: `docker compose up -d`.

## Optional: more sources

Aggregator keys (free) and a job-alert mailbox are described in [sources](sources.md). Put the
values in `.env` and restart.

## Uninstall

```bash
docker compose down --rmi local
```

then delete the folder (after a backup if you want to keep your data).
