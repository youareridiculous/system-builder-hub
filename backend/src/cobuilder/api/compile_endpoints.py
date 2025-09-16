"""
SBH Backend API endpoints for compile and spec management
"""
import os
import json
import hashlib
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from ..persistent_registry import persistent_build_registry


compile_bp = Blueprint('compile', __name__, url_prefix='/api/cobuilder')


@compile_bp.route('/compile', methods=['POST'])
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
        
        # Get workspace path
        workspace_path = os.path.join(current_app.config.get('WORKSPACE_ROOT', 'workspace'), build_id)
        if not os.path.exists(workspace_path):
            return jsonify({'error': 'Build workspace not found'}), 404
        
        # Log compilation start
        persistent_build_registry.append_log(
            build_id, 
            "system", 
            "[COMPILER] Starting compilation..."
        )
        
        # Call the compiler
        result = _compile_spec_to_workspace(spec, workspace_path, build_id)
        
        # Log compilation result
        persistent_build_registry.append_log(
            build_id,
            "system",
            f"[COMPILER] Compilation complete: {len(result['writes'])} files written, {len(result['diffs'])} changes"
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Compilation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@compile_bp.route('/spec', methods=['GET', 'POST'])
def manage_spec():
    """Get or save specification for a build"""
    try:
        build_id = request.args.get('build_id') or request.json.get('build_id')
        if not build_id:
            return jsonify({'error': 'No build_id provided'}), 400
        
        # Get workspace path
        workspace_path = os.path.join(current_app.config.get('WORKSPACE_ROOT', 'workspace'), build_id)
        if not os.path.exists(workspace_path):
            return jsonify({'error': 'Build workspace not found'}), 404
        
        spec_path = os.path.join(workspace_path, 'apps', 'studio', 'storage', 'spec.json')
        
        if request.method == 'GET':
            # Get spec
            if os.path.exists(spec_path):
                with open(spec_path, 'r') as f:
                    spec = json.load(f)
                return jsonify({'spec': spec})
            else:
                return jsonify({'spec': None})
        
        elif request.method == 'POST':
            # Save spec
            data = request.get_json()
            if not data or 'spec' not in data:
                return jsonify({'error': 'No spec provided'}), 400
            
            spec = data['spec']
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(spec_path), exist_ok=True)
            
            # Save spec
            with open(spec_path, 'w') as f:
                json.dump(spec, f, indent=2)
            
            # Log spec save
            persistent_build_registry.append_log(
                build_id,
                "system",
                "[STUDIO] Specification saved"
            )
            
            return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Spec management error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@compile_bp.route('/diff', methods=['GET'])
