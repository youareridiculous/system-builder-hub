"""
Export service for project bundling and GitHub sync
"""
import os
import json
import logging
import hashlib
import zipfile
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from io import BytesIO
from src.exporter.models import ExportBundle, ExportManifest, ExportFile, ExportDiff
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)

class ExportService:
    """Export service for project bundling and GitHub sync"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
        self.sbh_version = os.environ.get('SBH_VERSION', '1.0.0')
        self.max_archive_size = int(os.environ.get('EXPORT_MAX_SIZE_MB', '200')) * 1024 * 1024
        self.include_infra = os.environ.get('EXPORT_INCLUDE_INFRA', 'true').lower() == 'true'
    
    def materialize_build(self, project_id: str, tenant_id: str, 
                         include_runtime: bool = True) -> ExportBundle:
        """Materialize a complete standalone app from BuilderState"""
        try:
            # Create manifest
            manifest = ExportManifest(
                project_id=project_id,
                tenant_id=tenant_id,
                export_timestamp=datetime.utcnow(),
                sbh_version=self.sbh_version,
                files=[],
                total_size=0,
                checksum='',
                metadata={
                    'include_runtime': include_runtime,
                    'include_infra': self.include_infra,
                    'generated_at': datetime.utcnow().isoformat()
                }
            )
            
            bundle = ExportBundle(manifest=manifest, files={})
            
            # Get project builder state
            builder_state = self._get_builder_state(project_id, tenant_id)
            if not builder_state:
                raise ValueError(f"Builder state not found for project {project_id}")
            
            # Generate app files
            self._generate_app_files(bundle, builder_state, include_runtime)
            
            # Generate runtime files
            if include_runtime:
                self._generate_runtime_files(bundle)
            
            # Generate infrastructure files
            if self.include_infra:
                self._generate_infra_files(bundle)
            
            # Generate CI/CD files
            self._generate_ci_files(bundle)
            
            # Generate documentation
            self._generate_docs(bundle, builder_state)
            
            # Update checksum
            bundle.update_checksum()
            
            return bundle
            
        except Exception as e:
            logger.error(f"Error materializing build for project {project_id}: {e}")
            raise
    
    def zip_bundle(self, bundle: ExportBundle) -> BytesIO:
        """Create ZIP archive from export bundle"""
        try:
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add files in deterministic order
                sorted_files = sorted(bundle.files.items(), key=lambda x: x[0])
                
                for path, content in sorted_files:
                    # Use deterministic timestamp for all files
                    timestamp = (2024, 1, 1, 0, 0, 0)
                    
                    zip_file.writestr(
                        zipfile.ZipInfo(path, timestamp),
                        content
                    )
            
            zip_buffer.seek(0)
            
            # Check size limit
            if zip_buffer.getbuffer().nbytes > self.max_archive_size:
                raise ValueError(f"Archive size exceeds limit of {self.max_archive_size} bytes")
            
            return zip_buffer
            
        except Exception as e:
            logger.error(f"Error creating ZIP bundle: {e}")
            raise
    
    def diff_bundle(self, prev_manifest: ExportManifest, 
                   new_manifest: ExportManifest) -> ExportDiff:
        """Generate diff between two export manifests"""
        try:
            prev_files = {f.path: f.sha256 for f in prev_manifest.files}
            new_files = {f.path: f.sha256 for f in new_manifest.files}
            
            added = []
            removed = []
            changed = []
            
            # Find added and changed files
            for path, new_sha in new_files.items():
                if path not in prev_files:
                    added.append(path)
                elif prev_files[path] != new_sha:
                    changed.append(path)
            
            # Find removed files
            for path in prev_files:
                if path not in new_files:
                    removed.append(path)
            
            return ExportDiff(
                added=added,
                removed=removed,
                changed=changed,
                total_added=len(added),
                total_removed=len(removed),
                total_changed=len(changed)
            )
            
        except Exception as e:
            logger.error(f"Error generating bundle diff: {e}")
            raise
    
    def _get_builder_state(self, project_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get builder state for project"""
        try:
            # This would integrate with the actual builder state storage
            # For now, return a sample builder state
            return {
                'project_id': project_id,
                'tenant_id': tenant_id,
                'nodes': [
                    {
                        'id': 'ui_page_main',
                        'type': 'ui_page',
                        'name': 'main',
                        'config': {
                            'title': 'Main Page',
                            'description': 'Main application page'
                        }
                    },
                    {
                        'id': 'rest_api_main',
                        'type': 'rest_api',
                        'name': 'main_api',
                        'config': {
                            'base_path': '/api',
                            'description': 'Main API'
                        }
                    },
                    {
                        'id': 'db_table_items',
                        'type': 'db_table',
                        'name': 'items',
                        'config': {
                            'fields': [
                                {'name': 'id', 'type': 'uuid', 'primary': True},
                                {'name': 'name', 'type': 'string', 'required': True},
                                {'name': 'description', 'type': 'text'},
                                {'name': 'created_at', 'type': 'datetime'}
                            ]
                        }
                    }
                ],
                'connections': [
                    {
                        'from': 'ui_page_main',
                        'to': 'rest_api_main',
                        'type': 'data_source'
                    },
                    {
                        'from': 'rest_api_main',
                        'to': 'db_table_items',
                        'type': 'data_source'
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error getting builder state: {e}")
            return None
    
    def _generate_app_files(self, bundle: ExportBundle, builder_state: Dict[str, Any], 
                           include_runtime: bool):
        """Generate application files from builder state"""
        try:
            # Generate Flask app structure
            app_content = self._generate_flask_app(builder_state)
            bundle.add_file('app/__init__.py', app_content)
            
            # Generate routes
            routes_content = self._generate_routes(builder_state)
            bundle.add_file('app/routes.py', routes_content)
            
            # Generate models
            models_content = self._generate_models(builder_state)
            bundle.add_file('app/models.py', models_content)
            
            # Generate templates
            templates_content = self._generate_templates(builder_state)
            bundle.add_file('app/templates/base.html', templates_content)
            
            # Generate static files
            static_content = self._generate_static_files(builder_state)
            bundle.add_file('app/static/css/main.css', static_content)
            
        except Exception as e:
            logger.error(f"Error generating app files: {e}")
            raise
    
    def _generate_runtime_files(self, bundle: ExportBundle):
        """Generate runtime files"""
        try:
            # Requirements.txt
            requirements = '''Flask==2.3.3
gunicorn==21.2.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
python-dotenv==1.0.0
'''
            bundle.add_file('requirements.txt', requirements)
            
            # WSGI entry point
            wsgi_content = '''from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
'''
            bundle.add_file('wsgi.py', wsgi_content)
            
            # Gunicorn config
            gunicorn_content = '''bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
'''
            bundle.add_file('gunicorn.conf.py', gunicorn_content)
            
            # Dockerfile
            dockerfile_content = '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
'''
            bundle.add_file('Dockerfile', dockerfile_content)
            
        except Exception as e:
            logger.error(f"Error generating runtime files: {e}")
            raise
    
    def _generate_infra_files(self, bundle: ExportBundle):
        """Generate infrastructure files"""
        try:
            # AWS Elastic Beanstalk
            eb_content = '''{
  "AWSEBDockerrunVersion": "1",
  "Image": {
    "Name": "your-app:latest",
    "Update": "true"
  },
  "Ports": [
    {
      "ContainerPort": 8000,
      "HostPort": 80
    }
  ]
}
'''
            bundle.add_file('Dockerrun.aws.json', eb_content)
            
            # EB extensions
            eb_extensions = '''option_settings:
  aws:elasticbeanstalk:application:environment:
    FLASK_ENV: production
  aws:elasticbeanstalk:container:python:
    WSGIPath: wsgi:app
'''
            bundle.add_file('.ebextensions/01-options.config', eb_extensions)
            
            # Terraform placeholder
            terraform_content = '''# Terraform configuration for your application
# Uncomment and customize as needed

# resource "aws_ecr_repository" "app" {
#   name = "your-app"
# }

# resource "aws_ecs_cluster" "main" {
#   name = "your-app-cluster"
# }
'''
            bundle.add_file('deploy/terraform/main.tf', terraform_content)
            
        except Exception as e:
            logger.error(f"Error generating infra files: {e}")
            raise
    
    def _generate_ci_files(self, bundle: ExportBundle):
        """Generate CI/CD files"""
        try:
            # GitHub Actions workflow
            ci_content = '''name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache pip dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Lint with flake8
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Test with pytest
      run: |
        pip install pytest
        pytest -q
    
    - name: Build Docker image
      if: env.CI_BUILD_IMAGE == 'true'
      run: |
        docker build -t your-app .
    
    - name: Upload test artifacts
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: |
          test-results/
          coverage.xml
'''
            bundle.add_file('.github/workflows/ci.yml', ci_content)
            
        except Exception as e:
            logger.error(f"Error generating CI files: {e}")
            raise
    
    def _generate_docs(self, bundle: ExportBundle, builder_state: Dict[str, Any]):
        """Generate documentation"""
        try:
            # README.md
            readme_content = f'''# {builder_state.get('project_name', 'SBH Generated App')}

This application was generated by System Builder Hub.

## Features

- Flask web application
- REST API endpoints
- Database integration
- Docker support
- CI/CD pipeline

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment:
   ```bash
   cp .env.sample .env
   # Edit .env with your configuration
   ```

3. Run the application:
   ```bash
   python wsgi.py
   ```

## Development

- Run tests: `pytest`
- Lint code: `flake8`
- Build Docker: `docker build -t your-app .`

## Deployment

### Docker
```bash
docker build -t your-app .
docker run -p 8000:8000 your-app
```

### AWS Elastic Beanstalk
```bash
eb init
eb create
eb deploy
```

## Project Structure

- `app/` - Flask application
- `app/templates/` - HTML templates
- `app/static/` - Static files (CSS, JS, images)
- `deploy/` - Deployment configurations
- `.github/workflows/` - CI/CD pipelines

Generated on: {datetime.utcnow().isoformat()}
'''
            bundle.add_file('README.md', readme_content)
            
            # Environment sample
            env_sample = '''# Application Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# Security
SECRET_KEY=your-secret-key-here

# External Services
REDIS_URL=redis://localhost:6379
'''
            bundle.add_file('.env.sample', env_sample)
            
        except Exception as e:
            logger.error(f"Error generating docs: {e}")
            raise
    
    def _generate_flask_app(self, builder_state: Dict[str, Any]) -> str:
        """Generate Flask app from builder state"""
        return '''from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)
    
    return app
'''
    
    def _generate_routes(self, builder_state: Dict[str, Any]) -> str:
        """Generate routes from builder state"""
        routes = []
        
        for node in builder_state.get('nodes', []):
            if node['type'] == 'ui_page':
                routes.append(f'''
@app.route('/{node["name"]}')
def {node["name"]}_page():
    return render_template('{node["name"]}.html')
''')
            elif node['type'] == 'rest_api':
                routes.append(f'''
@app.route('/api/{node["name"]}', methods=['GET'])
def get_{node["name"]}():
    return jsonify({{"message": "API endpoint for {node["name"]}"}})

@app.route('/api/{node["name"]}', methods=['POST'])
def create_{node["name"]}():
    return jsonify({{"message": "Create {node["name"]}"}})
''')
        
        return f'''from flask import Blueprint, render_template, jsonify, request
from app.models import db

main_bp = Blueprint('main', __name__)

{''.join(routes)}
'''
    
    def _generate_models(self, builder_state: Dict[str, Any]) -> str:
        """Generate models from builder state"""
        models = []
        
        for node in builder_state.get('nodes', []):
            if node['type'] == 'db_table':
                table_name = node['name']
                fields = node.get('config', {}).get('fields', [])
                
                model_fields = []
                for field in fields:
                    if field['type'] == 'uuid':
                        model_fields.append(f"    {field['name']} = db.Column(db.String(36), primary_key=True)")
                    elif field['type'] == 'string':
                        model_fields.append(f"    {field['name']} = db.Column(db.String(255), nullable={not field.get('required', False)})")
                    elif field['type'] == 'text':
                        model_fields.append(f"    {field['name']} = db.Column(db.Text, nullable={not field.get('required', False)})")
                    elif field['type'] == 'datetime':
                        model_fields.append(f"    {field['name']} = db.Column(db.DateTime, default=db.func.now())")
                
                model_content = f'''
class {table_name.title()}(db.Model):
    __tablename__ = '{table_name}'
    
{chr(10).join(model_fields)}
    
    def to_dict(self):
        return {{
            'id': self.id,
            {', '.join([f"'{field['name']}': self.{field['name']}" for field in fields if field['name'] != 'id'])}
        }}
'''
                models.append(model_content)
        
        return f'''from app import db
from datetime import datetime

{''.join(models)}
'''
    
    def _generate_templates(self, builder_state: Dict[str, Any]) -> str:
        """Generate HTML templates from builder state"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
</head>
<body>
    <nav>
        <div class="container">
            <h1>SBH Generated App</h1>
        </div>
    </nav>
    
    <main class="container">
        {% block content %}{% endblock %}
    </main>
    
    <script src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>
'''
    
    def _generate_static_files(self, builder_state: Dict[str, Any]) -> str:
        """Generate static files from builder state"""
        return '''/* Main CSS */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

nav {
    background-color: #333;
    color: white;
    padding: 1rem 0;
}

nav h1 {
    margin: 0;
    font-size: 1.5rem;
}

main {
    margin-top: 2rem;
}
'''
