#!/usr/bin/env python3
"""
Tests for the /api/cobuilder/full_build endpoint
"""

import json
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from src.cobuilder.api import cobuilder_bp


class TestFullBuildEndpoint(unittest.TestCase):
    """Test cases for the full build endpoint"""
    
    def setUp(self):
        """Set up test client"""
        self.app = Flask(__name__)
        # Create a fresh blueprint for testing to avoid conflicts
        from flask import Blueprint
        test_bp = Blueprint('test_cobuilder', __name__)
        
        # Import the function directly and register it
        from src.cobuilder.api import full_build
        test_bp.add_url_rule('/full_build', 'full_build', full_build, methods=['POST'])
        
        self.app.register_blueprint(test_bp, url_prefix='/api/cobuilder')
        self.client = self.app.test_client()
    
    def test_body_only(self):
        """Test POST with JSON {message, idempotency_key, started_at} → expect 202, JSON has build_id, ok:true"""
        with patch('src.cobuilder.api.FullBuildOrchestrator') as mock_orchestrator, \
             patch('src.cobuilder.api.PlanParser') as mock_parser:
            
            # Mock the orchestrator and parser
            mock_orchestrator_instance = MagicMock()
            mock_orchestrator.return_value = mock_orchestrator_instance
            
            mock_parser_instance = MagicMock()
            mock_parser.return_value = mock_parser_instance
            
            # Mock task graph with nodes
            mock_task_graph = MagicMock()
            mock_task_graph.nodes = [MagicMock()]  # Non-empty nodes
            mock_parser_instance.parse_plan.return_value = mock_task_graph
            
            # Mock build result
            mock_build_result = MagicMock()
            mock_build_result.build_id = "test-build-123"
            mock_orchestrator_instance.execute_task_graph.return_value = mock_build_result
            
            # Test request
            payload = {
                "message": "Create /studio directory with package files",
                "idempotency_key": "test-key-123",
                "started_at": "2024-01-01T00:00:00Z"
            }
            
            response = self.client.post('/api/cobuilder/full_build', 
                                      json=payload,
                                      content_type='application/json')
            
            # Assertions
            self.assertEqual(response.status_code, 202)
            response_data = json.loads(response.data)
            self.assertTrue(response_data['success'])
            self.assertTrue(response_data['data']['ok'])
            self.assertEqual(response_data['data']['build_id'], "test-build-123")
            self.assertIsNotNone(response_data['data']['build_id'])
    
    def test_headers_only(self):
        """Test POST with JSON {message} and headers Idempotency-Key, X-Started-At → 202, build_id, ok:true"""
        with patch('src.cobuilder.api.FullBuildOrchestrator') as mock_orchestrator, \
             patch('src.cobuilder.api.PlanParser') as mock_parser:
            
            # Mock the orchestrator and parser
            mock_orchestrator_instance = MagicMock()
            mock_orchestrator.return_value = mock_orchestrator_instance
            
            mock_parser_instance = MagicMock()
            mock_parser.return_value = mock_parser_instance
            
            # Mock task graph with nodes
            mock_task_graph = MagicMock()
            mock_task_graph.nodes = [MagicMock()]  # Non-empty nodes
            mock_parser_instance.parse_plan.return_value = mock_task_graph
            
            # Mock build result
            mock_build_result = MagicMock()
            mock_build_result.build_id = "test-build-456"
            mock_orchestrator_instance.execute_task_graph.return_value = mock_build_result
            
            # Test request with headers
            payload = {"message": "Create /studio directory with package files"}
            headers = {
                'Idempotency-Key': 'header-key-456',
                'X-Started-At': '2024-01-01T12:00:00Z'
            }
            
            response = self.client.post('/api/cobuilder/full_build', 
                                      json=payload,
                                      headers=headers,
                                      content_type='application/json')
            
            # Assertions
            self.assertEqual(response.status_code, 202)
            response_data = json.loads(response.data)
            self.assertTrue(response_data['success'])
            self.assertTrue(response_data['data']['ok'])
            self.assertEqual(response_data['data']['build_id'], "test-build-456")
            self.assertIsNotNone(response_data['data']['build_id'])
    
    def test_defaults(self):
        """Test POST with JSON {message} and no headers → 202, build_id, ok:true (server generated idempotency_key + started_at)"""
        with patch('src.cobuilder.api.FullBuildOrchestrator') as mock_orchestrator, \
             patch('src.cobuilder.api.PlanParser') as mock_parser:
            
            # Mock the orchestrator and parser
            mock_orchestrator_instance = MagicMock()
            mock_orchestrator.return_value = mock_orchestrator_instance
            
            mock_parser_instance = MagicMock()
            mock_parser.return_value = mock_parser_instance
            
            # Mock task graph with nodes
            mock_task_graph = MagicMock()
            mock_task_graph.nodes = [MagicMock()]  # Non-empty nodes
            mock_parser_instance.parse_plan.return_value = mock_task_graph
            
            # Mock build result
            mock_build_result = MagicMock()
            mock_build_result.build_id = "test-build-789"
            mock_orchestrator_instance.execute_task_graph.return_value = mock_build_result
            
            # Test request with minimal payload
            payload = {"message": "Create /studio directory with package files"}
            
            response = self.client.post('/api/cobuilder/full_build', 
                                      json=payload,
                                      content_type='application/json')
            
            # Assertions
            self.assertEqual(response.status_code, 202)
            response_data = json.loads(response.data)
            self.assertTrue(response_data['success'])
            self.assertTrue(response_data['data']['ok'])
            self.assertEqual(response_data['data']['build_id'], "test-build-789")
            self.assertIsNotNone(response_data['data']['build_id'])
    
    def test_missing_message(self):
        """Test POST with {} → 400, JSON error code:'missing_message'"""
        # Test request with empty payload
        payload = {}
        
        response = self.client.post('/api/cobuilder/full_build', 
                                  json=payload,
                                  content_type='application/json')
        
        # Assertions
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'missing_message')
        self.assertIn('Message is required', data['error']['message'])


if __name__ == '__main__':
    unittest.main()
