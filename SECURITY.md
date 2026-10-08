# Security

## Reporting a vulnerability

Please use GitHub's **private vulnerability reporting** (Security tab → *Report a vulnerability*)
rather than a public issue. You'll get an answer within a few days.

## Security model

The app holds personal data (your CV, your applications, notes about employers), so:

- **It has no login of its own.** It listens on `127.0.0.1` by default. Anything wider must go
  through an authenticating layer: Cloudflare Access (verified by the app itself when
  `CF_TEAM_DOMAIN` and `CF_ACCESS_AUD` are set, with an optional `ALLOWED_EMAILS` list), a VPN, or an
  authenticating reverse proxy. See [docs/installation.md](docs/installation.md#reaching-it-from-other-devices).
- **Cross-site requests are refused:** every state-changing request must come from the app's own
  origin (`Sec-Fetch-Site` / `Origin` check), and pages can't be framed (`X-Frame-Options: DENY`).
- **HTTPS only on the platform:** a visitor arriving over plain http is redirected, and pages send HSTS.
- **Two addresses work without a sign-in, each with its own secret.** The calendar feed
  (`/calendar/<key>.ics`): a 192-bit random key in the address, read-only, dates with job titles and
  company names only; "New address" in Settings revokes it. The operator's totals (`/ops/summary`):
  only when `OPS_TOKEN` is set (the platform sets one per workspace), and it returns counts, never content.
- **Output is escaped** (Jinja autoescape); stored links are kept only if they are `http(s)`.
- **Secrets stay out of git and logs:** `.env` (mode 600) and `data/` are git-ignored; API keys, the
  IMAP password and key-bearing URLs are never written into error messages. The alert mailbox is
  opened read-only.
- **Uploads** (CV, LinkedIn files) are size-limited and parsed in a separate, CPU/memory/time-limited
  process; ZIP members are size-checked before reading.
- **Container:** runs as an unprivileged user (uid 1000).
- **No outbound AI or tracking service:** outbound requests go to the job sources you enable, to the Swiss
  public-transport timetable (town names only, for travel times), to postings' own addresses (to notice the ones
  that went offline) and once to the SECO site for the blank official form.

The multi-tenant platform adds per-workspace containers, networks and volumes, a LAN egress firewall,
read-only root filesystems, dropped capabilities and resource limits: see
[docs/platform.md](docs/platform.md#isolation-of-each-workspace).

## Known limits

- The jobs.ch / jobup.ch source uses an unofficial backend; the sites may change or block it.
- The platform's provisioner has the Docker socket (root-equivalent on the host). It is reachable only
  on an internal Docker network, with a shared token: run the platform on a dedicated VM or container.
