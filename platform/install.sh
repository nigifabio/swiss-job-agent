#!/bin/bash
# One-time install on a Docker host (e.g. a Debian LXC with nesting), repo at /opt/swiss-job-agent.
# Creates platform/.env with fresh secrets, the LAN egress firewall, builds both images, starts.
set -euo pipefail
umask 022
cd "$(dirname "$0")"
REPO=$(cd .. && pwd)
if [ ! -f .env ]; then
  cp .env.example .env
  sed -i "s/^PLATFORM_SECRET=.*/PLATFORM_SECRET=$(openssl rand -hex 32)/; s/^PROVISIONER_TOKEN=.*/PROVISIONER_TOKEN=$(openssl rand -hex 32)/" .env
  chmod 600 .env
  echo "created platform/.env: set CF_ACCESS_AUD and ADMIN_EMAILS, then run this again"
  exit 0
fi
grep -q '^CF_ACCESS_AUD=.\+' .env || { echo "set CF_ACCESS_AUD in platform/.env"; exit 1; }
cat > /etc/systemd/system/jobagent-egress.service <<UNIT
[Unit]
Description=Swiss Job Agent: block LAN egress from tenant containers
After=docker.service
PartOf=docker.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$REPO/platform/egress.sh
[Install]
WantedBy=multi-user.target docker.service
UNIT
systemctl daemon-reload
systemctl enable --now jobagent-egress.service
systemctl restart jobagent-egress.service
exec "$REPO/platform/upgrade.sh"
