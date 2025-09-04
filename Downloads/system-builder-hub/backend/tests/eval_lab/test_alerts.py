"""
Tests for alert functionality.
"""

import pytest
from unittest.mock import Mock, patch
import requests

from src.eval_lab.alerts import (
    AlertConfig, EvaluationSummary, SlackNotifier, PagerDutyNotifier, AlertManager
)


class TestAlertConfig:
    """Test alert configuration."""
    
    def test_default_config(self):
        """Test default alert configuration."""
        config = AlertConfig()
        
        assert config.slack_webhook_url is None
        assert config.pagerduty_routing_key is None
        assert config.privacy_mode == "private_cloud"
        assert config.redact_sensitive is True
    
    def test_custom_config(self):
        """Test custom alert configuration."""
        config = AlertConfig(
            slack_webhook_url="https://hooks.slack.com/services/test",
            pagerduty_routing_key="test-key",
            privacy_mode="local_only",
            redact_sensitive=False
        )
        
        assert config.slack_webhook_url == "https://hooks.slack.com/services/test"
        assert config.pagerduty_routing_key == "test-key"
        assert config.privacy_mode == "local_only"
        assert config.redact_sensitive is False


class TestEvaluationSummary:
    """Test evaluation summary data class."""
    
    def test_evaluation_summary_creation(self):
        """Test creating an evaluation summary."""
        summary = EvaluationSummary(
            run_id="eval_run_123",
            suite_name="core_crm",
            total_cases=21,
            passed_cases=20,
            failed_cases=1,
            quarantined_cases=0,
            pass_rate=0.95,
            avg_latency_ms=2500,
            total_cost_usd=1.25,
            new_regressions=0,
            guard_breaches=0,
            report_url="https://example.com/report"
        )
        
        assert summary.run_id == "eval_run_123"
        assert summary.suite_name == "core_crm"
        assert summary.total_cases == 21
        assert summary.passed_cases == 20
        assert summary.failed_cases == 1
        assert summary.pass_rate == 0.95
        assert summary.avg_latency_ms == 2500
        assert summary.total_cost_usd == 1.25
        assert summary.new_regressions == 0
        assert summary.guard_breaches == 0
        assert summary.report_url == "https://example.com/report"
        assert summary.metadata == {}


class TestSlackNotifier:
    """Test Slack notification functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.webhook_url = "https://hooks.slack.com/services/test"
        self.notifier = SlackNotifier(self.webhook_url, "private_cloud")
    
    @patch('requests.post')
    def test_send_evaluation_summary_success(self, mock_post):
        """Test successful Slack notification."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        summary = EvaluationSummary(
            run_id="eval_run_123",
            suite_name="core_crm",
            total_cases=21,
            passed_cases=20,
            failed_cases=1,
            quarantined_cases=0,
            pass_rate=0.95,
            avg_latency_ms=2500,
            total_cost_usd=1.25,
            new_regressions=0,
            guard_breaches=0
        )
        
        success = self.notifier.send_evaluation_summary(summary)
        
        assert success is True
        mock_post.assert_called_once()
        
        # Verify the message structure
        call_args = mock_post.call_args
        assert call_args[0][0] == self.webhook_url
        assert call_args[1]['headers']['Content-Type'] == 'application/json'
        
        message = call_args[1]['json']
        assert 'attachments' in message
        assert len(message['attachments']) == 1
        assert message['attachments'][0]['title'] == "Evaluation Results: core_crm"
    
    @patch('requests.post')
    def test_send_evaluation_summary_failure(self, mock_post):
        """Test failed Slack notification."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        summary = EvaluationSummary(
            run_id="eval_run_123",
            suite_name="core_crm",
            total_cases=21,
            passed_cases=20,
            failed_cases=1,
            quarantined_cases=0,
            pass_rate=0.95,
            avg_latency_ms=2500,
            total_cost_usd=1.25,
            new_regressions=0,
            guard_breaches=0
        )
        
        success = self.notifier.send_evaluation_summary(summary)
        
        assert success is False
    
    @patch('requests.post')
    def test_send_evaluation_summary_exception(self, mock_post):
        """Test Slack notification with exception."""
        mock_post.side_effect = Exception("Network error")
        
        summary = EvaluationSummary(
            run_id="eval_run_123",
            suite_name="core_crm",
            total_cases=21,
            passed_cases=20,
            failed_cases=1,
            quarantined_cases=0,
            pass_rate=0.95,
            avg_latency_ms=2500,
            total_cost_usd=1.25,
            new_regressions=0,
            guard_breaches=0
        )
        
        success = self.notifier.send_evaluation_summary(summary)
        
        assert success is False
    
    @patch('requests.post')
    def test_send_guard_breach_alert(self, mock_post):
        """Test sending guard breach alert."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        success = self.notifier.send_guard_breach_alert(
            guard_name="pass_rate_minimum",
            metric="pass_rate",
            value=0.85,
            threshold=0.95,
            severity="error"
        )
        
        assert success is True
        mock_post.assert_called_once()
        
        # Verify the message structure
        call_args = mock_post.call_args
        message = call_args[1]['json']
        assert message['attachments'][0]['title'] == "🚨 KPI Guard Breach: pass_rate_minimum"
        assert message['attachments'][0]['color'] == "#ff0000"


