"""
Tenant model for managing tenant information.
"""

from pydantic import BaseModel
from typing import Dict, Any


class Tenant(BaseModel):
    id: str
    name: str
    slug: str
    metadata: Dict[str, Any]
    tenant_description: str = ""

    class Config:
        json_encoders = {}


def get_tenant_info(tenant: Tenant) -> str:
    return f"Tenant {tenant.name} ({tenant.slug})"