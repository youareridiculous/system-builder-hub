"""
Debug script to test template location
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app

app = create_app()

print(f"App root path: {app.root_path}")
print(f"Template folder: {app.template_folder}")
print(f"Static folder: {app.static_folder}")

# Check if template exists
template_path = os.path.join(app.template_folder, 'ui', 'tasks.html')
print(f"Looking for template at: {template_path}")
print(f"Template exists: {os.path.exists(template_path)}")

# List templates directory
templates_dir = os.path.join(app.template_folder, 'ui')
if os.path.exists(templates_dir):
    print(f"Templates in {templates_dir}:")
    for f in os.listdir(templates_dir):
        print(f"  - {f}")
