#!/bin/sh
set -e

run_db_migrations() {
  output=""
  code=0
  output=$(alembic upgrade head 2>&1) || code=$?
  if [ "$code" -ne 0 ]; then
    echo "Migration failed, checking if idempotent SQLite duplicate-column error" >&2
    echo "${output}" >&2
    if echo "${output}" | grep -qi 'duplicate column name'; then
      echo "Detected duplicate-column migration error on SQLite. Marking head and continuing..." >&2
      migrate_id=$(alembic heads 2>/dev/null | head -1 | awk '{print $1}' || true)
      if [ -n "${migrate_id}" ]; then
        alembic stamp "${migrate_id}"
      else
        alembic stamp head
      fi
      return 0
    fi
    return ${code}
  fi
}

run_db_migrations
exec uvicorn app.main:app --host 0.0.0.0 --port 5555
