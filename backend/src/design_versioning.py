#!/usr/bin/env python3
"""
P35: Design Versioning Module
Branches, merges, reviews, and version control for design artifacts
"""

import os
import json
import sqlite3
import logging
import uuid
import time
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
design_versioning_bp = Blueprint('design_versioning', __name__, url_prefix='/api/design')

# Data Models
class BranchStatus(Enum):
    ACTIVE = "active"
    MERGED = "merged"
    DELETED = "deleted"

class ReviewState(Enum):
    OPEN = "open"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    CLOSED = "closed"

class CommitType(Enum):
    CANVAS_UPDATE = "canvas_update"
    WORKFLOW_UPDATE = "workflow_update"
    COMPONENT_ADD = "component_add"
    COMPONENT_UPDATE = "component_update"
    COMPONENT_DELETE = "component_delete"
    METADATA_UPDATE = "metadata_update"

@dataclass
class DesignBranch:
    id: str
    project_id: str
    name: str
    base_branch: Optional[str]
    head_commit: str
    created_by: str
    created_at: datetime
    status: BranchStatus
    metadata: Dict[str, Any]

@dataclass
class DesignCommit:
    id: str
    branch_id: str
    author_id: str
    commit_type: CommitType
    diff_json: Dict[str, Any]
    message: str
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class DesignReview:
    id: str
    branch_id: str
    reviewer_id: str
    state: ReviewState
    comments: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

