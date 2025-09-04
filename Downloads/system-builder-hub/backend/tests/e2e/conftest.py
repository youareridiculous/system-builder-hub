"""
E2E Test Configuration and Fixtures
"""
import pytest
import os
import json
import time
import sqlite3
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

# Add src to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

class FakeOpenAIClient:
    """Fake OpenAI client for testing with controllable outcomes"""
    
    def __init__(self, api_key: str = "sk-test123456789"):
        self.api_key = api_key
        self.calls = []
        self.failure_mode = None  # None, 'timeout', '429', 'invalid_model', 'auth_error'
        self.failure_count = 0
        self.max_failures = 0
    
    def set_failure_mode(self, mode: str, max_failures: int = 0):
        """Set failure mode for testing"""
        self.failure_mode = mode
        self.max_failures = max_failures
        self.failure_count = 0
    
    def ChatCompletion(self):
        """Return fake ChatCompletion object"""
        return self
    
    def create(self, **kwargs):
        """Fake completion creation"""
        self.calls.append(kwargs)
        
        # Check failure conditions
        if self.failure_mode and self.failure_count < self.max_failures:
            self.failure_count += 1
            
            if self.failure_mode == 'timeout':
                import time
                time.sleep(10)  # Simulate timeout
                raise Exception("Request timeout")
            
            elif self.failure_mode == '429':
                raise Exception("Rate limit exceeded")
            
            elif self.failure_mode == 'invalid_model':
                raise Exception("Model not found")
            
            elif self.failure_mode == 'auth_error':
                raise Exception("Invalid API key")
        
        # Return successful response
        return Mock(
            choices=[Mock(message=Mock(content="Test response"))],
            usage=Mock(total_tokens=10)
        )

class FakeAnthropicClient:
    """Fake Anthropic client for testing"""
    
    def __init__(self, api_key: str = "sk-ant-test123456789"):
        self.api_key = api_key
        self.calls = []
    
    def messages(self):
        return self
    
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return Mock(
            content=[Mock(text="Test response")],
            usage=Mock(input_tokens=5, output_tokens=5)
        )

class FakeGroqClient:
    """Fake Groq client for testing"""
    
    def __init__(self, api_key: str = "gsk_test123456789"):
        self.api_key = api_key
        self.calls = []
    
    def chat(self):
        return self
    
    def completions(self):
        return self
    
    def create(self, **kwargs):
        self.calls.append(kwargs)
        return Mock(
            choices=[Mock(message=Mock(content="Test response"))],
            usage=Mock(total_tokens=10)
        )

class TestDatabase:
    """Test database helper"""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.init_db()
    
    def init_db(self):
        """Initialize test database"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_provider_configs (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                api_key_encrypted TEXT NOT NULL,
                default_model TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                last_tested TIMESTAMP,
                test_latency_ms INTEGER,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_usage_logs (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                provider_config_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                tokens_used INTEGER,
                latency_ms INTEGER,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP NOT NULL,
                metadata TEXT
            )
        """)
        
        self.conn.commit()
    
    def get_usage_logs(self, tenant_id: str) -> list:
        """Get usage logs for tenant"""
        cursor = self.conn.execute("""
            SELECT * FROM llm_usage_logs 
            WHERE tenant_id = ?
            ORDER BY created_at DESC
        """, (tenant_id,))
        
        return [dict(zip([col[0] for col in cursor.description], row)) 
                for row in cursor.fetchall()]
    
    def get_provider_configs(self, tenant_id: str) -> list:
        """Get provider configs for tenant"""
        cursor = self.conn.execute("""
            SELECT * FROM llm_provider_configs 
            WHERE tenant_id = ?
            ORDER BY updated_at DESC
        """, (tenant_id,))
        
        return [dict(zip([col[0] for col in cursor.description], row)) 
                for row in cursor.fetchall()]
    
    def clear_data(self):
        """Clear all test data"""
        self.conn.execute("DELETE FROM llm_usage_logs")
        self.conn.execute("DELETE FROM llm_provider_configs")
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()

