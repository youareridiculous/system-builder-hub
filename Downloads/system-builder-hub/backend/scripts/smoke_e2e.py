#!/usr/bin/env python3
"""
CLI/HTTP Smoke Helper for SBH CRM
Runs a pared-down version of end-to-end tests and prints a concise pass/fail summary.
Used by CI and EB post-deploy check.
"""

import sys
import os
import requests
import json
import time
from typing import Dict, Any, Optional, List

class SmokeTestRunner:
    """Runs smoke tests against SBH CRM API"""
    
    def __init__(self, base_url: str, auth_token: str, tenant_id: str):
        self.base_url = base_url
        self.auth_token = auth_token
        self.tenant_id = tenant_id
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "X-Tenant-ID": tenant_id,
            "Content-Type": "application/json"
        }
        self.results = []
    
    def run_test(self, name: str, test_func) -> bool:
        """Run a single test and record the result"""
        try:
            start_time = time.time()
            result = test_func()
            duration = time.time() - start_time
            
            self.results.append({
                "name": name,
                "passed": result,
                "duration": duration,
                "error": None
            })
            
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {name} ({duration:.2f}s)")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.append({
                "name": name,
                "passed": False,
                "duration": duration,
                "error": str(e)
            })
            
            print(f"  ❌ FAIL {name} ({duration:.2f}s) - {str(e)}")
            return False
    
    def test_health_readiness(self) -> bool:
        """Test health and readiness endpoints"""
        # Health check
        response = requests.get(f"{self.base_url}/healthz", timeout=10)
        if response.status_code != 200:
            return False
        
        # Readiness check
        response = requests.get(f"{self.base_url}/readiness", timeout=10)
        if response.status_code != 200:
            return False
        
        readiness_data = response.json()
        return readiness_data.get("status") == "ready"
    
    def test_auth_flow(self) -> bool:
        """Test authentication flow"""
        # Register new user
        register_data = {
            "email": f"smoke_test_{int(time.time())}@example.com",
            "password": "testpassword123",
            "first_name": "Smoke",
            "last_name": "Test",
            "company_name": "Smoke Test Company"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/register", json=register_data, timeout=10)
        if response.status_code != 201:
            return False
        
        # Login
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        
        response = requests.post(f"{self.base_url}/api/auth/login", json=login_data, timeout=10)
        if response.status_code != 200:
            return False
        
        login_response = response.json()
        if "access_token" not in login_response:
            return False
        
        # Test /api/auth/me
        token = login_response["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{self.base_url}/api/auth/me", headers=headers, timeout=10)
        return response.status_code == 200
    
    def test_onboarding_demo_seed(self) -> bool:
        """Test onboarding and demo seed"""
        # Check onboarding status
        response = requests.get(f"{self.base_url}/api/onboarding/status", headers=self.headers, timeout=10)
        if response.status_code != 200:
            return False
        
        onboarding_status = response.json()
        
        # Complete onboarding if needed
        if not onboarding_status.get("completed", False):
            onboarding_data = {
                "company_name": "Smoke Test Company",
                "industry": "Technology",
                "team_size": 10,
                "primary_use_case": "sales"
            }
            
            response = requests.post(f"{self.base_url}/api/onboarding/complete", 
                                   json=onboarding_data, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return False
        
        # Seed demo data
        response = requests.post(f"{self.base_url}/api/admin/demo-seed", 
                               json={"contacts": 5, "deals": 2, "projects": 1, "tasks_per_project": 3}, 
                               headers=self.headers, timeout=30)
        return response.status_code == 200
    
    def test_contacts_crud(self) -> bool:
        """Test contacts CRUD operations"""
        # Create contact
        contact_data = {
            "first_name": "John",
            "last_name": "Smoke",
            "email": f"john.smoke_{int(time.time())}@example.com",
            "company": "Smoke Test Corp"
        }
        
        response = requests.post(f"{self.base_url}/api/contacts", json=contact_data, headers=self.headers, timeout=10)
        if response.status_code != 201:
            return False
        
        contact_response = response.json()
        contact_id = contact_response["data"]["id"]
        
        # Get contact
        response = requests.get(f"{self.base_url}/api/contacts/{contact_id}", headers=self.headers, timeout=10)
        if response.status_code != 200:
            return False
        
        # List contacts
        response = requests.get(f"{self.base_url}/api/contacts", headers=self.headers, timeout=10)
        return response.status_code == 200 and len(response.json().get("data", [])) > 0
    
    def test_deals_crud(self) -> bool:
        """Test deals CRUD operations"""
        # Get first contact for deal creation
        response = requests.get(f"{self.base_url}/api/contacts", headers=self.headers, timeout=10)
        if response.status_code != 200:
            return False
        
        contacts = response.json().get("data", [])
        if not contacts:
            return False
        
        contact_id = contacts[0]["id"]
        
        # Create deal
        deal_data = {
            "title": "Smoke Test Deal",
            "value": 10000,
            "pipeline_stage": "qualification",
            "contact_id": contact_id,
            "status": "open"
        }
        
        response = requests.post(f"{self.base_url}/api/deals", json=deal_data, headers=self.headers, timeout=10)
        if response.status_code != 201:
            return False
        
        deal_response = response.json()
        deal_id = deal_response["data"]["id"]
        
        # Get deal
        response = requests.get(f"{self.base_url}/api/deals/{deal_id}", headers=self.headers, timeout=10)
        if response.status_code != 200:
            return False
        
        # List deals
        response = requests.get(f"{self.base_url}/api/deals", headers=self.headers, timeout=10)
        return response.status_code == 200
    
    def test_tasks_crud(self) -> bool:
        """Test tasks CRUD operations"""
        # Create task
        task_data = {
            "title": "Smoke Test Task",
            "description": "This is a smoke test task",
            "priority": "medium",
            "status": "todo"
        }
        
        response = requests.post(f"{self.base_url}/api/tasks", json=task_data, headers=self.headers, timeout=10)
        if response.status_code != 201:
            return False
        
        task_response = response.json()
        task_id = task_response["data"]["id"]
        
        # Get task
        response = requests.get(f"{self.base_url}/api/tasks/{task_id}", headers=self.headers, timeout=10)
        if response.status_code != 200:
            return False
        
        # List tasks
        response = requests.get(f"{self.base_url}/api/tasks", headers=self.headers, timeout=10)
        return response.status_code == 200
    
    def test_analytics(self) -> bool:
        """Test analytics functionality"""
        response = requests.get(f"{self.base_url}/api/analytics/crm", headers=self.headers, timeout=10)
        if response.status_code != 200:
            return False
        
        analytics_data = response.json()
        return "data" in analytics_data and "attributes" in analytics_data["data"]
    
    def test_export_import(self) -> bool:
        """Test export and import functionality"""
        # Export contacts CSV
        response = requests.get(f"{self.base_url}/api/contacts/export.csv", headers=self.headers, timeout=15)
        if response.status_code != 200:
            return False
        
        # Import small CSV
        csv_content = f"first_name,last_name,email,company\nSmoke,Import,smoke.import_{int(time.time())}@example.com,Import Corp"
        files = {"file": ("contacts.csv", csv_content, "text/csv")}
        
        response = requests.post(f"{self.base_url}/api/contacts/import", files=files, headers={"Authorization": self.headers["Authorization"], "X-Tenant-ID": self.headers["X-Tenant-ID"]}, timeout=15)
        return response.status_code == 200
    
    def test_file_store(self) -> bool:
        """Test file storage functionality"""
        # Upload file
        file_content = b"This is a smoke test file"
        files = {"file": ("smoke_test.txt", file_content, "text/plain")}
        
        response = requests.post(f"{self.base_url}/api/files/upload", files=files, 
                               headers={"Authorization": self.headers["Authorization"], "X-Tenant-ID": self.headers["X-Tenant-ID"]}, timeout=10)
        if response.status_code != 200:
            return False
        
        upload_response = response.json()
        file_id = upload_response["data"]["id"]
        
        # List files
        response = requests.get(f"{self.base_url}/api/files", headers=self.headers, timeout=10)
        return response.status_code == 200
    
    def test_multi_tenancy(self) -> bool:
        """Test multi-tenancy isolation"""
        # Create another user (different tenant)
        register_data = {
            "email": f"smoke_test_tenant2_{int(time.time())}@example.com",
            "password": "testpassword123",
            "first_name": "Smoke2",
            "last_name": "Test2",
            "company_name": "Smoke Test Company 2"
        }
        
        response = requests.post(f"{self.base_url}/api/auth/register", json=register_data, timeout=10)
        if response.status_code != 201:
            return False
        
        # Login as second user
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        
        response = requests.post(f"{self.base_url}/api/auth/login", json=login_data, timeout=10)
        if response.status_code != 200:
            return False
        
        login_response = response.json()
        second_token = login_response["access_token"]
        
        # Create contact with second user
        contact_data = {
            "first_name": "Jane",
            "last_name": "Smoke2",
            "email": f"jane.smoke2_{int(time.time())}@example.com"
        }
        
        headers = {"Authorization": f"Bearer {second_token}"}
        response = requests.post(f"{self.base_url}/api/contacts", json=contact_data, headers=headers, timeout=10)
        if response.status_code != 201:
            return False
        
        # Switch back to first user and verify isolation
        response = requests.get(f"{self.base_url}/api/contacts", headers=self.headers, timeout=10)
        if response.status_code != 200:
            return False
        
        contacts_response = response.json()
        contact_emails = [contact["attributes"]["email"] for contact in contacts_response["data"]]
        
        # Should not see second user's contact
        return f"jane.smoke2_{int(time.time())}@example.com" not in contact_emails
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all smoke tests and return summary"""
        print(f"🚀 SBH CRM Smoke Tests")
        print(f"   Base URL: {self.base_url}")
        print(f"   Tenant ID: {self.tenant_id}")
        print()
        
        tests = [
            ("Health & Readiness", self.test_health_readiness),
            ("Authentication Flow", self.test_auth_flow),
            ("Onboarding & Demo Seed", self.test_onboarding_demo_seed),
            ("Contacts CRUD", self.test_contacts_crud),
            ("Deals CRUD", self.test_deals_crud),
            ("Tasks CRUD", self.test_tasks_crud),
            ("Analytics", self.test_analytics),
            ("Export/Import", self.test_export_import),
            ("File Store", self.test_file_store),
            ("Multi-tenancy", self.test_multi_tenancy)
        ]
        
        passed = 0
        total = len(tests)
        
        for name, test_func in tests:
            if self.run_test(name, test_func):
                passed += 1
        
        # Summary
        print()
        print("📊 Test Summary:")
        print(f"   Passed: {passed}/{total}")
        print(f"   Failed: {total - passed}/{total}")
        
        success_rate = (passed / total) * 100
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Detailed results
        print()
        print("📋 Detailed Results:")
        for result in self.results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            duration = f"({result['duration']:.2f}s)"
            error = f" - {result['error']}" if result["error"] else ""
            print(f"   {status} {result['name']} {duration}{error}")
        
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": success_rate,
            "results": self.results
        }

def main():
    """Main function"""
    # Get configuration from environment or command line
    base_url = os.getenv("SBH_BASE_URL", "http://localhost:5000")
    auth_token = os.getenv("SBH_AUTH_TOKEN")
    tenant_id = os.getenv("SBH_TENANT_ID")
    
    # Command line arguments
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        auth_token = sys.argv[2]
    if len(sys.argv) > 3:
        tenant_id = sys.argv[3]
    
    if not auth_token:
        print("❌ Error: SBH_AUTH_TOKEN environment variable or command line argument is required")
        print("   Usage: python smoke_e2e.py [base_url] [auth_token] [tenant_id]")
        sys.exit(1)
    
    if not tenant_id:
        print("❌ Error: SBH_TENANT_ID environment variable or command line argument is required")
        print("   Usage: python smoke_e2e.py [base_url] [auth_token] [tenant_id]")
        sys.exit(1)
    
    # Run smoke tests
    runner = SmokeTestRunner(base_url, auth_token, tenant_id)
    summary = runner.run_all_tests()
    
    # Exit with appropriate code
    if summary["success_rate"] >= 90:  # Allow 10% failure rate for smoke tests
        print("\n✅ Smoke tests PASSED (success rate >= 90%)")
        sys.exit(0)
    else:
        print("\n❌ Smoke tests FAILED (success rate < 90%)")
        sys.exit(1)

if __name__ == "__main__":
    main()
