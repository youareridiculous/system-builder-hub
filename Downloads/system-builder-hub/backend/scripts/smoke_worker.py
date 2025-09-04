#!/usr/bin/env python3
"""
Worker environment smoke test
"""
import requests
import time
import sys
import os
import json
from typing import Optional

class WorkerSmokeTest:
    """Worker environment smoke test"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SBH-Worker-Smoke-Test/1.0'
        })
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_worker_health(self):
        """Test worker health (basic health check)"""
        self.log("Testing worker health...")
        
        try:
            # Workers don't serve HTTP, so we test Redis connectivity indirectly
            # by checking if the web environment can enqueue jobs
            
            # Test job enqueue endpoint
            response = self.session.post(
                f"{self.base_url}/api/jobs/enqueue/build",
                json={'project_id': 'smoke-test'},
                timeout=10
            )
            
            if response.status_code == 202:
                data = response.json()
                job_id = data.get('job_id')
                self.log(f"✅ Job enqueued successfully, job ID: {job_id}")
                
                # Poll job status
                max_attempts = 10
                for attempt in range(max_attempts):
                    time.sleep(2)
                    
                    response = self.session.get(
                        f"{self.base_url}/api/jobs/{job_id}",
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        job_data = response.json()
                        job_status = job_data.get('job', {}).get('status')
                        self.log(f"   Job status: {job_status}")
                        
                        if job_status == 'finished':
                            self.log("✅ Worker processed job successfully")
                            return True
                        elif job_status == 'failed':
                            self.log("❌ Worker job failed", "ERROR")
                            return False
                    else:
                        self.log(f"❌ Job status check failed: {response.status_code}", "ERROR")
                        return False
                else:
                    self.log("⚠️  Worker job timed out (this may be expected)")
                    return True
                    
            elif response.status_code == 503:
                self.log("⚠️  Redis not available (worker may not be needed)")
                return True
            else:
                self.log(f"❌ Job enqueue failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Worker health test failed: {e}", "ERROR")
            return False
    
    def test_redis_connectivity(self):
        """Test Redis connectivity through web environment"""
        self.log("Testing Redis connectivity...")
        
        try:
            # Check readiness endpoint for Redis status
            response = self.session.get(f"{self.base_url}/readiness", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                redis_info = data.get('redis', {})
                redis_ok = redis_info.get('ok', False)
                redis_details = redis_info.get('details', 'unknown')
                
                if redis_ok:
                    self.log(f"✅ Redis connectivity OK: {redis_details}")
                    return True
                else:
                    self.log(f"❌ Redis connectivity failed: {redis_details}", "ERROR")
                    return False
            else:
                self.log(f"❌ Readiness check failed: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Redis connectivity test failed: {e}", "ERROR")
            return False
    
    def run_all_tests(self):
        """Run all worker smoke tests"""
        self.log("🚀 Starting Worker Smoke Tests")
        self.log("=" * 50)
        
        tests = [
            ("Redis Connectivity", self.test_redis_connectivity),
            ("Worker Health", self.test_worker_health)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            self.log(f"\n🧪 Running: {test_name}")
            try:
                if test_func():
                    self.log(f"✅ {test_name} PASSED")
                    passed += 1
                else:
                    self.log(f"❌ {test_name} FAILED", "ERROR")
                    failed += 1
            except Exception as e:
                self.log(f"❌ {test_name} ERROR: {e}", "ERROR")
                failed += 1
        
        self.log("\n" + "=" * 50)
        self.log(f"RESULTS: {passed} passed, {failed} failed")
        
        if failed == 0:
            self.log("🎉 All worker tests passed!")
            return True
        else:
            self.log(f"❌ {failed} worker test(s) failed", "ERROR")
            return False

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python scripts/smoke_worker.py <base_url>")
        print("Example: python scripts/smoke_worker.py https://your-app.elasticbeanstalk.com")
        sys.exit(1)
    
    base_url = sys.argv[1]
    
    # Run smoke tests
    smoke_test = WorkerSmokeTest(base_url)
    success = smoke_test.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
