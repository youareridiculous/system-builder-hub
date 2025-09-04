"""
Plugin loader for loading and validating plugins
"""
import os
import json
import zipfile
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from src.ext.models import Plugin, PluginInstallation
from src.ext.registry import plugin_registry, LoadedPlugin

logger = logging.getLogger(__name__)

class PluginLoader:
    """Plugin loader for loading and validating plugins"""
    
    def __init__(self):
        self.plugin_storage_path = Path("/tmp/plugins")  # In production, use proper storage
        self.plugin_storage_path.mkdir(exist_ok=True)
        
        # Allowed imports for sandboxing
        self.allowed_imports = {
            'json', 'datetime', 'time', 'uuid', 'hashlib', 'base64',
            'urllib.parse', 'collections', 'itertools', 'functools'
        }
    
    def load_plugin_from_zip(self, zip_file_path: str, tenant_id: str) -> Tuple[Plugin, PluginInstallation]:
        """Load a plugin from a ZIP file"""
        try:
            # Extract ZIP to temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Load plugin manifest
                manifest_path = Path(temp_dir) / "plugin.json"
                if not manifest_path.exists():
                    raise ValueError("plugin.json not found in ZIP")
                
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                # Validate manifest
                self._validate_manifest(manifest)
                
                # Create plugin record
                plugin = Plugin(
                    slug=manifest['slug'],
                    name=manifest['name'],
                    version=manifest['version'],
                    description=manifest.get('description', ''),
                    author=manifest.get('author', ''),
                    repo_url=manifest.get('repo_url', ''),
                    entry=manifest['entry'],
                    permissions=manifest.get('permissions', []),
                    routes=manifest.get('routes', False),
                    events=manifest.get('events', []),
                    jobs=manifest.get('jobs', [])
                )
                
                # Create installation record
                installation = PluginInstallation(
                    tenant_id=tenant_id,
                    plugin_id=plugin.id,
                    enabled=False,
                    installed_version=plugin.version,
                    permissions_json={},
                    config_json={}
                )
                
                # Copy plugin files to storage
                plugin_path = self.plugin_storage_path / tenant_id / plugin.slug
                plugin_path.mkdir(parents=True, exist_ok=True)
                
                # Copy all files
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        src_path = Path(root) / file
                        rel_path = src_path.relative_to(temp_dir)
                        dst_path = plugin_path / rel_path
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                            dst.write(src.read())
                
                return plugin, installation
                
        except Exception as e:
            logger.error(f"Error loading plugin from ZIP {zip_file_path}: {e}")
            raise
    
    def load_plugin_module(self, plugin: Plugin, installation: PluginInstallation) -> LoadedPlugin:
        """Load a plugin module"""
        try:
            # Get plugin path
            plugin_path = self.plugin_storage_path / installation.tenant_id / plugin.slug
            
            # Add plugin path to Python path
            import sys
            sys.path.insert(0, str(plugin_path))
            
            # Load the entry module
            entry_module_name = plugin.entry.replace('.py', '')
            module = __import__(entry_module_name)
            
            # Remove plugin path from Python path
            sys.path.pop(0)
            
            # Create loaded plugin
            loaded_plugin = LoadedPlugin(
                installation=installation,
                plugin=plugin,
                module=module,
                routes=[],
                hooks={},
                jobs={},
                webhooks=[]
            )
            
            # Extract routes, hooks, and jobs from module
            self._extract_plugin_components(loaded_plugin)
            
            return loaded_plugin
            
        except Exception as e:
            logger.error(f"Error loading plugin module {plugin.slug}: {e}")
            raise
    
    def _validate_manifest(self, manifest: Dict[str, Any]):
        """Validate plugin manifest"""
        required_fields = ['slug', 'name', 'version', 'entry']
        for field in required_fields:
            if field not in manifest:
                raise ValueError(f"Required field '{field}' missing from manifest")
        
        # Validate slug format
        slug = manifest['slug']
        if not slug.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Plugin slug must be alphanumeric with hyphens and underscores only")
        
        # Validate permissions
        permissions = manifest.get('permissions', [])
        allowed_permissions = {
            'db.read', 'db.write', 'files.read', 'files.write',
            'emit_webhook', 'send_email', 'outbound_http', 'llm.use'
        }
        
        for permission in permissions:
            if permission not in allowed_permissions:
                raise ValueError(f"Invalid permission: {permission}")
        
        # Validate events
        events = manifest.get('events', [])
        allowed_events = {
            'auth.user.created', 'auth.user.updated', 'auth.user.deleted',
            'payments.subscription.created', 'payments.subscription.updated',
            'files.uploaded', 'files.deleted', 'builder.generated',
            'webhook.received', 'analytics.rollup.completed'
        }
        
        for event in events:
            if event not in allowed_events:
                raise ValueError(f"Invalid event: {event}")
    
    def _extract_plugin_components(self, loaded_plugin: LoadedPlugin):
        """Extract routes, hooks, and jobs from loaded plugin module"""
        try:
            module = loaded_plugin.module
            
            # Extract routes
            if hasattr(module, 'routes'):
                loaded_plugin.routes = module.routes
            
            # Extract hooks (already handled by decorators)
            # Extract jobs
            if hasattr(module, 'jobs'):
                loaded_plugin.jobs = module.jobs
            
            # Extract webhooks
            if hasattr(module, 'webhooks'):
                loaded_plugin.webhooks = module.webhooks
                
        except Exception as e:
            logger.error(f"Error extracting plugin components: {e}")
            raise
    
    def validate_plugin_security(self, plugin_path: Path) -> bool:
        """Validate plugin security (check for forbidden imports, etc.)"""
        try:
            # Check for forbidden imports in Python files
            for py_file in plugin_path.rglob("*.py"):
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Check for dangerous imports
                dangerous_imports = [
                    'os.system', 'subprocess', 'eval', 'exec',
                    'import os', 'import subprocess', 'import sys'
                ]
                
                for dangerous_import in dangerous_imports:
                    if dangerous_import in content:
                        logger.warning(f"Dangerous import found in {py_file}: {dangerous_import}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating plugin security: {e}")
            return False
    
    def get_plugin_path(self, tenant_id: str, plugin_slug: str) -> Path:
        """Get plugin storage path"""
        return self.plugin_storage_path / tenant_id / plugin_slug
    
    def list_plugin_files(self, tenant_id: str, plugin_slug: str) -> List[str]:
        """List files in a plugin"""
        try:
            plugin_path = self.get_plugin_path(tenant_id, plugin_slug)
            if not plugin_path.exists():
                return []
            
            files = []
            for file_path in plugin_path.rglob("*"):
                if file_path.is_file():
                    files.append(str(file_path.relative_to(plugin_path)))
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing plugin files: {e}")
            return []

# Global plugin loader
plugin_loader = PluginLoader()
