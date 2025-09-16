"""
Section codegen generator for creating React components from spec sections.
"""

import os
from typing import Dict, List, Any


def generate_sections_codegen(build_id: str, workspace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate section components and main page from spec."""
    try:
        build_dir = f"{workspace}/{build_id}"
        
        # Extract sections from spec
        sections = spec.get('sections', [])
        if not sections:
            # Default sections if none provided
            sections = [
                {'type': 'hero', 'title': 'Hero Section'},
                {'type': 'feature-grid', 'title': 'Feature Grid Section'},
                {'type': 'logo-cloud', 'title': 'Logo Cloud Section'},
                {'type': 'showreel', 'title': 'Showreel Section'},
                {'type': 'pricing', 'title': 'Pricing Section'},
                {'type': 'cta-banner', 'title': 'CTA Banner Section'}
            ]
        
        # Generate main page
        main_page_content = _generate_main_page(sections)
        main_page_path = f"{build_dir}/apps/site/app/page.tsx"
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(main_page_path), exist_ok=True)
        
        # Write main page
        with open(main_page_path, 'w') as f:
            f.write(main_page_content)
        
        # Generate section components
        components_dir = f"{build_dir}/apps/site/components/sections"
        os.makedirs(components_dir, exist_ok=True)
        
        for section in sections:
            component_content = _generate_section_component(section)
            component_name = section['type'].title().replace('-', '')
            component_path = f"{components_dir}/{component_name}.tsx"
            
            with open(component_path, 'w') as f:
                f.write(component_content)
        
        return {
            "success": True,
            "path": main_page_path,
            "sha256": "generated",
            "lines_changed": len(main_page_content.split('\n')),
            "is_directory": False
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": "",
            "sha256": "",
            "lines_changed": 0,
            "is_directory": False
        }


def _generate_section_component(section: Dict[str, Any]) -> str:
    """Generate a React component for a specific section."""
    section_type = section['type']
    title = section_type.title().replace('-', '')
    
    if section_type == 'hero':
        return f'''import React from 'react'

interface Props {{
  title?: string
  subtitle?: string
  cta?: {{
    text: string
    href: string
  }}
}}

export default function {title}({{ title, subtitle, cta }}: Props) {{
  return (
    <section className="py-20 px-4 text-center">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">{{title}}</h1>
        <p className="text-xl text-gray-600 mb-8">{{subtitle}}</p>
        {{cta && (
          <a
            href={{cta.href}}
            className="inline-flex items-center justify-center rounded-lg px-8 py-3 text-lg font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            {{cta.text}}
          </a>
        )}}
      </div>
    </section>
  )
}}
'''
    
    elif section_type == 'feature-grid':
        return f'''import React from 'react'

interface Props {{
  title?: string
  subtitle?: string
  features?: Array<{{
    title: string
    description: string
  }}>
}}

export default function {title}({{ title, subtitle, features }}: Props) {{
  return (
    <section className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">{{title}}</h2>
          {{subtitle && <p className="text-xl text-gray-600">{{subtitle}}</p>}}
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {{features?.map((feature, index) => (
            <div key={{index}} className="text-center">
              <h3 className="text-xl font-semibold text-gray-900 mb-2">{{feature.title}}</h3>
              <p className="text-gray-600">{{feature.description}}</p>
            </div>
          ))}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    elif section_type == 'logo-cloud':
        return f'''import React from 'react'

interface Props {{
  title?: string
  logos?: Array<{{
    name: string
    url: string
  }}>
}}

export default function {title}({{ title, logos }}: Props) {{
  return (
    <section className="py-20 px-4 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        {{title && <h2 className="text-4xl font-bold text-gray-900 mb-16 text-center">{{title}}</h2>}}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-8 items-center">
          {{logos?.map((logo, index) => (
            <div key={{index}} className="text-center">
              <div className="text-2xl font-bold text-gray-600">{{logo.name}}</div>
            </div>
          ))}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    elif section_type == 'showreel':
        return f'''import React from 'react'

interface Props {{
  title?: string
  description?: string
  videoUrl?: string
  imageUrl?: string
}}

export default function {title}({{ title, description, videoUrl, imageUrl }}: Props) {{
  return (
    <section className="py-20 px-4">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-4xl font-bold text-gray-900 mb-4">{{title}}</h2>
        <p className="text-xl text-gray-600 mb-12">{{description}}</p>
        <div className="aspect-video bg-gray-200 rounded-lg flex items-center justify-center">
          {{videoUrl ? (
            <video controls className="w-full h-full rounded-lg">
              <source src={{videoUrl}} type="video/mp4" />
            </video>
          ) : (
            <div className="text-gray-500 text-lg">Demo Video Placeholder</div>
          )}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    elif section_type == 'pricing':
        return f'''import React from 'react'

interface Props {{
  title?: string
  subtitle?: string
  plans?: Array<{{
    name: string
    price: string
    description?: string
    features?: string[]
    cta?: string
  }}>
}}

export default function {title}({{ title, subtitle, plans }}: Props) {{
  return (
    <section className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">{{title}}</h2>
          {{subtitle && <p className="text-xl text-gray-600">{{subtitle}}</p>}}
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {{plans?.map((plan, index) => (
            <div key={{index}} className="bg-white border border-gray-200 rounded-lg p-8 text-center">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">{{plan.name}}</h3>
              <div className="text-4xl font-bold text-blue-600 mb-4">{{plan.price}}</div>
              {{plan.description && <p className="text-gray-600 mb-6">{{plan.description}}</p>}}
              {{plan.features && (
                <ul className="text-left mb-8 space-y-2">
                  {{plan.features.map((feature, idx) => (
                    <li key={{idx}} className="flex items-center">
                      <span className="text-blue-600 mr-2">✓</span>
                      {{feature}}
                    </li>
                  ))}}
                </ul>
              )}}
              {{plan.cta && (
                <button className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors">
                  {{plan.cta}}
                </button>
              )}}
            </div>
          ))}}
        </div>
      </div>
    </section>
  )
}}
'''
    
    elif section_type == 'cta-banner':
        return f'''import React from 'react'

interface Props {{
  title?: string
  subtitle?: string
  button?: string
  buttonHref?: string
}}

export default function {title}({{ title, subtitle, button, buttonHref }}: Props) {{
  return (
    <section className="py-20 px-4 bg-blue-600">
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-4xl font-bold text-white mb-4">{{title}}</h2>
        {{subtitle && <p className="text-xl text-blue-100 mb-8">{{subtitle}}</p>}}
        <a
          href={{buttonHref || '#'}}
          className="inline-flex items-center justify-center rounded-lg px-8 py-3 text-lg font-medium bg-white text-blue-600 hover:bg-gray-100 transition-colors"
        >
          {{button}}
        </a>
      </div>
    </section>
  )
}}
'''
    
    else:
        # Generic section
        return f'''import React from 'react'

interface Props {{
  title?: string
  children?: React.ReactNode
  className?: string
}}

export default function {title}({{ title, children, className = '' }}: Props) {{
  return (
    <section className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        {{title && <h2 className="text-4xl font-bold text-gray-900 mb-8 text-center">{{title}}</h2>}}
        {{children}}
      </div>
    </section>
  )
}}
'''


def _generate_main_page(sections: List[Dict[str, Any]]) -> str:
    """Generate the main page.tsx file that imports and renders all sections."""
    
    # Generate imports
    imports = []
    for section in sections:
        component_name = section['type'].title().replace('-', '')
        imports.append(f"import {component_name} from './components/sections/{component_name}'")
    
    imports_str = '\n'.join(imports)
    
    # Generate JSX
    jsx_elements = []
    for section in sections:
        component_name = section['type'].title().replace('-', '')
        jsx_elements.append(f"      <{component_name} />")
    
    jsx_str = '\n'.join(jsx_elements)
    
    return f'''{imports_str}

export default function Page() {{
  return (
    <main>
{jsx_str}
    </main>
  )
}}
'''
