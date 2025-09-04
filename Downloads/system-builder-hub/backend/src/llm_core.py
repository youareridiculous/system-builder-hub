"""
LLM Core - Database-backed LLM functionality with security hardening
"""
import os
import time
import json
from typing import Dict, List, Any, Optional
from enum import Enum
from .llm_provider_service import llm_provider_service
from .llm_safety import llm_safety, retry_with_backoff
from .sbh_secrets import secrets_manager, redact_secret, sanitize_error_message

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    LOCAL = "local"

class LLMConfig:
    """LLM configuration management with database integration and security"""
    
    def __init__(self, provider: str, api_key: str, default_model: str):
        self.provider = provider
        self.api_key = api_key
        self.default_model = default_model
    
    def is_configured(self) -> bool:
        """Check if LLM is properly configured"""
        return bool(self.provider and self.api_key and self.default_model)
    
    def make_test_call(self) -> str:
        """Make a minimal test call to verify connection"""
        if self.provider == LLMProvider.OPENAI.value:
            return self._test_openai()
        elif self.provider == LLMProvider.ANTHROPIC.value:
            return self._test_anthropic()
        elif self.provider == LLMProvider.GROQ.value:
            return self._test_groq()
        else:
            return "Test call completed"
    
    def _test_openai(self) -> str:
        """Test OpenAI connection"""
        try:
            import openai
            openai.api_key = self.api_key
            response = openai.ChatCompletion.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                timeout=llm_safety.timeouts['read']
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI test failed: {sanitize_error_message(str(e))}")
    
    def _test_anthropic(self) -> str:
        """Test Anthropic connection"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.default_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}]
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic test failed: {sanitize_error_message(str(e))}")
    
    def _test_groq(self) -> str:
        """Test Groq connection"""
        try:
            import groq
            client = groq.Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Groq test failed: {sanitize_error_message(str(e))}")
    
    @staticmethod
    def get_current(tenant_id: str = 'default') -> Optional['LLMConfig']:
        """Get current LLM configuration from database"""
        # First try database
        api_key = llm_provider_service.get_api_key(tenant_id)
        if api_key:
            config = llm_provider_service.get_active_config(tenant_id)
            if config:
                return LLMConfig(config.provider, api_key, config.default_model)
        
        # Fallback to environment variables
        provider = os.getenv('LLM_PROVIDER', 'openai')
        api_key = os.getenv('LLM_API_KEY')
        default_model = os.getenv('LLM_DEFAULT_MODEL', 'gpt-3.5-turbo')
        
        if not api_key:
            return None
        
        return LLMConfig(provider, api_key, default_model)

class LLMAvailability:
    """LLM availability and configuration status with database integration"""
    
    @staticmethod
    def get_status(tenant_id: str = 'default') -> Dict[str, Any]:
        """Get current LLM availability status"""
        config = LLMConfig.get_current(tenant_id)
        
        if not config or not config.is_configured():
            return {
                "available": False,
                "provider": None,
                "model": None,
                "missing": ["api_key", "provider"],
                "setup_hint": "Configure an LLM provider in Settings",
                "required_keys": ["api_key"]
            }
        
        return {
            "available": True,
            "provider": config.provider,
            "model": config.default_model,
            "missing": [],
            "setup_hint": None,
            "required_keys": []
        }
    
    @staticmethod
    def test_connection(tenant_id: str = 'default') -> Dict[str, Any]:
        """Test LLM connection with database logging"""
        return llm_provider_service.test_connection(tenant_id)

class LLMStub:
    """Stub LLM responses for no-LLM mode"""
    
    @staticmethod
    def guided_questions() -> List[str]:
        """Return seeded clarifying questions for guided mode"""
        return [
            "What type of system are you building? (web app, API, dashboard, etc.)",
            "What is the primary functionality you need?",
            "Do you have any specific requirements or constraints?"
        ]
    
    @staticmethod
    def expand_blueprint(template: Dict[str, Any]) -> Dict[str, Any]:
        """Echo template with TODO notes for expansion"""
        expanded = template.copy()
        expanded['notes'] = [
            "TODO: Expand entities based on requirements",
            "TODO: Add authentication if needed",
            "TODO: Configure database schema",
            "TODO: Add API endpoints",
            "TODO: Create UI components"
        ]
        expanded['stubbed'] = True
        return expanded

class LLMService:
    """LLM service for Core Build Loop integration with security hardening"""
    
    def __init__(self, tenant_id: str = 'default'):
        self.tenant_id = tenant_id
        self.config = LLMConfig.get_current(tenant_id)
    
    def is_available(self) -> bool:
        """Check if LLM is available for this tenant"""
        return self.config is not None and self.config.is_configured()
    
    def generate_completion(self, prompt: str, model: Optional[str] = None, 
                           max_tokens: int = 1000) -> Dict[str, Any]:
        """Generate completion using configured LLM with safety checks"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'LLM not configured',
                'content': None
            }
        
        model = model or self.config.default_model
        start_time = time.time()
        
        try:
            # Use safety manager for the completion call
            def completion_func():
                if self.config.provider == LLMProvider.OPENAI.value:
                    return self._openai_completion(prompt, model, max_tokens)
                elif self.config.provider == LLMProvider.ANTHROPIC.value:
                    return self._anthropic_completion(prompt, model, max_tokens)
                elif self.config.provider == LLMProvider.GROQ.value:
                    return self._groq_completion(prompt, model, max_tokens)
                else:
                    return {'success': False, 'error': f'Unsupported provider: {self.config.provider}'}
            
            # Execute with safety checks and retries
            result = llm_safety.safe_call(
                self.config.provider, 
                model, 
                lambda: retry_with_backoff(completion_func, max_retries=2),
                tokens=max_tokens  # Estimate for rate limiting
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log usage
            if result['success']:
                llm_provider_service._log_usage(
                    self.tenant_id, 
                    llm_provider_service.get_active_config(self.tenant_id).id,
                    self.config.provider, model, 'completion', 
                    result.get('tokens_used'), latency_ms, True, None
                )
            else:
                llm_provider_service._log_usage(
                    self.tenant_id,
                    llm_provider_service.get_active_config(self.tenant_id).id,
                    self.config.provider, model, 'completion',
                    None, latency_ms, False, result.get('error')
                )
            
            return result
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = sanitize_error_message(str(e))
            
            # Log error
            llm_provider_service._log_usage(
                self.tenant_id,
                llm_provider_service.get_active_config(self.tenant_id).id,
                self.config.provider, model, 'completion',
                None, latency_ms, False, error_msg
            )
            
            return {
                'success': False,
                'error': error_msg,
                'content': None
            }
    
    def _openai_completion(self, prompt: str, model: str, max_tokens: int) -> Dict[str, Any]:
        """Generate OpenAI completion"""
        try:
            import openai
            openai.api_key = self.config.api_key
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                timeout=llm_safety.timeouts['read']
            )
            return {
                'success': True,
                'content': response.choices[0].message.content,
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else None
            }
        except Exception as e:
            return {'success': False, 'error': f"OpenAI completion failed: {sanitize_error_message(str(e))}"}
    
    def _anthropic_completion(self, prompt: str, model: str, max_tokens: int) -> Dict[str, Any]:
        """Generate Anthropic completion"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.config.api_key)
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return {
                'success': True,
                'content': response.content[0].text,
                'tokens_used': response.usage.input_tokens + response.usage.output_tokens if hasattr(response, 'usage') else None
            }
        except Exception as e:
            return {'success': False, 'error': f"Anthropic completion failed: {sanitize_error_message(str(e))}"}
    
    def _groq_completion(self, prompt: str, model: str, max_tokens: int) -> Dict[str, Any]:
        """Generate Groq completion"""
        try:
            import groq
            client = groq.Groq(api_key=self.config.api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return {
                'success': True,
                'content': response.choices[0].message.content,
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else None
            }
        except Exception as e:
            return {'success': False, 'error': f"Groq completion failed: {sanitize_error_message(str(e))}"}
