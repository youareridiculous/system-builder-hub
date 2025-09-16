from __future__ import annotations

from dataclasses import dataclass

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from datetime import datetime

from threading import RLock

from venture_os.entity.model import Entity, EntityKind

@dataclass(frozen=True)
class Page:
    items: List[Entity]
    total: int
    offset: int
    limit: int

Predicate = Callable[[Entity], bool]

class MemoryEntityRepo:
    def __init__(self) -> None:
        self._lock = RLock()
        self._by_tenant: Dict[str, Dict[str, Entity]] = {}

    def put(self, e: Entity) -> Entity:
        with self._lock:
            tenant_entities = self._by_tenant.setdefault(e.tenant_id, {})
            e.updated_at = self._now()
            tenant_entities[e.id] = e
            return e

    def get(self, tenant_id: str, entity_id: str) -> Optional[Entity]:
        with self._lock:
            return self._by_tenant.get(tenant_id, {}).get(entity_id)

    def delete(self, tenant_id: str, entity_id: str) -> bool:
        with self._lock:
            if tenant_id in self._by_tenant and entity_id in self._by_tenant[tenant_id]:
                del self._by_tenant[tenant_id][entity_id]
                return True
            return False

    def list(self, tenant_id: str, *, kind: Optional[EntityKind]=None, status: Optional[str]=None,
             q: Optional[str]=None, tags: Optional[List[str]]=None, offset: int=0, limit: int=50,
             sort: str = "-updated_at") -> Page:
        with self._lock:
            tenant_entities = self._by_tenant.get(tenant_id, {}).values()
            filtered_entities = [e for e in tenant_entities if self._matches(e, kind, status, q, tags)]
            total = len(filtered_entities)
            if sort.startswith("-"):
                filtered_entities.sort(key=lambda e: getattr(e, sort[1:]), reverse=True)
            else:
                filtered_entities.sort(key=lambda e: getattr(e, sort))
            return Page(items=filtered_entities[offset:offset + limit], total=total, offset=offset, limit=limit)

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _matches(self, e: Entity, kind: Optional[EntityKind], status: Optional[str], q: Optional[str], tags: Optional[List[str]]) -> bool:
        if kind and e.kind != kind:
            return False
        if status and e.status != status:
            return False
        if q and not (q.lower() in e.name.lower() or (e.metadata and any(q.lower() in str(v).lower() for v in e.metadata.values()))):
            return False
        if tags and e.metadata.get("tags"):
            if not all(tag in e.metadata["tags"] for tag in tags):
                return False
        return True
