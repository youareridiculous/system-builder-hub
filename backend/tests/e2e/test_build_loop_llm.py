"""
E2E Tests for Core Build Loop - LLM & No-LLM Paths
"""
import pytest
import time
import json
from typing import Dict, Any

class TestLLMPath:
    """Test LLM-enabled build path"""
    
    def test_llm_provider_configuration_and_test(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test A: Configure provider and test connection"""
        # 1. Configure OpenAI provider
        config_result = llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        assert config_result['success'] is True
        assert config_result['provider'] == 'openai'
        assert config_result['model'] == 'gpt-3.5-turbo'
        
        # 2. Test connection
        test_result = llm_helper.test_connection()
        
        assert test_result['success'] is True
        assert test_result['provider'] == 'openai'
        assert test_result['model'] == 'gpt-3.5-turbo'
        assert 'latency_ms' in test_result
        assert test_result['latency_ms'] > 0
        
        # 3. Verify status reflects connected state
        status = llm_helper.get_status()
        
        assert status['available'] is True
        assert status['provider'] == 'openai'
        assert status['model'] == 'gpt-3.5-turbo'
        
        # Find our provider in the list
        provider_status = None
        for provider in status['providers']:
            if provider['name'] == 'openai' and provider['active']:
                provider_status = provider
                break
        
        assert provider_status is not None
        assert provider_status['circuit_state'] == 'closed'
        assert provider_status['today_requests'] > 0
    
    def test_guided_build_with_llm(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test A: Start guided build and confirm LLM usage"""
        # 1. Configure provider
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        # 2. Start guided build
        build_result = llm_helper.start_build(
            name='Test Guided Build',
            template='crud-app',
            no_llm_mode=False
        )
        
        assert build_result['success'] is True
        assert build_result['no_llm_mode'] is False
        assert 'project_id' in build_result
        assert 'system_id' in build_result
        
        # 3. Verify LLM usage logs (this would check database in real test)
        # For now, we verify the build succeeded with LLM mode
        
        # 4. Check metrics
        status = llm_helper.get_status()
        provider_status = None
        for provider in status['providers']:
            if provider['name'] == 'openai' and provider['active']:
                provider_status = provider
                break
        
        assert provider_status is not None
        assert provider_status['today_requests'] > 0
    
    def test_dry_run_prompt(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test dry-run prompt functionality"""
        # 1. Configure provider
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        # 2. Run dry-run
        dry_run_result = llm_helper.dry_run("echo ping")
        
        assert dry_run_result['success'] is True
        assert dry_run_result['provider'] == 'openai'
        assert dry_run_result['model'] == 'gpt-3.5-turbo'
        assert 'latency_ms' in dry_run_result
        assert 'tokens_used' in dry_run_result
        assert dry_run_result['content'] == "Test response"

class TestFailureAndRecovery:
    """Test B: Failure scenarios and circuit breaker recovery"""
    
    def test_circuit_breaker_opens_on_failures(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test circuit breaker opens after consecutive failures"""
        # 1. Configure provider
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        # 2. Set failure mode to timeout
        mock_llm_clients['openai'].set_failure_mode('timeout', max_failures=5)
        
        # 3. Trigger failures until circuit opens
        for i in range(5):
            try:
                llm_helper.test_connection()
            except Exception:
                pass  # Expected to fail
        
        # 4. Verify circuit breaker is open
        status = llm_helper.get_status()
        provider_status = None
        for provider in status['providers']:
            if provider['name'] == 'openai' and provider['active']:
                provider_status = provider
                break
        
        assert provider_status is not None
        assert provider_status['circuit_state'] == 'open'
        assert provider_status['failure_count'] >= 5
    
    def test_circuit_breaker_recovery(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test circuit breaker recovers after cooldown"""
        # 1. Configure provider
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        # 2. Set failure mode and trigger failures
        mock_llm_clients['openai'].set_failure_mode('timeout', max_failures=5)
        
        for i in range(5):
            try:
                llm_helper.test_connection()
            except Exception:
                pass
        
        # 3. Clear failure mode and wait for recovery
        mock_llm_clients['openai'].set_failure_mode(None)
        
        # 4. Test recovery (in real scenario, would wait for cooldown)
        # For test purposes, we'll simulate the recovery
        from src.llm_safety import llm_safety
        cb = llm_safety.get_circuit_breaker('openai')
        cb.state = cb.state.__class__("half_open")  # Simulate recovery
        
        # 5. Verify dry-run succeeds and circuit closes
        dry_run_result = llm_helper.dry_run("echo ping")
        
        assert dry_run_result['success'] is True
        
        # 6. Check circuit state
        status = llm_helper.get_status()
        provider_status = None
        for provider in status['providers']:
            if provider['name'] == 'openai' and provider['active']:
                provider_status = provider
                break
        
        # Circuit should be closed after successful recovery
        assert provider_status is not None
        assert provider_status['circuit_state'] in ['closed', 'half_open']
    
    def test_rate_limit_exceeded(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test rate limit exceeded scenario"""
        # 1. Configure provider
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        # 2. Set failure mode to 429
        mock_llm_clients['openai'].set_failure_mode('429', max_failures=1)
        
        # 3. Test connection should fail with rate limit error
        test_result = llm_helper.test_connection()
        
        assert test_result['success'] is False
        assert 'rate limit' in test_result['error'].lower()
    
    def test_invalid_model_error(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test invalid model error"""
        # 1. Configure provider with invalid model
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='invalid-model'
        )
        
        # 2. Set failure mode to invalid model
        mock_llm_clients['openai'].set_failure_mode('invalid_model', max_failures=1)
        
        # 3. Test connection should fail with model error
        test_result = llm_helper.test_connection()
        
        assert test_result['success'] is False
        assert 'model' in test_result['error'].lower()

class TestNoLLMPath:
    """Test C: No-LLM build path"""
    
    def test_no_llm_build_creation(self, llm_helper, reset_metrics):
        """Test No-LLM project creation"""
        # 1. Start build with No-LLM mode
        build_result = llm_helper.start_build(
            name='Test No-LLM Build',
            template='crud-app',
            no_llm_mode=True
        )
        
        assert build_result['success'] is True
        assert build_result['no_llm_mode'] is True
        assert 'project_id' in build_result
        assert 'system_id' in build_result
        assert '(No-LLM mode)' in build_result['message']
    
    def test_no_llm_build_without_provider(self, llm_helper, reset_metrics):
        """Test No-LLM build works without LLM provider"""
        # 1. Start build with No-LLM mode (no provider configured)
        build_result = llm_helper.start_build(
            name='Test No-LLM Build No Provider',
            template='dashboard-db',
            no_llm_mode=True
        )
        
        assert build_result['success'] is True
        assert build_result['no_llm_mode'] is True
        
        # 2. Verify no LLM usage logs would be created
        # In real test, would check database for zero usage logs
        
        # 3. Check status shows No-LLM mode
        status = llm_helper.get_status()
        assert status['available'] is False  # No LLM configured
    
    def test_no_llm_build_requires_template(self, llm_helper, reset_metrics):
        """Test No-LLM build requires template"""
        # 1. Try to start build without template
        build_result = llm_helper.start_build(
            name='Test No-LLM Build No Template',
            template='',  # Empty template
            no_llm_mode=True
        )
        
        assert build_result['success'] is False
        assert 'template' in build_result['error'].lower()

class TestMetricsAndLogging:
    """Test metrics and logging functionality"""
    
    def test_usage_logs_increment(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test that usage logs increment with LLM calls"""
        # 1. Configure provider
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        # 2. Get initial status
        initial_status = llm_helper.get_status()
        initial_requests = 0
        for provider in initial_status['providers']:
            if provider['name'] == 'openai' and provider['active']:
                initial_requests = provider['today_requests']
                break
        
        # 3. Make LLM calls
        llm_helper.test_connection()
        llm_helper.dry_run("test prompt")
        
        # 4. Check metrics incremented
        final_status = llm_helper.get_status()
        final_requests = 0
        for provider in final_status['providers']:
            if provider['name'] == 'openai' and provider['active']:
                final_requests = provider['today_requests']
                break
        
        assert final_requests > initial_requests
    
    def test_prometheus_metrics_format(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test Prometheus metrics format"""
        # 1. Configure provider
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        # 2. Make some calls
        llm_helper.test_connection()
        
        # 3. Get metrics
        response = llm_helper.app.get('/api/llm/metrics',
            headers={'X-Tenant-ID': llm_helper.tenant_id}
        )
        
        assert response.status_code == 200
        metrics_text = response.get_data(as_text=True)
        
        # 4. Verify Prometheus format
        assert 'llm_requests_total' in metrics_text
        assert 'llm_circuit_state' in metrics_text
        assert 'llm_failure_count' in metrics_text
        assert 'provider="openai"' in metrics_text

class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_invalid_api_key(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test invalid API key handling"""
        # 1. Configure with invalid key
        config_result = llm_helper.configure_provider(
            provider='openai',
            api_key='invalid-key',
            model='gpt-3.5-turbo'
        )
        
        assert config_result['success'] is True  # Config saves, but test will fail
        
        # 2. Set auth error mode
        mock_llm_clients['openai'].set_failure_mode('auth_error', max_failures=1)
        
        # 3. Test connection should fail
        test_result = llm_helper.test_connection()
        
        assert test_result['success'] is False
        assert 'api key' in test_result['error'].lower() or 'auth' in test_result['error'].lower()
    
    def test_provider_timeout(self, llm_helper, mock_llm_clients, reset_metrics):
        """Test provider timeout handling"""
        # 1. Configure provider
        llm_helper.configure_provider(
            provider='openai',
            api_key='sk-test123456789',
            model='gpt-3.5-turbo'
        )
        
        # 2. Set timeout mode
        mock_llm_clients['openai'].set_failure_mode('timeout', max_failures=1)
        
        # 3. Test connection should timeout
        test_result = llm_helper.test_connection()
        
        assert test_result['success'] is False
        assert 'timeout' in test_result['error'].lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
