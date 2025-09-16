"""Add ERP Core tables

Revision ID: 7a8b9c0d1e2f
Revises: 694e7cbf6b05
Create Date: 2025-09-01 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a8b9c0d1e2f'
down_revision = '694e7cbf6b05'
branch_labels = None
depends_on = None


def upgrade():
    # Create warehouses table
    op.create_table('warehouses',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_warehouses_tenant_id', 'warehouses', ['tenant_id'])
    
    # Create suppliers table
    op.create_table('suppliers',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('contact_person', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('tax_id', sa.String(100), nullable=True),
        sa.Column('payment_terms', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_suppliers_tenant_id', 'suppliers', ['tenant_id'])
    
    # Create inventory_items table
    op.create_table('inventory_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('sku', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('unit_price', sa.Float, nullable=False),
        sa.Column('cost_price', sa.Float, nullable=False),
        sa.Column('quantity_on_hand', sa.Integer, nullable=False),
        sa.Column('reorder_point', sa.Integer, nullable=True),
        sa.Column('reorder_quantity', sa.Integer, nullable=True),
        sa.Column('warehouse_id', sa.String(36), nullable=True),
        sa.Column('supplier_id', sa.String(36), nullable=True),
        sa.Column('barcode', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_inventory_items_tenant_id', 'inventory_items', ['tenant_id'])
    op.create_index('ix_inventory_items_sku', 'inventory_items', ['sku'])
    
    # Create purchase_orders table
    op.create_table('purchase_orders',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('po_number', sa.String(100), nullable=False),
        sa.Column('supplier_id', sa.String(36), nullable=False),
        sa.Column('order_date', sa.DateTime, nullable=False),
        sa.Column('expected_delivery', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('total_amount', sa.Float, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_purchase_orders_tenant_id', 'purchase_orders', ['tenant_id'])
    op.create_index('ix_purchase_orders_po_number', 'purchase_orders', ['po_number'], unique=True)
    
    # Create purchase_order_items table
    op.create_table('purchase_order_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('purchase_order_id', sa.String(36), nullable=False),
        sa.Column('inventory_item_id', sa.String(36), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit_price', sa.Float, nullable=False),
        sa.Column('total_price', sa.Float, nullable=False),
        sa.Column('received_quantity', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['inventory_item_id'], ['inventory_items.id'], ),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create sales_orders table
    op.create_table('sales_orders',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('so_number', sa.String(100), nullable=False),
        sa.Column('customer_name', sa.String(255), nullable=False),
        sa.Column('customer_email', sa.String(255), nullable=True),
        sa.Column('customer_phone', sa.String(50), nullable=True),
        sa.Column('order_date', sa.DateTime, nullable=False),
        sa.Column('expected_shipment', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('total_amount', sa.Float, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sales_orders_tenant_id', 'sales_orders', ['tenant_id'])
    op.create_index('ix_sales_orders_so_number', 'sales_orders', ['so_number'], unique=True)
    
    # Create sales_order_items table
    op.create_table('sales_order_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('sales_order_id', sa.String(36), nullable=False),
        sa.Column('inventory_item_id', sa.String(36), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit_price', sa.Float, nullable=False),
        sa.Column('total_price', sa.Float, nullable=False),
        sa.Column('shipped_quantity', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['inventory_item_id'], ['inventory_items.id'], ),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create general_ledger table
    op.create_table('general_ledger',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('account_number', sa.String(50), nullable=False),
        sa.Column('account_name', sa.String(255), nullable=False),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_general_ledger_tenant_id', 'general_ledger', ['tenant_id'])
    op.create_index('ix_general_ledger_account_number', 'general_ledger', ['account_number'], unique=True)
    
    # Create journal_entries table
    op.create_table('journal_entries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('entry_number', sa.String(100), nullable=False),
        sa.Column('entry_date', sa.DateTime, nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('reference', sa.String(255), nullable=True),
        sa.Column('total_debit', sa.Float, nullable=False),
        sa.Column('total_credit', sa.Float, nullable=False),
        sa.Column('is_posted', sa.Boolean, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_journal_entries_tenant_id', 'journal_entries', ['tenant_id'])
    op.create_index('ix_journal_entries_entry_number', 'journal_entries', ['entry_number'], unique=True)
    
    # Create journal_entry_lines table
    op.create_table('journal_entry_lines',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('journal_entry_id', sa.String(36), nullable=False),
        sa.Column('account_id', sa.String(36), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('debit_amount', sa.Float, nullable=True),
        sa.Column('credit_amount', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['general_ledger.id'], ),
        sa.ForeignKeyConstraint(['journal_entry_id'], ['journal_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('journal_entry_lines')
    op.drop_index('ix_journal_entries_entry_number', table_name='journal_entries')
    op.drop_index('ix_journal_entries_tenant_id', table_name='journal_entries')
    op.drop_table('journal_entries')
    op.drop_index('ix_general_ledger_account_number', table_name='general_ledger')
    op.drop_index('ix_general_ledger_tenant_id', table_name='general_ledger')
    op.drop_table('general_ledger')
    op.drop_table('sales_order_items')
    op.drop_index('ix_sales_orders_so_number', table_name='sales_orders')
    op.drop_index('ix_sales_orders_tenant_id', table_name='sales_orders')
    op.drop_table('sales_orders')
    op.drop_table('purchase_order_items')
    op.drop_index('ix_purchase_orders_po_number', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_tenant_id', table_name='purchase_orders')
    op.drop_table('purchase_orders')
    op.drop_index('ix_inventory_items_sku', table_name='inventory_items')
    op.drop_index('ix_inventory_items_tenant_id', table_name='inventory_items')
    op.drop_table('inventory_items')
    op.drop_index('ix_suppliers_tenant_id', table_name='suppliers')
    op.drop_table('suppliers')
    op.drop_index('ix_warehouses_tenant_id', table_name='warehouses')
    op.drop_table('warehouses')
