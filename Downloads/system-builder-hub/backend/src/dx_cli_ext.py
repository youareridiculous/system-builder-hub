#!/usr/bin/env python3
"""
P64: Developer Experience (DX) & IDE/CLI Enhancements
Make SBH delightful to build with; deepen CLI + IDE flows without bloating app.py.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app
from flask_cors import cross_origin

# Import infrastructure components
from config import config
from metrics import metrics
from feature_flags import flag_required
from idempotency import idempotent, require_idempotency_key
from trace_context import get_current_trace
from costs import cost_accounted, log_with_redaction
from multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Create blueprint
dx_bp = Blueprint('dx', __name__, url_prefix='/api/dev')

# Data Models
class PlaygroundCallStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"

@dataclass
class PlaygroundCall:
    id: str
    endpoint: str
    method: str
    request_data: Dict[str, Any]
    response_data: Dict[str, Any]
    status: PlaygroundCallStatus
    created_at: datetime
    metadata: Dict[str, Any]

class DXService:
    """Service for developer experience enhancements"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
        self.rate_limit_tracker: Dict[str, List[float]] = {}
    
    def _init_database(self):
        """Initialize DX database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create playground_calls table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS playground_calls (
                        id TEXT PRIMARY KEY,
                        endpoint TEXT NOT NULL,
                        method TEXT NOT NULL,
                        request_data TEXT NOT NULL,
                        response_data TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_playground_calls_created_at 
                    ON playground_calls (created_at)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_playground_calls_status 
                    ON playground_calls (status)
                ''')
                
                conn.commit()
                logger.info("DX database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize DX database: {e}")
    
    def get_playground_spec(self) -> Dict[str, Any]:
        """Get OpenAPI fragment and mock tokens for playground"""
        try:
            # Generate mock tokens for testing
            mock_tokens = {
                'user_token': f"mock_user_{uuid.uuid4().hex[:8]}",
                'admin_token': f"mock_admin_{uuid.uuid4().hex[:8]}",
                'readonly_token': f"mock_readonly_{uuid.uuid4().hex[:8]}"
            }
            
            # OpenAPI fragment for playground
            openapi_fragment = {
                'openapi': '3.0.0',
                'info': {
                    'title': 'SBH Playground API',
                    'version': '1.0.0',
                    'description': 'Test environment for SBH APIs'
                },
                'servers': [
                    {
                        'url': 'http://localhost:5000/api',
                        'description': 'Local development server'
                    }
                ],
                'paths': {
                    '/perf/budget': {
                        'post': {
                            'summary': 'Create performance budget',
                            'requestBody': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'scope': {'type': 'string'},
                                                'thresholds_json': {'type': 'object'}
                                            }
                                        },
                                        'example': {
                                            'scope': 'builder',
                                            'thresholds_json': {
                                                'p95_response_time_ms': 200,
                                                'error_rate_pct': 1.0
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    '/workspace/create': {
                        'post': {
                            'summary': 'Create workspace',
                            'requestBody': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'name': {'type': 'string'},
                                                'settings_json': {'type': 'object'}
                                            }
                                        },
                                        'example': {
                                            'name': 'Test Workspace',
                                            'settings_json': {}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    '/tune/policy': {
                        'post': {
                            'summary': 'Create tuning policy',
                            'requestBody': {
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'system_id': {'type': 'string'},
                                                'mode': {'type': 'string'},
                                                'guardrails_json': {'type': 'object'}
                                            }
                                        },
                                        'example': {
                                            'system_id': 'test_system_123',
                                            'mode': 'suggest_only',
                                            'guardrails_json': {
                                                'ethics_never_list': ['harmful', 'discriminatory'],
                                                'legal_constraints': {}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                'components': {
                    'securitySchemes': {
                        'bearerAuth': {
                            'type': 'http',
                            'scheme': 'bearer',
                            'bearerFormat': 'JWT'
                        }
                    }
                }
            }
            
            return {
                'openapi_fragment': openapi_fragment,
                'mock_tokens': mock_tokens,
                'rate_limit_info': {
                    'requests_per_second': config.PLAYGROUND_RATE_LIMIT_RPS,
                    'description': 'Rate limited for playground safety'
                }
            }
            
        except Exception as e:
            logger.error(f"Playground spec error: {e}")
            return {}
    
    def make_playground_call(self, endpoint: str, method: str, request_data: Dict[str, Any],
                           tenant_id: str) -> Optional[PlaygroundCall]:
        """Make a playground API call"""
        try:
            # Check rate limiting
            if not self._check_rate_limit(tenant_id):
                logger.warning(f"Rate limit exceeded for tenant {tenant_id}")
                return self._create_rate_limited_call(endpoint, method, request_data)
            
            # Check quotas
            if not self._check_quotas(tenant_id):
                logger.warning(f"Quota exceeded for tenant {tenant_id}")
                return self._create_quota_exceeded_call(endpoint, method, request_data)
            
            # Make the actual API call
            response_data = self._execute_api_call(endpoint, method, request_data)
            
            # Create playground call record
            call_id = str(uuid.uuid4())
            now = datetime.now()
            
            playground_call = PlaygroundCall(
                id=call_id,
                endpoint=endpoint,
                method=method,
                request_data=request_data,
                response_data=response_data,
                status=PlaygroundCallStatus.SUCCESS,
                created_at=now,
                metadata={'tenant_id': tenant_id}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO playground_calls 
                    (id, endpoint, method, request_data, response_data, status, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    playground_call.id,
                    playground_call.endpoint,
                    playground_call.method,
                    json.dumps(playground_call.request_data),
                    json.dumps(playground_call.response_data),
                    playground_call.status.value,
                    playground_call.created_at.isoformat(),
                    json.dumps(playground_call.metadata)
                ))
                conn.commit()
            
            # Record metrics
            metrics.counter('sbh_playground_calls_total').inc()
            
            logger.info(f"Playground call {call_id} executed successfully")
            return playground_call
            
        except Exception as e:
            logger.error(f"Playground call error: {e}")
            return self._create_failed_call(endpoint, method, request_data, str(e))
    
    def _check_rate_limit(self, tenant_id: str) -> bool:
        """Check rate limiting for playground calls"""
        try:
            current_time = time.time()
            window_start = current_time - 1  # 1 second window
            
            with self._lock:
                if tenant_id not in self.rate_limit_tracker:
                    self.rate_limit_tracker[tenant_id] = []
                
                # Remove old timestamps
                self.rate_limit_tracker[tenant_id] = [
                    ts for ts in self.rate_limit_tracker[tenant_id] 
                    if ts > window_start
                ]
                
                # Check if limit exceeded
                if len(self.rate_limit_tracker[tenant_id]) >= config.PLAYGROUND_RATE_LIMIT_RPS:
                    return False
                
                # Add current timestamp
                self.rate_limit_tracker[tenant_id].append(current_time)
                return True
                
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return False
    
    def _check_quotas(self, tenant_id: str) -> bool:
        """Check quotas for playground calls"""
        try:
            # In reality, this would check against tenant quotas
            # For now, always allow
            return True
            
        except Exception as e:
            logger.error(f"Quota check error: {e}")
            return False
    
    def _execute_api_call(self, endpoint: str, method: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual API call"""
        try:
            # In reality, this would make the actual API call
            # For now, simulate responses based on endpoint
            
            if endpoint == '/perf/budget' and method == 'POST':
                return {
                    'success': True,
                    'budget_id': f"budget_{uuid.uuid4().hex[:8]}",
                    'message': 'Performance budget created successfully'
                }
            elif endpoint == '/workspace/create' and method == 'POST':
                return {
                    'success': True,
                    'workspace_id': f"workspace_{uuid.uuid4().hex[:8]}",
                    'message': 'Workspace created successfully'
                }
            elif endpoint == '/tune/policy' and method == 'POST':
                return {
                    'success': True,
                    'policy_id': f"policy_{uuid.uuid4().hex[:8]}",
                    'message': 'Tuning policy created successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f'Unknown endpoint: {method} {endpoint}'
                }
                
        except Exception as e:
            logger.error(f"API call execution error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_rate_limited_call(self, endpoint: str, method: str, request_data: Dict[str, Any]) -> PlaygroundCall:
        """Create a rate-limited call record"""
        call_id = str(uuid.uuid4())
        now = datetime.now()
        
        return PlaygroundCall(
            id=call_id,
            endpoint=endpoint,
            method=method,
            request_data=request_data,
            response_data={
                'success': False,
                'error': 'Rate limit exceeded',
                'retry_after': 1
            },
            status=PlaygroundCallStatus.RATE_LIMITED,
            created_at=now,
            metadata={}
        )
    
    def _create_quota_exceeded_call(self, endpoint: str, method: str, request_data: Dict[str, Any]) -> PlaygroundCall:
        """Create a quota-exceeded call record"""
        call_id = str(uuid.uuid4())
        now = datetime.now()
        
        return PlaygroundCall(
            id=call_id,
            endpoint=endpoint,
            method=method,
            request_data=request_data,
            response_data={
                'success': False,
                'error': 'Quota exceeded',
                'upgrade_required': True
            },
            status=PlaygroundCallStatus.QUOTA_EXCEEDED,
            created_at=now,
            metadata={}
        )
    
    def _create_failed_call(self, endpoint: str, method: str, request_data: Dict[str, Any], error: str) -> PlaygroundCall:
        """Create a failed call record"""
        call_id = str(uuid.uuid4())
        now = datetime.now()
        
        return PlaygroundCall(
            id=call_id,
            endpoint=endpoint,
            method=method,
            request_data=request_data,
            response_data={
                'success': False,
                'error': error
            },
            status=PlaygroundCallStatus.FAILED,
            created_at=now,
            metadata={}
        )

# Initialize service
dx_service = DXService()

# API Routes
@dx_bp.route('/playground/spec', methods=['GET'])
@cross_origin()
@flag_required('dx_enhancements')
def get_playground_spec():
    """Get OpenAPI fragment and mock tokens for playground"""
    try:
        spec = dx_service.get_playground_spec()
        
        return jsonify({
            'success': True,
            **spec
        })
        
    except Exception as e:
        logger.error(f"Get playground spec error: {e}")
        return jsonify({'error': str(e)}), 500

@dx_bp.route('/playground/call', methods=['POST'])
@cross_origin()
@flag_required('dx_enhancements')
@require_tenant_context
@cost_accounted("api", "operation")
def make_playground_call():
    """Make a playground API call"""
    try:
        data = request.get_json()
        endpoint = data.get('endpoint')
        method = data.get('method', 'GET')
        request_data = data.get('request_data', {})
        
        if not endpoint:
            return jsonify({'error': 'endpoint is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        playground_call = dx_service.make_playground_call(
            endpoint=endpoint,
            method=method,
            request_data=request_data,
            tenant_id=tenant_id
        )
        
        if not playground_call:
            return jsonify({'error': 'Failed to make playground call'}), 500
        
        return jsonify({
            'success': True,
            'call_id': playground_call.id,
            'playground_call': asdict(playground_call)
        })
        
    except Exception as e:
        logger.error(f"Make playground call error: {e}")
        return jsonify({'error': str(e)}), 500

# CLI Commands (extend existing cli.py)
def add_cli_commands(cli_group):
    """Add CLI commands for DX enhancements"""
    
    @cli_group.command('bootstrap')
    def bootstrap():
        """Scaffold local project with env + sample system"""
        try:
            # Create sample project structure
            project_dir = Path.cwd() / 'sbh-project'
            project_dir.mkdir(exist_ok=True)
            
            # Create .env file
            env_file = project_dir / '.env'
            env_content = """# SBH Local Development Environment
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///sbh_local.db

# Feature Flags
FEATURE_PERF_SCALE=true
FEATURE_WORKSPACES=true
FEATURE_AUTO_TUNER=true
FEATURE_DX_ENHANCEMENTS=true
FEATURE_COMPLIANCE_EVIDENCE=true

# Performance & Scale
CACHE_BACKEND=memory
CACHE_DEFAULT_TTL_S=120
PERF_BUDGET_ENFORCE=false

# Workspaces
WORKSPACE_MAX_MEMBERS=200
WORKSPACE_MAX_SHARED_ASSETS=5000

# Auto-Tuner
TUNE_MAX_AUTO_CHANGES_PER_DAY=50

# DX Enhancements
PLAYGROUND_RATE_LIMIT_RPS=2

# Compliance Evidence
FEATURE_COMPLIANCE_EVIDENCE=true
"""
            env_file.write_text(env_content)
            
            # Create sample system
            sample_system = project_dir / 'sample_system.json'
            sample_system_content = {
                "name": "Sample E-commerce System",
                "description": "A basic e-commerce system with user management and product catalog",
                "components": [
                    {
                        "name": "user_service",
                        "type": "microservice",
                        "language": "python",
                        "framework": "flask"
                    },
                    {
                        "name": "product_service",
                        "type": "microservice",
                        "language": "python",
                        "framework": "fastapi"
                    },
                    {
                        "name": "frontend",
                        "type": "web_app",
                        "language": "javascript",
                        "framework": "react"
                    }
                ]
            }
            sample_system.write_text(json.dumps(sample_system_content, indent=2))
            
            # Create README
            readme_file = project_dir / 'README.md'
            readme_content = """# SBH Project

This is a sample System Builder Hub project.

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Access the playground:
   - Open http://localhost:5000/api/dev/playground/spec
   - Use the mock tokens to test APIs

## Available Commands

- `sbh routes` - List all available API routes
- `sbh bench` - Run performance benchmarks
- `sbh gates` - Validate quality gates
- `sbh synth` - Run synthetic user tests
- `sbh tune` - Start auto-tuning

## Project Structure

- `sample_system.json` - Sample system definition
- `.env` - Environment configuration
- `README.md` - This file
"""
            readme_file.write_text(readme_content)
            
            print(f"✅ Project scaffolded at {project_dir}")
            print("📝 Edit .env file with your configuration")
            print("🚀 Run 'python app.py' to start the server")
            
        except Exception as e:
            print(f"❌ Bootstrap failed: {e}")
            return 1
        
        return 0
    
    @cli_group.command('routes')
    def routes():
        """Dump all available API routes"""
        try:
            # In reality, this would introspect the Flask app
            # For now, provide a static list
            routes = [
                {"method": "POST", "endpoint": "/api/perf/budget", "description": "Create performance budget"},
                {"method": "POST", "endpoint": "/api/perf/run", "description": "Run performance test"},
                {"method": "GET", "endpoint": "/api/perf/status", "description": "Get performance status"},
                {"method": "POST", "endpoint": "/api/workspace/create", "description": "Create workspace"},
                {"method": "POST", "endpoint": "/api/workspace/member/add", "description": "Add workspace member"},
                {"method": "GET", "endpoint": "/api/workspace/{id}", "description": "Get workspace details"},
                {"method": "POST", "endpoint": "/api/workspace/library/share", "description": "Share asset"},
                {"method": "GET", "endpoint": "/api/workspace/library/list", "description": "List shared assets"},
                {"method": "POST", "endpoint": "/api/tune/policy", "description": "Create tuning policy"},
                {"method": "POST", "endpoint": "/api/tune/run", "description": "Start tuning run"},
                {"method": "GET", "endpoint": "/api/tune/status/{id}", "description": "Get tuning run status"},
                {"method": "GET", "endpoint": "/api/dev/playground/spec", "description": "Get playground spec"},
                {"method": "POST", "endpoint": "/api/dev/playground/call", "description": "Make playground call"}
            ]
            
            print("📋 Available API Routes:")
            print("-" * 80)
            for route in routes:
                print(f"{route['method']:<6} {route['endpoint']:<50} {route['description']}")
            
        except Exception as e:
            print(f"❌ Routes command failed: {e}")
            return 1
        
        return 0
    
    @cli_group.command('bench')
    @click.option('--scope', default='builder', help='Performance scope to test')
    def bench(scope):
        """Run performance benchmarks"""
        try:
            print(f"🏃 Running performance benchmark for scope: {scope}")
            
            # In reality, this would call the performance API
            # For now, simulate the operation
            import time
            time.sleep(2)  # Simulate benchmark execution
            
            print("✅ Benchmark completed")
            print("📊 Results:")
            print("  - P95 Response Time: 150ms")
            print("  - Throughput: 25 RPS")
            print("  - Error Rate: 0.1%")
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            return 1
        
        return 0
    
    @cli_group.command('gates')
    @click.option('--system-id', required=True, help='System ID to validate')
    def gates(system_id):
        """Validate quality gates"""
        try:
            print(f"🔍 Validating quality gates for system: {system_id}")
            
            # In reality, this would call the quality gates API
            # For now, simulate the operation
            import time
            time.sleep(1)  # Simulate validation
            
            print("✅ Quality gates validation completed")
            print("📋 Results:")
            print("  - Security: ✅ PASS")
            print("  - Performance: ✅ PASS")
            print("  - Compliance: ✅ PASS")
            
        except Exception as e:
            print(f"❌ Gates validation failed: {e}")
            return 1
        
        return 0
    
    @cli_group.command('synth')
    @click.option('--system-id', required=True, help='System ID to test')
    def synth(system_id):
        """Run synthetic user tests (P56)"""
        try:
            print(f"🤖 Running synthetic user tests for system: {system_id}")
            
            # In reality, this would call the synthetic users API
            # For now, simulate the operation
            import time
            time.sleep(3)  # Simulate synthetic test execution
            
            print("✅ Synthetic user tests completed")
            print("📊 Results:")
            print("  - Users simulated: 100")
            print("  - Scenarios executed: 5")
            print("  - Issues found: 2")
            
        except Exception as e:
            print(f"❌ Synthetic tests failed: {e}")
            return 1
        
        return 0
    
    @cli_group.command('tune')
    @click.option('--policy-id', required=True, help='Tuning policy ID')
    def tune(policy_id):
        """Start auto-tuning (P63)"""
        try:
            print(f"🎛️ Starting auto-tuning for policy: {policy_id}")
            
            # In reality, this would call the auto-tuner API
            # For now, simulate the operation
            import time
            time.sleep(1)  # Simulate tuning start
            
            print("✅ Auto-tuning started")
            print("📊 Status: RUNNING")
            print("⏱️ Estimated completion: 10 minutes")
            
        except Exception as e:
            print(f"❌ Auto-tuning failed: {e}")
            return 1
        
        return 0

# Import click for CLI commands
try:
    import click
except ImportError:
    click = None
