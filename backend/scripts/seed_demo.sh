#!/usr/bin/env bash
set -euo pipefail

# Seed demo data
curl -sS -X POST http://localhost:5001/api/venture_os/seed/demo -H "X-Tenant-ID:${1:-demo_tenant}" -H "X-User-Role: admin"
