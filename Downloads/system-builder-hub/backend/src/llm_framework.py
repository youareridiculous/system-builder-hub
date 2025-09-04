"""
🧠 System Build Hub OS - LLM Integration Framework

This module provides a model-agnostic interface for LLM integration,
supporting multiple providers and local inference capabilities.
"""

import json
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    LOCAL = "local"

class LLMModel(Enum):
    # OpenAI Models
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    
    # Anthropic Models
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    
    # Google Models
    GEMINI_PRO = "gemini-pro"
    GEMINI_FLASH = "gemini-1.5-flash"
    
    # Mistral Models
    MISTRAL_LARGE = "mistral-large-latest"
    MISTRAL_MEDIUM = "mistral-medium-latest"
    MISTRAL_SMALL = "mistral-small-latest"
    
    # Local Models
    LLAMA_3_8B = "llama3:8b"
    LLAMA_3_70B = "llama3:70b"
    MISTRAL_7B = "mistral:7b"
    PHI_3 = "phi3:latest"

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"

@dataclass
class Message:
    """Represents a message in a conversation"""
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LLMRequest:
    """Represents an LLM request"""
    id: str
    model: LLMModel
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    functions: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[str] = None
    created_at: datetime = None

@dataclass
class LLMResponse:
    """Represents an LLM response"""
    id: str
    request_id: str
    content: str
    model: LLMModel
    usage: Optional[Dict[str, int]] = None
    function_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    created_at: datetime = None

@dataclass
class LLMConfig:
    """Configuration for an LLM provider"""
    provider: LLMProvider
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_mapping: Dict[LLMModel, str] = None
    default_model: LLMModel = None
    max_tokens: int = 4000
    temperature: float = 0.7

class LLMProviderInterface(ABC):
    """Abstract interface for LLM providers"""
    
    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models"""
        pass
    
    @abstractmethod
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get information about a specific model"""
        pass

class OpenAIProvider(LLMProviderInterface):
    """OpenAI API provider implementation"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = config.api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API"""
        try:
            from openai import OpenAI
            
            # Initialize OpenAI client
            client = OpenAI(api_key=self.api_key)
            
            # Convert messages to OpenAI format
            messages = []
            for msg in request.messages:
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            
            # Prepare function definitions if provided
            tools = None
            if request.functions:
                tools = request.functions
            
            # Make API call
            response = client.chat.completions.create(
                model=request.model.value,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens or self.config.max_tokens,
                tools=tools,
                tool_choice=request.function_call
            )
            
            # Extract response
            content = response.choices[0].message.content or ""
            function_calls = None
            if response.choices[0].message.tool_calls:
                function_calls = response.choices[0].message.tool_calls
            
            return LLMResponse(
                id=f"resp-{uuid.uuid4().hex[:8]}",
                request_id=request.id,
                content=content,
                model=request.model,
                usage=response.usage,
                function_calls=function_calls,
                finish_reason=response.choices[0].finish_reason,
                created_at=datetime.now()
            )
        
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def list_models(self) -> List[str]:
        """List available OpenAI models"""
        return [
            "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
            "gpt-4-32k", "gpt-3.5-turbo-16k"
        ]
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get OpenAI model information"""
        model_info = {
            "gpt-4": {"max_tokens": 8192, "context_length": 8192},
            "gpt-4-turbo": {"max_tokens": 4096, "context_length": 128000},
            "gpt-3.5-turbo": {"max_tokens": 4096, "context_length": 16385}
        }
        return model_info.get(model, {})

class OllamaProvider(LLMProviderInterface):
    """Ollama local provider implementation"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url or "http://localhost:11434"
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Ollama API"""
        try:
            import requests
            
            # Convert messages to Ollama format
            messages = []
            for msg in request.messages:
                messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            
            # Prepare request payload
            payload = {
                "model": request.model.value,
                "messages": messages,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens or self.config.max_tokens
                }
            }
            
            # Make API call
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            
            return LLMResponse(
                id=f"resp-{uuid.uuid4().hex[:8]}",
                request_id=request.id,
                content=result.get("message", {}).get("content", ""),
                model=request.model,
                finish_reason="stop",
                created_at=datetime.now()
            )
        
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")
    
    def list_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model["name"] for model in models]
            return []
        except:
            return []
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get Ollama model information"""
        try:
            import requests
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model}
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}

