"""
Import/Export service for CRM/Ops Template
"""
import logging
import csv
import io
import json
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from src.database import db_session
from src.crm_ops.models import Contact, Deal

logger = logging.getLogger(__name__)

class ImportExportService:
    """Service for CSV import/export operations"""
    
    @staticmethod
    def import_contacts_csv(tenant_id: str, user_id: str, reader) -> Dict[str, Any]:
        """Import contacts from CSV reader"""
        inserted = 0
        updated = 0
        skipped = 0
        errors = []
        
        with db_session() as session:
            for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                try:
                    # Validate required fields
                    if not row.get('first_name') or not row.get('last_name'):
                        errors.append({
                            'row': row_num,
                            'field': 'first_name/last_name',
                            'message': 'First name and last name are required'
                        })
                        skipped += 1
                        continue
                    
                    # Validate email format
                    email = row.get('email', '').strip()
                    if email and '@' not in email:
                        errors.append({
                            'row': row_num,
                            'field': 'email',
                            'message': 'Invalid email format'
                        })
                        skipped += 1
                        continue
                    
                    # Check for existing contact by email
                    existing_contact = None
                    if email:
                        existing_contact = session.query(Contact).filter(
                            Contact.tenant_id == tenant_id,
                            Contact.email == email
                        ).first()
                    
                    # Prepare custom fields
                    custom_fields = {}
                    standard_fields = ['first_name', 'last_name', 'email', 'phone', 'company', 'tags']
                    
                    for key, value in row.items():
                        if key not in standard_fields and value.strip():
                            custom_fields[key] = value.strip()
                    
                    # Parse tags
                    tags = []
                    if row.get('tags'):
                        tags = [tag.strip() for tag in row['tags'].split(',') if tag.strip()]
                    
                    if existing_contact:
                        # Update existing contact
                        existing_contact.first_name = row['first_name'].strip()
                        existing_contact.last_name = row['last_name'].strip()
                        existing_contact.phone = row.get('phone', '').strip() or existing_contact.phone
                        existing_contact.company = row.get('company', '').strip() or existing_contact.company
                        existing_contact.tags = tags
                        existing_contact.custom_fields = {**existing_contact.custom_fields, **custom_fields}
                        updated += 1
                    else:
                        # Create new contact
                        contact = Contact(
                            tenant_id=tenant_id,
                            first_name=row['first_name'].strip(),
                            last_name=row['last_name'].strip(),
                            email=email,
                            phone=row.get('phone', '').strip(),
                            company=row.get('company', '').strip(),
                            tags=tags,
                            custom_fields=custom_fields,
                            created_by=user_id
                        )
                        session.add(contact)
                        inserted += 1
                
                except Exception as e:
                    errors.append({
                        'row': row_num,
                        'field': 'general',
                        'message': f'Error processing row: {str(e)}'
                    })
                    skipped += 1
            
            session.commit()
        
        return {
            'inserted': inserted,
            'updated': updated,
            'skipped': skipped,
            'errors': errors
        }
    
    @staticmethod
    def export_contacts_csv(tenant_id: str, filters: Dict[str, Any] = None) -> str:
        """Export contacts to CSV string"""
        if filters is None:
            filters = {}
        
        with db_session() as session:
            query = session.query(Contact).filter(Contact.tenant_id == tenant_id)
            
            # Apply filters
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Contact.first_name.ilike(search_term),
                        Contact.last_name.ilike(search_term),
                        Contact.email.ilike(search_term),
                        Contact.company.ilike(search_term)
                    )
                )
            
            if filters.get('status'):
                if filters['status'] == 'active':
                    query = query.filter(Contact.is_active == True)
                elif filters['status'] == 'inactive':
                    query = query.filter(Contact.is_active == False)
            
            if filters.get('tags'):
                for tag in filters['tags']:
                    query = query.filter(Contact.tags.contains([tag]))
            
            # Limit to 50k rows
            contacts = query.limit(50000).all()
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            headers = ['first_name', 'last_name', 'email', 'phone', 'company', 'tags']
            writer.writerow(headers)
            
            # Write data
            for contact in contacts:
                row = [
                    contact.first_name or '',
                    contact.last_name or '',
                    contact.email or '',
                    contact.phone or '',
                    contact.company or '',
                    ','.join(contact.tags) if contact.tags else ''
                ]
                writer.writerow(row)
            
            return output.getvalue()
    
    @staticmethod
    def export_deals_csv(tenant_id: str, filters: Dict[str, Any] = None) -> str:
        """Export deals to CSV string"""
        if filters is None:
            filters = {}
        
        with db_session() as session:
            query = session.query(Deal).filter(Deal.tenant_id == tenant_id)
            
            # Apply filters
            if filters.get('status'):
                query = query.filter(Deal.status == filters['status'])
            
            if filters.get('pipeline_stage'):
                query = query.filter(Deal.pipeline_stage == filters['pipeline_stage'])
            
            # Limit to 50k rows
            deals = query.limit(50000).all()
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            headers = ['title', 'contact_id', 'pipeline_stage', 'value', 'status', 'notes', 'expected_close_date']
            writer.writerow(headers)
            
            # Write data
            for deal in deals:
                row = [
                    deal.title or '',
                    deal.contact_id or '',
                    deal.pipeline_stage or '',
                    deal.value or '',
                    deal.status or '',
                    deal.notes or '',
                    deal.expected_close_date.isoformat() if deal.expected_close_date else ''
                ]
                writer.writerow(row)
            
            return output.getvalue()
