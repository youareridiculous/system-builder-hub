"""
Tool execution kernel
"""
import time
import logging
from typing import List, Dict, Any, Optional
from src.agent_tools.types import ToolCall, ToolResult, ToolContext, ToolTranscript
from src.agent_tools.registry import tool_registry
from src.agent_tools.policy import tool_policy
from src.analytics.service import AnalyticsService
from src.llm.rate_limits import LLMRateLimiter

logger = logging.getLogger(__name__)

class ToolKernel:
    """Tool execution kernel"""
    
    def __init__(self):
        self.analytics = AnalyticsService()
        self.rate_limiter = LLMRateLimiter()
    
    def execute(self, call: ToolCall, context: ToolContext) -> ToolResult:
        """Execute a single tool call"""
        start_time = time.time()
        
        try:
            # Track tool usage
            self.analytics.track(
                tenant_id=context.tenant_id,
                event='agent.tools.used',
                user_id=context.user_id,
                source='agent_tools',
                props={
                    'tool': call.tool,
                    'call_id': call.id
                }
            )
            
            # Validate tool call
            validation = tool_policy.validate_tool_call(call, context)
            if not validation['valid']:
                return ToolResult(
                    id=call.id,
                    ok=False,
                    error={
                        'code': 'validation_failed',
                        'message': 'Tool call validation failed',
                        'details': validation['errors']
                    }
                )
            
            # Check rate limits
            rate_limit_key = tool_policy.get_rate_limit_key(call.tool, context)
            if not self.rate_limiter.check_rate_limit(rate_limit_key, 1):
                return ToolResult(
                    id=call.id,
                    ok=False,
                    error={
                        'code': 'rate_limit_exceeded',
                        'message': f'Rate limit exceeded for tool {call.tool}'
                    }
                )
            
            # Get tool handler
            handler = tool_registry.get_handler(call.tool)
            if not handler:
                return ToolResult(
                    id=call.id,
                    ok=False,
                    error={
                        'code': 'handler_not_found',
                        'message': f'Handler not found for tool {call.tool}'
                    }
                )
            
            # Execute tool
            try:
                raw_output = handler(call.args, context)
                execution_time = time.time() - start_time
                
                # Redact output
                redacted_output = tool_policy.redact_output(call.tool, raw_output)
                
                # Track successful execution
                self.analytics.track(
                    tenant_id=context.tenant_id,
                    event='agent.tools.success',
                    user_id=context.user_id,
                    source='agent_tools',
                    props={
                        'tool': call.tool,
                        'call_id': call.id,
                        'execution_time': execution_time
                    }
                )
                
                return ToolResult(
                    id=call.id,
                    ok=True,
                    redacted_output=redacted_output,
                    raw_output=raw_output
                )
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Error executing tool {call.tool}: {e}")
                
                # Track failed execution
                self.analytics.track(
                    tenant_id=context.tenant_id,
                    event='agent.tools.failed',
                    user_id=context.user_id,
                    source='agent_tools',
                    props={
                        'tool': call.tool,
                        'call_id': call.id,
                        'error': str(e),
                        'execution_time': execution_time
                    }
                )
                
                return ToolResult(
                    id=call.id,
                    ok=False,
                    error={
                        'code': 'execution_error',
                        'message': str(e)
                    }
                )
        
        except Exception as e:
            logger.error(f"Error in tool kernel: {e}")
            return ToolResult(
                id=call.id,
                ok=False,
                error={
                    'code': 'kernel_error',
                    'message': str(e)
                }
            )
    
    def execute_many(self, calls: List[ToolCall], context: ToolContext, 
                    parallel: bool = False) -> ToolTranscript:
        """Execute multiple tool calls"""
        start_time = time.time()
        results = []
        errors = []
        
        if parallel:
            # Parallel execution (with concurrency control)
            import concurrent.futures
            
            def execute_single(call):
                return self.execute(call, context)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_call = {
                    executor.submit(execute_single, call): call 
                    for call in calls
                }
                
                for future in concurrent.futures.as_completed(future_to_call):
                    call = future_to_call[future]
                    try:
                        result = future.result()
                        results.append(result)
                        if not result.ok:
                            errors.append({
                                'call_id': call.id,
                                'tool': call.tool,
                                'error': result.error
                            })
                    except Exception as e:
                        logger.error(f"Error in parallel execution: {e}")
                        results.append(ToolResult(
                            id=call.id,
                            ok=False,
                            error={
                                'code': 'parallel_execution_error',
                                'message': str(e)
                            }
                        ))
                        errors.append({
                            'call_id': call.id,
                            'tool': call.tool,
                            'error': {'code': 'parallel_execution_error', 'message': str(e)}
                        })
        else:
            # Sequential execution
            for call in calls:
                result = self.execute(call, context)
                results.append(result)
                if not result.ok:
                    errors.append({
                        'call_id': call.id,
                        'tool': call.tool,
                        'error': result.error
                    })
        
        total_time = time.time() - start_time
        
        # Track batch execution
        self.analytics.track(
            tenant_id=context.tenant_id,
            event='agent.tools.batch',
            user_id=context.user_id,
            source='agent_tools',
            props={
                'total_calls': len(calls),
                'successful_calls': len([r for r in results if r.ok]),
                'failed_calls': len([r for r in results if not r.ok]),
                'total_time': total_time,
                'parallel': parallel
            }
        )
        
        return ToolTranscript(
            calls=calls,
            results=results,
            total_time=total_time,
            errors=errors
        )
    
    def get_tool_specs(self) -> List[Dict[str, Any]]:
        """Get all registered tool specifications"""
        return [spec.to_dict() for spec in tool_registry.list()]
    
    def get_tool_names(self) -> List[str]:
        """Get all registered tool names"""
        return tool_registry.list_names()
    
    def is_tool_available(self, tool_name: str) -> bool:
        """Check if tool is available"""
        return tool_registry.is_registered(tool_name)

# Global singleton kernel
tool_kernel = ToolKernel()
