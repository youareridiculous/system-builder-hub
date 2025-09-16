"""
LLM evaluation runner
"""
import os
import yaml
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from src.llm.providers import LLMProviderManager
from src.llm.prompt_library import PromptLibrary
from src.llm.schema import LLMRequest

logger = logging.getLogger(__name__)

class EvalRunner:
    """LLM evaluation runner"""
    
    def __init__(self):
        self.provider_manager = LLMProviderManager()
        self.prompt_library = PromptLibrary()
        self.goldens_dir = Path(__file__).parent / 'goldens'
        self.reports_dir = Path('instance/eval_reports')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def load_golden(self, file_path: Path) -> Dict[str, Any]:
        """Load golden test case from YAML"""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading golden {file_path}: {e}")
            raise
    
    def run_assertion(self, assertion: Dict[str, Any], response_text: str) -> Dict[str, Any]:
        """Run assertion against response"""
        assertion_type = assertion.get('type')
        value = assertion.get('value', '')
        
        if assertion_type == 'contains':
            passed = value.lower() in response_text.lower()
        elif assertion_type == 'not_contains':
            passed = value.lower() not in response_text.lower()
        elif assertion_type == 'regex':
            import re
            pattern = re.compile(value, re.IGNORECASE)
            passed = bool(pattern.search(response_text))
        elif assertion_type == 'json_schema':
            try:
                import jsonschema
                response_json = json.loads(response_text)
                jsonschema.validate(response_json, value)
                passed = True
            except Exception:
                passed = False
        else:
            passed = False
            logger.warning(f"Unknown assertion type: {assertion_type}")
        
        return {
            'type': assertion_type,
            'value': value,
            'passed': passed
        }
    
    def run_golden(self, golden_data: Dict[str, Any], provider_name: str = 'local-stub') -> Dict[str, Any]:
        """Run a single golden test"""
        try:
            slug = golden_data['slug']
            guided_input = golden_data['guided_input']
            assertions = golden_data.get('assertions', [])
            
            # Get provider
            provider = self.provider_manager.get_provider(provider_name)
            
            # Render prompt
            messages = self.prompt_library.render(slug, guided_input, 'system')
            
            # Create request
            request = LLMRequest(
                model=provider.default_model,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=500
            )
            
            # Get response
            start_time = time.time()
            response = provider.complete(request)
            latency = time.time() - start_time
            
            # Run assertions
            assertion_results = []
            all_passed = True
            
            for assertion in assertions:
                result = self.run_assertion(assertion, response.text)
                assertion_results.append(result)
                if not result['passed']:
                    all_passed = False
            
            return {
                'slug': slug,
                'description': golden_data.get('description', ''),
                'provider': provider_name,
                'model': provider.default_model,
                'response_text': response.text,
                'usage': response.usage.to_dict(),
                'latency': latency,
                'assertions': assertion_results,
                'passed': all_passed,
                'total_assertions': len(assertions),
                'passed_assertions': sum(1 for r in assertion_results if r['passed'])
            }
            
        except Exception as e:
            logger.error(f"Error running golden {slug}: {e}")
            return {
                'slug': slug,
                'description': golden_data.get('description', ''),
                'provider': provider_name,
                'error': str(e),
                'passed': False
            }
    
    def run_all_goldens(self, provider_name: str = 'local-stub') -> Dict[str, Any]:
        """Run all golden tests"""
        try:
            golden_files = list(self.goldens_dir.glob('*.yaml'))
            
            if not golden_files:
                logger.warning("No golden test files found")
                return {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'results': []
                }
            
            results = []
            total = len(golden_files)
            passed = 0
            failed = 0
            
            for golden_file in golden_files:
                logger.info(f"Running golden: {golden_file.name}")
                
                golden_data = self.load_golden(golden_file)
                result = self.run_golden(golden_data, provider_name)
                
                results.append(result)
                
                if result['passed']:
                    passed += 1
                else:
                    failed += 1
            
            return {
                'total': total,
                'passed': passed,
                'failed': failed,
                'results': results,
                'timestamp': datetime.utcnow().isoformat(),
                'provider': provider_name
            }
            
        except Exception as e:
            logger.error(f"Error running all goldens: {e}")
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'results': [],
                'error': str(e)
            }
    
    def generate_junit_xml(self, results: Dict[str, Any]) -> str:
        """Generate JUnit XML report"""
        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_parts.append('<testsuites>')
        xml_parts.append(f'<testsuite name="LLM Golden Tests" tests="{results["total"]}" failures="{results["failed"]}">')
        
        for result in results['results']:
            test_name = result['slug']
            if result['passed']:
                xml_parts.append(f'<testcase name="{test_name}" classname="LLMGoldenTest"/>')
            else:
                xml_parts.append(f'<testcase name="{test_name}" classname="LLMGoldenTest">')
                xml_parts.append('<failure>')
                if 'error' in result:
                    xml_parts.append(f'Error: {result["error"]}')
                else:
                    failed_assertions = [a for a in result['assertions'] if not a['passed']]
                    xml_parts.append(f'Failed assertions: {failed_assertions}')
                xml_parts.append('</failure>')
                xml_parts.append('</testcase>')
        
        xml_parts.append('</testsuite>')
        xml_parts.append('</testsuites>')
        
        return '\n'.join(xml_parts)
    
    def generate_markdown_summary(self, results: Dict[str, Any]) -> str:
        """Generate markdown summary report"""
        md_parts = []
        
        # Header
        md_parts.append('# LLM Golden Test Results')
        md_parts.append('')
        md_parts.append(f'**Generated:** {results.get("timestamp", "Unknown")}')
        md_parts.append(f'**Provider:** {results.get("provider", "Unknown")}')
        md_parts.append('')
        
        # Summary
        total = results['total']
        passed = results['passed']
        failed = results['failed']
        
        md_parts.append('## Summary')
        md_parts.append('')
        md_parts.append(f'- **Total Tests:** {total}')
        md_parts.append(f'- **Passed:** {passed}')
        md_parts.append(f'- **Failed:** {failed}')
        md_parts.append(f'- **Success Rate:** {(passed/total*100):.1f}%' if total > 0 else '- **Success Rate:** 0%')
        md_parts.append('')
        
        # Results
        md_parts.append('## Test Results')
        md_parts.append('')
        
        for result in results['results']:
            status = '✅ PASS' if result['passed'] else '❌ FAIL'
            md_parts.append(f'### {result["slug"]} {status}')
            md_parts.append('')
            md_parts.append(f'**Description:** {result.get("description", "No description")}')
            md_parts.append('')
            
            if 'error' in result:
                md_parts.append(f'**Error:** {result["error"]}')
                md_parts.append('')
            else:
                md_parts.append(f'**Provider:** {result.get("provider", "Unknown")}')
                md_parts.append(f'**Model:** {result.get("model", "Unknown")}')
                md_parts.append(f'**Latency:** {result.get("latency", 0):.2f}s')
                md_parts.append(f'**Tokens:** {result.get("usage", {}).get("total_tokens", 0)}')
                md_parts.append('')
                
                # Assertions
                if 'assertions' in result:
                    md_parts.append('**Assertions:**')
                    md_parts.append('')
                    for assertion in result['assertions']:
                        status = '✅' if assertion['passed'] else '❌'
                        md_parts.append(f'- {status} {assertion["type"]}: `{assertion["value"]}`')
                    md_parts.append('')
                
                # Response preview
                response_text = result.get('response_text', '')
                if response_text:
                    preview = response_text[:200] + '...' if len(response_text) > 200 else response_text
                    md_parts.append('**Response Preview:**')
                    md_parts.append('```')
                    md_parts.append(preview)
                    md_parts.append('```')
                    md_parts.append('')
        
        return '\n'.join(md_parts)
    
    def save_reports(self, results: Dict[str, Any]):
        """Save evaluation reports"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Save JUnit XML
            junit_xml = self.generate_junit_xml(results)
            junit_path = self.reports_dir / f'junit_{timestamp}.xml'
            with open(junit_path, 'w') as f:
                f.write(junit_xml)
            
            # Save markdown summary
            markdown_summary = self.generate_markdown_summary(results)
            markdown_path = self.reports_dir / f'summary_{timestamp}.md'
            with open(markdown_path, 'w') as f:
                f.write(markdown_summary)
            
            # Save JSON results
            json_path = self.reports_dir / f'results_{timestamp}.json'
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Reports saved to {self.reports_dir}")
            return {
                'junit_xml': str(junit_path),
                'markdown_summary': str(markdown_path),
                'json_results': str(json_path)
            }
            
        except Exception as e:
            logger.error(f"Error saving reports: {e}")
            raise

def run_eval(provider_name: str = 'local-stub') -> Dict[str, Any]:
    """Run evaluation and return results"""
    runner = EvalRunner()
    results = runner.run_all_goldens(provider_name)
    report_paths = runner.save_reports(results)
    
    return {
        'results': results,
        'reports': report_paths
    }
