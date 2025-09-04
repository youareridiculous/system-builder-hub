"""
Co-Builder Router for intent classification and action routing
"""

import re
import logging
import time
from typing import Dict, Any

# Timeout constants
MODEL_TIMEOUT_S = 30       # per model call
REQUEST_DEADLINE_S = 90    # total hard cap

logger = logging.getLogger(__name__)

class CoBuilderRouter:
    """Routes Co-Builder messages to appropriate SBH actions"""
    
    def __init__(self):
        """Initialize router"""
        self.llm_client = None
        self.generator = None
        self.using_mock = True
        
        # Initialize generator with real OpenAI client or mock adapter
        try:
            from .generator import CoBuilderGenerator
            from src.llm import openai_client, provider_info
            
            if openai_client is not None:
                # Use real OpenAI/Azure client
                self.client = self._create_real_client_interface(openai_client, provider_info)
                self.generator = CoBuilderGenerator(self.client, provider_info["model_label"])
                self.using_mock = False
                logger.info(f"Co-Builder generator initialized with {provider_info['provider']} ({provider_info['model_label']})")
            else:
                # Use mock adapter
                self.client = self._create_mock_adapter()
                self.generator = CoBuilderGenerator(self.client, "mock")
                self.using_mock = True
                logger.info("Real LLM not configured; using mock adapter")
        except Exception as e:
            logger.warning(f"Failed to initialize generator: {e}")
            self.generator = None
            self.using_mock = True
    
    def _create_real_client_interface(self, client, provider_info):
        """Create a thin wrapper for real OpenAI/Azure clients"""
        class _ClientCompat:
            """
            Normalizes OpenAI (native) and AzureOpenAI to a uniform chat.completions.create interface.
            """
            def __init__(self, client, provider: str, model_label: str):
                self._client = client
                self._provider = provider
                self._model_label = model_label

            @property
            def model_label(self) -> str:
                return self._model_label

            class _Chat:
                def __init__(self, outer):
                    self._outer = outer
                    self.completions = _ClientCompat._Completions(outer)

            class _Completions:
                def __init__(self, outer):
                    self._outer = outer

                def create(self, **kwargs):
                    # kwargs we expect: model (or azure deployment), messages, temperature, timeout
                    client = self._outer._client
                    provider = self._outer._provider
                    if provider == "azure":
                        # Azure expects deployment name in model=, same API in SDK v1
                        return client.chat.completions.create(**kwargs)
                    else:
                        return client.chat.completions.create(**kwargs)

            @property
            def chat(self):
                return _ClientCompat._Chat(self)

        return _ClientCompat(client, provider_info["provider"], provider_info["model_label"])
    
    def _create_mock_adapter(self):
        """
        Return an object that exposes .chat.completions.create(...)
        If the real OpenAI client is available, return it.
        Otherwise return a tiny adapter that mirrors the shape exactly
        and can be replaced transparently.
        """
        # Prefer a real client if you have one wired
        try:
            from src.llm import openai_client  # must already match the OpenAI Python shape
            # quick shape sanity (won't raise in normal cases)
            _ = openai_client.chat.completions
            return openai_client
        except Exception as e:
            logger.warning(f"OpenAI client not available, using adapter: {e!r}")

        # Lightweight adapter with the exact shape: .chat.completions.create(...)
        class _ChatCompletions:
            def __init__(self, _call_fn):
                self._call_fn = _call_fn
            def create(self, **kwargs):
                # kwargs: model, messages, temperature, timeout (seconds), etc.
                return self._call_fn(**kwargs)

        class _Chat:
            def __init__(self, _call_fn):
                self.completions = _ChatCompletions(_call_fn)

        class OpenAIShapeAdapter:
            def __init__(self, call_fn):
                self.chat = _Chat(call_fn)

        # Default adapter "call" returns a response object that looks like OpenAI's
        def _mock_call(**kwargs):
            # Keep the generator working even without the real client.
            content = (
                '{'
                '"file":"src/tenant/model.py",'
                '"diff":"--- a/src/tenant/model.py\\n+++ b/src/tenant/model.py\\n@@ -1,1 +1,2 @@\\n+tenant_description: \\"\\"\\n",'
                '"snippet":"print(tenant.tenant_description or \\"\\")"'
                '}'
            )
            class _Msg:  # choices[0].message.content
                def __init__(self, c): self.content = c
            class _Choice:
                def __init__(self, c): self.message = _Msg(c)
            class _Resp:
                def __init__(self, c): self.choices = [ _Choice(c) ]
            return _Resp(content)

        return OpenAIShapeAdapter(_mock_call)
    
    def route_message(self, message: str, tenant_id: str, dry_run: bool = False, remaining_time: float = None) -> Dict[str, Any]:
        """Route a message to the appropriate action handler with timeout protection"""
        message_lower = message.lower()
        
        # Check deadline before processing
        if remaining_time is not None and remaining_time <= 0:
            logger.warning(f"Request deadline exceeded in router (tenant: {tenant_id})")
            return {
                "success": False,
                "response": "Request exceeded processing time limit.",
                "action_type": "timeout",
                "llm_generated": False
            }
        
        # Classify intent
        intent = self._classify_intent(message_lower)
        
        logger.info(f"ask.model.start request_id=unknown tenant={tenant_id} intent={intent}")
        
        # Route based on intent
        if "build" in intent or "create" in intent or "generate" in intent:
            return self._handle_build(message, tenant_id, dry_run, remaining_time)
        elif "provision" in intent or "install" in intent or "setup" in intent:
            return self._handle_provision(message, tenant_id, dry_run, remaining_time)
        else:
            return self._handle_unknown(message, tenant_id, dry_run, remaining_time)
    
    def _classify_intent(self, message: str) -> str:
        """Classify the intent of a message"""
        if any(word in message for word in ["build", "create", "generate", "make"]):
            return "build"
        elif any(word in message for word in ["provision", "install", "setup", "deploy"]):
            return "provision"
        else:
            return "unknown"
    
    def _handle_build(self, message: str, tenant_id: str, dry_run: bool, remaining_time: float = None) -> Dict[str, Any]:
        """Handle build-related requests"""
        # Check deadline before processing
        if remaining_time is not None and remaining_time <= 0:
            logger.warning(f"Build deadline exceeded (tenant: {tenant_id})")
            return {
                "success": False,
                "response": "Request exceeded processing time limit.",
                "action_type": "timeout",
                "llm_generated": False
            }
        
        # Use the generator for build requests
        if self.generator and not dry_run:
            try:
                # Calculate deadline timestamp
                deadline_ts = time.monotonic() + (remaining_time or MODEL_TIMEOUT_S)
                
                result = self.generator.apply_change(
                    prompt=message,
                    tenant_id=tenant_id,
                    request_id="unknown",  # We'll get this from the API layer
                    deadline_ts=deadline_ts
                )
                
                logger.info(f"ask.model.done request_id=unknown tenant={tenant_id} action=build elapsed_ms={result.elapsed_ms}")
                
                return {
                    "success": True,
                    "response": result.response,
                    "action_type": "build",
                    "llm_generated": True,
                    "model": result.model,
                    "file": result.file,
                    "diff": result.diff,
                    "snippet": result.snippet,
                    "elapsed_ms": result.elapsed_ms
                }
                
            except TimeoutError as te:
                logger.warning(f"Build generation timed out: {te}")
                return {
                    "success": False,
                    "response": "Generation exceeded time limit.",
                    "action_type": "timeout",
                    "llm_generated": False
                }
            except Exception as e:
                logger.error(f"Build generation failed: {e}")
                return {
                    "success": True,
                    "response": f"Build request received but generation failed: {str(e)}",
                    "action_type": "build",
                    "llm_generated": False,
                    "model": "error"
                }
        
        # Fallback for dry_run or if generator unavailable
        response = f"I understand you want to build something. Your message was: '{message}'. This feature is coming soon!"
        
        logger.info(f"ask.model.done request_id=unknown tenant={tenant_id} action=build elapsed_ms=0")
        
        return {
            "success": True,
            "response": response,
            "action_type": "build",
            "llm_generated": False,
            "model": "stub"
        }
    
    def _handle_provision(self, message: str, tenant_id: str, dry_run: bool, remaining_time: float = None) -> Dict[str, Any]:
        """Handle provision-related requests"""
        # Check deadline before processing
        if remaining_time is not None and remaining_time <= 0:
            logger.warning(f"Provision deadline exceeded (tenant: {tenant_id})")
            return {
                "success": False,
                "response": "Request exceeded processing time limit.",
                "action_type": "timeout",
                "llm_generated": False
            }
        
        # For now, return a simple response
        response = f"I understand you want to provision something. Your message was: '{message}'. This feature is coming soon!"
        
        logger.info(f"ask.model.done request_id=unknown tenant={tenant_id} action=build elapsed_ms=0")
        
        return {
            "success": True,
            "response": response,
            "action_type": "provision",
            "llm_generated": False,
            "model": "stub"
        }
    
    def _handle_unknown(self, message: str, tenant_id: str, dry_run: bool, remaining_time: float = None) -> Dict[str, Any]:
        """Handle unknown or general requests"""
        # Check deadline before processing
        if remaining_time is not None and remaining_time <= 0:
            logger.warning(f"Request deadline exceeded in _handle_unknown (tenant: {tenant_id})")
            return {
                "success": False,
                "response": "Request exceeded processing time limit.",
                "action_type": "timeout",
                "llm_generated": False
            }
        
        # For now, return a simple response
        response = f"I received your message: '{message}'. How can I help you today?"
        
        logger.info(f"ask.model.done request_id=unknown tenant={tenant_id} action=build elapsed_ms=0")
        
        return {
            "success": True,
            "response": response,
            "action_type": "unknown",
            "llm_generated": False,
            "model": "stub"
        }