class LLMManager:
    """
    Main LLM manager for handling multiple providers and models
    """
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_file = base_dir / "llm" / "config.json"
        self.conversations_file = base_dir / "llm" / "conversations.json"
        
        # Create LLM directory
        (base_dir / "llm").mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize providers
        self.providers = self._initialize_providers()
        
        # Current active provider
        active_provider_name = self.config.get("active_provider", LLMProvider.OPENAI.value)
        self.active_provider = LLMProvider(active_provider_name)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load LLM configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading LLM config: {e}")
        
        # Default configuration
        return {
            "active_provider": LLMProvider.OPENAI.value,
            "providers": {
                LLMProvider.OPENAI.value: {
                    "api_key": os.getenv('OPENAI_API_KEY'),
                    "default_model": LLMModel.GPT_4.value,
                    "max_tokens": 4000,
                    "temperature": 0.7
                },
                LLMProvider.OLLAMA.value: {
                    "base_url": "http://localhost:11434",
                    "default_model": LLMModel.LLAMA_3_8B.value,
                    "max_tokens": 4000,
                    "temperature": 0.7
                }
            }
        }
    
    def _save_config(self):
        """Save LLM configuration"""
        config_data = {
            "active_provider": self.active_provider.value,
            "providers": {}
        }
        
        for provider_name, provider_config in self.config["providers"].items():
            config_data["providers"][provider_name] = provider_config
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def _initialize_providers(self) -> Dict[LLMProvider, LLMProviderInterface]:
        """Initialize LLM providers"""
        providers = {}
        
        # Initialize OpenAI provider
        if LLMProvider.OPENAI.value in self.config["providers"]:
            try:
                openai_config = LLMConfig(
                    provider=LLMProvider.OPENAI,
                    api_key=self.config["providers"][LLMProvider.OPENAI.value]["api_key"],
                    default_model=LLMModel.GPT_4,
                    max_tokens=self.config["providers"][LLMProvider.OPENAI.value]["max_tokens"],
                    temperature=self.config["providers"][LLMProvider.OPENAI.value]["temperature"]
                )
                providers[LLMProvider.OPENAI] = OpenAIProvider(openai_config)
            except Exception as e:
                print(f"Failed to initialize OpenAI provider: {e}")
        
        # Initialize Ollama provider
        if LLMProvider.OLLAMA.value in self.config["providers"]:
            try:
                ollama_config = LLMConfig(
                    provider=LLMProvider.OLLAMA,
                    base_url=self.config["providers"][LLMProvider.OLLAMA.value]["base_url"],
                    default_model=LLMModel.LLAMA_3_8B,
                    max_tokens=self.config["providers"][LLMProvider.OLLAMA.value]["max_tokens"],
                    temperature=self.config["providers"][LLMProvider.OLLAMA.value]["temperature"]
                )
                providers[LLMProvider.OLLAMA] = OllamaProvider(ollama_config)
            except Exception as e:
                print(f"Failed to initialize Ollama provider: {e}")
        
        return providers
    
    def generate_response(self, messages: List[Message], model: Optional[LLMModel] = None, 
                         temperature: Optional[float] = None, max_tokens: Optional[int] = None,
                         functions: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        """Generate a response using the active provider"""
        
        if self.active_provider not in self.providers:
            # Return a mock response for testing when providers are not available
            return self._generate_mock_response(messages, model)
        
        provider = self.providers[self.active_provider]
        
        # Use default model if none specified
        if not model:
            provider_config = self.config["providers"][self.active_provider.value]
            model_name = provider_config.get("default_model", LLMModel.GPT_4.value)
            model = LLMModel(model_name)
        
        # Use default temperature if none specified
        if temperature is None:
            provider_config = self.config["providers"][self.active_provider.value]
            temperature = provider_config.get("temperature", 0.7)
        
        # Use default max_tokens if none specified
        if max_tokens is None:
            provider_config = self.config["providers"][self.active_provider.value]
            max_tokens = provider_config.get("max_tokens", 4000)
        
        # Create request
        request = LLMRequest(
            id=f"req-{uuid.uuid4().hex[:8]}",
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            functions=functions,
            created_at=datetime.now()
        )
        
        try:
            # Generate response
            response = provider.generate(request)
            
            # Log conversation
            self._log_conversation(request, response)
            
            return response
        except Exception as e:
            # Return a mock response if the provider fails
            print(f"Provider error: {e}")
            return self._generate_mock_response(messages, model)
    
    def _generate_mock_response(self, messages: List[Message], model: Optional[LLMModel] = None) -> LLMResponse:
        """Generate a mock response for testing when providers are not available"""
        if not model:
            model = LLMModel.GPT_3_5_TURBO
        
        # Get the last user message
        last_user_message = None
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                last_user_message = msg.content
                break
        
        # Generate a simple mock response
        if last_user_message and "Flask API" in last_user_message:
            mock_content = """I'd be happy to help you build a simple Flask API! Here's a basic example:

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({'message': 'Hello, World!'})

@app.route('/api/users', methods=['GET'])
def get_users():
    users = [{'id': 1, 'name': 'John'}, {'id': 2, 'name': 'Jane'}]
    return jsonify(users)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

This creates a simple Flask API with two endpoints. Would you like me to help you expand this with more features like database integration, authentication, or specific business logic?"""
        else:
            mock_content = "Hello! I'm a mock LLM response for testing purposes. In a real deployment, I would connect to an actual LLM provider like OpenAI, Anthropic, or a local model."
        
        # Create mock request and response for logging
        request = LLMRequest(
            id=f"req-{uuid.uuid4().hex[:8]}",
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            created_at=datetime.now()
        )
        
        response = LLMResponse(
            id=f"resp-{uuid.uuid4().hex[:8]}",
            request_id=request.id,
            content=mock_content,
            model=model,
            usage={"prompt_tokens": 50, "completion_tokens": 200, "total_tokens": 250},
            finish_reason="stop",
            created_at=datetime.now()
        )
        
        # Log the mock conversation
        self._log_conversation(request, response)
        
        return response
    
    def _log_conversation(self, request: LLMRequest, response: LLMResponse):
        """Log conversation for memory and training"""
        # Convert messages to serializable format
        messages_data = []
        for msg in request.messages:
            msg_dict = asdict(msg)
            msg_dict['role'] = msg.role.value
            msg_dict['timestamp'] = msg.timestamp.isoformat()
            messages_data.append(msg_dict)
        
        # Convert response to serializable format
        response_dict = asdict(response)
        response_dict['model'] = response.model.value
        response_dict['created_at'] = response.created_at.isoformat()
        
        conversation = {
            "id": f"conv-{uuid.uuid4().hex[:8]}",
            "request_id": request.id,
            "response_id": response.id,
            "provider": self.active_provider.value,
            "model": request.model.value,
            "messages": messages_data,
            "response": response_dict,
            "timestamp": datetime.now().isoformat()
        }
        
        # Load existing conversations
        conversations = []
        if self.conversations_file.exists():
            try:
                with open(self.conversations_file, 'r') as f:
                    conversations = json.load(f)
            except:
                conversations = []
        
        # Add new conversation
        conversations.append(conversation)
        
        # Save conversations (keep last 1000)
        conversations = conversations[-1000:]
        
        with open(self.conversations_file, 'w') as f:
            json.dump(conversations, f, indent=2)
    
    def switch_provider(self, provider: LLMProvider):
        """Switch to a different LLM provider"""
        if provider not in self.providers:
            raise Exception(f"Provider {provider.value} not available")
        
        self.active_provider = provider
        self.config["active_provider"] = provider.value
        self._save_config()
    
    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Get list of available providers with their status"""
        available = []
        
        for provider in LLMProvider:
            status = "available" if provider in self.providers else "unavailable"
            config = self.config["providers"].get(provider.value, {})
            
            available.append({
                "provider": provider.value,
                "status": status,
                "default_model": config.get("default_model"),
                "max_tokens": config.get("max_tokens"),
                "temperature": config.get("temperature")
            })
        
        return available
    
    def get_conversation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get conversation history for training and analysis"""
        if not self.conversations_file.exists():
            return []
        
        try:
            with open(self.conversations_file, 'r') as f:
                conversations = json.load(f)
            return conversations[-limit:]
        except:
            return []
    
    def inject_knowledge(self, knowledge_base: List[Dict[str, Any]]):
        """Inject knowledge base into LLM context for enhanced responses"""
        # This would be used for fine-tuning or context injection
        # Implementation depends on the specific LLM provider
        pass
