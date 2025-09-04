#!/usr/bin/env python3
"""
Priority 27: Verdant - Data Feedback Loop
Scoring and feedback mechanisms for ripened datasets
"""

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
import statistics
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """Types of feedback for datasets"""
    QUALITY_ISSUE = "quality_issue"
    SCHEMA_MISMATCH = "schema_mismatch"
    PROCESSING_ERROR = "processing_error"
    PERFORMANCE_FEEDBACK = "performance_feedback"
    USER_CORRECTION = "user_correction"

class DatasetStatus(Enum):
    """Status of ripened datasets"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    UNDER_REVIEW = "under_review"
    ARCHIVED = "archived"


class FeedbackStatus(str, Enum):
    """Status of feedback"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

@dataclass
class DatasetFeedback:
    """Represents feedback for a ripened dataset"""
    feedback_id: str
    dataset_id: str
    feedback_type: FeedbackType
    severity: str
    description: str
    suggested_improvements: List[str]
    user_id: str
    timestamp: datetime
    resolved: bool
    resolution_notes: Optional[str]

@dataclass
class DatasetScore:
    """Represents a comprehensive score for a ripened dataset"""
    score_id: str
    dataset_id: str
    overall_score: float
    quality_score: float
    schema_score: float
    performance_score: float
    usability_score: float
    scoring_factors: Dict[str, float]
    timestamp: datetime
    version: str

