#!/usr/bin/env python3
"""Minimal test server for Co-Builder Apply Engine"""

import os
import sys
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_app():
    """Create minimal Flask app with Co-Builder endpoints"""
    app = Flask(__name__)
    CORS(app)
    
    # Health check
    @app.route('/healthz')
    def health_check():
        return jsonify({'status': 'healthy', 'mode': 'test'})
    
    # Co-Builder ask endpoint
    @app.route('/api/cobuilder/ask', methods=['POST'])
    def cobuilder_ask():
        try:
            data = request.get_json()
            message = data.get('message', '')
            apply_changes = data.get('apply', False)
            
            logger.info(f"Co-Builder request: {message[:100]}... (apply={apply_changes})")
            
            # Import and use the generator
            from cobuilder.generator import CoBuilderGenerator
            from cobuilder.applier import apply_single_file
            
            # Create mock client for testing
            class MockClient:
                def __init__(self):
                    self.chat = Mock()
                    self.chat.completions = Mock()
                    self.chat.completions.create = Mock()
                    
                    # Mock response
                    mock_resp = Mock()
                    mock_resp.choices = [Mock()]
                    mock_resp.choices[0].message.content = f'''
                    {{
                        "file": "venture_os/__init__.py",
                        "diff": "--- /dev/null\\n+++ venture_os/__init__.py\\n@@ -0,0 +1,1 @@\\n+__version__ = \\"0.0.1\\"\\n",
                        "content": "__version__ = \\"0.0.1\\"\\n",
                        "response": "Created venture_os/__init__.py with version",
                        "snippet": "print(__version__)"
                    }}
                    '''
                    self.chat.completions.create.return_value = mock_resp
            
            # Test the generator
            generator = CoBuilderGenerator(
                llm_client=MockClient(),
                model_default="gpt-4o-mini"
            )
            
            # Generate the change
            result = generator.apply_change(
                prompt=message,
                tenant_id=request.headers.get('X-Tenant-ID', 'demo'),
                request_id="test123",
                deadline_ts=time.time() + 60
            )
            
            response_data = {
                "action_type": "build",
                "message": result.response,
                "file": result.file,
                "diff": result.diff,
                "content": result.content,
                "snippet": result.snippet,
                "model": result.model,
                "elapsed_ms": result.elapsed_ms,
                "llm_generated": result.llm_generated,
            }
            
            # Apply if requested
            if apply_changes and result.file and result.content:
                try:
                    apply_result = apply_single_file(result.file, result.content)
                    response_data["applied"] = True
                    response_data["apply"] = {
                        "file": apply_result.file,
                        "bytes_written": apply_result.bytes_written,
                        "created": apply_result.created,
                        "sha256": apply_result.sha256,
                    }
                    logger.info(f"Applied change to {apply_result.file}")
                except Exception as e:
                    logger.error(f"Apply failed: {e}")
                    response_data["applied"] = False
                    response_data["apply_error"] = str(e)
            
            return jsonify({
                "success": True,
                "data": response_data
            })
            
        except Exception as e:
            logger.error(f"Co-Builder error: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    # File inspection endpoint
    @app.route('/api/cobuilder/files/inspect')
    def inspect_file():
        try:
            path = request.args.get("path", "")
            from cobuilder.applier import _safe_join, ALLOWED_ROOT
            
            dest = _safe_join(ALLOWED_ROOT, os.path.normpath(path))
            
            if not os.path.exists(dest):
                return jsonify({"ok": True, "data": {"exists": False}})
            
            import hashlib
            size = os.path.getsize(dest)
            with open(dest, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            
            return jsonify({
                "ok": True,
                "data": {
                    "exists": True,
                    "size": size,
                    "sha256": sha
                }
            })
            
        except Exception as e:
            logger.error(f"Inspect error: {e}")
            return jsonify({
                "ok": False,
                "error": str(e)
            }), 500
    
    return app

if __name__ == '__main__':
    import time
    print(f"Starting test server...")
    print(f"COBUILDER_USE_JSON_MODE: {os.environ.get('COBUILDER_USE_JSON_MODE', 'not set')}")
    app = create_test_app()
    app.run(host='127.0.0.1', port=5001, debug=True)
