"""
Blueprint Registry with Fault Isolation
Handles blueprint registration with graceful error handling
"""
import logging
from typing import List, Tuple, Dict, Any, Optional
from flask import Flask

logger = logging.getLogger(__name__)

# Core blueprints that are always loaded in safe mode
CORE_BLUEPRINTS = [
    ('llm_config', None, None),  # LLM configuration    ('health', '/healthz', None),  # Health check
    ('metrics', '/metrics', None),  # Prometheus metrics
    ('openapi', '/docs', None),  # OpenAPI docs
    ('ui', '/ui', None),  # UI routes
    ('ui_build', None, None),  # Build wizard
    ('ui_project_loader', None, None),  # Project loader
    ('ui_visual_builder', None, None),  # Visual builder
    ('ui_guided', None, None),  # Guided sessions
]

# Optional blueprints that require full mode
OPTIONAL_BLUEPRINTS = [
    ('collab_workspace', '/collab', 'collab_workspace_enabled'),
    ('background', None, 'background_tasks_enabled'),
    ('memory', '/memory', 'memory_enabled'),
    ('template_gen', '/templates', 'template_gen_enabled'),
    ('client_success', '/client-success', 'client_success_enabled'),
    ('design_versioning', '/versioning', 'design_versioning_enabled'),
    ('data_refinery', '/data-refinery', 'data_refinery_enabled'),
    ('modelops', '/modelops', 'modelops_enabled'),
    ('sovereign_deploy', '/sovereign', 'sovereign_deploy_enabled'),
    ('gtm_engine', '/gtm', 'gtm_engine_enabled'),
    ('investor_pack', '/investor', 'investor_pack_enabled'),
    ('growth_agent', '/growth', 'growth_agent_enabled'),
    ('conversational_builder', '/conversational', 'conversational_builder_enabled'),
    ('context_engine', '/context', 'context_engine_enabled'),
    ('benchmark', '/benchmark', 'benchmark_enabled'),
    ('quality_gates', '/quality', 'quality_gates_enabled'),
    ('compliance_integration', '/compliance', 'compliance_enabled'),
    ('synthetic_data', '/synthetic', 'synthetic_data_enabled'),
    ('recycle', '/recycle', 'recycle_enabled'),
    ('residency', '/residency', 'residency_enabled'),
    ('supply_chain', '/supply-chain', 'supply_chain_enabled'),
    ('builder_llm_policy', '/builder-llm', 'builder_llm_enabled'),
    ('perf_scale', '/perf-scale', 'perf_scale_enabled'),
    ('workspaces', '/workspaces', 'workspaces_enabled'),
    ('auto_tuner', '/auto-tuner', 'auto_tuner_enabled'),
    ('dx_cli_ext', '/dx-cli', 'dx_cli_enabled'),
    ('compliance_evidence', '/compliance-evidence', 'compliance_evidence_enabled'),
]

class BlueprintRegistry:
    """Manages blueprint registration with fault isolation"""
    
    def __init__(self):
        self.registered_blueprints: Dict[str, Dict[str, Any]] = {}
        self.failed_blueprints: Dict[str, Dict[str, Any]] = {}
    
    def register_blueprints(self, app: Flask, mode: str = 'safe') -> Dict[str, Any]:
        """Register blueprints with fault isolation"""
        logger.info(f"Registering blueprints in {mode} mode")
        
        # Always register core blueprints
        blueprints_to_register = CORE_BLUEPRINTS.copy()
        
        # Add optional blueprints in full mode
        if mode == 'full':
            blueprints_to_register.extend(OPTIONAL_BLUEPRINTS)
        
        total_blueprints = len(blueprints_to_register)
        successful_registrations = 0
        failed_registrations = 0
        
        for blueprint_name, url_prefix, feature_flag in blueprints_to_register:
            try:
                # Check feature flag if specified
                if feature_flag and hasattr(app, 'feature_flags'):
                    if not app.feature_flags.is_enabled(feature_flag):
                        logger.info(f"Blueprint {blueprint_name} disabled by feature flag {feature_flag}")
                        self.failed_blueprints[blueprint_name] = {
                            'reason': f'Feature flag {feature_flag} disabled',
                            'type': 'feature_flag'
                        }
                        failed_registrations += 1
                        continue
                
                # Import blueprint module
                module_name = blueprint_name
                if blueprint_name == 'ui_build':
                    module_name = 'ui_build'
                elif blueprint_name == 'ui_project_loader':
                    module_name = 'ui_project_loader'
                elif blueprint_name == 'ui_visual_builder':
                    module_name = 'ui_visual_builder'
                elif blueprint_name == 'ui_guided':
                    module_name = 'ui_guided'
                
                # Try to import the blueprint
                try:
                    module = __import__(module_name, fromlist=[f'{module_name}_bp'])
                    blueprint = getattr(module, f'{module_name}_bp')
                except (ImportError, AttributeError) as e:
                    logger.warning(f"Blueprint {blueprint_name} not found: {e}")
                    self.failed_blueprints[blueprint_name] = {
                        'reason': f'Module not found: {e}',
                        'type': 'import_error'
                    }
                    failed_registrations += 1
                    continue
                
                # Register blueprint
                if url_prefix:
                    app.register_blueprint(blueprint, url_prefix=url_prefix)
                else:
                    app.register_blueprint(blueprint)
                
                self.registered_blueprints[blueprint_name] = {
                    'url_prefix': url_prefix,
                    'feature_flag': feature_flag
                }
                successful_registrations += 1
                logger.info(f"Blueprint {blueprint_name} registered successfully")
                
            except Exception as e:
                logger.error(f"Failed to register blueprint {blueprint_name}: {e}")
                self.failed_blueprints[blueprint_name] = {
                    'reason': str(e),
                    'type': 'registration_error'
                }
                failed_registrations += 1
        
        # Log summary
        logger.info(f"Blueprint registration complete: {successful_registrations}/{total_blueprints} successful, {failed_registrations} failed")
        
        return {
            'mode': mode,
            'total': total_blueprints,
            'successful': successful_registrations,
            'failed': failed_registrations,
            'registered': list(self.registered_blueprints.keys()),
            'failed_blueprints': self.failed_blueprints
        }
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get blueprint diagnostics for admin endpoint"""
        return {
            'registered_blueprints': self.registered_blueprints,
            'failed_blueprints': self.failed_blueprints,
            'summary': {
                'total_registered': len(self.registered_blueprints),
                'total_failed': len(self.failed_blueprints)
            }
        }

# Global registry instance
blueprint_registry = BlueprintRegistry()
