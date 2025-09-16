#!/usr/bin/env python3
"""
P36: Data Refinery ("Ripening") & Managed Data Layer
Ingest, clean, validate, enrich, label, and serve high-quality datasets for every system.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import hashlib
import csv
import tempfile
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
data_refinery_bp = Blueprint('data_refinery', __name__, url_prefix='/api/data')

# Data Models
class DatasetStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"

class RunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class QualityRuleType(Enum):
    VALIDATION = "validation"
    ANOMALY_DETECTION = "anomaly_detection"
    DEDUPLICATION = "deduplication"
    PII_DETECTION = "pii_detection"

@dataclass
class Dataset:
    id: str
    tenant_id: str
    name: str
    version: str
    schema_json: Dict[str, Any]
    retention_days: int
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class DatasetRun:
    id: str
    dataset_id: str
    status: RunStatus
    source_uri: str
    bytes_in: int
    rows_in: int
    rows_out: int
    errors_json: List[Dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime]

@dataclass
class QualityReport:
    id: str
    dataset_id: str
    run_id: str
    metrics_json: Dict[str, Any]
    violations_json: List[Dict[str, Any]]
    created_at: datetime

@dataclass
class DatasetAccessKey:
    id: str
    dataset_id: str
    key_hash: str
    scope: str
    expires_at: datetime
    created_at: datetime

class DataRefineryService:
    """Service for data ingestion, quality, and management"""
    
    def __init__(self):
        self._init_database()
        self.quality_rules = self._load_quality_rules()
    
    def _init_database(self):
        """Initialize data refinery database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create datasets table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS datasets (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        version TEXT NOT NULL,
                        schema_json TEXT NOT NULL,
                        retention_days INTEGER NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create dataset_runs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS dataset_runs (
                        id TEXT PRIMARY KEY,
                        dataset_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        source_uri TEXT NOT NULL,
                        bytes_in INTEGER DEFAULT 0,
                        rows_in INTEGER DEFAULT 0,
                        rows_out INTEGER DEFAULT 0,
                        errors_json TEXT,
                        created_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
                    )
                ''')
                
                # Create quality_reports table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS quality_reports (
                        id TEXT PRIMARY KEY,
                        dataset_id TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        violations_json TEXT,
                        created_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (dataset_id) REFERENCES datasets (id),
                        FOREIGN KEY (run_id) REFERENCES dataset_runs (id)
                    )
                ''')
                
                # Create dataset_access_keys table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS dataset_access_keys (
                        id TEXT PRIMARY KEY,
                        dataset_id TEXT NOT NULL,
                        key_hash TEXT NOT NULL UNIQUE,
                        scope TEXT NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        FOREIGN KEY (dataset_id) REFERENCES datasets (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Data refinery database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize data refinery database: {e}")
    
    def _load_quality_rules(self) -> Dict[str, Any]:
        """Load quality rules configuration"""
        return {
            'validation': {
                'required_fields': True,
                'data_types': True,
                'value_ranges': True
            },
            'anomaly_detection': {
                'outlier_threshold': 3.0,
                'missing_data_threshold': 0.1
            },
            'deduplication': {
                'enabled': True,
                'key_fields': ['id', 'email']
            },
            'pii_detection': {
                'enabled': True,
                'patterns': {
                    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                    'ssn': r'\b\d{3}-\d{2}-\d{4}\b'
                }
            }
        }
    
    def create_dataset(self, tenant_id: str, name: str, schema_json: Dict[str, Any],
                      retention_days: int = 30) -> Optional[Dataset]:
        """Create a new dataset"""
        try:
            dataset_id = f"dataset_{int(time.time())}"
            version = "1.0.0"
            now = datetime.now()
            
            dataset = Dataset(
                id=dataset_id,
                tenant_id=tenant_id,
                name=name,
                version=version,
                schema_json=schema_json,
                retention_days=retention_days,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO datasets 
                    (id, tenant_id, name, version, schema_json, retention_days, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dataset.id,
                    dataset.tenant_id,
                    dataset.name,
                    dataset.version,
                    json.dumps(dataset.schema_json),
                    dataset.retention_days,
                    dataset.created_at.isoformat(),
                    json.dumps(dataset.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created dataset: {dataset_id}")
            return dataset
            
        except Exception as e:
            logger.error(f"Failed to create dataset: {e}")
            return None
    
    def ingest_data(self, dataset_id: str, source_uri: str, tenant_id: str) -> Optional[DatasetRun]:
        """Start data ingestion process"""
        try:
            run_id = f"run_{int(time.time())}"
            now = datetime.now()
            
            run = DatasetRun(
                id=run_id,
                dataset_id=dataset_id,
                status=RunStatus.PENDING,
                source_uri=source_uri,
                bytes_in=0,
                rows_in=0,
                rows_out=0,
                errors_json=[],
                created_at=now,
                completed_at=None
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO dataset_runs 
                    (id, dataset_id, status, source_uri, bytes_in, rows_in, rows_out, errors_json, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    run.id,
                    run.dataset_id,
                    run.status.value,
                    run.source_uri,
                    run.bytes_in,
                    run.rows_in,
                    run.rows_out,
                    json.dumps(run.errors_json),
                    run.created_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None
                ))
                conn.commit()
            
            # Start processing in background
            self._process_ingestion(run_id, dataset_id, source_uri, tenant_id)
            
            logger.info(f"Started ingestion run: {run_id}")
            return run
            
        except Exception as e:
            logger.error(f"Failed to start ingestion: {e}")
            return None
    
    def _process_ingestion(self, run_id: str, dataset_id: str, source_uri: str, tenant_id: str):
        """Process data ingestion in background"""
        try:
            # Update status to running
            self._update_run_status(run_id, RunStatus.RUNNING)
            
            # Process based on source type
            if source_uri.startswith('file://'):
                file_path = source_uri.replace('file://', '')
                success = self._process_file_ingestion(run_id, file_path, tenant_id)
            elif source_uri.startswith('s3://'):
                success = self._process_s3_ingestion(run_id, source_uri, tenant_id)
            else:
                success = self._process_generic_ingestion(run_id, source_uri, tenant_id)
            
            if success:
                self._update_run_status(run_id, RunStatus.COMPLETED)
                # Generate quality report
                self._generate_quality_report(run_id, dataset_id)
            else:
                self._update_run_status(run_id, RunStatus.FAILED)
            
            # Update metrics
            metrics.increment_counter('sbh_data_ingest_bytes_total', {'tenant_id': tenant_id})
            
        except Exception as e:
            logger.error(f"Processing ingestion failed: {e}")
            self._update_run_status(run_id, RunStatus.FAILED)
    
    def _process_file_ingestion(self, run_id: str, file_path: str, tenant_id: str) -> bool:
        """Process file-based ingestion"""
        try:
            if not os.path.exists(file_path):
                return False
            
            file_size = os.path.getsize(file_path)
            
            # Read and process file
            if file_path.endswith('.csv'):
                rows = self._process_csv_file(file_path)
            elif file_path.endswith('.json'):
                rows = self._process_json_file(file_path)
            else:
                rows = self._process_text_file(file_path)
            
            # Update run statistics
            self._update_run_stats(run_id, file_size, len(rows), len(rows))
            
            return True
            
        except Exception as e:
            logger.error(f"File ingestion failed: {e}")
            return False
    
    def _process_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process CSV file"""
        rows = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        except Exception as e:
            logger.error(f"CSV processing failed: {e}")
        return rows
    
    def _process_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    return [data]
        except Exception as e:
            logger.error(f"JSON processing failed: {e}")
            return []
    
    def _process_text_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return [{'content': content}]
        except Exception as e:
            logger.error(f"Text processing failed: {e}")
            return []
    
    def _process_s3_ingestion(self, run_id: str, s3_uri: str, tenant_id: str) -> bool:
        """Process S3-based ingestion (stub)"""
        # TODO: Implement S3 ingestion
        logger.info(f"S3 ingestion stub for: {s3_uri}")
        return True
    
    def _process_generic_ingestion(self, run_id: str, source_uri: str, tenant_id: str) -> bool:
        """Process generic ingestion (stub)"""
        # TODO: Implement generic ingestion
        logger.info(f"Generic ingestion stub for: {source_uri}")
        return True
    
    def _update_run_status(self, run_id: str, status: RunStatus):
        """Update run status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE dataset_runs 
                    SET status = ?, completed_at = ?
                    WHERE id = ?
                ''', (
                    status.value,
                    datetime.now().isoformat() if status in [RunStatus.COMPLETED, RunStatus.FAILED] else None,
                    run_id
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update run status: {e}")
    
    def _update_run_stats(self, run_id: str, bytes_in: int, rows_in: int, rows_out: int):
        """Update run statistics"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE dataset_runs 
                    SET bytes_in = ?, rows_in = ?, rows_out = ?
                    WHERE id = ?
                ''', (bytes_in, rows_in, rows_out, run_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update run stats: {e}")
    
    def _generate_quality_report(self, run_id: str, dataset_id: str):
        """Generate quality report for ingestion run"""
        try:
            report_id = f"report_{int(time.time())}"
            now = datetime.now()
            
            # Run quality checks
            metrics_data = self._run_quality_checks(dataset_id, run_id)
            violations = self._detect_violations(dataset_id, run_id)
            
            report = QualityReport(
                id=report_id,
                dataset_id=dataset_id,
                run_id=run_id,
                metrics_json=metrics_data,
                violations_json=violations,
                created_at=now
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO quality_reports 
                    (id, dataset_id, run_id, metrics_json, violations_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    report.id,
                    report.dataset_id,
                    report.run_id,
                    json.dumps(report.metrics_json),
                    json.dumps(report.violations_json),
                    report.created_at.isoformat()
                ))
                conn.commit()
            
            logger.info(f"Generated quality report: {report_id}")
            
        except Exception as e:
            logger.error(f"Failed to generate quality report: {e}")
    
    def _run_quality_checks(self, dataset_id: str, run_id: str) -> Dict[str, Any]:
        """Run quality checks on dataset"""
        # TODO: Implement actual quality checks
        return {
            'total_rows': 1000,
            'valid_rows': 950,
            'invalid_rows': 50,
            'completeness': 0.95,
            'accuracy': 0.92,
            'consistency': 0.88
        }
    
    def _detect_violations(self, dataset_id: str, run_id: str) -> List[Dict[str, Any]]:
        """Detect quality violations"""
        # TODO: Implement actual violation detection
        violations = []
        
        # Mock violations
        if self.quality_rules['pii_detection']['enabled']:
            violations.append({
                'type': 'pii_detection',
                'field': 'email',
                'row': 123,
                'severity': 'high',
                'description': 'PII detected in email field'
            })
        
        return violations
    
    def get_dataset_schema(self, dataset_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset schema"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT schema_json FROM datasets 
                    WHERE id = ? AND tenant_id = ?
                ''', (dataset_id, tenant_id))
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
                return None
                
        except Exception as e:
            logger.error(f"Failed to get dataset schema: {e}")
            return None
    
    def create_access_key(self, dataset_id: str, scope: str, 
                         expires_in_days: int = 30) -> Optional[DatasetAccessKey]:
        """Create access key for dataset"""
        try:
            key_id = f"key_{int(time.time())}"
            now = datetime.now()
            expires_at = now + timedelta(days=expires_in_days)
            
            # Generate access key
            access_key = f"sbh_{uuid.uuid4().hex}"
            key_hash = hashlib.sha256(access_key.encode()).hexdigest()
            
            access_key_obj = DatasetAccessKey(
                id=key_id,
                dataset_id=dataset_id,
                key_hash=key_hash,
                scope=scope,
                expires_at=expires_at,
                created_at=now
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO dataset_access_keys 
                    (id, dataset_id, key_hash, scope, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    access_key_obj.id,
                    access_key_obj.dataset_id,
                    access_key_obj.key_hash,
                    access_key_obj.scope,
                    access_key_obj.expires_at.isoformat(),
                    access_key_obj.created_at.isoformat()
                ))
                conn.commit()
            
            # Return the actual key (not hash) for the user
            access_key_obj.key_hash = access_key
            
            logger.info(f"Created access key: {key_id}")
            return access_key_obj
            
        except Exception as e:
            logger.error(f"Failed to create access key: {e}")
            return None
    
    def validate_access_key(self, access_key: str, dataset_id: str) -> bool:
        """Validate access key"""
        try:
            key_hash = hashlib.sha256(access_key.encode()).hexdigest()
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id FROM dataset_access_keys 
                    WHERE key_hash = ? AND dataset_id = ? AND expires_at > ?
                ''', (key_hash, dataset_id, datetime.now().isoformat()))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Failed to validate access key: {e}")
            return False
    
    def export_dataset(self, dataset_id: str, format_type: str = 'csv', 
                      access_key: str = None) -> Optional[str]:
        """Export dataset in specified format"""
        try:
            # Validate access if key provided
            if access_key and not self.validate_access_key(access_key, dataset_id):
                return None
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                mode='w', 
                suffix=f'.{format_type}', 
                delete=False
            )
            
            # Generate mock data based on format
            if format_type == 'csv':
                self._export_csv(temp_file.name, dataset_id)
            elif format_type == 'json':
                self._export_json(temp_file.name, dataset_id)
            else:
                return None
            
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Failed to export dataset: {e}")
            return None
    
    def _export_csv(self, file_path: str, dataset_id: str):
        """Export dataset as CSV"""
        # TODO: Implement actual CSV export
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'email', 'created_at'])
            writer.writerow(['1', 'John Doe', 'john@example.com', '2024-01-01'])
            writer.writerow(['2', 'Jane Smith', 'jane@example.com', '2024-01-02'])
    
    def _export_json(self, file_path: str, dataset_id: str):
        """Export dataset as JSON"""
        # TODO: Implement actual JSON export
        data = [
            {'id': '1', 'name': 'John Doe', 'email': 'john@example.com', 'created_at': '2024-01-01'},
            {'id': '2', 'name': 'Jane Smith', 'email': 'jane@example.com', 'created_at': '2024-01-02'}
        ]
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

# Initialize service
data_refinery_service = DataRefineryService()

# API Routes
@data_refinery_bp.route('/ingest', methods=['POST'])
@cross_origin()
@flag_required('data_refinery')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def ingest_data():
    """Start data ingestion process"""
    try:
        data = request.get_json()
        dataset_id = data.get('dataset_id')
        source_uri = data.get('source_uri')
        
        if not all([dataset_id, source_uri]):
            return jsonify({'error': 'dataset_id and source_uri are required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        run = data_refinery_service.ingest_data(dataset_id, source_uri, tenant_id)
        
        if not run:
            return jsonify({'error': 'Failed to start ingestion'}), 500
        
        return jsonify({
            'success': True,
            'run': asdict(run)
        })
        
    except Exception as e:
        logger.error(f"Ingest data error: {e}")
        return jsonify({'error': str(e)}), 500

@data_refinery_bp.route('/runs', methods=['GET'])
@cross_origin()
@flag_required('data_refinery')
@require_tenant_context
def get_runs():
    """Get dataset runs"""
    try:
        dataset_id = request.args.get('dataset_id')
        
        if not dataset_id:
            return jsonify({'error': 'dataset_id is required'}), 400
        
        # TODO: Implement get runs
        runs = []
        
        return jsonify({
            'success': True,
            'runs': runs
        })
        
    except Exception as e:
        logger.error(f"Get runs error: {e}")
        return jsonify({'error': str(e)}), 500

@data_refinery_bp.route('/schema/<dataset_id>', methods=['GET'])
@cross_origin()
@flag_required('data_refinery')
@require_tenant_context
def get_schema(dataset_id):
    """Get dataset schema"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        schema = data_refinery_service.get_dataset_schema(dataset_id, tenant_id)
        
        if not schema:
            return jsonify({'error': 'Schema not found'}), 404
        
        return jsonify({
            'success': True,
            'schema': schema
        })
        
    except Exception as e:
        logger.error(f"Get schema error: {e}")
        return jsonify({'error': str(e)}), 500

@data_refinery_bp.route('/quality/check/<dataset_id>', methods=['POST'])
@cross_origin()
@flag_required('data_refinery')
@require_tenant_context
@cost_accounted("api", "operation")
def check_quality(dataset_id):
    """Run ad-hoc quality checks"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        # Run quality checks
        metrics_data = data_refinery_service._run_quality_checks(dataset_id, 'adhoc')
        violations = data_refinery_service._detect_violations(dataset_id, 'adhoc')
        
        return jsonify({
            'success': True,
            'metrics': metrics_data,
            'violations': violations
        })
        
    except Exception as e:
        logger.error(f"Check quality error: {e}")
        return jsonify({'error': str(e)}), 500

@data_refinery_bp.route('/access-key/<dataset_id>', methods=['POST'])
@cross_origin()
@flag_required('data_refinery')
@require_tenant_context
@cost_accounted("api", "operation")
def create_access_key(dataset_id):
    """Create access key for dataset"""
    try:
        data = request.get_json()
        scope = data.get('scope', 'read')
        expires_in_days = data.get('expires_in_days', 30)
        
        access_key = data_refinery_service.create_access_key(
            dataset_id=dataset_id,
            scope=scope,
            expires_in_days=expires_in_days
        )
        
        if not access_key:
            return jsonify({'error': 'Failed to create access key'}), 500
        
        return jsonify({
            'success': True,
            'access_key': asdict(access_key)
        })
        
    except Exception as e:
        logger.error(f"Create access key error: {e}")
        return jsonify({'error': str(e)}), 500

@data_refinery_bp.route('/export/<dataset_id>', methods=['GET'])
@cross_origin()
@flag_required('data_refinery')
def export_dataset(dataset_id):
    """Export dataset"""
    try:
        format_type = request.args.get('format', 'csv')
        access_key = request.args.get('access_key')
        
        if format_type not in ['csv', 'json']:
            return jsonify({'error': 'Invalid format'}), 400
        
        file_path = data_refinery_service.export_dataset(
            dataset_id=dataset_id,
            format_type=format_type,
            access_key=access_key
        )
        
        if not file_path:
            return jsonify({'error': 'Failed to export dataset'}), 500
        
        # Update metrics
        metrics.increment_counter('sbh_dataset_export_total', {'format': format_type})
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"dataset_{dataset_id}.{format_type}"
        )
        
    except Exception as e:
        logger.error(f"Export dataset error: {e}")
        return jsonify({'error': str(e)}), 500
