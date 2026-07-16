#!/usr/bin/env bash
# Syncs local Postgres backups to off-server object storage via rclone.
#
# Requires manual one-time setup before this will work - see
# docs/PRODUCTION_RUNBOOK.md "Off-server backup setup" for the exact steps
# (creating a DigitalOcean Spaces bucket/API key, running `rclone config`).
# This script deliberately does not attempt that setup itself - it requires
# an external account, which is outside what can be done without a human.
#
# Usage: ./backup-sync.sh [backup_dir] [rclone_remote:bucket_path]

set -euo pipefail

BACKUP_DIR="${1:-/var/backups/tasklytics}"
REMOTE_TARGET="${2:-}"

if [ -z "$REMOTE_TARGET" ]; then
    echo "FAIL: no rclone remote target given. Usage: $0 <backup_dir> <remote:bucket/path>"
    echo "Example: $0 /var/backups/tasklytics spaces:tasklytics-backups"
    exit 1
fi

if ! command -v rclone >/dev/null 2>&1; then
    echo "FAIL: rclone is not installed. See docs/PRODUCTION_RUNBOOK.md for setup steps."
    exit 1
fi

if [ ! -d "$BACKUP_DIR" ]; then
    echo "FAIL: backup directory $BACKUP_DIR does not exist"
    exit 1
fi

echo "Syncing $BACKUP_DIR -> $REMOTE_TARGET"
rclone sync "$BACKUP_DIR" "$REMOTE_TARGET" --checksum

echo "Verifying remote file count matches local..."
LOCAL_COUNT=$(find "$BACKUP_DIR" -name "tasklytics_backup_*.sql" -type f | wc -l)
REMOTE_COUNT=$(rclone lsf "$REMOTE_TARGET" --files-only | grep -c "tasklytics_backup_" || true)

if [ "$LOCAL_COUNT" -ne "$REMOTE_COUNT" ]; then
    echo "FAIL: local file count ($LOCAL_COUNT) does not match remote ($REMOTE_COUNT)"
    exit 1
fi

echo "OK: $REMOTE_COUNT backup files confirmed on remote, matching local count"