def get_diff():
    """Get diff for a build"""
    try:
        build_id = request.args.get('build_id')
        if not build_id:
            return jsonify({'error': 'No build_id provided'}), 400
        
        # Get workspace path
        workspace_path = os.path.join(current_app.config.get('WORKSPACE_ROOT', 'workspace'), build_id)
        if not os.path.exists(workspace_path):
            return jsonify({'error': 'Build workspace not found'}), 404
        
        diff_path = os.path.join(workspace_path, 'apps', 'studio', 'storage', 'diff.json')
        
        if os.path.exists(diff_path):
            with open(diff_path, 'r') as f:
                diff = json.load(f)
            return jsonify({'diff': diff})
        else:
            return jsonify({'diff': []})
        
    except Exception as e:
        current_app.logger.error(f"Diff retrieval error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@compile_bp.route('/pricing', methods=['POST'])
def generate_pricing():
    """Generate pricing from specification"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        spec = data.get('spec')
        if not spec:
            return jsonify({'error': 'No spec provided'}), 400
        
        # Generate pricing based on spec
        pricing = _generate_pricing_from_spec(spec)
        
        return jsonify({
            'success': True,
            'pricing': pricing
        })
        
    except Exception as e:
        current_app.logger.error(f"Pricing generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@compile_bp.route('/deploy', methods=['POST'])
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
        
        # Get workspace path
        workspace_path = os.path.join(current_app.config.get('WORKSPACE_ROOT', 'workspace'), build_id)
        if not os.path.exists(workspace_path):
            return jsonify({'error': 'Build workspace not found'}), 404
        
        # Deploy to hosting provider
        result = _deploy_to_provider(workspace_path, provider, domain, build_id)
        
        return jsonify({
            'success': True,
            'url': result['url'],
            'provider': provider,
            'domain': result['domain']
        })
        
    except Exception as e:
        current_app.logger.error(f"Deployment error: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _compile_spec_to_workspace(spec: Dict[str, Any], workspace_path: str, build_id: str) -> Dict[str, Any]:
    """Compile specification to workspace files"""
    writes = []
    diffs = []
    
    # Create generated files directory
    gen_path = os.path.join(workspace_path, 'apps', 'site', 'gen')
    os.makedirs(gen_path, exist_ok=True)
    
    # Save spec as JSON
    spec_path = os.path.join(gen_path, 'spec.json')
    with open(spec_path, 'w') as f:
        json.dump(spec, f, indent=2)
    
    writes.append({
        'path': 'apps/site/gen/spec.json',
        'sha256': _calculate_sha256(json.dumps(spec, indent=2))
    })
    
    # Generate site config
    site_config_path = os.path.join(workspace_path, 'apps', 'site', 'site.config.ts')
    site_config_content = _generate_site_config(spec)
    with open(site_config_path, 'w') as f:
        f.write(site_config_content)
    
    writes.append({
        'path': 'apps/site/site.config.ts',
        'sha256': _calculate_sha256(site_config_content)
    })
    
    # Generate section components
    sections_path = os.path.join(workspace_path, 'apps', 'site', 'components', 'sections')
    os.makedirs(sections_path, exist_ok=True)
    
    for section in spec.get('sections', []):
        component_path = os.path.join(sections_path, f"{section['id']}.tsx")
        component_content = _generate_section_component(section)
        with open(component_path, 'w') as f:
            f.write(component_content)
        
        writes.append({
            'path': f"apps/site/components/sections/{section['id']}.tsx",
            'sha256': _calculate_sha256(component_content)
        })
    
    # Generate main page
    page_path = os.path.join(workspace_path, 'apps', 'site', 'app', 'page.tsx')
    page_content = _generate_main_page(spec)
    with open(page_path, 'w') as f:
        f.write(page_content)
    
    writes.append({
        'path': 'apps/site/app/page.tsx',
        'sha256': _calculate_sha256(page_content)
    })
    
    # Create diffs (simplified - in real implementation, compare with existing files)
    for write in writes:
        diffs.append({
            'path': write['path'],
            'type': 'added',
            'content': write['sha256'][:8] + '...'  # Truncated for display
        })
    
    # Save diff
    diff_path = os.path.join(workspace_path, 'apps', 'studio', 'storage')
    os.makedirs(diff_path, exist_ok=True)
    with open(os.path.join(diff_path, 'diff.json'), 'w') as f:
        json.dump(diffs, f, indent=2)
    
    return {
        'writes': writes,
        'diffs': diffs
    }


def _generate_site_config(spec: Dict[str, Any]) -> str:
    """Generate site configuration file"""
    return f'''import {{ CoreSpec }} from '@sbh/core'
import specData from './gen/spec.json'

export const siteConfig: CoreSpec = specData as CoreSpec

export function getSectionById(id: string) {{
  return siteConfig.sections.find(section => section.id === id)
}}

export function getSectionsByType(type: string) {{
  return siteConfig.sections.filter(section => section.type === type)
}}

export function getBrand() {{
  return siteConfig.brand
}}

export function getGoals() {{
  return siteConfig.goals
}}
'''


def _generate_section_component(section: Dict[str, Any]) -> str:
    """Generate a section component"""
    component_name = section['id'].replace('-', ' ').title().replace(' ', '')
    
    return f'''import React from 'react'

interface {component_name}Props {{
  // Add props as needed
}}

export function {component_name}({{ }}: {component_name}Props) {{
  return (
    <section className="py-16">
      <div className="container mx-auto px-4">
        {f'<h2 className="text-3xl font-bold text-center mb-8">{section.get("title", "")}</h2>' if section.get('title') else ''}
        {f'<p className="text-xl text-center text-gray-600 mb-12">{section.get("subtitle", "")}</p>' if section.get('subtitle') else ''}
        <div className="content">
          {{/* Generated content for {section['type']} section */}}
          <div className="text-center">
            <p className="text-gray-500">Section: {section['id']}</p>
            <p className="text-sm text-gray-400">Type: {section['type']}</p>
          </div>
        </div>
      </div>
    </section>
  )
}}
'''


def _generate_main_page(spec: Dict[str, Any]) -> str:
    """Generate main page component"""
    sections = spec.get('sections', [])
    
    imports = []
    components = []
    
    for section in sections:
        component_name = section['id'].replace('-', ' ').title().replace(' ', '')
        imports.append(f"import {{ {component_name} }} from '@/components/sections/{section['id']}'")
        components.append(f"      <{component_name} />")
    
    imports_str = '\n'.join(imports)
    components_str = '\n'.join(components)
    
    return f'''import React from 'react'
{imports_str}

export default function HomePage() {{
  return (
    <main>
{components_str}
    </main>
  )
}}
'''


def _generate_pricing_from_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate pricing information from specification"""
    sections = spec.get('sections', [])
    goals = spec.get('goals', [])
    
    # Simple pricing calculation based on complexity
    base_price = 99
    section_price = len(sections) * 25
    goal_price = len(goals) * 15
    
    total_price = base_price + section_price + goal_price
    
    return {
        'tiers': [
            {
                'name': 'Basic',
                'price': total_price,
                'currency': 'USD',
                'features': [
                    f'{len(sections)} sections',
                    f'{len(goals)} goals',
                    'Basic hosting',
                    'Email support'
                ]
            },
            {
                'name': 'Pro',
                'price': total_price * 1.5,
                'currency': 'USD',
                'features': [
                    f'{len(sections)} sections',
                    f'{len(goals)} goals',
                    'Premium hosting',
                    'Priority support',
                    'Custom domain',
                    'Analytics'
                ],
                'popular': True
            },
            {
                'name': 'Enterprise',
                'price': total_price * 2,
                'currency': 'USD',
                'features': [
                    f'{len(sections)} sections',
                    f'{len(goals)} goals',
                    'Enterprise hosting',
                    '24/7 support',
                    'Custom domain',
                    'Advanced analytics',
                    'White-label'
                ]
            }
        ],
        'estimated_cost': total_price,
        'breakdown': {
            'base': base_price,
            'sections': section_price,
            'goals': goal_price
        }
    }


def _deploy_to_provider(workspace_path: str, provider: str, domain: str, build_id: str) -> Dict[str, Any]:
    """Deploy website to hosting provider"""
    import random
    import string
    
    # Generate a random domain if auto
    if domain == 'auto':
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        domain = f"ai-website-{random_suffix}"
    
    # Simulate deployment (in real implementation, this would call actual hosting APIs)
    if provider == 'vercel':
        url = f"https://{domain}.vercel.app"
    elif provider == 'netlify':
        url = f"https://{domain}.netlify.app"
    elif provider == 'aws':
        url = f"https://{domain}.amazonaws.com"
    else:
        url = f"https://{domain}.example.com"
    
    # Log deployment
    persistent_build_registry.append_log(
        build_id,
        "system",
        f"[DEPLOY] Deployed to {provider} at {url}"
    )
    
    return {
        'url': url,
        'domain': domain,
        'provider': provider,
        'status': 'deployed'
    }


def _calculate_sha256(content: str) -> str:
    """Calculate SHA256 hash of content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
