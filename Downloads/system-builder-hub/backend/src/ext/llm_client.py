"""
Plugin LLM client
"""
import logging
from typing import Dict, Any, Optional
from src.llm.providers import LLMProviderManager
from src.llm.schema import LLMRequest, LLMMessage, MessageRole

logger = logging.getLogger(__name__)

class LLMClient:
    """Plugin LLM client"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.provider_manager = LLMProviderManager()
    
    def run(self, prompt: str, model: Optional[str] = None, 
            temperature: float = 0.7, max_tokens: int = 1000) -> Dict[str, Any]:
        """Run LLM completion"""
        try:
            # Get default provider (will fallback to local-stub if not configured)
            provider = self.provider_manager.get_provider()
            
            # Create request
            request = LLMRequest(
                model=model or provider.default_model,
                messages=[LLMMessage(role=MessageRole.USER, content=prompt)],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Run completion
            response = provider.complete(request)
            
            # Track usage
            self._track_usage(prompt, response)
            
            return {
                'text': response.text,
                'usage': response.usage,
                'model': request.model
            }
            
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return {
                'text': '',
                'error': str(e),
                'usage': None,
                'model': model
            }
    
    def _track_usage(self, prompt: str, response):
        """Track LLM usage"""
        try:
            from src.analytics.service import AnalyticsService
            analytics = AnalyticsService()
            
            # Normalize usage data to ensure JSON serializability
            usage_data = None
            if response.usage:
                try:
                    usage_data = {
                        'prompt_tokens': int(response.usage.prompt_tokens),
                        'completion_tokens': int(response.usage.completion_tokens),
                        'total_tokens': int(response.usage.total_tokens)
                    }
                except Exception:
                    usage_data = {'error': 'Failed to serialize usage data'}
            
            analytics.track(
                tenant_id=self.tenant_id,
                event='plugin.llm_usage',
                user_id='system',
                source='plugin',
                props={
                    'prompt_length': len(prompt),
                    'response_length': len(response.text),
                    'model': response.raw.get('model', 'unknown') if response.raw else 'unknown',
                    'usage': usage_data
                }
            )
            
        except Exception as e:
            logger.warning("Analytics failure ignored: %s", e)
