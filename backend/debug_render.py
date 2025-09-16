"""
Debug script to test template rendering
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app
from flask import render_template

app = create_app()

with app.app_context():
    try:
        print("Testing template rendering...")
        result = render_template('ui/tasks.html')
        print("Template rendered successfully!")
        print(f"Length: {len(result)}")
        print("First 200 chars:")
        print(result[:200])
    except Exception as e:
        print(f"Template rendering failed: {e}")
        import traceback
        traceback.print_exc()
