#!/usr/bin/env python3
"""
OpenAPI/Swagger Documentation System
Automatic API documentation generation with schema validation and interactive UI.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from flask import Blueprint, jsonify, render_template_string, request, current_app
import logging

logger = logging.getLogger(__name__)

# OpenAPI 3.0.3 specification
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "System Builder Hub API",
        "description": "Comprehensive API for the System Builder Hub platform with 29 priority modules",
        "version": "3.0.0",
        "contact": {
            "name": "System Builder Hub Team",
            "url": "https://system-builder-hub.com"
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
    },
    "servers": [
        {
            "url": "http://localhost:5001",
            "description": "Development server"
        },
        {
            "url": "https://api.system-builder-hub.com",
            "description": "Production server"
        }
    ],
    "paths": {},
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token for API authentication"
            }
        },
        "schemas": {
            "Error": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Error message"
                    },
                    "request_id": {
                        "type": "string",
                        "description": "Request ID for tracing"
                    }
                },
                "required": ["error"]
            },
            "Success": {
                "type": "object",
                "properties": {
                    "success": {
                        "type": "boolean",
                        "description": "Success status"
                    },
                    "message": {
                        "type": "string",
                        "description": "Success message"
                    },
                    "request_id": {
                        "type": "string",
                        "description": "Request ID for tracing"
                    }
                },
                "required": ["success"]
            },
            "HealthStatus": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["healthy", "unhealthy"],
                        "description": "Health status"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Health check timestamp"
                    }
                },
                "required": ["status"]
            },
            "TemplateGeneration": {
                "type": "object",
                "properties": {
                    "logic_text": {
                        "type": "string",
                        "description": "Logic text for template generation"
                    }
                },
                "required": ["logic_text"]
            },
            "TemplateResponse": {
                "type": "object",
                "properties": {
                    "success": {
                        "type": "boolean"
                    },
                    "template_id": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "confidence_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "request_id": {
                        "type": "string"
                    }
                },
                "required": ["success", "template_id", "confidence_score"]
            },
            "ProjectLoad": {
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Path to the project to load"
                    }
                },
                "required": ["project_path"]
            },
            "ProjectResponse": {
                "type": "object",
                "properties": {
                    "success": {
                        "type": "boolean"
                    },
                    "system_id": {
                        "type": "string",
                        "format": "uuid"
                    },
                    "message": {
                        "type": "string"
                    },
                    "request_id": {
                        "type": "string"
                    }
                },
                "required": ["success", "system_id", "message"]
            },
            "ClientProfile": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string"
                    },
                    "stage": {
                        "type": "string",
                        "enum": ["new", "active", "power_user", "churned"]
                    },
                    "satisfaction_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "churn_risk_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "request_id": {
                        "type": "string"
                    }
                },
                "required": ["user_id", "stage", "satisfaction_score", "churn_risk_score"]
            }
        }
    },
    "security": [
        {
            "bearerAuth": []
        }
    ],
    "tags": [
        {
            "name": "Health",
            "description": "Health check and monitoring endpoints"
        },
        {
            "name": "Core",
            "description": "Core infrastructure endpoints (P1-P10)"
        },
        {
            "name": "Advanced",
            "description": "Advanced features endpoints (P11-P20)"
        },
        {
            "name": "Intelligence",
            "description": "Intelligence and diagnostics endpoints (P21-P29)"
        }
    ]
}

# API endpoint definitions
API_ENDPOINTS = {
    # Health endpoints
    "/healthz": {
        "get": {
            "tags": ["Health"],
            "summary": "Kubernetes health check",
            "description": "Health check endpoint for Kubernetes probes",
            "responses": {
                "200": {
                    "description": "Service is healthy",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/HealthStatus"
                            }
                        }
                    }
                }
            }
        }
    },
    "/readiness": {
        "get": {
            "tags": ["Health"],
            "summary": "Kubernetes readiness probe",
            "description": "Readiness probe endpoint for Kubernetes",
            "responses": {
                "200": {
                    "description": "Service is ready",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/HealthStatus"
                            }
                        }
                    }
                }
            }
        }
    },
    "/liveness": {
        "get": {
            "tags": ["Health"],
            "summary": "Kubernetes liveness probe",
            "description": "Liveness probe endpoint for Kubernetes",
            "responses": {
                "200": {
                    "description": "Service is alive",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/HealthStatus"
                            }
                        }
                    }
                }
            }
        }
    },
    "/version": {
        "get": {
            "tags": ["Health"],
            "summary": "Version information",
            "description": "Get application version and build information",
            "responses": {
                "200": {
                    "description": "Version information",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "version": {"type": "string"},
                                    "build": {"type": "string"},
                                    "priorities": {"type": "string"},
                                    "status": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "/metrics": {
        "get": {
            "tags": ["Health"],
            "summary": "Prometheus metrics",
            "description": "Prometheus-compatible metrics endpoint",
            "responses": {
                "200": {
                    "description": "Prometheus metrics",
                    "content": {
                        "text/plain": {
                            "schema": {
                                "type": "string"
                            }
                        }
                    }
                }
            }
        }
    },
    
    # Core endpoints
    "/api/v1/core/health": {
        "get": {
            "tags": ["Core"],
            "summary": "Core infrastructure health",
            "description": "Health check for core infrastructure components",
            "security": [{"bearerAuth": []}],
            "responses": {
                "200": {
                    "description": "Core infrastructure status",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "message": {"type": "string"},
                                    "priority": {"type": "string"},
                                    "timestamp": {"type": "string", "format": "date-time"},
                                    "request_id": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                }
            }
        }
    },
    "/api/v1/core/llm/status": {
        "get": {
            "tags": ["Core"],
            "summary": "LLM system status",
            "description": "Get status of LLM components",
            "security": [{"bearerAuth": []}],
            "responses": {
                "200": {
                    "description": "LLM system status",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "llm_manager": {"type": "string"},
                                    "llm_factory": {"type": "string"},
                                    "tenant_llm_manager": {"type": "string"},
                                    "federated_finetune": {"type": "string"},
                                    "request_id": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                }
            }
        }
    },
    "/api/v1/core/projects/load": {
        "post": {
            "tags": ["Core"],
            "summary": "Load existing project",
            "description": "Load an existing project into the system",
            "security": [{"bearerAuth": []}],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ProjectLoad"}
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Project loaded successfully",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProjectResponse"}
                        }
                    }
                },
                "400": {
                    "description": "Bad request",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "403": {
                    "description": "Forbidden",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                }
            }
        }
    },
    
    # Advanced endpoints
    "/api/v1/advanced/templates/generate": {
        "post": {
            "tags": ["Advanced"],
            "summary": "Generate template",
            "description": "Generate a template from memory content",
            "security": [{"bearerAuth": []}],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/TemplateGeneration"}
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Template generated successfully",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TemplateResponse"}
                        }
                    }
                },
                "400": {
                    "description": "Bad request",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "403": {
                    "description": "Forbidden",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "429": {
                    "description": "Rate limit exceeded",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                }
            }
        }
    },
    
    # Intelligence endpoints
    "/api/v1/intelligence/client-success/profile/{user_id}": {
        "get": {
            "tags": ["Intelligence"],
            "summary": "Get client profile",
            "description": "Get client success profile and metrics",
            "security": [{"bearerAuth": []}],
            "parameters": [
                {
                    "name": "user_id",
                    "in": "path",
                    "required": True,
                    "schema": {
                        "type": "string"
                    },
                    "description": "User ID"
                }
            ],
            "responses": {
                "200": {
                    "description": "Client profile",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ClientProfile"}
                        }
                    }
                },
                "401": {
                    "description": "Unauthorized",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                },
                "404": {
                    "description": "User not found",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    }
                }
            }
        }
    }
}

# Swagger UI HTML template
SWAGGER_UI_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Builder Hub API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin:0;
            background: #fafafa;
        }
        .swagger-ui .topbar {
            background-color: #2c3e50;
        }
        .swagger-ui .topbar .download-url-wrapper .select-label {
            color: #fff;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: '/openapi.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
                oauth2RedirectUrl: window.location.origin + '/swagger-ui/oauth2-redirect.html'
            });
        };
    </script>
</body>
</html>
"""

