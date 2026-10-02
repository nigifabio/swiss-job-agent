# Docker image and the `jobagent` wrapper

Two ways to run the same app:

| | From the source (clone) | Prebuilt image (no clone) |
|---|---|---|
| Get it | `git clone` + `./install.sh` | download `jobagent` + `./jobagent init` |
| Image | built on your machine | `ghcr.io/nigifabio/swiss-job-agent`, amd64 + arm64 (Raspberry Pi 4/5, Apple silicon) |
| Compose file | `docker-compose.yml` | `docker-compose.image.yml` |
| Update | `./jobagent update` (= `./install.sh upgrade`) | `./jobagent update` (pulls the new image) |

Both keep everything in `data/` next to the compose file and read settings from `.env`.

## Run the prebuilt image

```bash
mkdir swiss-job-agent && cd swiss-job-agent
curl -fsSLO https://raw.githubusercontent.com/nigifabio/swiss-job-agent/main/jobagent
chmod +x jobagent
./jobagent init     # downloads docker-compose.image.yml and creates .env (port, listen address)
./jobagent up       # pulls the image, starts web + scheduler, waits until healthy
```

Open http://127.0.0.1:8080 and follow the setup wizard. Every other setting is in `.env`
(documented in [`.env.example`](../.env.example)) or on the app's Settings page.

### Image tags

| Tag | What |
|---|---|
| `latest` | the newest build of `main` |
| `1.2.3`, `1.2` | a release, and the newest patch of that minor version |
| `sha-abc1234` | one exact build |

Pin a version by setting `IMAGE` in `.env`, e.g. `IMAGE=ghcr.io/nigifabio/swiss-job-agent:1.2`.

### Plain Docker Compose, without the wrapper

```bash
curl -fsSLO https://raw.githubusercontent.com/nigifabio/swiss-job-agent/main/docker-compose.image.yml
curl -fsSL https://raw.githubusercontent.com/nigifabio/swiss-job-agent/main/.env.example -o .env
mkdir -p data          # on Linux: sudo chown 1000:1000 data (the app runs as uid 1000)
docker compose -f docker-compose.image.yml up -d
```

Or a single container (no scheduled scans, use **Scan now**):

```bash
docker run -d --name jobagent -p 127.0.0.1:8080:8080 --env-file .env \
  -v "$PWD/data:/data" ghcr.io/nigifabio/swiss-job-agent:latest
```

## `jobagent` commands

The wrapper works in a clone (builds from the source) and in a folder with only the image.

| Command | What it does |
|---|---|
| `./jobagent init` | image mode: download the compose file, create `.env` |
| `./jobagent up` / `down` / `restart` | start (pull or build, then health check), stop, restart |
| `./jobagent status` | containers and health |
| `./jobagent logs [-f]` | web and scheduler logs |
| `./jobagent scan` | scan all sources now |
| `./jobagent rescore` | recompute match scores after changing `SCORE_KEYWORDS` in `.env` |
| `./jobagent discover <seeds>` | find company career sites: a seed list in the image (`app/companies.romandie.txt`, `app/companies.seed.txt`, `app/companies.vaud-services.txt`) or your own file in this folder |
| `./jobagent verify-boards` | re-check the watchlist, drop boards of other companies |
| `./jobagent update` | new version, with a backup first; goes back to the previous image or commit if the new one isn't healthy |
| `./jobagent backup` | database and files into `backups/` |
| `./jobagent shell` | shell inside the web container |

## The image

- Base `python:3.13-slim`, runs as the unprivileged user `app` (uid 1000), port 8080, data in `/data`.
- Built health check on `/healthz`.
- Built by GitHub Actions after the tests pass: see [releasing](releasing.md).
