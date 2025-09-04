"""
ERP Core Models
Enterprise Resource Planning system with inventory, accounting, and business operations
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class InventoryItem(Base):
    """Inventory items/products"""
    __tablename__ = 'inventory_items'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    sku = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    unit_price = Column(Float, nullable=False, default=0.0)
    cost_price = Column(Float, nullable=False, default=0.0)
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    reorder_point = Column(Integer, default=0)
    reorder_quantity = Column(Integer, default=0)
    warehouse_id = Column(String(36), ForeignKey('warehouses.id'))
    supplier_id = Column(String(36), ForeignKey('suppliers.id'))
    barcode = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = Column(JSON)
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="inventory_items")
    supplier = relationship("Supplier", back_populates="inventory_items")


class Warehouse(Base):
    """Warehouse locations"""
    __tablename__ = 'warehouses'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    phone = Column(String(50))
    email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="warehouse")


class Supplier(Base):
    """Supplier/vendor information"""
    __tablename__ = 'suppliers'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    tax_id = Column(String(100))
    payment_terms = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inventory_items = relationship("InventoryItem", back_populates="supplier")


class PurchaseOrder(Base):
    """Purchase orders"""
    __tablename__ = 'purchase_orders'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    po_number = Column(String(100), nullable=False, unique=True)
    supplier_id = Column(String(36), ForeignKey('suppliers.id'), nullable=False)
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    expected_delivery = Column(DateTime)
    status = Column(String(50), nullable=False, default='draft')  # draft, ordered, received, cancelled
    total_amount = Column(Float, nullable=False, default=0.0)
    notes = Column(Text)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")


class PurchaseOrderItem(Base):
    """Purchase order line items"""
    __tablename__ = 'purchase_order_items'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    purchase_order_id = Column(String(36), ForeignKey('purchase_orders.id'), nullable=False)
    inventory_item_id = Column(String(36), ForeignKey('inventory_items.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    received_quantity = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    inventory_item = relationship("InventoryItem")


class SalesOrder(Base):
    """Sales orders"""
    __tablename__ = 'sales_orders'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    so_number = Column(String(100), nullable=False, unique=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255))
    customer_phone = Column(String(50))
    order_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    expected_shipment = Column(DateTime)
    status = Column(String(50), nullable=False, default='draft')  # draft, confirmed, shipped, delivered, cancelled
    total_amount = Column(Float, nullable=False, default=0.0)
    notes = Column(Text)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = relationship("SalesOrderItem", back_populates="sales_order")


class SalesOrderItem(Base):
    """Sales order line items"""
    __tablename__ = 'sales_order_items'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sales_order_id = Column(String(36), ForeignKey('sales_orders.id'), nullable=False)
    inventory_item_id = Column(String(36), ForeignKey('inventory_items.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    shipped_quantity = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sales_order = relationship("SalesOrder", back_populates="items")
    inventory_item = relationship("InventoryItem")


class GeneralLedger(Base):
    """General ledger accounts"""
    __tablename__ = 'general_ledger'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    account_number = Column(String(50), nullable=False, unique=True)
    account_name = Column(String(255), nullable=False)
    account_type = Column(String(50), nullable=False)  # asset, liability, equity, revenue, expense
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JournalEntry(Base):
    """Journal entries for accounting"""
    __tablename__ = 'journal_entries'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(255), nullable=False, index=True)
    entry_number = Column(String(100), nullable=False, unique=True)
    entry_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    description = Column(Text, nullable=False)
    reference = Column(String(255))
    total_debit = Column(Float, nullable=False, default=0.0)
    total_credit = Column(Float, nullable=False, default=0.0)
    is_posted = Column(Boolean, default=False)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lines = relationship("JournalEntryLine", back_populates="journal_entry")


class JournalEntryLine(Base):
    """Journal entry line items"""
    __tablename__ = 'journal_entry_lines'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    journal_entry_id = Column(String(36), ForeignKey('journal_entries.id'), nullable=False)
    account_id = Column(String(36), ForeignKey('general_ledger.id'), nullable=False)
    description = Column(Text)
    debit_amount = Column(Float, default=0.0)
    credit_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("GeneralLedger")
