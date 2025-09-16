"""
Tests for SBH Meta-Builder functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch
from src.meta_builder.models import (
    ScaffoldSession, ScaffoldPlan, PatternLibrary, TemplateLink,
    PromptTemplate, EvaluationCase, PlanArtifact
)
from src.meta_builder.planner import ScaffoldPlanner, PlanningContext
from src.meta_builder.implementer import ScaffoldImplementer, BuildContext
from src.meta_builder.evaluator import ScaffoldEvaluator


class TestScaffoldPlanner:
    """Test scaffold planning functionality."""
    
    def test_plan_scaffold_basic(self):
        """Test basic scaffold planning."""
        llm_mock = Mock()
        planner = ScaffoldPlanner(llm_mock)
        
        context = PlanningContext(
            goal_text="Build a simple CRUD app for managing users",
            tenant_id="test-tenant",
            user_id="test-user"
        )
        
        result = planner.plan_scaffold(context)
        
        assert result.plan_json is not None
        assert 'entities' in result.plan_json
        assert 'api_endpoints' in result.plan_json
        assert 'ui_pages' in result.plan_json
        assert result.rationale is not None
        assert result.scorecard is not None
    
    def test_plan_scaffold_with_patterns(self):
        """Test scaffold planning with specific patterns."""
        llm_mock = Mock()
        planner = ScaffoldPlanner(llm_mock)
        
        context = PlanningContext(
            goal_text="Build a helpdesk system",
            pattern_slugs=['helpdesk', 'ai-rag-app'],
            template_slugs=['flagship-crm'],
            tenant_id="test-tenant",
            user_id="test-user"
        )
        
        result = planner.plan_scaffold(context)
        
        assert result.plan_json is not None
        assert 'helpdesk' in str(result.plan_json).lower()
        assert result.risks is not None
    
    def test_plan_scaffold_composition(self):
        """Test scaffold planning with template composition."""
        llm_mock = Mock()
        planner = ScaffoldPlanner(llm_mock)
        
        context = PlanningContext(
            goal_text="Build a marketplace with payments",
            pattern_slugs=['marketplace'],
            template_slugs=['flagship-crm', 'stripe-payments'],
            composition_rules={
                'merge_strategy': 'compose',
                'resolve_conflicts': True
            },
            tenant_id="test-tenant",
            user_id="test-user"
        )
        
        result = planner.plan_scaffold(context)
        
        assert result.plan_json is not None
        assert result.plan_json.get('payments') is True


class TestScaffoldImplementer:
    """Test scaffold implementation functionality."""
    
    def test_build_scaffold_success(self):
        """Test successful scaffold building."""
        tool_kernel_mock = Mock()
        implementer = ScaffoldImplementer(tool_kernel_mock)
        
        builder_state = {
            'entities': ['user', 'product'],
            'api_endpoints': [
                {'method': 'GET', 'path': '/api/users'},
                {'method': 'POST', 'path': '/api/users'}
            ],
            'ui_pages': ['users', 'products'],
            'auth': True,
            'storage': False
        }
        
        context = BuildContext(
            session_id="test-session",
            plan_id="test-plan",
            builder_state=builder_state,
            export_config={'zip': True},
            run_tests=True
        )
        
        result = implementer.build_scaffold(context)
        
        assert result.success is True
        assert len(result.artifacts) > 0
        assert len(result.preview_urls) > 0
        assert result.test_results is not None
    
    def test_build_scaffold_with_migrations(self):
        """Test scaffold building with database migrations."""
        tool_kernel_mock = Mock()
        implementer = ScaffoldImplementer(tool_kernel_mock)
        
        builder_state = {
            'models': [
                {
                    'name': 'User',
                    'fields': [
                        {'name': 'id', 'type': 'uuid'},
                        {'name': 'email', 'type': 'string'},
                        {'name': 'name', 'type': 'string'},
                        {'name': 'created_at', 'type': 'datetime'}
                    ]
                }
            ],
            'auth': True
        }
        
        context = BuildContext(
            session_id="test-session",
            plan_id="test-plan",
            builder_state=builder_state
        )
        
        result = implementer.build_scaffold(context)
        
        assert result.success is True
        # Check that migrations were generated
        assert any('migration' in str(artifact) for artifact in result.artifacts)


class TestScaffoldEvaluator:
    """Test scaffold evaluation functionality."""
    
    def test_evaluate_case_success(self):
        """Test successful case evaluation."""
        llm_mock = Mock()
        evaluator = ScaffoldEvaluator(llm_mock)
        
        case = Mock()
        case.id = "test-case"
        case.name = "Test Case"
        case.golden_prompt = "Build a simple CRUD app"
        case.expected_assertions = {
            'entities': ['user', 'product'],
            'api_endpoints': {'count': 4},
            'features': {'auth': True}
        }
        
        result = evaluator.evaluate_case(case)
        
        assert result['case_id'] == "test-case"
        assert result['status'] in ['pass', 'fail', 'partial']
        assert result['score'] >= 0
        assert result['score'] <= 100
        assert 'details' in result
    
    def test_evaluate_case_with_entity_assertions(self):
        """Test case evaluation with entity assertions."""
        llm_mock = Mock()
        evaluator = ScaffoldEvaluator(llm_mock)
        
        case = Mock()
        case.id = "test-case"
        case.name = "Test Case"
        case.golden_prompt = "Build a helpdesk system"
        case.expected_assertions = {
            'entities': ['ticket', 'user', 'category']
        }
        
        result = evaluator.evaluate_case(case)
        
        assert result['status'] in ['pass', 'fail', 'partial']
        assert 'entities' in result['details']
    
    def test_evaluate_case_with_feature_assertions(self):
        """Test case evaluation with feature assertions."""
        llm_mock = Mock()
        evaluator = ScaffoldEvaluator(llm_mock)
        
        case = Mock()
        case.id = "test-case"
        case.name = "Test Case"
        case.golden_prompt = "Build an e-commerce app"
        case.expected_assertions = {
            'features': {
                'auth': True,
                'payments': True,
                'storage': False
            }
        }
        
        result = evaluator.evaluate_case(case)
        
        assert result['status'] in ['pass', 'fail', 'partial']
        assert any('feature_' in key for key in result['details'].keys())


class TestMetaBuilderAPI:
    """Test meta-builder API endpoints."""
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def auth_headers(self):
        """Create authenticated headers."""
        return {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
        }
    
    def test_plan_scaffold_endpoint(self, client, auth_headers):
        """Test scaffold planning endpoint."""
        data = {
            'goal_text': 'Build a simple CRUD app for users',
            'mode': 'freeform',
            'options': {
                'llm': True,
                'dry_run': False
            }
        }
        
        response = client.post(
            '/api/meta/scaffold/plan',
            json=data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        result = response.get_json()
        assert 'data' in result
        assert result['data']['type'] == 'scaffold_plan'
    
    def test_build_scaffold_endpoint(self, client, auth_headers):
        """Test scaffold building endpoint."""
        # First create a plan
        plan_data = {
            'goal_text': 'Build a simple CRUD app',
            'mode': 'freeform'
        }
        
        plan_response = client.post(
            '/api/meta/scaffold/plan',
            json=plan_data,
            headers=auth_headers
        )
        
        assert plan_response.status_code == 201
        plan_result = plan_response.get_json()
        session_id = plan_result['data']['attributes']['session_id']
        plan_id = plan_result['data']['id']
        
        # Then build the scaffold
        build_data = {
            'session_id': session_id,
            'plan_id': plan_id,
            'export': {'zip': True},
            'run_tests': True
        }
        
        build_response = client.post(
            '/api/meta/scaffold/build',
            json=build_data,
            headers=auth_headers
        )
        
        assert build_response.status_code == 200
        result = build_response.get_json()
        assert 'data' in result
        assert result['data']['type'] == 'scaffold_build'
    
    def test_list_patterns_endpoint(self, client, auth_headers):
        """Test patterns listing endpoint."""
        response = client.get(
            '/api/meta/patterns',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.get_json()
        assert 'data' in result
        assert isinstance(result['data'], list)
    
    def test_list_templates_endpoint(self, client, auth_headers):
        """Test templates listing endpoint."""
        response = client.get(
            '/api/meta/templates',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.get_json()
        assert 'data' in result
        assert isinstance(result['data'], list)
    
    def test_run_evaluation_endpoint(self, client, auth_headers):
        """Test evaluation running endpoint."""
        response = client.post(
            '/api/meta/eval/run',
            headers=auth_headers
        )
        
        # Should return 404 if no evaluation cases exist
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            result = response.get_json()
            assert 'data' in result
            assert result['data']['type'] == 'evaluation_results'


class TestMetaBuilderModels:
    """Test meta-builder data models."""
    
    def test_scaffold_session_creation(self):
        """Test scaffold session model creation."""
        session = ScaffoldSession(
            tenant_id="test-tenant",
            user_id="test-user",
            goal_text="Build a simple app",
            mode="guided",
            status="draft"
        )
        
        assert session.tenant_id == "test-tenant"
        assert session.user_id == "test-user"
        assert session.goal_text == "Build a simple app"
        assert session.mode == "guided"
        assert session.status == "draft"
    
    def test_scaffold_plan_creation(self):
        """Test scaffold plan model creation."""
        plan = ScaffoldPlan(
            tenant_id="test-tenant",
            session_id="test-session",
            version=1,
            planner_kind="llm",
            plan_json={'entities': ['user']},
            rationale="Simple CRUD app",
            scorecard_json={'score': 85}
        )
        
        assert plan.tenant_id == "test-tenant"
        assert plan.session_id == "test-session"
        assert plan.version == 1
        assert plan.planner_kind == "llm"
        assert plan.plan_json['entities'] == ['user']
        assert plan.rationale == "Simple CRUD app"
    
    def test_pattern_library_creation(self):
        """Test pattern library model creation."""
        pattern = PatternLibrary(
            tenant_id="test-tenant",
            slug="crud-app",
            name="CRUD Application",
            description="Basic CRUD app pattern",
            tags=["crud", "api"],
            inputs_schema={'entities': {'type': 'array'}},
            outputs_schema={'models': {'type': 'array'}},
            compose_points=["database", "api"]
        )
        
        assert pattern.tenant_id == "test-tenant"
        assert pattern.slug == "crud-app"
        assert pattern.name == "CRUD Application"
        assert pattern.tags == ["crud", "api"]
        assert pattern.compose_points == ["database", "api"]
    
    def test_evaluation_case_creation(self):
        """Test evaluation case model creation."""
        case = EvaluationCase(
            tenant_id="test-tenant",
            name="Test Case",
            description="Test evaluation case",
            golden_prompt="Build a simple app",
            expected_assertions={
                'entities': ['user'],
                'features': {'auth': True}
            },
            pattern_slugs=["crud-app"],
            template_slugs=["basic-auth"]
        )
        
        assert case.tenant_id == "test-tenant"
        assert case.name == "Test Case"
        assert case.golden_prompt == "Build a simple app"
        assert case.expected_assertions['entities'] == ['user']
        assert case.pattern_slugs == ["crud-app"]
        assert case.template_slugs == ["basic-auth"]


if __name__ == '__main__':
    pytest.main([__file__])
