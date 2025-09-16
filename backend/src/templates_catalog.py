"""
Templates Catalog - Seed templates for build wizard
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class Template:
    """Template definition"""
    slug: str
    name: str
    description: str
    category: str
    complexity: str  # simple, medium, complex
    estimated_time: str  # e.g., "5-10 minutes"
    blueprint: Dict[str, Any]
    canvas_layout: List[Dict[str, Any]]
    readme_snippet: str


# Seed templates
TEMPLATES: List[Template] = [
    Template(
        slug="crud-app",
        name="CRUD Application",
        description="Basic CRUD operations with database and REST API",
        category="web",
        complexity="simple",
        estimated_time="5-10 minutes",
        blueprint={
            "entities": [
                {
                    "name": "Item",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "name", "type": "string", "required": True},
                        {"name": "description", "type": "text"},
                        {"name": "created_at", "type": "datetime"},
                        {"name": "updated_at", "type": "datetime"}
                    ]
                }
            ],
            "endpoints": [
                {
                    "path": "/api/items",
                    "method": "GET",
                    "description": "List all items"
                },
                {
                    "path": "/api/items/{id}",
                    "method": "GET", 
                    "description": "Get item by ID"
                },
                {
                    "path": "/api/items",
                    "method": "POST",
                    "description": "Create new item"
                },
                {
                    "path": "/api/items/{id}",
                    "method": "PUT",
                    "description": "Update item"
                },
                {
                    "path": "/api/items/{id}",
                    "method": "DELETE",
                    "description": "Delete item"
                }
            ],
            "ui_pages": [
                {
                    "name": "Items List",
                    "route": "/items",
                    "type": "list",
                    "entity": "Item"
                },
                {
                    "name": "Item Detail",
                    "route": "/items/{id}",
                    "type": "detail",
                    "entity": "Item"
                },
                {
                    "name": "Create Item",
                    "route": "/items/new",
                    "type": "form",
                    "entity": "Item"
                }
            ]
        },
        canvas_layout=[
            {
                "id": "db-table",
                "type": "db_table",
                "name": "Items Table",
                "position": {"x": 100, "y": 100},
                "config": {"entity": "Item"}
            },
            {
                "id": "rest-api",
                "type": "rest_api",
                "name": "Items API",
                "position": {"x": 300, "y": 100},
                "config": {"entity": "Item"}
            },
            {
                "id": "ui-page",
                "type": "ui_page",
                "name": "Items UI",
                "position": {"x": 500, "y": 100},
                "config": {"entity": "Item"}
            }
        ],
        readme_snippet="""
# CRUD Application

A simple CRUD application with:
- Database table for items
- REST API endpoints
- Web UI for management

## Quick Start
1. The system is ready to run
2. Access the UI at `/items`
3. Create, read, update, and delete items
        """
    ),
    
    Template(
        slug="dashboard-db",
        name="Dashboard + Database",
        description="Analytics dashboard with database backend",
        category="analytics",
        complexity="medium",
        estimated_time="10-15 minutes",
        blueprint={
            "entities": [
                {
                    "name": "Metric",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "name", "type": "string", "required": True},
                        {"name": "value", "type": "float", "required": True},
                        {"name": "category", "type": "string"},
                        {"name": "timestamp", "type": "datetime"}
                    ]
                }
            ],
            "endpoints": [
                {
                    "path": "/api/metrics",
                    "method": "GET",
                    "description": "Get metrics with filtering"
                },
                {
                    "path": "/api/metrics/summary",
                    "method": "GET",
                    "description": "Get metrics summary"
                }
            ],
            "ui_pages": [
                {
                    "name": "Dashboard",
                    "route": "/dashboard",
                    "type": "dashboard",
                    "components": ["chart", "metrics", "table"]
                }
            ]
        },
        canvas_layout=[
            {
                "id": "db-table",
                "type": "db_table",
                "name": "Metrics Table",
                "position": {"x": 100, "y": 100},
                "config": {"entity": "Metric"}
            },
            {
                "id": "rest-api",
                "type": "rest_api",
                "name": "Metrics API",
                "position": {"x": 300, "y": 100},
                "config": {"entity": "Metric"}
            },
            {
                "id": "ui-dashboard",
                "type": "ui_page",
                "name": "Analytics Dashboard",
                "position": {"x": 500, "y": 100},
                "config": {"type": "dashboard"}
            }
        ],
        readme_snippet="""
