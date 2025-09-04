"""
Search service for CRM/Ops Template
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text
from src.database import db_session
from src.crm_ops.collaboration.models import SearchIndex, SavedView
from src.crm_ops.models import Contact, Deal, Task, Project

logger = logging.getLogger(__name__)

class SearchService:
    """Service for search operations"""
    
    def __init__(self):
        pass
    
    def global_search(self, tenant_id: str, query: str, entity_types: List[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Perform global search across entities"""
        if entity_types is None:
            entity_types = ['contact', 'deal', 'task', 'project']
        
        with db_session() as session:
            results = {}
            
            for entity_type in entity_types:
                if entity_type == 'contact':
                    results['contacts'] = self._search_contacts(session, tenant_id, query, limit)
                elif entity_type == 'deal':
                    results['deals'] = self._search_deals(session, tenant_id, query, limit)
                elif entity_type == 'task':
                    results['tasks'] = self._search_tasks(session, tenant_id, query, limit)
                elif entity_type == 'project':
                    results['projects'] = self._search_projects(session, tenant_id, query, limit)
            
            return results
    
    def advanced_search(self, tenant_id: str, filters: Dict[str, Any], entity_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Perform advanced search with filters"""
        with db_session() as session:
            if entity_type == 'contact':
                return self._advanced_search_contacts(session, tenant_id, filters, limit)
            elif entity_type == 'deal':
                return self._advanced_search_deals(session, tenant_id, filters, limit)
            elif entity_type == 'task':
                return self._advanced_search_tasks(session, tenant_id, filters, limit)
            elif entity_type == 'project':
                return self._advanced_search_projects(session, tenant_id, filters, limit)
            else:
                return []
    
    def get_faceted_search(self, tenant_id: str, entity_type: str) -> Dict[str, Any]:
        """Get faceted search data (tag counts, status counts, etc.)"""
        with db_session() as session:
            if entity_type == 'contact':
                return self._get_contact_facets(session, tenant_id)
            elif entity_type == 'deal':
                return self._get_deal_facets(session, tenant_id)
            elif entity_type == 'task':
                return self._get_task_facets(session, tenant_id)
            elif entity_type == 'project':
                return self._get_project_facets(session, tenant_id)
            else:
                return {}
    
    def _search_contacts(self, session: Session, tenant_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search contacts"""
        search_term = f"%{query}%"
        
        contacts = session.query(Contact).filter(
            Contact.tenant_id == tenant_id,
            or_(
                Contact.first_name.ilike(search_term),
                Contact.last_name.ilike(search_term),
                Contact.email.ilike(search_term),
                Contact.company.ilike(search_term),
                Contact.phone.ilike(search_term)
            )
        ).limit(limit).all()
        
        return [contact.to_dict() for contact in contacts]
    
    def _search_deals(self, session: Session, tenant_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search deals"""
        search_term = f"%{query}%"
        
        deals = session.query(Deal).filter(
            Deal.tenant_id == tenant_id,
            or_(
                Deal.title.ilike(search_term),
                Deal.notes.ilike(search_term)
            )
        ).limit(limit).all()
        
        return [deal.to_dict() for deal in deals]
    
    def _search_tasks(self, session: Session, tenant_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search tasks"""
        search_term = f"%{query}%"
        
        tasks = session.query(Task).filter(
            Task.tenant_id == tenant_id,
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term)
            )
        ).limit(limit).all()
        
        return [task.to_dict() for task in tasks]
    
    def _search_projects(self, session: Session, tenant_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search projects"""
        search_term = f"%{query}%"
        
        projects = session.query(Project).filter(
            Project.tenant_id == tenant_id,
            or_(
                Project.name.ilike(search_term),
                Project.description.ilike(search_term)
            )
        ).limit(limit).all()
        
        return [project.to_dict() for project in projects]
    
    def _advanced_search_contacts(self, session: Session, tenant_id: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Advanced search contacts with filters"""
        query = session.query(Contact).filter(Contact.tenant_id == tenant_id)
        
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
        
        if filters.get('tags'):
            for tag in filters['tags']:
                query = query.filter(Contact.tags.contains([tag]))
        
        if filters.get('status'):
            if filters['status'] == 'active':
                query = query.filter(Contact.is_active == True)
            elif filters['status'] == 'inactive':
                query = query.filter(Contact.is_active == False)
        
        if filters.get('company'):
            query = query.filter(Contact.company.ilike(f"%{filters['company']}%"))
        
        contacts = query.limit(limit).all()
        return [contact.to_dict() for contact in contacts]
    
    def _advanced_search_deals(self, session: Session, tenant_id: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Advanced search deals with filters"""
        query = session.query(Deal).filter(Deal.tenant_id == tenant_id)
        
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    Deal.title.ilike(search_term),
                    Deal.notes.ilike(search_term)
                )
            )
        
        if filters.get('status'):
            query = query.filter(Deal.status == filters['status'])
        
        if filters.get('pipeline_stage'):
            query = query.filter(Deal.pipeline_stage == filters['pipeline_stage'])
        
        if filters.get('min_value'):
            query = query.filter(Deal.value >= filters['min_value'])
        
        if filters.get('max_value'):
            query = query.filter(Deal.value <= filters['max_value'])
        
        deals = query.limit(limit).all()
        return [deal.to_dict() for deal in deals]
    
    def _advanced_search_tasks(self, session: Session, tenant_id: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Advanced search tasks with filters"""
        query = session.query(Task).filter(Task.tenant_id == tenant_id)
        
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term)
                )
            )
        
        if filters.get('status'):
            query = query.filter(Task.status == filters['status'])
        
        if filters.get('priority'):
            query = query.filter(Task.priority == filters['priority'])
        
        if filters.get('assignee_id'):
            query = query.filter(Task.assignee_id == filters['assignee_id'])
        
        tasks = query.limit(limit).all()
        return [task.to_dict() for task in tasks]
    
    def _advanced_search_projects(self, session: Session, tenant_id: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Advanced search projects with filters"""
        query = session.query(Project).filter(Project.tenant_id == tenant_id)
        
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    Project.name.ilike(search_term),
                    Project.description.ilike(search_term)
                )
            )
        
        if filters.get('status'):
            query = query.filter(Project.status == filters['status'])
        
        projects = query.limit(limit).all()
        return [project.to_dict() for project in projects]
    
    def _get_contact_facets(self, session: Session, tenant_id: str) -> Dict[str, Any]:
        """Get contact facets"""
        # Get tag counts
        tag_counts = session.query(
            func.unnest(Contact.tags).label('tag'),
            func.count().label('count')
        ).filter(
            Contact.tenant_id == tenant_id,
            Contact.tags.isnot(None)
        ).group_by(text('tag')).all()
        
        # Get company counts
        company_counts = session.query(
            Contact.company,
            func.count().label('count')
        ).filter(
            Contact.tenant_id == tenant_id,
            Contact.company.isnot(None)
        ).group_by(Contact.company).all()
        
        return {
            'tags': [{'tag': tag, 'count': count} for tag, count in tag_counts],
            'companies': [{'company': company, 'count': count} for company, count in company_counts]
        }
    
    def _get_deal_facets(self, session: Session, tenant_id: str) -> Dict[str, Any]:
        """Get deal facets"""
        # Get status counts
        status_counts = session.query(
            Deal.status,
            func.count().label('count')
        ).filter(
            Deal.tenant_id == tenant_id
        ).group_by(Deal.status).all()
        
        # Get pipeline stage counts
        stage_counts = session.query(
            Deal.pipeline_stage,
            func.count().label('count')
        ).filter(
            Deal.tenant_id == tenant_id
        ).group_by(Deal.pipeline_stage).all()
        
        return {
            'statuses': [{'status': status, 'count': count} for status, count in status_counts],
            'stages': [{'stage': stage, 'count': count} for stage, count in stage_counts]
        }
    
    def _get_task_facets(self, session: Session, tenant_id: str) -> Dict[str, Any]:
        """Get task facets"""
        # Get status counts
        status_counts = session.query(
            Task.status,
            func.count().label('count')
        ).filter(
            Task.tenant_id == tenant_id
        ).group_by(Task.status).all()
        
        # Get priority counts
        priority_counts = session.query(
            Task.priority,
            func.count().label('count')
        ).filter(
            Task.tenant_id == tenant_id
        ).group_by(Task.priority).all()
        
        return {
            'statuses': [{'status': status, 'count': count} for status, count in status_counts],
            'priorities': [{'priority': priority, 'count': count} for priority, count in priority_counts]
        }
    
    def _get_project_facets(self, session: Session, tenant_id: str) -> Dict[str, Any]:
        """Get project facets"""
        # Get status counts
        status_counts = session.query(
            Project.status,
            func.count().label('count')
        ).filter(
            Project.tenant_id == tenant_id
        ).group_by(Project.status).all()
        
        return {
            'statuses': [{'status': status, 'count': count} for status, count in status_counts]
        }
