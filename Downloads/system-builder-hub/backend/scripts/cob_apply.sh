#!/bin/bash
# Co-Builder CLI smoke test script

set -e

echo "=== Co-Builder CLI Smoke Test ==="

# Test 1: Create venture_os/__init__.py with __version__ = "0.0.1", apply, assert bytes_written > 0
echo "Test 1: Creating venture_os/__init__.py..."
cd "$(dirname "$0")/.."

python -m src.cobuilder.cli apply \
  --message "Create venture_os/__init__.py with __version__ = \"0.0.1\"" \
  --tenant demo --json 2>/tmp/test1_stderr.json > /tmp/test1.json

# Check success
if ! jq -e '.success == true' /tmp/test1.json > /dev/null; then
    echo "❌ Test 1 failed: success != true"
    cat /tmp/test1.json
    exit 1
fi

# Check applied
applied=$(jq -r '.applied' /tmp/test1.json)
if [ "$applied" != "true" ]; then
    echo "❌ Test 1 failed: not applied (got: $applied)"
    cat /tmp/test1.json
    exit 1
fi

# Check bytes_written > 0
bytes_written=$(jq -r '.apply.bytes_written' /tmp/test1.json)
if [ "$bytes_written" -le 0 ]; then
    echo "❌ Test 1 failed: bytes_written <= 0 ($bytes_written)"
    cat /tmp/test1.json
    exit 1
fi

echo "✅ Test 1 passed: bytes_written = $bytes_written"

# Test 2: Propose README.md (dry-run), ensure diff and content non-empty; then apply for real
echo "Test 2a: Proposing README.md (dry-run)..."
python -m src.cobuilder.cli apply \
  --message "Add README.md at project root with a one-line overview: Venture OS Entity Management v1.0.1. Single-file additive change." \
  --tenant demo --dry-run --json 2>/tmp/test2a_stderr.json > /tmp/test2a.json

# Check diff and content non-empty
diff_len=$(jq -r '(.diff | length)' /tmp/test2a.json)
content_len=$(jq -r '(.content | length)' /tmp/test2a.json)

if [ "$diff_len" -le 0 ]; then
    echo "❌ Test 2a failed: diff length <= 0 ($diff_len)"
    cat /tmp/test2a.json
    exit 1
fi

if [ "$content_len" -le 0 ]; then
    echo "❌ Test 2a failed: content length <= 0 ($content_len)"
    cat /tmp/test2a.json
    exit 1
fi

echo "✅ Test 2a passed: diff_len = $diff_len, content_len = $content_len"

# Test 2b: Apply the README.md for real
echo "Test 2b: Applying README.md..."
python -m src.cobuilder.cli apply \
  --message "Add README.md at project root with a one-line overview: Venture OS Entity Management v1.0.1. Single-file additive change." \
  --tenant demo --json 2>/tmp/test2b_stderr.json > /tmp/test2b.json

# Check success and applied
success=$(jq -r '.success' /tmp/test2b.json)
if [ "$success" != "true" ]; then
    echo "❌ Test 2b failed: success != true (got: $success)"
    cat /tmp/test2b.json
    exit 1
fi

applied=$(jq -r '.applied' /tmp/test2b.json)
if [ "$applied" != "true" ]; then
    echo "❌ Test 2b failed: not applied (got: $applied)"
    cat /tmp/test2b.json
    exit 1
fi

# Print absolute written paths and sha256
echo "✅ Test 2b passed:"
echo "   File: $(jq -r '.apply.file' /tmp/test2b.json)"
echo "   Absolute path: $(jq -r '.apply.absolute_path' /tmp/test2b.json)"
echo "   SHA256: $(jq -r '.apply.sha256' /tmp/test2b.json)"

echo "=== All CLI tests passed! ==="
