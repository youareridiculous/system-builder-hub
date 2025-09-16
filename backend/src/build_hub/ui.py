"""
Build Hub UI - Dual-Mode Build Experience

Provides users with choice between:
- Vibe Mode: Chat-first exploration via Co-Builder
- Spec Mode: Plan-first structured wizard
"""

from flask import Blueprint, render_template_string, request, redirect, url_for
import json

build_hub_bp = Blueprint('build_hub', __name__, url_prefix='/ui')

# HTML template for the build hub
BUILD_HUB_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SBH Build Hub - Choose Your Build Style</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .header {
            text-align: center;
            margin-bottom: 3rem;
            color: white;
        }
        
        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .build-modes {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .mode-card {
            background: white;
            border-radius: 20px;
            padding: 2.5rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            border: 3px solid transparent;
        }
        
        .mode-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 30px 60px rgba(0,0,0,0.15);
            border-color: #667eea;
        }
        
        .mode-card.vibe {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            color: white;
        }
        
        .mode-card.spec {
            background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
            color: white;
        }
        
        .mode-icon {
            font-size: 4rem;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        
        .mode-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1rem;
            text-align: center;
        }
        
        .mode-subtitle {
            font-size: 1.1rem;
            margin-bottom: 1.5rem;
            text-align: center;
            opacity: 0.9;
        }
        
        .mode-benefits {
            list-style: none;
            margin-bottom: 2rem;
        }
        
        .mode-benefits li {
            padding: 0.5rem 0;
            display: flex;
            align-items: center;
        }
        
        .mode-benefits li:before {
            content: "✓";
            font-weight: bold;
            margin-right: 0.75rem;
            font-size: 1.2rem;
        }
        
        .mode-button {
            display: block;
            width: 100%;
            padding: 1rem 2rem;
            background: rgba(255,255,255,0.2);
            color: white;
            text-decoration: none;
            text-align: center;
            border-radius: 50px;
            font-weight: 600;
            font-size: 1.1rem;
            transition: all 0.3s ease;
            border: 2px solid rgba(255,255,255,0.3);
        }
        
        .mode-button:hover {
            background: rgba(255,255,255,0.3);
            transform: scale(1.05);
            text-decoration: none;
            color: white;
        }
        
        .footer {
            text-align: center;
            color: white;
            opacity: 0.8;
            margin-top: 2rem;
        }
        
        .footer a {
            color: white;
            text-decoration: underline;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .build-modes {
                grid-template-columns: 1fr;
            }
            
            .mode-card {
                padding: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 SBH Build Hub</h1>
            <p>Choose your preferred way to build amazing systems. Both paths lead to the same destination - powerful, scalable modules.</p>
        </div>
        
        <div class="build-modes">
            <div class="mode-card vibe" onclick="window.location.href='/ui/cobuilder/'">
                <div class="mode-icon">⚡</div>
                <div class="mode-title">Vibe Mode</div>
                <div class="mode-subtitle">Chat-first exploration. Iterate fast.</div>
                <ul class="mode-benefits">
                    <li>Natural language conversations</li>
                    <li>Quick prototyping and iteration</li>
                    <li>AI-powered suggestions</li>
                    <li>Perfect for exploration</li>
                </ul>
                <a href="/ui/cobuilder/" class="mode-button">Start Chatting →</a>
            </div>
            
            <div class="mode-card spec" onclick="window.location.href='/ui/spec/'">
                <div class="mode-icon">📑</div>
                <div class="mode-title">Spec Mode</div>
                <div class="mode-subtitle">Plan-first. Define requirements, then generate.</div>
                <ul class="mode-benefits">
                    <li>Structured requirement gathering</li>
                    <li>Deterministic module generation</li>
                    <li>Enterprise-grade planning</li>
                    <li>Perfect for production</li>
                </ul>
                <a href="/ui/spec/" class="mode-button">Start Planning →</a>
            </div>
        </div>
        
        <div class="footer">
            <p>Both modes use the same powerful SBH engine. <a href="/ui/cobuilder/">Vibe Mode</a> | <a href="/ui/spec/">Spec Mode</a></p>
        </div>
    </div>
</body>
</html>
"""

@build_hub_bp.route('/build')
def build_hub():
    """Main build hub page with Vibe vs Spec choice"""
    return BUILD_HUB_HTML

@build_hub_bp.route('/build/')
def build_hub_redirect():
    """Redirect /build/ to /build"""
    return redirect(url_for('build_hub.build_hub'))
