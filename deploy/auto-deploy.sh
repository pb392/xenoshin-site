#!/bin/sh
# Runs every 2 minutes from cron. Deploys only the "release" branch, which
# GitHub Actions moves forward only after every test has passed.
#
# The commit that is actually running is recorded in .deployed only after
# `docker compose up` succeeds, so a failed build is retried on the next run
# instead of being skipped. A lock stops two runs from overlapping during a
# long build.
set -eu
cd "$(dirname "$0")/.."

exec 9>.deploy.lock
flock -n 9 || exit 0

git fetch -q origin release
target=$(git rev-parse origin/release)
deployed=$(cat .deployed 2>/dev/null || echo none)
[ "$deployed" = "$target" ] && exit 0

echo "$(date -u +%FT%TZ) deploying $target (running: $deployed)"
git reset -q --hard "$target"
if GIT_COMMIT="$target" docker compose up -d --build --remove-orphans; then
  echo "$target" > .deployed
  docker image prune -f >/dev/null
  echo "$(date -u +%FT%TZ) deployed $target"
else
  echo "$(date -u +%FT%TZ) FAILED to deploy $target; will retry in 2 minutes" >&2
  exit 1
fi
