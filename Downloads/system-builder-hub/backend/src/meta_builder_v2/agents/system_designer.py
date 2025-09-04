"""
System Designer Agent
Expands specifications into detailed system architecture and implementation plans.
"""

import json
import logging
from typing import Dict, Any, List
from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class SystemDesignerAgent(BaseAgent):
    """System Designer Agent - maps specifications to scaffold plans."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.architecture_patterns = self._load_architecture_patterns()
    
    def _load_architecture_patterns(self) -> Dict[str, Any]:
        """Load architecture patterns for different system types."""
        return {
            "web_app": {
                "frontend": ["React", "Vue", "Angular"],
                "backend": ["FastAPI", "Django", "Flask"],
                "database": ["PostgreSQL", "MySQL", "MongoDB"],
                "cache": ["Redis", "Memcached"],
                "queue": ["Celery", "RQ", "Bull"],
                "storage": ["S3", "GCS", "Azure Blob"],
                "monitoring": ["Prometheus", "Grafana", "Sentry"]
            },
            "api_service": {
                "framework": ["FastAPI", "Django REST", "Flask REST"],
                "database": ["PostgreSQL", "MySQL"],
                "cache": ["Redis"],
                "auth": ["JWT", "OAuth2", "API Keys"],
                "documentation": ["OpenAPI", "Swagger"],
                "testing": ["pytest", "unittest"]
            },
            "mobile_app": {
                "frontend": ["React Native", "Flutter", "Native iOS/Android"],
                "backend": ["FastAPI", "Node.js", "Firebase"],
                "database": ["PostgreSQL", "Firebase Firestore"],
                "push_notifications": ["FCM", "APNS"],
                "analytics": ["Mixpanel", "Amplitude", "Firebase Analytics"]
            }
        }
    
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute System Designer actions."""
        if action == "create_plan":
            return await self._create_plan(inputs)
        elif action == "expand_schemas":
            return await self._expand_schemas(inputs)
        elif action == "design_apis":
            return await self._design_apis(inputs)
        elif action == "plan_integrations":
            return await self._plan_integrations(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _create_plan(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comprehensive system plan from specification."""
        spec = inputs.get("spec", {})
        
        # Expand schemas
        schemas = await self._expand_schemas({"spec": spec})
        
        # Design APIs
        apis = await self._design_apis({"spec": spec, "schemas": schemas})
        
        # Plan integrations
        integrations = await self._plan_integrations({"spec": spec})
        
        # Design UI pages
        ui_pages = await self._design_ui_pages({"spec": spec, "apis": apis})
        
        # Plan infrastructure
        infrastructure = await self._plan_infrastructure({"spec": spec})
        
        # Create plan summary
        plan = {
            "database_schema": schemas["database_schema"],
            "api_endpoints": apis["endpoints"],
            "ui_pages": ui_pages["pages"],
            "integrations": integrations["integration_plans"],
            "infrastructure": infrastructure["infrastructure"],
            "security": schemas["security_plan"],
            "testing": self._create_testing_plan(spec),
            "deployment": infrastructure["deployment_plan"]
        }
        
        return {
            "plan": plan,
            "summary": self._generate_plan_summary(plan),
            "risk_assessment": self._assess_risks(plan),
            "estimated_effort": self._estimate_effort(plan)
        }
    
    async def _expand_schemas(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Expand entity schemas with detailed field definitions."""
        spec = inputs.get("spec", {})
        entities = spec.get("entities", [])
        
        expanded_schemas = []
        relationships = []
        
        for entity in entities:
            if isinstance(entity, str):
                entity = {"name": entity, "fields": []}
            expanded_entity = await self._expand_entity_schema(entity)
            expanded_schemas.append(expanded_entity)
            
            # Identify relationships
            entity_relationships = self._identify_relationships(entity, entities)
            relationships.extend(entity_relationships)
        
        # Create database schema
        database_schema = {
            "tables": expanded_schemas,
            "relationships": relationships,
            "indexes": self._generate_indexes(expanded_schemas),
            "constraints": self._generate_constraints(expanded_schemas, relationships)
        }
        
        # Security plan
        security_plan = self._create_security_plan(expanded_schemas, spec)
        
        return {
            "database_schema": database_schema,
            "security_plan": security_plan,
            "expanded_entities": expanded_schemas
        }
    
    async def _expand_entity_schema(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Expand a single entity schema with detailed field definitions."""
        entity_name = entity.get("name", "Unknown")
        fields = entity.get("fields", [])
        
        # Add standard fields
        standard_fields = [
            {"name": "id", "type": "uuid", "primary": True, "auto": True},
            {"name": "created_at", "type": "datetime", "auto": True},
            {"name": "updated_at", "type": "datetime", "auto": True}
        ]
        
        # Add tenant field if multi-tenant
        if entity.get("multi_tenant", True):
            standard_fields.append({"name": "tenant_id", "type": "uuid", "required": True})
        
        # Expand user-defined fields
        expanded_fields = []
        for field in fields:
            expanded_field = self._expand_field_definition(field)
            expanded_fields.append(expanded_field)
        
        all_fields = standard_fields + expanded_fields
        
        return {
            "name": entity_name,
            "table_name": self._to_snake_case(entity_name),
            "fields": all_fields,
            "description": entity.get("description", f"{entity_name} entity"),
            "multi_tenant": entity.get("multi_tenant", True),
            "audit_enabled": entity.get("audit_enabled", True)
        }
    
    def _expand_field_definition(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Expand field definition with additional properties."""
        field_type = field.get("type", "string")
        
        expanded_field = {
            "name": field["name"],
            "type": field_type,
            "required": field.get("required", False),
            "unique": field.get("unique", False),
            "indexed": field.get("indexed", False),
            "description": field.get("description", ""),
            "validation": field.get("validation", {}),
            "encrypted": field.get("encrypted", False)
        }
        
        # Add type-specific properties
        if field_type == "string":
            expanded_field["max_length"] = field.get("max_length", 255)
        elif field_type == "decimal":
            expanded_field["precision"] = field.get("precision", 10)
            expanded_field["scale"] = field.get("scale", 2)
        elif field_type == "enum":
            expanded_field["values"] = field.get("values", [])
        
        return expanded_field
    
    def _identify_relationships(self, entity: Dict[str, Any], all_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify relationships between entities."""
        relationships = []
        entity_name = entity.get("name", "")
        
        for field in entity.get("fields", []):
            if field.get("type") == "foreign_key":
                target_entity = field.get("target_entity", "")
                relationships.append({
                    "from_entity": entity_name,
                    "to_entity": target_entity,
                    "type": "many_to_one",
                    "field": field["name"],
                    "cascade": field.get("cascade", "restrict")
                })
        
        return relationships
    
    def _generate_indexes(self, schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate database indexes for performance."""
        indexes = []
        
        for schema in schemas:
            table_name = schema["table_name"]
            
            # Primary key index (usually automatic)
            indexes.append({
                "table": table_name,
                "name": f"idx_{table_name}_id",
                "columns": ["id"],
                "type": "btree",
                "unique": True
            })
            
            # Tenant index for multi-tenant tables
            if schema.get("multi_tenant", True):
                indexes.append({
                    "table": table_name,
                    "name": f"idx_{table_name}_tenant",
                    "columns": ["tenant_id"],
                    "type": "btree"
                })
            
            # Indexes for indexed fields
            for field in schema["fields"]:
                if field.get("indexed", False):
                    indexes.append({
                        "table": table_name,
                        "name": f"idx_{table_name}_{field['name']}",
                        "columns": [field["name"]],
                        "type": "btree"
                    })
        
        return indexes
    
    def _generate_constraints(self, schemas: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate database constraints."""
        constraints = []
        
        # Foreign key constraints
        for rel in relationships:
            constraints.append({
                "name": f"fk_{rel['from_entity']}_{rel['field']}",
                "type": "foreign_key",
                "table": self._to_snake_case(rel["from_entity"]),
                "column": rel["field"],
                "references": {
                    "table": self._to_snake_case(rel["to_entity"]),
                    "column": "id"
                },
                "on_delete": rel.get("cascade", "restrict")
            })
        
        return constraints
    
    async def _design_apis(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Design API endpoints based on entities and workflows."""
        spec = inputs.get("spec", {})
        schemas = inputs.get("schemas", {})
        entities = spec.get("entities", [])
        workflows = spec.get("workflows", [])
        
        endpoints = []
        
        # CRUD endpoints for each entity
        for entity in entities:
            if isinstance(entity, str):
                entity = {"name": entity, "fields": []}
            entity_endpoints = self._create_crud_endpoints(entity)
            endpoints.extend(entity_endpoints)
        
        # Workflow endpoints
        for workflow in workflows:
            if isinstance(workflow, str):
                workflow = {"name": workflow, "states": [], "transitions": []}
            workflow_endpoints = self._create_workflow_endpoints(workflow)
            endpoints.extend(workflow_endpoints)
        
        # Authentication endpoints
        auth_endpoints = self._create_auth_endpoints()
        endpoints.extend(auth_endpoints)
        
        # Integration endpoints
        integration_endpoints = self._create_integration_endpoints(spec.get("integrations", []))
        endpoints.extend(integration_endpoints)
        
        return {
            "endpoints": endpoints,
            "openapi_spec": self._generate_openapi_spec(endpoints),
            "rate_limits": self._define_rate_limits(endpoints)
        }
    
    def _create_crud_endpoints(self, entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create CRUD endpoints for an entity."""
        entity_name = entity.get("name", "")
        table_name = self._to_snake_case(entity_name)
        
        endpoints = [
            {
                "path": f"/api/{table_name}",
                "method": "GET",
                "operation": "list",
                "description": f"List {entity_name} records",
                "parameters": ["page", "limit", "sort", "filter"],
                "response": f"List[{entity_name}]",
                "auth_required": True
            },
            {
                "path": f"/api/{table_name}",
                "method": "POST",
                "operation": "create",
                "description": f"Create new {entity_name}",
                "parameters": [f"{entity_name}Create"],
                "response": entity_name,
                "auth_required": True
            },
            {
                "path": f"/api/{table_name}/{{id}}",
                "method": "GET",
                "operation": "read",
                "description": f"Get {entity_name} by ID",
                "parameters": ["id"],
                "response": entity_name,
                "auth_required": True
            },
            {
                "path": f"/api/{table_name}/{{id}}",
                "method": "PUT",
                "operation": "update",
                "description": f"Update {entity_name}",
                "parameters": ["id", f"{entity_name}Update"],
                "response": entity_name,
                "auth_required": True
            },
            {
                "path": f"/api/{table_name}/{{id}}",
                "method": "DELETE",
                "operation": "delete",
                "description": f"Delete {entity_name}",
                "parameters": ["id"],
                "response": "Success",
                "auth_required": True
            }
        ]
        
        return endpoints
    
    def _create_workflow_endpoints(self, workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create endpoints for workflow operations."""
        workflow_name = workflow.get("name", "")
        states = workflow.get("states", [])
        
        endpoints = [
            {
                "path": f"/api/workflows/{workflow_name}/{{id}}/transition",
                "method": "POST",
                "operation": "transition",
                "description": f"Transition {workflow_name} workflow",
                "parameters": ["id", "to_state", "data"],
                "response": "WorkflowState",
                "auth_required": True
            },
            {
                "path": f"/api/workflows/{workflow_name}/{{id}}/history",
                "method": "GET",
                "operation": "history",
                "description": f"Get {workflow_name} transition history",
                "parameters": ["id"],
                "response": "List[WorkflowTransition]",
                "auth_required": True
            }
        ]
        
        return endpoints
    
    def _create_auth_endpoints(self) -> List[Dict[str, Any]]:
        """Create authentication endpoints."""
        return [
            {
                "path": "/api/auth/login",
                "method": "POST",
                "operation": "login",
                "description": "User login",
                "parameters": ["LoginRequest"],
                "response": "LoginResponse",
                "auth_required": False
            },
            {
                "path": "/api/auth/logout",
                "method": "POST",
                "operation": "logout",
                "description": "User logout",
                "parameters": [],
                "response": "Success",
                "auth_required": True
            },
            {
                "path": "/api/auth/refresh",
                "method": "POST",
                "operation": "refresh",
                "description": "Refresh access token",
                "parameters": ["RefreshRequest"],
                "response": "LoginResponse",
                "auth_required": False
            }
        ]
    
    def _create_integration_endpoints(self, integrations: List[str]) -> List[Dict[str, Any]]:
        """Create endpoints for integrations."""
        endpoints = []
        
        for integration in integrations:
            if integration == "webhooks":
                endpoints.extend([
                    {
                        "path": "/api/webhooks/{provider}",
                        "method": "POST",
                        "operation": "webhook",
                        "description": f"Handle {integration} webhook",
                        "parameters": ["provider", "payload"],
                        "response": "Success",
                        "auth_required": False
                    }
                ])
        
        return endpoints
    
    async def _plan_integrations(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Plan integration implementations."""
        spec = inputs.get("spec", {})
        integrations = spec.get("integrations", [])
        
        integration_plans = {}
        
        for integration in integrations:
            plan = await self._plan_single_integration(integration, spec)
            integration_plans[integration] = plan
        
        return {
            "integration_plans": integration_plans,
            "dependencies": self._identify_integration_dependencies(integration_plans)
        }
    
    async def _plan_single_integration(self, integration: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Plan a single integration."""
        plans = {
            "stripe": {
                "type": "payment_processing",
                "config": ["api_key", "webhook_secret"],
                "endpoints": ["/api/payments/create", "/api/payments/webhook"],
                "models": ["Payment", "Subscription"],
                "dependencies": ["stripe-python"]
            },
            "email": {
                "type": "communication",
                "config": ["smtp_host", "smtp_port", "username", "password"],
                "endpoints": ["/api/email/send"],
                "models": ["EmailTemplate", "EmailLog"],
                "dependencies": ["fastapi-mail"]
            },
            "analytics": {
                "type": "tracking",
                "config": ["api_key", "endpoint"],
                "endpoints": ["/api/analytics/track"],
                "models": ["AnalyticsEvent"],
                "dependencies": ["analytics-python"]
            }
        }
        
        return plans.get(integration, {
            "type": "custom",
            "config": [],
            "endpoints": [],
            "models": [],
            "dependencies": []
        })
    
    async def _design_ui_pages(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Design UI pages based on entities and workflows."""
        spec = inputs.get("spec", {})
        apis = inputs.get("apis", {})
        entities = spec.get("entities", [])
        
        pages = []
        
        # Entity list pages
        for entity in entities:
            if isinstance(entity, str):
                entity = {"name": entity, "fields": []}
            pages.append({
                "name": f"{entity['name']}List",
                "path": f"/{self._to_kebab_case(entity['name'])}",
                "type": "list",
                "entity": entity["name"],
                "features": ["search", "filter", "sort", "pagination"]
            })
        
        # Entity detail pages
        for entity in entities:
            if isinstance(entity, str):
                entity = {"name": entity, "fields": []}
            pages.append({
                "name": f"{entity['name']}Detail",
                "path": f"/{self._to_kebab_case(entity['name'])}/{{id}}",
                "type": "detail",
                "entity": entity["name"],
                "features": ["view", "edit", "delete"]
            })
        
        # Dashboard
        pages.append({
            "name": "Dashboard",
            "path": "/dashboard",
            "type": "dashboard",
            "features": ["overview", "charts", "recent_activity"]
        })
        
        return {
            "pages": pages,
            "navigation": self._create_navigation(pages),
            "layouts": self._create_layouts(pages)
        }
    
    async def _plan_infrastructure(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Plan infrastructure requirements."""
        spec = inputs.get("spec", {})
        
        # Basic infrastructure
        infrastructure = {
            "compute": {
                "type": "container",
                "platform": "docker",
                "orchestration": "docker-compose"
            },
            "database": {
                "type": "postgresql",
                "version": "15",
                "backup": True
            },
            "cache": {
                "type": "redis",
                "version": "7"
            },
            "storage": {
                "type": "local",
                "backup": True
            },
            "monitoring": {
                "logs": "structured",
                "metrics": "prometheus",
                "tracing": "jaeger"
            }
        }
        
        # Deployment plan
        deployment_plan = {
            "environments": ["development", "staging", "production"],
            "ci_cd": "github_actions",
            "container_registry": "docker_hub",
            "monitoring": "prometheus_grafana"
        }
        
        return {
            "infrastructure": infrastructure,
            "deployment_plan": deployment_plan
        }
    
    def _create_security_plan(self, schemas: List[Dict[str, Any]], spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create security plan for the system."""
        return {
            "authentication": {
                "method": "jwt",
                "session_timeout": 3600,
                "refresh_tokens": True
            },
            "authorization": {
                "rbac": True,
                "permissions": ["read", "write", "delete", "admin"],
                "roles": ["user", "admin", "super_admin"]
            },
            "data_protection": {
                "encryption": "aes-256",
                "pii_handling": "masked",
                "audit_logging": True
            },
            "api_security": {
                "rate_limiting": True,
                "cors": True,
                "input_validation": True
            }
        }
    
    def _create_testing_plan(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Create testing plan."""
        return {
            "unit_tests": {
                "framework": "pytest",
                "coverage_target": 80,
                "entities": spec.get("entities", [])
            },
            "integration_tests": {
                "framework": "pytest",
                "api_testing": True,
                "database_testing": True
            },
            "e2e_tests": {
                "framework": "playwright",
                "browsers": ["chrome", "firefox"],
                "scenarios": ["user_flows", "critical_paths"]
            }
        }
    
    def _generate_plan_summary(self, plan: Dict[str, Any]) -> str:
        """Generate human-readable plan summary."""
        entities = len(plan["database_schema"]["tables"])
        endpoints = len(plan["api_endpoints"])
        pages = 0
        
        return f"System plan with {entities} entities, {endpoints} API endpoints, and {pages} UI pages"
    
    def _assess_risks(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risks in the system plan."""
        risks = []
        
        # Complexity risks
        if len(plan["database_schema"]["tables"]) > 20:
            risks.append({
                "type": "complexity",
                "severity": "medium",
                "description": "High number of entities may increase complexity"
            })
        
        # Security risks
        if not plan["security"]["authorization"]["rbac"]:
            risks.append({
                "type": "security",
                "severity": "high",
                "description": "No RBAC implementation"
            })
        
        return {
            "risks": risks,
            "overall_risk": "low" if not risks else "medium"
        }
    
    def _estimate_effort(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate development effort."""
        entities = len(plan["database_schema"]["tables"])
        endpoints = len(plan["api_endpoints"])
        pages = 0
        
        # Rough estimates (in hours)
        db_effort = entities * 2
        api_effort = endpoints * 1.5
        ui_effort = pages * 3
        testing_effort = (db_effort + api_effort + ui_effort) * 0.3
        
        total_effort = db_effort + api_effort + ui_effort + testing_effort
        
        return {
            "database": db_effort,
            "api": api_effort,
            "ui": ui_effort,
            "testing": testing_effort,
            "total": total_effort,
            "unit": "hours"
        }
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()
    
    def _to_kebab_case(self, text: str) -> str:
        """Convert text to kebab-case."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '-', text).lower()

    def _generate_openapi_spec(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate OpenAPI specification from endpoints."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Generated API", "version": "1.0.0"},
            "paths": {}
        }
    
    def _define_rate_limits(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Define rate limits for endpoints."""
        return {"default": {"requests": 100, "window": 60}}


    def _identify_integration_dependencies(self, integration_plans: Dict[str, Any]) -> List[str]:
        """Identify dependencies between integrations."""
        return []


    def _create_navigation(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create navigation structure from pages."""
        return {"main": [page["name"] for page in pages]}
    
    def _create_layouts(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create layout definitions for pages."""
        return {"default": {"header": True, "sidebar": True, "footer": True}}
    
    def _to_kebab_case(self, text: str) -> str:
        """Convert text to kebab case."""
        return text.lower().replace(" ", "-")

