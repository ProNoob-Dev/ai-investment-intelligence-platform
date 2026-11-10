#!/usr/bin/env bash
# Dev server for local testing only. Loads .env via the app's config.
set -e
cd "$(dirname "$0")/.."
export TMPDIR="$HOME/workspace/.pip-tmp"
export HF_HOME="$HOME/workspace/.hf-cache"
exec .venv/bin/python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000