# Dashboard + Database

An analytics dashboard with:
- Metrics database table
- REST API for data access
- Interactive dashboard UI

## Quick Start
1. Add metrics via API
2. View dashboard at `/dashboard`
3. Monitor real-time analytics
        """
    ),
    
    Template(
        slug="rest-api-ui",
        name="REST API + UI",
        description="Complete REST API with modern web interface",
        category="web",
        complexity="medium",
        estimated_time="10-15 minutes",
        blueprint={
            "entities": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "email", "type": "string", "required": True},
                        {"name": "name", "type": "string", "required": True},
                        {"name": "role", "type": "string", "default": "user"}
                    ]
                }
            ],
            "endpoints": [
                {
                    "path": "/api/users",
                    "method": "GET",
                    "description": "List users"
                },
                {
                    "path": "/api/users/{id}",
                    "method": "GET",
                    "description": "Get user"
                },
                {
                    "path": "/api/users",
                    "method": "POST",
                    "description": "Create user"
                }
            ],
            "ui_pages": [
                {
                    "name": "User Management",
                    "route": "/users",
                    "type": "management",
                    "entity": "User"
                }
            ]
        },
        canvas_layout=[
            {
                "id": "auth",
                "type": "auth",
                "name": "Authentication",
                "position": {"x": 100, "y": 100},
                "config": {"type": "jwt"}
            },
            {
                "id": "rest-api",
                "type": "rest_api",
                "name": "Users API",
                "position": {"x": 300, "y": 100},
                "config": {"entity": "User"}
            },
            {
                "id": "ui-page",
                "type": "ui_page",
                "name": "User Management UI",
                "position": {"x": 500, "y": 100},
                "config": {"entity": "User"}
            }
        ],
        readme_snippet="""
# REST API + UI

A complete web application with:
- JWT authentication
- REST API endpoints
- Modern web interface

## Quick Start
1. Register/login via UI
2. Manage users through API
3. Access protected endpoints
        """
    ),
    
    Template(
        slug="rag-bot",
        name="RAG Bot",
        description="Retrieval-Augmented Generation chatbot",
        category="ai",
        complexity="medium",
        estimated_time="15-20 minutes",
        blueprint={
            "entities": [
                {
                    "name": "Document",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "title", "type": "string", "required": True},
                        {"name": "content", "type": "text", "required": True},
                        {"name": "embedding", "type": "vector"}
                    ]
                },
                {
                    "name": "Conversation",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "user_id", "type": "uuid"},
                        {"name": "messages", "type": "json"}
                    ]
                }
            ],
            "endpoints": [
                {
                    "path": "/api/chat",
                    "method": "POST",
                    "description": "Chat with RAG bot"
                },
                {
                    "path": "/api/documents",
                    "method": "POST",
                    "description": "Add document to knowledge base"
                }
            ],
            "ui_pages": [
                {
                    "name": "Chat Interface",
                    "route": "/chat",
                    "type": "chat",
                    "components": ["chat_window", "document_upload"]
                }
            ]
        },
        canvas_layout=[
            {
                "id": "db-table",
                "type": "db_table",
                "name": "Documents & Conversations",
                "position": {"x": 100, "y": 100},
                "config": {"entities": ["Document", "Conversation"]}
            },
            {
                "id": "agent-tool",
                "type": "agent_tool",
                "name": "RAG Agent",
                "position": {"x": 300, "y": 100},
                "config": {"type": "rag", "model": "gpt-4"}
            },
            {
                "id": "ui-chat",
                "type": "ui_page",
                "name": "Chat Interface",
                "position": {"x": 500, "y": 100},
                "config": {"type": "chat"}
            }
        ],
        readme_snippet="""
# RAG Bot

An intelligent chatbot with:
- Document knowledge base
- Vector embeddings
- Conversational AI

