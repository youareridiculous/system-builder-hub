"""
Tests for Meta-Builder v3 API endpoints.
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime
from uuid import uuid4

from src.meta_builder_v3.api_v3 import (
    get_auto_fix_history, approve_auto_fix, reject_auto_fix,
    retry_run, get_escalations, get_plan_deltas, classify_failure_endpoint
)


class TestAutoFixHistoryAPI:
    """Test auto-fix history endpoint."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock()
        request.args = {}
        return request
    
    @pytest.fixture
    def mock_current_user(self):
        """Create mock current user."""
        user = Mock()
        user.tenant_id = "test-tenant"
        user.role = "admin"
        return user
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = Mock()
        return session
    
    def test_get_auto_fix_history_success(self, mock_request, mock_current_user, mock_db_session):
        """Test successful auto-fix history retrieval."""
        run_id = str(uuid4())
        
        # Mock run
        mock_run = Mock()
        mock_run.tenant_id = "test-tenant"
        
        # Mock auto-fix runs
        mock_auto_fix_run = Mock()
        mock_auto_fix_run.id = uuid4()
        mock_auto_fix_run.step_id = uuid4()
        mock_auto_fix_run.signal_type = "test_assert"
        mock_auto_fix_run.strategy = "retry_step"
        mock_auto_fix_run.outcome = "retried"
        mock_auto_fix_run.attempt = 1
        mock_auto_fix_run.backoff = 2.0
        mock_auto_fix_run.created_at = datetime.utcnow()
        mock_auto_fix_run.updated_at = datetime.utcnow()
        
        # Mock step
        mock_step = Mock()
        mock_step.name = "test_step"
        
        # Mock retry state
        mock_retry_state = Mock()
        mock_retry_state.total_attempts = 2
        mock_retry_state.max_total_attempts = 6
        mock_retry_state.per_step_attempts = {"step1": 1}
        mock_retry_state.last_backoff_seconds = 2.0
        
        with patch('src.meta_builder_v3.api_v3.current_app') as mock_app:
            mock_app.db.session = mock_db_session
            
            # Mock queries
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [
                mock_run,  # Run query
                mock_retry_state  # Retry state query
            ]
            
            mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
                mock_auto_fix_run
            ]
            
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [
                mock_run,  # Run query
                mock_step,  # Step query
                mock_retry_state  # Retry state query
            ]
            
            with patch('src.meta_builder_v3.api_v3.current_user', mock_current_user):
                with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                    mock_jsonify.return_value = Mock()
                    
                    result = get_auto_fix_history(run_id)
                    
                    # Verify the response structure
                    mock_jsonify.assert_called()
                    call_args = mock_jsonify.call_args[0][0]
                    assert "run_id" in call_args
                    assert "history" in call_args
                    assert "retry_state" in call_args
    
    def test_get_auto_fix_history_run_not_found(self, mock_request, mock_current_user, mock_db_session):
        """Test auto-fix history when run not found."""
        run_id = str(uuid4())
        
        with patch('src.meta_builder_v3.api_v3.current_app') as mock_app:
            mock_app.db.session = mock_db_session
            
            # Mock run not found
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            
            with patch('src.meta_builder_v3.api_v3.current_user', mock_current_user):
                with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                    mock_jsonify.return_value = Mock()
                    
                    result = get_auto_fix_history(run_id)
                    
                    # Should return 404
                    mock_jsonify.assert_called_with({"error": "Run not found"})
    
    def test_get_auto_fix_history_access_denied(self, mock_request, mock_current_user, mock_db_session):
        """Test auto-fix history with access denied."""
        run_id = str(uuid4())
        
        # Mock run with different tenant
        mock_run = Mock()
        mock_run.tenant_id = "different-tenant"
        
        with patch('src.meta_builder_v3.api_v3.current_app') as mock_app:
            mock_app.db.session = mock_db_session
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_run
            
            with patch('src.meta_builder_v3.api_v3.current_user', mock_current_user):
                with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                    mock_jsonify.return_value = Mock()
                    
                    result = get_auto_fix_history(run_id)
                    
                    # Should return 403
                    mock_jsonify.assert_called_with({"error": "Access denied"})


