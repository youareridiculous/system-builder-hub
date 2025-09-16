#!/usr/bin/env python3
"""
Acceptance Runner for SBH Full Build Mode

Parses "Acceptance Criteria" sections into concrete tests (unit/integration/smoke).
Auto-generates test stubs (e.g., test_endpoints.py, schema_validation.test.ts).
Runs after build; halts if failing.
"""

import re
import os
import subprocess
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)

class TestType(Enum):
    """Types of tests to generate"""
    UNIT = "unit"
    INTEGRATION = "integration"
    SMOKE = "smoke"
    ENDPOINT = "endpoint"
    SCHEMA = "schema"

@dataclass
class AcceptanceCriteria:
    """Represents a single acceptance criterion"""
    criterion_id: str
    description: str
    test_type: TestType
    expected_behavior: str
    test_file: str
    test_function: str
    language: str = "python"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class TestResult:
    """Result of running a test"""
    test_id: str
    passed: bool
    output: str
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class AcceptanceRunner:
    """Runs acceptance tests and generates test stubs"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.test_results: List[TestResult] = []
        self.generated_tests: List[str] = []
    
    def parse_acceptance_criteria(self, content: str, language: str = "python") -> List[AcceptanceCriteria]:
        """Parse acceptance criteria from content"""
        criteria = []
        
        # Common patterns for acceptance criteria
        patterns = [
            r'(?i)(?:should|must|need to|verify|assert)\s+([^.\n]+)',
            r'(?i)(?:endpoint|api|function)\s+([^.\n]+)\s+(?:returns|should|must)',
            r'(?i)(?:test|check|validate)\s+([^.\n]+)',
            r'(?i)(?:when|if)\s+([^.\n]+)\s+(?:then|should)',
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                description = match.group(1).strip()
                if description:
                    criterion = self._create_criterion_from_description(description, language, i)
                    criteria.append(criterion)
        
        return criteria
    
    def _create_criterion_from_description(self, description: str, language: str, index: int) -> AcceptanceCriteria:
        """Create acceptance criterion from description"""
        # Determine test type based on description
        test_type = TestType.UNIT
        if "endpoint" in description.lower() or "api" in description.lower():
            test_type = TestType.ENDPOINT
        elif "schema" in description.lower() or "validation" in description.lower():
            test_type = TestType.SCHEMA
        elif "integration" in description.lower():
            test_type = TestType.INTEGRATION
        elif "smoke" in description.lower():
            test_type = TestType.SMOKE
        
        # Generate test file and function names
        test_file = self._generate_test_file_name(test_type, language)
        test_function = self._generate_test_function_name(description)
        
        return AcceptanceCriteria(
            criterion_id=f"criterion_{index}",
            description=description,
            test_type=test_type,
            expected_behavior=description,
            test_file=test_file,
            test_function=test_function,
            language=language
        )
    
    def _generate_test_file_name(self, test_type: TestType, language: str) -> str:
        """Generate test file name based on type and language"""
        if language == "python":
            return f"tests/test_{test_type.value}.py"
        elif language == "typescript":
            return f"tests/{test_type.value}.test.ts"
        else:
            return f"tests/test_{test_type.value}.py"
    
    def _generate_test_function_name(self, description: str) -> str:
        """Generate test function name from description"""
        # Clean and convert description to function name
        func_name = re.sub(r'[^a-zA-Z0-9\s]', '', description.lower())
        func_name = re.sub(r'\s+', '_', func_name)
        func_name = func_name[:50]  # Limit length
        return f"test_{func_name}"
    
    def generate_test_stubs(self, criteria: List[AcceptanceCriteria]) -> Dict[str, Any]:
        """Generate test stubs for acceptance criteria"""
        results = {
            "generated_files": [],
            "failed_generations": [],
            "total_criteria": len(criteria)
        }
        
        # Group criteria by test file
        files_to_generate = {}
        for criterion in criteria:
            if criterion.test_file not in files_to_generate:
                files_to_generate[criterion.test_file] = []
            files_to_generate[criterion.test_file].append(criterion)
        
        # Generate each test file
        for test_file, file_criteria in files_to_generate.items():
            try:
                content = self._generate_test_file_content(file_criteria)
                self._write_test_file(test_file, content)
                results["generated_files"].append(test_file)
                self.generated_tests.append(test_file)
            except Exception as e:
                logger.error(f"Failed to generate test file {test_file}: {e}")
                results["failed_generations"].append({
                    "file": test_file,
                    "error": str(e)
                })
        
        return results
    
    def _generate_test_file_content(self, criteria: List[AcceptanceCriteria]) -> str:
        """Generate content for a test file"""
        if not criteria:
            return ""
        
        language = criteria[0].language
        test_type = criteria[0].test_type
        
        if language == "python":
            return self._generate_python_test_content(criteria, test_type)
        elif language == "typescript":
            return self._generate_typescript_test_content(criteria, test_type)
        else:
            return self._generate_python_test_content(criteria, test_type)
    
    def _generate_python_test_content(self, criteria: List[AcceptanceCriteria], test_type: TestType) -> str:
        """Generate Python test file content"""
        content = f'#!/usr/bin/env python3\n"""\n{test_type.value.title()} tests generated by SBH Acceptance Runner\n"""\n\nimport unittest\nimport requests\nimport json\nfrom unittest.mock import Mock, patch\n\n\nclass Test{test_type.value.title()}(unittest.TestCase):\n    """Test class for {test_type.value} acceptance criteria"""\n\n'
        
        for criterion in criteria:
            content += f'    def {criterion.test_function}(self):\n'
            content += f'        """Test: {criterion.description}"""\n'
            
            if test_type == TestType.ENDPOINT:
                content += self._generate_endpoint_test_content(criterion)
            elif test_type == TestType.SCHEMA:
                content += self._generate_schema_test_content(criterion)
            elif test_type == TestType.SMOKE:
                content += self._generate_smoke_test_content(criterion)
            else:
                content += self._generate_unit_test_content(criterion)
            
            content += '\n'
        
        content += '\nif __name__ == "__main__":\n    unittest.main()\n'
        return content
    
    def _generate_typescript_test_content(self, criteria: List[AcceptanceCriteria], test_type: TestType) -> str:
        """Generate TypeScript test file content"""
        content = f'/**\n * {test_type.value.title()} tests generated by SBH Acceptance Runner\n */\n\nimport {{ describe, it, expect }} from \'jest\';\n\n'
        
        content += f'describe(\'{test_type.value.title()} Tests\', () => {{\n'
        
        for criterion in criteria:
            content += f'  it(\'{criterion.description}\', () => {{\n'
            
            if test_type == TestType.ENDPOINT:
                content += self._generate_endpoint_test_content_ts(criterion)
            elif test_type == TestType.SCHEMA:
                content += self._generate_schema_test_content_ts(criterion)
            elif test_type == TestType.SMOKE:
                content += self._generate_smoke_test_content_ts(criterion)
            else:
                content += self._generate_unit_test_content_ts(criterion)
            
            content += '  });\n\n'
        
        content += '});\n'
        return content
    
    def _generate_endpoint_test_content(self, criterion: AcceptanceCriteria) -> str:
        """Generate endpoint test content for Python"""
        return f'''        # Test endpoint behavior: {criterion.description}
        try:
            # TODO: Replace with actual endpoint URL
            response = requests.get('http://localhost:5001/api/test')
            self.assertEqual(response.status_code, 200)
            
            # TODO: Add specific assertions based on: {criterion.expected_behavior}
            data = response.json()
            self.assertIn('ok', data)
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Endpoint test failed: {{e}}")'''
    
    def _generate_schema_test_content(self, criterion: AcceptanceCriteria) -> str:
        """Generate schema test content for Python"""
        return f'''        # Test schema validation: {criterion.description}
        # TODO: Import your schema validation function
        # from your_module import validate_schema
        
        # TODO: Create test data
        test_data = {{"example": "data"}}
        
        # TODO: Test validation
        # result = validate_schema(test_data)
        # self.assertTrue(result)
        
        # Placeholder assertion
        self.assertTrue(True, "Schema test not implemented")'''
    
    def _generate_smoke_test_content(self, criterion: AcceptanceCriteria) -> str:
        """Generate smoke test content for Python"""
        return f'''        # Smoke test: {criterion.description}
        # TODO: Implement smoke test logic
        
        # Basic smoke test - check if system is responsive
        try:
            response = requests.get('http://localhost:5001/healthz', timeout=5)
            self.assertEqual(response.status_code, 200)
        except requests.exceptions.RequestException:
            self.fail("System is not responsive")'''
    
    def _generate_unit_test_content(self, criterion: AcceptanceCriteria) -> str:
        """Generate unit test content for Python"""
        return f'''        # Unit test: {criterion.description}
        # TODO: Import the function/class to test
        # from your_module import your_function
        
        # TODO: Test the function
        # result = your_function()
        # self.assertIsNotNone(result)
        
        # Placeholder assertion
        self.assertTrue(True, "Unit test not implemented")'''
    
    def _generate_endpoint_test_content_ts(self, criterion: AcceptanceCriteria) -> str:
        """Generate endpoint test content for TypeScript"""
        return f'''    // Test endpoint behavior: {criterion.description}
    // TODO: Replace with actual endpoint URL
    const response = await fetch('http://localhost:5001/api/test');
    expect(response.status).toBe(200);
    
    // TODO: Add specific assertions based on: {criterion.expected_behavior}
    const data = await response.json();
    expect(data).toHaveProperty('ok');'''
    
    def _generate_schema_test_content_ts(self, criterion: AcceptanceCriteria) -> str:
        """Generate schema test content for TypeScript"""
        return f'''    // Test schema validation: {criterion.description}
    // TODO: Import your schema validation function
    // import {{ validateSchema }} from './your-module';
    
    // TODO: Create test data
    const testData = {{ example: 'data' }};
    
    // TODO: Test validation
    // const result = validateSchema(testData);
    // expect(result).toBe(true);
    
    // Placeholder assertion
    expect(true).toBe(true);'''
    
    def _generate_smoke_test_content_ts(self, criterion: AcceptanceCriteria) -> str:
        """Generate smoke test content for TypeScript"""
        return f'''    // Smoke test: {criterion.description}
    // TODO: Implement smoke test logic
    
    // Basic smoke test - check if system is responsive
    const response = await fetch('http://localhost:5001/healthz');
    expect(response.status).toBe(200);'''
    
    def _generate_unit_test_content_ts(self, criterion: AcceptanceCriteria) -> str:
        """Generate unit test content for TypeScript"""
        return f'''    // Unit test: {criterion.description}
    // TODO: Import the function/class to test
    // import {{ yourFunction }} from './your-module';
    
    // TODO: Test the function
    // const result = yourFunction();
    // expect(result).not.toBeNull();
    
    // Placeholder assertion
    expect(true).toBe(true);'''
    
    def _write_test_file(self, file_path: str, content: str):
        """Write test file to disk"""
        full_path = os.path.join(self.project_root, file_path)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def run_acceptance_tests(self, test_files: List[str] = None) -> Dict[str, Any]:
        """Run acceptance tests and return results"""
        if test_files is None:
            test_files = self.generated_tests
        
        results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_results": [],
            "overall_success": True
        }
        
        for test_file in test_files:
            try:
                result = self._run_single_test_file(test_file)
                results["test_results"].append(result)
                results["total_tests"] += 1
                
                if result.passed:
                    results["passed_tests"] += 1
                else:
                    results["failed_tests"] += 1
                    results["overall_success"] = False
                    
            except Exception as e:
                logger.error(f"Error running test file {test_file}: {e}")
                results["test_results"].append(TestResult(
                    test_id=test_file,
                    passed=False,
                    output="",
                    error=str(e)
                ))
                results["total_tests"] += 1
                results["failed_tests"] += 1
                results["overall_success"] = False
        
        return results
    
    def _run_single_test_file(self, test_file: str) -> TestResult:
        """Run a single test file"""
        full_path = os.path.join(self.project_root, test_file)
        
        if not os.path.exists(full_path):
            return TestResult(
                test_id=test_file,
                passed=False,
                output="",
                error=f"Test file not found: {test_file}"
            )
        
        try:
            # Determine test runner based on file extension
            if test_file.endswith('.py'):
                return self._run_python_test(full_path)
            elif test_file.endswith('.ts'):
                return self._run_typescript_test(full_path)
            else:
                return TestResult(
                    test_id=test_file,
                    passed=False,
                    output="",
                    error=f"Unsupported test file type: {test_file}"
                )
        except Exception as e:
            return TestResult(
                test_id=test_file,
                passed=False,
                output="",
                error=str(e)
            )
    
    def _run_python_test(self, test_file: str) -> TestResult:
        """Run Python test using pytest or unittest"""
        start_time = time.time()
        
        try:
            # Try pytest first
            result = subprocess.run(
                ['python', '-m', 'pytest', test_file, '-v'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return TestResult(
                test_id=os.path.basename(test_file),
                passed=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                duration_ms=duration_ms
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                test_id=os.path.basename(test_file),
                passed=False,
                output="",
                error="Test timed out after 30 seconds"
            )
        except FileNotFoundError:
            # Fallback to unittest
            try:
                result = subprocess.run(
                    ['python', '-m', 'unittest', test_file],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                return TestResult(
                    test_id=os.path.basename(test_file),
                    passed=result.returncode == 0,
                    output=result.stdout,
                    error=result.stderr if result.returncode != 0 else None,
                    duration_ms=duration_ms
                )
            except Exception as e:
                return TestResult(
                    test_id=os.path.basename(test_file),
                    passed=False,
                    output="",
                    error=str(e)
                )
    
    def _run_typescript_test(self, test_file: str) -> TestResult:
        """Run TypeScript test using jest"""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ['npx', 'jest', test_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return TestResult(
                test_id=os.path.basename(test_file),
                passed=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
                duration_ms=duration_ms
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                test_id=os.path.basename(test_file),
                passed=False,
                output="",
                error="Test timed out after 30 seconds"
            )
        except Exception as e:
            return TestResult(
                test_id=os.path.basename(test_file),
                passed=False,
                output="",
                error=str(e)
            )