## Quick Start
1. Upload documents to knowledge base
2. Start chatting at `/chat`
3. Get AI-powered responses
        """
    ),
    
    Template(
        slug="streamlit-fastapi",
        name="Streamlit + FastAPI",
        description="Data science app with Streamlit frontend and FastAPI backend",
        category="data",
        complexity="medium",
        estimated_time="10-15 minutes",
        blueprint={
            "entities": [
                {
                    "name": "Dataset",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "name", "type": "string", "required": True},
                        {"name": "data", "type": "json"},
                        {"name": "metadata", "type": "json"}
                    ]
                }
            ],
            "endpoints": [
                {
                    "path": "/api/datasets",
                    "method": "GET",
                    "description": "List datasets"
                },
                {
                    "path": "/api/datasets/{id}/analyze",
                    "method": "POST",
                    "description": "Analyze dataset"
                }
            ],
            "ui_pages": [
                {
                    "name": "Data Explorer",
                    "route": "/explorer",
                    "type": "streamlit",
                    "components": ["data_upload", "charts", "analysis"]
                }
            ]
        },
        canvas_layout=[
            {
                "id": "db-table",
                "type": "db_table",
                "name": "Datasets",
                "position": {"x": 100, "y": 100},
                "config": {"entity": "Dataset"}
            },
            {
                "id": "rest-api",
                "type": "rest_api",
                "name": "Data API",
                "position": {"x": 300, "y": 100},
                "config": {"entity": "Dataset"}
            },
            {
                "id": "ui-streamlit",
                "type": "ui_page",
                "name": "Streamlit App",
                "position": {"x": 500, "y": 100},
                "config": {"type": "streamlit"}
            }
        ],
        readme_snippet="""
# Streamlit + FastAPI

A data science application with:
- Dataset storage
- FastAPI backend
- Streamlit frontend

## Quick Start
1. Upload datasets via API
2. Explore data at `/explorer`
3. Run analysis and visualizations
        """
    ),
    
    Template(
        slug="agent-tool",
        name="Agent Tool",
        description="AI agent with custom tools and capabilities",
        category="ai",
        complexity="complex",
        estimated_time="20-30 minutes",
        blueprint={
            "entities": [
                {
                    "name": "Tool",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "name", "type": "string", "required": True},
                        {"name": "description", "type": "text"},
                        {"name": "function", "type": "text"},
                        {"name": "enabled", "type": "boolean", "default": True}
                    ]
                },
                {
                    "name": "AgentSession",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "agent_id", "type": "uuid"},
                        {"name": "tools_used", "type": "json"},
                        {"name": "conversation", "type": "json"}
                    ]
                }
            ],
            "endpoints": [
                {
                    "path": "/api/agent/chat",
                    "method": "POST",
                    "description": "Chat with agent"
                },
                {
                    "path": "/api/tools",
                    "method": "GET",
                    "description": "List available tools"
                }
            ],
            "ui_pages": [
                {
                    "name": "Agent Console",
                    "route": "/agent",
                    "type": "console",
                    "components": ["chat", "tools", "logs"]
                }
            ]
        },
        canvas_layout=[
            {
                "id": "db-table",
                "type": "db_table",
                "name": "Tools & Sessions",
                "position": {"x": 100, "y": 100},
                "config": {"entities": ["Tool", "AgentSession"]}
            },
            {
                "id": "agent-tool",
                "type": "agent_tool",
                "name": "AI Agent",
                "position": {"x": 300, "y": 100},
                "config": {"type": "agent", "model": "gpt-4", "tools": True}
            },
            {
                "id": "ui-console",
                "type": "ui_page",
                "name": "Agent Console",
                "position": {"x": 500, "y": 100},
                "config": {"type": "console"}
            }
        ],
        readme_snippet="""
# Agent Tool

An AI agent system with:
- Custom tool definitions
- Agent sessions
- Interactive console

## Quick Start
1. Define custom tools
2. Start agent session at `/agent`
3. Interact with AI agent
        """
    )
]


def get_template_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Get template by slug"""
    for template in TEMPLATES:
        if template.slug == slug:
            return {
                'slug': template.slug,
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'complexity': template.complexity,
                'estimated_time': template.estimated_time,
                'blueprint': template.blueprint,
                'canvas_layout': template.canvas_layout,
                'readme_snippet': template.readme_snippet
            }
    return None


def get_templates_by_category(category: str) -> List[Dict[str, Any]]:
    """Get templates by category"""
    return [
        {
            'slug': template.slug,
            'name': template.name,
            'description': template.description,
            'category': template.category,
            'complexity': template.complexity,
            'estimated_time': template.estimated_time
        }
        for template in TEMPLATES
        if template.category == category
    ]
