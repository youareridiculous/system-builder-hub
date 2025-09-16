"""
Deployment Generators

Generates deployment artifacts like Docker Compose and Kubernetes manifests.
"""

import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .bundles import DeploymentBundle
from .environments import EnvironmentProfile, get_environment_profile

logger = logging.getLogger(__name__)

class DockerComposeGenerator:
    """Generates Docker Compose files from deployment bundles"""
    
    def __init__(self, bundle: DeploymentBundle):
        self.bundle = bundle
        self.environment = get_environment_profile(bundle.environment)
    
    def generate(self, output_path: str = None, dry_run: bool = False) -> str:
        """Generate Docker Compose YAML"""
        compose = {
            "version": "3.8",
            "name": self.bundle.name,
            "services": {},
            "volumes": {},
            "networks": {
                "sbh-network": {
                    "driver": "bridge"
                }
            }
        }
        
        # Generate services
        for service_name, service_config in self.bundle.services.items():
            compose["services"][service_name] = self._generate_service(service_config)
        
        # Generate volumes
        compose["volumes"] = self._generate_volumes()
        
        # Convert to YAML
        yaml_content = yaml.dump(compose, default_flow_style=False, sort_keys=False)
        
        if not dry_run and output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(yaml_content)
                logger.info(f"Generated Docker Compose file: {output_path}")
            except Exception as e:
                logger.error(f"Failed to write Docker Compose file: {e}")
        
        return yaml_content
    
    def _generate_service(self, service_config) -> Dict[str, Any]:
        """Generate service configuration for Docker Compose"""
        service = {
            "container_name": service_config.name,
            "image": service_config.image or "alpine:latest",
            "restart": "unless-stopped"
        }
        
        if service_config.ports:
            service["ports"] = [f"{port}:{port}" for port in service_config.ports]
        
        if service_config.volumes:
            service["volumes"] = service_config.volumes
        
        if service_config.environment:
            service["environment"] = service_config.environment
        
        if service_config.command:
            service["command"] = service_config.command
        
        if service_config.depends_on:
            service["depends_on"] = service_config.depends_on
        
        if service_config.healthcheck:
            service["healthcheck"] = service_config.healthcheck
        
        # Add environment-specific overrides
        if self.bundle.environment == "production":
            service["restart"] = "always"
            service["deploy"] = {
                "resources": {
                    "limits": {
                        "memory": "512M",
                        "cpus": "0.5"
                    }
                }
            }
        
        # Add network
        service["networks"] = ["sbh-network"]
        
        return service
    
    def _generate_volumes(self) -> Dict[str, Any]:
        """Generate volume definitions"""
        volumes = {}
        
        # Add data volume for database
        if "db" in self.bundle.services:
            volumes["sbh-data"] = {
                "driver": "local"
            }
        
        # Add source code volume for development
        if self.bundle.environment == "local":
            volumes["sbh-src"] = {
                "driver": "local"
            }
        
        return volumes

