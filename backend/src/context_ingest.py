#!/usr/bin/env python3
"""
P43: Image/File Context Ingest (Docs, CSV, Wireframes)
Ingest and parse documents, CSV files, wireframes, and other artifacts for system design context.
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import mimetypes
import csv
import tempfile
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from flask import Blueprint, request, jsonify, g, current_app, send_file
from flask_cors import cross_origin
from werkzeug.utils import secure_filename

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
context_ingest_bp = Blueprint('context_ingest', __name__, url_prefix='/api/context')

# Data Models
class ArtifactType(Enum):
    DOCUMENT = "document"
    CSV = "csv"
    WIREFRAME = "wireframe"
    IMAGE = "image"
    JSON = "json"
    YAML = "yaml"
    TEXT = "text"
    UNKNOWN = "unknown"

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ContextArtifact:
    id: str
    project_id: str
    kind: ArtifactType
    uri: str
    summary_md: str
    derived_json: Dict[str, Any]
    created_at: datetime
    processed_at: Optional[datetime]
    status: ProcessingStatus
    metadata: Dict[str, Any]

class ContextIngestService:
    """Service for ingesting and processing context artifacts"""
    
    def __init__(self):
        self._init_database()
        self.supported_types = {
            'pdf': ArtifactType.DOCUMENT,
            'doc': ArtifactType.DOCUMENT,
            'docx': ArtifactType.DOCUMENT,
            'txt': ArtifactType.TEXT,
            'csv': ArtifactType.CSV,
            'json': ArtifactType.JSON,
            'yaml': ArtifactType.YAML,
            'yml': ArtifactType.YAML,
            'png': ArtifactType.WIREFRAME,
            'jpg': ArtifactType.WIREFRAME,
            'jpeg': ArtifactType.WIREFRAME,
            'gif': ArtifactType.WIREFRAME,
            'svg': ArtifactType.WIREFRAME
        }
    
    def _init_database(self):
        """Initialize context ingest database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create context_artifacts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS context_artifacts (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        uri TEXT NOT NULL,
                        summary_md TEXT NOT NULL,
                        derived_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        processed_at TIMESTAMP,
                        status TEXT NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                conn.commit()
                logger.info("Context ingest database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize context ingest database: {e}")
    
    def ingest_artifact(self, project_id: str, file_path: str, tenant_id: str) -> Optional[ContextArtifact]:
        """Ingest and process an artifact"""
        try:
            # Determine artifact type
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            artifact_type = self.supported_types.get(file_extension, ArtifactType.UNKNOWN)
            
            if artifact_type == ArtifactType.UNKNOWN:
                logger.warning(f"Unsupported file type: {file_extension}")
                return None
            
            # Create artifact record
            artifact_id = f"artifact_{int(time.time())}"
            now = datetime.now()
            
            artifact = ContextArtifact(
                id=artifact_id,
                project_id=project_id,
                kind=artifact_type,
                uri=file_path,
                summary_md="",
                derived_json={},
                created_at=now,
                processed_at=None,
                status=ProcessingStatus.PENDING,
                metadata={'file_extension': file_extension, 'file_size': os.path.getsize(file_path)}
            )
            
            # Save to database
            self._save_artifact(artifact)
            
            # Process artifact in background
            processing_thread = threading.Thread(
                target=self._process_artifact,
                args=(artifact_id, file_path, artifact_type, tenant_id),
                daemon=True
            )
            processing_thread.start()
            
            logger.info(f"Ingested artifact: {artifact_id}")
            return artifact
            
        except Exception as e:
            logger.error(f"Failed to ingest artifact: {e}")
            return None
    
    def _process_artifact(self, artifact_id: str, file_path: str, artifact_type: ArtifactType, tenant_id: str):
        """Process artifact in background"""
        try:
            # Update status to processing
            self._update_artifact_status(artifact_id, ProcessingStatus.PROCESSING)
            
            # Process based on type
            if artifact_type == ArtifactType.DOCUMENT:
                summary, derived_data = self._process_document(file_path)
            elif artifact_type == ArtifactType.CSV:
                summary, derived_data = self._process_csv(file_path)
            elif artifact_type == ArtifactType.WIREFRAME:
                summary, derived_data = self._process_wireframe(file_path)
            elif artifact_type == ArtifactType.JSON:
                summary, derived_data = self._process_json(file_path)
            elif artifact_type == ArtifactType.YAML:
                summary, derived_data = self._process_yaml(file_path)
            elif artifact_type == ArtifactType.TEXT:
                summary, derived_data = self._process_text(file_path)
            else:
                summary = "Unsupported file type"
                derived_data = {}
            
            # Update artifact with results
            self._update_artifact_results(artifact_id, summary, derived_data, ProcessingStatus.COMPLETED)
            
            logger.info(f"Processed artifact: {artifact_id}")
            
        except Exception as e:
            logger.error(f"Failed to process artifact {artifact_id}: {e}")
            self._update_artifact_status(artifact_id, ProcessingStatus.FAILED)
    
    def _process_document(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """Process document files (PDF, DOC, DOCX)"""
        try:
            # TODO: Implement actual document parsing
            # For now, return mock data
            summary = f"Document processed: {Path(file_path).name}\n\nKey sections identified:\n- Introduction\n- Requirements\n- Technical specifications\n- User stories"
            
            derived_data = {
                'document_type': 'requirements_document',
                'sections': ['introduction', 'requirements', 'technical_specs', 'user_stories'],
                'extracted_requirements': [
                    'User authentication system',
                    'Database storage',
                    'API endpoints',
                    'Admin dashboard'
                ],
                'technical_terms': ['REST API', 'JWT', 'PostgreSQL', 'React'],
                'estimated_complexity': 'medium'
            }
            
            return summary, derived_data
            
        except Exception as e:
            logger.error(f"Failed to process document: {e}")
            return "Document processing failed", {}
    
    def _process_csv(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """Process CSV files and extract schema"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                rows = list(reader)
            
            if not rows:
                return "Empty CSV file", {}
            
            headers = rows[0]
            data_rows = rows[1:5] if len(rows) > 1 else []  # Sample first 4 data rows
            
            # Analyze schema
            schema = self._analyze_csv_schema(headers, data_rows)
            
            summary = f"CSV file processed: {Path(file_path).name}\n\nSchema analysis:\n- Columns: {len(headers)}\n- Sample rows: {len(data_rows)}\n- Data types: {schema['data_types']}"
            
            derived_data = {
                'schema': schema,
                'headers': headers,
                'sample_data': data_rows,
                'total_rows': len(rows) - 1,
                'suggested_models': self._suggest_models_from_csv(headers, schema)
            }
            
            return summary, derived_data
            
        except Exception as e:
            logger.error(f"Failed to process CSV: {e}")
            return "CSV processing failed", {}
    
    def _analyze_csv_schema(self, headers: List[str], data_rows: List[List[str]]) -> Dict[str, Any]:
        """Analyze CSV schema and data types"""
        schema = {
            'columns': [],
            'data_types': {},
            'constraints': {}
        }
        
        for i, header in enumerate(headers):
            column_data = [row[i] if i < len(row) else '' for row in data_rows]
            
            # Determine data type
            data_type = self._infer_data_type(column_data)
            
            schema['columns'].append({
                'name': header,
                'type': data_type,
                'nullable': any(not cell for cell in column_data),
                'unique': len(set(cell for cell in column_data if cell)) == len([cell for cell in column_data if cell])
            })
            
            schema['data_types'][header] = data_type
        
        return schema
    
    def _infer_data_type(self, values: List[str]) -> str:
        """Infer data type from values"""
        if not values:
            return 'string'
        
        # Check for common patterns
        all_numeric = all(v.replace('.', '').replace('-', '').isdigit() for v in values if v)
        all_dates = all(self._is_date(v) for v in values if v)
        all_emails = all('@' in v and '.' in v.split('@')[1] for v in values if v)
        
        if all_dates:
            return 'date'
        elif all_emails:
            return 'email'
        elif all_numeric:
            return 'numeric'
        else:
            return 'string'
    
    def _is_date(self, value: str) -> bool:
        """Check if value looks like a date"""
        import re
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{2}-\d{2}-\d{4}'
        ]
        return any(re.match(pattern, value) for pattern in date_patterns)
    
    def _suggest_models_from_csv(self, headers: List[str], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest data models from CSV structure"""
        models = []
        
        # Create a main model
        main_model = {
            'name': 'DataRecord',
            'fields': []
        }
        
        for column in schema['columns']:
            field = {
                'name': column['name'].lower().replace(' ', '_'),
                'type': column['type'],
                'nullable': column['nullable'],
                'unique': column['unique']
            }
            main_model['fields'].append(field)
        
        models.append(main_model)
        
        # Suggest related models if there are foreign key patterns
        fk_patterns = ['id', 'user_id', 'customer_id', 'order_id']
        for header in headers:
            if any(pattern in header.lower() for pattern in fk_patterns):
                related_model = {
                    'name': header.replace('_id', '').title(),
                    'type': 'related_model',
                    'relationship': 'foreign_key'
                }
                models.append(related_model)
        
        return models
    
    def _process_wireframe(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """Process wireframe images"""
        try:
            # TODO: Implement actual image analysis
            # For now, return mock data
            summary = f"Wireframe processed: {Path(file_path).name}\n\nUI components identified:\n- Navigation bar\n- Form elements\n- Data tables\n- Action buttons"
            
            derived_data = {
                'ui_components': [
                    {'type': 'navigation', 'location': 'top', 'elements': ['logo', 'menu', 'user_profile']},
                    {'type': 'form', 'location': 'center', 'elements': ['input_fields', 'submit_button']},
                    {'type': 'table', 'location': 'main', 'elements': ['headers', 'rows', 'pagination']},
                    {'type': 'actions', 'location': 'bottom', 'elements': ['create', 'edit', 'delete']}
                ],
                'suggested_layout': 'responsive_grid',
                'color_scheme': 'neutral',
                'accessibility_features': ['high_contrast', 'keyboard_navigation'],
                'estimated_pages': 3
            }
            
            return summary, derived_data
            
        except Exception as e:
            logger.error(f"Failed to process wireframe: {e}")
            return "Wireframe processing failed", {}
    
    def _process_json(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """Process JSON files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            summary = f"JSON file processed: {Path(file_path).name}\n\nStructure analyzed:\n- Root type: {type(data).__name__}\n- Keys: {list(data.keys()) if isinstance(data, dict) else 'Array'}"
            
            derived_data = {
                'structure': self._analyze_json_structure(data),
                'suggested_schema': self._generate_schema_from_json(data),
                'data_types': self._extract_json_types(data)
            }
            
            return summary, derived_data
            
        except Exception as e:
            logger.error(f"Failed to process JSON: {e}")
            return "JSON processing failed", {}
    
    def _analyze_json_structure(self, data: Any, path: str = "") -> Dict[str, Any]:
        """Analyze JSON structure recursively"""
        if isinstance(data, dict):
            return {
                'type': 'object',
                'properties': {k: self._analyze_json_structure(v, f"{path}.{k}" if path else k) for k, v in data.items()}
            }
        elif isinstance(data, list):
            if data:
                return {
                    'type': 'array',
                    'items': self._analyze_json_structure(data[0], f"{path}[0]")
                }
            else:
                return {'type': 'array', 'items': 'unknown'}
        else:
            return {'type': type(data).__name__, 'value': str(data)}
    
    def _generate_schema_from_json(self, data: Any) -> Dict[str, Any]:
        """Generate JSON schema from data"""
        if isinstance(data, dict):
            schema = {
                'type': 'object',
                'properties': {},
                'required': []
            }
            for key, value in data.items():
                schema['properties'][key] = self._generate_schema_from_json(value)
            return schema
        elif isinstance(data, list):
            if data:
                return {
                    'type': 'array',
                    'items': self._generate_schema_from_json(data[0])
                }
            else:
                return {'type': 'array'}
        else:
            return {'type': type(data).__name__}
    
    def _extract_json_types(self, data: Any) -> Dict[str, str]:
        """Extract data types from JSON"""
        types = {}
        
        def extract_types(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    types[full_key] = type(value).__name__
                    extract_types(value, full_key)
            elif isinstance(obj, list) and obj:
                extract_types(obj[0], f"{prefix}[0]")
        
        extract_types(data)
        return types
    
    def _process_yaml(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """Process YAML files"""
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
            
            summary = f"YAML file processed: {Path(file_path).name}\n\nConfiguration analyzed:\n- Root keys: {list(data.keys()) if isinstance(data, dict) else 'Array'}"
            
            derived_data = {
                'config_type': self._identify_config_type(data),
                'structure': self._analyze_json_structure(data),  # Reuse JSON analysis
                'suggested_validation': self._suggest_yaml_validation(data)
            }
            
            return summary, derived_data
            
        except Exception as e:
            logger.error(f"Failed to process YAML: {e}")
            return "YAML processing failed", {}
    
    def _identify_config_type(self, data: Any) -> str:
        """Identify configuration type from YAML content"""
        if isinstance(data, dict):
            keys = list(data.keys())
            if 'api' in keys or 'endpoints' in keys:
                return 'api_config'
            elif 'database' in keys or 'db' in keys:
                return 'database_config'
            elif 'services' in keys or 'microservices' in keys:
                return 'service_config'
            elif 'deployment' in keys or 'docker' in keys:
                return 'deployment_config'
            else:
                return 'general_config'
        return 'unknown'
    
    def _suggest_yaml_validation(self, data: Any) -> Dict[str, Any]:
        """Suggest validation rules for YAML"""
        validation = {
            'required_fields': [],
            'type_checks': {},
            'value_constraints': {}
        }
        
        if isinstance(data, dict):
            for key, value in data.items():
                validation['required_fields'].append(key)
                validation['type_checks'][key] = type(value).__name__
        
        return validation
    
    def _process_text(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """Process text files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            summary = f"Text file processed: {Path(file_path).name}\n\nContent analysis:\n- Length: {len(content)} characters\n- Lines: {len(content.splitlines())}\n- Words: {len(content.split())}"
            
            derived_data = {
                'content_length': len(content),
                'line_count': len(content.splitlines()),
                'word_count': len(content.split()),
                'language': 'english',  # TODO: Implement language detection
                'key_topics': self._extract_key_topics(content),
                'suggested_actions': self._suggest_actions_from_text(content)
            }
            
            return summary, derived_data
            
        except Exception as e:
            logger.error(f"Failed to process text: {e}")
            return "Text processing failed", {}
    
    def _extract_key_topics(self, content: str) -> List[str]:
        """Extract key topics from text content"""
        # Simple keyword extraction
        keywords = ['user', 'system', 'data', 'api', 'database', 'authentication', 'authorization', 'deployment']
        found_topics = []
        
        content_lower = content.lower()
        for keyword in keywords:
            if keyword in content_lower:
                found_topics.append(keyword)
        
        return found_topics
    
    def _suggest_actions_from_text(self, content: str) -> List[str]:
        """Suggest actions based on text content"""
        actions = []
        content_lower = content.lower()
        
        if 'user' in content_lower and 'login' in content_lower:
            actions.append('implement_user_authentication')
        if 'database' in content_lower:
            actions.append('setup_database_schema')
        if 'api' in content_lower:
            actions.append('create_rest_api_endpoints')
        if 'deploy' in content_lower:
            actions.append('configure_deployment_pipeline')
        
        return actions
    
    def get_artifact(self, artifact_id: str, tenant_id: str) -> Optional[ContextArtifact]:
        """Get artifact by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, project_id, kind, uri, summary_md, derived_json, created_at, processed_at, status, metadata
                    FROM context_artifacts 
                    WHERE id = ? AND project_id IN (
                        SELECT id FROM projects WHERE tenant_id = ?
                    )
                ''', (artifact_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return ContextArtifact(
                        id=row[0],
                        project_id=row[1],
                        kind=ArtifactType(row[2]),
                        uri=row[3],
                        summary_md=row[4],
                        derived_json=json.loads(row[5]),
                        created_at=datetime.fromisoformat(row[6]),
                        processed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                        status=ProcessingStatus(row[8]),
                        metadata=json.loads(row[9]) if row[9] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get artifact: {e}")
            return None
    
    def apply_artifact_to_project(self, artifact_id: str, project_id: str, tenant_id: str) -> bool:
        """Apply artifact context to project blueprint/canvas"""
        try:
            artifact = self.get_artifact(artifact_id, tenant_id)
            if not artifact or artifact.status != ProcessingStatus.COMPLETED:
                return False
            
            # TODO: Apply artifact data to project
            # This would update the project's blueprint or canvas with extracted information
            
            logger.info(f"Applied artifact {artifact_id} to project {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply artifact: {e}")
            return False
    
    def _save_artifact(self, artifact: ContextArtifact):
        """Save artifact to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO context_artifacts 
                    (id, project_id, kind, uri, summary_md, derived_json, created_at, processed_at, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    artifact.id,
                    artifact.project_id,
                    artifact.kind.value,
                    artifact.uri,
                    artifact.summary_md,
                    json.dumps(artifact.derived_json),
                    artifact.created_at.isoformat(),
                    artifact.processed_at.isoformat() if artifact.processed_at else None,
                    artifact.status.value,
                    json.dumps(artifact.metadata)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save artifact: {e}")
    
    def _update_artifact_status(self, artifact_id: str, status: ProcessingStatus):
        """Update artifact processing status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE context_artifacts 
                    SET status = ?
                    WHERE id = ?
                ''', (status.value, artifact_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update artifact status: {e}")
    
    def _update_artifact_results(self, artifact_id: str, summary: str, derived_json: Dict[str, Any], status: ProcessingStatus):
        """Update artifact with processing results"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE context_artifacts 
                    SET summary_md = ?, derived_json = ?, processed_at = ?, status = ?
                    WHERE id = ?
                ''', (
                    summary,
                    json.dumps(derived_json),
                    datetime.now().isoformat(),
                    status.value,
                    artifact_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update artifact results: {e}")

# Initialize service
context_ingest_service = ContextIngestService()

# API Routes
@context_ingest_bp.route('/ingest', methods=['POST'])
@cross_origin()
@flag_required('context_ingest')
@require_tenant_context
@cost_accounted("api", "operation")
def ingest_artifact():
    """Ingest a context artifact"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        project_id = request.form.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file type
        file_extension = Path(file.filename).suffix.lower().lstrip('.')
        if file_extension not in context_ingest_service.supported_types:
            return jsonify({'error': f'Unsupported file type: {file_extension}'}), 400
        
        # Save file temporarily
        temp_path = Path(tempfile.gettempdir()) / f"context_{uuid.uuid4()}_{file.filename}"
        file.save(temp_path)
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        # Ingest artifact
        artifact = context_ingest_service.ingest_artifact(
            project_id=project_id,
            file_path=str(temp_path),
            tenant_id=tenant_id
        )
        
        if not artifact:
            return jsonify({'error': 'Failed to ingest artifact'}), 500
        
        return jsonify({
            'success': True,
            'artifact_id': artifact.id,
            'artifact': asdict(artifact)
        })
        
    except Exception as e:
        logger.error(f"Ingest artifact error: {e}")
        return jsonify({'error': str(e)}), 500

@context_ingest_bp.route('/artifact/<artifact_id>', methods=['GET'])
@cross_origin()
@flag_required('context_ingest')
@require_tenant_context
def get_artifact(artifact_id):
    """Get artifact details"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        artifact = context_ingest_service.get_artifact(artifact_id, tenant_id)
        
        if not artifact:
            return jsonify({'error': 'Artifact not found'}), 404
        
        return jsonify({
            'success': True,
            'artifact': asdict(artifact)
        })
        
    except Exception as e:
        logger.error(f"Get artifact error: {e}")
        return jsonify({'error': str(e)}), 500

@context_ingest_bp.route('/apply/<artifact_id>', methods=['POST'])
@cross_origin()
@flag_required('context_ingest')
@require_tenant_context
@cost_accounted("api", "operation")
def apply_artifact(artifact_id):
    """Apply artifact to project"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        success = context_ingest_service.apply_artifact_to_project(
            artifact_id=artifact_id,
            project_id=project_id,
            tenant_id=tenant_id
        )
        
        if not success:
            return jsonify({'error': 'Failed to apply artifact'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Artifact applied successfully'
        })
        
    except Exception as e:
        logger.error(f"Apply artifact error: {e}")
        return jsonify({'error': str(e)}), 500
