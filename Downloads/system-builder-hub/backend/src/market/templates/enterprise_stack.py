"""
Enterprise Stack Template
"""
import json
from typing import Dict, Any, List
from src.market.models import Template, TemplateVariant, TemplateGuidedSchema, TemplateBuilderState

def create_enterprise_stack_template() -> Template:
    """Create the Enterprise Stack template"""
    
    # Guided Prompt schema
    guided_schema = {
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "title": "Company Name",
                "description": "Your company or organization name",
                "default": "Acme Corp",
                "minLength": 2,
                "maxLength": 100
            },
            "primary_color": {
                "type": "string",
                "title": "Primary Brand Color",
                "description": "Primary color for your brand (hex code)",
                "default": "#3B82F6",
                "pattern": "^#[0-9A-Fa-f]{6}$"
            },
            "enable_custom_domains": {
                "type": "boolean",
                "title": "Enable Custom Domains",
                "description": "Allow customers to use their own domains",
                "default": False
            },
            "plans": {
                "type": "array",
                "title": "Subscription Plans",
                "description": "Define your subscription tiers",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "price": {"type": "number"},
                        "features": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["id", "name", "price", "features"]
                },
                "default": [
                    {
                        "id": "basic",
                        "name": "Basic",
                        "price": 29,
                        "features": [
                            "Up to 10 projects",
                            "Basic analytics",
                            "Email support"
                        ]
                    },
                    {
                        "id": "pro",
                        "name": "Pro",
                        "price": 99,
                        "features": [
                            "Unlimited projects",
                            "Advanced analytics",
                            "Custom domains",
                            "Priority support",
                            "API access"
                        ]
                    },
                    {
                        "id": "enterprise",
                        "name": "Enterprise",
                        "price": 299,
                        "features": [
                            "Everything in Pro",
                            "SSO integration",
                            "Dedicated support",
                            "Custom integrations",
                            "Advanced security"
                        ]
                    }
                ]
            },
            "demo_seed": {
                "type": "boolean",
                "title": "Seed Demo Data",
                "description": "Create sample projects and tasks for demonstration",
                "default": True
            },
            "demo_tenant_slug": {
                "type": "string",
                "title": "Demo Tenant Slug",
                "description": "Slug for the demo tenant (if demo_seed is enabled)",
                "default": "acme",
                "pattern": "^[a-z0-9-]+$"
            }
        },
        "required": ["company_name", "primary_color"]
    }
    
    # Builder State template
    builder_state = {
        "name": "Enterprise Stack",
        "description": "Multi-tenant SaaS with Auth, Subscriptions, Files, CRUD, Analytics, and Custom Domains",
        "version": "1.0.0",
        "models": {
            "auth": {
                "type": "auth",
                "provider": "jwt",
                "config": {
                    "session_duration": 86400,
                    "refresh_tokens": True,
                    "password_policy": {
                        "min_length": 8,
                        "require_uppercase": True,
                        "require_numbers": True
                    }
                }
            },
            "payment": {
                "type": "payment",
                "provider": "stripe",
                "config": {
                    "webhook_endpoint": "/api/webhooks/stripe",
                    "subscription_management": True,
                    "usage_billing": False
                }
            },
            "file_store": {
                "type": "file_store",
                "provider": "s3",
                "config": {
                    "bucket_name": "{{tenant_slug}}-files",
                    "region": "us-east-1",
                    "public_read": False,
                    "max_file_size": 10485760
                }
            }
        },
        "database": {
            "tables": [
                {
                    "name": "accounts",
                    "columns": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "name", "type": "varchar(255)", "nullable": False},
                        {"name": "slug", "type": "varchar(100)", "nullable": False, "unique": True},
                        {"name": "plan", "type": "varchar(50)", "nullable": False, "default": "basic"},
                        {"name": "custom_domain", "type": "varchar(255)", "nullable": True},
                        {"name": "created_at", "type": "timestamp", "nullable": False, "default": "now()"},
                        {"name": "updated_at", "type": "timestamp", "nullable": False, "default": "now()"}
                    ],
                    "indexes": [
                        {"name": "idx_accounts_slug", "columns": ["slug"]},
                        {"name": "idx_accounts_plan", "columns": ["plan"]}
                    ]
                },
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "account_id", "type": "uuid", "nullable": False},
                        {"name": "email", "type": "varchar(255)", "nullable": False, "unique": True},
                        {"name": "password_hash", "type": "varchar(255)", "nullable": False},
                        {"name": "first_name", "type": "varchar(100)", "nullable": True},
                        {"name": "last_name", "type": "varchar(100)", "nullable": True},
                        {"name": "role", "type": "varchar(50)", "nullable": False, "default": "user"},
                        {"name": "is_active", "type": "boolean", "nullable": False, "default": True},
                        {"name": "created_at", "type": "timestamp", "nullable": False, "default": "now()"},
                        {"name": "updated_at", "type": "timestamp", "nullable": False, "default": "now()"}
                    ],
                    "indexes": [
                        {"name": "idx_users_account_id", "columns": ["account_id"]},
                        {"name": "idx_users_email", "columns": ["email"]},
                        {"name": "idx_users_role", "columns": ["role"]}
                    ],
                    "foreign_keys": [
                        {
                            "name": "fk_users_account_id",
                            "columns": ["account_id"],
                            "references": {"table": "accounts", "columns": ["id"]},
                            "on_delete": "cascade"
                        }
                    ]
                },
                {
                    "name": "projects",
                    "columns": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "account_id", "type": "uuid", "nullable": False},
                        {"name": "name", "type": "varchar(255)", "nullable": False},
                        {"name": "description", "type": "text", "nullable": True},
                        {"name": "status", "type": "varchar(50)", "nullable": False, "default": "active"},
                        {"name": "created_by", "type": "uuid", "nullable": False},
                        {"name": "created_at", "type": "timestamp", "nullable": False, "default": "now()"},
                        {"name": "updated_at", "type": "timestamp", "nullable": False, "default": "now()"}
                    ],
                    "indexes": [
                        {"name": "idx_projects_account_id", "columns": ["account_id"]},
                        {"name": "idx_projects_status", "columns": ["status"]},
                        {"name": "idx_projects_created_by", "columns": ["created_by"]}
                    ],
                    "foreign_keys": [
                        {
                            "name": "fk_projects_account_id",
                            "columns": ["account_id"],
                            "references": {"table": "accounts", "columns": ["id"]},
                            "on_delete": "cascade"
                        },
                        {
                            "name": "fk_projects_created_by",
                            "columns": ["created_by"],
                            "references": {"table": "users", "columns": ["id"]},
                            "on_delete": "cascade"
                        }
                    ]
                },
                {
                    "name": "tasks",
                    "columns": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "project_id", "type": "uuid", "nullable": False},
                        {"name": "title", "type": "varchar(255)", "nullable": False},
                        {"name": "description", "type": "text", "nullable": True},
                        {"name": "status", "type": "varchar(50)", "nullable": False, "default": "todo"},
                        {"name": "priority", "type": "varchar(20)", "nullable": False, "default": "medium"},
                        {"name": "assigned_to", "type": "uuid", "nullable": True},
                        {"name": "due_date", "type": "timestamp", "nullable": True},
                        {"name": "created_by", "type": "uuid", "nullable": False},
                        {"name": "created_at", "type": "timestamp", "nullable": False, "default": "now()"},
                        {"name": "updated_at", "type": "timestamp", "nullable": False, "default": "now()"}
                    ],
                    "indexes": [
                        {"name": "idx_tasks_project_id", "columns": ["project_id"]},
                        {"name": "idx_tasks_status", "columns": ["status"]},
                        {"name": "idx_tasks_priority", "columns": ["priority"]},
                        {"name": "idx_tasks_assigned_to", "columns": ["assigned_to"]},
                        {"name": "idx_tasks_due_date", "columns": ["due_date"]}
                    ],
                    "foreign_keys": [
                        {
                            "name": "fk_tasks_project_id",
                            "columns": ["project_id"],
                            "references": {"table": "projects", "columns": ["id"]},
                            "on_delete": "cascade"
                        },
                        {
                            "name": "fk_tasks_assigned_to",
                            "columns": ["assigned_to"],
                            "references": {"table": "users", "columns": ["id"]},
                            "on_delete": "set null"
                        },
                        {
                            "name": "fk_tasks_created_by",
                            "columns": ["created_by"],
                            "references": {"table": "users", "columns": ["id"]},
                            "on_delete": "cascade"
                        }
                    ]
                }
            ]
        },
        "apis": [
            {
                "name": "projects_api",
                "path": "/api/projects",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "table": "projects",
                "auth_required": True,
                "subscription_required": True
            },
            {
                "name": "tasks_api",
                "path": "/api/tasks",
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "table": "tasks",
                "auth_required": True,
                "subscription_required": True
            },
            {
                "name": "users_api",
                "path": "/api/users",
                "method": ["GET", "PUT"],
                "table": "users",
                "auth_required": True,
                "subscription_required": False
            }
        ],
        "pages": [
            {
                "name": "login",
                "path": "/ui/login",
                "template": "auth/login.html",
                "auth_required": False,
                "subscription_required": False
            },
            {
                "name": "register",
                "path": "/ui/register",
                "template": "auth/register.html",
                "auth_required": False,
                "subscription_required": False
            },
            {
                "name": "dashboard",
                "path": "/ui/dashboard",
                "template": "dashboard/index.html",
                "auth_required": True,
                "subscription_required": True
            },
            {
                "name": "projects",
                "path": "/ui/projects",
                "template": "projects/index.html",
                "auth_required": True,
                "subscription_required": True,
                "table": "projects"
            },
            {
                "name": "tasks",
                "path": "/ui/tasks",
                "template": "tasks/index.html",
                "auth_required": True,
                "subscription_required": True,
                "table": "tasks"
            },
            {
                "name": "files",
                "path": "/ui/files",
                "template": "files/index.html",
                "auth_required": True,
                "subscription_required": True,
                "file_store": "file_store"
            },
            {
                "name": "billing",
                "path": "/ui/billing",
                "template": "billing/index.html",
                "auth_required": True,
                "subscription_required": False
            },
            {
                "name": "admin_analytics",
                "path": "/ui/admin/analytics",
                "template": "admin/analytics.html",
                "auth_required": True,
                "subscription_required": True,
                "role_required": "admin"
            },
            {
                "name": "admin_domains",
                "path": "/ui/admin/domains",
                "template": "admin/domains.html",
                "auth_required": True,
                "subscription_required": True,
                "role_required": "admin"
            },
            {
                "name": "admin_integrations",
                "path": "/ui/admin/integrations",
                "template": "admin/integrations.html",
                "auth_required": True,
                "subscription_required": True,
                "role_required": "admin"
            }
        ],
        "webhooks": [
            {
                "name": "stripe_webhook",
                "path": "/api/webhooks/stripe",
                "provider": "stripe",
                "events": ["customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"]
            }
        ],
        "email_templates": [
            {
                "name": "welcome",
                "subject": "Welcome to {{company_name}}",
                "template": "emails/welcome.html"
            },
            {
                "name": "subscription_created",
                "subject": "Your subscription is active",
                "template": "emails/subscription_created.html"
            },
            {
                "name": "subscription_updated",
                "subject": "Your subscription has been updated",
                "template": "emails/subscription_updated.html"
            }
        ],
        "feature_flags": {
            "custom_domains": "{{enable_custom_domains}}",
            "advanced_analytics": "pro",
            "api_access": "pro",
            "sso_integration": "enterprise",
            "dedicated_support": "enterprise"
        }
    }
    
    # Create template
    template = Template(
        slug="enterprise-stack",
        title="Enterprise Stack",
        description="Complete multi-tenant SaaS with Auth, Subscriptions, Files, CRUD, Analytics, and Custom Domains",
        category="enterprise",
        tags=["saas", "multi-tenant", "auth", "subscriptions", "analytics"],
        is_published=True,
        is_featured=True,
        subscription_required="pro"
    )
    
    # Create guided schema
    guided_schema_obj = TemplateGuidedSchema(
        schema=guided_schema,
        examples=[
            {
                "company_name": "TechCorp Inc",
                "primary_color": "#10B981",
                "enable_custom_domains": True,
                "demo_seed": True,
                "demo_tenant_slug": "techcorp"
            },
            {
                "company_name": "StartupXYZ",
                "primary_color": "#8B5CF6",
                "enable_custom_domains": False,
                "demo_seed": True,
                "demo_tenant_slug": "startupxyz"
            }
        ]
    )
    
    # Create builder state
    builder_state_obj = TemplateBuilderState(
        state=builder_state,
        placeholders={
            "company_name": "{{company_name}}",
            "primary_color": "{{primary_color}}",
            "enable_custom_domains": "{{enable_custom_domains}}",
            "demo_seed": "{{demo_seed}}",
            "demo_tenant_slug": "{{demo_tenant_slug}}"
        }
    )
    
    # Create variant
    variant = TemplateVariant(
        name="default",
        description="Standard Enterprise Stack with all features",
        guided_schema=guided_schema_obj,
        builder_state=builder_state_obj
    )
    
    template.variants = [variant]
    
    return template
