"""
Tool execution policy and safety controls
"""
import os
import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from src.agent_tools.types import ToolCall, ToolContext
from src.llm.safety import SafetyFilter

logger = logging.getLogger(__name__)

class ToolPolicy:
    """Tool execution policy and safety controls"""
    
    def __init__(self):
        self.safety_filter = SafetyFilter()
        
        # Load configuration
        self.http_allow_domains = self._parse_domains(
            os.environ.get('TOOLS_HTTP_ALLOW_DOMAINS', '')
        )
        self.rate_limit_per_min = int(
            os.environ.get('TOOLS_RATE_LIMIT_PER_MIN', '60')
        )
        
        # Default allowlist for common APIs
        self.default_allow_domains = [
            'jsonplaceholder.typicode.com',
            'api.stripe.com',
            'api.github.com',
            'api.openai.com',
            'api.anthropic.com'
        ]
        
        # Merge with environment domains
        self.allowed_domains = list(set(
            self.default_allow_domains + self.http_allow_domains
        ))
    
    def _parse_domains(self, domains_str: str) -> List[str]:
        """Parse comma-separated domain list"""
        if not domains_str:
            return []
        
        return [
            domain.strip().lower()
            for domain in domains_str.split(',')
            if domain.strip()
        ]
    
    def validate_tool_call(self, call: ToolCall, context: ToolContext) -> Dict[str, Any]:
        """Validate tool call against policy"""
        errors = []
        
        # Check if tool is registered
        from src.agent_tools.registry import tool_registry
        if not tool_registry.is_registered(call.tool):
            errors.append({
                'code': 'tool_not_found',
                'message': f'Tool {call.tool} is not registered'
            })
            return {'valid': False, 'errors': errors}
        
        # Get tool spec
        spec = tool_registry.get(call.tool)
        if not spec:
            errors.append({
                'code': 'tool_spec_not_found',
                'message': f'Tool specification for {call.tool} not found'
            })
            return {'valid': False, 'errors': errors}
        
        # Validate schema
        schema_errors = self._validate_schema(call.args, spec.input_schema)
        if schema_errors:
            errors.extend(schema_errors)
        
        # Tool-specific validation
        tool_errors = self._validate_tool_specific(call, context)
        if tool_errors:
            errors.extend(tool_errors)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_schema(self, args: Dict[str, Any], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate arguments against JSON schema"""
        errors = []
        
        try:
            from jsonschema import validate, ValidationError
            validate(instance=args, schema=schema)
        except ImportError:
            logger.warning("jsonschema not available, skipping schema validation")
            return errors
        except ValidationError as e:
            errors.append({
                'code': 'schema_validation_error',
                'message': str(e),
                'path': '.'.join(str(p) for p in e.path)
            })
        
        return errors
    
    def _validate_tool_specific(self, call: ToolCall, context: ToolContext) -> List[Dict[str, Any]]:
        """Validate tool-specific policies"""
        errors = []
        
        if call.tool == 'http.openapi':
            errors.extend(self._validate_http_openapi(call.args))
        elif call.tool == 'db.migrate':
            errors.extend(self._validate_db_migrate(call.args, context))
        elif call.tool == 'files.store':
            errors.extend(self._validate_files_store(call.args, context))
        elif call.tool == 'email.send':
            errors.extend(self._validate_email_send(call.args))
        
        return errors
    
    def _validate_http_openapi(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate HTTP OpenAPI tool call"""
        errors = []
        
        base = args.get('base', '')
        if not base:
            errors.append({
                'code': 'missing_base_url',
                'message': 'base URL is required for http.openapi'
            })
            return errors
        
        # Parse and validate domain
        try:
            parsed = urlparse(base)
            domain = parsed.netloc.lower()
            
            if not domain:
                errors.append({
                    'code': 'invalid_url',
                    'message': f'Invalid URL: {base}'
                })
                return errors
            
            if domain not in self.allowed_domains:
                errors.append({
                    'code': 'domain_not_allowed',
                    'message': f'Domain {domain} is not in allowlist. Allowed: {", ".join(self.allowed_domains)}'
                })
        
        except Exception as e:
            errors.append({
                'code': 'url_parse_error',
                'message': f'Error parsing URL {base}: {str(e)}'
            })
        
        return errors
    
    def _validate_db_migrate(self, args: Dict[str, Any], context: ToolContext) -> List[Dict[str, Any]]:
        """Validate database migration tool call"""
        errors = []
        
        # Check if database operations are enabled
        if not os.environ.get('FEATURE_AGENT_TOOLS', 'false').lower() == 'true':
            errors.append({
                'code': 'feature_disabled',
                'message': 'Database migration tools are disabled'
            })
        
        # Validate table name
        table = args.get('table', '')
        if not table:
            errors.append({
                'code': 'missing_table',
                'message': 'table is required for db.migrate'
            })
        elif not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            errors.append({
                'code': 'invalid_table_name',
                'message': f'Invalid table name: {table}'
            })
        
        return errors
    
    def _validate_files_store(self, args: Dict[str, Any], context: ToolContext) -> List[Dict[str, Any]]:
        """Validate file store tool call"""
        errors = []
        
        # Check if file operations are enabled
        if not os.environ.get('FEATURE_AGENT_TOOLS', 'false').lower() == 'true':
            errors.append({
                'code': 'feature_disabled',
                'message': 'File store tools are disabled'
            })
        
        # Validate store name
        store = args.get('store', '')
        if not store:
            errors.append({
                'code': 'missing_store',
                'message': 'store is required for files.store'
            })
        
        return errors
    
    def _validate_email_send(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate email send tool call"""
        errors = []
        
        # Check if email operations are enabled
        if not os.environ.get('FEATURE_AGENT_TOOLS', 'false').lower() == 'true':
            errors.append({
                'code': 'feature_disabled',
                'message': 'Email tools are disabled'
            })
        
        # Validate email address
        to_email = args.get('to', '')
        if not to_email:
            errors.append({
                'code': 'missing_recipient',
                'message': 'to is required for email.send'
            })
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', to_email):
            errors.append({
                'code': 'invalid_email',
                'message': f'Invalid email address: {to_email}'
            })
        
        return errors
    
    def redact_output(self, tool_name: str, output: Any) -> Any:
        """Redact sensitive information from tool output"""
        if not output:
            return output
        
        # Convert to string for redaction
        output_str = str(output)
        
        # Apply safety filter redaction
        redacted = self.safety_filter.redact(output_str)
        
        # Tool-specific redaction
        if tool_name == 'http.openapi':
            redacted = self._redact_http_output(redacted)
        elif tool_name == 'email.send':
            redacted = self._redact_email_output(redacted)
        
        return redacted
    
    def _redact_http_output(self, output: str) -> str:
        """Redact HTTP response output"""
        # Redact authorization headers
        output = re.sub(r'Authorization:\s*Bearer\s+\S+', 'Authorization: Bearer [REDACTED]', output)
        output = re.sub(r'Authorization:\s*Basic\s+\S+', 'Authorization: Basic [REDACTED]', output)
        
        # Redact cookies
        output = re.sub(r'Set-Cookie:\s*[^;]+', 'Set-Cookie: [REDACTED]', output)
        
        return output
    
    def _redact_email_output(self, output: str) -> str:
        """Redact email output"""
        # Redact email addresses (keep domain)
        output = re.sub(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', '[REDACTED]@\\2', output)
        
        # Redact phone numbers
        output = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[REDACTED]', output)
        
        return output
    
    def get_rate_limit_key(self, tool_name: str, context: ToolContext) -> str:
        """Get rate limit key for tool"""
        return f"tool_rate_limit:{tool_name}:{context.tenant_id}"
    
    def get_allowed_domains(self) -> List[str]:
        """Get list of allowed domains"""
        return self.allowed_domains.copy()
    
    def add_allowed_domain(self, domain: str) -> None:
        """Add domain to allowlist"""
        domain = domain.strip().lower()
        if domain not in self.allowed_domains:
            self.allowed_domains.append(domain)
            logger.info(f"Added domain to allowlist: {domain}")
    
    def remove_allowed_domain(self, domain: str) -> bool:
        """Remove domain from allowlist"""
        domain = domain.strip().lower()
        if domain not in self.allowed_domains:
            self.allowed_domains.remove(domain)
            logger.info(f"Removed domain from allowlist: {domain}")
            return True
        return False

# Global singleton policy
tool_policy = ToolPolicy()
