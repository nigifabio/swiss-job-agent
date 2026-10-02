#!/usr/bin/env bash
# Swiss Job Agent installer: one-person instance with Docker Compose.
#
#   ./install.sh              install (asks a few questions, creates .env, builds, starts)
#   ./install.sh --yes        install with the defaults, no questions
#   ./install.sh upgrade      pull the latest code, rebuild, health-check, roll back on failure
#   ./install.sh backup       copy the database and your files into backups/<date>.tar.gz
#   ./install.sh status       containers, version and health
#   ./install.sh platform     multi-tenant platform instead (see platform/install.sh)
#
# Needs: git, Docker with the compose plugin, curl. Linux or macOS.
set -euo pipefail
umask 022
cd "$(dirname "$0")"

say()  { printf '\033[1m==>\033[0m %s\n' "$*"; }
die()  { printf '\033[31mError:\033[0m %s\n' "$*" >&2; exit 1; }
envget() { sed -n "s/^$1=//p" .env 2>/dev/null | tail -1; }
port() { local p; p=$(envget PORT); echo "${p:-8080}"; }
healthy() {
  for _ in $(seq 1 60); do
    curl -fs -o /dev/null "http://127.0.0.1:$(port)/healthz" && return 0; sleep 2
  done
  return 1
}

need() {
  command -v git >/dev/null || die "git is not installed."
  command -v curl >/dev/null || die "curl is not installed."
  command -v docker >/dev/null || die "Docker is not installed: https://docs.docker.com/engine/install/"
  docker compose version >/dev/null 2>&1 || die "The Docker compose plugin is missing (docker compose version)."
  docker info >/dev/null 2>&1 || die "Docker isn't running or this user can't use it (try sudo, or add yourself to the docker group)."
}

ask() {   # ask VAR "question" default
  local var=$1 q=$2 def=$3 ans
  if [ "$YES" = 1 ]; then ans=$def; else read -rp "$q [$def]: " ans; ans=${ans:-$def}; fi
  setenv "$var" "$ans"
}

setenv() {  # set KEY=value in .env (replaces an existing or commented line, else appends)
  local k=$1 v=$2 tmp
  tmp=$(mktemp)
  awk -v k="$k" -v v="$v" 'BEGIN{done=0} ($0 ~ "^#?" k "=" && !done){print k "=" v; done=1; next} {print} END{if(!done) print k "=" v}' .env > "$tmp"
  cat "$tmp" > .env && rm -f "$tmp"
}

