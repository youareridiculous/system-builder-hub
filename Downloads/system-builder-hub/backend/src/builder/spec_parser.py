"""
LLM-powered Spec Parser for System Builder Hub
Parses natural language requests into structured module specifications
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SpecParser:
    """Parses natural language specifications into structured module specs"""
    
    def __init__(self):
        self.base_path = Path.cwd()
        
    def parse_spec(self, natural_language_spec: str) -> Dict[str, Any]:
        """
        Parse natural language specification into structured format
        
        Args:
            natural_language_spec: Natural language request like "Build me a lightweight LMS..."
            
        Returns:
            Dict containing structured specification
        """
        logger.info("Parsing natural language specification with LLM")
        
        # For now, use a simple heuristic parser
        # In production, this would call OpenAI/Anthropic API
        parsed_spec = self._heuristic_parse(natural_language_spec)
        
        # Validate the parsed specification
        self._validate_spec(parsed_spec)
        
        logger.info(f"Parsed specification: {parsed_spec}")
        return parsed_spec
    
    def _heuristic_parse(self, spec: str) -> Dict[str, Any]:
        """
        Simple heuristic parser for demonstration
        In production, this would be replaced with LLM API calls
        """
        spec_lower = spec.lower()
        
        # Extract module name from common patterns
        name = self._extract_name(spec_lower)
        
        # Extract features from common keywords
        features = self._extract_features(spec_lower)
        
        # Determine category based on keywords
        category = self._extract_category(spec_lower)
        
        # Generate title
        title = self._generate_title(name, category)
        
        # Default plans
        plans = ["starter", "pro", "enterprise"]
        
        # Default version
        version = "1.0.0"
        
        return {
            "name": name,
            "title": title,
            "version": version,
            "category": category,
            "features": features,
            "plans": plans,
            "spec": spec
        }
    
    def _extract_name(self, spec: str) -> str:
        """Extract module name from specification"""
        # Common patterns for module names
        patterns = [
            ("lms", "learning management system"),
            ("crm", "customer relationship management"),
            ("erp", "enterprise resource planning"),
            ("ats", "applicant tracking system"),
            ("helpdesk", "help desk"),
            ("analytics", "analytics dashboard"),
            ("ecommerce", "e-commerce"),
            ("inventory", "inventory management"),
            ("accounting", "accounting system"),
            ("hr", "human resources"),
            ("project", "project management"),
            ("support", "customer support"),
            ("marketing", "marketing automation"),
            ("sales", "sales pipeline"),
            ("finance", "financial management"),
        ]
        
        for short_name, long_name in patterns:
            if short_name in spec or long_name in spec:
                return short_name
        
        # If no pattern matches, extract from common words
        words = spec.split()
        for word in words:
            if len(word) > 3 and word.isalpha():
                return word
        
        # Default fallback
        return "module"
    
    def _extract_features(self, spec: str) -> list:
        """Extract features from specification"""
        features = []
        
        # Common feature keywords
        feature_keywords = {
            "courses": ["course", "lesson", "training", "education"],
            "lessons": ["lesson", "module", "unit", "chapter"],
            "quizzes": ["quiz", "test", "assessment", "exam"],
            "progress": ["progress", "tracking", "analytics", "reporting"],
            "contacts": ["contact", "customer", "client", "lead"],
            "deals": ["deal", "opportunity", "sales", "pipeline"],
            "activities": ["activity", "task", "todo", "action"],
            "projects": ["project", "task", "milestone"],
            "tickets": ["ticket", "issue", "support", "help"],
            "inventory": ["inventory", "stock", "product", "item"],
            "orders": ["order", "purchase", "transaction"],
            "analytics": ["analytics", "dashboard", "report", "metrics"],
            "users": ["user", "member", "account"],
            "payments": ["payment", "billing", "subscription"],
            "notifications": ["notification", "alert", "message"],
        }
        
        for feature, keywords in feature_keywords.items():
            if any(keyword in spec for keyword in keywords):
                features.append(feature)
        
        # If no features found, add some defaults based on module type
        if not features:
            if "lms" in spec or "learning" in spec:
                features = ["courses", "lessons", "quizzes", "progress"]
            elif "crm" in spec or "customer" in spec:
                features = ["contacts", "deals", "activities", "analytics"]
            elif "erp" in spec or "enterprise" in spec:
                features = ["inventory", "orders", "analytics", "users"]
            elif "support" in spec or "help" in spec:
                features = ["tickets", "users", "analytics", "notifications"]
            else:
                features = ["items", "users", "analytics"]
        
        return features
    
    def _extract_category(self, spec: str) -> str:
        """Extract category from specification"""
        category_keywords = {
            "Education": ["lms", "learning", "education", "course", "training"],
            "Business": ["crm", "erp", "business", "enterprise"],
            "HR & Recruiting": ["hr", "recruiting", "ats", "hiring", "candidate"],
            "Customer Support": ["support", "helpdesk", "ticket", "customer service"],
            "Analytics": ["analytics", "dashboard", "reporting", "metrics"],
            "E-commerce": ["ecommerce", "shop", "store", "retail"],
            "Finance": ["finance", "accounting", "billing", "payment"],
            "Project Management": ["project", "task", "milestone"],
            "Marketing": ["marketing", "campaign", "lead"],
            "Sales": ["sales", "pipeline", "deal"],
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in spec for keyword in keywords):
                return category
        
        return "Business"  # Default category
    
    def _generate_title(self, name: str, category: str) -> str:
        """Generate a title for the module"""
        if name == "lms":
            return "Learning Management System"
        elif name == "crm":
            return "Customer Relationship Management"
        elif name == "erp":
            return "Enterprise Resource Planning"
        elif name == "ats":
            return "Applicant Tracking System"
        elif name == "helpdesk":
            return "Helpdesk & Support"
        elif name == "analytics":
            return "Analytics Dashboard"
        else:
            return f"{name.title()} System"
    
    def _validate_spec(self, spec: Dict[str, Any]) -> None:
        """Validate the parsed specification"""
        required_fields = ["name", "title", "version", "category", "features", "plans", "spec"]
        
        for field in required_fields:
            if field not in spec:
                raise ValueError(f"Missing required field: {field}")
        
        if not spec["features"]:
            raise ValueError("At least one feature must be specified")
        
        if not spec["plans"]:
            raise ValueError("At least one plan must be specified")
        
        # Validate name format
        if not spec["name"].isalnum() and "_" not in spec["name"]:
            raise ValueError("Module name must be alphanumeric with optional underscores")
    
    def save_parsed_spec(self, module_name: str, parsed_spec: Dict[str, Any]) -> None:
        """Save the parsed specification to scaffold.spec.md"""
        spec_file = self.base_path / "src" / module_name / "scaffold.spec.md"
        
        if not spec_file.parent.exists():
            spec_file.parent.mkdir(parents=True)
        
        content = f"""# {parsed_spec['title']} Module Specification

