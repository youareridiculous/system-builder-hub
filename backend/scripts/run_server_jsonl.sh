#!/usr/bin/env bash
set -euo pipefail

# Run server with JSONL storage
VOS_STORE=jsonl VOS_STORE_PATH="${1:-data/venture_os.jsonl}" PYTHONPATH=src python -m src.cli run
