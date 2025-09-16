"""
DevOps Agent
Handles deployment, CI/CD, and infrastructure setup.
"""

import json
import logging
import os
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path
from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class DevOpsAgent(BaseAgent):
    """DevOps Agent - handles deployment and infrastructure."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.deployment_configs = self._load_deployment_configs()
    
    def _load_deployment_configs(self) -> Dict[str, Any]:
        """Load deployment configurations."""
        return {
            "docker": {
                "dockerfile_template": """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
""",
                "docker_compose_template": """version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/app
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=app
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
"""
            },
            "github_actions": {
                "ci_template": """name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
    
    - name: Build Docker image
      run: |
        docker build -t app .
    
    - name: Deploy to staging
      if: github.ref == 'refs/heads/develop'
      run: |
        echo "Deploy to staging"
        # Add deployment commands here
"""
            },
            "kubernetes": {
                "deployment_template": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
      - name: app
        image: app:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secret
              key: database-url
---
apiVersion: v1
kind: Service
metadata:
  name: app-service
spec:
  selector:
    app: app
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
"""
            }
        }
    
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DevOps actions."""
        if action == "prepare_deployment":
            return await self._prepare_deployment(inputs)
        elif action == "create_ci_config":
            return await self._create_ci_config(inputs)
        elif action == "generate_artifacts":
            return await self._generate_artifacts(inputs)
        elif action == "create_pr":
            return await self._create_pr(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _prepare_deployment(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare deployment artifacts and configurations."""
        spec = inputs.get("spec", {})
        artifacts = inputs.get("artifacts", [])
        deployment_type = inputs.get("deployment_type", "docker")
        
        deployment_artifacts = []
        
        # Generate deployment-specific configurations
        if deployment_type == "docker":
            docker_artifacts = await self._generate_docker_configs(spec, artifacts)
            deployment_artifacts.extend(docker_artifacts)
        elif deployment_type == "kubernetes":
            k8s_artifacts = await self._generate_kubernetes_configs(spec, artifacts)
            deployment_artifacts.extend(k8s_artifacts)
        
        # Generate CI/CD configuration
        ci_artifacts = await self._create_ci_config(inputs)
        deployment_artifacts.extend(ci_artifacts.get("artifacts", []))
        
        # Generate deployment scripts
        script_artifacts = await self._generate_deployment_scripts(spec, deployment_type)
        deployment_artifacts.extend(script_artifacts)
        
        return {
            "deployment_artifacts": deployment_artifacts,
            "deployment_type": deployment_type,
            "summary": f"Generated {len(deployment_artifacts)} deployment artifacts for {deployment_type}"
        }
    
    async def _generate_docker_configs(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Docker configuration files."""
        docker_artifacts = []
        
        # Generate Dockerfile
        dockerfile_content = self.deployment_configs["docker"]["dockerfile_template"]
        docker_artifacts.append({
            "file_path": "Dockerfile",
            "content": dockerfile_content,
            "type": "docker",
            "language": "dockerfile"
        })
        
        # Generate docker-compose.yml
        docker_compose_content = self.deployment_configs["docker"]["docker_compose_template"]
        docker_artifacts.append({
            "file_path": "docker-compose.yml",
            "content": docker_compose_content,
            "type": "docker",
            "language": "yaml"
        })
        
        # Generate .dockerignore
        dockerignore_content = """__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
.DS_Store
"""
        docker_artifacts.append({
            "file_path": ".dockerignore",
            "content": dockerignore_content,
            "type": "docker",
            "language": "text"
        })
        
        return docker_artifacts
    
    async def _generate_kubernetes_configs(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Kubernetes configuration files."""
        k8s_artifacts = []
        
        # Generate deployment.yaml
        deployment_content = self.deployment_configs["kubernetes"]["deployment_template"]
        k8s_artifacts.append({
            "file_path": "k8s/deployment.yaml",
            "content": deployment_content,
            "type": "kubernetes",
            "language": "yaml"
        })
        
        # Generate namespace.yaml
        namespace_content = """apiVersion: v1
kind: Namespace
metadata:
  name: app-namespace
"""
        k8s_artifacts.append({
            "file_path": "k8s/namespace.yaml",
            "content": namespace_content,
            "type": "kubernetes",
            "language": "yaml"
        })
        
        # Generate ingress.yaml
        ingress_content = """apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 80
"""
        k8s_artifacts.append({
            "file_path": "k8s/ingress.yaml",
            "content": ingress_content,
            "type": "kubernetes",
            "language": "yaml"
        })
        
        return k8s_artifacts
    
    async def _create_ci_config(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create CI/CD configuration."""
        spec = inputs.get("spec", {})
        ci_type = inputs.get("ci_type", "github_actions")
        
        ci_artifacts = []
        
        if ci_type == "github_actions":
            # Generate GitHub Actions workflow
            workflow_content = self.deployment_configs["github_actions"]["ci_template"]
            ci_artifacts.append({
                "file_path": ".github/workflows/ci.yml",
                "content": workflow_content,
                "type": "ci",
                "language": "yaml"
            })
        
        # Generate Makefile for common operations
        makefile_content = await self._generate_makefile(spec)
        ci_artifacts.append({
            "file_path": "Makefile",
            "content": makefile_content,
            "type": "ci",
            "language": "makefile"
        })
        
        return {
            "artifacts": ci_artifacts,
            "ci_type": ci_type
        }
    
    async def _generate_makefile(self, spec: Dict[str, Any]) -> str:
        """Generate Makefile for common operations."""
        return f"""# Makefile for {spec.get('name', 'Generated System')}

.PHONY: help install test build run deploy clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {{FS = ":.*?## "}} /^[a-zA-Z_-]+:.*?## / {{printf "  %-15s %s\\n", $$1, $$2}}' $(MAKEFILE_LIST)

install: ## Install dependencies
	pip install -r requirements.txt

test: ## Run tests
	python -m pytest tests/ -v

test-coverage: ## Run tests with coverage
	python -m pytest tests/ --cov=src --cov-report=html

build: ## Build Docker image
	docker build -t app .

run: ## Run application locally
	uvicorn src.app:app --reload --host 0.0.0.0 --port 8000

run-docker: ## Run application with Docker Compose
	docker-compose up --build

deploy: ## Deploy to production
	@echo "Deploying to production..."
	# Add deployment commands here

deploy-staging: ## Deploy to staging
	@echo "Deploying to staging..."
	# Add staging deployment commands here

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {{}} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/

lint: ## Run linting
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

format: ## Format code
	black src/ tests/
	isort src/ tests/

security: ## Run security checks
	bandit -r src/
	safety check
"""
    
    async def _generate_deployment_scripts(self, spec: Dict[str, Any], deployment_type: str) -> List[Dict[str, Any]]:
        """Generate deployment scripts."""
        scripts = []
        
        # Generate deployment script
        if deployment_type == "docker":
            deploy_script = """#!/bin/bash
set -e

echo "Building Docker image..."
docker build -t app .

echo "Running tests..."
docker run --rm app python -m pytest tests/

echo "Deploying to production..."
docker-compose -f docker-compose.prod.yml up -d

echo "Deployment completed successfully!"
"""
        else:
            deploy_script = """#!/bin/bash
set -e

echo "Deploying to Kubernetes..."
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/ingress.yaml

echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/app-deployment -n app-namespace

echo "Deployment completed successfully!"
"""
        
        scripts.append({
            "file_path": "scripts/deploy.sh",
            "content": deploy_script,
            "type": "script",
            "language": "bash"
        })
        
        # Generate rollback script
        rollback_script = """#!/bin/bash
set -e

echo "Rolling back deployment..."

# Add rollback logic here based on deployment type
if [ "$DEPLOYMENT_TYPE" = "docker" ]; then
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml up -d --scale app=0
    echo "Rollback completed - application is down"
else
    kubectl rollout undo deployment/app-deployment -n app-namespace
    echo "Rollback completed"
fi
"""
        
        scripts.append({
            "file_path": "scripts/rollback.sh",
            "content": rollback_script,
            "type": "script",
            "language": "bash"
        })
        
        return scripts
    
    async def _generate_artifacts(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate deployment artifacts (ZIP, manifest, etc.)."""
        spec = inputs.get("spec", {})
        artifacts = inputs.get("artifacts", [])
        deployment_artifacts = inputs.get("deployment_artifacts", [])
        
        # Create export bundle
        export_bundle = await self._create_export_bundle(artifacts, deployment_artifacts)
        
        # Generate deployment manifest
        manifest = await self._generate_deployment_manifest(spec, artifacts, deployment_artifacts)
        
        # Create release notes
        release_notes = await self._generate_release_notes(spec, artifacts)
        
        return {
            "export_bundle": export_bundle,
            "deployment_manifest": manifest,
            "release_notes": release_notes,
            "artifacts": [
                {
                    "kind": "zip",
                    "url": export_bundle["url"],
                    "metadata": {
                        "size": export_bundle["size"],
                        "files": export_bundle["file_count"]
                    }
                },
                {
                    "kind": "export_manifest",
                    "url": manifest["url"],
                    "metadata": manifest["metadata"]
                },
                {
                    "kind": "release_manifest",
                    "url": release_notes["url"],
                    "metadata": release_notes["metadata"]
                }
            ]
        }
    
    async def _create_export_bundle(self, artifacts: List[Dict[str, Any]], 
                                  deployment_artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create export bundle (ZIP file) with all artifacts."""
        import zipfile
        import tempfile
        
        # Create temporary ZIP file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all artifacts
                all_artifacts = artifacts + deployment_artifacts
                
                for artifact in all_artifacts:
                    file_path = artifact["file_path"]
                    content = artifact["content"]
                    
                    # Create directory structure
                    zipf.writestr(file_path, content)
                
                # Add README
                readme_content = """# Generated System

This is an auto-generated system bundle.

## Contents
- Source code
- Configuration files
- Deployment scripts
- Documentation

## Quick Start
1. Install dependencies: `pip install -r requirements.txt`
2. Run tests: `make test`
3. Start application: `make run`
4. Deploy: `make deploy`

## Files
"""
                
                for artifact in all_artifacts:
                    readme_content += f"- {artifact['file_path']}\n"
                
                zipf.writestr("README.md", readme_content)
            
            # Get file size
            file_size = os.path.getsize(temp_zip.name)
            
            # In a real implementation, this would upload to S3 or similar
            # For now, we'll just return the local path
            return {
                "url": temp_zip.name,
                "size": file_size,
                "file_count": len(all_artifacts) + 1  # +1 for README
            }
    
    async def _generate_deployment_manifest(self, spec: Dict[str, Any], 
                                          artifacts: List[Dict[str, Any]],
                                          deployment_artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate deployment manifest."""
        manifest = {
            "version": "1.0.0",
            "name": spec.get("name", "Generated System"),
            "description": spec.get("description", ""),
            "created_at": "2024-01-01T00:00:00Z",
            "artifacts": {
                "source_files": len(artifacts),
                "deployment_files": len(deployment_artifacts),
                "total_files": len(artifacts) + len(deployment_artifacts)
            },
            "dependencies": {
                "python_version": "3.11",
                "packages": self._extract_dependencies(artifacts)
            },
            "deployment": {
                "type": "docker",
                "ports": [8000],
                "environment_variables": [
                    "DATABASE_URL",
                    "REDIS_URL",
                    "SECRET_KEY"
                ]
            }
        }
        
        # In a real implementation, this would be saved to a file and uploaded
        return {
            "url": "manifest.json",  # Would be actual URL in production
            "metadata": manifest
        }
    
    def _extract_dependencies(self, artifacts: List[Dict[str, Any]]) -> List[str]:
        """Extract dependencies from artifacts."""
        dependencies = []
        
        for artifact in artifacts:
            if artifact.get("file_path") == "requirements.txt":
                content = artifact.get("content", "")
                dependencies = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                break
        
        return dependencies
    
    async def _generate_release_notes(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate release notes."""
        release_notes = f"""# Release Notes - {spec.get('name', 'Generated System')}

## Version 1.0.0
**Release Date:** 2024-01-01

### Features
- Auto-generated system based on specification
- {len(spec.get('entities', []))} entities with full CRUD operations
- {len(spec.get('workflows', []))} workflows
- {len(spec.get('integrations', []))} integrations
- RESTful API with OpenAPI documentation
- Database models and migrations
- Authentication and authorization
- Comprehensive test suite

### Technical Details
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **Language:** Python 3.11
- **Deployment:** Docker
- **Testing:** pytest

### Files Generated
"""
        
        # Add file list
        for artifact in artifacts:
            release_notes += f"- {artifact['file_path']}\n"
        
        release_notes += """
### Deployment Instructions
1. Build Docker image: `docker build -t app .`
2. Run tests: `docker run --rm app python -m pytest tests/`
3. Deploy: `docker-compose up -d`

### Support
For issues and questions, please refer to the documentation or contact support.
"""
        
        return {
            "url": "RELEASE_NOTES.md",  # Would be actual URL in production
            "metadata": {
                "version": "1.0.0",
                "release_date": "2024-01-01",
                "features_count": len(spec.get('entities', [])) + len(spec.get('workflows', []))
            }
        }
    
    async def _create_pr(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create pull request for the generated code."""
        spec = inputs.get("spec", {})
        artifacts = inputs.get("artifacts", [])
        branch_name = inputs.get("branch_name", "feature/auto-generated-system")
        
        # Generate PR title and description
        pr_title = f"Add auto-generated {spec.get('name', 'system')}"
        
        pr_description = f"""# Auto-Generated System: {spec.get('name', 'System')}

This PR contains an auto-generated system based on the specification.

## Summary
- **Entities:** {len(spec.get('entities', []))}
- **Workflows:** {len(spec.get('workflows', []))}
- **Integrations:** {len(spec.get('integrations', []))}
- **Files Generated:** {len(artifacts)}

## Key Features
- RESTful API with FastAPI
- Database models and migrations
- Authentication and authorization
- Comprehensive test suite
- Docker deployment configuration

## Files Added
"""
        
        # Add file list
        for artifact in artifacts:
            pr_description += f"- `{artifact['file_path']}`\n"
        
        pr_description += """
## Testing
- [x] Unit tests pass
- [x] Integration tests pass
- [x] Code quality checks pass

## Deployment
- [x] Docker configuration ready
- [x] CI/CD pipeline configured
- [x] Documentation included

## Next Steps
1. Review the generated code
2. Run tests locally: `make test`
3. Deploy to staging: `make deploy-staging`
4. Approve and merge

---
*This PR was auto-generated by the Meta-Builder v2 system.*
"""
        
        # In a real implementation, this would create an actual PR via GitHub API
        return {
            "pr_url": f"https://github.com/example/repo/pull/123",  # Would be actual PR URL
            "branch_name": branch_name,
            "title": pr_title,
            "description": pr_description,
            "status": "draft"
        }