class TestPagerDutyNotifier:
    """Test PagerDuty notification functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.routing_key = "test-routing-key"
        self.notifier = PagerDutyNotifier(self.routing_key, "private_cloud")
    
    @patch('requests.post')
    def test_send_critical_alert_success(self, mock_post):
        """Test successful PagerDuty alert."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response
        
        success = self.notifier.send_critical_alert(
            summary="Test alert",
            details={"test": "data"},
            severity="critical"
        )
        
        assert success is True
        mock_post.assert_called_once()
        
        # Verify the payload structure
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://events.pagerduty.com/v2/enqueue"
        
        payload = call_args[1]['json']
        assert payload['routing_key'] == self.routing_key
        assert payload['event_action'] == "trigger"
        assert payload['payload']['summary'] == "Test alert"
        assert payload['payload']['severity'] == "critical"
    
    @patch('requests.post')
    def test_send_critical_alert_failure(self, mock_post):
        """Test failed PagerDuty alert."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        success = self.notifier.send_critical_alert(
            summary="Test alert",
            details={"test": "data"},
            severity="critical"
        )
        
        assert success is False
    
    @patch('requests.post')
    def test_send_guard_breach_alert(self, mock_post):
        """Test sending guard breach alert to PagerDuty."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response
        
        success = self.notifier.send_guard_breach_alert(
            guard_name="pass_rate_minimum",
            metric="pass_rate",
            value=0.85,
            threshold=0.95,
            severity="critical"
        )
        
        assert success is True
        mock_post.assert_called_once()
        
        # Verify the payload structure
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['payload']['summary'] == "KPI Guard Breach: pass_rate_minimum"
        assert payload['payload']['severity'] == "critical"
    
    @patch('requests.post')
    def test_resolve_alert(self, mock_post):
        """Test resolving a PagerDuty alert."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_post.return_value = mock_response
        
        success = self.notifier.resolve_alert("test-dedup-key")
        
        assert success is True
        mock_post.assert_called_once()
        
        # Verify the payload structure
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['event_action'] == "resolve"
        assert payload['dedup_key'] == "test-dedup-key"


class TestAlertManager:
    """Test alert manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = AlertConfig(
            slack_webhook_url="https://hooks.slack.com/services/test",
            pagerduty_routing_key="test-key",
            privacy_mode="private_cloud"
        )
        self.manager = AlertManager(self.config)
    
    @patch.object(SlackNotifier, 'send_evaluation_summary')
    def test_send_evaluation_summary_slack_only(self, mock_slack):
        """Test sending evaluation summary to Slack only."""
        mock_slack.return_value = True
        
        summary = EvaluationSummary(
            run_id="eval_run_123",
            suite_name="core_crm",
            total_cases=21,
            passed_cases=20,
            failed_cases=1,
            quarantined_cases=0,
            pass_rate=0.95,
            avg_latency_ms=2500,
            total_cost_usd=1.25,
            new_regressions=0,
            guard_breaches=0
        )
        
        results = self.manager.send_evaluation_summary(summary)
        
        assert results["slack"] is True
        assert "pagerduty" not in results
        mock_slack.assert_called_once_with(summary)
    
    @patch.object(SlackNotifier, 'send_evaluation_summary')
    @patch.object(PagerDutyNotifier, 'send_critical_alert')
    def test_send_evaluation_summary_with_guard_breaches(self, mock_pagerduty, mock_slack):
        """Test sending evaluation summary with guard breaches."""
        mock_slack.return_value = True
        mock_pagerduty.return_value = True
        
        summary = EvaluationSummary(
            run_id="eval_run_123",
            suite_name="core_crm",
            total_cases=21,
            passed_cases=20,
            failed_cases=1,
            quarantined_cases=0,
            pass_rate=0.95,
            avg_latency_ms=2500,
            total_cost_usd=1.25,
            new_regressions=0,
            guard_breaches=3  # This should trigger PagerDuty
        )
        
        results = self.manager.send_evaluation_summary(summary)
        
        assert results["slack"] is True
        assert results["pagerduty"] is True
        mock_slack.assert_called_once_with(summary)
        mock_pagerduty.assert_called_once()
    
    @patch.object(SlackNotifier, 'send_guard_breach_alert')
    @patch.object(PagerDutyNotifier, 'send_guard_breach_alert')
    def test_send_guard_breach_alert(self, mock_pagerduty, mock_slack):
        """Test sending guard breach alert."""
        mock_slack.return_value = True
        mock_pagerduty.return_value = True
        
        results = self.manager.send_guard_breach_alert(
            guard_name="pass_rate_minimum",
            metric="pass_rate",
            value=0.85,
            threshold=0.95,
            severity="critical"
        )
        
        assert results["slack"] is True
        assert results["pagerduty"] is True
        mock_slack.assert_called_once()
        mock_pagerduty.assert_called_once()
    
    @patch.object(SlackNotifier, 'send_guard_breach_alert')
    @patch.object(PagerDutyNotifier, 'send_guard_breach_alert')
    def test_send_guard_breach_alert_warning_only(self, mock_pagerduty, mock_slack):
        """Test sending guard breach alert with warning severity."""
        mock_slack.return_value = True
        mock_pagerduty.return_value = True
        
        results = self.manager.send_guard_breach_alert(
            guard_name="pass_rate_minimum",
            metric="pass_rate",
            value=0.85,
            threshold=0.95,
            severity="warning"
        )
        
        assert results["slack"] is True
        assert "pagerduty" not in results  # PagerDuty only for critical
        mock_slack.assert_called_once()
        mock_pagerduty.assert_not_called()
    
    @patch.object(SlackNotifier, 'send_evaluation_summary')
    def test_send_flake_alert(self, mock_slack):
        """Test sending flake alert."""
        mock_slack.return_value = True
        
        results = self.manager.send_flake_alert(
            case_id="contact_create",
            suite_name="core_crm",
            flake_score=0.8,
            reason="High flake score"
        )
        
        assert results["slack"] is True
        mock_slack.assert_called_once()


