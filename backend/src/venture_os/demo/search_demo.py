"""
This demo wires Query Service + RBAC over the in-memory repo,
showing text search, tag filtering, and kind filtering with a viewer vs admin.
"""

from __future__ import annotations

from typing import Dict, Any, List

from venture_os.entity.model import Entity, EntityKind
from venture_os.rbac.model import User, Role
from venture_os.repo.memory import MemoryEntityRepo
from venture_os.service.query_service import list_entities, search_entities
from venture_os.service.entity_service import create_entity

def run_search_demo() -> None:
    tenant_id = "demo_tenant"

    # Create users
    admin = User(id="u_admin", tenant_id=tenant_id, email="admin@example.com", name="Admin", roles=[Role.ADMIN])
    viewer = User(id="u_view", tenant_id=tenant_id, email="viewer@example.com", name="Viewer", roles=[Role.VIEWER])

    # Init repo
    repo = MemoryEntityRepo()

    # Seed a few entities
    create_entity(user=admin, repo=repo, tenant_id=tenant_id, kind=EntityKind("company"), name="Acme Corporation", metadata={"id": "c_1", "domain": "acme.com", "tags": ["vip"]})
    create_entity(user=admin, repo=repo, tenant_id=tenant_id, kind=EntityKind("company"), name="Beta Industries",   metadata={"id": "c_2", "domain": "beta.io", "tags": ["trial"]})
    create_entity(user=admin, repo=repo, tenant_id=tenant_id, kind=EntityKind("contact"), name="Jane Doe",          metadata={"id": "p_1", "email": "jane@acme.com", "tags": ["vip", "cto"]})
    create_entity(user=admin, repo=repo, tenant_id=tenant_id, kind=EntityKind("deal"),    name="ACME — Yearly SaaS",metadata={"id": "d_1", "amount": "12000", "currency": "USD", "tags": ["priority"]})

    # List all (as admin)
    res = list_entities(user=admin, repo=repo, tenant_id=tenant_id, limit=100)
    print("[list/admin] total:", res.data.total, "items:", [e.name for e in res.data.items])

    # Search by text (as viewer, RBAC read-only)
    res = search_entities(user=viewer, repo=repo, tenant_id=tenant_id, q="acme", limit=10)
    print("[search/viewer q=acme] items:", [e.name for e in res.data.items])

    # Filter by tags
    res = list_entities(user=viewer, repo=repo, tenant_id=tenant_id, tags=["vip"])
    print("[list/viewer tags=vip] items:", [e.name for e in res.data.items])

    # Filter by kind
    res = list_entities(user=viewer, repo=repo, tenant_id=tenant_id, kind=EntityKind("deal"))
    print("[list/viewer kind=deal] items:", [e.name for e in res.data.items])

if __name__ == "__main__":
    run_search_demo()
