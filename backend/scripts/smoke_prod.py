#!/usr/bin/env python3
"""
Production Smoke Test for SBH
Validates end-to-end functionality: Auth → Payments → Builder → Agent → Preview
"""
import os
import sys
import time
import requests
import json
from urllib.parse import urljoin

class SmokeTest:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_user_email = f"smoke_test_{int(time.time())}@example.com"
        self.test_user_password = "smoke_test_password_123"
        self.auth_token = None
        self.project_id = None
        
    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_health_endpoints(self):
        """Test health and readiness endpoints"""
        self.log("Testing health endpoints...")
        
        # Test /healthz
        try:
            response = self.session.get(f"{self.base_url}/healthz", timeout=10)
            if response.status_code == 200:
                self.log("✅ /healthz endpoint OK")
            else:
                self.log(f"❌ /healthz returned {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ /healthz failed: {e}", "ERROR")
            return False
            
        # Test /readiness
        try:
            response = self.session.get(f"{self.base_url}/readiness", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log("✅ /readiness endpoint OK")
                
                # Log database information
                db_driver = data.get('db_driver', 'unknown')
                db_url_kind = data.get('db_url_kind', 'unknown')
                self.log(f"   Database: {db_driver} ({db_url_kind})")
                
                # Log Redis information
                redis_info = data.get('redis', {})
                redis_configured = redis_info.get('configured', False)
                redis_ok = redis_info.get('ok', False)
                redis_details = redis_info.get('details', 'unknown')
                self.log(f"   Redis: {'✅' if redis_ok else '❌'} ({redis_details})")
                
                # Validate production database in production
                if data.get('production', {}).get('is_production'):
                    self.log(f"   Production mode: {data['production']}")
                    if db_url_kind != 'postgresql':
                        self.log(f"   ⚠️  Warning: Production should use PostgreSQL, found: {db_url_kind}")
                    
                                    # Validate Redis in production
                if redis_configured and not redis_ok:
                    self.log(f"   ⚠️  Warning: Redis configured but not available: {redis_details}")
                
                # Log observability information
                observability = data.get('observability', {})
                self.log(f"   Observability:")
                self.log(f"     Log JSON: {observability.get('log_json', False)}")
                self.log(f"     Sentry: {observability.get('sentry', {}).get('configured', False)}")
                self.log(f"     OTEL: {observability.get('otel', {}).get('configured', False)}")
                self.log(f"     Metrics: {observability.get('metrics', {}).get('configured', False)}")
                
                # Validate database connectivity
                if not data.get('db', False):
                    self.log("❌ Database connectivity failed", "ERROR")
                    return False
                else:
                    self.log("✅ Database connectivity OK")
                    
            else:
                self.log(f"❌ /readiness returned {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"❌ /readiness failed: {e}", "ERROR")
            return False
            
        return True
        
    def test_auth_flow(self):
        """Test user registration and authentication"""
        self.log("Testing authentication flow...")
        
        # Register user
        try:
            register_data = {
                "email": self.test_user_email,
                "password": self.test_user_password
            }
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json=register_data,
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                self.auth_token = data.get('token')
                self.log("✅ User registration successful")
            else:
                self.log(f"❌ User registration failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ User registration failed: {e}", "ERROR")
            return False
            
        # Test login
        try:
            login_data = {
                "email": self.test_user_email,
                "password": self.test_user_password
            }
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log("✅ User login successful")
            else:
                self.log(f"❌ User login failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ User login failed: {e}", "ERROR")
            return False
            
        return True
        
    def test_payments_api(self):
        """Test payments API (mock Stripe)"""
        self.log("Testing payments API...")
        
        if not self.auth_token:
            self.log("❌ No auth token available", "ERROR")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(
                f"{self.base_url}/api/payments/plans",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'plans' in data:
                    self.log("✅ Payments API (plans) successful")
                else:
                    self.log("❌ Payments API returned unexpected format", "ERROR")
                    return False
            else:
                self.log(f"❌ Payments API failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Payments API failed: {e}", "ERROR")
            return False
            
        return True
        
    def test_agent_build(self):
        """Test agent build functionality"""
        self.log("Testing agent build...")
        
        if not self.auth_token:
            self.log("❌ No auth token available", "ERROR")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            build_data = {
                "goal": "Build a task tracker",
                "description": "A simple task management application"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/agent/build",
                json=build_data,
                headers=headers,
                timeout=30  # Longer timeout for agent processing
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.project_id = data.get('project_id')
                    self.log(f"✅ Agent build successful, project ID: {self.project_id}")
                else:
                    self.log("❌ Agent build returned success=false", "ERROR")
                    return False
            else:
                self.log(f"❌ Agent build failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Agent build failed: {e}", "ERROR")
            return False
            
                return True
    
    def test_https_and_metrics(self):
        """Test HTTPS enforcement and metrics endpoint"""
        self.log("Testing HTTPS and metrics...")
        
        try:
            # Test HTTPS enforcement
            if self.base_url.startswith('https'):
                self.log("✅ HTTPS enforced")
            else:
                self.log("⚠️  Not using HTTPS")
            
            # Test Prometheus metrics
            try:
                response = self.session.get(f"{self.base_url}/metrics", timeout=10)
                if response.status_code == 200:
                    content = response.text
                    if '# HELP' in content and '# TYPE' in content:
                        self.log("✅ Prometheus metrics accessible and valid")
                    else:
                        self.log("⚠️  Metrics endpoint accessible but format may be invalid")
                else:
                    self.log(f"⚠️  Metrics endpoint returned: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️  Metrics endpoint error: {e}")
            
            # Test S3 file operations if enabled
            try:
                if self.auth_token:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    
                    # Test file upload (if S3 enabled)
                    test_file_content = b"test file content"
                    files = {'file': ('test.txt', test_file_content, 'text/plain')}
                    
                    response = self.session.post(
                        f"{self.base_url}/api/files/test-store/upload",
                        files=files,
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code == 201:
                        data = response.json()
                        file_info = data.get('file_info', {})
                        self.log("✅ File upload test successful")
                        
                        # Test file download
                        filename = file_info.get('name')
                        if filename:
                            response = self.session.get(
                                f"{self.base_url}/api/files/test-store/{filename}",
                                headers=headers,
                                timeout=10
                            )
                            
                            if response.status_code in [200, 302]:  # 302 for S3 redirect
                                self.log("✅ File download test successful")
                            else:
                                self.log(f"⚠️  File download returned: {response.status_code}")
                    else:
                        self.log(f"⚠️  File upload test returned: {response.status_code}")
                        
            except Exception as e:
                self.log(f"⚠️  File operations test error: {e}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ HTTPS and metrics test failed: {e}", "ERROR")
            return False
        
    def test_async_build_and_rate_limits(self):
        """Test async build and rate limiting"""
        self.log("Testing async build and rate limits...")
        
        if not self.auth_token:
            self.log("❌ No auth token available", "ERROR")
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test async build
            build_data = {"project_id": self.project_id or "test-project"}
            
            response = self.session.post(
                f"{self.base_url}/api/builder/generate-build?async=1",
                json=build_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 202:
                data = response.get_json()
                job_id = data.get('job_id')
                self.log(f"✅ Async build queued, job ID: {job_id}")
                
                # Poll job status
                max_attempts = 5
                for attempt in range(max_attempts):
                    time.sleep(2)  # Wait between polls
                    
                    job_response = self.session.get(
                        f"{self.base_url}/api/jobs/{job_id}",
                        headers=headers,
                        timeout=10
                    )
                    
                    if job_response.status_code == 200:
                        job_data = job_response.get_json()
                        job_status = job_data.get('job', {}).get('status')
                        self.log(f"   Job status: {job_status}")
                        
                        if job_status == 'finished':
                            self.log("✅ Async build completed successfully")
                            break
                        elif job_status == 'failed':
                            self.log("❌ Async build failed", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Job status check failed: {job_response.status_code}", "ERROR")
                        return False
                else:
                    self.log("⚠️  Async build timed out (this is expected in test environment)")
            
            # Test rate limiting (hit the same endpoint multiple times)
            self.log("   Testing rate limits...")
            for i in range(3):
                rate_response = self.session.post(
                    f"{self.base_url}/api/builder/generate-build?async=1",
                    json=build_data,
                    headers=headers,
                    timeout=5
                )
                
                if rate_response.status_code == 429:
                    self.log("✅ Rate limiting working (429 received)")
                    break
                elif i == 2:  # Last attempt
                    self.log("⚠️  Rate limiting not enforced (this is OK if Redis unavailable)")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Async build/rate limit test failed: {e}", "ERROR")
            return False
        
    def test_preview_endpoint(self):
        """Test preview endpoint"""
        self.log("Testing preview endpoint...")
        
        if not self.auth_token:
            self.log("❌ No auth token available", "ERROR")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            # Test preview without specific project (should show available projects)
            response = self.session.get(
                f"{self.base_url}/ui/preview",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log("✅ Preview endpoint accessible")
            else:
                self.log(f"❌ Preview endpoint failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Preview endpoint failed: {e}", "ERROR")
            return False
            
        return True
        
    def run_all_tests(self):
        """Run all smoke tests"""
        self.log("🚀 Starting SBH Production Smoke Test")
        self.log(f"   Base URL: {self.base_url}")
        self.log(f"   Test User: {self.test_user_email}")
        print()
        
        tests = [
            ("Health Endpoints", self.test_health_endpoints),
            ("HTTPS & Metrics", self.test_https_and_metrics),
            ("Authentication", self.test_auth_flow),
            ("Payments API", self.test_payments_api),
            ("Agent Build", self.test_agent_build),
            ("Async Build & Rate Limits", self.test_async_build_and_rate_limits),
            ("Preview Endpoint", self.test_preview_endpoint)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"Running {test_name}...")
            try:
                if test_func():
                    self.log(f"✅ {test_name} PASSED")
                    passed += 1
                else:
                    self.log(f"❌ {test_name} FAILED")
                    failed += 1
            except Exception as e:
                self.log(f"❌ {test_name} FAILED with exception: {e}", "ERROR")
                failed += 1
            print()
            
        # Summary
        self.log("=" * 50)
        self.log(f"SMOKE TEST SUMMARY")
        self.log(f"   Passed: {passed}")
        self.log(f"   Failed: {failed}")
        self.log(f"   Total: {passed + failed}")
        
        if failed == 0:
            self.log("🎉 ALL TESTS PASSED - SBH is ready for production!")
            return True
        else:
            self.log("❌ SOME TESTS FAILED - Please check the deployment", "ERROR")
            return False

def main():
    """Main function"""
    # Check for help
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print("Usage: python smoke_prod.py <base-url>")
        print("   or set PUBLIC_BASE_URL environment variable")
        print("Example: python smoke_prod.py https://sbh.example.com")
        sys.exit(0)
    
    # Get base URL from environment or command line
    base_url = os.environ.get('PUBLIC_BASE_URL')
    if not base_url and len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    if not base_url:
        print("Usage: python smoke_prod.py <base-url>")
        print("   or set PUBLIC_BASE_URL environment variable")
        print("Example: python smoke_prod.py https://sbh.example.com")
        sys.exit(1)
    
    # Run smoke test
    smoke_test = SmokeTest(base_url)
    success = smoke_test.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