class RipenedDatasetScorer:
    """Scores ripened datasets based on multiple criteria"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "data" / "ripening.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Scoring weights
        self.scoring_weights = {
            "quality": 0.3,
            "schema": 0.25,
            "performance": 0.2,
            "usability": 0.25
        }
        
        logger.info("Ripened Dataset Scorer initialized")
    
    def _init_database(self):
        """Initialize the feedback database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dataset_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    suggested_improvements TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0,
                    resolution_notes TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dataset_scores (
                    score_id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    quality_score REAL NOT NULL,
                    schema_score REAL NOT NULL,
                    performance_score REAL NOT NULL,
                    usability_score REAL NOT NULL,
                    scoring_factors TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    version TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dataset_status (
                    dataset_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    status_reason TEXT
                )
            """)
    
    def score_dataset(self, dataset_id: str, ripened_dataset: Any) -> DatasetScore:
        """Score a ripened dataset comprehensively"""
        try:
            # Calculate individual scores
            quality_score = self._calculate_quality_score(ripened_dataset)
            schema_score = self._calculate_schema_score(ripened_dataset)
            performance_score = self._calculate_performance_score(ripened_dataset)
            usability_score = self._calculate_usability_score(ripened_dataset)
            
            # Calculate overall score
            overall_score = (
                quality_score * self.scoring_weights["quality"] +
                schema_score * self.scoring_weights["schema"] +
                performance_score * self.scoring_weights["performance"] +
                usability_score * self.scoring_weights["usability"]
            )
            
            # Create scoring factors dictionary
            scoring_factors = {
                "quality_factors": self._get_quality_factors(ripened_dataset),
                "schema_factors": self._get_schema_factors(ripened_dataset),
                "performance_factors": self._get_performance_factors(ripened_dataset),
                "usability_factors": self._get_usability_factors(ripened_dataset)
            }
            
            # Create dataset score
            dataset_score = DatasetScore(
                score_id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                overall_score=overall_score,
                quality_score=quality_score,
                schema_score=schema_score,
                performance_score=performance_score,
                usability_score=usability_score,
                scoring_factors=scoring_factors,
                timestamp=datetime.now(),
                version="1.0"
            )
            
            # Store score
            self._store_dataset_score(dataset_score)
            
            return dataset_score
            
        except Exception as e:
            logger.error(f"Error scoring dataset {dataset_id}: {e}")
            raise
    
    def _calculate_quality_score(self, ripened_dataset: Any) -> float:
        """Calculate quality score based on data characteristics"""
        try:
            # Get metadata from ripened dataset
            metadata = getattr(ripened_dataset, 'metadata', {})
            
            quality_factors = []
            
            # File size factor (larger files generally better)
            file_size = metadata.get('file_size', 0)
            if file_size > 1000000:  # > 1MB
                quality_factors.append(1.0)
            elif file_size > 100000:  # > 100KB
                quality_factors.append(0.8)
            elif file_size > 10000:  # > 10KB
                quality_factors.append(0.6)
            else:
                quality_factors.append(0.3)
            
            # Data completeness factor
            completeness = metadata.get('completeness', 0.8)
            quality_factors.append(completeness)
            
            # Data consistency factor
            consistency = metadata.get('consistency', 0.8)
            quality_factors.append(consistency)
            
            # Processing success factor
            processing_success = metadata.get('processing_success', 1.0)
            quality_factors.append(processing_success)
            
            return sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0.5
    
    def _calculate_schema_score(self, ripened_dataset: Any) -> float:
        """Calculate schema score based on field detection accuracy"""
        try:
            # Get schema information
            schema_score = getattr(ripened_dataset, 'schema_score', 0.5)
            
            # Additional schema factors
            schema_factors = []
            
            # Field count factor
            metadata = getattr(ripened_dataset, 'metadata', {})
            field_count = metadata.get('field_count', 1)
            if field_count > 10:
                schema_factors.append(1.0)
            elif field_count > 5:
                schema_factors.append(0.8)
            elif field_count > 2:
                schema_factors.append(0.6)
            else:
                schema_factors.append(0.4)
            
            # Schema confidence factor
            schema_factors.append(schema_score)
            
            return sum(schema_factors) / len(schema_factors) if schema_factors else schema_score
            
        except Exception as e:
            logger.error(f"Error calculating schema score: {e}")
            return 0.5
    
    def _calculate_performance_score(self, ripened_dataset: Any) -> float:
        """Calculate performance score based on processing efficiency"""
        try:
            metadata = getattr(ripened_dataset, 'metadata', {})
            
            performance_factors = []
            
            # Processing time factor
            processing_time = metadata.get('processing_time', 60)  # seconds
            if processing_time < 10:
                performance_factors.append(1.0)
            elif processing_time < 30:
                performance_factors.append(0.8)
            elif processing_time < 60:
                performance_factors.append(0.6)
            else:
                performance_factors.append(0.4)
            
            # Memory efficiency factor
            memory_usage = metadata.get('memory_usage', 100)  # MB
            if memory_usage < 50:
                performance_factors.append(1.0)
            elif memory_usage < 100:
                performance_factors.append(0.8)
            elif memory_usage < 200:
                performance_factors.append(0.6)
            else:
                performance_factors.append(0.4)
            
            # Error rate factor
            error_rate = metadata.get('error_rate', 0.0)
            performance_factors.append(1.0 - error_rate)
            
            return sum(performance_factors) / len(performance_factors) if performance_factors else 0.7
            
        except Exception as e:
            logger.error(f"Error calculating performance score: {e}")
            return 0.7
    
    def _calculate_usability_score(self, ripened_dataset: Any) -> float:
        """Calculate usability score based on user experience factors"""
        try:
            metadata = getattr(ripened_dataset, 'metadata', {})
            
            usability_factors = []
            
            # Format compatibility factor
            format_compatibility = metadata.get('format_compatibility', 0.8)
            usability_factors.append(format_compatibility)
            
            # Documentation quality factor
            documentation_quality = metadata.get('documentation_quality', 0.7)
            usability_factors.append(documentation_quality)
            
            # Ease of integration factor
            integration_ease = metadata.get('integration_ease', 0.8)
            usability_factors.append(integration_ease)
            
            # User feedback factor
            user_satisfaction = metadata.get('user_satisfaction', 0.8)
            usability_factors.append(user_satisfaction)
            
            return sum(usability_factors) / len(usability_factors) if usability_factors else 0.7
            
        except Exception as e:
            logger.error(f"Error calculating usability score: {e}")
            return 0.7
    
    def _get_quality_factors(self, ripened_dataset: Any) -> Dict[str, float]:
        """Get detailed quality factors"""
        metadata = getattr(ripened_dataset, 'metadata', {})
        return {
            "file_size_score": metadata.get('file_size_score', 0.7),
            "completeness": metadata.get('completeness', 0.8),
            "consistency": metadata.get('consistency', 0.8),
            "processing_success": metadata.get('processing_success', 1.0)
        }
    
    def _get_schema_factors(self, ripened_dataset: Any) -> Dict[str, float]:
        """Get detailed schema factors"""
        metadata = getattr(ripened_dataset, 'metadata', {})
        return {
            "field_count_score": metadata.get('field_count_score', 0.7),
            "schema_confidence": getattr(ripened_dataset, 'schema_score', 0.5),
            "field_type_accuracy": metadata.get('field_type_accuracy', 0.8)
        }
    
    def _get_performance_factors(self, ripened_dataset: Any) -> Dict[str, float]:
        """Get detailed performance factors"""
        metadata = getattr(ripened_dataset, 'metadata', {})
        return {
            "processing_time_score": metadata.get('processing_time_score', 0.7),
            "memory_efficiency": metadata.get('memory_efficiency', 0.8),
            "error_rate": metadata.get('error_rate', 0.0)
        }
    
    def _get_usability_factors(self, ripened_dataset: Any) -> Dict[str, float]:
        """Get detailed usability factors"""
        metadata = getattr(ripened_dataset, 'metadata', {})
        return {
            "format_compatibility": metadata.get('format_compatibility', 0.8),
            "documentation_quality": metadata.get('documentation_quality', 0.7),
            "integration_ease": metadata.get('integration_ease', 0.8),
            "user_satisfaction": metadata.get('user_satisfaction', 0.8)
        }
    
    def _store_dataset_score(self, dataset_score: DatasetScore):
        """Store dataset score in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO dataset_scores 
                    (score_id, dataset_id, overall_score, quality_score, schema_score,
                     performance_score, usability_score, scoring_factors, timestamp, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    dataset_score.score_id,
                    dataset_score.dataset_id,
                    dataset_score.overall_score,
                    dataset_score.quality_score,
                    dataset_score.schema_score,
                    dataset_score.performance_score,
                    dataset_score.usability_score,
                    json.dumps(dataset_score.scoring_factors),
                    dataset_score.timestamp.isoformat(),
                    dataset_score.version
                ))
        except Exception as e:
            logger.error(f"Error storing dataset score: {e}")

