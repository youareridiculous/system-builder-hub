"""
ERP Core API
Enterprise Resource Planning system endpoints
"""

import logging
from typing import Dict, Any, List
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid

from src.db_core import get_database_url
from src.security.decorators import require_tenant_context

logger = logging.getLogger(__name__)

# Create blueprints for different ERP modules
inventory_bp = Blueprint('inventory', __name__, url_prefix='/api/inventory')
orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')
accounting_bp = Blueprint('accounting', __name__, url_prefix='/api/accounting')
warehouses_bp = Blueprint('warehouses', __name__, url_prefix='/api/warehouses')
suppliers_bp = Blueprint('suppliers', __name__, url_prefix='/api/suppliers')


def get_db_session():
    """Get database session for ERP operations"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()


# Inventory Management Endpoints
@inventory_bp.route('/', methods=['GET'])
@require_tenant_context
def list_inventory_items():
    """List all inventory items for the tenant"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        session = get_db_session()
        
        # Get inventory items with warehouse and supplier info
        result = session.execute(text("""
            SELECT 
                i.id, i.sku, i.name, i.description, i.category,
                i.unit_price, i.cost_price, i.quantity_on_hand,
                i.reorder_point, i.reorder_quantity, i.barcode,
                i.is_active, i.created_at, i.updated_at,
                w.name as warehouse_name,
                s.name as supplier_name
            FROM inventory_items i
            LEFT JOIN warehouses w ON i.warehouse_id = w.id
            LEFT JOIN suppliers s ON i.supplier_id = s.id
            WHERE i.tenant_id = :tenant_id
            ORDER BY i.name
        """), {'tenant_id': tenant_id})
        
        items = []
        for row in result:
            items.append({
                'id': row.id,
                'sku': row.sku,
                'name': row.name,
                'description': row.description,
                'category': row.category,
                'unit_price': float(row.unit_price),
                'cost_price': float(row.cost_price),
                'quantity_on_hand': row.quantity_on_hand,
                'reorder_point': row.reorder_point,
                'reorder_quantity': row.reorder_quantity,
                'barcode': row.barcode,
                'is_active': bool(row.is_active),
                'warehouse_name': row.warehouse_name,
                'supplier_name': row.supplier_name,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
        
        session.close()
        
        return jsonify({
            'data': items,
            'meta': {
                'total': len(items),
                'tenant_id': tenant_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list inventory items: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'INVENTORY_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


@inventory_bp.route('/', methods=['POST'])
@require_tenant_context
def create_inventory_item():
    """Create a new inventory item"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        data = request.get_json()
        
        if not data.get('sku') or not data.get('name'):
            return jsonify({
                'errors': [{
                    'status': 400,
                    'code': 'MISSING_REQUIRED_FIELDS',
                    'detail': 'SKU and name are required'
                }]
            }), 400
        
        session = get_db_session()
        
        # Check if SKU already exists
        existing = session.execute(text("""
            SELECT id FROM inventory_items 
            WHERE tenant_id = :tenant_id AND sku = :sku
        """), {'tenant_id': tenant_id, 'sku': data['sku']}).fetchone()
        
        if existing:
            session.close()
            return jsonify({
                'errors': [{
                    'status': 409,
                    'code': 'SKU_EXISTS',
                    'detail': f'SKU {data["sku"]} already exists'
                }]
            }), 409
        
        # Insert new inventory item
        result = session.execute(text("""
            INSERT INTO inventory_items (
                id, tenant_id, sku, name, description, category,
                unit_price, cost_price, quantity_on_hand,
                reorder_point, reorder_quantity, barcode, is_active
            ) VALUES (
                :id, :tenant_id, :sku, :name, :description, :category,
                :unit_price, :cost_price, :quantity_on_hand,
                :reorder_point, :reorder_quantity, :barcode, :is_active
            ) RETURNING id
        """), {
            'id': str(uuid.uuid4()),
            'tenant_id': tenant_id,
            'sku': data['sku'],
            'name': data['name'],
            'description': data.get('description'),
            'category': data.get('category'),
            'unit_price': data.get('unit_price', 0.0),
            'cost_price': data.get('cost_price', 0.0),
            'quantity_on_hand': data.get('quantity_on_hand', 0),
            'reorder_point': data.get('reorder_point', 0),
            'reorder_quantity': data.get('reorder_quantity', 0),
            'barcode': data.get('barcode'),
            'is_active': data.get('is_active', True)
        })
        
        item_id = result.fetchone()[0]
        session.commit()
        session.close()
        
        return jsonify({
            'data': {
                'id': item_id,
                'message': 'Inventory item created successfully'
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to create inventory item: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'INVENTORY_CREATE_FAILED',
                'detail': str(e)
            }]
        }), 500


# Warehouse Management Endpoints
@warehouses_bp.route('/', methods=['GET'])
@require_tenant_context
def list_warehouses():
    """List all warehouses for the tenant"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        session = get_db_session()
        
        result = session.execute(text("""
            SELECT id, name, address, city, state, country, postal_code,
                   phone, email, is_active, created_at, updated_at
            FROM warehouses
            WHERE tenant_id = :tenant_id
            ORDER BY name
        """), {'tenant_id': tenant_id})
        
        warehouses = []
        for row in result:
            warehouses.append({
                'id': row.id,
                'name': row.name,
                'address': row.address,
                'city': row.city,
                'state': row.state,
                'country': row.country,
                'postal_code': row.postal_code,
                'phone': row.phone,
                'email': row.email,
                'is_active': bool(row.is_active),
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
        
        session.close()
        
        return jsonify({
            'data': warehouses,
            'meta': {
                'total': len(warehouses),
                'tenant_id': tenant_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list warehouses: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'WAREHOUSE_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


# Supplier Management Endpoints
@suppliers_bp.route('/', methods=['GET'])
@require_tenant_context
def list_suppliers():
    """List all suppliers for the tenant"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        session = get_db_session()
        
        result = session.execute(text("""
            SELECT id, name, contact_person, email, phone, address,
                   city, state, country, postal_code, tax_id,
                   payment_terms, is_active, created_at, updated_at
            FROM suppliers
            WHERE tenant_id = :tenant_id
            ORDER BY name
        """), {'tenant_id': tenant_id})
        
        suppliers = []
        for row in result:
            suppliers.append({
                'id': row.id,
                'name': row.name,
                'contact_person': row.contact_person,
                'email': row.email,
                'phone': row.phone,
                'address': row.address,
                'city': row.city,
                'state': row.state,
                'country': row.country,
                'postal_code': row.postal_code,
                'tax_id': row.tax_id,
                'payment_terms': row.payment_terms,
                'is_active': bool(row.is_active),
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
        
        session.close()
        
        return jsonify({
            'data': suppliers,
            'meta': {
                'total': len(suppliers),
                'tenant_id': tenant_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list suppliers: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'SUPPLIER_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


# Purchase Orders Endpoints
@orders_bp.route('/purchase', methods=['GET'])
@require_tenant_context
def list_purchase_orders():
    """List all purchase orders for the tenant"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        session = get_db_session()
        
        result = session.execute(text("""
            SELECT 
                po.id, po.po_number, po.order_date, po.expected_delivery,
                po.status, po.total_amount, po.notes, po.created_by,
                po.created_at, po.updated_at,
                s.name as supplier_name
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.id
            WHERE po.tenant_id = :tenant_id
            ORDER BY po.order_date DESC
        """), {'tenant_id': tenant_id})
        
        orders = []
        for row in result:
            orders.append({
                'id': row.id,
                'po_number': row.po_number,
                'order_date': row.order_date.isoformat() if row.order_date else None,
                'expected_delivery': row.expected_delivery.isoformat() if row.expected_delivery else None,
                'status': row.status,
                'total_amount': float(row.total_amount),
                'notes': row.notes,
                'created_by': row.created_by,
                'supplier_name': row.supplier_name,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
        
        session.close()
        
        return jsonify({
            'data': orders,
            'meta': {
                'total': len(orders),
                'tenant_id': tenant_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list purchase orders: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'PURCHASE_ORDER_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


# Sales Orders Endpoints
@orders_bp.route('/sales', methods=['GET'])
@require_tenant_context
def list_sales_orders():
    """List all sales orders for the tenant"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        session = get_db_session()
        
        result = session.execute(text("""
            SELECT id, so_number, customer_name, customer_email, customer_phone,
                   order_date, expected_shipment, status, total_amount,
                   notes, created_by, created_at, updated_at
            FROM sales_orders
            WHERE tenant_id = :tenant_id
            ORDER BY order_date DESC
        """), {'tenant_id': tenant_id})
        
        orders = []
        for row in result:
            orders.append({
                'id': row.id,
                'so_number': row.so_number,
                'customer_name': row.customer_name,
                'customer_email': row.customer_email,
                'customer_phone': row.customer_phone,
                'order_date': row.order_date.isoformat() if row.order_date else None,
                'expected_shipment': row.expected_shipment.isoformat() if row.expected_shipment else None,
                'status': row.status,
                'total_amount': float(row.total_amount),
                'notes': row.notes,
                'created_by': row.created_by,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
        
        session.close()
        
        return jsonify({
            'data': orders,
            'meta': {
                'total': len(orders),
                'tenant_id': tenant_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list sales orders: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'SALES_ORDER_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


# Accounting Endpoints
@accounting_bp.route('/accounts', methods=['GET'])
@require_tenant_context
def list_accounts():
    """List all general ledger accounts for the tenant"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        session = get_db_session()
        
        result = session.execute(text("""
            SELECT id, account_number, account_name, account_type,
                   description, is_active, created_at, updated_at
            FROM general_ledger
            WHERE tenant_id = :tenant_id
            ORDER BY account_number
        """), {'tenant_id': tenant_id})
        
        accounts = []
        for row in result:
            accounts.append({
                'id': row.id,
                'account_number': row.account_number,
                'account_name': row.account_name,
                'account_type': row.account_type,
                'description': row.description,
                'is_active': bool(row.is_active),
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
        
        session.close()
        
        return jsonify({
            'data': accounts,
            'meta': {
                'total': len(accounts),
                'tenant_id': tenant_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list accounts: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'ACCOUNT_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


@accounting_bp.route('/journal-entries', methods=['GET'])
@require_tenant_context
def list_journal_entries():
    """List all journal entries for the tenant"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        session = get_db_session()
        
        result = session.execute(text("""
            SELECT id, entry_number, entry_date, description, reference,
                   total_debit, total_credit, is_posted, created_by,
                   created_at, updated_at
            FROM journal_entries
            WHERE tenant_id = :tenant_id
            ORDER BY entry_date DESC
        """), {'tenant_id': tenant_id})
        
        entries = []
        for row in result:
            entries.append({
                'id': row.id,
                'entry_number': row.entry_number,
                'entry_date': row.entry_date.isoformat() if row.entry_date else None,
                'description': row.description,
                'reference': row.reference,
                'total_debit': float(row.total_debit),
                'total_credit': float(row.total_credit),
                'is_posted': bool(row.is_posted),
                'created_by': row.created_by,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
        
        session.close()
        
        return jsonify({
            'data': entries,
            'meta': {
                'total': len(entries),
                'tenant_id': tenant_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to list journal entries: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'JOURNAL_ENTRY_LIST_FAILED',
                'detail': str(e)
            }]
        }), 500


# ERP Dashboard/Summary Endpoints
@inventory_bp.route('/dashboard', methods=['GET'])
@require_tenant_context
def inventory_dashboard():
    """Get inventory dashboard summary"""
    try:
        tenant_id = request.headers.get('X-Tenant-ID')
        session = get_db_session()
        
        # Get inventory summary
        summary = session.execute(text("""
            SELECT 
                COUNT(*) as total_items,
                SUM(quantity_on_hand) as total_quantity,
                SUM(quantity_on_hand * unit_price) as total_value,
                COUNT(CASE WHEN quantity_on_hand <= reorder_point THEN 1 END) as low_stock_items
            FROM inventory_items
            WHERE tenant_id = :tenant_id AND is_active = true
        """), {'tenant_id': tenant_id}).fetchone()
        
        # Get top categories
        categories = session.execute(text("""
            SELECT category, COUNT(*) as item_count
            FROM inventory_items
            WHERE tenant_id = :tenant_id AND is_active = true
            GROUP BY category
            ORDER BY item_count DESC
            LIMIT 5
        """), {'tenant_id': tenant_id})
        
        category_data = []
        for row in categories:
            category_data.append({
                'category': row.category,
                'item_count': row.item_count
            })
        
        session.close()
        
        return jsonify({
            'data': {
                'summary': {
                    'total_items': summary.total_items,
                    'total_quantity': summary.total_quantity or 0,
                    'total_value': float(summary.total_value or 0),
                    'low_stock_items': summary.low_stock_items
                },
                'top_categories': category_data
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get inventory dashboard: {e}")
        return jsonify({
            'errors': [{
                'status': 500,
                'code': 'DASHBOARD_FAILED',
                'detail': str(e)
            }]
        }), 500
