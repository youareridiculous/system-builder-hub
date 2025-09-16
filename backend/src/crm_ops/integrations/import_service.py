"""
Import service for Salesforce and HubSpot integrations
"""
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.integrations.models import SalesforceIntegration, HubSpotIntegration, IntegrationSync
from src.crm_ops.models import Contact, Deal, Task
from src.crm_ops.collaboration.activity_service import ActivityService

logger = logging.getLogger(__name__)

class ImportService:
    """Service for importing data from external systems"""
    
    def __init__(self):
        self.activity_service = ActivityService()
    
    def import_from_salesforce(self, tenant_id: str, integration_id: str, entity_types: List[str] = None) -> IntegrationSync:
        """Import data from Salesforce"""
        if entity_types is None:
            entity_types = ['contacts', 'leads', 'opportunities']
        
        with db_session() as session:
            # Create sync record
            sync = IntegrationSync(
                tenant_id=tenant_id,
                integration_type='salesforce',
                sync_type='import',
                status='running',
                metadata={'entity_types': entity_types}
            )
            session.add(sync)
            session.commit()
            
            try:
                # Get integration config
                integration = session.query(SalesforceIntegration).filter(
                    SalesforceIntegration.id == integration_id,
                    SalesforceIntegration.tenant_id == tenant_id
                ).first()
                
                if not integration:
                    raise ValueError("Salesforce integration not found")
                
                # Import each entity type
                total_processed = 0
                total_created = 0
                total_updated = 0
                total_skipped = 0
                total_failed = 0
                
                for entity_type in entity_types:
                    if entity_type == 'contacts':
                        processed, created, updated, skipped, failed = self._import_salesforce_contacts(
                            session, integration, tenant_id
                        )
                    elif entity_type == 'leads':
                        processed, created, updated, skipped, failed = self._import_salesforce_leads(
                            session, integration, tenant_id
                        )
                    elif entity_type == 'opportunities':
                        processed, created, updated, skipped, failed = self._import_salesforce_opportunities(
                            session, integration, tenant_id
                        )
                    else:
                        logger.warning(f"Unknown Salesforce entity type: {entity_type}")
                        continue
                    
                    total_processed += processed
                    total_created += created
                    total_updated += updated
                    total_skipped += skipped
                    total_failed += failed
                
                # Update sync record
                sync.status = 'completed'
                sync.records_processed = total_processed
                sync.records_created = total_created
                sync.records_updated = total_updated
                sync.records_skipped = total_skipped
                sync.records_failed = total_failed
                sync.completed_at = datetime.utcnow()
                
                session.commit()
                
                return sync
                
            except Exception as e:
                logger.error(f"Error importing from Salesforce: {e}")
                
                # Update sync record with error
                sync.status = 'failed'
                sync.error_message = str(e)
                sync.completed_at = datetime.utcnow()
                session.commit()
                
                raise
    
    def import_from_hubspot(self, tenant_id: str, integration_id: str, entity_types: List[str] = None) -> IntegrationSync:
        """Import data from HubSpot"""
        if entity_types is None:
            entity_types = ['contacts', 'companies', 'deals']
        
        with db_session() as session:
            # Create sync record
            sync = IntegrationSync(
                tenant_id=tenant_id,
                integration_type='hubspot',
                sync_type='import',
                status='running',
                metadata={'entity_types': entity_types}
            )
            session.add(sync)
            session.commit()
            
            try:
                # Get integration config
                integration = session.query(HubSpotIntegration).filter(
                    HubSpotIntegration.id == integration_id,
                    HubSpotIntegration.tenant_id == tenant_id
                ).first()
                
                if not integration:
                    raise ValueError("HubSpot integration not found")
                
                # Import each entity type
                total_processed = 0
                total_created = 0
                total_updated = 0
                total_skipped = 0
                total_failed = 0
                
                for entity_type in entity_types:
                    if entity_type == 'contacts':
                        processed, created, updated, skipped, failed = self._import_hubspot_contacts(
                            session, integration, tenant_id
                        )
                    elif entity_type == 'companies':
                        processed, created, updated, skipped, failed = self._import_hubspot_companies(
                            session, integration, tenant_id
                        )
                    elif entity_type == 'deals':
                        processed, created, updated, skipped, failed = self._import_hubspot_deals(
                            session, integration, tenant_id
                        )
                    else:
                        logger.warning(f"Unknown HubSpot entity type: {entity_type}")
                        continue
                    
                    total_processed += processed
                    total_created += created
                    total_updated += updated
                    total_skipped += skipped
                    total_failed += failed
                
                # Update sync record
                sync.status = 'completed'
                sync.records_processed = total_processed
                sync.records_created = total_created
                sync.records_updated = total_updated
                sync.records_skipped = total_skipped
                sync.records_failed = total_failed
                sync.completed_at = datetime.utcnow()
                
                session.commit()
                
                return sync
                
            except Exception as e:
                logger.error(f"Error importing from HubSpot: {e}")
                
                # Update sync record with error
                sync.status = 'failed'
                sync.error_message = str(e)
                sync.completed_at = datetime.utcnow()
                session.commit()
                
                raise
    
    def _import_salesforce_contacts(self, session: Session, integration: SalesforceIntegration, tenant_id: str) -> Tuple[int, int, int, int, int]:
        """Import contacts from Salesforce"""
        processed = 0
        created = 0
        updated = 0
        skipped = 0
        failed = 0
        
        try:
            # Get Salesforce contacts
            contacts_data = self._fetch_salesforce_contacts(integration)
            
            for contact_data in contacts_data:
                processed += 1
                
                try:
                    # Map Salesforce fields to CRM fields
                    mapped_data = self._map_salesforce_contact_fields(contact_data, integration.field_mappings)
                    
                    # Check for existing contact
                    existing_contact = session.query(Contact).filter(
                        Contact.tenant_id == tenant_id,
                        Contact.email == mapped_data.get('email')
                    ).first()
                    
                    if existing_contact:
                        # Update existing contact
                        self._update_contact_from_salesforce(existing_contact, mapped_data)
                        updated += 1
                    else:
                        # Create new contact
                        contact = Contact(
                            tenant_id=tenant_id,
                            first_name=mapped_data.get('first_name', ''),
                            last_name=mapped_data.get('last_name', ''),
                            email=mapped_data.get('email', ''),
                            company=mapped_data.get('company', ''),
                            phone=mapped_data.get('phone', ''),
                            custom_fields={
                                'salesforce_id': contact_data.get('Id'),
                                'salesforce_lead_source': contact_data.get('LeadSource'),
                                'salesforce_title': contact_data.get('Title')
                            },
                            created_by='salesforce_import'
                        )
                        session.add(contact)
                        created += 1
                    
                except Exception as e:
                    logger.error(f"Error processing Salesforce contact: {e}")
                    failed += 1
                    continue
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error importing Salesforce contacts: {e}")
            failed += 1
        
        return processed, created, updated, skipped, failed
    
    def _import_salesforce_leads(self, session: Session, integration: SalesforceIntegration, tenant_id: str) -> Tuple[int, int, int, int, int]:
        """Import leads from Salesforce"""
        processed = 0
        created = 0
        updated = 0
        skipped = 0
        failed = 0
        
        try:
            # Get Salesforce leads
            leads_data = self._fetch_salesforce_leads(integration)
            
            for lead_data in leads_data:
                processed += 1
                
                try:
                    # Map Salesforce fields to CRM fields
                    mapped_data = self._map_salesforce_lead_fields(lead_data, integration.field_mappings)
                    
                    # Check for existing contact
                    existing_contact = session.query(Contact).filter(
                        Contact.tenant_id == tenant_id,
                        Contact.email == mapped_data.get('email')
                    ).first()
                    
                    if existing_contact:
                        # Update existing contact
                        self._update_contact_from_salesforce(existing_contact, mapped_data)
                        updated += 1
                    else:
                        # Create new contact
                        contact = Contact(
                            tenant_id=tenant_id,
                            first_name=mapped_data.get('first_name', ''),
                            last_name=mapped_data.get('last_name', ''),
                            email=mapped_data.get('email', ''),
                            company=mapped_data.get('company', ''),
                            phone=mapped_data.get('phone', ''),
                            tags=['salesforce_lead'],
                            custom_fields={
                                'salesforce_lead_id': lead_data.get('Id'),
                                'salesforce_lead_source': lead_data.get('LeadSource'),
                                'salesforce_company': lead_data.get('Company'),
                                'salesforce_status': lead_data.get('Status')
                            },
                            created_by='salesforce_import'
                        )
                        session.add(contact)
                        created += 1
                    
                except Exception as e:
                    logger.error(f"Error processing Salesforce lead: {e}")
                    failed += 1
                    continue
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error importing Salesforce leads: {e}")
            failed += 1
        
        return processed, created, updated, skipped, failed
    
    def _import_salesforce_opportunities(self, session: Session, integration: SalesforceIntegration, tenant_id: str) -> Tuple[int, int, int, int, int]:
        """Import opportunities from Salesforce"""
        processed = 0
        created = 0
        updated = 0
        skipped = 0
        failed = 0
        
        try:
            # Get Salesforce opportunities
            opportunities_data = self._fetch_salesforce_opportunities(integration)
            
            for opp_data in opportunities_data:
                processed += 1
                
                try:
                    # Map Salesforce fields to CRM fields
                    mapped_data = self._map_salesforce_opportunity_fields(opp_data, integration.field_mappings)
                    
                    # Check for existing deal
                    existing_deal = session.query(Deal).filter(
                        Deal.tenant_id == tenant_id,
                        Deal.custom_fields.contains({'salesforce_id': opp_data.get('Id')})
                    ).first()
                    
                    if existing_deal:
                        # Update existing deal
                        self._update_deal_from_salesforce(existing_deal, mapped_data)
                        updated += 1
                    else:
                        # Create new deal
                        deal = Deal(
                            tenant_id=tenant_id,
                            title=mapped_data.get('title', ''),
                            value=mapped_data.get('value', 0),
                            pipeline_stage=mapped_data.get('pipeline_stage', 'qualification'),
                            status=mapped_data.get('status', 'open'),
                            notes=mapped_data.get('description', ''),
                            custom_fields={
                                'salesforce_id': opp_data.get('Id'),
                                'salesforce_stage': opp_data.get('StageName'),
                                'salesforce_type': opp_data.get('Type'),
                                'salesforce_probability': opp_data.get('Probability')
                            },
                            created_by='salesforce_import'
                        )
                        session.add(deal)
                        created += 1
                    
                except Exception as e:
                    logger.error(f"Error processing Salesforce opportunity: {e}")
                    failed += 1
                    continue
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error importing Salesforce opportunities: {e}")
            failed += 1
        
        return processed, created, updated, skipped, failed
    
    def _import_hubspot_contacts(self, session: Session, integration: HubSpotIntegration, tenant_id: str) -> Tuple[int, int, int, int, int]:
        """Import contacts from HubSpot"""
        processed = 0
        created = 0
        updated = 0
        skipped = 0
        failed = 0
        
        try:
            # Get HubSpot contacts
            contacts_data = self._fetch_hubspot_contacts(integration)
            
            for contact_data in contacts_data:
                processed += 1
                
                try:
                    # Map HubSpot fields to CRM fields
                    mapped_data = self._map_hubspot_contact_fields(contact_data, integration.field_mappings)
                    
                    # Check for existing contact
                    existing_contact = session.query(Contact).filter(
                        Contact.tenant_id == tenant_id,
                        Contact.email == mapped_data.get('email')
                    ).first()
                    
                    if existing_contact:
                        # Update existing contact
                        self._update_contact_from_hubspot(existing_contact, mapped_data)
                        updated += 1
                    else:
                        # Create new contact
                        contact = Contact(
                            tenant_id=tenant_id,
                            first_name=mapped_data.get('first_name', ''),
                            last_name=mapped_data.get('last_name', ''),
                            email=mapped_data.get('email', ''),
                            company=mapped_data.get('company', ''),
                            phone=mapped_data.get('phone', ''),
                            custom_fields={
                                'hubspot_id': contact_data.get('id'),
                                'hubspot_lifecycle_stage': contact_data.get('properties', {}).get('lifecyclestage'),
                                'hubspot_lead_status': contact_data.get('properties', {}).get('hs_lead_status')
                            },
                            created_by='hubspot_import'
                        )
                        session.add(contact)
                        created += 1
                    
                except Exception as e:
                    logger.error(f"Error processing HubSpot contact: {e}")
                    failed += 1
                    continue
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error importing HubSpot contacts: {e}")
            failed += 1
        
        return processed, created, updated, skipped, failed
    
    def _import_hubspot_companies(self, session: Session, integration: HubSpotIntegration, tenant_id: str) -> Tuple[int, int, int, int, int]:
        """Import companies from HubSpot"""
        processed = 0
        created = 0
        updated = 0
        skipped = 0
        failed = 0
        
        try:
            # Get HubSpot companies
            companies_data = self._fetch_hubspot_companies(integration)
            
            for company_data in companies_data:
                processed += 1
                
                try:
                    # Map HubSpot fields to CRM fields
                    mapped_data = self._map_hubspot_company_fields(company_data, integration.field_mappings)
                    
                    # Create contact for company (or update existing)
                    existing_contact = session.query(Contact).filter(
                        Contact.tenant_id == tenant_id,
                        Contact.company == mapped_data.get('company')
                    ).first()
                    
                    if existing_contact:
                        # Update existing contact with company info
                        existing_contact.company = mapped_data.get('company')
                        existing_contact.custom_fields.update({
                            'hubspot_company_id': company_data.get('id'),
                            'hubspot_company_domain': company_data.get('properties', {}).get('domain'),
                            'hubspot_company_industry': company_data.get('properties', {}).get('industry')
                        })
                        updated += 1
                    else:
                        # Create new contact for company
                        contact = Contact(
                            tenant_id=tenant_id,
                            first_name='',
                            last_name='',
                            email='',
                            company=mapped_data.get('company', ''),
                            custom_fields={
                                'hubspot_company_id': company_data.get('id'),
                                'hubspot_company_domain': company_data.get('properties', {}).get('domain'),
                                'hubspot_company_industry': company_data.get('properties', {}).get('industry')
                            },
                            created_by='hubspot_import'
                        )
                        session.add(contact)
                        created += 1
                    
                except Exception as e:
                    logger.error(f"Error processing HubSpot company: {e}")
                    failed += 1
                    continue
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error importing HubSpot companies: {e}")
            failed += 1
        
        return processed, created, updated, skipped, failed
    
    def _import_hubspot_deals(self, session: Session, integration: HubSpotIntegration, tenant_id: str) -> Tuple[int, int, int, int, int]:
        """Import deals from HubSpot"""
        processed = 0
        created = 0
        updated = 0
        skipped = 0
        failed = 0
        
        try:
            # Get HubSpot deals
            deals_data = self._fetch_hubspot_deals(integration)
            
            for deal_data in deals_data:
                processed += 1
                
                try:
                    # Map HubSpot fields to CRM fields
                    mapped_data = self._map_hubspot_deal_fields(deal_data, integration.field_mappings)
                    
                    # Check for existing deal
                    existing_deal = session.query(Deal).filter(
                        Deal.tenant_id == tenant_id,
                        Deal.custom_fields.contains({'hubspot_id': deal_data.get('id')})
                    ).first()
                    
                    if existing_deal:
                        # Update existing deal
                        self._update_deal_from_hubspot(existing_deal, mapped_data)
                        updated += 1
                    else:
                        # Create new deal
                        deal = Deal(
                            tenant_id=tenant_id,
                            title=mapped_data.get('title', ''),
                            value=mapped_data.get('value', 0),
                            pipeline_stage=mapped_data.get('pipeline_stage', 'qualification'),
                            status=mapped_data.get('status', 'open'),
                            notes=mapped_data.get('description', ''),
                            custom_fields={
                                'hubspot_id': deal_data.get('id'),
                                'hubspot_deal_stage': deal_data.get('properties', {}).get('dealstage'),
                                'hubspot_deal_type': deal_data.get('properties', {}).get('dealtype')
                            },
                            created_by='hubspot_import'
                        )
                        session.add(deal)
                        created += 1
                    
                except Exception as e:
                    logger.error(f"Error processing HubSpot deal: {e}")
                    failed += 1
                    continue
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error importing HubSpot deals: {e}")
            failed += 1
        
        return processed, created, updated, skipped, failed
    
    def _fetch_salesforce_contacts(self, integration: SalesforceIntegration) -> List[Dict[str, Any]]:
        """Fetch contacts from Salesforce"""
        # This would use Salesforce REST API
        # For now, return mock data
        return [
            {
                'Id': '0031234567890ABC',
                'FirstName': 'John',
                'LastName': 'Doe',
                'Email': 'john@example.com',
                'Phone': '+1234567890',
                'Title': 'Sales Manager',
                'LeadSource': 'Website',
                'Account': {'Name': 'Acme Corp'}
            }
        ]
    
    def _fetch_salesforce_leads(self, integration: SalesforceIntegration) -> List[Dict[str, Any]]:
        """Fetch leads from Salesforce"""
        # This would use Salesforce REST API
        return [
            {
                'Id': '00Q1234567890ABC',
                'FirstName': 'Jane',
                'LastName': 'Smith',
                'Email': 'jane@example.com',
                'Company': 'Tech Inc',
                'LeadSource': 'Trade Show',
                'Status': 'New'
            }
        ]
    
    def _fetch_salesforce_opportunities(self, integration: SalesforceIntegration) -> List[Dict[str, Any]]:
        """Fetch opportunities from Salesforce"""
        # This would use Salesforce REST API
        return [
            {
                'Id': '0061234567890ABC',
                'Name': 'Enterprise Deal',
                'Amount': 50000,
                'StageName': 'Proposal',
                'Type': 'New Business',
                'Probability': 75,
                'Description': 'Large enterprise deal'
            }
        ]
    
    def _fetch_hubspot_contacts(self, integration: HubSpotIntegration) -> List[Dict[str, Any]]:
        """Fetch contacts from HubSpot"""
        # This would use HubSpot API
        return [
            {
                'id': '123',
                'properties': {
                    'firstname': 'John',
                    'lastname': 'Doe',
                    'email': 'john@example.com',
                    'phone': '+1234567890',
                    'company': 'Acme Corp',
                    'lifecyclestage': 'lead',
                    'hs_lead_status': 'NEW'
                }
            }
        ]
    
    def _fetch_hubspot_companies(self, integration: HubSpotIntegration) -> List[Dict[str, Any]]:
        """Fetch companies from HubSpot"""
        # This would use HubSpot API
        return [
            {
                'id': '456',
                'properties': {
                    'name': 'Acme Corp',
                    'domain': 'acme.com',
                    'industry': 'Technology'
                }
            }
        ]
    
    def _fetch_hubspot_deals(self, integration: HubSpotIntegration) -> List[Dict[str, Any]]:
        """Fetch deals from HubSpot"""
        # This would use HubSpot API
        return [
            {
                'id': '789',
                'properties': {
                    'dealname': 'Enterprise Deal',
                    'amount': '50000',
                    'dealstage': 'proposal',
                    'dealtype': 'newbusiness',
                    'description': 'Large enterprise deal'
                }
            }
        ]
    
    def _map_salesforce_contact_fields(self, contact_data: Dict[str, Any], field_mappings: Dict[str, str]) -> Dict[str, Any]:
        """Map Salesforce contact fields to CRM fields"""
        return {
            'first_name': contact_data.get('FirstName', ''),
            'last_name': contact_data.get('LastName', ''),
            'email': contact_data.get('Email', ''),
            'phone': contact_data.get('Phone', ''),
            'company': contact_data.get('Account', {}).get('Name', '')
        }
    
    def _map_salesforce_lead_fields(self, lead_data: Dict[str, Any], field_mappings: Dict[str, str]) -> Dict[str, Any]:
        """Map Salesforce lead fields to CRM fields"""
        return {
            'first_name': lead_data.get('FirstName', ''),
            'last_name': lead_data.get('LastName', ''),
            'email': lead_data.get('Email', ''),
            'company': lead_data.get('Company', '')
        }
    
    def _map_salesforce_opportunity_fields(self, opp_data: Dict[str, Any], field_mappings: Dict[str, str]) -> Dict[str, Any]:
        """Map Salesforce opportunity fields to CRM fields"""
        return {
            'title': opp_data.get('Name', ''),
            'value': opp_data.get('Amount', 0),
            'pipeline_stage': self._map_salesforce_stage(opp_data.get('StageName', '')),
            'status': 'open',
            'description': opp_data.get('Description', '')
        }
    
    def _map_hubspot_contact_fields(self, contact_data: Dict[str, Any], field_mappings: Dict[str, str]) -> Dict[str, Any]:
        """Map HubSpot contact fields to CRM fields"""
        properties = contact_data.get('properties', {})
        return {
            'first_name': properties.get('firstname', ''),
            'last_name': properties.get('lastname', ''),
            'email': properties.get('email', ''),
            'phone': properties.get('phone', ''),
            'company': properties.get('company', '')
        }
    
    def _map_hubspot_company_fields(self, company_data: Dict[str, Any], field_mappings: Dict[str, str]) -> Dict[str, Any]:
        """Map HubSpot company fields to CRM fields"""
        properties = company_data.get('properties', {})
        return {
            'company': properties.get('name', '')
        }
    
    def _map_hubspot_deal_fields(self, deal_data: Dict[str, Any], field_mappings: Dict[str, str]) -> Dict[str, Any]:
        """Map HubSpot deal fields to CRM fields"""
        properties = deal_data.get('properties', {})
        return {
            'title': properties.get('dealname', ''),
            'value': float(properties.get('amount', 0)),
            'pipeline_stage': self._map_hubspot_stage(properties.get('dealstage', '')),
            'status': 'open',
            'description': properties.get('description', '')
        }
    
    def _map_salesforce_stage(self, stage: str) -> str:
        """Map Salesforce stage to CRM pipeline stage"""
        stage_mapping = {
            'Qualification': 'qualification',
            'Proposal': 'proposal',
            'Negotiation': 'negotiation',
            'Closed Won': 'closed_won',
            'Closed Lost': 'closed_lost'
        }
        return stage_mapping.get(stage, 'qualification')
    
    def _map_hubspot_stage(self, stage: str) -> str:
        """Map HubSpot stage to CRM pipeline stage"""
        stage_mapping = {
            'qualification': 'qualification',
            'proposal': 'proposal',
            'negotiation': 'negotiation',
            'closedwon': 'closed_won',
            'closedlost': 'closed_lost'
        }
        return stage_mapping.get(stage, 'qualification')
    
    def _update_contact_from_salesforce(self, contact: Contact, mapped_data: Dict[str, Any]):
        """Update contact with Salesforce data"""
        contact.first_name = mapped_data.get('first_name', contact.first_name)
        contact.last_name = mapped_data.get('last_name', contact.last_name)
        contact.email = mapped_data.get('email', contact.email)
        contact.phone = mapped_data.get('phone', contact.phone)
        contact.company = mapped_data.get('company', contact.company)
    
    def _update_contact_from_hubspot(self, contact: Contact, mapped_data: Dict[str, Any]):
        """Update contact with HubSpot data"""
        contact.first_name = mapped_data.get('first_name', contact.first_name)
        contact.last_name = mapped_data.get('last_name', contact.last_name)
        contact.email = mapped_data.get('email', contact.email)
        contact.phone = mapped_data.get('phone', contact.phone)
        contact.company = mapped_data.get('company', contact.company)
    
    def _update_deal_from_salesforce(self, deal: Deal, mapped_data: Dict[str, Any]):
        """Update deal with Salesforce data"""
        deal.title = mapped_data.get('title', deal.title)
        deal.value = mapped_data.get('value', deal.value)
        deal.pipeline_stage = mapped_data.get('pipeline_stage', deal.pipeline_stage)
        deal.notes = mapped_data.get('description', deal.notes)
    
    def _update_deal_from_hubspot(self, deal: Deal, mapped_data: Dict[str, Any]):
        """Update deal with HubSpot data"""
        deal.title = mapped_data.get('title', deal.title)
        deal.value = mapped_data.get('value', deal.value)
        deal.pipeline_stage = mapped_data.get('pipeline_stage', deal.pipeline_stage)
        deal.notes = mapped_data.get('description', deal.notes)
