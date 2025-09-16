"""
This demo seeds minimal data, links entities, and retrieves a CompanySummary via the service layer with RBAC read checks. Pure Python, no frameworks/DB.
"""

from __future__ import annotations

from typing import Any, Dict

from venture_os.entity.model import EntityKind
from venture_os.rbac.model import User, Role
from venture_os.repo.memory import MemoryEntityRepo
from venture_os.service.entity_service import create_entity
from venture_os.linkage.relations import link_contact_to_company, link_deal_to_company
from venture_os.service.company_service import get_company_summary

def run_company_summary_demo() -> None:
    tenant_id = "demo_tenant"

    # Users:
    admin = User(id="u_admin", tenant_id=tenant_id, email="admin@example.com", name="Admin", roles=[Role.ADMIN])
    viewer = User(id="u_view", tenant_id=tenant_id, email="viewer@example.com", name="Viewer", roles=[Role.VIEWER])

    # Repo:
    repo = MemoryEntityRepo()

    # Seed entities (caller-supplied IDs):
    create_entity(user=admin, repo=repo, tenant_id=tenant_id, kind=EntityKind("company"), name="Acme Corporation", metadata={"id": "c_1", "domain": "acme.com", "tags": ["vip"]})
    create_entity(user=admin, repo=repo, tenant_id=tenant_id, kind=EntityKind("contact"), name="Jane Doe", metadata={"id": "p_1", "email": "jane@acme.com", "title": "CTO"})
    create_entity(user=admin, repo=repo, tenant_id=tenant_id, kind=EntityKind("deal"), name="ACME — Yearly SaaS", metadata={"id": "d_1", "amount": "12000", "currency": "USD", "stage": "proposal"})

    # Link contact & deal → company:
    link_contact_to_company(user=admin, repo=repo, tenant_id=tenant_id, contact_id="p_1", company_id="c_1")
    link_deal_to_company(user=admin, repo=repo, tenant_id=tenant_id, deal_id="d_1", company_id="c_1")

    # Fetch summary (admin):
    res = get_company_summary(user=admin, repo=repo, tenant_id=tenant_id, company_id="c_1")
    print("[summary/admin]", "ok" if getattr(res, "data", None) else res)
    if getattr(res, "data", None):
        s = res.data
        print(" company:", s.company.name)
        print(" contacts:", [e.name for e in s.contacts])
        print(" deals:", [e.name for e in s.deals])

    # Fetch summary (viewer, read-only): repeat with user=viewer to prove RBAC read works.
    res = get_company_summary(user=viewer, repo=repo, tenant_id=tenant_id, company_id="c_1")
    print("[summary/viewer]", "ok" if getattr(res, "data", None) else res)
    if getattr(res, "data", None):
        s = res.data
        print(" company:", s.company.name)
        print(" contacts:", [e.name for e in s.contacts])
        print(" deals:", [e.name for e in s.deals])

if __name__ == "__main__":
    run_company_summary_demo()
