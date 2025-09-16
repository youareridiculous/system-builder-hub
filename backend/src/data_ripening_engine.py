#!/usr/bin/env python3
"""
Priority 27: Verdant - AI Data Ripening & Readiness Engine
Core data processing for AI-ready datasets
"""

import pandas as pd
import numpy as np
import json
import uuid
import sqlite3
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import logging
import re
import hashlib
import mimetypes
import tempfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RipeningMethod(Enum):
    """Methods for data ripening"""
    RAG_OPTIMIZATION = "rag_optimization"
    TRAINING_PREPARATION = "training_preparation"
    PROMPT_BUILDING = "prompt_building"
    CONFIG_BUILDING = "config_building"
    SCHEMA_INFERENCE = "schema_inference"

class SchemaMatchConfidence(Enum):
    """Confidence levels for schema matching"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXACT = "exact"

class DataQuality(Enum):
    """Data quality levels"""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class RipeningStage(str, Enum):
    """Stages of data ripening"""
    RAW = "raw"
    PROCESSING = "processing"
    VALIDATED = "validated"
    ENRICHED = "enriched"
    READY = "ready"
    ARCHIVED = "archived"


class RipeningStatus(str, Enum):
    """Status of ripening process"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class RipenedDataset:
    """Represents a ripened dataset"""
    dataset_id: str
    original_file: str
    final_version: str
    schema_score: float
    quality_score: float
    ripening_method: RipeningMethod
    metadata: Dict[str, Any]
    timestamp: datetime
    lineage: List[str]

@dataclass
class DataSchema:
    """Represents a data schema"""
    schema_id: str
    dataset_id: str
    field_name: str
    field_type: str
    confidence: SchemaMatchConfidence
    sample_values: List[str]
    validation_rules: Dict[str, Any]
    timestamp: datetime

class DataIngestor:
    """Accepts and processes raw files in various formats"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.data_dir = base_dir / "data" / "ripening"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported file types
        self.supported_formats = {
            '.csv': self._ingest_csv,
            '.xlsx': self._ingest_excel,
            '.json': self._ingest_json,
            '.txt': self._ingest_text,
            '.pdf': self._ingest_pdf,
            '.parquet': self._ingest_parquet
        }
        
        logger.info("Data Ingestor initialized")
    
    def ingest_file(self, file_path: Path, dataset_id: str) -> Dict[str, Any]:
        """Ingest a file and return metadata"""
        try:
            file_extension = file_path.suffix.lower()
            
            if file_extension not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # Copy file to data directory
            dest_path = self.data_dir / f"{dataset_id}{file_extension}"
            shutil.copy2(file_path, dest_path)
            
            # Ingest based on file type
            ingest_func = self.supported_formats[file_extension]
            data_info = ingest_func(dest_path)
            
            # Add file metadata
            data_info.update({
                "dataset_id": dataset_id,
                "original_path": str(file_path),
                "stored_path": str(dest_path),
                "file_size": dest_path.stat().st_size,
                "file_hash": self._calculate_file_hash(dest_path),
                "ingestion_timestamp": datetime.now().isoformat()
            })
            
            return data_info
            
        except Exception as e:
            logger.error(f"Error ingesting file {file_path}: {e}")
            raise
    
    def _ingest_csv(self, file_path: Path) -> Dict[str, Any]:
        """Ingest CSV file"""
        try:
            df = pd.read_csv(file_path)
            return {
                "format": "csv",
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.to_dict(),
                "sample_data": df.head(5).to_dict('records')
            }
        except Exception as e:
            logger.error(f"Error ingesting CSV {file_path}: {e}")
            raise
    
    def _ingest_excel(self, file_path: Path) -> Dict[str, Any]:
        """Ingest Excel file"""
        try:
            df = pd.read_excel(file_path)
            return {
                "format": "excel",
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.to_dict(),
                "sample_data": df.head(5).to_dict('records')
            }
        except Exception as e:
            logger.error(f"Error ingesting Excel {file_path}: {e}")
            raise
    
    def _ingest_json(self, file_path: Path) -> Dict[str, Any]:
        """Ingest JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                df = pd.DataFrame(data)
                return {
                    "format": "json",
                    "rows": len(df),
                    "columns": len(df.columns) if len(df.columns) > 0 else 0,
                    "column_names": df.columns.tolist() if len(df.columns) > 0 else [],
                    "data_types": df.dtypes.to_dict() if len(df.columns) > 0 else {},
                    "sample_data": data[:5]
                }
            else:
                return {
                    "format": "json",
                    "rows": 1,
                    "columns": len(data),
                    "column_names": list(data.keys()),
                    "data_types": {k: type(v).__name__ for k, v in data.items()},
                    "sample_data": [data]
                }
        except Exception as e:
            logger.error(f"Error ingesting JSON {file_path}: {e}")
            raise
    
    def _ingest_text(self, file_path: Path) -> Dict[str, Any]:
        """Ingest text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            return {
                "format": "text",
                "rows": len(lines),
                "columns": 1,
                "column_names": ["text"],
                "data_types": {"text": "object"},
                "sample_data": [{"text": line} for line in lines[:5]]
            }
        except Exception as e:
            logger.error(f"Error ingesting text {file_path}: {e}")
            raise
    
    def _ingest_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Ingest PDF file (placeholder)"""
        return {
            "format": "pdf",
            "rows": 1,
            "columns": 1,
            "column_names": ["content"],
            "data_types": {"content": "object"},
            "sample_data": [{"content": "PDF content extracted"}],
            "note": "PDF processing requires additional libraries"
        }
    
    def _ingest_parquet(self, file_path: Path) -> Dict[str, Any]:
        """Ingest Parquet file"""
        try:
            df = pd.read_parquet(file_path)
            return {
                "format": "parquet",
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.to_dict(),
                "sample_data": df.head(5).to_dict('records')
            }
        except Exception as e:
            logger.error(f"Error ingesting Parquet {file_path}: {e}")
            raise
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

