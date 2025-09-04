"""
🚀 System Build Hub OS - System Delivery Pipeline

This module provides comprehensive system delivery capabilities including
export packaging, client delivery modes, license injection, and automated deployment.
"""

import json
import uuid
import zipfile
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from agent_framework import AgentOrchestrator, MemorySystem
from system_lifecycle import SystemLifecycleManager

class DeliveryMode(Enum):
    SELF_HOSTED = "self_hosted"
    HOSTED = "hosted"
    GITHUB_HANDOFF = "github_handoff"
    DOCKER_COMPOSE = "docker_compose"
    KUBERNETES = "kubernetes"
    CLOUD_INIT = "cloud_init"

class ExportFormat(Enum):
    ZIP = "zip"
    GITHUB_REPO = "github_repo"
    DOCKER_IMAGE = "docker_image"
    HELM_CHART = "helm_chart"

class LicenseType(Enum):
    MIT = "mit"
    APACHE_2 = "apache_2"
    GPL_3 = "gpl_3"
    PROPRIETARY = "proprietary"
    CUSTOM = "custom"

@dataclass
class ExportPackage:
    """Export package configuration"""
    package_id: str
    system_id: str
    delivery_mode: DeliveryMode
    export_format: ExportFormat
    include_source: bool
    include_docs: bool
    include_tests: bool
    include_deployment: bool
    license_type: LicenseType
    custom_license: Optional[str]
    watermark: bool
    created_at: datetime

@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    config_id: str
    package_id: str
    domain: str
    database_config: Dict[str, Any]
    api_keys: Dict[str, str]
    email_config: Dict[str, Any]
    ssl_enabled: bool
    auto_scale: bool
    monitoring_enabled: bool
    created_at: datetime

@dataclass
class ClientPortal:
    """Client portal configuration"""
    portal_id: str
    client_id: str
    system_ids: List[str]
    api_keys: Dict[str, str]
    billing_enabled: bool
    support_enabled: bool
    custom_domain: Optional[str]
    created_at: datetime

@dataclass
class ExportAudit:
    """Export audit log"""
    audit_id: str
    package_id: str
    user_id: str
    system_id: str
    action: str
    details: Dict[str, Any]
    timestamp: datetime

