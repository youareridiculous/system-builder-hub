"""
CRM Lite Contacts API
"""
from flask import jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.db_core import get_database_url

# Mock contacts data
MOCK_CONTACTS = [
    {
        "id": 1,
        "name": "John Smith",
        "email": "john.smith@example.com",
        "tenant_id": "demo",
        "phone": "+1-555-0123",
        "company": "Acme Corp"
    },
    {
        "id": 2,
        "name": "Sarah Johnson",
        "email": "sarah.johnson@example.com",
        "tenant_id": "demo",
        "phone": "+1-555-0456",
        "company": "TechStart Inc"
    },
    {
        "id": 3,
        "name": "Mike Chen",
        "email": "mike.chen@example.com",
        "tenant_id": "demo",
        "phone": "+1-555-0789",
        "company": "Global Solutions"
    }
]

def init_contacts_routes(crm_lite_bp):
    """Initialize contacts routes on the CRM Lite blueprint"""
    
    @crm_lite_bp.route("/contacts", methods=["GET"])
    def get_contacts():
        """Get all contacts (mock data for now)"""
        return jsonify({
            "success": True,
            "data": MOCK_CONTACTS,
            "count": len(MOCK_CONTACTS),
            "message": "Contacts retrieved successfully"
        })
    
    @crm_lite_bp.route("/contacts/<int:contact_id>", methods=["GET"])
    def get_contact(contact_id):
        """Get a specific contact by ID"""
        contact = next((c for c in MOCK_CONTACTS if c["id"] == contact_id), None)
        
        if not contact:
            return jsonify({
                "success": False,
                "error": "Contact not found",
                "contact_id": contact_id
            }), 404
        
        return jsonify({
            "success": True,
            "data": contact,
            "message": "Contact retrieved successfully"
        })
    
    @crm_lite_bp.route("/contacts_db", methods=["GET"])
    def get_contacts_db():
        """Get all contacts from database for a tenant"""
        try:
            # Get tenant ID from header, default to demo
            tenant_id = request.headers.get('X-Tenant-ID', 'demo')
            
            # Check if table exists
            engine = create_engine(get_database_url())
            with engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='crm_lite_contacts'"))
                if not result.fetchone():
                    return jsonify({
                        "success": False,
                        "error": "contacts table not available"
                    }), 501
                
                # Get contacts for tenant
                result = conn.execute(
                    text("SELECT id, tenant_id, name, email, phone, company, created_at, updated_at FROM crm_lite_contacts WHERE tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                
                contacts = []
                for row in result:
                    contacts.append({
                        "id": row[0],
                        "tenant_id": row[1],
                        "name": row[2],
                        "email": row[3],
                        "phone": row[4],
                        "company": row[5],
                        "created_at": str(row[6]) if row[6] else None,
                        "updated_at": str(row[7]) if row[7] else None
                    })
                
                # Add smoke check information
                response_data = {
                    "success": True,
                    "data": contacts,
                    "count": len(contacts),
                    "tenant_id": tenant_id,
                    "message": "Contacts retrieved from database successfully"
                }
                
                if len(contacts) == 0:
                    response_data["smoke_check"] = {
                        "status": "empty",
                        "suggestion": f"No contacts found for tenant '{tenant_id}'. Run: python -m src.cli crm-lite seed-contacts-cmd --tenant {tenant_id}"
                    }
                
                return jsonify(response_data)
                
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Database error: {str(e)}"
            }), 500
