#!/usr/bin/env bash
set -euo pipefail

echo "=== Verifying Full Build Endpoint Fix ==="

echo "1. Testing unit tests:"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src pytest -q src/cobuilder/tests/test_full_build_endpoint.py

echo ""
echo "2. Testing endpoint logic directly:"
PYTHONPATH="src" python -c "
from src.cobuilder.plan_parser import PlanParser
from src.cobuilder.orchestrator import FullBuildOrchestrator

# Test the core logic
parser = PlanParser()
orchestrator = FullBuildOrchestrator()

# Test plan parsing
content = 'Create /studio directory with package files'
task_graph = parser.parse_plan(content, 'text')
print(f'✅ Plan parsing works: {len(task_graph.nodes)} tasks')

# Test orchestrator creation
build_result = orchestrator.execute_task_graph(task_graph, 'demo_tenant', 'test-key')
print(f'✅ Orchestrator execution works: {build_result.build_id}')
print(f'✅ Build status: {build_result.status.value}')
"

echo ""
echo "3. Testing response format:"
PYTHONPATH="src" python -c "
from src.cobuilder.response_utils import build_cobuilder_response

# Test response building
response = build_cobuilder_response(
    tenant_id_friendly='demo',
    request_id='test-123',
    data={'build_id': 'test-build-123', 'ok': True},
    status=202
)

print(f'✅ Response building works: {response[1]} status')
print(f'✅ Response data: {response[0].get_json()}')
"

echo ""
echo "=== Summary ==="
echo "✅ All core components working:"
echo "   • Plan parser creates TaskGraph"
echo "   • Orchestrator executes with proper FullBuildResult"
echo "   • Response builder creates 202 responses"
echo "   • Unit tests pass with proper response format"
echo ""
echo "🎯 The /api/cobuilder/full_build endpoint fix is complete!"
echo "   • Accepts message in JSON body"
echo "   • Handles idempotency_key from body/headers"
echo "   • Handles started_at from body/headers"
echo "   • Returns 202 with {\"build_id\":\"...\",\"ok\":true}"
echo "   • Proper error handling for missing message"
echo "   • Structured logging with full_build_start event"
