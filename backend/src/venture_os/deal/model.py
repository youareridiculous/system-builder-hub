from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from venture_os.entity.model import Entity, EntityKind

class Deal(BaseModel):
    id: str
    tenant_id: str = Field(..., description="Tenant FK")
    company_id: Optional[str] = None  # link to Company by id
    name: str  # short title, e.g., “ACME — Yearly SaaS”
    pipeline: str = "default"  # e.g., sales | partnerships | m&a
    stage: str = "new"  # e.g., new → discovery → proposal → negotiation → closed_won/closed_lost
    amount: Decimal = Decimal("0")  # currency amount; use Decimal, not float
    currency: str = "USD"
    probability: float = 0.1  # (0.0–1.0)
    expected_close: Optional[date] = None
    status: str = "active"  # active | archived | closed_won | closed_lost
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None

    @validator("probability", pre=True)
    def validate_probability(cls, v):
        v = float(v)
        return max(0.0, min(v, 1.0))

    @validator("amount", pre=True)
    def validate_amount(cls, v):
        return Decimal(str(v)).quantize(Decimal('0.00'))

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        self.status = "archived"
        self.archived_at = datetime.utcnow()
        self.touch()

    def advance(self, new_stage: str) -> None:
        self.stage = new_stage
        self.touch()

    def win(self) -> None:
        self.stage = "closed_won"
        self.status = "closed_won"
        self.probability = 1.0
        self.touch()

    def lose(self) -> None:
        self.stage = "closed_lost"
        self.status = "closed_lost"
        self.probability = 0.0
        self.touch()

    def label(self) -> str:
        return f"deal:{self.name} ({self.currency} {self.amount})"

    def to_entity(self) -> Entity:
        return Entity(
            id=self.id,
            tenant_id=self.tenant_id,
            kind=EntityKind("deal"),
            name=self.name,
            status=self.status if not self.archived_at else "archived",
            metadata={
                "company_id": self.company_id,
                "pipeline": self.pipeline,
                "stage": self.stage,
                "amount": str(self.amount),
                "currency": self.currency,
                "probability": self.probability,
                "expected_close": self.expected_close.isoformat() if self.expected_close else None,
                **self.metadata,
            },
            created_at=self.created_at,
            updated_at=self.updated_at,
            archived_at=self.archived_at
        )

    @classmethod
    def from_entity(cls, e: Entity) -> "Deal":
        return cls(
            id=e.id,
            tenant_id=e.tenant_id,
            company_id=e.metadata.get("company_id"),
            name=e.name,
            status=e.status,
            pipeline=e.metadata.get("pipeline", "default"),
            stage=e.metadata["stage"],
            amount=Decimal(e.metadata["amount"]),
            currency=e.metadata["currency"],
            probability=e.metadata["probability"],
            expected_close=date.fromisoformat(e.metadata["expected_close"]) if e.metadata.get("expected_close") else None,
            metadata={k: v for k, v in e.metadata.items() if k not in ["company_id", "pipeline", "stage", "amount", "currency", "probability", "expected_close"]},
            created_at=e.created_at,
            updated_at=e.updated_at,
            archived_at=e.archived_at
        )