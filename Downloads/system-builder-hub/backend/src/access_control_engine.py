import sqlite3
import json
import threading
import time
import hashlib
import hmac
import secrets as py_secrets
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Set, Any
import ipaddress
import re


class AccessLevel(Enum):
    """Access levels for systems and resources"""
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"
    RESTRICTED = "restricted"


class PermissionType(Enum):
    """Types of permissions"""
    VIEW = "view"
    EDIT = "edit"
    DELETE = "delete"
    ADMIN = "admin"
    SHARE = "share"
    EXPORT = "export"
    APPROVE = "approve"


class RoleType(Enum):
    """System roles"""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    GUEST = "guest"
    CUSTOM = "custom"


class InviteStatus(Enum):
    """Invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class AccessTrigger(Enum):
    """Access control triggers"""
    LOGIN = "login"
    API_CALL = "api_call"
    UI_ACCESS = "ui_access"
    EXPORT = "export"
    SHARE = "share"


@dataclass
class AccessRule:
    """Dynamic access rule"""
    rule_id: str
    system_id: str
    rule_type: str  # "ip_whitelist", "time_based", "license_required", "custom"
    rule_config: Dict[str, Any]
    is_active: bool
    created_at: datetime
    created_by: str


@dataclass
class SystemAccess:
    """System-level access settings"""
    system_id: str
    access_level: AccessLevel
    owner_id: str
    owner_organization_id: str
    created_at: datetime
    updated_at: datetime
    
    # Role-based access
    roles: Dict[str, List[str]]  # role -> user_ids
    
    # Restrictions
    ip_whitelist: List[str]
    region_restrictions: List[str]
    device_restrictions: List[str]
    time_restrictions: Dict[str, Any]  # {"start_time": "09:00", "end_time": "17:00", "timezone": "UTC"}
    
    # License requirements
    requires_license: bool
    license_type: Optional[str]
    license_restrictions: Dict[str, Any]
    
    # Sharing settings
    allow_sharing: bool
    share_expires_in_days: Optional[int]
    share_requires_auth: bool
    share_password_protected: bool


@dataclass
class UserRole:
    """User role assignment"""
    user_id: str
    organization_id: str
    system_id: str
    role_type: RoleType
    custom_permissions: List[str]
    granted_by: str
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool


@dataclass
class AccessInvite:
    """Access invitation"""
    invite_id: str
    system_id: str
    invited_by: str
    invited_email: str
    invited_username: Optional[str]
    role_type: RoleType
    custom_permissions: List[str]
    expires_at: datetime
    status: InviteStatus
    accepted_at: Optional[datetime]
    accepted_by: Optional[str]
    message: Optional[str]


@dataclass
class ShareLink:
    """Shareable link"""
    link_id: str
    system_id: str
    created_by: str
    access_level: AccessLevel
    expires_at: Optional[datetime]
    requires_auth: bool
    password_hash: Optional[str]
    max_uses: Optional[int]
    current_uses: int
    is_active: bool
    created_at: datetime


@dataclass
class AccessLog:
    """Access attempt log"""
    log_id: str
    system_id: str
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    access_trigger: AccessTrigger
    success: bool
    reason: Optional[str]
    timestamp: datetime
    session_id: Optional[str]
    metadata: Dict[str, Any]


class AccessControlEngine:
    """Advanced access control engine with fine-grained permissions"""
    
    def __init__(self, base_dir: str, llm_factory):
        self.base_dir = base_dir
        self.llm_factory = llm_factory
        
        self.db_path = f"{base_dir}/access_control_engine.db"
        self.rules_cache = {}
        self.permission_cache = {}
        
        # Initialize database
        self._init_database()
        
        # Background tasks
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        self.analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        self.analytics_thread.start()
    
    def _init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # System access settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_access (
                system_id TEXT PRIMARY KEY,
                access_level TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                owner_organization_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                roles TEXT NOT NULL,
                ip_whitelist TEXT NOT NULL,
                region_restrictions TEXT NOT NULL,
                device_restrictions TEXT NOT NULL,
                time_restrictions TEXT NOT NULL,
                requires_license BOOLEAN NOT NULL,
                license_type TEXT,
                license_restrictions TEXT NOT NULL,
                allow_sharing BOOLEAN NOT NULL,
                share_expires_in_days INTEGER,
                share_requires_auth BOOLEAN NOT NULL,
                share_password_protected BOOLEAN NOT NULL
            )
        """)
        
        # User roles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                system_id TEXT NOT NULL,
                role_type TEXT NOT NULL,
                custom_permissions TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                expires_at TEXT,
                is_active BOOLEAN NOT NULL,
                PRIMARY KEY (user_id, system_id)
            )
        """)
        
        # Access rules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_rules (
                rule_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                rule_config TEXT NOT NULL,
                is_active BOOLEAN NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL
            )
        """)
        
        # Access invites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_invites (
                invite_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                invited_by TEXT NOT NULL,
                invited_email TEXT NOT NULL,
                invited_username TEXT,
                role_type TEXT NOT NULL,
                custom_permissions TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL,
                accepted_at TEXT,
                accepted_by TEXT,
                message TEXT
            )
        """)
        
        # Share links
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS share_links (
                link_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                created_by TEXT NOT NULL,
                access_level TEXT NOT NULL,
                expires_at TEXT,
                requires_auth BOOLEAN NOT NULL,
                password_hash TEXT,
                max_uses INTEGER,
                current_uses INTEGER NOT NULL,
                is_active BOOLEAN NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Access logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                log_id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT NOT NULL,
                user_agent TEXT NOT NULL,
                access_trigger TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                metadata TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_system_access(self, system_id: str, owner_id: str, owner_organization_id: str, 
                           access_level: AccessLevel = AccessLevel.PRIVATE) -> SystemAccess:
        """Create access settings for a system"""
        now = datetime.now()
        
        system_access = SystemAccess(
            system_id=system_id,
            access_level=access_level,
            owner_id=owner_id,
            owner_organization_id=owner_organization_id,
            created_at=now,
            updated_at=now,
            roles={},
            ip_whitelist=[],
            region_restrictions=[],
            device_restrictions=[],
            time_restrictions={},
            requires_license=False,
            license_type=None,
            license_restrictions={},
            allow_sharing=False,
            share_expires_in_days=None,
            share_requires_auth=True,
            share_password_protected=False
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO system_access VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            system_id,
            access_level.value,
            owner_id,
            owner_organization_id,
            now.isoformat(),
            now.isoformat(),
            json.dumps({}),
            json.dumps([]),
            json.dumps([]),
            json.dumps([]),
            json.dumps({}),
            False,
            None,
            json.dumps({}),
            False,
            None,
            True,
            False
        ))
        
        conn.commit()
        conn.close()
        
        return system_access
    
    def get_system_access(self, system_id: str) -> Optional[SystemAccess]:
        """Get access settings for a system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM system_access WHERE system_id = ?", (system_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        return SystemAccess(
            system_id=row[0],
            access_level=AccessLevel(row[1]),
            owner_id=row[2],
            owner_organization_id=row[3],
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5]),
            roles=json.loads(row[6]),
            ip_whitelist=json.loads(row[7]),
            region_restrictions=json.loads(row[8]),
            device_restrictions=json.loads(row[9]),
            time_restrictions=json.loads(row[10]),
            requires_license=row[11],
            license_type=row[12],
            license_restrictions=json.loads(row[13]),
            allow_sharing=row[14],
            share_expires_in_days=row[15],
            share_requires_auth=row[16],
            share_password_protected=row[17]
        )
    
    def update_system_access(self, system_id: str, updates: Dict[str, Any]) -> bool:
        """Update system access settings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build update query dynamically
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ['roles', 'ip_whitelist', 'region_restrictions', 'device_restrictions', 
                      'time_restrictions', 'license_restrictions']:
                set_clauses.append(f"{key} = ?")
                values.append(json.dumps(value))
            elif key == 'access_level':
                set_clauses.append(f"{key} = ?")
                values.append(value.value if hasattr(value, 'value') else value)
            else:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(system_id)
        
        query = f"UPDATE system_access SET {', '.join(set_clauses)} WHERE system_id = ?"
        cursor.execute(query, values)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        # Clear cache
        self.rules_cache.pop(system_id, None)
        self.permission_cache.pop(system_id, None)
        
        return success
    
    def assign_user_role(self, system_id: str, user_id: str, organization_id: str,
                        role_type: RoleType, granted_by: str, 
                        custom_permissions: List[str] = None,
                        expires_at: Optional[datetime] = None) -> bool:
        """Assign a role to a user for a system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_roles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            organization_id,
            system_id,
            role_type.value,
            json.dumps(custom_permissions or []),
            granted_by,
            datetime.now().isoformat(),
            expires_at.isoformat() if expires_at else None,
            True
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        # Clear cache
        self.permission_cache.pop(f"{system_id}:{user_id}", None)
        
        return success
    
    def get_user_role(self, system_id: str, user_id: str) -> Optional[UserRole]:
        """Get user's role for a system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM user_roles 
            WHERE system_id = ? AND user_id = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > ?)
        """, (system_id, user_id, datetime.now().isoformat()))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return UserRole(
            user_id=row[0],
            organization_id=row[1],
            system_id=row[2],
            role_type=RoleType(row[3]),
            custom_permissions=json.loads(row[4]),
            granted_by=row[5],
            granted_at=datetime.fromisoformat(row[6]),
            expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
            is_active=row[8]
        )
    
    def check_access(self, system_id: str, user_id: Optional[str], 
                    organization_id: Optional[str], permission: PermissionType,
                    ip_address: str = None, user_agent: str = None,
                    session_id: str = None) -> bool:
        """Check if user has access to system with specific permission"""
        # Get system access settings
        system_access = self.get_system_access(system_id)
        if not system_access:
            return False
        
        # Check cache first
        cache_key = f"{system_id}:{user_id}:{permission.value}"
        if cache_key in self.permission_cache:
            return self.permission_cache[cache_key]
        
        # Public access check
        if system_access.access_level == AccessLevel.PUBLIC:
            result = True
        else:
            # Check ownership
            if user_id == system_access.owner_id:
                result = True
            else:
                # Check role-based access
                user_role = self.get_user_role(system_id, user_id) if user_id else None
                result = self._check_role_permission(user_role, permission, system_access)
                
                # Check dynamic rules
                if result:
                    result = self._check_dynamic_rules(system_id, user_id, ip_address, user_agent)
        
        # Log access attempt
        self._log_access_attempt(
            system_id, user_id, ip_address, user_agent, 
            AccessTrigger.API_CALL, result, None, session_id
        )
        
        # Cache result
        self.permission_cache[cache_key] = result
        
        return result
    
    def _check_role_permission(self, user_role: Optional[UserRole], 
                              permission: PermissionType, 
                              system_access: SystemAccess) -> bool:
        """Check if user role has the required permission"""
        if not user_role:
            return False
        
        # Role-based permissions
        role_permissions = {
            RoleType.OWNER: [p.value for p in PermissionType],
            RoleType.ADMIN: [PermissionType.VIEW.value, PermissionType.EDIT.value, 
                           PermissionType.DELETE.value, PermissionType.ADMIN.value, 
                           PermissionType.SHARE.value, PermissionType.EXPORT.value],
            RoleType.EDITOR: [PermissionType.VIEW.value, PermissionType.EDIT.value, 
                            PermissionType.SHARE.value, PermissionType.EXPORT.value],
            RoleType.VIEWER: [PermissionType.VIEW.value],
            RoleType.GUEST: [PermissionType.VIEW.value],
            RoleType.CUSTOM: user_role.custom_permissions
        }
        
        allowed_permissions = role_permissions.get(user_role.role_type, [])
        return permission.value in allowed_permissions
    
    def _check_dynamic_rules(self, system_id: str, user_id: Optional[str],
                           ip_address: str, user_agent: str) -> bool:
        """Check dynamic access rules"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rule_type, rule_config FROM access_rules 
            WHERE system_id = ? AND is_active = 1
        """, (system_id,))
        
        rules = cursor.fetchall()
        conn.close()
        
        for rule_type, rule_config in rules:
            config = json.loads(rule_config)
            
            if rule_type == "ip_whitelist":
                if not self._check_ip_whitelist(ip_address, config.get("allowed_ips", [])):
                    return False
            elif rule_type == "time_based":
                if not self._check_time_restriction(config):
                    return False
            elif rule_type == "license_required":
                if not self._check_license_requirement(user_id, config):
                    return False
        
        return True
    
    def _check_ip_whitelist(self, ip_address: str, allowed_ips: List[str]) -> bool:
        """Check if IP is in whitelist"""
        if not allowed_ips:
            return True
        
        try:
            client_ip = ipaddress.ip_address(ip_address)
            for allowed_ip in allowed_ips:
                if client_ip in ipaddress.ip_network(allowed_ip):
                    return True
        except ValueError:
            pass
        
        return False
    
    def _check_time_restriction(self, config: Dict[str, Any]) -> bool:
        """Check time-based restrictions"""
        if not config:
            return True
        
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        start_time = config.get("start_time")
        end_time = config.get("end_time")
        
        if start_time and end_time:
            return start_time <= current_time <= end_time
        
        return True
    
    def _check_license_requirement(self, user_id: Optional[str], config: Dict[str, Any]) -> bool:
        """Check license requirements"""
        # This would integrate with the licensing module
        # For now, return True as placeholder
        return True
    
    def create_access_invite(self, system_id: str, invited_by: str, invited_email: str,
                           role_type: RoleType, custom_permissions: List[str] = None,
                           expires_in_days: int = 7, message: str = None) -> str:
        """Create an access invitation"""
        invite_id = py_secrets.token_urlsafe(16)
        expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO access_invites VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invite_id,
            system_id,
            invited_by,
            invited_email,
            None,  # invited_username
            role_type.value,
            json.dumps(custom_permissions or []),
            expires_at.isoformat(),
            InviteStatus.PENDING.value,
            None,  # accepted_at
            None,  # accepted_by
            message
        ))
        
        conn.commit()
        conn.close()
        
        return invite_id
    
    def accept_invite(self, invite_id: str, accepted_by: str, accepted_username: str) -> bool:
        """Accept an access invitation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get invite details
        cursor.execute("SELECT * FROM access_invites WHERE invite_id = ?", (invite_id,))
        invite_row = cursor.fetchone()
        
        if not invite_row:
            conn.close()
            return False
        
        # Check if expired
        expires_at = datetime.fromisoformat(invite_row[7])
        if datetime.now() > expires_at:
            cursor.execute("""
                UPDATE access_invites SET status = ? WHERE invite_id = ?
            """, (InviteStatus.EXPIRED.value, invite_id))
            conn.commit()
            conn.close()
            return False
        
        # Update invite status
        cursor.execute("""
            UPDATE access_invites 
            SET status = ?, accepted_at = ?, accepted_by = ?, invited_username = ?
            WHERE invite_id = ?
        """, (
            InviteStatus.ACCEPTED.value,
            datetime.now().isoformat(),
            accepted_by,
            accepted_username,
            invite_id
        ))
        
        # Assign role
        system_id = invite_row[1]
        role_type = RoleType(invite_row[5])
        custom_permissions = json.loads(invite_row[6])
        
        self.assign_user_role(
            system_id=system_id,
            user_id=accepted_by,
            organization_id="",  # Would get from user profile
            role_type=role_type,
            granted_by=invite_row[2],
            custom_permissions=custom_permissions
        )
        
        conn.commit()
        conn.close()
        
        return True
    
    def create_share_link(self, system_id: str, created_by: str, access_level: AccessLevel,
                         expires_in_days: Optional[int] = None, requires_auth: bool = True,
                         password: Optional[str] = None, max_uses: Optional[int] = None) -> str:
        """Create a shareable link"""
        link_id = py_secrets.token_urlsafe(16)
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO share_links VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            link_id,
            system_id,
            created_by,
            access_level.value,
            expires_at.isoformat() if expires_at else None,
            requires_auth,
            password_hash,
            max_uses,
            0,  # current_uses
            True,  # is_active
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return link_id
    
    def validate_share_link(self, link_id: str, user_id: Optional[str] = None,
                          password: Optional[str] = None) -> bool:
        """Validate a share link"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM share_links WHERE link_id = ? AND is_active = 1", (link_id,))
        link_row = cursor.fetchone()
        
        if not link_row:
            conn.close()
            return False
        
        # Check expiration
        if link_row[4]:  # expires_at
            expires_at = datetime.fromisoformat(link_row[4])
            if datetime.now() > expires_at:
                conn.close()
                return False
        
        # Check max uses
        if link_row[7] and link_row[8] >= link_row[7]:  # max_uses and current_uses
            conn.close()
            return False
        
        # Check password
        if link_row[6] and password:  # password_hash
            provided_hash = hashlib.sha256(password.encode()).hexdigest()
            if provided_hash != link_row[6]:
                conn.close()
                return False
        
        # Increment usage
        cursor.execute("""
            UPDATE share_links SET current_uses = current_uses + 1 WHERE link_id = ?
        """, (link_id,))
        
        conn.commit()
        conn.close()
        
        return True
    
    def _log_access_attempt(self, system_id: str, user_id: Optional[str],
                          ip_address: str, user_agent: str, trigger: AccessTrigger,
                          success: bool, reason: Optional[str], session_id: Optional[str]):
        """Log access attempt"""
        log_id = py_secrets.token_urlsafe(16)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO access_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id,
            system_id,
            user_id,
            ip_address or "unknown",
            user_agent or "unknown",
            trigger.value,
            success,
            reason,
            datetime.now().isoformat(),
            session_id,
            json.dumps({})
        ))
        
        conn.commit()
        conn.close()
    
    def get_access_logs(self, system_id: str, limit: int = 100, offset: int = 0) -> List[AccessLog]:
        """Get access logs for a system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM access_logs 
            WHERE system_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?
        """, (system_id, limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            AccessLog(
                log_id=row[0],
                system_id=row[1],
                user_id=row[2],
                ip_address=row[3],
                user_agent=row[4],
                access_trigger=AccessTrigger(row[5]),
                success=row[6],
                reason=row[7],
                timestamp=datetime.fromisoformat(row[8]),
                session_id=row[9],
                metadata=json.loads(row[10])
            )
            for row in rows
        ]
    
    def _cleanup_loop(self):
        """Background cleanup of expired invites and links"""
        while True:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Expire old invites
                cursor.execute("""
                    UPDATE access_invites 
                    SET status = ? 
                    WHERE status = ? AND expires_at < ?
                """, (InviteStatus.EXPIRED.value, InviteStatus.PENDING.value, 
                     datetime.now().isoformat()))
                
                # Expire old share links
                cursor.execute("""
                    UPDATE share_links 
                    SET is_active = 0 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """, (datetime.now().isoformat(),))
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                print(f"Access control cleanup error: {e}")
            
            time.sleep(3600)  # Run every hour
    
    def _analytics_loop(self):
        """Background analytics processing"""
        while True:
            try:
                # Process access patterns and feed to LLM Factory
                # This would analyze access logs and generate insights
                pass
            except Exception as e:
                print(f"Access control analytics error: {e}")
            
            time.sleep(1800)  # Run every 30 minutes
