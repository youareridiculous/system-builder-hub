"""
Type definitions for Meta-Builder v3.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class AutoFixOutcome(Enum):
    """Possible outcomes of auto-fix operations."""
    RETRIED = "retried"
    PATCH_APPLIED = "patch_applied"
    REPLANNED = "replanned"
    ESCALATED = "escalated"
    GAVE_UP = "gave_up"


@dataclass
class RetryState:
    """State tracking for retry attempts."""
    attempt_counter: int = 0
    per_step_attempts: Dict[str, int] = None
    total_attempts: int = 0
    last_backoff_seconds: float = 0.0
    max_total_attempts: int = 6
    max_per_step_attempts: int = 3
    
    def __post_init__(self):
        if self.per_step_attempts is None:
            self.per_step_attempts = {}
    
    def can_retry_step(self, step_id: str) -> bool:
        """Check if we can retry a specific step."""
        step_attempts = self.per_step_attempts.get(step_id, 0)
        return step_attempts < self.max_per_step_attempts
    
    def can_retry_total(self) -> bool:
        """Check if we can retry overall."""
        return self.total_attempts < self.max_total_attempts
    
    def increment_step_attempt(self, step_id: str):
        """Increment attempt count for a step."""
        self.per_step_attempts[step_id] = self.per_step_attempts.get(step_id, 0) + 1
        self.total_attempts += 1
