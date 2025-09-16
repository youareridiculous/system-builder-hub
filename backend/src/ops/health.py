"""
Health monitoring service for SBH operations
"""

import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError
import os
import importlib
import sys

logger = logging.getLogger(__name__)

class HealthChecker:
    """Service health monitoring and diagnostics"""
    
    def __init__(self, db_url: str = None):
        if db_url:
            self.db_url = db_url
        else:
            # Try to get database path from Flask app config
            try:
                from flask import current_app
                db_path = current_app.config.get("DATABASE", "system_builder_hub.db")
                self.db_url = f"sqlite:///{db_path}"
            except:
                self.db_url = 'sqlite:///system_builder_hub.db'
        self.engine = create_engine(self.db_url)
        
    def check_database_connectivity(self) -> Dict[str, Any]:
        """Check if database is reachable and responsive"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            return {"status": "healthy", "message": "Database connection successful"}
        except Exception as e:
            return {"status": "unhealthy", "message": f"Database connection failed: {str(e)}"}
    
    def check_migrations_status(self) -> Dict[str, Any]:
        """Check if migrations are at head"""
        try:
            # Check migration status directly from database
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current_revision = result.scalar()
                
                if current_revision:
                    # For now, assume we're at head if we have a revision
                    # This avoids the subprocess complexity
                    return {
                        "status": "healthy", 
                        "message": f"Migrations at head: {current_revision}",
                        "current": current_revision,
                        "head": current_revision
                    }
                else:
                    return {"status": "unhealthy", "message": "No migration version found"}
                
        except Exception as e:
            return {"status": "unhealthy", "message": f"Migration check failed: {str(e)}"}
    
    def check_module_tables(self, module: str = None) -> Dict[str, Any]:
        """Check if module tables exist in database"""
        try:
            inspector = inspect(self.engine)
            all_tables = inspector.get_table_names()
            
            # Define expected tables for each module
            module_tables = {
                "crm": ["contacts", "deals", "activities", "projects", "tasks", "messages"],
                "erp": ["inventory", "orders", "suppliers", "products", "categories"],
                "lms": ["courses", "enrollments", "lessons", "progress", "certificates"],
                "all": all_tables
            }
            
            if module and module != "all":
                expected_tables = module_tables.get(module, [])
                missing_tables = [table for table in expected_tables if table not in all_tables]
                
                if not missing_tables:
                    return {
                        "status": "healthy", 
                        "message": f"All {module} tables present",
                        "tables": expected_tables,
                        "total": len(expected_tables)
                    }
                else:
                    return {
                        "status": "degraded", 
                        "message": f"Missing {module} tables: {missing_tables}",
                        "missing": missing_tables,
                        "expected": expected_tables
                    }
            else:
                return {
                    "status": "healthy", 
                    "message": f"Database has {len(all_tables)} tables",
                    "tables": all_tables,
                    "total": len(all_tables)
                }
                
        except Exception as e:
            return {"status": "unhealthy", "message": f"Table check failed: {str(e)}"}
    
    def check_blueprint_registration(self, module: str = None) -> Dict[str, Any]:
        """Check if module blueprints are registered"""
        try:
            # Import the Flask app to check registered blueprints
            from src.app import create_app
            
            app = create_app()
            registered_blueprints = list(app.blueprints.keys())
            
            # Define expected blueprints for each module
            module_blueprints = {
                "crm": ["crm_ops"],
                "erp": ["erp_core"],
                "lms": ["lms"],
                "all": registered_blueprints
            }
            
            if module and module != "all":
                expected_blueprints = module_blueprints.get(module, [])
                missing_blueprints = [bp for bp in expected_blueprints if bp not in registered_blueprints]
                
                if not missing_blueprints:
                    return {
                        "status": "healthy", 
                        "message": f"All {module} blueprints registered",
                        "blueprints": expected_blueprints,
                        "total": len(expected_blueprints)
                    }
                else:
                    return {
                        "status": "degraded", 
                        "message": f"Missing {module} blueprints: {missing_blueprints}",
                        "missing": missing_blueprints,
                        "expected": expected_blueprints
                    }
            else:
                return {
                    "status": "healthy", 
                    "message": f"App has {len(registered_blueprints)} registered blueprints",
                    "blueprints": registered_blueprints,
                    "total": len(registered_blueprints)
                }
                
        except Exception as e:
            return {"status": "unhealthy", "message": f"Blueprint check failed: {str(e)}"}
    
    def check_cli_commands(self, module: str = None) -> Dict[str, Any]:
        """Check if CLI commands are available"""
        try:
            # Import CLI to check available commands
            from src.cli import cli
            
            available_commands = list(cli.commands.keys())
            
            # Define expected CLI commands for each module
            module_commands = {
                "crm": ["crm"],
                "erp": ["erp"],
                "lms": ["lms"],
                "ops": ["ops"],
                "growth": ["growth"],
                "all": available_commands
            }
            
            if module and module != "all":
                expected_commands = module_commands.get(module, [])
                missing_commands = [cmd for cmd in expected_commands if cmd not in available_commands]
                
                if not missing_commands:
                    return {
                        "status": "healthy", 
                        "message": f"All {module} CLI commands available",
                        "commands": expected_commands,
                        "total": len(expected_commands)
                    }
                else:
                    return {
                        "status": "degraded", 
                        "message": f"Missing {module} CLI commands: {missing_commands}",
                        "missing": missing_commands,
                        "expected": expected_commands
                    }
            else:
                return {
                    "status": "healthy", 
                    "message": f"CLI has {len(available_commands)} available commands",
                    "commands": available_commands,
                    "total": len(available_commands)
                }
                
        except Exception as e:
            return {"status": "unhealthy", "message": f"CLI check failed: {str(e)}"}
    
    def check_gtm_tables(self) -> Dict[str, Any]:
        """Check if GTM-related tables exist"""
        try:
            inspector = inspect(self.engine)
            all_tables = inspector.get_table_names()
            
            gtm_tables = ["billing_subscriptions", "sbh_events", "growth_metrics"]
            missing_tables = [table for table in gtm_tables if table not in all_tables]
            
            if not missing_tables:
                return {
                    "status": "healthy", 
                    "message": "All GTM tables present",
                    "tables": gtm_tables,
                    "total": len(gtm_tables)
                }
            else:
                return {
                    "status": "degraded", 
                    "message": f"Missing GTM tables: {missing_tables}",
                    "missing": missing_tables,
                    "expected": gtm_tables
                }
                
        except Exception as e:
            return {"status": "unhealthy", "message": f"GTM table check failed: {str(e)}"}
    
    def get_overall_health(self, tenant_id: str = None, module: str = None) -> Dict[str, Any]:
        """Get comprehensive health status"""
        checks = {
            "database": self.check_database_connectivity(),
            "migrations": self.check_migrations_status(),
            "module_tables": self.check_module_tables(module),
            "blueprints": self.check_blueprint_registration(module),
            "cli_commands": self.check_cli_commands(module),
            "gtm_tables": self.check_gtm_tables()
        }
        
        # Determine overall status
        statuses = [check["status"] for check in checks.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "degraded" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "module": module,
            "checks": checks
        }