class DataCleaner:
    """Cleans and fixes data quality issues"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.cleaned_dir = base_dir / "data" / "ripening" / "cleaned"
        self.cleaned_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Data Cleaner initialized")
    
    def clean_dataset(self, dataset_id: str, data_info: Dict[str, Any]) -> Dict[str, Any]:
        """Clean a dataset and return cleaning report"""
        try:
            # Load data based on format
            df = self._load_dataframe(data_info)
            
            # Apply cleaning steps
            cleaning_report = {
                "original_rows": len(df),
                "original_columns": len(df.columns),
                "cleaning_steps": []
            }
            
            # Remove duplicates
            original_len = len(df)
            df = df.drop_duplicates()
            duplicates_removed = original_len - len(df)
            if duplicates_removed > 0:
                cleaning_report["cleaning_steps"].append({
                    "step": "remove_duplicates",
                    "rows_removed": duplicates_removed
                })
            
            # Handle missing values
            missing_report = self._handle_missing_values(df)
            cleaning_report["cleaning_steps"].append(missing_report)
            
            # Fix data types
            type_report = self._fix_data_types(df)
            cleaning_report["cleaning_steps"].append(type_report)
            
            # Remove outliers (for numeric columns)
            outlier_report = self._remove_outliers(df)
            cleaning_report["cleaning_steps"].append(outlier_report)
            
            # Save cleaned data
            cleaned_path = self.cleaned_dir / f"{dataset_id}_cleaned.csv"
            df.to_csv(cleaned_path, index=False)
            
            cleaning_report.update({
                "final_rows": len(df),
                "final_columns": len(df.columns),
                "cleaned_file_path": str(cleaned_path),
                "cleaning_timestamp": datetime.now().isoformat()
            })
            
            return cleaning_report
            
        except Exception as e:
            logger.error(f"Error cleaning dataset {dataset_id}: {e}")
            raise
    
    def _load_dataframe(self, data_info: Dict[str, Any]) -> pd.DataFrame:
        """Load data into DataFrame"""
        file_path = data_info["stored_path"]
        format_type = data_info["format"]
        
        if format_type == "csv":
            return pd.read_csv(file_path)
        elif format_type == "excel":
            return pd.read_excel(file_path)
        elif format_type == "json":
            with open(file_path, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                return pd.DataFrame(data)
            else:
                return pd.DataFrame([data])
        elif format_type == "parquet":
            return pd.read_parquet(file_path)
        else:
            raise ValueError(f"Unsupported format for DataFrame loading: {format_type}")
    
    def _handle_missing_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Handle missing values in DataFrame"""
        missing_counts = df.isnull().sum().to_dict()
        total_missing = sum(missing_counts.values())
        
        # Fill missing values based on data type
        for column in df.columns:
            if df[column].isnull().sum() > 0:
                if df[column].dtype in ['int64', 'float64']:
                    df[column].fillna(df[column].median(), inplace=True)
                else:
                    df[column].fillna(df[column].mode()[0] if len(df[column].mode()) > 0 else "Unknown", inplace=True)
        
        return {
            "step": "handle_missing_values",
            "missing_counts": missing_counts,
            "total_missing": total_missing
        }
    
    def _fix_data_types(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Fix data types in DataFrame"""
        type_changes = []
        
        for column in df.columns:
            original_type = str(df[column].dtype)
            
            # Try to convert to appropriate type
            if df[column].dtype == 'object':
                # Try to convert to numeric
                try:
                    pd.to_numeric(df[column])
                    df[column] = pd.to_numeric(df[column], errors='coerce')
                    type_changes.append({
                        "column": column,
                        "from": original_type,
                        "to": str(df[column].dtype)
                    })
                except:
                    # Try to convert to datetime
                    try:
                        pd.to_datetime(df[column])
                        df[column] = pd.to_datetime(df[column], errors='coerce')
                        type_changes.append({
                            "column": column,
                            "from": original_type,
                            "to": str(df[column].dtype)
                        })
                    except:
                        pass
        
        return {
            "step": "fix_data_types",
            "type_changes": type_changes
        }
    
    def _remove_outliers(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Remove outliers from numeric columns"""
        outliers_removed = 0
        
        for column in df.select_dtypes(include=[np.number]).columns:
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
            outliers_removed += len(outliers)
            
            # Remove outliers
            df = df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]
        
        return {
            "step": "remove_outliers",
            "outliers_removed": outliers_removed
        }

