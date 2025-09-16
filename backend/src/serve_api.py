"""
Serve API - Serve generated applications
"""
import os
import json
import logging
import subprocess
import socket
import threading
import time
import requests
from typing import Dict, Optional
from flask import Blueprint, request, jsonify, send_from_directory, current_app, Response
from .auth_api import require_auth
from .tenancy.decorators import require_tenant
from .scaffold import get_build_path, GENERATED_ROOT

logger = logging.getLogger(__name__)

# Create blueprint
serve_api_bp = Blueprint("serve_api", __name__)

# In-memory registry of running backends and frontends
running_backends: Dict[str, Dict] = {}
running_frontends: Dict[str, Dict] = {}

def find_free_port() -> int:
    """Find a free port to use for backend services"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def _probe_backend(port: int, timeout: float = 0.6) -> bool:
    """Probe backend health on given port"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            return data.get('status') == 'healthy'
        return False
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        return False

def ensure_backend_started(build_id: str) -> Optional[int]:
    """Ensure backend is started and return port"""
    if build_id in running_backends:
        backend_info = running_backends[build_id]
        if backend_info['running']:
            return backend_info['port']
    
    build_path = get_build_path(build_id)
    backend_path = os.path.join(build_path, 'backend')
    app_py = os.path.join(backend_path, 'app.py')
    
    if not os.path.exists(app_py):
        logger.warning(f"Backend app.py not found for build {build_id}")
        return None
    
    # Find free port
    port = find_free_port()
    
    try:
        # Start backend process
        process = subprocess.Popen(
            ['python', 'app.py'],
            cwd=backend_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, 'PORT': str(port)}
        )
        
        # Wait a moment for startup
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            running_backends[build_id] = {
                'process': process,
                'port': port,
                'pid': process.pid,
                'running': True,
                'started_at': time.time()
            }
            logger.info(f"Started backend for build {build_id} on port {port}")
            return port
        else:
            logger.error(f"Backend failed to start for build {build_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error starting backend for build {build_id}: {e}")
        return None

def _get_backend_port_from_manifest(build_id: str) -> Optional[int]:
    """Get backend port from manifest.json"""
    try:
        build_path = get_build_path(build_id)
        manifest_path = os.path.join(build_path, 'manifest.json')
        
        if not os.path.exists(manifest_path):
            return None
            
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Get port from manifest, default to 8000
        ports = manifest.get('ports', {})
        return ports.get('backend', 8000)
        
    except Exception as e:
        logger.warning(f"Error reading manifest for build {build_id}: {e}")
        return None

def _resolve_backend_port(build_id: str) -> Optional[int]:
    """Resolve backend port from tracked process or manifest + probe"""
    # First check if we're managing this backend
    if build_id in running_backends:
        backend_info = running_backends[build_id]
        if backend_info['running']:
            return backend_info['port']
    
    # Check manifest for port and probe
    port = _get_backend_port_from_manifest(build_id)
    if port and _probe_backend(port):
        logger.info(f"SERVE: Attached to running backend on port {port} for build {build_id}")
        return port
    
    return None

