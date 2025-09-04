"""
Auto-Fixer Agent
Analyzes test failures and generates fixes to resolve issues.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from .base import BaseAgent, AgentContext

logger = logging.getLogger(__name__)


class AutoFixerAgent(BaseAgent):
    """Auto-Fixer Agent - generates fixes for test failures."""
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.fix_patterns = self._load_fix_patterns()
    
    def _load_fix_patterns(self) -> Dict[str, Any]:
        """Load common fix patterns for different types of failures."""
        return {
            "missing_imports": {
                "pattern": "ImportError|ModuleNotFoundError|NameError",
                "fixes": [
                    "Add missing import statements",
                    "Check import paths and module names",
                    "Install missing dependencies"
                ]
            },
            "syntax_errors": {
                "pattern": "SyntaxError|IndentationError",
                "fixes": [
                    "Fix syntax errors in code",
                    "Check indentation and brackets",
                    "Validate Python syntax"
                ]
            },
            "database_errors": {
                "pattern": "DatabaseError|OperationalError|IntegrityError",
                "fixes": [
                    "Fix database schema issues",
                    "Check foreign key constraints",
                    "Validate database migrations"
                ]
            },
            "api_errors": {
                "pattern": "404|500|422",
                "fixes": [
                    "Fix API endpoint routing",
                    "Check request/response schemas",
                    "Validate API parameters"
                ]
            },
            "auth_errors": {
                "pattern": "401|403|Unauthorized|Forbidden",
                "fixes": [
                    "Fix authentication logic",
                    "Check authorization rules",
                    "Validate JWT tokens"
                ]
            },
            "validation_errors": {
                "pattern": "ValidationError|422|Bad Request",
                "fixes": [
                    "Fix input validation",
                    "Check data types and constraints",
                    "Update Pydantic schemas"
                ]
            }
        }
    
    async def execute(self, action: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Auto-Fixer actions."""
        if action == "fix_issues":
            return await self._fix_issues(inputs)
        elif action == "analyze_failures":
            return await self._analyze_failures(inputs)
        elif action == "generate_fixes":
            return await self._generate_fixes(inputs)
        elif action == "apply_fixes":
            return await self._apply_fixes(inputs)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _fix_issues(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Main method to fix issues based on evaluation results."""
        spec = inputs.get("spec", {})
        evaluation_report = inputs.get("evaluation_report", {})
        artifacts = inputs.get("artifacts", [])
        current_code = inputs.get("current_code", "")
        
        # Analyze failures
        failure_analysis = await self._analyze_failures({
            "evaluation_report": evaluation_report,
            "artifacts": artifacts
        })
        
        # Generate fixes
        fixes = await self._generate_fixes({
            "spec": spec,
            "failure_analysis": failure_analysis,
            "artifacts": artifacts,
            "current_code": current_code
        })
        
        # Apply fixes
        applied_fixes = await self._apply_fixes({
            "fixes": fixes,
            "artifacts": artifacts,
            "current_code": current_code
        })
        
        return {
            "fixed": applied_fixes["success"],
            "failure_analysis": failure_analysis,
            "generated_fixes": fixes,
            "applied_fixes": applied_fixes,
            "new_artifacts": applied_fixes.get("new_artifacts", []),
            "summary": applied_fixes.get("summary", "")
        }
    
    async def _analyze_failures(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test failures and categorize issues."""
        evaluation_report = inputs.get("evaluation_report", {})
        artifacts = inputs.get("artifacts", [])
        
        failures = []
        categories = {}
        
        # Analyze unit test failures
        unit_tests = evaluation_report.get("unit_tests", {})
        for test_result in unit_tests.get("results", []):
            if test_result.get("status") == "failed":
                failure = self._categorize_failure(test_result, "unit_test")
                failures.append(failure)
                categories[failure["category"]] = categories.get(failure["category"], 0) + 1
        
        # Analyze smoke test failures
        smoke_tests = evaluation_report.get("smoke_tests", {})
        for test_result in smoke_tests.get("results", []):
            if test_result.get("status") == "failed":
                failure = self._categorize_failure(test_result, "smoke_test")
                failures.append(failure)
                categories[failure["category"]] = categories.get(failure["category"], 0) + 1
        
        # Analyze golden task failures
        golden_tests = evaluation_report.get("golden_tests", {})
        for task_result in golden_tests.get("results", []):
            if task_result.get("status") == "failed":
                failure = self._categorize_failure(task_result, "golden_task")
                failures.append(failure)
                categories[failure["category"]] = categories.get(failure["category"], 0) + 1
        
        # Analyze code quality issues
        code_quality = evaluation_report.get("code_quality", {})
        if code_quality.get("documentation_ratio", 0) < 0.1:
            failures.append({
                "type": "code_quality",
                "category": "documentation",
                "severity": "medium",
                "description": "Low documentation coverage",
"error_message": "Documentation ratio: 0.00",
                "file": "multiple",
                "line": None
            })
            categories["documentation"] = categories.get("documentation", 0) + 1
        
        return {
            "failures": failures,
            "categories": categories,
            "total_failures": len(failures),
            "priority_order": self._prioritize_failures(failures)
        }
    
    def _categorize_failure(self, test_result: Dict[str, Any], test_type: str) -> Dict[str, Any]:
        """Categorize a test failure based on error patterns."""
        error_message = test_result.get("error", "")
        test_name = test_result.get("name", "")
        
        # Match error patterns
        for category, pattern_info in self.fix_patterns.items():
            if pattern_info["pattern"].lower() in error_message.lower():
                return {
                    "type": test_type,
                    "category": category,
                    "severity": "high" if category in ["syntax_errors", "database_errors"] else "medium",
                    "description": f"{test_type.replace('_', ' ').title()} failure: {test_name}",
                    "error_message": error_message,
                    "file": self._extract_file_from_error(error_message),
                    "line": self._extract_line_from_error(error_message),
                    "suggested_fixes": pattern_info["fixes"]
                }
        
        # Default categorization
        return {
            "type": test_type,
            "category": "unknown",
            "severity": "medium",
            "description": f"{test_type.replace('_', ' ').title()} failure: {test_name}",
            "error_message": error_message,
            "file": self._extract_file_from_error(error_message),
            "line": self._extract_line_from_error(error_message),
            "suggested_fixes": ["Review error message and implement appropriate fix"]
        }
    
    def _extract_file_from_error(self, error_message: str) -> Optional[str]:
        """Extract file name from error message."""
        import re
        
        # Look for file patterns in error messages
        patterns = [
            r'File "([^"]+)"',
            r'in ([^:]+):',
            r'at ([^:]+):'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_line_from_error(self, error_message: str) -> Optional[int]:
        """Extract line number from error message."""
        import re
        
        # Look for line number patterns
        patterns = [
            r'line (\d+)',
            r':(\d+):',
            r'at line (\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _prioritize_failures(self, failures: List[Dict[str, Any]]) -> List[str]:
        """Prioritize failures for fixing."""
        # Priority order: syntax errors, database errors, auth errors, api errors, others
        priority_order = [
            "syntax_errors",
            "database_errors", 
            "auth_errors",
            "api_errors",
            "validation_errors",
            "missing_imports",
            "documentation",
            "unknown"
        ]
        
        # Sort failures by priority
        sorted_failures = sorted(
            failures,
            key=lambda f: priority_order.index(f["category"]) if f["category"] in priority_order else len(priority_order)
        )
        
        return [f["category"] for f in sorted_failures]
    
    async def _generate_fixes(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fixes for identified issues."""
        spec = inputs.get("spec", {})
        failure_analysis = inputs.get("failure_analysis", {})
        artifacts = inputs.get("artifacts", [])
        current_code = inputs.get("current_code", "")
        
        fixes = []
        
        # Generate fixes for each failure category
        for failure in failure_analysis.get("failures", []):
            category = failure["category"]
            fix = await self._generate_category_fix(category, failure, spec, artifacts, current_code)
            if fix:
                fixes.append(fix)
        
        return {
            "fixes": fixes,
            "total_fixes": len(fixes),
            "fix_summary": self._generate_fix_summary(fixes)
        }
    
    async def _generate_category_fix(self, category: str, failure: Dict[str, Any], 
                                   spec: Dict[str, Any], artifacts: List[Dict[str, Any]], 
                                   current_code: str) -> Optional[Dict[str, Any]]:
        """Generate fix for a specific failure category."""
        if category == "missing_imports":
            return await self._fix_missing_imports(failure, artifacts)
        elif category == "syntax_errors":
            return await self._fix_syntax_errors(failure, artifacts)
        elif category == "database_errors":
            return await self._fix_database_errors(failure, spec, artifacts)
        elif category == "api_errors":
            return await self._fix_api_errors(failure, spec, artifacts)
        elif category == "auth_errors":
            return await self._fix_auth_errors(failure, spec, artifacts)
        elif category == "validation_errors":
            return await self._fix_validation_errors(failure, spec, artifacts)
        elif category == "documentation":
            return await self._fix_documentation(failure, artifacts)
        else:
            return await self._fix_generic_issue(failure, artifacts)
    
    async def _fix_missing_imports(self, failure: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix missing import issues."""
        error_message = failure.get("error_message", "")
        
        # Extract missing module/class names from error
        missing_imports = self._extract_missing_imports(error_message)
        
        # Find relevant files to fix
        target_files = self._find_files_by_extension(artifacts, [".py"])
        
        fixes = []
        for file_info in target_files:
            content = file_info.get("content", "")
            
            # Add missing imports
            new_imports = []
            for import_name in missing_imports:
                if import_name not in content:
                    new_imports.append(f"import {import_name}")
            
            if new_imports:
                # Add imports at the top of the file
                lines = content.split('\n')
                import_section_end = 0
                
                # Find end of import section
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith(('import ', 'from ')):
                        import_section_end = i
                        break
                
                # Insert new imports
                for import_stmt in new_imports:
                    lines.insert(import_section_end, import_stmt)
                    import_section_end += 1
                
                fixes.append({
                    "file_path": file_info["file_path"],
                    "type": "add_imports",
                    "changes": new_imports,
                    "new_content": '\n'.join(lines)
                })
        
        return {
            "category": "missing_imports",
            "description": f"Add missing imports: {', '.join(missing_imports)}",
            "fixes": fixes,
            "files_affected": len(fixes)
        }
    
    def _extract_missing_imports(self, error_message: str) -> List[str]:
        """Extract missing import names from error message."""
        import re
        
        # Common patterns for missing imports
        patterns = [
            r"name '([^']+)' is not defined",
            r"No module named '([^']+)'",
            r"cannot import name '([^']+)'",
            r"ImportError: No module named '([^']+)'"
        ]
        
        missing_imports = []
        for pattern in patterns:
            matches = re.findall(pattern, error_message)
            missing_imports.extend(matches)
        
        return list(set(missing_imports))  # Remove duplicates
    
    async def _fix_syntax_errors(self, failure: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix syntax errors."""
        error_message = failure.get("error_message", "")
        file_path = failure.get("file")
        
        if not file_path:
            return {
                "category": "syntax_errors",
                "description": "Cannot fix syntax error - file not identified",
                "fixes": [],
                "files_affected": 0
            }
        
        # Find the file to fix
        target_file = self._find_file_by_path(artifacts, file_path)
        if not target_file:
            return {
                "category": "syntax_errors",
                "description": f"Cannot find file to fix: {file_path}",
                "fixes": [],
                "files_affected": 0
            }
        
        content = target_file.get("content", "")
        line_number = failure.get("line")
        
        # Use LLM to fix syntax error
        fix_prompt = f"""
Fix the syntax error in the following Python code:

Error: {error_message}
File: {file_path}
Line: {line_number}

Code:
{content}

Provide only the corrected code without any explanations.
"""
        
        try:
            response = await self.context.llm.generate(
                prompt=fix_prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            fixed_content = response['content']
            
            return {
                "category": "syntax_errors",
                "description": f"Fix syntax error in {file_path}",
                "fixes": [{
                    "file_path": file_path,
                    "type": "fix_syntax",
                    "changes": ["Fix syntax error"],
                    "new_content": fixed_content
                }],
                "files_affected": 1
            }
            
        except Exception as e:
            logger.error(f"Failed to generate syntax fix: {e}")
            return {
                "category": "syntax_errors",
                "description": f"Failed to fix syntax error: {str(e)}",
                "fixes": [],
                "files_affected": 0
            }
    
    async def _fix_database_errors(self, failure: Dict[str, Any], spec: Dict[str, Any], 
                                 artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix database-related errors."""
        error_message = failure.get("error_message", "")
        
        # Common database fixes
        fixes = []
        
        # Check for missing database models
        if "table" in error_message.lower() and "doesn't exist" in error_message.lower():
            # Generate missing database models
            model_fix = await self._generate_missing_models(spec, artifacts)
            if model_fix:
                fixes.append(model_fix)
        
        # Check for migration issues
        if "migration" in error_message.lower():
            # Generate missing migrations
            migration_fix = await self._generate_missing_migrations(spec, artifacts)
            if migration_fix:
                fixes.append(migration_fix)
        
        return {
            "category": "database_errors",
            "description": "Fix database schema and migration issues",
            "fixes": fixes,
            "files_affected": len(fixes)
        }
    
    async def _fix_api_errors(self, failure: Dict[str, Any], spec: Dict[str, Any], 
                            artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix API-related errors."""
        error_message = failure.get("error_message", "")
        
        fixes = []
        
        # Check for missing endpoints
        if "404" in error_message:
            # Generate missing API endpoints
            endpoint_fix = await self._generate_missing_endpoints(spec, artifacts)
            if endpoint_fix:
                fixes.append(endpoint_fix)
        
        # Check for schema validation errors
        if "422" in error_message or "validation" in error_message.lower():
            # Fix schema validation
            schema_fix = await self._fix_schema_validation(spec, artifacts)
            if schema_fix:
                fixes.append(schema_fix)
        
        return {
            "category": "api_errors",
            "description": "Fix API endpoint and validation issues",
            "fixes": fixes,
            "files_affected": len(fixes)
        }
    
    async def _fix_auth_errors(self, failure: Dict[str, Any], spec: Dict[str, Any], 
                             artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix authentication-related errors."""
        error_message = failure.get("error_message", "")
        
        fixes = []
        
        # Check for missing authentication
        if "401" in error_message or "unauthorized" in error_message.lower():
            # Generate authentication middleware
            auth_fix = await self._generate_auth_middleware(spec, artifacts)
            if auth_fix:
                fixes.append(auth_fix)
        
        # Check for missing authorization
        if "403" in error_message or "forbidden" in error_message.lower():
            # Generate authorization checks
            authz_fix = await self._generate_authz_checks(spec, artifacts)
            if authz_fix:
                fixes.append(authz_fix)
        
        return {
            "category": "auth_errors",
            "description": "Fix authentication and authorization issues",
            "fixes": fixes,
            "files_affected": len(fixes)
        }
    
    async def _fix_validation_errors(self, failure: Dict[str, Any], spec: Dict[str, Any], 
                                   artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix validation-related errors."""
        error_message = failure.get("error_message", "")
        
        fixes = []
        
        # Check for Pydantic schema issues
        if "pydantic" in error_message.lower() or "validation" in error_message.lower():
            # Fix Pydantic schemas
            schema_fix = await self._fix_pydantic_schemas(spec, artifacts)
            if schema_fix:
                fixes.append(schema_fix)
        
        return {
            "category": "validation_errors",
            "description": "Fix data validation issues",
            "fixes": fixes,
            "files_affected": len(fixes)
        }
    
    async def _fix_documentation(self, failure: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix documentation issues."""
        fixes = []
        
        # Add documentation to Python files
        python_files = self._find_files_by_extension(artifacts, [".py"])
        
        for file_info in python_files:
            content = file_info.get("content", "")
            
            # Check if file has docstring
            if not content.strip().startswith('"""') and not content.strip().startswith("'''"):
                # Add file docstring
                lines = content.split('\n')
                file_name = file_info["file_path"].split('/')[-1]
                
                docstring = f'''"""
{file_name}

Auto-generated file for the system.
"""

'''
                
                lines.insert(0, docstring)
                
                fixes.append({
                    "file_path": file_info["file_path"],
                    "type": "add_documentation",
                    "changes": ["Add file docstring"],
                    "new_content": '\n'.join(lines)
                })
        
        return {
            "category": "documentation",
            "description": "Add missing documentation",
            "fixes": fixes,
            "files_affected": len(fixes)
        }
    
    async def _fix_generic_issue(self, failure: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fix generic issues using LLM."""
        error_message = failure.get("error_message", "")
        file_path = failure.get("file")
        
        if not file_path:
            return {
                "category": "unknown",
                "description": "Cannot fix issue - file not identified",
                "fixes": [],
                "files_affected": 0
            }
        
        target_file = self._find_file_by_path(artifacts, file_path)
        if not target_file:
            return {
                "category": "unknown",
                "description": f"Cannot find file to fix: {file_path}",
                "fixes": [],
                "files_affected": 0
            }
        
        content = target_file.get("content", "")
        
        # Use LLM to fix the issue
        fix_prompt = f"""
Fix the following error in the code:

Error: {error_message}
File: {file_path}

Code:
{content}

Provide only the corrected code without any explanations.
"""
        
        try:
            response = await self.context.llm.generate(
                prompt=fix_prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            fixed_content = response['content']
            
            return {
                "category": "unknown",
                "description": f"Fix issue in {file_path}",
                "fixes": [{
                    "file_path": file_path,
                    "type": "fix_generic",
                    "changes": ["Fix identified issue"],
                    "new_content": fixed_content
                }],
                "files_affected": 1
            }
            
        except Exception as e:
            logger.error(f"Failed to generate generic fix: {e}")
            return {
                "category": "unknown",
                "description": f"Failed to fix issue: {str(e)}",
                "fixes": [],
                "files_affected": 0
            }
    
    def _find_files_by_extension(self, artifacts: List[Dict[str, Any]], extensions: List[str]) -> List[Dict[str, Any]]:
        """Find files with specific extensions."""
        return [
            artifact for artifact in artifacts
            if any(artifact.get("file_path", "").endswith(ext) for ext in extensions)
        ]
    
    def _find_file_by_path(self, artifacts: List[Dict[str, Any]], file_path: str) -> Optional[Dict[str, Any]]:
        """Find artifact by file path."""
        for artifact in artifacts:
            if artifact.get("file_path") == file_path:
                return artifact
        return None
    
    async def _generate_missing_models(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate missing database models."""
        # This would generate missing models based on spec
        # Implementation would be similar to CodegenEngineerAgent
        return None
    
    async def _generate_missing_migrations(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate missing database migrations."""
        # This would generate missing migrations
        return None
    
    async def _generate_missing_endpoints(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate missing API endpoints."""
        # This would generate missing endpoints
        return None
    
    async def _fix_schema_validation(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Fix schema validation issues."""
        # This would fix Pydantic schemas
        return None
    
    async def _generate_auth_middleware(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate authentication middleware."""
        # This would generate auth middleware
        return None
    
    async def _generate_authz_checks(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate authorization checks."""
        # This would generate authz checks
        return None
    
    async def _fix_pydantic_schemas(self, spec: Dict[str, Any], artifacts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Fix Pydantic schemas."""
        # This would fix Pydantic schemas
        return None
    
    async def _apply_fixes(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply generated fixes to artifacts."""
        fixes = inputs.get("fixes", [])
        artifacts = inputs.get("artifacts", [])
        current_code = inputs.get("current_code", "")
        
        new_artifacts = artifacts.copy()
        applied_count = 0
        
        for fix in fixes:
            if isinstance(fix, str):
                fix = {"fixes": []}
            for file_fix in fix.get("fixes", []):
                file_path = file_fix["file_path"]
                
                # Find and update the artifact
                for i, artifact in enumerate(new_artifacts):
                    if artifact.get("file_path") == file_path:
                        new_artifacts[i] = {
                            **artifact,
                            "content": file_fix["new_content"]
                        }
                        applied_count += 1
                        break
        
        success = applied_count > 0
        
        return {
            "success": success,
            "applied_fixes": applied_count,
            "new_artifacts": new_artifacts,
"summary": f"Applied {applied_count} fixes"
        }
    
    def _generate_fix_summary(self, fixes: List[Dict[str, Any]]) -> str:
        """Generate summary of fixes."""
        if not fixes:
            return "No fixes generated"
        
        summary_parts = []
        for fix in fixes:
            if isinstance(fix, str):
                fix = {"fixes": []}
            category = fix["category"]
            files_affected = fix["files_affected"]
            summary_parts.append(f"{category}: {files_affected} files")
        
        return f"Generated fixes for: {', '.join(summary_parts)}"
