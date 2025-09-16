#!/usr/bin/env python3
"""
P34: Multimodal Ingest Module
Voice → text, image/file parsing to requirements, and natural language processing
"""

import os
import json
import sqlite3
import logging
import uuid
import time
import base64
import hashlib
import tempfile
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from werkzeug.utils import secure_filename
import mimetypes
import re

# Import infrastructure components
from config import config
from metrics import metrics
from feature_flags import flag_required
from idempotency import idempotent, require_idempotency_key
from trace_context import get_current_trace
from costs import cost_accounted, log_with_redaction
from multi_tenancy import require_tenant_context, enforce_tenant_isolation

logger = logging.getLogger(__name__)

# Data Models
class IngestStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class FileType(Enum):
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    CSV = "csv"
    JSON = "json"
    YAML = "yaml"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"

@dataclass
class IngestResult:
    id: str
    project_id: str
    ingest_type: str
    file_type: Optional[str]
    status: IngestStatus
    transcript: Optional[str]
    intents: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    requirements: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime]

class MultimodalIngestService:
    """Service for processing multimodal inputs (voice, files, images)"""
    
    def __init__(self):
        self._init_database()
        self.supported_file_types = {
            'pdf': FileType.PDF,
            'doc': FileType.DOC,
            'docx': FileType.DOCX,
            'csv': FileType.CSV,
            'json': FileType.JSON,
            'yaml': FileType.YAML,
            'yml': FileType.YAML,
            'png': FileType.IMAGE,
            'jpg': FileType.IMAGE,
            'jpeg': FileType.IMAGE,
            'gif': FileType.IMAGE,
            'wav': FileType.AUDIO,
            'mp3': FileType.AUDIO,
            'mp4': FileType.VIDEO,
            'txt': FileType.TEXT,
            'md': FileType.TEXT
        }
    
    def _init_database(self):
        """Initialize multimodal ingest database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create ingest_results table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ingest_results (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        ingest_type TEXT NOT NULL,
                        file_type TEXT,
                        status TEXT NOT NULL,
                        transcript TEXT,
                        intents TEXT,
                        entities TEXT,
                        requirements TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP,
                        FOREIGN KEY (project_id) REFERENCES builder_projects (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Multimodal ingest database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize multimodal ingest database: {e}")
    
    def process_voice_input(self, project_id: str, audio_file_path: str, 
                          tenant_id: str) -> Optional[IngestResult]:
        """Process voice input and extract transcript + intents"""
        try:
            ingest_id = f"ingest_{int(time.time())}"
            now = datetime.now()
            
            # Create initial result
            result = IngestResult(
                id=ingest_id,
                project_id=project_id,
                ingest_type="voice",
                file_type="audio",
                status=IngestStatus.PROCESSING,
                transcript=None,
                intents=[],
                entities=[],
                requirements=[],
                metadata={},
                created_at=now,
                completed_at=None
            )
            
            # Save initial state
            self._save_ingest_result(result)
            
            # TODO: Integrate with actual speech-to-text service
            # For now, simulate processing
            transcript = self._simulate_speech_to_text(audio_file_path)
            
            # Extract intents and entities
            intents = self._extract_intents_from_text(transcript)
            entities = self._extract_entities_from_text(transcript)
            requirements = self._extract_requirements_from_text(transcript)
            
            # Update result
            result.transcript = transcript
            result.intents = intents
            result.entities = entities
            result.requirements = requirements
            result.status = IngestStatus.COMPLETED
            result.completed_at = datetime.now()
            result.metadata = {
                'audio_duration': 30.0,  # Mock duration
                'confidence_score': 0.95,
                'language': 'en'
            }
            
            # Save final result
            self._save_ingest_result(result)
            
            # Update metrics
            metrics.increment_counter('sbh_builder_ingest_voice_total', {'tenant_id': tenant_id})
            
            logger.info(f"Processed voice input: {ingest_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process voice input: {e}")
            return None
    
    def process_file_input(self, project_id: str, file_path: str, 
                          tenant_id: str) -> Optional[IngestResult]:
        """Process file input and extract specifications/entities"""
        try:
            ingest_id = f"ingest_{int(time.time())}"
            now = datetime.now()
            
            # Determine file type
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            file_type = self.supported_file_types.get(file_extension, FileType.TEXT)
            
            # Create initial result
            result = IngestResult(
                id=ingest_id,
                project_id=project_id,
                ingest_type="file",
                file_type=file_type.value,
                status=IngestStatus.PROCESSING,
                transcript=None,
                intents=[],
                entities=[],
                requirements=[],
                metadata={},
                created_at=now,
                completed_at=None
            )
            
            # Save initial state
            self._save_ingest_result(result)
            
            # Process based on file type
            if file_type == FileType.PDF:
                content = self._extract_pdf_content(file_path)
            elif file_type == FileType.CSV:
                content = self._extract_csv_content(file_path)
            elif file_type == FileType.JSON:
                content = self._extract_json_content(file_path)
            elif file_type == FileType.YAML:
                content = self._extract_yaml_content(file_path)
            elif file_type == FileType.IMAGE:
                content = self._extract_image_content(file_path)
            elif file_type == FileType.TEXT:
                content = self._extract_text_content(file_path)
            else:
                content = self._extract_generic_content(file_path)
            
            # Extract entities and requirements
            entities = self._extract_entities_from_text(content)
            requirements = self._extract_requirements_from_text(content)
            
            # Update result
            result.transcript = content
            result.entities = entities
            result.requirements = requirements
            result.status = IngestStatus.COMPLETED
            result.completed_at = datetime.now()
            result.metadata = {
                'file_size': os.path.getsize(file_path),
                'file_type': file_type.value,
                'extraction_method': 'automated'
            }
            
            # Save final result
            self._save_ingest_result(result)
            
            # Update metrics
            metrics.increment_counter('sbh_builder_ingest_file_total', {'tenant_id': tenant_id})
            
            logger.info(f"Processed file input: {ingest_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process file input: {e}")
            return None
    
    def _simulate_speech_to_text(self, audio_file_path: str) -> str:
        """Simulate speech-to-text conversion"""
        # TODO: Integrate with actual STT service (OpenAI Whisper, Google Speech, etc.)
        mock_transcripts = [
            "Create a dashboard for user analytics with charts and filters",
            "Build a customer management system with forms and tables",
            "Design a workflow for order processing with approval steps",
            "Generate a reporting interface with data visualization",
            "Create an admin panel with user management and settings"
        ]
        import random
        return random.choice(mock_transcripts)
    
    def _extract_intents_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract intents from text using NLP"""
        intents = []
        
        # Simple keyword-based intent extraction
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['dashboard', 'analytics', 'chart', 'report']):
            intents.append({
                'intent': 'create_dashboard',
                'confidence': 0.9,
                'entities': ['dashboard', 'analytics']
            })
        
        if any(word in text_lower for word in ['form', 'input', 'submit', 'create']):
            intents.append({
                'intent': 'create_form',
                'confidence': 0.85,
                'entities': ['form', 'input']
            })
        
        if any(word in text_lower for word in ['table', 'list', 'data', 'grid']):
            intents.append({
                'intent': 'create_table',
                'confidence': 0.8,
                'entities': ['table', 'data']
            })
        
        if any(word in text_lower for word in ['workflow', 'process', 'step', 'approval']):
            intents.append({
                'intent': 'create_workflow',
                'confidence': 0.9,
                'entities': ['workflow', 'process']
            })
        
        return intents
    
    def _extract_entities_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text"""
        entities = []
        
        # Simple entity extraction patterns
        patterns = {
            'user': r'\buser\w*\b',
            'customer': r'\bcustomer\w*\b',
            'order': r'\border\w*\b',
            'product': r'\bproduct\w*\b',
            'analytics': r'\banalytics\b',
            'dashboard': r'\bdashboard\b',
            'form': r'\bform\w*\b',
            'table': r'\btable\w*\b',
            'chart': r'\bchart\w*\b',
            'workflow': r'\bworkflow\w*\b'
        }
        
        for entity_type, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    'entity': entity_type,
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.8
                })
        
        return entities
    
    def _extract_requirements_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract requirements from text"""
        requirements = []
        
        # Simple requirement extraction
        text_lower = text.lower()
        
        if 'dashboard' in text_lower:
            requirements.append({
                'type': 'component',
                'component': 'dashboard',
                'description': 'User analytics dashboard',
                'priority': 'high'
            })
        
        if 'chart' in text_lower:
            requirements.append({
                'type': 'component',
                'component': 'chart',
                'description': 'Data visualization charts',
                'priority': 'medium'
            })
        
        if 'form' in text_lower:
            requirements.append({
                'type': 'component',
                'component': 'form',
                'description': 'Data input forms',
                'priority': 'high'
            })
        
        if 'table' in text_lower:
            requirements.append({
                'type': 'component',
                'component': 'table',
                'description': 'Data display tables',
                'priority': 'medium'
            })
        
        if 'workflow' in text_lower:
            requirements.append({
                'type': 'workflow',
                'component': 'workflow',
                'description': 'Process workflow with steps',
                'priority': 'high'
            })
        
        return requirements
    
    def _extract_pdf_content(self, file_path: str) -> str:
        """Extract content from PDF file"""
        # TODO: Integrate with PyPDF2 or pdfplumber
        return f"PDF content extracted from {Path(file_path).name}"
    
    def _extract_csv_content(self, file_path: str) -> str:
        """Extract content from CSV file"""
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            return f"CSV data with {len(df)} rows and {len(df.columns)} columns"
        except ImportError:
            return f"CSV file: {Path(file_path).name}"
    
    def _extract_json_content(self, file_path: str) -> str:
        """Extract content from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return f"JSON data with {len(data)} top-level keys"
        except Exception:
            return f"JSON file: {Path(file_path).name}"
    
    def _extract_yaml_content(self, file_path: str) -> str:
        """Extract content from YAML file"""
        try:
            import yaml
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            return f"YAML data with {len(data) if isinstance(data, dict) else 'multiple'} entries"
        except ImportError:
            return f"YAML file: {Path(file_path).name}"
    
    def _extract_image_content(self, file_path: str) -> str:
        """Extract content from image file"""
        # TODO: Integrate with OCR (Tesseract) or image analysis
        return f"Image file: {Path(file_path).name}"
    
    def _extract_text_content(self, file_path: str) -> str:
        """Extract content from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return f"Text file: {Path(file_path).name}"
    
    def _extract_generic_content(self, file_path: str) -> str:
        """Extract content from generic file"""
        return f"File: {Path(file_path).name}"
    
    def _save_ingest_result(self, result: IngestResult):
        """Save ingest result to database"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO ingest_results 
                    (id, project_id, ingest_type, file_type, status, transcript, intents, entities, requirements, metadata, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.id,
                    result.project_id,
                    result.ingest_type,
                    result.file_type,
                    result.status.value,
                    result.transcript,
                    json.dumps(result.intents),
                    json.dumps(result.entities),
                    json.dumps(result.requirements),
                    json.dumps(result.metadata),
                    result.created_at.isoformat(),
                    result.completed_at.isoformat() if result.completed_at else None
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to save ingest result: {e}")
    
    def get_ingest_result(self, ingest_id: str, project_id: str, tenant_id: str) -> Optional[IngestResult]:
        """Get ingest result by ID with tenant isolation"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT ir.id, ir.project_id, ir.ingest_type, ir.file_type, ir.status, 
                           ir.transcript, ir.intents, ir.entities, ir.requirements, ir.metadata, 
                           ir.created_at, ir.completed_at
                    FROM ingest_results ir
                    JOIN builder_projects bp ON ir.project_id = bp.id
                    WHERE ir.id = ? AND ir.project_id = ? AND bp.tenant_id = ?
                ''', (ingest_id, project_id, tenant_id))
                row = cursor.fetchone()
                
                if row:
                    return IngestResult(
                        id=row[0],
                        project_id=row[1],
                        ingest_type=row[2],
                        file_type=row[3],
                        status=IngestStatus(row[4]),
                        transcript=row[5],
                        intents=json.loads(row[6]) if row[6] else [],
                        entities=json.loads(row[7]) if row[7] else [],
                        requirements=json.loads(row[8]) if row[8] else [],
                        metadata=json.loads(row[9]) if row[9] else {},
                        created_at=datetime.fromisoformat(row[10]),
                        completed_at=datetime.fromisoformat(row[11]) if row[11] else None
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get ingest result: {e}")
            return None

# Initialize service
multimodal_ingest_service = MultimodalIngestService()
