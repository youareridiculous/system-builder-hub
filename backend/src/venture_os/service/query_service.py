from __future__ import annotations

from dataclasses import dataclass

from typing import Any, Dict, List, Optional

from venture_os.entity.model import Entity, EntityKind
from venture_os.rbac.model import User
from venture_os.security.guards import can_read_entity, Decision
from venture_os.repo.memory import MemoryEntityRepo, Page

@dataclass(frozen=True)
class ServiceOk:
    data: Any
    message: str = ""

@dataclass(frozen=True)
class ServiceErr:
    reason: str
    code: str = "forbidden"  # or "invalid"

def list_entities(user: User, repo: MemoryEntityRepo, *, tenant_id: str, kind: Optional[EntityKind] = None, status: Optional[str] = None, q: Optional[str] = None, tags: Optional[List[str]] = None, offset: int = 0, limit: int = 50, sort: str = "-updated_at") -> Any:
    if user.tenant_id != tenant_id:
        return ServiceErr("cross-tenant", code="forbidden")

    page = repo.list(tenant_id, kind=kind, status=status, q=q, tags=tags, offset=offset, limit=limit, sort=sort)
    filtered_items = [e for e in page.items if can_read_entity(user, e).allow]

    return ServiceOk(data=Page(items=filtered_items, total=len(filtered_items), offset=offset, limit=limit))

def search_entities(user: User, repo: MemoryEntityRepo, *, tenant_id: str, q: str, kind: Optional[EntityKind] = None, limit: int = 25) -> Any:
    return list_entities(user, repo, tenant_id=tenant_id, q=q, limit=limit)

# This module provides a thin query layer that merges repository filters with RBAC read checks,
# suitable for CLI/HTTP later. It does not perform any I/O and is deterministic.