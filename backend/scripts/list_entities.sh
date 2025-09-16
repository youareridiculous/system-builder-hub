#!/usr/bin/env bash
set -euo pipefail

# List entities
curl -sS "http://localhost:5001/api/venture_os/entities?limit=${1:-5}" -H "X-Tenant-ID:${2:-demo_tenant}"
