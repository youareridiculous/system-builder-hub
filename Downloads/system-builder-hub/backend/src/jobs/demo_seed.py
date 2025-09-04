"""
Demo data seeding job
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from src.database import db_session
from src.analytics.service import AnalyticsService
from src.agent_tools.kernel import tool_kernel
from src.agent_tools.types import ToolCall, ToolContext

logger = logging.getLogger(__name__)

class DemoSeedJob:
    """Demo data seeding job"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
    
    def seed_enterprise_demo(self, tenant_slug: str, num_projects: int = 3, 
                           tasks_per_project: int = 8) -> Dict[str, Any]:
        """Seed demo data for enterprise stack"""
        try:
            # Create tool context
            tool_context = ToolContext(
                tenant_id=tenant_slug,
                user_id='system',
                role='admin'
            )
            
            # Track seeding start
            self.analytics.track(
                tenant_id=tenant_slug,
                event='demo.seed.started',
                user_id='system',
                source='demo_seed',
                props={
                    'num_projects': num_projects,
                    'tasks_per_project': tasks_per_project
                }
            )
            
            # Seed demo data using tools
            results = []
            
            # 1. Create demo account
            account_result = self._create_demo_account(tenant_slug, tool_context)
            results.append(account_result)
            
            # 2. Create demo users
            users_result = self._create_demo_users(tenant_slug, tool_context)
            results.append(users_result)
            
            # 3. Create demo projects
            projects_result = self._create_demo_projects(
                tenant_slug, num_projects, tool_context
            )
            results.append(projects_result)
            
            # 4. Create demo tasks
            tasks_result = self._create_demo_tasks(
                tenant_slug, num_projects, tasks_per_project, tool_context
            )
            results.append(tasks_result)
            
            # 5. Upload demo files
            files_result = self._upload_demo_files(tenant_slug, tool_context)
            results.append(files_result)
            
            # 6. Send welcome email
            email_result = self._send_welcome_email(tenant_slug, tool_context)
            results.append(email_result)
            
            # Track seeding completion
            self.analytics.track(
                tenant_id=tenant_slug,
                event='demo.seed.completed',
                user_id='system',
                source='demo_seed',
                props={
                    'results': results,
                    'total_operations': len(results)
                }
            )
            
            logger.info(f"Demo seeding completed for tenant: {tenant_slug}")
            
            return {
                'success': True,
                'tenant_slug': tenant_slug,
                'results': results,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error seeding demo data: {e}")
            
            # Track seeding failure
            self.analytics.track(
                tenant_id=tenant_slug,
                event='demo.seed.failed',
                user_id='system',
                source='demo_seed',
                props={
                    'error': str(e)
                }
            )
            
            return {
                'success': False,
                'error': str(e),
                'tenant_slug': tenant_slug
            }
    
    def _create_demo_account(self, tenant_slug: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Create demo account"""
        try:
            # Use queue.enqueue to create account
            call = ToolCall(
                id='seed_account',
                tool='queue.enqueue',
                args={
                    'queue': 'default',
                    'job': 'create_demo_account',
                    'payload': {
                        'tenant_slug': tenant_slug,
                        'account_name': f'{tenant_slug.title()} Demo Account',
                        'plan': 'pro'
                    }
                }
            )
            
            result = tool_kernel.execute(call, tool_context)
            
            return {
                'operation': 'create_account',
                'success': result.ok,
                'result': result.redacted_output if result.ok else result.error
            }
            
        except Exception as e:
            logger.error(f"Error creating demo account: {e}")
            return {
                'operation': 'create_account',
                'success': False,
                'error': str(e)
            }
    
    def _create_demo_users(self, tenant_slug: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Create demo users"""
        try:
            demo_users = [
                {
                    'email': f'admin@{tenant_slug}.com',
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'role': 'admin'
                },
                {
                    'email': f'manager@{tenant_slug}.com',
                    'first_name': 'Project',
                    'last_name': 'Manager',
                    'role': 'manager'
                },
                {
                    'email': f'developer@{tenant_slug}.com',
                    'first_name': 'Dev',
                    'last_name': 'User',
                    'role': 'user'
                }
            ]
            
            # Use queue.enqueue to create users
            call = ToolCall(
                id='seed_users',
                tool='queue.enqueue',
                args={
                    'queue': 'default',
                    'job': 'create_demo_users',
                    'payload': {
                        'tenant_slug': tenant_slug,
                        'users': demo_users
                    }
                }
            )
            
            result = tool_kernel.execute(call, tool_context)
            
            return {
                'operation': 'create_users',
                'success': result.ok,
                'users_count': len(demo_users),
                'result': result.redacted_output if result.ok else result.error
            }
            
        except Exception as e:
            logger.error(f"Error creating demo users: {e}")
            return {
                'operation': 'create_users',
                'success': False,
                'error': str(e)
            }
    
    def _create_demo_projects(self, tenant_slug: str, num_projects: int, 
                            tool_context: ToolContext) -> Dict[str, Any]:
        """Create demo projects"""
        try:
            project_names = [
                'Website Redesign',
                'Mobile App Development',
                'API Integration',
                'Data Migration',
                'Security Audit'
            ]
            
            # Use queue.enqueue to create projects
            call = ToolCall(
                id='seed_projects',
                tool='queue.enqueue',
                args={
                    'queue': 'default',
                    'job': 'create_demo_projects',
                    'payload': {
                        'tenant_slug': tenant_slug,
                        'projects': project_names[:num_projects]
                    }
                }
            )
            
            result = tool_kernel.execute(call, tool_context)
            
            return {
                'operation': 'create_projects',
                'success': result.ok,
                'projects_count': num_projects,
                'result': result.redacted_output if result.ok else result.error
            }
            
        except Exception as e:
            logger.error(f"Error creating demo projects: {e}")
            return {
                'operation': 'create_projects',
                'success': False,
                'error': str(e)
            }
    
    def _create_demo_tasks(self, tenant_slug: str, num_projects: int, 
                          tasks_per_project: int, tool_context: ToolContext) -> Dict[str, Any]:
        """Create demo tasks"""
        try:
            task_templates = [
                'Design user interface',
                'Implement authentication',
                'Write unit tests',
                'Set up CI/CD pipeline',
                'Optimize database queries',
                'Add error handling',
                'Update documentation',
                'Perform code review'
            ]
            
            # Use queue.enqueue to create tasks
            call = ToolCall(
                id='seed_tasks',
                tool='queue.enqueue',
                args={
                    'queue': 'default',
                    'job': 'create_demo_tasks',
                    'payload': {
                        'tenant_slug': tenant_slug,
                        'num_projects': num_projects,
                        'tasks_per_project': tasks_per_project,
                        'task_templates': task_templates
                    }
                }
            )
            
            result = tool_kernel.execute(call, tool_context)
            
            return {
                'operation': 'create_tasks',
                'success': result.ok,
                'tasks_count': num_projects * tasks_per_project,
                'result': result.redacted_output if result.ok else result.error
            }
            
        except Exception as e:
            logger.error(f"Error creating demo tasks: {e}")
            return {
                'operation': 'create_tasks',
                'success': False,
                'error': str(e)
            }
    
    def _upload_demo_files(self, tenant_slug: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Upload demo files"""
        try:
            # Use files.store to list files (simulate upload)
            call = ToolCall(
                id='seed_files',
                tool='files.store',
                args={
                    'action': 'list',
                    'store': f'{tenant_slug}-files',
                    'prefix': 'demo/'
                }
            )
            
            result = tool_kernel.execute(call, tool_context)
            
            return {
                'operation': 'upload_files',
                'success': result.ok,
                'result': result.redacted_output if result.ok else result.error
            }
            
        except Exception as e:
            logger.error(f"Error uploading demo files: {e}")
            return {
                'operation': 'upload_files',
                'success': False,
                'error': str(e)
            }
    
    def _send_welcome_email(self, tenant_slug: str, tool_context: ToolContext) -> Dict[str, Any]:
        """Send welcome email"""
        try:
            # Use email.send to send welcome email
            call = ToolCall(
                id='welcome_email',
                tool='email.send',
                args={
                    'template': 'welcome',
                    'to': f'admin@{tenant_slug}.com',
                    'payload': {
                        'company_name': f'{tenant_slug.title()} Corp',
                        'admin_email': f'admin@{tenant_slug}.com',
                        'demo_url': f'https://{tenant_slug}.demo.com'
                    },
                    'dry_run': True
                }
            )
            
            result = tool_kernel.execute(call, tool_context)
            
            return {
                'operation': 'send_welcome_email',
                'success': result.ok,
                'result': result.redacted_output if result.ok else result.error
            }
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return {
                'operation': 'send_welcome_email',
                'success': False,
                'error': str(e)
            }

# Global instance
demo_seed_job = DemoSeedJob()
