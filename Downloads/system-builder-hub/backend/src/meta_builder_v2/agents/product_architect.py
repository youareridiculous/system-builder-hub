"""
Product Architect Agent
Converts natural language specifications into formal scaffold plans.
"""

import json
import logging
from typing import Dict, Any, List
from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class ProductArchitectAgent(BaseAgent):
    """Product Architect Agent - converts goals into formal specifications."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.pattern_library = self._load_pattern_library()
    
    def _load_pattern_library(self) -> Dict[str, Any]:
        """Load pattern library for common system types."""
        return {
            "crm": {
                "entities": ["Contact", "Deal", "Company", "Task", "Note"],
                "workflows": ["lead_pipeline", "deal_pipeline", "task_management"],
                "integrations": ["email", "calendar", "crm_platforms"],
                "ai_features": ["lead_scoring", "deal_prediction", "email_automation"]
            },
            "lms": {
                "entities": ["Course", "Lesson", "Student", "Instructor", "Enrollment"],
                "workflows": ["course_creation", "student_enrollment", "progress_tracking"],
                "integrations": ["video_platforms", "payment_gateways", "analytics"],
                "ai_features": ["content_recommendation", "adaptive_learning", "automated_grading"]
            },
            "helpdesk": {
                "entities": ["Ticket", "Customer", "Agent", "Category", "Knowledge_Base"],
                "workflows": ["ticket_routing", "escalation", "resolution"],
                "integrations": ["email", "chat", "crm", "analytics"],
                "ai_features": ["ticket_classification", "auto_response", "sentiment_analysis"]
            },
            "ecommerce": {
                "entities": ["Product", "Order", "Customer", "Inventory", "Payment"],
                "workflows": ["order_processing", "inventory_management", "customer_service"],
                "integrations": ["payment_gateways", "shipping", "analytics"],
                "ai_features": ["product_recommendation", "pricing_optimization", "fraud_detection"]
            }
        }
    
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Product Architect actions."""
        if action == "create_spec":
            return await self._create_specification(inputs)
        elif action == "analyze_requirements":
            return await self._analyze_requirements(inputs)
        elif action == "identify_patterns":
            return await self._identify_patterns(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _create_specification(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Create a formal specification from natural language input."""
        goal_text = inputs.get("goal_text", "")
        guided_input = inputs.get("guided_input", {})
        
        # Analyze the goal to identify patterns and requirements
        analysis = await self._analyze_requirements({"goal_text": goal_text})
        
        # Generate the specification
        spec = {
            "name": self._extract_system_name(goal_text, guided_input),
            "domain": analysis["domain"],
            "entities": analysis["entities"],
            "workflows": analysis["workflows"],
            "integrations": analysis["integrations"],
            "ai": analysis["ai_features"],
            "non_functional": analysis["non_functional"],
            "acceptance": analysis["acceptance_criteria"]
        }
        
        return {
            "spec": spec,
            "analysis": analysis,
            "confidence": analysis["confidence"]
        }
    
    async def _analyze_requirements(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze requirements and identify system components."""
        goal_text = inputs.get("goal_text", "")
        
        # Use LLM to analyze requirements
        prompt = self._build_analysis_prompt(goal_text)
        
        try:
            response = await self.context.llm.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            analysis = json.loads(response['content'])
            
            # Validate and enhance analysis
            analysis = self._validate_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Requirements analysis failed: {e}")
            # Fallback to pattern-based analysis
            return self._fallback_analysis(goal_text)
    
    def _build_analysis_prompt(self, goal_text: str) -> str:
        """Build prompt for requirements analysis."""
        return f"""
You are a Product Architect analyzing a system requirement. Analyze the following goal and return a JSON response with the following structure:

Goal: {goal_text}

Return a JSON object with:
{{
    "domain": "crm|lms|helpdesk|ecommerce|custom",
    "entities": [
        {{
            "name": "EntityName",
            "fields": [
                {{"name": "field_name", "type": "string|integer|boolean|datetime|uuid", "required": true, "unique": false}}
            ]
        }}
    ],
    "workflows": [
        {{
            "name": "workflow_name",
            "states": ["state1", "state2", "state3"],
            "transitions": [
                {{"from": "state1", "to": "state2", "trigger": "event_name"}}
            ]
        }}
    ],
    "integrations": ["stripe", "email", "analytics", "storage"],
    "ai_features": {{
        "copilots": ["sales", "support", "ops"],
        "rag": true,
        "automation": ["email", "notifications", "reports"]
    }},
    "non_functional": {{
        "multi_tenant": true,
        "rbac": true,
        "observability": true,
        "security": ["encryption", "audit_logging", "rate_limiting"]
    }},
    "acceptance_criteria": [
        {{
            "id": "AC1",
            "text": "User can create and manage entities",
            "category": "functional"
        }}
    ],
    "confidence": 0.85
}}

Focus on identifying the core entities, workflows, and integrations needed to fulfill the goal.
"""
    
    def _validate_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance analysis results."""
        # Ensure required fields exist
        required_fields = ["domain", "entities", "workflows", "integrations", "ai_features", "non_functional", "acceptance_criteria"]
        for field in required_fields:
            if field not in analysis:
                analysis[field] = self._get_default_value(field)
        
        # Validate domain
        valid_domains = ["crm", "lms", "helpdesk", "ecommerce", "custom"]
        if analysis["domain"] not in valid_domains:
            analysis["domain"] = "custom"
        
        # Ensure entities have required structure
        for entity in analysis["entities"]:
            if "name" not in entity:
                entity["name"] = "Unknown"
            if "fields" not in entity:
                entity["fields"] = []
        
        # Set confidence if not present
        if "confidence" not in analysis:
            analysis["confidence"] = 0.8
        
        return analysis
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for missing fields."""
        defaults = {
            "domain": "custom",
            "entities": [],
            "workflows": [],
            "integrations": [],
            "ai_features": {"copilots": [], "rag": False, "automation": []},
            "non_functional": {"multi_tenant": True, "rbac": True, "observability": True},
            "acceptance_criteria": []
        }
        return defaults.get(field, None)
    
    def _fallback_analysis(self, goal_text: str) -> Dict[str, Any]:
        """Fallback analysis using pattern matching."""
        goal_lower = goal_text.lower()
        
        # Simple pattern matching
        if any(word in goal_lower for word in ["crm", "customer", "contact", "deal", "lead"]):
            domain = "crm"
        elif any(word in goal_lower for word in ["lms", "learning", "course", "student", "education"]):
            domain = "lms"
        elif any(word in goal_lower for word in ["helpdesk", "support", "ticket", "issue"]):
            domain = "helpdesk"
        elif any(word in goal_lower for word in ["ecommerce", "shop", "product", "order", "payment"]):
            domain = "ecommerce"
        else:
            domain = "custom"
        
        # Use pattern library
        pattern = self.pattern_library.get(domain, {})
        
        return {
            "domain": domain,
            "entities": pattern.get("entities", []),
            "workflows": pattern.get("workflows", []),
            "integrations": pattern.get("integrations", []),
            "ai_features": pattern.get("ai_features", []),
            "non_functional": {"multi_tenant": True, "rbac": True, "observability": True},
            "acceptance_criteria": [],
            "confidence": 0.6
        }
    
    async def _identify_patterns(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Identify patterns in the specification."""
        spec = inputs.get("spec", {})
        domain = spec.get("domain", "custom")
        
        patterns = self.pattern_library.get(domain, {})
        
        return {
            "patterns": patterns,
            "domain": domain,
            "suggestions": self._generate_pattern_suggestions(spec, patterns)
        }
    
    def _generate_pattern_suggestions(self, spec: Dict[str, Any], patterns: Dict[str, Any]) -> List[str]:
        """Generate suggestions based on patterns."""
        suggestions = []
        
        # Check for missing entities
        spec_entities = {e["name"] for e in spec.get("entities", [])}
        pattern_entities = set(patterns.get("entities", []))
        missing_entities = pattern_entities - spec_entities
        
        if missing_entities:
            suggestions.append(f"Consider adding entities: {', '.join(missing_entities)}")
        
        # Check for missing workflows
        spec_workflows = {w["name"] for w in spec.get("workflows", [])}
        pattern_workflows = set(patterns.get("workflows", []))
        missing_workflows = pattern_workflows - spec_workflows
        
        if missing_workflows:
            suggestions.append(f"Consider adding workflows: {', '.join(missing_workflows)}")
        
        return suggestions
    
    def _extract_system_name(self, goal_text: str, guided_input: Dict[str, Any]) -> str:
        """Extract system name from goal or guided input."""
        if guided_input.get("title"):
            return guided_input["title"]
        
        # Simple extraction from goal text
        words = goal_text.split()
        if len(words) >= 3:
            return " ".join(words[:3]).title()
        
        return "System"
