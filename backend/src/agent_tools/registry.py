"""
Tool registry for agent tools
"""
import logging
from typing import Dict, List, Callable, Any, Optional
from src.agent_tools.types import ToolSpec, ToolCall, ToolResult, ToolContext

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for agent tools"""
    
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._handlers: Dict[str, Callable] = {}
    
    def register(self, spec: ToolSpec, handler: Callable) -> None:
        """Register a tool with its handler"""
        if spec.name in self._tools:
            logger.warning(f"Tool {spec.name} already registered, overwriting")
        
        self._tools[spec.name] = spec
        self._handlers[spec.name] = handler
        logger.info(f"Registered tool: {spec.name} v{spec.version}")
    
    def get(self, name: str) -> Optional[ToolSpec]:
        """Get tool specification by name"""
        return self._tools.get(name)
    
    def get_handler(self, name: str) -> Optional[Callable]:
        """Get tool handler by name"""
        return self._handlers.get(name)
    
    def list(self) -> List[ToolSpec]:
        """List all registered tools"""
        return list(self._tools.values())
    
    def list_names(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def is_registered(self, name: str) -> bool:
        """Check if tool is registered"""
        return name in self._tools
    
    def unregister(self, name: str) -> bool:
        """Unregister a tool"""
        if name in self._tools:
            del self._tools[name]
            del self._handlers[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

# Global singleton tool registry
tool_registry = ToolRegistry()