class DataLabeler:
    """Auto-tags schema fields using heuristics and LLMs"""
    
    def __init__(self, base_dir: Path, llm_factory=None):
        self.base_dir = base_dir
        self.llm_factory = llm_factory
        self.db_path = base_dir / "data" / "ripening.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Common field patterns
        self.field_patterns = {
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "phone": r"^[\+]?[1-9][\d]{0,15}$",
            "date": r"^\d{4}-\d{2}-\d{2}$|^\d{2}/\d{2}/\d{4}$",
            "url": r"^https?://[^\s/$.?#].[^\s]*$",
            "ip_address": r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",
            "postal_code": r"^\d{5}(-\d{4})?$",
            "ssn": r"^\d{3}-\d{2}-\d{4}$"
        }
        
        logger.info("Data Labeler initialized")
    
    def _init_database(self):
        """Initialize the ripening database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ripened_datasets (
                    dataset_id TEXT PRIMARY KEY,
                    original_file TEXT NOT NULL,
                    final_version TEXT NOT NULL,
                    schema_score REAL NOT NULL,
                    quality_score REAL NOT NULL,
                    ripening_method TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    lineage TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ripening_logs (
                    log_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    step TEXT NOT NULL,
                    tool_used TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    failure_type TEXT NOT NULL,
                    associated_input_id TEXT NOT NULL,
                    caused_by TEXT NOT NULL,
                    recommended_fix TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
    
    def label_schema(self, dataset_id: str, df: pd.DataFrame) -> List[DataSchema]:
        """Label schema fields for a dataset"""
        schemas = []
        
        for column in df.columns:
            schema = self._analyze_column(column, df[column], dataset_id)
            schemas.append(schema)
            
            # Store schema
            self._store_schema(schema)
        
        return schemas
    
    def _analyze_column(self, column_name: str, column_data: pd.Series, dataset_id: str) -> DataSchema:
        """Analyze a single column and determine its schema"""
        # Basic type detection
        data_type = str(column_data.dtype)
        
        # Pattern matching
        field_type = self._detect_field_type(column_name, column_data)
        
        # Confidence calculation
        confidence = self._calculate_confidence(column_name, column_data, field_type)
        
        # Sample values
        sample_values = column_data.dropna().head(10).astype(str).tolist()
        
        # Validation rules
        validation_rules = self._generate_validation_rules(field_type, column_data)
        
        return DataSchema(
            schema_id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            field_name=column_name,
            field_type=field_type,
            confidence=confidence,
            sample_values=sample_values,
            validation_rules=validation_rules,
            timestamp=datetime.now()
        )
    
    def _detect_field_type(self, column_name: str, column_data: pd.Series) -> str:
        """Detect the field type based on name and data patterns"""
        column_lower = column_name.lower()
        
        # Check for common field names
        if any(word in column_lower for word in ['email', 'e-mail', 'mail']):
            return "email"
        elif any(word in column_lower for word in ['phone', 'tel', 'mobile']):
            return "phone"
        elif any(word in column_lower for word in ['date', 'time', 'created', 'updated']):
            return "datetime"
        elif any(word in column_lower for word in ['url', 'link', 'website']):
            return "url"
        elif any(word in column_lower for word in ['name', 'title', 'description']):
            return "text"
        elif any(word in column_lower for word in ['id', 'key']):
            return "identifier"
        elif any(word in column_lower for word in ['price', 'cost', 'amount', 'value']):
            return "currency"
        elif any(word in column_lower for word in ['age', 'count', 'number']):
            return "integer"
        elif any(word in column_lower for word in ['score', 'rating', 'percentage']):
            return "float"
        
        # Check data patterns
        sample_data = column_data.dropna().astype(str).head(100)
        
        for field_type, pattern in self.field_patterns.items():
            matches = sum(1 for value in sample_data if re.match(pattern, value))
            if matches > len(sample_data) * 0.8:  # 80% match rate
                return field_type
        
        # Default based on data type
        if column_data.dtype in ['int64', 'int32']:
            return "integer"
        elif column_data.dtype in ['float64', 'float32']:
            return "float"
        elif column_data.dtype == 'datetime64[ns]':
            return "datetime"
        else:
            return "text"
    
    def _calculate_confidence(self, column_name: str, column_data: pd.Series, field_type: str) -> SchemaMatchConfidence:
        """Calculate confidence in field type detection"""
        # Check pattern match rate
        if field_type in self.field_patterns:
            pattern = self.field_patterns[field_type]
            sample_data = column_data.dropna().astype(str).head(100)
            matches = sum(1 for value in sample_data if re.match(pattern, value))
            match_rate = matches / len(sample_data) if len(sample_data) > 0 else 0
            
            if match_rate > 0.95:
                return SchemaMatchConfidence.EXACT
            elif match_rate > 0.8:
                return SchemaMatchConfidence.HIGH
            elif match_rate > 0.6:
                return SchemaMatchConfidence.MEDIUM
            else:
                return SchemaMatchConfidence.LOW
        
        # Check name-based detection
        column_lower = column_name.lower()
        if any(word in column_lower for word in ['email', 'phone', 'date', 'url']):
            return SchemaMatchConfidence.HIGH
        elif any(word in column_lower for word in ['name', 'id', 'price']):
            return SchemaMatchConfidence.MEDIUM
        else:
            return SchemaMatchConfidence.LOW
    
    def _generate_validation_rules(self, field_type: str, column_data: pd.Series) -> Dict[str, Any]:
        """Generate validation rules for a field type"""
        rules = {"field_type": field_type}
        
        if field_type == "email":
            rules["pattern"] = self.field_patterns["email"]
        elif field_type == "phone":
            rules["pattern"] = self.field_patterns["phone"]
        elif field_type == "url":
            rules["pattern"] = self.field_patterns["url"]
        elif field_type in ["integer", "float"]:
            rules["min_value"] = float(column_data.min()) if len(column_data) > 0 else None
            rules["max_value"] = float(column_data.max()) if len(column_data) > 0 else None
        elif field_type == "text":
            rules["max_length"] = int(column_data.astype(str).str.len().max()) if len(column_data) > 0 else None
        
        return rules
    
    def _store_schema(self, schema: DataSchema):
        """Store schema in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO data_schemas 
                    (schema_id, dataset_id, field_name, field_type, confidence, 
                     sample_values, validation_rules, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    schema.schema_id,
                    schema.dataset_id,
                    schema.field_name,
                    schema.field_type,
                    schema.confidence.value,
                    json.dumps(schema.sample_values),
                    json.dumps(schema.validation_rules),
                    schema.timestamp.isoformat()
                ))
        except Exception as e:
            logger.error(f"Error storing schema: {e}")

