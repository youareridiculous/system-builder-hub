"""
Meta-Builder v3 Failure Taxonomy & Classification
Comprehensive failure detection and classification system.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from uuid import UUID

logger = logging.getLogger(__name__)


class FailureType(str, Enum):
    """Failure types for classification."""
    TRANSIENT = "transient"  # Network, timeout, temporary issues
    INFRA = "infra"  # Infrastructure, deployment, environment issues
    TEST_ASSERT = "test_assert"  # Test failures, assertions
    LINT = "lint"  # Code style, formatting issues
    TYPECHECK = "typecheck"  # Type checking errors
    SECURITY = "security"  # Security violations, vulnerabilities
    POLICY = "policy"  # Policy violations, permissions
    RUNTIME = "runtime"  # Runtime errors, exceptions
    SCHEMA_MIGRATION = "schema_migration"  # Database schema issues
    RATE_LIMIT = "rate_limit"  # Rate limiting, throttling
    UNKNOWN = "unknown"  # Unclassified failures


class Severity(str, Enum):
    """Failure severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailureSignal:
    """Failure signal with comprehensive metadata."""
    type: FailureType
    source: str  # agent/step name
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)  # logs, stderr, stack traces
    artifact_ids: List[UUID] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM
    can_retry: bool = True
    requires_replan: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context


