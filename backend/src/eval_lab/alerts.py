"""
Evaluation Lab Alerts

Handles Slack and PagerDuty notifications for evaluation results.
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

from .redaction import redact_sensitive_data

logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """Configuration for alert notifications."""
    slack_webhook_url: Optional[str] = None
    pagerduty_routing_key: Optional[str] = None
    privacy_mode: str = "private_cloud"
    redact_sensitive: bool = True


@dataclass
class EvaluationSummary:
    """Summary of evaluation results for alerts."""
    run_id: str
    suite_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    quarantined_cases: int
    pass_rate: float
    avg_latency_ms: float
    total_cost_usd: float
    new_regressions: int
    guard_breaches: int
    report_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.meta_json is None:
            self.meta_json = {}


class SlackNotifier:
    """Handles Slack notifications for evaluation results."""
    
    def __init__(self, webhook_url: str, privacy_mode: str = "private_cloud"):
        self.webhook_url = webhook_url
        self.privacy_mode = privacy_mode
    
    def send_evaluation_summary(self, summary: EvaluationSummary) -> bool:
        """Send evaluation summary to Slack."""
        try:
            # Determine color based on pass rate
            if summary.pass_rate >= 0.95:
                color = "#36a64f"  # Green
            elif summary.pass_rate >= 0.85:
                color = "#ffa500"  # Orange
            else:
                color = "#ff0000"  # Red
            
            # Create Slack message
            message = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"Evaluation Results: {summary.suite_name}",
                        "title_link": summary.report_url,
                        "fields": [
                            {
                                "title": "Pass Rate",
                                "value": f"{summary.pass_rate:.1%}",
                                "short": True
                            },
                            {
                                "title": "Total Cases",
                                "value": str(summary.total_cases),
                                "short": True
                            },
                            {
                                "title": "Failed Cases",
                                "value": str(summary.failed_cases),
                                "short": True
                            },
                            {
                                "title": "Quarantined",
                                "value": str(summary.quarantined_cases),
                                "short": True
                            },
                            {
                                "title": "Avg Latency",
                                "value": f"{summary.avg_latency_ms:.0f}ms",
                                "short": True
                            },
                            {
                                "title": "Total Cost",
                                "value": f"${summary.total_cost_usd:.2f}",
                                "short": True
                            }
                        ],
                        "footer": f"Run ID: {summary.run_id}",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            # Add regressions and guard breaches if any
            if summary.new_regressions > 0 or summary.guard_breaches > 0:
                alert_fields = []
                if summary.new_regressions > 0:
                    alert_fields.append({
                        "title": "⚠️ New Regressions",
                        "value": str(summary.new_regressions),
                        "short": True
                    })
                if summary.guard_breaches > 0:
                    alert_fields.append({
                        "title": "🚨 Guard Breaches",
                        "value": str(summary.guard_breaches),
                        "short": True
                    })
                
                message["attachments"][0]["fields"].extend(alert_fields)
            
            # Redact sensitive data if needed
            if self.privacy_mode != "local_only" and summary.meta_json:
                redacted_metadata = redact_sensitive_data(summary.meta_json)
                if redacted_metadata != summary.meta_json:
                    message["attachments"][0]["text"] = "*Note: Sensitive data has been redacted*"
            
            # Send to Slack
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack notification sent for run {summary.run_id}")
                return True
            else:
                logger.error(f"Failed to send Slack notification: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    def send_guard_breach_alert(self, guard_name: str, metric: str, value: float, 
                               threshold: float, severity: str) -> bool:
        """Send alert for KPI guard breach."""
        try:
            color = "#ff0000" if severity == "critical" else "#ffa500"
            
            message = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 KPI Guard Breach: {guard_name}",
                        "fields": [
                            {
                                "title": "Metric",
                                "value": metric,
                                "short": True
                            },
                            {
                                "title": "Current Value",
                                "value": str(value),
                                "short": True
                            },
                            {
                                "title": "Threshold",
                                "value": str(threshold),
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": severity.upper(),
                                "short": True
                            }
                        ],
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Slack guard breach alert sent: {guard_name}")
                return True
            else:
                logger.error(f"Failed to send Slack guard breach alert: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Slack guard breach alert: {e}")
            return False


class PagerDutyNotifier:
    """Handles PagerDuty notifications for critical issues."""
    
    def __init__(self, routing_key: str, privacy_mode: str = "private_cloud"):
        self.routing_key = routing_key
        self.privacy_mode = privacy_mode
        self.pagerduty_url = "https://events.pagerduty.com/v2/enqueue"
    
    def send_critical_alert(self, summary: str, details: Dict[str, Any], 
                           severity: str = "critical") -> bool:
        """Send critical alert to PagerDuty."""
        try:
            # Map severity to PagerDuty severity
            pd_severity = "critical" if severity == "critical" else "warning"
            
            payload = {
                "routing_key": self.routing_key,
                "event_action": "trigger",
                "payload": {
                    "summary": summary,
                    "severity": pd_severity,
                    "source": "system-builder-hub-eval-lab",
                    "custom_details": details
                }
            }
            
            # Redact sensitive data if needed
            if self.privacy_mode != "local_only":
                payload["payload"]["custom_details"] = redact_sensitive_data(details)
            
            response = requests.post(
                self.pagerduty_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 202:
                logger.info(f"PagerDuty alert sent: {summary}")
                return True
            else:
                logger.error(f"Failed to send PagerDuty alert: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending PagerDuty alert: {e}")
            return False
    
    def send_guard_breach_alert(self, guard_name: str, metric: str, value: float, 
                               threshold: float, severity: str) -> bool:
        """Send PagerDuty alert for KPI guard breach."""
        summary = f"KPI Guard Breach: {guard_name}"
        details = {
            "guard_name": guard_name,
            "metric": metric,
            "current_value": value,
            "threshold": threshold,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.send_critical_alert(summary, details, severity)
    
    def resolve_alert(self, dedup_key: str) -> bool:
        """Resolve a PagerDuty alert."""
        try:
            payload = {
                "routing_key": self.routing_key,
                "event_action": "resolve",
                "dedup_key": dedup_key
            }
            
            response = requests.post(
                self.pagerduty_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 202:
                logger.info(f"PagerDuty alert resolved: {dedup_key}")
                return True
            else:
                logger.error(f"Failed to resolve PagerDuty alert: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error resolving PagerDuty alert: {e}")
            return False


class AlertManager:
    """Manages all alert notifications."""
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.slack_notifier = None
        self.pagerduty_notifier = None
        
        if config.slack_webhook_url:
            self.slack_notifier = SlackNotifier(
                config.slack_webhook_url, 
                config.privacy_mode
            )
        
        if config.pagerduty_routing_key:
            self.pagerduty_notifier = PagerDutyNotifier(
                config.pagerduty_routing_key,
                config.privacy_mode
            )
    
    def send_evaluation_summary(self, summary: EvaluationSummary) -> Dict[str, bool]:
        """Send evaluation summary to all configured channels."""
        results = {}
        
        if self.slack_notifier:
            results["slack"] = self.slack_notifier.send_evaluation_summary(summary)
        
        if self.pagerduty_notifier and summary.guard_breaches > 0:
            # Only send to PagerDuty if there are guard breaches
            results["pagerduty"] = self.pagerduty_notifier.send_critical_alert(
                f"Evaluation Guard Breaches: {summary.suite_name}",
                {
                    "run_id": summary.run_id,
                    "guard_breaches": summary.guard_breaches,
                    "pass_rate": summary.pass_rate,
                    "total_cases": summary.total_cases
                },
                "critical" if summary.guard_breaches > 2 else "warning"
            )
        
        return results
    
    def send_guard_breach_alert(self, guard_name: str, metric: str, value: float, 
                               threshold: float, severity: str) -> Dict[str, bool]:
        """Send guard breach alert to all configured channels."""
        results = {}
        
        if self.slack_notifier:
            results["slack"] = self.slack_notifier.send_guard_breach_alert(
                guard_name, metric, value, threshold, severity
            )
        
        if self.pagerduty_notifier and severity == "critical":
            results["pagerduty"] = self.pagerduty_notifier.send_guard_breach_alert(
                guard_name, metric, value, threshold, severity
            )
        
        return results
    
    def send_flake_alert(self, case_id: str, suite_name: str, flake_score: float, 
                        reason: str) -> Dict[str, bool]:
        """Send alert for flaky test case."""
        results = {}
        
        if self.slack_notifier:
            # Create a simple flake alert for Slack
            message = {
                "attachments": [
                    {
                        "color": "#ffa500",
                        "title": f"⚠️ Flaky Test Detected: {case_id}",
                        "fields": [
                            {
                                "title": "Suite",
                                "value": suite_name,
                                "short": True
                            },
                            {
                                "title": "Flake Score",
                                "value": f"{flake_score:.2f}",
                                "short": True
                            },
                            {
                                "title": "Reason",
                                "value": reason,
                                "short": False
                            }
                        ],
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            try:
                response = requests.post(
                    self.config.slack_webhook_url,
                    json=message,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                results["slack"] = response.status_code == 200
            except Exception as e:
                logger.error(f"Error sending flake alert to Slack: {e}")
                results["slack"] = False
        
        return results


# Simple redaction utility (placeholder - would integrate with existing redaction)
def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive data from alert payloads."""
    if not isinstance(data, dict):
        return data
    
    redacted = {}
    sensitive_keys = ["prompt", "input", "output", "error_message", "token_usage"]
    
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive_data(value)
        elif isinstance(value, list):
            redacted[key] = [redact_sensitive_data(item) if isinstance(item, dict) else item for item in value]
        else:
            redacted[key] = value
    
    return redacted
