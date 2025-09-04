"""
Builder Schema - Canonical payload definitions for Visual Builder
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from uuid import UUID
import uuid
import re

# Valid node types
VALID_NODE_TYPES = ["ui_page", "rest_api", "auth", "db_table", "agent_tool", "payment", "file_store"]

@dataclass
class Node:
    """Builder node representing a component"""
    id: str
    type: str
    props: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)  # For position, etc.
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        
        # Validate node type
        if self.type not in VALID_NODE_TYPES:
            raise ValueError(f"Unknown node type: {self.type}. Must be one of: {VALID_NODE_TYPES}")
        
        # Apply defaults
        self.props = coerce_defaults(self)

@dataclass
class Edge:
    """Builder edge representing connections between nodes"""
    source: str
    target: str
    kind: str = "default"  # "data_flow", "auth", "ui_navigation", etc.

@dataclass
class BuilderState:
    """Complete builder state"""
    project_id: str
    version: Optional[str] = None
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    exists: bool = True  # Whether this state exists in storage
    
    def __post_init__(self):
        if not self.project_id:
            raise ValueError("project_id is required")
        
        # Ensure arrays exist
        if not hasattr(self, 'nodes') or self.nodes is None:
            self.nodes = []
        if not hasattr(self, 'edges') or self.edges is None:
            self.edges = []
        if not hasattr(self, 'metadata') or self.metadata is None:
            self.metadata = {}
        
        # Validate that all edges reference existing nodes
        node_ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge source '{edge.source}' references non-existent node")
            if edge.target not in node_ids:
                raise ValueError(f"Edge target '{edge.target}' references non-existent node")

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    if not text:
        return ""
    # Convert to lowercase, replace spaces and special chars with hyphens, remove special chars
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    slug = re.sub(r'\s+', '-', slug)
    # Collapse multiple dashes and strip leading/trailing dashes
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def route_to_slug(route: str) -> str:
    """Convert route to slug by taking the last non-empty segment"""
    if not route:
        return "page"
    
    # Normalize route (ensure leading slash)
    if not route.startswith('/'):
        route = '/' + route
    
    # Split and get non-empty segments
    segs = [s for s in route.split('/') if s]
    
    # Return slugified last segment, or "page" if no segments
    return slugify(segs[-1] if segs else "page")

def coerce_defaults(node: Node) -> Dict[str, Any]:
    """Apply defaults for node type"""
    props = node.props.copy()
    
    if node.type == "ui_page":
        # Determine name and route with proper defaults
        name = props.get('name') or props.get('title') or "Page"
        route = props.get('route')
        
        # If no route specified, derive from name
        if not route:
            route = "/" + slugify(name)
        
        # Ensure route starts with /
        if route and not route.startswith('/'):
            route = '/' + route
        
        # Update props with coerced values
        props['name'] = name
        props['title'] = props.get('title') or name
        props['route'] = route
        
        # Ensure content exists
        if 'content' not in props:
            props['content'] = f'<h1>{props["title"]}</h1><p>Content goes here.</p>'
        
        # Ensure consumes exists
        if 'consumes' not in props:
            props['consumes'] = {}
        
        # Ensure bind_table exists
        if 'bind_table' not in props:
            props['bind_table'] = None
        
        # Ensure bind_file_store exists
        if 'bind_file_store' not in props:
            props['bind_file_store'] = None
        
        # Ensure form exists
        if 'form' not in props:
            props['form'] = {'enabled': False, 'fields': []}
        
        # Ensure requires_auth exists
        if 'requires_auth' not in props:
            props['requires_auth'] = False
        
        # Ensure requires_subscription exists
        if 'requires_subscription' not in props:
            props['requires_subscription'] = False
    
    elif node.type == "rest_api":
        # Ensure required props exist
        if 'name' not in props:
            props['name'] = 'Api'
        if 'method' not in props:
            props['method'] = 'GET'
        if 'sample_response' not in props:
            props['sample_response'] = '{"ok": true}'
        
        # Ensure route exists
        if 'route' not in props:
            props['route'] = '/api/' + slugify(props.get('name', 'api'))
        
        # Ensure route starts with /api/
        if props['route'] and not props['route'].startswith('/api/'):
            if props['route'].startswith('/'):
                props['route'] = '/api' + props['route']
            else:
                props['route'] = '/api/' + props['route']
        
        # Ensure requires_auth exists
        if 'requires_auth' not in props:
            props['requires_auth'] = False
    
    elif node.type == "db_table":
        # Ensure name exists
        if 'name' not in props:
            props['name'] = 'table'
        
        # Ensure columns exist with defaults
        if 'columns' not in props or not props['columns']:
            props['columns'] = [
                {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                {"name": "title", "type": "TEXT"}
            ]
        
        # Ensure all columns have name and type
        for col in props['columns']:
            if 'name' not in col:
                col['name'] = 'column'
            if 'type' not in col:
                col['type'] = 'TEXT'
    
    elif node.type == "auth":
        # Ensure name exists
        if 'name' not in props:
            props['name'] = 'Auth'
        
        # Ensure strategy exists (jwt or session)
        if 'strategy' not in props:
            props['strategy'] = 'jwt'
        
        # Ensure roles exist with defaults
        if 'roles' not in props:
            props['roles'] = ['admin', 'user']
        
        # Ensure user_table exists
        if 'user_table' not in props:
            props['user_table'] = 'users'
        
        # Ensure user_columns exist with secure defaults
        if 'user_columns' not in props:
            props['user_columns'] = [
                {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                {"name": "email", "type": "TEXT UNIQUE NOT NULL"},
                {"name": "password_hash", "type": "TEXT NOT NULL"},
                {"name": "role", "type": "TEXT DEFAULT 'user'"},
                {"name": "subscription_plan", "type": "TEXT DEFAULT 'free'"},
                {"name": "subscription_status", "type": "TEXT DEFAULT 'trial'"},
                {"name": "trial_end", "type": "TEXT"},
                {"name": "created_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"},
                {"name": "updated_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"}
            ]
    
    elif node.type == "payment":
        # Ensure name exists
        if 'name' not in props:
            props['name'] = 'Payments'
        
        # Ensure provider exists
        if 'provider' not in props:
            props['provider'] = 'stripe'
        
        # Ensure plans exist with defaults
        if 'plans' not in props or not props['plans']:
            props['plans'] = [
                {"name": "Basic", "price": 9.99, "interval": "month"},
                {"name": "Pro", "price": 29.99, "interval": "month"},
                {"name": "Enterprise", "price": 99.99, "interval": "month"}
            ]
        
        # Ensure trial_days exists
        if 'trial_days' not in props:
            props['trial_days'] = 14
        
        # Ensure currency exists
        if 'currency' not in props:
            props['currency'] = 'usd'
    
    elif node.type == "file_store":
        # Ensure name exists
        if 'name' not in props:
            props['name'] = 'FileStore'
        
        # Ensure provider exists
        if 'provider' not in props:
            props['provider'] = 'local'
        
        # Ensure local_path exists
        if 'local_path' not in props:
            props['local_path'] = './instance/uploads'
        
        # Ensure allowed_types exists
        if 'allowed_types' not in props:
            props['allowed_types'] = ['*']
        
        # Ensure max_size_mb exists
        if 'max_size_mb' not in props:
            props['max_size_mb'] = 20
        
        # Ensure bucket exists (for future S3/GCS support)
        if 'bucket' not in props:
            props['bucket'] = None
    
    elif node.type == "agent_tool":
        if 'name' not in props:
            props['name'] = 'NewTool'
        if 'description' not in props:
            props['description'] = 'Agent tool description'
    
    return props

def normalize_state(state_data: Dict[str, Any]) -> BuilderState:
    """Normalize and validate builder state"""
    # Ensure arrays exist
    if 'nodes' not in state_data or state_data['nodes'] is None:
        state_data['nodes'] = []
    if 'edges' not in state_data or state_data['edges'] is None:
        state_data['edges'] = []
    if 'metadata' not in state_data or state_data['metadata'] is None:
        state_data['metadata'] = {}
    
    # Convert nodes to Node objects
    nodes = []
    for node_data in state_data.get('nodes', []):
        if isinstance(node_data, dict):
            nodes.append(Node(**node_data))
        else:
            nodes.append(node_data)
    
    # Convert edges to Edge objects
    edges = []
    for edge_data in state_data.get('edges', []):
        if isinstance(edge_data, dict):
            edges.append(Edge(**edge_data))
        else:
            edges.append(edge_data)
    
    return BuilderState(
        project_id=state_data['project_id'],
        version=state_data.get('version', 'v1'),
        nodes=nodes,
        edges=edges,
        metadata=state_data.get('metadata', {}),
        exists=state_data.get('exists', True)
    )

def validate_builder_state(data: Dict[str, Any]) -> BuilderState:
    """Validate and create BuilderState from dict"""
    try:
        return normalize_state(data)
    except KeyError as e:
        raise ValueError(f"Missing required field: {e}")
    except Exception as e:
        raise ValueError(f"Validation error: {e}")

def create_minimal_builder_state(project_id: str) -> BuilderState:
    """Create a minimal builder state with default scaffold"""
    return BuilderState(
        project_id=project_id,
        version="v1",
        nodes=[],
        edges=[],
        metadata={"created": "minimal_scaffold"},
        exists=False
    )

def create_hello_world_state(project_id: str) -> BuilderState:
    """Create a builder state for a 'Hello World' app"""
    hello_page_node = Node(
        id=str(uuid.uuid4()),
        type="ui_page",
        props={
            "name": "HelloPage",
            "route": "/hello-page",
            "title": "Hello World",
            "content": "<h1>Hello World!</h1><p>This is your first generated page.</p>"
        }
    )
    
    return BuilderState(
        project_id=project_id,
        version="v1",
        nodes=[hello_page_node],
        edges=[],
        metadata={"description": "A simple 'Hello World' UI page."},
        exists=True
    )
