#!/usr/bin/env python3
"""Tests for AI Chat functionality"""
import os
import pytest
import json
from unittest.mock import patch, MagicMock
from src.server import create_app

@pytest.fixture
def app():
    """Create test app"""
    return create_app()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI response"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello! I'm an AI assistant."
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.usage.total_tokens = 15
    return mock_response

class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_api_health_returns_200(self, client):
        """Test /api/health returns 200"""
        response = client.get('/api/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['ok'] is True
        assert data['status'] == 'healthy'
        assert 'openai_configured' in data
        assert isinstance(data['openai_configured'], bool)
    
    def test_ai_chat_health_returns_200(self, client):
        """Test /api/ai-chat/health returns 200"""
        response = client.get('/api/ai-chat/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'openai_configured' in data
        assert isinstance(data['openai_configured'], bool)
        assert 'timestamp' in data

class TestAIChatEndpoint:
    """Test AI chat endpoint"""
    
    def test_chat_without_openai_key_returns_echo(self, client):
        """Test chat returns echo behavior when no OpenAI key"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.post('/api/ai-chat/chat', 
                                 json={'message': 'Hello'})
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['response'] == 'You said: Hello'
            assert 'conversation_id' in data
            assert data['note'] == 'openai not configured'
    
    @patch('src.server.create_openai_client')
    def test_chat_with_openai_returns_real_response(self, mock_create_client, client, mock_openai_response):
        """Test chat returns real OpenAI response when configured"""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_create_client.return_value = mock_client
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            response = client.post('/api/ai-chat/chat', 
                                 json={'message': 'Hello'})
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['response'] == "Hello! I'm an AI assistant."
            assert 'usage' in data
            assert data['usage']['prompt_tokens'] == 10
            assert data['usage']['completion_tokens'] == 5
            assert data['usage']['total_tokens'] == 15
            assert 'model' in data
            assert 'conversation_id' in data
    
    def test_chat_without_message_returns_400(self, client):
        """Test chat returns 400 when no message provided"""
        response = client.post('/api/ai-chat/chat', json={})
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_chat_without_data_returns_400(self, client):
        """Test chat returns 400 when no data provided"""
        response = client.post('/api/ai-chat/chat')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('src.server.create_openai_client')
    def test_chat_with_conversation_history(self, mock_create_client, client, mock_openai_response):
        """Test chat handles conversation history"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_create_client.return_value = mock_client
        
        conversation_history = [
            {'role': 'user', 'content': 'Previous message'},
            {'role': 'assistant', 'content': 'Previous response'}
        ]
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            response = client.post('/api/ai-chat/chat', 
                                 json={
                                     'message': 'New message',
                                     'conversation_history': conversation_history
                                 })
            assert response.status_code == 200
            
            # Verify OpenAI was called with conversation history
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]['messages']
            
            assert len(messages) == 4  # system + 2 history + 1 current
            assert messages[0]['role'] == 'system'
            assert messages[1]['role'] == 'user'
            assert messages[2]['role'] == 'assistant'
            assert messages[3]['role'] == 'user'
            assert messages[3]['content'] == 'New message'

if __name__ == '__main__':
    pytest.main([__file__])
