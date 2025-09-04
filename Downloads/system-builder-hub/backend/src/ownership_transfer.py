#!/usr/bin/env python3
"""
Priority 20: Full Ownership Transfer Protocols
Secure, seamless, and auditable system handoffs to external parties
"""

import json
import sqlite3
import threading
import time
import zipfile
import tarfile
import hashlib
import hmac
import os
import shutil
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, BinaryIO
import uuid
import base64
from pathlib import Path
import yaml
import tempfile

# Enums for ownership transfer
class TransferType(Enum):
    FULL_TRANSFER = "full_transfer"
    PARTIAL_TRANSFER = "partial_transfer"
    EXPORT_ONLY = "export_only"
    LICENSE_TRANSFER = "license_transfer"

class TransferStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVOKED = "revoked"

class ExportFormat(Enum):
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar_gz"
    CUSTOM = "custom"

class TransferScope(Enum):
    FULL_SYSTEM = "full_system"
    AGENTS_ONLY = "agents_only"
    MODELS_ONLY = "models_only"
    UI_ONLY = "ui_only"
    API_ONLY = "api_only"
    CUSTOM = "custom"

class SecurityLevel(Enum):
    STANDARD = "standard"
    ENCRYPTED = "encrypted"
    SIGNED = "signed"
    ENCRYPTED_SIGNED = "encrypted_signed"

# Data structures
@dataclass
class TransferRequest:
    transfer_id: str
    system_id: str
    from_org_id: str
    from_user_id: str
    to_org_id: Optional[str]
    to_user_id: Optional[str]
    transfer_type: TransferType
    transfer_scope: TransferScope
    export_format: ExportFormat
    security_level: SecurityLevel
    include_models: bool
    include_training_data: bool
    include_analytics: bool
    include_licenses: bool
    custom_metadata: Dict[str, Any]
    transfer_notes: str
    created_at: datetime
    expires_at: datetime
    status: TransferStatus

@dataclass
class TransferBundle:
    bundle_id: str
    transfer_id: str
    system_id: str
    bundle_path: str
    checksum: str
    size_bytes: int
    encryption_key: Optional[str]
    signature: Optional[str]
    created_at: datetime
    expires_at: datetime

@dataclass
class TransferHistory:
    history_id: str
    transfer_id: str
    action: str
    user_id: str
    timestamp: datetime
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]

