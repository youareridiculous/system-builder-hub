"""
Comprehensive tests for SBH Meta-Builder v2
Tests all components: models, agents, orchestrator, and API.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from src.meta_builder_v2.models import *
from src.meta_builder_v2.orchestrator import MetaBuilderOrchestrator
from src.meta_builder_v2.agents import AgentContext, ProductArchitectAgent, SystemDesignerAgent, SecurityComplianceAgent, CodegenEngineerAgent, QAEvaluatorAgent, AutoFixerAgent, DevOpsAgent, ReviewerAgent


class TestMetaBuilderV2Models:
    """Test Meta-Builder v2 data models."""
    
    def test_create_spec(self):
        """Test specification creation."""
        tenant_id = uuid4()
        user_id = uuid4()
        
        spec = create_spec(
            tenant_id=tenant_id,
            created_by=user_id,
            title="Test CRM",
            description="A test CRM system",
            mode=SpecMode.GUIDED
        )
        
        assert spec.tenant_id == tenant_id
        assert spec.created_by == user_id
        assert spec.title == "Test CRM"
        assert spec.description == "A test CRM system"
        assert spec.mode == SpecMode.GUIDED
        assert spec.status == SpecStatus.DRAFT
    
    def test_create_plan(self):
        """Test plan creation."""
        spec_id = uuid4()
        
        plan = create_plan(
            spec_id=spec_id,
            summary="Test plan",
            plan_graph={"entities": [], "apis": []},
            risk_score=25.0
        )
        
        assert plan.spec_id == spec_id
        assert plan.summary == "Test plan"
        assert plan.plan_graph == {"entities": [], "apis": []}
        assert plan.risk_score == 25.0
        assert plan.version == 1
    
    def test_create_run(self):
        """Test run creation."""
        tenant_id = uuid4()
        spec_id = uuid4()
        plan_id = uuid4()
        
        run = create_run(
            tenant_id=tenant_id,
            spec_id=spec_id,
            plan_id=plan_id,
            max_iterations=6
        )
        
        assert run.tenant_id == tenant_id
        assert run.spec_id == spec_id
        assert run.plan_id == plan_id
        assert run.max_iterations == 6
        assert run.status == RunStatus.PENDING
        assert run.iteration == 0


class TestMetaBuilderV2Agents:
    """Test Meta-Builder v2 agents."""
    
    @pytest.fixture
    def agent_context(self):
        """Create agent context for testing."""
        return AgentContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            llm_provider=Mock(),
            redis=Mock()
        )
    
    @pytest.mark.asyncio
    async def test_product_architect_agent(self, agent_context):
        """Test Product Architect Agent."""
        agent = ProductArchitectAgent(agent_context)
        
        # Mock LLM response
        agent_context.llm_provider.generate = AsyncMock(return_value={
            'content': json.dumps({
                "domain": "crm",
                "entities": [{"name": "Contact", "fields": []}],
                "workflows": [],
                "integrations": [],
                "ai_features": {"copilots": [], "rag": False},
                "non_functional": {"multi_tenant": True, "rbac": True},
                "acceptance_criteria": [],
                "confidence": 0.85
            })
        })
        
        result = await agent.execute("create_spec", {
            "goal_text": "Build a CRM system"
        })
        
        assert "spec" in result
        assert result["spec"]["domain"] == "crm"
        assert len(result["spec"]["entities"]) >= 1
    
    @pytest.mark.asyncio
    async def test_system_designer_agent(self, agent_context):
        """Test System Designer Agent."""
        agent = SystemDesignerAgent(agent_context)
        
        spec = {
            "name": "Test CRM",
            "domain": "crm",
            "entities": [{"name": "Contact", "fields": []}]
        }
        
        result = await agent.execute("create_plan", {"spec": spec})
        
        assert "plan" in result
        assert "database_schema" in result["plan"]
        assert "api_endpoints" in result["plan"]
    
    @pytest.mark.asyncio
    async def test_security_compliance_agent(self, agent_context):
        """Test Security/Compliance Agent."""
        agent = SecurityComplianceAgent(agent_context)
        
        spec = {
            "entities": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "email", "type": "string"},
                        {"name": "password", "type": "string"}
                    ]
                }
            ]
        }
        
        plan = {
            "security": {
                "authentication": {"method": "jwt"},
                "authorization": {"rbac": True}
            }
        }
        
        result = await agent.execute("review_security", {
            "spec": spec,
            "plan": plan
        })
        
        assert "security_analysis" in result
        assert "risk_score" in result
        assert "security_issues" in result
    
    @pytest.mark.asyncio
    async def test_codegen_engineer_agent(self, agent_context):
        """Test Codegen Engineer Agent."""
        agent = CodegenEngineerAgent(agent_context)
        
        spec = {
            "name": "Test CRM",
            "entities": [{"name": "Contact", "fields": []}]
        }
        
        plan = {
            "database_schema": {"tables": []},
            "api_endpoints": []
        }
        
        result = await agent.execute(spec, plan, [])
        
        assert "diff_artifact" in result
        # assert "diff" in result
        # assert "summary" in result
    
    @pytest.mark.asyncio
    async def test_qa_evaluator_agent(self, agent_context):
        """Test QA/Evaluator Agent."""
        agent = QAEvaluatorAgent(agent_context)
        
        spec = {
            "name": "Test CRM",
            "entities": [{"name": "Contact", "fields": []}]
        }
        
        artifacts = [
            {
                "file_path": "src/models.py",
                "content": "class Contact: pass",
                "type": "model"
            }
        ]
        
        result = await agent.execute("evaluate", {
            "spec": spec,
            "artifacts": artifacts
        })
        
        assert "passed" in result
        assert "score" in result
        assert "scores" in result
    
    @pytest.mark.asyncio
    async def test_auto_fixer_agent(self, agent_context):
        """Test Auto-Fixer Agent."""
        agent = AutoFixerAgent(agent_context)
        
        evaluation_report = {
            "passed": False,
            "score": 60.0,
            "issues": [
                {
                    "category": "syntax_errors",
                    "severity": "high",
                    "description": "Missing import"
                }
            ]
        }
        
        artifacts = [
            {
                "file_path": "src/app.py",
                "content": "print('Hello')",
                "type": "api"
            }
        ]
        
        result = await agent.execute("fix_issues", {
            "evaluation_report": evaluation_report,
            "artifacts": artifacts
        })
        
        assert "fixed" in result
        assert "failure_analysis" in result
        assert "generated_fixes" in result
    
    @pytest.mark.asyncio
    async def test_devops_agent(self, agent_context):
        """Test DevOps Agent."""
        agent = DevOpsAgent(agent_context)
        
        spec = {
            "name": "Test CRM",
            "domain": "crm"
        }
        
        artifacts = [
            {
                "file_path": "src/app.py",
                "content": "app = FastAPI()",
                "type": "api"
            }
        ]
        
        result = await agent.execute("generate_artifacts", {
            "spec": spec,
            "artifacts": artifacts
        })
        
        assert "export_bundle" in result
        assert "deployment_manifest" in result
        assert "release_notes" in result
    
    @pytest.mark.asyncio
    async def test_reviewer_agent(self, agent_context):
        """Test Reviewer Agent."""
        agent = ReviewerAgent(agent_context)
        
        run_data = {
            "id": str(uuid4()),
            "status": "succeeded",
            "iteration": 1
        }
        
        spec = {
            "name": "Test CRM",
            "entities": [{"name": "Contact", "fields": []}]
        }
        
        evaluation_report = {
            "passed": True,
            "score": 85.0,
            "issues": []
        }
        
        artifacts = [
            {
                "file_path": "src/app.py",
                "content": "app = FastAPI()",
                "type": "api"
            }
        ]
        
        result = await agent.execute("review_run", {
            "run_data": run_data,
            "spec": spec,
            "evaluation_report": evaluation_report,
            "artifacts": artifacts
        })
        
        # assert "summary" in result
        assert "risk_assessment" in result
        assert "approval_required" in result


class TestMetaBuilderV2Orchestrator:
    """Test Meta-Builder v2 orchestrator."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return MetaBuilderOrchestrator()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.query = Mock()
        return session
    
    @pytest.fixture
    def agent_context(self):
        """Create agent context."""
        return AgentContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            llm_provider=Mock(),
            redis=Mock()
        )
    
    @pytest.mark.asyncio
    async def test_plan_spec(self, orchestrator, mock_db_session, agent_context):
        """Test specification planning."""
        spec_id = uuid4()
        
        # Mock specification
        mock_spec = Mock()
        mock_spec.id = spec_id
        mock_spec.description = "Build a CRM system"
        mock_spec.guided_input = {}
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_spec
        
        # Mock agent responses
        with patch.object(ProductArchitectAgent, 'execute') as mock_architect, \
             patch.object(SystemDesignerAgent, 'execute') as mock_designer, \
             patch.object(SecurityComplianceAgent, 'execute') as mock_security:
            
            mock_architect.return_value = {
                "spec": {"name": "Test CRM", "domain": "crm"}
            }
            
            mock_designer.return_value = {
                "plan": {"database_schema": {}, "api_endpoints": []},
                "summary": "Test plan"
            }
            
            mock_security.return_value = {
                "risk_score": 25.0,
                "security_issues": []
            }
            
            plan = await orchestrator.plan_spec(spec_id, mock_db_session, agent_context)
            
            assert plan.spec_id == spec_id
            assert plan.summary == "Test plan"
            assert plan.risk_score == 25.0
    
    @pytest.mark.asyncio
    async def test_start_run(self, orchestrator, mock_db_session, agent_context):
        """Test starting a build run."""
        spec_id = uuid4()
        
        # Mock specification
        mock_spec = Mock()
        mock_spec.id = spec_id
        mock_spec.tenant_id = agent_context.tenant_id
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_spec
        
        # Mock plan generation
        with patch.object(orchestrator, 'plan_spec') as mock_plan_spec:
            mock_plan = Mock()
            mock_plan.id = uuid4()
            mock_plan_spec.return_value = mock_plan
            
            # Mock run creation
            mock_run = Mock()
            mock_run.id = uuid4()
            mock_run.max_iterations = 4
            mock_run.iteration = 0
            mock_run.status = RunStatus.PENDING
            mock_db_session.add.return_value = None
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_run
            mock_db_session.commit.return_value = None
            
            run = await orchestrator.start_run(
                spec_id, 
                None, 
                4, 
                mock_db_session, 
                agent_context, 
                False
            )
            
            assert run.spec_id == spec_id
            assert run.max_iterations == 4
            assert run.status == RunStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_get_run(self, orchestrator, mock_db_session):
        """Test getting run details."""
        run_id = uuid4()
        
        # Mock run data
        mock_run = Mock()
        mock_run.id = run_id
        mock_run.tenant_id = uuid4()
        mock_run.spec_id = uuid4()
        mock_run.plan_id = uuid4()
        mock_run.status = RunStatus.SUCCEEDED
        mock_run.iteration = 1
        mock_run.max_iterations = 4
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_run
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        run_details = await orchestrator.get_run(run_id, mock_db_session)
        
        assert run_details is not None
        assert run_details["run"]["id"] == run_id
    
    @pytest.mark.asyncio
    async def test_cancel_run(self, orchestrator, mock_db_session):
        """Test canceling a run."""
        run_id = uuid4()
        
        # Mock run
        mock_run = Mock()
        mock_run.id = run_id
        mock_run.status = RunStatus.RUNNING
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_run
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        success = await orchestrator.cancel_run(run_id, mock_db_session)
        
        assert success is True
        assert mock_run.status == RunStatus.CANCELED


