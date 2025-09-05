from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from venture_os.entity.model import Entity, EntityKind

class Task(BaseModel):
    id: str
    tenant_id: str = Field(..., description="Tenant FK")
    title: str
    description: str = ""
    status: str = "todo"  # allowed: todo, in_progress, blocked, done, canceled
    priority: str = "medium"  # allowed: low, medium, high, urgent
    assignee_ids: List[str] = Field(default_factory=list)  # user ids; optional
    related_entity_id: Optional[str] = None  # link to company/deal/contact/etc.
    tags: List[str] = Field(default_factory=list)
    due_date: Optional[date] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None

    @validator("status", pre=True)
    def validate_status(cls, value: str) -> str:
        allowed_values = {"todo", "in_progress", "blocked", "done", "canceled"}
        return value.strip().lower() if value.strip().lower() in allowed_values else "todo"

    @validator("priority", pre=True)
    def validate_priority(cls, value: str) -> str:
        allowed_values = {"low", "medium", "high", "urgent"}
        return value.strip().lower() if value.strip().lower() in allowed_values else "medium"

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def start(self) -> None:
        self.status = "in_progress"
        self.touch()

    def complete(self) -> None:
        self.status = "done"
        self.archived_at = None
        self.touch()

    def block(self) -> None:
        self.status = "blocked"
        self.touch()

    def cancel(self) -> None:
        self.status = "canceled"
        self.touch()

    def reopen(self) -> None:
        self.status = "todo"
        self.archived_at = None
        self.touch()

    def archive(self) -> None:
        self.archived_at = datetime.utcnow()
        if self.status not in {"done", "canceled"}:
            self.status = "canceled"
        self.touch()

    def label(self) -> str:
        return f"task:{self.title} (prio={self.priority})"

    def to_entity(self) -> Entity:
        return Entity(
            id=self.id,
            tenant_id=self.tenant_id,
            kind=EntityKind("task"),
            name=self.title,
            status="archived" if self.archived_at else self.status,
            metadata={
                "description": self.description,
                "priority": self.priority,
                "assignee_ids": self.assignee_ids,
                "related_entity_id": self.related_entity_id,
                "tags": self.tags,
                "due_date": self.due_date.isoformat() if self.due_date else None,
                **self.metadata,
            },
            created_at=self.created_at,
            updated_at=self.updated_at,
            archived_at=self.archived_at,
        )

    @classmethod
    def from_entity(cls, e: Entity) -> "Task":
        return cls(
            id=e.id,
            tenant_id=e.tenant_id,
            title=e.name,
            status=e.status,
            description=e.metadata.get("description", ""),
            priority=e.metadata.get("priority", "medium"),
            assignee_ids=e.metadata.get("assignee_ids", []),
            related_entity_id=e.metadata.get("related_entity_id", None),
            tags=e.metadata.get("tags", []),
            due_date=date.fromisoformat(e.metadata["due_date"]) if e.metadata.get("due_date") else None,
            metadata={k: v for k, v in e.metadata.items() if k not in {"description", "priority", "assignee_ids", "related_entity_id", "tags", "due_date"}},
            created_at=e.created_at,
            updated_at=e.updated_at,
            archived_at=e.archived_at,
        )
