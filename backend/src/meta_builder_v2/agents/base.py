"""
Base agent classes and context for Meta-Builder v2.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from uuid import UUID
import json

from src.llm.providers import LLMProviderManager
from src.llm.prompt_library import PromptLibrary
from src.llm.safety import SafetyFilter
from src.llm.cache import LLMCache
from src.llm.metering import LLMMetering
from src.llm.schema import LLMRequest, LLMMessage, LLMTool
from src.redis_core import get_redis
from src.analytics.service import AnalyticsService
from src.obs.audit import audit

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Shared context for all agents."""
    tenant_id: UUID
    user_id: UUID
    repo_ref: Optional[str] = None
    allow_tools: bool = True
    cache: bool = True
    safety: bool = True
    llm_provider: Optional[LLMProviderManager] = None
    prompt_library: Optional[PromptLibrary] = None
    safety_filter: Optional[SafetyFilter] = None
    llm_cache: Optional[LLMCache] = None
    llm_metering: Optional[LLMMetering] = None
    redis: Optional[Any] = None
    analytics: Optional[AnalyticsService] = None
    
    def __post_init__(self):
        if self.llm_provider is None:
            self.llm_provider = LLMProviderManager()
            self.prompt_library = PromptLibrary()
            self.safety_filter = SafetyFilter()
            self.llm_cache = LLMCache()
            self.llm_metering = LLMMetering()
        if self.redis is None:
            self.redis = get_redis()
        if self.analytics is None:
            self.analytics = AnalyticsService()


class BaseAgent(ABC):
    """Base class for all Meta-Builder v2 agents."""
    
    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    @abstractmethod
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's primary action."""
        pass
    
    def _get_cache_key(self, action: str, inputs: Dict[str, Any]) -> str:
        """Generate cache key for agent execution."""
        input_hash = json.dumps(inputs, sort_keys=True)
        return f"meta_builder:agent:{self.__class__.__name__}:{action}:{input_hash}"
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available."""
        if not self.context.cache:
            return None
        
        try:
            cached = await self.context.redis.get(cache_key)
            if cached:
                self.logger.info(f"Cache hit for {cache_key}")
                return json.loads(cached)
        except Exception as e:
            self.logger.warning(f"Cache get failed: {e}")
        
        return None
    
    async def _set_cached_result(self, cache_key: str, result: Dict[str, Any], ttl: int = 3600):
        """Cache result with TTL."""
        if not self.context.cache:
            return
        
        try:
            await self.context.redis.setex(
                cache_key, 
                ttl, 
                json.dumps(result)
            )
            self.logger.info(f"Cached result for {cache_key}")
        except Exception as e:
            self.logger.warning(f"Cache set failed: {e}")
    
    def _emit_analytics(self, event: str, data: Dict[str, Any]):
        """Emit analytics event."""
        try:
            self.context.analytics.track(
                event=event,
                user_id=str(self.context.user_id),
                tenant_id=str(self.context.tenant_id),
                properties=data
            )
        except Exception as e:
            self.logger.warning(f"Analytics emit failed: {e}")
    
    def _audit_log(self, action: str, resource: str, details: Dict[str, Any]):
        """Log audit event."""
        try:
            audit_log(
                user_id=self.context.user_id,
                tenant_id=self.context.tenant_id,
                action=action,
                resource=resource,
                details=details
            )
        except Exception as e:
            self.logger.warning(f"Audit log failed: {e}")
    
    async def _execute_with_metrics(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent with timing and metrics."""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(action, inputs)
            cached_result = await self._get_cached_result(cache_key)
            if cached_result:
                self._emit_analytics("meta.agent.cache_hit", {
                    "agent": self.__class__.__name__,
                    "action": action
                })
                return cached_result
            
            # Execute agent
            result = await self.execute(action, inputs)
            
            # Cache result
            await self._set_cached_result(cache_key, result)
            
            # Emit metrics
            duration_ms = int((time.time() - start_time) * 1000)
            self._emit_analytics("meta.agent.executed", {
                "agent": self.__class__.__name__,
                "action": action,
                "duration_ms": duration_ms,
                "success": True
            })
            
            # Audit log
            self._audit_log(
                action=f"agent.{action}",
                resource=f"meta_builder.{self.__class__.__name__}",
                details={
                    "inputs": inputs,
                    "duration_ms": duration_ms,
                    "success": True
                }
            )
            
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.error(f"Agent execution failed: {e}")
            
            # Emit failure metrics
            self._emit_analytics("meta.agent.failed", {
                "agent": self.__class__.__name__,
                "action": action,
                "duration_ms": duration_ms,
                "error": str(e)
            })
            
            # Audit log failure
            self._audit_log(
                action=f"agent.{action}.failed",
                resource=f"meta_builder.{self.__class__.__name__}",
                details={
                    "inputs": inputs,
                    "duration_ms": duration_ms,
                    "error": str(e)
                }
            )
            
            raise