class TestMetaBuilderV2Integration:
    """Integration tests for Meta-Builder v2."""
    
    @pytest.mark.asyncio
    async def test_full_build_workflow(self):
        """Test the complete build workflow."""
        # Create test specification
        spec_data = {
            "name": "Integration Test CRM",
            "domain": "crm",
            "entities": [
                {
                    "name": "Contact",
                    "fields": [
                        {"name": "email", "type": "email", "unique": True},
                        {"name": "name", "type": "string", "required": True}
                    ]
                }
            ],
            "workflows": [],
            "integrations": [],
            "ai": {"copilots": [], "rag": False},
            "non_functional": {"multi_tenant": True, "rbac": True},
            "acceptance": []
        }
        
        # Create agent context
        agent_context = AgentContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            llm_provider=Mock(),
            redis=Mock()
        )
        
        # Mock LLM responses
        agent_context.llm_provider.generate = AsyncMock(return_value={
            'content': json.dumps(spec_data)
        })
        
        # Test Product Architect
        architect = ProductArchitectAgent(agent_context)
        spec_result = await architect.execute("create_spec", {
            "goal_text": "Build a CRM system"
        })
        
        assert "name" in spec_result["spec"]
        
        # Test System Designer
        designer = SystemDesignerAgent(agent_context)
        plan_result = await designer.execute("create_plan", {
            "spec": spec_result["spec"]
        })
        
        assert "plan" in plan_result
        assert "database_schema" in plan_result["plan"]
        
        # Test Security/Compliance
        security = SecurityComplianceAgent(agent_context)
        security_result = await security.execute("review_security", {
            "spec": spec_result["spec"],
            "plan": plan_result["plan"]
        })
        
        assert "risk_score" in security_result
        assert "security_issues" in security_result
        
        # Test Codegen Engineer
        codegen = CodegenEngineerAgent(agent_context)
        codegen_result = await codegen.execute(spec_result["spec"], plan_result["plan"], [])
        assert "diff_artifact" in codegen_result
        assert "diff_artifact" in codegen_result
        
        # Test QA/Evaluator
        evaluator = QAEvaluatorAgent(agent_context)
        eval_result = await evaluator.execute("evaluate", {
            "spec": spec_result["spec"],
            "artifacts": []
        })
        
        assert "passed" in eval_result
        assert "score" in eval_result
        
        # Test Reviewer
        reviewer = ReviewerAgent(agent_context)
        review_result = await reviewer.execute("review_run", {
            "run_data": {
                "id": str(uuid4()),
                "status": "succeeded",
                "iteration": 1
            },
            "spec": spec_result["spec"],
            "plan": plan_result["plan"],
            "evaluation_report": eval_result,
            "artifacts": []
        })
        
        assert "summary" in review_result
        assert "risk_assessment" in review_result
        assert "approval_required" in review_result


