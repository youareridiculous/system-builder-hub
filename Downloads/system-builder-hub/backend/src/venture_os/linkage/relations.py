from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
from venture_os.entity.model import Entity, EntityKind
from venture_os.rbac.model import User
from venture_os.repo.memory import MemoryEntityRepo, Page
from venture_os.security.guards import can_read_entity, can_write_entity
from venture_os.service.entity_service import get_entity, update_entity

"""
Relationship utilities for Venture OS to connect Companies ↔ Contacts/Deals
and to produce a simple CompanySummary for UIs, CLIs, or APIs.
"""

# DTO summary (for convenience in UIs/CLIs)
@dataclass(frozen=True)
class CompanySummary:
    company: Entity
    contacts: List[Entity]
    deals: List[Entity]

# Helpers (pure functions; repo + guards only)
def link_contact_to_company(user: User, repo: MemoryEntityRepo, *, tenant_id: str, contact_id: str, company_id: str) -> Entity:
    contact = get_entity(repo, tenant_id, contact_id)
    company = get_entity(repo, tenant_id, company_id)
    if contact.kind != EntityKind("contact") or company.kind != EntityKind("company"):
        raise ValueError("Invalid entity kind.")
    if not can_write_entity(user, contact):
        raise ValueError("User cannot write to contact.")
    if not can_read_entity(user, company):
        raise ValueError("User cannot read company.")
    contact.metadata["company_id"] = company_id
    return update_entity(repo, contact)

def link_deal_to_company(user: User, repo: MemoryEntityRepo, *, tenant_id: str, deal_id: str, company_id: str) -> Entity:
    deal = get_entity(repo, tenant_id, deal_id)
    company = get_entity(repo, tenant_id, company_id)
    if deal.kind != EntityKind("deal") or company.kind != EntityKind("company"):
        raise ValueError("Invalid entity kind.")
    if not can_write_entity(user, deal):
        raise ValueError("User cannot write to deal.")
    if not can_read_entity(user, company):
        raise ValueError("User cannot read company.")
    deal.metadata["company_id"] = company_id
    return update_entity(repo, deal)

def list_company_contacts(user: User, repo: MemoryEntityRepo, *, tenant_id: str, company_id: str, limit: int = 100) -> List[Entity]:
    contacts = repo.list(tenant_id, kind=EntityKind("contact"), limit=limit)
    return [e for e in contacts if e.metadata.get("company_id") == company_id and can_read_entity(user, e)]

def list_company_deals(user: User, repo: MemoryEntityRepo, *, tenant_id: str, company_id: str, limit: int = 100) -> List[Entity]:
    deals = repo.list(tenant_id, kind=EntityKind("deal"), limit=limit)
    return [e for e in deals if e.metadata.get("company_id") == company_id and can_read_entity(user, e)]

def get_company_summary(user: User, repo: MemoryEntityRepo, *, tenant_id: str, company_id: str) -> CompanySummary:
    company = get_entity(repo, tenant_id, company_id)
    if company.kind != EntityKind("company") or not can_read_entity(user, company):
        raise ValueError("Invalid company or access denied.")
    contacts = list_company_contacts(user, repo, tenant_id=tenant_id, company_id=company_id)
    deals = list_company_deals(user, repo, tenant_id=tenant_id, company_id=company_id)
    return CompanySummary(company=company, contacts=contacts, deals=deals)
