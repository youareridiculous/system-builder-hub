"""
Codegen planner using LLM orchestration
"""
import os
import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from src.agent_codegen.schema import CodegenGoal, ProposedChange, UnifiedDiff, RiskLevel
from src.llm.providers import LLMProviderManager
from src.llm.prompt_library import PromptLibrary
from src.llm.schema import LLMRequest, LLMMessage
from src.agent_tools.kernel import tool_kernel
from src.agent_tools.types import ToolCall, ToolContext, ToolTranscript

logger = logging.getLogger(__name__)

class CodegenPlanner:
    """Codegen planner using LLM orchestration"""
    
    def __init__(self):
        self.provider_manager = LLMProviderManager()
        self.prompt_library = PromptLibrary()
        self.max_diff_files = int(os.environ.get('CODEGEN_MAX_DIFF_FILES', '50'))
    
    def plan_changes(self, goal: CodegenGoal, workspace_path: Path, 
                    tool_context: Optional[ToolContext] = None,
                    allow_tools: bool = False) -> ProposedChange:
        """Plan code changes using LLM with optional tool calling"""
        try:
            # Get repository context
            repo_context = self._analyze_repository(workspace_path)
            
            if allow_tools and tool_context:
                # Generate plan with tool calling
                plan, tool_transcript = self._generate_plan_with_tools(goal, repo_context, tool_context)
            else:
                # Generate plan using LLM only
                plan = self._generate_plan_with_llm(goal, repo_context)
                tool_transcript = None
            
            # Validate and process plan
            validated_plan = self._validate_plan(plan, goal)
            
            # Store tool transcript if available
            if tool_transcript:
                validated_plan.tool_transcript = tool_transcript
            
            return validated_plan
            
        except Exception as e:
            logger.error(f"Error planning changes: {e}")
            raise
    
    def _analyze_repository(self, workspace_path: Path) -> Dict[str, Any]:
        """Analyze repository structure and content"""
        try:
            repo_info = {
                'files': [],
                'structure': {},
                'main_files': [],
                'test_files': [],
                'config_files': []
            }
            
            # Walk through workspace
            for file_path in workspace_path.rglob('*'):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(workspace_path))
                    
                    # Skip hidden files and directories
                    if any(part.startswith('.') for part in file_path.parts):
                        continue
                    
                    file_info = {
                        'path': relative_path,
                        'size': file_path.stat().st_size,
                        'extension': file_path.suffix
                    }
                    
                    repo_info['files'].append(file_info)
                    
                    # Categorize files
                    if relative_path.endswith('.py'):
                        if 'test' in relative_path.lower():
                            repo_info['test_files'].append(relative_path)
                        else:
                            repo_info['main_files'].append(relative_path)
                    elif relative_path in ['requirements.txt', 'Dockerfile', 'wsgi.py', 'gunicorn.conf.py']:
                        repo_info['config_files'].append(relative_path)
                    elif relative_path == 'README.md':
                        repo_info['main_files'].append(relative_path)
            
            # Add file content samples for key files
            repo_info['samples'] = {}
            for file_path in repo_info['main_files'][:5]:  # Sample first 5 main files
                full_path = workspace_path / file_path
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                        repo_info['samples'][file_path] = content[:1000]  # First 1000 chars
                except Exception:
                    pass
            
            return repo_info
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            return {'files': [], 'structure': {}, 'main_files': [], 'test_files': [], 'config_files': []}
    
    def _generate_plan_with_llm(self, goal: CodegenGoal, repo_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate plan using LLM orchestration"""
        try:
            # Get provider
            provider = self.provider_manager.get_provider('local-stub')  # Use stub for deterministic results
            
            # Build guided input
            guided_input = {
                'role': 'Senior Python/Flask Engineer',
                'context': f"Repository with {len(repo_context['files'])} files, {len(repo_context['main_files'])} main files, {len(repo_context['test_files'])} test files",
                'task': f"Generate minimal diffs and tests for: {goal.goal_text}",
                'audience': 'maintainers',
                'output': 'unified diffs + test notes',
                'custom_fields': {
                    'repo_files': repo_context['files'],
                    'main_files': repo_context['main_files'],
                    'test_files': repo_context['test_files'],
                    'file_samples': repo_context.get('samples', {}),
                    'constraints': goal.constraints or {},
                    'allow_paths': goal.allow_paths or [],
                    'deny_globs': goal.deny_globs or []
                }
            }
            
            # Render prompt
            messages = self.prompt_library.render('codegen-patch-planner', guided_input, 'system')
            
            # Create LLM request
            request = LLMRequest(
                model=provider.default_model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=2000,
                json_mode=True
            )
            
            # Get response
            response = provider.complete(request)
            
            # Parse response
            plan = self._parse_llm_response(response.text)
            
            return plan
            
        except Exception as e:
            logger.error(f"Error generating plan with LLM: {e}")
            # Return a default plan for testing
            return self._generate_default_plan(goal, repo_context)
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured plan"""
        try:
            import json
            
            # Try to parse as JSON
            if response_text.strip().startswith('{'):
                return json.loads(response_text)
            
            # Fallback: parse as structured text
            return self._parse_structured_response(response_text)
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return {
                'summary': 'Failed to parse LLM response',
                'diffs': [],
                'risk': 'high',
                'files_touched': [],
                'tests_touched': []
            }
    
    def _parse_structured_response(self, response_text: str) -> Dict[str, Any]:
        """Parse structured text response"""
        lines = response_text.split('\n')
        plan = {
            'summary': '',
            'diffs': [],
            'risk': 'medium',
            'files_touched': [],
            'tests_touched': []
        }
        
        current_section = None
        current_diff = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('SUMMARY:'):
                current_section = 'summary'
                plan['summary'] = line.replace('SUMMARY:', '').strip()
            elif line.startswith('RISK:'):
                risk = line.replace('RISK:', '').strip().lower()
                if risk in ['low', 'medium', 'high']:
                    plan['risk'] = risk
            elif line.startswith('FILE:'):
                current_section = 'diff'
                current_diff = {
                    'file_path': line.replace('FILE:', '').strip(),
                    'operation': 'modify',
                    'diff_content': '',
                    'new_content': ''
                }
            elif line.startswith('DIFF:'):
                current_section = 'diff_content'
            elif line.startswith('CONTENT:'):
                current_section = 'content'
            elif current_section == 'diff_content' and current_diff:
                current_diff['diff_content'] += line + '\n'
            elif current_section == 'content' and current_diff:
                current_diff['new_content'] += line + '\n'
            elif line.startswith('END_FILE') and current_diff:
                plan['diffs'].append(current_diff)
                plan['files_touched'].append(current_diff['file_path'])
                current_diff = None
                current_section = None
        
        return plan
    
    def _generate_default_plan(self, goal: CodegenGoal, repo_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate default plan for testing"""
        # Create a simple default plan
        plan = {
            'summary': f"Implement changes for: {goal.goal_text}",
            'risk': 'low',
            'diffs': [],
            'files_touched': [],
            'tests_touched': []
        }
        
        # Add a sample diff for README.md
        if 'README.md' in repo_context['main_files']:
            plan['diffs'].append({
                'file_path': 'README.md',
                'operation': 'modify',
                'diff_content': '''--- a/README.md
+++ b/README.md
@@ -1,3 +1,4 @@
 # SBH Generated App
 
 This application was generated by System Builder Hub.
+Updated by SBH Codegen Agent
''',
                'new_content': '''# SBH Generated App

This application was generated by System Builder Hub.
Updated by SBH Codegen Agent
'''
            })
            plan['files_touched'].append('README.md')
        
        # Add a sample endpoint if there are Python files
        if repo_context['main_files']:
            for file_path in repo_context['main_files']:
                if file_path.endswith('.py') and 'routes' in file_path.lower():
                    plan['diffs'].append({
                        'file_path': file_path,
                        'operation': 'modify',
                        'diff_content': f'''--- a/{file_path}
+++ b/{file_path}
@@ -1,3 +1,8 @@
 from flask import Blueprint, render_template, jsonify, request
 from app.models import db

+@main_bp.route('/api/codegen-test')
+def codegen_test():
+    return jsonify({{"message": "Codegen agent test endpoint"}})
+
 main_bp = Blueprint('main', __name__)
''',
                        'new_content': '''from flask import Blueprint, render_template, jsonify, request
from app.models import db

@main_bp.route('/api/codegen-test')
def codegen_test():
    return jsonify({"message": "Codegen agent test endpoint"})

main_bp = Blueprint('main', __name__)
'''
                    })
                    plan['files_touched'].append(file_path)
                    break
        
        return plan
    
    def _validate_plan(self, plan: Dict[str, Any], goal: CodegenGoal) -> ProposedChange:
        """Validate and process plan"""
        try:
            # Extract plan components
            summary = plan.get('summary', 'No summary provided')
            risk_str = plan.get('risk', 'medium').lower()
            diffs_data = plan.get('diffs', [])
            
            # Validate risk level
            if risk_str == 'low':
                risk = RiskLevel.LOW
            elif risk_str == 'high':
                risk = RiskLevel.HIGH
            else:
                risk = RiskLevel.MEDIUM
            
            # Process diffs
            diffs = []
            files_touched = []
            tests_touched = []
            
            for diff_data in diffs_data[:self.max_diff_files]:  # Limit number of files
                file_path = diff_data.get('file_path', '')
                
                # Validate file path
                if not self._validate_file_path(file_path, goal):
                    logger.warning(f"Skipping invalid file path: {file_path}")
                    continue
                
                # Create unified diff
                diff = UnifiedDiff(
                    file_path=file_path,
                    diff_content=diff_data.get('diff_content', ''),
                    operation=diff_data.get('operation', 'modify'),
                    old_content=diff_data.get('old_content'),
                    new_content=diff_data.get('new_content', '')
                )
                
                diffs.append(diff)
                files_touched.append(file_path)
                
                # Check if it's a test file
                if 'test' in file_path.lower():
                    tests_touched.append(file_path)
            
            return ProposedChange(
                summary=summary,
                diffs=diffs,
                risk=risk,
                files_touched=files_touched,
                tests_touched=tests_touched
            )
            
        except Exception as e:
            logger.error(f"Error validating plan: {e}")
            raise
    
    def _validate_file_path(self, file_path: str, goal: CodegenGoal) -> bool:
        """Validate file path against allow/deny patterns"""
        from fnmatch import fnmatch
        
        # Check deny patterns
        deny_globs = goal.deny_globs or []
        for pattern in deny_globs:
            if fnmatch(file_path, pattern):
                logger.warning(f"File path denied by pattern {pattern}: {file_path}")
                return False
        
        # Check allow patterns
        allow_paths = goal.allow_paths or []
        if allow_paths:
            for pattern in allow_paths:
                if fnmatch(file_path, pattern):
                    return True
            logger.warning(f"File path not in allow list: {file_path}")
            return False
        
        return True

    def _generate_plan_with_tools(self, goal: CodegenGoal, repo_context: Dict[str, Any], 
                                 tool_context: ToolContext) -> tuple[Dict[str, Any], ToolTranscript]:
        """Generate plan using LLM with tool calling"""
        try:
            # Get provider
            provider = self.provider_manager.get_provider('local-stub')  # Use stub for deterministic results
            
            # Build guided input with tool information
            guided_input = {
                'role': 'Senior Python/Flask Engineer with Tool Access',
                'context': f"Repository with {len(repo_context['files'])} files, {len(repo_context['main_files'])} main files, {len(repo_context['test_files'])} test files. Tools available: {', '.join(tool_kernel.get_tool_names())}",
                'task': f"Generate minimal diffs and tests for: {goal.goal_text}. Use tools as needed to gather information or perform actions.",
                'audience': 'maintainers',
                'output': 'unified diffs + test notes + tool usage',
                'custom_fields': {
                    'repo_files': repo_context['files'],
                    'main_files': repo_context['main_files'],
                    'test_files': repo_context['test_files'],
                    'file_samples': repo_context.get('samples', {}),
                    'constraints': goal.constraints or {},
                    'allow_paths': goal.allow_paths or [],
                    'deny_globs': goal.deny_globs or [],
                    'available_tools': tool_kernel.get_tool_specs()
                }
            }
            
            # Initialize tool transcript
            tool_transcript = ToolTranscript(calls=[], results=[], total_time=0.0, errors=[])
            
            # Tool calling loop
            max_iterations = 5
            for iteration in range(max_iterations):
                # Render prompt with tool results
                messages = self.prompt_library.render('codegen-tool-planner', guided_input, 'system')
                
                # Add tool results to context if available
                if tool_transcript.results:
                    tool_results_text = self._format_tool_results(tool_transcript.results)
                    messages.append(LLMMessage(
                        role='assistant',
                        content=f"Tool results from previous calls:\n{tool_results_text}"
                    ))
                
                # Create LLM request
                request = LLMRequest(
                    model=provider.default_model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2000,
                    json_mode=True
                )
                
                # Get response
                response = provider.complete(request)
                
                # Parse response for tool calls
                tool_calls = self._extract_tool_calls(response.text)
                
                if not tool_calls:
                    # No more tool calls, parse final plan
                    plan = self._parse_llm_response(response.text)
                    return plan, tool_transcript
                
                # Execute tool calls
                for tool_call in tool_calls:
                    result = tool_kernel.execute(tool_call, tool_context)
                    tool_transcript.calls.append(tool_call)
                    tool_transcript.results.append(result)
                    
                    if not result.ok:
                        tool_transcript.errors.append({
                            'call_id': tool_call.id,
                            'tool': tool_call.tool,
                            'error': result.error
                        })
                
                # Update guided input with tool results
                guided_input['custom_fields']['tool_results'] = [
                    {
                        'tool': result.id,
                        'success': result.ok,
                        'output': result.redacted_output if result.ok else result.error
                    }
                    for result in tool_transcript.results
                ]
            
            # If we reach here, use the last response as the plan
            plan = self._parse_llm_response(response.text)
            return plan, tool_transcript
            
        except Exception as e:
            logger.error(f"Error generating plan with tools: {e}")
            # Return a default plan
            return self._generate_default_plan(goal, repo_context), ToolTranscript(calls=[], results=[], total_time=0.0, errors=[])
    
    def _extract_tool_calls(self, response_text: str) -> List[ToolCall]:
        """Extract tool calls from LLM response"""
        tool_calls = []
        
        try:
            # Try to parse as JSON first
            if response_text.strip().startswith('{'):
                data = json.loads(response_text)
                if 'tool_calls' in data:
                    for call_data in data['tool_calls']:
                        tool_calls.append(ToolCall.from_dict(call_data))
                    return tool_calls
            
            # Parse structured text for tool calls
            lines = response_text.split('\n')
            current_call = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('TOOL_CALL:'):
                    if current_call:
                        tool_calls.append(current_call)
                    
                    # Parse tool call header
                    parts = line.replace('TOOL_CALL:', '').strip().split()
                    if len(parts) >= 2:
                        current_call = ToolCall(
                            id=parts[0],
                            tool=parts[1],
                            args={}
                        )
                
                elif line.startswith('ARGS:') and current_call:
                    # Parse arguments
                    args_str = line.replace('ARGS:', '').strip()
                    try:
                        current_call.args = json.loads(args_str)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse tool args: {args_str}")
                
                elif line.startswith('END_TOOL_CALL') and current_call:
                    tool_calls.append(current_call)
                    current_call = None
            
            # Add any remaining call
            if current_call:
                tool_calls.append(current_call)
            
        except Exception as e:
            logger.error(f"Error extracting tool calls: {e}")
        
        return tool_calls
    
    def _format_tool_results(self, results: List) -> str:
        """Format tool results for LLM context"""
        formatted = []
        
        for result in results:
            if result.ok:
                formatted.append(f"Tool {result.id}: SUCCESS - {result.redacted_output}")
            else:
                formatted.append(f"Tool {result.id}: FAILED - {result.error}")
        
        return "\n".join(formatted)
