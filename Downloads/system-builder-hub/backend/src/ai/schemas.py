"""
AI schemas for CRM/Ops Template
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CopilotRequest:
    """Copilot request schema"""
    agent: str  # 'sales', 'ops', 'success', 'builder'
    message: str
    context: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, bool]] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class CopilotResponse:
    """Copilot response schema"""
    conversation_id: str
    reply: str
    actions: Optional[List[Dict[str, Any]]] = None
    references: Optional[List[Dict[str, Any]]] = None
    metrics: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

@dataclass
class AnalyticsQuery:
    """Analytics query schema"""
    question: str
    time_range: Optional[Dict[str, str]] = None
    filters: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class AnalyticsResponse:
    """Analytics response schema"""
    summary: str
    charts: List[Dict[str, Any]]
    tables: Optional[List[Dict[str, Any]]] = None
    export: Optional[Dict[str, str]] = None
    metrics: Optional[Dict[str, Any]] = None

@dataclass
class ReportRequest:
    """Report request schema"""
    type: str  # 'weekly_sales', 'pipeline_forecast', 'ops_throughput', 'activity_sla'
    name: str
    params: Dict[str, Any]
    scheduled_cron: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class ReportResponse:
    """Report response schema"""
    report_id: str
    status: str
    file_url: Optional[str] = None
    scheduled: bool = False
    next_run_at: Optional[datetime] = None

@dataclass
class VoiceTranscribeRequest:
    """Voice transcription request schema"""
    audio_data: bytes
    session_id: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class VoiceTranscribeResponse:
    """Voice transcription response schema"""
    session_id: str
    transcript: str
    intent: Dict[str, Any]
    confidence: float
    status: str

@dataclass
class VoiceExecuteRequest:
    """Voice execution request schema"""
    session_id: str
    intent: Dict[str, Any]
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class VoiceExecuteResponse:
    """Voice execution response schema"""
    session_id: str
    actions: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    status: str

@dataclass
class RAGSearchRequest:
    """RAG search request schema"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class RAGSearchResponse:
    """RAG search response schema"""
    matches: List[Dict[str, Any]]
    answer: Optional[str] = None
    sources: List[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]] = None

@dataclass
class RAGIndexRequest:
    """RAG indexing request schema"""
    scopes: List[str]  # ['contacts', 'deals', 'tasks', 'files']
    incremental: bool = True
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

@dataclass
class RAGIndexResponse:
    """RAG indexing response schema"""
    job_id: str
    status: str
    scopes: List[str]
    estimated_duration: Optional[int] = None

@dataclass
class ToolCall:
    """Tool call schema"""
    name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None

@dataclass
class ToolResult:
    """Tool result schema"""
    tool_call_id: str
    result: Any
    error: Optional[str] = None

@dataclass
class ConversationContext:
    """Conversation context schema"""
    conversation_id: str
    messages: List[Dict[str, Any]]
    agent: str
    user_id: str
    tenant_id: str
    tools_enabled: bool = True

@dataclass
class AnalyticsChart:
    """Analytics chart schema"""
    type: str  # 'line', 'bar', 'pie', 'table'
    title: str
    data: List[Dict[str, Any]]
    config: Optional[Dict[str, Any]] = None

@dataclass
class ReportTemplate:
    """Report template schema"""
    type: str
    name: str
    description: str
    template_path: str
    params_schema: Dict[str, Any]
    default_params: Dict[str, Any]

@dataclass
class AIConfig:
    """AI configuration schema"""
    tenant_id: str
    rag_enabled: bool = True
    voice_enabled: bool = True
    copilot_enabled: bool = True
    analytics_enabled: bool = True
    reports_enabled: bool = True
    rate_limits: Dict[str, int] = None
    model_config: Dict[str, Any] = None

# Default rate limits
DEFAULT_RATE_LIMITS = {
    'copilot_ask': 60,  # per minute
    'analytics_query': 20,  # per minute
    'reports_run': 10,  # per minute
    'rag_search': 10,  # per minute
    'voice_transcribe': 6,  # per minute
}

# Available agents
AVAILABLE_AGENTS = {
    'sales': {
        'name': 'Sales Copilot',
        'description': 'Assists with sales activities, deal management, and pipeline optimization',
        'tools': ['read_contacts', 'read_deals', 'create_tasks', 'schedule_activities', 'draft_emails']
    },
    'ops': {
        'name': 'Operations Copilot',
        'description': 'Helps with operational tasks, project management, and process optimization',
        'tools': ['read_projects', 'read_tasks', 'create_tasks', 'update_status', 'generate_reports']
    },
    'success': {
        'name': 'Success Copilot',
        'description': 'Supports customer success activities and relationship management',
        'tools': ['read_contacts', 'read_activities', 'create_tasks', 'schedule_meetings', 'draft_emails']
    },
    'builder': {
        'name': 'Builder Copilot',
        'description': 'Assists with system configuration, automation setup, and customization',
        'tools': ['read_automations', 'create_automations', 'test_automations', 'configure_system']
    }
}

# Report templates
REPORT_TEMPLATES = {
    'weekly_sales': {
        'name': 'Weekly Sales Summary',
        'description': 'Weekly sales performance and pipeline summary',
        'template_path': 'reports/weekly_sales.html',
        'params_schema': {
            'start_date': {'type': 'date', 'required': True},
            'end_date': {'type': 'date', 'required': True},
            'include_charts': {'type': 'boolean', 'default': True}
        },
        'default_params': {
            'include_charts': True
        }
    },
    'pipeline_forecast': {
        'name': 'Pipeline Forecast',
        'description': 'Sales pipeline forecast and analysis',
        'template_path': 'reports/pipeline_forecast.html',
        'params_schema': {
            'forecast_period': {'type': 'string', 'enum': ['30d', '60d', '90d'], 'default': '90d'},
            'include_probability': {'type': 'boolean', 'default': True}
        },
        'default_params': {
            'forecast_period': '90d',
            'include_probability': True
        }
    },
    'ops_throughput': {
        'name': 'Operations Throughput',
        'description': 'Operations team throughput and efficiency metrics',
        'template_path': 'reports/ops_throughput.html',
        'params_schema': {
            'team_members': {'type': 'array', 'items': {'type': 'string'}},
            'time_period': {'type': 'string', 'enum': ['week', 'month', 'quarter'], 'default': 'month'}
        },
        'default_params': {
            'time_period': 'month'
        }
    },
    'activity_sla': {
        'name': 'Activity SLA Report',
        'description': 'Activity SLA compliance and performance',
        'template_path': 'reports/activity_sla.html',
        'params_schema': {
            'sla_type': {'type': 'string', 'enum': ['response_time', 'resolution_time'], 'default': 'response_time'},
            'date_range': {'type': 'object', 'properties': {'start': {'type': 'date'}, 'end': {'type': 'date'}}}
        },
        'default_params': {
            'sla_type': 'response_time'
        }
    }
}
