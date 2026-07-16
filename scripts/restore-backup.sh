#!/usr/bin/env bash
# Restores a backup into a NEW, temporary database - never overwrites the
# live database directly. Wraps the manual procedure from
# docs/PRODUCTION_RUNBOOK.md into a script to remove typo risk during an
# actual disaster recovery, when it matters most.
#
# Usage: ./restore-backup.sh <backup_file.sql> [temp_db_name]
#
# After restoring, inspect the temp database, then either:
#   - promote it manually (documented separately - a deliberate, reviewed
#     action, not something this script automates), or
#   - drop it: docker exec tasklytics_db psql -U postgres -c "DROP DATABASE <temp_db_name>;"

set -euo pipefail

BACKUP_FILE="${1:?Usage: $0 <backup_file.sql> [temp_db_name]}"
TEMP_DB="${2:-tasklytics_restore_test}"
DB_CONTAINER="tasklytics_db"
DB_USER="postgres"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "FAIL: backup file $BACKUP_FILE does not exist"
    exit 1
fi

if [ ! -s "$BACKUP_FILE" ]; then
    echo "FAIL: backup file $BACKUP_FILE is empty"
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER"; then
    echo "FAIL: container $DB_CONTAINER is not running"
    exit 1
fi

echo "Creating temporary database: $TEMP_DB"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $TEMP_DB;"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -c "CREATE DATABASE $TEMP_DB;"

echo "Restoring $BACKUP_FILE into $TEMP_DB..."
docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEMP_DB" < "$BACKUP_FILE"

echo "Verifying restored data..."
USER_COUNT=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEMP_DB" -tAc "SELECT count(*) FROM users;")
TASK_COUNT=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$TEMP_DB" -tAc "SELECT count(*) FROM tasks;")

echo "OK: restored $TEMP_DB - users=$USER_COUNT tasks=$TASK_COUNT"
echo "Review the data, then drop the temp database when done:"
echo "  docker exec $DB_CONTAINER psql -U $DB_USER -c \"DROP DATABASE $TEMP_DB;\""
