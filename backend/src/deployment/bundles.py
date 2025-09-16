"""
Deployment Bundles

Defines the structure for packaging multi-module ecosystems into deployable bundles.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Configuration for a service in a deployment bundle"""
    name: str
    image: Optional[str] = None
    ports: Optional[List[int]] = None
    volumes: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    command: Optional[str] = None
    depends_on: Optional[List[str]] = None
    healthcheck: Optional[Dict[str, Any]] = None

@dataclass
class DeploymentBundle:
    """Deployment bundle for packaging ecosystems into deployable stacks"""
    name: str
    version: str
    ecosystem: str
    environment: str
    services: Dict[str, ServiceConfig]
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bundle to dictionary"""
        return asdict(self)
    
    def validate(self) -> List[str]:
        """Validate bundle configuration"""
        errors = []
        
        if not self.name:
            errors.append("Bundle name is required")
        
        if not self.version:
            errors.append("Bundle version is required")
        
        if not self.ecosystem:
            errors.append("Ecosystem name is required")
        
        if not self.environment:
            errors.append("Environment is required")
        
        if not self.services:
            errors.append("At least one service is required")
        
        # Validate services
        for service_name, service in self.services.items():
            if not isinstance(service, ServiceConfig):
                errors.append(f"Service {service_name} must be a ServiceConfig")
            else:
                if not service.name:
                    errors.append(f"Service {service_name} must have a name")
        
        return errors
    
    def get_service(self, name: str) -> Optional[ServiceConfig]:
        """Get a service by name"""
        return self.services.get(name)
    
    def list_services(self) -> List[str]:
        """List all service names"""
        return list(self.services.keys())

def load_deployment_bundles() -> Dict[str, DeploymentBundle]:
    """Load deployment bundles from deployments directory"""
    bundles = {}
    
    try:
        # Look for deployments directory
        deployments_dir = Path("deployments")
        if not deployments_dir.exists():
            logger.info("Deployments directory not found, creating with default bundles")
            deployments_dir.mkdir(exist_ok=True)
            _create_default_bundles(deployments_dir)
        
        # Load all .json files
        for bundle_file in deployments_dir.glob("*.json"):
            try:
                with open(bundle_file, 'r') as f:
                    data = json.load(f)
                
                # Parse services
                services = {}
                for service_name, service_data in data.get('services', {}).items():
                    if isinstance(service_data, dict):
                        services[service_name] = ServiceConfig(
                            name=service_data.get('name', service_name),
                            image=service_data.get('image'),
                            ports=service_data.get('ports'),
                            volumes=service_data.get('volumes'),
                            environment=service_data.get('environment'),
                            command=service_data.get('command'),
                            depends_on=service_data.get('depends_on'),
                            healthcheck=service_data.get('healthcheck')
                        )
                
                # Create bundle object
                bundle = DeploymentBundle(
                    name=data.get('name', ''),
                    version=data.get('version', '1.0.0'),
                    ecosystem=data.get('ecosystem', ''),
                    environment=data.get('environment', ''),
                    services=services,
                    description=data.get('description', ''),
                    tags=data.get('tags', [])
                )
                
                # Validate bundle
                errors = bundle.validate()
                if errors:
                    logger.warning(f"Bundle {bundle.name} has validation errors: {errors}")
                    continue
                
                bundles[bundle.name] = bundle
                logger.info(f"Loaded deployment bundle: {bundle.name}")
                
            except Exception as e:
                logger.error(f"Failed to load bundle {bundle_file}: {e}")
                continue
        
        if not bundles:
            logger.warning("No valid bundles found, creating defaults")
            _create_default_bundles(deployments_dir)
            bundles = load_deployment_bundles()  # Recursive call to load defaults
        
        return bundles
        
    except Exception as e:
        logger.error(f"Failed to load deployment bundles: {e}")
        return {}

def _create_default_bundles(deployments_dir: Path):
    """Create default deployment bundles"""
    
    # Local development bundle
    local_bundle = {
        "name": "revops_suite_local",
        "version": "1.0.0",
        "ecosystem": "revops_suite",
        "environment": "local",
        "description": "Local development environment for RevOps Suite",
        "tags": ["local", "dev", "revops"],
        "services": {
            "backend": {
                "name": "sbh-backend",
                "image": "sbh-backend:local",
                "ports": [5001],
                "volumes": ["./src:/app/src", "./data:/app/data"],
                "environment": {
                    "FLASK_ENV": "development",
                    "DEBUG": "true",
                    "DATABASE": "./data/local.db"
                },
                "command": "python -m src.cli run"
            },
            "db": {
                "name": "sqlite-local",
                "image": "alpine:latest",
                "volumes": ["./data:/data"],
                "command": "tail -f /dev/null"
            },
            "worker": {
                "name": "sbh-worker",
                "image": "sbh-backend:local",
                "volumes": ["./src:/app/src", "./data:/app/data"],
                "command": "python -m src.cli worker"
            }
        }
    }
    
    # Staging bundle
    staging_bundle = {
        "name": "revops_suite_staging",
        "version": "1.0.0",
        "ecosystem": "revops_suite",
        "environment": "staging",
        "description": "Staging environment for RevOps Suite",
        "tags": ["staging", "test", "revops"],
        "services": {
            "backend": {
                "name": "sbh-backend",
                "image": "sbh-backend:staging",
                "ports": [5001],
                "environment": {
                    "FLASK_ENV": "staging",
                    "DEBUG": "false",
                    "DATABASE": "/data/staging.db"
                },
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://localhost:5001/healthz"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                }
            },
            "db": {
                "name": "sqlite-staging",
                "image": "alpine:latest",
                "volumes": ["/data:/data"],
                "command": "tail -f /dev/null"
            },
            "worker": {
                "name": "sbh-worker",
                "image": "sbh-backend:staging",
                "environment": {
                    "FLASK_ENV": "staging",
                    "DATABASE": "/data/staging.db"
                },
                "command": "python -m src.cli worker"
            }
        }
    }
    
    # Production bundle
    production_bundle = {
        "name": "revops_suite_prod",
        "version": "1.0.0",
        "ecosystem": "revops_suite",
        "environment": "production",
        "description": "Production environment for RevOps Suite",
        "tags": ["production", "prod", "revops"],
        "services": {
            "backend": {
                "name": "sbh-backend",
                "image": "sbh-backend:latest",
                "ports": [5001],
                "environment": {
                    "FLASK_ENV": "production",
                    "DEBUG": "false",
                    "DATABASE": "/data/production.db"
                },
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://localhost:5001/healthz"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                },
                "depends_on": ["db"]
            },
            "db": {
                "name": "sqlite-prod",
                "image": "alpine:latest",
                "volumes": ["/data:/data"],
                "command": "tail -f /dev/null"
            },
            "worker": {
                "name": "sbh-worker",
                "image": "sbh-backend:latest",
                "environment": {
                    "FLASK_ENV": "production",
                    "DATABASE": "/data/production.db"
                },
                "command": "python -m src.cli worker",
                "depends_on": ["db"]
            },
            "nginx": {
                "name": "nginx-proxy",
                "image": "nginx:alpine",
                "ports": [80, 443],
                "volumes": ["./nginx.conf:/etc/nginx/nginx.conf"],
                "depends_on": ["backend"]
            }
        }
    }
    
    # Write bundles to files
    bundles = [local_bundle, staging_bundle, production_bundle]
    
    for bundle_data in bundles:
        bundle_file = deployments_dir / f"{bundle_data['name']}.json"
        try:
            with open(bundle_file, 'w') as f:
                json.dump(bundle_data, f, indent=2)
            logger.info(f"Created default bundle: {bundle_file}")
        except Exception as e:
            logger.error(f"Failed to create default bundle {bundle_data['name']}: {e}")

def get_bundle(name: str) -> Optional[DeploymentBundle]:
    """Get a specific deployment bundle by name"""
    bundles = load_deployment_bundles()
    return bundles.get(name)

def list_bundles() -> List[Dict[str, Any]]:
    """List all available deployment bundles"""
    bundles = load_deployment_bundles()
    return [
        {
            "name": bundle.name,
            "version": bundle.version,
            "ecosystem": bundle.ecosystem,
            "environment": bundle.environment,
            "description": bundle.description,
            "services_count": len(bundle.services),
            "tags": bundle.tags or []
        }
        for bundle in bundles.values()
    ]

def validate_bundle_file(file_path: str) -> Dict[str, Any]:
    """Validate a bundle file without loading it"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check required fields
        required_fields = ['name', 'ecosystem', 'environment', 'services']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return {
                "valid": False,
                "errors": [f"Missing required field: {field}" for field in missing_fields]
            }
        
        # Check field types
        type_errors = []
        if not isinstance(data.get('services', {}), dict):
            type_errors.append("Services must be a dictionary")
        if not isinstance(data.get('tags', []), list):
            type_errors.append("Tags must be a list")
        
        if type_errors:
            return {
                "valid": False,
                "errors": type_errors
            }
        
        # Check services structure
        service_errors = []
        for service_name, service_data in data.get('services', {}).items():
            if not isinstance(service_data, dict):
                service_errors.append(f"Service {service_name} must be a dictionary")
            elif 'name' not in service_data:
                service_errors.append(f"Service {service_name} missing name field")
        
        if service_errors:
            return {
                "valid": False,
                "errors": service_errors
            }
        
        return {
            "valid": True,
            "name": data.get('name'),
            "ecosystem": data.get('ecosystem'),
            "environment": data.get('environment'),
            "services_count": len(data.get('services', {}))
        }
        
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "errors": [f"Invalid JSON: {str(e)}"]
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Validation failed: {str(e)}"]
        }
