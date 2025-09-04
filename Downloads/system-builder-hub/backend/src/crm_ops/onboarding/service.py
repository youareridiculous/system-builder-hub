"""
Onboarding service for CRM/Ops Template
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.models import Contact, Deal, Activity, Project, Task, MessageThread, Message
from src.crm_ops.onboarding.models import OnboardingSession
from faker import Faker
import random

logger = logging.getLogger(__name__)
fake = Faker()

class OnboardingService:
    """Service for onboarding operations"""
    
    @staticmethod
    def seed_demo_data(tenant_id: str, user_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Seed demo data for a tenant"""
        if params is None:
            params = {
                'contacts': 20,
                'deals': 5,
                'projects': 2,
                'tasks_per_project': 8
            }
        
        with db_session() as session:
            # Track what we create
            created_data = {
                'contacts': [],
                'deals': [],
                'activities': [],
                'projects': [],
                'tasks': [],
                'message_threads': [],
                'messages': []
            }
            
            # Create contacts
            contacts = []
            for i in range(params['contacts']):
                contact = Contact(
                    tenant_id=tenant_id,
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    email=fake.email(),
                    phone=fake.phone_number(),
                    company=fake.company(),
                    tags=random.sample(['lead', 'customer', 'prospect', 'partner'], random.randint(1, 2)),
                    custom_fields={
                        'linkedin': fake.url(),
                        'industry': random.choice(['technology', 'healthcare', 'finance', 'retail', 'manufacturing']),
                        'source': random.choice(['website', 'referral', 'cold_outreach', 'event'])
                    },
                    created_by=user_id
                )
                session.add(contact)
                contacts.append(contact)
            
            session.flush()  # Get IDs
            
            # Create deals
            deals = []
            pipeline_stages = ['prospecting', 'qualification', 'proposal', 'negotiation']
            deal_statuses = ['open', 'won', 'lost']
            
            for i in range(params['deals']):
                contact = random.choice(contacts)
                deal = Deal(
                    tenant_id=tenant_id,
                    contact_id=str(contact.id),
                    title=f"Deal {i+1}: {fake.catch_phrase()}",
                    pipeline_stage=random.choice(pipeline_stages),
                    value=random.randint(5000, 500000),
                    status=random.choice(deal_statuses),
                    notes=fake.text(max_nb_chars=200),
                    expected_close_date=datetime.utcnow() + timedelta(days=random.randint(30, 180)),
                    created_by=user_id
                )
                session.add(deal)
                deals.append(deal)
            
            session.flush()
            
            # Create activities
            activity_types = ['call', 'email', 'meeting', 'task']
            activity_statuses = ['pending', 'completed', 'cancelled']
            
            for i in range(min(10, len(contacts))):
                contact = random.choice(contacts)
                deal = random.choice(deals) if deals else None
                
                activity = Activity(
                    tenant_id=tenant_id,
                    contact_id=str(contact.id),
                    deal_id=str(deal.id) if deal else None,
                    type=random.choice(activity_types),
                    title=f"{random.choice(activity_types).title()} with {contact.first_name}",
                    description=fake.text(max_nb_chars=150),
                    status=random.choice(activity_statuses),
                    priority=random.choice(['low', 'medium', 'high']),
                    due_date=datetime.utcnow() + timedelta(days=random.randint(1, 30)),
                    duration_minutes=random.randint(15, 120),
                    created_by=user_id
                )
                session.add(activity)
                created_data['activities'].append(activity)
            
            # Create projects
            projects = []
            for i in range(params['projects']):
                project = Project(
                    tenant_id=tenant_id,
                    name=f"Project {i+1}: {fake.catch_phrase()}",
                    description=fake.text(max_nb_chars=300),
                    status=random.choice(['active', 'archived']),
                    start_date=datetime.utcnow() - timedelta(days=random.randint(30, 90)),
                    end_date=datetime.utcnow() + timedelta(days=random.randint(30, 180)),
                    created_by=user_id
                )
                session.add(project)
                projects.append(project)
            
            session.flush()
            
            # Create tasks
            task_statuses = ['todo', 'in_progress', 'review', 'done']
            task_priorities = ['low', 'medium', 'high', 'urgent']
            
            for project in projects:
                for i in range(params['tasks_per_project']):
                    task = Task(
                        tenant_id=tenant_id,
                        project_id=str(project.id),
                        title=f"Task {i+1}: {fake.catch_phrase()}",
                        description=fake.text(max_nb_chars=200),
                        assignee_id=user_id,
                        priority=random.choice(task_priorities),
                        status=random.choice(task_statuses),
                        due_date=datetime.utcnow() + timedelta(days=random.randint(1, 60)),
                        estimated_hours=random.randint(1, 8),
                        actual_hours=random.randint(1, 8) if random.random() > 0.5 else None,
                        created_by=user_id
                    )
                    session.add(task)
                    created_data['tasks'].append(task)
            
            # Create message thread
            thread = MessageThread(
                tenant_id=tenant_id,
                title="Welcome to CRM/Ops!",
                participants=[user_id],
                created_by=user_id
            )
            session.add(thread)
            session.flush()
            
            # Create welcome message
            welcome_message = Message(
                tenant_id=tenant_id,
                thread_id=str(thread.id),
                sender_id=user_id,
                body="Welcome to your new CRM/Ops workspace! This is where you can collaborate with your team on deals, projects, and activities. Feel free to explore the different sections and start building your customer relationships.",
                attachments=[]
            )
            session.add(welcome_message)
            
            session.commit()
            
            # Update counts
            created_data['contacts'] = contacts
            created_data['deals'] = deals
            created_data['projects'] = projects
            created_data['message_threads'] = [thread]
            created_data['messages'] = [welcome_message]
            
            logger.info(f"Demo data seeded for tenant {tenant_id}: {len(contacts)} contacts, {len(deals)} deals, {len(projects)} projects")
            
            return {
                'contacts_created': len(contacts),
                'deals_created': len(deals),
                'activities_created': len(created_data['activities']),
                'projects_created': len(projects),
                'tasks_created': len(created_data['tasks']),
                'message_threads_created': 1,
                'messages_created': 1
            }
    
    @staticmethod
    def should_show_onboarding(tenant_id: str) -> bool:
        """Check if onboarding should be shown for a tenant"""
        with db_session() as session:
            # Check if tenant has any CRM data
            from src.crm_ops.models import Contact, Deal, Project
            
            has_contacts = session.query(Contact).filter(Contact.tenant_id == tenant_id).first() is not None
            has_deals = session.query(Deal).filter(Deal.tenant_id == tenant_id).first() is not None
            has_projects = session.query(Project).filter(Project.tenant_id == tenant_id).first() is not None
            
            has_crm_data = has_contacts or has_deals or has_projects
            
            # Check if onboarding is completed
            onboarding = session.query(OnboardingSession).filter(
                OnboardingSession.tenant_id == tenant_id,
                OnboardingSession.completed == True
            ).first()
            
            return not has_crm_data and not onboarding
