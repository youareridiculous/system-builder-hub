"""
Test demo seeding functionality
"""
import unittest
from unittest.mock import patch, MagicMock
from src.jobs.demo_seed import DemoSeedJob

class TestDemoSeed(unittest.TestCase):
    """Test demo seeding"""
    
    def setUp(self):
        """Set up test environment"""
        self.demo_seed_job = DemoSeedJob()
    
    @patch('src.jobs.demo_seed.tool_kernel')
    def test_demo_seed_job_populates_data(self, mock_tool_kernel):
        """Test that demo seed job populates data"""
        # Mock tool kernel responses
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.redacted_output = {
            'job_id': 'job_123',
            'enqueued': True
        }
        mock_tool_kernel.execute.return_value = mock_result
        
        # Mock analytics
        with patch('src.jobs.demo_seed.AnalyticsService') as mock_analytics:
            mock_analytics_instance = MagicMock()
            mock_analytics.return_value = mock_analytics_instance
            
            # Test demo seeding
            result = self.demo_seed_job.seed_enterprise_demo(
                tenant_slug='test-tenant',
                num_projects=3,
                tasks_per_project=8
            )
            
            # Check result
            self.assertTrue(result['success'])
            self.assertEqual(result['tenant_slug'], 'test-tenant')
            self.assertIn('results', result)
            self.assertEqual(len(result['results']), 6)  # account, users, projects, tasks, files, email
            
            # Check individual operations
            operations = [r['operation'] for r in result['results']]
            self.assertIn('create_account', operations)
            self.assertIn('create_users', operations)
            self.assertIn('create_projects', operations)
            self.assertIn('create_tasks', operations)
            self.assertIn('upload_files', operations)
            self.assertIn('send_welcome_email', operations)
            
            # Verify tool calls
            self.assertEqual(mock_tool_kernel.execute.call_count, 6)
            
            # Check analytics tracking
            mock_analytics_instance.track.assert_called()
    
    def test_demo_seed_validation(self):
        """Test demo seed parameter validation"""
        # Test invalid num_projects
        result = self.demo_seed_job.seed_enterprise_demo(
            tenant_slug='test-tenant',
            num_projects=0,  # Invalid
            tasks_per_project=8
        )
        
        # Should still succeed but with validation
        self.assertTrue(result['success'])
        
        # Test invalid tasks_per_project
        result = self.demo_seed_job.seed_enterprise_demo(
            tenant_slug='test-tenant',
            num_projects=3,
            tasks_per_project=0  # Invalid
        )
        
        # Should still succeed but with validation
        self.assertTrue(result['success'])

if __name__ == '__main__':
    unittest.main()
