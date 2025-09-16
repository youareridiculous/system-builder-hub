from __future__ import annotations

from typing import Any, Dict, Optional, Literal
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field, validator
from venture_os.entity.model import Entity, EntityKind

AssetClass = Literal["real_estate", "business", "security", "index_fund", "cash", "bond", "collectible", "alternative", "equipment", "vehicle", "ip", "crypto", "other"]
Liquidity = Literal["high", "medium", "low", "locked"]
RiskLevel = Literal["low", "medium", "high", "speculative"]
Horizon = Literal["short", "medium", "long", "permanent"]

class Asset(BaseModel):
    id: str
    tenant_id: str = Field(..., description="Tenant FK")
    name: str
    asset_class: AssetClass = "other"
    subtype: Optional[str] = None  # e.g., "single_family", "s&p500", "bourbon_cask"
    currency: str = "USD"
    cost_basis: Decimal = Decimal("0")
    acquisition_date: Optional[date] = None
    current_value: Decimal = Decimal("0")
    valuation_date: Optional[date] = None
    location: Optional[str] = None  # city/region or custodian/broker
    liquidity: Liquidity = "medium"
    risk: RiskLevel = "medium"
    horizon: Horizon = "long"
    status: str = "active"  # active | archived | sold
    notes: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = None

    @validator("cost_basis", "current_value", pre=True)
    def money_coercion(cls, value: Any) -> Decimal:
        return Decimal(value).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

    @validator("currency", pre=True)
    def clamp_currency(cls, value: str) -> str:
        return value.strip().upper() or "USD"

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        self.status = "archived"
        self.archived_at = datetime.utcnow()
        self.touch()

    def mark_sold(self, on: Optional[date] = None) -> None:
        self.status = "sold"
        self.valuation_date = on or date.today()
        self.touch()

    def set_valuation(self, value: Any, on: Optional[date] = None) -> None:
        self.current_value = self.money_coercion(value)
        self.valuation_date = on or date.today()
        self.touch()

    def unrealized_gain(self) -> Decimal:
        return self.current_value - self.cost_basis

    def gain_pct(self) -> Decimal:
        return (self.current_value / self.cost_basis - 1) * 100 if self.cost_basis > 0 else Decimal("0").quantize(Decimal('0.00'))

    def label(self) -> str:
        return f"asset:{self.name} [{self.asset_class}] ({self.currency} {self.current_value})"

    def to_entity(self) -> Entity:
        return Entity(
            id=self.id,
            tenant_id=self.tenant_id,
            kind=EntityKind("asset"),
            name=self.name,
            status="archived" if self.archived_at else self.status,
            metadata={
                "asset_class": self.asset_class,
                "subtype": self.subtype,
                "currency": self.currency,
                "cost_basis": str(self.cost_basis),
                "acquisition_date": self.acquisition_date.isoformat() if self.acquisition_date else None,
                "current_value": str(self.current_value),
                "valuation_date": self.valuation_date.isoformat() if self.valuation_date else None,
                "location": self.location,
                "liquidity": self.liquidity,
                "risk": self.risk,
                "horizon": self.horizon,
                "notes": self.notes,
                **self.metadata,
            },
            created_at=self.created_at,
            updated_at=self.updated_at,
            archived_at=self.archived_at
        )

    @classmethod
    def from_entity(cls, e: Entity) -> "Asset":
        return cls(
            id=e.id,
            tenant_id=e.tenant_id,
            name=e.name,
            status=e.status,
            metadata=e.metadata,
            # Parse Decimal fields from strings
            cost_basis=Decimal(e.metadata.get("cost_basis", "0")),
            current_value=Decimal(e.metadata.get("current_value", "0")),
            # Parse dates from ISO strings
            acquisition_date=date.fromisoformat(e.metadata.get("acquisition_date")) if e.metadata.get("acquisition_date") else None,
            valuation_date=date.fromisoformat(e.metadata.get("valuation_date")) if e.metadata.get("valuation_date") else None,
            location=e.metadata.get("location"),
            liquidity=e.metadata.get("liquidity", "medium"),
            risk=e.metadata.get("risk", "medium"),
            horizon=e.metadata.get("horizon", "long"),
            notes=e.metadata.get("notes", ""),
            archived_at=None  # Set as needed
        )