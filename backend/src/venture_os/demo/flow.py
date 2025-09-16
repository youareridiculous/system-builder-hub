from __future__ import annotations

from typing import Dict, Any

from datetime import datetime

from venture_os.entity.model import Entity, EntityKind
from venture_os.rbac.model import User, Role, Permission
from venture_os.repo.memory import MemoryEntityRepo
from venture_os.security.guards import can_read_entity, can_write_entity
from venture_os.service.entity_service import create_entity, get_entity, update_entity, archive_entity

def run_demo() -> None:
    tenant_id = "demo_tenant"

    # Create a writer user:
    writer = User(
        id="u_writer",
        tenant_id=tenant_id,
        email="writer@example.com",
        name="Writer",
        roles=[Role.MEMBER]
    )

    # Create a viewer user (read-only):
    viewer = User(
        id="u_viewer",
        tenant_id=tenant_id,
        email="viewer@example.com",
        name="Viewer",
        roles=[Role.VIEWER]
    )

    # Init repo:
    repo = MemoryEntityRepo()

    # Create (with supplied id—no generation):
    data: Dict[str, Any] = {
        "id": "ent_1",  # caller-supplied per our rules
        "domain": "acme.com",
        "tags": ["vip"]
    }
    res = create_entity(
        user=writer, repo=repo,
        tenant_id=tenant_id,
        kind=EntityKind("company"),
        name="Acme Corporation",
        status="active",
        metadata=data
    )
    print("[create]", res)

    # Get:
    res = get_entity(user=writer, repo=repo, tenant_id=tenant_id, entity_id="ent_1")
    print("[get/writer]", res)

    # Update (rename + add tag):
    res = update_entity(
        user=writer, repo=repo, tenant_id=tenant_id, entity_id="ent_1",
        patch={"name": "Acme Corp", "metadata": {"tags": ["vip", "priority"]}}
    )
    print("[update]", res)

    # Attempt write as viewer (should be denied):
    deny = update_entity(
        user=viewer, repo=repo, tenant_id=tenant_id, entity_id="ent_1",
        patch={"name": "Should Not Work"}
    )
    print("[update/viewer]", deny)

    # Archive:
    res = archive_entity(user=writer, repo=repo, tenant_id=tenant_id, entity_id="ent_1")
    print("[archive]", res)

    # Reader after archive (allowed):
    res = get_entity(user=viewer, repo=repo, tenant_id=tenant_id, entity_id="ent_1")
    print("[get/viewer archived]", res)

if __name__ == "__main__": run_demo()

# This is a minimal, deterministic demo that:
# shows RBAC in action (writer vs viewer),
# persists via in-memory repo,
# uses the service layer to enforce access,
# has no web/DB dependencies.