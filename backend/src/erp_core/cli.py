"""
ERP Core CLI Commands
Command-line interface for ERP Core operations
"""

import click
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid

from src.db_core import get_database_url

logger = logging.getLogger(__name__)


def get_db_session():
    """Get database session for ERP operations"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()


@click.group()
def erp():
    """ERP Core management commands"""
    pass


@erp.command()
@click.option('--tenant', default='demo', help='Tenant ID for seeding')
def seed(tenant):
    """Seed ERP Core with demo data"""
    try:
        logger.info(f"Seeding ERP Core data for tenant: {tenant}")
        session = get_db_session()
        
        # Create demo warehouse
        warehouse_id = str(uuid.uuid4())
        session.execute(text("""
            INSERT INTO warehouses (
                id, tenant_id, name, address, city, state, country, postal_code, phone, email
            ) VALUES (
                :id, :tenant_id, :name, :address, :city, :state, :country, :postal_code, :phone, :email
            )
        """), {
            'id': warehouse_id,
            'tenant_id': tenant,
            'name': 'Main Warehouse',
            'address': '123 Business St',
            'city': 'San Francisco',
            'state': 'CA',
            'country': 'USA',
            'postal_code': '94105',
            'phone': '+1-555-0123',
            'email': 'warehouse@demo.com'
        })
        
        # Create demo supplier
        supplier_id = str(uuid.uuid4())
        session.execute(text("""
            INSERT INTO suppliers (
                id, tenant_id, name, contact_person, email, phone, address, city, state, country, postal_code
            ) VALUES (
                :id, :tenant_id, :name, :contact_person, :email, :phone, :address, :city, :state, :country, :postal_code
            )
        """), {
            'id': supplier_id,
            'tenant_id': tenant,
            'name': 'Tech Supplies Co',
            'contact_person': 'John Supplier',
            'email': 'john@techsupplies.com',
            'phone': '+1-555-0456',
            'address': '456 Supplier Ave',
            'city': 'Los Angeles',
            'state': 'CA',
            'country': 'USA',
            'postal_code': '90210'
        })
        
        # Create demo inventory items
        inventory_items = [
            {
                'sku': 'LAPTOP-001',
                'name': 'Business Laptop',
                'description': 'High-performance business laptop',
                'category': 'Electronics',
                'unit_price': 1299.99,
                'cost_price': 899.99,
                'quantity_on_hand': 25,
                'reorder_point': 5,
                'reorder_quantity': 20
            },
            {
                'sku': 'DESK-001',
                'name': 'Office Desk',
                'description': 'Standard office desk',
                'category': 'Furniture',
                'unit_price': 299.99,
                'cost_price': 199.99,
                'quantity_on_hand': 15,
                'reorder_point': 3,
                'reorder_quantity': 10
            },
            {
                'sku': 'CHAIR-001',
                'name': 'Ergonomic Chair',
                'description': 'Comfortable ergonomic office chair',
                'category': 'Furniture',
                'unit_price': 199.99,
                'cost_price': 129.99,
                'quantity_on_hand': 30,
                'reorder_point': 8,
                'reorder_quantity': 15
            },
            {
                'sku': 'MONITOR-001',
                'name': '24" Monitor',
                'description': '24-inch LED monitor',
                'category': 'Electronics',
                'unit_price': 249.99,
                'cost_price': 179.99,
                'quantity_on_hand': 20,
                'reorder_point': 4,
                'reorder_quantity': 12
            },
            {
                'sku': 'KEYBOARD-001',
                'name': 'Wireless Keyboard',
                'description': 'Wireless ergonomic keyboard',
                'category': 'Electronics',
                'unit_price': 79.99,
                'cost_price': 49.99,
                'quantity_on_hand': 50,
                'reorder_point': 10,
                'reorder_quantity': 25
            }
        ]
        
        for item in inventory_items:
            session.execute(text("""
                INSERT INTO inventory_items (
                    id, tenant_id, sku, name, description, category,
                    unit_price, cost_price, quantity_on_hand,
                    reorder_point, reorder_quantity, warehouse_id, supplier_id
                ) VALUES (
                    :id, :tenant_id, :sku, :name, :description, :category,
                    :unit_price, :cost_price, :quantity_on_hand,
                    :reorder_point, :reorder_quantity, :warehouse_id, :supplier_id
                )
            """), {
                'id': str(uuid.uuid4()),
                'tenant_id': tenant,
                'warehouse_id': warehouse_id,
                'supplier_id': supplier_id,
                **item
            })
        
        # Create demo general ledger accounts
        accounts = [
            {'account_number': '1000', 'account_name': 'Cash', 'account_type': 'asset'},
            {'account_number': '1100', 'account_name': 'Accounts Receivable', 'account_type': 'asset'},
            {'account_number': '1200', 'account_name': 'Inventory', 'account_type': 'asset'},
            {'account_number': '2000', 'account_name': 'Accounts Payable', 'account_type': 'liability'},
            {'account_number': '3000', 'account_name': 'Owner Equity', 'account_type': 'equity'},
            {'account_number': '4000', 'account_name': 'Sales Revenue', 'account_type': 'revenue'},
            {'account_number': '5000', 'account_name': 'Cost of Goods Sold', 'account_type': 'expense'},
            {'account_number': '6000', 'account_name': 'Operating Expenses', 'account_type': 'expense'}
        ]
        
        for account in accounts:
            session.execute(text("""
                INSERT INTO general_ledger (
                    id, tenant_id, account_number, account_name, account_type
                ) VALUES (
                    :id, :tenant_id, :account_number, :account_name, :account_type
                )
            """), {
                'id': str(uuid.uuid4()),
                'tenant_id': tenant,
                **account
            })
        
        # Create demo purchase order
        po_id = str(uuid.uuid4())
        session.execute(text("""
            INSERT INTO purchase_orders (
                id, tenant_id, po_number, supplier_id, order_date, expected_delivery,
                status, total_amount, created_by
            ) VALUES (
                :id, :tenant_id, :po_number, :supplier_id, :order_date, :expected_delivery,
                :status, :total_amount, :created_by
            )
        """), {
            'id': po_id,
            'tenant_id': tenant,
            'po_number': 'PO-2025-001',
            'supplier_id': supplier_id,
            'order_date': datetime.utcnow(),
            'expected_delivery': datetime.utcnow() + timedelta(days=7),
            'status': 'ordered',
            'total_amount': 2599.98,
            'created_by': 'demo-user'
        })
        
        # Create demo sales order
        so_id = str(uuid.uuid4())
        session.execute(text("""
            INSERT INTO sales_orders (
                id, tenant_id, so_number, customer_name, customer_email, order_date,
                expected_shipment, status, total_amount, created_by
            ) VALUES (
                :id, :tenant_id, :so_number, :customer_name, :customer_email, :order_date,
                :expected_shipment, :status, :total_amount, :created_by
            )
        """), {
            'id': so_id,
            'tenant_id': tenant,
            'so_number': 'SO-2025-001',
            'customer_name': 'Acme Corp',
            'customer_email': 'purchasing@acme.com',
            'order_date': datetime.utcnow(),
            'expected_shipment': datetime.utcnow() + timedelta(days=3),
            'status': 'confirmed',
            'total_amount': 1599.98,
            'created_by': 'demo-user'
        })
        
        session.commit()
        session.close()
        
        logger.info(f"✅ ERP Core seeded successfully for tenant: {tenant}")
        logger.info(f"   - Created 1 warehouse, 1 supplier")
        logger.info(f"   - Created 5 inventory items")
        logger.info(f"   - Created 8 general ledger accounts")
        logger.info(f"   - Created 1 purchase order, 1 sales order")
        
    except Exception as e:
        logger.error(f"Failed to seed ERP Core: {e}")
        raise click.ClickException(f"Seeding failed: {e}")


@erp.command()
@click.option('--tenant', default='demo', help='Tenant ID to check')
def status(tenant):
    """Check ERP Core status and data"""
    try:
        logger.info(f"Checking ERP Core status for tenant: {tenant}")
        session = get_db_session()
        
        # Check tables exist
        tables = ['inventory_items', 'warehouses', 'suppliers', 'purchase_orders', 
                 'sales_orders', 'general_ledger', 'journal_entries']
        
        for table in tables:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tenant_id"), 
                                   {'tenant_id': tenant}).fetchone()
            count = result[0] if result else 0
            logger.info(f"   {table}: {count} records")
        
        # Check inventory summary
        summary = session.execute(text("""
            SELECT 
                COUNT(*) as total_items,
                SUM(quantity_on_hand) as total_quantity,
                SUM(quantity_on_hand * unit_price) as total_value
            FROM inventory_items
            WHERE tenant_id = :tenant_id
        """), {'tenant_id': tenant}).fetchone()
        
        if summary:
            logger.info(f"   Inventory Summary:")
            logger.info(f"     - Total items: {summary.total_items}")
            logger.info(f"     - Total quantity: {summary.total_quantity or 0}")
            logger.info(f"     - Total value: ${summary.total_value or 0:.2f}")
        
        session.close()
        logger.info("✅ ERP Core status check completed")
        
    except Exception as e:
        logger.error(f"Failed to check ERP Core status: {e}")
        raise click.ClickException(f"Status check failed: {e}")


@erp.command()
@click.option('--tenant', default='demo', help='Tenant ID to reset')
def reset(tenant):
    """Reset ERP Core data for a tenant"""
    try:
        logger.info(f"Resetting ERP Core data for tenant: {tenant}")
        session = get_db_session()
        
        # Delete all ERP data for the tenant (in correct order due to foreign keys)
        tables = [
            'journal_entry_lines',  # No tenant_id, delete all
            'journal_entries', 'sales_order_items', 'sales_orders',
            'purchase_order_items', 'purchase_orders', 'inventory_items', 'warehouses', 'suppliers',
            'general_ledger'
        ]
        
        for table in tables:
            if table == 'journal_entry_lines':
                # This table doesn't have tenant_id, delete all
                result = session.execute(text(f"DELETE FROM {table}"))
            else:
                result = session.execute(text(f"DELETE FROM {table} WHERE tenant_id = :tenant_id"), 
                                       {'tenant_id': tenant})
            deleted_count = result.rowcount
            logger.info(f"   Deleted {deleted_count} records from {table}")
        
        session.commit()
        session.close()
        
        logger.info(f"✅ ERP Core reset completed for tenant: {tenant}")
        
    except Exception as e:
        logger.error(f"Failed to reset ERP Core: {e}")
        raise click.ClickException(f"Reset failed: {e}")
