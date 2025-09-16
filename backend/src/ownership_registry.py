#!/usr/bin/env python3
"""
Ownership Registry for System Builder Hub
Handles ownership buyouts, licenses, exports, and entitlements.
"""

import os
import json
import time
import logging
import sqlite3
import hashlib
import tempfile
import shutil
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from flask import current_app, g
from config import config

logger = logging.getLogger(__name__)

class BuyoutStatus(Enum):
    """Buyout status"""
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ExportStatus(Enum):
    """Export status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

class LicenseType(Enum):
    """License types"""
    EVALUATION = "evaluation"
    STANDARD = "standard"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

@dataclass
class BuyoutRequest:
    """Ownership buyout request"""
    id: str
    user_id: str
    tenant_id: str
    system_id: str
    buyout_type: str
    amount: float
    currency: str
    status: BuyoutStatus
    description: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

@dataclass
class License:
    """Software license"""
    id: str
    user_id: str
    tenant_id: str
    license_type: LicenseType
    license_key: str
    features: Dict[str, Any]
    valid_from: datetime
    valid_until: datetime
    max_users: int
    active: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class Export:
    """System export"""
    id: str
    user_id: str
    tenant_id: str
    system_id: str
    export_type: str
    status: ExportStatus
    file_path: Optional[str]
    file_size: int
    checksum: str
    expires_at: datetime
    metadata: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime]

@dataclass
class Entitlement:
    """User entitlement"""
    id: str
    user_id: str
    tenant_id: str
    feature: str
    enabled: bool
    limits: Dict[str, int]
    valid_from: datetime
    valid_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class OwnershipRegistry:
    """Manages ownership, buyouts, licenses, and exports"""
    
    def __init__(self):
        self._init_database()
    
    def _init_database(self):
        """Initialize ownership registry database tables"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                # Create buyouts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS buyouts (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        buyout_type TEXT NOT NULL,
                        amount REAL NOT NULL,
                        currency TEXT NOT NULL,
                        status TEXT NOT NULL,
                        description TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP
                    )
                ''')
                
                # Create licenses table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS licenses (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        license_type TEXT NOT NULL,
                        license_key TEXT NOT NULL UNIQUE,
                        features TEXT,
                        valid_from TIMESTAMP NOT NULL,
                        valid_until TIMESTAMP NOT NULL,
                        max_users INTEGER NOT NULL,
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # Create exports table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS exports (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        system_id TEXT NOT NULL,
                        export_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        file_path TEXT,
                        file_size INTEGER DEFAULT 0,
                        checksum TEXT,
                        expires_at TIMESTAMP NOT NULL,
                        metadata TEXT,
                        created_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP
                    )
                ''')
                
                # Create entitlements table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS entitlements (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        feature TEXT NOT NULL,
                        enabled BOOLEAN DEFAULT TRUE,
                        limits TEXT,
                        valid_from TIMESTAMP NOT NULL,
                        valid_until TIMESTAMP,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                conn.commit()
                logger.info("Ownership registry database tables initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize ownership registry database: {e}")
    
    def create_buyout_request(self, user_id: str, tenant_id: str, system_id: str, 
                             buyout_type: str, amount: float, currency: str = "USD",
                             description: str = "", metadata: Dict[str, Any] = None) -> BuyoutRequest:
        """Create a new buyout request"""
        buyout_id = f"buyout_{int(time.time())}"
        now = datetime.now()
        
        buyout = BuyoutRequest(
            id=buyout_id,
            user_id=user_id,
            tenant_id=tenant_id,
            system_id=system_id,
            buyout_type=buyout_type,
            amount=amount,
            currency=currency,
            status=BuyoutStatus.PENDING,
            description=description,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
            completed_at=None
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO buyouts 
                    (id, user_id, tenant_id, system_id, buyout_type, amount, currency, status, 
                     description, metadata, created_at, updated_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    buyout.id,
                    buyout.user_id,
                    buyout.tenant_id,
                    buyout.system_id,
                    buyout.buyout_type,
                    buyout.amount,
                    buyout.currency,
                    buyout.status.value,
                    buyout.description,
                    json.dumps(buyout.metadata),
                    buyout.created_at.isoformat(),
                    buyout.updated_at.isoformat(),
                    buyout.completed_at.isoformat() if buyout.completed_at else None
                ))
                conn.commit()
                
                logger.info(f"Created buyout request: {buyout_id}")
                return buyout
                
        except Exception as e:
            logger.error(f"Failed to create buyout request: {e}")
            raise
    
    def get_buyout_request(self, buyout_id: str) -> Optional[BuyoutRequest]:
        """Get buyout request by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM buyouts WHERE id = ?', (buyout_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return BuyoutRequest(
                    id=row[0],
                    user_id=row[1],
                    tenant_id=row[2],
                    system_id=row[3],
                    buyout_type=row[4],
                    amount=row[5],
                    currency=row[6],
                    status=BuyoutStatus(row[7]),
                    description=row[8],
                    metadata=json.loads(row[9]) if row[9] else {},
                    created_at=datetime.fromisoformat(row[10]),
                    updated_at=datetime.fromisoformat(row[11]),
                    completed_at=datetime.fromisoformat(row[12]) if row[12] else None
                )
                
        except Exception as e:
            logger.error(f"Failed to get buyout request: {e}")
            return None
    
    def update_buyout_status(self, buyout_id: str, status: BuyoutStatus) -> bool:
        """Update buyout request status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                updates = ["status = ?", "updated_at = ?"]
                params = [status.value, datetime.now().isoformat()]
                
                if status == BuyoutStatus.COMPLETED:
                    updates.append("completed_at = ?")
                    params.append(datetime.now().isoformat())
                
                params.append(buyout_id)
                
                cursor.execute(f'''
                    UPDATE buyouts 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                logger.info(f"Updated buyout status: {buyout_id} -> {status.value}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update buyout status: {e}")
            return False
    
    def list_buyout_requests(self, user_id: str = None, tenant_id: str = None, 
                            status: BuyoutStatus = None, limit: int = 100) -> List[BuyoutRequest]:
        """List buyout requests"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM buyouts'
                params = []
                
                conditions = []
                if user_id:
                    conditions.append('user_id = ?')
                    params.append(user_id)
                if tenant_id:
                    conditions.append('tenant_id = ?')
                    params.append(tenant_id)
                if status:
                    conditions.append('status = ?')
                    params.append(status.value)
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [BuyoutRequest(
                    id=row[0],
                    user_id=row[1],
                    tenant_id=row[2],
                    system_id=row[3],
                    buyout_type=row[4],
                    amount=row[5],
                    currency=row[6],
                    status=BuyoutStatus(row[7]),
                    description=row[8],
                    metadata=json.loads(row[9]) if row[9] else {},
                    created_at=datetime.fromisoformat(row[10]),
                    updated_at=datetime.fromisoformat(row[11]),
                    completed_at=datetime.fromisoformat(row[12]) if row[12] else None
                ) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list buyout requests: {e}")
            return []
    
    def create_license(self, user_id: str, tenant_id: str, license_type: LicenseType,
                      features: Dict[str, Any], valid_days: int = 365, max_users: int = 1) -> License:
        """Create a new software license"""
        license_id = f"license_{int(time.time())}"
        now = datetime.now()
        
        # Generate license key
        license_key = self._generate_license_key(license_type, user_id, tenant_id)
        
        license_obj = License(
            id=license_id,
            user_id=user_id,
            tenant_id=tenant_id,
            license_type=license_type,
            license_key=license_key,
            features=features,
            valid_from=now,
            valid_until=now + timedelta(days=valid_days),
            max_users=max_users,
            active=True,
            created_at=now,
            updated_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO licenses 
                    (id, user_id, tenant_id, license_type, license_key, features, valid_from, 
                     valid_until, max_users, active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    license_obj.id,
                    license_obj.user_id,
                    license_obj.tenant_id,
                    license_obj.license_type.value,
                    license_obj.license_key,
                    json.dumps(license_obj.features),
                    license_obj.valid_from.isoformat(),
                    license_obj.valid_until.isoformat(),
                    license_obj.max_users,
                    license_obj.active,
                    license_obj.created_at.isoformat(),
                    license_obj.updated_at.isoformat()
                ))
                conn.commit()
                
                logger.info(f"Created license: {license_id}")
                return license_obj
                
        except Exception as e:
            logger.error(f"Failed to create license: {e}")
            raise
    
    def _generate_license_key(self, license_type: LicenseType, user_id: str, tenant_id: str) -> str:
        """Generate a unique license key"""
        # Create a hash from license data
        data = f"{license_type.value}:{user_id}:{tenant_id}:{int(time.time())}"
        hash_obj = hashlib.sha256(data.encode())
        
        # Convert to base32 and format as license key
        import base64
        key_bytes = base64.b32encode(hash_obj.digest()[:20])
        key_str = key_bytes.decode('ascii')
        
        # Format as XXXX-XXXX-XXXX-XXXX
        formatted_key = '-'.join([key_str[i:i+4] for i in range(0, 16, 4)])
        
        return formatted_key
    
    def validate_license(self, license_key: str, user_id: str = None, tenant_id: str = None) -> Optional[License]:
        """Validate a license key"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM licenses WHERE license_key = ? AND active = TRUE'
                params = [license_key]
                
                if user_id:
                    query += ' AND user_id = ?'
                    params.append(user_id)
                if tenant_id:
                    query += ' AND tenant_id = ?'
                    params.append(tenant_id)
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                license_obj = License(
                    id=row[0],
                    user_id=row[1],
                    tenant_id=row[2],
                    license_type=LicenseType(row[3]),
                    license_key=row[4],
                    features=json.loads(row[5]) if row[5] else {},
                    valid_from=datetime.fromisoformat(row[6]),
                    valid_until=datetime.fromisoformat(row[7]),
                    max_users=row[8],
                    active=bool(row[9]),
                    created_at=datetime.fromisoformat(row[10]),
                    updated_at=datetime.fromisoformat(row[11])
                )
                
                # Check if license is still valid
                now = datetime.now()
                if now > license_obj.valid_until:
                    logger.warning(f"License expired: {license_key}")
                    return None
                
                return license_obj
                
        except Exception as e:
            logger.error(f"Failed to validate license: {e}")
            return None
    
    def create_export(self, user_id: str, tenant_id: str, system_id: str, 
                     export_type: str, metadata: Dict[str, Any] = None) -> Export:
        """Create a new system export"""
        export_id = f"export_{int(time.time())}"
        now = datetime.now()
        
        export = Export(
            id=export_id,
            user_id=user_id,
            tenant_id=tenant_id,
            system_id=system_id,
            export_type=export_type,
            status=ExportStatus.PENDING,
            file_path=None,
            file_size=0,
            checksum="",
            expires_at=now + timedelta(hours=72),  # 3 days
            metadata=metadata or {},
            created_at=now,
            completed_at=None
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO exports 
                    (id, user_id, tenant_id, system_id, export_type, status, file_path, 
                     file_size, checksum, expires_at, metadata, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    export.id,
                    export.user_id,
                    export.tenant_id,
                    export.system_id,
                    export.export_type,
                    export.status.value,
                    export.file_path,
                    export.file_size,
                    export.checksum,
                    export.expires_at.isoformat(),
                    json.dumps(export.metadata),
                    export.created_at.isoformat(),
                    export.completed_at.isoformat() if export.completed_at else None
                ))
                conn.commit()
                
                logger.info(f"Created export: {export_id}")
                return export
                
        except Exception as e:
            logger.error(f"Failed to create export: {e}")
            raise
    
    def generate_export_package(self, export_id: str, system_data: Dict[str, Any]) -> bool:
        """Generate export package"""
        try:
            # Get export record
            export = self.get_export(export_id)
            if not export:
                logger.error(f"Export not found: {export_id}")
                return False
            
            # Update status to in progress
            self._update_export_status(export_id, ExportStatus.IN_PROGRESS)
            
            # Create export package
            export_data = self._create_export_package(system_data, export.export_type)
            if not export_data:
                self._update_export_status(export_id, ExportStatus.FAILED)
                return False
            
            # Save export file
            export_dir = os.path.join(config.UPLOAD_FOLDER, 'exports')
            os.makedirs(export_dir, exist_ok=True)
            
            file_path = os.path.join(export_dir, f"{export_id}.zip")
            with open(file_path, 'wb') as f:
                f.write(export_data)
            
            # Calculate checksum
            checksum = hashlib.sha256(export_data).hexdigest()
            
            # Update export record
            self._update_export_completed(export_id, file_path, len(export_data), checksum)
            
            logger.info(f"Generated export package: {export_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate export package: {e}")
            self._update_export_status(export_id, ExportStatus.FAILED)
            return False
    
    def _create_export_package(self, system_data: Dict[str, Any], export_type: str) -> Optional[bytes]:
        """Create export package content"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    
                    # Add system data
                    zip_file.writestr('system.json', json.dumps(system_data, indent=2))
                    
                    # Add export metadata
                    export_info = {
                        'export_type': export_type,
                        'created_at': datetime.now().isoformat(),
                        'version': '1.0',
                        'sbh_version': '1.0.0'
                    }
                    zip_file.writestr('export_info.json', json.dumps(export_info, indent=2))
                    
                    # Add license information
                    license_info = {
                        'license_type': 'evaluation',
                        'valid_until': (datetime.now() + timedelta(days=30)).isoformat(),
                        'terms': 'This export is for evaluation purposes only.'
                    }
                    zip_file.writestr('LICENSE.txt', json.dumps(license_info, indent=2))
                    
                    # Add README
                    readme_content = f"""
System Builder Hub Export Package

Export Type: {export_type}
Created: {datetime.now().isoformat()}

This package contains:
- system.json: Complete system configuration
- export_info.json: Export metadata
- LICENSE.txt: License information

To use this export:
1. Extract all files
2. Review system.json for system configuration
3. Follow the included documentation

For support, contact: support@systembuilderhub.com
                    """
                    zip_file.writestr('README.md', readme_content.strip())
                
                # Read the zip file
                with open(temp_file.name, 'rb') as f:
                    data = f.read()
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                return data
                
        except Exception as e:
            logger.error(f"Failed to create export package: {e}")
            return None
    
    def _update_export_status(self, export_id: str, status: ExportStatus):
        """Update export status"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE exports 
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (status.value, datetime.now().isoformat(), export_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update export status: {e}")
    
    def _update_export_completed(self, export_id: str, file_path: str, file_size: int, checksum: str):
        """Update export as completed"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE exports 
                    SET status = ?, file_path = ?, file_size = ?, checksum = ?, 
                        completed_at = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    ExportStatus.COMPLETED.value,
                    file_path,
                    file_size,
                    checksum,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    export_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update export completed: {e}")
    
    def get_export(self, export_id: str) -> Optional[Export]:
        """Get export by ID"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM exports WHERE id = ?', (export_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return Export(
                    id=row[0],
                    user_id=row[1],
                    tenant_id=row[2],
                    system_id=row[3],
                    export_type=row[4],
                    status=ExportStatus(row[5]),
                    file_path=row[6],
                    file_size=row[7],
                    checksum=row[8],
                    expires_at=datetime.fromisoformat(row[9]),
                    metadata=json.loads(row[10]) if row[10] else {},
                    created_at=datetime.fromisoformat(row[11]),
                    completed_at=datetime.fromisoformat(row[12]) if row[12] else None
                )
                
        except Exception as e:
            logger.error(f"Failed to get export: {e}")
            return None
    
    def get_export_file(self, export_id: str) -> Optional[bytes]:
        """Get export file content"""
        try:
            export = self.get_export(export_id)
            if not export or not export.file_path:
                return None
            
            # Check if file exists and is not expired
            if not os.path.exists(export.file_path):
                logger.error(f"Export file not found: {export.file_path}")
                return None
            
            if datetime.now() > export.expires_at:
                logger.warning(f"Export expired: {export_id}")
                return None
            
            with open(export.file_path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Failed to get export file: {e}")
            return None
    
    def create_entitlement(self, user_id: str, tenant_id: str, feature: str,
                          limits: Dict[str, int], valid_days: int = 365) -> Entitlement:
        """Create a new entitlement"""
        entitlement_id = f"entitlement_{int(time.time())}"
        now = datetime.now()
        
        entitlement = Entitlement(
            id=entitlement_id,
            user_id=user_id,
            tenant_id=tenant_id,
            feature=feature,
            enabled=True,
            limits=limits,
            valid_from=now,
            valid_until=now + timedelta(days=valid_days),
            created_at=now,
            updated_at=now
        )
        
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO entitlements 
                    (id, user_id, tenant_id, feature, enabled, limits, valid_from, 
                     valid_until, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entitlement.id,
                    entitlement.user_id,
                    entitlement.tenant_id,
                    entitlement.feature,
                    entitlement.enabled,
                    json.dumps(entitlement.limits),
                    entitlement.valid_from.isoformat(),
                    entitlement.valid_until.isoformat() if entitlement.valid_until else None,
                    entitlement.created_at.isoformat(),
                    entitlement.updated_at.isoformat()
                ))
                conn.commit()
                
                logger.info(f"Created entitlement: {entitlement_id}")
                return entitlement
                
        except Exception as e:
            logger.error(f"Failed to create entitlement: {e}")
            raise
    
    def get_entitlements(self, user_id: str, tenant_id: str) -> List[Entitlement]:
        """Get user entitlements"""
        try:
            with sqlite3.connect(config.DATABASE_URL.replace('sqlite:///', '')) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM entitlements 
                    WHERE user_id = ? AND tenant_id = ? AND enabled = TRUE
                    ORDER BY created_at DESC
                ''', (user_id, tenant_id))
                rows = cursor.fetchall()
                
                entitlements = []
                for row in rows:
                    entitlement = Entitlement(
                        id=row[0],
                        user_id=row[1],
                        tenant_id=row[2],
                        feature=row[3],
                        enabled=bool(row[4]),
                        limits=json.loads(row[5]) if row[5] else {},
                        valid_from=datetime.fromisoformat(row[6]),
                        valid_until=datetime.fromisoformat(row[7]) if row[7] else None,
                        created_at=datetime.fromisoformat(row[8]),
                        updated_at=datetime.fromisoformat(row[9])
                    )
                    
                    # Check if entitlement is still valid
                    if not entitlement.valid_until or datetime.now() <= entitlement.valid_until:
                        entitlements.append(entitlement)
                
                return entitlements
                
        except Exception as e:
            logger.error(f"Failed to get entitlements: {e}")
            return []
    
    def check_entitlement(self, user_id: str, tenant_id: str, feature: str) -> Optional[Entitlement]:
        """Check if user has entitlement for feature"""
        entitlements = self.get_entitlements(user_id, tenant_id)
        
        for entitlement in entitlements:
            if entitlement.feature == feature:
                return entitlement
        
        return None

# Global instance
ownership_registry = OwnershipRegistry()
