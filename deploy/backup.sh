#!/bin/sh
# Back up or restore the RAG database (the rag-data volume).
#   sh deploy/backup.sh backup            -> ~/backups/rag-YYYY-MM-DDTHHMMSS.sqlite3
#   sh deploy/backup.sh restore FILE      -> replaces /data/rag.sqlite3 with FILE, restarts the app
# Run from ~/xenoshin-site. Uses SQLite's online backup, so the app can stay up during a backup.
set -eu
SERVICE="${SERVICE:-rag}"
COMPOSE="${COMPOSE:-docker compose}"
case "${1:-}" in
  backup)
    mkdir -p "$HOME/backups"
    out="$HOME/backups/rag-$(date -u +%Y-%m-%dT%H%M%S).sqlite3"
    $COMPOSE exec -T "$SERVICE" python -c "import sqlite3; s=sqlite3.connect('/data/rag.sqlite3'); d=sqlite3.connect('/data/backup.sqlite3'); s.backup(d); d.close(); print('runs in backup:', sqlite3.connect('/data/backup.sqlite3').execute('select count(*) from import_runs').fetchone()[0])"
    $COMPOSE cp "$SERVICE:/data/backup.sqlite3" "$out"
    $COMPOSE exec -T "$SERVICE" rm -f /data/backup.sqlite3
    echo "saved $out"
    ;;
  restore)
    file="${2:?usage: sh deploy/backup.sh restore FILE}"
    $COMPOSE cp "$file" "$SERVICE:/data/restore.sqlite3"
    $COMPOSE exec -T -u 0 "$SERVICE" chown rag:rag /data/restore.sqlite3   # the app runs as user rag
    # Copy page by page with SQLite's backup API (safe with WAL mode), after an integrity check.
    $COMPOSE exec -T "$SERVICE" python -c "import sqlite3,sys; src=sqlite3.connect('/data/restore.sqlite3'); ok=src.execute('pragma integrity_check').fetchone()[0]=='ok'; ok or sys.exit('backup file is damaged'); dst=sqlite3.connect('/data/rag.sqlite3'); src.backup(dst); dst.close(); src.close()"
    $COMPOSE exec -T "$SERVICE" rm -f /data/restore.sqlite3
    $COMPOSE restart "$SERVICE"
    echo "restored $file and restarted $SERVICE"
    ;;
  *) echo "usage: sh deploy/backup.sh backup | restore FILE"; exit 64 ;;
esac
