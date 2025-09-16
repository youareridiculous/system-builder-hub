#!/usr/bin/env python3
"""
AI Chat API - Backend endpoint for AI Chat OpenAI integration
"""
import os
import json
import logging
import openai
from flask import Blueprint, request, jsonify
from flask_cors import cross_origin

logger = logging.getLogger(__name__)

# Create blueprint
ai_chat_bp = Blueprint('ai_chat', __name__, url_prefix='/api/ai-chat')

# Initialize OpenAI client
openai.api_key = os.getenv('OPENAI_API_KEY')

@ai_chat_bp.route('/chat', methods=['POST'])
@cross_origin()
def chat_with_ai():
    """Handle AI chat messages with OpenAI"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        conversation_history = data.get('history', [])
        context = data.get('context', {})
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Build conversation context
        messages = []
        
        # Add system context
        system_prompt = """You are an expert AI Website Builder Assistant. You help users create professional, enterprise-grade websites by:

1. Asking intelligent questions about their business
2. Understanding their design preferences and visual inspiration
3. Providing industry-specific insights and recommendations
4. Creating detailed website specifications (BuildSpecs)
5. Offering professional advice on web design, SEO, and user experience

You are knowledgeable about:
- Modern web design trends and best practices
- Enterprise website requirements
- SEO optimization
- User experience design
- Conversion optimization
- Industry-specific website needs

Always be helpful, professional, and provide actionable advice. When users share visual inspiration or URLs, analyze the design elements and provide specific feedback."""
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for msg in conversation_history[-10:]:  # Keep last 10 messages for context
            if msg.get('type') == 'user':
                messages.append({"role": "user", "content": msg.get('content', '')})
            elif msg.get('type') == 'ai':
                messages.append({"role": "assistant", "content": msg.get('content', '')})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        return jsonify({
            'response': ai_response,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
        })
        
    except Exception as e:
        logger.error(f"AI Chat error: {str(e)}")
        return jsonify({'error': f'AI Chat error: {str(e)}'}), 500

@ai_chat_bp.route('/analyze-inspiration', methods=['POST'])
@cross_origin()
def analyze_inspiration():
    """Analyze visual inspiration (URLs or image descriptions)"""
    try:
        data = request.get_json()
        inspiration_type = data.get('type', 'url')  # 'url' or 'image'
        content = data.get('content', '')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        if inspiration_type == 'url':
            prompt = f"""Analyze this website URL and provide design insights: {content}

Please provide:
1. Design style (modern, minimalist, corporate, creative, etc.)
2. Color palette analysis
3. Layout structure
4. Typography style
5. Key design elements
6. Overall aesthetic
7. Suggestions for incorporating similar elements

Be specific and actionable in your analysis."""
        
        else:  # image description
            prompt = f"""Analyze this image description and provide design insights: {content}

Please provide:
1. Design style identification
2. Color palette suggestions
3. Layout recommendations
4. Typography style
5. Key design elements to incorporate
6. Overall aesthetic assessment
7. Specific suggestions for website design

Be specific and actionable in your analysis."""
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional web design analyst. Provide detailed, actionable insights about design elements and how to incorporate them into website designs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        analysis = response.choices[0].message.content.strip()
        
        return jsonify({
            'analysis': analysis,
            'type': inspiration_type,
            'content': content
        })
        
    except Exception as e:
        logger.error(f"Inspiration analysis error: {str(e)}")
        return jsonify({'error': f'Analysis error: {str(e)}'}), 500

@ai_chat_bp.route('/generate-spec', methods=['POST'])
@cross_origin()
def generate_spec():
    """Generate BuildSpec from conversation data"""
    try:
        data = request.get_json()
        conversation_data = data.get('data', {})
        
        prompt = f"""Based on this conversation data, generate a comprehensive BuildSpec for a professional website:

Conversation Data: {json.dumps(conversation_data, indent=2)}

Please generate a complete BuildSpec JSON that includes:

1. Brand information (name, voice, industry, design tokens)
2. Site configuration (domain, locales, target audience, integrations)
3. Pages array with detailed page specifications
4. Forms array with field specifications and integrations
5. SEO configuration with structured data
6. Analytics and tracking setup

The BuildSpec should be production-ready and include all necessary details for building a professional website. Return only valid JSON format."""

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional website specification generator. Create detailed, production-ready BuildSpecs in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        spec_text = response.choices[0].message.content.strip()
        
        # Try to parse and validate JSON
        try:
            spec_json = json.loads(spec_text)
            return jsonify({
                'spec': spec_json,
                'raw_response': spec_text
            })
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw response
            return jsonify({
                'spec': None,
                'raw_response': spec_text,
                'error': 'Generated spec is not valid JSON'
            })
        
    except Exception as e:
        logger.error(f"Spec generation error: {str(e)}")
        return jsonify({'error': f'Spec generation error: {str(e)}'}), 500

@ai_chat_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check for AI Chat API"""
    return jsonify({
        'status': 'healthy',
        'service': 'ai-chat-api',
        'openai_configured': bool(os.getenv('OPENAI_API_KEY'))
    })
