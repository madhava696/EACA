#!/usr/bin/env bash
set -euo pipefail

: "${MODE:=web}"
: "${PORT:=8080}"
: "${DATABASE_URL:=}"

echo "Starting container in mode: $MODE"

# Simple wait-for-postgres function (tries asyncpg connection using Python)
wait_for_db() {
  if [ -z "$DATABASE_URL" ]; then
    echo "DATABASE_URL is not set - skipping DB wait."
    return 0
  fi

  echo "Waiting for database to become available..."
  python - <<PY
import os,sys,asyncio
from urllib.parse import urlparse
dsn = os.environ.get("DATABASE_URL")
if not dsn:
    print("No DATABASE_URL in environment, skipping db check.")
    sys.exit(0)

import asyncpg, asyncio
async def try_connect():
    try:
        conn = await asyncpg.connect(dsn)
        await conn.close()
        print("Database reachable.")
        return 0
    except Exception as e:
        print("Database not ready:", e, file=sys.stderr)
        return 1

# try multiple times
for attempt in range(1, 21):
    try:
        rc = asyncio.get_event_loop().run_until_complete(try_connect())
        if rc == 0:
            sys.exit(0)
    except Exception as e:
        pass
    print(f"Attempt {attempt}/20 - sleeping 1s")
    import time; time.sleep(1)
print("DB did not become available in time.")
sys.exit(2)
PY
}

# Run alembic migrations if alembic is available
run_migrations() {
  if command -v alembic >/dev/null 2>&1; then
    echo "Running alembic upgrade head..."
    alembic upgrade head || echo "alembic failed; continuing"
  else
    echo "alembic not installed; skipping migrations"
  fi
}

if [ "$MODE" = "web" ]; then
  echo "==> Mode=web: starting migrations (if any) and gunicorn"

  # Wait for DB if using Neon / Postgres
  wait_for_db || echo "DB wait returned non-zero; continuing anyway"

  run_migrations

  # Use a small worker count for small instances; let the deployer override via CMD or env.
  WORKERS=${GUNICORN_WORKERS:-2}
  TIMEOUT=${GUNICORN_TIMEOUT:-30}
  echo "Launching gunicorn with ${WORKERS} worker(s) at 0.0.0.0:${PORT}"
  exec gunicorn -w ${WORKERS} -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --timeout ${TIMEOUT} \
    backend.main:app

elif [ "$MODE" = "worker" ]; then
  echo "==> Mode=worker: starting ML worker process"

  # ensure DB available for worker if needed
  wait_for_db || echo "DB wait returned non-zero; continuing anyway"

  # Replace the command below with the correct entrypoint for your worker.
  # Many repos expose a script like backend/emotion_face.py that runs inference loop or a fastapi app.
  # Default fallback: try to run a dedicated module `backend.emotion_face` as a script.
  if [ -f "./backend/emotion_face.py" ]; then
    echo "Found backend/emotion_face.py -> running it"
    exec python -u ./backend/emotion_face.py
  else
    echo "No backend/emotion_face.py found. Falling back to uvicorn backend.main:app (with ML libs available)."
    exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --workers 1
  fi

else
  echo "Unknown MODE: $MODE"
  exit 1
fi
