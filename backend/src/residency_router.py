#!/usr/bin/env python3
"""
P58: Data Residency & Sovereign Data Mesh
Enforce region-aware storage/processing (e.g., EU-only), with routing and proofs.
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
residency_bp = Blueprint('residency', __name__, url_prefix='/api/residency')

# Data Models
class ResidencyAction(Enum):
    STORAGE_WRITE = "storage_write"
    PROCESSOR_BLOCK = "processor_block"
    REGION_VIOLATION = "region_violation"
    VALIDATION = "validation"

@dataclass
class ResidencyPolicy:
    id: str
    tenant_id: str
    name: str
    regions_allowed: List[str]
    storage_classes: Dict[str, Any]
    processor_allowlist: List[str]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class ResidencyEvent:
    id: str
    tenant_id: str
    system_id: Optional[str]
    object_uri: str
    region: str
    action: ResidencyAction
    timestamp: datetime
    meta_json: Dict[str, Any]

class ResidencyRouter:
    """Service for data residency routing and enforcement"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
        self.region_routing_cache: Dict[str, str] = {}
    
    def _init_database(self):
        """Initialize residency database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create residency_policies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS residency_policies (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        regions_allowed TEXT NOT NULL,
                        storage_classes TEXT NOT NULL,
                        processor_allowlist TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create residency_events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS residency_events (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT,
                        object_uri TEXT NOT NULL,
                        region TEXT NOT NULL,
                        action TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        meta_json TEXT
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_residency_policies_tenant_id 
                    ON residency_policies (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_residency_events_tenant_id 
                    ON residency_events (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_residency_events_timestamp 
                    ON residency_events (timestamp)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_residency_events_system_id 
                    ON residency_events (system_id)
                ''')
                
                conn.commit()
                logger.info("Residency database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize residency database: {e}")
    
    def create_residency_policy(self, tenant_id: str, name: str, regions_allowed: List[str],
                               storage_classes: Dict[str, Any], processor_allowlist: List[str]) -> Optional[ResidencyPolicy]:
        """Create a residency policy"""
        try:
            policy_id = str(uuid.uuid4())
            now = datetime.now()
            
            residency_policy = ResidencyPolicy(
                id=policy_id,
                tenant_id=tenant_id,
                name=name,
                regions_allowed=regions_allowed,
                storage_classes=storage_classes,
                processor_allowlist=processor_allowlist,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO residency_policies 
                    (id, tenant_id, name, regions_allowed, storage_classes, processor_allowlist, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    residency_policy.id,
                    residency_policy.tenant_id,
                    residency_policy.name,
                    json.dumps(residency_policy.regions_allowed),
                    json.dumps(residency_policy.storage_classes),
                    json.dumps(residency_policy.processor_allowlist),
                    residency_policy.created_at.isoformat(),
                    json.dumps(residency_policy.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created residency policy: {policy_id}")
            return residency_policy
            
        except Exception as e:
            logger.error(f"Failed to create residency policy: {e}")
            return None
    
    def get_residency_policy(self, tenant_id: str) -> Optional[ResidencyPolicy]:
        """Get current residency policy for tenant"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, name, regions_allowed, storage_classes, processor_allowlist, created_at, metadata
                    FROM residency_policies 
                    WHERE tenant_id = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (tenant_id,))
                
                row = cursor.fetchone()
                if row:
                    return ResidencyPolicy(
                        id=row[0],
                        tenant_id=row[1],
                        name=row[2],
                        regions_allowed=json.loads(row[3]),
                        storage_classes=json.loads(row[4]),
                        processor_allowlist=json.loads(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get residency policy: {e}")
            return None
    
    def get_residency_events(self, tenant_id: str, since: Optional[str] = None, 
                           system_id: Optional[str] = None) -> List[ResidencyEvent]:
        """Get residency events audit stream"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, tenant_id, system_id, object_uri, region, action, timestamp, meta_json
                    FROM residency_events 
                    WHERE tenant_id = ?
                '''
                params = [tenant_id]
                
                if since:
                    query += ' AND timestamp >= ?'
                    params.append(since)
                
                if system_id:
                    query += ' AND system_id = ?'
                    params.append(system_id)
                
                query += ' ORDER BY timestamp DESC LIMIT 100'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    events.append(ResidencyEvent(
                        id=row[0],
                        tenant_id=row[1],
                        system_id=row[2],
                        object_uri=row[3],
                        region=row[4],
                        action=ResidencyAction(row[5]),
                        timestamp=datetime.fromisoformat(row[6]),
                        meta_json=json.loads(row[7]) if row[7] else {}
                    ))
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to get residency events: {e}")
            return []
    
    def validate_residency(self, tenant_id: str, system_id: Optional[str] = None, 
                          object_uri: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
        """Validate residency compliance"""
        try:
            policy = self.get_residency_policy(tenant_id)
            if not policy:
                return {
                    'ok': True,
                    'message': 'No residency policy configured',
                    'violations': []
                }
            
            violations = []
            
            # Check region compliance
            if region and region not in policy.regions_allowed:
                violations.append({
                    'type': 'region_violation',
                    'message': f'Region {region} not allowed by policy',
                    'allowed_regions': policy.regions_allowed,
                    'actual_region': region
                })
                
                # Record violation event
                self._record_event(tenant_id, system_id, object_uri or 'unknown', region, 
                                 ResidencyAction.REGION_VIOLATION, {
                                     'policy_id': policy.id,
                                     'allowed_regions': policy.regions_allowed
                                 })
                
                metrics.counter('sbh_residency_violations_total').inc()
            
            # Check processor compliance (if applicable)
            if system_id:
                # In reality, this would check the system's processor configuration
                # For now, simulate the check
                pass
            
            # Record validation event
            self._record_event(tenant_id, system_id, object_uri or 'unknown', region or 'unknown',
                             ResidencyAction.VALIDATION, {
                                 'policy_id': policy.id,
                                 'violations_count': len(violations)
                             })
            
            return {
                'ok': len(violations) == 0,
                'policy_id': policy.id,
                'violations': violations
            }
            
        except Exception as e:
            logger.error(f"Failed to validate residency: {e}")
            return {
                'ok': False,
                'error': str(e),
                'violations': []
            }
    
    def route_storage_write(self, tenant_id: str, object_uri: str, 
                           preferred_region: Optional[str] = None) -> Dict[str, Any]:
        """Route storage write to appropriate region"""
        try:
            policy = self.get_residency_policy(tenant_id)
            if not policy:
                # Use default regions if no policy
                allowed_regions = config.DEFAULT_RESIDENCY_REGIONS
            else:
                allowed_regions = policy.regions_allowed
            
            # Determine target region
            target_region = self._determine_target_region(preferred_region, allowed_regions)
            
            # Record storage write event
            self._record_event(tenant_id, None, object_uri, target_region,
                             ResidencyAction.STORAGE_WRITE, {
                                 'preferred_region': preferred_region,
                                 'allowed_regions': allowed_regions
                             })
            
            metrics.counter('sbh_residency_writes_total', {'region': target_region}).inc()
            
            return {
                'target_region': target_region,
                'allowed_regions': allowed_regions,
                'routing_reason': 'policy_compliance'
            }
            
        except Exception as e:
            logger.error(f"Failed to route storage write: {e}")
            return {
                'target_region': 'us',  # fallback
                'error': str(e)
            }
    
    def block_processor(self, tenant_id: str, processor_region: str, 
                       system_id: Optional[str] = None, object_uri: Optional[str] = None) -> bool:
        """Block processor in non-allowed region"""
        try:
            policy = self.get_residency_policy(tenant_id)
            if not policy:
                return False  # No policy means no blocking
            
            # Check if processor region is allowed
            if processor_region not in policy.processor_allowlist:
                # Record block event
                self._record_event(tenant_id, system_id, object_uri or 'unknown', processor_region,
                                 ResidencyAction.PROCESSOR_BLOCK, {
                                     'processor_region': processor_region,
                                     'allowed_processors': policy.processor_allowlist
                                 })
                
                metrics.counter('sbh_residency_blocks_total').inc()
                
                logger.warning(f"Blocked processor in region {processor_region} for tenant {tenant_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to block processor: {e}")
            return False
    
    def _determine_target_region(self, preferred_region: Optional[str], allowed_regions: List[str]) -> str:
        """Determine target region based on preferences and policy"""
        if preferred_region and preferred_region in allowed_regions:
            return preferred_region
        
        # Use first allowed region as default
        return allowed_regions[0] if allowed_regions else 'us'
    
    def _record_event(self, tenant_id: str, system_id: Optional[str], object_uri: str, 
                     region: str, action: ResidencyAction, meta_json: Dict[str, Any]):
        """Record residency event"""
        try:
            event_id = str(uuid.uuid4())
            now = datetime.now()
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO residency_events 
                    (id, tenant_id, system_id, object_uri, region, action, timestamp, meta_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    tenant_id,
                    system_id,
                    object_uri,
                    region,
                    action.value,
                    now.isoformat(),
                    json.dumps(meta_json)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to record residency event: {e}")

# Initialize service
residency_router = ResidencyRouter()

# API Routes
@residency_bp.route('/policy', methods=['POST'])
@cross_origin()
@flag_required('data_residency')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_residency_policy():
    """Create a residency policy"""
    try:
        data = request.get_json()
        name = data.get('name')
        regions_allowed = data.get('regions_allowed', [])
        storage_classes = data.get('storage_classes', {})
        processor_allowlist = data.get('processor_allowlist', [])
        
        if not name:
            return jsonify({'error': 'name is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        residency_policy = residency_router.create_residency_policy(
            tenant_id=tenant_id,
            name=name,
            regions_allowed=regions_allowed,
            storage_classes=storage_classes,
            processor_allowlist=processor_allowlist
        )
        
        if not residency_policy:
            return jsonify({'error': 'Failed to create residency policy'}), 500
        
        return jsonify({
            'success': True,
            'policy_id': residency_policy.id,
            'residency_policy': asdict(residency_policy)
        })
        
    except Exception as e:
        logger.error(f"Create residency policy error: {e}")
        return jsonify({'error': str(e)}), 500

@residency_bp.route('/policy', methods=['GET'])
@cross_origin()
@flag_required('data_residency')
@require_tenant_context
def get_residency_policy():
    """Get current residency policy"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        residency_policy = residency_router.get_residency_policy(tenant_id)
        
        if not residency_policy:
            return jsonify({
                'success': True,
                'policy': None,
                'message': 'No residency policy configured'
            })
        
        return jsonify({
            'success': True,
            'residency_policy': asdict(residency_policy)
        })
        
    except Exception as e:
        logger.error(f"Get residency policy error: {e}")
        return jsonify({'error': str(e)}), 500

@residency_bp.route('/events', methods=['GET'])
@cross_origin()
@flag_required('data_residency')
@require_tenant_context
def get_residency_events():
    """Get residency events audit stream"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        since = request.args.get('since')
        system_id = request.args.get('system_id')
        
        events = residency_router.get_residency_events(
            tenant_id=tenant_id,
            since=since,
            system_id=system_id
        )
        
        return jsonify({
            'success': True,
            'events': [asdict(event) for event in events]
        })
        
    except Exception as e:
        logger.error(f"Get residency events error: {e}")
        return jsonify({'error': str(e)}), 500

@residency_bp.route('/validate', methods=['POST'])
@cross_origin()
@flag_required('data_residency')
@require_tenant_context
@cost_accounted("api", "operation")
def validate_residency():
    """Validate residency compliance"""
    try:
        data = request.get_json()
        system_id = data.get('system_id')
        object_uri = data.get('object_uri')
        region = data.get('region')
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        result = residency_router.validate_residency(
            tenant_id=tenant_id,
            system_id=system_id,
            object_uri=object_uri,
            region=region
        )
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Validate residency error: {e}")
        return jsonify({'error': str(e)}), 500
