#!/usr/bin/env python3
"""
P59: Supply Chain & Secrets Hardening (SBOM, SCA, KMS/HSM)
Prevent supply-chain compromise and secret leakage across SBH and generated systems.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app
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
supply_chain_bp = Blueprint('supply_chain', __name__, url_prefix='/api/security')

# Data Models
class SecretScope(Enum):
    SBH = "sbh"
    SYSTEM = "system"
    PREVIEW = "preview"

class SCAFindingSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecretMetadata:
    id: str
    tenant_id: Optional[str]
    scope: SecretScope
    key_id: str
    created_at: datetime
    rotated_at: Optional[datetime]
    metadata: Dict[str, Any]

@dataclass
class SBOMManifest:
    id: str
    system_id: str
    version: str
    manifest_uri: str
    created_at: datetime
    metadata: Dict[str, Any]

class SupplyChainService:
    """Service for supply chain security and secrets management"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
        self.secret_cache: Dict[str, str] = {}
    
    def _init_database(self):
        """Initialize supply chain database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create secret_metadata table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS secret_metadata (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT,
                        scope TEXT NOT NULL,
                        key_id TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        rotated_at TIMESTAMP,
                        metadata TEXT
                    )
                ''')
                
                # Create sbom_manifests table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sbom_manifests (
                        id TEXT PRIMARY KEY,
                        system_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        manifest_uri TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_secret_metadata_tenant_id 
                    ON secret_metadata (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_secret_metadata_scope 
                    ON secret_metadata (scope)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_secret_metadata_rotated_at 
                    ON secret_metadata (rotated_at)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_sbom_manifests_system_id 
                    ON sbom_manifests (system_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_sbom_manifests_version 
                    ON sbom_manifests (version)
                ''')
                
                conn.commit()
                logger.info("Supply chain database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize supply chain database: {e}")
    
    def generate_sbom(self, system_id: str, version: Optional[str] = None, tenant_id: str = None) -> Optional[SBOMManifest]:
        """Generate SBOM (Software Bill of Materials) for a system"""
        try:
            if not version:
                version = "latest"
            
            manifest_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Generate SBOM content (CycloneDX format)
            sbom_content = self._generate_sbom_content(system_id, version, tenant_id)
            
            # Store manifest (in reality, this would be in object storage)
            manifest_uri = f"sbom/{tenant_id}/{system_id}/{version}/{manifest_id}.json"
            self._store_sbom_manifest(manifest_uri, sbom_content)
            
            sbom_manifest = SBOMManifest(
                id=manifest_id,
                system_id=system_id,
                version=version,
                manifest_uri=manifest_uri,
                created_at=now,
                metadata={'format': 'cyclonedx', 'version': '1.4'}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sbom_manifests 
                    (id, system_id, version, manifest_uri, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    sbom_manifest.id,
                    sbom_manifest.system_id,
                    sbom_manifest.version,
                    sbom_manifest.manifest_uri,
                    sbom_manifest.created_at.isoformat(),
                    json.dumps(sbom_manifest.metadata)
                ))
                conn.commit()
            
            # Record metrics
            metrics.counter('sbh_sbom_generated_total').inc()
            
            logger.info(f"Generated SBOM for system {system_id} version {version}")
            return sbom_manifest
            
        except Exception as e:
            logger.error(f"Failed to generate SBOM: {e}")
            return None
    
    def rotate_secrets(self, scope: SecretScope, key_id: Optional[str] = None, tenant_id: str = None) -> bool:
        """Rotate secrets for specified scope"""
        try:
            now = datetime.now()
            
            # Determine which keys to rotate
            if key_id:
                keys_to_rotate = [key_id]
            else:
                keys_to_rotate = self._get_keys_for_rotation(scope, tenant_id)
            
            rotated_count = 0
            for key in keys_to_rotate:
                # Generate new secret
                new_secret = self._generate_new_secret(scope, key)
                
                # Update secret in KMS
                success = self._update_secret_in_kms(key, new_secret)
                if success:
                    # Update metadata
                    self._update_secret_metadata(key, now, tenant_id)
                    rotated_count += 1
                    
                    # Clear cache
                    cache_key = f"{scope.value}:{key}"
                    if cache_key in self.secret_cache:
                        del self.secret_cache[cache_key]
            
            # Record metrics
            metrics.counter('sbh_secret_rotations_total').inc(rotated_count)
            
            logger.info(f"Rotated {rotated_count} secrets for scope {scope.value}")
            return rotated_count > 0
            
        except Exception as e:
            logger.error(f"Failed to rotate secrets: {e}")
            return False
    
    def get_secrets_status(self, tenant_id: str = None) -> Dict[str, Any]:
        """Get secrets status and rotation information"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, tenant_id, scope, key_id, created_at, rotated_at, metadata
                    FROM secret_metadata 
                    WHERE 1=1
                '''
                params = []
                
                if tenant_id:
                    query += ' AND (tenant_id = ? OR tenant_id IS NULL)'
                    params.append(tenant_id)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                keys = []
                rotation_due = []
                
                for row in rows:
                    key_info = {
                        'id': row[0],
                        'tenant_id': row[1],
                        'scope': row[2],
                        'key_id': row[3],
                        'created_at': row[4],
                        'rotated_at': row[5],
                        'metadata': json.loads(row[6]) if row[6] else {}
                    }
                    keys.append(key_info)
                    
                    # Check if rotation is due
                    if self._is_rotation_due(row[5], row[4]):
                        rotation_due.append(key_info)
                
                return {
                    'keys': keys,
                    'rotation_due': rotation_due,
                    'total_keys': len(keys),
                    'keys_needing_rotation': len(rotation_due)
                }
                
        except Exception as e:
            logger.error(f"Failed to get secrets status: {e}")
            return {'keys': [], 'rotation_due': [], 'total_keys': 0, 'keys_needing_rotation': 0}
    
    def scan_sca(self, system_id: str, version: Optional[str] = None, tenant_id: str = None) -> Dict[str, Any]:
        """Run Software Composition Analysis (SCA) scan"""
        try:
            if not version:
                version = "latest"
            
            # Run SCA scan (in reality, this would integrate with tools like Snyk, OWASP Dependency Check)
            findings = self._run_sca_scan(system_id, version, tenant_id)
            
            # Categorize findings by severity
            findings_by_severity = {
                'critical': [],
                'high': [],
                'medium': [],
                'low': []
            }
            
            for finding in findings:
                severity = finding.get('severity', 'low')
                findings_by_severity[severity].append(finding)
            
            # Record metrics
            for severity, finding_list in findings_by_severity.items():
                if finding_list:
                    metrics.counter('sbh_sca_findings_total', {'severity': severity}).inc(len(finding_list))
            
            # Check if critical findings should block release
            has_critical_findings = len(findings_by_severity['critical']) > 0
            
            result = {
                'system_id': system_id,
                'version': version,
                'scan_timestamp': datetime.now().isoformat(),
                'findings': findings,
                'findings_by_severity': findings_by_severity,
                'total_findings': len(findings),
                'has_critical_findings': has_critical_findings,
                'should_block_release': has_critical_findings
            }
            
            logger.info(f"SCA scan completed for system {system_id}: {len(findings)} findings")
            return result
            
        except Exception as e:
            logger.error(f"Failed to run SCA scan: {e}")
            return {
                'system_id': system_id,
                'version': version,
                'error': str(e),
                'findings': [],
                'should_block_release': False
            }
    
    def _generate_sbom_content(self, system_id: str, version: str, tenant_id: str) -> Dict[str, Any]:
        """Generate SBOM content in CycloneDX format"""
        try:
            # In reality, this would analyze the system's dependencies
            # For now, generate a sample SBOM
            sbom = {
                "bomFormat": "CycloneDX",
                "specVersion": "1.4",
                "version": 1,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "tools": [
                        {
                            "vendor": "SBH",
                            "name": "System Builder Hub",
                            "version": "1.0.0"
                        }
                    ],
                    "component": {
                        "type": "application",
                        "name": f"system-{system_id}",
                        "version": version,
                        "purl": f"pkg:sbh/system/{system_id}@{version}"
                    }
                },
                "components": [
                    {
                        "type": "library",
                        "name": "flask",
                        "version": "2.3.3",
                        "purl": "pkg:pypi/flask@2.3.3"
                    },
                    {
                        "type": "library",
                        "name": "sqlalchemy",
                        "version": "2.0.21",
                        "purl": "pkg:pypi/sqlalchemy@2.0.21"
                    }
                ]
            }
            
            return sbom
            
        except Exception as e:
            logger.error(f"Failed to generate SBOM content: {e}")
            return {}
    
    def _store_sbom_manifest(self, manifest_uri: str, content: Dict[str, Any]):
        """Store SBOM manifest in object storage"""
        try:
            # In reality, this would store in S3/GCS/Azure
            # For now, simulate storage
            logger.info(f"Storing SBOM manifest: {manifest_uri}")
            
        except Exception as e:
            logger.error(f"Failed to store SBOM manifest: {e}")
    
    def _get_keys_for_rotation(self, scope: SecretScope, tenant_id: str) -> List[str]:
        """Get keys that need rotation"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT key_id FROM secret_metadata 
                    WHERE scope = ? AND (tenant_id = ? OR tenant_id IS NULL)
                ''', (scope.value, tenant_id))
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get keys for rotation: {e}")
            return []
    
    def _generate_new_secret(self, scope: SecretScope, key_id: str) -> str:
        """Generate new secret value"""
        try:
            # In reality, this would use proper cryptographic random generation
            # For now, generate a UUID-based secret
            import secrets as py_secrets
            return py_secrets.token_urlsafe(32)
            
        except Exception as e:
            logger.error(f"Failed to generate new secret: {e}")
            return ""
    
    def _update_secret_in_kms(self, key_id: str, new_secret: str) -> bool:
        """Update secret in KMS"""
        try:
            # In reality, this would update the secret in AWS KMS, GCP KMS, Azure Key Vault, etc.
            # For now, simulate the operation
            logger.info(f"Updated secret {key_id} in KMS")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update secret in KMS: {e}")
            return False
    
    def _update_secret_metadata(self, key_id: str, rotated_at: datetime, tenant_id: str):
        """Update secret metadata with rotation timestamp"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE secret_metadata 
                    SET rotated_at = ?
                    WHERE key_id = ? AND (tenant_id = ? OR tenant_id IS NULL)
                ''', (rotated_at.isoformat(), key_id, tenant_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update secret metadata: {e}")
    
    def _is_rotation_due(self, rotated_at: Optional[str], created_at: str) -> bool:
        """Check if secret rotation is due"""
        try:
            if not rotated_at:
                # Never rotated, check creation date
                created_date = datetime.fromisoformat(created_at)
                rotation_days = config.SECRET_ROTATION_DAYS
                return datetime.now() - created_date > timedelta(days=rotation_days)
            else:
                # Check last rotation date
                rotated_date = datetime.fromisoformat(rotated_at)
                rotation_days = config.SECRET_ROTATION_DAYS
                return datetime.now() - rotated_date > timedelta(days=rotation_days)
                
        except Exception as e:
            logger.error(f"Failed to check rotation due: {e}")
            return False
    
    def _run_sca_scan(self, system_id: str, version: str, tenant_id: str) -> List[Dict[str, Any]]:
        """Run SCA scan on system"""
        try:
            # In reality, this would run actual SCA tools
            # For now, simulate findings
            findings = [
                {
                    'id': 'CVE-2023-1234',
                    'severity': 'medium',
                    'component': 'flask@2.3.3',
                    'description': 'Cross-site scripting vulnerability',
                    'cve_id': 'CVE-2023-1234',
                    'cvss_score': 6.1,
                    'recommendation': 'Upgrade to Flask 2.3.4 or later'
                },
                {
                    'id': 'CVE-2023-5678',
                    'severity': 'low',
                    'component': 'sqlalchemy@2.0.21',
                    'description': 'Information disclosure vulnerability',
                    'cve_id': 'CVE-2023-5678',
                    'cvss_score': 3.1,
                    'recommendation': 'Upgrade to SQLAlchemy 2.0.22 or later'
                }
            ]
            
            return findings
            
        except Exception as e:
            logger.error(f"Failed to run SCA scan: {e}")
            return []

# Initialize service
supply_chain_service = SupplyChainService()

# API Routes
@supply_chain_bp.route('/sbom/generate', methods=['POST'])
@cross_origin()
@flag_required('supply_chain')
@require_tenant_context
@cost_accounted("api", "operation")
def generate_sbom():
    """Generate SBOM for a system"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        version = data.get('version')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        sbom_manifest = supply_chain_service.generate_sbom(
            system_id=system_id,
            version=version,
            tenant_id=tenant_id
        )
        
        if not sbom_manifest:
            return jsonify({'error': 'Failed to generate SBOM'}), 500
        
        return jsonify({
            'success': True,
            'manifest_id': sbom_manifest.id,
            'download_url': f"/api/security/sbom/download/{sbom_manifest.id}",
            'sbom_manifest': asdict(sbom_manifest)
        })
        
    except Exception as e:
        logger.error(f"Generate SBOM error: {e}")
        return jsonify({'error': str(e)}), 500

