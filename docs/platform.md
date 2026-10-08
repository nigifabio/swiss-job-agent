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

**Account requests:** the home page has a *Request an account* button. The person signs in first (so the
address is verified), gives a name and a short message; the request appears on the admin page with **Approve** /
**Decline**. An approved person finds a *Create my workspace* button on the home page at their next visit. Set
`NOTIFY_WEBHOOK` in `platform/.env` (a URL taking `POST {"msg": "..."}`, e.g. a Telegram bridge) to be told about
new requests; the provisioner posts it, because the gateway has no access to the LAN.

**Same person, two addresses:** on the admin page, *add an address* under a workspace lets its owner sign in
with another e-mail too (their Gmail next to their Hotmail). Both open the same workspace; an address can only
belong to one workspace.

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
| Backups | every night (`BACKUP_HOUR`, default 03:00 UTC) the provisioner writes one archive per workspace plus the platform database to `platform/backups/` (`BACKUP_HOST_DIR`), keeping the newest `BACKUP_KEEP` (14) of each; `... provisioner backup` runs it now. Point `BACKUP_HOST_DIR` at a NAS mount, or copy the folder elsewhere, so the copies don't live on the same disk. Each person can also export their own data from **Account** |
| Restore one workspace | stop it on the admin page, then `docker run --rm -v jat-<id>-data:/data -v "$PWD/platform/backups":/b alpine sh -c "rm -rf /data/* && tar -xzf /b/<id>-<stamp>.tar.gz -C / && chown -R 1000:1000 /data"`, and resume it |

### What the admin page shows about a workspace

**Activity and scan health** lists, per workspace: when it was last used, when it last scanned, how many
jobs it holds (new, applied, all) and how each job source did at the last scan (postings found, and an
error kind such as `HTTP 403` when it failed). These are totals: each workspace answers a counts-only
address (`/ops/summary`) that needs a token derived for that workspace; no job title, company, name or
text leaves a workspace, and there is no page to look inside one.

Above the table, **what needs a look**: an app that is not healthy, a workspace whose scans stopped,
a source failing and for how many workspaces, a backup that didn't run. Every `HEALTH_CHECK_HOURS`
(default 6) the same list is checked and, when it changed, sent through `NOTIFY_WEBHOOK`.

### Bug reports and feature requests

The 💬 link of the top bar opens `/_platform/feedback`: a signed-in person writes what doesn't work or what they would
like. The message is kept (admin page, with Done / Reopen), and sent through `NOTIFY_WEBHOOK` with the sender's address
and the page they came from. At most eight a day per person; nothing from the workspace is attached.

### The forum

`/_platform/forum` (link "Forum" in the top bar): topics about the job search in six subjects (CV and letters, interviews,
ORP / RAV, training, leads, everything else), with replies. People write under the same username as in the league; taking a
username for the forum does not put them on the league board. Only people with a workspace can read it. Text only, escaped;
thirty messages a day per person. Authors can remove their own messages and administrators any message; a new topic is
announced through `NOTIFY_WEBHOOK` so it can be looked at.

### The league

`/_platform/league`: people join by choice with a nickname. The gateway asks only the members' workspaces for their score
(the `game` part of the counts-only `/ops/summary`: points, streak, level and badge keys) and ranks them. Nothing else is
shared between workspaces; the board never shows an e-mail or a workspace id.

### Calendar feeds

A person's calendar address is `https://<host>/welcome/cal/<workspace>/<key>.ics`. Calendar apps can't
sign in, so this path must be public like `/welcome`: the Cloudflare Access bypass for `/welcome` already
covers it. The gateway passes only that one request to the workspace, which checks the key; repeated
wrong keys from one address are refused for ten minutes.

Workspace containers are read-only: `docker cp` into them fails; pipe scripts with
`docker exec -i jat-<id>-web python - < script.py`.

## What a new person does

1. Opens the invite link, signs in, clicks **Create my workspace**.
2. Imports a CV, LinkedIn PDF and/or LinkedIn data export, reviews the profile, picks target roles,
   town and commute radius, confirms the generated search. The first scan starts.
3. Later: **Settings**, **Edit my profile**, **Re-run the setup wizard**, and **Account** (download all
   data as `.tar.gz`, delete the workspace).
