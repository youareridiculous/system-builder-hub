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
    contact_res = get_entity(user, repo, tenant_id=tenant_id, entity_id=contact_id)
    company_res = get_entity(user, repo, tenant_id=tenant_id, entity_id=company_id)
    
    if not hasattr(contact_res, "data") or not hasattr(company_res, "data"):
        raise ValueError("Entity not found.")
    
    contact = contact_res.data
    company = company_res.data
    
    if contact.kind != "contact" or company.kind != "company":
        raise ValueError("Invalid entity kind.")
    if not can_write_entity(user, contact).allow:
        raise ValueError("User cannot write to contact.")
    if not can_read_entity(user, company).allow:
        raise ValueError("User cannot read company.")
    
    contact.metadata["company_id"] = company_id
    update_res = update_entity(user, repo, tenant_id=tenant_id, entity_id=contact_id, patch={"metadata": contact.metadata})
    if not hasattr(update_res, "data"):
        raise ValueError("Failed to update contact.")
    return update_res.data

def link_deal_to_company(user: User, repo: MemoryEntityRepo, *, tenant_id: str, deal_id: str, company_id: str) -> Entity:
    deal_res = get_entity(user, repo, tenant_id=tenant_id, entity_id=deal_id)
    company_res = get_entity(user, repo, tenant_id=tenant_id, entity_id=company_id)
    
    if not hasattr(deal_res, "data") or not hasattr(company_res, "data"):
        raise ValueError("Entity not found.")
    
    deal = deal_res.data
    company = company_res.data
    
    if deal.kind != "deal" or company.kind != "company":
        raise ValueError("Invalid entity kind.")
    if not can_write_entity(user, deal).allow:
        raise ValueError("User cannot write to deal.")
    if not can_read_entity(user, company).allow:
        raise ValueError("User cannot read company.")
    
    deal.metadata["company_id"] = company_id
    update_res = update_entity(user, repo, tenant_id=tenant_id, entity_id=deal_id, patch={"metadata": deal.metadata})
    if not hasattr(update_res, "data"):
        raise ValueError("Failed to update deal.")
    return update_res.data

def list_company_contacts(user: User, repo: MemoryEntityRepo, *, tenant_id: str, company_id: str, limit: int = 100) -> List[Entity]:
    page = repo.list(tenant_id, kind="contact", limit=limit)
    return [e for e in page.items if e.metadata.get("company_id") == company_id and can_read_entity(user, e).allow]

def list_company_deals(user: User, repo: MemoryEntityRepo, *, tenant_id: str, company_id: str, limit: int = 100) -> List[Entity]:
    page = repo.list(tenant_id, kind="deal", limit=limit)
    return [e for e in page.items if e.metadata.get("company_id") == company_id and can_read_entity(user, e).allow]

def get_company_summary(user: User, repo: MemoryEntityRepo, *, tenant_id: str, company_id: str) -> CompanySummary:
    company_res = get_entity(user, repo, tenant_id=tenant_id, entity_id=company_id)
    if not hasattr(company_res, "data"):
        raise ValueError("Company not found.")
    
    company = company_res.data
    if company.kind != "company" or not can_read_entity(user, company).allow:
        raise ValueError("Invalid company or access denied.")
    
    contacts = list_company_contacts(user, repo, tenant_id=tenant_id, company_id=company_id)
    deals = list_company_deals(user, repo, tenant_id=tenant_id, company_id=company_id)
    return CompanySummary(company=company, contacts=contacts, deals=deals)
