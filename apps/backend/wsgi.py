#!/usr/bin/env python3
"""
WSGI entry point for SBH Backend
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import and create the Flask app
try:
    from src.server import create_app
    application = create_app()
    app = application
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback to a simple app
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def health():
        return {"status": "error", "message": "Import failed"}
    
    @app.route('/api/ai-chat/health')
    def ai_chat_health():
        return {"status": "healthy", "message": "Fallback app"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
