#!/bin/bash
set -e

echo "Waiting for database..."
until python -c "import psycopg2; psycopg2.connect(host='$POSTGRES_HOST', dbname='$POSTGRES_DB', user='$POSTGRES_USER', password='$POSTGRES_PASSWORD')" 2>/dev/null; do
  echo "Database not ready — retrying in 2s..."
  sleep 2
done

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
