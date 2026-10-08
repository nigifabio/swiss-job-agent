#!/bin/bash
# Build the current checkout and roll it out: tenant image, platform services, then every tenant
# (one at a time, health-checked, rolled back on failure). Used by install.sh and the rollout.
set -euo pipefail
umask 022
cd "$(dirname "$0")/.."
sha=$(git rev-parse --short HEAD 2>/dev/null || echo local)
# no provenance/SBOM attestations: with them every build gets a new image id even when nothing changed,
# which re-created every workspace on every run and orphaned the image of the running ones
docker build -q --provenance=false --sbom=false -t "swiss-job-agent:$sha" -t swiss-job-agent:latest . > /dev/null
docker compose -f platform/docker-compose.yml up -d --build --remove-orphans
for _ in $(seq 1 45); do
  curl -fs -o /dev/null http://127.0.0.1:8090/_platform/healthz && break; sleep 2
done
curl -fs -o /dev/null http://127.0.0.1:8090/_platform/healthz || { echo "gateway not healthy"; exit 1; }
docker exec jobplatform-provisioner python -m jobplatform.provisioner upgrade
docker image prune -f > /dev/null
echo "platform at $sha"