class RipeningStrategy:
    """Chooses ripening path based on use case"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.strategies = {
            RipeningMethod.RAG_OPTIMIZATION: self._rag_optimization,
            RipeningMethod.TRAINING_PREPARATION: self._training_preparation,
            RipeningMethod.PROMPT_BUILDING: self._prompt_building,
            RipeningMethod.CONFIG_BUILDING: self._config_building,
            RipeningMethod.SCHEMA_INFERENCE: self._schema_inference
        }
        
        logger.info("Ripening Strategy initialized")
    
    def ripen_dataset(self, dataset_id: str, method: RipeningMethod, 
                     data_info: Dict[str, Any], schemas: List[DataSchema]) -> RipenedDataset:
        """Apply ripening strategy to dataset"""
        try:
            strategy_func = self.strategies.get(method)
            if not strategy_func:
                raise ValueError(f"Unknown ripening method: {method}")
            
            # Apply strategy
            ripened_data = strategy_func(dataset_id, data_info, schemas)
            
            # Calculate scores
            schema_score = self._calculate_schema_score(schemas)
            quality_score = self._calculate_quality_score(data_info)
            
            # Create ripened dataset
            ripened_dataset = RipenedDataset(
                dataset_id=dataset_id,
                original_file=data_info["original_path"],
                final_version=ripened_data["output_path"],
                schema_score=schema_score,
                quality_score=quality_score,
                ripening_method=method,
                metadata=ripened_data["metadata"],
                timestamp=datetime.now(),
                lineage=ripened_data["lineage"]
            )
            
            # Store ripened dataset
            self._store_ripened_dataset(ripened_dataset)
            
            return ripened_dataset
            
        except Exception as e:
            logger.error(f"Error ripening dataset {dataset_id}: {e}")
            raise
    
    def _rag_optimization(self, dataset_id: str, data_info: Dict[str, Any], 
                         schemas: List[DataSchema]) -> Dict[str, Any]:
        """Optimize dataset for RAG applications"""
        # Create chunked and indexed version for RAG
        output_path = self.base_dir / "data" / "ripening" / "rag" / f"{dataset_id}_rag.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Simulate RAG optimization
        rag_data = {
            "chunks": [],
            "embeddings": [],
            "metadata": {
                "chunk_size": 512,
                "overlap": 50,
                "embedding_model": "text-embedding-ada-002"
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(rag_data, f, indent=2)
        
        return {
            "output_path": str(output_path),
            "metadata": {
                "optimization_type": "rag",
                "chunk_size": 512,
                "overlap": 50
            },
            "lineage": ["ingestion", "cleaning", "rag_optimization"]
        }
    
    def _training_preparation(self, dataset_id: str, data_info: Dict[str, Any], 
                            schemas: List[DataSchema]) -> Dict[str, Any]:
        """Prepare dataset for training"""
        output_path = self.base_dir / "data" / "ripening" / "training" / f"{dataset_id}_training.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Simulate training preparation
        training_data = {
            "train": [],
            "validation": [],
            "test": [],
            "metadata": {
                "split_ratio": [0.7, 0.15, 0.15],
                "target_column": "label"
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        return {
            "output_path": str(output_path),
            "metadata": {
                "optimization_type": "training",
                "split_ratio": [0.7, 0.15, 0.15]
            },
            "lineage": ["ingestion", "cleaning", "training_preparation"]
        }
    
    def _prompt_building(self, dataset_id: str, data_info: Dict[str, Any], 
                        schemas: List[DataSchema]) -> Dict[str, Any]:
        """Prepare dataset for prompt building"""
        output_path = self.base_dir / "data" / "ripening" / "prompts" / f"{dataset_id}_prompts.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Simulate prompt building preparation
        prompt_data = {
            "prompts": [],
            "examples": [],
            "metadata": {
                "prompt_type": "few_shot",
                "example_count": 10
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(prompt_data, f, indent=2)
        
        return {
            "output_path": str(output_path),
            "metadata": {
                "optimization_type": "prompt_building",
                "prompt_type": "few_shot"
            },
            "lineage": ["ingestion", "cleaning", "prompt_building"]
        }
    
    def _config_building(self, dataset_id: str, data_info: Dict[str, Any], 
                        schemas: List[DataSchema]) -> Dict[str, Any]:
        """Prepare dataset for configuration building"""
        output_path = self.base_dir / "data" / "ripening" / "config" / f"{dataset_id}_config.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate configuration from schemas
        config_data = {
            "schema": {schema.field_name: schema.validation_rules for schema in schemas},
            "validation": {},
            "metadata": {
                "config_type": "data_validation",
                "schema_version": "1.0"
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        return {
            "output_path": str(output_path),
            "metadata": {
                "optimization_type": "config_building",
                "config_type": "data_validation"
            },
            "lineage": ["ingestion", "cleaning", "config_building"]
        }
    
    def _schema_inference(self, dataset_id: str, data_info: Dict[str, Any], 
                         schemas: List[DataSchema]) -> Dict[str, Any]:
        """Infer and validate schema"""
        output_path = self.base_dir / "data" / "ripening" / "schema" / f"{dataset_id}_schema.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create schema definition
        schema_data = {
            "dataset_id": dataset_id,
            "fields": [
                {
                    "name": schema.field_name,
                    "type": schema.field_type,
                    "confidence": schema.confidence.value,
                    "validation_rules": schema.validation_rules,
                    "sample_values": schema.sample_values
                }
                for schema in schemas
            ],
            "metadata": {
                "inference_method": "heuristic_llm",
                "confidence_threshold": 0.8
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(schema_data, f, indent=2)
        
        return {
            "output_path": str(output_path),
            "metadata": {
                "optimization_type": "schema_inference",
                "inference_method": "heuristic_llm"
            },
            "lineage": ["ingestion", "cleaning", "schema_inference"]
        }
    
    def _calculate_schema_score(self, schemas: List[DataSchema]) -> float:
        """Calculate schema confidence score"""
        if not schemas:
            return 0.0
        
        confidence_scores = {
            SchemaMatchConfidence.EXACT: 1.0,
            SchemaMatchConfidence.HIGH: 0.8,
            SchemaMatchConfidence.MEDIUM: 0.6,
            SchemaMatchConfidence.LOW: 0.3
        }
        
        total_score = sum(confidence_scores[schema.confidence] for schema in schemas)
        return total_score / len(schemas)
    
    def _calculate_quality_score(self, data_info: Dict[str, Any]) -> float:
        """Calculate data quality score"""
        # Simple quality scoring based on data characteristics
        quality_factors = []
        
        # Row count factor
        if data_info["rows"] > 1000:
            quality_factors.append(1.0)
        elif data_info["rows"] > 100:
            quality_factors.append(0.8)
        elif data_info["rows"] > 10:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.3)
        
        # Column count factor
        if data_info["columns"] > 5:
            quality_factors.append(1.0)
        elif data_info["columns"] > 2:
            quality_factors.append(0.8)
        else:
            quality_factors.append(0.6)
        
        # Data type diversity factor
        unique_types = len(set(data_info["data_types"].values()))
        if unique_types > 3:
            quality_factors.append(1.0)
        elif unique_types > 1:
            quality_factors.append(0.8)
        else:
            quality_factors.append(0.6)
        
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
    
    def _store_ripened_dataset(self, ripened_dataset: RipenedDataset):
        """Store ripened dataset in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO ripened_datasets 
                    (dataset_id, original_file, final_version, schema_score, quality_score,
                     ripening_method, metadata, timestamp, lineage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ripened_dataset.dataset_id,
                    ripened_dataset.original_file,
                    ripened_dataset.final_version,
                    ripened_dataset.schema_score,
                    ripened_dataset.quality_score,
                    ripened_dataset.ripening_method.value,
                    json.dumps(ripened_dataset.metadata),
                    ripened_dataset.timestamp.isoformat(),
                    json.dumps(ripened_dataset.lineage)
                ))
        except Exception as e:
            logger.error(f"Error storing ripened dataset: {e}")