def _probe_frontend(port: int, timeout: float = 0.6) -> bool:
    """Probe frontend health on given port"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/", timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

def _get_frontend_port_from_manifest(build_id: str) -> Optional[int]:
    """Get frontend port from manifest.json"""
    try:
        build_path = get_build_path(build_id)
        manifest_path = os.path.join(build_path, 'manifest.json')
        
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                return manifest.get('ports', {}).get('frontend', 3000)
    except Exception as e:
        logger.error(f"Error reading manifest for build {build_id}: {e}")
    
    return None

def _resolve_frontend_port(build_id: str) -> Optional[int]:
    """Resolve frontend port from tracked process or manifest"""
    # First check if we have a tracked process
    if build_id in running_frontends:
        frontend_info = running_frontends[build_id]
        if frontend_info['running']:
            return frontend_info['port']
    
    # Then check manifest and probe
    port = _get_frontend_port_from_manifest(build_id)
    if port and _probe_frontend(port):
        logger.info(f"Attached to running frontend on port {port} for build {build_id}")
        return port
    
    return None

def ensure_frontend_started(build_id: str) -> Optional[int]:
    """Ensure frontend is started and return port"""
    if build_id in running_frontends:
        frontend_info = running_frontends[build_id]
        if frontend_info['running']:
            return frontend_info['port']
    
    build_path = get_build_path(build_id)
    frontend_path = os.path.join(build_path, 'frontend')
    package_json = os.path.join(frontend_path, 'package.json')
    
    if not os.path.exists(package_json):
        logger.warning(f"Frontend package.json not found for build {build_id}")
        return None
    
    # Use default port 3000 for frontend
    port = 3000
    
    try:
        # Start frontend process
        process = subprocess.Popen(
            ['npm', 'run', 'dev', '--', '-p', str(port)],
            cwd=frontend_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ}
        )
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            running_frontends[build_id] = {
                'process': process,
                'port': port,
                'pid': process.pid,
                'running': True,
                'started_at': time.time()
            }
            logger.info(f"Started frontend for build {build_id} on port {port}")
            return port
        else:
            logger.error(f"Frontend failed to start for build {build_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error starting frontend for build {build_id}: {e}")
        return None

def cleanup_backends():
    """Clean up stopped backend processes"""
    global running_backends
    
    to_remove = []
    for build_id, backend_info in running_backends.items():
        if not backend_info['running']:
            continue
            
        process = backend_info['process']
        if process.poll() is not None:
            # Process has stopped
            backend_info['running'] = False
            to_remove.append(build_id)
            logger.info(f"Backend for build {build_id} has stopped")
    
    for build_id in to_remove:
        del running_backends[build_id]

def cleanup_frontends():
    """Clean up stopped frontend processes"""
    global running_frontends
    
    to_remove = []
    for build_id, frontend_info in running_frontends.items():
        if not frontend_info['running']:
            continue
            
        process = frontend_info['process']
        if process.poll() is not None:
            # Process has stopped
            frontend_info['running'] = False
            to_remove.append(build_id)
            logger.info(f"Frontend for build {build_id} has stopped")
    
    for build_id in to_remove:
        del running_frontends[build_id]

@serve_api_bp.route('/serve/<build_id>')
@require_auth
def serve_app(build_id):
    """Serve the generated application"""
    try:
        # Clean up stopped backends and frontends
        cleanup_backends()
        cleanup_frontends()
        
        build_path = get_build_path(build_id)
        if not os.path.exists(build_path):
            return jsonify({'error': 'Build not found'}), 404
        
        # Try to resolve frontend port
        frontend_port = _resolve_frontend_port(build_id)
        
        if frontend_port:
            # Frontend is running, proxy to it
            try:
                response = requests.get(f"http://127.0.0.1:{frontend_port}/", timeout=1.0)
                if response.status_code == 200:
                    # Return the frontend content
                    return Response(response.content, content_type=response.headers.get('content-type', 'text/html'))
            except requests.RequestException as e:
                logger.warning(f"Failed to proxy to frontend on port {frontend_port}: {e}")
        
        # Try to start frontend if not running
        frontend_port = ensure_frontend_started(build_id)
        if frontend_port:
            try:
                # Wait a bit more for the frontend to be ready
                time.sleep(2)
                response = requests.get(f"http://127.0.0.1:{frontend_port}/", timeout=1.0)
                if response.status_code == 200:
                    return Response(response.content, content_type=response.headers.get('content-type', 'text/html'))
            except requests.RequestException as e:
                logger.warning(f"Failed to proxy to started frontend on port {frontend_port}: {e}")
        
        # Fall back to simple HTML shell
        return _create_simple_shell(build_id, build_path)
        
    except Exception as e:
        logger.error(f"Error serving app for build {build_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@serve_api_bp.route('/serve/<build_id>/status')
@require_auth
def serve_status(build_id):
    """Get status of the served application"""
    try:
        cleanup_backends()
        cleanup_frontends()
        
        build_path = get_build_path(build_id)
        if not os.path.exists(build_path):
            return jsonify({'error': 'Build not found'}), 404
        
        backend_info = running_backends.get(build_id, {})
        frontend_info = running_frontends.get(build_id, {})
        
        # Check if we have a tracked backend process
        if backend_info.get('running'):
            backend_running = True
            backend_port = backend_info.get('port')
            backend_pid = backend_info.get('pid')
        else:
            # No tracked process, check if backend is running on manifest port
            port = _get_backend_port_from_manifest(build_id)
            backend_running = False
            backend_port = None
            backend_pid = None
            
            if port and _probe_backend(port):
                backend_running = True
                backend_port = port
                backend_pid = None  # Not managed by us
                logger.info(f"SERVE: Attached to running backend on port {port} for build {build_id}")
        
        # Check if we have a tracked frontend process
        if frontend_info.get('running'):
            frontend_running = True
            frontend_port = frontend_info.get('port')
            frontend_pid = frontend_info.get('pid')
        else:
            # No tracked process, check if frontend is running on manifest port
            port = _get_frontend_port_from_manifest(build_id)
            frontend_running = False
            frontend_port = None
            frontend_pid = None
            
            if port and _probe_frontend(port):
                frontend_running = True
                frontend_port = port
                frontend_pid = None  # Not managed by us
                logger.info(f"SERVE: Attached to running frontend on port {port} for build {build_id}")
        
        status = {
            'build_id': build_id,
            'backend_running': backend_running,
            'backend_port': backend_port,
            'backend_pid': backend_pid,
            'frontend_running': frontend_running,
            'frontend_port': frontend_port,
            'frontend_pid': frontend_pid,
            'frontend_exists': os.path.exists(os.path.join(build_path, 'frontend')),
            'backend_exists': os.path.exists(os.path.join(build_path, 'backend')),
            'manifest_exists': os.path.exists(os.path.join(build_path, 'manifest.json'))
        }
        
        # Add manifest info if available
        manifest_path = os.path.join(build_path, 'manifest.json')
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                status['manifest'] = manifest
            except Exception as e:
                logger.warning(f"Error reading manifest for build {build_id}: {e}")
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting status for build {build_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@serve_api_bp.route('/serve/<build_id>/api/<path:api_path>')
@require_auth
def proxy_api(build_id, api_path):
    """Proxy API requests to the backend"""
    try:
        # Resolve backend port
        port = _resolve_backend_port(build_id)
        if not port:
            return jsonify({'error': 'Backend not available'}), 503
        
        # Build the target URL
        target_url = f"http://127.0.0.1:{port}/api/{api_path}"
        
        # Prepare headers (exclude hop-by-hop headers)
        headers = {}
        for key, value in request.headers.items():
            if key.lower() not in ['host', 'connection', 'content-length', 'transfer-encoding']:
                headers[key] = value
        
        # Make the request to the backend
        try:
            response = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                params=request.args,
                timeout=30
            )
            
            # Create Flask response
            flask_response = Response(
                response.content,
                status=response.status_code,
                headers=dict(response.headers)
            )
            
            return flask_response
            
        except requests.RequestException as e:
            logger.error(f"Error proxying request to backend for build {build_id}: {e}")
            return jsonify({'error': 'Backend not available'}), 503
        
    except Exception as e:
        logger.error(f"Error proxying API for build {build_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@serve_api_bp.route('/serve/<build_id>/start', methods=['POST'])
@require_auth
def start_backend(build_id):
    """Start the backend for a build"""
    try:
        build_path = get_build_path(build_id)
        if not os.path.exists(build_path):
            return jsonify({'error': 'Build not found'}), 404
        
        # Check if backend is already running on manifest port
        port = _get_backend_port_from_manifest(build_id)
        if port and _probe_backend(port):
            # Backend is already running, attach to it
            running_backends[build_id] = {
                'process': None,
                'port': port,
                'pid': None,
                'running': True,
                'started_at': time.time()
            }
            logger.info(f"Attached to existing backend on port {port} for build {build_id}")
            return jsonify({
                'message': f'Attached to existing backend on port {port}',
                'port': port,
                'pid': None
            })
        
        # Start new backend
        port = ensure_backend_started(build_id)
        if not port:
            return jsonify({'error': 'Failed to start backend'}), 500
        
        return jsonify({
            'message': f'Backend started on port {port}',
            'port': port,
            'pid': running_backends[build_id]['pid']
        })
        
    except Exception as e:
        logger.error(f"Error starting backend for build {build_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@serve_api_bp.route('/serve/<build_id>/start-frontend', methods=['POST'])
@require_auth
def start_frontend(build_id):
    """Start the frontend for a build"""
    try:
        build_path = get_build_path(build_id)
        if not os.path.exists(build_path):
            return jsonify({'error': 'Build not found'}), 404
        
        # Check if frontend is already running on manifest port
        port = _get_frontend_port_from_manifest(build_id)
        if port and _probe_frontend(port):
            # Frontend is already running, attach to it
            running_frontends[build_id] = {
                'process': None,
                'port': port,
                'pid': None,
                'running': True,
                'started_at': time.time()
            }
            logger.info(f"Attached to existing frontend on port {port} for build {build_id}")
            return jsonify({
                'message': f'Attached to existing frontend on port {port}',
                'port': port,
                'pid': None
            })
        
        # Start new frontend
        port = ensure_frontend_started(build_id)
        if not port:
            return jsonify({
                'error': 'Failed to start frontend',
                'details': 'Check that npm install completed successfully and the frontend can start manually with: npm run dev -- --port 3000'
            }), 500
        
        return jsonify({
            'message': f'Frontend started on port {port}',
            'port': port,
            'pid': running_frontends[build_id]['pid']
        })
        
    except Exception as e:
        logger.error(f"Error starting frontend for build {build_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def _create_simple_shell(build_id: str, build_path: str):
    """Create a simple HTML shell for apps without frontend"""
    manifest_path = os.path.join(build_path, 'manifest.json')
    manifest = {}
    
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception as e:
            logger.warning(f"Error reading manifest for build {build_id}: {e}")
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{manifest.get('name', 'Generated App')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        .content {{
            background: #f8f9fa;
            padding: 2rem;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }}
        .api-section {{
            margin-top: 2rem;
            padding: 1rem;
            background: #e9ecef;
            border-radius: 4px;
        }}
        .api-endpoint {{
            font-family: monospace;
            background: #f8f9fa;
            padding: 0.5rem;
            border-radius: 3px;
            margin: 0.5rem 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{manifest.get('name', 'Generated App')}</h1>
        <p>{manifest.get('template', 'unknown')} template</p>
    </div>
    
    <div class="content">
        <h2>Application Status</h2>
        <p>Build ID: {build_id}</p>
        <p>Template: {manifest.get('template', 'unknown')}</p>
        <p>Created: {manifest.get('created_at', 'unknown')}</p>
        
        <div class="api-section">
            <h3>API Endpoints</h3>
            <p>This application provides the following API endpoints:</p>
            <div class="api-endpoint">GET /api/health</div>
            <div class="api-endpoint">GET /api/accounts</div>
            <div class="api-endpoint">GET /api/contacts</div>
            <div class="api-endpoint">GET /api/deals</div>
            <div class="api-endpoint">GET /api/pipelines</div>
            <div class="api-endpoint">GET /api/activities</div>
        </div>
        
        <p><strong>Note:</strong> This is a simple shell. The full frontend application would be served here
.</p>

    </div>
</body>
</html>
'''
    
    return html_content, 200, {'Content-Type': 'text/html'}
