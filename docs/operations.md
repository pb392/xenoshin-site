# Operations guide

How to set up, update, back up, restore, roll back and re-key xenoshin.com and rag.xenoshin.com. Every command runs as `webadmin` on the droplet (104.248.180.176) unless it says "on your laptop". Nothing here prints a secret.

| Item | Where |
|---|---|
| Code on the server | `~/xenoshin-site` (a clone of the `release` branch) |
| Secrets | `~/xenoshin-site/.env`, mode 600: `GEMINI_API_KEY`, `ADMIN_TOKEN`. Never in Git. |
| Database | Docker volume `xenoshin-site_rag-data`, file `/data/rag.sqlite3` inside the `rag` container |
| Auto-deploy log | `~/xenoshin-site-deploy.log` |
| Backups | `~/backups/rag-<UTC time>.sqlite3` |

## 1. Set up a new server from nothing

Needs Docker and the existing Traefik proxy on the `hosting-web` network, and DNS for `xenoshin.com`, `www.xenoshin.com` and `rag.xenoshin.com` pointing at the droplet.

```sh
curl -fsSL https://raw.githubusercontent.com/pb392/xenoshin-site/release/deploy/setup.sh -o setup.sh
sh setup.sh prepare            # clones the release branch, creates .env with a random admin token
nano ~/xenoshin-site/.env      # paste the Gemini key after GEMINI_API_KEY=
sh ~/xenoshin-site/deploy/setup.sh start   # builds, starts, installs the 2-minute auto-deploy cron job
```

Check: `https://rag.xenoshin.com/health` shows `"sources": 7` and `https://rag.xenoshin.com/import-record` shows a new run.

## 2. Normal updates

Push to `main`. CI runs the tests, the portfolio checks, the container smoke test, the restart/backup drill and the keyboard and phone-width checks. Only if all pass does it move `release`. Within 2 minutes the server pulls `release` and rebuilds. Each container start runs the import; unchanged sources are not re-embedded.

To see what the server is running: the footer of any RAG page shows the commit, or run `git -C ~/xenoshin-site log --oneline -1`.

## 3. Back up and restore the database

The database can always be rebuilt from `rag/corpus` by restarting the container, but a backup keeps the import history and saves re-embedding cost.

```sh
cd ~/xenoshin-site
sh deploy/backup.sh backup                          # app stays up; prints how many import runs are saved
sh deploy/backup.sh restore ~/backups/rag-2026-11-23T170000.sqlite3
```

Restore checks the file's integrity first, copies it in with SQLite's backup API (safe while the app is running), then restarts the app. The restart runs one more import, so the import record shows the restored history plus one new run.

This exact sequence (back up, delete the container and its volume, start fresh, restore, confirm the history is back) runs in CI on every push: see the "Restart, repeat-import and backup/restore drill" step in [`ci.yml`](../.github/workflows/ci.yml).

## 4. Roll back a bad release

The safe way, which keeps history and still goes through CI. On your laptop:

```sh
git revert <bad-commit>       # makes a new commit that undoes it
git push origin main          # CI checks it, moves release, the server updates within 2 minutes
```

Emergency (CI is down or too slow). On your laptop, point `release` straight at the last good commit:

```sh
git push origin <good-commit>:release --force
```

The server picks it up within 2 minutes. Afterwards, fix `main` so the next CI run doesn't move `release` back to the bad code.

If GitHub itself can't be reached, on the server: `crontab -e` and comment out the auto-deploy line, then
`cd ~/xenoshin-site && git reset --hard <good-commit> && GIT_COMMIT=<good-commit> docker compose up -d --build`. Re-enable the cron line when GitHub is back.

## 5. Change the Gemini API key or the admin token

Do this right away if a key may have leaked, and at least once a term.

1. Create a new key in Google AI Studio. Don't delete the old one yet.
2. `nano ~/xenoshin-site/.env` and replace the value after `GEMINI_API_KEY=` (no spaces, no quotes).
3. `cd ~/xenoshin-site && docker compose up -d --force-recreate rag`
4. Check `https://rag.xenoshin.com/health`, then ask one question on the site. The answer must have citations, not "generation unavailable".
5. Delete the old key in Google AI Studio.

For the admin token: generate a new one with `head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'`, put it after `ADMIN_TOKEN=`, and run step 3. The old token stops working immediately.

## 6. If something is wrong

| Symptom | Look at |
|---|---|
| Site down | `docker compose ps` (both services "healthy"?), `docker compose logs --tail 50 rag` |
| Changes not showing up | `tail ~/xenoshin-site-deploy.log`; did CI pass and move `release`? "Permission denied" means cron can't run the script: run `sh ~/xenoshin-site/deploy/auto-deploy.sh` once (this happened on 2026-11-23; the scripts are now stored as executable and CI checks that). |
| Answers say "generation unavailable" | Gemini key or quota: `docker compose logs rag | grep -i gemini` |
| Server low on memory | `free -m`; limits are 300 MB for `rag`, 64 MB for `portfolio` |
| Import failed | `docker compose exec -T rag cat /data/last-import.json` |
