"""
SBH Meta-Builder Planner Service
Hybrid heuristic + LLM planning for scaffold generation.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import re

from src.meta_builder.models import PatternLibrary, TemplateLink, ScaffoldPlan
from src.llm.orchestration import LLMOrchestration
from src.utils.audit import audit_log
from src.utils.multi_tenancy import get_current_tenant_id

logger = logging.getLogger(__name__)


@dataclass
class PlanningContext:
    """Context for scaffold planning."""
    goal_text: str
    guided_input: Optional[Dict[str, Any]] = None
    pattern_slugs: Optional[List[str]] = None
    template_slugs: Optional[List[str]] = None
    composition_rules: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class PlanningResult:
    """Result of scaffold planning."""
    plan_json: Dict[str, Any]
    rationale: str
    risks: List[Dict[str, Any]]
    scorecard: Dict[str, Any]
    diffs_json: Optional[Dict[str, Any]] = None


class ScaffoldPlanner:
    """Hybrid heuristic + LLM planner for scaffold generation."""
    
    def __init__(self, llm_orchestration: LLMOrchestration):
        self.llm = llm_orchestration
        self.pattern_matcher = PatternMatcher()
        self.template_composer = TemplateComposer()
        
    def plan_scaffold(self, context: PlanningContext) -> PlanningResult:
        """Generate a scaffold plan from natural language goal."""
        
        logger.info(f"Planning scaffold for goal: {context.goal_text[:100]}...")
        
        # Step 1: Extract entities and requirements using heuristic analysis
        entities = self._extract_entities(context.goal_text)
        requirements = self._extract_requirements(context.goal_text)
        
        # Step 2: Match patterns based on extracted information
        matched_patterns = self.pattern_matcher.match_patterns(
            entities, requirements, context.pattern_slugs
        )
        
        # Step 3: Select and compose templates
        selected_templates = self.template_composer.select_templates(
            matched_patterns, context.template_slugs
        )
        
        # Step 4: Generate BuilderState using LLM
        builder_state = self._generate_builder_state(
            context, entities, requirements, matched_patterns, selected_templates
        )
        
        # Step 5: Generate rationale and identify risks
        rationale = self._generate_rationale(context, matched_patterns, selected_templates)
        risks = self._identify_risks(builder_state, matched_patterns, selected_templates)
        
        # Step 6: Calculate scorecard
        scorecard = self._calculate_scorecard(builder_state, matched_patterns, selected_templates)
        
        return PlanningResult(
            plan_json=builder_state,
            rationale=rationale,
            risks=risks,
            scorecard=scorecard
        )
    
    def _extract_entities(self, goal_text: str) -> List[Dict[str, Any]]:
        """Extract entities from natural language goal using heuristic rules."""
        
        entities = []
        goal_lower = goal_text.lower()
        
        # Common entity patterns
        entity_patterns = {
            'user': r'\b(users?|customers?|clients?|members?|employees?)\b',
            'product': r'\b(products?|items?|goods?|services?)\b',
            'order': r'\b(orders?|purchases?|transactions?|bookings?)\b',
            'ticket': r'\b(tickets?|issues?|requests?|support)\b',
            'article': r'\b(articles?|posts?|content|blog|news)\b',
            'course': r'\b(courses?|lessons?|training|education)\b',
            'project': r'\b(projects?|tasks?|assignments?)\b',
            'message': r'\b(messages?|chat|conversations?|communications?)\b',
            'file': r'\b(files?|documents?|uploads?|attachments?)\b',
            'payment': r'\b(payments?|billing|invoices?|subscriptions?)\b',
        }
        
        for entity_type, pattern in entity_patterns.items():
            if re.search(pattern, goal_lower):
                entities.append({
                    'type': entity_type,
                    'name': entity_type.title(),
                    'confidence': 0.8
                })
        
        # Look for specific entity mentions
        specific_entities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', goal_text)
        for entity_name in specific_entities:
            if entity_name.lower() not in ['the', 'and', 'or', 'with', 'for', 'from', 'to', 'in', 'on', 'at']:
                entities.append({
                    'type': 'custom',
                    'name': entity_name,
                    'confidence': 0.6
                })
        
        return entities
    
    def _extract_requirements(self, goal_text: str) -> Dict[str, Any]:
        """Extract functional requirements from natural language goal."""
        
        requirements = {
            'authentication': False,
            'authorization': False,
            'file_upload': False,
            'notifications': False,
            'search': False,
            'analytics': False,
            'integrations': [],
            'ai_features': []
        }
        
        goal_lower = goal_text.lower()
        
        # Authentication requirements
        if any(word in goal_lower for word in ['login', 'signup', 'register', 'user account']):
            requirements['authentication'] = True
        
        # Authorization requirements
        if any(word in goal_lower for word in ['roles', 'permissions', 'admin', 'access control']):
            requirements['authorization'] = True
        
        # File upload requirements
        if any(word in goal_lower for word in ['upload', 'file', 'document', 'attachment']):
            requirements['file_upload'] = True
        
        # Notification requirements
        if any(word in goal_lower for word in ['notification', 'alert', 'email', 'slack', 'webhook']):
            requirements['notifications'] = True
        
        # Search requirements
        if any(word in goal_lower for word in ['search', 'find', 'filter', 'query']):
            requirements['search'] = True
        
        # Analytics requirements
        if any(word in goal_lower for word in ['analytics', 'report', 'dashboard', 'metrics']):
            requirements['analytics'] = True
        
        # Integration requirements
        integrations = []
        if 'slack' in goal_lower:
            integrations.append('slack')
        if 'email' in goal_lower:
            integrations.append('email')
        if 'payment' in goal_lower or 'stripe' in goal_lower:
            integrations.append('stripe')
        if 'google' in goal_lower:
            integrations.append('google')
        requirements['integrations'] = integrations
        
        # AI features
        ai_features = []
        if any(word in goal_lower for word in ['ai', 'chatbot', 'assistant', 'recommendation']):
            ai_features.append('chatbot')
        if 'search' in goal_lower and 'ai' in goal_lower:
            ai_features.append('ai_search')
        if 'analytics' in goal_lower and 'ai' in goal_lower:
            ai_features.append('ai_analytics')
        requirements['ai_features'] = ai_features
        
        return requirements
    
    def _generate_builder_state(
        self,
        context: PlanningContext,
        entities: List[Dict[str, Any]],
        requirements: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        templates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate BuilderState using LLM orchestration."""
        
        # Prepare context for LLM
        llm_context = {
            'goal_text': context.goal_text,
            'entities': entities,
            'requirements': requirements,
            'patterns': patterns,
            'templates': templates,
            'guided_input': context.guided_input or {}
        }
        
        # Generate BuilderState using LLM
        prompt = self._build_planner_prompt(llm_context)
        
        try:
            response = self.llm.generate(
                prompt=prompt,
                context=llm_context,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse BuilderState from response
            builder_state = self._parse_builder_state(response.content)
            
            # Apply composition rules
            builder_state = self.template_composer.compose_templates(
                builder_state, templates, context.composition_rules
            )
            
            return builder_state
            
        except Exception as e:
            logger.error(f"LLM planning failed: {e}")
            # Fallback to heuristic BuilderState generation
            return self._generate_heuristic_builder_state(
                entities, requirements, patterns, templates
            )
    
    def _build_planner_prompt(self, context: Dict[str, Any]) -> str:
        """Build the planner prompt for LLM."""
        
        return f"""
You are an expert system architect tasked with generating a BuilderState for a new application.

GOAL: {context['goal_text']}

EXTRACTED ENTITIES:
{json.dumps(context['entities'], indent=2)}

REQUIREMENTS:
{json.dumps(context['requirements'], indent=2)}

SELECTED PATTERNS:
{json.dumps(context['patterns'], indent=2)}

SELECTED TEMPLATES:
{json.dumps(context['templates'], indent=2)}

GUIDED INPUT:
{json.dumps(context['guided_input'], indent=2)}

Generate a complete BuilderState JSON that includes:

1. Database models for all identified entities
2. API endpoints for CRUD operations
3. UI components and pages
4. Authentication and authorization setup
5. File storage configuration
6. Integration configurations
7. AI features if requested
8. Analytics and reporting setup

The BuilderState should follow this structure:
{{
  "models": [...],
  "api_endpoints": [...],
  "ui_components": [...],
  "pages": [...],
  "auth": {{...}},
  "storage": {{...}},
  "integrations": [...],
  "ai_features": [...],
  "analytics": {{...}}
}}

Return only valid JSON without any additional text.
"""
    
    def _parse_builder_state(self, llm_response: str) -> Dict[str, Any]:
        """Parse BuilderState from LLM response."""
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(llm_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse BuilderState: {e}")
            raise ValueError(f"Invalid BuilderState JSON: {e}")
    
    def _generate_heuristic_builder_state(
        self,
        entities: List[Dict[str, Any]],
        requirements: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        templates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate BuilderState using heuristic rules as fallback."""
        
        builder_state = {
            "models": [],
            "api_endpoints": [],
            "ui_components": [],
            "pages": [],
            "auth": {},
            "storage": {},
            "integrations": [],
            "ai_features": [],
            "analytics": {}
        }
        
        # Generate models for entities
        for entity in entities:
            if entity['type'] != 'custom':
                model = self._generate_model_for_entity(entity)
                builder_state["models"].append(model)
        
        # Generate API endpoints
        for entity in entities:
            if entity['type'] != 'custom':
                endpoints = self._generate_endpoints_for_entity(entity)
                builder_state["api_endpoints"].extend(endpoints)
        
        # Generate UI components
        builder_state["ui_components"] = self._generate_ui_components(entities, requirements)
        
        # Generate pages
        builder_state["pages"] = self._generate_pages(entities, requirements)
        
        # Configure auth
        if requirements['authentication']:
            builder_state["auth"] = self._generate_auth_config()
        
        # Configure storage
        if requirements['file_upload']:
            builder_state["storage"] = self._generate_storage_config()
        
        # Configure integrations
        builder_state["integrations"] = requirements['integrations']
        
        # Configure AI features
        builder_state["ai_features"] = requirements['ai_features']
        
        # Configure analytics
        if requirements['analytics']:
            builder_state["analytics"] = self._generate_analytics_config()
        
        return builder_state
    
    def _generate_model_for_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a database model for an entity."""
        
        model_templates = {
            'user': {
                "name": "User",
                "fields": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "email", "type": "string", "unique": True},
                    {"name": "first_name", "type": "string"},
                    {"name": "last_name", "type": "string"},
                    {"name": "created_at", "type": "datetime"},
                    {"name": "updated_at", "type": "datetime"}
                ]
            },
            'product': {
                "name": "Product",
                "fields": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "name", "type": "string"},
                    {"name": "description", "type": "text"},
                    {"name": "price", "type": "decimal"},
                    {"name": "created_at", "type": "datetime"},
                    {"name": "updated_at", "type": "datetime"}
                ]
            },
            'order': {
                "name": "Order",
                "fields": [
                    {"name": "id", "type": "uuid", "primary_key": True},
                    {"name": "user_id", "type": "uuid", "foreign_key": "users.id"},
                    {"name": "status", "type": "string"},
                    {"name": "total_amount", "type": "decimal"},
                    {"name": "created_at", "type": "datetime"},
                    {"name": "updated_at", "type": "datetime"}
                ]
            }
        }
        
        return model_templates.get(entity['type'], {
            "name": entity['name'],
            "fields": [
                {"name": "id", "type": "uuid", "primary_key": True},
                {"name": "name", "type": "string"},
                {"name": "created_at", "type": "datetime"},
                {"name": "updated_at", "type": "datetime"}
            ]
        })
    
    def _generate_endpoints_for_entity(self, entity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate API endpoints for an entity."""
        
        entity_name = entity['name'].lower()
        entity_name_plural = f"{entity_name}s"
        
        return [
            {
                "path": f"/api/{entity_name_plural}",
                "method": "GET",
                "description": f"List all {entity_name_plural}"
            },
            {
                "path": f"/api/{entity_name_plural}",
                "method": "POST",
                "description": f"Create a new {entity_name}"
            },
            {
                "path": f"/api/{entity_name_plural}/{{id}}",
                "method": "GET",
                "description": f"Get a specific {entity_name}"
            },
            {
                "path": f"/api/{entity_name_plural}/{{id}}",
                "method": "PUT",
                "description": f"Update a {entity_name}"
            },
            {
                "path": f"/api/{entity_name_plural}/{{id}}",
                "method": "DELETE",
                "description": f"Delete a {entity_name}"
            }
        ]
    
    def _generate_ui_components(self, entities: List[Dict[str, Any]], requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate UI components based on entities and requirements."""
        
        components = []
        
        for entity in entities:
            if entity['type'] != 'custom':
                entity_name = entity['name']
                components.extend([
                    {
                        "name": f"{entity_name}List",
                        "type": "table",
                        "description": f"List of {entity_name}s"
                    },
                    {
                        "name": f"{entity_name}Form",
                        "type": "form",
                        "description": f"Form for creating/editing {entity_name}s"
                    },
                    {
                        "name": f"{entity_name}Detail",
                        "type": "detail",
                        "description": f"Detail view for {entity_name}"
                    }
                ])
        
        if requirements['search']:
            components.append({
                "name": "SearchBar",
                "type": "input",
                "description": "Search functionality"
            })
        
        if requirements['file_upload']:
            components.append({
                "name": "FileUpload",
                "type": "upload",
                "description": "File upload component"
            })
        
        return components
    
    def _generate_pages(self, entities: List[Dict[str, Any]], requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate pages based on entities and requirements."""
        
        pages = [
            {
                "name": "Dashboard",
                "path": "/",
                "description": "Main dashboard"
            }
        ]
        
        for entity in entities:
            if entity['type'] != 'custom':
                entity_name = entity['name']
                entity_name_plural = f"{entity_name}s"
                pages.extend([
                    {
                        "name": f"{entity_name_plural}",
                        "path": f"/{entity_name_plural.lower()}",
                        "description": f"List of {entity_name_plural}"
                    },
                    {
                        "name": f"New{entity_name}",
                        "path": f"/{entity_name_plural.lower()}/new",
                        "description": f"Create new {entity_name}"
                    },
                    {
                        "name": f"Edit{entity_name}",
                        "path": f"/{entity_name_plural.lower()}/{{id}}/edit",
                        "description": f"Edit {entity_name}"
                    }
                ])
        
        if requirements['analytics']:
            pages.append({
                "name": "Analytics",
                "path": "/analytics",
                "description": "Analytics dashboard"
            })
        
        return pages
    
    def _generate_auth_config(self) -> Dict[str, Any]:
        """Generate authentication configuration."""
        
        return {
            "provider": "jwt",
            "routes": {
                "login": "/auth/login",
                "register": "/auth/register",
                "logout": "/auth/logout"
            },
            "components": [
                "LoginForm",
                "RegisterForm",
                "UserProfile"
            ]
        }
    
    def _generate_storage_config(self) -> Dict[str, Any]:
        """Generate file storage configuration."""
        
        return {
            "provider": "s3",
            "bucket": "uploads",
            "components": [
                "FileUpload",
                "FileViewer"
            ]
        }
    
    def _generate_analytics_config(self) -> Dict[str, Any]:
        """Generate analytics configuration."""
        
        return {
            "provider": "internal",
            "components": [
                "AnalyticsDashboard",
                "ChartComponent"
            ]
        }
    
    def _generate_rationale(
        self,
        context: PlanningContext,
        patterns: List[Dict[str, Any]],
        templates: List[Dict[str, Any]]
    ) -> str:
        """Generate rationale for the planning decisions."""
        
        rationale_parts = []
        
        if patterns:
            pattern_names = [p['name'] for p in patterns]
            rationale_parts.append(f"Selected patterns: {', '.join(pattern_names)}")
        
        if templates:
            template_names = [t['name'] for t in templates]
            rationale_parts.append(f"Selected templates: {', '.join(template_names)}")
        
        if context.guided_input:
            rationale_parts.append("Used guided input to refine the plan")
        
        if not rationale_parts:
            rationale_parts.append("Generated plan based on natural language analysis")
        
        return ". ".join(rationale_parts) + "."
    
    def _identify_risks(
        self,
        builder_state: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        templates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify potential risks in the generated plan."""
        
        risks = []
        
        # Check for potential naming conflicts
        model_names = [model['name'] for model in builder_state.get('models', [])]
        if len(model_names) != len(set(model_names)):
            risks.append({
                "type": "naming_conflict",
                "severity": "medium",
                "description": "Potential naming conflicts detected in models",
                "mitigation": "Review and rename conflicting models"
            })
        
        # Check for missing authentication
        if builder_state.get('models') and not builder_state.get('auth'):
            risks.append({
                "type": "security",
                "severity": "high",
                "description": "No authentication configured",
                "mitigation": "Add authentication configuration"
            })
        
        # Check for complex integrations
        integrations = builder_state.get('integrations', [])
        if len(integrations) > 3:
            risks.append({
                "type": "complexity",
                "severity": "medium",
                "description": "Multiple integrations may increase complexity",
                "mitigation": "Consider implementing integrations incrementally"
            })
        
        return risks
    
    def _calculate_scorecard(
        self,
        builder_state: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        templates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate quality scorecard for the generated plan."""
        
        score = 0
        max_score = 100
        details = {}
        
        # Completeness score (40 points)
        completeness_score = 0
        if builder_state.get('models'):
            completeness_score += 10
        if builder_state.get('api_endpoints'):
            completeness_score += 10
        if builder_state.get('ui_components'):
            completeness_score += 10
        if builder_state.get('pages'):
            completeness_score += 10
        
        score += completeness_score
        details['completeness'] = completeness_score
        
        # Pattern alignment score (30 points)
        pattern_score = min(len(patterns) * 10, 30)
        score += pattern_score
        details['pattern_alignment'] = pattern_score
        
        # Template usage score (20 points)
        template_score = min(len(templates) * 10, 20)
        score += template_score
        details['template_usage'] = template_score
        
        # Security score (10 points)
        security_score = 0
        if builder_state.get('auth'):
            security_score += 10
        
        score += security_score
        details['security'] = security_score
        
        return {
            "overall_score": score,
            "max_score": max_score,
            "percentage": (score / max_score) * 100,
            "grade": self._calculate_grade(score)
        }
    
    def _calculate_grade(self, score: int) -> str:
        """Calculate letter grade based on score."""
        
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


class PatternMatcher:
    """Pattern matching service for scaffold planning."""
    
    def match_patterns(
        self,
        entities: List[Dict[str, Any]],
        requirements: Dict[str, Any],
        requested_patterns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Match patterns based on entities and requirements."""
        
        # TODO: Implement pattern matching logic
        # For now, return basic patterns based on requirements
        
        patterns = []
        
        if requirements['authentication']:
            patterns.append({
                'slug': 'auth',
                'name': 'Authentication',
                'description': 'User authentication and authorization',
                'confidence': 0.9
            })
        
        if requirements['file_upload']:
            patterns.append({
                'slug': 'file_management',
                'name': 'File Management',
                'description': 'File upload and storage',
                'confidence': 0.8
            })
        
        if requirements['notifications']:
            patterns.append({
                'slug': 'notifications',
                'name': 'Notifications',
                'description': 'Email and push notifications',
                'confidence': 0.7
            })
        
        if requirements['search']:
            patterns.append({
                'slug': 'search',
                'name': 'Search',
                'description': 'Full-text search functionality',
                'confidence': 0.8
            })
        
        if requirements['analytics']:
            patterns.append({
                'slug': 'analytics',
                'name': 'Analytics',
                'description': 'Data analytics and reporting',
                'confidence': 0.7
            })
        
        return patterns


class TemplateComposer:
    """Template composition service for scaffold planning."""
    
    def select_templates(
        self,
        patterns: List[Dict[str, Any]],
        requested_templates: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Select templates based on patterns."""
        
        # TODO: Implement template selection logic
        # For now, return basic templates based on patterns
        
        templates = []
        
        for pattern in patterns:
            if pattern['slug'] == 'auth':
                templates.append({
                    'slug': 'auth-basic',
                    'name': 'Basic Authentication',
                    'description': 'JWT-based authentication',
                    'compose_points': ['auth', 'api', 'ui']
                })
            
            if pattern['slug'] == 'file_management':
                templates.append({
                    'slug': 'file-s3',
                    'name': 'S3 File Storage',
                    'description': 'AWS S3 file storage',
                    'compose_points': ['storage', 'api']
                })
        
        return templates
    
    def compose_templates(
        self,
        builder_state: Dict[str, Any],
        templates: List[Dict[str, Any]],
        composition_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compose templates into the BuilderState."""
        
        # TODO: Implement template composition logic
        # For now, return the original BuilderState
        
        return builder_state
