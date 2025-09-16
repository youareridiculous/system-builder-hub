#!/usr/bin/env bash
set -euo pipefail

# Minimal pytest runner with noise suppression
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q "$@"
