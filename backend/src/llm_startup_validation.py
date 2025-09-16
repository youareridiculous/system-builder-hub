"""
LLM Startup Validation - Check LLM provider availability on startup
"""
import logging
import time
from typing import Dict, Any, List
from llm_provider_service import llm_provider_service

logger = logging.getLogger(__name__)

class LLMStartupValidator:
    """Validate LLM provider configurations on startup"""
    
    def __init__(self):
        self.validation_results = []
    
    def validate_all_providers(self) -> Dict[str, Any]:
        """Validate all configured LLM providers"""
        logger.info("🔍 Starting LLM provider validation...")
        
        try:
            # Get all active configurations
            with llm_provider_service._init_db() as conn:
                cursor = conn.execute("""
                    SELECT tenant_id, provider, default_model, last_tested, test_latency_ms
                    FROM llm_provider_configs 
                    WHERE is_active = 1
                """)
                
                configs = cursor.fetchall()
            
            if not configs:
                logger.info("ℹ️ No LLM providers configured")
                return {
                    'status': 'no_providers',
                    'message': 'No LLM providers configured',
                    'results': []
                }
            
            logger.info(f"🔍 Found {len(configs)} active LLM provider configurations")
            
            # Test each configuration
            for config in configs:
                tenant_id, provider, model, last_tested, latency = config
                result = self._validate_provider(tenant_id, provider, model)
                self.validation_results.append(result)
            
            # Summary
            successful = [r for r in self.validation_results if r['success']]
            failed = [r for r in self.validation_results if not r['success']]
            
            summary = {
                'status': 'validation_complete',
                'total_providers': len(configs),
                'successful': len(successful),
                'failed': len(failed),
                'results': self.validation_results
            }
            
            if failed:
                logger.warning(f"⚠️ {len(failed)} LLM providers failed validation:")
                for result in failed:
                    logger.warning(f"  - {result['provider']} ({result['tenant_id']}): {result['error']}")
            else:
                logger.info(f"✅ All {len(successful)} LLM providers validated successfully")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ LLM validation failed: {e}")
            return {
                'status': 'validation_error',
                'error': str(e),
                'results': []
            }
    
    def _validate_provider(self, tenant_id: str, provider: str, model: str) -> Dict[str, Any]:
        """Validate a single LLM provider"""
        logger.info(f"🔍 Testing {provider} for tenant {tenant_id}")
        
        start_time = time.time()
        
        try:
            # Test connection
            result = llm_provider_service.test_connection(tenant_id, provider)
            
            validation_time = time.time() - start_time
            
            validation_result = {
                'tenant_id': tenant_id,
                'provider': provider,
                'model': model,
                'success': result['success'],
                'latency_ms': result.get('latency_ms'),
                'validation_time_ms': int(validation_time * 1000),
                'error': result.get('error'),
                'timestamp': time.time()
            }
            
            if result['success']:
                logger.info(f"✅ {provider} ({tenant_id}): {result.get('latency_ms', 0)}ms")
            else:
                logger.warning(f"⚠️ {provider} ({tenant_id}): {result.get('error', 'Unknown error')}")
            
            return validation_result
            
        except Exception as e:
            validation_time = time.time() - start_time
            logger.error(f"❌ {provider} ({tenant_id}): {e}")
            
            return {
                'tenant_id': tenant_id,
                'provider': provider,
                'model': model,
                'success': False,
                'latency_ms': None,
                'validation_time_ms': int(validation_time * 1000),
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary for health checks"""
        if not self.validation_results:
            return {
                'llm_validation': 'not_run',
                'providers_configured': 0,
                'providers_working': 0
            }
        
        working = [r for r in self.validation_results if r['success']]
        
        return {
            'llm_validation': 'complete',
            'providers_configured': len(self.validation_results),
            'providers_working': len(working),
            'last_validation': max(r['timestamp'] for r in self.validation_results) if self.validation_results else None
        }

# Global validator instance
llm_startup_validator = LLMStartupValidator()

def run_llm_startup_validation():
    """Run LLM startup validation"""
    return llm_startup_validator.validate_all_providers()

def get_llm_validation_summary():
    """Get LLM validation summary"""
    return llm_startup_validator.get_validation_summary()
