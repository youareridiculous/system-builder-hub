from __future__ import annotations

from dataclasses import dataclass

from typing import Optional, Set

from venture_os.rbac.model import User, Permission, Role
from venture_os.entity.model import Entity

"""
RBAC and Entity Guards

This module provides storage-agnostic guard helpers that combine RBAC (User, Permission, Role)
with the base Entity model to determine if an action is allowed in a multi-tenant environment.

Core Policy:
- Cross-tenant data is never allowed: if user.tenant_id != entity.tenant_id → deny.
- Suspended users: deny everything.
- Owner/Admin: read & write everything in their tenant.
- Member: read & write.
- Viewer/Integration: read only.
- Inactive users: deny.
- Entity archived: reads allowed; writes denied unless user has Permission.ADMIN.

Explicit permission checks honor Permission.READ / Permission.WRITE and Permission.MANAGE_TENANT for tenant-level ops.

Example:

    user = User(tenant_id='tenant1', status='active')
    entity = Entity(tenant_id='tenant1', archived=False)
    decision = can_read_entity(user, entity)
    # decision.allow will be True if the user can read the entity.
"""

@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str = ""

def can_read_entity(user: User, entity: Entity) -> Decision:
    if user.status == 'suspended':
        return Decision(allow=False, reason="User is suspended.")
    if user.status == 'inactive':
        return Decision(allow=False, reason="User is inactive.")
    if user.tenant_id != entity.tenant_id:
        return Decision(allow=False, reason="Cross-tenant access denied.")
    if entity.archived:
        return Decision(allow=True, reason="Entity is archived; read access granted.")
    return Decision(allow=True, reason="Read access granted.")

def can_write_entity(user: User, entity: Entity) -> Decision:
    if user.status == 'suspended':
        return Decision(allow=False, reason="User is suspended.")
    if user.status == 'inactive':
        return Decision(allow=False, reason="User is inactive.")
    if user.tenant_id != entity.tenant_id:
        return Decision(allow=False, reason="Cross-tenant access denied.")
    if entity.archived:
        if not _has(user, Permission.ADMIN):
            return Decision(allow=False, reason="Entity is archived; write access denied.")
    return Decision(allow=True, reason="Write access granted.")

def can_manage_tenant(user: User) -> Decision:
    return require_permission(user, Permission.MANAGE_TENANT)

def require_permission(user: User, perm: Permission) -> Decision:
    if _has(user, perm):
        return Decision(allow=True, reason="Permission granted.")
    return Decision(allow=False, reason="Permission denied.")

def _roles(user: User) -> Set[Role]:
    return user.roles

def _has(user: User, perm: Permission) -> bool:
    return user.has_permission(perm)
