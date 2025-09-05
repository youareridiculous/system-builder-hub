from __future__ import annotations

from dataclasses import dataclass

from typing import Any

from venture_os.entity.model import Entity, EntityKind
from venture_os.rbac.model import User
from venture_os.repo.memory import MemoryEntityRepo
from venture_os.security.guards import can_read_entity, Decision
from venture_os.linkage.relations import CompanySummary, list_company_contacts, list_company_deals
from venture_os.service.entity_service import get_entity

@dataclass(frozen=True)
class ServiceOk:
    data: Any
    message: str = ""

@dataclass(frozen=True)
class ServiceErr:
    reason: str
    code: str = "forbidden"  # or "not_found"

def get_company_summary(user: User, repo: MemoryEntityRepo, *, tenant_id: str, company_id: str) -> Any:
    """
    Return a CompanySummary (company, contacts, deals) if caller has RBAC read access.
    Filters out related entities the user cannot read.
    """
    # 1) load company entity (must exist and be kind='company')
    res = get_entity(user=user, repo=repo, tenant_id=tenant_id, entity_id=company_id)
    if isinstance(res, ServiceErr):
        return res
    company = res.data
    if company.kind != EntityKind("company"):
        return ServiceErr(reason="not a company", code="not_found")

    # 2) RBAC read check on company
    dec = can_read_entity(user, company)
    if not dec.allow:
        return ServiceErr(reason=dec.reason, code="forbidden")

    # 3) fetch related, RBAC-filtered
    contacts = list_company_contacts(user=user, repo=repo, tenant_id=tenant_id, company_id=company_id)
    deals    = list_company_deals(user=user, repo=repo, tenant_id=tenant_id, company_id=company_id)

    # 4) package
    summary = CompanySummary(company=company, contacts=contacts, deals=deals)
    return ServiceOk(data=summary, message="ok")

"""
This is a thin service wrapper over repo + linkage helpers that returns a CompanySummary for UIs, CLIs, or future HTTP endpoints.
Emphasize: no I/O, no frameworks, RBAC enforced.
"""