class FailureClassifier:
    """Deterministic failure classification using rules and patterns."""
    
    def __init__(self):
        self.patterns = self._load_classification_patterns()
        self.rules = self._load_classification_rules()
    
    def _load_classification_patterns(self) -> Dict[FailureType, List[Dict[str, Any]]]:
        """Load classification patterns for each failure type."""
        return {
            FailureType.TRANSIENT: [
                {
                    "pattern": r"Connection.*timeout|timeout.*error|Connection.*refused|timeout.*after",
                    "severity": Severity.LOW,
                    "can_retry": True,
                    "requires_replan": False
                },
                {
                    "pattern": r"Network.*unreachable|DNS.*resolution.*failed",
                    "severity": Severity.LOW,
                    "can_retry": True,
                    "requires_replan": False
                },
                {
                    "pattern": r"Temporary.*failure|Service.*unavailable.*temporarily",
                    "severity": Severity.LOW,
                    "can_retry": True,
                    "requires_replan": False
                }
            ],
            FailureType.INFRA: [
                {
                    "pattern": r"docker.*error|container.*failed|deployment.*failed",
                    "severity": Severity.MEDIUM,
                    "can_retry": True,
                    "requires_replan": False
                },
                {
                    "pattern": r"kubernetes.*error|pod.*failed|service.*unavailable",
                    "severity": Severity.MEDIUM,
                    "can_retry": True,
                    "requires_replan": False
                },
                {
                    "pattern": r"disk.*full|memory.*exhausted|resource.*quota.*exceeded",
                    "severity": Severity.HIGH,
                    "can_retry": True,
                    "requires_replan": False
                }
            ],
            FailureType.TEST_ASSERT: [
                {
                    "pattern": r"AssertionError|assert.*==.*|test.*failed|pytest.*FAILED",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"pytest.*FAILED|unittest.*AssertionError",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"expected.*but.*got|actual.*does.*not.*equal.*expected",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                }
            ],
            FailureType.LINT: [
                {
                    "pattern": r"E\d{3}|W\d{3}|F\d{3}",
                    "severity": Severity.LOW,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"black.*error|isort.*error|formatting.*error",
                    "severity": Severity.LOW,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"pylint.*error|C\d{4}|R\d{4}",
                    "severity": Severity.LOW,
                    "can_retry": False,
                    "requires_replan": False
                }
            ],
            FailureType.TYPECHECK: [
                {
                    "pattern": r"mypy.*error|type.*error|TypeError",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"incompatible.*type|type.*annotation.*error",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                }
            ],
            FailureType.SECURITY: [
                {
                    "pattern": r"security.*vulnerability|CVE-\d{4}-\d+",
                    "severity": Severity.HIGH,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"authentication.*failed|unauthorized.*access",
                    "severity": Severity.HIGH,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"injection.*attack|XSS|CSRF|SQL.*injection",
                    "severity": Severity.CRITICAL,
                    "can_retry": False,
                    "requires_replan": False
                }
            ],
            FailureType.POLICY: [
                {
                    "pattern": r"permission.*denied|access.*denied|forbidden",
                    "severity": Severity.HIGH,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"policy.*violation|compliance.*error",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"license.*error|terms.*violation",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                }
            ],
            FailureType.RUNTIME: [
                {
                    "pattern": r"RuntimeError|Exception.*occurred|Error.*occurred",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"ImportError|ModuleNotFoundError|NameError",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"SyntaxError|IndentationError|TabError",
                    "severity": Severity.MEDIUM,
                    "can_retry": False,
                    "requires_replan": False
                }
            ],
            FailureType.SCHEMA_MIGRATION: [
                {
                    "pattern": r"alembic.*error|migration.*failed|schema.*error",
                    "severity": Severity.HIGH,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"table.*does.*not.*exist|column.*does.*not.*exist",
                    "severity": Severity.HIGH,
                    "can_retry": False,
                    "requires_replan": False
                },
                {
                    "pattern": r"foreign.*key.*constraint|integrity.*error",
                    "severity": Severity.HIGH,
                    "can_retry": False,
                    "requires_replan": False
                }
            ],
            FailureType.RATE_LIMIT: [
                {
                    "pattern": r"429|HTTPError.*429|Too.*Many.*Requests",
                    "severity": Severity.LOW,
                    "can_retry": True,
                    "requires_replan": False
                },
                {
                    "pattern": r"quota.*exceeded|throttling.*error",
                    "severity": Severity.LOW,
                    "can_retry": True,
                    "requires_replan": False
                },
                {
                    "pattern": r"Retry-After.*header|X-RateLimit-Remaining.*0",
                    "severity": Severity.LOW,
                    "can_retry": True,
                    "requires_replan": False
                }
            ]
        }
    
    def _load_classification_rules(self) -> List[Dict[str, Any]]:
        """Load additional classification rules."""
        return [
            {
                "name": "consecutive_unknown_failures",
                "condition": lambda signals: len([s for s in signals if s.type == FailureType.UNKNOWN]) >= 2,
                "action": lambda signals: FailureType.UNKNOWN,
                "metadata": {"rule": "consecutive_unknown_failures", "requires_replan": True}
            },
            {
                "name": "mixed_failure_types",
                "condition": lambda signals: len(set(s.type for s in signals)) > 3,
                "action": lambda signals: FailureType.RUNTIME,
                "metadata": {"rule": "mixed_failure_types", "requires_replan": True}
            }
        ]
    
    def classify_failure(self, step_name: str, logs: str, artifacts: List[Dict[str, Any]], 
                        previous_signals: List[FailureSignal] = None) -> FailureSignal:
        """Classify a failure based on logs and context."""
        if previous_signals is None:
            previous_signals = []
        
        # Apply pattern matching
        best_match = self._find_best_pattern_match(logs)
        
        # Apply rules
        rule_result = self._apply_classification_rules(previous_signals + [best_match] if best_match else previous_signals)
        
        if rule_result:
            return rule_result
        
        if best_match:
            return best_match
        
        # Default to unknown
        return FailureSignal(
            type=FailureType.UNKNOWN,
            source=step_name,
            message="Unclassified failure",
            evidence={"logs": logs[:1000]},  # Limit log size
            severity=Severity.MEDIUM,
            can_retry=True,
            requires_replan=False
        )
    
    def _find_best_pattern_match(self, logs: str) -> Optional[FailureSignal]:
        """Find the best pattern match for the given logs."""
        best_match = None
        best_confidence = 0.0
        
        for failure_type, patterns in self.patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info["pattern"]
                confidence = self._calculate_pattern_confidence(logs, pattern)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = FailureSignal(
                        type=failure_type,
                        source="pattern_match",
                        message=f"Matched pattern: {pattern}",
                        evidence={"logs": logs[:1000], "pattern": pattern, "confidence": confidence},
                        severity=pattern_info["severity"],
                        can_retry=pattern_info["can_retry"],
                        requires_replan=pattern_info["requires_replan"]
                    )
        
        return best_match if best_confidence > 0.3 else None
    
    def _calculate_pattern_confidence(self, logs: str, pattern: str) -> float:
        """Calculate confidence score for pattern matching."""
        # Simple regex-based confidence scoring
        matches = re.findall(pattern, logs, re.IGNORECASE)
        
        if not matches:
            return 0.0
        
        # Base confidence on number of matches and pattern specificity
        match_count = len(matches)
        pattern_complexity = len(pattern.split("|"))  # Multiple alternatives reduce confidence
        
        base_confidence = min(0.9, 0.5 + (match_count * 0.1))
        complexity_factor = max(0.5, 1.0 - (pattern_complexity * 0.1))
        
        return base_confidence * complexity_factor
    
    def _apply_classification_rules(self, signals: List[FailureSignal]) -> Optional[FailureSignal]:
        """Apply classification rules to signals."""
        for rule in self.rules:
            if rule["condition"](signals):
                failure_type = rule["action"](signals)
                return FailureSignal(
                    type=failure_type,
                    source="classification_rule",
                    message=f"Applied rule: {rule['name']}",
                    evidence={"rule": rule["name"], "signals_count": len(signals)},
                    severity=Severity.MEDIUM,
                    can_retry=True,
                    requires_replan=rule["metadata"].get("requires_replan", False)
                )
        
        return None
    
    def extract_backoff_info(self, logs: str) -> Optional[Dict[str, Any]]:
        """Extract backoff information from logs (e.g., Retry-After headers)."""
        # Look for Retry-After headers
        retry_after_match = re.search(r"Retry-After:\s*(\d+)", logs, re.IGNORECASE)
        if retry_after_match:
            return {
                "retry_after_seconds": int(retry_after_match.group(1)),
                "source": "http_header"
            }
        
        # Look for rate limit info
        rate_limit_match = re.search(r"X-RateLimit-Reset:\s*(\d+)", logs, re.IGNORECASE)
        if rate_limit_match:
            return {
                "rate_limit_reset": int(rate_limit_match.group(1)),
                "source": "rate_limit_header"
            }
        
        return None


# Global classifier instance
classifier = FailureClassifier()


def classify_failure(step_name: str, logs: str, artifacts: List[Dict[str, Any]], 
                    previous_signals: List[FailureSignal] = None) -> FailureSignal:
    """Convenience function to classify a failure."""
    return classifier.classify_failure(step_name, logs, artifacts, previous_signals)
