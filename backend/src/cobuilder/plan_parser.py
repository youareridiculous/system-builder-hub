#!/usr/bin/env python3
"""
Plan Parser for SBH Full Build Mode

Parses structured inputs (docx/markdown/text) containing sections like:
- System Map
- Spec
- Generators  
- Acceptance Criteria
- Roadmap

Maps concepts to actions and creates TaskGraph for orchestration.
"""

import re
import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """Types of tasks in the build plan"""
    CREATE_FILE = "create_file"
    CREATE_DIRECTORY = "create_directory"
    GENERATE_MODULE = "generate_module"
    CREATE_SCHEMA = "create_schema"
    CREATE_TEST = "create_test"
    RUN_ACCEPTANCE = "run_acceptance"
    SETUP_REPO = "setup_repo"

@dataclass
class TaskNode:
    """Represents a single task in the build plan"""
    task_id: str
    task_type: TaskType
    file: Optional[str] = None
    directory: Optional[str] = None
    anchor: Optional[str] = None
    content: Optional[str] = None
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None
    acceptance_criteria: Optional[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

@dataclass
class TaskGraph:
    """Represents the complete build plan as a graph of tasks"""
    nodes: List[TaskNode]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class PlanParser:
    """Parses structured plan documents into TaskGraph"""
    
    def __init__(self):
        self.concept_mappings = {
            # Repo Skeleton concepts
            "repo skeleton": "setup_repo",
            "directory structure": "create_directory", 
            "folder structure": "create_directory",
            "package structure": "create_directory",
            
            # Spec concepts
            "spec": "create_schema",
            "schema": "create_schema",
            "zod": "create_schema",
            "validation": "create_schema",
            
            # Generator concepts
            "generator": "generate_module",
            "generators": "generate_module",
            "module": "generate_module",
            "component": "generate_module",
            
            # Test concepts
            "test": "create_test",
            "tests": "create_test",
            "acceptance": "run_acceptance",
            "criteria": "run_acceptance",
        }
    
    def parse_plan(self, content: str, format_type: str = "text") -> TaskGraph:
        """Parse plan content into TaskGraph"""
        try:
            if format_type == "docx":
                return self._parse_docx(content)
            elif format_type == "markdown":
                return self._parse_markdown(content)
            else:
                return self._parse_text(content)
        except Exception as e:
            logger.error(f"Failed to parse plan: {e}")
            raise
    
    def _parse_text(self, content: str) -> TaskGraph:
        """Parse plain text content"""
        # Check for AI Website Builder specification first
        if self._is_ai_website_builder_spec(content):
            nodes = self._parse_ai_website_builder_spec(content)
            return TaskGraph(nodes=nodes, metadata={"source": "ai_website_builder", "sections": []})
        
        # Fall back to section-based parsing
        sections = self._extract_sections(content)
        nodes = []
        
        for section_name, section_content in sections.items():
            section_nodes = self._parse_section(section_name, section_content)
            nodes.extend(section_nodes)
        
        # If no sections found, try to parse as simple message
        if not nodes and content.strip():
            nodes = self._parse_simple_message(content)
        
        return TaskGraph(nodes=nodes, metadata={"source": "text", "sections": list(sections.keys())})
    
    def _parse_markdown(self, content: str) -> TaskGraph:
        """Parse markdown content"""
        # Extract sections using markdown headers
        sections = {}
        current_section = None
        current_content = []
        
        for line in content.split('\n'):
            if line.startswith('#'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line.strip('# ').lower()
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        nodes = []
        for section_name, section_content in sections.items():
            section_nodes = self._parse_section(section_name, section_content)
            nodes.extend(section_nodes)
        
        return TaskGraph(nodes=nodes, metadata={"source": "markdown", "sections": list(sections.keys())})
    
    def _parse_docx(self, content: str) -> TaskGraph:
        """Parse docx content with comprehensive AI Website Builder system extraction"""
        try:
            # Extract the full AI Website Builder specification from the DOCX content
            spec = self._extract_full_ai_website_builder_spec(content)
            
            # Create a comprehensive task graph for the complete AI Website Builder system
            nodes = []
            
            # Extract all system components from the DOCX
            system_components = self._extract_system_components(content)
            
            # Add the complete AI Website Builder system steps
            ai_website_builder_steps = [
                # Control Plane (Studio)
                ("generate_studio_app", "Generate Studio Control Plane app with Next.js 14"),
                ("generate_studio_routes", "Generate Studio routes (/spec, /compile, /preview, /diff, /deploy, /pricing)"),
                ("generate_studio_ui", "Generate Studio UI components for spec editing and compilation"),
                
                # Data Plane (Generated Site)
                ("generate_site_app", "Generate Next.js 14 site app with App Router"),
                ("generate_site_components", "Generate site components driven by spec JSON"),
                ("generate_site_config", "Generate site.config.ts loader for compiled spec artifacts"),
                
                # Compiler & Packages
                ("generate_core_package", "Generate packages/core with types and utilities"),
                ("generate_compiler_package", "Generate packages/compiler with compileSpec function"),
                ("generate_validators_package", "Generate packages/validators for spec validation"),
                ("generate_integrations_package", "Generate packages/integrations (payments, email, analytics)"),
                ("generate_infra_package", "Generate packages/infra (hosting adapters, deploy plans)"),
                ("generate_runtime_package", "Generate packages/runtime (client/runtime helpers)"),
                
                # Backend & API
                ("generate_compile_endpoints", "Generate SBH backend endpoints (/api/cobuilder/compile, /api/cobuilder/spec)"),
                ("generate_lead_api", "Generate lead capture API with Prisma integration"),
                ("generate_payments_router", "Generate payments router with multi-provider support"),
                
                # Database & Infrastructure
                ("generate_prisma_schema", "Generate Prisma schema with Lead model and multi-tenant support"),
                ("generate_database_migrations", "Generate database migrations and setup"),
                
                # Hosting & Deployment
                ("generate_hosting_config", "Generate hosting configuration (Vercel, Cloudflare, AWS)"),
                ("generate_domain_management", "Generate domain connection and SSL provisioning"),
                ("generate_deployment_scripts", "Generate deployment and CI/CD scripts"),
                
                # Documentation & Testing
                ("generate_documentation", "Generate comprehensive documentation and user guides"),
                ("generate_test_suite", "Generate test suite with Lighthouse CI, Playwright, API tests"),
                
                # Integration & Orchestration
                ("generate_orchestrator_hooks", "Add orchestration hooks into SBH for compile and spec management"),
                ("generate_verifier_updates", "Update verifier to check for Studio and compiler prerequisites"),
                ("generate_root_package_json", "Update root package.json with new scripts and workspace structure"),
                ("generate_compile_script", "Generate scripts/compile-from-spec.js for CLI compilation")
            ]
            
            for step_id, description in ai_website_builder_steps:
                nodes.append(TaskNode(
                    task_id=step_id,
                    task_type=TaskType.GENERATE_MODULE,
                    content=description,
                    metadata={
                        "source": "ai_website_builder_full_spec",
                        "spec": spec,
                        "system_components": system_components,
                        "description": description,
                        "step_order": len(nodes) + 1,
                        "category": self._categorize_step(step_id)
                    }
                ))
            
            return TaskGraph(
                nodes=nodes, 
                metadata={
                    "source": "ai_website_builder_full_spec", 
                    "spec": spec,
                    "system_components": system_components,
                    "total_steps": len(ai_website_builder_steps),
                    "architecture": "complete_ai_website_builder_system"
                }
            )
            
        except Exception as e:
            logger.error(f"DOCX parsing failed: {e}")
            # Fallback to text parsing
            return self._parse_text(content)
    
    def _extract_full_ai_website_builder_spec(self, content: str) -> Dict[str, Any]:
        """Extract the complete AI Website Builder specification from DOCX content"""
        try:
            # Look for comprehensive AI Website Builder specification
            spec_patterns = [
                r'(?i)Full‑Stack, Integration‑Ready AI Website Builder.*?(?=\n\n|\Z)',
                r'(?i)AI Website Builder System.*?(?=\n\n|\Z)',
                r'(?i)System Map.*?(?=\n\n|\Z)',
                r'(?i)Control Plane.*?(?=\n\n|\Z)',
                r'(?i)Data Plane.*?(?=\n\n|\Z)',
            ]
            
            extracted_spec = {}
            for pattern in spec_patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    section_content = match.group(0)
                    # Extract key components from each section
                    if 'Control Plane' in section_content:
                        extracted_spec['control_plane'] = self._extract_control_plane_spec(section_content)
                    elif 'Data Plane' in section_content:
                        extracted_spec['data_plane'] = self._extract_data_plane_spec(section_content)
                    elif 'System Map' in section_content:
                        extracted_spec['system_map'] = self._extract_system_map_spec(section_content)
            
            # If no specific sections found, create comprehensive spec
            if not extracted_spec:
                extracted_spec = self._get_comprehensive_ai_website_builder_spec()
            
            logger.info(f"Successfully extracted comprehensive AI Website Builder spec with {len(extracted_spec)} components")
            return extracted_spec
                
        except Exception as e:
            logger.error(f"Full spec extraction failed: {e}")
            return self._get_comprehensive_ai_website_builder_spec()
    
    def _extract_system_components(self, content: str) -> Dict[str, Any]:
        """Extract system components from DOCX content"""
        components = {
            "studio_app": {"routes": ["/", "/spec", "/compile", "/preview", "/diff", "/deploy", "/pricing"]},
            "generated_site": {"framework": "Next.js 14", "router": "App Router", "database": "Prisma"},
            "compiler_packages": ["core", "compiler", "validators", "integrations", "infra", "runtime"],
            "hosting": {"providers": ["Vercel", "Cloudflare", "AWS"], "ssl": "ACME/Let's Encrypt"},
            "integrations": {"payments": ["Stripe", "PayPal", "Adyen", "Razorpay"], "auth": ["Clerk", "Auth0"]}
        }
        return components
    
    def _categorize_step(self, step_id: str) -> str:
        """Categorize build steps"""
        if "studio" in step_id:
            return "control_plane"
        elif "site" in step_id:
            return "data_plane"
        elif "package" in step_id or "compiler" in step_id:
            return "compiler_packages"
        elif "api" in step_id or "endpoint" in step_id:
            return "backend_api"
        elif "prisma" in step_id or "database" in step_id:
            return "database"
        elif "hosting" in step_id or "deploy" in step_id:
            return "hosting_deployment"
        elif "doc" in step_id or "test" in step_id:
            return "documentation_testing"
        else:
            return "integration_orchestration"
    
    def _get_comprehensive_ai_website_builder_spec(self) -> Dict[str, Any]:
        """Get comprehensive AI Website Builder specification"""
        return {
            "title": "AI Website Builder System",
            "description": "Full-Stack, Integration-Ready AI Website Builder",
            "architecture": {
                "control_plane": "Studio app for operators to upload/parse specs, compile, preview, diff, deploy",
                "data_plane": "Generated Next.js 14 websites with Prisma database and API routes",
                "compiler": "Robust compilation engine that transforms specifications into production-ready websites",
                "hosting": "Multi-provider hosting with domain management and SSL provisioning"
            },
            "features": [
                "Upload DOCX specs and edit configurations",
                "Compile websites with AI-powered generation",
                "Preview and diff changes",
                "Deploy to multiple hosting providers",
                "Domain connection and SSL management",
                "Multi-provider payments integration",
                "Comprehensive testing and validation"
            ],
            "sections": [
                {"type": "hero", "title": "AI Website Builder", "subtitle": "Build amazing websites with AI"},
                {"type": "feature-grid", "title": "Features", "features": [
                    {"title": "Studio Control Plane", "description": "Upload specs, edit, compile, deploy"},
                    {"title": "Generated Sites", "description": "Next.js 14 apps with Prisma and API routes"},
                    {"title": "AI Compilation", "description": "Transform specs into production-ready websites"},
                    {"title": "Multi-Provider Hosting", "description": "Deploy to Vercel, Cloudflare, AWS"}
                ]},
                {"type": "pricing", "title": "Pricing", "plans": [
                    {"name": "Starter", "price": "$29/month", "features": ["1 hosted site", "5k visits", "1 custom domain"]},
                    {"name": "Pro", "price": "$79/month", "features": ["5 sites", "100k visits", "forms/surveys/chat"]},
                    {"name": "Studio", "price": "$199/month", "features": ["unlimited sites", "multi-region hosting", "white-label"]}
                ]}
            ]
        }
    
    def _extract_control_plane_spec(self, content: str) -> Dict[str, Any]:
        """Extract Control Plane (Studio) specification"""
        return {
            "name": "Studio Control Plane",
            "framework": "Next.js 14",
            "routes": ["/", "/spec", "/compile", "/preview", "/diff", "/deploy", "/pricing"],
            "features": ["spec upload", "configuration editing", "compilation", "preview", "deployment"]
        }
    
    def _extract_data_plane_spec(self, content: str) -> Dict[str, Any]:
        """Extract Data Plane (Generated Site) specification"""
        return {
            "name": "Generated Site Data Plane",
            "framework": "Next.js 14",
            "router": "App Router",
            "database": "Prisma",
            "features": ["spec-driven components", "API routes", "database integration"]
        }
    
    def _extract_system_map_spec(self, content: str) -> Dict[str, Any]:
        """Extract System Map specification"""
        return {
            "control_plane": "Studio app for operators",
            "data_plane": "Generated Next.js apps",
            "compiler": "Spec to website transformation",
            "hosting": "Multi-provider deployment"
        }

    def _extract_example_spec_json(self, content: str) -> Dict[str, Any]:
        """Extract and parse the Example Spec JSON from DOCX content"""
        try:
            # Look for "Example Spec" section
            spec_pattern = r'(?i)Example Spec[^}]*?(\{[^}]*\})'
            match = re.search(spec_pattern, content, re.DOTALL)
            
            if not match:
                # Try alternative patterns
                spec_patterns = [
                    r'(?i)Example Spec.*?(\{.*?\})',
                    r'(?i)Spec.*?(\{.*?\})',
                    r'(\{[^}]*"sections"[^}]*\})',
                ]
                
                for pattern in spec_patterns:
                    match = re.search(pattern, content, re.DOTALL)
                    if match:
                        break
            
            if match:
                json_str = match.group(1)
                
                # Normalize the JSON string
                json_str = self._normalize_json_string(json_str)
                
                # Parse the JSON
                spec = json.loads(json_str)
                
                # Validate and normalize the spec
                spec = self._normalize_spec(spec)
                
                logger.info(f"Successfully extracted spec with {len(spec.get('sections', []))} sections")
                return spec
            else:
                logger.warning("No Example Spec JSON found, using default spec")
                return self._get_default_spec()
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Raw JSON string: {json_str if 'json_str' in locals() else 'Not found'}")
            return self._get_default_spec()
        except Exception as e:
            logger.error(f"Spec extraction failed: {e}")
            return self._get_default_spec()
    
    def _normalize_json_string(self, json_str: str) -> str:
        """Normalize JSON string by fixing common issues from DOCX conversion"""
        # Replace smart quotes with ASCII quotes
        json_str = json_str.replace('"', '"').replace('"', '"')
        json_str = json_str.replace(''', "'").replace(''', "'")
        
        # Remove trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Remove comments (// and /* */)
        json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # Clean up whitespace
        json_str = json_str.strip()
        
        return json_str
    
    def _normalize_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize the spec to ensure it has the expected structure"""
        if not isinstance(spec, dict):
            return self._get_default_spec()
        
        # Ensure sections exist
        if 'sections' not in spec:
            spec['sections'] = []
        
        # Normalize each section
        normalized_sections = []
        for section in spec.get('sections', []):
            if isinstance(section, dict):
                normalized_section = self._normalize_section(section)
                normalized_sections.append(normalized_section)
        
        spec['sections'] = normalized_sections
        
        return spec
    
    def _normalize_section(self, section: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single section to ensure it has required fields"""
        if not isinstance(section, dict):
            return {"type": "hero", "headline": "Welcome"}
        
        # Ensure type exists
        if 'type' not in section:
            section['type'] = 'hero'
        
        # Map common field names
        if 'headline' in section and 'title' not in section:
            section['title'] = section['headline']
        if 'sub' in section and 'subtitle' not in section:
            section['subtitle'] = section['sub']
        
        # Provide defaults for missing fields
        section_type = section.get('type', 'hero')
        
        if section_type == 'hero':
            section.setdefault('title', 'Welcome to Our Platform')
            section.setdefault('subtitle', 'Build amazing things with our tools')
            section.setdefault('cta', {'text': 'Get Started', 'href': '/signup'})
        elif section_type == 'feature-grid':
            section.setdefault('title', 'Features')
            section.setdefault('features', [
                {'title': 'Feature 1', 'description': 'Description 1'},
                {'title': 'Feature 2', 'description': 'Description 2'},
                {'title': 'Feature 3', 'description': 'Description 3'}
            ])
        elif section_type == 'logo-cloud':
            section.setdefault('title', 'Trusted by')
            section.setdefault('logos', ['Company 1', 'Company 2', 'Company 3'])
        elif section_type == 'showreel':
            section.setdefault('title', 'See It In Action')
            section.setdefault('description', 'Watch our demo')
        elif section_type == 'pricing':
            section.setdefault('title', 'Simple Pricing')
            section.setdefault('tiers', [
                {'name': 'Basic', 'price': '$9/month', 'features': ['Feature 1', 'Feature 2']},
                {'name': 'Pro', 'price': '$29/month', 'features': ['All Basic', 'Feature 3', 'Feature 4']}
            ])
        elif section_type == 'cta-banner':
            section.setdefault('title', 'Ready to Get Started?')
            section.setdefault('button', 'Start Free Trial')
        
        return section
    
    def _get_default_spec(self) -> Dict[str, Any]:
        """Get a default spec when parsing fails"""
        return {
            "sections": [
                {
                    "type": "hero",
                    "title": "Welcome to Our Platform",
                    "subtitle": "Build amazing things with our tools",
                    "cta": {"text": "Get Started", "href": "/signup"}
                },
                {
                    "type": "feature-grid",
                    "title": "Features",
                    "features": [
                        {"title": "Feature 1", "description": "Description 1"},
                        {"title": "Feature 2", "description": "Description 2"},
                        {"title": "Feature 3", "description": "Description 3"}
                    ]
                },
                {
                    "type": "logo-cloud",
                    "title": "Trusted by",
                    "logos": ["Company 1", "Company 2", "Company 3"]
                },
                {
                    "type": "showreel",
                    "title": "See It In Action",
                    "description": "Watch our demo"
                },
                {
                    "type": "pricing",
                    "title": "Simple Pricing",
                    "tiers": [
                        {"name": "Basic", "price": "$9/month", "features": ["Feature 1", "Feature 2"]},
                        {"name": "Pro", "price": "$29/month", "features": ["All Basic", "Feature 3", "Feature 4"]}
                    ]
                },
                {
                    "type": "cta-banner",
                    "title": "Ready to Get Started?",
                    "button": "Start Free Trial"
                }
            ]
        }
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract sections from content using common patterns"""
        sections = {}
        
        # Common section patterns
        section_patterns = [
            r'(?i)(repo skeleton|directory structure|folder structure)',
            r'(?i)(spec|schema|zod|validation)',
            r'(?i)(generator|generators|module|component)',
            r'(?i)(acceptance criteria|acceptance|criteria)',
            r'(?i)(roadmap|plan|timeline)',
            r'(?i)(system map|architecture)',
        ]
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                section_name = match.group(1).lower()
                # Extract content until next section or end
                start_pos = match.end()
                next_section = re.search(r'(?i)(repo skeleton|spec|generator|acceptance|roadmap|system map)', 
                                       content[start_pos:])
                if next_section:
                    end_pos = start_pos + next_section.start()
                else:
                    end_pos = len(content)
                
                sections[section_name] = content[start_pos:end_pos].strip()
        
        return sections
    
    def _parse_section(self, section_name: str, section_content: str) -> List[TaskNode]:
        """Parse a specific section into task nodes"""
        nodes = []
        
        # Map section to task type
        task_type = self._map_concept_to_task_type(section_name)
        
        if task_type == TaskType.SETUP_REPO:
            nodes.extend(self._parse_repo_skeleton(section_content))
        elif task_type == TaskType.CREATE_SCHEMA:
            nodes.extend(self._parse_spec_section(section_content))
        elif task_type == TaskType.GENERATE_MODULE:
            nodes.extend(self._parse_generators_section(section_content))
        elif task_type == TaskType.RUN_ACCEPTANCE:
            nodes.extend(self._parse_acceptance_section(section_content))
        
        return nodes
    
    def _map_concept_to_task_type(self, concept: str) -> TaskType:
        """Map concept to task type"""
        concept_lower = concept.lower()
        
        for key, task_type in self.concept_mappings.items():
            if key in concept_lower:
                return TaskType(task_type)
        
        return TaskType.CREATE_FILE  # Default
    
    def _parse_repo_skeleton(self, content: str) -> List[TaskNode]:
        """Parse repo skeleton section into directory/file creation tasks"""
        nodes = []
        
        # Look for directory patterns
        dir_patterns = [
            r'(?i)(?:create|add|setup)\s+(?:directory|folder|package)\s+([^\s\n]+)',
            r'(?i)(?:directory|folder|package)\s+([^\s\n]+)',
            r'([a-zA-Z_][a-zA-Z0-9_]*/[a-zA-Z_][a-zA-Z0-9_]*)',  # path-like patterns
        ]
        
        for pattern in dir_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                dir_path = match.group(1).strip('/')
                if dir_path:
                    nodes.append(TaskNode(
                        task_id=f"create_dir_{dir_path.replace('/', '_')}",
                        task_type=TaskType.CREATE_DIRECTORY,
                        directory=dir_path,
                        metadata={"source": "repo_skeleton"}
                    ))
        
        # Look for file patterns
        file_patterns = [
            r'(?i)(?:create|add|setup)\s+(?:file|module)\s+([^\s\n]+)',
            r'([a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z0-9]+)',  # file extensions
        ]
        
        for pattern in file_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                file_path = match.group(1)
                if file_path and '.' in file_path:
                    nodes.append(TaskNode(
                        task_id=f"create_file_{file_path.replace('/', '_').replace('.', '_')}",
                        task_type=TaskType.CREATE_FILE,
                        file=file_path,
                        content="# TODO: Implement based on plan",
                        metadata={"source": "repo_skeleton"}
                    ))
        
        return nodes
    
    def _parse_spec_section(self, content: str) -> List[TaskNode]:
        """Parse spec section into schema creation tasks"""
        nodes = []
        
        # Look for schema definitions
        schema_patterns = [
            r'(?i)(?:schema|spec|zod)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'(?i)(?:define|create)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:schema|spec)',
        ]
        
        for pattern in schema_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                schema_name = match.group(1)
                nodes.append(TaskNode(
                    task_id=f"create_schema_{schema_name}",
                    task_type=TaskType.CREATE_SCHEMA,
                    file=f"src/schema/{schema_name}.ts",
                    content=f"// {schema_name} schema definition\n// TODO: Implement based on plan",
                    metadata={"schema_name": schema_name, "source": "spec"}
                ))
        
        return nodes
    
    def _parse_generators_section(self, content: str) -> List[TaskNode]:
        """Parse generators section into module creation tasks"""
        nodes = []
        
        # Look for generator definitions
        generator_patterns = [
            r'(?i)(?:generator|module|component)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'(?i)(?:create|add)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:generator|module)',
        ]
        
        for pattern in generator_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                generator_name = match.group(1)
                nodes.append(TaskNode(
                    task_id=f"create_generator_{generator_name}",
                    task_type=TaskType.GENERATE_MODULE,
                    file=f"src/generators/{generator_name}.py",
                    content=f"# {generator_name} generator\n# TODO: Implement based on plan",
                    metadata={"generator_name": generator_name, "source": "generators"}
                ))
        
        return nodes
    
    def _parse_acceptance_section(self, content: str) -> List[TaskNode]:
        """Parse acceptance criteria into test creation tasks"""
        nodes = []
        
        # Look for test criteria
        test_patterns = [
            r'(?i)(?:test|assert|verify)\s+([^.\n]+)',
            r'(?i)(?:should|must|need to)\s+([^.\n]+)',
            r'(?i)(?:endpoint|api|function)\s+([^.\n]+)\s+(?:returns|should)',
        ]
        
        for pattern in test_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                test_description = match.group(1).strip()
                nodes.append(TaskNode(
                    task_id=f"create_test_{hash(test_description) % 10000}",
                    task_type=TaskType.CREATE_TEST,
                    file=f"tests/test_acceptance.py",
                    content=f"# Test: {test_description}\n# TODO: Implement test",
                    acceptance_criteria=test_description,
                    metadata={"test_description": test_description, "source": "acceptance"}
                ))
        
        return nodes
    
    def _parse_simple_message(self, content: str) -> List[TaskNode]:
        """Parse simple messages into basic tasks"""
        nodes = []
        content_lower = content.lower()
        
        # Check if this is an AI Website Builder specification
        if self._is_ai_website_builder_spec(content):
            return self._parse_ai_website_builder_spec(content)
        
        # Look for directory creation
        if "create" in content_lower and ("directory" in content_lower or "/" in content):
            # Extract directory name
            import re
            dir_match = re.search(r'/(\w+)', content)
            if dir_match:
                dir_name = dir_match.group(1)
                nodes.append(TaskNode(
                    task_id=f"create_{dir_name}_dir",
                    task_type=TaskType.CREATE_DIRECTORY,
                    directory=f"/{dir_name}",
                    content=f"Create {dir_name} directory with basic structure"
                ))
        
        # Look for file creation
        if "create" in content_lower and ("file" in content_lower or "." in content):
            # Extract file name
            import re
            file_match = re.search(r'(\w+\.\w+)', content)
            if file_match:
                file_name = file_match.group(1)
                nodes.append(TaskNode(
                    task_id=f"create_{file_name.replace('.', '_')}",
                    task_type=TaskType.CREATE_FILE,
                    file=file_name,
                    content=f"Create {file_name} with basic content"
                ))
        
        # Default: create a simple file task
        if not nodes:
            nodes.append(TaskNode(
                task_id="simple_task",
                task_type=TaskType.CREATE_FILE,
                file="simple.txt",
                content=content
            ))
        
        return nodes
    
    def _is_ai_website_builder_spec(self, content: str) -> bool:
        """Check if content is an AI Website Builder specification"""
        content_lower = content.lower()
        indicators = [
            "ai website builder",
            "master drop-in prompt",
            "full-stack, integration-ready",
            "system that builds systems",
            "next.js app",
            "prisma db",
            "stripe checkout",
            "design tokens",
            "motion grammar"
        ]
        return any(indicator in content_lower for indicator in indicators)
    
    def _parse_ai_website_builder_spec(self, content: str) -> List[TaskNode]:
        """Parse AI Website Builder specification into generator steps"""
        nodes = []
        
        # Extract spec data from content
        spec_data = self._extract_spec_from_content(content)
        
        # Generate the complete build pipeline
        nodes.extend([
            # 1. Repository scaffold
            TaskNode(
                task_id="generate_repo_scaffold",
                task_type=TaskType.CREATE_DIRECTORY,
                directory="",
                content="Generate complete repository structure with packages, apps, and configuration",
                metadata={"source": "ai_website_builder", "spec": spec_data}
            ),
            
            # 2. Design tokens and Tailwind
            TaskNode(
                task_id="emit_tokens_tailwind",
                task_type=TaskType.CREATE_FILE,
                file="packages/core/src/tokens.ts",
                content="Generate design tokens and Tailwind configuration from spec",
                metadata={"source": "ai_website_builder", "spec": spec_data}
            ),
            
            # 3. Section components
            TaskNode(
                task_id="emit_sections",
                task_type=TaskType.CREATE_FILE,
                file="apps/site/components/sections/",
                content="Generate section components from spec",
                metadata={"source": "ai_website_builder", "spec": spec_data}
            ),
            
            # 4. Lead capture API
            TaskNode(
                task_id="emit_api_lead",
                task_type=TaskType.CREATE_FILE,
                file="apps/site/app/api/lead/route.ts",
                content="Generate lead capture API with Prisma integration",
                metadata={"source": "ai_website_builder", "spec": spec_data}
            ),
            
            # 5. Payments router
            TaskNode(
                task_id="emit_payments_router",
                task_type=TaskType.CREATE_FILE,
                file="apps/site/lib/payments/router.ts",
                content="Generate payments router with Stripe integration",
                metadata={"source": "ai_website_builder", "spec": spec_data}
            ),
            
            # 6. SEO files
            TaskNode(
                task_id="emit_seo",
                task_type=TaskType.CREATE_FILE,
                file="apps/site/app/robots.ts",
                content="Generate SEO files (robots.txt, sitemap)",
                metadata={"source": "ai_website_builder", "spec": spec_data}
            ),
            
            # 7. Prisma schema
            TaskNode(
                task_id="emit_prisma",
                task_type=TaskType.CREATE_FILE,
                file="prisma/schema.prisma",
                content="Generate database schema with Lead model",
                metadata={"source": "ai_website_builder", "spec": spec_data}
            ),
            
            # 8. Documentation
            TaskNode(
                task_id="emit_docs",
                task_type=TaskType.CREATE_FILE,
                file="README.md",
                content="Generate project documentation and setup instructions",
                metadata={"source": "ai_website_builder", "spec": spec_data}
            )
        ])
        
        return nodes
    
    def _extract_spec_from_content(self, content: str) -> dict:
        """Extract specification data from the content"""
        spec = {
            "title": "AI Website Builder",
            "description": "Generated by Co-Builder",
            "sections": []
        }
        
        # Try to extract sections from the content
        if "sections" in content.lower():
            # Look for section definitions
            section_patterns = [
                r'"kind":\s*"([^"]+)"',
                r'kind:\s*([a-zA-Z_]+)',
                r'(hero|feature_grid|logo_cloud|showreel|pricing|cta_banner)'
            ]
            
            for pattern in section_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match.groups():
                        section_type = match.group(1).lower()
                        if section_type in ['hero', 'feature_grid', 'logo_cloud', 'showreel', 'pricing', 'cta_banner']:
                            spec["sections"].append({
                                "type": section_type,
                                "title": f"{section_type.title()} Section"
                            })
        
        # If no sections found, add default ones
        if not spec["sections"]:
            spec["sections"] = [
                {"type": "hero", "title": "Welcome to Our Platform", "subtitle": "Build amazing things with our tools"},
                {"type": "feature-grid", "title": "Features", "features": [{"title": "Feature 1", "description": "Description 1"}]},
                {"type": "logo-cloud", "title": "Trusted by", "logos": ["Company 1", "Company 2", "Company 3"]},
                {"type": "showreel", "title": "See It In Action", "description": "Watch our demo"},
                {"type": "pricing", "title": "Simple Pricing", "plans": [{"name": "Basic", "price": "$9/month"}]},
                {"type": "cta-banner", "title": "Ready to Get Started?", "button": "Start Free Trial"}
            ]
        
        return spec
    
    def to_json(self, task_graph: TaskGraph) -> str:
        """Convert TaskGraph to JSON format"""
        # Convert nodes to serializable format
        serializable_nodes = []
        for node in task_graph.nodes:
            node_dict = asdict(node)
            # Convert TaskType enum to string
            node_dict['task_type'] = node.task_type.value
            serializable_nodes.append(node_dict)
        
        return json.dumps({
            "nodes": serializable_nodes,
            "metadata": task_graph.metadata
        }, indent=2)
    
    def from_json(self, json_str: str) -> TaskGraph:
        """Create TaskGraph from JSON"""
        data = json.loads(json_str)
        nodes = []
        for node_data in data["nodes"]:
            # Convert string back to TaskType enum
            if 'task_type' in node_data and isinstance(node_data['task_type'], str):
                node_data['task_type'] = TaskType(node_data['task_type'])
            nodes.append(TaskNode(**node_data))
        return TaskGraph(nodes=nodes, metadata=data.get("metadata", {}))
