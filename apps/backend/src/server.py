#!/usr/bin/env python3
"""System Builder Hub - Simplified Server for Phase 3"""
import os
import time
import openai
from flask import Flask, jsonify, request
from flask_cors import CORS

def create_app():
    """Create Flask application"""
    app = Flask(__name__)
    
    # Basic Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Initialize CORS
    CORS(app)
    
    # Initialize OpenAI
    openai.api_key = os.getenv('OPENAI_API_KEY')

    @app.route('/api/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            "ok": True, 
            "status": "healthy",
            "openai_configured": bool(openai.api_key),
            "environment": os.getenv('FLASK_ENV', 'production')
        })

    @app.route('/')
    def index():
        return jsonify({
            "name": "System Builder Hub",
            "version": "1.0.0",
            "status": "running"
        })

    @app.route('/api/ai-chat/health', methods=['GET'])
    def ai_chat_health():
        """Health check for AI Chat service"""
        return jsonify({
            'status': 'healthy',
            'openai_configured': bool(openai.api_key),
            'timestamp': int(time.time())
        })

    @app.route('/api/ai-chat/chat', methods=['POST'])
    def ai_chat():
        """AI Chat endpoint"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            message = data.get('message', '')
            if not message:
                return jsonify({'error': 'No message provided'}), 400

            # Simple response for now
            return jsonify({
                'success': True,
                'response': f'You said: {message}',
                'conversation_id': f'conv_{int(time.time())}'
            })
            
        except Exception as e:
            return jsonify({'error': 'AI Chat failed', 'details': str(e)}), 500

    return app

# Create app instance for WSGI
app = create_app()
