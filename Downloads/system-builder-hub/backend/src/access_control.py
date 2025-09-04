"""
Access Control System - Fine-grained multi-tenant permission management
"""

import json
import hashlib
import secrets as py_secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path


class RoleType(Enum):
    """User role types"""
    ADMIN = "admin"
    BUILDER = "builder"
    VIEWER = "viewer"
    CLIENT = "client"
    PARTNER = "partner"


class ResourceType(Enum):
    """Resource types for permission control"""
    SYSTEM = "system"
    AGENT = "agent"
    FILE = "file"
    API = "api"
    DATASET = "dataset"
    DEPLOYMENT = "deployment"
    TEMPLATE = "template"
    USER = "user"
    ORGANIZATION = "organization"


class PermissionType(Enum):
    """Permission types"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    SHARE = "share"
    ADMIN = "admin"


class SessionStatus(Enum):
    """Session status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class User:
    """User entity"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: RoleType
    organization_id: str
    is_active: bool = True
    created_at: str = None
    last_login: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Organization:
    """Organization entity"""
    organization_id: str
    name: str
    domain: str
    plan: str
    max_users: int
    max_systems: int
    is_active: bool = True
    created_at: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Permission:
    """Permission entity"""
    permission_id: str
    resource_type: ResourceType
    resource_id: str
    role: RoleType
    permissions: List[PermissionType]
    organization_id: str
    created_at: str = None
    expires_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class Session:
    """User session entity"""
    session_id: str
    user_id: str
    organization_id: str
    token: str
    ip_address: str
    user_agent: str
    status: SessionStatus
    created_at: str = None
    expires_at: str = None
    last_activity: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow().isoformat()


@dataclass
class AuditLog:
    """Audit log entry"""
    log_id: str
    user_id: str
    organization_id: str
    action: str
    resource_type: ResourceType
    resource_id: str
    details: Dict[str, Any]
    ip_address: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class AccessControlSystem:
    """Fine-grained access control system"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "access_control.db"
        self._init_database()
        self._load_default_permissions()

    def _init_database(self):
        """Initialize the database with tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT,
                metadata TEXT
            )
        """)

        # Organizations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                organization_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                domain TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL,
                max_users INTEGER NOT NULL,
                max_systems INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # Permissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                permission_id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                role TEXT NOT NULL,
                permissions TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                UNIQUE(resource_type, resource_id, role, organization_id)
            )
        """)

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                ip_address TEXT NOT NULL,
                user_agent TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                last_activity TEXT NOT NULL
            )
        """)

        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                details TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def _load_default_permissions(self):
        """Load default permissions for new organizations"""
        self.default_permissions = {
            RoleType.ADMIN: [
                PermissionType.READ, PermissionType.WRITE, PermissionType.DELETE,
                PermissionType.EXECUTE, PermissionType.SHARE, PermissionType.ADMIN
            ],
            RoleType.BUILDER: [
                PermissionType.READ, PermissionType.WRITE, PermissionType.EXECUTE, PermissionType.SHARE
            ],
            RoleType.VIEWER: [PermissionType.READ],
            RoleType.CLIENT: [PermissionType.READ, PermissionType.EXECUTE],
            RoleType.PARTNER: [
                PermissionType.READ, PermissionType.WRITE, PermissionType.EXECUTE, PermissionType.SHARE
            ]
        }

    def create_organization(self, name: str, domain: str, plan: str = "basic") -> Organization:
        """Create a new organization"""
        organization_id = f"org_{py_secrets.token_hex(8)}"
        
        # Set limits based on plan
        plan_limits = {
            "basic": {"max_users": 10, "max_systems": 5},
            "pro": {"max_users": 50, "max_systems": 25},
            "enterprise": {"max_users": 500, "max_systems": 250}
        }
        
        limits = plan_limits.get(plan, plan_limits["basic"])
        
        organization = Organization(
            organization_id=organization_id,
            name=name,
            domain=domain,
            plan=plan,
            max_users=limits["max_users"],
            max_systems=limits["max_systems"]
        )
        
        self._save_organization(organization)
        return organization

    def create_user(self, username: str, email: str, password: str, role: RoleType, 
                   organization_id: str) -> User:
        """Create a new user"""
        # Check organization exists and has capacity
        organization = self.get_organization(organization_id)
        if not organization:
            raise ValueError("Organization not found")
        
        user_count = self._get_user_count(organization_id)
        if user_count >= organization.max_users:
            raise ValueError("Organization user limit reached")
        
        user_id = f"user_{py_secrets.token_hex(8)}"
        password_hash = self._hash_password(password)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            organization_id=organization_id
        )
        
        self._save_user(user)
        return user

    def authenticate_user(self, username: str, password: str, ip_address: str, 
                         user_agent: str) -> Optional[Session]:
        """Authenticate user and create session"""
        user = self._get_user_by_username(username)
        if not user or not user.is_active:
            return None
        
        if not self._verify_password(password, user.password_hash):
            return None
        
        # Create session
        session_id = f"session_{py_secrets.token_hex(16)}"
        token = py_secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            organization_id=user.organization_id,
            token=token,
            ip_address=ip_address,
            user_agent=user_agent,
            status=SessionStatus.ACTIVE,
            expires_at=expires_at
        )
        
        self._save_session(session)
        self._update_user_last_login(user.user_id)
        
        # Log authentication
        self.log_audit_event(
            user_id=user.user_id,
            organization_id=user.organization_id,
            action="user_login",
            resource_type=ResourceType.USER,
            resource_id=user.user_id,
            details={"username": username, "ip_address": ip_address},
            ip_address=ip_address
        )
        
        return session

    def validate_session(self, token: str) -> Optional[User]:
        """Validate session token and return user"""
        session = self._get_session_by_token(token)
        if not session:
            return None
        
        # Check if session is expired
        if session.expires_at and datetime.fromisoformat(session.expires_at) < datetime.utcnow():
            self._update_session_status(session.session_id, SessionStatus.EXPIRED)
            return None
        
        # Check if session is revoked
        if session.status != SessionStatus.ACTIVE:
            return None
        
        # Update last activity
        self._update_session_activity(session.session_id)
        
        return self.get_user(session.user_id)

    def check_permission(self, user_id: str, resource_type: ResourceType, 
                        resource_id: str, permission: PermissionType) -> bool:
        """Check if user has specific permission on resource"""
        user = self.get_user(user_id)
        if not user or not user.is_active:
            return False
        
        # Admin role has all permissions
        if user.role == RoleType.ADMIN:
            return True
        
        # Get user's permissions for this resource
        permissions = self._get_user_permissions(user_id, resource_type, resource_id)
        
        # Check if user has the required permission
        return permission in permissions

    def grant_permission(self, resource_type: ResourceType, resource_id: str,
                        role: RoleType, permissions: List[PermissionType],
                        organization_id: str, expires_at: str = None) -> Permission:
        """Grant permissions to a role for a resource"""
        permission_id = f"perm_{py_secrets.token_hex(8)}"
        
        permission = Permission(
            permission_id=permission_id,
            resource_type=resource_type,
            resource_id=resource_id,
            role=role,
            permissions=permissions,
            organization_id=organization_id,
            expires_at=expires_at
        )
        
        self._save_permission(permission)
        
        # Log permission grant
        self.log_audit_event(
            user_id="system",
            organization_id=organization_id,
            action="permission_granted",
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "role": role.value,
                "permissions": [p.value for p in permissions],
                "expires_at": expires_at
            },
            ip_address="system"
        )
        
        return permission

    def revoke_permission(self, permission_id: str, user_id: str = "system") -> bool:
        """Revoke a permission"""
        permission = self._get_permission(permission_id)
        if not permission:
            return False
        
        self._delete_permission(permission_id)
        
        # Log permission revocation
        self.log_audit_event(
            user_id=user_id,
            organization_id=permission.organization_id,
            action="permission_revoked",
            resource_type=permission.resource_type,
            resource_id=permission.resource_id,
            details={"permission_id": permission_id},
            ip_address="system"
        )
        
        return True

    def share_resource(self, resource_type: ResourceType, resource_id: str,
                      from_user_id: str, to_user_id: str, permissions: List[PermissionType],
                      expires_at: str = None) -> bool:
        """Share a resource with another user"""
        from_user = self.get_user(from_user_id)
        to_user = self.get_user(to_user_id)
        
        if not from_user or not to_user:
            return False
        
        # Check if from_user has share permission
        if not self.check_permission(from_user_id, resource_type, resource_id, PermissionType.SHARE):
            return False
        
        # Create temporary permission for to_user
        role = RoleType.VIEWER  # Default role for shared resources
        self.grant_permission(resource_type, resource_id, role, permissions, 
                            to_user.organization_id, expires_at)
        
        # Log sharing
        self.log_audit_event(
            user_id=from_user_id,
            organization_id=from_user.organization_id,
            action="resource_shared",
            resource_type=resource_type,
            resource_id=resource_id,
            details={
                "shared_with": to_user_id,
                "permissions": [p.value for p in permissions],
                "expires_at": expires_at
            },
            ip_address="system"
        )
        
        return True

    def log_audit_event(self, user_id: str, organization_id: str, action: str,
                       resource_type: ResourceType, resource_id: str,
                       details: Dict[str, Any], ip_address: str):
        """Log an audit event"""
        log_id = f"log_{py_secrets.token_hex(8)}"
        
        audit_log = AuditLog(
            log_id=log_id,
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )
        
        self._save_audit_log(audit_log)

    def get_organization(self, organization_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT organization_id, name, domain, plan, max_users, max_systems,
                   is_active, created_at, metadata
            FROM organizations WHERE organization_id = ?
        """, (organization_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Organization(
                organization_id=row[0],
                name=row[1],
                domain=row[2],
                plan=row[3],
                max_users=row[4],
                max_systems=row[5],
                is_active=bool(row[6]),
                created_at=row[7],
                metadata=json.loads(row[8]) if row[8] else {}
            )
        return None

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, email, password_hash, role, organization_id,
                   is_active, created_at, last_login, metadata
            FROM users WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                password_hash=row[3],
                role=RoleType(row[4]),
                organization_id=row[5],
                is_active=bool(row[6]),
                created_at=row[7],
                last_login=row[8],
                metadata=json.loads(row[9]) if row[9] else {}
            )
        return None

    def get_organization_users(self, organization_id: str) -> List[User]:
        """Get all users in an organization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, email, password_hash, role, organization_id,
                   is_active, created_at, last_login, metadata
            FROM users WHERE organization_id = ?
        """, (organization_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                password_hash=row[3],
                role=RoleType(row[4]),
                organization_id=row[5],
                is_active=bool(row[6]),
                created_at=row[7],
                last_login=row[8],
                metadata=json.loads(row[9]) if row[9] else {}
            )
            for row in rows
        ]

    def get_audit_logs(self, organization_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs for an organization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT log_id, user_id, organization_id, action, resource_type,
                   resource_id, details, ip_address, timestamp
            FROM audit_logs 
            WHERE organization_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (organization_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            AuditLog(
                log_id=row[0],
                user_id=row[1],
                organization_id=row[2],
                action=row[3],
                resource_type=ResourceType(row[4]),
                resource_id=row[5],
                details=json.loads(row[6]),
                ip_address=row[7],
                timestamp=row[8]
            )
            for row in rows
        ]

    def _hash_password(self, password: str) -> str:
        """Hash a password"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        return self._hash_password(password) == password_hash

    def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, username, email, password_hash, role, organization_id,
                   is_active, created_at, last_login, metadata
            FROM users WHERE username = ?
        """, (username,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                user_id=row[0],
                username=row[1],
                email=row[2],
                password_hash=row[3],
                role=RoleType(row[4]),
                organization_id=row[5],
                is_active=bool(row[6]),
                created_at=row[7],
                last_login=row[8],
                metadata=json.loads(row[9]) if row[9] else {}
            )
        return None

    def _get_session_by_token(self, token: str) -> Optional[Session]:
        """Get session by token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, user_id, organization_id, token, ip_address,
                   user_agent, status, created_at, expires_at, last_activity
            FROM sessions WHERE token = ?
        """, (token,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Session(
                session_id=row[0],
                user_id=row[1],
                organization_id=row[2],
                token=row[3],
                ip_address=row[4],
                user_agent=row[5],
                status=SessionStatus(row[6]),
                created_at=row[7],
                expires_at=row[8],
                last_activity=row[9]
            )
        return None

    def _get_user_permissions(self, user_id: str, resource_type: ResourceType, 
                            resource_id: str) -> Set[PermissionType]:
        """Get user's permissions for a specific resource"""
        user = self.get_user(user_id)
        if not user:
            return set()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT permissions FROM permissions 
            WHERE resource_type = ? AND resource_id = ? AND role = ? AND organization_id = ?
        """, (resource_type.value, resource_id, user.role.value, user.organization_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        permissions = set()
        for row in rows:
            perms = json.loads(row[0])
            permissions.update([PermissionType(p) for p in perms])
        
        return permissions

    def _get_user_count(self, organization_id: str) -> int:
        """Get user count for organization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE organization_id = ?", (organization_id,))
        count = cursor.fetchone()[0]
        conn.close()
        
        return count

    def _save_organization(self, organization: Organization):
        """Save organization to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO organizations 
            (organization_id, name, domain, plan, max_users, max_systems, is_active, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            organization.organization_id, organization.name, organization.domain,
            organization.plan, organization.max_users, organization.max_systems,
            organization.is_active, organization.created_at, json.dumps(organization.metadata)
        ))
        
        conn.commit()
        conn.close()

    def _save_user(self, user: User):
        """Save user to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO users 
            (user_id, username, email, password_hash, role, organization_id, is_active, created_at, last_login, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user.user_id, user.username, user.email, user.password_hash,
            user.role.value, user.organization_id, user.is_active,
            user.created_at, user.last_login, json.dumps(user.metadata)
        ))
        
        conn.commit()
        conn.close()

    def _save_permission(self, permission: Permission):
        """Save permission to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO permissions 
            (permission_id, resource_type, resource_id, role, permissions, organization_id, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            permission.permission_id, permission.resource_type.value,
            permission.resource_id, permission.role.value,
            json.dumps([p.value for p in permission.permissions]),
            permission.organization_id, permission.created_at, permission.expires_at
        ))
        
        conn.commit()
        conn.close()

    def _save_session(self, session: Session):
        """Save session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sessions 
            (session_id, user_id, organization_id, token, ip_address, user_agent, status, created_at, expires_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id, session.user_id, session.organization_id,
            session.token, session.ip_address, session.user_agent,
            session.status.value, session.created_at, session.expires_at, session.last_activity
        ))
        
        conn.commit()
        conn.close()

    def _save_audit_log(self, audit_log: AuditLog):
        """Save audit log to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO audit_logs 
            (log_id, user_id, organization_id, action, resource_type, resource_id, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_log.log_id, audit_log.user_id, audit_log.organization_id,
            audit_log.action, audit_log.resource_type.value, audit_log.resource_id,
            json.dumps(audit_log.details), audit_log.ip_address, audit_log.timestamp
        ))
        
        conn.commit()
        conn.close()

    def _update_user_last_login(self, user_id: str):
        """Update user's last login time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE users SET last_login = ? WHERE user_id = ?
        """, (datetime.utcnow().isoformat(), user_id))
        
        conn.commit()
        conn.close()

    def _update_session_status(self, session_id: str, status: SessionStatus):
        """Update session status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions SET status = ? WHERE session_id = ?
        """, (status.value, session_id))
        
        conn.commit()
        conn.close()

    def _update_session_activity(self, session_id: str):
        """Update session last activity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sessions SET last_activity = ? WHERE session_id = ?
        """, (datetime.utcnow().isoformat(), session_id))
        
        conn.commit()
        conn.close()

    def _get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get permission by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT permission_id, resource_type, resource_id, role, permissions,
                   organization_id, created_at, expires_at
            FROM permissions WHERE permission_id = ?
        """, (permission_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Permission(
                permission_id=row[0],
                resource_type=ResourceType(row[1]),
                resource_id=row[2],
                role=RoleType(row[3]),
                permissions=[PermissionType(p) for p in json.loads(row[4])],
                organization_id=row[5],
                created_at=row[6],
                expires_at=row[7]
            )
        return None

    def _delete_permission(self, permission_id: str):
        """Delete permission from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM permissions WHERE permission_id = ?", (permission_id,))
        
        conn.commit()
        conn.close()