class DesignVersioningService:
    """Service for managing design versioning, branches, and reviews"""
    
    def __init__(self):
        self._init_database()
    
    def _init_database(self):
        """Initialize design versioning database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create design_branches table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS design_branches (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        base_branch TEXT,
                        head_commit TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        status TEXT NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (project_id) REFERENCES builder_projects (id)
                    )
                ''')
                
                # Create design_commits table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS design_commits (
                        id TEXT PRIMARY KEY,
                        branch_id TEXT NOT NULL,
                        author_id TEXT NOT NULL,
                        commit_type TEXT NOT NULL,
                        diff_json TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (branch_id) REFERENCES design_branches (id)
                    )
                ''')
                
                # Create design_reviews table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS design_reviews (
                        id TEXT PRIMARY KEY,
                        branch_id TEXT NOT NULL,
                        reviewer_id TEXT NOT NULL,
                        state TEXT NOT NULL,
                        comments TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (branch_id) REFERENCES design_branches (id)
                    )
                ''')
                
                conn.commit()
                logger.info("Design versioning database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize design versioning database: {e}")
    
    def create_branch(self, project_id: str, name: str, base_branch: Optional[str], 
                     created_by: str) -> Optional[DesignBranch]:
        """Create a new design branch"""
        try:
            branch_id = f"branch_{int(time.time())}"
            now = datetime.now()
            
            # Generate initial commit
            head_commit = f"commit_{int(time.time())}"
            
            branch = DesignBranch(
                id=branch_id,
                project_id=project_id,
                name=name,
                base_branch=base_branch,
                head_commit=head_commit,
                created_by=created_by,
                created_at=now,
                status=BranchStatus.ACTIVE,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO design_branches 
                    (id, project_id, name, base_branch, head_commit, created_by, created_at, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    branch.id,
                    branch.project_id,
                    branch.name,
                    branch.base_branch,
                    branch.head_commit,
                    branch.created_by,
                    branch.created_at.isoformat(),
                    branch.status.value,
                    json.dumps(branch.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created design branch: {branch_id}")
            return branch
            
        except Exception as e:
            logger.error(f"Failed to create design branch: {e}")
            return None
    
    def create_commit(self, branch_id: str, author_id: str, commit_type: CommitType,
                     diff_json: Dict[str, Any], message: str) -> Optional[DesignCommit]:
        """Create a new design commit"""
        try:
            commit_id = f"commit_{int(time.time())}"
            now = datetime.now()
            
            commit = DesignCommit(
                id=commit_id,
                branch_id=branch_id,
                author_id=author_id,
                commit_type=commit_type,
                diff_json=diff_json,
                message=message,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO design_commits 
                    (id, branch_id, author_id, commit_type, diff_json, message, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    commit.id,
                    commit.branch_id,
                    commit.author_id,
                    commit.commit_type.value,
                    json.dumps(commit.diff_json),
                    commit.message,
                    commit.created_at.isoformat(),
                    json.dumps(commit.metadata)
                ))
                
                # Update branch head commit
                cursor.execute('''
                    UPDATE design_branches 
                    SET head_commit = ?
                    WHERE id = ?
                ''', (commit_id, branch_id))
                conn.commit()
            
            logger.info(f"Created design commit: {commit_id}")
            return commit
            
        except Exception as e:
            logger.error(f"Failed to create design commit: {e}")
            return None
    
    def get_branch_commits(self, branch_id: str, limit: int = 50) -> List[DesignCommit]:
        """Get commits for a branch"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, branch_id, author_id, commit_type, diff_json, message, created_at, metadata
                    FROM design_commits 
                    WHERE branch_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (branch_id, limit))
                
                commits = []
                for row in cursor.fetchall():
                    commits.append(DesignCommit(
                        id=row[0],
                        branch_id=row[1],
                        author_id=row[2],
                        commit_type=CommitType(row[3]),
                        diff_json=json.loads(row[4]),
                        message=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    ))
                
                return commits
                
        except Exception as e:
            logger.error(f"Failed to get branch commits: {e}")
            return []
    
    def create_review(self, branch_id: str, reviewer_id: str, 
                     comments: List[Dict[str, Any]] = None) -> Optional[DesignReview]:
        """Create a new design review"""
        try:
            review_id = f"review_{int(time.time())}"
            now = datetime.now()
            
            review = DesignReview(
                id=review_id,
                branch_id=branch_id,
                reviewer_id=reviewer_id,
                state=ReviewState.OPEN,
                comments=comments or [],
                created_at=now,
                updated_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO design_reviews 
                    (id, branch_id, reviewer_id, state, comments, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    review.id,
                    review.branch_id,
                    review.reviewer_id,
                    review.state.value,
                    json.dumps(review.comments),
                    review.created_at.isoformat(),
                    review.updated_at.isoformat(),
                    json.dumps(review.metadata)
                ))
                conn.commit()
            
            logger.info(f"Created design review: {review_id}")
            return review
            
        except Exception as e:
            logger.error(f"Failed to create design review: {e}")
            return None
    
    def update_review_state(self, review_id: str, reviewer_id: str, 
                           state: ReviewState, comments: List[Dict[str, Any]] = None) -> bool:
        """Update review state"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE design_reviews 
                    SET state = ?, comments = ?, updated_at = ?
                    WHERE id = ? AND reviewer_id = ?
                ''', (
                    state.value,
                    json.dumps(comments or []),
                    datetime.now().isoformat(),
                    review_id,
                    reviewer_id
                ))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Updated review state: {review_id} -> {state.value}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Failed to update review state: {e}")
            return False
    
    def merge_branch(self, source_branch_id: str, target_branch_id: str, 
                    merged_by: str) -> bool:
        """Merge source branch into target branch"""
        try:
            # Get source branch commits
            source_commits = self.get_branch_commits(source_branch_id)
            if not source_commits:
                return False
            
            # Create merge commit
            merge_diff = {
                'type': 'merge',
                'source_branch': source_branch_id,
                'target_branch': target_branch_id,
                'commits_merged': len(source_commits)
            }
            
            merge_commit = self.create_commit(
                branch_id=target_branch_id,
                author_id=merged_by,
                commit_type=CommitType.METADATA_UPDATE,
                diff_json=merge_diff,
                message=f"Merged branch {source_branch_id} into {target_branch_id}"
            )
            
            if not merge_commit:
                return False
            
            # Update source branch status
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE design_branches 
                    SET status = ?
                    WHERE id = ?
                ''', (BranchStatus.MERGED.value, source_branch_id))
                conn.commit()
            
            # Update metrics
            metrics.increment_counter('sbh_design_merge_total')
            
            logger.info(f"Merged branch {source_branch_id} into {target_branch_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to merge branch: {e}")
            return False
    
    def get_project_branches(self, project_id: str) -> List[DesignBranch]:
        """Get all branches for a project"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, project_id, name, base_branch, head_commit, created_by, created_at, status, metadata
                    FROM design_branches 
                    WHERE project_id = ?
                    ORDER BY created_at DESC
                ''', (project_id,))
                
                branches = []
                for row in cursor.fetchall():
                    branches.append(DesignBranch(
                        id=row[0],
                        project_id=row[1],
                        name=row[2],
                        base_branch=row[3],
                        head_commit=row[4],
                        created_by=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        status=BranchStatus(row[7]),
                        metadata=json.loads(row[8]) if row[8] else {}
                    ))
                
                return branches
                
        except Exception as e:
            logger.error(f"Failed to get project branches: {e}")
            return []
    
    def get_branch_reviews(self, branch_id: str) -> List[DesignReview]:
        """Get all reviews for a branch"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, branch_id, reviewer_id, state, comments, created_at, updated_at, metadata
                    FROM design_reviews 
                    WHERE branch_id = ?
                    ORDER BY created_at DESC
                ''', (branch_id,))
                
                reviews = []
                for row in cursor.fetchall():
                    reviews.append(DesignReview(
                        id=row[0],
                        branch_id=row[1],
                        reviewer_id=row[2],
                        state=ReviewState(row[3]),
                        comments=json.loads(row[4]) if row[4] else [],
                        created_at=datetime.fromisoformat(row[5]),
                        updated_at=datetime.fromisoformat(row[6]),
                        metadata=json.loads(row[7]) if row[7] else {}
                    ))
                
                return reviews
                
        except Exception as e:
            logger.error(f"Failed to get branch reviews: {e}")
            return []

