"""
Tests for flake detection functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.eval_lab.flake import (
    FlakeDetector, FlakeHeuristics, FlakeScore, FlakeClass,
    QuarantineManager
)


class TestFlakeHeuristics:
    """Test flake detection heuristics."""
    
    def test_default_heuristics(self):
        """Test default heuristic values."""
        heuristics = FlakeHeuristics()
        
        assert heuristics.pass_fail_pass_threshold == 3
        assert heuristics.latency_variance_threshold == 1.5
        assert heuristics.provider_error_threshold == 0.3
        assert heuristics.time_of_day_correlation is False
        assert heuristics.min_runs_for_analysis == 5
        assert heuristics.quarantine_score_threshold == 0.7
    
    def test_custom_heuristics(self):
        """Test custom heuristic configuration."""
        heuristics = FlakeHeuristics(
            pass_fail_pass_threshold=5,
            latency_variance_threshold=2.0,
            provider_error_threshold=0.5,
            time_of_day_correlation=True,
            min_runs_for_analysis=10,
            quarantine_score_threshold=0.8
        )
        
        assert heuristics.pass_fail_pass_threshold == 5
        assert heuristics.latency_variance_threshold == 2.0
        assert heuristics.provider_error_threshold == 0.5
        assert heuristics.time_of_day_correlation is True
        assert heuristics.min_runs_for_analysis == 10
        assert heuristics.quarantine_score_threshold == 0.8


class TestFlakeDetector:
    """Test flake detection logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.heuristics = FlakeHeuristics()
        self.detector = FlakeDetector(self.heuristics)
    
    def test_insufficient_data(self):
        """Test flake detection with insufficient data."""
        case_runs = [
            {"passed": True, "started_at": "2024-01-01T10:00:00Z"},
            {"passed": False, "started_at": "2024-01-01T11:00:00Z"}
        ]
        
        score = self.detector.analyze_case_flakiness(case_runs)
        
        assert score.score == 0.0
        assert score.class_ == FlakeClass.STABLE
        assert "Insufficient data" in score.reasons
    
    def test_pass_fail_pass_pattern(self):
        """Test detection of pass-fail-pass pattern."""
        case_runs = [
            {"passed": True, "started_at": "2024-01-01T10:00:00Z"},
            {"passed": False, "started_at": "2024-01-01T11:00:00Z"},
            {"passed": True, "started_at": "2024-01-01T12:00:00Z"},
            {"passed": False, "started_at": "2024-01-01T13:00:00Z"},
            {"passed": True, "started_at": "2024-01-01T14:00:00Z"}
        ]
        
        score = self.detector.analyze_case_flakiness(case_runs)
        
        assert score.score > 0.0
        assert "Inconsistent pass/fail pattern" in score.reasons
    
    def test_latency_variance(self):
        """Test detection of high latency variance."""
        case_runs = [
            {"passed": True, "latency_ms": 1000, "started_at": "2024-01-01T10:00:00Z"},
            {"passed": True, "latency_ms": 5000, "started_at": "2024-01-01T11:00:00Z"},
            {"passed": True, "latency_ms": 2000, "started_at": "2024-01-01T12:00:00Z"},
            {"passed": True, "latency_ms": 8000, "started_at": "2024-01-01T13:00:00Z"},
            {"passed": True, "latency_ms": 1500, "started_at": "2024-01-01T14:00:00Z"}
        ]
        
        score = self.detector.analyze_case_flakiness(case_runs)
        
        assert score.score > 0.0
        assert "High latency variance" in score.reasons
    
    def test_provider_errors(self):
        """Test detection of provider errors."""
        case_runs = [
            {"passed": True, "error_message": "", "started_at": "2024-01-01T10:00:00Z"},
            {"passed": False, "error_message": "HTTP 429: Rate limit exceeded", "started_at": "2024-01-01T11:00:00Z"},
            {"passed": True, "error_message": "", "started_at": "2024-01-01T12:00:00Z"},
            {"passed": False, "error_message": "HTTP 500: Internal server error", "started_at": "2024-01-01T13:00:00Z"},
            {"passed": True, "error_message": "", "started_at": "2024-01-01T14:00:00Z"}
        ]
        
        score = self.detector.analyze_case_flakiness(case_runs)
        
        assert score.score > 0.0
        assert "Intermittent provider errors" in score.reasons
    
    def test_stable_case(self):
        """Test detection of stable case."""
        case_runs = [
            {"passed": True, "latency_ms": 1000, "started_at": "2024-01-01T10:00:00Z"},
            {"passed": True, "latency_ms": 1100, "started_at": "2024-01-01T11:00:00Z"},
            {"passed": True, "latency_ms": 1050, "started_at": "2024-01-01T12:00:00Z"},
            {"passed": True, "latency_ms": 1150, "started_at": "2024-01-01T13:00:00Z"},
            {"passed": True, "latency_ms": 1000, "started_at": "2024-01-01T14:00:00Z"}
        ]
        
        score = self.detector.analyze_case_flakiness(case_runs)
        
        assert score.score < 0.3
        assert score.class_ == FlakeClass.STABLE
    
    def test_flaky_case(self):
        """Test detection of flaky case."""
        case_runs = [
            {"passed": True, "latency_ms": 1000, "started_at": "2024-01-01T10:00:00Z"},
            {"passed": False, "latency_ms": 5000, "error_message": "HTTP 429", "started_at": "2024-01-01T11:00:00Z"},
            {"passed": True, "latency_ms": 1200, "started_at": "2024-01-01T12:00:00Z"},
            {"passed": False, "latency_ms": 8000, "error_message": "HTTP 500", "started_at": "2024-01-01T13:00:00Z"},
            {"passed": True, "latency_ms": 1100, "started_at": "2024-01-01T14:00:00Z"}
        ]
        
        score = self.detector.analyze_case_flakiness(case_runs)
        
        assert 0.3 <= score.score < 0.7
        assert score.class_ == FlakeClass.FLAKY
    
    def test_quarantine_recommended(self):
        """Test detection of quarantine recommendation."""
        # Create a very flaky case
        case_runs = []
        for i in range(10):
            case_runs.append({
                "passed": i % 2 == 0,  # Alternating pass/fail
                "latency_ms": 1000 + (i * 1000),  # Increasing latency
                "error_message": "HTTP 429" if i % 2 == 1 else "",
                "started_at": f"2024-01-01T{10+i:02d}:00:00Z"
            })
        
        score = self.detector.analyze_case_flakiness(case_runs)
        
        assert score.score >= 0.7
        assert score.class_ == FlakeClass.QUARANTINE_RECOMMENDED


