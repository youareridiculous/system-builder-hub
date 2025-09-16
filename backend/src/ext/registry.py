"""
Plugin registry for managing loaded plugins
"""
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from src.ext.models import Plugin, PluginInstallation
from src.database import db_session

logger = logging.getLogger(__name__)

@dataclass
class LoadedPlugin:
    """Loaded plugin instance"""
    installation: PluginInstallation
    plugin: Plugin
    module: Any  # Loaded Python module
    routes: List[Any]  # Flask routes
    hooks: Dict[str, List[Any]]  # Event hooks
    jobs: Dict[str, Any]  # Scheduled jobs
    webhooks: List[Any]  # Webhook definitions

class PluginRegistry:
    """In-memory registry of loaded plugins per tenant"""
    
    def __init__(self):
        self._plugins: Dict[str, Dict[str, LoadedPlugin]] = {}  # tenant_id -> {plugin_slug -> LoadedPlugin}
        self._event_hooks: Dict[str, List[Any]] = {}  # event_type -> [hook_functions]
        self._llm_filters: Dict[str, List[Any]] = {}  # filter_type -> [filter_functions]
        self._generator_hooks: Dict[str, List[Any]] = {}  # hook_type -> [hook_functions]
    
    def install_plugin(self, tenant_id: str, installation: PluginInstallation, plugin: Plugin, module: Any) -> LoadedPlugin:
        """Install a plugin for a tenant"""
        try:
            # Create loaded plugin instance
            loaded_plugin = LoadedPlugin(
                installation=installation,
                plugin=plugin,
                module=module,
                routes=[],
                hooks={},
                jobs={},
                webhooks=[]
            )
            
            # Initialize tenant plugins dict if needed
            if tenant_id not in self._plugins:
                self._plugins[tenant_id] = {}
            
            # Store plugin
            self._plugins[tenant_id][plugin.slug] = loaded_plugin
            
            # Register event hooks
            self._register_event_hooks(loaded_plugin)
            
            # Register LLM filters
            self._register_llm_filters(loaded_plugin)
            
            # Register generator hooks
            self._register_generator_hooks(loaded_plugin)
            
            logger.info(f"Plugin {plugin.slug} installed for tenant {tenant_id}")
            return loaded_plugin
            
        except Exception as e:
            logger.error(f"Error installing plugin {plugin.slug} for tenant {tenant_id}: {e}")
            raise
    
    def uninstall_plugin(self, tenant_id: str, plugin_slug: str) -> bool:
        """Uninstall a plugin for a tenant"""
        try:
            if tenant_id in self._plugins and plugin_slug in self._plugins[tenant_id]:
                loaded_plugin = self._plugins[tenant_id][plugin_slug]
                
                # Unregister event hooks
                self._unregister_event_hooks(loaded_plugin)
                
                # Unregister LLM filters
                self._unregister_llm_filters(loaded_plugin)
                
                # Unregister generator hooks
                self._unregister_generator_hooks(loaded_plugin)
                
                # Remove from registry
                del self._plugins[tenant_id][plugin_slug]
                
                # Clean up empty tenant dict
                if not self._plugins[tenant_id]:
                    del self._plugins[tenant_id]
                
                logger.info(f"Plugin {plugin_slug} uninstalled for tenant {tenant_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error uninstalling plugin {plugin_slug} for tenant {tenant_id}: {e}")
            return False
    
    def enable_plugin(self, tenant_id: str, plugin_slug: str) -> bool:
        """Enable a plugin for a tenant"""
        try:
            if tenant_id in self._plugins and plugin_slug in self._plugins[tenant_id]:
                loaded_plugin = self._plugins[tenant_id][plugin_slug]
                loaded_plugin.installation.enabled = True
                
                # Update database
                with db_session() as session:
                    session.merge(loaded_plugin.installation)
                    session.commit()
                
                logger.info(f"Plugin {plugin_slug} enabled for tenant {tenant_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error enabling plugin {plugin_slug} for tenant {tenant_id}: {e}")
            return False
    
    def disable_plugin(self, tenant_id: str, plugin_slug: str) -> bool:
        """Disable a plugin for a tenant"""
        try:
            if tenant_id in self._plugins and plugin_slug in self._plugins[tenant_id]:
                loaded_plugin = self._plugins[tenant_id][plugin_slug]
                loaded_plugin.installation.enabled = False
                
                # Update database
                with db_session() as session:
                    session.merge(loaded_plugin.installation)
                    session.commit()
                
                logger.info(f"Plugin {plugin_slug} disabled for tenant {tenant_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error disabling plugin {plugin_slug} for tenant {tenant_id}: {e}")
            return False
    
    def get_plugin(self, tenant_id: str, plugin_slug: str) -> Optional[LoadedPlugin]:
        """Get a loaded plugin"""
        return self._plugins.get(tenant_id, {}).get(plugin_slug)
    
    def get_tenant_plugins(self, tenant_id: str) -> List[LoadedPlugin]:
        """Get all plugins for a tenant"""
        return list(self._plugins.get(tenant_id, {}).values())
    
    def get_enabled_plugins(self, tenant_id: str) -> List[LoadedPlugin]:
        """Get enabled plugins for a tenant"""
        return [
            plugin for plugin in self.get_tenant_plugins(tenant_id)
            if plugin.installation.enabled
        ]
    
    def get_event_hooks(self, event_type: str) -> List[Any]:
        """Get hooks for an event type"""
        return self._event_hooks.get(event_type, [])
    
    def get_llm_filters(self, filter_type: str) -> List[Any]:
        """Get LLM filters for a filter type"""
        return self._llm_filters.get(filter_type, [])
    
    def get_generator_hooks(self, hook_type: str) -> List[Any]:
        """Get generator hooks for a hook type"""
        return self._generator_hooks.get(hook_type, [])
    
    def _register_event_hooks(self, loaded_plugin: LoadedPlugin):
        """Register event hooks for a plugin"""
        try:
            # Look for @hook decorators in the module
            for attr_name in dir(loaded_plugin.module):
                attr = getattr(loaded_plugin.module, attr_name)
                if hasattr(attr, '_plugin_hook_type') and attr._plugin_hook_type == 'event':
                    event_type = attr._plugin_event_type
                    
                    if event_type not in self._event_hooks:
                        self._event_hooks[event_type] = []
                    
                    self._event_hooks[event_type].append(attr)
                    loaded_plugin.hooks.setdefault(event_type, []).append(attr)
                    
                    logger.debug(f"Registered event hook {attr_name} for event {event_type}")
                    
        except Exception as e:
            logger.error(f"Error registering event hooks for plugin {loaded_plugin.plugin.slug}: {e}")
    
    def _unregister_event_hooks(self, loaded_plugin: LoadedPlugin):
        """Unregister event hooks for a plugin"""
        try:
            for event_type, hooks in loaded_plugin.hooks.items():
                if event_type in self._event_hooks:
                    for hook in hooks:
                        if hook in self._event_hooks[event_type]:
                            self._event_hooks[event_type].remove(hook)
                    
                    # Clean up empty event type
                    if not self._event_hooks[event_type]:
                        del self._event_hooks[event_type]
                        
        except Exception as e:
            logger.error(f"Error unregistering event hooks for plugin {loaded_plugin.plugin.slug}: {e}")
    
    def _register_llm_filters(self, loaded_plugin: LoadedPlugin):
        """Register LLM filters for a plugin"""
        try:
            # Look for @llm_filter decorators in the module
            for attr_name in dir(loaded_plugin.module):
                attr = getattr(loaded_plugin.module, attr_name)
                if hasattr(attr, '_plugin_hook_type') and attr._plugin_hook_type == 'llm_filter':
                    filter_type = attr._plugin_filter_type
                    
                    if filter_type not in self._llm_filters:
                        self._llm_filters[filter_type] = []
                    
                    self._llm_filters[filter_type].append(attr)
                    
                    logger.debug(f"Registered LLM filter {attr_name} for type {filter_type}")
                    
        except Exception as e:
            logger.error(f"Error registering LLM filters for plugin {loaded_plugin.plugin.slug}: {e}")
    
    def _unregister_llm_filters(self, loaded_plugin: LoadedPlugin):
        """Unregister LLM filters for a plugin"""
        try:
            # This would need to track which filters belong to which plugin
            # For now, we'll just clear all filters (simplified)
            pass
            
        except Exception as e:
            logger.error(f"Error unregistering LLM filters for plugin {loaded_plugin.plugin.slug}: {e}")
    
    def _register_generator_hooks(self, loaded_plugin: LoadedPlugin):
        """Register generator hooks for a plugin"""
        try:
            # Look for @generator_hook decorators in the module
            for attr_name in dir(loaded_plugin.module):
                attr = getattr(loaded_plugin.module, attr_name)
                if hasattr(attr, '_plugin_hook_type') and attr._plugin_hook_type == 'generator':
                    hook_type = attr._plugin_generator_hook_type
                    
                    if hook_type not in self._generator_hooks:
                        self._generator_hooks[hook_type] = []
                    
                    self._generator_hooks[hook_type].append(attr)
                    
                    logger.debug(f"Registered generator hook {attr_name} for type {hook_type}")
                    
        except Exception as e:
            logger.error(f"Error registering generator hooks for plugin {loaded_plugin.plugin.slug}: {e}")
    
    def _unregister_generator_hooks(self, loaded_plugin: LoadedPlugin):
        """Unregister generator hooks for a plugin"""
        try:
            # This would need to track which hooks belong to which plugin
            # For now, we'll just clear all hooks (simplified)
            pass
            
        except Exception as e:
            logger.error(f"Error unregistering generator hooks for plugin {loaded_plugin.plugin.slug}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_plugins = sum(len(plugins) for plugins in self._plugins.values())
        enabled_plugins = sum(
            len([p for p in plugins.values() if p.installation.enabled])
            for plugins in self._plugins.values()
        )
        
        return {
            'total_tenants': len(self._plugins),
            'total_plugins': total_plugins,
            'enabled_plugins': enabled_plugins,
            'event_hooks': len(self._event_hooks),
            'llm_filters': len(self._llm_filters),
            'generator_hooks': len(self._generator_hooks)
        }

# Global plugin registry
plugin_registry = PluginRegistry()
