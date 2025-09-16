"""
Spec Mode Wizard UI

Provides a structured interface for planning and generating modules
"""

from flask import Blueprint, render_template_string, request, redirect, url_for, jsonify
import json
import uuid

spec_ui_bp = Blueprint('spec_ui', __name__, url_prefix='/ui')

# HTML template for the Spec Wizard
SPEC_WIZARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SBH Spec Wizard - Plan Your Module</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .header {
            text-align: center;
            margin-bottom: 2rem;
            color: white;
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .wizard-form {
            background: white;
            border-radius: 20px;
            padding: 2.5rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-label {
            display: block;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #333;
        }
        
        .form-input {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #4ecdc4;
        }
        
        .form-textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        .form-select {
            background: white;
        }
        
        .chips-container {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        
        .chip {
            background: #4ecdc4;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .chip-remove {
            background: rgba(255,255,255,0.3);
            border: none;
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            cursor: pointer;
            font-size: 0.8rem;
        }
        
        .add-chip {
            background: #e1e5e9;
            color: #666;
            border: 2px dashed #ccc;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .add-chip:hover {
            background: #d1d5d9;
            border-color: #4ecdc4;
        }
        
        .plans-container {
            border: 2px dashed #e1e5e9;
            border-radius: 10px;
            padding: 1rem;
            margin-top: 0.5rem;
        }
        
        .plan-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
            border: 1px solid #e1e5e9;
        }
        
        .plan-item:last-child {
            margin-bottom: 0;
        }
        
        .plan-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .plan-name {
            font-weight: 600;
            color: #333;
        }
        
        .plan-price {
            color: #4ecdc4;
            font-weight: 600;
        }
        
        .plan-remove {
            background: #ff6b6b;
            color: white;
            border: none;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            cursor: pointer;
            font-size: 0.8rem;
        }
        
        .add-plan {
            background: #4ecdc4;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 10px;
            cursor: pointer;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
        
        .submit-btn {
            background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 50px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: all 0.3s ease;
        }
        
        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .submit-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .chat-link {
            text-align: center;
            margin-top: 1.5rem;
        }
        
        .chat-link a {
            color: #4ecdc4;
            text-decoration: none;
            font-weight: 600;
        }
        
        .chat-link a:hover {
            text-decoration: underline;
        }
        
        .success-message {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            display: none;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            display: none;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin: 1rem 0;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #4ecdc4;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .wizard-form {
                padding: 1.5rem;
            }
            
            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📑 Spec Wizard</h1>
            <p>Plan your module with structured requirements, then generate it automatically</p>
        </div>
        
        <div class="wizard-form">
            <div class="success-message" id="successMessage">
                ✅ Module generated successfully! Check the marketplace for your new module.
            </div>
            
            <div class="error-message" id="errorMessage">
                ❌ Error generating module. Please check your inputs and try again.
            </div>
            
            <form id="specForm">
                <div class="form-group">
                    <label class="form-label" for="name">Module Name (slug)</label>
                    <input type="text" id="name" name="name" class="form-input" placeholder="e.g., helpdesk, lms, crm" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label" for="title">Display Title</label>
                    <input type="text" id="title" name="title" class="form-input" placeholder="e.g., Helpdesk System, Learning Management System" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label" for="version">Version</label>
                    <input type="text" id="version" name="version" class="form-input" placeholder="1.0.0" value="1.0.0" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label" for="category">Category</label>
                    <select id="category" name="category" class="form-input form-select" required>
                        <option value="">Select a category</option>
                        <option value="business">Business</option>
                        <option value="education">Education</option>
                        <option value="support">Support</option>
                        <option value="productivity">Productivity</option>
                        <option value="communication">Communication</option>
                        <option value="analytics">Analytics</option>
                        <option value="other">Other</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Features</label>
                    <div class="chips-container" id="featuresContainer">
                        <div class="add-chip" onclick="addFeature()">+ Add Feature</div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Plans & Pricing</label>
                    <div class="plans-container" id="plansContainer">
                        <div class="add-plan" onclick="addPlan()">+ Add Plan</div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="form-label" for="description">Description</label>
                    <textarea id="description" name="description" class="form-input form-textarea" placeholder="Describe what your module does, its key features, and target users..." required></textarea>
                </div>
                
                <div class="form-group">
                    <label class="form-label" for="tags">Tags (comma-separated)</label>
                    <input type="text" id="tags" name="tags" class="form-input" placeholder="e.g., helpdesk, tickets, support, sla">
                </div>
                
                <button type="submit" class="submit-btn" id="submitBtn">
                    🚀 Generate Module
                </button>
            </form>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Generating your module...</p>
            </div>
            
            <div class="chat-link">
                <p>Prefer to chat? <a href="/ui/cobuilder/?message=Build a module with these requirements: " onclick="this.href += encodeURIComponent(document.getElementById('description').value)">Switch to Vibe Mode</a></p>
            </div>
        </div>
    </div>
    
    <script>
        let features = [];
        let plans = [];
        
        function addFeature() {
            const feature = prompt('Enter feature name:');
            if (feature && feature.trim()) {
                features.push(feature.trim());
                renderFeatures();
            }
        }
        
        function removeFeature(index) {
            features.splice(index, 1);
            renderFeatures();
        }
        
        function renderFeatures() {
            const container = document.getElementById('featuresContainer');
            container.innerHTML = '';
            
            features.forEach((feature, index) => {
                const chip = document.createElement('div');
                chip.className = 'chip';
                chip.innerHTML = `
                    ${feature}
                    <button class="chip-remove" onclick="removeFeature(${index})">×</button>
                `;
                container.appendChild(chip);
            });
            
            const addBtn = document.createElement('div');
            addBtn.className = 'add-chip';
            addBtn.onclick = addFeature;
            addBtn.textContent = '+ Add Feature';
            container.appendChild(addBtn);
        }
        
        function addPlan() {
            const name = prompt('Enter plan name:');
            if (!name || !name.trim()) return;
            
            const price = prompt('Enter plan price (e.g., $9.99, Free):');
            if (!price || !price.trim()) return;
            
            plans.push({
                name: name.trim(),
                price: price.trim()
            });
            renderPlans();
        }
        
        function removePlan(index) {
            plans.splice(index, 1);
            renderPlans();
        }
        
        function renderPlans() {
            const container = document.getElementById('plansContainer');
            container.innerHTML = '';
            
            plans.forEach((plan, index) => {
                const planItem = document.createElement('div');
                planItem.className = 'plan-item';
                planItem.innerHTML = `
                    <div class="plan-header">
                        <span class="plan-name">${plan.name}</span>
                        <span class="plan-price">${plan.price}</span>
                        <button class="plan-remove" onclick="removePlan(${index})">×</button>
                    </div>
                `;
                container.appendChild(planItem);
            });
            
            const addBtn = document.createElement('div');
            addBtn.className = 'add-plan';
            addBtn.onclick = addPlan;
            addBtn.textContent = '+ Add Plan';
            container.appendChild(addBtn);
        }
        
        document.getElementById('specForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                name: formData.get('name'),
                title: formData.get('title'),
                version: formData.get('version'),
                category: formData.get('category'),
                features: features,
                plans: plans,
                description: formData.get('description'),
                tags: formData.get('tags').split(',').map(t => t.trim()).filter(t => t)
            };
            
            // Show loading
            document.getElementById('loading').style.display = 'block';
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('successMessage').style.display = 'none';
            document.getElementById('errorMessage').style.display = 'none';
            
            try {
                const response = await fetch('/api/spec/build', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('successMessage').style.display = 'block';
                    document.getElementById('specForm').reset();
                    features = [];
                    plans = [];
                    renderFeatures();
                    renderPlans();
                } else {
                    document.getElementById('errorMessage').textContent = `❌ ${result.error || 'Unknown error occurred'}`;
                    document.getElementById('errorMessage').style.display = 'block';
                }
            } catch (error) {
                document.getElementById('errorMessage').textContent = `❌ Network error: ${error.message}`;
                document.getElementById('errorMessage').style.display = 'block';
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('submitBtn').disabled = false;
            }
        });
        
        // Pre-fill form if coming from Co-Builder
        const urlParams = new URLSearchParams(window.location.search);
        const prefillData = urlParams.get('prefill');
        if (prefillData) {
            try {
                const data = JSON.parse(decodeURIComponent(prefillData));
                if (data.description) {
                    document.getElementById('description').value = data.description;
                }
                if (data.features) {
                    features = data.features;
                    renderFeatures();
                }
            } catch (e) {
                console.log('Could not parse prefill data');
            }
        }
    </script>
</body>
</html>
"""

@spec_ui_bp.route('/spec')
def spec_wizard():
    """Spec Mode wizard interface"""
    return SPEC_WIZARD_HTML

@spec_ui_bp.route('/spec/')
def spec_wizard_redirect():
    """Redirect /spec/ to /spec"""
    return redirect(url_for('spec_ui.spec_wizard'))
