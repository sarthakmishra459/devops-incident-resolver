#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip
pip install -e .
exec uvicorn devops_resolver.presentation.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