configure() {
  if [ -f .env ]; then say "Keeping your existing .env"; return; fi
  cp .env.example .env
  chmod 600 .env
  say "A few questions to set up your search (all can be changed later on the Settings page)"
  echo "The setup wizard imports your CV (PDF/Word) or LinkedIn export in the browser and"
  echo "builds the search from it. Without it you set the search here and write data/profile.json."
  ask ONBOARDING "Use the setup wizard? (1 = yes, 0 = no)" "1"
  if [ "$(envget ONBOARDING)" != 1 ]; then
    setup_search
  fi
  until ask PORT "Port for the web interface" "8080"; [[ "$(envget PORT)" =~ ^[0-9]{2,5}$ ]] && [ "$(envget PORT)" -le 65535 ]; do
    [ "$YES" = 0 ] || die "invalid PORT"; echo "A number between 10 and 65535, please."; done
  echo "Listen on localhost only (safe), or on every network interface (needed behind a"
  echo "reverse proxy on another machine; then protect it with Cloudflare Access or similar)."
  until ask BIND_ADDR "Address to listen on (127.0.0.1 or 0.0.0.0)" "127.0.0.1"; [[ "$(envget BIND_ADDR)" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; do
    [ "$YES" = 0 ] || die "invalid BIND_ADDR"; echo "An IPv4 address such as 127.0.0.1 or 0.0.0.0, please."; done
  [ "$(envget BIND_ADDR)" = 127.0.0.1 ] || [ -n "$(envget CF_ACCESS_AUD)" ] ||
    printf '\033[33mWarning:\033[0m the app has no login of its own. Put it behind Cloudflare Access (CF_TEAM_DOMAIN + CF_ACCESS_AUD in .env), a VPN or an authenticating proxy.\n'
}

setup_search() {
  ask SEARCH_TERMS "Job titles to search, ';'-separated" "Project Manager;Business Analyst"
  ask WHERE "Region(s), ';'-separated (a canton or town)" "Vaud"
  ask LANGUAGES "Languages of the postings to keep (en,fr,de,it)" "en,fr"
  ask TITLE_KEYWORDS "Keep only titles containing one of these words (blank = all)" ""
  ask SCORE_KEYWORDS "Your skills, comma-separated (used for the match score)" ""
  ask PROVIDERS "Sources, ';'-separated" "jobup;jobroom;ats;remote"
}

start() {
  mkdir -p data
  if [ "$(uname)" = Linux ] && [ "$(stat -c %u data)" != 1000 ]; then   # the app runs as uid 1000
    if [ "$(id -u)" = 0 ]; then chown -R 1000:1000 data
    else say "data/ must be writable by uid 1000 (the app user): sudo chown -R 1000:1000 data"; fi
  fi
  say "Building and starting (first build takes a few minutes)"
  docker compose up -d --build --remove-orphans
}

install() {
  need
  configure
  start
  healthy || die "The app didn't become healthy. Logs: docker compose logs web"
  say "Running: http://127.0.0.1:$(port)  (first scan: Scan now on the homepage)"
  echo "    Next: put your CV facts in data/profile.json for tailored CVs and letters (see docs/)."
  echo "    Day to day: ./jobagent help   (scan, logs, update, backup, discover...)"
}

upgrade() {
  need
  [ -f .env ] || die "Not installed yet: run ./install.sh"
  [ -z "$(git status --porcelain --untracked-files=no)" ] || die "Local changes to tracked files; commit or stash them first."
  local prev
  prev=$(git rev-parse HEAD)
  backup
  say "Fetching the latest version"
  git pull --ff-only
  if [ "$(git rev-parse HEAD)" = "$prev" ] && healthy; then say "Already up to date ($(git rev-parse --short HEAD))"; return; fi
  if start && healthy; then
    docker image prune -f >/dev/null
    say "Upgraded $(git rev-parse --short "$prev") -> $(git rev-parse --short HEAD)"
  else
    say "New version unhealthy; rolling back to $(git rev-parse --short "$prev")"
    git checkout -q "$prev"
    start && healthy && die "Rolled back. The upgrade failed; check: docker compose logs web"
    die "Rollback is unhealthy too; check: docker compose logs web"
  fi
}

backup() {
  [ -d data ] || { say "No data yet, nothing to back up"; return; }
  mkdir -p backups
  local out="backups/$(date +%Y%m%d-%H%M%S).tar.gz" skip=()
  if [ -f data/jobs.db ] && docker compose ps --status running web 2>/dev/null | grep -q web &&
     docker compose exec -T web python -c "import sqlite3; s=sqlite3.connect('/data/jobs.db'); d=sqlite3.connect('/data/jobs.backup.db'); s.backup(d); d.close()" </dev/null; then
    skip=(--exclude=data/jobs.db)      # live database: the consistent copy above goes in instead
  fi
  tar -czf "$out" "${skip[@]+"${skip[@]}"}" --exclude='data/*.lock' data
  rm -f data/jobs.backup.db
  chmod 600 "$out"
  say "Backup: $out"
}

status() {
  docker compose ps
  echo "version: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  curl -fs -o /dev/null "http://127.0.0.1:$(port)/healthz" && echo "health: ok" || echo "health: NOT responding"
}

YES=0
cmd=install
for a in "$@"; do
  case $a in
    -y|--yes) YES=1 ;;
    install|upgrade|backup|status|platform) cmd=$a ;;
    -h|--help) sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $a (see ./install.sh --help)" ;;
  esac
done
case $cmd in
  platform) exec platform/install.sh ;;
  *) $cmd ;;
esac
