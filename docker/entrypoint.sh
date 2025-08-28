#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-web}"
shift || true

# Wait for Postgres
if [ -n "${DB_HOST:-}" ]; then
  echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT:-5432}..."
  until python - <<'PY'
import os, socket, sys
host = os.environ.get('DB_HOST','127.0.0.1')
port = int(os.environ.get('DB_PORT','5432'))
s = socket.socket()
s.settimeout(1.5)
try:
    s.connect((host, port))
    print('db reachable')
    sys.exit(0)
except Exception as e:
    print('db not ready:', e)
    sys.exit(1)
PY
  do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

if [ "$ROLE" = "web" ]; then
  exec gunicorn modbus_site.wsgi:application --bind 0.0.0.0:8000 --workers ${WEB_CONCURRENCY:-2}
elif [ "$ROLE" = "worker" ]; then
  # Start poller (async) with default interval; env POLL_INTERVAL can override
  INTERVAL="${POLL_INTERVAL:-1.0}"
  exec python manage.py poll_modbus --interval "$INTERVAL"
else
  exec "$@"
fi