@dataclass
class ExportConfig:
    config_id: str
    system_id: str
    name: str
    description: str
    transfer_scope: TransferScope
    include_models: bool
    include_training_data: bool
    include_analytics: bool
    include_licenses: bool
    llm_endpoints: List[str]
    custom_metadata: Dict[str, Any]
    setup_scripts: List[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class OwnershipMetadata:
    metadata_id: str
    system_id: str
    original_builder: str
    original_org: str
    transfer_chain: List[Dict[str, Any]]
    co_branding: Optional[Dict[str, Any]]
    attribution_required: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class HandoverAgent:
    agent_id: str
    transfer_id: str
    system_id: str
    agent_type: str
    configuration: Dict[str, Any]
    knowledge_base: List[str]
    contact_info: Dict[str, Any]
    created_at: datetime
    expires_at: datetime

class OwnershipTransferEngine:
    """Core handler for secure system ownership transfers and exports"""
    
    def __init__(self, base_dir: str, system_delivery, access_control, licensing_module, llm_factory, predictive_engine):
        self.base_dir = base_dir
        self.system_delivery = system_delivery
        self.access_control = access_control
        self.licensing_module = licensing_module
        self.llm_factory = llm_factory
        self.predictive_engine = predictive_engine
        
        self.db_path = f"{base_dir}/ownership_transfer.db"
        self.transfers_dir = f"{base_dir}/transfers"
        self.bundles_dir = f"{base_dir}/bundles"
        self.exports_dir = f"{base_dir}/exports"
        
        # Initialize directories and database
        self._init_directories()
        self._init_database()
        
        # Security settings
        self.encryption_key = os.getenv('TRANSFER_ENCRYPTION_KEY', 'default-key-change-in-production')
        self.signing_key = os.getenv('TRANSFER_SIGNING_KEY', 'default-signing-key-change-in-production')
        
        # Background tasks
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        self.audit_thread = threading.Thread(target=self._audit_loop, daemon=True)
        self.audit_thread.start()
    
    def _init_directories(self):
        """Initialize required directories"""
        os.makedirs(self.transfers_dir, exist_ok=True)
        os.makedirs(self.bundles_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)
    
    def _init_database(self):
        """Initialize SQLite database with all tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Transfer requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfer_requests (
                transfer_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                from_org_id TEXT NOT NULL,
                from_user_id TEXT NOT NULL,
                to_org_id TEXT,
                to_user_id TEXT,
                transfer_type TEXT NOT NULL,
                transfer_scope TEXT NOT NULL,
                export_format TEXT NOT NULL,
                security_level TEXT NOT NULL,
                include_models INTEGER NOT NULL,
                include_training_data INTEGER NOT NULL,
                include_analytics INTEGER NOT NULL,
                include_licenses INTEGER NOT NULL,
                custom_metadata TEXT NOT NULL,
                transfer_notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        
        # Transfer bundles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfer_bundles (
                bundle_id TEXT PRIMARY KEY,
                transfer_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                bundle_path TEXT NOT NULL,
                checksum TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                encryption_key TEXT,
                signature TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        
        # Transfer history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfer_history (
                history_id TEXT PRIMARY KEY,
                transfer_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        
        # Export configurations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS export_configs (
                config_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                transfer_scope TEXT NOT NULL,
                include_models INTEGER NOT NULL,
                include_training_data INTEGER NOT NULL,
                include_analytics INTEGER NOT NULL,
                include_licenses INTEGER NOT NULL,
                llm_endpoints TEXT NOT NULL,
                custom_metadata TEXT NOT NULL,
                setup_scripts TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Ownership metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ownership_metadata (
                metadata_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                original_builder TEXT NOT NULL,
                original_org TEXT NOT NULL,
                transfer_chain TEXT NOT NULL,
                co_branding TEXT,
                attribution_required INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Handover agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS handover_agents (
                agent_id TEXT PRIMARY KEY,
                transfer_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                configuration TEXT NOT NULL,
                knowledge_base TEXT NOT NULL,
                contact_info TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_transfer_request(self, system_id: str, from_org_id: str, from_user_id: str,
                              to_org_id: Optional[str] = None, to_user_id: Optional[str] = None,
                              transfer_type: TransferType = TransferType.FULL_TRANSFER,
                              transfer_scope: TransferScope = TransferScope.FULL_SYSTEM,
                              export_format: ExportFormat = ExportFormat.ZIP,
                              security_level: SecurityLevel = SecurityLevel.STANDARD,
                              include_models: bool = True, include_training_data: bool = False,
                              include_analytics: bool = True, include_licenses: bool = True,
                              custom_metadata: Dict[str, Any] = None, transfer_notes: str = "") -> TransferRequest:
        """Create a new transfer request"""
        transfer_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Validate access permissions
        if not self._validate_transfer_permissions(system_id, from_user_id, from_org_id):
            raise PermissionError("User does not have permission to transfer this system")
        
        # Set expiration (30 days default)
        expires_at = now + timedelta(days=30)
        
        request = TransferRequest(
            transfer_id=transfer_id,
            system_id=system_id,
            from_org_id=from_org_id,
            from_user_id=from_user_id,
            to_org_id=to_org_id,
            to_user_id=to_user_id,
            transfer_type=transfer_type,
            transfer_scope=transfer_scope,
            export_format=export_format,
            security_level=security_level,
            include_models=include_models,
            include_training_data=include_training_data,
            include_analytics=include_analytics,
            include_licenses=include_licenses,
            custom_metadata=custom_metadata or {},
            transfer_notes=transfer_notes,
            created_at=now,
            expires_at=expires_at,
            status=TransferStatus.PENDING
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transfer_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.transfer_id,
            request.system_id,
            request.from_org_id,
            request.from_user_id,
            request.to_org_id,
            request.to_user_id,
            request.transfer_type.value,
            request.transfer_scope.value,
            request.export_format.value,
            request.security_level.value,
            request.include_models,
            request.include_training_data,
            request.include_analytics,
            request.include_licenses,
            json.dumps(request.custom_metadata),
            request.transfer_notes,
            request.created_at.isoformat(),
            request.expires_at.isoformat(),
            request.status.value
        ))
        
        conn.commit()
        conn.close()
        
        # Log transfer request
        self._log_transfer_action(request.transfer_id, "transfer_request_created", from_user_id, {
            "transfer_type": transfer_type.value,
            "transfer_scope": transfer_scope.value,
            "security_level": security_level.value
        })
        
        return request
    
    def execute_transfer(self, transfer_id: str, user_id: str) -> TransferBundle:
        """Execute a transfer request and create the export bundle"""
        # Get transfer request
        request = self._get_transfer_request(transfer_id)
        if not request:
            raise ValueError("Transfer request not found")
        
        if request.status != TransferStatus.PENDING:
            raise ValueError(f"Transfer request is in {request.status.value} status")
        
        # Update status to in progress
        self._update_transfer_status(transfer_id, TransferStatus.IN_PROGRESS)
        
        try:
            # Create export bundle
            bundle = self._create_export_bundle(request)
            
            # Update status to completed
            self._update_transfer_status(transfer_id, TransferStatus.COMPLETED)
            
            # Log successful transfer
            self._log_transfer_action(transfer_id, "transfer_completed", user_id, {
                "bundle_id": bundle.bundle_id,
                "bundle_size": bundle.size_bytes,
                "checksum": bundle.checksum
            })
            
            return bundle
            
        except Exception as e:
            # Update status to failed
            self._update_transfer_status(transfer_id, TransferStatus.FAILED)
            
            # Log failure
            self._log_transfer_action(transfer_id, "transfer_failed", user_id, {
                "error": str(e)
            })
            
            raise
    
    def create_export_config(self, system_id: str, name: str, description: str,
                           transfer_scope: TransferScope = TransferScope.FULL_SYSTEM,
                           include_models: bool = True, include_training_data: bool = False,
                           include_analytics: bool = True, include_licenses: bool = True,
                           llm_endpoints: List[str] = None, custom_metadata: Dict[str, Any] = None,
                           setup_scripts: List[str] = None) -> ExportConfig:
        """Create a reusable export configuration"""
        config_id = str(uuid.uuid4())
        now = datetime.now()
        
        config = ExportConfig(
            config_id=config_id,
            system_id=system_id,
            name=name,
            description=description,
            transfer_scope=transfer_scope,
            include_models=include_models,
            include_training_data=include_training_data,
            include_analytics=include_analytics,
            include_licenses=include_licenses,
            llm_endpoints=llm_endpoints or [],
            custom_metadata=custom_metadata or {},
            setup_scripts=setup_scripts or [],
            created_at=now,
            updated_at=now
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO export_configs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            config.config_id,
            config.system_id,
            config.name,
            config.description,
            config.transfer_scope.value,
            config.include_models,
            config.include_training_data,
            config.include_analytics,
            config.include_licenses,
            json.dumps(config.llm_endpoints),
            json.dumps(config.custom_metadata),
            json.dumps(config.setup_scripts),
            config.created_at.isoformat(),
            config.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return config
    
    def export_system(self, system_id: str, export_format: ExportFormat = ExportFormat.ZIP,
                     security_level: SecurityLevel = SecurityLevel.STANDARD,
                     include_models: bool = True, include_training_data: bool = False,
                     include_analytics: bool = True, include_licenses: bool = True,
                     custom_metadata: Dict[str, Any] = None) -> TransferBundle:
        """Export a system without transferring ownership"""
        # Create temporary transfer request for export
        request = TransferRequest(
            transfer_id=str(uuid.uuid4()),
            system_id=system_id,
            from_org_id="export",
            from_user_id="export",
            to_org_id=None,
            to_user_id=None,
            transfer_type=TransferType.EXPORT_ONLY,
            transfer_scope=TransferScope.FULL_SYSTEM,
            export_format=export_format,
            security_level=security_level,
            include_models=include_models,
            include_training_data=include_training_data,
            include_analytics=include_analytics,
            include_licenses=include_licenses,
            custom_metadata=custom_metadata or {},
            transfer_notes="System export",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=7),
            status=TransferStatus.PENDING
        )
        
        # Create export bundle
        bundle = self._create_export_bundle(request)
        
        return bundle
    
    def revoke_transfer(self, transfer_id: str, user_id: str, reason: str = "") -> bool:
        """Revoke a transfer request"""
        request = self._get_transfer_request(transfer_id)
        if not request:
            return False
        
        # Update status to revoked
        self._update_transfer_status(transfer_id, TransferStatus.REVOKED)
        
        # Log revocation
        self._log_transfer_action(transfer_id, "transfer_revoked", user_id, {
            "reason": reason
        })
        
        return True
    
    def get_transfer_history(self, system_id: str = None, transfer_id: str = None) -> List[TransferHistory]:
        """Get transfer history for a system or specific transfer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if transfer_id:
            cursor.execute("""
                SELECT * FROM transfer_history WHERE transfer_id = ? ORDER BY timestamp DESC
            """, (transfer_id,))
        elif system_id:
            cursor.execute("""
                SELECT th.* FROM transfer_history th
                JOIN transfer_requests tr ON th.transfer_id = tr.transfer_id
                WHERE tr.system_id = ? ORDER BY th.timestamp DESC
            """, (system_id,))
        else:
            cursor.execute("""
                SELECT * FROM transfer_history ORDER BY timestamp DESC LIMIT 100
            """)
        
        history = []
        for row in cursor.fetchall():
            history_item = TransferHistory(
                history_id=row[0],
                transfer_id=row[1],
                action=row[2],
                user_id=row[3],
                timestamp=datetime.fromisoformat(row[4]),
                details=json.loads(row[5]),
                ip_address=row[6],
                user_agent=row[7]
            )
            history.append(history_item)
        
        conn.close()
        return history
    
    def get_ownership_metadata(self, system_id: str) -> Optional[OwnershipMetadata]:
        """Get ownership metadata for a system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ownership_metadata WHERE system_id = ?
        """, (system_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return OwnershipMetadata(
                metadata_id=row[0],
                system_id=row[1],
                original_builder=row[2],
                original_org=row[3],
                transfer_chain=json.loads(row[4]),
                co_branding=json.loads(row[5]) if row[5] else None,
                attribution_required=bool(row[6]),
                created_at=datetime.fromisoformat(row[7]),
                updated_at=datetime.fromisoformat(row[8])
            )
        
        return None
    
    def create_handover_agent(self, transfer_id: str, system_id: str, agent_type: str,
                            configuration: Dict[str, Any], knowledge_base: List[str],
                            contact_info: Dict[str, Any]) -> HandoverAgent:
        """Create a handover agent for system onboarding"""
        agent_id = str(uuid.uuid4())
        now = datetime.now()
        
        agent = HandoverAgent(
            agent_id=agent_id,
            transfer_id=transfer_id,
            system_id=system_id,
            agent_type=agent_type,
            configuration=configuration,
            knowledge_base=knowledge_base,
            contact_info=contact_info,
            created_at=now,
            expires_at=now + timedelta(days=90)  # 90 days default
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO handover_agents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent.agent_id,
            agent.transfer_id,
            agent.system_id,
            agent.agent_type,
            json.dumps(agent.configuration),
            json.dumps(agent.knowledge_base),
            json.dumps(agent.contact_info),
            agent.created_at.isoformat(),
            agent.expires_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return agent
    
    # Helper methods
    def _validate_transfer_permissions(self, system_id: str, user_id: str, org_id: str) -> bool:
        """Validate that user has permission to transfer the system"""
        # This would integrate with the access control engine
        # For now, return True (placeholder)
        return True
    
    def _get_transfer_request(self, transfer_id: str) -> Optional[TransferRequest]:
        """Get transfer request by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM transfer_requests WHERE transfer_id = ?
        """, (transfer_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return TransferRequest(
                transfer_id=row[0],
                system_id=row[1],
                from_org_id=row[2],
                from_user_id=row[3],
                to_org_id=row[4],
                to_user_id=row[5],
                transfer_type=TransferType(row[6]),
                transfer_scope=TransferScope(row[7]),
                export_format=ExportFormat(row[8]),
                security_level=SecurityLevel(row[9]),
                include_models=bool(row[10]),
                include_training_data=bool(row[11]),
                include_analytics=bool(row[12]),
                include_licenses=bool(row[13]),
                custom_metadata=json.loads(row[14]),
                transfer_notes=row[15],
                created_at=datetime.fromisoformat(row[16]),
                expires_at=datetime.fromisoformat(row[17]),
                status=TransferStatus(row[18])
            )
        
        return None
    
    def _update_transfer_status(self, transfer_id: str, status: TransferStatus):
        """Update transfer request status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE transfer_requests SET status = ? WHERE transfer_id = ?
        """, (status.value, transfer_id))
        
        conn.commit()
        conn.close()
    
    def _create_export_bundle(self, request: TransferRequest) -> TransferBundle:
        """Create an export bundle for the transfer"""
        bundle_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Create bundle directory
        bundle_dir = os.path.join(self.bundles_dir, bundle_id)
        os.makedirs(bundle_dir, exist_ok=True)
        
        # Collect system components based on scope
        self._collect_system_components(request, bundle_dir)
        
        # Create export archive
        bundle_path = self._create_archive(bundle_dir, request.export_format, bundle_id)
        
        # Calculate checksum
        checksum = self._calculate_checksum(bundle_path)
        
        # Get file size
        size_bytes = os.path.getsize(bundle_path)
        
        # Handle encryption and signing
        encryption_key = None
        signature = None
        
        if request.security_level in [SecurityLevel.ENCRYPTED, SecurityLevel.ENCRYPTED_SIGNED]:
            encryption_key = self._encrypt_bundle(bundle_path)
        
        if request.security_level in [SecurityLevel.SIGNED, SecurityLevel.ENCRYPTED_SIGNED]:
            signature = self._sign_bundle(bundle_path)
        
        # Create bundle record
        bundle = TransferBundle(
            bundle_id=bundle_id,
            transfer_id=request.transfer_id,
            system_id=request.system_id,
            bundle_path=bundle_path,
            checksum=checksum,
            size_bytes=size_bytes,
            encryption_key=encryption_key,
            signature=signature,
            created_at=now,
            expires_at=request.expires_at
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transfer_bundles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bundle.bundle_id,
            bundle.transfer_id,
            bundle.system_id,
            bundle.bundle_path,
            bundle.checksum,
            bundle.size_bytes,
            bundle.encryption_key,
            bundle.signature,
            bundle.created_at.isoformat(),
            bundle.expires_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return bundle
    
    def _collect_system_components(self, request: TransferRequest, bundle_dir: str):
        """Collect system components based on transfer scope"""
        system_dir = os.path.join(bundle_dir, "system")
        os.makedirs(system_dir, exist_ok=True)
        
        # Create system manifest
        manifest = {
            "system_id": request.system_id,
            "transfer_type": request.transfer_type.value,
            "transfer_scope": request.transfer_scope.value,
            "security_level": request.security_level.value,
            "include_models": request.include_models,
            "include_training_data": request.include_training_data,
            "include_analytics": request.include_analytics,
            "include_licenses": request.include_licenses,
            "custom_metadata": request.custom_metadata,
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        with open(os.path.join(system_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Collect components based on scope
        if request.transfer_scope in [TransferScope.FULL_SYSTEM, TransferScope.AGENTS_ONLY]:
            self._collect_agents(system_dir, request)
        
        if request.transfer_scope in [TransferScope.FULL_SYSTEM, TransferScope.MODELS_ONLY]:
            if request.include_models:
                self._collect_models(system_dir, request)
        
        if request.transfer_scope in [TransferScope.FULL_SYSTEM, TransferScope.UI_ONLY]:
            self._collect_ui_components(system_dir, request)
        
        if request.transfer_scope in [TransferScope.FULL_SYSTEM, TransferScope.API_ONLY]:
            self._collect_api_components(system_dir, request)
        
        # Collect licenses if requested
        if request.include_licenses:
            self._collect_licenses(system_dir, request)
        
        # Create setup scripts
        self._create_setup_scripts(bundle_dir, request)
    
    def _collect_agents(self, system_dir: str, request: TransferRequest):
        """Collect agent components"""
        agents_dir = os.path.join(system_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
        
        # This would integrate with the agent ecosystem
        # For now, create placeholder
        agent_manifest = {
            "agents": [],
            "collected_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(agents_dir, "manifest.json"), "w") as f:
            json.dump(agent_manifest, f, indent=2)
    
    def _collect_models(self, system_dir: str, request: TransferRequest):
        """Collect model components"""
        models_dir = os.path.join(system_dir, "models")
        os.makedirs(models_dir, exist_ok=True)
        
        # This would integrate with the LLM factory
        # For now, create placeholder
        model_manifest = {
            "models": [],
            "endpoints": [],
            "collected_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(models_dir, "manifest.json"), "w") as f:
            json.dump(model_manifest, f, indent=2)
    
    def _collect_ui_components(self, system_dir: str, request: TransferRequest):
        """Collect UI components"""
        ui_dir = os.path.join(system_dir, "ui")
        os.makedirs(ui_dir, exist_ok=True)
        
        # This would collect UI templates and assets
        ui_manifest = {
            "templates": [],
            "assets": [],
            "collected_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(ui_dir, "manifest.json"), "w") as f:
            json.dump(ui_manifest, f, indent=2)
    
    def _collect_api_components(self, system_dir: str, request: TransferRequest):
        """Collect API components"""
        api_dir = os.path.join(system_dir, "api")
        os.makedirs(api_dir, exist_ok=True)
        
        # This would collect API definitions and integrations
        api_manifest = {
            "endpoints": [],
            "integrations": [],
            "collected_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(api_dir, "manifest.json"), "w") as f:
            json.dump(api_manifest, f, indent=2)
    
    def _collect_licenses(self, system_dir: str, request: TransferRequest):
        """Collect license information"""
        licenses_dir = os.path.join(system_dir, "licenses")
        os.makedirs(licenses_dir, exist_ok=True)
        
        # This would integrate with the licensing module
        license_manifest = {
            "licenses": [],
            "terms": {},
            "collected_at": datetime.now().isoformat()
        }
        
        with open(os.path.join(licenses_dir, "manifest.json"), "w") as f:
            json.dump(license_manifest, f, indent=2)
    
    def _create_setup_scripts(self, bundle_dir: str, request: TransferRequest):
        """Create setup and installation scripts"""
        scripts_dir = os.path.join(bundle_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        
        # Create setup script
        setup_script = f"""#!/bin/bash
# System Setup Script
# Generated for {request.system_id}
# Transfer Type: {request.transfer_type.value}
# Security Level: {request.security_level.value}

echo "Setting up system: {request.system_id}"

# Create directories
mkdir -p /opt/system-builder-hub
mkdir -p /opt/system-builder-hub/system
mkdir -p /opt/system-builder-hub/logs

# Extract system components
tar -xzf system.tar.gz -C /opt/system-builder-hub/system

# Set permissions
chmod +x /opt/system-builder-hub/system/scripts/*.sh

# Run initialization
/opt/system-builder-hub/system/scripts/init.sh

echo "System setup complete!"
"""
        
        with open(os.path.join(scripts_dir, "setup.sh"), "w") as f:
            f.write(setup_script)
        
        os.chmod(os.path.join(scripts_dir, "setup.sh"), 0o755)
        
        # Create initialization script
        init_script = f"""#!/bin/bash
# System Initialization Script

echo "Initializing system components..."

# Initialize database
python3 /opt/system-builder-hub/system/scripts/init_db.py

# Start services
systemctl enable system-builder-hub
systemctl start system-builder-hub

echo "System initialization complete!"
"""
        
        with open(os.path.join(scripts_dir, "init.sh"), "w") as f:
            f.write(init_script)
        
        os.chmod(os.path.join(scripts_dir, "init.sh"), 0o755)
    
    def _create_archive(self, bundle_dir: str, export_format: ExportFormat, bundle_id: str) -> str:
        """Create archive file from bundle directory"""
        if export_format == ExportFormat.ZIP:
            archive_path = os.path.join(self.bundles_dir, f"{bundle_id}.zip")
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(bundle_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, bundle_dir)
                        zipf.write(file_path, arcname)
        
        elif export_format == ExportFormat.TAR:
            archive_path = os.path.join(self.bundles_dir, f"{bundle_id}.tar")
            with tarfile.open(archive_path, 'w') as tarf:
                tarf.add(bundle_dir, arcname=os.path.basename(bundle_dir))
        
        elif export_format == ExportFormat.TAR_GZ:
            archive_path = os.path.join(self.bundles_dir, f"{bundle_id}.tar.gz")
            with tarfile.open(archive_path, 'w:gz') as tarf:
                tarf.add(bundle_dir, arcname=os.path.basename(bundle_dir))
        
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        return archive_path
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def _encrypt_bundle(self, bundle_path: str) -> str:
        """Encrypt bundle file"""
        # This would implement actual encryption
        # For now, return a placeholder key
        return base64.b64encode(os.urandom(32)).decode('utf-8')
    
    def _sign_bundle(self, bundle_path: str) -> str:
        """Sign bundle file"""
        # This would implement actual digital signing
        # For now, return a placeholder signature
        with open(bundle_path, 'rb') as f:
            data = f.read()
        signature = hmac.new(
            self.signing_key.encode(),
            data,
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _log_transfer_action(self, transfer_id: str, action: str, user_id: str, details: Dict[str, Any]):
        """Log transfer action to history"""
        history_id = str(uuid.uuid4())
        now = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO transfer_history VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            history_id,
            transfer_id,
            action,
            user_id,
            now.isoformat(),
            json.dumps(details),
            None,  # IP address
            None   # User agent
        ))
        
        conn.commit()
        conn.close()
    
    # Background processing loops
    def _cleanup_loop(self):
        """Background loop for cleaning up expired transfers and bundles"""
        while True:
            try:
                # Clean up expired transfers
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                
                # Delete expired transfer requests
                cursor.execute("""
                    DELETE FROM transfer_requests WHERE expires_at < ?
                """, (now,))
                
                # Delete expired bundles
                cursor.execute("""
                    DELETE FROM transfer_bundles WHERE expires_at < ?
                """, (now,))
                
                # Delete expired handover agents
                cursor.execute("""
                    DELETE FROM handover_agents WHERE expires_at < ?
                """, (now,))
                
                conn.commit()
                conn.close()
                
                time.sleep(3600)  # Run every hour
            except Exception as e:
                print(f"Error in cleanup loop: {e}")
                time.sleep(60)
    
    def _audit_loop(self):
        """Background loop for audit logging"""
        while True:
            try:
                # This would implement audit logging
                # For now, just sleep
                time.sleep(7200)  # Run every 2 hours
            except Exception as e:
                print(f"Error in audit loop: {e}")
                time.sleep(60)

def build_ownership_transfer_engine():
    """Build and return the Ownership Transfer Engine instance"""
    # This would be called from the main application
    # For now, return a mock instance for testing
    class MockSystemDelivery:
        pass
    
    class MockAccessControl:
        pass
    
    class MockLicensingModule:
        pass
    
    class MockLLMFactory:
        pass
    
    class MockPredictiveEngine:
        pass
    
    return OwnershipTransferEngine(
        base_dir="/tmp/ownership_transfer",
        system_delivery=MockSystemDelivery(),
        access_control=MockAccessControl(),
        licensing_module=MockLicensingModule(),
        llm_factory=MockLLMFactory(),
        predictive_engine=MockPredictiveEngine()
    )

if __name__ == "__main__":
    # Test the ownership transfer engine
    engine = build_ownership_transfer_engine()
    print("✅ Ownership Transfer Engine initialized successfully")