class TestQuarantineManager:
    """Test quarantine management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage = Mock()
        self.manager = QuarantineManager(self.mock_storage, ttl_days=7)
    
    def test_add_to_quarantine(self):
        """Test adding a case to quarantine."""
        with patch('src.eval_lab.flake.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            quarantine_id = self.manager.add_to_quarantine(
                tenant_id="tenant123",
                suite_id="core_crm",
                case_id="contact_create",
                reason="High flake score",
                flake_score=0.8
            )
            
            assert quarantine_id.startswith("quarantine_")
            self.mock_storage.get_session.assert_called_once()
    
    def test_is_quarantined(self):
        """Test checking if a case is quarantined."""
        # Mock the database query
        mock_session = Mock()
        mock_quarantine_case = Mock()
        mock_quarantine_case.id = "quarantine_123"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_quarantine_case
        
        self.mock_storage.get_session.return_value.__enter__.return_value = mock_session
        
        is_quarantined = self.manager.is_quarantined(
            tenant_id="tenant123",
            suite_id="core_crm",
            case_id="contact_create"
        )
        
        assert is_quarantined is True
    
    def test_is_not_quarantined(self):
        """Test checking if a case is not quarantined."""
        # Mock the database query to return None
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        self.mock_storage.get_session.return_value.__enter__.return_value = mock_session
        
        is_quarantined = self.manager.is_quarantined(
            tenant_id="tenant123",
            suite_id="core_crm",
            case_id="contact_create"
        )
        
        assert is_quarantined is False
    
    def test_release_from_quarantine(self):
        """Test releasing a case from quarantine."""
        # Mock the database query
        mock_session = Mock()
        mock_quarantine_case = Mock()
        mock_quarantine_case.id = "quarantine_123"
        mock_quarantine_case.metadata = {}
        mock_session.query.return_value.filter.return_value.first.return_value = mock_quarantine_case
        
        self.mock_storage.get_session.return_value.__enter__.return_value = mock_session
        
        success = self.manager.release_from_quarantine(
            tenant_id="tenant123",
            quarantine_id="quarantine_123"
        )
        
        assert success is True
        assert mock_quarantine_case.status == "MANUAL_RELEASED"
    
    def test_release_nonexistent_quarantine(self):
        """Test releasing a nonexistent quarantine case."""
        # Mock the database query to return None
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        self.mock_storage.get_session.return_value.__enter__.return_value = mock_session
        
        success = self.manager.release_from_quarantine(
            tenant_id="tenant123",
            quarantine_id="nonexistent"
        )
        
        assert success is False
    
    def test_cleanup_expired_quarantines(self):
        """Test cleanup of expired quarantine cases."""
        # Mock expired cases
        mock_session = Mock()
        mock_expired_case1 = Mock()
        mock_expired_case1.metadata = {}
        mock_expired_case2 = Mock()
        mock_expired_case2.metadata = {}
        
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_expired_case1, mock_expired_case2
        ]
        
        self.mock_storage.get_session.return_value.__enter__.return_value = mock_session
        
        count = self.manager.cleanup_expired_quarantines()
        
        assert count == 2
        assert mock_expired_case1.status == "EXPIRED"
        assert mock_expired_case2.status == "EXPIRED"
    
    def test_get_quarantine_list(self):
        """Test getting list of quarantined cases."""
        # Mock quarantine cases
        mock_session = Mock()
        mock_case1 = Mock()
        mock_case1.id = "quarantine_1"
        mock_case1.tenant_id = "tenant123"
        mock_case1.suite_id = "core_crm"
        mock_case1.case_id = "contact_create"
        mock_case1.reason = "High flake score"
        mock_case1.flake_score = 0.8
        mock_case1.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_case1.expires_at = datetime(2024, 1, 8, 12, 0, 0)
        mock_case1.status = "ACTIVE"
        mock_case1.metadata = {}
        
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_case1]
        
        self.mock_storage.get_session.return_value.__enter__.return_value = mock_session
        
        cases = self.manager.get_quarantine_list("tenant123")
        
        assert len(cases) == 1
        assert cases[0]["id"] == "quarantine_1"
        assert cases[0]["case_id"] == "contact_create"
        assert cases[0]["status"] == "ACTIVE"
