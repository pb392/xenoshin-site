#!/bin/sh
# Runs every 2 minutes from cron. Deploys only the "release" branch, which
# GitHub Actions moves forward only after every test has passed.
set -eu
cd "$(dirname "$0")/.."

git fetch -q origin release
current=$(git rev-parse HEAD)
target=$(git rev-parse origin/release)
[ "$current" = "$target" ] && exit 0

echo "$(date -u +%FT%TZ) deploying $target (was $current)"
git reset -q --hard "$target"
GIT_COMMIT="$target" docker compose up -d --build --remove-orphans
docker image prune -f >/dev/null
echo "$(date -u +%FT%TZ) deployed $target"