def generate_openapi_spec() -> Dict[str, Any]:
    """Generate the complete OpenAPI specification"""
    spec = OPENAPI_SPEC.copy()
    spec["paths"] = API_ENDPOINTS.copy()
    return spec

def create_openapi_blueprint() -> Blueprint:
    """Create Flask blueprint for OpenAPI endpoints"""
    openapi_bp = Blueprint('openapi', __name__)
    
    @openapi_bp.route('/openapi.json')
    def openapi_spec():
        """Serve OpenAPI specification"""
        return jsonify(generate_openapi_spec())
    
    @openapi_bp.route('/docs')
    def swagger_ui():
        """Serve Swagger UI"""
        return render_template_string(SWAGGER_UI_TEMPLATE)
    
    @openapi_bp.route('/docs/')
    def swagger_ui_redirect():
        """Redirect /docs/ to /docs"""
        return render_template_string(SWAGGER_UI_TEMPLATE)
    
    return openapi_bp

# Schema validation decorator
def validate_schema(schema_name: str):
    """Decorator to validate request/response against OpenAPI schemas"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            # TODO: Implement schema validation
            # For now, just pass through
            return f(*args, **kwargs)
        return wrapper
    return decorator

# OpenAPI blueprint instance
openapi_blueprint = create_openapi_blueprint()
