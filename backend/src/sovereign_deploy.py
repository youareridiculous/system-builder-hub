#!/usr/bin/env python3
"""
P38: Sovereign Deploy – Self-Hosting & Appliance Mode
Give tenants the option to self-host SBH-built systems and in-house models with one-click export → appliance.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import hashlib
import tempfile
import zipfile
import tarfile
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app, send_file
from flask_cors import cross_origin

# Import infrastructure components
from config import config
from metrics import metrics
from feature_flags import flag_required
from idempotency import idempotent, require_idempotency_key
from trace_context import get_current_trace
from costs import cost_accounted, log_with_redaction
from multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Create blueprint
sovereign_deploy_bp = Blueprint('sovereign_deploy', __name__, url_prefix='/api/sovereign')

# Data Models
class NodeStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"

class DeployStatus(Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class NodeKind(Enum):
    ONPREM = "onprem"
    EDGE = "edge"
    CLOUD = "cloud"

@dataclass
class ApplianceNode:
    id: str
    tenant_id: str
    name: str
    kind: NodeKind
    capacity_json: Dict[str, Any]
    status: NodeStatus
    created_at: datetime
    last_heartbeat: datetime
    metadata: Dict[str, Any]

@dataclass
class ApplianceDeployment:
    id: str
    tenant_id: str
    system_id: str
    version: str
    target_node_id: str
    status: DeployStatus
    logs_uri: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]

class SovereignDeployService:
    """Service for sovereign deployment and appliance management"""
    
    def __init__(self):
        self._init_database()
        self.active_nodes: Dict[str, ApplianceNode] = {}
        self.active_deployments: Dict[str, ApplianceDeployment] = {}
    
    def _init_database(self):
        """Initialize sovereign deploy database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create appliance_nodes table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS appliance_nodes (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        capacity_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        last_heartbeat TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create appliance_deployments table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS appliance_deployments (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        target_node_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        logs_uri TEXT,
                        created_at TIMESTAMP NOT NULL,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (target_node_id) REFERENCES appliance_nodes (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Sovereign deploy database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize sovereign deploy database: {e}")
    
    def register_node(self, tenant_id: str, name: str, kind: NodeKind, 
                     capacity_json: Dict[str, Any], signed_token: str) -> Optional[ApplianceNode]:
        """Register a new appliance node"""
        try:
            # Validate signed token
            if not self._validate_node_token(signed_token, tenant_id):
                return None
            
            node_id = f"node_{int(time.time())}"
            now = datetime.now()
            
            node = ApplianceNode(
                id=node_id,
                tenant_id=tenant_id,
                name=name,
                kind=kind,
                capacity_json=capacity_json,
                status=NodeStatus.ACTIVE,
                created_at=now,
                last_heartbeat=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO appliance_nodes 
                    (id, tenant_id, name, kind, capacity_json, status, created_at, last_heartbeat, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    node.id,
                    node.tenant_id,
                    node.name,
                    node.kind.value,
                    json.dumps(node.capacity_json),
                    node.status.value,
                    node.created_at.isoformat(),
                    node.last_heartbeat.isoformat(),
                    json.dumps(node.metadata)
                ))
                conn.commit()
            
            # Add to active nodes
            self.active_nodes[node_id] = node
            
            # Update metrics
            metrics.increment_counter('sbh_appliance_nodes_active')
            
            logger.info(f"Registered appliance node: {node_id}")
            return node
            
        except Exception as e:
            logger.error(f"Failed to register node: {e}")
            return None
    
    def _validate_node_token(self, signed_token: str, tenant_id: str) -> bool:
        """Validate signed token for node registration"""
        try:
            # TODO: Implement actual token validation
            # For now, accept any token
            return True
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False
    
    def update_node_health(self, node_id: str, health_data: Dict[str, Any]) -> bool:
        """Update node health status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE appliance_nodes 
                    SET last_heartbeat = ?, metadata = ?
                    WHERE id = ?
                ''', (
                    datetime.now().isoformat(),
                    json.dumps(health_data),
                    node_id
                ))
                conn.commit()
                
                if cursor.rowcount > 0:
                    # Update active node
                    if node_id in self.active_nodes:
                        self.active_nodes[node_id].last_heartbeat = datetime.now()
                        self.active_nodes[node_id].metadata.update(health_data)
                    
                    logger.info(f"Updated node health: {node_id}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to update node health: {e}")
            return False
    
    def list_nodes(self, tenant_id: str) -> List[ApplianceNode]:
        """List appliance nodes for tenant"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, name, kind, capacity_json, status, created_at, last_heartbeat, metadata
                    FROM appliance_nodes 
                    WHERE tenant_id = ?
                    ORDER BY created_at DESC
                ''', (tenant_id,))
                
                nodes = []
                for row in cursor.fetchall():
                    nodes.append(ApplianceNode(
                        id=row[0],
                        tenant_id=row[1],
                        name=row[2],
                        kind=NodeKind(row[3]),
                        capacity_json=json.loads(row[4]),
                        status=NodeStatus(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        last_heartbeat=datetime.fromisoformat(row[7]),
                        metadata=json.loads(row[8]) if row[8] else {}
                    ))
                
                return nodes
                
        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            return []
    
    def get_node_health(self, node_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get node health status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT status, last_heartbeat, metadata
                    FROM appliance_nodes 
                    WHERE id = ? AND tenant_id = ?
                ''', (node_id, tenant_id))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'status': row[0],
                        'last_heartbeat': row[1],
                        'health_data': json.loads(row[2]) if row[2] else {}
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get node health: {e}")
            return None
    
    def create_deployment(self, tenant_id: str, system_id: str, version: str,
                         target_node_id: str) -> Optional[ApplianceDeployment]:
        """Create a new appliance deployment"""
        try:
            deployment_id = f"deploy_{int(time.time())}"
            now = datetime.now()
            
            deployment = ApplianceDeployment(
                id=deployment_id,
                tenant_id=tenant_id,
                system_id=system_id,
                version=version,
                target_node_id=target_node_id,
                status=DeployStatus.PENDING,
                logs_uri=f"logs/{deployment_id}",
                created_at=now,
                started_at=None,
                completed_at=None,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO appliance_deployments 
                    (id, tenant_id, system_id, version, target_node_id, status, logs_uri, created_at, started_at, completed_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    deployment.id,
                    deployment.tenant_id,
                    deployment.system_id,
                    deployment.version,
                    deployment.target_node_id,
                    deployment.status.value,
                    deployment.logs_uri,
                    deployment.created_at.isoformat(),
                    deployment.started_at.isoformat() if deployment.started_at else None,
                    deployment.completed_at.isoformat() if deployment.completed_at else None,
                    json.dumps(deployment.metadata)
                ))
                conn.commit()
            
            # Add to active deployments
            self.active_deployments[deployment_id] = deployment
            
            # Start deployment process
            self._start_deployment_process(deployment_id, system_id, version, target_node_id, tenant_id)
            
            logger.info(f"Created deployment: {deployment_id}")
            return deployment
            
        except Exception as e:
            logger.error(f"Failed to create deployment: {e}")
            return None
    
    def _start_deployment_process(self, deployment_id: str, system_id: str, version: str,
                                 target_node_id: str, tenant_id: str):
        """Start deployment process in background"""
        try:
            # Update status to building
            self._update_deployment_status(deployment_id, DeployStatus.BUILDING)
            
            # TODO: Implement actual deployment logic
            # For now, simulate deployment process
            import threading
            deployment_thread = threading.Thread(
                target=self._simulate_deployment,
                args=(deployment_id, system_id, version, target_node_id, tenant_id),
                daemon=True
            )
            deployment_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start deployment process: {e}")
            self._update_deployment_status(deployment_id, DeployStatus.FAILED)
    
    def _simulate_deployment(self, deployment_id: str, system_id: str, version: str,
                            target_node_id: str, tenant_id: str):
        """Simulate deployment process"""
        try:
            # Simulate building phase
            time.sleep(3)
            self._update_deployment_status(deployment_id, DeployStatus.DEPLOYING)
            
            # Simulate deploying phase
            time.sleep(2)
            self._update_deployment_status(deployment_id, DeployStatus.COMPLETED)
            
            # Update metrics
            metrics.increment_counter('sbh_sovereign_deploy_total')
            
            logger.info(f"Deployment completed: {deployment_id}")
            
        except Exception as e:
            logger.error(f"Deployment simulation failed: {e}")
            self._update_deployment_status(deployment_id, DeployStatus.FAILED)
    
    def _update_deployment_status(self, deployment_id: str, status: DeployStatus):
        """Update deployment status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                if status == DeployStatus.BUILDING:
                    cursor.execute('''
                        UPDATE appliance_deployments 
                        SET status = ?, started_at = ?
                        WHERE id = ?
                    ''', (status.value, datetime.now().isoformat(), deployment_id))
                elif status in [DeployStatus.COMPLETED, DeployStatus.FAILED]:
                    cursor.execute('''
                        UPDATE appliance_deployments 
                        SET status = ?, completed_at = ?
                        WHERE id = ?
                    ''', (status.value, datetime.now().isoformat(), deployment_id))
                else:
                    cursor.execute('''
                        UPDATE appliance_deployments 
                        SET status = ?
                        WHERE id = ?
                    ''', (status.value, deployment_id))
                
                conn.commit()
                
                # Update active deployments
                if deployment_id in self.active_deployments:
                    self.active_deployments[deployment_id].status = status
                
        except Exception as e:
            logger.error(f"Failed to update deployment status: {e}")
    
    def get_deployment_status(self, deployment_id: str, tenant_id: str) -> Optional[ApplianceDeployment]:
        """Get deployment status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, system_id, version, target_node_id, status, logs_uri, 
                           created_at, started_at, completed_at, metadata
                    FROM appliance_deployments 
                    WHERE id = ? AND tenant_id = ?
                ''', (deployment_id, tenant_id))
                row = cursor.fetchone()
                
                if row:
                    return ApplianceDeployment(
                        id=row[0],
                        tenant_id=row[1],
                        system_id=row[2],
                        version=row[3],
                        target_node_id=row[4],
                        status=DeployStatus(row[5]),
                        logs_uri=row[6],
                        created_at=datetime.fromisoformat(row[7]),
                        started_at=datetime.fromisoformat(row[8]) if row[8] else None,
                        completed_at=datetime.fromisoformat(row[9]) if row[9] else None,
                        metadata=json.loads(row[10]) if row[10] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return None
    
    def create_package(self, system_id: str, version: str, tenant_id: str) -> Optional[str]:
        """Create deployment package"""
        try:
            package_id = f"package_{int(time.time())}"
            
            # Create temporary package directory
            package_dir = tempfile.mkdtemp()
            
            # Generate package contents
            self._generate_package_contents(package_dir, system_id, version, tenant_id)
            
            # Create package archive
            package_path = self._create_package_archive(package_dir, package_id)
            
            # Clean up temp directory
            import shutil
            shutil.rmtree(package_dir)
            
            if package_path:
                logger.info(f"Created package: {package_id}")
                return package_path
            return None
            
        except Exception as e:
            logger.error(f"Failed to create package: {e}")
            return None
    
    def _generate_package_contents(self, package_dir: str, system_id: str, version: str, tenant_id: str):
        """Generate package contents"""
        try:
            # Create package structure
            os.makedirs(os.path.join(package_dir, 'app'), exist_ok=True)
            os.makedirs(os.path.join(package_dir, 'config'), exist_ok=True)
            os.makedirs(os.path.join(package_dir, 'data'), exist_ok=True)
            os.makedirs(os.path.join(package_dir, 'models'), exist_ok=True)
            
            # Create manifest
            manifest = {
                'system_id': system_id,
                'version': version,
                'tenant_id': tenant_id,
                'created_at': datetime.now().isoformat(),
                'package_id': f"package_{int(time.time())}",
                'components': {
                    'app': 'system_application',
                    'config': 'system_configuration',
                    'data': 'system_data',
                    'models': 'system_models'
                }
            }
            
            with open(os.path.join(package_dir, 'manifest.json'), 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Create docker-compose template
            docker_compose = {
                'version': '3.8',
                'services': {
                    'sbh-appliance': {
                        'image': 'sbh/appliance:latest',
                        'ports': ['8080:8080'],
                        'environment': [
                            'SYSTEM_ID=${SYSTEM_ID}',
                            'TENANT_ID=${TENANT_ID}',
                            'LICENSE_KEY=${LICENSE_KEY}'
                        ],
                        'volumes': [
                            './data:/app/data',
                            './models:/app/models'
                        ]
                    }
                }
            }
            
            with open(os.path.join(package_dir, 'docker-compose.yml'), 'w') as f:
                import yaml
                yaml.dump(docker_compose, f, default_flow_style=False)
            
            # Create environment template
            env_template = f"""# SBH Appliance Environment Configuration
SYSTEM_ID={system_id}
TENANT_ID={tenant_id}
LICENSE_KEY=your_license_key_here
DATABASE_URL=sqlite:///app/data/system.db
LOG_LEVEL=INFO
"""
            
            with open(os.path.join(package_dir, '.env.example'), 'w') as f:
                f.write(env_template)
            
            # Create README
            readme = f"""# SBH Appliance Package

System ID: {system_id}
Version: {version}
Tenant ID: {tenant_id}

## Installation

1. Extract this package to your target environment
2. Copy `.env.example` to `.env` and configure your settings
3. Run: `docker-compose up -d`

## License

This appliance requires a valid license key from System Builder Hub.

## Support

For support, contact your SBH administrator.
"""
            
            with open(os.path.join(package_dir, 'README.md'), 'w') as f:
                f.write(readme)
            
        except Exception as e:
            logger.error(f"Failed to generate package contents: {e}")
    
    def _create_package_archive(self, package_dir: str, package_id: str) -> Optional[str]:
        """Create package archive"""
        try:
            # Create temporary archive file
            archive_path = tempfile.mktemp(suffix='.tar.gz')
            
            # Create tar.gz archive
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(package_dir, arcname='')
            
            # Calculate checksum
            with open(archive_path, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            # Rename with checksum
            final_path = archive_path.replace('.tar.gz', f'_{checksum[:8]}.tar.gz')
            os.rename(archive_path, final_path)
            
            logger.info(f"Created package archive: {final_path}")
            return final_path
            
        except Exception as e:
            logger.error(f"Failed to create package archive: {e}")
            return None
    
    def download_package(self, package_id: str, tenant_id: str) -> Optional[str]:
        """Get download URL for package"""
        try:
            # TODO: Implement actual package storage and retrieval
            # For now, create a new package
            package_path = self.create_package("system_123", "1.0.0", tenant_id)
            
            if package_path:
                # Update metrics
                file_size = os.path.getsize(package_path)
                metrics.increment_counter('sbh_sovereign_package_bytes_total', {'bytes': file_size})
                
                return package_path
            return None
            
        except Exception as e:
            logger.error(f"Failed to download package: {e}")
            return None

# Initialize service
sovereign_deploy_service = SovereignDeployService()

# API Routes
@sovereign_deploy_bp.route('/node/register', methods=['POST'])
@cross_origin()
@flag_required('sovereign_deploy')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def register_node():
    """Register a new appliance node"""
    try:
        data = request.get_json()
        name = data.get('name')
        kind = data.get('kind')
        capacity_json = data.get('capacity', {})
        signed_token = data.get('signed_token')
        
        if not all([name, kind, signed_token]):
            return jsonify({'error': 'name, kind, and signed_token are required'}), 400
        
        try:
            node_kind = NodeKind(kind)
        except ValueError:
            return jsonify({'error': 'Invalid kind'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        node = sovereign_deploy_service.register_node(
            tenant_id=tenant_id,
            name=name,
            kind=node_kind,
            capacity_json=capacity_json,
            signed_token=signed_token
        )
        
        if not node:
            return jsonify({'error': 'Failed to register node'}), 500
        
        return jsonify({
            'success': True,
            'node': asdict(node)
        })
        
    except Exception as e:
        logger.error(f"Register node error: {e}")
        return jsonify({'error': str(e)}), 500

@sovereign_deploy_bp.route('/node/list', methods=['GET'])
@cross_origin()
@flag_required('sovereign_deploy')
@require_tenant_context
def list_nodes():
    """List appliance nodes"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        nodes = sovereign_deploy_service.list_nodes(tenant_id)
        
        return jsonify({
            'success': True,
            'nodes': [asdict(n) for n in nodes]
        })
        
    except Exception as e:
        logger.error(f"List nodes error: {e}")
        return jsonify({'error': str(e)}), 500

@sovereign_deploy_bp.route('/node/health', methods=['GET'])
@cross_origin()
@flag_required('sovereign_deploy')
@require_tenant_context
def get_node_health():
    """Get node health status"""
    try:
        node_id = request.args.get('node_id')
        
        if not node_id:
            return jsonify({'error': 'node_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        health = sovereign_deploy_service.get_node_health(node_id, tenant_id)
        
        if not health:
            return jsonify({'error': 'Node not found'}), 404
        
        return jsonify({
            'success': True,
            'health': health
        })
        
    except Exception as e:
        logger.error(f"Get node health error: {e}")
        return jsonify({'error': str(e)}), 500

@sovereign_deploy_bp.route('/deploy', methods=['POST'])
@cross_origin()
@flag_required('sovereign_deploy')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_deployment():
    """Create a new deployment"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        version = data.get('version')
        target_node_id = data.get('target_node_id')
        
        if not all([system_id, version, target_node_id]):
            return jsonify({'error': 'system_id, version, and target_node_id are required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        deployment = sovereign_deploy_service.create_deployment(
            tenant_id=tenant_id,
            system_id=system_id,
            version=version,
            target_node_id=target_node_id
        )
        
        if not deployment:
            return jsonify({'error': 'Failed to create deployment'}), 500
        
        return jsonify({
            'success': True,
            'deployment': asdict(deployment)
        })
        
    except Exception as e:
        logger.error(f"Create deployment error: {e}")
        return jsonify({'error': str(e)}), 500

@sovereign_deploy_bp.route('/deploy/status/<deployment_id>', methods=['GET'])
@cross_origin()
@flag_required('sovereign_deploy')
@require_tenant_context
def get_deployment_status(deployment_id):
    """Get deployment status"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        deployment = sovereign_deploy_service.get_deployment_status(deployment_id, tenant_id)
        
        if not deployment:
            return jsonify({'error': 'Deployment not found'}), 404
        
        return jsonify({
            'success': True,
            'deployment': asdict(deployment)
        })
        
    except Exception as e:
        logger.error(f"Get deployment status error: {e}")
        return jsonify({'error': str(e)}), 500

@sovereign_deploy_bp.route('/package', methods=['POST'])
@cross_origin()
@flag_required('sovereign_deploy')
@require_tenant_context
@cost_accounted("api", "operation")
def create_package():
    """Create deployment package"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        version = data.get('version')
        
        if not all([system_id, version]):
            return jsonify({'error': 'system_id and version are required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        package_path = sovereign_deploy_service.create_package(system_id, version, tenant_id)
        
        if not package_path:
            return jsonify({'error': 'Failed to create package'}), 500
        
        return jsonify({
            'success': True,
            'package_path': package_path
        })
        
    except Exception as e:
        logger.error(f"Create package error: {e}")
        return jsonify({'error': str(e)}), 500

@sovereign_deploy_bp.route('/package/<package_id>/download', methods=['GET'])
@cross_origin()
@flag_required('sovereign_deploy')
def download_package(package_id):
    """Download package"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        package_path = sovereign_deploy_service.download_package(package_id, tenant_id)
        
        if not package_path:
            return jsonify({'error': 'Package not found'}), 404
        
        return send_file(
            package_path,
            as_attachment=True,
            download_name=f"sbh_appliance_{package_id}.tar.gz"
        )
        
    except Exception as e:
        logger.error(f"Download package error: {e}")
        return jsonify({'error': str(e)}), 500
