"""
Automations engine for CRM/Ops Template
"""
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.database import db_session
from src.crm_ops.automations.models import AutomationRule, AutomationRun
from src.crm_ops.automations.actions import ActionExecutor
from src.crm_ops.automations.conditions import ConditionEvaluator
import redis
from src.config import get_config

logger = logging.getLogger(__name__)

class AutomationEngine:
    """Main automation engine for processing rules"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = redis.Redis.from_url(self.config.REDIS_URL)
        self.action_executor = ActionExecutor()
        self.condition_evaluator = ConditionEvaluator()
    
    def process_event(self, tenant_id: str, event_type: str, event_data: Dict[str, Any]) -> List[str]:
        """Process an event and execute matching automation rules"""
        run_ids = []
        
        with db_session() as session:
            # Find matching rules
            rules = session.query(AutomationRule).filter(
                AutomationRule.tenant_id == tenant_id,
                AutomationRule.enabled == True
            ).all()
            
            for rule in rules:
                try:
                    # Check if rule should be triggered
                    if self._should_trigger_rule(rule, event_type, event_data):
                        # Check idempotency
                        event_id = f"{event_type}:{event_data.get('id', 'unknown')}"
                        if self._is_duplicate_event(tenant_id, rule.id, event_id):
                            logger.info(f"Skipping duplicate event {event_id} for rule {rule.id}")
                            continue
                        
                        # Execute rule
                        run_id = self._execute_rule(session, rule, event_type, event_data, event_id)
                        if run_id:
                            run_ids.append(run_id)
                
                except Exception as e:
                    logger.error(f"Error processing rule {rule.id}: {e}")
                    continue
        
        return run_ids
    
    def _should_trigger_rule(self, rule: AutomationRule, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Check if a rule should be triggered by an event"""
        trigger = rule.trigger
        
        if trigger.get('type') == 'event':
            # Event-based trigger
            if trigger.get('event') == event_type:
                # Check conditions
                if rule.conditions:
                    return self.condition_evaluator.evaluate_conditions(rule.conditions, event_data)
                return True
        
        elif trigger.get('type') == 'cron':
            # Cron-based trigger (handled separately)
            return False
        
        return False
    
    def _is_duplicate_event(self, tenant_id: str, rule_id: str, event_id: str) -> bool:
        """Check if this event has already been processed for this rule"""
        key = f"automation:event:{tenant_id}:{rule_id}:{event_id}"
        return self.redis_client.exists(key)
    
    def _mark_event_processed(self, tenant_id: str, rule_id: str, event_id: str, ttl: int = 3600):
        """Mark an event as processed to prevent duplicates"""
        key = f"automation:event:{tenant_id}:{rule_id}:{event_id}"
        self.redis_client.setex(key, ttl, "1")
    
    def _execute_rule(self, session: Session, rule: AutomationRule, event_type: str, event_data: Dict[str, Any], event_id: str) -> Optional[str]:
        """Execute a single automation rule"""
        start_time = time.time()
        
        # Create run record
        run = AutomationRun(
            tenant_id=rule.tenant_id,
            rule_id=rule.id,
            status='running',
            started_at=datetime.utcnow(),
            input_snapshot=event_data,
            event_id=event_id
        )
        session.add(run)
        session.flush()
        
        try:
            # Execute actions
            results = []
            for action in rule.actions:
                try:
                    result = self.action_executor.execute_action(action, event_data, rule.tenant_id)
                    results.append({
                        'action': action,
                        'result': result,
                        'status': 'success'
                    })
                except Exception as e:
                    logger.error(f"Action execution failed: {e}")
                    results.append({
                        'action': action,
                        'result': str(e),
                        'status': 'failed'
                    })
                    
                    # Check if we should stop on failure
                    if action.get('stop_on_failure', True):
                        break
            
            # Update run record
            run.status = 'completed'
            run.finished_at = datetime.utcnow()
            run.result_snapshot = results
            run.duration_ms = int((time.time() - start_time) * 1000)
            
            # Mark event as processed
            self._mark_event_processed(rule.tenant_id, str(rule.id), event_id)
            
            session.commit()
            
            # Log metrics
            self._log_metrics(rule.tenant_id, 'automation_completed', run.duration_ms)
            
            return str(run.id)
            
        except Exception as e:
            logger.error(f"Rule execution failed: {e}")
            
            # Update run record with error
            run.status = 'failed'
            run.finished_at = datetime.utcnow()
            run.error = str(e)
            run.duration_ms = int((time.time() - start_time) * 1000)
            
            session.commit()
            
            # Log metrics
            self._log_metrics(rule.tenant_id, 'automation_failed', run.duration_ms)
            
            return str(run.id)
    
    def _log_metrics(self, tenant_id: str, metric_name: str, duration_ms: int = None):
        """Log metrics for monitoring"""
        try:
            # Increment counter
            self.redis_client.incr(f"metrics:{metric_name}:{tenant_id}")
            
            # Record duration if provided
            if duration_ms:
                self.redis_client.lpush(f"metrics:{metric_name}_duration:{tenant_id}", duration_ms)
                # Keep only last 100 values
                self.redis_client.ltrim(f"metrics:{metric_name}_duration:{tenant_id}", 0, 99)
        except Exception as e:
            logger.error(f"Error logging metrics: {e}")

class AutomationEventBus:
    """Event bus for triggering automations"""
    
    def __init__(self):
        self.engine = AutomationEngine()
    
    def emit_event(self, tenant_id: str, event_type: str, event_data: Dict[str, Any]):
        """Emit an event to trigger automations"""
        try:
            # Add metadata to event data
            event_data['_event_type'] = event_type
            event_data['_timestamp'] = datetime.utcnow().isoformat()
            event_data['_tenant_id'] = tenant_id
            
            # Process event
            run_ids = self.engine.process_event(tenant_id, event_type, event_data)
            
            logger.info(f"Emitted event {event_type} for tenant {tenant_id}, triggered {len(run_ids)} rules")
            
            return run_ids
            
        except Exception as e:
            logger.error(f"Error emitting event {event_type}: {e}")
            return []

# Global event bus instance
event_bus = AutomationEventBus()
