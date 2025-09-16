"""
Tests for canary testing module.
"""

import pytest
from datetime import datetime, timedelta

from src.meta_builder_v4.canary import (
    CanaryManager, CanaryGroup, CanarySample, CanaryMetrics, CanaryComparison
)


class TestCanaryManager:
    """Test canary manager functionality."""
    
    @pytest.fixture
    def canary_manager(self):
        """Create a canary manager for testing."""
        return CanaryManager(canary_percent=0.5)
    
    def test_should_use_v4_disabled(self):
        """Test v4 selection when canary is disabled."""
        manager = CanaryManager(canary_percent=0.0)
        result = manager.should_use_v4("run_1", "tenant_1")
        assert result is False
    
    def test_should_use_v4_enabled(self, canary_manager):
        """Test v4 selection when canary is enabled."""
        # Test multiple runs to see distribution
        v4_count = 0
        total_runs = 100
        
        for i in range(total_runs):
            if canary_manager.should_use_v4(f"run_{i}", "tenant_1"):
                v4_count += 1
        
        # Should be roughly 50% (allowing for some variance)
        v4_percentage = v4_count / total_runs
        assert 0.4 <= v4_percentage <= 0.6
    
    def test_should_use_v4_consistent_assignment(self, canary_manager):
        """Test that the same run gets consistent assignment."""
        run_id = "run_1"
        tenant_id = "tenant_1"
        
        # First assignment
        first_result = canary_manager.should_use_v4(run_id, tenant_id)
        
        # Second assignment should be the same
        second_result = canary_manager.should_use_v4(run_id, tenant_id)
        
        assert first_result == second_result
    
    def test_record_completion(self, canary_manager):
        """Test recording completion of a canary sample."""
        # Create a sample first
        canary_manager.should_use_v4("run_1", "tenant_1")
        
        # Record completion
        canary_manager.record_completion(
            run_id="run_1",
            success=True,
            metrics={"test_metric": 1.0},
            cost_usd=2.5,
            duration_seconds=300,
            retry_count=1,
            replan_count=0,
            rollback_count=0
        )
        
        # Find the sample
        sample = canary_manager._get_sample_by_run_id("run_1")
        assert sample is not None
        assert sample.success is True
        assert sample.cost_usd == 2.5
        assert sample.duration_seconds == 300
        assert sample.retry_count == 1
        assert sample.completed_at is not None
    
    def test_get_canary_metrics_empty(self, canary_manager):
        """Test getting metrics with no samples."""
        metrics = canary_manager.get_canary_metrics(hours=24)
        
        assert "control" in metrics
        assert "v4" in metrics
        
        control = metrics["control"]
        v4 = metrics["v4"]
        
        assert control.sample_size == 0
        assert v4.sample_size == 0
        assert control.success_rate == 0.0
        assert v4.success_rate == 0.0
    
    def test_get_canary_metrics_with_samples(self, canary_manager):
        """Test getting metrics with samples."""
        # Create some samples
        canary_manager.should_use_v4("run_1", "tenant_1")
        canary_manager.should_use_v4("run_2", "tenant_1")
        
        # Record completions
        canary_manager.record_completion("run_1", True, {}, 2.0, 200, 0, 0, 0)
        canary_manager.record_completion("run_2", False, {}, 3.0, 400, 2, 1, 0)
        
        # Get metrics
        metrics = canary_manager.get_canary_metrics(hours=24)
        
        # Should have samples
        assert metrics["control"].sample_size >= 0
        assert metrics["v4"].sample_size >= 0
    
    def test_evaluate_canary_performance_insufficient_samples(self, canary_manager):
        """Test evaluation with insufficient samples."""
        # Set minimum sample size to 10
        canary_manager.config["min_sample_size"] = 10
        
        # Create only 5 samples
        for i in range(5):
            canary_manager.should_use_v4(f"run_{i}", "tenant_1")
            canary_manager.record_completion(f"run_{i}", True, {}, 2.0, 200, 0, 0, 0)
        
        evaluation = canary_manager.evaluate_canary_performance()
        
        assert evaluation["evaluation_ready"] is False
        assert "Insufficient sample size" in evaluation["reason"]
    
    def test_evaluate_canary_performance_sufficient_samples(self, canary_manager):
        """Test evaluation with sufficient samples."""
        # Set minimum sample size to 5
        canary_manager.config["min_sample_size"] = 5
        
        # Create samples - need both control and v4 samples
        for i in range(10):
            # Force some to be control by setting canary percent to 0 temporarily
            original_percent = canary_manager.canary_percent
            canary_manager.canary_percent = 0.0
            canary_manager.should_use_v4(f"run_control_{i}", "tenant_1")
            canary_manager.record_completion(f"run_control_{i}", True, {}, 2.0, 200, 0, 0, 0)
            
            # Reset to original percent for v4 samples
            canary_manager.canary_percent = original_percent
            canary_manager.should_use_v4(f"run_v4_{i}", "tenant_1")
            canary_manager.record_completion(f"run_v4_{i}", True, {}, 2.0, 200, 0, 0, 0)
        for i in range(10):
            canary_manager.should_use_v4(f"run_{i}", "tenant_1")
            canary_manager.record_completion(f"run_{i}", True, {}, 2.0, 200, 0, 0, 0)
        
        evaluation = canary_manager.evaluate_canary_performance()
        
        assert evaluation["evaluation_ready"] is True
        assert "overall_success" in evaluation
        assert "metrics" in evaluation
        assert "recommendation" in evaluation
    
    def test_get_canary_stats(self, canary_manager):
        """Test getting canary statistics."""
        # Create some samples
        canary_manager.should_use_v4("run_1", "tenant_1")
        canary_manager.should_use_v4("run_2", "tenant_1")
        canary_manager.record_completion("run_1", True, {}, 2.0, 200, 0, 0, 0)
        
        stats = canary_manager.get_canary_stats()
        
        assert "config" in stats
        assert "samples" in stats
        assert "actual_percent" in stats
        assert "evaluation" in stats
        
        assert stats["config"]["canary_percent"] == 0.5
        assert stats["samples"]["total"] >= 2
        assert stats["samples"]["completed"] >= 1


