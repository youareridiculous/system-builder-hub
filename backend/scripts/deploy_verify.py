#!/usr/bin/env python3
"""
Deployment Verification Script for System Builder Hub
Runs comprehensive tests against a deployed container to verify functionality
"""
import os
import sys
import time
import subprocess
import requests
import json
from typing import Dict, Any, List, Optional

# Add smoke test functionality
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class DeploymentVerifier:
    """Deployment verification for SBH"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.results = []
    
    def wait_for_service(self, max_wait: int = 60) -> bool:
        """Wait for service to become available"""
        print(f"⏳ Waiting for service at {self.base_url}...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.base_url}/healthz", timeout=5)
                if response.status_code == 200:
                    print(f"✅ Service is available after {time.time() - start_time:.1f}s")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(2)
        
        print(f"❌ Service did not become available within {max_wait}s")
        return False
    
    def test_health_endpoint(self) -> Dict[str, Any]:
        """Test health endpoint with version info"""
        try:
            response = requests.get(f"{self.base_url}/healthz", timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ['status', 'version', 'timestamp']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    return {
                        'name': 'Health Check',
                        'success': False,
                        'error': f'Missing fields: {missing_fields}',
                        'data': data
                    }
                
                # Check version format
                if not data.get('version'):
                    return {
                        'name': 'Health Check',
                        'success': False,
                        'error': 'No version information',
                        'data': data
                    }
                
                return {
                    'name': 'Health Check',
                    'success': True,
                    'data': data,
                    'version': data.get('version'),
                    'version_string': data.get('version_string')
                }
            else:
                return {
                    'name': 'Health Check',
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'data': None
                }
                
        except Exception as e:
            return {
                'name': 'Health Check',
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def test_readiness_endpoint(self) -> Dict[str, Any]:
        """Test readiness endpoint"""
        try:
            response = requests.get(f"{self.base_url}/readiness", timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required fields
                required_fields = ['db', 'llm', 'migrations_applied', 'timestamp']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    return {
                        'name': 'Readiness Check',
                        'success': False,
                        'error': f'Missing fields: {missing_fields}',
                        'data': data
                    }
                
                # Check if service is ready
                if not data.get('db'):
                    return {
                        'name': 'Readiness Check',
                        'success': False,
                        'error': 'Database not ready',
                        'data': data
                    }
                
                return {
                    'name': 'Readiness Check',
                    'success': True,
                    'data': data
                }
            else:
                return {
                    'name': 'Readiness Check',
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'data': None
                }
                
        except Exception as e:
            return {
                'name': 'Readiness Check',
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def test_llm_status(self) -> Dict[str, Any]:
        """Test LLM status endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/llm/status", timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response has expected structure
                if 'available' not in data:
                    return {
                        'name': 'LLM Status',
                        'success': False,
                        'error': 'Invalid response structure',
                        'data': data
                    }
                
                return {
                    'name': 'LLM Status',
                    'success': True,
                    'data': data,
                    'llm_available': data.get('available', False)
                }
            else:
                return {
                    'name': 'LLM Status',
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'data': None
                }
                
        except Exception as e:
            return {
                'name': 'LLM Status',
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def test_ui_build_page(self) -> Dict[str, Any]:
        """Test UI build page loads"""
        try:
            response = requests.get(f"{self.base_url}/ui/build", timeout=self.timeout)
            
            if response.status_code == 200:
                content = response.text
                
                # Check for expected content
                if 'System Builder Hub' in content or 'Start a Build' in content:
                    return {
                        'name': 'UI Build Page',
                        'success': True,
                        'data': {'status_code': response.status_code}
                    }
                else:
                    return {
                        'name': 'UI Build Page',
                        'success': False,
                        'error': 'Page content not as expected',
                        'data': {'status_code': response.status_code}
                    }
            else:
                return {
                    'name': 'UI Build Page',
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'data': None
                }
                
        except Exception as e:
            return {
                'name': 'UI Build Page',
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def test_dashboard_page(self) -> Dict[str, Any]:
        """Test dashboard page loads"""
        try:
            response = requests.get(f"{self.base_url}/dashboard", timeout=self.timeout)
            
            if response.status_code == 200:
                content = response.text
                
                # Check for expected content
                if 'System Builder Hub' in content or 'Dashboard' in content:
                    return {
                        'name': 'Dashboard Page',
                        'success': True,
                        'data': {'status_code': response.status_code}
                    }
                else:
                    return {
                        'name': 'Dashboard Page',
                        'success': False,
                        'error': 'Page content not as expected',
                        'data': {'status_code': response.status_code}
                    }
            else:
                return {
                    'name': 'Dashboard Page',
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'data': None
                }
                
        except Exception as e:
            return {
                'name': 'Dashboard Page',
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def run_verification(self) -> List[Dict[str, Any]]:
        """Run complete deployment verification"""
        print(f"🚀 Running deployment verification against {self.base_url}")
        print("=" * 70)
        
        # Wait for service to be available
        if not self.wait_for_service():
            return [{'name': 'Service Availability', 'success': False, 'error': 'Service not available'}]
        
        # Run all tests
        tests = [
            self.test_health_endpoint,
            self.test_readiness_endpoint,
            self.test_llm_status,
            self.test_ui_build_page,
            self.test_dashboard_page
        ]
        
        results = []
        for test_func in tests:
            result = test_func()
            results.append(result)
            
            # Print result
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} {result['name']}")
            
            if result.get('error'):
                print(f"   Error: {result['error']}")
            
            if result.get('version'):
                print(f"   Version: {result['version']}")
                if result.get('version_string'):
                    print(f"   Version String: {result['version_string']}")
        
        return results
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print verification summary"""
        print("\n" + "=" * 70)
        print("📊 DEPLOYMENT VERIFICATION SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show version information if available
        version_info = next((r for r in results if r.get('version')), None)
        if version_info:
            print(f"\n📋 Version Information:")
            print(f"  Version: {version_info['version']}")
            if version_info.get('version_string'):
                print(f"  Version String: {version_info['version_string']}")
        
        if passed == total:
            print("\n🎉 ALL VERIFICATION TESTS PASSED")
            print("✅ Deployment is successful!")
            return 0
        else:
            print("\n⚠️ SOME VERIFICATION TESTS FAILED")
            print("❌ Deployment verification failed")
            return 1

def main():
    """Main verification function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deployment verification for SBH')
    parser.add_argument('url', help='Base URL of deployed application')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--wait', type=int, default=60, help='Wait time for service startup')
    
    args = parser.parse_args()
    
    # Run verification
    verifier = DeploymentVerifier(args.url, args.timeout)
    results = verifier.run_verification()
    
    # Print summary and exit
    exit_code = verifier.print_summary(results)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