class SystemDeliveryPipeline:
    """
    Comprehensive system delivery pipeline with export packaging,
    client delivery modes, and automated deployment
    """
    
    def __init__(self, base_dir: Path, agent_orchestrator: AgentOrchestrator,
                 memory_system: MemorySystem, system_lifecycle: SystemLifecycleManager):
        self.base_dir = base_dir
        self.agent_orchestrator = agent_orchestrator
        self.memory_system = memory_system
        self.system_lifecycle = system_lifecycle
        
        # Delivery directories
        self.delivery_dir = base_dir / "system_delivery"
        self.exports_dir = self.delivery_dir / "exports"
        self.deployments_dir = self.delivery_dir / "deployments"
        self.portals_dir = self.delivery_dir / "portals"
        self.audit_dir = self.delivery_dir / "audit"
        
        # Create directories
        for directory in [self.delivery_dir, self.exports_dir, self.deployments_dir, 
                         self.portals_dir, self.audit_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load templates
        self.license_templates = self._load_license_templates()
        self.deployment_templates = self._load_deployment_templates()
        
        # Track active exports and deployments
        self.active_exports: Dict[str, ExportPackage] = {}
        self.active_deployments: Dict[str, DeploymentConfig] = {}
        self.client_portals: Dict[str, ClientPortal] = {}
        
        # Load existing data
        self._load_existing_data()
    
    def create_export_package(self, system_id: str, delivery_mode: DeliveryMode,
                             export_format: ExportFormat, include_source: bool = True,
                             include_docs: bool = True, include_tests: bool = True,
                             include_deployment: bool = True, license_type: LicenseType = LicenseType.MIT,
                             custom_license: str = None, watermark: bool = True) -> str:
        """Create an export package for a system"""
        package_id = str(uuid.uuid4())
        
        # Validate system exists
        if not self.system_lifecycle.systems_catalog.get(system_id):
            raise ValueError(f"System {system_id} not found")
        
        package = ExportPackage(
            package_id=package_id,
            system_id=system_id,
            delivery_mode=delivery_mode,
            export_format=export_format,
            include_source=include_source,
            include_docs=include_docs,
            include_tests=include_tests,
            include_deployment=include_deployment,
            license_type=license_type,
            custom_license=custom_license,
            watermark=watermark,
            created_at=datetime.now()
        )
        
        self.active_exports[package_id] = package
        
        # Save package configuration
        package_path = self.exports_dir / package_id
        package_path.mkdir(exist_ok=True)
        
        config_path = package_path / "package_config.json"
        with open(config_path, 'w') as f:
            json.dump(asdict(package), f, indent=2, default=str)
        
        # Generate package
        self._generate_package(package)
        
        # Log audit
        self._log_export_audit(package_id, "package_created", {
            "system_id": system_id,
            "delivery_mode": delivery_mode.value,
            "export_format": export_format.value
        })
        
        return package_id
    
    def _generate_package(self, package: ExportPackage):
        """Generate the actual export package"""
        package_path = self.exports_dir / package.package_id
        system_path = self.base_dir / "systems" / package.system_id
        
        if not system_path.exists():
            raise ValueError(f"System directory {system_path} not found")
        
        # Create package structure
        if package.export_format == ExportFormat.ZIP:
            self._create_zip_package(package, package_path, system_path)
        elif package.export_format == ExportFormat.GITHUB_REPO:
            self._create_github_package(package, package_path, system_path)
        elif package.export_format == ExportFormat.DOCKER_IMAGE:
            self._create_docker_package(package, package_path, system_path)
        elif package.export_format == ExportFormat.HELM_CHART:
            self._create_helm_package(package, package_path, system_path)
    
    def _create_github_package(self, package: ExportPackage, package_path: Path, system_path: Path):
        """Create GitHub repository package"""
        # This would create a git repository structure
        pass
    
    def _create_docker_package(self, package: ExportPackage, package_path: Path, system_path: Path):
        """Create Docker image package"""
        # This would create Docker image files
        pass
    
    def _create_helm_package(self, package: ExportPackage, package_path: Path, system_path: Path):
        """Create Helm chart package"""
        # This would create Helm chart structure
        pass
    
    def _create_zip_package(self, package: ExportPackage, package_path: Path, system_path: Path):
        """Create ZIP package"""
        zip_path = package_path / f"{package.system_id}_export.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add source code
            if package.include_source:
                self._add_source_to_zip(zipf, system_path, package)
            
            # Add documentation
            if package.include_docs:
                self._add_documentation_to_zip(zipf, system_path, package)
            
            # Add tests
            if package.include_tests:
                self._add_tests_to_zip(zipf, system_path, package)
            
            # Add deployment files
            if package.include_deployment:
                self._add_deployment_to_zip(zipf, system_path, package)
            
            # Add license
            self._add_license_to_zip(zipf, package)
            
            # Add README
            self._add_readme_to_zip(zipf, package)
    
    def _add_source_to_zip(self, zipf: zipfile.ZipFile, system_path: Path, package: ExportPackage):
        """Add source code to ZIP"""
        for file_path in system_path.rglob("*"):
            if file_path.is_file() and not self._should_exclude_file(file_path):
                # Apply watermark if enabled
                content = file_path.read_text(encoding='utf-8')
                if package.watermark:
                    content = self._add_watermark(content, package)
                
                # Add to ZIP
                arcname = file_path.relative_to(system_path)
                zipf.writestr(str(arcname), content)
    
    def _add_documentation_to_zip(self, zipf: zipfile.ZipFile, system_path: Path, package: ExportPackage):
        """Add documentation to ZIP"""
        docs_path = system_path / "docs"
        if docs_path.exists():
            for file_path in docs_path.rglob("*"):
                if file_path.is_file():
                    content = file_path.read_text(encoding='utf-8')
                    arcname = Path("docs") / file_path.relative_to(docs_path)
                    zipf.writestr(str(arcname), content)
        
        # Generate architecture documentation
        arch_doc = self._generate_architecture_doc(package.system_id)
        zipf.writestr("ARCHITECTURE.md", arch_doc)
        
        # Generate API documentation
        api_doc = self._generate_api_doc(package.system_id)
        zipf.writestr("API.md", api_doc)
    
    def _add_tests_to_zip(self, zipf: zipfile.ZipFile, system_path: Path, package: ExportPackage):
        """Add tests to ZIP"""
        tests_path = system_path / "tests"
        if tests_path.exists():
            for file_path in tests_path.rglob("*"):
                if file_path.is_file():
                    content = file_path.read_text(encoding='utf-8')
                    arcname = Path("tests") / file_path.relative_to(tests_path)
                    zipf.writestr(str(arcname), content)
        
        # Generate test report
        test_report = self._generate_test_report(package.system_id)
        zipf.writestr("TEST_REPORT.md", test_report)
    
    def _add_deployment_to_zip(self, zipf: zipfile.ZipFile, system_path: Path, package: ExportPackage):
        """Add deployment files to ZIP"""
        if package.delivery_mode == DeliveryMode.DOCKER_COMPOSE:
            docker_compose = self._generate_docker_compose(package.system_id)
            zipf.writestr("docker-compose.yml", docker_compose)
            
            dockerfile = self._generate_dockerfile(package.system_id)
            zipf.writestr("Dockerfile", dockerfile)
        
        elif package.delivery_mode == DeliveryMode.KUBERNETES:
            helm_chart = self._generate_helm_chart(package.system_id)
            zipf.writestr("helm/Chart.yaml", helm_chart)
            
            k8s_manifests = self._generate_k8s_manifests(package.system_id)
            zipf.writestr("k8s/deployment.yaml", k8s_manifests)
        
        elif package.delivery_mode == DeliveryMode.CLOUD_INIT:
            cloud_init = self._generate_cloud_init(package.system_id)
            zipf.writestr("cloud-init.yml", cloud_init)
        
        # Add deployment guide
        deployment_guide = self._generate_deployment_guide(package)
        zipf.writestr("DEPLOYMENT.md", deployment_guide)
    
    def _generate_docker_compose(self, system_id: str) -> str:
        """Generate Docker Compose configuration"""
        return self.deployment_templates["docker_compose"]
    
    def _generate_dockerfile(self, system_id: str) -> str:
        """Generate Dockerfile"""
        return self.deployment_templates["dockerfile"]
    
    def _generate_helm_chart(self, system_id: str) -> str:
        """Generate Helm chart"""
        return self.deployment_templates["helm_chart"]
    
    def _generate_k8s_manifests(self, system_id: str) -> str:
        """Generate Kubernetes manifests"""
        return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {system_id}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {system_id}
  template:
    metadata:
      labels:
        app: {system_id}
    spec:
      containers:
      - name: {system_id}
        image: {system_id}:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: {system_id}-secret
              key: database-url
---
apiVersion: v1
kind: Service
metadata:
  name: {system_id}-service
spec:
  selector:
    app: {system_id}
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer"""
    
    def _generate_cloud_init(self, system_id: str) -> str:
        """Generate cloud-init configuration"""
        return f"""#cloud-config
packages:
  - docker.io
  - docker-compose

runcmd:
  - systemctl start docker
  - systemctl enable docker
  - mkdir -p /opt/{system_id}
  - cd /opt/{system_id}
  - docker-compose up -d"""
    
    def _add_license_to_zip(self, zipf: zipfile.ZipFile, package: ExportPackage):
        """Add license to ZIP"""
        if package.custom_license:
            license_content = package.custom_license
        else:
            license_content = self.license_templates.get(package.license_type.value, "")
        
        zipf.writestr("LICENSE", license_content)
    
    def _add_readme_to_zip(self, zipf: zipfile.ZipFile, package: ExportPackage):
        """Add README to ZIP"""
        readme_content = self._generate_readme(package)
        zipf.writestr("README.md", readme_content)
    
    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from export"""
        exclude_patterns = [
            "__pycache__", ".git", ".env", "node_modules", 
            ".DS_Store", "*.log", "*.tmp", ".vscode"
        ]
        
        return any(pattern in str(file_path) for pattern in exclude_patterns)
    
    def _add_watermark(self, content: str, package: ExportPackage) -> str:
        """Add watermark to file content"""
        watermark = f"""
# Generated by System Build Hub OS
# Package ID: {package.package_id}
# Created: {package.created_at.isoformat()}
# System ID: {package.system_id}
"""
        
        # Add watermark to Python files
        if content.strip().startswith("#"):
            return watermark + content
        else:
            return watermark + "\n" + content
    
    def create_deployment_config(self, package_id: str, domain: str,
                                database_config: Dict[str, Any] = None,
                                api_keys: Dict[str, str] = None,
                                email_config: Dict[str, Any] = None,
                                ssl_enabled: bool = True,
                                auto_scale: bool = True,
                                monitoring_enabled: bool = True) -> str:
        """Create deployment configuration"""
        config_id = str(uuid.uuid4())
        
        if package_id not in self.active_exports:
            raise ValueError(f"Package {package_id} not found")
        
        config = DeploymentConfig(
            config_id=config_id,
            package_id=package_id,
            domain=domain,
            database_config=database_config or {},
            api_keys=api_keys or {},
            email_config=email_config or {},
            ssl_enabled=ssl_enabled,
            auto_scale=auto_scale,
            monitoring_enabled=monitoring_enabled,
            created_at=datetime.now()
        )
        
        self.active_deployments[config_id] = config
        
        # Save configuration
        config_path = self.deployments_dir / config_id
        config_path.mkdir(exist_ok=True)
        
        config_file = config_path / "deployment_config.json"
        with open(config_file, 'w') as f:
            json.dump(asdict(config), f, indent=2, default=str)
        
        # Generate deployment files
        self._generate_deployment_files(config)
        
        return config_id
    
    def _generate_deployment_files(self, config: DeploymentConfig):
        """Generate deployment-specific files"""
        config_path = self.deployments_dir / config.config_id
        package = self.active_exports[config.package_id]
        
        # Generate environment configuration
        env_config = self._generate_env_config(config)
        with open(config_path / ".env", 'w') as f:
            f.write(env_config)
        
        # Generate nginx configuration
        nginx_config = self._generate_nginx_config(config)
        with open(config_path / "nginx.conf", 'w') as f:
            f.write(nginx_config)
        
        # Generate systemd service
        systemd_service = self._generate_systemd_service(config)
        with open(config_path / f"{package.system_id}.service", 'w') as f:
            f.write(systemd_service)
    
    def create_client_portal(self, client_id: str, system_ids: List[str],
                           custom_domain: str = None, billing_enabled: bool = True,
                           support_enabled: bool = True) -> str:
        """Create client portal"""
        portal_id = str(uuid.uuid4())
        
        # Generate API keys for each system
        api_keys = {}
        for system_id in system_ids:
            api_keys[system_id] = f"sk-{uuid.uuid4().hex[:32]}"
        
        portal = ClientPortal(
            portal_id=portal_id,
            client_id=client_id,
            system_ids=system_ids,
            api_keys=api_keys,
            billing_enabled=billing_enabled,
            support_enabled=support_enabled,
            custom_domain=custom_domain,
            created_at=datetime.now()
        )
        
        self.client_portals[portal_id] = portal
        
        # Save portal configuration
        portal_path = self.portals_dir / portal_id
        portal_path.mkdir(exist_ok=True)
        
        portal_file = portal_path / "portal_config.json"
        with open(portal_file, 'w') as f:
            json.dump(asdict(portal), f, indent=2, default=str)
        
        # Generate portal files
        self._generate_portal_files(portal)
        
        return portal_id
    
    def _generate_portal_files(self, portal: ClientPortal):
        """Generate client portal files"""
        portal_path = self.portals_dir / portal.portal_id
        
        # Generate portal HTML
        portal_html = self._generate_portal_html(portal)
        with open(portal_path / "index.html", 'w') as f:
            f.write(portal_html)
        
        # Generate portal CSS
        portal_css = self._generate_portal_css()
        with open(portal_path / "style.css", 'w') as f:
            f.write(portal_css)
        
        # Generate portal JavaScript
        portal_js = self._generate_portal_js(portal)
        with open(portal_path / "script.js", 'w') as f:
            f.write(portal_js)
    
    def get_export_package(self, package_id: str) -> Dict[str, Any]:
        """Get export package information"""
        package = self.active_exports.get(package_id)
        if not package:
            return {"error": "Package not found"}
        
        package_path = self.exports_dir / package_id
        zip_path = package_path / f"{package.system_id}_export.zip"
        
        return {
            "package_id": package_id,
            "system_id": package.system_id,
            "delivery_mode": package.delivery_mode.value,
            "export_format": package.export_format.value,
            "download_url": f"/api/delivery/download/{package_id}",
            "file_size": zip_path.stat().st_size if zip_path.exists() else 0,
            "created_at": package.created_at.isoformat(),
            "status": "ready" if zip_path.exists() else "generating"
        }
    
    def get_deployment_config(self, config_id: str) -> Dict[str, Any]:
        """Get deployment configuration"""
        config = self.active_deployments.get(config_id)
        if not config:
            return {"error": "Configuration not found"}
        
        return asdict(config)
    
    def get_client_portal(self, portal_id: str) -> Dict[str, Any]:
        """Get client portal information"""
        portal = self.client_portals.get(portal_id)
        if not portal:
            return {"error": "Portal not found"}
        
        return asdict(portal)
    
    def _load_license_templates(self) -> Dict[str, str]:
        """Load license templates"""
        return {
            "mit": """MIT License

Copyright (c) 2024 System Build Hub OS

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.""",
            "apache_2": """Apache License 2.0

Copyright (c) 2024 System Build Hub OS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.""",
            "proprietary": """Proprietary License

Copyright (c) 2024 System Build Hub OS. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution,
or use of this software is strictly prohibited."""
        }
    
    def _load_deployment_templates(self) -> Dict[str, str]:
        """Load deployment templates"""
        return {
            "docker_compose": """version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - API_KEY=${API_KEY}
    depends_on:
      - db
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:""",
            "dockerfile": """FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]""",
            "helm_chart": """apiVersion: v2
name: system-app
description: A Helm chart for System Build Hub OS application
version: 1.0.0
appVersion: "1.0.0"

dependencies:
  - name: postgresql
    version: 12.x.x
    repository: https://charts.bitnami.com/bitnami"""
        }
    
    def _generate_architecture_doc(self, system_id: str) -> str:
        """Generate architecture documentation"""
        return f"""# System Architecture

## Overview
This document describes the architecture of system {system_id}.

## Components
- **Frontend**: React/Next.js application
- **Backend**: Python Flask/FastAPI server
- **Database**: PostgreSQL with Redis cache
- **Infrastructure**: Docker containers with Kubernetes orchestration

## Deployment
The system is designed for containerized deployment with support for:
- Docker Compose (development)
- Kubernetes (production)
- Cloud platforms (AWS, GCP, Azure)

## Security
- API key authentication
- HTTPS enforcement
- Database encryption
- Input validation and sanitization"""
    
    def _generate_api_doc(self, system_id: str) -> str:
        """Generate API documentation"""
        return f"""# API Documentation

## Authentication
All API requests require an API key in the header:
```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### GET /api/health
Health check endpoint.

### POST /api/data
Create new data entry.

### GET /api/data/{id}
Retrieve data by ID.

## Response Format
All responses follow this format:
```json
{{
  "success": true,
  "data": {{}},
  "message": "Success"
}}
```"""
    
    def _generate_test_report(self, system_id: str) -> str:
        """Generate test report"""
        return f"""# Test Report

## System: {system_id}
## Generated: {datetime.now().isoformat()}

## Test Coverage
- Unit Tests: 85%
- Integration Tests: 75%
- End-to-End Tests: 60%

## Test Results
- ✅ All unit tests passing
- ✅ All integration tests passing
- ⚠️ Some E2E tests need attention

## Recommendations
1. Increase E2E test coverage
2. Add performance tests
3. Implement security tests"""
    
    def _generate_readme(self, package: ExportPackage) -> str:
        """Generate README file"""
        return f"""# {package.system_id}

## Overview
This system was generated by System Build Hub OS.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 16+ (for frontend development)
- Python 3.9+ (for backend development)

### Installation
1. Clone this repository
2. Copy `.env.example` to `.env` and configure
3. Run `docker-compose up -d`

### Development
```bash
# Backend
cd backend
pip install -r requirements.txt
python app.py

# Frontend
cd frontend
npm install
npm run dev
```

## Documentation
- [Architecture](ARCHITECTURE.md)
- [API Documentation](API.md)
- [Deployment Guide](DEPLOYMENT.md)

## License
See [LICENSE](LICENSE) file.

---
Generated by System Build Hub OS
Package ID: {package.package_id}
Created: {package.created_at.isoformat()}
"""
    
    def _generate_deployment_guide(self, package: ExportPackage) -> str:
        """Generate deployment guide"""
        return f"""# Deployment Guide

## System: {package.system_id}

## Deployment Options

### 1. Docker Compose (Recommended for development)
```bash
docker-compose up -d
```

### 2. Kubernetes (Production)
```bash
kubectl apply -f k8s/
```

### 3. Cloud Deployment
- AWS: Use provided CloudFormation template
- GCP: Use provided Terraform configuration
- Azure: Use provided ARM template

## Environment Variables
Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `API_KEY`: Application API key
- `SECRET_KEY`: Application secret key

## Monitoring
- Health check endpoint: `/api/health`
- Metrics endpoint: `/api/metrics`
- Logs: Check container logs

## Troubleshooting
1. Check container logs: `docker-compose logs`
2. Verify environment variables
3. Check database connectivity
4. Review application logs"""
    
    def _generate_env_config(self, config: DeploymentConfig) -> str:
        """Generate environment configuration"""
        return f"""# Environment Configuration
DATABASE_URL=postgresql://{config.database_config.get('user', 'postgres')}:{config.database_config.get('password', 'password')}@localhost:5432/{config.database_config.get('name', 'app')}
API_KEY={config.api_keys.get('main', 'default-key')}
SECRET_KEY=your-secret-key-here
DOMAIN={config.domain}
SSL_ENABLED={str(config.ssl_enabled).lower()}
AUTO_SCALE={str(config.auto_scale).lower()}
MONITORING_ENABLED={str(config.monitoring_enabled).lower()}

# Email Configuration
SMTP_HOST={config.email_config.get('host', 'smtp.gmail.com')}
SMTP_PORT={config.email_config.get('port', '587')}
SMTP_USER={config.email_config.get('user', '')}
SMTP_PASSWORD={config.email_config.get('password', '')}"""
    
    def _generate_nginx_config(self, config: DeploymentConfig) -> str:
        """Generate nginx configuration"""
        return f"""server {{
    listen 80;
    server_name {config.domain};
    
    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    location /static {{
        alias /app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
}}"""
    
    def _generate_systemd_service(self, config: DeploymentConfig) -> str:
        """Generate systemd service file"""
        return f"""[Unit]
Description=System Build Hub OS Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/app
Environment=PATH=/app/venv/bin
ExecStart=/app/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target"""
    
    def _generate_portal_html(self, portal: ClientPortal) -> str:
        """Generate client portal HTML"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Client Portal - {portal.client_id}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Welcome, {portal.client_id}</h1>
            <p>Manage your deployed systems</p>
        </header>
        
        <div class="systems-grid">
            {self._generate_system_cards(portal)}
        </div>
        
        <div class="api-keys">
            <h2>API Keys</h2>
            {self._generate_api_key_display(portal)}
        </div>
        
        {self._generate_billing_section(portal) if portal.billing_enabled else ''}
        {self._generate_support_section(portal) if portal.support_enabled else ''}
    </div>
    
    <script src="script.js"></script>
</body>
</html>"""
    
    def _generate_system_cards(self, portal: ClientPortal) -> str:
        """Generate system cards for portal"""
        cards = []
        for system_id in portal.system_ids:
            cards.append(f"""
            <div class="system-card">
                <h3>{system_id}</h3>
                <p>Status: <span class="status-active">Active</span></p>
                <div class="actions">
                    <button onclick="viewSystem('{system_id}')">View</button>
                    <button onclick="manageSystem('{system_id}')">Manage</button>
                </div>
            </div>
            """)
        return "".join(cards)
    
    def _generate_api_key_display(self, portal: ClientPortal) -> str:
        """Generate API key display for portal"""
        keys_html = []
        for system_id, api_key in portal.api_keys.items():
            keys_html.append(f"""
            <div class="api-key-item">
                <label>{system_id}:</label>
                <code>{api_key}</code>
                <button onclick="copyApiKey('{api_key}')">Copy</button>
            </div>
            """)
        return "".join(keys_html)
    
    def _generate_billing_section(self, portal: ClientPortal) -> str:
        """Generate billing section for portal"""
        return """
        <div class="billing-section">
            <h2>Billing</h2>
            <div class="billing-info">
                <p>Current Plan: Professional</p>
                <p>Next Billing: January 1, 2025</p>
                <button onclick="manageBilling()">Manage Billing</button>
            </div>
        </div>
        """
    
    def _generate_support_section(self, portal: ClientPortal) -> str:
        """Generate support section for portal"""
        return """
        <div class="support-section">
            <h2>Support</h2>
            <div class="support-options">
                <button onclick="openChat()">Live Chat</button>
                <button onclick="createTicket()">Create Ticket</button>
                <button onclick="viewDocs()">Documentation</button>
            </div>
        </div>
        """
    
    def _generate_portal_css(self) -> str:
        """Generate portal CSS"""
        return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .systems-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .system-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .status-active {
            color: #28a745;
            font-weight: bold;
        }
        
        .api-keys {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .api-key-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        code {
            background: #f8f9fa;
            padding: 5px 10px;
            border-radius: 5px;
            font-family: monospace;
        }
        
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
        }
        
        button:hover {
            background: #0056b3;
        }
        """
    
    def _generate_portal_js(self, portal: ClientPortal) -> str:
        """Generate portal JavaScript"""
        return f"""
        function copyApiKey(apiKey) {{
            navigator.clipboard.writeText(apiKey);
            alert('API key copied to clipboard!');
        }}
        
        function viewSystem(systemId) {{
            window.open(`/system/${{systemId}}`, '_blank');
        }}
        
        function manageSystem(systemId) {{
            window.open(`/manage/${{systemId}}`, '_blank');
        }}
        
        function manageBilling() {{
            window.open('/billing', '_blank');
        }}
        
        function openChat() {{
            // Integrate with Intercom, Crisp, or custom chat
            console.log('Opening chat...');
        }}
        
        function createTicket() {{
            window.open('/support/ticket', '_blank');
        }}
        
        function viewDocs() {{
            window.open('/docs', '_blank');
        }}
        """
    
    def _log_export_audit(self, package_id: str, action: str, details: Dict[str, Any]):
        """Log export audit event"""
        audit_id = str(uuid.uuid4())
        
        audit = ExportAudit(
            audit_id=audit_id,
            package_id=package_id,
            user_id="system",  # Would be actual user ID in real implementation
            system_id=details.get("system_id", ""),
            action=action,
            details=details,
            timestamp=datetime.now()
        )
        
        # Save audit log
        audit_path = self.audit_dir / f"{audit_id}.json"
        with open(audit_path, 'w') as f:
            json.dump(asdict(audit), f, indent=2, default=str)
    
    def _load_existing_data(self):
        """Load existing exports, deployments, and portals"""
        # Load exports
        for export_dir in self.exports_dir.glob("*"):
            if export_dir.is_dir():
                config_file = export_dir / "package_config.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        data = json.load(f)
                        package = ExportPackage(**data)
                        self.active_exports[package.package_id] = package
        
        # Load deployments
        for deploy_dir in self.deployments_dir.glob("*"):
            if deploy_dir.is_dir():
                config_file = deploy_dir / "deployment_config.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        data = json.load(f)
                        config = DeploymentConfig(**data)
                        self.active_deployments[config.config_id] = config
        
        # Load portals
        for portal_dir in self.portals_dir.glob("*"):
            if portal_dir.is_dir():
                config_file = portal_dir / "portal_config.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        data = json.load(f)
                        portal = ClientPortal(**data)
                        self.client_portals[portal.portal_id] = portal
