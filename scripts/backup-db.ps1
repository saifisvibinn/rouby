# Daily Postgres backup for Rouby (run from repo root)
$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dir = Join-Path $PSScriptRoot "..\backups"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$remote = "/tmp/rouby_$stamp.dump"
docker compose exec -T db pg_dump -U rouby -d rouby -Fc -f $remote
$out = Join-Path $dir "rouby_$stamp.dump"
docker compose cp "db:$remote" $out
Write-Output "Wrote $out"
