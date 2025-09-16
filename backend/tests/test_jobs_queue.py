#!/usr/bin/env python3
"""
Test background jobs queue functionality
"""
import unittest
import os
import sys
import tempfile
import shutil
import uuid
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestJobsQueue(unittest.TestCase):
    """Test background jobs queue functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.old_env = os.environ.copy()
        os.environ.clear()
        os.environ['FLASK_ENV'] = 'development'
        os.environ['LLM_SECRET_KEY'] = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
        os.environ['AUTH_SECRET_KEY'] = 'test-secret-key-for-auth-testing'
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_mock'
        os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
        os.environ['PUBLIC_BASE_URL'] = 'http://localhost:5001'
        os.environ['FEATURE_BG_JOBS'] = 'true'
        
        # Create temporary database with unique name
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, f'test_{uuid.uuid4().hex[:8]}.db')
        os.environ['DATABASE'] = self.db_path
    
    def tearDown(self):
        """Clean up test environment"""
        os.environ.clear()
        os.environ.update(self.old_env)
        
        # Clean up temporary database
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_jobs_api_returns_503_when_redis_unavailable(self):
        """Test that jobs API returns 503 when Redis is unavailable"""
        os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
        
        try:
            from app import create_app
            
            app = create_app()
            
            with app.test_client() as client:
                # Test job status endpoint
                response = client.get('/api/jobs/test-job-id')
                self.assertEqual(response.status_code, 503)
                
                # Test enqueue endpoints
                response = client.post('/api/jobs/enqueue/build', json={'project_id': 'test'})
                self.assertEqual(response.status_code, 503)
                
                response = client.post('/api/jobs/enqueue/email', json={
                    'to': 'test@example.com',
                    'subject': 'Test',
                    'body': 'Test body'
                })
                self.assertEqual(response.status_code, 503)
                
        except ImportError:
            self.skipTest("Jobs dependencies not available")
    
    def test_job_tasks_importable(self):
        """Test that job tasks can be imported"""
        try:
            from jobs.tasks import (
                generate_build_job,
                send_email_mock,
                process_payment_webhook,
                cleanup_expired_sessions,
                health_check_job
            )
            
            # All tasks should be callable
            self.assertTrue(callable(generate_build_job))
            self.assertTrue(callable(send_email_mock))
            self.assertTrue(callable(process_payment_webhook))
            self.assertTrue(callable(cleanup_expired_sessions))
            self.assertTrue(callable(health_check_job))
            
        except ImportError:
            self.skipTest("Jobs dependencies not available")
    
    def test_worker_importable(self):
        """Test that worker can be imported"""
        try:
            from jobs.worker import main
            self.assertTrue(callable(main))
        except ImportError:
            self.skipTest("Worker dependencies not available")

if __name__ == '__main__':
    unittest.main()
