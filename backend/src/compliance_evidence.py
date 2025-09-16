#!/usr/bin/env python3
"""
P65: Enterprise Compliance Evidence & Attestations
Produce exportable evidence packs for audits (SOC2/ISO/HIPAA/PCI) and deployment attestation bundles.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import threading
import hashlib
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
compliance_bp = Blueprint('compliance', __name__, url_prefix='/api/compliance')

# Data Models
class EvidenceScope(Enum):
    PLATFORM = "platform"
    TENANT = "tenant"
    SYSTEM = "system"

class AttestationStatus(Enum):
    PENDING = "pending"
    GENERATED = "generated"
    SIGNED = "signed"
    VERIFIED = "verified"
    EXPIRED = "expired"

@dataclass
class EvidencePacket:
    id: str
    tenant_id: str
    scope: EvidenceScope
    bundle_uri: str
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class Attestation:
    id: str
    system_id: str
    version: str
    summary_json: Dict[str, Any]
    bundle_uri: str
    created_at: datetime
    metadata: Dict[str, Any]

class ComplianceEvidenceService:
    """Service for compliance evidence and attestations"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize compliance evidence database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create evidence_packets table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS evidence_packets (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        scope TEXT NOT NULL,
                        bundle_uri TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create attestations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attestations (
                        id TEXT PRIMARY KEY,
                        system_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        summary_json TEXT NOT NULL,
                        bundle_uri TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_evidence_packets_tenant_id 
                    ON evidence_packets (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_evidence_packets_scope 
                    ON evidence_packets (scope)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_evidence_packets_created_at 
                    ON evidence_packets (created_at)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_attestations_system_id 
                    ON attestations (system_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_attestations_version 
                    ON attestations (version)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_attestations_created_at 
                    ON attestations (created_at)
                ''')
                
                conn.commit()
                logger.info("Compliance evidence database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize compliance evidence database: {e}")
    
    def generate_evidence_packet(self, tenant_id: str, scope: EvidenceScope, 
                                 system_id: str = None) -> Optional[EvidencePacket]:
        """Generate evidence packet for compliance audit"""
        try:
            packet_id = str(uuid.uuid4())
            now = datetime.now()
            
            # Collect evidence from various sources
            evidence_data = self._collect_evidence(scope, tenant_id, system_id)
            
            # Create signed bundle
            bundle_uri = self._create_evidence_bundle(packet_id, evidence_data)
            
            evidence_packet = EvidencePacket(
                id=packet_id,
                tenant_id=tenant_id,
                scope=scope,
                bundle_uri=bundle_uri,
                created_at=now,
                metadata={
                    'system_id': system_id,
                    'evidence_sources': list(evidence_data.keys()),
                    'bundle_hash': self._calculate_bundle_hash(bundle_uri)
                }
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO evidence_packets 
                    (id, tenant_id, scope, bundle_uri, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    evidence_packet.id,
                    evidence_packet.tenant_id,
                    evidence_packet.scope.value,
                    evidence_packet.bundle_uri,
                    evidence_packet.created_at.isoformat(),
                    json.dumps(evidence_packet.metadata)
                ))
                conn.commit()
            
            # Record metrics
            metrics.counter('sbh_evidence_packets_total', {'scope': scope.value}).inc()
            
            logger.info(f"Generated evidence packet: {packet_id} for scope {scope.value}")
            return evidence_packet
            
        except Exception as e:
            logger.error(f"Failed to generate evidence packet: {e}")
            return None
    
    def generate_attestation(self, system_id: str, version: str = None) -> Optional[Attestation]:
        """Generate deployment attestation bundle"""
        try:
            attestation_id = str(uuid.uuid4())
            now = datetime.now()
            
            if version is None:
                version = "latest"
            
            # Collect attestation data
            attestation_data = self._collect_attestation_data(system_id, version)
            
            # Create signed bundle
            bundle_uri = self._create_attestation_bundle(attestation_id, attestation_data)
            
            attestation = Attestation(
                id=attestation_id,
                system_id=system_id,
                version=version,
                summary_json=attestation_data.get('summary', {}),
                bundle_uri=bundle_uri,
                created_at=now,
                metadata={
                    'status': AttestationStatus.GENERATED.value,
                    'bundle_hash': self._calculate_bundle_hash(bundle_uri),
                    'signature': self._sign_attestation(attestation_data)
                }
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO attestations 
                    (id, system_id, version, summary_json, bundle_uri, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    attestation.id,
                    attestation.system_id,
                    attestation.version,
                    json.dumps(attestation.summary_json),
                    attestation.bundle_uri,
                    attestation.created_at.isoformat(),
                    json.dumps(attestation.metadata)
                ))
                conn.commit()
            
            # Record metrics
            metrics.counter('sbh_attestations_total').inc()
            
            logger.info(f"Generated attestation: {attestation_id} for system {system_id}")
            return attestation
            
        except Exception as e:
            logger.error(f"Failed to generate attestation: {e}")
            return None
    
    def get_attestation(self, attestation_id: str) -> Optional[Attestation]:
        """Get attestation by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, system_id, version, summary_json, bundle_uri, created_at, metadata
                    FROM attestations 
                    WHERE id = ?
                ''', (attestation_id,))
                
                row = cursor.fetchone()
                if row:
                    return Attestation(
                        id=row[0],
                        system_id=row[1],
                        version=row[2],
                        summary_json=json.loads(row[3]),
                        bundle_uri=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get attestation: {e}")
            return None
    
    def _collect_evidence(self, scope: EvidenceScope, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect evidence from various sources"""
        try:
            evidence = {
                'timestamp': datetime.now().isoformat(),
                'scope': scope.value,
                'tenant_id': tenant_id,
                'system_id': system_id
            }
            
            # Collect from OmniTrace (P21)
            evidence['omn_trace'] = self._collect_omn_trace_evidence(tenant_id, system_id)
            
            # Collect from Supply Chain (P59)
            evidence['supply_chain'] = self._collect_supply_chain_evidence(tenant_id, system_id)
            
            # Collect from Residency (P58)
            evidence['residency'] = self._collect_residency_evidence(tenant_id, system_id)
            
            # Collect from Quality Gates (P54)
            evidence['quality_gates'] = self._collect_quality_gates_evidence(tenant_id, system_id)
            
            # Collect security events
            evidence['security_events'] = self._collect_security_events(tenant_id, system_id)
            
            # Collect from Backups (P31)
            evidence['backups'] = self._collect_backup_evidence(tenant_id, system_id)
            
            # Collect SBOM/SCA data
            evidence['sbom_sca'] = self._collect_sbom_sca_evidence(tenant_id, system_id)
            
            # Collect Redteam runs
            evidence['redteam_runs'] = self._collect_redteam_evidence(tenant_id, system_id)
            
            return evidence
            
        except Exception as e:
            logger.error(f"Evidence collection error: {e}")
            return {'error': str(e)}
    
    def _collect_omn_trace_evidence(self, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect evidence from OmniTrace (P21)"""
        try:
            # In reality, this would call P21 OmniTrace service
            # For now, simulate the data
            return {
                'trace_count': 15000,
                'error_rate': 0.02,
                'avg_response_time': 120,
                'security_events': 5,
                'compliance_checks': 100
            }
        except Exception as e:
            logger.error(f"OmniTrace evidence collection error: {e}")
            return {}
    
    def _collect_supply_chain_evidence(self, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect evidence from Supply Chain (P59)"""
        try:
            # In reality, this would call P59 Supply Chain service
            # For now, simulate the data
            return {
                'dependencies_count': 45,
                'vulnerabilities_found': 2,
                'licenses_verified': 43,
                'last_scan': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Supply chain evidence collection error: {e}")
            return {}
    
    def _collect_residency_evidence(self, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect evidence from Residency (P58)"""
        try:
            # In reality, this would call P58 Residency service
            # For now, simulate the data
            return {
                'data_regions': ['us-east-1', 'us-west-2'],
                'compliance_regions': ['us', 'eu'],
                'data_classification': 'confidential',
                'retention_policy': '7_years'
            }
        except Exception as e:
            logger.error(f"Residency evidence collection error: {e}")
            return {}
    
    def _collect_quality_gates_evidence(self, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect evidence from Quality Gates (P54)"""
        try:
            # In reality, this would call P54 Quality Gates service
            # For now, simulate the data
            return {
                'gates_passed': 8,
                'gates_failed': 0,
                'last_validation': datetime.now().isoformat(),
                'security_score': 95,
                'performance_score': 88
            }
        except Exception as e:
            logger.error(f"Quality gates evidence collection error: {e}")
            return {}
    
    def _collect_security_events(self, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect security events"""
        try:
            # In reality, this would query security event logs
            # For now, simulate the data
            return {
                'events_count': 1250,
                'critical_events': 0,
                'high_events': 3,
                'medium_events': 15,
                'low_events': 1232,
                'last_incident': None
            }
        except Exception as e:
            logger.error(f"Security events collection error: {e}")
            return {}
    
    def _collect_backup_evidence(self, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect evidence from Backups (P31)"""
        try:
            # In reality, this would call P31 Backups service
            # For now, simulate the data
            return {
                'backup_count': 30,
                'last_backup': datetime.now().isoformat(),
                'backup_size_gb': 2.5,
                'recovery_tests': 12,
                'rto_minutes': 15,
                'rpo_minutes': 5
            }
        except Exception as e:
            logger.error(f"Backup evidence collection error: {e}")
            return {}
    
    def _collect_sbom_sca_evidence(self, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect SBOM/SCA evidence"""
        try:
            # In reality, this would query SBOM/SCA databases
            # For now, simulate the data
            return {
                'sbom_generated': True,
                'components_count': 156,
                'vulnerabilities': 3,
                'licenses': ['MIT', 'Apache-2.0', 'GPL-3.0'],
                'last_scan': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"SBOM/SCA evidence collection error: {e}")
            return {}
    
    def _collect_redteam_evidence(self, tenant_id: str, system_id: str = None) -> Dict[str, Any]:
        """Collect Redteam evidence"""
        try:
            # In reality, this would query Redteam run results
            # For now, simulate the data
            return {
                'runs_count': 4,
                'last_run': datetime.now().isoformat(),
                'findings_count': 2,
                'critical_findings': 0,
                'high_findings': 1,
                'medium_findings': 1
            }
        except Exception as e:
            logger.error(f"Redteam evidence collection error: {e}")
            return {}
    
    def _collect_attestation_data(self, system_id: str, version: str) -> Dict[str, Any]:
        """Collect attestation data"""
        try:
            attestation_data = {
                'system_id': system_id,
                'version': version,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'deployment_status': 'successful',
                    'security_validation': 'passed',
                    'compliance_check': 'passed',
                    'performance_metrics': 'acceptable'
                }
            }
            
            # Add deployment evidence (P20/P38/P46)
            attestation_data['deployment'] = self._collect_deployment_evidence(system_id, version)
            
            # Add access hub evidence (P33)
            attestation_data['access_hub'] = self._collect_access_hub_evidence(system_id, version)
            
            return attestation_data
            
        except Exception as e:
            logger.error(f"Attestation data collection error: {e}")
            return {'error': str(e)}
    
    def _collect_deployment_evidence(self, system_id: str, version: str) -> Dict[str, Any]:
        """Collect deployment evidence (P20/P38/P46)"""
        try:
            # In reality, this would call deployment services
            # For now, simulate the data
            return {
                'deployment_id': f"deploy_{uuid.uuid4().hex[:8]}",
                'environment': 'production',
                'region': 'us-east-1',
                'deployment_time': datetime.now().isoformat(),
                'rollback_available': True
            }
        except Exception as e:
            logger.error(f"Deployment evidence collection error: {e}")
            return {}
    
    def _collect_access_hub_evidence(self, system_id: str, version: str) -> Dict[str, Any]:
        """Collect access hub evidence (P33)"""
        try:
            # In reality, this would call P33 Access Hub service
            # For now, simulate the data
            return {
                'access_controls': 'enabled',
                'user_count': 25,
                'role_count': 8,
                'last_access_review': datetime.now().isoformat(),
                'mfa_enabled': True
            }
        except Exception as e:
            logger.error(f"Access hub evidence collection error: {e}")
            return {}
    
    def _create_evidence_bundle(self, packet_id: str, evidence_data: Dict[str, Any]) -> str:
        """Create signed evidence bundle"""
        try:
            # In reality, this would create a signed, timestamped bundle
            # For now, create a simple file
            bundle_dir = Path(config.EVIDENCE_BUNDLE_PATH)
            bundle_dir.mkdir(exist_ok=True)
            
            bundle_file = bundle_dir / f"evidence_{packet_id}.json"
            bundle_content = {
                'id': packet_id,
                'created_at': datetime.now().isoformat(),
                'evidence': evidence_data,
                'signature': self._sign_evidence(evidence_data)
            }
            
            bundle_file.write_text(json.dumps(bundle_content, indent=2))
            
            return str(bundle_file)
            
        except Exception as e:
            logger.error(f"Evidence bundle creation error: {e}")
            return f"error://{packet_id}"
    
    def _create_attestation_bundle(self, attestation_id: str, attestation_data: Dict[str, Any]) -> str:
        """Create signed attestation bundle"""
        try:
            # In reality, this would create a signed, timestamped bundle
            # For now, create a simple file
            bundle_dir = Path(config.ATTESTATION_BUNDLE_PATH)
            bundle_dir.mkdir(exist_ok=True)
            
            bundle_file = bundle_dir / f"attestation_{attestation_id}.json"
            bundle_content = {
                'id': attestation_id,
                'created_at': datetime.now().isoformat(),
                'attestation': attestation_data,
                'signature': self._sign_attestation(attestation_data)
            }
            
            bundle_file.write_text(json.dumps(bundle_content, indent=2))
            
            return str(bundle_file)
            
        except Exception as e:
            logger.error(f"Attestation bundle creation error: {e}")
            return f"error://{attestation_id}"
    
    def _calculate_bundle_hash(self, bundle_uri: str) -> str:
        """Calculate hash of bundle"""
        try:
            if bundle_uri.startswith('error://'):
                return "error_hash"
            
            bundle_file = Path(bundle_uri)
            if bundle_file.exists():
                content = bundle_file.read_bytes()
                return hashlib.sha256(content).hexdigest()
            else:
                return "missing_hash"
                
        except Exception as e:
            logger.error(f"Bundle hash calculation error: {e}")
            return "error_hash"
    
    def _sign_evidence(self, evidence_data: Dict[str, Any]) -> str:
        """Sign evidence data"""
        try:
            # In reality, this would use proper cryptographic signing
            # For now, create a simple hash-based signature
            content = json.dumps(evidence_data, sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Evidence signing error: {e}")
            return "error_signature"
    
    def _sign_attestation(self, attestation_data: Dict[str, Any]) -> str:
        """Sign attestation data"""
        try:
            # In reality, this would use proper cryptographic signing
            # For now, create a simple hash-based signature
            content = json.dumps(attestation_data, sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Attestation signing error: {e}")
            return "error_signature"

# Initialize service
compliance_evidence_service = ComplianceEvidenceService()

# API Routes
@compliance_bp.route('/evidence', methods=['POST'])
@cross_origin()
@flag_required('compliance_evidence')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def generate_evidence_packet():
    """Generate evidence packet for compliance audit"""
    try:
        data = request.get_json()
        scope = data.get('scope')
        system_id = data.get('system_id')
        
        if not scope:
            return jsonify({'error': 'scope is required'}), 400
        
        try:
            evidence_scope = EvidenceScope(scope)
        except ValueError:
            return jsonify({'error': 'Invalid scope'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        evidence_packet = compliance_evidence_service.generate_evidence_packet(
            tenant_id=tenant_id,
            scope=evidence_scope,
            system_id=system_id
        )
        
        if not evidence_packet:
            return jsonify({'error': 'Failed to generate evidence packet'}), 500
        
        return jsonify({
            'success': True,
            'packet_id': evidence_packet.id,
            'download_url': evidence_packet.bundle_uri,
            'evidence_packet': asdict(evidence_packet)
        })
        
    except Exception as e:
        logger.error(f"Generate evidence packet error: {e}")
        return jsonify({'error': str(e)}), 500

@compliance_bp.route('/attestations/generate', methods=['POST'])
@cross_origin()
@flag_required('compliance_evidence')
@require_tenant_context
@cost_accounted("api", "operation")
def generate_attestation():
    """Generate deployment attestation bundle"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        version = data.get('version')
        
        if not system_id:
            return jsonify({'error': 'system_id is required'}), 400
        
        attestation = compliance_evidence_service.generate_attestation(
            system_id=system_id,
            version=version
        )
        
        if not attestation:
            return jsonify({'error': 'Failed to generate attestation'}), 500
        
        return jsonify({
            'success': True,
            'attestation_id': attestation.id,
            'download_url': attestation.bundle_uri,
            'attestation': asdict(attestation)
        })
        
    except Exception as e:
        logger.error(f"Generate attestation error: {e}")
        return jsonify({'error': str(e)}), 500

@compliance_bp.route('/attestations/<attestation_id>', methods=['GET'])
@cross_origin()
@flag_required('compliance_evidence')
@require_tenant_context
def get_attestation(attestation_id):
    """Get attestation by ID"""
    try:
        attestation = compliance_evidence_service.get_attestation(attestation_id)
        
        if not attestation:
            return jsonify({'error': 'Attestation not found'}), 404
        
        return jsonify({
            'success': True,
            'attestation': asdict(attestation)
        })
        
    except Exception as e:
        logger.error(f"Get attestation error: {e}")
        return jsonify({'error': str(e)}), 500
