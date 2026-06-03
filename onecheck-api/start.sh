#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PORT="${PORT:-8000}"

# Seed apenas se banco vazio (primeiro deploy)
python scripts/seed.py 2>/dev/null || true

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