class DataRipeningEngine:
    """
    Main Data Ripening Engine that orchestrates all data processing components
    """
    
    def __init__(self, base_dir: Path, llm_factory=None):
        self.base_dir = base_dir
        self.llm_factory = llm_factory
        
        # Initialize components
        self.data_ingestor = DataIngestor(base_dir)
        self.data_cleaner = DataCleaner(base_dir)
        self.data_labeler = DataLabeler(base_dir, llm_factory)
        self.ripening_strategy = RipeningStrategy(base_dir)
        
        logger.info("Data Ripening Engine initialized")
    
    def process_dataset(self, file_path: Path, ripening_method: RipeningMethod) -> RipenedDataset:
        """Process a dataset through the complete ripening pipeline"""
        try:
            dataset_id = str(uuid.uuid4())
            
            # Step 1: Ingest data
            logger.info(f"Step 1: Ingesting dataset {dataset_id}")
            data_info = self.data_ingestor.ingest_file(file_path, dataset_id)
            
            # Step 2: Clean data
            logger.info(f"Step 2: Cleaning dataset {dataset_id}")
            cleaning_report = self.data_cleaner.clean_dataset(dataset_id, data_info)
            
            # Step 3: Label schema
            logger.info(f"Step 3: Labeling schema for dataset {dataset_id}")
            df = pd.read_csv(cleaning_report["cleaned_file_path"])
            schemas = self.data_labeler.label_schema(dataset_id, df)
            
            # Step 4: Apply ripening strategy
            logger.info(f"Step 4: Applying {ripening_method.value} to dataset {dataset_id}")
            ripened_dataset = self.ripening_strategy.ripen_dataset(
                dataset_id, ripening_method, data_info, schemas
            )
            
            # Log processing
            self._log_processing_step(dataset_id, "ingestion", "DataIngestor", data_info)
            self._log_processing_step(dataset_id, "cleaning", "DataCleaner", cleaning_report)
            self._log_processing_step(dataset_id, "labeling", "DataLabeler", {"schemas_count": len(schemas)})
            self._log_processing_step(dataset_id, "ripening", "RipeningStrategy", {"method": ripening_method.value})
            
            logger.info(f"Dataset {dataset_id} processed successfully")
            return ripened_dataset
            
        except Exception as e:
            logger.error(f"Error processing dataset: {e}")
            # Log failure
            self._log_failure(str(uuid.uuid4()), "processing_error", str(e), "Check file format and permissions")
            raise
    
    def _log_processing_step(self, dataset_id: str, step: str, tool: str, details: Dict[str, Any]):
        """Log a processing step"""
        try:
            with sqlite3.connect(self.data_labeler.db_path) as conn:
                conn.execute("""
                    INSERT INTO ripening_logs 
                    (log_id, dataset_id, step, tool_used, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    dataset_id,
                    step,
                    tool,
                    datetime.now().isoformat(),
                    json.dumps(details)
                ))
        except Exception as e:
            logger.error(f"Error logging processing step: {e}")
    
    def _log_failure(self, feedback_id: str, failure_type: str, caused_by: str, recommended_fix: str):
        """Log a processing failure"""
        try:
            with sqlite3.connect(self.data_labeler.db_path) as conn:
                conn.execute("""
                    INSERT INTO data_feedback 
                    (feedback_id, failure_type, associated_input_id, caused_by, recommended_fix, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    feedback_id,
                    failure_type,
                    "unknown",
                    caused_by,
                    recommended_fix,
                    datetime.now().isoformat()
                ))
        except Exception as e:
            logger.error(f"Error logging failure: {e}")
    
    def get_ripening_stats(self) -> Dict[str, Any]:
        """Get ripening statistics"""
        try:
            with sqlite3.connect(self.data_labeler.db_path) as conn:
                # Total datasets processed
                cursor = conn.execute("SELECT COUNT(*) FROM ripened_datasets")
                total_datasets = cursor.fetchone()[0]
                
                # Datasets by method
                cursor = conn.execute("""
                    SELECT ripening_method, COUNT(*) FROM ripened_datasets 
                    GROUP BY ripening_method
                """)
                datasets_by_method = dict(cursor.fetchall())
                
                # Average scores
                cursor = conn.execute("SELECT AVG(schema_score), AVG(quality_score) FROM ripened_datasets")
                avg_scores = cursor.fetchone()
                avg_schema_score = avg_scores[0] or 0
                avg_quality_score = avg_scores[1] or 0
                
                # Recent processing logs
                cursor = conn.execute("""
                    SELECT step, COUNT(*) FROM ripening_logs 
                    WHERE timestamp > ?
                    GROUP BY step
                """, ((datetime.now() - timedelta(days=7)).isoformat(),))
                recent_logs = dict(cursor.fetchall())
                
            return {
                "total_datasets": total_datasets,
                "datasets_by_method": datasets_by_method,
                "average_schema_score": avg_schema_score,
                "average_quality_score": avg_quality_score,
                "recent_processing": recent_logs,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting ripening stats: {e}")
            return {"error": str(e)}
