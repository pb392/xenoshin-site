#!/bin/sh
# One-time server setup for xenoshin-site. Run as webadmin on the droplet:
#
#   curl -fsSL https://raw.githubusercontent.com/pb392/xenoshin-site/release/deploy/setup.sh -o setup.sh
#   sh setup.sh prepare     # stops the retired CI/CD containers, clones the repo, creates .env
#   nano ~/xenoshin-site/.env   # paste the Gemini key after GEMINI_API_KEY=
#   sh ~/xenoshin-site/deploy/setup.sh start
#
# Nothing here prints secrets.
set -eu
DIR="$HOME/xenoshin-site"
REPO="https://github.com/pb392/xenoshin-site.git"

check() {
  docker ps >/dev/null 2>&1 || { echo "ERROR: this account can't run docker. Send Claude the output of: groups"; exit 1; }
  docker network inspect hosting-web >/dev/null 2>&1 || { echo "ERROR: the hosting-web network (Traefik) wasn't found."; exit 1; }
}

prepare() {
  check
  echo "== Retiring the graded CI/CD containers (they stay on disk, just stopped)"
  for name in $(docker ps -a --format '{{.Names}}' | grep -E '^is373[-_]ci[-_]cd[-_](prod|qa|wud)[-_][0-9]+$' || true); do
    docker update --restart=no "$name" >/dev/null
    docker stop "$name" >/dev/null && echo "stopped $name"
  done
  echo "== Getting the code"
  if [ -d "$DIR/.git" ]; then
    git -C "$DIR" fetch -q origin release && git -C "$DIR" reset -q --hard origin/release
  else
    git clone -q --branch release "$REPO" "$DIR"
  fi
  if [ ! -f "$DIR/.env" ]; then
    cp "$DIR/.env.example" "$DIR/.env"
    chmod 600 "$DIR/.env"
    token=$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')
    sed -i "s/^ADMIN_TOKEN=.*/ADMIN_TOKEN=$token/" "$DIR/.env"
    echo "== Created $DIR/.env with a random admin token"
  fi
  echo
  echo "NEXT: run   nano $DIR/.env"
  echo "      paste your Gemini key right after GEMINI_API_KEY=  (no spaces), save with Ctrl+O, Enter, Ctrl+X"
  echo "THEN: run   sh $DIR/deploy/setup.sh start"
}

start() {
  check
  grep -q '^GEMINI_API_KEY=..*' "$DIR/.env" || { echo "ERROR: GEMINI_API_KEY is still empty in $DIR/.env"; exit 1; }
  cd "$DIR"
  echo "== Building and starting (first build takes a few minutes)"
  GIT_COMMIT=$(git rev-parse HEAD) docker compose up -d --build --remove-orphans
  chmod +x deploy/auto-deploy.sh
  line="*/2 * * * * sh $DIR/deploy/auto-deploy.sh >> $HOME/xenoshin-site-deploy.log 2>&1"   # sh: works even if the file loses its execute bit
  (crontab -l 2>/dev/null | grep -v 'xenoshin-site/deploy/auto-deploy.sh' || true; echo "$line") | crontab -
  echo "== Auto-deploy installed (checks for new releases every 2 minutes)"
  sleep 20
  docker compose ps
  echo
  echo "== Import result:"
  docker compose exec -T rag cat /data/last-import.json | head -40 || true
  echo
  echo "Memory now:"; free -m
  echo
  echo "Done. Send Claude the output above (it contains no secrets)."
}

case "${1:-}" in
  prepare) prepare ;;
  start) start ;;
  *) echo "usage: sh setup.sh prepare|start"; exit 64 ;;
esac