class TestApprovalAPI:
    """Test approval endpoints."""
    
    def test_approve_auto_fix_success(self, mock_current_user, mock_db_session):
        """Test successful auto-fix approval."""
        gate_id = str(uuid4())
        
        # Mock approval gate
        mock_gate = Mock()
        mock_gate.id = uuid4()
        mock_gate.status = "pending"
        mock_gate.metadata = {}
        
        # Mock run
        mock_run = Mock()
        mock_run.tenant_id = "test-tenant"
        
        with patch('src.meta_builder_v3.api_v3.current_app') as mock_app:
            mock_app.db.session = mock_db_session
            
            # Mock queries
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [
                mock_gate,  # Gate query
                mock_run   # Run query
            ]
            
            with patch('src.meta_builder_v3.api_v3.current_user', mock_current_user):
                with patch('src.meta_builder_v3.api_v3.request') as mock_request:
                    mock_request.get_json.return_value = {"approved": True, "comment": "Looks good"}
                    
                    with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                        mock_jsonify.return_value = Mock()
                        
                        result = approve_auto_fix(gate_id)
                        
                        # Verify gate was updated
                        assert mock_gate.status == "approved"
                        assert mock_gate.metadata["approved_by"] == str(mock_current_user.id)
                        assert "comment" in mock_gate.metadata
                        
                        # Verify response
                        mock_jsonify.assert_called_with({
                            "success": True,
                            "message": "Auto-fix approved",
                            "gate_id": gate_id
                        })
    
    def test_approve_auto_fix_insufficient_permissions(self, mock_current_user, mock_db_session):
        """Test auto-fix approval with insufficient permissions."""
        gate_id = str(uuid4())
        
        # Mock user with insufficient role
        mock_current_user.role = "member"
        
        # Mock approval gate
        mock_gate = Mock()
        mock_gate.id = uuid4()
        
        # Mock run
        mock_run = Mock()
        mock_run.tenant_id = "test-tenant"
        
        with patch('src.meta_builder_v3.api_v3.current_app') as mock_app:
            mock_app.db.session = mock_db_session
            
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [
                mock_gate,  # Gate query
                mock_run   # Run query
            ]
            
            with patch('src.meta_builder_v3.api_v3.current_user', mock_current_user):
                with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                    mock_jsonify.return_value = Mock()
                    
                    result = approve_auto_fix(gate_id)
                    
                    # Should return 403
                    mock_jsonify.assert_called_with({"error": "Insufficient permissions"})


