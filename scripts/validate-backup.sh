#!/usr/bin/env bash
# Confirms today's automated backup actually ran and produced a real file -
# run this yourself, or add as a cron entry a few minutes after the 0 2 * * *
# pg_dump job, so a silently-broken backup gets caught same-day instead of
# discovered during an actual disaster recovery.
#
# Usage: ./validate-backup.sh [backup_dir] [max_age_hours]

set -euo pipefail

BACKUP_DIR="${1:-/var/backups/tasklytics}"
MAX_AGE_HOURS="${2:-25}"  # 25, not 24, to tolerate normal cron timing drift

if [ ! -d "$BACKUP_DIR" ]; then
    echo "FAIL: backup directory $BACKUP_DIR does not exist"
    exit 1
fi

LATEST=$(find "$BACKUP_DIR" -name "tasklytics_backup_*.sql" -type f -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | head -1 | cut -d' ' -f2-)

if [ -z "$LATEST" ]; then
    echo "FAIL: no backup files found in $BACKUP_DIR"
    exit 1
fi

SIZE=$(stat -c%s "$LATEST" 2>/dev/null || stat -f%z "$LATEST")
if [ "$SIZE" -eq 0 ]; then
    echo "FAIL: latest backup ($LATEST) is 0 bytes"
    exit 1
fi

AGE_SECONDS=$(( $(date +%s) - $(stat -c%Y "$LATEST" 2>/dev/null || stat -f%m "$LATEST") ))
AGE_HOURS=$(( AGE_SECONDS / 3600 ))

if [ "$AGE_HOURS" -gt "$MAX_AGE_HOURS" ]; then
    echo "FAIL: latest backup ($LATEST) is ${AGE_HOURS}h old, exceeds ${MAX_AGE_HOURS}h threshold - the cron job may have stopped running"
    exit 1
fi

echo "OK: $LATEST is ${SIZE} bytes, ${AGE_HOURS}h old"
