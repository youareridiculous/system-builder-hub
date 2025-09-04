"""
SBH Meta-Builder Evaluator Service
Handles evaluation of scaffold plans and golden test cases.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.meta_builder.models import EvaluationCase, ScaffoldEvaluation
from src.utils.audit import audit_log
from src.utils.multi_tenancy import get_current_tenant_id

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of an evaluation case."""
    case_id: str
    status: str  # 'pass', 'fail', 'error'
    score: float
    details: Dict[str, Any]
    errors: Optional[List[str]] = None
    execution_time: Optional[float] = None
    memory_usage: Optional[float] = None


class ScaffoldEvaluator:
    """Evaluates scaffold plans against golden test cases."""
    
    def __init__(self, llm_orchestration):
        self.llm = llm_orchestration
        
    def evaluate_case(self, case: EvaluationCase) -> Dict[str, Any]:
        """Evaluate a single test case."""
        
        start_time = time.time()
        
        try:
            logger.info(f"Evaluating case: {case.name}")
            
            # Parse the golden prompt
            prompt = case.golden_prompt
            
            # Run the prompt through the planner
            # TODO: Integrate with actual planner
            plan_result = self._run_planner(prompt)
            
            # Evaluate against expected assertions
            evaluation = self._evaluate_assertions(
                plan_result, case.expected_assertions
            )
            
            execution_time = time.time() - start_time
            
            return {
                'case_id': str(case.id),
                'case_name': case.name,
                'status': evaluation['status'],
                'score': evaluation['score'],
                'details': evaluation['details'],
                'errors': evaluation.get('errors'),
                'execution_time': execution_time
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed for case {case.name}: {e}")
            return {
                'case_id': str(case.id),
                'case_name': case.name,
                'status': 'error',
                'score': 0.0,
                'details': {},
                'errors': [str(e)],
                'execution_time': time.time() - start_time
            }
    
    def _run_planner(self, prompt: str) -> Dict[str, Any]:
        """Run the planner with a golden prompt."""
        
        # TODO: Integrate with actual planner
        # For now, return a mock result
        
        return {
            'entities': ['user', 'product', 'order'],
            'api_endpoints': [
                {'method': 'GET', 'path': '/api/users'},
                {'method': 'POST', 'path': '/api/users'},
                {'method': 'GET', 'path': '/api/products'},
                {'method': 'POST', 'path': '/api/products'},
                {'method': 'GET', 'path': '/api/orders'},
                {'method': 'POST', 'path': '/api/orders'}
            ],
            'ui_pages': ['users', 'products', 'orders'],
            'auth': True,
            'storage': True
        }
    
    def _evaluate_assertions(
        self, 
        plan_result: Dict[str, Any], 
        expected_assertions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate plan result against expected assertions."""
        
        score = 0.0
        total_checks = 0
        passed_checks = 0
        details = {}
        errors = []
        
        # Check entity assertions
        if 'entities' in expected_assertions:
            total_checks += 1
            expected_entities = expected_assertions['entities']
            actual_entities = plan_result.get('entities', [])
            
            if isinstance(expected_entities, list):
                # Check if all expected entities are present
                missing_entities = set(expected_entities) - set(actual_entities)
                if not missing_entities:
                    passed_checks += 1
                    details['entities'] = 'pass'
                else:
                    details['entities'] = f'fail: missing {missing_entities}'
                    errors.append(f'Missing entities: {missing_entities}')
            elif isinstance(expected_entities, dict):
                # Check entity count
                expected_count = expected_entities.get('count', 0)
                actual_count = len(actual_entities)
                if actual_count >= expected_count:
                    passed_checks += 1
                    details['entities'] = f'pass: {actual_count} >= {expected_count}'
                else:
                    details['entities'] = f'fail: {actual_count} < {expected_count}'
                    errors.append(f'Insufficient entities: {actual_count} < {expected_count}')
        
        # Check API endpoint assertions
        if 'api_endpoints' in expected_assertions:
            total_checks += 1
            expected_endpoints = expected_assertions['api_endpoints']
            actual_endpoints = plan_result.get('api_endpoints', [])
            
            if isinstance(expected_endpoints, dict):
                expected_count = expected_endpoints.get('count', 0)
                actual_count = len(actual_endpoints)
                if actual_count >= expected_count:
                    passed_checks += 1
                    details['api_endpoints'] = f'pass: {actual_count} >= {expected_count}'
                else:
                    details['api_endpoints'] = f'fail: {actual_count} < {expected_count}'
                    errors.append(f'Insufficient API endpoints: {actual_count} < {expected_count}')
        
        # Check UI page assertions
        if 'ui_pages' in expected_assertions:
            total_checks += 1
            expected_pages = expected_assertions['ui_pages']
            actual_pages = plan_result.get('ui_pages', [])
            
            if isinstance(expected_pages, list):
                missing_pages = set(expected_pages) - set(actual_pages)
                if not missing_pages:
                    passed_checks += 1
                    details['ui_pages'] = 'pass'
                else:
                    details['ui_pages'] = f'fail: missing {missing_pages}'
                    errors.append(f'Missing UI pages: {missing_pages}')
        
        # Check feature assertions
        if 'features' in expected_assertions:
            expected_features = expected_assertions['features']
            for feature, required in expected_features.items():
                total_checks += 1
                actual_value = plan_result.get(feature, False)
                if actual_value == required:
                    passed_checks += 1
                    details[f'feature_{feature}'] = 'pass'
                else:
                    details[f'feature_{feature}'] = f'fail: expected {required}, got {actual_value}'
                    errors.append(f'Feature {feature}: expected {required}, got {actual_value}')
        
        # Calculate score
        if total_checks > 0:
            score = (passed_checks / total_checks) * 100
        
        # Determine status
        if score >= 80:
            status = 'pass'
        elif score >= 60:
            status = 'partial'
        else:
            status = 'fail'
        
        return {
            'status': status,
            'score': score,
            'details': details,
            'errors': errors if errors else None
        }
    
    def run_batch_evaluation(self, cases: List[EvaluationCase]) -> List[Dict[str, Any]]:
        """Run evaluation on multiple cases."""
        
        results = []
        
        for case in cases:
            result = self.evaluate_case(case)
            results.append(result)
            
            # Log progress
            logger.info(f"Case {case.name}: {result['status']} ({result['score']:.1f}%)")
        
        return results
    
    def generate_evaluation_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a comprehensive evaluation report."""
        
        total_cases = len(results)
        passed_cases = len([r for r in results if r['status'] == 'pass'])
        failed_cases = len([r for r in results if r['status'] == 'fail'])
        error_cases = len([r for r in results if r['status'] == 'error'])
        partial_cases = len([r for r in results if r['status'] == 'partial'])
        
        avg_score = sum(r['score'] for r in results) / total_cases if total_cases > 0 else 0
        avg_execution_time = sum(r.get('execution_time', 0) for r in results) / total_cases if total_cases > 0 else 0
        
        # Group by pattern/template
        pattern_results = {}
        for result in results:
            # TODO: Extract pattern/template from case
            pattern = 'unknown'
            if pattern not in pattern_results:
                pattern_results[pattern] = []
            pattern_results[pattern].append(result)
        
        # Calculate pattern-specific metrics
        pattern_metrics = {}
        for pattern, pattern_cases in pattern_results.items():
            pattern_total = len(pattern_cases)
            pattern_passed = len([r for r in pattern_cases if r['status'] == 'pass'])
            pattern_score = sum(r['score'] for r in pattern_cases) / pattern_total if pattern_total > 0 else 0
            
            pattern_metrics[pattern] = {
                'total_cases': pattern_total,
                'passed_cases': pattern_passed,
                'pass_rate': (pattern_passed / pattern_total * 100) if pattern_total > 0 else 0,
                'avg_score': pattern_score
            }
        
        return {
            'summary': {
                'total_cases': total_cases,
                'passed': passed_cases,
                'failed': failed_cases,
                'errors': error_cases,
                'partial': partial_cases,
                'pass_rate': (passed_cases / total_cases * 100) if total_cases > 0 else 0,
                'avg_score': avg_score,
                'avg_execution_time': avg_execution_time
            },
            'pattern_metrics': pattern_metrics,
            'detailed_results': results
        }