class TestRetryRunAPI:
    """Test retry run endpoint."""
    
    def test_retry_run_success(self, mock_current_user, mock_db_session):
        """Test successful run retry."""
        run_id = str(uuid4())
        
        # Mock original run
        mock_run = Mock()
        mock_run.id = uuid4()
        mock_run.tenant_id = "test-tenant"
        mock_run.status = "failed"
        mock_run.plan_id = uuid4()
        mock_run.iteration = 1
        mock_run.user_id = "test-user"
        mock_run.repo_ref = "test-repo"
        mock_run.safety = "medium"
        mock_run.llm_provider = "openai"
        mock_run.redis = Mock()
        mock_run.analytics = Mock()
        
        with patch('src.meta_builder_v3.api_v3.current_app') as mock_app:
            mock_app.db.session = mock_db_session
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_run
            
            with patch('src.meta_builder_v3.api_v3.current_user', mock_current_user):
                with patch('src.meta_builder_v3.api_v3.request') as mock_request:
                    mock_request.get_json.return_value = {}
                    
                    with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                        mock_jsonify.return_value = Mock()
                        
                        with patch('src.meta_builder_v3.api_v3.BuildRun') as mock_build_run:
                            mock_new_run = Mock()
                            mock_new_run.id = uuid4()
                            mock_new_run.iteration = 2
                            mock_build_run.return_value = mock_new_run
                            
                            with patch('src.meta_builder_v3.api_v3.RetryState') as mock_retry_state:
                                mock_retry_state_instance = Mock()
                                mock_retry_state.return_value = mock_retry_state_instance
                                
                                result = retry_run(run_id)
                                
                                # Verify new run was created
                                mock_build_run.assert_called_once()
                                mock_retry_state.assert_called_once()
                                
                                # Verify response
                                mock_jsonify.assert_called_with({
                                    "success": True,
                                    "message": "Run retry initiated",
                                    "new_run_id": str(mock_new_run.id),
                                    "iteration": mock_new_run.iteration
                                })
    
    def test_retry_run_cannot_retry(self, mock_current_user, mock_db_session):
        """Test retry run when run cannot be retried."""
        run_id = str(uuid4())
        
        # Mock run with status that cannot be retried
        mock_run = Mock()
        mock_run.tenant_id = "test-tenant"
        mock_run.status = "succeeded"  # Cannot retry succeeded runs
        
        with patch('src.meta_builder_v3.api_v3.current_app') as mock_app:
            mock_app.db.session = mock_db_session
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_run
            
            with patch('src.meta_builder_v3.api_v3.current_user', mock_current_user):
                with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                    mock_jsonify.return_value = Mock()
                    
                    result = retry_run(run_id)
                    
                    # Should return 400
                    mock_jsonify.assert_called_with({"error": "Run cannot be retried"})


class TestClassifyFailureAPI:
    """Test failure classification endpoint."""
    
    def test_classify_failure_success(self, mock_current_user):
        """Test successful failure classification."""
        step_name = "test_step"
        logs = "AssertionError: expected 1 but got 2"
        artifacts = []
        
        with patch('src.meta_builder_v3.api_v3.request') as mock_request:
            mock_request.get_json.return_value = {
                "step_name": step_name,
                "logs": logs,
                "artifacts": artifacts
            }
            
            with patch('src.meta_builder_v3.api_v3.classify_failure') as mock_classify:
                mock_signal = Mock()
                mock_signal.type = "test_assert"
                mock_signal.source = step_name
                mock_signal.message = "Test assertion failed"
                mock_signal.evidence = {"logs": logs}
                mock_signal.severity = "medium"
                mock_signal.can_retry = False
                mock_signal.requires_replan = False
                mock_signal.created_at = datetime.utcnow()
                mock_signal.metadata = {}
                
                mock_classify.return_value = mock_signal
                
                with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                    mock_jsonify.return_value = Mock()
                    
                    result = classify_failure_endpoint()
                    
                    # Verify classification was called
                    mock_classify.assert_called_once_with(step_name, logs, artifacts, [])
                    
                    # Verify response
                    mock_jsonify.assert_called()
                    call_args = mock_jsonify.call_args[0][0]
                    assert "failure_signal" in call_args
                    assert call_args["failure_signal"]["type"] == "test_assert"
    
    def test_classify_failure_missing_step_name(self, mock_current_user):
        """Test failure classification with missing step name."""
        with patch('src.meta_builder_v3.api_v3.request') as mock_request:
            mock_request.get_json.return_value = {
                "logs": "Some error"
            }
            
            with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                mock_jsonify.return_value = Mock()
                
                result = classify_failure_endpoint()
                
                # Should return 400
                mock_jsonify.assert_called_with({"error": "step_name is required"})
    
    def test_classify_failure_no_data(self, mock_current_user):
        """Test failure classification with no data."""
        with patch('src.meta_builder_v3.api_v3.request') as mock_request:
            mock_request.get_json.return_value = None
            
            with patch('src.meta_builder_v3.api_v3.jsonify') as mock_jsonify:
                mock_jsonify.return_value = Mock()
                
                result = classify_failure_endpoint()
                
                # Should return 400
                mock_jsonify.assert_called_with({"error": "No data provided"})
