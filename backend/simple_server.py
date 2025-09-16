#!/usr/bin/env python3
"""Simple Flask server for AI Website Builder Studio"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import openai

app = Flask(__name__)
CORS(app)

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/')
def index():
    return jsonify({
        "name": "AI Website Builder Backend",
        "status": "running",
        "version": "1.0.0"
    })

@app.route('/api/cobuilder/compile', methods=['POST'])
def compile_spec():
    """Compile a specification into a website"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        spec = data.get('spec')
        if not spec:
            return jsonify({'error': 'No spec provided'}), 400
        
        build_id = data.get('build_id')
        if not build_id:
            return jsonify({'error': 'No build_id provided'}), 400
        
        # Simulate compilation - generate some files
        writes = []
        diffs = []
        
        # Create a simple spec.json file
        spec_data = {
            "company": "Eric Larson Consulting",
            "tagline": "Applied AI systems that actually ship",
            "description": "Eric Larson Consulting helps teams turn AI ideas into production-ready systems.",
            "pages": [
                {
                    "id": "home",
                    "title": "Home",
                    "sections": ["hero", "services", "about"]
                },
                {
                    "id": "services", 
                    "title": "Services",
                    "sections": ["service-list", "pricing"]
                },
                {
                    "id": "about",
                    "title": "About", 
                    "sections": ["company-story", "team"]
                },
                {
                    "id": "contact",
                    "title": "Contact",
                    "sections": ["contact-form", "contact-info"]
                }
            ],
            "sections": [
                {
                    "id": "hero",
                    "type": "hero",
                    "title": "Build production AI systems that ship",
                    "subtitle": "Strategy, architecture, and hands-on engineering to deliver real business impact with AI."
                },
                {
                    "id": "services",
                    "type": "services",
                    "title": "What we do",
                    "items": ["AI Strategy Sprint", "Full-Stack AI Product", "LLM Routing & Eval", "Data & MLOps"]
                }
            ]
        }
        
        writes.append({
            'path': 'apps/site/gen/spec.json',
            'sha256': 'abc123...'
        })
        
        writes.append({
            'path': 'apps/site/app/page.tsx',
            'sha256': 'def456...'
        })
        
        writes.append({
            'path': 'apps/site/components/Hero.tsx',
            'sha256': 'ghi789...'
        })
        
        # Create diffs
        for write in writes:
            diffs.append({
                'path': write['path'],
                'type': 'added',
                'content': write['sha256'][:8] + '...'
            })
        
        return jsonify({
            'success': True,
            'result': {
                'writes': writes,
                'diffs': diffs
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cobuilder/deploy', methods=['POST'])
def deploy_website():
    """Deploy a compiled website to hosting provider"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        build_id = data.get('build_id')
        provider = data.get('provider', 'vercel')
        domain = data.get('domain', 'auto')
        
        if not build_id:
            return jsonify({'error': 'No build_id provided'}), 400
        
        # Simulate deployment
        import random
        import string
        
        if domain == 'auto':
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            domain = f"ai-website-{random_suffix}"
        
        if provider == 'vercel':
            url = f"https://{domain}.vercel.app"
        elif provider == 'netlify':
            url = f"https://{domain}.netlify.app"
        else:
            url = f"https://{domain}.example.com"
        
        return jsonify({
            'success': True,
            'url': url,
            'provider': provider,
            'domain': domain
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai-chat/chat', methods=['POST'])
def ai_chat():
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
        return jsonify({'error': f'AI Chat error: {str(e)}'}), 500

@app.route('/api/ai-chat/analyze-inspiration', methods=['POST'])
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
        return jsonify({'error': f'Analysis error: {str(e)}'}), 500

@app.route('/api/ai-chat/health', methods=['GET'])
def ai_chat_health():
    """Health check for AI Chat API"""
    return jsonify({
        'status': 'healthy',
        'service': 'ai-chat-api',
        'openai_configured': bool(os.getenv('OPENAI_API_KEY'))
    })

if __name__ == '__main__':
    print("🚀 Starting AI Website Builder Backend on port 5001...")
    app.run(host='127.0.0.1', port=5001, debug=True)
