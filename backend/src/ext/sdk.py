"""
Plugin SDK for developers
"""
import logging
import functools
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from src.security.policy import UserContext, Role
from src.tenancy.context import get_current_tenant_id

logger = logging.getLogger(__name__)

class PluginContext:
    """Plugin execution context"""
    
    def __init__(self, tenant_id: str, user_id: Optional[str] = None, role: Optional[str] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role
        self._secrets = {}
        self._http_client = None
        self._llm_client = None
        self._files_client = None
        self._db_client = None
    
    @property
    def secrets(self):
        """Get secrets manager"""
        if not hasattr(self, '_secrets_manager'):
            from src.ext.secrets import SecretsManager
            self._secrets_manager = SecretsManager(self.tenant_id)
        return self._secrets_manager
    
    @property
    def http(self):
        """Get HTTP client"""
        if not self._http_client:
            from src.ext.http_client import HTTPClient
            self._http_client = HTTPClient(self.tenant_id)
        return self._http_client
    
    @property
    def llm(self):
        """Get LLM client"""
        if not self._llm_client:
            from src.ext.llm_client import LLMClient
            self._llm_client = LLMClient(self.tenant_id)
        return self._llm_client
    
    @property
    def files(self):
        """Get files client"""
        if not self._files_client:
            from src.ext.files_client import FilesClient
            self._files_client = FilesClient(self.tenant_id)
        return self._files_client
    
    @property
    def db(self):
        """Get database client (read-only)"""
        if not self._db_client:
            from src.ext.db_client import DBClient
            self._db_client = DBClient(self.tenant_id)
        return self._db_client
    
    def emit(self, event_type: str, payload: Dict[str, Any]):
        """Emit an event"""
        try:
            from src.analytics.service import AnalyticsService
            analytics = AnalyticsService()
            
            analytics.track(
                tenant_id=self.tenant_id,
                event=event_type,
                user_id=self.user_id,
                source='plugin',
                props=payload
            )
            
            logger.info(f"Plugin emitted event: {event_type}")
            
        except Exception as e:
            logger.error(f"Error emitting event {event_type}: {e}")

def hook(event_type: str):
    """Decorator for event hooks"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(ctx: PluginContext, event_data: Dict[str, Any]):
            try:
                return func(ctx, event_data)
            except Exception as e:
                logger.error(f"Error in event hook {event_type}: {e}")
                raise
        
        # Mark as event hook
        wrapper._plugin_hook_type = 'event'
        wrapper._plugin_event_type = event_type
        
        return wrapper
    return decorator

def route(path: str, methods: List[str] = None):
    """Decorator for plugin routes"""
    if methods is None:
        methods = ['GET']
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(ctx: PluginContext, *args, **kwargs):
            try:
                return func(ctx, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in plugin route {path}: {e}")
                raise
        
        # Mark as route
        wrapper._plugin_route_type = 'route'
        wrapper._plugin_route_path = path
        wrapper._plugin_route_methods = methods
        
        return wrapper
    return decorator

def job(name: str, schedule: str = None):
    """Decorator for scheduled jobs"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(ctx: PluginContext):
            try:
                return func(ctx)
            except Exception as e:
                logger.error(f"Error in plugin job {name}: {e}")
                raise
        
        # Mark as job
        wrapper._plugin_job_type = 'job'
        wrapper._plugin_job_name = name
        wrapper._plugin_job_schedule = schedule
        
        return wrapper
    return decorator

def llm_filter(filter_type: str):
    """Decorator for LLM filters"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(ctx: PluginContext, data: Any):
            try:
                return func(ctx, data)
            except Exception as e:
                logger.error(f"Error in LLM filter {filter_type}: {e}")
                raise
        
        # Mark as LLM filter
        wrapper._plugin_hook_type = 'llm_filter'
        wrapper._plugin_filter_type = filter_type
        
        return wrapper
    return decorator

def generator_hook(hook_type: str):
    """Decorator for generator hooks"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(ctx: PluginContext, data: Any):
            try:
                return func(ctx, data)
            except Exception as e:
                logger.error(f"Error in generator hook {hook_type}: {e}")
                raise
        
        # Mark as generator hook
        wrapper._plugin_hook_type = 'generator'
        wrapper._plugin_generator_hook_type = hook_type
        
        return wrapper
    return decorator

# Example plugin usage:
"""
from src.ext.sdk import hook, route, job, PluginContext

@hook("auth.user.created")
def on_user_created(ctx: PluginContext, event_data):
    user_email = event_data['user']['email']
    ctx.secrets.get("WELCOME_EMAIL_TEMPLATE")
    # Send welcome email...

@route("/ping", methods=["GET"])
def ping_route(ctx: PluginContext):
    return {"status": "ok", "tenant": ctx.tenant_id}

@job("daily_cleanup", schedule="0 2 * * *")
def daily_cleanup_job(ctx: PluginContext):
    # Clean up old data...
    pass
"""
