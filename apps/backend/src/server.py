#!/usr/bin/env python3
"""
System Builder Hub - Enhanced Server with OpenAI Integration

Configuration:
- OPENAI_API_KEY: Required in production (provided via ECS task definition secrets)
- OPENAI_MODEL: Default gpt-4o-mini
- OPENAI_TIMEOUT_SECONDS: Default 20 seconds
"""
import os
import time
import uuid
import logging
from typing import Optional, Dict, Any
from flask import Flask, jsonify, request
from flask_cors import CORS
import openai
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration from environment variables"""
    return {
        'api_key': os.getenv('OPENAI_API_KEY'),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        'timeout': int(os.getenv('OPENAI_TIMEOUT_SECONDS', '20'))
    }

def create_openai_client() -> Optional[OpenAI]:
    """Create OpenAI client if API key is available"""
    config = get_openai_config()
    if not config['api_key']:
        return None
    
    try:
        return OpenAI(
            api_key=config['api_key'],
            timeout=config['timeout']
        )
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        return None

def create_app():
    """Create Flask application with OpenAI integration"""
    app = Flask(__name__)
    
    # Basic Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # CORS Configuration
    cors_origins = [
        'http://localhost:3000',
        'https://sbh.umbervale.com'
    ]
    CORS(app, 
         origins=cors_origins,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'OPTIONS'],
         supports_credentials=False)
    
    # Get OpenAI configuration
    openai_config = get_openai_config()
    openai_client = create_openai_client()
    
    logger.info(f"OpenAI configured: {bool(openai_config['api_key'])}")
    logger.info(f"OpenAI model: {openai_config['model']}")

    @app.route('/api/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            "ok": True, 
            "status": "healthy",
            "openai_configured": bool(openai_config['api_key']),
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
            'openai_configured': bool(openai_config['api_key']),
            'model': openai_config['model'] if openai_config['api_key'] else None,
            'timestamp': int(time.time())
        })

    @app.route('/api/ai-chat/chat', methods=['POST'])
    def ai_chat():
        """AI Chat endpoint with real OpenAI integration"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            message = data.get('message', '')
            if not message:
                return jsonify({'error': 'No message provided'}), 400

            # Get conversation context
            conversation_history = data.get('conversation_history', [])
            conversation_id = data.get('conversation_id', f'conv_{int(time.time())}_{str(uuid.uuid4())[:8]}')
            system_message = data.get('system', 'You are an AI assistant for the System Builder Hub (SBH) - an AI-assisted platform that designs, scaffolds, deploys, and monitors complete software systems onto AWS. SBH is better than Cursor because it takes high-level specifications and outputs complete, bootable applications with their own infrastructure, CI/CD, and monitoring. You help users create comprehensive specifications for any type of system they want to build, then guide them through the process of generating working applications that are ready to deploy independently. Ask relevant questions to understand their requirements, provide architecture guidance, and help them create detailed specifications that SBH can use to build their complete system with Terraform, ECS, ALB, RDS, S3, and GitHub Actions.')

            # If no OpenAI client, return echo behavior
            if not openai_client:
                return jsonify({
                    'success': True,
                    'response': f'You said: {message}',
                    'conversation_id': conversation_id,
                    'note': 'openai not configured'
                })

            # Build messages for OpenAI
            messages = [{"role": "system", "content": system_message}]
            
            # Add conversation history
            for msg in conversation_history:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": message})

            # Call OpenAI API
            try:
                response = openai_client.chat.completions.create(
                    model=openai_config['model'],
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
                usage = response.usage
                
                return jsonify({
                    'success': True,
                    'response': ai_response,
                    'usage': {
                        'prompt_tokens': usage.prompt_tokens,
                        'completion_tokens': usage.completion_tokens,
                        'total_tokens': usage.total_tokens
                    },
                    'model': openai_config['model'],
                    'conversation_id': conversation_id
                })
                
            except openai.APIError as e:
                logger.error(f"OpenAI API error: {e}")
                return jsonify({
                    'error_code': 'openai_api_error',
                    'message': f'OpenAI API error: {str(e)}'
                }), 502
                
            except openai.Timeout as e:
                logger.error(f"OpenAI timeout: {e}")
                return jsonify({
                    'error_code': 'openai_timeout',
                    'message': f'OpenAI request timed out after {openai_config["timeout"]} seconds'
                }), 502
                
            except Exception as e:
                logger.error(f"OpenAI client error: {e}")
                return jsonify({
                    'error_code': 'openai_client_error',
                    'message': f'OpenAI client error: {str(e)}'
                }), 502
            
        except Exception as e:
            logger.error(f"AI Chat endpoint error: {e}")
            return jsonify({'error': 'AI Chat failed', 'details': str(e)}), 500

    return app

# Create app instance for WSGI
app = create_app()
