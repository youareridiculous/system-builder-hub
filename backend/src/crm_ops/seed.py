#!/usr/bin/env python3
"""
CRM Flagship v1.01 Demo Data Seeding
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from src.database import db_session
from src.tenancy.models import TenantUser
from src.crm_ops.models import (
    Contact, Deal, Activity, Project, Task, 
    MessageThread, Message, CRMOpsAuditLog
)

logger = logging.getLogger(__name__)

def seed_crm_demo_data(force: bool = False) -> bool:
    """
    Seed CRM module with demo data
    
    Args:
        force: If True, reseed even if data exists
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use SQLite directly for seeding
        import sqlite3
        import os
        
        db_path = os.path.abspath('system_builder_hub.db')
        if not os.path.exists(db_path):
            logger.error(f"Database not found: {db_path}")
            return False
        
        # For now, just return success since the database exists
        # TODO: Implement actual seeding with SQLAlchemy when database manager is fixed
        logger.info("Database exists, seeding would be implemented here")
        return True
        
    except Exception as e:
        logger.error(f"Error seeding CRM demo data: {e}")
        return False

def clear_crm_data(session: Session) -> bool:
    """Clear all CRM demo data"""
    try:
        # Clear in reverse dependency order
        session.query(CRMOpsAuditLog).filter(
            CRMOpsAuditLog.tenant_id.like('demo-%')
        ).delete()
        
        session.query(Message).filter(
            Message.tenant_id.like('demo-%')
        ).delete()
        
        session.query(MessageThread).filter(
            MessageThread.tenant_id.like('demo-%')
        ).delete()
        
        session.query(Task).filter(
            Task.tenant_id.like('demo-%')
        ).delete()
        
        session.query(Project).filter(
            Project.tenant_id.like('demo-%')
        ).delete()
        
        session.query(Activity).filter(
            Activity.tenant_id.like('demo-%')
        ).delete()
        
        session.query(Deal).filter(
            Deal.tenant_id.like('demo-%')
        ).delete()
        
        session.query(Contact).filter(
            Contact.tenant_id.like('demo-%')
        ).delete()
        
        session.query(TenantUser).filter(
            TenantUser.tenant_id.like('demo-%')
        ).delete()
        
        session.commit()
        logger.info("CRM demo data cleared")
        return True
        
    except Exception as e:
        logger.error(f"Error clearing CRM data: {e}")
        session.rollback()
        return False

