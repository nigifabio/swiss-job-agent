#!/bin/bash
# Tenants may reach the internet (job boards) but nothing on the LAN or private ranges:
# no LAN services, no Docker host, no other platform service. Idempotent; run at boot
# after Docker by jobagent-egress.service (install.sh).
set -euo pipefail
POOL=$(sed -n 's/^TENANT_SUBNET_POOL=//p' "$(dirname "$0")/.env" 2>/dev/null || true)
POOL=${POOL:-172.31.0.0/16}
iptables -N DOCKER-USER 2>/dev/null || true
iptables -N JOBAGENT-EGRESS 2>/dev/null || true
iptables -F JOBAGENT-EGRESS
iptables -A JOBAGENT-EGRESS -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
iptables -A JOBAGENT-EGRESS -d "$POOL" -j RETURN        # gateway <-> tenant on the tenant's own bridge
for net in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 100.64.0.0/10; do
  iptables -A JOBAGENT-EGRESS -d "$net" -j REJECT
done
iptables -C DOCKER-USER -s "$POOL" -j JOBAGENT-EGRESS 2>/dev/null || iptables -I DOCKER-USER -s "$POOL" -j JOBAGENT-EGRESS
# ...and nothing on the Docker host itself (SSH, the gateway port...): that traffic takes INPUT,
# not FORWARD. DNS is unaffected (Docker's resolver answers inside the container).
iptables -N JOBAGENT-HOST 2>/dev/null || true
iptables -F JOBAGENT-HOST
iptables -A JOBAGENT-HOST -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
iptables -A JOBAGENT-HOST -j REJECT
iptables -C INPUT -s "$POOL" -j JOBAGENT-HOST 2>/dev/null || iptables -I INPUT -s "$POOL" -j JOBAGENT-HOST
echo "egress rules active for $POOL"
