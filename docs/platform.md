# Multi-tenant platform

An **invite-only** service where each person gets an **isolated workspace**, set up in a few minutes
by the wizard from their CV and/or LinkedIn. Same app code as a one-person instance; the platform adds
a gateway and a provisioner (`platform/`). Use it to help several people (friends, a job club, an
outplacement group) from one server.

## Architecture

| Piece | Role |
|---|---|
| **Cloudflare Access** application | the only way in: Google, one-time e-mail code or any Access login method. Policy "everyone who authenticates"; *who gets a workspace* is decided by the gateway's invites |
| **gateway** `jobplatform-gateway` (port 8090, the only published port) | verifies the Access token, maps the e-mail to a workspace and forwards the request; `/_platform/*` = invite, account and admin pages; `/welcome` = public home page |
| **provisioner** `jobplatform-provisioner` (internal network only) | the only holder of the Docker socket; creates, stops, exports, upgrades and deletes workspaces with a fixed spec; API protected by a shared token |
| **workspace** `jat-<id>-web` + `jat-<id>-sched` | the normal app with the setup wizard, data in volume `jat-<id>-data` |

## Isolation of each workspace

- Own volume, own SQLite, own **/28 bridge network**: workspaces can't reach each other.
- Containers run as uid 1000 with a **read-only root filesystem**, `cap_drop: ALL`,
  `no-new-privileges`, 512 MB memory, 0.5 CPU, 128 processes, rotated logs.
- **Egress firewall** (`platform/egress.sh`, systemd unit `jobagent-egress`): internet yes; LAN,
  all private ranges and the Docker host itself **no**.
- Routing is by **verified e-mail only**: no URL, header or cookie leads to another workspace. Each
  workspace app re-checks the Access token for its owner.
- Uploaded CVs are parsed inside the workspace, in a CPU/memory/time-limited subprocess.
- Gateway: CSRF token on its forms, same-origin check on every POST, `X-Frame-Options: DENY`.
- The admin **cannot** open someone's workspace: ask them for an export.

## Install

On a Linux Docker host (VM, or an LXC with nesting) as root, with the repo checked out
(for example in `/opt/swiss-job-agent`):

1. **Cloudflare**: publish a hostname (Cloudflare Tunnel) to `http://<host>:8090` and create an
   **Access application** on it: your login methods, policy *Allow / Everyone*. Copy its
   **Application Audience (AUD) tag**.
2. `./install.sh platform` once: it creates `platform/.env` with fresh random secrets
   (`PLATFORM_SECRET`, `PROVISIONER_TOKEN`) and stops.
3. Edit `platform/.env`: `CF_TEAM_DOMAIN`, `CF_ACCESS_AUD`, `ADMIN_EMAILS` (who sees the admin page),
   `PUBLIC_URL`. Optional shared job-board keys (`ADZUNA_*`, `CAREERJET_API_KEY`, `JOOBLE_API_KEY`).
4. `./install.sh platform` again: installs the egress firewall unit, builds both images, starts the
   gateway and provisioner.
5. Open `https://<your host>/_platform/admin`, create an invite for yourself and go through the
   wizard once.

There is no login mode without Cloudflare Access, on purpose: test it behind a real Access application.

## Invite someone

Admin page → *Invite someone* → copy the link (shown once) → send it.

- **For one person** (default), optionally locked to their e-mail address.
- **For several people**: choose "up to 3 / 5 / 10 people" and share the same link, e.g. in a group chat.
  It stops working when that many workspaces were created, when it expires (3-30 days) or when you revoke it.
- `MAX_TENANTS` caps the total number of workspaces. Count roughly 300-400 MB of RAM per active workspace.

The person opens the link, signs in (see below), clicks **Create my workspace** and follows the wizard.

## Who can sign in, and the public home page

Signing in is Cloudflare Access; *having a workspace* is the gateway's invites. Two ways to set the
Access policy of the application:

- **Closed**: Allow → the e-mail addresses you list. You add each person before sending the invite.
- **Open sign-in**: Allow → *Everyone*, with the login methods Google and One-time PIN. Anybody can
  prove who they are with their own Google account or an e-mailed code, but without an invite they
  only see the home page ("you don't have a workspace yet"). Use this to onboard people you don't
  know the address of.

`/welcome` is the home page: what the service does, how to start, a link to the source code. It is
the only page the gateway serves without a login (plain text, no personal data). To make it reachable
without the Cloudflare login, add a second Access application for the path `<hostname>/welcome` with a
policy **Bypass → Everyone**; the more specific path wins over the main application. Signed-in people
without a workspace get the same page at `/`. `PROJECT_URL` and `CONTACT_EMAIL` in `platform/.env`
set the source link and an optional "ask for an invite" address.

## Operations

| Task | How |
|---|---|
| Upgrade platform + every workspace | `git pull && platform/upgrade.sh` (workspace by workspace, health-checked, rolled back on failure) |
| List workspaces | admin page, or `docker exec jobplatform-provisioner python -m jobplatform.provisioner list` |
| Pause / resume / re-create / delete | admin page (deleting asks for the id; data archived for `ARCHIVE_DAYS`) |
| Upgrade some workspaces only | `docker exec jobplatform-provisioner python -m jobplatform.provisioner upgrade <id>…` |
| A workspace's logs | `docker logs jat-<id>-web` / `jat-<id>-sched` |
| Check the egress rules | `iptables -S JOBAGENT-EGRESS` |
| Backups | back up the Docker volumes (`jobplatform_state`, `jat-*-data`); each person can export their own data from **Account** |

Workspace containers are read-only: `docker cp` into them fails; pipe scripts with
`docker exec -i jat-<id>-web python - < script.py`.

## What a new person does

1. Opens the invite link, signs in, clicks **Create my workspace**.
2. Imports a CV, LinkedIn PDF and/or LinkedIn data export, reviews the profile, picks target roles,
   town and commute radius, confirms the generated search. The first scan starts.
3. Later: **Settings**, **Edit my profile**, **Re-run the setup wizard**, and **Account** (download all
   data as `.tar.gz`, delete the workspace).
