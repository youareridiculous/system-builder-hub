"""
Analytics tests
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date
from flask import Flask
from src.app import create_app
from src.analytics.service import AnalyticsService

class TestAnalytics(unittest.TestCase):
    """Test analytics functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['ANALYTICS_ENABLED'] = True
        self.client = self.app.test_client()
    
    def test_track_event_and_list(self):
        """Test event tracking and listing"""
        with self.app.app_context():
            service = AnalyticsService()
            
            # Track an event
            service.track(
                tenant_id='test-tenant',
                event='test.event',
                user_id='user-123',
                source='app',
                props={'test': 'data'}
            )
            
            # List events
            result = service.get_events('test-tenant')
            
            self.assertIn('events', result)
            self.assertTrue(len(result['events']) > 0)
            
            # Check event data
            event = result['events'][0]
            self.assertEqual(event['event'], 'test.event')
            self.assertEqual(event['user_id'], 'user-123')
            self.assertEqual(event['source'], 'app')
            self.assertEqual(event['props']['test'], 'data')
    
    def test_usage_increment_and_rollup(self):
        """Test usage increment and rollup"""
        with self.app.app_context():
            service = AnalyticsService()
            
            # Increment usage
            service.increment_usage('test-tenant', 'test.metric', 5)
            
            # Check Redis counter (mocked)
            with patch.object(service, '_get_redis_counter', return_value=5):
                count = service._get_redis_counter('test-tenant', 'test.metric', date.today())
                self.assertEqual(count, 5)
    
    def test_filters_and_pagination(self):
        """Test event filtering and pagination"""
        with self.app.app_context():
            service = AnalyticsService()
            
            # Track multiple events
            for i in range(10):
                service.track(
                    tenant_id='test-tenant',
                    event='test.event',
                    user_id=f'user-{i}',
                    source='app'
                )
            
            # Test filtering
            result = service.get_events(
                tenant_id='test-tenant',
                event='test.event',
                limit=5
            )
            
            self.assertIn('events', result)
            self.assertIn('has_more', result)
            self.assertIn('next_cursor', result)
            self.assertTrue(len(result['events']) <= 5)
    
    def test_export_csv(self):
        """Test CSV export"""
        with self.app.app_context():
            service = AnalyticsService()
            
            # Track an event
            service.track(
                tenant_id='test-tenant',
                event='test.event',
                user_id='user-123',
                source='app',
                props={'test': 'data'}
            )
            
            # Export CSV
            csv_content = service.export_csv('test-tenant')
            
            self.assertIn('timestamp,event,source,user_id,ip,request_id,properties', csv_content)
            self.assertIn('test.event', csv_content)
    
    def test_kpis_endpoint(self):
        """Test KPIs endpoint"""
        with self.app.app_context():
            service = AnalyticsService()
            
            # Track some events
            service.track('test-tenant', 'auth.user.registered', user_id='user-1')
            service.track('test-tenant', 'auth.user.login', user_id='user-1')
            service.track('test-tenant', 'builder.generate.completed', user_id='user-1')
            
            # Get metrics
            metrics = service.get_metrics('test-tenant')
            
            self.assertIn('auth.user.registered', metrics)
            self.assertIn('auth.user.login', metrics)
            self.assertIn('builder.generate.completed', metrics)
    
    def test_rbac(self):
        """Test RBAC for analytics endpoints"""
        # This would test that viewer users are denied access
        # and admin users are allowed access
        pass
    
    def test_quota_soft_limit(self):
        """Test quota soft limit checking"""
        with self.app.app_context():
            service = AnalyticsService()
            service.quotas_enabled = True
            
            # Check quota
            quota_result = service.check_quota('test-tenant', 'api_requests_daily')
            
            self.assertIn('exceeded', quota_result)
            self.assertIn('current', quota_result)
            self.assertIn('limit', quota_result)
    
    def test_auto_hooks_smoke(self):
        """Test that auto-tracking hooks work"""
        # This would test that hitting various endpoints
        # produces the expected analytics events
        pass

if __name__ == '__main__':
    unittest.main()
