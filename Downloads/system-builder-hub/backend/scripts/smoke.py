#!/usr/bin/env python3
"""
Smoke Test Script for System Builder Hub
Used for CI/CD pre-deploy gates and health verification
"""
import os
import sys
import requests
import json
from typing import Dict, Any, List

# Configuration
BASE_URL = os.getenv('SMOKE_BASE_URL', 'http://localhost:5001')
TIMEOUT = int(os.getenv('SMOKE_TIMEOUT', '10'))

class SmokeTest:
    """Smoke test runner for SBH"""
    
    def __init__(self, base_url: str = BASE_URL, timeout: int = TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.results = []
    
    def test_endpoint(self, path: str, expected_status: int = 200, 
                     check_json: bool = True, name: str = None) -> Dict[str, Any]:
        """Test an endpoint and return results"""
        if name is None:
            name = path
        
        url = f"{self.base_url}{path}"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            
            result = {
                'name': name,
                'url': url,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'success': response.status_code == expected_status,
                'error': None
            }
            
            if check_json and response.status_code == 200:
                try:
                    result['response'] = response.json()
                except json.JSONDecodeError:
                    result['error'] = 'Invalid JSON response'
                    result['success'] = False
            
            return result
            
        except requests.exceptions.RequestException as e:
            return {
                'name': name,
                'url': url,
                'status_code': None,
                'expected_status': expected_status,
                'success': False,
                'error': str(e)
            }
    
    def test_health(self) -> Dict[str, Any]:
        """Test health endpoint"""
        return self.test_endpoint('/healthz', name='Health Check')
    
    def test_readiness(self) -> Dict[str, Any]:
        """Test readiness endpoint"""
        return self.test_endpoint('/readiness', name='Readiness Check')
    
    def test_llm_status(self) -> Dict[str, Any]:
        """Test LLM status endpoint"""
        return self.test_endpoint('/api/llm/status', name='LLM Status')
    
    def test_dashboard(self) -> Dict[str, Any]:
        """Test dashboard endpoint"""
        return self.test_endpoint('/dashboard', name='Dashboard')
    
    def test_llm_connection(self) -> Dict[str, Any]:
        """Test LLM connection if configured"""
        try:
            # First check if LLM is configured
            status_response = requests.get(f"{self.base_url}/api/llm/status", timeout=self.timeout)
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data.get('available', False):
                    # Test LLM connection
                    test_response = requests.post(
                        f"{self.base_url}/api/llm/test",
                        json={},
                        timeout=self.timeout
                    )
                    
                    return {
                        'name': 'LLM Connection Test',
                        'url': f"{self.base_url}/api/llm/test",
                        'status_code': test_response.status_code,
                        'expected_status': 200,
                        'success': test_response.status_code == 200,
                        'error': None
                    }
                else:
                    return {
                        'name': 'LLM Connection Test',
                        'url': f"{self.base_url}/api/llm/test",
                        'status_code': None,
                        'expected_status': 200,
                        'success': True,  # Skip if not configured
                        'error': 'LLM not configured (skipping)'
                    }
            else:
                return {
                    'name': 'LLM Connection Test',
                    'url': f"{self.base_url}/api/llm/test",
                    'status_code': None,
                    'expected_status': 200,
                    'success': False,
                    'error': f'Failed to get LLM status: {status_response.status_code}'
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'name': 'LLM Connection Test',
                'url': f"{self.base_url}/api/llm/test",
                'status_code': None,
                'expected_status': 200,
                'success': False,
                'error': str(e)
            }
    
    def run_all_tests(self) -> List[Dict[str, Any]]:
        """Run all smoke tests"""
        print(f"🚀 Running smoke tests against {self.base_url}")
        print("=" * 60)
        
        tests = [
            self.test_health,
            self.test_readiness,
            self.test_llm_status,
            self.test_dashboard,
            self.test_llm_connection
        ]
        
        results = []
        for test_func in tests:
            result = test_func()
            results.append(result)
            
            # Print result
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} {result['name']}")
            
            if result['error']:
                print(f"   Error: {result['error']}")
            elif result['status_code']:
                print(f"   Status: {result['status_code']}")
        
        return results
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("�� SMOKE TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED")
            return 0
        else:
            print("⚠️ SOME TESTS FAILED")
            return 1

def main():
    """Main smoke test function"""
    # Parse command line arguments
    base_url = os.getenv('SMOKE_BASE_URL', 'http://localhost:5001')
    timeout = int(os.getenv('SMOKE_TIMEOUT', '10'))
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    # Run smoke tests
    smoke = SmokeTest(base_url, timeout)
    results = smoke.run_all_tests()
    
    # Print summary and exit
    exit_code = smoke.print_summary(results)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
