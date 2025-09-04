"""
Tests for Meta-Builder v3 orchestrator integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from uuid import uuid4

from src.meta_builder_v2.orchestrator import MetaBuilderOrchestrator, RunContext
from src.meta_builder_v2.models import BuildRun, BuildStep, ScaffoldSpec, ScaffoldPlan
from src.meta_builder_v2.agents import AgentContext
from src.meta_builder_v3.auto_fixer_v3 import AutoFixOutcome, RetryState
from src.meta_builder_v3.failures import FailureSignal


class TestOrchestratorIntegration:
    """Test orchestrator integration with v3 auto-fix."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance."""
        return MetaBuilderOrchestrator()
    
    @pytest.fixture
    def mock_run(self):
        """Create mock build run."""
        run = Mock(spec=BuildRun)
        run.id = uuid4()
        run.status = 'running'
        run.iteration = 1
        run.tenant_id = 'test-tenant'
        run.user_id = 'test-user'
        run.repo_ref = 'test/repo'
        run.safety = 'medium'
        run.llm_provider = 'openai'
        run.created_at = datetime.utcnow()
        run.updated_at = datetime.utcnow()
        return run
    
    @pytest.fixture
    def mock_step(self, mock_run):
        """Create mock build step."""
        step = Mock(spec=BuildStep)
        step.id = uuid4()
        step.run_id = mock_run.id
        step.name = 'test_step'
        step.status = 'failed'
        step.started_at = datetime.utcnow()
        step.finished_at = datetime.utcnow()
        step.output = {'error': 'Test failure'}
        return step
    
    @pytest.fixture
    def mock_context(self):
        """Create mock agent context."""
        context = Mock(spec=AgentContext)
        context.tenant_id = 'test-tenant'
        context.user_id = 'test-user'
        context.repo_ref = 'test/repo'
        context.allow_tools = True
        context.cache = {}
        context.safety = 'medium'
        context.llm_provider = 'openai'
        context.redis = Mock()
        context.analytics = Mock()
        return context
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.query = Mock()
        return session
    
    def test_init_v3_adapter(self, orchestrator):
        """Test v3 adapter initialization."""
        assert orchestrator.v3_adapter is None
        assert orchestrator.retry_states == {}
        
        orchestrator._init_v3_adapter()
        assert orchestrator.v3_adapter is not None
    
    @pytest.mark.asyncio
    async def test_handle_step_failure_v3_retry(self, orchestrator, mock_run, mock_step, mock_context, mock_db_session):
        """Test v3 failure handling with retry outcome."""
        # Mock v3 adapter
        orchestrator.v3_adapter = Mock()
        orchestrator.v3_adapter.classify.return_value = FailureSignal(
            type='transient',
            source='test_step',
            message='Connection timeout',
            severity='low',
            can_retry=True,
            requires_replan=False
        )
        orchestrator.v3_adapter.auto_fix = AsyncMock(return_value=AutoFixOutcome.RETRIED)
        orchestrator.v3_adapter.next_backoff_seconds.return_value = 5
        
        # Mock create_build_artifact
        with patch('src.meta_builder_v2.orchestrator.create_build_artifact') as mock_create_artifact:
            mock_create_artifact.return_value = Mock()
            
            result = await orchestrator._handle_step_failure_v3(
                mock_run, mock_step, 'Test logs', [], mock_db_session, mock_context
            )
        
        assert result['success'] is False
        assert result['outcome'] == 'retried'
        assert result['backoff_seconds'] == 5
        assert result['should_retry'] is True
        
        # Check retry state was updated
        retry_state = orchestrator.retry_states[str(mock_run.id)]
        assert retry_state.total_attempts == 1
        assert retry_state.per_step_attempts[str(mock_step.id)] == 1
    
    @pytest.mark.asyncio
    async def test_handle_step_failure_v3_patch_applied(self, orchestrator, mock_run, mock_step, mock_context, mock_db_session):
        """Test v3 failure handling with patch applied outcome."""
        # Mock v3 adapter
        orchestrator.v3_adapter = Mock()
        orchestrator.v3_adapter.classify.return_value = FailureSignal(
            type='lint',
            source='test_step',
            message='E302 expected 2 blank lines',
            severity='medium',
            can_retry=True,
            requires_replan=False
        )
        orchestrator.v3_adapter.auto_fix = AsyncMock(return_value=AutoFixOutcome.PATCH_APPLIED)
        
        # Mock create_build_artifact
        with patch('src.meta_builder_v2.orchestrator.create_build_artifact') as mock_create_artifact:
            mock_create_artifact.return_value = Mock()
            
            result = await orchestrator._handle_step_failure_v3(
                mock_run, mock_step, 'Test logs', [], mock_db_session, mock_context
            )
        
        assert result['success'] is True
        assert result['outcome'] == 'patch_applied'
        assert result['should_retry'] is False
    
    @pytest.mark.asyncio
    async def test_handle_step_failure_v3_replanned(self, orchestrator, mock_run, mock_step, mock_context, mock_db_session):
        """Test v3 failure handling with re-plan outcome."""
        # Mock v3 adapter
        orchestrator.v3_adapter = Mock()
        orchestrator.v3_adapter.classify.return_value = FailureSignal(
            type='unknown',
            source='test_step',
            message='Unknown error',
            severity='high',
            can_retry=False,
            requires_replan=True
        )
        orchestrator.v3_adapter.auto_fix = AsyncMock(return_value=AutoFixOutcome.REPLANNED)
        
        # Mock create_build_artifact
        with patch('src.meta_builder_v2.orchestrator.create_build_artifact') as mock_create_artifact:
            mock_create_artifact.return_value = Mock()
            
            result = await orchestrator._handle_step_failure_v3(
                mock_run, mock_step, 'Test logs', [], mock_db_session, mock_context
            )
        
        assert result['success'] is False
        assert result['outcome'] == 'replanned'
        assert result['should_retry'] is False
        assert result['requires_replan'] is True
    
    @pytest.mark.asyncio
    async def test_handle_step_failure_v3_escalated(self, orchestrator, mock_run, mock_step, mock_context, mock_db_session):
        """Test v3 failure handling with escalation outcome."""
        # Mock v3 adapter
        orchestrator.v3_adapter = Mock()
        orchestrator.v3_adapter.classify = Mock()
        orchestrator.v3_adapter.classify.return_value = FailureSignal(
            type='security',
            source='test_step',
            message='Security vulnerability detected',
            severity='high',
            can_retry=False,
            requires_replan=False
        )
        orchestrator.v3_adapter.auto_fix = AsyncMock(return_value=AutoFixOutcome.ESCALATED)
        
        # Mock create_build_artifact and create_approval_gate
        with patch('src.meta_builder_v2.orchestrator.create_build_artifact') as mock_create_artifact, \
             patch('src.meta_builder_v2.orchestrator.create_approval_gate') as mock_create_gate:
            
            mock_create_artifact.return_value = Mock()
            mock_gate = Mock()
            mock_gate.id = uuid4()
            mock_create_gate.return_value = mock_gate
            
            result = await orchestrator._handle_step_failure_v3(
                mock_run, mock_step, 'Test logs', [], mock_db_session, mock_context
            )
        
        assert result['success'] is False
        assert result['outcome'] == 'escalated'
        assert result['should_retry'] is False
        assert 'approval_gate_id' in result
        
        # Check run status was updated
        assert mock_run.status == 'paused_awaiting_approval'
    
    @pytest.mark.asyncio
    async def test_handle_step_failure_v3_gave_up(self, orchestrator, mock_run, mock_step, mock_context, mock_db_session):
        """Test v3 failure handling with give up outcome."""
        # Mock v3 adapter
        orchestrator.v3_adapter = Mock()
        orchestrator.v3_adapter.classify.return_value = FailureSignal(
            type='runtime',
            source='test_step',
            message='Critical runtime error',
            severity='high',
            can_retry=False,
            requires_replan=False
        )
        orchestrator.v3_adapter.auto_fix = AsyncMock(return_value=AutoFixOutcome.GAVE_UP)
        
        # Mock create_build_artifact
        with patch('src.meta_builder_v2.orchestrator.create_build_artifact') as mock_create_artifact:
            mock_create_artifact.return_value = Mock()
            
            result = await orchestrator._handle_step_failure_v3(
                mock_run, mock_step, 'Test logs', [], mock_db_session, mock_context
            )
        
        assert result['success'] is False
        assert result['outcome'] == 'gave_up'
        assert result['should_retry'] is False
        assert 'reason' in result
        
        # Check step status was updated
        assert mock_step.status == 'failed'
    
    @pytest.mark.asyncio
    async def test_handle_step_failure_v3_budget_exceeded(self, orchestrator, mock_run, mock_step, mock_context, mock_db_session):
        """Test v3 failure handling when budget is exceeded."""
        # Initialize retry state with max attempts
        orchestrator.retry_states[str(mock_run.id)] = RetryState()
        retry_state = orchestrator.retry_states[str(mock_run.id)]
        retry_state.total_attempts = 6  # Max attempts
        retry_state.max_total_attempts = 6
        
        # Mock v3 adapter
        orchestrator.v3_adapter = Mock()
        orchestrator.v3_adapter.classify.return_value = FailureSignal(
            type='runtime',
            source='test_step',
            message='Critical runtime error',
            severity='high',
            can_retry=False,
            requires_replan=False
        )
        orchestrator.v3_adapter.auto_fix = AsyncMock(return_value=AutoFixOutcome.GAVE_UP)
        
        # Mock create_build_artifact
        with patch('src.meta_builder_v2.orchestrator.create_build_artifact') as mock_create_artifact:
            mock_create_artifact.return_value = Mock()
            
            result = await orchestrator._handle_step_failure_v3(
                mock_run, mock_step, 'Test logs', [], mock_db_session, mock_context
            )
        
        assert result['success'] is False
        assert result['outcome'] == 'gave_up'
        
        # Check run status was updated to failed
        assert mock_run.status == 'failed'
    
    @pytest.mark.asyncio
    async def test_execute_autofix_step_v3_fallback(self, orchestrator, mock_context, mock_db_session):
        """Test auto-fix step with v3 fallback to v2."""
        # Create run context
        spec = Mock(spec=ScaffoldSpec)
        plan = Mock(spec=ScaffoldPlan)
        run = Mock(spec=BuildRun)
        run.id = uuid4()
        
        run_context = RunContext(run, spec, plan)
        run_context.reports = [{'error': 'Test failure'}]
        run_context.artifacts = []
        
        # Mock v3 adapter to fail
        orchestrator.v3_adapter = Mock()
        orchestrator.v3_adapter.auto_fix.side_effect = Exception("V3 not available")
        
        # Mock v2 auto-fixer
        with patch('src.meta_builder_v2.orchestrator.AutoFixerAgent') as mock_agent_class:
            mock_agent = Mock()
            mock_agent.execute = AsyncMock(return_value={'fixed': True})
            mock_agent_class.return_value = mock_agent
            
            # Mock create_step
            with patch('src.meta_builder_v2.orchestrator.create_step') as mock_create_step:
                mock_step = Mock(spec=BuildStep)
                mock_step.id = uuid4()
                mock_step.name = 'autofix'
                mock_create_step.return_value = mock_step
                
                result = await orchestrator._execute_autofix_step(
                    run_context, mock_db_session, mock_context
                )
        
        assert result['success'] is True
        assert result['fixed'] is True
        
        # Verify v2 agent was called
        mock_agent.execute.assert_called_once()


class TestRunContextV3:
    """Test enhanced run context for v3."""
    
    @pytest.fixture
    def run_context(self):
        """Create run context."""
        spec = Mock(spec=ScaffoldSpec)
        plan = Mock(spec=ScaffoldPlan)
        run = Mock(spec=BuildRun)
        run.id = uuid4()
        run.iteration = 1
        
        return RunContext(run, spec, plan)
    
    def test_add_artifact(self, run_context):
        """Test adding artifact to context."""
        artifact = {'type': 'test', 'content': 'test'}
        run_context.add_artifact(artifact)
        
        assert len(run_context.artifacts) == 1
        assert run_context.artifacts[0] == artifact
    
    def test_add_report(self, run_context):
        """Test adding report to context."""
        report = {'status': 'success', 'score': 95}
        run_context.add_report(report)
        
        assert len(run_context.reports) == 1
        assert run_context.reports[0] == report
    
    def test_add_span(self, run_context):
        """Test adding span to context."""
        span = {'agent': 'test', 'duration': 1.5}
        run_context.add_span(span)
        
        assert len(run_context.spans) == 1
        assert run_context.spans[0] == span
