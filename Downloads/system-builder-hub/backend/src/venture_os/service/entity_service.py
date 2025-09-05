from __future__ import annotations

from dataclasses import dataclass

from typing import Any, Dict, Optional, Tuple

from datetime import datetime

from venture_os.entity.model import Entity, EntityKind

from venture_os.rbac.model import User, Permission

from venture_os.security.guards import can_read_entity, can_write_entity, require_permission, Decision

from venture_os.repo.memory import MemoryEntityRepo

# Result = Union[ServiceOk, ServiceErr]

@dataclass(frozen=True)
class ServiceOk:
    data: Any
    message: str = ""

@dataclass(frozen=True)
class ServiceErr:
    reason: str
    code: str = "forbidden"  # or "invalid", "not_found"

def _now() -> datetime:
    return datetime.utcnow()

def _same_tenant(user: User, tenant_id: str) -> bool:
    return user.tenant_id == tenant_id

def _invalid(reason: str) -> ServiceErr:
    return ServiceErr(reason=reason)

def create_entity(user: User, repo: MemoryEntityRepo, *, tenant_id: str, kind: EntityKind, name: str, status: str = "active", metadata: Optional[Dict[str, Any]] = None) -> Any:
    if not _same_tenant(user, tenant_id):
        return _invalid("forbidden")
    if not name:
        return _invalid("invalid")

    require_permission(user, Permission.WRITE)

    entity_id = metadata.get("id") if metadata else None
    if not entity_id:
        return ServiceErr(code="invalid")

    e = Entity(
        id=entity_id,
        tenant_id=tenant_id,
        kind=kind,
        name=name,
        status=status,
        metadata=metadata,
        created_at=_now(),
        updated_at=_now(),
        archived_at=None
    )

    repo.put(e)
    return ServiceOk(data=e, message="created")

def get_entity(user: User, repo: MemoryEntityRepo, *, tenant_id: str, entity_id: str) -> Any:
    e = repo.get(tenant_id, entity_id)
    if e is None:
        return ServiceErr(code="not_found")

    decision = can_read_entity(user, e)
    if decision != Decision.ALLOW:
        return ServiceErr(reason=decision.reason)

    return ServiceOk(data=e)

def update_entity(user: User, repo: MemoryEntityRepo, *, tenant_id: str, entity_id: str, patch: Dict[str, Any]) -> Any:
    e = repo.get(tenant_id, entity_id)
    if e is None:
        return ServiceErr(reason="not_found")

    decision = can_write_entity(user, e)
    if decision != Decision.ALLOW:
        return ServiceErr(reason=decision.reason)

    if "name" in patch:
        e.name = patch["name"]
    if "status" in patch:
        e.status = patch["status"]
    if "metadata" in patch:
        e.metadata.update(patch["metadata"])

    e.updated_at = _now()
    repo.put(e)
    return ServiceOk(data=e, message="updated")

def archive_entity(user: User, repo: MemoryEntityRepo, *, tenant_id: str, entity_id: str) -> Any:
    e = repo.get(tenant_id, entity_id)
    if e is None:
        return ServiceErr(reason="not_found")

    decision = can_write_entity(user, e)
    if decision != Decision.ALLOW:
        return ServiceErr(reason=decision.reason)

    e.status = "archived"
    e.archived_at = _now()
    e.updated_at = _now()
    repo.put(e)
    return ServiceOk(data=e, message="archived")

# This is a thin application service layer for Venture OS:
# combines RBAC decisions (from security.guards) with a storage-agnostic repo (repo.memory)
# suitable for CLI, HTTP handlers, or jobs
# no framework, no I/O, deterministic behavior for tests
# Keep everything pure and synchronous.
# No ID generation; caller supplies id (keeps consistency across backends).
# Error messages should be short and UI/log-friendly.