class TestMetaBuilderV2Performance:
    """Performance tests for Meta-Builder v2."""
    
    @pytest.mark.asyncio
    async def test_large_specification_performance(self):
        """Test performance with large specifications."""
        # Create large specification
        spec_data = {
            "name": "Large Enterprise System",
            "domain": "custom",
            "entities": [
                {
                    "name": f"Entity{i}",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary": True},
                        {"name": "name", "type": "string", "required": True},
                        {"name": "description", "type": "text"}
                    ]
                } for i in range(20)  # 20 entities
            ],
            "workflows": [
                {
                    "name": f"Workflow{i}",
                    "states": ["start", "process", "complete"],
                    "transitions": [
                        {"from": "start", "to": "process"},
                        {"from": "process", "to": "complete"}
                    ]
                } for i in range(5)  # 5 workflows
            ],
            "integrations": ["api1", "api2", "api3"],
            "ai": {"copilots": ["general"], "rag": True},
            "non_functional": {"multi_tenant": True, "rbac": True},
            "acceptance": [
                {"id": f"AC{i}", "text": f"Test {i}", "category": "functional"}
                for i in range(10)  # 10 acceptance criteria
            ]
        }
        
        # Create agent context
        agent_context = AgentContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            llm_provider=Mock(),
            redis=Mock()
        )
        
        # Mock LLM responses
        agent_context.llm_provider.generate = AsyncMock(return_value={
            'content': json.dumps(spec_data)
        })
        
        # Test performance
        import time
        start_time = time.time()
        
        # Run full workflow
        architect = ProductArchitectAgent(agent_context)
        spec_result = await architect.execute("create_spec", {
            "goal_text": "Build a large enterprise system"
        })
        
        designer = SystemDesignerAgent(agent_context)
        plan_result = await designer.execute("create_plan", {
            "spec": spec_result["spec"]
        })
        
        codegen = CodegenEngineerAgent(agent_context)
        codegen_result = await codegen.execute(spec_result["spec"], plan_result["plan"], [])
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert performance requirements
        assert duration < 30.0  # Should complete within 30 seconds
        assert "diff_artifact" in codegen_result
        
        print(f"Large specification processing completed in {duration:.2f} seconds")


