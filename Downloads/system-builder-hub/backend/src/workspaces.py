#!/usr/bin/env python3
"""
P62: Team Workspaces & Shared Libraries
First-class team spaces with shared assets (teardowns, GTM plans, bench scripts, golden paths), granular roles, and audit.
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
workspaces_bp = Blueprint('workspaces', __name__, url_prefix='/api/workspace')

# Data Models
class WorkspaceRole(Enum):
    OWNER = "owner"
    MAINTAINER = "maintainer"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

class AssetKind(Enum):
    TEARDOWN = "teardown"
    GTM_PLAN = "gtm_plan"
    BENCH_SCRIPT = "bench_script"
    GOLDEN_PATH = "golden_path"
    TEMPLATE = "template"
    DOCUMENTATION = "documentation"
    CONFIG = "config"

@dataclass
class Workspace:
    id: str
    tenant_id: str
    name: str
    settings_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class WorkspaceMember:
    id: str
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    created_at: datetime
    metadata: Dict[str, Any]

@dataclass
class SharedAsset:
    id: str
    workspace_id: str
    kind: AssetKind
    uri: str
    meta_json: Dict[str, Any]
    created_at: datetime
    metadata: Dict[str, Any]

class WorkspaceService:
    """Service for workspace and shared library management"""
    
    def __init__(self):
        self._init_database()
        self._lock = threading.Lock()
    
    def _init_database(self):
        """Initialize workspace database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create workspaces table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS workspaces (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        settings_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create workspace_members table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS workspace_members (
                        id TEXT PRIMARY KEY,
                        workspace_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
                    )
                ''')
                
                # Create shared_assets table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS shared_assets (
                        id TEXT PRIMARY KEY,
                        workspace_id TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        uri TEXT NOT NULL,
                        meta_json TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
                    )
                ''')
                
                # Create indices for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_workspaces_tenant_id 
                    ON workspaces (tenant_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace_id 
                    ON workspace_members (workspace_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_workspace_members_user_id 
                    ON workspace_members (user_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_shared_assets_workspace_id 
                    ON shared_assets (workspace_id)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_shared_assets_kind 
                    ON shared_assets (kind)
                ''')
                
                conn.commit()
                logger.info("Workspace database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize workspace database: {e}")
    
    def create_workspace(self, tenant_id: str, name: str, 
                        settings_json: Dict[str, Any] = None) -> Optional[Workspace]:
        """Create a new workspace"""
        try:
            workspace_id = str(uuid.uuid4())
            now = datetime.now()
            
            if settings_json is None:
                settings_json = {}
            
            workspace = Workspace(
                id=workspace_id,
                tenant_id=tenant_id,
                name=name,
                settings_json=settings_json,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO workspaces 
                    (id, tenant_id, name, settings_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    workspace.id,
                    workspace.tenant_id,
                    workspace.name,
                    json.dumps(workspace.settings_json),
                    workspace.created_at.isoformat(),
                    json.dumps(workspace.metadata)
                ))
                conn.commit()
            
            # Record metrics
            metrics.counter('sbh_workspace_activity_events_total').inc()
            
            logger.info(f"Created workspace: {workspace_id} for tenant {tenant_id}")
            return workspace
            
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")
            return None
    
    def get_workspace(self, workspace_id: str, tenant_id: str) -> Optional[Workspace]:
        """Get workspace by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, name, settings_json, created_at, metadata
                    FROM workspaces 
                    WHERE id = ? AND tenant_id = ?
                ''', (workspace_id, tenant_id))
                
                row = cursor.fetchone()
                if row:
                    return Workspace(
                        id=row[0],
                        tenant_id=row[1],
                        name=row[2],
                        settings_json=json.loads(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        metadata=json.loads(row[5]) if row[5] else {}
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get workspace: {e}")
            return None
    
    def list_workspaces(self, tenant_id: str) -> List[Workspace]:
        """List all workspaces for tenant"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, tenant_id, name, settings_json, created_at, metadata
                    FROM workspaces 
                    WHERE tenant_id = ?
                    ORDER BY created_at DESC
                ''', (tenant_id,))
                
                rows = cursor.fetchall()
                workspaces = []
                for row in rows:
                    workspaces.append(Workspace(
                        id=row[0],
                        tenant_id=row[1],
                        name=row[2],
                        settings_json=json.loads(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        metadata=json.loads(row[5]) if row[5] else {}
                    ))
                
                return workspaces
                
        except Exception as e:
            logger.error(f"Failed to list workspaces: {e}")
            return []
    
    def add_workspace_member(self, workspace_id: str, user_id: str, 
                           role: WorkspaceRole, tenant_id: str) -> Optional[WorkspaceMember]:
        """Add member to workspace"""
        try:
            # Check if workspace exists and belongs to tenant
            workspace = self.get_workspace(workspace_id, tenant_id)
            if not workspace:
                return None
            
            # Check member limits
            current_members = self.get_workspace_members(workspace_id)
            if len(current_members) >= config.WORKSPACE_MAX_MEMBERS:
                logger.warning(f"Workspace {workspace_id} has reached member limit")
                return None
            
            member_id = str(uuid.uuid4())
            now = datetime.now()
            
            workspace_member = WorkspaceMember(
                id=member_id,
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO workspace_members 
                    (id, workspace_id, user_id, role, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    workspace_member.id,
                    workspace_member.workspace_id,
                    workspace_member.user_id,
                    workspace_member.role.value,
                    workspace_member.created_at.isoformat(),
                    json.dumps(workspace_member.metadata)
                ))
                conn.commit()
            
            # Record metrics
            metrics.counter('sbh_workspace_members_total').inc()
            metrics.counter('sbh_workspace_activity_events_total').inc()
            
            logger.info(f"Added member {user_id} to workspace {workspace_id} with role {role.value}")
            return workspace_member
            
        except Exception as e:
            logger.error(f"Failed to add workspace member: {e}")
            return None
    
    def get_workspace_members(self, workspace_id: str) -> List[WorkspaceMember]:
        """Get all members of a workspace"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, workspace_id, user_id, role, created_at, metadata
                    FROM workspace_members 
                    WHERE workspace_id = ?
                    ORDER BY created_at ASC
                ''', (workspace_id,))
                
                rows = cursor.fetchall()
                members = []
                for row in rows:
                    members.append(WorkspaceMember(
                        id=row[0],
                        workspace_id=row[1],
                        user_id=row[2],
                        role=WorkspaceRole(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        metadata=json.loads(row[5]) if row[5] else {}
                    ))
                
                return members
                
        except Exception as e:
            logger.error(f"Failed to get workspace members: {e}")
            return []
    
    def check_user_permission(self, workspace_id: str, user_id: str, 
                            required_role: WorkspaceRole) -> bool:
        """Check if user has required permission in workspace"""
        try:
            members = self.get_workspace_members(workspace_id)
            
            for member in members:
                if member.user_id == user_id:
                    # Check role hierarchy
                    if self._role_has_permission(member.role, required_role):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Permission check error: {e}")
            return False
    
    def share_asset(self, workspace_id: str, kind: AssetKind, uri: str, 
                   meta_json: Dict[str, Any], tenant_id: str) -> Optional[SharedAsset]:
        """Share an asset in workspace"""
        try:
            # Check if workspace exists and belongs to tenant
            workspace = self.get_workspace(workspace_id, tenant_id)
            if not workspace:
                return None
            
            # Check asset limits
            current_assets = self.list_shared_assets(workspace_id)
            if len(current_assets) >= config.WORKSPACE_MAX_SHARED_ASSETS:
                logger.warning(f"Workspace {workspace_id} has reached asset limit")
                return None
            
            asset_id = str(uuid.uuid4())
            now = datetime.now()
            
            shared_asset = SharedAsset(
                id=asset_id,
                workspace_id=workspace_id,
                kind=kind,
                uri=uri,
                meta_json=meta_json,
                created_at=now,
                metadata={}
            )
            
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO shared_assets 
                    (id, workspace_id, kind, uri, meta_json, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    shared_asset.id,
                    shared_asset.workspace_id,
                    shared_asset.kind.value,
                    shared_asset.uri,
                    json.dumps(shared_asset.meta_json),
                    shared_asset.created_at.isoformat(),
                    json.dumps(shared_asset.metadata)
                ))
                conn.commit()
            
            # Record metrics
            metrics.counter('sbh_shared_assets_total', {'kind': kind.value}).inc()
            metrics.counter('sbh_workspace_activity_events_total').inc()
            
            logger.info(f"Shared asset {asset_id} of kind {kind.value} in workspace {workspace_id}")
            return shared_asset
            
        except Exception as e:
            logger.error(f"Failed to share asset: {e}")
            return None
    
    def list_shared_assets(self, workspace_id: str, kind: Optional[AssetKind] = None) -> List[SharedAsset]:
        """List shared assets in workspace"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, workspace_id, kind, uri, meta_json, created_at, metadata
                    FROM shared_assets 
                    WHERE workspace_id = ?
                '''
                params = [workspace_id]
                
                if kind:
                    query += ' AND kind = ?'
                    params.append(kind.value)
                
                query += ' ORDER BY created_at DESC'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                assets = []
                for row in rows:
                    assets.append(SharedAsset(
                        id=row[0],
                        workspace_id=row[1],
                        kind=AssetKind(row[2]),
                        uri=row[3],
                        meta_json=json.loads(row[4]),
                        created_at=datetime.fromisoformat(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {}
                    ))
                
                return assets
                
        except Exception as e:
            logger.error(f"Failed to list shared assets: {e}")
            return []
    
    def _role_has_permission(self, user_role: WorkspaceRole, required_role: WorkspaceRole) -> bool:
        """Check if user role has permission for required role"""
        role_hierarchy = {
            WorkspaceRole.OWNER: 5,
            WorkspaceRole.MAINTAINER: 4,
            WorkspaceRole.EDITOR: 3,
            WorkspaceRole.REVIEWER: 2,
            WorkspaceRole.VIEWER: 1
        }
        
        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)

# Initialize service
workspace_service = WorkspaceService()

# API Routes
@workspaces_bp.route('/create', methods=['POST'])
@cross_origin()
@flag_required('workspaces')
@require_tenant_context
@idempotent()
@cost_accounted("api", "operation")
def create_workspace():
    """Create a new workspace"""
    try:
        data = request.get_json()
        name = data.get('name')
        settings_json = data.get('settings_json', {})
        
        if not name:
            return jsonify({'error': 'name is required'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        workspace = workspace_service.create_workspace(
            tenant_id=tenant_id,
            name=name,
            settings_json=settings_json
        )
        
        if not workspace:
            return jsonify({'error': 'Failed to create workspace'}), 500
        
        return jsonify({
            'success': True,
            'workspace_id': workspace.id,
            'workspace': asdict(workspace)
        })
        
    except Exception as e:
        logger.error(f"Create workspace error: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/member/add', methods=['POST'])
@cross_origin()
@flag_required('workspaces')
@require_tenant_context
@cost_accounted("api", "operation")
def add_workspace_member():
    """Add member to workspace"""
    try:
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        user_id = data.get('user_id')
        role = data.get('role')
        
        if not all([workspace_id, user_id, role]):
            return jsonify({'error': 'workspace_id, user_id, and role are required'}), 400
        
        try:
            workspace_role = WorkspaceRole(role)
        except ValueError:
            return jsonify({'error': 'Invalid role'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        workspace_member = workspace_service.add_workspace_member(
            workspace_id=workspace_id,
            user_id=user_id,
            role=workspace_role,
            tenant_id=tenant_id
        )
        
        if not workspace_member:
            return jsonify({'error': 'Failed to add workspace member'}), 500
        
        return jsonify({
            'success': True,
            'member_id': workspace_member.id,
            'workspace_member': asdict(workspace_member)
        })
        
    except Exception as e:
        logger.error(f"Add workspace member error: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/<workspace_id>', methods=['GET'])
@cross_origin()
@flag_required('workspaces')
@require_tenant_context
def get_workspace(workspace_id):
    """Get workspace details"""
    try:
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        workspace = workspace_service.get_workspace(workspace_id, tenant_id)
        
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        # Get members
        members = workspace_service.get_workspace_members(workspace_id)
        
        return jsonify({
            'success': True,
            'workspace': asdict(workspace),
            'members': [asdict(member) for member in members]
        })
        
    except Exception as e:
        logger.error(f"Get workspace error: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/library/share', methods=['POST'])
@cross_origin()
@flag_required('workspaces')
@require_tenant_context
@cost_accounted("api", "operation")
def share_asset():
    """Share an asset in workspace"""
    try:
        data = request.get_json()
        workspace_id = data.get('workspace_id')
        kind = data.get('kind')
        uri = data.get('uri')
        meta_json = data.get('meta_json', {})
        
        if not all([workspace_id, kind, uri]):
            return jsonify({'error': 'workspace_id, kind, and uri are required'}), 400
        
        try:
            asset_kind = AssetKind(kind)
        except ValueError:
            return jsonify({'error': 'Invalid asset kind'}), 400
        
        tenant_id = getattr(g, 'tenant_id', 'default')
        
        shared_asset = workspace_service.share_asset(
            workspace_id=workspace_id,
            kind=asset_kind,
            uri=uri,
            meta_json=meta_json,
            tenant_id=tenant_id
        )
        
        if not shared_asset:
            return jsonify({'error': 'Failed to share asset'}), 500
        
        return jsonify({
            'success': True,
            'asset_id': shared_asset.id,
            'shared_asset': asdict(shared_asset)
        })
        
    except Exception as e:
        logger.error(f"Share asset error: {e}")
        return jsonify({'error': str(e)}), 500

@workspaces_bp.route('/library/list', methods=['GET'])
@cross_origin()
@flag_required('workspaces')
@require_tenant_context
def list_shared_assets():
    """List shared assets in workspace"""
    try:
        workspace_id = request.args.get('workspace_id')
        kind = request.args.get('kind')
        
        if not workspace_id:
            return jsonify({'error': 'workspace_id is required'}), 400
        
        asset_kind = None
        if kind:
            try:
                asset_kind = AssetKind(kind)
            except ValueError:
                return jsonify({'error': 'Invalid asset kind'}), 400
        
        assets = workspace_service.list_shared_assets(workspace_id, asset_kind)
        
        return jsonify({
            'success': True,
            'assets': [asdict(asset) for asset in assets]
        })
        
    except Exception as e:
        logger.error(f"List shared assets error: {e}")
        return jsonify({'error': str(e)}), 500
