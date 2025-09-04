"""
Guided prompt engine
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
from src.market.models import TemplateGuidedSchema, TemplateBuilderState

logger = logging.getLogger(__name__)

class GuidedPromptEngine:
    """Guided prompt engine for template customization"""
    
    def __init__(self):
        self.default_prompt_structure = {
            'role': 'User',
            'context': 'General application',
            'task': 'Manage data',
            'audience': 'End users',
            'output': 'Web application'
        }
    
    def validate_guided_input(self, schema: Dict[str, Any], guided_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate guided input against schema and return normalized input"""
        try:
            validated_input = {}
            
            # Handle prompt structure fields
            for field in ['role', 'context', 'task', 'audience', 'output']:
                value = guided_input.get(field, self.default_prompt_structure.get(field, ''))
                validated_input[field] = self._sanitize_string(value, max_length=200)
            
            # Handle custom schema fields
            if 'fields' in schema:
                for field_def in schema['fields']:
                    field_name = field_def['name']
                    field_type = field_def.get('type', 'string')
                    required = field_def.get('required', False)
                    default = field_def.get('default', '')
                    max_length = field_def.get('max_length', 100)
                    
                    value = guided_input.get(field_name, default)
                    
                    if required and not value:
                        raise ValueError(f"Required field '{field_name}' is missing")
                    
                    # Validate and sanitize based on type
                    if field_type == 'string':
                        validated_input[field_name] = self._sanitize_string(value, max_length)
                    elif field_type == 'number':
                        validated_input[field_name] = self._sanitize_number(value)
                    elif field_type == 'boolean':
                        validated_input[field_name] = bool(value)
                    elif field_type == 'select':
                        options = field_def.get('options', [])
                        if value not in options:
                            value = default if default in options else options[0] if options else ''
                        validated_input[field_name] = value
                    else:
                        validated_input[field_name] = self._sanitize_string(value, max_length)
            
            return validated_input
            
        except Exception as e:
            logger.error(f"Error validating guided input: {e}")
            raise ValueError(f"Invalid guided input: {str(e)}")
    
    def generate_builder_state(self, template_builder_state: TemplateBuilderState, 
                              guided_input: Dict[str, Any]) -> Dict[str, Any]:
        """Generate builder state from template and guided input"""
        try:
            # Get the template builder state JSON
            builder_state = template_builder_state.builder_state.copy()
            
            # Substitute placeholders with guided input values
            builder_state_str = json.dumps(builder_state)
            
            # Replace placeholders
            for key, value in guided_input.items():
                placeholder = f"{{{{{key}}}}}"
                if isinstance(value, str):
                    # Convert to slug-safe format for certain fields
                    if key in ['table_name', 'project_name', 'api_name']:
                        slug_value = self._to_slug(value)
                        builder_state_str = builder_state_str.replace(placeholder, slug_value)
                    else:
                        builder_state_str = builder_state_str.replace(placeholder, value)
                else:
                    builder_state_str = builder_state_str.replace(placeholder, str(value))
            
            # Replace common placeholders
            builder_state_str = self._replace_common_placeholders(builder_state_str, guided_input)
            
            # Parse back to JSON
            result = json.loads(builder_state_str)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating builder state: {e}")
            raise ValueError(f"Error generating builder state: {str(e)}")
    
    def _sanitize_string(self, value: Any, max_length: int = 100) -> str:
        """Sanitize string value"""
        if not value:
            return ''
        
        # Convert to string
        value = str(value).strip()
        
        # Remove control characters
        value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    def _sanitize_number(self, value: Any) -> int:
        """Sanitize number value"""
        try:
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0
    
    def _to_slug(self, value: str) -> str:
        """Convert string to slug-safe format"""
        if not value:
            return 'default'
        
        # Convert to lowercase and replace spaces with underscores
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', value.lower())
        slug = re.sub(r'\s+', '_', slug)
        
        # Ensure it starts with a letter
        if slug and not slug[0].isalpha():
            slug = 'item_' + slug
        
        # Limit length
        if len(slug) > 50:
            slug = slug[:50]
        
        return slug or 'default'
    
    def _replace_common_placeholders(self, text: str, guided_input: Dict[str, Any]) -> str:
        """Replace common placeholders in text"""
        replacements = {
            '{{project_slug}}': self._to_slug(guided_input.get('table_name', 'project')),
            '{{table_name}}': self._to_slug(guided_input.get('table_name', 'items')),
            '{{api_name}}': self._to_slug(guided_input.get('table_name', 'api')),
            '{{ui_name}}': self._to_slug(guided_input.get('table_name', 'ui')),
            '{{role}}': guided_input.get('role', 'User'),
            '{{context}}': guided_input.get('context', 'Application'),
            '{{task}}': guided_input.get('task', 'Manage data'),
            '{{audience}}': guided_input.get('audience', 'Users'),
            '{{output}}': guided_input.get('output', 'Web app')
        }
        
        for placeholder, replacement in replacements.items():
            text = text.replace(placeholder, str(replacement))
        
        return text
    
    def get_schema_errors(self, schema: Dict[str, Any], guided_input: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get validation errors for guided input"""
        errors = []
        
        try:
            # Validate prompt structure fields
            for field in ['role', 'context', 'task', 'audience', 'output']:
                value = guided_input.get(field, '')
                if not value:
                    errors.append({
                        'field': field,
                        'message': f'{field.title()} is required'
                    })
                elif len(value) > 200:
                    errors.append({
                        'field': field,
                        'message': f'{field.title()} must be less than 200 characters'
                    })
            
            # Validate custom schema fields
            if 'fields' in schema:
                for field_def in schema['fields']:
                    field_name = field_def['name']
                    field_type = field_def.get('type', 'string')
                    required = field_def.get('required', False)
                    max_length = field_def.get('max_length', 100)
                    
                    value = guided_input.get(field_name, '')
                    
                    if required and not value:
                        errors.append({
                            'field': field_name,
                            'message': f'{field_name} is required'
                        })
                    elif value and len(str(value)) > max_length:
                        errors.append({
                            'field': field_name,
                            'message': f'{field_name} must be less than {max_length} characters'
                        })
                    elif field_type == 'number' and value:
                        try:
                            int(value)
                        except ValueError:
                            errors.append({
                                'field': field_name,
                                'message': f'{field_name} must be a number'
                            })
                    elif field_type == 'select' and value:
                        options = field_def.get('options', [])
                        if options and value not in options:
                            errors.append({
                                'field': field_name,
                                'message': f'{field_name} must be one of: {", ".join(options)}'
                            })
            
            return errors
            
        except Exception as e:
            logger.error(f"Error validating schema: {e}")
            errors.append({
                'field': 'general',
                'message': 'Validation error occurred'
            })
            return errors
