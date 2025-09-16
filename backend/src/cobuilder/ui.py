"""
Co-Builder Web UI for chat interface
"""

import logging
from flask import Blueprint, render_template_string, request, jsonify
from src.security.decorators import require_tenant_context

logger = logging.getLogger(__name__)

cobuilder_ui_bp = Blueprint('cobuilder_ui', __name__, url_prefix='/ui/cobuilder')

# Simple HTML template for the chat interface
CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SBH Co-Builder</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 14px;
        }
        .chat-container {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            border-bottom: 1px solid #eee;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
        }
        .message.user {
            justify-content: flex-end;
        }
        .message.bot {
            justify-content: flex-start;
        }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            font-size: 14px;
            line-height: 1.4;
        }
        .message.user .message-content {
            background: #667eea;
            color: white;
        }
        .message.bot .message-content {
            background: #f1f3f4;
            color: #333;
        }
        .input-container {
            padding: 20px;
            display: flex;
            gap: 10px;
        }
        .message-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e1e5e9;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }
        .message-input:focus {
            border-color: #667eea;
        }
        .send-button {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .send-button:hover {
            background: #5a6fd8;
        }
        .send-button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            padding: 10px 20px;
            background: #f8f9fa;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
            text-align: center;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #666;
        }
        .error {
            color: #dc3545;
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .success {
            color: #155724;
            background: #d4edda;
            border: 1px solid #c3e6cb;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container" id="cb-root" data-tenant="demo">
        <div class="header">
            <h1>🤖 SBH Co-Builder</h1>
            <p>Your AI co-founder for building and managing systems</p>
        </div>
        
        <div class="chat-container" id="cb-transcript" aria-live="polite" aria-atomic="false">
            <div class="message bot">
                <div class="message-content">
                    👋 Hi! I'm your SBH Co-Builder. I can help you:
                    <br><br>
                    • <strong>Build new modules</strong>: "Build a lightweight LMS with courses and progress"
                    <br>
                    • <strong>Provision modules</strong>: "Provision CRM for tenant demo"
                    <br>
                    • <strong>Start trials</strong>: "Start a 14-day trial for CRM"
                    <br>
                    • <strong>Resume projects</strong>: "Resume ./my-ecommerce-project"
                    <br>
                    • <strong>Check status</strong>: "What's the system status?"
                    <br><br>
                    What would you like to do today?
                </div>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div>🤔 Thinking...</div>
        </div>
        
        <div class="cb-footer">
            <div class="cb-input-wrap">
                <textarea id="cb-input"
                          rows="3"
                          maxlength="10000"
                          placeholder="Type your request…  (Shift+Enter = newline, Enter = send)"
                          aria-label="Co-Builder prompt editor"
                          class="cb-input"></textarea>

                <div class="cb-meta">
                    <span id="cb-counter" aria-live="polite">0 / 10,000</span>
                    <span id="cb-tokens" title="Rough estimate (≈4 chars per token)">~0 tokens</span>
                </div>
            </div>

            <div class="cb-actions">
                <button id="cb-send" class="cb-send" aria-label="Send message">Send</button>
                <button id="cb-cancel" class="cb-cancel" disabled aria-label="Cancel running request" title="Cancel running request">Cancel</button>
            </div>
        </div>
        
        <div id="cb-error" class="cb-error" role="alert" style="display: none;"></div>
        
        <div class="status">
            Tenant: <span id="tenantId">demo</span> | 
            Status: <span id="connectionStatus">Connected</span>
        </div>
    </div>

    <script>
        // Co-Builder functionality is now handled by cobuilder.js
        // The external script provides all the chat functionality
    </script>
    
    <link rel="stylesheet" href="{{ url_for('static', filename='cobuilder.css') }}">
    <script src="{{ url_for('static', filename='cobuilder.js') }}" defer></script>
</body>
</html>
"""

@cobuilder_ui_bp.route('/', methods=['GET'])
def chat_interface():
    """Render the Co-Builder chat interface"""
    return render_template_string(CHAT_HTML)
