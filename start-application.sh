#!/usr/bin/env bash
cd "$(dirname "$0")"
python -m uvicorn server:app --port 8000
