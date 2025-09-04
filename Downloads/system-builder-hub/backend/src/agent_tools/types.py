"""
Agent tools type definitions
"""
import enum
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime

class ToolAuth(str, enum.Enum):
    """Tool authentication levels"""
    NONE = "none"
    TENANT = "tenant"
    SYSTEM = "system"

@dataclass
class ToolSpec:
    """Tool specification"""
    name: str
    version: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    auth: ToolAuth
    allow_concurrent: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['auth'] = self.auth.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolSpec':
        """Create from dictionary"""
        if 'auth' in data:
            data['auth'] = ToolAuth(data['auth'])
        return cls(**data)

@dataclass
class ToolCall:
    """Tool call request"""
    tool: str
    args: Dict[str, Any]
    id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolCall':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class ToolResult:
    """Tool call result"""
    id: str
    ok: bool
    error: Optional[Dict[str, Any]] = None
    redacted_output: Optional[Any] = None
    raw_output: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolResult':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class ToolContext:
    """Tool execution context"""
    tenant_id: str
    user_id: Optional[str] = None
    role: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolContext':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class ToolTranscript:
    """Tool execution transcript"""
    calls: List[ToolCall]
    results: List[ToolResult]
    total_time: float
    errors: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'calls': [call.to_dict() for call in self.calls],
            'results': [result.to_dict() for result in self.results],
            'total_time': self.total_time,
            'errors': self.errors
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolTranscript':
        """Create from dictionary"""
        calls = [ToolCall.from_dict(c) for c in data.get('calls', [])]
        results = [ToolResult.from_dict(r) for r in data.get('results', [])]
        return cls(
            calls=calls,
            results=results,
            total_time=data.get('total_time', 0.0),
            errors=data.get('errors', [])
        )

# Built-in tool schemas
DB_MIGRATE_SCHEMA = {
    "type": "object",
    "properties": {
        "op": {
            "type": "string",
            "enum": ["create_table", "add_column", "drop_column", "modify_column"]
        },
        "table": {"type": "string"},
        "columns": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "nullable": {"type": "boolean"},
                    "pk": {"type": "boolean"}
                },
                "required": ["name", "type"]
            }
        },
        "column": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "type": {"type": "string"},
                "nullable": {"type": "boolean"}
            },
            "required": ["name", "type"]
        },
        "dry_run": {"type": "boolean"}
    },
    "required": ["op", "table"]
}

HTTP_OPENAPI_SCHEMA = {
    "type": "object",
    "properties": {
        "base": {"type": "string"},
        "op_id": {"type": "string"},
        "params": {"type": "object"},
        "body": {"type": "object"},
        "headers": {"type": "object"}
    },
    "required": ["base", "op_id"]
}

FILES_STORE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["list", "info"]
        },
        "store": {"type": "string"},
        "prefix": {"type": "string"}
    },
    "required": ["action", "store"]
}

QUEUE_ENQUEUE_SCHEMA = {
    "type": "object",
    "properties": {
        "queue": {
            "type": "string",
            "enum": ["default", "low", "high"]
        },
        "job": {"type": "string"},
        "payload": {"type": "object"}
    },
    "required": ["job", "payload"]
}

EMAIL_SEND_SCHEMA = {
    "type": "object",
    "properties": {
        "template": {"type": "string"},
        "to": {"type": "string"},
        "payload": {"type": "object"},
        "dry_run": {"type": "boolean"}
    },
    "required": ["template", "to", "payload"]
}