# Initialize service
design_versioning_service = DesignVersioningService()

# API Routes
@design_versioning_bp.route('/branch', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_branch():
    """Create a new design branch"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        name = data.get('name')
        base_branch = data.get('base_branch')
        
        if not all([project_id, name]):
            return jsonify({'error': 'project_id and name are required'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        branch = design_versioning_service.create_branch(
            project_id=project_id,
            name=name,
            base_branch=base_branch,
            created_by=user_id
        )
        
        if not branch:
            return jsonify({'error': 'Failed to create branch'}), 500
        
        return jsonify({
            'success': True,
            'branch': asdict(branch)
        })
        
    except Exception as e:
        logger.error(f"Create branch error: {e}")
        return jsonify({'error': str(e)}), 500

@design_versioning_bp.route('/commit', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_commit():
    """Create a new design commit"""
    try:
        data = request.get_json()
        branch_id = data.get('branch_id')
        commit_type = data.get('commit_type')
        diff_json = data.get('diff')
        message = data.get('message')
        
        if not all([branch_id, commit_type, diff_json, message]):
            return jsonify({'error': 'branch_id, commit_type, diff, and message are required'}), 400
        
        try:
            commit_type_enum = CommitType(commit_type)
        except ValueError:
            return jsonify({'error': 'Invalid commit_type'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        commit = design_versioning_service.create_commit(
            branch_id=branch_id,
            author_id=user_id,
            commit_type=commit_type_enum,
            diff_json=diff_json,
            message=message
        )
        
        if not commit:
            return jsonify({'error': 'Failed to create commit'}), 500
        
        return jsonify({
            'success': True,
            'commit': asdict(commit)
        })
        
    except Exception as e:
        logger.error(f"Create commit error: {e}")
        return jsonify({'error': str(e)}), 500

@design_versioning_bp.route('/commits', methods=['GET'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
def get_commits():
    """Get commits for a branch"""
    try:
        branch_id = request.args.get('branch_id')
        limit = int(request.args.get('limit', 50))
        
        if not branch_id:
            return jsonify({'error': 'branch_id is required'}), 400
        
        commits = design_versioning_service.get_branch_commits(branch_id, limit)
        
        return jsonify({
            'success': True,
            'commits': [asdict(c) for c in commits]
        })
        
    except Exception as e:
        logger.error(f"Get commits error: {e}")
        return jsonify({'error': str(e)}), 500

@design_versioning_bp.route('/merge', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def merge_branch():
    """Merge source branch into target branch"""
    try:
        data = request.get_json()
        source_branch_id = data.get('source_branch_id')
        target_branch_id = data.get('target_branch_id')
        
        if not all([source_branch_id, target_branch_id]):
            return jsonify({'error': 'source_branch_id and target_branch_id are required'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        success = design_versioning_service.merge_branch(
            source_branch_id=source_branch_id,
            target_branch_id=target_branch_id,
            merged_by=user_id
        )
        
        if not success:
            return jsonify({'error': 'Failed to merge branch'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Branch merged successfully'
        })
        
    except Exception as e:
        logger.error(f"Merge branch error: {e}")
        return jsonify({'error': str(e)}), 500

@design_versioning_bp.route('/review/<branch_id>', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_review(branch_id):
    """Create a new design review"""
    try:
        data = request.get_json()
        comments = data.get('comments', [])
        
        user_id = getattr(g, 'user_id', 'system')
        
        review = design_versioning_service.create_review(
            branch_id=branch_id,
            reviewer_id=user_id,
            comments=comments
        )
        
        if not review:
            return jsonify({'error': 'Failed to create review'}), 500
        
        return jsonify({
            'success': True,
            'review': asdict(review)
        })
        
    except Exception as e:
        logger.error(f"Create review error: {e}")
        return jsonify({'error': str(e)}), 500

@design_versioning_bp.route('/review/<review_id>/state', methods=['POST'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
@cost_accounted("api", "operation")
def update_review_state(review_id):
    """Update review state"""
    try:
        data = request.get_json()
        state = data.get('state')
        comments = data.get('comments', [])
        
        if not state:
            return jsonify({'error': 'state is required'}), 400
        
        try:
            review_state = ReviewState(state)
        except ValueError:
            return jsonify({'error': 'Invalid state'}), 400
        
        user_id = getattr(g, 'user_id', 'system')
        
        success = design_versioning_service.update_review_state(
            review_id=review_id,
            reviewer_id=user_id,
            state=review_state,
            comments=comments
        )
        
        if not success:
            return jsonify({'error': 'Failed to update review state'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Review state updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Update review state error: {e}")
        return jsonify({'error': str(e)}), 500

@design_versioning_bp.route('/branches', methods=['GET'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
def get_branches():
    """Get all branches for a project"""
    try:
        project_id = request.args.get('project_id')
        
        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400
        
        branches = design_versioning_service.get_project_branches(project_id)
        
        return jsonify({
            'success': True,
            'branches': [asdict(b) for b in branches]
        })
        
    except Exception as e:
        logger.error(f"Get branches error: {e}")
        return jsonify({'error': str(e)}), 500

@design_versioning_bp.route('/reviews/<branch_id>', methods=['GET'])
@cross_origin()
@flag_required('collab_versioning')
@require_tenant_context
def get_reviews(branch_id):
    """Get all reviews for a branch"""
    try:
        reviews = design_versioning_service.get_branch_reviews(branch_id)
        
        return jsonify({
            'success': True,
            'reviews': [asdict(r) for r in reviews]
        })
        
    except Exception as e:
        logger.error(f"Get reviews error: {e}")
        return jsonify({'error': str(e)}), 500