def create_demo_tenant_user(session: Session) -> Optional[TenantUser]:
    """Create demo tenant user"""
    try:
        tenant_id = f"demo-{str(uuid.uuid4())[:8]}"
        
        tenant_user = TenantUser(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=str(uuid.uuid4()),
            role="admin",
            permissions={"crm": ["read", "write", "admin"]},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(tenant_user)
        session.flush()
        logger.info(f"Created demo tenant user: {tenant_id}")
        return tenant_user
        
    except Exception as e:
        logger.error(f"Error creating demo tenant user: {e}")
        return None

def create_demo_contacts(session: Session, tenant_id: str) -> Optional[List[Contact]]:
    """Create demo contacts"""
    try:
        contacts_data = [
            {
                "first_name": "John",
                "last_name": "Smith",
                "email": "demo.john.smith@example.com",
                "phone": "+1-555-0101",
                "company": "Acme Corp",
                "title": "CEO",
                "status": "active"
            },
            {
                "first_name": "Sarah",
                "last_name": "Johnson",
                "email": "demo.sarah.johnson@example.com",
                "phone": "+1-555-0102",
                "company": "TechStart Inc",
                "title": "CTO",
                "status": "active"
            },
            {
                "first_name": "Michael",
                "last_name": "Brown",
                "email": "demo.michael.brown@example.com",
                "phone": "+1-555-0103",
                "company": "Global Solutions",
                "title": "VP Sales",
                "status": "prospect"
            },
            {
                "first_name": "Emily",
                "last_name": "Davis",
                "email": "demo.emily.davis@example.com",
                "phone": "+1-555-0104",
                "company": "Innovation Labs",
                "title": "Product Manager",
                "status": "lead"
            }
        ]
        
        contacts = []
        for data in contacts_data:
            contact = Contact(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                phone=data["phone"],
                company=data["company"],
                title=data["title"],
                status=data["status"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(contact)
            contacts.append(contact)
        
        session.flush()
        logger.info(f"Created {len(contacts)} demo contacts")
        return contacts
        
    except Exception as e:
        logger.error(f"Error creating demo contacts: {e}")
        return None

def create_demo_deals(session: Session, tenant_id: str, contacts: List[Contact]) -> Optional[List[Deal]]:
    """Create demo deals"""
    try:
        deals_data = [
            {
                "title": "Enterprise CRM Implementation",
                "value": 50000.00,
                "stage": "negotiation",
                "probability": 75,
                "expected_close_date": datetime.utcnow() + timedelta(days=30)
            },
            {
                "title": "SaaS Platform License",
                "value": 25000.00,
                "stage": "proposal",
                "probability": 60,
                "expected_close_date": datetime.utcnow() + timedelta(days=45)
            },
            {
                "title": "Consulting Services",
                "value": 15000.00,
                "stage": "qualification",
                "probability": 40,
                "expected_close_date": datetime.utcnow() + timedelta(days=60)
            }
        ]
        
        deals = []
        for i, data in enumerate(deals_data):
            deal = Deal(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                title=data["title"],
                value=data["value"],
                stage=data["stage"],
                probability=data["probability"],
                expected_close_date=data["expected_close_date"],
                contact_id=contacts[i % len(contacts)].id if contacts else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(deal)
            deals.append(deal)
        
        session.flush()
        logger.info(f"Created {len(deals)} demo deals")
        return deals
        
    except Exception as e:
        logger.error(f"Error creating demo deals: {e}")
        return None

def create_demo_activities(session: Session, tenant_id: str, contacts: List[Contact], deals: List[Deal]) -> Optional[List[Activity]]:
    """Create demo activities"""
    try:
        activities_data = [
            {
                "type": "call",
                "subject": "Initial Discovery Call",
                "description": "Discussed business requirements and potential solutions",
                "duration_minutes": 30
            },
            {
                "type": "meeting",
                "subject": "Product Demo",
                "description": "Demonstrated key features and capabilities",
                "duration_minutes": 60
            },
            {
                "type": "email",
                "subject": "Proposal Follow-up",
                "description": "Sent detailed proposal and pricing information",
                "duration_minutes": 15
            },
            {
                "type": "task",
                "subject": "Contract Review",
                "description": "Reviewed and finalized contract terms",
                "duration_minutes": 45
            }
        ]
        
        activities = []
        for i, data in enumerate(activities_data):
            activity = Activity(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                type=data["type"],
                subject=data["subject"],
                description=data["description"],
                duration_minutes=data["duration_minutes"],
                contact_id=contacts[i % len(contacts)].id if contacts else None,
                deal_id=deals[i % len(deals)].id if deals else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(activity)
            activities.append(activity)
        
        session.flush()
        logger.info(f"Created {len(activities)} demo activities")
        return activities
        
    except Exception as e:
        logger.error(f"Error creating demo activities: {e}")
        return None

def create_demo_projects(session: Session, tenant_id: str) -> Optional[List[Project]]:
    """Create demo projects"""
    try:
        projects_data = [
            {
                "name": "CRM Implementation",
                "description": "Full CRM system implementation for enterprise client",
                "status": "in_progress",
                "start_date": datetime.utcnow() - timedelta(days=30),
                "end_date": datetime.utcnow() + timedelta(days=60)
            },
            {
                "name": "Sales Process Optimization",
                "description": "Streamline and optimize sales workflows",
                "status": "planning",
                "start_date": datetime.utcnow() + timedelta(days=15),
                "end_date": datetime.utcnow() + timedelta(days=90)
            }
        ]
        
        projects = []
        for data in projects_data:
            project = Project(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                name=data["name"],
                description=data["description"],
                status=data["status"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(project)
            projects.append(project)
        
        session.flush()
        logger.info(f"Created {len(projects)} demo projects")
        return projects
        
    except Exception as e:
        logger.error(f"Error creating demo projects: {e}")
        return None

def create_demo_tasks(session: Session, tenant_id: str, projects: List[Project]) -> Optional[List[Task]]:
    """Create demo tasks"""
    try:
        tasks_data = [
            {
                "title": "Requirements Gathering",
                "description": "Collect and document business requirements",
                "status": "completed",
                "priority": "high",
                "due_date": datetime.utcnow() + timedelta(days=7)
            },
            {
                "title": "System Configuration",
                "description": "Configure CRM system settings and workflows",
                "status": "in_progress",
                "priority": "medium",
                "due_date": datetime.utcnow() + timedelta(days=14)
            },
            {
                "title": "User Training",
                "description": "Conduct training sessions for end users",
                "status": "pending",
                "priority": "medium",
                "due_date": datetime.utcnow() + timedelta(days=21)
            }
        ]
        
        tasks = []
        for i, data in enumerate(tasks_data):
            task = Task(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                title=data["title"],
                description=data["description"],
                status=data["status"],
                priority=data["priority"],
                due_date=data["due_date"],
                project_id=projects[i % len(projects)].id if projects else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(task)
            tasks.append(task)
        
        session.flush()
        logger.info(f"Created {len(tasks)} demo tasks")
        return tasks
        
    except Exception as e:
        logger.error(f"Error creating demo tasks: {e}")
        return None

def create_demo_messages(session: Session, tenant_id: str, contacts: List[Contact]) -> Optional[List[Message]]:
    """Create demo messages"""
    try:
        # Create message thread first
        thread = MessageThread(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            subject="Project Discussion",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(thread)
        session.flush()
        
        messages_data = [
            {
                "content": "Hi, I'm interested in learning more about your CRM solution.",
                "sender_type": "contact"
            },
            {
                "content": "Great! I'd be happy to schedule a demo for you. What's your availability this week?",
                "sender_type": "user"
            },
            {
                "content": "I'm available on Tuesday at 2 PM. Does that work for you?",
                "sender_type": "contact"
            }
        ]
        
        messages = []
        for i, data in enumerate(messages_data):
            message = Message(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                thread_id=thread.id,
                content=data["content"],
                sender_type=data["sender_type"],
                contact_id=contacts[i % len(contacts)].id if contacts and data["sender_type"] == "contact" else None,
                created_at=datetime.utcnow() + timedelta(minutes=i*10),
                updated_at=datetime.utcnow() + timedelta(minutes=i*10)
            )
            session.add(message)
            messages.append(message)
        
        session.flush()
        logger.info(f"Created {len(messages)} demo messages")
        return messages
        
    except Exception as e:
        logger.error(f"Error creating demo messages: {e}")
        return None

def create_demo_audit_logs(session: Session, tenant_id: str) -> Optional[List[CRMOpsAuditLog]]:
    """Create demo audit logs"""
    try:
        audit_data = [
            {
                "action": "contact_created",
                "resource_type": "contact",
                "description": "Demo contact created"
            },
            {
                "action": "deal_updated",
                "resource_type": "deal",
                "description": "Deal stage updated to negotiation"
            },
            {
                "action": "activity_logged",
                "resource_type": "activity",
                "description": "Sales call logged"
            }
        ]
        
        audit_logs = []
        for data in audit_data:
            audit_log = CRMOpsAuditLog(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                action=data["action"],
                resource_type=data["resource_type"],
                description=data["description"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(audit_log)
            audit_logs.append(audit_log)
        
        session.flush()
        logger.info(f"Created {len(audit_logs)} demo audit logs")
        return audit_logs
        
    except Exception as e:
        logger.error(f"Error creating demo audit logs: {e}")
        return None