class KubernetesManifestGenerator:
    """Generates Kubernetes manifests from deployment bundles"""
    
    def __init__(self, bundle: DeploymentBundle):
        self.bundle = bundle
        self.environment = get_environment_profile(bundle.environment)
    
    def generate(self, output_path: str = None, dry_run: bool = False) -> str:
        """Generate Kubernetes manifests YAML"""
        manifests = []
        
        # Generate namespace
        namespace = self._generate_namespace()
        manifests.append(namespace)
        
        # Generate configmap
        configmap = self._generate_configmap()
        manifests.append(configmap)
        
        # Generate secrets (placeholder)
        secrets = self._generate_secrets()
        manifests.append(secrets)
        
        # Generate services
        for service_name, service_config in self.bundle.services.items():
            if service_config.ports:
                service = self._generate_k8s_service(service_name, service_config)
                manifests.append(service)
        
        # Generate deployments
        for service_name, service_config in self.bundle.services.items():
            deployment = self._generate_deployment(service_name, service_config)
            manifests.append(deployment)
        
        # Generate ingress (for production)
        if self.bundle.environment == "production":
            ingress = self._generate_ingress()
            manifests.append(ingress)
        
        # Combine all manifests
        combined_yaml = ""
        for manifest in manifests:
            combined_yaml += yaml.dump(manifest, default_flow_style=False, sort_keys=False)
            combined_yaml += "---\n"
        
        if not dry_run and output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(combined_yaml)
                logger.info(f"Generated Kubernetes manifest: {output_path}")
            except Exception as e:
                logger.error(f"Failed to write Kubernetes manifest: {e}")
        
        return combined_yaml
    
    def _generate_namespace(self) -> Dict[str, Any]:
        """Generate namespace manifest"""
        return {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {
                "name": f"sbh-{self.bundle.name}",
                "labels": {
                    "app": "sbh",
                    "ecosystem": self.bundle.ecosystem,
                    "environment": self.bundle.environment
                }
            }
        }
    
    def _generate_configmap(self) -> Dict[str, Any]:
        """Generate configmap manifest"""
        config_data = {
            "FLASK_ENV": self.bundle.environment,
            "DEBUG": str(self.environment.debug).lower(),
            "DATABASE": self.environment.database_path,
            "LOG_LEVEL": self.environment.logging_level
        }
        
        # Add feature flags
        for flag in self.environment.feature_flags:
            config_data[f"FEATURE_{flag.upper()}"] = "true"
        
        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{self.bundle.name}-config",
                "namespace": f"sbh-{self.bundle.name}"
            },
            "data": config_data
        }
    
    def _generate_secrets(self) -> Dict[str, Any]:
        """Generate secrets manifest (placeholder)"""
        return {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": f"{self.bundle.name}-secrets",
                "namespace": f"sbh-{self.bundle.name}"
            },
            "type": "Opaque",
            "data": {
                "secret-key": "cGxhY2Vob2xkZXItY2hhbmdlLWluLXByb2R1Y3Rpb24="  # base64 encoded
            }
        }
    
    def _generate_k8s_service(self, service_name: str, service_config) -> Dict[str, Any]:
        """Generate Kubernetes service manifest"""
        ports = []
        for port in service_config.ports or []:
            ports.append({
                "name": f"http-{port}",
                "port": port,
                "targetPort": port,
                "protocol": "TCP"
            })
        
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{service_name}-service",
                "namespace": f"sbh-{self.bundle.name}",
                "labels": {
                    "app": service_name,
                    "ecosystem": self.bundle.ecosystem
                }
            },
            "spec": {
                "selector": {
                    "app": service_name
                },
                "ports": ports,
                "type": "ClusterIP"
            }
        }
    
    def _generate_deployment(self, service_name: str, service_config) -> Dict[str, Any]:
        """Generate Kubernetes deployment manifest"""
        containers = [{
            "name": service_name,
            "image": service_config.image or "alpine:latest",
            "ports": [{"containerPort": port} for port in service_config.ports or []],
            "envFrom": [
                {
                    "configMapRef": {
                        "name": f"{self.bundle.name}-config"
                    }
                }
            ],
            "resources": {
                "requests": {
                    "memory": "128Mi",
                    "cpu": "100m"
                },
                "limits": {
                    "memory": "256Mi",
                    "cpu": "200m"
                }
            }
        }]
        
        if service_config.command:
            containers[0]["command"] = service_config.command.split()
        
        if service_config.healthcheck:
            containers[0]["livenessProbe"] = {
                "httpGet": {
                    "path": "/healthz",
                    "port": service_config.ports[0] if service_config.ports else 80
                },
                "initialDelaySeconds": 30,
                "periodSeconds": 10
            }
        
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"{service_name}-deployment",
                "namespace": f"sbh-{self.bundle.name}",
                "labels": {
                    "app": service_name,
                    "ecosystem": self.bundle.ecosystem
                }
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "app": service_name
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": service_name
                        }
                    },
                    "spec": {
                        "containers": containers
                    }
                }
            }
        }
        
        # Add environment-specific overrides
        if self.bundle.environment == "production":
            deployment["spec"]["replicas"] = 3
            deployment["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["memory"] = "512Mi"
            deployment["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["cpu"] = "500m"
        
        return deployment
    
    def _generate_ingress(self) -> Dict[str, Any]:
        """Generate ingress manifest for production"""
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": f"{self.bundle.name}-ingress",
                "namespace": f"sbh-{self.bundle.name}",
                "annotations": {
                    "kubernetes.io/ingress.class": "nginx",
                    "cert-manager.io/cluster-issuer": "letsencrypt-prod"
                }
            },
            "spec": {
                "tls": [{
                    "hosts": [f"{self.bundle.name}.example.com"],
                    "secretName": f"{self.bundle.name}-tls"
                }],
                "rules": [{
                    "host": f"{self.bundle.name}.example.com",
                    "http": {
                        "paths": [{
                            "path": "/",
                            "pathType": "Prefix",
                            "backend": {
                                "service": {
                                    "name": "backend-service",
                                    "port": {
                                        "number": 5001
                                    }
                                }
                            }
                        }]
                    }
                }]
            }
        }

def generate_deployment_artifacts(bundle_name: str, artifact_type: str, 
                                output_path: str = None, dry_run: bool = False) -> str:
    """Generate deployment artifacts for a bundle"""
    from .bundles import get_bundle
    
    bundle = get_bundle(bundle_name)
    if not bundle:
        raise ValueError(f"Bundle not found: {bundle_name}")
    
    if artifact_type == "compose":
        generator = DockerComposeGenerator(bundle)
        return generator.generate(output_path, dry_run)
    elif artifact_type == "kubernetes":
        generator = KubernetesManifestGenerator(bundle)
        return generator.generate(output_path, dry_run)
    else:
        raise ValueError(f"Unknown artifact type: {artifact_type}")