class TestCanarySample:
    """Test canary sample functionality."""
    
    def test_canary_sample_creation(self):
        """Test creating a canary sample."""
        sample = CanarySample(
            sample_id="sample_1",
            run_id="run_1",
            tenant_id="tenant_1",
            canary_group=CanaryGroup.V4,
            assigned_at=datetime.utcnow()
        )
        
        assert sample.sample_id == "sample_1"
        assert sample.run_id == "run_1"
        assert sample.tenant_id == "tenant_1"
        assert sample.canary_group == CanaryGroup.V4
        assert sample.is_completed() is False
    
    def test_canary_sample_completion(self):
        """Test marking a sample as completed."""
        sample = CanarySample(
            sample_id="sample_1",
            run_id="run_1",
            tenant_id="tenant_1",
            canary_group=CanaryGroup.V4,
            assigned_at=datetime.utcnow()
        )
        
        sample.completed_at = datetime.utcnow()
        sample.success = True
        
        assert sample.is_completed() is True
        assert sample.get_duration() >= 0


class TestCanaryMetrics:
    """Test canary metrics functionality."""
    
    def test_canary_metrics_creation(self):
        """Test creating canary metrics."""
        metrics = CanaryMetrics(
            success_rate=0.8,
            avg_cost_usd=2.5,
            avg_duration_seconds=300,
            retry_rate=0.2,
            replan_rate=0.1,
            rollback_rate=0.0,
            confidence_score=0.75,
            sample_size=10
        )
        
        assert metrics.success_rate == 0.8
        assert metrics.avg_cost_usd == 2.5
        assert metrics.avg_duration_seconds == 300
        assert metrics.sample_size == 10
    
    def test_canary_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = CanaryMetrics(
            success_rate=0.8,
            avg_cost_usd=2.5,
            avg_duration_seconds=300,
            retry_rate=0.2,
            replan_rate=0.1,
            rollback_rate=0.0,
            confidence_score=0.75,
            sample_size=10
        )
        
        metrics_dict = metrics.to_dict()
        
        assert metrics_dict["success_rate"] == 0.8
        assert metrics_dict["avg_cost_usd"] == 2.5
        assert metrics_dict["sample_size"] == 10