@pytest.fixture
def test_db():
    """Test database fixture"""
    db = TestDatabase()
    yield db
    db.close()

@pytest.fixture
def fake_openai_client():
    """Fake OpenAI client fixture"""
    return FakeOpenAIClient()

@pytest.fixture
def fake_anthropic_client():
    """Fake Anthropic client fixture"""
    return FakeAnthropicClient()

@pytest.fixture
def fake_groq_client():
    """Fake Groq client fixture"""
    return FakeGroqClient()

@pytest.fixture
def test_tenant_id():
    """Test tenant ID fixture"""
    return f"test_tenant_{int(time.time())}"

@pytest.fixture
def llm_secret_key():
    """LLM secret key fixture"""
    return "dGVzdC1rZXktZm9yLXRlc3Rpbmctc2VjcmV0cy0xMjM="  # 32 bytes

@pytest.fixture
def mock_llm_clients(fake_openai_client, fake_anthropic_client, fake_groq_client):
    """Mock LLM clients fixture"""
    with patch('openai.ChatCompletion', fake_openai_client.ChatCompletion), \
         patch('anthropic.Anthropic', return_value=fake_anthropic_client), \
         patch('groq.Groq', return_value=fake_groq_client):
        yield {
            'openai': fake_openai_client,
            'anthropic': fake_anthropic_client,
            'groq': fake_groq_client
        }

@pytest.fixture
def reset_metrics():
    """Reset metrics between tests"""
    # Clear any global metrics state
    from src.llm_safety import llm_safety
    llm_safety.circuit_breakers.clear()
    llm_safety.rate_limiters.clear()
    yield

@pytest.fixture
def test_app():
    """Test Flask app fixture"""
    from src.app import create_app
    app = create_app()
    app.config['TESTING'] = True
    app.config['BOOT_MODE'] = 'safe'
    
    with app.test_client() as client:
        yield client

class LLMTestHelper:
    """Helper class for LLM testing"""
    
    def __init__(self, test_app, test_tenant_id: str):
        self.app = test_app
        self.tenant_id = test_tenant_id
    
    def configure_provider(self, provider: str, api_key: str, model: str) -> Dict[str, Any]:
        """Configure LLM provider as UI does"""
        response = self.app.post('/api/llm/provider/configure', 
            json={
                'provider': provider,
                'api_key': api_key,
                'default_model': model
            },
            headers={'X-Tenant-ID': self.tenant_id}
        )
        return response.get_json()
    
    def test_connection(self) -> Dict[str, Any]:
        """Test LLM connection"""
        response = self.app.post('/api/llm/test',
            headers={'X-Tenant-ID': self.tenant_id}
        )
        return response.get_json()
    
    def get_status(self) -> Dict[str, Any]:
        """Get LLM status"""
        response = self.app.get('/api/llm/status',
            headers={'X-Tenant-ID': self.tenant_id}
        )
        return response.get_json()
    
    def dry_run(self, prompt: str = "echo ping") -> Dict[str, Any]:
        """Run dry-run prompt"""
        response = self.app.post('/api/llm/dry-run',
            json={'prompt': prompt},
            headers={'X-Tenant-ID': self.tenant_id}
        )
        return response.get_json()
    
    def start_build(self, name: str, template: str, no_llm_mode: bool = False) -> Dict[str, Any]:
        """Start a build"""
        response = self.app.post('/api/build/start',
            json={
                'name': name,
                'template_slug': template,
                'no_llm_mode': no_llm_mode
            },
            headers={'X-Tenant-ID': self.tenant_id}
        )
        return response.get_json()

@pytest.fixture
def llm_helper(test_app, test_tenant_id):
    """LLM test helper fixture"""
    return LLMTestHelper(test_app, test_tenant_id)