@supply_chain_bp.route('/secrets/rotate', methods=['POST'])
@cross_origin()
@flag_required('supply_chain')
@require_tenant_context
@cost_accounted("api", "operation")
def rotate_secrets():
    """Rotate secrets"""
    try:
        data = request.get_json()
        scope = data.get('scope')
        key_id = data.get('key_id')
        
        if not scope:
            return jsonify({'error': 'scope is required'}), 400
        
        try:
            secret_scope = SecretScope(scope)
        except ValueError:
            return jsonify({'error': 'Invalid scope'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        success = supply_chain_service.rotate_secrets(
            scope=secret_scope,
            key_id=key_id,
            tenant_id=tenant_id
        )
        
        if not success:
            return jsonify({'error': 'Failed to rotate secrets'}), 500
        
        return jsonify({
            'success': True,
            'rotated_at': datetime.now().isoformat(),
            'message': f'Secrets rotated for scope {scope}'
        })
        
    except Exception as e:
        logger.error(f"Rotate secrets error: {e}")
        return jsonify({'error': str(e)}), 500

@supply_chain_bp.route('/secrets/status', methods=['GET'])
@cross_origin()
@flag_required('supply_chain')
@require_tenant_context
def get_secrets_status():
    """Get secrets status"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        status = supply_chain_service.get_secrets_status(tenant_id=tenant_id)
        
        return jsonify({
            'success': True,
            **status
        })
        
    except Exception as e:
        logger.error(f"Get secrets status error: {e}")
        return jsonify({'error': str(e)}), 500

@supply_chain_bp.route('/sca/scan', methods=['POST'])
@cross_origin()
@flag_required('supply_chain')
@require_tenant_context
@cost_accounted("api", "operation")
def scan_sca():
    """Run SCA scan"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        version = data.get('version')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        findings = supply_chain_service.scan_sca(
            system_id=system_id,
            version=version,
            tenant_id=tenant_id
        )
        
        return jsonify({
            'success': True,
            **findings
        })
        
    except Exception as e:
        logger.error(f"SCA scan error: {e}")
        return jsonify({'error': str(e)}), 500
