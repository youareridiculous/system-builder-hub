import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid
import hashlib
from src.db_core import get_database_url
from src.crm_lite.models import CrmLiteContact

logger = logging.getLogger(__name__)

def get_db_session():
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()

def seed_contacts(tenant_id: str = 'demo'):
    """Seed demo contacts for crm_lite module"""
    logger.info(f"Seeding crm_lite contacts for tenant: {tenant_id}")
    
    session = get_db_session()
    
    try:
        # Check if table exists
        result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='crm_lite_contacts'"))
        
        if not result.fetchone():
            logger.warning("Table crm_lite_contacts does not exist yet")
            return
        
        # Sample contacts data with deterministic UUIDs based on email
        contacts_data = [
            {
                "name": "John Smith",
                "email": "john.smith@example.com",
                "phone": "+1-555-0123",
                "company": "Acme Corp"
            },
            {
                "name": "Sarah Johnson",
                "email": "sarah.johnson@example.com",
                "phone": "+1-555-0456",
                "company": "TechStart Inc"
            },
            {
                "name": "Mike Chen",
                "email": "mike.chen@example.com",
                "phone": "+1-555-0789",
                "company": "Global Solutions"
            }
        ]
        
        # Generate deterministic UUIDs based on email + tenant_id
        for contact_data in contacts_data:
            # Create deterministic UUID from email + tenant_id
            unique_string = f"{contact_data['email']}:{tenant_id}"
            contact_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))
            
            # Check if contact already exists
            existing = session.query(CrmLiteContact).filter_by(id=contact_id).first()
            if existing:
                logger.info(f"Contact {contact_data['email']} already exists, skipping")
                continue
            
            # Create new contact
            contact = CrmLiteContact(
                id=contact_id,
                tenant_id=tenant_id,
                name=contact_data['name'],
                email=contact_data['email'],
                phone=contact_data['phone'],
                company=contact_data['company']
            )
            
            session.add(contact)
            logger.info(f"Added contact: {contact_data['name']} ({contact_data['email']})")
        
        session.commit()
        logger.info(f"✅ crm_lite contacts seeding completed for tenant: {tenant_id}")
        
    except Exception as e:
        logger.error(f"Failed to seed crm_lite contacts: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def seed_crm_lite_data(tenant_id: str = 'demo'):
    """Seed demo data for crm_lite module"""
    logger.info(f"Seeding crm_lite data for tenant: {tenant_id}")
    
    # Seed contacts
    seed_contacts(tenant_id)
    
    logger.info(f"✅ crm_lite seeding completed for tenant: {tenant_id}")