class TestDataRedaction:
    """Test data redaction functionality."""
    
    def test_redact_sensitive_data(self):
        """Test redaction of sensitive data."""
        from src.eval_lab.alerts import redact_sensitive_data
        
        original_data = {
            "prompt": "Create a contact for John Doe",
            "input": "sensitive input data",
            "output": "contact created",
            "token_usage": {"total_tokens": 150},
            "safe_data": "this should remain"
        }
        
        redacted_data = redact_sensitive_data(original_data)
        
        assert redacted_data["prompt"] == "[REDACTED]"
        assert redacted_data["input"] == "[REDACTED]"
        assert redacted_data["output"] == "[REDACTED]"
        assert redacted_data["token_usage"] == "[REDACTED]"
        assert redacted_data["safe_data"] == "this should remain"
    
    def test_redact_nested_data(self):
        """Test redaction of nested sensitive data."""
        from src.eval_lab.alerts import redact_sensitive_data
        
        original_data = {
            "case_data": {
                "prompt": "sensitive prompt",
                "result": "sensitive result"
            },
            "metadata": {
                "token_usage": {"total": 100},
                "safe_info": "keep this"
            }
        }
        
        redacted_data = redact_sensitive_data(original_data)
        
        assert redacted_data["case_data"]["prompt"] == "[REDACTED]"
        assert redacted_data["case_data"]["result"] == "[REDACTED]"
        assert redacted_data["metadata"]["token_usage"] == "[REDACTED]"
        assert redacted_data["metadata"]["safe_info"] == "keep this"
