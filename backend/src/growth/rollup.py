"""
Daily metrics rollup service for growth intelligence
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
import json

logger = logging.getLogger(__name__)

class DailyRollupService:
    """Service for rolling up daily growth metrics"""
    
    def __init__(self):
        self.db = None
    
    def get_db_session(self):
        """Get database session"""
        from flask import current_app
        import sqlite3
        db_path = current_app.config.get("DATABASE", "system_builder_hub.db")
        return sqlite3.connect(db_path)
    
    def write_growth_metric(self, tenant_id: str, module: str, metric: str, value: float, metadata: Dict[str, Any] = None):
        """Write a growth metric to the database"""
        try:
            db = self.get_db_session()
            
            # Ensure growth_metrics table exists
            db.execute("""
                CREATE TABLE IF NOT EXISTS growth_metrics (
                    id TEXT PRIMARY KEY,
                    date DATE NOT NULL,
                    tenant_id TEXT NOT NULL,
                    module TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value REAL NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            import uuid
            metric_id = str(uuid.uuid4())
            today = date.today()
            metadata_json = json.dumps(metadata) if metadata else None
            
            db.execute("""
                INSERT INTO growth_metrics (id, date, tenant_id, module, metric, value, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (metric_id, today, tenant_id, module, metric, value, metadata_json))
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to write growth metric: {e}")
    
    def rollup_events(self, target_date: date = None) -> Dict[str, Any]:
        """Roll up events from sbh_events table into daily metrics"""
        if target_date is None:
            target_date = date.today()
        
        try:
            db = self.get_db_session()
            
            # Get events for the target date
            start_date = datetime.combine(target_date, datetime.min.time())
            end_date = datetime.combine(target_date, datetime.max.time())
            
            events_query = """
                SELECT event_type, tenant_id, details, created_at
                FROM sbh_events 
                WHERE created_at BETWEEN ? AND ?
            """
            
            events = db.execute(events_query, [start_date, end_date]).fetchall()
            
            # Aggregate metrics
            metrics = {
                "active_users": 0,
                "api_calls": 0,
                "trial_started": 0,
                "trial_expired": 0,
                "subscribed": 0,
                "canceled": 0,
                "mrr": 0.0
            }
            
            tenant_modules = set()
            
            for event in events:
                event_type, tenant_id, details_str, created_at = event
                
                if not tenant_id:
                    continue
                
                # Parse details
                try:
                    details = json.loads(details_str) if details_str else {}
                except:
                    details = {}
                
                # Count different event types
                if event_type in ["cobuilder_intent", "cobuilder_action_completed"]:
                    metrics["api_calls"] += 1
                    tenant_modules.add((tenant_id, details.get("module", "unknown")))
                
                elif event_type == "trial_started":
                    metrics["trial_started"] += 1
                    tenant_modules.add((tenant_id, details.get("module", "unknown")))
                
                elif event_type == "trial_expired":
                    metrics["trial_expired"] += 1
                
                elif event_type == "subscribed":
                    metrics["subscribed"] += 1
                    # Add MRR based on plan
                    plan = details.get("plan", "starter")
                    mrr_values = {"starter": 29.0, "professional": 99.0, "enterprise": 299.0}
                    metrics["mrr"] += mrr_values.get(plan, 29.0)
                
                elif event_type == "canceled":
                    metrics["canceled"] += 1
            
            # Count active users (unique tenants with activity)
            metrics["active_users"] = len(set(tenant for tenant, _ in tenant_modules))
            
            # Write metrics for each module
            for tenant_id, module in tenant_modules:
                for metric_name, value in metrics.items():
                    if value > 0:
                        self.write_growth_metric(
                            tenant_id=tenant_id,
                            module=module,
                            metric=metric_name,
                            value=value,
                            metadata={
                                "rollup_date": target_date.isoformat(),
                                "source": "daily_rollup"
                            }
                        )
            
            return {
                "date": target_date.isoformat(),
                "events_processed": len(events),
                "metrics_written": len(metrics),
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to rollup events: {e}")
            return {
                "date": target_date.isoformat(),
                "error": str(e)
            }
    
    def run_daily_rollup(self, target_date: date = None) -> Dict[str, Any]:
        """Run the complete daily rollup process"""
        try:
            logger.info("Starting daily metrics rollup")
            
            result = self.rollup_events(target_date)
            
            logger.info(f"Daily rollup completed: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Daily rollup failed: {e}")
            return {
                "error": str(e),
                "status": "failed"
            }
