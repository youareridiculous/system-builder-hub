#!/usr/bin/env python3
"""
Quiet smoke tests for Venture OS endpoints
Tests seed and list endpoints without external dependencies
"""

import unittest
import json
from unittest.mock import Mock, patch
from flask import Flask

# Import the blueprint
from venture_os.http.api import bp as venture_os_bp


class TestVentureOSEndpoints(unittest.TestCase):
    """Test Venture OS HTTP endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.app = Flask(__name__)
        self.app.register_blueprint(venture_os_bp, url_prefix='/api/venture_os')
        self.client = self.app.test_client()
    
    def test_seed_demo_endpoint(self):
        """Test seed demo endpoint creates entities"""
        response = self.client.post(
            '/api/venture_os/seed/demo',
            headers={'X-Tenant-ID': 'test_tenant'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
        self.assertGreater(data['created'], 0)
    
    def test_list_entities_endpoint(self):
        """Test list entities endpoint returns data"""
        # First seed some data
        self.client.post(
            '/api/venture_os/seed/demo',
            headers={'X-Tenant-ID': 'test_tenant'}
        )
        
        # Then list entities
        response = self.client.get(
            '/api/venture_os/entities?limit=5',
            headers={'X-Tenant-ID': 'test_tenant'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
        self.assertGreater(data['total'], 0)
        self.assertGreater(len(data['items']), 0)
    
    def test_list_entities_missing_tenant(self):
        """Test list entities endpoint requires tenant ID"""
        response = self.client.get('/api/venture_os/entities?limit=5')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['ok'])
        self.assertIn('missing X-Tenant-ID', data['error'])
    
    def test_list_entities_pagination(self):
        """Test list entities endpoint pagination"""
        # First seed some data
        self.client.post(
            '/api/venture_os/seed/demo',
            headers={'X-Tenant-ID': 'test_tenant'}
        )
        
        # Test with limit and offset
        response = self.client.get(
            '/api/venture_os/entities?limit=2&offset=1',
            headers={'X-Tenant-ID': 'test_tenant'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['ok'])
        self.assertLessEqual(len(data['items']), 2)


if __name__ == '__main__':
    unittest.main()
