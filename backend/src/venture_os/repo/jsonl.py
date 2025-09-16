from __future__ import annotations

import json, os, tempfile

from dataclasses import dataclass

from typing import Any, Dict, List, Optional, Callable

from datetime import datetime

from threading import RLock

from venture_os.entity.model import Entity, EntityKind

"""
JSONL format for entity storage.
Atomic rewrites ensure no partial writes. Mirrors MemoryEntityRepo API.
"""

@dataclass(frozen=True)
class Page:
    items: List[Entity]
    total: int
    offset: int
    limit: int

class JsonlEntityRepo:
    def __init__(self, path: str):
        self._path = path
        self._lock = RLock()
        self._by_tenant: Dict[str, Dict[str, Entity]] = {}

        if os.path.exists(path):
            with open(path, 'r') as f:
                for line in f:
                    entity_data = json.loads(line)
                    entity_data['updated_at'] = datetime.fromisoformat(entity_data['updated_at'])
                    entity = Entity(**entity_data)
                    self._by_tenant.setdefault(entity.tenant_id, {})[entity.id] = entity

    def _encode(self, e: Entity) -> Dict[str, Any]:
        return {**e.__dict__, 'updated_at': e.updated_at.isoformat()}

    def _decode(self, d: Dict[str, Any]) -> Entity:
        d['updated_at'] = datetime.fromisoformat(d['updated_at']) if d['updated_at'] else None
        return Entity(**d)

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _flush(self) -> None:
        temp_path = tempfile.mktemp(dir=os.path.dirname(self._path))
        with open(temp_path, 'w') as f:
            for tenant_entities in self._by_tenant.values():
                for entity in tenant_entities.values():
                    f.write(json.dumps(self._encode(entity)) + '\n')
        os.replace(temp_path, self._path)

    def put(self, e: Entity) -> Entity:
        self._by_tenant.setdefault(e.tenant_id, {})[e.id] = e
        self._flush()
        return e

    def get(self, tenant_id: str, entity_id: str) -> Optional[Entity]:
        return self._by_tenant.get(tenant_id, {}).get(entity_id)

    def delete(self, tenant_id: str, entity_id: str) -> bool:
        if tenant_id in self._by_tenant and entity_id in self._by_tenant[tenant_id]:
            del self._by_tenant[tenant_id][entity_id]
            self._flush()
            return True
        return False

    def list(self, tenant_id: str, *, kind: Optional[EntityKind] = None, status: Optional[str] = None,
             q: Optional[str] = None, tags: Optional[List[str]] = None, offset: int = 0,
             limit: int = 50, sort: str = "-updated_at") -> Page:
        # Implementation of filtering and sorting logic goes here.
        pass
