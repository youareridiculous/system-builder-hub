"""
System Blueprint (Declarative Composition)

Defines the structure for composing multiple modules into unified systems.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class SystemBlueprint:
    """Declarative specification for a multi-module system"""
    name: str
    version: str
    modules: List[str]
    contracts: List[str]
    workflows: List[str]
    env: Dict[str, Any]
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert blueprint to dictionary"""
        return asdict(self)
    
    def validate(self) -> List[str]:
        """Validate blueprint configuration"""
        errors = []
        
        if not self.name:
            errors.append("System name is required")
        
        if not self.version:
            errors.append("System version is required")
        
        if not self.modules:
            errors.append("At least one module is required")
        
        if not isinstance(self.modules, list):
            errors.append("Modules must be a list")
        
        if not isinstance(self.contracts, list):
            errors.append("Contracts must be a list")
        
        if not isinstance(self.workflows, list):
            errors.append("Workflows must be a list")
        
        if not isinstance(self.env, dict):
            errors.append("Environment must be a dictionary")
        
        return errors

def load_system_blueprints() -> Dict[str, SystemBlueprint]:
    """Load system blueprints from ecosystems directory"""
    blueprints = {}
    
    try:
        # Look for ecosystems directory
        ecosystems_dir = Path("ecosystems")
        if not ecosystems_dir.exists():
            logger.info("Ecosystems directory not found, creating with default blueprint")
            ecosystems_dir.mkdir(exist_ok=True)
            _create_default_blueprint(ecosystems_dir)
        
        # Load all .json files
        for blueprint_file in ecosystems_dir.glob("*.json"):
            try:
                with open(blueprint_file, 'r') as f:
                    data = json.load(f)
                
                # Create blueprint object
                blueprint = SystemBlueprint(
                    name=data.get('name', ''),
                    version=data.get('version', '1.0.0'),
                    modules=data.get('modules', []),
                    contracts=data.get('contracts', []),
                    workflows=data.get('workflows', []),
                    env=data.get('env', {}),
                    description=data.get('description', '')
                )
                
                # Validate blueprint
                errors = blueprint.validate()
                if errors:
                    logger.warning(f"Blueprint {blueprint.name} has validation errors: {errors}")
                    continue
                
                blueprints[blueprint.name] = blueprint
                logger.info(f"Loaded system blueprint: {blueprint.name}")
                
            except Exception as e:
                logger.error(f"Failed to load blueprint {blueprint_file}: {e}")
                continue
        
        if not blueprints:
            logger.warning("No valid blueprints found, creating default")
            _create_default_blueprint(ecosystems_dir)
            blueprints = load_system_blueprints()  # Recursive call to load default
        
        return blueprints
        
    except Exception as e:
        logger.error(f"Failed to load system blueprints: {e}")
        return {}

def _create_default_blueprint(ecosystems_dir: Path):
    """Create a default revops_suite blueprint"""
    default_blueprint = {
        "name": "revops_suite",
        "version": "1.0.0",
        "description": "Revenue Operations Suite - CRM + ERP + LMS integration",
        "modules": ["crm", "erp", "lms"],
        "contracts": [
            "contacts_sync",
            "orders_to_deals",
            "leads_to_opportunities",
            "customer_profile_sync"
        ],
        "workflows": [
            "new_customer_360",
            "lead_to_cash",
            "order_fulfillment",
            "customer_retention"
        ],
        "env": {
            "tenants": ["demo"],
            "feature_flags": ["cross_module_sync", "unified_dashboard"],
            "data_retention_days": 90,
            "sync_frequency_minutes": 15
        }
    }
    
    blueprint_file = ecosystems_dir / "revops_suite.json"
    try:
        with open(blueprint_file, 'w') as f:
            json.dump(default_blueprint, f, indent=2)
        logger.info(f"Created default blueprint: {blueprint_file}")
    except Exception as e:
        logger.error(f"Failed to create default blueprint: {e}")

def get_blueprint(name: str) -> Optional[SystemBlueprint]:
    """Get a specific system blueprint by name"""
    blueprints = load_system_blueprints()
    return blueprints.get(name)

def list_blueprints() -> List[Dict[str, Any]]:
    """List all available system blueprints"""
    blueprints = load_system_blueprints()
    return [
        {
            "name": bp.name,
            "version": bp.version,
            "description": bp.description,
            "modules": bp.modules,
            "contracts_count": len(bp.contracts),
            "workflows_count": len(bp.workflows),
            "env_summary": {
                "tenants": bp.env.get("tenants", []),
                "feature_flags": bp.env.get("feature_flags", [])
            }
        }
        for bp in blueprints.values()
    ]

def validate_blueprint_file(file_path: str) -> Dict[str, Any]:
    """Validate a blueprint file without loading it"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check required fields
        required_fields = ['name', 'version', 'modules']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return {
                "valid": False,
                "errors": [f"Missing required field: {field}" for field in missing_fields]
            }
        
        # Check field types
        type_errors = []
        if not isinstance(data.get('modules', []), list):
            type_errors.append("Modules must be a list")
        if not isinstance(data.get('contracts', []), list):
            type_errors.append("Contracts must be a list")
        if not isinstance(data.get('workflows', []), list):
            type_errors.append("Workflows must be a list")
        if not isinstance(data.get('env', {}), dict):
            type_errors.append("Environment must be a dictionary")
        
        if type_errors:
            return {
                "valid": False,
                "errors": type_errors
            }
        
        return {
            "valid": True,
            "name": data.get('name'),
            "modules_count": len(data.get('modules', [])),
            "contracts_count": len(data.get('contracts', [])),
            "workflows_count": len(data.get('workflows', []))
        }
        
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "errors": [f"Invalid JSON: {str(e)}"]
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Validation failed: {str(e)}"]
        }
