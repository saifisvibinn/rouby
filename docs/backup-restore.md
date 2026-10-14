# Postgres backup & restore

## Quick backup (PowerShell)

From repo root with Compose running:

```powershell
.\scripts\backup-db.ps1
```

Writes a custom-format dump under `./backups/rouby_YYYYMMDD_HHMMSS.dump`.

## Backup (from host with Compose running)

```bash
docker compose exec -T db pg_dump -U rouby -d rouby -Fc > backup_rouby_$(date +%Y%m%d).dump
```

PowerShell (manual):

```powershell
docker compose exec db pg_dump -U rouby -d rouby -Fc -f /tmp/rouby.dump
docker compose cp db:/tmp/rouby.dump ./backup_rouby.dump
```

## Restore

```bash
docker compose exec -T db pg_restore -U rouby -d rouby --clean --if-exists < backup_rouby.dump
```

## Cron-style (optional Compose service)

Add a sidecar later that runs `pg_dump` on a schedule into a host-mounted `./backups` volume. For MVP, run the backup command daily on the restaurant PC Task Scheduler.
