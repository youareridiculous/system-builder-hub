"""
SBH SDK for Python (FastAPI/Flask)
Provides auth helpers, RBAC decorators, API client, and event tracking.
"""

import functools
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


@dataclass
class SBHUser:
    """SBH user information."""
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
    permissions: List[str]


@dataclass
class SBHContext:
    """SBH request context."""
    user: SBHUser
    tenant_id: str
    request_id: str
    timestamp: datetime


class SBHAuth:
    """SBH Authentication helper."""
    
    def __init__(self, api_url: str = "http://localhost:5001"):
        self.api_url = api_url
        self._current_user: Optional[SBHUser] = None
        self._current_tenant: Optional[str] = None
    
    def get_current_user(self) -> Optional[SBHUser]:
        """Get current authenticated user."""
        return self._current_user
    
    def get_current_tenant(self) -> Optional[str]:
        """Get current tenant ID."""
        return self._current_tenant or (self._current_user.tenant_id if self._current_user else None)
    
    def set_user(self, user: SBHUser):
        """Set current user."""
        self._current_user = user
        self._current_tenant = user.tenant_id
    
    def require_auth(self, f: Callable) -> Callable:
        """Decorator to require authentication."""
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not self._current_user:
                raise ValueError("Authentication required")
            return f(*args, **kwargs)
        return wrapper
    
    def require_role(self, roles: List[str]) -> Callable:
        """Decorator to require specific roles."""
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                if not self._current_user:
                    raise ValueError("Authentication required")
                if self._current_user.role not in roles:
                    raise ValueError(f"Role required: {roles}")
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    def require_permission(self, permission: str) -> Callable:
        """Decorator to require specific permission."""
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                if not self._current_user:
                    raise ValueError("Authentication required")
                if permission not in self._current_user.permissions:
                    raise ValueError(f"Permission required: {permission}")
                return f(*args, **kwargs)
            return wrapper
        return decorator


