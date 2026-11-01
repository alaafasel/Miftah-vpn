#!/bin/bash
set -e
cd /opt/miftah
TS=$(date -u +%Y%m%d-%H%M%S)
docker exec miftah_postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > backups/db-$TS.sql.gz
cp .env backups/env-$TS.bak
chmod 600 backups/db-$TS.sql.gz backups/env-$TS.bak
find backups -name 'db-*.sql.gz' -mtime +14 -delete
find backups -name 'env-*.bak' -mtime +14 -delete
echo "backup ok: $TS"
