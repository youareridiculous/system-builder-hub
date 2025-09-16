from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Set
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator


class Permission(str, Enum):
    """Granular, composable permissions used by Venture OS RBAC."""
    READ = "read"
    WRITE = "write"
    MANAGE_TENANT = "manage_tenant"
    INVITE = "invite"
    BILLING = "billing"
    INTEGRATIONS = "integrations"
    ADMIN = "admin"


class Role(str, Enum):
    """High-level roles mapped to a set of permissions."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    INTEGRATION = "integration"
    SUSPENDED = "suspended"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.OWNER: {Permission.READ, Permission.WRITE, Permission.MANAGE_TENANT, Permission.INVITE, Permission.BILLING, Permission.INTEGRATIONS, Permission.ADMIN},
    Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.MANAGE_TENANT, Permission.INVITE, Permission.BILLING, Permission.INTEGRATIONS},
    Role.MEMBER: {Permission.READ, Permission.WRITE},
    Role.VIEWER: {Permission.READ},
    Role.INTEGRATION: {Permission.READ},
    Role.SUSPENDED: set(),
}


class User(BaseModel):
    id: str
    tenant_id: str = Field(..., description="Tenant foreign key (FK)")
    email: EmailStr
    name: str = ""
    roles: List[Role] = Field(default_factory=lambda: [Role.MEMBER])
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @validator("roles", pre=True)
    def _coerce_roles(cls, v):
        if isinstance(v, str):
            return [Role(v)]
        return v

    def permissions(self) -> Set[Permission]:
        if not self.is_active:
            return set()
        perms: Set[Permission] = set()
        for r in self.roles:
            perms |= ROLE_PERMISSIONS.get(r, set())
        return perms

    def has_permission(self, perm: Permission) -> bool:
        return perm in self.permissions()


def can_manage_tenant(user: User) -> bool:
    return user.has_permission(Permission.MANAGE_TENANT)


def get_user_summary(user: User) -> str:
    roles = ", ".join(r.value for r in user.roles) or "member"
    return f"User {user.name or user.email} [{roles}] (tenant={user.tenant_id})"
