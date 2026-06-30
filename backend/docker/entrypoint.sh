#!/bin/sh
set -e

echo "[entrypoint] Migrating"
alembic upgrade head
echo "[entrypoint] Migrated"

exec "$@"
