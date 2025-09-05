from typing import Any, Dict, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field

EntityKind = Literal[
    'company',
    'contact',
    'deal',
    'task',
    'doc',
    'asset',
    'note',
]  

class Entity(BaseModel):
    """
    Base entity model for multi-tenant, exit-ready applications.
    """
    id: str
    tenant_id: str = Field(..., description='Foreign key for tenant')
    kind: EntityKind
    name: str
    status: str = 'active'
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None

    def touch(self) -> None:
        """
        Update the updated_at timestamp to the current time.
        """
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        """
        Archive the entity by setting status to 'archived' and updating timestamps.
        """
        self.status = 'archived'
        self.archived_at = datetime.utcnow()
        self.touch()

    def label(self) -> str:
        """
        Generate a label for the entity in the format: '{kind}:{name} (tenant={tenant_id})'.
        """
        return f'{self.kind}:{self.name} (tenant={self.tenant_id})'