## Original Natural Language Specification

```
{parsed_spec['spec']}
```

## Parsed Fields

- **Name**: {parsed_spec['name']}
- **Title**: {parsed_spec['title']}
- **Version**: {parsed_spec['version']}
- **Category**: {parsed_spec['category']}
- **Features**: {', '.join(parsed_spec['features'])}
- **Plans**: {', '.join(parsed_spec['plans'])}

## Generated Artifacts

- Marketplace entry: `marketplace/{parsed_spec['name']}.json`
- Module structure: `src/{parsed_spec['name']}/`
- Database migration: `alembic/versions/`
- Onboarding guide: `marketplace/onboarding/{parsed_spec['name']}.onboarding.json`

## TODO for LLM Expansion

- [ ] Implement actual models based on features
- [ ] Add business logic to API endpoints
- [ ] Create comprehensive seed data
- [ ] Add validation and error handling
- [ ] Implement relationships between models
- [ ] Add tests
- [ ] Customize onboarding steps

## LLM Integration Notes

This module was generated using the heuristic parser. Future versions will use:
- OpenAI GPT-4 for natural language understanding
- Anthropic Claude for specification refinement
- Custom fine-tuned models for domain-specific parsing
"""
        
        with open(spec_file, 'w') as f:
            f.write(content)
        
        logger.info(f"Saved parsed specification to: {spec_file}")

# Mock LLM integration for future implementation
class LLMIntegration:
    """Mock LLM integration for future OpenAI/Anthropic API calls"""
    
    @staticmethod
    def parse_with_llm(natural_language_spec: str) -> Dict[str, Any]:
        """
        Mock LLM parsing - in production this would call OpenAI/Anthropic API
        
        Example prompt:
        Parse this natural language specification into a structured module specification:
        "{natural_language_spec}"
        
        Return a JSON object with the following structure:
        {
            "name": "module_name",
            "title": "Module Title",
            "version": "1.0.0",
            "category": "Category",
            "features": ["feature1", "feature2"],
            "plans": ["starter", "pro", "enterprise"],
            "spec": "original_specification"
        }
        """
        # For now, use the heuristic parser
        parser = SpecParser()
        return parser.parse_spec(natural_language_spec)
