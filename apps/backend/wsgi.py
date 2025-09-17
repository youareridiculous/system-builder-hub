#!/usr/bin/env python3
"""
WSGI entry point for SBH Backend
"""
import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import and create the Flask app
from src.server import create_app

# Create the application instance
application = create_app()

# For compatibility with gunicorn
app = application

if __name__ == "__main__":
    # This won't be used in production (gunicorn handles it)
    # But useful for local development
    app.run(host="0.0.0.0", port=8000, debug=False)