class DataFeedbackLoop:
    """Manages feedback collection and processing for ripened datasets"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.scorer = RipenedDatasetScorer(base_dir)
        self.db_path = base_dir / "data" / "ripening.db"
        
        logger.info("Data Feedback Loop initialized")
    
    def add_feedback(self, dataset_id: str, feedback_type: FeedbackType, 
                    severity: str, description: str, suggested_improvements: List[str], 
                    user_id: str) -> DatasetFeedback:
        """Add feedback for a dataset"""
        try:
            feedback = DatasetFeedback(
                feedback_id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                feedback_type=feedback_type,
                severity=severity,
                description=description,
                suggested_improvements=suggested_improvements,
                user_id=user_id,
                timestamp=datetime.now(),
                resolved=False,
                resolution_notes=None
            )
            
            # Store feedback
            self._store_feedback(feedback)
            
            # Update dataset status if needed
            self._update_dataset_status(dataset_id, feedback)
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error adding feedback for dataset {dataset_id}: {e}")
            raise
    
    def resolve_feedback(self, feedback_id: str, resolution_notes: str) -> bool:
        """Mark feedback as resolved"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE dataset_feedback 
                    SET resolved = 1, resolution_notes = ?
                    WHERE feedback_id = ?
                """, (resolution_notes, feedback_id))
                
                return conn.total_changes > 0
                
        except Exception as e:
            logger.error(f"Error resolving feedback {feedback_id}: {e}")
            return False
    
    def get_dataset_feedback(self, dataset_id: str, resolved_only: bool = False) -> List[DatasetFeedback]:
        """Get feedback for a specific dataset"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT feedback_id, dataset_id, feedback_type, severity, description,
                           suggested_improvements, user_id, timestamp, resolved, resolution_notes
                    FROM dataset_feedback 
                    WHERE dataset_id = ?
                """
                
                if resolved_only:
                    query += " AND resolved = 1"
                
                query += " ORDER BY timestamp DESC"
                
                cursor = conn.execute(query, (dataset_id,))
                rows = cursor.fetchall()
                
                feedback_list = []
                for row in rows:
                    feedback = DatasetFeedback(
                        feedback_id=row[0],
                        dataset_id=row[1],
                        feedback_type=FeedbackType(row[2]),
                        severity=row[3],
                        description=row[4],
                        suggested_improvements=json.loads(row[5]),
                        user_id=row[6],
                        timestamp=datetime.fromisoformat(row[7]),
                        resolved=bool(row[8]),
                        resolution_notes=row[9]
                    )
                    feedback_list.append(feedback)
                
                return feedback_list
                
        except Exception as e:
            logger.error(f"Error getting feedback for dataset {dataset_id}: {e}")
            return []
    
    def get_dataset_score(self, dataset_id: str) -> Optional[DatasetScore]:
        """Get the latest score for a dataset"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT score_id, dataset_id, overall_score, quality_score, schema_score,
                           performance_score, usability_score, scoring_factors, timestamp, version
                    FROM dataset_scores 
                    WHERE dataset_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (dataset_id,))
                
                row = cursor.fetchone()
                if row:
                    return DatasetScore(
                        score_id=row[0],
                        dataset_id=row[1],
                        overall_score=row[2],
                        quality_score=row[3],
                        schema_score=row[4],
                        performance_score=row[5],
                        usability_score=row[6],
                        scoring_factors=json.loads(row[7]),
                        timestamp=datetime.fromisoformat(row[8]),
                        version=row[9]
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting score for dataset {dataset_id}: {e}")
            return None
    
    def get_dataset_status(self, dataset_id: str) -> Optional[DatasetStatus]:
        """Get the current status of a dataset"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT status FROM dataset_status 
                    WHERE dataset_id = ?
                """, (dataset_id,))
                
                row = cursor.fetchone()
                if row:
                    return DatasetStatus(row[0])
                
                return DatasetStatus.ACTIVE  # Default status
                
        except Exception as e:
            logger.error(f"Error getting status for dataset {dataset_id}: {e}")
            return DatasetStatus.ACTIVE
    
    def update_dataset_status(self, dataset_id: str, status: DatasetStatus, reason: str = None):
        """Update the status of a dataset"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO dataset_status 
                    (dataset_id, status, last_updated, status_reason)
                    VALUES (?, ?, ?, ?)
                """, (
                    dataset_id,
                    status.value,
                    datetime.now().isoformat(),
                    reason
                ))
                
        except Exception as e:
            logger.error(f"Error updating status for dataset {dataset_id}: {e}")
    
    def get_feedback_statistics(self) -> Dict[str, Any]:
        """Get comprehensive feedback statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total feedback count
                cursor = conn.execute("SELECT COUNT(*) FROM dataset_feedback")
                total_feedback = cursor.fetchone()[0]
                
                # Feedback by type
                cursor = conn.execute("""
                    SELECT feedback_type, COUNT(*) FROM dataset_feedback 
                    GROUP BY feedback_type
                """)
                feedback_by_type = dict(cursor.fetchall())
                
                # Feedback by severity
                cursor = conn.execute("""
                    SELECT severity, COUNT(*) FROM dataset_feedback 
                    GROUP BY severity
                """)
                feedback_by_severity = dict(cursor.fetchall())
                
                # Resolution rate
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN resolved = 1 THEN 1 ELSE 0 END) as resolved
                    FROM dataset_feedback
                """)
                resolution_stats = cursor.fetchone()
                resolution_rate = resolution_stats[1] / resolution_stats[0] if resolution_stats[0] > 0 else 0
                
                # Recent feedback (last 30 days)
                thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM dataset_feedback 
                    WHERE timestamp > ?
                """, (thirty_days_ago,))
                recent_feedback = cursor.fetchone()[0]
                
                # Average scores
                cursor = conn.execute("""
                    SELECT AVG(overall_score), AVG(quality_score), AVG(schema_score),
                           AVG(performance_score), AVG(usability_score)
                    FROM dataset_scores
                """)
                avg_scores = cursor.fetchone()
                
            return {
                "total_feedback": total_feedback,
                "feedback_by_type": feedback_by_type,
                "feedback_by_severity": feedback_by_severity,
                "resolution_rate": resolution_rate,
                "recent_feedback": recent_feedback,
                "average_scores": {
                    "overall": avg_scores[0] or 0,
                    "quality": avg_scores[1] or 0,
                    "schema": avg_scores[2] or 0,
                    "performance": avg_scores[3] or 0,
                    "usability": avg_scores[4] or 0
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback statistics: {e}")
            return {"error": str(e)}
    
    def _store_feedback(self, feedback: DatasetFeedback):
        """Store feedback in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO dataset_feedback 
                    (feedback_id, dataset_id, feedback_type, severity, description,
                     suggested_improvements, user_id, timestamp, resolved, resolution_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    feedback.feedback_id,
                    feedback.dataset_id,
                    feedback.feedback_type.value,
                    feedback.severity,
                    feedback.description,
                    json.dumps(feedback.suggested_improvements),
                    feedback.user_id,
                    feedback.timestamp.isoformat(),
                    feedback.resolved,
                    feedback.resolution_notes
                ))
        except Exception as e:
            logger.error(f"Error storing feedback: {e}")
    
    def _update_dataset_status(self, dataset_id: str, feedback: DatasetFeedback):
        """Update dataset status based on feedback"""
        try:
            # Check if feedback is high severity
            if feedback.severity.lower() in ['critical', 'high']:
                self.update_dataset_status(dataset_id, DatasetStatus.UNDER_REVIEW, 
                                         f"High severity feedback: {feedback.feedback_type.value}")
            
            # Check for multiple unresolved feedback
            unresolved_feedback = self.get_dataset_feedback(dataset_id, resolved_only=False)
            unresolved_count = sum(1 for f in unresolved_feedback if not f.resolved)
            
            if unresolved_count > 5:
                self.update_dataset_status(dataset_id, DatasetStatus.UNDER_REVIEW,
                                         f"Multiple unresolved feedback items: {unresolved_count}")
                
        except Exception as e:
            logger.error(f"Error updating dataset status: {e}")
    
    def generate_improvement_recommendations(self, dataset_id: str) -> List[str]:
        """Generate improvement recommendations based on feedback and scores"""
        try:
            recommendations = []
            
            # Get dataset score
            score = self.get_dataset_score(dataset_id)
            if score:
                # Quality recommendations
                if score.quality_score < 0.7:
                    recommendations.append("Improve data quality through better cleaning and validation")
                
                # Schema recommendations
                if score.schema_score < 0.7:
                    recommendations.append("Enhance schema detection and field type accuracy")
                
                # Performance recommendations
                if score.performance_score < 0.7:
                    recommendations.append("Optimize processing performance and reduce resource usage")
                
                # Usability recommendations
                if score.usability_score < 0.7:
                    recommendations.append("Improve documentation and integration ease")
            
            # Get feedback-based recommendations
            feedback_list = self.get_dataset_feedback(dataset_id, resolved_only=False)
            unresolved_feedback = [f for f in feedback_list if not f.resolved]
            
            for feedback in unresolved_feedback:
                recommendations.extend(feedback.suggested_improvements)
            
            # Remove duplicates and return
            return list(set(recommendations))
            
        except Exception as e:
            logger.error(f"Error generating recommendations for dataset {dataset_id}: {e}")
            return []