class SBHDatabase:
    """SBH Database helper."""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query with tenant isolation."""
        # This is a simplified implementation
        # In a real implementation, you would use SQLAlchemy or similar
        if params and 'tid' in params:
            # Ensure tenant isolation
            sql = f"{sql} AND tenant_id = :tid"
        
        logger.info(f"Executing query: {sql}")
        # Placeholder for actual database query
        return []
    
    def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        """Execute a SQL statement."""
        logger.info(f"Executing statement: {sql}")
        # Placeholder for actual database execution
        return 1
    
    def get_by_id(self, table: str, id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get record by ID with tenant isolation."""
        sql = f"SELECT * FROM {table} WHERE id = :id AND tenant_id = :tid"
        result = self.query(sql, {"id": id, "tid": tenant_id})
        return result[0] if result else None
    
    def list(self, table: str, tenant_id: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List records with tenant isolation."""
        sql = f"SELECT * FROM {table} WHERE tenant_id = :tid"
        params = {"tid": tenant_id}
        
        if filters:
            for key, value in filters.items():
                sql += f" AND {key} = :{key}"
                params[key] = value
        
        return self.query(sql, params)
    
    def create(self, table: str, data: Dict[str, Any], tenant_id: str) -> str:
        """Create a new record with tenant isolation."""
        data['tenant_id'] = tenant_id
        data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = datetime.utcnow().isoformat()
        
        columns = ', '.join(data.keys())
        placeholders = ', '.join([f':{k}' for k in data.keys()])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
        
        # Placeholder for actual insert
        return "generated-id"
    
    def update(self, table: str, id: str, data: Dict[str, Any], tenant_id: str) -> bool:
        """Update a record with tenant isolation."""
        data['updated_at'] = datetime.utcnow().isoformat()
        
        set_clause = ', '.join([f"{k} = :{k}" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE id = :id AND tenant_id = :tid"
        
        data['id'] = id
        data['tid'] = tenant_id
        
        return self.execute(sql, data) > 0
    
    def delete(self, table: str, id: str, tenant_id: str) -> bool:
        """Delete a record with tenant isolation."""
        sql = f"DELETE FROM {table} WHERE id = :id AND tenant_id = :tid"
        return self.execute(sql, {"id": id, "tid": tenant_id}) > 0


class SBHFiles:
    """SBH File storage helper."""
    
    def __init__(self, storage_url: str = "http://localhost:5001"):
        self.storage_url = storage_url
    
    def upload(self, file_path: str, tenant_id: str, folder: str = "uploads") -> str:
        """Upload a file to SBH storage."""
        # Placeholder for actual file upload
        logger.info(f"Uploading file {file_path} to {folder} for tenant {tenant_id}")
        return f"https://storage.sbh.com/{tenant_id}/{folder}/file-id"
    
    def download(self, file_url: str) -> bytes:
        """Download a file from SBH storage."""
        # Placeholder for actual file download
        logger.info(f"Downloading file from {file_url}")
        return b"file content"
    
    def delete(self, file_url: str) -> bool:
        """Delete a file from SBH storage."""
        # Placeholder for actual file deletion
        logger.info(f"Deleting file {file_url}")
        return True


class SBHAnalytics:
    """SBH Analytics helper."""
    
    def __init__(self, api_url: str = "http://localhost:5001"):
        self.api_url = api_url
    
    def track(self, event: str, properties: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None):
        """Track an analytics event."""
        data = {
            "event": event,
            "properties": properties or {},
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        }
        
        try:
            response = requests.post(f"{self.api_url}/api/analytics/track", json=data)
            response.raise_for_status()
            logger.info(f"Tracked event: {event}")
        except Exception as e:
            logger.error(f"Failed to track event {event}: {e}")
    
    def identify(self, user_id: str, traits: Optional[Dict[str, Any]] = None):
        """Identify a user for analytics."""
        data = {
            "user_id": user_id,
            "traits": traits or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            response = requests.post(f"{self.api_url}/api/analytics/identify", json=data)
            response.raise_for_status()
            logger.info(f"Identified user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to identify user {user_id}: {e}")


class SBHAPI:
    """SBH API client."""
    
    def __init__(self, api_url: str = "http://localhost:5001", auth_token: Optional[str] = None):
        self.api_url = api_url
        self.auth_token = auth_token
        self.session = requests.Session()
        
        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}"})
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to SBH API."""
        url = f"{self.api_url}{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request to SBH API."""
        url = f"{self.api_url}{endpoint}"
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a PUT request to SBH API."""
        url = f"{self.api_url}{endpoint}"
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return response.json()
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request to SBH API."""
        url = f"{self.api_url}{endpoint}"
        response = self.session.delete(url)
        response.raise_for_status()
        return response.json()


# Global instances
auth = SBHAuth()
db = SBHDatabase("postgresql://user:pass@localhost/sbh")
files = SBHFiles()
analytics = SBHAnalytics()
api = SBHAPI()


# Convenience decorators
def require_auth(f: Callable) -> Callable:
    """Require authentication decorator."""
    return auth.require_auth(f)


def require_role(roles: List[str]) -> Callable:
    """Require role decorator."""
    return auth.require_role(roles)


def require_permission(permission: str) -> Callable:
    """Require permission decorator."""
    return auth.require_permission(permission)


# Example usage:
@require_auth
@require_role(["admin", "member"])
def get_contacts():
    """Get contacts for current tenant."""
    tenant_id = auth.get_current_tenant()
    return db.list("contacts", tenant_id)


@require_auth
@require_permission("contacts.create")
def create_contact(contact_data: Dict[str, Any]):
    """Create a new contact."""
    tenant_id = auth.get_current_tenant()
    contact_id = db.create("contacts", contact_data, tenant_id)
    
    # Track the event
    analytics.track("contact.created", {
        "contact_id": contact_id,
        "tenant_id": tenant_id
    }, auth.get_current_user().id)
    
    return contact_id