class TestMetaBuilderV2Security:
    """Security tests for Meta-Builder v2."""
    
    @pytest.mark.asyncio
    async def test_security_validation(self):
        """Test security validation in agents."""
        # Create specification with security concerns
        spec_data = {
            "name": "Secure System",
            "domain": "custom",
            "entities": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "email", "type": "email", "unique": True},
                        {"name": "password", "type": "string"},  # Should be encrypted
                        {"name": "ssn", "type": "string"}  # PII data
                    ]
                }
            ],
            "workflows": [],
            "integrations": [],
            "ai": {"copilots": [], "rag": False},
            "non_functional": {"multi_tenant": True, "rbac": False},  # Missing RBAC
            "acceptance": []
        }
        
        # Create agent context
        agent_context = AgentContext(
            tenant_id=uuid4(),
            user_id=uuid4(),
            llm_provider=Mock(),
            redis=Mock()
        )
        
        # Test security review
        security = SecurityComplianceAgent(agent_context)
        security_result = await security.execute("review_security", {
            "spec": spec_data,
            "plan": {"security": {}}
        })
        
        # Should identify security issues
        assert security_result["risk_score"] > 0
        assert len(security_result["security_issues"]) > 0
        
        # Check for specific security issues
        issue_descriptions = [issue["description"] for issue in security_result["security_issues"]]
        assert any("PII" in desc for desc in issue_descriptions)
        assert any("RBAC" in desc for desc in issue_descriptions)
    
    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        """Test tenant isolation in models."""
        tenant_1 = uuid4()
        tenant_2 = uuid4()
        user_id = uuid4()
        
        # Create specs for different tenants
        spec_1 = create_spec(
            tenant_id=tenant_1,
            created_by=user_id,
            title="Tenant 1 Spec"
        )
        
        spec_2 = create_spec(
            tenant_id=tenant_2,
            created_by=user_id,
            title="Tenant 2 Spec"
        )
        
        # Verify tenant isolation
        assert spec_1.tenant_id == tenant_1
        assert spec_2.tenant_id == tenant_2
        assert spec_1.tenant_id != spec_2.tenant_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
