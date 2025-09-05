#!/bin/bash
# Server smoke test script

set -e

echo "=== Server Smoke Test ==="

# Kill any existing processes on port 5001
echo "Cleaning up port 5001..."
./scripts/kill_5001.sh

# Start server in background
echo "Starting server..."
cd "$(dirname "$0")/.."
python -m src.server > /tmp/server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 5

# Test health endpoint
echo "Test 1: Health endpoint..."
if ! curl -s http://127.0.0.1:5001/api/health | jq -e '.ok == true' > /dev/null; then
    echo "❌ Health endpoint failed"
    cat /tmp/server.log
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi
echo "✅ Health endpoint passed"

# Test cobuilder ask endpoint
echo "Test 2: Co-Builder ask endpoint..."
if ! curl -s -X POST http://127.0.0.1:5001/api/cobuilder/ask \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -d '{"message":"Create test file"}' | jq -e '.success == true' > /dev/null; then
    echo "❌ Co-Builder ask endpoint failed"
    cat /tmp/server.log
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi
echo "✅ Co-Builder ask endpoint passed"

# Test cobuilder ask with apply
echo "Test 3: Co-Builder ask with apply..."
if ! curl -s -X POST http://127.0.0.1:5001/api/cobuilder/ask \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo" \
  -d '{"message":"Create test file","apply":true}' | jq -e '.data.apply.applied == true' > /dev/null; then
    echo "❌ Co-Builder apply failed"
    cat /tmp/server.log
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi
echo "✅ Co-Builder apply passed"

# Clean up
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true

echo "=== All server tests passed! ==="
